"""
Knowledge Base — PDF library backed by Google Drive.

Files live in the user's Drive folder "knowledgebase2026"; this app
never copies them locally. Drive is the source of truth, so we don't
mirror a row per file. The only thing we persist is the folder id —
cached on the existing user_google_tokens row (see
MIGRATION_KNOWLEDGEBASE.sql) so we don't re-search Drive on every
page load.

Auth piggybacks on the existing Calendar OAuth flow in
routes/events.py. The drive.file scope was added to its SCOPES list,
so re-clicking "Connect Google" once issues a token that covers both
Calendar and this page.
"""
import io
import logging
import os

from flask import (
    Blueprint, Response, abort, jsonify, redirect, render_template, request,
    session, url_for,
)

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from auth import login_required
from supabase_client import get, update

logger = logging.getLogger("daily_plan")

knowledgebase_bp = Blueprint("knowledgebase", __name__)

KB_FOLDER_NAME = "knowledgebase2026"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB — bigger than photos


# ── Credentials ─────────────────────────────────────────────────


def _load_token_row(user_id: str):
    rows = get(
        "user_google_tokens",
        {"user_id": f"eq.{user_id}", "limit": "1"},
    )
    return rows[0] if rows else None


def _row_has_drive_scope(row: dict) -> bool:
    scopes = (row or {}).get("scopes") or ""
    return DRIVE_SCOPE in [s.strip() for s in scopes.split(",")]


def _credentials_from_row(row: dict) -> Credentials:
    scopes = [s.strip() for s in (row.get("scopes") or "").split(",") if s.strip()]
    return Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token"),
        token_uri=row.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=row.get("client_id") or os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=row.get("client_secret") or os.environ.get("GOOGLE_CLIENT_SECRET"),
        scopes=scopes,
    )


def _refresh_if_needed(creds: Credentials, user_id: str) -> Credentials:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        update(
            "user_google_tokens",
            params={"user_id": f"eq.{user_id}"},
            json={"access_token": creds.token},
        )
    return creds


# ── Drive helpers ───────────────────────────────────────────────


def _build_drive(creds: Credentials):
    # cache_discovery=False avoids a noisy oauth2client warning on
    # newer google-api-python-client; doesn't affect functionality.
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _ensure_folder(service, user_id: str, row: dict) -> str:
    """Return the Drive file_id of the knowledgebase2026 folder,
    creating it (and caching the id) on first use."""
    cached = (row or {}).get("kb_folder_id")
    if cached:
        # Verify the cached id still resolves — the user could have
        # trashed/renamed the folder from Drive itself.
        try:
            service.files().get(
                fileId=cached, fields="id, trashed"
            ).execute()
            return cached
        except HttpError as e:
            logger.info("kb_folder_id %s stale (%s), re-resolving", cached, e.status_code)

    # Search for an existing folder by name (only files the app can see
    # under drive.file — i.e. ones it previously created or the user
    # explicitly opened with it).
    q = (
        "mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{KB_FOLDER_NAME}' and trashed = false"
    )
    found = service.files().list(
        q=q, fields="files(id, name)", pageSize=1
    ).execute()
    files = found.get("files", [])
    if files:
        folder_id = files[0]["id"]
    else:
        created = service.files().create(
            body={
                "name": KB_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()
        folder_id = created["id"]
        logger.info("Created Drive folder %s for user %s", folder_id, user_id)

    update(
        "user_google_tokens",
        params={"user_id": f"eq.{user_id}"},
        json={"kb_folder_id": folder_id},
    )
    return folder_id


def _count_pdf_pages(blob: bytes):
    """Best-effort page count via pypdf. Returns int or None on failure
    (corrupt PDF, encrypted with unsupported cipher, etc.). Cheap —
    pypdf parses the xref table only; doesn't extract text."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(blob))
        return len(reader.pages)
    except Exception as e:
        logger.warning("kb page-count failed: %s", e)
        return None


def _format_file(f: dict) -> dict:
    size = f.get("size")
    # Page count lives in Drive's per-file appProperties so it sticks
    # to the file itself (no local DB row). Set on upload.
    props = f.get("appProperties") or {}
    pc_raw = props.get("page_count")
    try:
        page_count = int(pc_raw) if pc_raw not in (None, "") else None
    except (TypeError, ValueError):
        page_count = None
    return {
        "id": f.get("id"),
        "name": f.get("name") or "Untitled.pdf",
        "size_bytes": int(size) if size else None,
        "page_count": page_count,
        "created_at": f.get("createdTime"),
        "modified_at": f.get("modifiedTime"),
        "web_view": f.get("webViewLink"),
        "thumbnail": f.get("thumbnailLink"),
        "icon": f.get("iconLink"),
        # "purpose" is just Drive's native description field — visible
        # in Drive's own details pane too, so anything you set here
        # shows up in both places. Keeps us out of the local-DB business.
        "purpose": f.get("description") or "",
    }


# ── Page ────────────────────────────────────────────────────────


@knowledgebase_bp.route("/knowledge-base", methods=["GET"])
@login_required
def knowledge_base_page():
    """Render the page. The grid is hydrated client-side by
    /api/knowledge-base so the page itself stays snappy even when the
    Drive folder has dozens of PDFs."""
    user_id = session["user_id"]
    row = _load_token_row(user_id)
    connected = bool(row and row.get("refresh_token"))
    has_scope = _row_has_drive_scope(row) if row else False
    # Cached folder id (if the user has uploaded at least once) lets the
    # "Open in Drive" button render with a real href on first paint.
    # The client-side list response refreshes it after auto-create on
    # first ever upload.
    folder_id = (row or {}).get("kb_folder_id") or ""
    return render_template(
        "knowledgebase.html",
        connected=connected,
        has_scope=has_scope,
        folder_name=KB_FOLDER_NAME,
        folder_id=folder_id,
        connect_url=url_for("events.google_login"),
        max_upload_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
    )


# ── API ─────────────────────────────────────────────────────────


def _need_connect_response(row):
    if not row or not row.get("refresh_token"):
        return jsonify({"error": "not_connected", "connect_url": url_for("events.google_login")}), 401
    if not _row_has_drive_scope(row):
        return jsonify({"error": "scope_missing", "connect_url": url_for("events.google_login")}), 403
    return None


@knowledgebase_bp.route("/api/knowledge-base", methods=["GET"])
@login_required
def kb_list():
    user_id = session["user_id"]
    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError as e:
        logger.warning("kb refresh failed: %s", e)
        return jsonify({"error": "refresh_failed", "connect_url": url_for("events.google_login")}), 401

    service = _build_drive(creds)
    folder_id = _ensure_folder(service, user_id, row)

    q = (
        f"'{folder_id}' in parents and trashed = false "
        "and mimeType = 'application/pdf'"
    )
    try:
        listed = service.files().list(
            q=q,
            fields=(
                "files(id, name, size, createdTime, modifiedTime, "
                "webViewLink, thumbnailLink, iconLink, description, "
                "appProperties)"
            ),
            orderBy="createdTime desc",
            pageSize=200,
        ).execute()
    except HttpError as e:
        logger.exception("kb list failed: %s", e)
        return jsonify({"error": "Drive list failed."}), 502

    files = [_format_file(f) for f in listed.get("files", [])]
    return jsonify({"folder_id": folder_id, "files": files})


@knowledgebase_bp.route("/api/knowledge-base/upload", methods=["POST"])
@login_required
def kb_upload():
    user_id = session["user_id"]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    mime = (f.mimetype or "").lower()
    if mime != "application/pdf" and not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed."}), 400

    # Size check (stream is small enough to read fully into memory at
    # 25 MB cap; MediaIoBaseUpload wants a seekable stream anyway).
    blob = f.stream.read()
    if not blob:
        return jsonify({"error": "Empty file"}), 400
    if len(blob) > MAX_UPLOAD_BYTES:
        return jsonify({
            "error": f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
        }), 400

    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError as e:
        logger.warning("kb upload refresh failed: %s", e)
        return jsonify({"error": "refresh_failed", "connect_url": url_for("events.google_login")}), 401

    service = _build_drive(creds)
    folder_id = _ensure_folder(service, user_id, row)

    name = (request.form.get("name") or f.filename or "Upload.pdf").strip()[:200]
    if not name.lower().endswith(".pdf"):
        name = name + ".pdf"

    # Count pages locally so we don't have to download the file later
    # to know how long it is. None on failure — UI handles gracefully.
    page_count = _count_pdf_pages(blob)
    body = {"name": name, "parents": [folder_id]}
    if page_count is not None:
        # appProperties values must be strings; max 124 chars per key.
        body["appProperties"] = {"page_count": str(page_count)}

    media = MediaIoBaseUpload(io.BytesIO(blob), mimetype="application/pdf", resumable=False)
    try:
        created = service.files().create(
            body=body,
            media_body=media,
            fields=(
                "id, name, size, createdTime, modifiedTime, "
                "webViewLink, thumbnailLink, iconLink, description, "
                "appProperties"
            ),
        ).execute()
    except HttpError as e:
        logger.exception("kb upload failed: %s", e)
        return jsonify({"error": "Drive upload failed."}), 502

    return jsonify({"ok": True, "file": _format_file(created)})


@knowledgebase_bp.route("/api/knowledge-base/<file_id>/delete", methods=["POST"])
@login_required
def kb_delete(file_id):
    user_id = session["user_id"]
    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed"}), 401

    service = _build_drive(creds)
    try:
        # Send to trash rather than permanent-delete — matches the
        # soft-delete convention used everywhere else in this app.
        service.files().update(fileId=file_id, body={"trashed": True}).execute()
    except HttpError as e:
        logger.warning("kb delete failed for %s: %s", file_id, e)
        return jsonify({"error": "Delete failed."}), 502
    return jsonify({"ok": True})


@knowledgebase_bp.route("/api/knowledge-base/<file_id>/rename", methods=["POST"])
@login_required
def kb_rename(file_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip()[:200]
    if not new_name:
        return jsonify({"error": "Name required"}), 400
    if not new_name.lower().endswith(".pdf"):
        new_name = new_name + ".pdf"

    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed"}), 401

    service = _build_drive(creds)
    try:
        service.files().update(fileId=file_id, body={"name": new_name}).execute()
    except HttpError as e:
        logger.warning("kb rename failed for %s: %s", file_id, e)
        return jsonify({"error": "Rename failed."}), 502
    return jsonify({"ok": True, "name": new_name})


# ── Annotation editor (in-browser PDF.js + pdf-lib) ─────────────


@knowledgebase_bp.route("/knowledge-base/<file_id>/annotate", methods=["GET"])
@login_required
def kb_annotate_page(file_id):
    """Full-page editor. Loads the PDF via the /file endpoint and lets
    the user mark it up with highlight/underline/strike/pen/notes, then
    overwrites the original in Drive via /save."""
    user_id = session["user_id"]
    row = _load_token_row(user_id)
    if not row or not row.get("refresh_token") or not _row_has_drive_scope(row):
        # Send them back through the existing connect/re-consent flow.
        return redirect(url_for("knowledgebase.knowledge_base_page"))

    # Cheap metadata-only call so the header can show the real filename
    # without the client doing a second round-trip.
    file_name = "PDF"
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
        meta = _build_drive(creds).files().get(
            fileId=file_id, fields="name"
        ).execute()
        file_name = meta.get("name") or file_name
    except (RefreshError, HttpError) as e:
        logger.info("kb annotate: name lookup failed for %s (%s)", file_id, e)

    return render_template(
        "knowledgebase_annotate.html",
        file_id=file_id,
        file_name=file_name,
        back_url=url_for("knowledgebase.knowledge_base_page"),
    )


@knowledgebase_bp.route("/api/knowledge-base/<file_id>/file", methods=["GET"])
@login_required
def kb_download(file_id):
    """Stream the raw PDF bytes from Drive to the browser. The browser
    can't auth to Drive directly without leaking the OAuth token, so we
    proxy. Small files (≤25 MB cap) so a buffered read is fine."""
    user_id = session["user_id"]
    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed"}), 401

    service = _build_drive(creds)
    try:
        req = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    except HttpError as e:
        logger.warning("kb download failed for %s: %s", file_id, e)
        status = getattr(e, "status_code", 502) or 502
        return jsonify({"error": "Drive download failed."}), status

    data = buf.getvalue()
    resp = Response(data, mimetype="application/pdf")
    # Inline so PDF.js fetches it as bytes, not as a browser download.
    resp.headers["Content-Disposition"] = "inline"
    resp.headers["Content-Length"] = str(len(data))
    # Editor refetches on each open; no point caching across sessions
    # because the file could have been annotated and rewritten.
    resp.headers["Cache-Control"] = "no-store"
    return resp


@knowledgebase_bp.route("/api/knowledge-base/<file_id>/save", methods=["POST"])
@login_required
def kb_save_annotated(file_id):
    """Overwrite the existing Drive file with new PDF bytes. Same
    file_id, sharing, and Drive URL — Drive treats this as a new
    revision on the same file."""
    user_id = session["user_id"]

    # Accept either multipart upload (field name "file") or a raw
    # application/pdf body. Multipart is what the editor sends today.
    blob = None
    f = request.files.get("file")
    if f and f.filename:
        blob = f.stream.read()
    elif request.data and request.mimetype == "application/pdf":
        blob = request.data
    if not blob:
        return jsonify({"error": "No PDF body"}), 400
    if len(blob) > MAX_UPLOAD_BYTES:
        return jsonify({
            "error": f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
        }), 400

    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed"}), 401

    service = _build_drive(creds)

    # Refresh page count since the annotated copy might have changed
    # length (rare, but the bake process can re-flow if anything weird).
    page_count = _count_pdf_pages(blob)
    body = {}
    if page_count is not None:
        body["appProperties"] = {"page_count": str(page_count)}

    media = MediaIoBaseUpload(io.BytesIO(blob), mimetype="application/pdf", resumable=False)
    try:
        updated = service.files().update(
            fileId=file_id,
            body=body or None,
            media_body=media,
            fields=(
                "id, name, size, createdTime, modifiedTime, "
                "webViewLink, thumbnailLink, iconLink, description, "
                "appProperties"
            ),
        ).execute()
    except HttpError as e:
        logger.exception("kb save failed for %s: %s", file_id, e)
        return jsonify({"error": "Drive save failed."}), 502

    return jsonify({"ok": True, "file": _format_file(updated)})


@knowledgebase_bp.route("/api/knowledge-base/<file_id>/purpose", methods=["POST"])
@login_required
def kb_set_purpose(file_id):
    """Set the 'purpose' note on a PDF — stored in Drive's native
    description field so the value also shows up in Drive's own
    details pane. Empty string clears it."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    purpose = (data.get("purpose") or "").strip()[:500]

    row = _load_token_row(user_id)
    err = _need_connect_response(row)
    if err:
        return err
    try:
        creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed"}), 401

    service = _build_drive(creds)
    try:
        service.files().update(
            fileId=file_id, body={"description": purpose}
        ).execute()
    except HttpError as e:
        logger.warning("kb set_purpose failed for %s: %s", file_id, e)
        return jsonify({"error": "Save failed."}), 502
    return jsonify({"ok": True, "purpose": purpose})


# ── Backlog (per-user "to add" list) ────────────────────────────


BACKLOG_TITLE_MAX = 300
BACKLOG_NOTES_MAX = 2000


def _backlog_now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _backlog_author_name():
    """Display name for the current user, with the same email-local-part
    fallback the chat blueprint uses — keeps "created by" labels
    consistent across surfaces."""
    from flask_login import current_user
    name = (getattr(current_user, "display_name", "") or "").strip()
    if name:
        return name[:80]
    email = (getattr(current_user, "email", "") or "").strip()
    if email:
        return email.split("@", 1)[0][:80]
    return "Someone"


def _backlog_family_allowed():
    """True if the viewer is on the CHAT_USER_EMAILS allowlist. Lets
    `is_shared` items show up only to family members. Imports lazily
    so this module doesn't depend on chat existing at import time."""
    try:
        from routes.chat import user_allowed as _chat_allowed
        return _chat_allowed()
    except Exception:
        return False


def _backlog_shape(row, viewer_id):
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "notes": row.get("notes") or "",
        "done_at": row.get("done_at"),
        "is_done": bool(row.get("done_at")),
        "created_at": row.get("created_at"),
        "is_shared": bool(row.get("is_shared")),
        "created_by": row.get("user_id"),
        "created_by_name": row.get("created_by_name") or "",
        "mine": str(row.get("user_id")) == str(viewer_id),
    }


@knowledgebase_bp.route("/api/knowledge-base/backlog", methods=["GET"])
@login_required
def kb_backlog_list():
    """List backlog items. Modes:

      ?scope=mine   (default) — items I created with is_shared=false
      ?scope=family           — every shared item, by anyone in the
                                family allowlist; 403 if I'm not on it

    `?show_done=1` brings completed rows back into view (hidden by
    default so the panel stays focused on what's left).
    """
    user_id = session["user_id"]
    scope = (request.args.get("scope") or "mine").strip().lower()
    show_done = (request.args.get("show_done") or "").strip() in ("1", "true", "yes")

    params = {
        "deleted_at": "is.null",
        "select": "id,user_id,title,notes,done_at,created_at,is_shared,created_by_name",
        # Open items first (done_at NULL), then most-recently-added.
        "order": "done_at.asc.nullsfirst,created_at.desc",
        "limit": "200",
    }
    if scope == "family":
        if not _backlog_family_allowed():
            return jsonify({"error": "Not on the family allowlist"}), 403
        params["is_shared"] = "eq.true"
    else:
        # Personal scope = I'm the creator AND it isn't a shared row.
        # Shared rows (even if I created them) live on the Family tab so
        # each item shows up in exactly one place.
        params["user_id"] = f"eq.{user_id}"
        params["is_shared"] = "eq.false"

    if not show_done:
        params["done_at"] = "is.null"

    try:
        rows = get("kb_backlog", params) or []
    except Exception as e:
        # Most likely cause: migration not applied yet (is_shared column
        # missing). Don't 500 the page — return an empty list so the
        # panel renders quietly and the user can apply the migration.
        logger.warning("kb backlog list failed (migration pending?): %s", e)
        return jsonify({"items": [], "migration_pending": True})

    return jsonify({"items": [_backlog_shape(r, user_id) for r in rows]})


@knowledgebase_bp.route("/api/knowledge-base/backlog", methods=["POST"])
@login_required
def kb_backlog_create():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    title = title[:BACKLOG_TITLE_MAX]
    notes = (data.get("notes") or "").strip() or None
    if notes:
        notes = notes[:BACKLOG_NOTES_MAX]

    is_shared = bool(data.get("is_shared"))
    if is_shared and not _backlog_family_allowed():
        return jsonify({"error": "Not on the family allowlist"}), 403

    payload = {
        "user_id": user_id,
        "title": title,
        "notes": notes,
        "is_shared": is_shared,
        # Always stamp the display name so family rows can render
        # "added by …" without joining users — and so the label
        # survives a later rename.
        "created_by_name": _backlog_author_name(),
    }
    try:
        rows = post("kb_backlog", payload)
    except Exception as e:
        logger.exception("kb backlog create failed: %s", e)
        return jsonify({"error": "Create failed"}), 502

    row = rows[0] if rows else payload
    return jsonify({"item": _backlog_shape(row, user_id)})


@knowledgebase_bp.route("/api/knowledge-base/backlog/<item_id>/done", methods=["POST"])
@login_required
def kb_backlog_toggle_done(item_id):
    """Tick/untick. Body: {done: bool}; omit to toggle whatever the
    current state is. Permissions:

      Personal row (is_shared=false) — only the owner.
      Shared row  (is_shared=true)  — anyone on the family allowlist
                                       (collaborative ticking, like a
                                       shared todo list).
    """
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    rows = get("kb_backlog", {
        "id": f"eq.{item_id}",
        "deleted_at": "is.null",
        "select": "id,user_id,done_at,is_shared",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    cur = rows[0]

    if cur.get("is_shared"):
        if not _backlog_family_allowed():
            return jsonify({"error": "Not on the family allowlist"}), 403
    else:
        if str(cur.get("user_id")) != str(user_id):
            return jsonify({"error": "Not yours"}), 403

    if "done" in data:
        want_done = bool(data["done"])
    else:
        want_done = not bool(cur.get("done_at"))

    try:
        update(
            "kb_backlog",
            params={"id": f"eq.{item_id}"},
            json={"done_at": _backlog_now_iso() if want_done else None},
        )
    except Exception as e:
        logger.exception("kb backlog done toggle failed: %s", e)
        return jsonify({"error": "Save failed"}), 502
    return jsonify({"ok": True, "done": want_done})


@knowledgebase_bp.route("/api/knowledge-base/backlog/<item_id>/update", methods=["POST"])
@login_required
def kb_backlog_update(item_id):
    """Edit title / notes / scope. Only the creator can edit (same
    rule for personal and shared rows — keeps the model simple, matches
    family_tasks). Flipping `is_shared` requires the family allowlist.
    """
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    rows = get("kb_backlog", {
        "id": f"eq.{item_id}",
        "deleted_at": "is.null",
        "select": "id,user_id,is_shared",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    cur = rows[0]
    if str(cur.get("user_id")) != str(user_id):
        return jsonify({"error": "Only the creator can edit"}), 403

    patch = {}
    if "title" in data:
        v = (data.get("title") or "").strip()
        if not v:
            return jsonify({"error": "Title required"}), 400
        patch["title"] = v[:BACKLOG_TITLE_MAX]
    if "notes" in data:
        v = (data.get("notes") or "").strip()
        patch["notes"] = v[:BACKLOG_NOTES_MAX] if v else None
    if "is_shared" in data:
        want_shared = bool(data["is_shared"])
        if want_shared and not _backlog_family_allowed():
            return jsonify({"error": "Not on the family allowlist"}), 403
        patch["is_shared"] = want_shared

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update(
            "kb_backlog",
            params={"id": f"eq.{item_id}"},
            json=patch,
        )
    except Exception as e:
        logger.exception("kb backlog update failed: %s", e)
        return jsonify({"error": "Save failed"}), 502
    return jsonify({"ok": True, "patch": patch})


@knowledgebase_bp.route("/api/knowledge-base/backlog/<item_id>/delete", methods=["POST"])
@login_required
def kb_backlog_delete(item_id):
    """Soft-delete. Only the creator can remove — matches the edit
    permission rule and avoids "X deleted my backlog item" surprises
    on shared rows."""
    user_id = session["user_id"]
    rows = get("kb_backlog", {
        "id": f"eq.{item_id}",
        "deleted_at": "is.null",
        "select": "id,user_id",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    if str(rows[0].get("user_id")) != str(user_id):
        return jsonify({"error": "Only the creator can delete"}), 403

    try:
        update(
            "kb_backlog",
            params={"id": f"eq.{item_id}"},
            json={"deleted_at": _backlog_now_iso()},
        )
    except Exception as e:
        logger.exception("kb backlog delete failed: %s", e)
        return jsonify({"error": "Delete failed"}), 502
    return jsonify({"ok": True})

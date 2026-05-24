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
    Blueprint, jsonify, redirect, render_template, request, session, url_for,
)

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

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


def _format_file(f: dict) -> dict:
    size = f.get("size")
    return {
        "id": f.get("id"),
        "name": f.get("name") or "Untitled.pdf",
        "size_bytes": int(size) if size else None,
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
                "webViewLink, thumbnailLink, iconLink, description)"
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

    media = MediaIoBaseUpload(io.BytesIO(blob), mimetype="application/pdf", resumable=False)
    try:
        created = service.files().create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields=(
                "id, name, size, createdTime, modifiedTime, "
                "webViewLink, thumbnailLink, iconLink, description"
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

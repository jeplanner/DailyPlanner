"""
Family chat — one shared room, every allow-listed signed-in user is
implicitly a member. No DMs, no rooms, no membership table.

Visibility is gated by an email allowlist in the CHAT_USER_EMAILS env
var (comma-separated). Users not on the list see a 404 so the feature
is invisible — the nav link is also hidden by a context flag set in
app.py. Empty allowlist disables the feature for everyone (safe
default), matching the bedtime-stories pattern.

Delivery is 3-second polling (not websockets) so it works on Render's
free tier and keeps this blueprint to a single Flask file. Swap to
Supabase Realtime later if latency becomes the bottleneck — the wire
shape (a list of message rows with `created_at`) already matches a
realtime INSERT payload, so the frontend swap is small.

On send we fan a web-push notification out to every other allowlisted
user via services.push_service, in a daemon thread so the POST
returns immediately even if a recipient's push endpoint is slow.

Schema: see MIGRATION_CHAT.sql. `author_name` is denormalized at write
time so renaming a user doesn't rewrite history.
"""
import io
import logging
import os
import threading
from datetime import datetime, timezone

from flask import (
    Blueprint, Response, abort, jsonify, render_template, request, session,
    url_for,
)

from flask_login import current_user

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from auth import login_required
from services import push_service
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

chat_bp = Blueprint("chat", __name__)

MAX_BODY = 2000              # matches the CHECK in messages.body
INITIAL_FETCH = 100          # last-N on cold load
POLL_FETCH_LIMIT = 200       # cap per poll response — defends against
                             # very chatty intervals or a clock skew bug

# ── File attachments (Google Drive) ─────────────────────────────
CHAT_FOLDER_NAME = "DailyPlannerChat"
MAX_ATTACH_BYTES = 25 * 1024 * 1024  # 25 MB — matches the KB cap

# What people can attach. Images render inline, PDFs open in the
# in-app viewer, everything else gets a download/open chip. Kept to a
# known set so a stray .exe etc. can't land in someone's Drive.
_IMAGE_MIMES = {
    "image/png", "image/jpeg", "image/jpg", "image/gif",
    "image/webp", "image/heic", "image/bmp",
}
_DOC_MIMES = {
    "application/pdf",
    "text/plain", "text/csv", "text/markdown",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
}
_ALLOWED_MIMES = _IMAGE_MIMES | _DOC_MIMES

# Columns added by MIGRATION_CHAT_FILES.sql. Selected on top of the
# base set, but the list endpoint falls back to the base set if the
# migration hasn't run yet so chat never 500s on a cold schema.
_ATTACH_COLS = (
    "attachment_file_id,attachment_name,attachment_mime,"
    "attachment_kind,attachment_url,attachment_size"
)
_BASE_COLS = "id,user_id,author_name,body,created_at,kind"


# ── Allowlist ───────────────────────────────────────────────────


def _allowlist():
    """Lowercased set of emails allowed to use chat. Empty set ⇒
    feature is off for everyone (safe default)."""
    raw = os.environ.get("CHAT_USER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def user_allowed(user=None):
    """Used by every route guard and by the context processor in app.py
    that hides the nav link from non-allowed users."""
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    email = (getattr(user, "email", "") or "").lower()
    return email in _allowlist()


def _gate():
    """One-liner used at the top of every endpoint. Returning a 404
    (not a 403) means the route appears not to exist to non-allowed
    users — no leakage that the feature is even installed."""
    if not user_allowed():
        abort(404)


def _allowed_user_ids():
    """Resolve allowlisted emails to user_ids via the users table.
    Used to fan push notifications out to everyone in the room.
    The users table is small enough that a single round-trip is fine
    on every send — no caching needed yet."""
    emails = list(_allowlist())
    if not emails:
        return []
    # PostgREST in() filter: ?email=in.(a@b.com,c@d.com). Bare-comma
    # join works because emails can't contain commas or parens.
    rows = get("users", {
        "email": f"in.({','.join(emails)})",
        "select": "id,email",
    }) or []
    return [r["id"] for r in rows if r.get("id")]


def _utcnow_iso():
    # PostgREST returns timestamps with a "+00:00" offset; we mirror that
    # so the client's `since=...` value round-trips cleanly without any
    # timezone reformatting on either side.
    return datetime.now(timezone.utc).isoformat()


def _author_name():
    """Best-effort display name for the current user — falls back to
    the email local-part, then a placeholder. Empty names break the
    UI's bubble header, so we never return ''."""
    name = (getattr(current_user, "display_name", "") or "").strip()
    if name:
        return name[:80]
    email = (getattr(current_user, "email", "") or "").strip()
    if email:
        return email.split("@", 1)[0][:80]
    return "Someone"


def _shape(row, viewer_id):
    out = {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "author_name": row.get("author_name") or "Someone",
        "body": row.get("body") or "",
        "created_at": row.get("created_at"),
        "is_mine": str(row.get("user_id")) == str(viewer_id),
        # Default 'text' covers rows from before the kind column
        # landed AND any rows that came back without the column (e.g.
        # the schema-resilient retry stripping it).
        "kind": row.get("kind") or "text",
    }
    # Attachment block only present when the row actually carries a
    # Drive file. `raw_url` streams the bytes back through the app
    # (using the *author's* token) so every family member sees the
    # image/PDF inline without a Drive login. `url` is the Drive
    # webViewLink for "open in Drive".
    if row.get("attachment_file_id"):
        out["attachment"] = {
            "file_id": row.get("attachment_file_id"),
            "name": row.get("attachment_name") or "file",
            "mime": row.get("attachment_mime") or "",
            "kind": row.get("attachment_kind") or "file",
            "url": row.get("attachment_url") or "",
            "size_bytes": row.get("attachment_size"),
            "raw_url": url_for("chat.attachment_raw", msg_id=row.get("id")),
        }
    return out


def _fetch_messages(params):
    """get('messages', …) but tolerant of the attachment columns not
    existing yet (migration not applied). PostgREST 400s on a select
    that names an unknown column; the raised HTTPError doesn't carry the
    response body, so rather than sniff the message we just retry once
    with the base columns. If that also fails it's a real outage and the
    error propagates. Attachments simply won't render until the
    migration runs. Mirrors the migration-pending handling in
    routes/knowledgebase.py's backlog list."""
    try:
        return get("messages", params)
    except Exception as e:
        logger.warning("chat: message fetch with attachment cols failed, "
                        "retrying base columns (run MIGRATION_CHAT_FILES.sql?): %s", e)
        fallback = dict(params)
        fallback["select"] = _BASE_COLS
        return get("messages", fallback)


# ── Drive helpers (shared token row with Calendar + Knowledge Base) ──


def _drive_service_for(user_id):
    """Build a Drive client for `user_id`, refreshing the access token
    if needed. Returns (service, token_row), or (None, token_row) when
    the user hasn't connected Drive or hasn't granted the drive.file
    scope. Raises RefreshError if the stored refresh token is dead.

    Reuses the Knowledge-Base credential helpers so there's exactly one
    place that knows how to turn a token row into a Drive client."""
    from routes.knowledgebase import (
        _build_drive, _credentials_from_row, _load_token_row,
        _refresh_if_needed, _row_has_drive_scope,
    )
    row = _load_token_row(user_id)
    if not row or not row.get("refresh_token") or not _row_has_drive_scope(row):
        return None, row
    creds = _refresh_if_needed(_credentials_from_row(row), user_id)
    return _build_drive(creds), row


def _ensure_chat_folder(service, user_id, row):
    """Return the Drive id of the DailyPlannerChat folder, creating it
    (and caching the id on user_google_tokens.chat_folder_id) on first
    use. Verifies a cached id still resolves so a folder the user
    trashed from Drive gets recreated. Mirrors KB's _ensure_folder."""
    cached = (row or {}).get("chat_folder_id")
    if cached:
        try:
            service.files().get(fileId=cached, fields="id, trashed").execute()
            return cached
        except HttpError as e:
            logger.info("chat_folder_id %s stale (%s), re-resolving", cached, e)

    q = (
        "mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{CHAT_FOLDER_NAME}' and trashed = false"
    )
    found = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = found.get("files", [])
    if files:
        folder_id = files[0]["id"]
    else:
        created = service.files().create(
            body={"name": CHAT_FOLDER_NAME,
                  "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        folder_id = created["id"]
        logger.info("Created chat Drive folder %s for user %s", folder_id, user_id)

    update(
        "user_google_tokens",
        params={"user_id": f"eq.{user_id}"},
        json={"chat_folder_id": folder_id},
    )
    return folder_id


def _attachment_kind(mime: str) -> str:
    if mime in _IMAGE_MIMES:
        return "image"
    if mime == "application/pdf":
        return "pdf"
    return "file"


def _stream_drive_file(service, file_id, mime_hint=None, name_hint=None):
    """Download a Drive file's bytes and return a Flask Response that
    renders inline (image/PDF) or downloads (everything else). Shared by
    the chat-attachment proxy and the Drive-search preview. Returns None
    on a Drive error so the caller can 404/502."""
    try:
        meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        req = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    except HttpError as e:
        logger.warning("chat: drive file %s fetch failed: %s", file_id, e)
        return None

    data = buf.getvalue()
    mime = meta.get("mimeType") or mime_hint or "application/octet-stream"
    name = (meta.get("name") or name_hint or "file").replace('"', "")
    resp = Response(data, mimetype=mime)
    # Inline for images/PDFs (renders in the bubble / viewer); attachment
    # disposition for the rest so a click downloads with the real name.
    inline = mime.startswith("image/") or mime == "application/pdf"
    disp = "inline" if inline else "attachment"
    resp.headers["Content-Disposition"] = f'{disp}; filename="{name}"'
    resp.headers["Content-Length"] = str(len(data))
    # Per-user private cache — the bytes are immutable for a given file
    # revision, so a short cache avoids re-downloading on every scroll.
    resp.headers["Cache-Control"] = "private, max-age=3600"
    return resp


# ── Page ────────────────────────────────────────────────────────


@chat_bp.route("/chat", methods=["GET"])
@login_required
def chat_page():
    _gate()
    # Attaching files needs the Drive scope. Surface whether the viewer
    # has connected so the composer can show a "Connect Google Drive"
    # nudge instead of silently failing the upload. Reuses the KB
    # helpers — the same token row backs Calendar, KB and chat files.
    from routes.knowledgebase import _load_token_row, _row_has_drive_scope
    row = _load_token_row(session["user_id"])
    drive_ready = bool(row and row.get("refresh_token") and _row_has_drive_scope(row))
    return render_template(
        "chat.html",
        viewer_name=_author_name(),
        drive_ready=drive_ready,
        connect_url=url_for("events.google_login"),
        max_upload_mb=MAX_ATTACH_BYTES // (1024 * 1024),
    )


# ── API ─────────────────────────────────────────────────────────


@chat_bp.route("/api/chat/messages", methods=["GET"])
@login_required
def list_messages():
    """Two modes, distinguished by the presence of `since`:

      - No `since` (cold load): return the last INITIAL_FETCH messages,
        oldest-first so the frontend can append without reversing.
      - With `since` (poll): return messages strictly newer than that
        timestamp, oldest-first. Empty list when nothing new — the
        frontend uses that to know it can keep its existing `since`
        cursor or advance to `now`.

    The response always carries `now` so the next poll can use it as
    `since`, guaranteeing no message is skipped or double-delivered
    even if the server's clock differs from the client's.
    """
    _gate()
    viewer_id = session["user_id"]
    since = (request.args.get("since") or "").strip()

    params = {
        "deleted_at": "is.null",
        "select": f"{_BASE_COLS},{_ATTACH_COLS}",
    }
    if since:
        params["created_at"] = f"gt.{since}"
        params["order"] = "created_at.asc"
        params["limit"] = str(POLL_FETCH_LIMIT)
        rows = _fetch_messages(params)
    else:
        # Latest-N then reverse so the wire shape is consistent
        # (always oldest-first), saving the frontend a sort.
        params["order"] = "created_at.desc"
        params["limit"] = str(INITIAL_FETCH)
        rows = list(reversed(_fetch_messages(params)))

    return jsonify({
        "messages": [_shape(r, viewer_id) for r in rows],
        "now": _utcnow_iso(),
    })


@chat_bp.route("/api/chat/messages", methods=["POST"])
@login_required
def send_message():
    _gate()
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Empty message"}), 400
    if len(body) > MAX_BODY:
        return jsonify({"error": f"Message too long (max {MAX_BODY} chars)"}), 400

    viewer_id = session["user_id"]
    sender_name = _author_name()
    payload = {
        "user_id": viewer_id,
        "author_name": sender_name,
        "body": body,
    }
    try:
        rows = post("messages", payload)
    except Exception as e:
        logger.exception("chat send failed: %s", e)
        return jsonify({"error": "Send failed"}), 502

    row = rows[0] if rows else payload
    # Fire push fanout in the background — webpush calls hit each
    # browser's push service over HTTPS and can take seconds in the
    # worst case. We don't want the sender's POST to block on that.
    threading.Thread(
        target=_fanout_push,
        args=(viewer_id, sender_name, body),
        daemon=True,
    ).start()
    return jsonify({"message": _shape(row, viewer_id)})


# ── File attachments ────────────────────────────────────────────


@chat_bp.route("/api/chat/upload", methods=["POST"])
@login_required
def upload_attachment():
    """Upload a file (image / PDF / document) to the sender's Drive
    "DailyPlannerChat" folder and post it as a chat message. Optional
    `body` form field rides along as a caption. The file is shared with
    the rest of the family allowlist in the background so the link opens
    for everyone, exactly like a Knowledge-Base share."""
    _gate()
    viewer_id = session["user_id"]

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    mime = (f.mimetype or "application/octet-stream").lower()
    if mime not in _ALLOWED_MIMES:
        return jsonify({"error": "That file type isn't supported."}), 400

    blob = f.stream.read()
    if not blob:
        return jsonify({"error": "Empty file"}), 400
    if len(blob) > MAX_ATTACH_BYTES:
        return jsonify({
            "error": f"File too large (max {MAX_ATTACH_BYTES // (1024 * 1024)} MB).",
        }), 400

    try:
        service, row = _drive_service_for(viewer_id)
    except RefreshError as e:
        logger.warning("chat upload refresh failed: %s", e)
        return jsonify({"error": "refresh_failed", "connect_url": url_for("events.google_login")}), 401
    if not service:
        return jsonify({"error": "not_connected", "connect_url": url_for("events.google_login")}), 401

    folder_id = _ensure_chat_folder(service, viewer_id, row)
    name = (f.filename or "upload").strip()[:200]

    media = MediaIoBaseUpload(io.BytesIO(blob), mimetype=mime, resumable=False)
    try:
        created = service.files().create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id, name, size, mimeType, webViewLink",
        ).execute()
    except HttpError as e:
        logger.exception("chat upload failed: %s", e)
        return jsonify({"error": "Drive upload failed."}), 502

    file_id = created["id"]
    fname = created.get("name") or name
    caption = (request.form.get("body") or "").strip()[:MAX_BODY]
    sender_name = _author_name()

    payload = {
        "user_id": viewer_id,
        "author_name": sender_name,
        # body has a NOT-NULL + char_length>=1 check, so fall back to the
        # filename when there's no caption.
        "body": caption or fname,
        "kind": "file-share",
        "attachment_file_id": file_id,
        "attachment_name": fname,
        "attachment_mime": mime,
        "attachment_kind": _attachment_kind(mime),
        "attachment_url": created.get("webViewLink"),
        "attachment_size": int(created["size"]) if created.get("size") else None,
    }
    try:
        rows = post("messages", payload)
    except Exception as e:
        logger.exception("chat attachment insert failed: %s", e)
        return jsonify({"error": "Send failed"}), 502

    msg_row = rows[0] if rows else payload
    # Fan out Drive read perms + push, both off the request path.
    threading.Thread(
        target=_grant_drive_read_to_family,
        args=(viewer_id, file_id),
        daemon=True,
    ).start()
    threading.Thread(
        target=_fanout_push,
        args=(viewer_id, sender_name, f"📎 {fname}"),
        daemon=True,
    ).start()
    return jsonify({"message": _shape(msg_row, viewer_id)})


@chat_bp.route("/api/chat/attachment/<msg_id>", methods=["GET"])
@login_required
def attachment_raw(msg_id):
    """Stream a message attachment's bytes for inline display. Served
    using the *author's* Drive token (not the viewer's) so every family
    member sees the image/PDF without each one having opened the file in
    their own Drive — drive.file scope only exposes files the token's
    own app created, and the author's token is the one that created it."""
    _gate()
    rows = get("messages", {
        "id": f"eq.{msg_id}",
        "deleted_at": "is.null",
        "select": "id,user_id,attachment_file_id,attachment_mime,attachment_name",
        "limit": "1",
    }) or []
    if not rows or not rows[0].get("attachment_file_id"):
        abort(404)
    m = rows[0]

    try:
        service, _row = _drive_service_for(m["user_id"])
    except RefreshError:
        abort(502)
    if not service:
        abort(404)

    resp = _stream_drive_file(
        service, m["attachment_file_id"],
        mime_hint=m.get("attachment_mime"),
        name_hint=m.get("attachment_name"),
    )
    if resp is None:
        abort(502)
    return resp


# ── Drive search ────────────────────────────────────────────────


@chat_bp.route("/api/chat/drive-search", methods=["GET"])
@login_required
def drive_search():
    """Search the files this app can see in the viewer's Drive (their
    chat uploads + Knowledge-Base PDFs). `?q=` matches on the filename;
    an empty query returns the most recently modified files.

    Scope note: the drive.file OAuth scope only exposes files this app
    created or the user explicitly opened with it — by design, this can
    NOT search the user's entire Drive. Broadening to drive.readonly
    would trigger Google's app-verification review, which we avoid."""
    _gate()
    viewer_id = session["user_id"]
    qstr = (request.args.get("q") or "").strip()

    try:
        service, _row = _drive_service_for(viewer_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed", "connect_url": url_for("events.google_login")}), 401
    if not service:
        return jsonify({"error": "not_connected", "connect_url": url_for("events.google_login")}), 401

    q_parts = ["trashed = false",
               "mimeType != 'application/vnd.google-apps.folder'"]
    if qstr:
        # Escape backslashes then single-quotes for Drive's query syntax.
        safe = qstr.replace("\\", "\\\\").replace("'", "\\'")
        q_parts.append(f"name contains '{safe}'")
    q = " and ".join(q_parts)

    try:
        listed = service.files().list(
            q=q,
            fields=("files(id, name, mimeType, size, modifiedTime, "
                    "webViewLink, iconLink)"),
            orderBy="modifiedTime desc",
            pageSize=50,
        ).execute()
    except HttpError as e:
        logger.warning("chat drive-search failed: %s", e)
        return jsonify({"error": "Search failed."}), 502

    out = []
    for fi in listed.get("files", []):
        mime = fi.get("mimeType") or ""
        is_image = mime.startswith("image/")
        is_pdf = mime == "application/pdf"
        # google-native docs (Docs/Sheets/Slides) can't get_media, so
        # they only get an "open in Drive" link, no inline preview.
        native = mime.startswith("application/vnd.google-apps")
        out.append({
            "id": fi.get("id"),
            "name": fi.get("name"),
            "mime": mime,
            "is_image": is_image,
            "is_pdf": is_pdf,
            "size_bytes": int(fi["size"]) if fi.get("size") else None,
            "modified_at": fi.get("modifiedTime"),
            "web_view": fi.get("webViewLink"),
            "icon": fi.get("iconLink"),
            # Inline proxy (viewer's own token) for images/PDFs only.
            "raw_url": (None if native else url_for("chat.drive_file_raw", file_id=fi.get("id"))),
        })
    return jsonify({"files": out, "query": qstr})


@chat_bp.route("/api/chat/drive-file/<file_id>", methods=["GET"])
@login_required
def drive_file_raw(file_id):
    """Stream a Drive file via the viewer's own token — backs inline
    previews from the Drive-search panel. (The chat-stream proxy above
    uses the author's token instead, because there the viewer may not
    own the file.)"""
    _gate()
    try:
        service, _row = _drive_service_for(session["user_id"])
    except RefreshError:
        abort(502)
    if not service:
        abort(404)
    resp = _stream_drive_file(service, file_id)
    if resp is None:
        abort(502)
    return resp


# ── Share-to-chat (used by Inbox and Knowledge Base) ───────────


@chat_bp.route("/api/chat/share", methods=["POST"])
@login_required
def share_to_chat():
    """Post a chat message that originated from another page (Inbox
    row, KB row, future others). Body:

      { kind: "inbox" | "kb",
        url:  "<absolute http(s) URL>",
        title: "<short display label>",
        file_id: "<drive id, only when kind=kb>" }

    For kind=kb, we also grant Drive read permission to every other
    family member's email in a background thread, so the link the
    recipient is about to receive actually opens for them.
    """
    _gate()
    viewer_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    kind = (data.get("kind") or "").strip().lower()
    if kind not in ("inbox", "kb"):
        return jsonify({"error": "Unknown share kind"}), 400

    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL required"}), 400
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "URL must be http(s)://..."}), 400

    title = (data.get("title") or "").strip()[:160] or url[:160]
    sender_name = _author_name()

    if kind == "kb":
        file_id = (data.get("file_id") or "").strip()
        if not file_id:
            return jsonify({"error": "file_id required for KB shares"}), 400
        # Best-effort permission grant — don't block the chat send on it,
        # and don't fail the request if Drive complains. The recipient
        # might briefly see "request access" if they tap the link before
        # Drive finishes propagating, but they'll be fine on retry.
        threading.Thread(
            target=_grant_drive_read_to_family,
            args=(viewer_id, file_id),
            daemon=True,
        ).start()
        # Synchronously flip is_shared=true on the file so it moves
        # into the Family tab right away. Skipping background here:
        # the user's next list refresh should see the file in Family,
        # not stuck in Mine while a thread races to update appProperty.
        try:
            from routes.knowledgebase import (
                _build_drive,
                _credentials_from_row,
                _load_token_row,
                _refresh_if_needed,
                _set_file_shared,
            )
            from google.auth.exceptions import RefreshError as _RefreshError
            tok = _load_token_row(viewer_id)
            if tok and tok.get("refresh_token"):
                try:
                    creds = _refresh_if_needed(_credentials_from_row(tok), viewer_id)
                    _set_file_shared(_build_drive(creds), file_id, True)
                except _RefreshError:
                    pass
        except Exception:
            # Non-fatal — the chat message still posts, the file just
            # stays in Mine until the user moves it explicitly.
            logger.exception("chat share: set_file_shared failed")
        prefix = "📚 PDF shared"
    else:
        prefix = "📥 Saved link"

    body = f"{prefix}: {title}\n{url}"
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY]

    # The `kind` tag is what lets the chat UI filter shares away from
    # regular conversation. Maps 1:1 with the request `kind` and is
    # constrained at the DB level by messages_kind_chk.
    payload = {
        "user_id": viewer_id,
        "author_name": sender_name,
        "body": body,
        "kind": "kb-share" if kind == "kb" else "inbox-share",
    }
    try:
        rows = post("messages", payload)
    except Exception as e:
        logger.exception("chat share failed: %s", e)
        return jsonify({"error": "Share failed"}), 502

    row = rows[0] if rows else payload
    threading.Thread(
        target=_fanout_push,
        args=(viewer_id, sender_name, body),
        daemon=True,
    ).start()
    return jsonify({"message": _shape(row, viewer_id)})


def _grant_drive_read_to_family(sender_id, file_id):
    """Best-effort: give every other family member read access to a
    Drive file the sender owns. Idempotent at Drive's end — granting
    the same permission twice is a no-op. Failures (token expired,
    file moved, permission already exists in a way Drive doesn't like)
    are logged and swallowed; the chat message has already gone out
    by the time this runs."""
    try:
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError
        # Import lazily so this module doesn't drag the Drive client in
        # for users who never share a KB file.
        from routes.knowledgebase import (
            _build_drive,
            _credentials_from_row,
            _load_token_row,
            _refresh_if_needed,
        )

        row = _load_token_row(sender_id)
        if not row or not row.get("refresh_token"):
            logger.info("share: sender %s has no Drive token; skipping perm grant", sender_id)
            return
        try:
            creds = _refresh_if_needed(_credentials_from_row(row), sender_id)
        except RefreshError as e:
            logger.warning("share: drive token refresh failed for %s (%s)", sender_id, e)
            return
        service = _build_drive(creds)

        # Sender's own email — we don't want to grant them a permission
        # they already implicitly have as owner. Look it up via users.
        urows = get("users", {"id": f"eq.{sender_id}", "select": "email", "limit": "1"}) or []
        sender_email = (urows[0].get("email", "") if urows else "").strip().lower()

        for email in _allowlist():
            if email == sender_email:
                continue
            try:
                service.permissions().create(
                    fileId=file_id,
                    body={"type": "user", "role": "reader", "emailAddress": email},
                    sendNotificationEmail=False,
                    fields="id",
                ).execute()
            except HttpError as e:
                # 400 "Sharing permission already exists" is the common
                # case — Drive doesn't dedupe these so we just log and
                # move on. Anything else is also worth a single log line
                # but not a retry.
                logger.info("share: drive grant to %s on %s skipped (%s)", email, file_id, e)
            except Exception:
                logger.exception("share: drive grant to %s on %s raised", email, file_id)
    except Exception:
        logger.exception("share: drive perm fanout crashed")


def _fanout_push(sender_id, sender_name, body):
    """Best-effort notify everyone else in the room. Swallows all
    exceptions — push delivery should never be able to crash a send."""
    try:
        recipients = _allowed_user_ids()
        if not recipients:
            return
        # Keep the body short so it renders cleanly inside the OS-level
        # notification on Android, iOS, macOS, and Windows — they all
        # truncate, but the cutoff is ugly. 120 chars is comfortable.
        preview = body if len(body) <= 120 else body[:119] + "…"
        for uid in recipients:
            if str(uid) == str(sender_id):
                continue
            try:
                push_service.send_to_user(
                    user_id=uid,
                    title=sender_name or "New message",
                    body=preview,
                    url="/chat",
                    # `tag` makes subsequent messages collapse into one
                    # notification per browser so a chatty conversation
                    # doesn't spam the notification tray.
                    tag="chat",
                )
            except Exception:
                logger.exception("chat push to %s failed", uid)
    except Exception:
        logger.exception("chat push fanout failed")


# ── Unread badge (drives the top-nav icon on every page) ───────


# Cap returned to the badge so we never have to count past this. The
# UI just shows "99+" when capped — actual count matters less than
# "something new is waiting".
UNREAD_CAP = 99


@chat_bp.route("/api/chat/unread-count", methods=["GET"])
@login_required
def unread_count():
    """Cheap endpoint polled by the top-nav badge from every page.
    Returns 0 for non-allowlisted users so the global script can run
    blindly without a permissions check on the client."""
    if not user_allowed():
        return jsonify({"count": 0})

    viewer_id = session["user_id"]

    # Defensive: if the chat_last_read_at column doesn't exist yet
    # (migration not run), fall through with last_read=None so the
    # endpoint reports unread = total-other-messages, which is at least
    # honest. A 500 here would break the badge on every page in the app.
    last_read = None
    try:
        urows = get("users", {
            "id": f"eq.{viewer_id}",
            "select": "chat_last_read_at",
            "limit": "1",
        }) or []
        if urows:
            last_read = urows[0].get("chat_last_read_at")
    except Exception as e:
        logger.warning("chat unread: read-cursor lookup failed (%s)", e)

    params = {
        "deleted_at": "is.null",
        "user_id": f"neq.{viewer_id}",
        "select": "id",
        # Cap+1 so we know whether the actual count exceeds the cap.
        "limit": str(UNREAD_CAP + 1),
    }
    if last_read:
        params["created_at"] = f"gt.{last_read}"

    try:
        rows = get("messages", params) or []
    except Exception as e:
        logger.warning("chat unread: message query failed (%s)", e)
        return jsonify({"count": 0})

    n = len(rows)
    return jsonify({
        "count": min(n, UNREAD_CAP),
        "capped": n > UNREAD_CAP,
    })


@chat_bp.route("/api/chat/mark-read", methods=["POST"])
@login_required
def mark_read():
    """Advance the viewer's read cursor to now. Called by the chat page
    on open, on poll-while-at-bottom, and on tab refocus. Safe to spam —
    the underlying UPDATE is idempotent."""
    _gate()
    viewer_id = session["user_id"]
    try:
        update(
            "users",
            params={"id": f"eq.{viewer_id}"},
            json={"chat_last_read_at": _utcnow_iso()},
        )
    except Exception as e:
        logger.exception("chat mark-read failed: %s", e)
        return jsonify({"error": "Mark-read failed"}), 502
    return jsonify({"ok": True})


@chat_bp.route("/api/chat/messages/<msg_id>", methods=["DELETE"])
@login_required
def delete_message(msg_id):
    """Soft-delete (matches the project convention — no hard DELETE).
    Senders can remove their own messages; nobody can remove anyone
    else's. RLS would enforce this server-side too, but since we hit
    Supabase with the service key from Flask, we gate it here."""
    _gate()
    viewer_id = session["user_id"]
    # Pull the row first so we can confirm ownership without trusting
    # whatever the client sent.
    rows = get("messages", {
        "id": f"eq.{msg_id}",
        "select": "id,user_id,deleted_at",
        "limit": "1",
    })
    if not rows:
        return jsonify({"error": "Not found"}), 404
    if str(rows[0].get("user_id")) != str(viewer_id):
        return jsonify({"error": "Not yours"}), 403

    try:
        update(
            "messages",
            params={"id": f"eq.{msg_id}"},
            json={"deleted_at": _utcnow_iso()},
        )
    except Exception as e:
        logger.exception("chat delete failed: %s", e)
        return jsonify({"error": "Delete failed"}), 502
    return jsonify({"ok": True})

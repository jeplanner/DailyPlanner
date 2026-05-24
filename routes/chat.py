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
import logging
import os
import threading
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, render_template, request, session

from flask_login import current_user

from auth import login_required
from services import push_service
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

chat_bp = Blueprint("chat", __name__)

MAX_BODY = 2000              # matches the CHECK in messages.body
INITIAL_FETCH = 100          # last-N on cold load
POLL_FETCH_LIMIT = 200       # cap per poll response — defends against
                             # very chatty intervals or a clock skew bug


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
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "author_name": row.get("author_name") or "Someone",
        "body": row.get("body") or "",
        "created_at": row.get("created_at"),
        "is_mine": str(row.get("user_id")) == str(viewer_id),
    }


# ── Page ────────────────────────────────────────────────────────


@chat_bp.route("/chat", methods=["GET"])
@login_required
def chat_page():
    _gate()
    return render_template(
        "chat.html",
        viewer_name=_author_name(),
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
        "select": "id,user_id,author_name,body,created_at",
    }
    if since:
        params["created_at"] = f"gt.{since}"
        params["order"] = "created_at.asc"
        params["limit"] = str(POLL_FETCH_LIMIT)
        rows = get("messages", params)
    else:
        # Latest-N then reverse so the wire shape is consistent
        # (always oldest-first), saving the frontend a sort.
        params["order"] = "created_at.desc"
        params["limit"] = str(INITIAL_FETCH)
        rows = list(reversed(get("messages", params)))

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

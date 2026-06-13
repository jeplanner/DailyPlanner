"""
Admin → Usage dashboard.

A single read-only page that surfaces the usage numbers we *can*
measure from inside the app:

  - Supabase row counts (chat messages, users, connected Google
    accounts) — a proxy for how full the 500 MB free-tier DB is.
  - Google Drive storage per connected account, read live via each
    user's stored OAuth token (about.get).
  - Which chat-files migration columns are present, so a partially
    applied migration is obvious at a glance.

The billing meters we *can't* read without a provider API key (Render
instance-hours / bandwidth, Supabase egress, Gemini / Groq quota) are
listed with their free-tier limits and a direct dashboard link.

Access is gated to an admin allowlist: ADMIN_EMAILS (comma-separated)
if set, otherwise the chat family allowlist (CHAT_USER_EMAILS). Empty
⇒ nobody, and the route 404s for non-admins so it's invisible.
"""
import logging
import os

import requests
from flask import Blueprint, abort, jsonify, render_template, session
from flask_login import current_user

from auth import login_required
from supabase_client import SUPABASE_KEY, SUPABASE_URL, get, update

logger = logging.getLogger("daily_plan")

admin_bp = Blueprint("admin", __name__)

# Free-tier limits + where to read the meter we can't reach from here.
# Purely reference data rendered on the page.
EXTERNAL_METERS = [
    {"name": "Render — instance hours", "limit": "750 hrs / month",
     "url": "https://dashboard.render.com",
     "note": "One always-on service ≈ 744 hrs, just under the cap."},
    {"name": "Render — bandwidth", "limit": "100 GB / month",
     "url": "https://dashboard.render.com",
     "note": "Attachment previews stream through here (1 h browser cache)."},
    {"name": "Supabase — database size", "limit": "500 MB",
     "url": "https://supabase.com/dashboard/project/{ref}/reports",
     "note": "Text + metadata only; files live in Google Drive."},
    {"name": "Supabase — egress", "limit": "5 GB / month",
     "url": "https://supabase.com/dashboard/project/{ref}/reports",
     "note": "Polling responses are tiny (empty list + timestamp)."},
    {"name": "Gemini API (GOOGLE_API_KEY)", "limit": "Free tier quota",
     "url": "https://console.cloud.google.com/apis/dashboard",
     "note": "AI parsing/assist calls."},
    {"name": "Groq API (GROQ_API_KEY)", "limit": "Free tier quota",
     "url": "https://console.groq.com/settings/limits",
     "note": "Llama fallback for AI features."},
    {"name": "Google One storage", "limit": "Per account",
     "url": "https://one.google.com/storage", "note": "Where Drive files count."},
]


def _admin_emails():
    raw = (os.environ.get("ADMIN_EMAILS") or "").strip()
    if raw:
        return {e.strip().lower() for e in raw.split(",") if e.strip()}
    # No explicit admin list → fall back to the chat family allowlist.
    try:
        from routes.chat import _allowlist
        return _allowlist()
    except Exception:
        return set()


def _gate():
    email = (getattr(current_user, "email", "") or "").lower()
    if not email or email not in _admin_emails():
        abort(404)


def _project_ref():
    """Extract the Supabase project ref from the URL (the subdomain)
    so the dashboard links point at the right project."""
    try:
        host = SUPABASE_URL.split("://", 1)[-1]
        return host.split(".", 1)[0]
    except Exception:
        return ""


def _count(path, select, extra=""):
    """Exact row count via PostgREST's Content-Range header. Returns an
    int, or None if the column/table errored (e.g. migration pending)."""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{path}",
            params={"select": select, **dict([extra.split("=", 1)] if extra else [])},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Prefer": "count=exact", "Range": "0-0"},
            timeout=15,
        )
        cr = r.headers.get("content-range", "")
        if "/" in cr and cr.split("/")[-1].isdigit():
            return int(cr.split("/")[-1])
    except Exception as e:
        logger.warning("admin count %s failed: %s", path, e)
    return None


def _column_exists(table, col):
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params={"select": col, "limit": "1"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
        return r.ok
    except Exception:
        return False


def _gb(x):
    try:
        return round(int(x) / 1024 / 1024 / 1024, 2)
    except (TypeError, ValueError):
        return None


def _drive_quotas():
    """Live Drive storage per connected account. Each entry is
    best-effort — a dead token / API error becomes an error row rather
    than failing the whole page."""
    out = []
    try:
        from supabase_client import get
        from routes.knowledgebase import (
            _build_drive, _credentials_from_row, _load_token_row, _refresh_if_needed,
        )
    except Exception as e:
        logger.warning("admin drive import failed: %s", e)
        return out

    toks = get("user_google_tokens", {"select": "user_id"}) or []
    for t in toks:
        uid = t.get("user_id")
        try:
            row = _load_token_row(uid)
            creds = _refresh_if_needed(_credentials_from_row(row), uid)
            about = _build_drive(creds).about().get(fields="storageQuota,user").execute()
            q = about.get("storageQuota", {}) or {}
            limit = _gb(q.get("limit"))
            out.append({
                "email": (about.get("user", {}) or {}).get("emailAddress", "?"),
                "used_gb": _gb(q.get("usage")),
                "limit_gb": limit,            # None ⇒ unlimited / pooled
                "in_drive_gb": _gb(q.get("usageInDrive")),
                "error": None,
            })
        except Exception as e:
            out.append({"email": f"user {str(uid)[:8]}…", "error": f"{type(e).__name__}",
                        "used_gb": None, "limit_gb": None, "in_drive_gb": None})
    return out


def _gather():
    ref = _project_ref()
    has_attach = _column_exists("messages", "attachment_file_id")
    supabase = {
        "messages": _count("messages", "id"),
        "messages_deleted": _count("messages", "id", "deleted_at=not.is.null"),
        "messages_with_files": _count("messages", "id", "attachment_file_id=not.is.null") if has_attach else None,
        "users": _count("users", "id"),
        "connected_accounts": _count("user_google_tokens", "user_id"),
    }
    migrations = {
        "messages.attachment_file_id": has_attach,
        "messages.edited_at": _column_exists("messages", "edited_at"),
        "user_google_tokens.chat_folder_id": _column_exists("user_google_tokens", "chat_folder_id"),
    }
    meters = [{**m, "url": m["url"].replace("{ref}", ref)} for m in EXTERNAL_METERS]
    return {
        "supabase": supabase,
        "drive": _drive_quotas(),
        "migrations": migrations,
        "meters": meters,
        "project_ref": ref,
        "users": _list_users(),
        "viewer_id": session.get("user_id"),
    }


def _list_users():
    """All accounts for the admin user-management table."""
    try:
        rows = get("users", {
            "select": "id,email,display_name,is_active,created_at",
            "order": "created_at.asc",
        }) or []
    except Exception as e:
        logger.warning("admin user list failed: %s", e)
        return []
    return [{
        "id": r.get("id"),
        "email": r.get("email"),
        "display_name": r.get("display_name") or (r.get("email") or "").split("@", 1)[0],
        "is_active": bool(r.get("is_active", True)),
        "created_at": r.get("created_at"),
    } for r in rows]


@admin_bp.route("/admin/usage", methods=["GET"])
@login_required
def usage_page():
    _gate()
    return render_template("admin_usage.html", data=_gather())


@admin_bp.route("/api/admin/usage", methods=["GET"])
@login_required
def usage_api():
    _gate()
    return jsonify(_gather())


def _set_user_active(user_id, active):
    """Flip a user's is_active. Disabling cuts existing sessions too:
    the Flask-Login user loader (User.get) only loads is_active=true
    rows, so the next request from a disabled user resolves to anonymous
    and bounces to /login."""
    update("users", params={"id": f"eq.{user_id}"}, json={"is_active": active})


@admin_bp.route("/api/admin/users/<user_id>/disable", methods=["POST"])
@login_required
def disable_user(user_id):
    _gate()
    if str(user_id) == str(session.get("user_id")):
        return jsonify({"error": "You can't disable your own account."}), 400
    try:
        _set_user_active(user_id, False)
    except Exception as e:
        logger.exception("disable user failed: %s", e)
        return jsonify({"error": "Couldn't disable account"}), 502
    return jsonify({"ok": True})


@admin_bp.route("/api/admin/users/<user_id>/enable", methods=["POST"])
@login_required
def enable_user(user_id):
    _gate()
    try:
        _set_user_active(user_id, True)
    except Exception as e:
        logger.exception("enable user failed: %s", e)
        return jsonify({"error": "Couldn't enable account"}), 502
    return jsonify({"ok": True})

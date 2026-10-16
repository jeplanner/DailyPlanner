"""Who may see Interview Prep.

Interview Prep is the whole prep group in the nav: Interview Prep (with
case rounds, behavioural, system design, guides and Random thoughts),
AI SDE Prep (with its own Random thoughts), Java and SQL, and every
/api/... route behind them. It is personal study material, so only these
accounts see it. Everyone else gets no nav links and a plain 404, the
same way bedtime stories and chat are hidden.

PREP_USER_EMAILS (comma-separated) replaces the default list without a
code change.
"""
import os

from flask import abort, jsonify, request
from flask_login import current_user

DEFAULT_PREP_EMAILS = ("venghatesh@gmail.com", "venghateshshreya@gmail.com")


def prep_emails():
    raw = (os.environ.get("PREP_USER_EMAILS") or "").strip()
    if raw:
        return {e.strip().lower() for e in raw.split(",") if e.strip()}
    return set(DEFAULT_PREP_EMAILS)


def prep_allowed(user=None):
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    email = (getattr(user, "email", "") or "").strip().lower()
    return bool(email) and email in prep_emails()


def guard_blueprint(bp):
    """Close every route on this blueprint to anyone not on the list.

    Signed-out visitors are left alone here so @login_required can send
    them to the login page as usual; signed-in users who are not on the
    list get a 404, so the pages look like they do not exist."""
    @bp.before_request
    def _prep_only():
        if not getattr(current_user, "is_authenticated", False):
            return None
        if prep_allowed():
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "not found"}), 404
        abort(404)
    return bp

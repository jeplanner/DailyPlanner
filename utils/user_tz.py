"""
Per-user timezone helper.

Every place in the codebase that needs "now" or "today" should call
`user_now()` / `user_today()` from this module — never `datetime.now(IST)`
directly, never `date.today()` (which uses the server's local time, not
the user's).

Resolution order for the current user's timezone:
  1. `session["user_tz"]` — set on login + on /settings save (fast path)
  2. `current_user.timezone` (database column on `users`)
  3. fallback to `Asia/Kolkata` (the original hard-coded default)

Outside a request context (e.g. background scripts, tests), falls back
to IST so legacy behaviour is unchanged.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import has_request_context, session
from flask_login import current_user

from config import IST

DEFAULT_TZ_NAME = "Asia/Kolkata"

# In-process cache so we don't re-build ZoneInfo objects every request.
_TZ_CACHE: dict[str, ZoneInfo] = {}


def _resolve(name: str | None) -> ZoneInfo | None:
    """Look up a ZoneInfo by IANA name, with caching. Returns None if
    the name is invalid or empty."""
    if not name:
        return None
    cached = _TZ_CACHE.get(name)
    if cached is not None:
        return cached
    try:
        z = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    _TZ_CACHE[name] = z
    return z


def user_tz() -> ZoneInfo:
    """Return the current request's effective timezone (falls back to IST)."""
    if not has_request_context():
        return IST

    name = session.get("user_tz")
    if not name:
        # Fall back to reading the persisted column. We cache it into the
        # session so subsequent requests skip the attribute lookup.
        try:
            if current_user.is_authenticated:
                name = getattr(current_user, "timezone", None)
                if name:
                    session["user_tz"] = name
        except Exception:
            # Outside an application context for current_user — be safe.
            name = None

    z = _resolve(name) if name else None
    return z or IST


def user_now() -> datetime:
    """Return the current datetime in the user's timezone."""
    return datetime.now(user_tz())


def user_today() -> date:
    """Return today's date in the user's timezone."""
    return user_now().date()


def user_tz_name() -> str:
    """Return the IANA name of the user's timezone (for templates / API)."""
    name = session.get("user_tz") if has_request_context() else None
    if not name:
        try:
            if current_user.is_authenticated:
                name = getattr(current_user, "timezone", None)
        except Exception:
            pass
    return name or DEFAULT_TZ_NAME


def set_session_tz(name: str) -> bool:
    """Validate `name` is a real IANA tz, store it in the session.
    Returns True on success, False if the name is unknown."""
    if _resolve(name) is None:
        return False
    session["user_tz"] = name
    return True

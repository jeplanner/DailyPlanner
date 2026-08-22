"""
User settings — currently just timezone, designed so we can drop in
notifications / display preferences here without restructuring.

GET  /settings           → render the settings page
GET  /settings/login-history → recent sign-ins, in the user's own timezone
POST /api/settings/timezone  → JSON body {"timezone": "America/New_York"} → persist
"""
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask import Blueprint, jsonify, render_template, request, session
from flask_login import current_user

from services.login_service import login_required
from supabase_client import get, update
from utils.user_tz import DEFAULT_TZ_NAME, set_session_tz, user_tz, user_tz_name

logger = logging.getLogger("daily_plan")
settings_bp = Blueprint("settings", __name__)


# Curated short list shown at the top of the dropdown — covers ~95%
# of likely users without making them scroll through 500 entries.
COMMON_TIMEZONES = [
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Dubai",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Amsterdam",
    "Africa/Johannesburg",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Sao_Paulo",
    "Pacific/Auckland",
    "UTC",
]


@settings_bp.route("/settings")
@login_required
def settings_page():
    # Sort the full IANA list once; the template renders <optgroup>s.
    all_tz = sorted(available_timezones())
    return render_template(
        "settings.html",
        common_timezones=COMMON_TIMEZONES,
        all_timezones=all_tz,
        current_tz=user_tz_name(),
        default_tz=DEFAULT_TZ_NAME,
    )


@settings_bp.route("/api/settings/timezone", methods=["POST"])
@login_required
def update_timezone():
    data = request.get_json(silent=True) or {}
    tz_name = (data.get("timezone") or "").strip()

    # Validate against the live IANA database — never trust the client.
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return jsonify({"status": "error", "error": "Unknown timezone"}), 400

    user_id = session.get("user_id")
    try:
        update(
            "users",
            params={"id": f"eq.{user_id}"},
            json={"timezone": tz_name},
        )
    except Exception as e:
        # If the migration hasn't been applied (column missing), supabase
        # wrapper auto-strips the field and returns None. Surface a
        # friendly error so the user sees it rather than silent acceptance.
        logger.warning("Timezone persist failed for user_id=%s: %s", user_id, e)
        return jsonify({
            "status": "error",
            "error": (
                "Could not save — the users.timezone column may be missing. "
                "Run the migration from INSTALL_FOR_NEW_USER.md."
            ),
        }), 500

    # Update the in-flight session so the change takes effect immediately
    # without forcing a re-login.
    set_session_tz(tz_name)
    if getattr(current_user, "timezone", None) is not None:
        try:
            current_user.timezone = tz_name  # in-memory mirror
        except Exception:
            pass

    return jsonify({"status": "ok", "timezone": tz_name})


# ── Login history ─────────────────────────────────────────────────────
#: How many sign-ins to show. Enough to cover "was that me last week?"
#: without paginating a page nobody visits twice a day.
LOGIN_HISTORY_LIMIT = 100


def _describe_location(row):
    """One human line for where a sign-in came from.

    `location_status` exists so this can be honest about the difference
    between "we know it was Chennai", "it was your own network", and "the
    lookup failed" — three states an empty cell would flatten into one that
    looks like a bug.
    """
    status = (row.get("location_status") or "").lower()
    if status == "ok":
        parts = [row.get("city"), row.get("region"), row.get("country")]
        text = ", ".join(p for p in parts if p)
        return text or "Unknown location"
    if status == "private":
        return "On this network"
    if status == "unknown":
        return "No address recorded"
    return "Could not determine"


def _describe_device(user_agent):
    """A short, honest device label from the user-agent string.

    Deliberately coarse. User-agent parsing is a bottomless pit and the
    question this answers is only "does that look like my phone or a machine
    I do not recognise", which needs the browser and the platform and nothing
    else.
    """
    ua = user_agent or ""
    low = ua.lower()
    if not ua:
        return "Unknown device"

    if "edg/" in low:
        browser = "Edge"
    elif "opr/" in low or "opera" in low:
        browser = "Opera"
    elif "chrome" in low and "chromium" not in low:
        browser = "Chrome"
    elif "firefox" in low:
        browser = "Firefox"
    elif "safari" in low:
        browser = "Safari"
    else:
        browser = "Browser"

    if "android" in low:
        platform = "Android"
    elif "iphone" in low:
        platform = "iPhone"
    elif "ipad" in low:
        platform = "iPad"
    elif "windows" in low:
        platform = "Windows"
    elif "mac os" in low or "macintosh" in low:
        platform = "Mac"
    elif "linux" in low:
        platform = "Linux"
    else:
        platform = "Unknown OS"
    return f"{browser} on {platform}"


@settings_bp.route("/settings/login-history")
@login_required
def login_history_page():
    """Recent sign-ins for the current user, newest first.

    STORED IN UTC, SHOWN IN THE USER'S OWN ZONE. The rows carry a UTC
    timestamp because that is the only representation that stays correct
    across a timezone change; the conversion happens here, once, so the
    template holds no date arithmetic. For this household the user timezone
    is Asia/Kolkata, so the page reads in IST.
    """
    from datetime import datetime, timezone as _tz

    tz = user_tz()
    rows = []
    migration_needed = False
    try:
        raw = get("login_events", params={
            "user_id": f"eq.{session['user_id']}",
            "order": "at.desc",
            "limit": str(LOGIN_HISTORY_LIMIT),
        }) or []
    except Exception as exc:
        text = str(exc)
        if ("login_events" in text or "does not exist" in text
                or "schema cache" in text):
            # An unrun migration is a setup step, not an error — say which
            # file closes it rather than showing a 500.
            logger.warning("login history unavailable: %s", text[:160])
            migration_needed = True
            raw = []
        else:
            raise

    for r in raw:
        at_raw = r.get("at") or ""
        local = None
        if at_raw:
            try:
                iso = at_raw.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(iso)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=_tz.utc)
                local = parsed.astimezone(tz)
            except ValueError:
                local = None
        rows.append({
            "when": local.strftime("%a %d %b %Y, %I:%M %p") if local else "—",
            "when_iso": local.isoformat() if local else "",
            "location": _describe_location(r),
            "device": _describe_device(r.get("user_agent")),
            "ip": r.get("ip") or "—",
            "outcome": (r.get("outcome") or "success").lower(),
        })

    return render_template(
        "login_history.html",
        rows=rows,
        tz_name=user_tz_name(),
        tz_abbr=datetime.now(tz).strftime("%Z"),
        migration_needed=migration_needed,
        limit=LOGIN_HISTORY_LIMIT,
    )

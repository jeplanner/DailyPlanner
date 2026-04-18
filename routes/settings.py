"""
User settings — currently just timezone, designed so we can drop in
notifications / display preferences here without restructuring.

GET  /settings           → render the settings page
POST /api/settings/timezone  → JSON body {"timezone": "America/New_York"} → persist
"""
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask import Blueprint, jsonify, render_template, request, session
from flask_login import current_user

from services.login_service import login_required
from supabase_client import update
from utils.user_tz import DEFAULT_TZ_NAME, set_session_tz, user_tz_name

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

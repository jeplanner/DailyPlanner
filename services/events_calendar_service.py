"""
Mirror daily_events (including recurring series) into Google Calendar.

Two paths:
  * Non-recurring event → single Calendar event.
  * Master of a recurring series → Calendar event WITH a recurrence
    rule so Google expands occurrences natively.

For per-occurrence overrides (is_exception=true), we use Google's
instance-override pattern: update the specific instance of the series
by computing its instanceId = "<master_gcal_id>_<YYYYMMDDTHHMMSSZ>".

Everything is best-effort — if Google sync fails, local save still wins
and we log the exception. The checklist_calendar_service followed the
same philosophy.
"""
import logging
from datetime import datetime, timedelta, date, time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from services import event_recurrence
from supabase_client import get, update

logger = logging.getLogger(__name__)


def _credentials(user_id):
    rows = get("user_google_tokens", {"user_id": f"eq.{user_id}"}) or []
    if not rows:
        return None
    row = rows[0]
    creds = Credentials(
        token=row["access_token"],
        refresh_token=row["refresh_token"],
        token_uri=row["token_uri"],
        client_id=row["client_id"],
        client_secret=row["client_secret"],
        scopes=(row.get("scopes") or "").split(","),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        update(
            "user_google_tokens",
            params={"user_id": f"eq.{user_id}"},
            json={"access_token": creds.token,
                  "updated_at": datetime.utcnow().isoformat()},
        )
    return creds


def _user_tz(user_id):
    try:
        rows = get("users", {"id": f"eq.{user_id}", "select": "timezone"}) or []
    except Exception:
        return "Asia/Kolkata"
    if rows and rows[0].get("timezone"):
        return rows[0]["timezone"]
    return "Asia/Kolkata"


def _service(user_id):
    try:
        creds = _credentials(user_id)
    except Exception:
        logger.exception("Could not load Google credentials for user %s", user_id)
        return None
    if not creds:
        return None
    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception:
        logger.exception("Could not build Calendar service for user %s", user_id)
        return None


def _combine(plan_date_str, time_str):
    """Accept "HH:MM" or "HH:MM:SS" and combine with plan_date_str."""
    d = date.fromisoformat(plan_date_str)
    parts = (time_str or "00:00").split(":")
    hh = int(parts[0]); mm = int(parts[1])
    ss = int(parts[2]) if len(parts) > 2 else 0
    return datetime.combine(d, time(hh, mm, ss))


def _event_body(row, tz_name):
    start = _combine(row["plan_date"], row.get("start_time") or "00:00")
    end = _combine(row["plan_date"], row.get("end_time") or "00:30")
    if end <= start:
        end = start + timedelta(minutes=30)

    body = {
        "summary": row.get("title") or "Untitled",
        "description": row.get("description") or "",
        "start": {"dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": tz_name},
        "end":   {"dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": tz_name},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup",
                           "minutes": int(row.get("reminder_minutes") or 10)}],
        },
    }

    if row.get("recurrence_rule"):
        rrule = event_recurrence.build_rrule(
            row["recurrence_rule"],
            row.get("recurrence_days"),
            end_date=row.get("recurrence_end"),
            count=row.get("recurrence_count"),
        )
        body["recurrence"] = [rrule]

    return body


def sync_create(user_id, row):
    """Create the Google event for this master/single row. Returns the
    new google_event_id, or None."""
    svc = _service(user_id)
    if not svc:
        return None
    try:
        created = svc.events().insert(
            calendarId="primary", body=_event_body(row, _user_tz(user_id))
        ).execute()
        return created.get("id")
    except Exception:
        logger.exception("Google insert failed for event %s", row.get("id"))
        return None


def sync_update(user_id, row):
    """Update the whole series/event on Google. No-op if no google_event_id."""
    gid = row.get("google_event_id")
    if not gid:
        # No existing link — try to create.
        return sync_create(user_id, row)
    svc = _service(user_id)
    if not svc:
        return gid
    try:
        svc.events().update(
            calendarId="primary",
            eventId=gid,
            body=_event_body(row, _user_tz(user_id)),
        ).execute()
    except Exception:
        logger.exception("Google update failed for event %s", gid)
    return gid


def sync_delete(user_id, google_event_id):
    if not google_event_id:
        return
    svc = _service(user_id)
    if not svc:
        return
    try:
        svc.events().delete(calendarId="primary", eventId=google_event_id).execute()
    except Exception:
        logger.info("Google delete noop for %s", google_event_id)


def _instance_id(master_gid, occurrence_date_str, start_time_str, tz_name):
    """Google's convention: "<base>_<YYYYMMDDTHHMMSS>" for a recurring
    instance. For all-day or simple cases, the date-time suffix of the
    occurrence's start works."""
    dt = _combine(occurrence_date_str, start_time_str or "00:00")
    return f"{master_gid}_{dt.strftime('%Y%m%dT%H%M%S')}"


def sync_exception_override(user_id, master_gid, occurrence_date, override_row):
    """Modify a single occurrence of a recurring series on Google."""
    if not master_gid:
        return
    svc = _service(user_id)
    if not svc:
        return
    tz = _user_tz(user_id)
    inst = _instance_id(master_gid, occurrence_date, override_row.get("start_time") or "00:00", tz)

    patch = {
        "summary": override_row.get("title") or "Untitled",
        "description": override_row.get("description") or "",
        "start": {
            "dateTime": _combine(occurrence_date, override_row.get("start_time") or "00:00")
                         .strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz,
        },
        "end": {
            "dateTime": _combine(occurrence_date, override_row.get("end_time") or "00:30")
                         .strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz,
        },
    }
    try:
        svc.events().patch(calendarId="primary", eventId=inst, body=patch).execute()
    except Exception:
        logger.info("Google patch-instance noop for %s", inst)


def sync_exception_cancel(user_id, master_gid, occurrence_date, start_time):
    """Cancel a single occurrence of a recurring series on Google."""
    if not master_gid:
        return
    svc = _service(user_id)
    if not svc:
        return
    tz = _user_tz(user_id)
    inst = _instance_id(master_gid, occurrence_date, start_time or "00:00", tz)
    try:
        svc.events().patch(
            calendarId="primary", eventId=inst, body={"status": "cancelled"},
        ).execute()
    except Exception:
        logger.info("Google cancel-instance noop for %s", inst)

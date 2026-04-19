"""
Mirror a checklist_item's reminder into the user's Google Calendar.

Why: Samsung and most Android OEMs aggressively suppress heads-up banners
from generic Web Push — they end up as tray-only notifications. But
Google Calendar popup reminders are treated as first-class by the OS
(full-screen alarm-style pop-up, bypass DND in most configurations). So
for checklist items that have a reminder_time, we also create a matching
recurring Google Calendar event with a popup override at T-0.

Design:
  * Silent no-op if the user hasn't linked Google Calendar (no rows in
    user_google_tokens).
  * `sync_to_calendar(user_id, item)` is idempotent:
      - if item.google_event_id is set → update the existing event
      - otherwise → create a new event and caller persists the ID
  * `delete_from_calendar` is safe on null IDs.
  * Schedule → RRULE mapping:
      daily     → FREQ=DAILY
      weekdays  → FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
      weekends  → FREQ=WEEKLY;BYDAY=SA,SU
      custom    → FREQ=WEEKLY;BYDAY=<Sun=0…Sat=6 CSV mapped to SU…SA>
"""
import logging
from datetime import date, datetime, time, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from supabase_client import get, update

logger = logging.getLogger(__name__)

SUMMARY_PREFIX = "✓ "   # visual marker in the calendar


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
            json={
                "access_token": creds.token,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
    return creds


def _user_tz(user_id):
    rows = get("users", {"id": f"eq.{user_id}", "select": "timezone"}) or []
    if rows and rows[0].get("timezone"):
        return rows[0]["timezone"]
    return "Asia/Kolkata"


def _rrule(schedule, schedule_days):
    if schedule == "weekdays":
        return "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    if schedule == "weekends":
        return "RRULE:FREQ=WEEKLY;BYDAY=SA,SU"
    if schedule == "custom":
        day_codes = {"0": "SU", "1": "MO", "2": "TU", "3": "WE",
                     "4": "TH", "5": "FR", "6": "SA"}
        days = [d.strip() for d in (schedule_days or "").split(",") if d.strip() in day_codes]
        if not days:
            return "RRULE:FREQ=DAILY"
        return "RRULE:FREQ=WEEKLY;BYDAY=" + ",".join(day_codes[d] for d in days)
    return "RRULE:FREQ=DAILY"


def _event_body(item, tz_name):
    rt = (item.get("reminder_time") or "")[:5]  # "HH:MM"
    hh, mm = (int(x) for x in rt.split(":"))
    start_dt = datetime.combine(date.today(), time(hh, mm))
    end_dt = start_dt + timedelta(minutes=10)
    return {
        "summary": SUMMARY_PREFIX + (item.get("name") or "Checklist reminder"),
        "description": item.get("notes") or "Daily checklist reminder",
        "start": {
            "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz_name,
        },
        "end": {
            "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz_name,
        },
        "recurrence": [_rrule(item.get("schedule"), item.get("schedule_days"))],
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 0}],
        },
    }


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


def sync_to_calendar(user_id, item):
    """Create or update a Google Calendar event for this item.

    Returns the (possibly new) google_event_id, or None if no event
    should exist (no Google link, or no reminder_time on the item)."""
    if not item.get("reminder_time"):
        # If an ID existed before, caller should delete it explicitly;
        # we just report "no event should be here now".
        return None
    svc = _service(user_id)
    if not svc:
        return None
    body = _event_body(item, _user_tz(user_id))
    existing_id = item.get("google_event_id")
    try:
        if existing_id:
            svc.events().update(
                calendarId="primary", eventId=existing_id, body=body,
            ).execute()
            return existing_id
        created = svc.events().insert(calendarId="primary", body=body).execute()
        return created.get("id")
    except Exception as e:
        # If the existing event was deleted in the user's calendar, the
        # update will 404 — fall back to insert.
        if existing_id:
            try:
                created = svc.events().insert(calendarId="primary", body=body).execute()
                return created.get("id")
            except Exception:
                logger.exception("Calendar re-insert failed for item %s", item.get("id"))
                return None
        logger.exception("Calendar sync failed for item %s: %s", item.get("id"), e)
        return None


def delete_from_calendar(user_id, google_event_id):
    if not google_event_id:
        return
    svc = _service(user_id)
    if not svc:
        return
    try:
        svc.events().delete(calendarId="primary", eventId=google_event_id).execute()
    except Exception:
        # Already deleted or permissions revoked — log and move on.
        logger.info("Calendar delete noop for event %s", google_event_id)

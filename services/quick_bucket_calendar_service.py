"""Mirror a quick_bucket row's deadline into the user's Google Calendar.

Why: Samsung and most Android OEMs aggressively suppress heads-up
banners from generic Web Push — they end up tray-only. Google Calendar
popup reminders are first-class on Android (full-screen alarm-style
pop-up, often bypassing DND). So for quick-bucket items that have a
due_at (i.e. the user picked a 5m / 15m / 30m / 45m / 1h..8h bucket),
we also create a one-off Google Calendar event with a popup override
at T-0.

Items in the 'now' or 'future' bucket have no due_at and therefore no
calendar mirror.

Pattern (and a chunk of the wiring) is adapted from
services.checklist_calendar_service so credentials and timezone
helpers stay in one place — we import them rather than duplicating.
"""

import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from services.checklist_calendar_service import _credentials, _user_tz
from supabase_client import update

logger = logging.getLogger(__name__)

SUMMARY_PREFIX = "⏱ "  # one-off task marker; differs from checklist's ✓


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


def _event_body(item, tz_name):
    """Build a one-shot event at item.due_at (UTC ISO string), 10 min long.
    The popup reminder fires at T-0 — i.e. exactly when the bucket
    countdown would hit zero in the app."""
    due_iso = item.get("due_at")
    if not due_iso:
        return None
    # PostgREST returns 'YYYY-MM-DDTHH:MM:SS+00:00' style; fromisoformat
    # handles that on 3.11+. For safety strip a trailing 'Z'.
    s = due_iso.replace("Z", "+00:00") if due_iso.endswith("Z") else due_iso
    try:
        start_dt = datetime.fromisoformat(s)
    except Exception:
        logger.warning("Invalid due_at %r; skipping calendar mirror", due_iso)
        return None
    end_dt = start_dt + timedelta(minutes=10)
    return {
        "summary": SUMMARY_PREFIX + (item.get("text") or "Quick task"),
        "description": "Tasks Bucket reminder",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": tz_name},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": tz_name},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 0}],
        },
    }


def sync_to_calendar(user_id, item):
    """Create or update the calendar event for `item`. Returns the event
    id (new or existing), or None if no event should exist (no due_at,
    no Google link, or item already done/archived)."""
    if item.get("is_done") or item.get("is_deleted"):
        return None
    if not item.get("due_at"):
        return None
    svc = _service(user_id)
    if not svc:
        return None
    body = _event_body(item, _user_tz(user_id))
    if not body:
        return None

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
        # Existing event may have been deleted in the user's calendar;
        # fall back to insert.
        if existing_id:
            try:
                created = svc.events().insert(calendarId="primary", body=body).execute()
                return created.get("id")
            except Exception:
                logger.exception("quick_bucket calendar re-insert failed for %s", item.get("id"))
                return None
        logger.exception("quick_bucket calendar sync failed for %s: %s", item.get("id"), e)
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
        # Already deleted or revoked — log and move on.
        logger.info("quick_bucket calendar delete noop for %s", google_event_id)


def sync_async(user_id, item_id, item, old_event_id=None, force_delete=False):
    """Run sync/delete in a background thread so the HTTP request returns
    immediately. The DB row is the source of truth; calendar is a
    downstream mirror.

    force_delete=True unconditionally removes old_event_id (used when
    the bucket changes to 'now'/'future'/'done'/'deleted'). Otherwise
    we sync the new state and persist any newly-issued event id back to
    the row."""
    import threading

    def _work():
        try:
            if force_delete and old_event_id:
                delete_from_calendar(user_id, old_event_id)
                update(
                    "quick_bucket",
                    params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                    json={"google_event_id": None},
                )
                return
            new_id = sync_to_calendar(user_id, item)
            if new_id and new_id != old_event_id:
                update(
                    "quick_bucket",
                    params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                    json={"google_event_id": new_id},
                )
        except Exception:
            logger.exception("quick_bucket calendar background sync failed for %s", item_id)

    t = threading.Thread(target=_work, name=f"qb-cal-{item_id}", daemon=True)
    t.start()

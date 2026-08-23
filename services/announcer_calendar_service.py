"""Mirror an announcement into the user's Google Calendar.

WHY, in the user's words: "can you not make it as system notification
since calendar notification in android did not work. i had to create it in
samsung calender or google calendar to make it work."

That is the right diagnosis, and this codebase already had the evidence —
see services/checklist_calendar_service.py, which says the same thing about
checklist reminders. Samsung and most Android OEMs suppress heads-up
banners from generic Web Push, and Doze defers the delivery entirely: a
push scheduled for 01:05 arrives when the screen is next unlocked, which is
what was measured. A Google Calendar popup goes through the OS's
exact-alarm path instead. It is not deferred, it is not batched, and it
looks like an alarm rather than a tray entry.

So an announcement now exists in two places on purpose:
  * the in-page voice and the Web Push, which are immediate and rich but
    only as reliable as the browser is allowed to be, and
  * a calendar event with a popup at T-0, which the phone treats as a
    first-class alarm.

Silent no-op when Google Calendar was never linked — most installs never
link it, and this must not become an error for them.
"""
import logging
import threading
from datetime import date, datetime, time, timedelta

from supabase_client import update

logger = logging.getLogger(__name__)

SUMMARY_PREFIX = "🔔 "

#: Sun=0 in this app's vocabulary (matches matchesOn/slotsFor in the
#: browser); Google wants two-letter codes starting at Sunday.
_DAY_CODES = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]


def _rrule(item):
    """The repeat rule as an RRULE, or None for a one-off.

    A WINDOWED announcement (until_time + every_mins) fires many times a
    day, and a calendar event cannot express "every 20 minutes between 8
    and 6" without becoming a wall of entries. Those keep the daily rule
    and get ONE popup at their start time; the in-page voice still covers
    the rest of the window. Half a mirror beats a calendar nobody can read.
    """
    rule = (item.get("repeat_rule") or "daily").lower()
    if rule == "once":
        return None

    parts = None
    if rule == "daily":
        parts = "FREQ=DAILY"
    elif rule == "weekly":
        parts = "FREQ=WEEKLY"
    elif rule == "monthly":
        parts = "FREQ=MONTHLY"
    elif rule == "yearly":
        parts = "FREQ=YEARLY"
    elif rule == "custom":
        days = [d for d in (item.get("days") or []) if 0 <= int(d) <= 6]
        if not days:
            return None            # "chosen days" with nothing chosen
        parts = "FREQ=WEEKLY;BYDAY=" + ",".join(_DAY_CODES[int(d)] for d in sorted(days))
    else:
        parts = "FREQ=DAILY"

    end = (item.get("end_date") or "").strip()
    if end:
        try:
            # UNTIL is exclusive-ish and must cover the whole last day.
            last = date.fromisoformat(end[:10])
            parts += ";UNTIL=" + last.strftime("%Y%m%d") + "T235959Z"
        except ValueError:
            pass
    return "RRULE:" + parts


def _event_body(item, tz_name):
    at = (item.get("at_time") or "")[:5]
    hh, mm = (int(x) for x in at.split(":"))

    # A one-off anchors on its own date; a repeating rule anchors on its
    # start, because Google reads the RRULE relative to that.
    try:
        base = date.fromisoformat((item.get("start_date") or "")[:10])
    except (ValueError, TypeError):
        base = date.today()

    start_dt = datetime.combine(base, time(hh, mm))
    body = {
        "summary": SUMMARY_PREFIX + (item.get("say_text") or "Announcement"),
        "description": "Spoken announcement from DailyPlanner.",
        "start": {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                  "timeZone": tz_name},
        "end": {"dateTime": (start_dt + timedelta(minutes=5))
                .strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": tz_name},
        # T-0 popup: the whole point. Anything earlier is a different
        # announcement from the one that was asked for.
        "reminders": {"useDefault": False,
                      "overrides": [{"method": "popup", "minutes": 0}]},
    }
    rule = _rrule(item)
    if rule:
        body["recurrence"] = [rule]
    return body


def sync_to_calendar(user_id, item):
    """Create or update the mirror. Returns the event id, or None.

    Reuses the checklist mirror's credential and service plumbing rather
    than growing a second copy of it — that module already handles token
    refresh, a missing link, and the user's timezone.
    """
    from services import checklist_calendar_service as base

    svc = base._service(user_id)
    if not svc:
        return None                      # Calendar was never linked
    if not (item.get("at_time") or "").strip():
        return None
    if item.get("is_on") is False or item.get("is_deleted"):
        return None

    tz_name = base._user_tz(user_id)
    body = _event_body(item, tz_name)
    existing = (item.get("google_event_id") or "").strip()
    try:
        if existing:
            ev = svc.events().update(calendarId="primary", eventId=existing,
                                     body=body).execute()
        else:
            ev = svc.events().insert(calendarId="primary", body=body).execute()
        return ev.get("id")
    except Exception:
        # A stale id (the user deleted the event in Calendar) must not
        # strand the announcement — drop it and make a fresh one.
        if existing:
            try:
                ev = svc.events().insert(calendarId="primary", body=body).execute()
                return ev.get("id")
            except Exception:
                logger.exception("announcer calendar insert failed for %s", user_id)
                return None
        logger.exception("announcer calendar sync failed for %s", user_id)
        return None


def delete_from_calendar(user_id, event_id):
    if not event_id:
        return
    from services import checklist_calendar_service as base
    svc = base._service(user_id)
    if not svc:
        return
    try:
        svc.events().delete(calendarId="primary", eventId=event_id).execute()
    except Exception:
        # Already gone is the common case and is not a failure.
        logger.debug("announcer calendar delete failed for %s", event_id,
                     exc_info=True)


def sync_async(user_id, client_id, item, old_event_id=None, remove=False):
    """Do it off the request thread. The row is the source of truth; the
    calendar is a downstream mirror, and saving an announcement must never
    wait on Google."""

    def _work():
        try:
            if remove:
                delete_from_calendar(user_id, old_event_id)
                update("announcer_items",
                       params={"user_id": f"eq.{user_id}",
                               "client_id": f"eq.{client_id}"},
                       json={"google_event_id": None})
                return
            new_id = sync_to_calendar(user_id, item)
            if new_id and new_id != old_event_id:
                update("announcer_items",
                       params={"user_id": f"eq.{user_id}",
                               "client_id": f"eq.{client_id}"},
                       json={"google_event_id": new_id})
        except Exception:
            logger.exception("announcer calendar background sync failed for %s",
                             client_id)

    threading.Thread(target=_work, name=f"ann-cal-{client_id}",
                     daemon=True).start()

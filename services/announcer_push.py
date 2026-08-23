"""Announcements as push notifications, so they reach a locked phone.

WHY THIS EXISTS. Spoken announcements need the page alive AND visible.
The keep-alive audio keeps it running with the screen off, but Web Speech
is suspended on a locked phone on every platform that matters, so nothing
is heard. That is a browser limitation, not something we can engineer
around.

A notification does work with the screen locked, and with the app fully
closed, which speech never can. So each announcement also fires as a push.
Speech is the experience when you are looking at the app; the notification
is what reaches you when you are not.

This is only possible because announcements moved server-side. A schedule
living in one browser's localStorage cannot be read by a scheduler.

THE RULES ARE THE CLIENT'S RULES, deliberately reimplemented here rather
than approximated: same recurrence, same start/end window, same daily time
window with its interval. If these two ever disagree, the user hears one
thing and reads another, which is worse than either alone — so the tests
check them against the same cases the JavaScript harness uses.
"""
import logging
from datetime import date, datetime, timedelta

from supabase_client import get, post

logger = logging.getLogger("daily_plan")

#: Mirrors REPEATS in static/js/time-announcer.js.
REPEATS = ("once", "daily", "weekly", "monthly", "yearly", "custom")

#: How late a fire may be and still be sent. The scheduler ticks once a
#: minute and can drift, so a slot must survive being noticed a minute
#: late — but not so long that a restart replays the morning.
GRACE_MINUTES = 2


def _days_in_month(y, m):
    if m == 12:
        return 31
    return (date(y, m + 1, 1) - timedelta(days=1)).day


def matches_on(item, on_date):
    """Does this announcement's recurrence fire on this date?

    Mirrors matchesOn() in time-announcer.js, INCLUDING the two clamps: a
    monthly reminder on the 31st fires on the last day of a short month,
    and a yearly one on 29 February fires on the 28th in a common year.
    Skipping instead would mean the phone stays silent in February while
    the app says the reminder is active.
    """
    start = item.get("start_date")
    end = item.get("end_date")
    if start and on_date.isoformat() < str(start):
        return False
    if end and on_date.isoformat() > str(end):
        return False

    rule = item.get("repeat_rule")
    if rule not in REPEATS:
        rule = "daily"
    if rule == "daily":
        return True
    if rule == "once":
        return bool(start) and on_date.isoformat() == str(start)
    if rule == "custom":
        days = item.get("days") or []
        # Python's weekday() is Mon=0; the client uses Sun=0.
        return ((on_date.weekday() + 1) % 7) in days
    if not start:
        return True

    s = date.fromisoformat(str(start))
    if rule == "weekly":
        return on_date.weekday() == s.weekday()
    if rule == "monthly":
        return on_date.day == min(s.day, _days_in_month(on_date.year,
                                                        on_date.month))
    if rule == "yearly":
        return (on_date.month == s.month and
                on_date.day == min(s.day, _days_in_month(on_date.year,
                                                         s.month)))
    return False


def _to_mins(hhmm):
    try:
        h, m = str(hhmm)[:5].split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def slots_for(item):
    """Minutes-since-midnight this announcement speaks on an active day.

    Mirrors slotsFor() in time-announcer.js: one slot at `at_time` unless
    both an end time and an interval are set, in which case it repeats
    through the window.
    """
    start = _to_mins(item.get("at_time"))
    if start is None:
        return []
    step = item.get("every_mins") or 0
    end = _to_mins(item.get("until_time")) if item.get("until_time") else None
    if not step or end is None or end < start:
        return [start]
    out, m = [], start
    # Bounded for the same reason the client bounds it: a 1-minute step
    # across a day is 1440 slots, and anything past that is a bug.
    while m <= end and len(out) < 1441:
        out.append(m)
        m += step
    return out


def due_now(items, now_local):
    """(item, 'HH:MM') pairs that should fire at this local minute."""
    today = now_local.date()
    now_mins = now_local.hour * 60 + now_local.minute
    out = []
    for it in items:
        if it.get("is_deleted"):
            continue
        if it.get("is_on") is False:
            continue
        # Per-announcement opt out. Absent column reads as True, so this
        # keeps working before MIGRATION_ANNOUNCER_PUSH.sql is run.
        if it.get("notify") is False:
            continue
        if not matches_on(it, today):
            continue
        for slot in slots_for(it):
            late = now_mins - slot
            if 0 <= late <= GRACE_MINUTES:
                out.append((it, "%02d:%02d" % (slot // 60, slot % 60)))
                break
    return out


def claim(user_id, client_id, fire_date, fire_time):
    """Take the send slot, or report that another worker already has it.

    The unique index does the work — several gunicorn workers tick at the
    same second, and only the first insert survives.
    """
    try:
        post("announcer_fire_log", {
            "user_id": user_id,
            "client_id": client_id,
            "fire_date": fire_date,
            "fire_time": fire_time,
        }, prefer="return=minimal")
        return True
    except Exception:
        return False


def spoken_label(item, fire_time):
    """What the notification says. The same words the voice would use."""
    text = (item.get("say_text") or "").strip()
    h, m = fire_time.split(":")
    h = int(h)
    suffix = "AM" if h < 12 else "PM"
    h12 = 12 if h % 12 == 0 else h % 12
    when = "%d:%s %s" % (h12, m, suffix)
    return (text or "Reminder"), when


def fires_for_user(user_id, now_local):
    """Everything this user should be notified about right now."""
    try:
        items = get("announcer_items", {
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
        }) or []
    except Exception:
        # The table arrives with MIGRATION_ANNOUNCER_SYNC.sql. Before that
        # this is simply a feature that does not exist yet, and it must not
        # take the checklist reminders down with it.
        logger.debug("announcer_items unavailable", exc_info=True)
        return []
    return due_now(items, now_local)

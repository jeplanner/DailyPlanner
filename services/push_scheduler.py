"""
Background scheduler that sends Web Push reminders for checklist items
whose reminder times match the user's local "now".

Design:
  * Runs every minute (APScheduler BackgroundScheduler).
  * For each user that has at least one active push subscription, we
    resolve their IANA timezone (cached in-process) and compute the
    local HH:MM and weekday.
  * For every checklist_reminder_times row whose time matches the local
    HH:MM and whose parent's schedule applies to today, we attempt to
    insert a row into checklist_reminder_log keyed on (item_id,
    sent_date, reminder_time) so each fire is independently deduped.
  * The unique constraint makes this safe across multiple gunicorn
    workers — only the first insert wins, and only that worker calls
    push_service.send_to_user().
  * Items with no child reminder_times rows fall back to the legacy
    checklist_items.reminder_time column for backwards compat.

The scheduler starts once inside create_app(); a module-level flag
prevents duplicate starts when the factory is invoked multiple times
(tests, reloads).
"""
import atexit
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from requests.exceptions import HTTPError

from services import push_service
from supabase_client import get, post

logger = logging.getLogger(__name__)

_started = False
_scheduler = None

_TZ_CACHE: dict[str, ZoneInfo] = {}


def _resolve_tz(name):
    if not name:
        return ZoneInfo("Asia/Kolkata")
    cached = _TZ_CACHE.get(name)
    if cached:
        return cached
    try:
        z = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        z = ZoneInfo("Asia/Kolkata")
    _TZ_CACHE[name] = z
    return z


def _schedule_applies_today(schedule, schedule_days, weekday, today=None):
    """weekday is Python Mon=0..Sun=6. We convert to Sun=0..Sat=6 for
    storage. `today` is a `date` and is only required for monthly
    schedules — pass it in from callers that support them; older
    callers can omit it and the monthly branches will simply return
    False (no false positives)."""
    dow = (weekday + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
    if schedule == "daily" or not schedule:
        return True
    if schedule == "weekdays":
        return dow in (1, 2, 3, 4, 5)
    if schedule == "weekends":
        return dow in (0, 6)
    if schedule == "custom":
        allowed = {int(x) for x in (schedule_days or "").split(",") if x.strip().lstrip("-").isdigit()}
        return dow in allowed
    if schedule == "monthly_dow":
        # "WEEK:DAY" — fires when today is the Nth (or last) DAY of the
        # current month. WEEK is 1..5 or -1 for "last occurrence".
        if today is None:
            return False
        try:
            week_s, day_s = (schedule_days or "").split(":", 1)
            target_week = int(week_s)
            target_day = int(day_s)
        except (ValueError, AttributeError):
            return False
        if dow != target_day:
            return False
        # nth occurrence of this weekday so far this month (1-indexed).
        occ = (today.day - 1) // 7 + 1
        if target_week == -1:
            # Last occurrence: there is no same-weekday day within the
            # next 7 days that's still in this month.
            from datetime import timedelta as _td
            next_same = today + _td(days=7)
            return next_same.month != today.month
        return occ == target_week
    if schedule == "monthly_dom":
        if today is None:
            return False
        raw = (schedule_days or "").strip()
        if not raw:
            return False
        try:
            target = int(raw)
        except ValueError:
            return False
        if target == -1:
            # Last day of month: tomorrow is in a different month.
            from datetime import timedelta as _td
            return (today + _td(days=1)).month != today.month
        return today.day == target
    return False


def _users_with_active_subscriptions():
    subs = get(
        "push_subscriptions",
        {"is_active": "eq.true", "select": "user_id"},
    ) or []
    return {s["user_id"] for s in subs}


def _user_tz_name(user_id):
    # If the `timezone` column isn't present on this Supabase project
    # yet (e.g. migration not applied), fall back silently instead of
    # crashing every minute in the scheduler.
    try:
        rows = get("users", {"id": f"eq.{user_id}", "select": "timezone"}) or []
    except Exception:
        return "Asia/Kolkata"
    if rows:
        return rows[0].get("timezone") or "Asia/Kolkata"
    return "Asia/Kolkata"


def _due_fires_for_user(user_id, local_hhmm, local_weekday, today_iso):
    """Return a list of (item, reminder_time) tuples that should fire
    right now for this user. reminder_time is the full HH:MM:SS string
    (or None for the legacy items-only fallback path)."""
    from datetime import date as _date

    today = _date.fromisoformat(today_iso)

    items = get(
        "checklist_items",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
        },
    ) or []
    if not items:
        return []
    items_by_id = {it["id"]: it for it in items}

    times = get(
        "checklist_reminder_times",
        {"user_id": f"eq.{user_id}"},
    ) or []
    items_with_children = {r["item_id"] for r in times}

    def _ok(it):
        if not _schedule_applies_today(it.get("schedule"), it.get("schedule_days"), local_weekday, today):
            return False
        end_str = it.get("recurrence_end")
        if end_str:
            try:
                if _date.fromisoformat(end_str) < today:
                    return False
            except Exception:
                pass
        return True

    due = []

    for r in times:
        rt_full = r.get("reminder_time") or ""
        if rt_full[:5] != local_hhmm:
            continue
        it = items_by_id.get(r["item_id"])
        if not it or not _ok(it):
            continue
        due.append((it, rt_full))

    # Legacy fallback: items that still rely on items.reminder_time and
    # have no child rows yet (shouldn't happen after migration but covers
    # any data we haven't normalized).
    for it in items:
        if it["id"] in items_with_children:
            continue
        rt = (it.get("reminder_time") or "")
        if rt[:5] != local_hhmm:
            continue
        if not _ok(it):
            continue
        due.append((it, rt))

    return due


def _claim_send_slot(item_id, user_id, sent_date, reminder_time):
    """Insert a reminder_log row; returns True if *this* worker wins.

    If another worker already inserted the same (item_id, sent_date,
    reminder_time), Postgres returns 409 and we skip sending."""
    payload = {"item_id": item_id, "user_id": user_id, "sent_date": sent_date}
    if reminder_time:
        payload["reminder_time"] = reminder_time
    try:
        post("checklist_reminder_log", payload, prefer="return=minimal")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            return False
        logger.exception("reminder_log insert failed for item %s", item_id)
        return False


def tick():
    """Called every minute. Safe to call manually for debugging."""
    try:
        user_ids = _users_with_active_subscriptions()
    except Exception:
        logger.exception("Could not list active push subscriptions")
        return

    if not user_ids:
        return

    for user_id in user_ids:
        try:
            tz = _resolve_tz(_user_tz_name(user_id))
            now_local = datetime.now(tz)
            hhmm = now_local.strftime("%H:%M")
            weekday = now_local.weekday()  # Mon=0..Sun=6
            today = now_local.date().isoformat()

            fires = _due_fires_for_user(user_id, hhmm, weekday, today)
            for it, rt in fires:
                if not _claim_send_slot(it["id"], user_id, today, rt):
                    continue
                title = "✓ Daily Checklist"
                body = it["name"]
                # Use the fire's HH:MM in the tag so the same item firing
                # at different times produces distinct notifications.
                tag_suffix = (rt or "")[:5].replace(":", "")
                push_service.send_to_user(
                    user_id,
                    title=title,
                    body=body,
                    url="/checklist",
                    tag=f"cl-{it['id']}-{tag_suffix}" if tag_suffix else f"cl-{it['id']}",
                )
        except Exception:
            logger.exception("Scheduler tick failed for user %s", user_id)


def start(app=None):
    """Start the background scheduler exactly once per process."""
    global _started, _scheduler
    if _started:
        return

    # Skip scheduler when running under a fork-spawn test runner or when
    # reminders are explicitly disabled — handy for local dev too.
    if os.environ.get("DISABLE_PUSH_SCHEDULER") == "1":
        logger.info("Push scheduler disabled via DISABLE_PUSH_SCHEDULER=1")
        _started = True
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler not installed — push reminders disabled")
        _started = True
        return

    sched = BackgroundScheduler(daemon=True, timezone="UTC")
    sched.add_job(tick, "cron", second=5, id="checklist_push_tick", max_instances=1, coalesce=True)
    sched.start()

    atexit.register(lambda: sched.shutdown(wait=False))
    _scheduler = sched
    _started = True
    logger.info("Push reminder scheduler started")

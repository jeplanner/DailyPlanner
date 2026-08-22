"""Does a checklist item fall on a given date?

WHY THIS IS ITS OWN MODULE
--------------------------
Three places needed the answer and each had grown its own version:

  * ``push_scheduler._schedule_applies_today`` — the canonical one, since
    it decides whether a reminder actually fires.
  * ``day_board._checklist_for`` — a cruder copy with no branch for
    ``weekdays`` or ``weekends``, so those items fell through to "show it"
    and appeared on the board EVERY day, weekends included. Measured
    against live data: 3 weekday items and one weekend item were showing
    on all seven days.
  * ``checklist.list_items`` — handled only ``once``.

Any "you missed this" or adherence figure has to agree with the thing that
reminded you, or the two are telling the user different stories about the
same day. So the reminder's logic is the one that moved here and the
others now call it.

DAY NUMBERING. ``schedule_days`` stores Sun=0 … Sat=6 for ``custom``,
which is NOT Python's Mon=0 … Sun=6. The conversion lives here, once,
because getting it wrong is silent — the item simply appears on the wrong
day and nothing errors.
"""

from datetime import date as _date
from datetime import timedelta


def applies_on(schedule, schedule_days, on_date):
    """True if an item with this schedule falls on `on_date`.

    Lifted verbatim from push_scheduler so behaviour is unchanged; the
    weekday conversion that used to be the caller's job is done here.
    """
    if on_date is None:
        return False
    dow = (on_date.weekday() + 1) % 7          # Sun=0, Mon=1, ..., Sat=6
    days = schedule_days or ""

    if schedule == "daily" or not schedule:
        return True
    if schedule == "weekdays":
        return dow in (1, 2, 3, 4, 5)
    if schedule == "weekends":
        return dow in (0, 6)
    if schedule == "custom":
        allowed = {int(x) for x in days.split(",")
                   if x.strip().lstrip("-").isdigit()}
        return dow in allowed
    if schedule == "monthly_dow":
        # "WEEK:DAY" — the Nth (or last) DAY of the month.
        try:
            week_s, day_s = days.split(":", 1)
            target_week = int(week_s)
            target_day = int(day_s)
        except (ValueError, AttributeError):
            return False
        if dow != target_day:
            return False
        if target_week == -1:
            # Last occurrence: no same weekday left in this month.
            return (on_date + timedelta(days=7)).month != on_date.month
        return (on_date.day - 1) // 7 + 1 == target_week
    if schedule == "once":
        return days.strip() == on_date.isoformat()
    if schedule == "monthly_dom":
        raw = days.strip()
        if not raw:
            return False
        try:
            target = int(raw)
        except ValueError:
            return False
        if target == -1:
            return (on_date + timedelta(days=1)).month != on_date.month
        return on_date.day == target
    return False


def _as_date(value):
    if isinstance(value, _date):
        return value
    try:
        return _date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def is_due(item, on_date):
    """True if `item` (a checklist_items row) is due on `on_date`.

    Adds what `applies_on` does not know about: a soft-deleted item is
    never due, and `recurrence_end` stops a repeating item without
    deleting its history — which matters here, because an adherence
    figure that kept counting a finished item would show a growing run of
    misses for something the user deliberately ended.
    """
    if not item or item.get("is_deleted"):
        return False
    on_date = _as_date(on_date)
    if on_date is None:
        return False

    end = _as_date(item.get("recurrence_end"))
    if end and on_date > end:
        return False

    # An item cannot be due before it existed. Without this, a checklist
    # started last week shows months of "missed" days behind it, which is
    # both wrong and demoralising.
    created = _as_date((item.get("created_at") or "")[:10])
    if created and on_date < created:
        return False

    return applies_on(item.get("schedule") or "daily",
                      item.get("schedule_days") or "", on_date)

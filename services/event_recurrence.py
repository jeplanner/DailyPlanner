"""
Calendar event recurrence utilities.

Responsibilities:
  * Validate recurrence payload from the client.
  * Build a Google Calendar RRULE string for sync.
  * Given a master event's rule + a date range, enumerate the dates
    on which the event should occur (respecting recurrence_end and
    recurrence_count).

Design note: Python's weekday() returns Mon=0..Sun=6, but the rest of
this codebase (checklist, etc.) uses Sun=0..Sat=6 for weekday CSV.
We keep that Sun=0 convention in schedule_days for consistency.
"""
from datetime import date, timedelta


VALID_RULES = {"daily", "weekdays", "weekends", "weekly", "monthly", "custom"}

# Sun=0..Sat=6 → iCal two-letter codes
_DAY_CODES = {0: "SU", 1: "MO", 2: "TU", 3: "WE", 4: "TH", 5: "FR", 6: "SA"}


def _sun0(d):
    """Python's date.weekday() is Mon=0..Sun=6. Return Sun=0..Sat=6 instead."""
    return (d.weekday() + 1) % 7


def parse_recurrence(data):
    """Pull and validate recurrence fields from a request payload.

    Returns a dict with normalised fields or {} if no recurrence."""
    rule = (data.get("recurrence_rule") or "").strip().lower() or None
    if rule is None:
        return {}
    if rule not in VALID_RULES:
        raise ValueError(f"Invalid recurrence_rule: {rule}")

    days = (data.get("recurrence_days") or "").strip()
    # Keep only 0..6 digits from comma/space separated input.
    if days:
        cleaned = [p.strip() for p in days.replace(" ", ",").split(",")]
        days_list = [d for d in cleaned if d in {"0", "1", "2", "3", "4", "5", "6"}]
        days = ",".join(days_list) if days_list else None
    else:
        days = None

    if rule == "custom" and not days:
        raise ValueError("Custom schedule requires at least one day")

    end_str = (data.get("recurrence_end") or "").strip() or None
    end = date.fromisoformat(end_str) if end_str else None

    count = data.get("recurrence_count")
    if count in ("", None):
        count = None
    else:
        count = int(count)
        if count < 1:
            raise ValueError("recurrence_count must be >= 1")

    if end and count:
        # Google allows only one; keep `end` as the authoritative bound.
        count = None

    return {
        "recurrence_rule": rule,
        "recurrence_days": days,
        "recurrence_end": end.isoformat() if end else None,
        "recurrence_count": count,
    }


def occurs_on(plan_date, rule, days_csv, start_date):
    """Does the recurring series cover this date (ignoring end/count)?
    `start_date` is the series' anchor date (first occurrence)."""
    if plan_date < start_date:
        return False
    dow = _sun0(plan_date)
    if rule == "daily":
        return True
    if rule == "weekdays":
        return dow in (1, 2, 3, 4, 5)
    if rule == "weekends":
        return dow in (0, 6)
    if rule == "weekly":
        # Same day of week as the start date.
        return _sun0(plan_date) == _sun0(start_date)
    if rule == "monthly":
        return plan_date.day == start_date.day
    if rule == "custom":
        allowed = {int(x) for x in (days_csv or "").split(",") if x.strip().isdigit()}
        return dow in allowed
    return False


def expand_occurrences(master, range_start, range_end):
    """Yield the dates in [range_start, range_end] on which `master`
    (a daily_events row with recurrence fields) occurs.

    Respects:
      - start = master["plan_date"]
      - recurrence_end (inclusive upper bound on dates)
      - recurrence_count (limits total occurrences across the whole series)
    """
    rule = master.get("recurrence_rule")
    if not rule:
        # Non-recurring event — one occurrence on its own plan_date.
        pd = date.fromisoformat(master["plan_date"])
        if range_start <= pd <= range_end:
            yield pd
        return

    series_start = date.fromisoformat(master["plan_date"])
    series_end = master.get("recurrence_end")
    series_end = date.fromisoformat(series_end) if series_end else None
    count_limit = master.get("recurrence_count")
    days_csv = master.get("recurrence_days")

    # Walk the intersection of [series_start, range_end].
    walk_start = max(series_start, range_start)
    walk_end = min(series_end, range_end) if series_end else range_end

    if walk_end < walk_start:
        return

    # If there's a count limit, we need to count from series_start even
    # for dates before range_start (so we stop at the right one).
    if count_limit:
        emitted_total = 0
        cursor = series_start
        while cursor <= walk_end and emitted_total < count_limit:
            if occurs_on(cursor, rule, days_csv, series_start):
                emitted_total += 1
                if cursor >= range_start:
                    yield cursor
            cursor += timedelta(days=1)
        return

    # No count limit — just walk the visible window.
    cursor = walk_start
    while cursor <= walk_end:
        if occurs_on(cursor, rule, days_csv, series_start):
            yield cursor
        cursor += timedelta(days=1)


def build_rrule(rule, days_csv, end_date=None, count=None):
    """Build a Google Calendar iCal RRULE string for the given rule."""
    if rule == "weekdays":
        base = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    elif rule == "weekends":
        base = "FREQ=WEEKLY;BYDAY=SA,SU"
    elif rule == "weekly":
        base = "FREQ=WEEKLY"
    elif rule == "monthly":
        base = "FREQ=MONTHLY"
    elif rule == "custom":
        codes = {"0": "SU", "1": "MO", "2": "TU", "3": "WE",
                 "4": "TH", "5": "FR", "6": "SA"}
        days = [d.strip() for d in (days_csv or "").split(",") if d.strip() in codes]
        base = "FREQ=WEEKLY;BYDAY=" + ",".join(codes[d] for d in days) if days else "FREQ=DAILY"
    else:  # daily, or anything unrecognised → daily
        base = "FREQ=DAILY"

    if end_date:
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        base += ";UNTIL=" + end_date.strftime("%Y%m%dT235959Z")
    elif count:
        base += f";COUNT={int(count)}"

    return "RRULE:" + base

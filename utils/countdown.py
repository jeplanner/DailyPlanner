"""
Deadline countdown maths for the goal planner.

Pure functions only — no Flask, no DB, no clock of their own. Every entry
point takes `now` explicitly so the behaviour is testable and so callers are
forced to pass a timezone-correct moment from `utils.user_tz.user_now()`. A
countdown that is silently a few hours out is worse than no countdown.

The design decisions encoded here, in order of how much they matter:

  1. COUNT TO A MOMENT. A bare date cannot express "6h 20m left", so a date
     is resolved to end-of-day in the user's timezone before anything else.

  2. ONE DOMINANT UNIT. Showing weeks AND days AND hours AND minutes at once
     is a wall of digits nobody reads. `breakdown()` returns every unit, and
     `display()` picks the one that should be big — escalating as the
     deadline closes. The escalation is itself the urgency signal, which is
     why the page does not need to shout while a goal is still far away.

  3. WORKING DAYS. "44 days" quietly includes a dozen weekend days the user
     was never going to work. Both numbers are returned.

  4. PACE, NOT JUST TIME. A countdown on its own produces anxiety without
     direction. `pace()` says how far ahead or behind the plan actually is.

  5. A TIME BUDGET. The most actionable number on the page: days remaining
     times the daily commitment, against the effort the goal is believed to
     need. `budget()` is what tells you a goal is impossible early enough to
     re-scope it.
"""
from datetime import date, datetime, time, timedelta

#: Tick intervals, in seconds, for the client. Counting every second for a
#: deadline six weeks out burns battery to animate a digit nobody is reading.
TICK_SECOND = 1
TICK_MINUTE = 60
TICK_HOUR = 3600

#: Urgency tones, coarsest first. The page maps these to styling; `urgent`
#: is the only one that pulses.
TONE_DONE = "done"
TONE_CALM = "calm"
TONE_SOON = "soon"
TONE_URGENT = "urgent"
TONE_OVERDUE = "overdue"

_MIN = 60
_HOUR = 3600
_DAY = 86400
_WEEK = 604800


def resolve_target(target_at, target_date, tz):
    """The deadline as an aware datetime, from whichever field is set.

    A bare `target_date` means "by the end of that day" — treating it as
    midnight would silently steal the last 24 hours of every goal.
    Returns None when neither field is set.
    """
    if target_at is not None:
        if isinstance(target_at, str):
            target_at = _parse_iso(target_at)
        if target_at is None:
            return None
        return target_at if target_at.tzinfo else target_at.replace(tzinfo=tz)
    if target_date is not None:
        if isinstance(target_date, str):
            try:
                target_date = date.fromisoformat(target_date[:10])
            except ValueError:
                return None
        return datetime.combine(target_date, time(23, 59, 59), tzinfo=tz)
    return None


def _parse_iso(value):
    """Tolerant ISO-8601 parse. Postgres sends `+00:00`, some clients send
    `Z`, and a value we cannot read must not take the page down."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def breakdown(target, now):
    """Every unit of the remaining time, plus the overdue flag.

    `weeks`/`days`/`hours`/`minutes`/`seconds` are a COMPLEMENTARY split —
    they sum to the total, so 16 days reads "2w 2d", not "2w 16d". When the
    deadline has passed the same split describes how long ago, and
    `overdue` is True.
    """
    if target is None:
        return None
    delta = target - now
    total = int(delta.total_seconds())
    overdue = total < 0
    rem = abs(total)
    weeks, rem = divmod(rem, _WEEK)
    days, rem = divmod(rem, _DAY)
    hours, rem = divmod(rem, _HOUR)
    minutes, seconds = divmod(rem, _MIN)
    return {
        "total_seconds": total,
        "overdue": overdue,
        "weeks": weeks, "days": days, "hours": hours,
        "minutes": minutes, "seconds": seconds,
        # Flat totals, for callers that want "44 days" rather than the split.
        "total_days": abs(total) // _DAY,
        "total_hours": abs(total) // _HOUR,
    }


def working_days(start, end, workdays=(0, 1, 2, 3, 4)):
    """Whole working days from `start` to `end`, counting the end date.

    `workdays` is a tuple of `date.weekday()` values, Monday = 0, so a
    six-day study week is `(0,1,2,3,4,5)`. Returns 0 when end precedes
    start rather than a negative count — "minus three working days" is
    not a thing anyone wants to read.
    """
    if start is None or end is None:
        return 0
    if isinstance(start, datetime):
        start = start.date()
    if isinstance(end, datetime):
        end = end.date()
    if end < start:
        return 0
    # Count by whole weeks first, then walk the ragged tail. Walking every
    # day would be fine for months but not for a multi-year goal.
    total_days = (end - start).days + 1
    whole_weeks, tail = divmod(total_days, 7)
    count = whole_weeks * len(workdays)
    for i in range(tail):
        if (start + timedelta(days=whole_weeks * 7 + i)).weekday() in workdays:
            count += 1
    return count


def display(bd):
    """Which unit to show big, how to label it, and how fast to tick.

    The unit escalates as the deadline approaches, so the page gets more
    precise — and only then more insistent — on its own.
    """
    if bd is None:
        return None
    if bd["overdue"]:
        return {"value": bd["total_days"], "unit": "days overdue",
                "tick": TICK_MINUTE, "tone": TONE_OVERDUE}
    total = bd["total_seconds"]
    if total >= 3 * _WEEK:
        weeks = total // _WEEK
        return {"value": weeks, "unit": "week" + ("s" if weeks != 1 else ""),
                "tick": TICK_HOUR, "tone": TONE_CALM}
    if total >= _WEEK:
        days = total // _DAY
        return {"value": days, "unit": "days", "tick": TICK_HOUR, "tone": TONE_CALM}
    if total >= _DAY:
        days = total // _DAY
        return {"value": days, "unit": "day" + ("s" if days != 1 else ""),
                "tick": TICK_MINUTE, "tone": TONE_SOON}
    if total >= _HOUR:
        return {"value": total // _HOUR, "unit": "hours left",
                "tick": TICK_SECOND, "tone": TONE_URGENT}
    if total > 0:
        return {"value": total // _MIN, "unit": "minutes left",
                "tick": TICK_SECOND, "tone": TONE_URGENT}
    return {"value": 0, "unit": "time is up", "tick": TICK_MINUTE, "tone": TONE_DONE}


def pace(start, target, now, progress_pct):
    """Where the plan SHOULD be versus where it is.

    Returns `expected` (percent of the elapsed calendar), `gap` (actual
    minus expected, so negative means behind) and `gap_days` — the gap
    expressed as days of slippage, which is the form people actually
    understand. Returns None when the window is unknown.
    """
    if start is None or target is None:
        return None
    if isinstance(start, datetime):
        start_dt = start
    else:
        start_dt = datetime.combine(start, time(0, 0), tzinfo=now.tzinfo)
    total = (target - start_dt).total_seconds()
    if total <= 0:
        return None
    elapsed = max(0.0, min(total, (now - start_dt).total_seconds()))
    expected = round(elapsed / total * 100)
    progress = max(0, min(100, int(progress_pct or 0)))
    gap = progress - expected
    # A percentage gap means little on its own; converting it back into days
    # of the plan is what makes it actionable.
    gap_days = round(gap / 100 * (total / _DAY), 1)
    return {"expected": expected, "progress": progress,
            "gap": gap, "gap_days": gap_days, "behind": gap < 0}


def budget(working_days_left, daily_commit_minutes, effort_minutes):
    """Time available against time required — the re-scope alarm.

    Returns None unless both a daily commitment and an effort estimate are
    known, because a budget with a guessed denominator is worse than no
    budget at all.
    """
    if not daily_commit_minutes or not effort_minutes:
        return None
    available = max(0, int(working_days_left)) * int(daily_commit_minutes)
    needed = int(effort_minutes)
    shortfall = needed - available
    # What the daily commitment would have to become to close the gap.
    required_daily = (
        int(round(needed / working_days_left)) if working_days_left > 0 else None
    )
    return {
        "available_minutes": available,
        "needed_minutes": needed,
        "shortfall_minutes": max(0, shortfall),
        "surplus_minutes": max(0, -shortfall),
        "feasible": shortfall <= 0,
        "required_daily_minutes": required_daily,
        "commit_minutes": int(daily_commit_minutes),
    }


def hhmm(minutes):
    """Minutes as a human duration: 88h, 3h 10m, 45m."""
    minutes = int(minutes or 0)
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def summarise(goal, now, tz, progress_pct=0, workdays=(0, 1, 2, 3, 4)):
    """Everything the UI needs for one goal, in one dict.

    `goal` is an objectives row (or anything with the same keys), so this
    is the single place that knows how the columns map onto the maths.
    """
    target = resolve_target(goal.get("target_at"), goal.get("target_date"), tz)
    bd = breakdown(target, now)
    if bd is None:
        return {"has_deadline": False}
    wd = working_days(now, target, workdays) if not bd["overdue"] else 0
    start = goal.get("start_date") or (goal.get("created_at") or "")[:10] or None
    if isinstance(start, str) and start:
        try:
            start = date.fromisoformat(start[:10])
        except ValueError:
            start = None
    out = {
        "has_deadline": True,
        "target_iso": target.isoformat(),
        "breakdown": bd,
        "display": display(bd),
        "working_days_left": wd,
        "pace": pace(start, target, now, progress_pct),
        "budget": budget(wd, goal.get("daily_commit_minutes"),
                         goal.get("effort_minutes")),
        # A goal can opt out of the pulse; the tone still drives the wording.
        "flash": bool(goal.get("flash_enabled", True))
        and display(bd)["tone"] in (TONE_URGENT, TONE_OVERDUE),
    }
    return out

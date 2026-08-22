"""THE CHAIN — one number that says whether you showed up today.

WHY THIS SHAPE, AND NOT POINTS. The app already has a game: Sadhana, the
swara ladder in static/js/gamify.js. It is good, and it has two problems
that stop it motivating anything. It lives in localStorage, so the phone
and the laptop each believe a different story and neither is true. And it
only exists on the prep pages, so it says nothing about the days you did
not open them — which are the days that need saying something about.

So this is deliberately NOT more XP. It is the oldest working mechanic
there is: don't break the chain. One bar, one number, every day, on the
screen you already look at.

CALIBRATED AGAINST THE REAL DATA, WHICH WAS BLEAK. Measured on 2026-08-22
over the preceding 60 days: 9 checklist ticks out of 926 due (1%), and
THREE days with any recorded activity of any kind. A perfect-day streak —
which is what services/checklist_history.load() already computes — would
have read 0 forever and been an accusation rather than a game.

Two consequences, both deliberate:

  * THE BAR IS LOW ON PURPOSE. Five things closed. Not a perfect day, not
    a percentage of a checklist that has nineteen due items on a weekday.
    A bar you clear is a bar you come back to; today's real count would
    clear it, which is the whole point of picking it.
  * ANYTHING COUNTS. A checklist tick, a bucket item, a task, a prep topic
    studied. Tying the only game to the checklist would have tied it to
    the one surface the data says he does not use.

THE STREAK DOES NOT DIE AT MIDNIGHT. It survives while YESTERDAY still
qualifies, because a streak that reads 0 every morning until you have done
five things is not a streak, it is a nag. It breaks when a whole day has
been and gone under the bar.

Nothing here writes. It is derived from rows the app already stores, so
there is no table, nothing to migrate, and nothing to keep in sync — the
same reasoning that made Sadhana's XP derived, applied to a number that
is actually shared between devices because the rows are.
"""
import logging
from collections import Counter
from datetime import timedelta

from services import loud
from supabase_client import get

logger = logging.getLogger("daily_plan")

#: Things closed in a day for it to count. See the calibration note above.
BAR = 5

#: How far back to look. Long enough for "best" to mean something, short
#: enough that four queries stay cheap.
WINDOW = 90

#: (table, date column, extra filters). Each contributes ONE point per row.
#:
#: todo_matrix has no done_at — only is_done and updated_at — so a finished
#: task is credited to the day it was last TOUCHED. That is right the day
#: you tick it and wrong if you edit it a week later, which is rare and
#: which inflates rather than deflates. Said out loud rather than papered
#: over; if it ever matters the fix is a done_at column, not arithmetic.
SOURCES = (
    ("checklist_ticks", "tick_date", {}),
    ("quick_bucket", "done_at", {"is_done": "eq.true"}),
    ("todo_matrix", "updated_at", {"is_done": "eq.true"}),
    ("ai_sde_progress", "studied_at", {"studied": "eq.true"}),
)


def _counts(user_id, start_iso):
    """{iso_date: things closed}, across every source, one query each."""
    tally = Counter()
    reached = 0
    for table, col, extra in SOURCES:
        params = {"user_id": f"eq.{user_id}", "select": col,
                  f"{col}": f"gte.{start_iso}", "limit": "5000"}
        params.update(extra)
        try:
            rows = get(table, params=params) or []
        except Exception:
            # One missing table must not cost the whole number. Loud, though:
            # a streak quietly computed from three of four sources is a
            # WRONG streak, not a smaller one.
            loud.bailed("streak", f"source {table} could not be read",
                        table=table)
            logger.warning("streak: %s unreadable", table, exc_info=True)
            continue
        reached += 1
        for r in rows:
            v = r.get(col)
            if v:
                tally[str(v)[:10]] += 1
    return tally, reached


def _line(streak, today_count, met, active, window):
    """The one sentence under the number.

    Tough, because that was asked for, and true, because copy that flatters
    a 1% adherence rate is how a dashboard becomes wallpaper.
    """
    if streak >= 30:
        return f"{streak} days. This is who you are now, not what you are trying."
    if streak >= 7:
        return f"{streak} days. Protect it — the only way this ends is you deciding it does."
    if streak >= 2:
        return f"Day {streak}. Two is luck, seven is a habit. Keep going."
    if met and streak == 1:
        return (f"Day 1. The {window} days before it had {active} like it. "
                "Tomorrow is the whole game.")
    if today_count > 0:
        need = BAR - today_count
        return (f"{today_count} closed. {need} more and today counts — "
                "that is twenty minutes, not a personality change.")
    if active == 0:
        return f"Nothing in {window} days. Close five things and the chain starts today."
    return "Chain broken. Close five things and it starts again today — that is the deal."


def compute(user_id, today, window=WINDOW, bar=BAR):
    """The chain, as of `today`. Never raises: a broken game is not an outage."""
    blank = {"ok": False, "streak": 0, "best": 0, "today": 0, "bar": bar,
             "met": False, "active": 0, "window": window,
             "line": "", "days": []}
    try:
        start = today - timedelta(days=window - 1)
        tally, reached = _counts(user_id, start.isoformat())
        if not reached:
            return blank

        # Newest first, every day present so a gap is a zero rather than a
        # missing key — the gaps ARE the data here.
        days = []
        for n in range(window):
            d = today - timedelta(days=n)
            days.append({"date": d.isoformat(), "n": tally.get(d.isoformat(), 0)})

        met_today = days[0]["n"] >= bar

        # Count back from today if today already qualifies, otherwise from
        # yesterday — see "does not die at midnight" above.
        streak = 0
        for d in (days if met_today else days[1:]):
            if d["n"] >= bar:
                streak += 1
            else:
                break

        best, run = 0, 0
        for d in reversed(days):
            run = run + 1 if d["n"] >= bar else 0
            best = max(best, run)

        active = sum(1 for d in days if d["n"] > 0)
        return {
            "ok": True,
            "streak": streak,
            "best": max(best, streak),
            "today": days[0]["n"],
            "bar": bar,
            "met": met_today,
            "active": active,
            "window": window,
            "line": _line(streak, days[0]["n"], met_today, active, window),
            "days": days[:14],          # for a sparkline; newest first
        }
    except Exception:
        logger.warning("streak: compute failed", exc_info=True)
        return blank

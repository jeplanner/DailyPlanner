"""Day Board — the whole day on one screen, with no scrolling, ever.

WHAT THIS IS FOR
----------------
A small always-on monitor (10", typically 1280x800 or 1024x600) sitting on a
desk showing today: the calendar down one side, the tasks and checklist down
the other. You glance at it. You do not touch it, and you never scroll it.

WHY IT IS A SEPARATE PAGE RATHER THAN A CSS TWEAK ON /todo
----------------------------------------------------------
Every other page in this app is built for a phone: a single column you scroll
through, with content free to be as tall as it likes. A board is the opposite
constraint — the viewport is FIXED and the content must be made to fit inside
it. Those two requirements fight, and trying to serve both from one template
produces a page that is bad at both.

THREE THINGS MAKE "IT ALWAYS FITS" TRUE RATHER THAN HOPEFUL
-----------------------------------------------------------
1. The page CANNOT scroll. `height:100dvh` + `overflow:hidden` on the grid, so
   overflow is a rendering decision rather than something the user is silently
   handed a scrollbar for.
2. The layout is measured and SHRUNK to fit. A single CSS custom property
   drives every size on the page, and a script steps it down until the tallest
   panel fits. That is the only way to be correct for both a 3-item day and a
   40-item one.
3. When it genuinely cannot fit even at the smallest readable size, it says so
   — "+7 more" — instead of quietly clipping. A board that hides work without
   telling you is worse than no board.

EVERYTHING IS SERVER-RENDERED IN ONE REQUEST. No client-side fetches: a kiosk
should never show a half-loaded screen, and a display left running for weeks
should not depend on a token still being valid in JavaScript.
"""
import logging
from datetime import date, datetime, time, timedelta

from flask import Blueprint, render_template, request, session

from services.login_service import login_required
from services import event_recurrence
from supabase_client import get
from utils.user_tz import user_now, user_today

logger = logging.getLogger("daily_plan")

day_board_bp = Blueprint("day_board", __name__)

#: The visible window when the day has no timed events to bound it. Chosen
#: over a full 00:00-24:00 rail because 24 rows on a 10" screen leaves each
#: hour too short to place anything legibly, and the small hours are almost
#: always empty.
DEFAULT_WINDOW = (time(7, 0), time(22, 0))

#: How often the page reloads itself. Two minutes is frequent enough that a
#: newly added task appears while you are still thinking about it, and rare
#: enough that a full re-render is never in the way.
DEFAULT_REFRESH_SECONDS = 120


def _parse_hhmm(value, fallback=None):
    """Accept '9', '9:30', '09:30', '0930'. Returns a time or the fallback."""
    if not value:
        return fallback
    v = str(value).strip()
    try:
        if ":" in v:
            h, m = v.split(":", 1)
            return time(int(h) % 24, int(m) % 60)
        if len(v) == 4 and v.isdigit():
            return time(int(v[:2]) % 24, int(v[2:]) % 60)
        return time(int(v) % 24, 0)
    except (ValueError, TypeError):
        return fallback


def _minutes(t):
    return t.hour * 60 + t.minute


def _events_for(user_id, plan_date):
    """Timed events for one date, with recurrence expanded.

    Deliberately mirrors /api/v2/events rather than calling it — the board
    renders server-side in one pass, and an internal HTTP hop to our own API
    would add a round trip and a second place for auth to fail.
    """
    plan_date_str = plan_date.isoformat()
    rows = get("daily_events", params={
        "user_id": f"eq.{user_id}", "is_deleted": "eq.false",
    }) or []

    singles = [r for r in rows
               if not r.get("recurrence_rule") and not r.get("is_exception")
               and r.get("plan_date") == plan_date_str]
    masters = [r for r in rows if r.get("recurrence_rule")]
    overrides = {(r.get("series_id"), r.get("original_date")): r
                 for r in rows if r.get("is_exception")}

    skipped_rows = get("event_exceptions", params={
        "user_id": f"eq.{user_id}", "exception_date": f"eq.{plan_date_str}",
    }) or []
    skipped = {r["series_id"] for r in skipped_rows if r.get("reason") == "deleted"}

    expanded = []
    for m in masters:
        if m.get("series_id") in skipped:
            continue
        if plan_date not in event_recurrence.expand_occurrences(m, plan_date, plan_date):
            continue
        override = overrides.get((m.get("series_id"), plan_date_str))
        expanded.append({**(override or m), "plan_date": plan_date_str})

    events = singles + expanded
    events.sort(key=lambda r: (r.get("start_time") or "99:99"))
    return events


def _tasks_for(user_id, plan_date):
    """Eisenhower tasks scheduled for the date, most urgent first."""
    rows = get("todo_matrix", params={
        "user_id": f"eq.{user_id}",
        "plan_date": f"eq.{plan_date.isoformat()}",
        "is_deleted": "eq.false",
    }) or []
    # Q1 urgent+important first, then Q2, Q3, Q4; done items sink to the bottom
    # so the board reads as "what is left", which is the only question a glance
    # is asking.
    rank = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
    def key(t):
        done = bool(t.get("is_done")) or t.get("status") == "done"
        return (done, rank.get((t.get("quadrant") or "").upper(), 4),
                t.get("task_time") or "99:99")
    rows.sort(key=key)
    return rows


def _checklist_for(user_id, plan_date):
    """Today's checklist with its tick state.

    Weekly/one-off items that do not fall on this date are dropped here rather
    than rendered greyed out — a board has no room for things that are not
    today's business.
    """
    day_str = plan_date.isoformat()
    weekday = plan_date.strftime("%a").lower()      # mon, tue, ...

    items = get("checklist_items", params={
        "user_id": f"eq.{user_id}", "is_deleted": "eq.false",
        "order": "position.asc,created_at.asc",
    }) or []

    def due_today(it):
        sched = (it.get("schedule") or "daily").lower()
        days = (it.get("schedule_days") or "").strip().lower()
        if sched == "once":
            return days == day_str
        if sched in ("weekly", "days", "custom") and days:
            return weekday in [d.strip()[:3] for d in days.split(",")]
        return True                                  # daily, or unspecified

    items = [i for i in items if due_today(i)]

    ticks = get("checklist_ticks", params={
        "user_id": f"eq.{user_id}", "tick_date": f"eq.{day_str}",
    }) or []
    ticked = {t["item_id"] for t in ticks}

    return [{
        "id": i.get("id"),
        "title": i.get("title") or i.get("name") or i.get("text") or "",
        "done": i.get("id") in ticked,
    } for i in items if (i.get("title") or i.get("name") or i.get("text"))]


def _layout_events(events, win_start, win_end):
    """Position each event on the rail as a percentage, and lane overlaps.

    Returns rows carrying top/height as percentages of the window, plus a lane
    index so concurrent events sit side by side instead of on top of each
    other — which is the difference between a board you can read at a glance
    and one you have to decode.
    """
    span = max(1, _minutes(win_end) - _minutes(win_start))
    placed = []
    for e in events:
        st = _parse_hhmm(e.get("start_time"))
        if st is None:
            continue                                  # untimed -> the task column
        en = _parse_hhmm(e.get("end_time")) or (
            datetime.combine(date.today(), st) + timedelta(minutes=30)).time()
        w0, w1 = _minutes(win_start), _minutes(win_end)
        raw_s = _minutes(st)
        raw_t = max(_minutes(en), raw_s + 1)

        # Decide in/out on the RAW span. Clamping first and then applying the
        # minimum height would drag a 02:00 event up to the top of an 08:00
        # window and render it as if it were happening at breakfast.
        if raw_t <= w0 or raw_s >= w1:
            continue

        s, t = max(w0, raw_s), min(w1, raw_t)
        if t - s < 15:                                # a visible minimum, taken
            s = max(w0, min(s, t - 15))               # from the START so the bar
            t = min(w1, max(t, s + 15))               # never runs past the window
        placed.append({
            "raw": e,
            "title": e.get("title") or e.get("event_text") or e.get("name") or "(untitled)",
            "start": st.strftime("%H:%M"),
            "end": en.strftime("%H:%M"),
            "s": s, "t": t,
            "top": (s - _minutes(win_start)) / span * 100.0,
            "height": (t - s) / span * 100.0,
        })

    # Greedy lane assignment: an event takes the first lane whose last event
    # has already finished.
    placed.sort(key=lambda p: (p["s"], -p["t"]))
    lane_end = []
    for p in placed:
        for i, end in enumerate(lane_end):
            if p["s"] >= end:
                p["lane"] = i
                lane_end[i] = p["t"]
                break
        else:
            p["lane"] = len(lane_end)
            lane_end.append(p["t"])
    lanes = max(1, len(lane_end))
    for p in placed:
        p["lane_count"] = lanes
    return placed


@day_board_bp.route("/day-board")
@day_board_bp.route("/board")
@login_required
def day_board():
    user_id = session["user_id"]

    raw_date = (request.args.get("date") or "").strip()
    try:
        plan_date = date.fromisoformat(raw_date) if raw_date else user_today()
    except ValueError:
        plan_date = user_today()

    events = _events_for(user_id, plan_date)
    tasks = _tasks_for(user_id, plan_date)
    checklist = _checklist_for(user_id, plan_date)

    # The visible window. Explicit ?from/?to wins; otherwise fit it to the
    # day's actual events with an hour of margin, so an early-start day is not
    # squeezed into a rail that begins at 07:00 and a quiet day does not waste
    # half the screen on empty hours.
    starts = [t for t in (_parse_hhmm(e.get("start_time")) for e in events) if t]
    ends = [t for t in (_parse_hhmm(e.get("end_time")) for e in events) if t]
    if starts:
        auto_start = time(max(0, min(starts).hour - 1), 0)
        auto_end = time(min(23, (max(ends or starts).hour + 2)), 0)
    else:
        auto_start, auto_end = DEFAULT_WINDOW
    win_start = _parse_hhmm(request.args.get("from"), auto_start)
    win_end = _parse_hhmm(request.args.get("to"), auto_end)
    if _minutes(win_end) <= _minutes(win_start):
        win_start, win_end = DEFAULT_WINDOW

    placed = _layout_events(events, win_start, win_end)
    untimed = [e for e in events if not _parse_hhmm(e.get("start_time"))]

    hours = []
    h = win_start.hour
    while h <= win_end.hour:
        hours.append(time(h, 0))
        h += 1

    now = user_now()
    is_today = plan_date == user_today()
    span = max(1, _minutes(win_end) - _minutes(win_start))
    now_pct = None
    if is_today:
        m = now.hour * 60 + now.minute
        if _minutes(win_start) <= m <= _minutes(win_end):
            now_pct = (m - _minutes(win_start)) / span * 100.0

    try:
        refresh = max(0, min(3600, int(request.args.get("refresh",
                                                        DEFAULT_REFRESH_SECONDS))))
    except (TypeError, ValueError):
        refresh = DEFAULT_REFRESH_SECONDS

    # Server-side "happening now", so the first paint is already right rather
    # than waiting a tick for the script.
    if is_today:
        m_now = now.hour * 60 + now.minute
        for p in placed:
            p["is_now"] = p["s"] <= m_now < p["t"]
    else:
        for p in placed:
            p["is_now"] = False

    open_tasks = [t for t in tasks
                  if not (t.get("is_done") or t.get("status") == "done")]

    return render_template(
        "day_board.html",
        plan_date=plan_date,
        is_today=is_today,
        date_label=plan_date.strftime("%a %-d %b") if hasattr(plan_date, "strftime")
                   else str(plan_date),
        prev_date=(plan_date - timedelta(days=1)).isoformat(),
        next_date=(plan_date + timedelta(days=1)).isoformat(),
        hours=hours,
        win_start=win_start, win_end=win_end,
        placed=placed, untimed=untimed,
        tasks=tasks, open_task_count=len(open_tasks),
        checklist=checklist,
        checklist_done=sum(1 for c in checklist if c["done"]),
        now_pct=now_pct,
        refresh=refresh,
        theme=(request.args.get("theme") or "dark").lower(),
    )

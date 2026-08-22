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

from flask import Blueprint, jsonify, render_template, request, session, url_for

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


def build_summary(user_id, plan_date, now_minutes=None):
    """The day compressed to a notification: a title and 2-3 short lines.

    A notification is not a board — it is one glance, in a shade the user is
    already looking at for other reasons. So it answers only the question a
    glance is asking: WHAT IS NEXT, and HOW MUCH IS LEFT. Everything else is
    one tap away on the board itself.
    """
    events = _events_for(user_id, plan_date)
    tasks = _tasks_for(user_id, plan_date)
    checklist = _checklist_for(user_id, plan_date)

    open_tasks = [t for t in tasks
                  if not (t.get("is_done") or t.get("status") == "done")]
    done_checks = sum(1 for c in checklist if c["done"])

    timed = []
    for e in events:
        st = _parse_hhmm(e.get("start_time"))
        if not st:
            continue
        en = _parse_hhmm(e.get("end_time")) or st
        timed.append((_minutes(st), _minutes(en), st.strftime("%H:%M"),
                      e.get("title") or e.get("event_text") or e.get("name") or "Event"))
    timed.sort()

    lines = []
    title = None

    if now_minutes is not None:
        current = [t for t in timed if t[0] <= now_minutes < max(t[1], t[0] + 1)]
        upcoming = [t for t in timed if t[0] > now_minutes]
        if current:
            title = "Now: " + current[0][3]
        elif upcoming:
            mins = upcoming[0][0] - now_minutes
            when = f"in {mins}m" if mins < 60 else f"at {upcoming[0][2]}"
            title = f"Next {when}: {upcoming[0][3]}"
        # The next two things after that, so the glance has a horizon rather
        # than just a single item.
        for t in upcoming[:2] if current else upcoming[1:3]:
            lines.append(f"{t[2]}  {t[3]}")
    else:
        upcoming = timed
        for t in timed[:2]:
            lines.append(f"{t[2]}  {t[3]}")

    if title is None:
        # No event now and none to come. The title should say WHAT IS LEFT,
        # not restate the day's total — "3 events today" at 6pm is a fact
        # about the past and answers nothing.
        if open_tasks:
            title = f"{len(open_tasks)} to do"
        elif checklist and done_checks < len(checklist):
            title = f"Checklist {done_checks}/{len(checklist)}"
        elif timed or tasks or checklist:
            title = "Day clear"
        else:
            title = "Nothing scheduled"

    if open_tasks:
        lines.append("To do: " + ", ".join(
            (t.get("task_text") or "").strip() for t in open_tasks[:2]))
        if len(open_tasks) > 2:
            lines[-1] += f"  (+{len(open_tasks) - 2})"
    if checklist:
        lines.append(f"Checklist {done_checks}/{len(checklist)}")

    if not lines:
        lines.append("Nothing left for today.")

    return {
        "title": title,
        "body": "\n".join(lines[:3]),
        "counts": {
            "events": len(timed),
            "open_tasks": len(open_tasks),
            "checklist_done": done_checks,
            "checklist_total": len(checklist),
        },
    }


#: The notification's payload flags. Ambient, not alerting: it refreshes
#: itself, so buzzing on every update would make the pin unusable within a
#: day. Kept here so the manual pin and the scheduled refresh cannot drift
#: apart — two places sending "the same" notification differently is exactly
#: the sort of thing nobody notices until the phone starts vibrating at 3pm.
AMBIENT = {"silent": True, "renotify": False, "vibrate": [],
           "requireInteraction": True}

PIN_TAG = "day-board"      # one row in the shade, replaced — never a stack


def signature(summary):
    """A stable hash of what the user would SEE.

    The scheduler re-sends when this changes rather than on a timer, so an
    unchanged day costs nothing. Hashing the rendered text rather than the
    underlying rows is deliberate: a task being reordered, or an event's
    description being edited, does not change the notification and should not
    produce one.
    """
    import hashlib
    raw = f"{summary['title']}\n{summary['body']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def send_pin(user_id, summary):
    """Push the summary. Returns (sent, failed)."""
    from services import push_service
    return push_service.send_to_user(
        user_id,
        title=summary["title"],
        body=summary["body"],
        url="/day-board",
        tag=PIN_TAG,
        extra=AMBIENT,
        urgency="low",          # let the push service batch it and save battery
    )


def _pin_row(user_id):
    rows = get("day_board_pins", {"user_id": f"eq.{user_id}"}) or []
    return rows[0] if rows else None


@day_board_bp.route("/api/day-board/pin", methods=["GET"])
@login_required
def pin_status():
    row = _pin_row(session["user_id"]) or {}
    return jsonify({
        "active": bool(row.get("is_active")),
        "start_hour": row.get("start_hour", 7),
        "end_hour": row.get("end_hour", 22),
    })


@day_board_bp.route("/api/day-board/unpin", methods=["POST"])
@login_required
def unpin():
    """Stop refreshing. The row is kept so the window and cadence survive a
    toggle — losing your settings because you turned something off for an
    afternoon is a small betrayal."""
    from supabase_client import update as sb_update
    user_id = session["user_id"]
    if _pin_row(user_id):
        sb_update("day_board_pins", params={"user_id": f"eq.{user_id}"},
                  json={"is_active": False})
    return jsonify({"active": False})


@day_board_bp.route("/api/day-board/pin", methods=["POST"])
@login_required
def pin_to_notifications():
    """Push today's summary as an AMBIENT notification.

    Android will not let a web app draw over other apps — that needs a native
    permission a PWA cannot hold. The notification shade is the one surface a
    web app CAN occupy while you are in another app, so this puts the day's
    next thing there and keeps it there.

    silent + no vibration + renotify:false, so refreshing it updates the same
    row in place without a second buzz. requireInteraction keeps it pinned
    until dismissed rather than auto-hiding after a few seconds. Urgency low
    lets the push service batch delivery and spare the battery, which is the
    right trade for a status update and the wrong one for a reminder.
    """
    from supabase_client import post as sb_post, update as sb_update

    user_id = session["user_id"]
    plan_date = user_today()
    now = user_now()
    summary = build_summary(user_id, plan_date,
                            now_minutes=now.hour * 60 + now.minute)
    sent, failed = send_pin(user_id, summary)

    # Record it so the scheduler takes over from here. Written even if the
    # send failed: the pin is the user's INTENT, and a push that failed
    # because the phone was offline should still be refreshed later rather
    # than silently forgotten.
    state = {
        "is_active": True,
        "last_signature": signature(summary),
        "last_sent_at": now.isoformat(),
        "pinned_date": plan_date.isoformat(),
    }
    try:
        if _pin_row(user_id):
            sb_update("day_board_pins", params={"user_id": f"eq.{user_id}"},
                      json=state)
        else:
            sb_post("day_board_pins", {"user_id": user_id, **state})
    except Exception:
        # A missing table must not break the button — the notification was
        # already sent, it just will not auto-refresh until the migration is
        # applied. Say so rather than failing the request.
        logger.warning("day_board_pins unavailable — pin sent but will not "
                       "auto-refresh (run MIGRATION_DAY_BOARD_PIN.sql)")
        return jsonify({"sent": sent, "failed": failed, "active": False,
                        "persisted": False, **summary})

    return jsonify({"sent": sent, "failed": failed, "active": True,
                    "persisted": True, **summary})


# ── Click-through ─────────────────────────────────────────────────────
# The board began as a look-only kiosk. It is now also the fastest way IN:
# tapping a row opens the section that owns it, and every such link carries
# `from=board` plus the board's date so the destination can offer one tap
# back. Without that return trip the board becomes a dead end, and a dead end
# is worse than a link nobody presses.
#
# The URLs are built HERE rather than in the template because the three
# destinations disagree about how a date is spelled — /day takes an ISO
# `date`, /todo takes year/month/day, /checklist takes none at all — and
# hiding that in Jinja would put three different conventions in the markup.

def _back_args(plan_date):
    """Query args every click-through carries, so the way back is never lost."""
    return {"from": "board", "bd": plan_date.isoformat()}


def _link_event(item, plan_date):
    """An event opens the day view for the date it belongs to.

    The focus id is PREFIXED "ev-" because that is what the day view calls
    its event rows (agenda_service builds them as f"ev-{row id}"). Sending
    the raw row id would land on the right page with nothing highlighted,
    which looks like the link is broken rather than like the row is gone.
    """
    raw_id = item.get("id")
    focus = f"ev-{raw_id}" if raw_id else ""
    return url_for("day.day_page", date=plan_date.isoformat(),
                   focus=focus, **_back_args(plan_date))


def _link_task(item, plan_date):
    """A task opens the Eisenhower matrix, which wants the date in parts."""
    return url_for("todo.todo", year=plan_date.year, month=plan_date.month,
                   day=plan_date.day, focus=item.get("id") or "",
                   **_back_args(plan_date))


def _link_checklist(item, plan_date):
    """The checklist now takes ?date=, so a row from any board day links.

    It used to be today-only by construction, which is why rows on a past or
    future board were left unlinked — a link would have landed on today's
    list while appearing to open that day's. The page now shows the day it
    is asked for, read-only when it is not today.
    """
    return url_for("checklist.checklist_page", date=plan_date.isoformat(),
                   focus=item.get("id") or "", **_back_args(plan_date))


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

    # Attach the click-through target to every row. Done here rather than in
    # the template so the three date conventions stay in one place.
    for _p in placed:
        _p["href"] = _link_event(_p.get("raw") or {}, plan_date)
    for _e in untimed:
        _e["href"] = _link_event(_e, plan_date)
    for _t in tasks:
        _t["href"] = _link_task(_t, plan_date)
    # Every day links now: the checklist takes ?date= and shows that day
    # read-only when it is not today.
    for _c in checklist:
        _c["href"] = _link_checklist(_c, plan_date)

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

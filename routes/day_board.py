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
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from flask import Blueprint, jsonify, render_template, request, session, url_for

from services.login_service import login_required
from services import checklist_schedule
from services import streak as streak_service, event_recurrence, loud
from supabase_client import get, update
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


#: The day, cut where its shape actually changes. Asked for as
#: before 8 / 8-12 / 12-18 / after 6, which is the rhythm of a working day
#: rather than an even split.
#:
#: Ordered EARLIEST FIRST, with the untimed band last: something with no
#: time is not "before dawn", it is "whenever", and putting it at the top
#: would make the first thing on the board the least urgent thing on it.
CHECKLIST_BANDS = (
    ("early",     "Before 8am",  0,    8 * 60),
    ("morning",   "8am – 12pm",  8 * 60,  12 * 60),
    ("afternoon", "12pm – 6pm",  12 * 60, 18 * 60),
    ("evening",   "After 6pm",   18 * 60, 24 * 60),
)


def _band_checklist(rows):
    """Group checklist rows into the four bands, plus an untimed one.

    Empty bands are dropped rather than rendered as headings over nothing —
    this board's whole constraint is that it fits on one screen, and four
    labels for two items is the opposite of that.
    """
    buckets = {key: [] for key, _l, _s, _e in CHECKLIST_BANDS}
    untimed = []
    for r in rows:
        at = r.get("at")
        if not at or ":" not in at:
            untimed.append(r)
            continue
        try:
            hh, mm = (int(x) for x in at.split(":", 1))
        except ValueError:
            untimed.append(r)
            continue
        mins = hh * 60 + mm
        for key, _label, start, end in CHECKLIST_BANDS:
            if start <= mins < end:
                buckets[key].append(r)
                break
        else:
            untimed.append(r)

    out = []
    for key, label, _s, _e in CHECKLIST_BANDS:
        # CHRONOLOGICAL, not done-last. Every other list on this board sinks
        # finished rows, but this one prints the clock time next to each
        # item — and a column of times that does not run downwards reads as
        # a bug. The strikethrough already says "done"; the order says
        # "when", and those are different jobs.
        rows_in = sorted(buckets[key],
                         key=lambda r: (r["at"] or "", r["title"].lower()))
        if rows_in:
            out.append({"key": key, "label": label, "rows": rows_in})
    if untimed:
        out.append({"key": "anytime", "label": "Any time",
                    "rows": sorted(untimed, key=lambda r: (r["done"],
                                                           r["title"].lower()))})
    # (The untimed band keeps done-last: with no clock to preserve there is
    #  no order to break, so the useful one wins.)
    return out


def _bucket_for(user_id, plan_date, is_today):
    """Quick Bucket rows that belong to THIS day.

    The board read daily_events, todo_matrix and checklist_items and simply
    never looked at the bucket — so anything captured there was invisible
    here, which is most of what actually gets typed on a given day.

    WHAT BELONGS, and it is not everything:

      * a row whose due_at falls on this date — real work with a real
        deadline, whichever bucket produced it (5m..8h, or a pinned "@1pm");
      * a "now" row, but ONLY when the board is showing today. "Now" carries
        no date, so on any other day it is not that day's business.

    WHAT DOES NOT: the FUTURE bucket. That is the backlog by definition, and
    this board's premise is one day on one screen with no scrolling — its own
    docstring says it has no room for things that are not today's business.
    /backlog is where those live.
    """
    rows = get("quick_bucket", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "select": "id,text,time_bucket,due_at,is_done,done_at,priority_label,"
                  "planned_minutes,actual_minutes",
        "limit": "1000",
    }) or []

    day = plan_date.isoformat()
    tz = user_now().tzinfo
    out = []
    for r in rows:
        bucket = (r.get("time_bucket") or "").lower()
        if bucket == "future":
            continue

        # ── FINISHED WORK BELONGS TO THE DAY IT WAS FINISHED ──────
        # A "now" row carries no date, so every one ever created landed on
        # every day's board forever. Measured 2026-08-23: 61 rows in To do,
        # 53 of them completed in May and July. The count said 8 because it
        # filtered done; the LIST did not, so the panel was 87% archive.
        # Reported as "it does not take into account completed tasks".
        #
        # Same rule the bucket page already applies: done today is today's
        # business — it is how you see what you have got through — and done
        # in May is the archive's.
        if r.get("is_done"):
            # A row with NO done_at cannot be placed, and every row the API
            # closes has carried one for months — so the unplaceable ones
            # are old and rare. Kept rather than hidden: dropping a row on a
            # guess is worse than showing one extra, and the 53 that caused
            # this all have a date.
            done_day = (r.get("done_at") or "")[:10]
            if done_day and done_day != day:
                continue

        when = None
        if r.get("due_at"):
            try:
                due = datetime.fromisoformat(
                    r["due_at"].replace("Z", "+00:00")).astimezone(tz)
            except (ValueError, TypeError):
                due = None
            if due is None or due.date().isoformat() != day:
                continue                      # a deadline on some other day
            when = due.strftime("%H:%M")
        elif not (bucket == "now" and is_today):
            continue                          # undated, and not today

        out.append({
            "id": r.get("id"),
            "title": (r.get("text") or "").strip(),
            "at": when,
            "done": bool(r.get("is_done")),
            "plan": r.get("planned_minutes") or 0,
            "spent": r.get("actual_minutes") or 0,
        })

    # Timed first and in time order, then the undated "now" ones; done sinks,
    # matching how the task column already reads.
    out.sort(key=lambda x: (x["done"], x["at"] is None, x["at"] or "",
                            x["title"].lower()))
    return [x for x in out if x["title"]]


def _checklist_for(user_id, plan_date):
    """Today's checklist with its tick state.

    Weekly/one-off items that do not fall on this date are dropped here rather
    than rendered greyed out — a board has no room for things that are not
    today's business.
    """
    day_str = plan_date.isoformat()

    items = get("checklist_items", params={
        "user_id": f"eq.{user_id}", "is_deleted": "eq.false",
        "order": "position.asc,created_at.asc",
    }) or []

    # WAS WRONG, and measurably so. This used to have no branch for
    # `weekdays` or `weekends`, so both fell through to "show it" and those
    # items appeared on the board every day of the week — three weekday
    # items and one weekend item, on all seven days. It also compared
    # `custom` days as three-letter names ("mon") when they are stored as
    # numbers (Sun=0..Sat=6), so a custom schedule matched nothing.
    #
    # The schedule logic now lives in one place, shared with the push
    # scheduler that decides whether a reminder actually fires. A board
    # disagreeing with the reminder is worse than either being wrong alone.
    before = len(items)
    items = [i for i in items if checklist_schedule.is_due(i, plan_date)]
    if before and not items:
        # Every item filtered out is possible (a weekend with only weekday
        # items) but it is also exactly what a broken schedule rule looks
        # like — which is what the previous version of this filter did for
        # `custom` schedules, silently, for months.
        loud.bailed("day board checklist", "every item was filtered out as "
                                           "not due",
                    date=plan_date.isoformat(), had=before)

    ticks = get("checklist_ticks", params={
        "user_id": f"eq.{user_id}", "tick_date": f"eq.{day_str}",
    }) or []
    ticked = {t["item_id"] for t in ticks}

    # Ticks are keyed by (item, reminder_time). An item with three reminders
    # is settled three times a day, independently — the checklist page has
    # always worked that way and the board must agree.
    ticked_at = {}
    for t in ticks:
        ticked_at.setdefault(t.get("item_id"), set()).add(t.get("reminder_time"))

    times = get("checklist_reminder_times", params={
        "user_id": f"eq.{user_id}",
        "select": "item_id,reminder_time",
        "order": "reminder_time.asc",
        "limit": "1000",
    }) or []
    times_by_item = {}
    for t in times:
        times_by_item.setdefault(t["item_id"], []).append(t.get("reminder_time"))

    out = []
    for i in items:
        title = i.get("title") or i.get("name") or i.get("text")
        if not title:
            continue
        item_ticks = ticked_at.get(i.get("id"), set())
        # A legacy whole-item tick predates reminder times and still counts —
        # configuring a reminder later cannot un-tick a day already ticked.
        legacy_done = None in item_ticks

        stamps = times_by_item.get(i.get("id")) or []
        if not stamps:
            stamps = [i.get("reminder_time")] if i.get("reminder_time") else [None]

        # ONE ROW PER REMINDER. "Drink water" at 08:00 and 11:00 is two
        # things to do, and a board that showed it once would be telling you
        # the day is smaller than it is.
        for stamp in stamps:
            hhmm = (stamp or "")[:5] or None
            out.append({
                "id": i.get("id"),
                "title": title,
                "at": hhmm,
                "done": legacy_done or (stamp in item_ticks),
            })
    return out


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
            # Completed events are struck through rather than hidden. A
            # board is a record of the day as well as a plan for it, and a
            # done item vanishing makes a full morning look empty.
            "done": (e.get("status") or "open") == "done" or bool(e.get("is_done")),
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


#: description fragment -> (bank page, human label). The prep scheduler
#: writes "{label} — open the topic at {page}" into the calendar row it
#: creates, and the bulk one writes "Open them at {page}". Both name the
#: page, which is the only durable thing to match on: the TITLE is the
#: topic itself and tells you nothing about which bank it came from.
_PREP_PAGES = ("/ai-sde", "/interview-prep", "/java", "/sql")


def _prep_target(item):
    """If this row came from a prep bank, the page it belongs to.

    Returns None for an ordinary calendar entry. Longest paths are checked
    first so "/interview-prep" is not swallowed by a shorter match.
    """
    text = (item.get("description") or "")
    if not text:
        return None
    for page in sorted(_PREP_PAGES, key=len, reverse=True):
        if page in text:
            return page
    return None


def _link_event(item, plan_date):
    """An event opens the day view for the date it belongs to.

    The focus id is PREFIXED "ev-" because that is what the day view calls
    its event rows (agenda_service builds them as f"ev-{row id}"). Sending
    the raw row id would land on the right page with nothing highlighted,
    which looks like the link is broken rather than like the row is gone.
    """
    # A PREP TOPIC GOES TO ITS BANK, not to the day view. Clicking
    # "SELECT ... WHERE" on the board should open that topic on /sql — the
    # day view would only show the same one-line title you just clicked,
    # which is a round trip to no new information.
    page = _prep_target(item)
    if page:
        title = (item.get("title") or "").strip()
        args = dict(_back_args(plan_date))
        if title:
            args["topic"] = title
        return page + "?" + urlencode(args)

    raw_id = item.get("id")
    focus = f"ev-{raw_id}" if raw_id else ""
    return url_for("day.day_page", date=plan_date.isoformat(),
                   focus=focus, **_back_args(plan_date))


def _parse_prep(text):
    """(bank, topic) if this bucket line was written by a prep bank.

    Imported lazily and never allowed to raise: routes.interview_prep pulls
    in every question bank, and the board must render even if one of them
    fails to import.
    """
    try:
        from routes.interview_prep import parse_bucket_text
        return parse_bucket_text(text)
    except Exception:
        logger.warning("day board: prep parse failed", exc_info=True)
        return (None, None)


def _prep_bank_spec(bank):
    try:
        from routes.interview_prep import PREP_BANKS
        return PREP_BANKS.get(bank) or {}
    except Exception:
        return {}


def _link_bucket(item, plan_date):
    """A bucket row opens the Quick Bucket — unless a bank wrote it.

    Reported as "todo when i click it goes to quick bucket instead of AISDE
    Prep link etc. It should go to the place where details are there".

    Every bucket row used to link to /quick-bucket. For a scheduled prep
    topic that is a page showing the same one line that was just clicked;
    the answer to "what is this and what do I do with it" is in the bank.
    This is the rule events have followed since the click-through work —
    bucket rows were simply never given it.
    """
    bank, topic = _parse_prep(item.get("title"))
    page = _prep_bank_spec(bank).get("page") if bank else None
    if page:
        args = dict(_back_args(plan_date))
        if topic:
            args["topic"] = topic
        return page + "?" + urlencode(args)
    # POINTED AT THE ROW, not just the page. Reported as "if i click a item
    # in dayboard which belongs to quickbucket it does go to quickbucket but
    # not to the specific item which i clicked". The bucket is long enough
    # that landing at the top of it is barely better than not linking at
    # all — you still have to find the thing you were already looking at.
    return url_for("quick_bucket.quick_bucket_page",
                   focus=item.get("id") or "", **_back_args(plan_date))


def _quote_of_day(plan_date):
    """One quote, and the SAME one all day.

    Picked by date rather than at random: a line that changes every time
    the board refreshes itself is wallpaper, and you stop reading it by
    lunchtime. One a day is something you can actually carry around.
    """
    try:
        rows = get("quotes", params={
            "is_active": "eq.true", "select": "text,author",
            "order": "id.asc", "limit": "500",
        }) or []
    except Exception:
        logger.warning("day board: quote read failed", exc_info=True)
        return None
    rows = [r for r in rows if (r.get("text") or "").strip()]
    if not rows:
        return None
    return rows[plan_date.toordinal() % len(rows)]


def _hm(mins):
    """90 → "1h30", 45 → "45m", 120 → "2h".

    Hours once it is worth saying in hours: "135m" is a number you have to
    do arithmetic on, and this board is read at a glance from across a room.
    """
    try:
        mins = int(mins or 0)
    except (TypeError, ValueError):
        return ""
    if mins <= 0:
        return ""
    if mins < 60:
        return "%dm" % mins
    h, m = divmod(mins, 60)
    return "%dh" % h if not m else "%dh%02d" % (h, m)


def _display_name(user_id):
    """The name to greet, or "" — never an exception and never an email.

    Falls back to the part of the address before the @, because "Hello
    venghatesh@gmail.com" is worse than no greeting at all.
    """
    try:
        rows = get("users", params={
            "id": f"eq.{user_id}", "select": "display_name,email", "limit": "1",
        }) or []
    except Exception:
        return ""
    if not rows:
        return ""
    name = (rows[0].get("display_name") or "").strip()
    if not name:
        name = (rows[0].get("email") or "").split("@", 1)[0].strip()
    # First name only: this is a greeting, not an address label.
    return name.split()[0][:24] if name else ""


def _greeting_word(now):
    h = now.hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def _appreciation(chain, is_today):
    """One true sentence about how this person is actually doing.

    DERIVED FROM THE DATA, NEVER INVENTED. Generic praise on a board that
    can see you did nothing for a week is worse than silence — it tells you
    the app is not really looking, and then nothing it says counts. Every
    branch below is a fact the chain already computed, and the last one
    admits there is nothing yet rather than dressing it up.
    """
    if not chain or not chain.get("ok"):
        return ""
    if not is_today:
        return ""

    streak = chain.get("streak") or 0
    today_n = chain.get("today") or 0
    best = chain.get("best") or 0
    active = chain.get("active") or 0
    window = chain.get("window") or 30
    bar = chain.get("bar") or 5

    if streak >= 2 and chain.get("met"):
        line = f"{streak} days running, and today is already done."
        if streak >= best and best > 1:
            line += " That is your best run yet."
        return line
    if chain.get("met"):
        return f"Today is done \u2014 {today_n} finished, past the bar of {bar}."
    if streak >= 2:
        return (f"{streak} days running. {bar - today_n} more today keeps it "
                f"alive.")
    if today_n > 0:
        return (f"{today_n} done so far today. "
                f"{bar - today_n} more and the day counts.")
    if active > 0:
        return (f"You showed up on {active} of the last {window} days. "
                f"Today is one of them if you want it.")
    return f"Nothing yet today. {bar} things starts a chain."


def _performance(chain):
    """The last seven days, as the board's own numbers.

    Reuses the chain's tally rather than querying again — it already counts
    exactly what "done" means here, and a second definition of done is how
    two screens end up disagreeing about the same day.
    """
    if not chain or not chain.get("ok"):
        return None
    days = list(reversed((chain.get("days") or [])[:7]))   # oldest → newest
    if not days:
        return None
    bar = chain.get("bar") or 5
    counts = [d.get("n") or 0 for d in days]
    total = sum(counts)
    hit = sum(1 for n in counts if n >= bar)
    peak = max(counts) if counts else 0
    return {
        "days": [{"date": d.get("date"), "n": d.get("n") or 0,
                  "met": (d.get("n") or 0) >= bar,
                  # Height as a percentage of the best day, so a quiet week
                  # still reads as a shape rather than a flat line.
                  "pct": int(round((d.get("n") or 0) * 100.0 / peak)) if peak else 0,
                  "label": (d.get("date") or "")[-2:]}
                 for d in days],
        "total": total,
        "hit": hit,
        "peak": peak,
        "avg": round(total / float(len(counts)), 1) if counts else 0,
        "bar": bar,
        "streak": chain.get("streak") or 0,
        "best": chain.get("best") or 0,
    }


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
    checklist_bands = _band_checklist(checklist)
    # THE CHAIN. Derived, never written, and never allowed to break the
    # board — compute() swallows its own failures and returns ok=False.
    chain = streak_service.compute(user_id, plan_date)
    bucket = _bucket_for(user_id, plan_date, plan_date == user_today())

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
    open_bucket = [b for b in bucket if not b["done"]]

    # ── HOW THE DAY IS GOING, not just what is left ───────────────────
    # "dayboard should highlight how i am progressing." A count of what
    # remains is the same number whether you have done nothing or nine
    # things, which is exactly the wrong signal on a day you are winning.
    done_tasks = len(tasks) - len(open_tasks)
    done_bucket = len(bucket) - len(open_bucket)
    done_checks = sum(1 for c in checklist if c["done"])
    done_now = done_tasks + done_bucket + done_checks
    total_now = len(tasks) + len(bucket) + len(checklist)
    # ── EFFORT, PLANNED AGAINST SPENT ─────────────────────────────────
    # "in dayboard we should show the planned hours in bracket and how much
    # we have spent etc." Only the bucket carries these figures; the
    # Eisenhower rows have no effort columns at all, so the totals say what
    # they cover rather than implying they cover the day.
    plan_total = sum(b.get("plan") or 0 for b in bucket)
    spent_total = sum(b.get("spent") or 0 for b in bucket)
    for _b in bucket:
        _b["plan_h"] = _hm(_b.get("plan"))
        _b["spent_h"] = _hm(_b.get("spent"))
    effort = {
        "plan": _hm(plan_total),
        "spent": _hm(spent_total),
        "over": bool(plan_total and spent_total > plan_total),
    } if (plan_total or spent_total) else None

    progress = {
        "done": done_now,
        "total": total_now,
        "left": total_now - done_now,
        "pct": int(round(done_now * 100.0 / total_now)) if total_now else 0,
    }
    for _b in bucket:
        _b["href"] = _link_bucket(_b, plan_date)
        # "AISDEPrep — Two-pointer technique" is a ROUTING prefix, and it is
        # repeated on every prep row. On a board whose whole constraint is
        # one screen, it spends the width that the actual topic needs. The
        # bank is shown as a short chip instead, where it reads as a
        # category rather than as part of the title.
        _bank, _topic = _parse_prep(_b.get("title"))
        if _bank and _topic:
            _b["title"] = _topic
            _b["prep"] = _prep_bank_spec(_bank).get("label") or ""

    # Attach the click-through target to every row. Done here rather than in
    # the template so the three date conventions stay in one place.
    for _p in placed:
        _p["href"] = _link_event(_p.get("raw") or {}, plan_date)
    for _e in untimed:
        _e["href"] = _link_event(_e, plan_date)
        _e["done"] = (_e.get("status") or "open") == "done" or bool(_e.get("is_done"))
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
        bucket=bucket, open_bucket_count=len(open_bucket),
        checklist=checklist, checklist_bands=checklist_bands, chain=chain,
        checklist_done=sum(1 for c in checklist if c["done"]),
        now_pct=now_pct,
        greeting=_greeting_word(now),
        display_name=_display_name(user_id),
        appreciation=_appreciation(chain, is_today),
        perf=_performance(chain),
        progress=progress,
        effort=effort,
        quote=_quote_of_day(plan_date),
        refresh=refresh,
        theme=(request.args.get("theme") or "dark").lower(),
    )


_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@day_board_bp.route("/api/day-board/task-time", methods=["POST"])
@login_required
def set_task_time():
    """Tag a to-do with a time, from the board itself.

    The board already SHOWED task_time and already sorted by it, but the
    only place to put one there was the matrix page — so the column that
    decides where a task sits in the day could not be set while looking at
    the day. Asked for as "tag time in to do in day board".

    An empty string CLEARS it. That has to be reachable: a time tagged by
    mistake is otherwise permanent, and a wrong time is worse than none
    because the board sorts by it.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    task_id = data.get("id")
    raw = (data.get("time") or "").strip()

    if not task_id:
        return jsonify({"error": "id required"}), 400
    if raw and not _HHMM.match(raw):
        return jsonify({"error": "Time must be HH:MM"}), 400

    rows = get("todo_matrix", params={
        "id": f"eq.{task_id}",
        "user_id": f"eq.{user_id}",
        "select": "id",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404

    try:
        update("todo_matrix",
               {"id": f"eq.{task_id}", "user_id": f"eq.{user_id}"},
               {"task_time": raw or None})
    except Exception:
        logger.exception("day board: could not set task_time")
        return jsonify({"error": "Could not save the time"}), 502

    return jsonify({"status": "ok", "task_time": raw or None})

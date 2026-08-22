"""Tests for the Day Board.

The board makes one promise — everything for the day fits on one screen with
no scrolling — and these guard the parts of that promise the server is
responsible for. The other half (shrink-to-fit) lives in the page's script and
is exercised by the layout maths here: if the server hands the template
overlapping or out-of-range geometry, no amount of client-side fitting saves it.
"""
import datetime as dt

import jinja2
import pytest

import routes.day_board as db


# ── time parsing ────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("9", dt.time(9, 0)),
    ("9:30", dt.time(9, 30)),
    ("09:30", dt.time(9, 30)),
    ("0930", dt.time(9, 30)),
    ("23:59", dt.time(23, 59)),
    ("", None),
    (None, None),
    ("nonsense", None),
])
def test_parse_hhmm(raw, expected):
    assert db._parse_hhmm(raw) == expected


def test_parse_hhmm_uses_fallback():
    assert db._parse_hhmm(None, dt.time(7, 0)) == dt.time(7, 0)
    assert db._parse_hhmm("bad", dt.time(7, 0)) == dt.time(7, 0)


# ── layout geometry ─────────────────────────────────────────────────────
WINDOW = (dt.time(8, 0), dt.time(18, 0))


def _place(events, window=WINDOW):
    return db._layout_events(events, *window)


def test_events_are_positioned_inside_the_window():
    placed = _place([
        {"title": "a", "start_time": "09:00", "end_time": "10:00"},
        {"title": "b", "start_time": "16:00", "end_time": "17:30"},
    ])
    assert len(placed) == 2
    for p in placed:
        assert p["top"] >= 0
        assert p["top"] + p["height"] <= 100.0001, "an event must not run off the rail"


def test_overlapping_events_get_separate_lanes():
    """Two things at once must sit SIDE BY SIDE. Stacked, the board is
    unreadable at a glance, which is the only thing it is for."""
    placed = _place([
        {"title": "standup", "start_time": "09:00", "end_time": "09:15"},
        {"title": "review", "start_time": "09:00", "end_time": "10:30"},
    ])
    assert {p["lane"] for p in placed} == {0, 1}
    assert all(p["lane_count"] == 2 for p in placed)


def test_sequential_events_reuse_one_lane():
    """Non-overlapping events must NOT each claim a lane — otherwise a busy
    day shrinks every event to a sliver for no reason."""
    placed = _place([
        {"title": "a", "start_time": "09:00", "end_time": "10:00"},
        {"title": "b", "start_time": "10:00", "end_time": "11:00"},
        {"title": "c", "start_time": "11:00", "end_time": "12:00"},
    ])
    assert all(p["lane"] == 0 for p in placed)
    assert all(p["lane_count"] == 1 for p in placed)


def test_untimed_events_are_excluded_from_the_rail():
    """An event with no start time has nowhere to go on a timeline; the route
    routes it to the task column instead."""
    placed = _place([{"title": "someday"}])
    assert placed == []


def test_events_outside_the_window_are_dropped():
    placed = _place([{"title": "midnight", "start_time": "02:00", "end_time": "03:00"}])
    assert placed == []


def test_events_are_clipped_to_the_window_not_dropped():
    """An event that starts before the window but runs into it must still
    appear — truncated, not vanished."""
    placed = _place([{"title": "early", "start_time": "07:00", "end_time": "09:00"}])
    assert len(placed) == 1
    assert placed[0]["top"] == pytest.approx(0.0)
    assert placed[0]["height"] > 0


def test_zero_length_events_get_a_minimum_height():
    """A 0-minute or missing-end event would otherwise render as an invisible
    hairline."""
    placed = _place([{"title": "ping", "start_time": "09:00", "end_time": "09:00"}])
    assert len(placed) == 1
    assert placed[0]["height"] > 0.5


def test_missing_end_time_defaults_to_a_slot():
    placed = _place([{"title": "no end", "start_time": "09:00"}])
    assert len(placed) == 1
    assert placed[0]["height"] > 0


# ── the template actually renders ───────────────────────────────────────
@pytest.fixture
def rendered():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                             autoescape=True)
    env.globals["url_for"] = lambda *a, **k: "#"
    placed = _place([
        {"title": "Standup", "start_time": "09:00", "end_time": "09:15"},
        {"title": "Design review", "start_time": "09:00", "end_time": "10:30"},
    ])
    for p in placed:
        p["is_now"] = False
    return env.get_template("day_board.html").render(
        plan_date=dt.date(2026, 8, 16), is_today=True, date_label="Sun 16 Aug",
        prev_date="2026-08-15", next_date="2026-08-17",
        hours=[dt.time(h, 0) for h in range(8, 19)],
        win_start=dt.time(8, 0), win_end=dt.time(18, 0),
        placed=placed, untimed=[{"title": "No time set"}],
        tasks=[{"task_text": "Ship the board", "quadrant": "Q1",
                "is_done": False, "task_time": "11:00"}],
        open_task_count=1,
        # Quick Bucket rows land in the same column as the tasks. The board
        # never read the bucket at all until this was added, so anything
        # captured there was invisible on the screen meant to show the day.
        bucket=[{"id": "b1", "title": "Call the bank", "at": "14:00",
                 "done": False, "href": "#"}],
        open_bucket_count=1,
        checklist=[{"id": 1, "title": "Meds", "at": "21:00", "done": True}],
        checklist_bands=db._band_checklist(
            [{"id": 1, "title": "Meds", "at": "21:00", "done": True}]),
        checklist_done=1, now_pct=45.0, refresh=120, theme="dark")


def test_template_renders_all_three_panels(rendered):
    assert "Design review" in rendered        # calendar
    assert "Ship the board" in rendered       # tasks
    assert "Meds" in rendered                 # checklist
    assert "No time set" in rendered          # untimed events land in tasks
    assert "Call the bank" in rendered        # and Quick Bucket rows
    # The heading counts every outstanding thing in the column, not just the
    # matrix tasks — a "1" over a list of two reads as a bug.
    assert ">2<" in rendered.split("To do")[1][:80]


def test_template_cannot_scroll(rendered):
    """The no-scroll contract is the whole point — if this assertion ever
    fails, the board has quietly become just another scrolling page."""
    assert "overflow:hidden" in rendered.replace(" ", "")
    assert "100dvh" in rendered


def test_template_has_the_fit_hooks(rendered):
    """The shrink-to-fit script keys off these; without them the page silently
    stops adapting and starts clipping."""
    assert "data-fit" in rendered
    assert "--u" in rendered
    assert 'class="more"' in rendered         # the honest-truncation counter


def test_template_escapes_titles():
    """Event titles are user input and land in an HTML attribute-adjacent
    context."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                             autoescape=True)
    env.globals["url_for"] = lambda *a, **k: "#"
    placed = _place([{"title": "<script>alert(1)</script>",
                      "start_time": "09:00", "end_time": "10:00"}])
    for p in placed:
        p["is_now"] = False
    html = env.get_template("day_board.html").render(
        plan_date=dt.date(2026, 8, 16), is_today=False, date_label="Sun 16 Aug",
        prev_date="2026-08-15", next_date="2026-08-17",
        hours=[dt.time(9, 0)], win_start=dt.time(8, 0), win_end=dt.time(18, 0),
        placed=placed, untimed=[], tasks=[], open_task_count=0,
        bucket=[], open_bucket_count=0,
        checklist=[], checklist_bands=[], checklist_done=0, now_pct=None,
        refresh=0, theme="dark")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_header_carries_the_navigation_controls(rendered):
    """The board is a kiosk with no nav, so these three ARE the navigation:
    a way out, a way to step days, and a way to jump to any day. Losing any
    one of them strands whoever tapped in from the menu."""
    assert 'href="/summary?view=daily"' in rendered      # a way back to the menu
    assert 'id="prev"' in rendered and 'id="next"' in rendered
    assert 'type="date"' in rendered                     # jump to any day
    assert 'id="pick"' in rendered


def test_today_button_only_appears_when_not_on_today():
    """A "Today" button while already on today is noise on a screen that has
    no room for noise."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                             autoescape=True)
    env.globals["url_for"] = lambda *a, **k: "#"

    def render(is_today):
        return env.get_template("day_board.html").render(
            plan_date=dt.date(2026, 8, 16), is_today=is_today,
            date_label="Sun 16 Aug", prev_date="2026-08-15",
            next_date="2026-08-17", hours=[dt.time(9, 0)],
            win_start=dt.time(8, 0), win_end=dt.time(18, 0),
            placed=[], untimed=[], tasks=[], open_task_count=0,
            bucket=[], open_bucket_count=0,
            checklist=[], checklist_bands=[], checklist_done=0, now_pct=None,
            refresh=0,
            theme="dark")

    assert 'id="today"' not in render(True)
    assert 'id="today"' in render(False)


def test_day_navigation_preserves_other_query_params(rendered):
    """Stepping to tomorrow must not silently drop a pinned ?from/?to window
    or a chosen theme — a setting that quietly resets feels broken."""
    assert "URLSearchParams(location.search)" in rendered
    assert 'p.set("date"' in rendered


def test_blueprint_is_registered(app):
    """Uses conftest's `app` fixture rather than `import app`.

    There is an old copy of this project one directory up with its own
    app.py, and a bare `import app` from a test picks THAT one up — it is
    stale enough to fail on an import removed months ago. conftest already
    prunes the parent from sys.path for exactly this reason; going through
    the fixture is how you get the benefit of that.
    """
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/day-board" in rules
    assert "/board" in rules


# ── the notification summary ────────────────────────────────────────────
from unittest.mock import patch


def _summary(events, tasks, checklist, minutes):
    with patch.object(db, "_events_for", return_value=events), \
         patch.object(db, "_tasks_for", return_value=tasks), \
         patch.object(db, "_checklist_for", return_value=checklist):
        return db.build_summary("u", dt.date(2026, 8, 16), now_minutes=minutes)


EVENTS = [
    {"title": "Standup", "start_time": "09:00", "end_time": "09:15"},
    {"title": "Design review", "start_time": "14:00", "end_time": "15:30"},
]
TASKS = [{"task_text": "Ship it", "quadrant": "Q1", "is_done": False}]
CHECK = [{"id": 1, "title": "Meds", "done": True},
         {"id": 2, "title": "Walk", "done": False}]


def test_summary_leads_with_what_is_happening_now():
    s = _summary(EVENTS, TASKS, CHECK, 9 * 60 + 5)
    assert s["title"] == "Now: Standup"


def test_summary_leads_with_what_is_next():
    s = _summary(EVENTS, TASKS, CHECK, 8 * 60 + 30)
    assert s["title"] == "Next in 30m: Standup"


def test_summary_uses_a_clock_time_when_the_next_thing_is_far_off():
    """'in 315m' is not a useful thing to read on a lock screen."""
    s = _summary(EVENTS, TASKS, CHECK, 10 * 60)
    assert s["title"] == "Next at 14:00: Design review"


def test_summary_title_says_what_is_LEFT_once_the_events_are_over():
    """'2 events today' at 6pm is a fact about the past and answers nothing."""
    s = _summary(EVENTS, TASKS, CHECK, 18 * 60)
    assert s["title"] == "1 to do"


def test_summary_says_day_clear_when_nothing_remains():
    s = _summary(EVENTS, [{"task_text": "x", "is_done": True}],
                 [{"id": 1, "title": "Meds", "done": True}], 18 * 60)
    assert s["title"] == "Day clear"


def test_summary_body_is_capped_to_three_lines():
    """A notification body is a glance, not a list. Android truncates anyway;
    choosing WHAT to drop is better than letting the OS choose."""
    many = [{"task_text": f"task {i}", "quadrant": "Q1", "is_done": False}
            for i in range(20)]
    s = _summary(EVENTS, many, CHECK, 8 * 60)
    assert len(s["body"].split("\n")) <= 3


def test_summary_counts_overflow_rather_than_hiding_it():
    many = [{"task_text": f"task {i}", "quadrant": "Q1", "is_done": False}
            for i in range(5)]
    s = _summary([], many, [], 8 * 60)
    assert "(+3)" in s["body"], "must say how many tasks were not listed"


def test_summary_never_counts_done_tasks_as_outstanding():
    tasks = [{"task_text": "done one", "is_done": True},
             {"task_text": "open one", "is_done": False}]
    s = _summary([], tasks, [], 8 * 60)
    assert s["counts"]["open_tasks"] == 1
    assert "done one" not in s["body"]


# ── the pinned notification's refresh logic ─────────────────────────────
def test_signature_ignores_changes_the_user_would_not_see():
    """The scheduler refreshes on CONTENT CHANGE rather than on a timer, so
    the signature must track exactly what is rendered — no more, no less."""
    a = {"title": "Now: Standup", "body": "To do: x"}
    b = {"title": "Now: Standup", "body": "To do: x"}
    c = {"title": "Now: Standup", "body": "To do: y"}
    assert db.signature(a) == db.signature(b)
    assert db.signature(a) != db.signature(c)


def test_signature_is_stable_across_calls():
    s = {"title": "t", "body": "b"}
    assert db.signature(s) == db.signature(s)


def test_ambient_flags_never_alert():
    """A notification that refreshes itself must not buzz. If any of these
    flips, the pin becomes unusable within a day and the user turns off
    notifications for the whole app."""
    assert db.AMBIENT["silent"] is True
    assert db.AMBIENT["renotify"] is False
    assert db.AMBIENT["vibrate"] == []
    assert db.AMBIENT["requireInteraction"] is True


def test_pin_uses_one_replaceable_tag():
    """Without a stable tag every refresh stacks a new row in the shade."""
    assert db.PIN_TAG == "day-board"


def test_scheduler_refresh_respects_the_window_and_signature():
    """Exercise the scheduler's decision logic directly: it must stay silent
    when nothing has changed, and speak when something has."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from unittest.mock import patch
    import services.push_scheduler as ps

    tz = ZoneInfo("Asia/Kolkata")
    summary = {"title": "Now: Standup", "body": "x", "counts": {}}
    sig = db.signature(summary)

    def run(pin_row, hour):
        sent = []
        with patch.object(ps, "get", return_value=[pin_row]), \
             patch.object(ps, "update") as upd, \
             patch.object(db, "build_summary", return_value=summary), \
             patch.object(db, "send_pin",
                          side_effect=lambda u, s: (sent.append(s), (1, 0))[1]):
            ps._refresh_day_board_pins(
                "u", datetime(2026, 8, 16, hour, 0, tzinfo=tz))
        return sent, upd

    base = {"user_id": "u", "is_active": True, "start_hour": 7,
            "end_hour": 22, "min_interval_minutes": 10,
            "last_signature": sig, "last_sent_at": None,
            "pinned_date": "2026-08-16"}

    # unchanged content, inside the window -> stays quiet
    sent, _ = run(dict(base), 10)
    assert sent == [], "an unchanged day must not push a notification"

    # content changed -> sends
    sent, _ = run(dict(base, last_signature="something-else"), 10)
    assert len(sent) == 1

    # outside the window -> silent even though the content changed
    sent, _ = run(dict(base, last_signature="something-else"), 3)
    assert sent == [], "must not refresh at 3am"

    # a new day forces a send even when the text matches yesterday's
    sent, _ = run(dict(base, pinned_date="2026-08-15"), 8)
    assert len(sent) == 1, "the first refresh of a new morning must land"


# ── CHECKLIST TIME BANDS ───────────────────────────────────────────────
# Asked for 2026-08-22: prefix each checklist row with its time and split
# the day at 8am / noon / 6pm "so that easy to visualise the day board
# items". Banding is pure, so it is tested directly.

def _row(title, at, done=False):
    return {"id": title, "title": title, "at": at, "done": done}


def test_bands_run_earliest_first_with_untimed_last():
    bands = db._band_checklist([
        _row("Ram", None), _row("Brush", "22:00"), _row("Wake", "06:00"),
        _row("Water", "08:00"), _row("Rent", "12:12"),
    ])
    assert [b["label"] for b in bands] == [
        "Before 8am", "8am – 12pm", "12pm – 6pm", "After 6pm", "Any time"]


def test_band_boundaries_are_inclusive_at_the_start():
    """08:00 is the morning, not before it; 12:00 is afternoon; 18:00 evening.

    The off-by-one at a boundary is the only interesting bug in a banding
    function, and it is invisible on a screen until the one day an item
    sits exactly on the hour.
    """
    for at, label in (("07:59", "Before 8am"), ("08:00", "8am – 12pm"),
                      ("11:59", "8am – 12pm"), ("12:00", "12pm – 6pm"),
                      ("17:59", "12pm – 6pm"), ("18:00", "After 6pm"),
                      ("23:59", "After 6pm")):
        bands = db._band_checklist([_row("x", at)])
        assert bands[0]["label"] == label, f"{at} landed in {bands[0]['label']}"


def test_empty_bands_are_dropped_not_rendered_as_headings_over_nothing():
    bands = db._band_checklist([_row("x", "09:00")])
    assert len(bands) == 1


def test_banding_never_loses_a_row():
    rows = [_row(f"i{n}", t) for n, t in enumerate(
        ["00:01", "08:00", "12:00", "18:00", None, "zz", ""])]
    bands = db._band_checklist(rows)
    assert sum(len(b["rows"]) for b in bands) == len(rows)


def test_unparseable_time_falls_into_any_time_rather_than_vanishing():
    bands = db._band_checklist([_row("x", "not-a-time")])
    assert bands[0]["label"] == "Any time"


def test_rows_within_a_band_stay_in_clock_order_even_when_done():
    """Done rows must NOT sink here.

    Every other list on this board sinks finished work, but this one prints
    the time beside each row — a column of times that does not run downwards
    reads as a rendering bug, so the strikethrough carries "done" instead.
    """
    bands = db._band_checklist([
        _row("late", "22:30", done=True), _row("early", "21:00", done=False),
    ])
    assert [r["title"] for r in bands[0]["rows"]] == ["early", "late"]


def test_board_renders_the_time_prefix_and_band_headings():
    bands = db._band_checklist([_row("Wake", "06:00"), _row("Ram", None)])
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                             autoescape=True)
    env.globals["url_for"] = lambda *a, **k: "#"
    html = env.get_template("day_board.html").render(
        plan_date=dt.date(2026, 8, 22), prev_date=dt.date(2026, 8, 21),
        next_date=dt.date(2026, 8, 23), is_today=True,
        win_start=dt.time(6, 0), win_end=dt.time(23, 0),
        placed=[], untimed=[], tasks=[], open_task_count=0,
        bucket=[], open_bucket_count=0,
        checklist=[], checklist_bands=bands, checklist_done=0,
        now_pct=None, refresh=0, theme="dark")
    assert 'class="band"' in html
    assert "Before 8am" in html and "Any time" in html
    assert ">06:00<" in html            # the time actually prefixes the row
    assert ">··<" in html               # ...and untimed rows say so

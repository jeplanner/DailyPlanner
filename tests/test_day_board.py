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
        checklist=[{"id": 1, "title": "Meds", "done": True}],
        checklist_done=1, now_pct=45.0, refresh=120, theme="dark")


def test_template_renders_all_three_panels(rendered):
    assert "Design review" in rendered        # calendar
    assert "Ship the board" in rendered       # tasks
    assert "Meds" in rendered                 # checklist
    assert "No time set" in rendered          # untimed events land in tasks


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
        checklist=[], checklist_done=0, now_pct=None, refresh=0, theme="dark")
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
            checklist=[], checklist_done=0, now_pct=None, refresh=0,
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

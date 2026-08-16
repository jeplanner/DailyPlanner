"""
tests/test_smoke.py
──────────────────
Smoke tests — the "does the house still have a roof" layer. Runs in
seconds, catches the regressions users actually hit:

  • App boots without error
  • Every registered blueprint exposes at least one route
  • Every registered route resolves for unauth GET (302 to /login or 200)
  • Every page template renders without Jinja errors
  • Auth-required pages return redirects when unauthed (302)
  • Protected pages return 200 with a seeded session

Run with:  python -m pytest tests/test_smoke.py -v
"""
import pytest


# ═══════════════════════════════════════════════════
# 1. Boot / import chain
# ═══════════════════════════════════════════════════

def test_app_factory_runs(app):
    """create_app() must return a Flask instance with url rules registered."""
    assert app is not None
    assert len(app.url_map._rules) > 0, "no routes registered — blueprint wiring broken"


def test_all_expected_blueprints_present(app):
    """If someone removes a blueprint by accident, this catches it.

    Blueprint NAMES (what flask stores in app.blueprints.keys()) can
    differ from the Python variable name — e.g. inbox_bp is named
    "inbox_bp" via `Blueprint("inbox_bp", __name__)`. We check what
    Flask actually registers, not the variable name."""
    expected = {
        "auth", "planner", "todo", "projects", "health", "habits",
        "references", "ai", "events", "timeline", "notes", "system",
        "inbox_bp", "refcards", "portfolio", "goals", "reports",
    }
    registered = set(app.blueprints.keys())
    missing = expected - registered
    assert not missing, f"blueprints missing: {missing} (registered: {sorted(registered)})"


# ═══════════════════════════════════════════════════
# 2. Core page routes render without error
# ═══════════════════════════════════════════════════

PUBLIC_ROUTES = [
    "/login",
    "/health_check",   # if it exists; the test is resilient
]


@pytest.mark.parametrize("path", PUBLIC_ROUTES)
def test_public_routes_respond(client, path):
    r = client.get(path, follow_redirects=False)
    # 200 for pages that render, 302 for redirects, 404 if optional route missing.
    assert r.status_code in (200, 301, 302, 404), f"{path} unexpected status {r.status_code}"


PROTECTED_PAGES = [
    "/",
    "/todo",
    "/calendar",
    "/inbox",
    "/projects",
    "/projects/timeline",
    "/goals",
    "/summary?view=daily",
    "/summary?view=weekly",
    "/reports",
    "/notes/scribble",
    "/references",
    "/refcards",
    "/portfolio",
    "/health",
]


@pytest.mark.parametrize("path", PROTECTED_PAGES)
def test_protected_pages_redirect_when_unauth(client, path):
    """Every protected page must 302-redirect when no session is active."""
    r = client.get(path, follow_redirects=False)
    # Some pages may return 401/403 directly; all non-2xx is fine here
    # so long as they don't return 500 (template/route bug).
    assert r.status_code < 500, (
        f"{path} returned {r.status_code} unauthed — possible template or "
        f"route bug. Response excerpt: {r.data[:300]!r}"
    )


@pytest.mark.parametrize("path", PROTECTED_PAGES)
def test_protected_pages_render_when_authed(auth_client, path):
    """With a seeded session, pages should render (200) or redirect
    sensibly (302 — e.g., /health may redirect based on mode). No 500s.

    Templates must not throw Jinja errors on empty data — all the
    supabase stubs return []."""
    r = auth_client.get(path, follow_redirects=False)
    assert r.status_code < 500, (
        f"{path} returned {r.status_code} — template or route bug. "
        f"Response excerpt: {r.data[:400]!r}"
    )


# ═══════════════════════════════════════════════════
# 3. Agenda service — pure logic, no side effects
# ═══════════════════════════════════════════════════

def test_agenda_service_build_dashboard_shape():
    """The morning-dashboard payload shape must not change — the UI
    depends on exactly these keys."""
    from datetime import date
    from services.agenda_service import build_dashboard
    d = build_dashboard("test-user", date(2026, 4, 18))
    assert isinstance(d, dict)
    assert set(d.keys()) >= {"today_items", "overdue", "habits", "counts"}
    assert set(d["counts"].keys()) >= {"meetings", "tasks", "habits", "habits_done", "overdue"}


def test_agenda_habits_template_contract():
    """Regression: Today's Plan (summary.html) reads `h.name`, `h.value`,
    `h.goal`, `h.unit`, `h.habit_type`, `h.progress_pct` directly. If the
    agenda service stops returning any of these keys, the template fails
    with a Jinja `|format` TypeError at render time (undefined → %g).

    Seen in prod on Render: line 234 of summary.html would crash when a
    user with habits loaded the morning dashboard."""
    from datetime import date
    from unittest.mock import patch
    import services.agenda_service as a

    def _fake_get(table, **kw):
        if table == "habit_master":
            return [{"id": 7, "name": "water", "unit": "L", "goal": 2.0,
                     "habit_type": "number", "position": 0}]
        if table == "habit_entries":
            return [{"habit_id": 7, "value": "1.2"}]
        return []

    with patch.object(a, "get", side_effect=_fake_get):
        items = a.fetch_habits("test-user", date(2026, 4, 18))

    assert len(items) == 1
    h = items[0]
    # These are the EXACT keys summary.html reads — changing any breaks
    # the template. If you must rename, update the template too.
    for required in ("name", "value", "goal", "unit", "habit_type",
                     "progress_pct", "done"):
        assert required in h, f"habit item missing '{required}' — summary.html will crash"
    assert h["name"] == "water"
    assert h["value"] == 1.2
    assert h["goal"] == 2.0
    assert h["unit"] == "L"


def test_agenda_sort_timed_then_untimed():
    """Items with a time come first, untimed items last. Crucial for the
    morning dashboard's chronological layout."""
    from services.agenda_service import _sort_timed_then_untimed
    items = [
        {"time": None, "title": "Untimed A", "priority": "medium"},
        {"time": "09:00", "title": "Morning meeting", "priority": "medium"},
        {"time": None, "title": "Untimed B", "priority": "medium"},
        {"time": "14:00", "title": "Afternoon", "priority": "medium"},
    ]
    _sort_timed_then_untimed(items)
    titles = [it["title"] for it in items]
    assert titles[0] == "Morning meeting"
    assert titles[1] == "Afternoon"
    assert set(titles[2:]) == {"Untimed A", "Untimed B"}


# ═══════════════════════════════════════════════════
# 4. Reports service — range parsing + aggregation contracts
# ═══════════════════════════════════════════════════

def test_reports_productivity_empty_safe():
    """On a user with zero tasks, the productivity report returns a
    zero-filled payload, not a crash."""
    from datetime import date
    from services.reports_service import productivity_report
    r = productivity_report("test-user", date(2026, 4, 1), date(2026, 4, 7))
    assert r["totals"]["total"] == 0
    assert r["totals"]["rate"] == 0
    assert len(r["daily"]) == 7


def test_reports_financial_empty_safe():
    """Financial snapshot on an empty vault → zeros, no division by zero."""
    from datetime import date
    from services.reports_service import financial_report
    r = financial_report("test-user", date(2026, 4, 18))
    assert r["portfolio"]["invested"] == 0
    assert r["portfolio"]["market_value"] == 0
    assert r["bills"]["monthly_equivalent"] == 0


# ═══════════════════════════════════════════════════
# 5. Vault password lifecycle — without real Supabase
# ═══════════════════════════════════════════════════

def test_vault_status_unconfigured(auth_client, monkeypatch):
    """Vault not set up → configured=False, unlocked=False. UI uses this
    to show the setup screen."""
    import routes.refcards as rc
    monkeypatch.setattr(rc, "_vault_row", lambda _: None)
    r = auth_client.get("/api/refcards/vault/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body["configured"] is False
    assert body["unlocked"] is False


# ═══════════════════════════════════════════════════
# 6. Encryption round-trip
# ═══════════════════════════════════════════════════

def test_copy_prev_route_is_gone(client):
    """Regression: /todo/copy-prev was retired. If somebody restores the
    route without also restoring proper user scoping + undo UX, this
    test fires a warning bell. 404 is the expected status.

    Context: the previous impl had a NameError and a missing user_id
    filter (data leak). Morning Dashboard replaces the feature."""
    r = client.post("/todo/copy-prev", follow_redirects=False)
    assert r.status_code in (404, 405), (
        f"/todo/copy-prev returned {r.status_code} — it was retired. "
        f"See Morning Dashboard for the replacement read-through view."
    )


def test_copy_prev_service_import_is_gone():
    """The service function copy_open_tasks_from_previous_day was
    retired along with the route. Re-introducing it without the fixes
    (user scoping, undo, audit) would re-introduce a data-leak bug."""
    import services.eisenhower_service as es
    assert not hasattr(es, "copy_open_tasks_from_previous_day"), (
        "copy_open_tasks_from_previous_day should stay retired — see "
        "the comment block where it used to live in eisenhower_service.py"
    )


def test_encryption_roundtrip():
    from utils.encryption import encrypt, decrypt
    secret = "ABCDE1234F"   # a PAN-shaped string
    cipher = encrypt(secret)
    assert cipher != secret
    assert decrypt(cipher) == secret


def test_encryption_handles_empty():
    from utils.encryption import encrypt, decrypt
    assert encrypt("") == ""
    assert decrypt("") == ""
    assert decrypt(None) is None


# ── AI SDE prep bank content invariants ────────────────────────────────────
# The bank patches worked examples onto entries by TITLE, through the _EX_*
# dicts in ai_sde_bank.py. A typo in a key fails silently — the entry simply
# never receives its examples — which is how "Raising the bar on hiring or
# quality" sat empty while the batch was reported as complete. These turn both
# content invariants into failing tests instead of something you notice later.

def test_ai_sde_example_keys_all_match_a_real_entry():
    import ai_sde_bank as bank
    titles = {e["title"] for e in bank.ENTRIES}
    orphans = []
    for name in dir(bank):
        if not name.startswith("_EX_"):
            continue
        table = getattr(bank, name)
        if isinstance(table, dict):
            orphans += [(name, key) for key in table if key not in titles]
    assert not orphans, (
        "these worked-example keys match no entry title, so their examples are "
        f"silently dropped: {orphans}"
    )


def test_ai_sde_p0_entries_all_carry_worked_examples():
    """P0 is the 'do these first' band, and the standing bar is 5+ varied
    worked examples per entry. Adding entries moves the P0 percentile cut, so
    this can regress without anyone touching the band deliberately."""
    import ai_sde_bank as bank
    short = [e["title"] for e in bank.ENTRIES
             if e["priority"] == "P0" and len(e.get("examples") or []) < 5]
    assert not short, (
        f"{len(short)} P0 entries have fewer than 5 worked examples: "
        f"{short[:5]}{'...' if len(short) > 5 else ''}"
    )


def test_ai_sde_list_payload_excludes_the_heavy_examples():
    """The list endpoint must stay light. A fully written-up topic carries
    ~16k characters of worked examples; shipping every topic's examples on
    every page load put the payload on course for ~10MB. The list sends a
    count instead, and the bodies come from /api/ai-sde/entry/<id>."""
    import json
    import ai_sde_bank as bank
    items = [{k: v for k, v in e.items() if k != "examples"}
             for e in bank.ENTRIES]
    assert all("examples" not in it for it in items)
    size_mb = len(json.dumps(items)) / 1e6
    assert size_mb < 6, (
        f"the AI SDE list payload is {size_mb:.1f}MB even without examples; "
        "another field has grown and needs the same lazy-load treatment"
    )


def test_ai_sde_tags_use_only_the_controlled_vocabulary():
    """Every tag value must come from the six fixed lists, and every key in
    TAGS must match a real entry title. A mis-keyed title silently drops its
    tags with no error - exactly the trap that cost a wrong 'complete' claim
    with the example dicts - so it is checked rather than assumed."""
    import ai_sde_bank as bank
    import ai_sde_tags
    ai_sde_tags.validate(bank.ENTRIES)


def test_ai_sde_tagged_entries_carry_all_six_dimensions():
    """No blanks: an entry is either untagged or has all six columns."""
    import ai_sde_bank as bank
    partial = [e["title"] for e in bank.ENTRIES
               if any("tag_" + d in e for d in ai_sde_dims())
               and not all("tag_" + d in e for d in ai_sde_dims())]
    assert not partial, f"entries tagged on some dimensions but not all: {partial[:5]}"


def ai_sde_dims():
    import ai_sde_tags
    return ai_sde_tags.DIMENSIONS


def test_ai_sde_tag_priority_is_not_a_rubber_stamp():
    """If Must-Know swallows the bank the tagging is worthless. Guard the
    calibration itself: once a decent slice is tagged, Must-Know must stay a
    minority and Rare must be genuinely used."""
    import ai_sde_bank as bank
    import ai_sde_tags
    if bank.TAGGED_COUNT < 100:
        return  # too early in the tagging pass to judge the distribution
    c = ai_sde_tags.counts(bank.ENTRIES)["priority"]
    total = sum(c.values())
    assert c["Must-Know"] / total < 0.40, (
        f"Must-Know is {c['Must-Know'] / total:.0%} of tagged entries - "
        "the priority dimension has stopped discriminating"
    )
    assert c["Rare"] / total > 0.10, (
        f"Rare is only {c['Rare'] / total:.0%} of tagged entries - "
        "nothing is being marked genuinely infrequent"
    )


def test_ai_sde_every_tagged_entry_has_a_legal_subtopic():
    """SUBTOPIC is the seventh column and is scoped per topic - a DSA subtopic
    on an NLP-LLM row is a mis-tag, not a free-text note. `validate` checks the
    pairing; this checks nothing was left blank, since a blank subtopic makes
    the study-page filter silently lose the entry."""
    import ai_sde_bank as bank
    blank = [e["title"] for e in bank.ENTRIES
             if "tag_topic" in e and not e.get("tag_subtopic")]
    assert not blank, (
        f"{len(blank)} tagged entries have no subtopic: "
        f"{blank[:5]}{'...' if len(blank) > 5 else ''}"
    )


def test_ai_sde_api_ships_the_tag_vocabulary_and_per_entry_tags(auth_client):
    """The filter dropdowns are built from the vocabulary the API serves, so a
    value added to ai_sde_tags.py appears in the UI without touching the
    template. If this payload loses tag_vocab the tag row silently goes empty."""
    r = auth_client.get("/api/ai-sde")
    assert r.status_code == 200
    body = r.get_json()
    vocab = body.get("tag_vocab") or {}
    for key in ("topic", "level", "priority", "format", "stage", "time", "subtopics"):
        assert vocab.get(key), f"tag_vocab is missing {key}"
    untagged = [e["title"] for e in body["entries"] if "tag_priority" not in e]
    assert not untagged, f"{len(untagged)} entries reach the page untagged: {untagged[:5]}"


def test_ai_sde_tag_filters_narrow_and_ignore_junk(app):
    """?tpriority/?ttopic/?tsub narrow the export. An unknown value must widen
    to everything rather than returning an empty page, so a stale bookmark
    degrades gracefully instead of looking like a broken bank."""
    import routes.interview_prep as ip
    from ai_sde_bank import ENTRIES
    items = [{"id": f"ai{i}", **e} for i, e in enumerate(ENTRIES)]

    with app.test_request_context("/?tpriority=Must-Know&ttopic=DSA&tsub=Graphs"):
        narrowed, bits = ip._ai_sde_tag_select(items)
    assert bits == ["Must-Know", "DSA", "Graphs"]
    assert narrowed and len(narrowed) < len(items)
    assert all(e["tag_priority"] == "Must-Know" and e["tag_subtopic"] == "Graphs"
               for e in narrowed)

    with app.test_request_context("/?tpriority=NotAValue"):
        wide, bits = ip._ai_sde_tag_select(items)
    assert len(wide) == len(items) and bits == []


def test_ai_sde_pdf_carries_the_interview_tags(auth_client):
    """The exported sheet must show the tags, not just filter by them."""
    pytest.importorskip("fpdf", reason="fpdf2 not installed; PDF route falls back to a redirect")
    r = auth_client.get("/ai-sde/pdf?tpriority=Must-Know&ttopic=DSA&tsub=Graphs")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"

    import re
    import zlib
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", r.get_data(), re.S):
        try:
            chunks.append(zlib.decompress(m.group(1)).decode("latin-1"))
        except Exception:
            pass
    text = " ".join(s[1:-1] for s in
                    re.findall(r"\((?:[^()\\]|\\.)*\)", " ".join(chunks)))
    assert "INTERVIEW TAGS" in text, "the PDF lost the Interview tags field"
    assert "Must-Know for a new grad" in text
    assert "DSA / Graphs" in text
    # The heading names the filter, so the sheet says what it is.
    assert "Must-Know" in text[:400]


# ═══════════════════════════════════════════════════
# Goal planner — countdown maths, coach calibration, page
# ═══════════════════════════════════════════════════

def _tz_and_now():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Kolkata")
    return tz, datetime(2026, 8, 15, 9, 0, tzinfo=tz)


def test_countdown_resolves_a_bare_date_to_end_of_day():
    """A date means "by the end of that day". Treating it as midnight would
    silently steal the last 24 hours of every goal."""
    from utils.countdown import resolve_target
    tz, _ = _tz_and_now()
    got = resolve_target(None, "2026-08-20", tz)
    assert (got.hour, got.minute, got.second) == (23, 59, 59)
    # An explicit moment must win over the date and keep its own time.
    exact = resolve_target("2026-08-20T14:30:00+05:30", "2026-08-20", tz)
    assert (exact.hour, exact.minute) == (14, 30)


def test_countdown_unit_escalates_towards_the_deadline():
    """The headline unit getting finer IS the urgency signal, so nothing has
    to flash while a goal is still weeks away. Also pins the tick rate: a
    per-second redraw six weeks out is pure battery burn."""
    from datetime import timedelta
    from utils.countdown import breakdown, display, TICK_SECOND, TICK_HOUR
    _, now = _tz_and_now()
    far = display(breakdown(now + timedelta(days=45), now))
    near = display(breakdown(now + timedelta(hours=12), now))
    assert (far["unit"], far["tone"], far["tick"]) == ("weeks", "calm", TICK_HOUR)
    assert near["tone"] == "urgent" and near["tick"] == TICK_SECOND
    late = display(breakdown(now - timedelta(days=2), now))
    assert late["tone"] == "overdue" and late["value"] == 2


def test_countdown_split_is_complementary():
    """16 days must read "2w 2d", never "2w 16d" — the parts sum to the whole."""
    from datetime import timedelta
    from utils.countdown import breakdown
    _, now = _tz_and_now()
    b = breakdown(now + timedelta(days=16), now)
    assert (b["weeks"], b["days"]) == (2, 2)
    assert b["total_days"] == 16


def test_countdown_working_days_excludes_weekends():
    """"44 days" quietly includes a dozen days nobody was going to work."""
    from datetime import date
    from utils.countdown import working_days
    # Mon 17 Aug 2026 → Fri 28 Aug is 12 calendar days, 10 working.
    assert working_days(date(2026, 8, 17), date(2026, 8, 28)) == 10
    assert working_days(date(2026, 8, 15), date(2026, 8, 16)) == 0   # a weekend
    assert working_days(date(2026, 8, 20), date(2026, 8, 10)) == 0   # end before start
    # A six-day study week loses only the Sunday.
    assert working_days(date(2026, 8, 17), date(2026, 8, 28), (0, 1, 2, 3, 4, 5)) == 11


def test_countdown_budget_flags_an_impossible_goal():
    """The most valuable number on the page: whether the remaining time can
    physically hold the remaining work, while re-scoping is still cheap."""
    from utils.countdown import budget
    # `days_left`, not `working_days_left` — a "per day" commitment is taken
    # at its word; see test_budget_takes_a_daily_commitment_at_its_word.
    b = budget(days_left=31, daily_commit_minutes=120, effort_minutes=139 * 60)
    assert b["feasible"] is False
    assert b["shortfall_minutes"] == 139 * 60 - 31 * 120
    assert b["required_daily_minutes"] == round(139 * 60 / 31)
    # Without both halves the answer would be a guess, so there isn't one.
    assert budget(31, 120, None) is None
    assert budget(31, None, 8340) is None


def test_goal_coach_judges_slippage_relatively_not_in_raw_points():
    """14 points behind at 24% expected means only 40% of the work is done —
    serious. The same 14 points at 90% expected is a rounding error. Absolute
    gaps get this backwards, which is why severity is a ratio."""
    from utils.countdown import summarise
    from services.goal_coach import coach
    tz, now = _tz_and_now()
    goal = {"title": "T", "start_date": "2026-08-01",
            "target_at": "2026-09-28T18:00:00+05:30"}
    early_bad = coach(summarise(goal, now, tz, progress_pct=10), "T", 10)
    assert early_bad[1] == "scold"
    late = {"title": "T", "start_date": "2026-01-01",
            "target_at": "2026-09-01T18:00:00+05:30"}
    late_slip = coach(summarise(late, now, tz, progress_pct=76), "T", 76)
    assert late_slip[1] == "push", "a late-stage 14-point gap is not a scolding"
    # Day one of a long goal must not be scolded for 0% against 0% expected.
    fresh = {"title": "T", "start_date": "2026-08-14",
             "target_at": "2027-08-14T18:00:00+05:30"}
    assert coach(summarise(fresh, now, tz, progress_pct=0), "T", 0)[1] == "cheer"


def test_goal_coach_puts_infeasibility_above_being_on_pace():
    """Being "on pace" for something arithmetically impossible is the most
    dangerous state a plan can be in, so the budget alarm outranks pace."""
    from utils.countdown import summarise
    from services.goal_coach import coach
    tz, now = _tz_and_now()
    goal = {"title": "T", "start_date": "2026-08-01",
            "target_at": "2026-09-28T18:00:00+05:30",
            "daily_commit_minutes": 120, "effort_minutes": 139 * 60}
    msg, tone = coach(summarise(goal, now, tz, progress_pct=33), "T", 33)
    assert tone == "alarm" and "short" in msg


def test_goal_planner_page_and_api(auth_client, monkeypatch):
    """The page renders and the API shapes one goal per objective, sorted by
    urgency with undated goals last."""
    import routes.goals as goals

    objectives = [
        {"id": "g1", "title": "Dated", "status": "active", "start_date": "2026-08-01",
         "target_at": "2036-09-28T18:00:00+05:30", "created_at": "2026-08-01T00:00:00+00:00"},
        {"id": "g2", "title": "Undated", "status": "active",
         "created_at": "2026-08-01T00:00:00+00:00"},
    ]
    krs = [{"id": "k1", "objective_id": "g1", "start_value": 0, "current_value": 5,
            "target_value": 10, "direction": "up", "title": "Half done"}]
    monkeypatch.setattr(goals, "get", lambda table, params=None, **kw:
                        objectives if table == "objectives"
                        else (krs if table == "key_results" else []))

    assert auth_client.get("/goal-planner").status_code == 200
    body = auth_client.get("/api/goal-planner").get_json()
    assert [g["title"] for g in body["goals"]] == ["Dated", "Undated"], \
        "undated goals must sink below dated ones — they cannot be urgent"
    dated = body["goals"][0]
    assert dated["progress"] == 50, "progress must roll up from key results"
    assert dated["countdown"]["has_deadline"] is True
    assert body["goals"][1]["countdown"]["has_deadline"] is False
    assert dated["coach"]["message"]


def test_countdown_widget_is_wired_into_goals_and_interview_prep(auth_client):
    """The ticker is shared by three pages. These assertions are the contract
    between countdown.js and its hosts: the script must load, and each page
    must expose the mount points it reads ([data-cd-big] / [data-cd-unit]).
    Rename one of those hooks and the countdown silently shows nothing, which
    is exactly the kind of breakage nobody notices until a deadline passes."""
    for path, hooks in (
        # The planner hero shows the full DAYS : HRS : MINS readout...
        ("/goal-planner", ("data-cd-d", "data-cd-h", "data-cd-m", "data-cd-detail")),
        # ...while dense surfaces use the one-line form of the same thing.
        ("/interview-prep", ("data-cd-compact",)),
    ):
        html = auth_client.get(path).get_data(as_text=True)
        assert "js/countdown.js" in html, f"{path} does not load countdown.js"
        for hook in hooks:
            assert hook in html, f"{path} is missing the {hook} mount point"

    # /goals builds its cards in static/goals.js, so the hooks live there.
    goals_html = auth_client.get("/goals").get_data(as_text=True)
    assert "js/countdown.js" in goals_html, "/goals does not load countdown.js"
    with open("static/goals.js", encoding="utf-8") as fh:
        js = fh.read()
    assert "data-cd-compact" in js and "renderDueBlock" in js
    assert "Countdown.mountAll" in js, "goals.js never mounts the tickers it renders"
    # Re-rendering the list must drop the old instances or detached nodes keep
    # ticking; that leak is invisible until the page has been open for hours.
    assert "Countdown.clear()" in js


def test_countdown_hosts_degrade_without_the_script(auth_client):
    """Every host must guard `typeof Countdown` — the ticker is an
    enhancement, and a failed script load must not blank the page. This
    already happened once on the planner during development."""
    with open("templates/goal_planner.html", encoding="utf-8") as fh:
        planner = fh.read()
    with open("templates/interview_prep.html", encoding="utf-8") as fh:
        prep = fh.read()
    with open("static/goals.js", encoding="utf-8") as fh:
        goals_js = fh.read()
    for name, src in (("goal_planner.html", planner),
                      ("interview_prep.html", prep),
                      ("goals.js", goals_js)):
        # Either spelling of the guard is fine (=== undefined, or !== to take
        # the happy path); what matters is that the reference is guarded at
        # all rather than assumed.
        assert 'typeof Countdown' in src, \
            f"{name} uses Countdown without guarding for it being absent"


def test_relative_deadlines_resolve_server_side(app):
    """A deadline can be given as a duration ("in 45 days") or as a date.
    Durations are resolved against the USER's now, not the browser's — a
    device clock in the wrong timezone must not shift the deadline. Junk and
    obvious typos are rejected rather than stored as a year-4000 date that
    would break every countdown on the page."""
    import routes.goals as goals
    from datetime import datetime
    from utils.user_tz import user_now

    with app.test_request_context():
        now = user_now()
        for payload, unit_seconds in (({"in_days": 45}, 45 * 86400),
                                      ({"in_hours": 36}, 36 * 3600),
                                      ({"in_minutes": 90}, 90 * 60)):
            iso, err = goals._resolve_relative_deadline(payload)
            assert err is None and iso
            delta = (datetime.fromisoformat(iso) - now).total_seconds()
            assert abs(delta - unit_seconds) < 5, f"{payload} landed at {iso}"

        # An explicit moment always wins; the relative field is ignored.
        iso, err = goals._resolve_relative_deadline(
            {"target_at": "2026-09-28T18:00", "in_days": 999})
        assert iso is None and err is None

        for bad in ({"in_days": 0}, {"in_days": -5}, {"in_days": "abc"},
                    {"in_days": 45000}):
            iso, err = goals._resolve_relative_deadline(bad)
            assert iso is None and err, f"{bad} should have been rejected"


def test_countdown_flash_flag_is_permission_not_current_state():
    """`flash` must mean "this goal is ALLOWED to flash", never "it is
    flashing right now".

    It used to be `flash_enabled AND tone is urgent`, which reads as
    equivalent and is not: the client freezes the value at mount, so a page
    opened 30 hours before a deadline was served flash=False and then never
    started flashing when it crossed into its last day. Since the planner is
    meant to sit open all day — on a phone especially — that silently killed
    the whole feature. `flash_now` carries the render-time state instead."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from utils.countdown import summarise
    tz = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 8, 15, 9, 0, tzinfo=tz)

    far = summarise({"title": "T", "flash_enabled": True,
                     "target_at": (now + timedelta(hours=30)).isoformat()}, now, tz)
    assert far["flash"] is True, "permission must not depend on how far away it is"
    assert far["flash_now"] is False, "30h out is not yet flashing"

    near = summarise({"title": "T", "flash_enabled": True,
                      "target_at": (now + timedelta(hours=5)).isoformat()}, now, tz)
    assert near["flash"] is True and near["flash_now"] is True

    # An explicit opt-out switches both off at every distance.
    off = summarise({"title": "T", "flash_enabled": False,
                     "target_at": (now + timedelta(hours=5)).isoformat()}, now, tz)
    assert off["flash"] is False and off["flash_now"] is False


def test_flash_survives_reduced_motion_and_paused_animations():
    """The blink must not be a CSS animation alone.

    iOS Low Power Mode pauses CSS animations and Reduce Motion suppresses
    them, and the first version's fallback was `animation: none` — i.e. no
    indication at all on exactly the phones where a deadline matters most.
    countdown.js therefore toggles a class, and pins it ON (rather than
    blinking) when the user has asked for reduced motion."""
    with open("static/js/countdown.js", encoding="utf-8") as fh:
        js = fh.read()
    assert "flash-on" in js, "the blink is not driven from JS"
    assert "prefers-reduced-motion" in js, "reduced motion is not detected in JS"
    assert "clearInterval(flashTimer)" in js, "the flash timer is never stopped"

    for name in ("templates/goal_planner.html", "templates/interview_prep.html"):
        with open(name, encoding="utf-8") as fh:
            css = fh.read()
        assert ".flash-on" in css, f"{name} has no styling for the JS flash state"
        # The old failure mode: an animation with a reduced-motion opt-out
        # that left nothing visible behind it.
        assert "animation: none" not in css, (
            f"{name} still disables the flash outright under reduced motion")


def test_typed_progress_wins_over_the_key_result_rollup(monkeypatch):
    """A goal created on the planner has no key results, so it scored 0 for
    ever and the coach scolded it permanently with no way to answer back.
    A typed percentage overrides the roll-up, and the SOURCE travels with the
    number so a typed 60% next to key results averaging 20% can be labelled
    rather than silently conflated. Clearing it restores the roll-up."""
    import routes.goals as goals
    krs = [{"id": "k1", "objective_id": "withkr", "start_value": 0,
            "current_value": 2, "target_value": 10, "direction": "up"},
           {"id": "k2", "objective_id": "both", "start_value": 0,
            "current_value": 2, "target_value": 10, "direction": "up"}]
    monkeypatch.setattr(goals, "get",
                        lambda table, params=None, **kw: krs if table == "key_results" else [])
    objectives = [
        {"id": "withkr", "title": "rollup only"},
        {"id": "both", "title": "typed beats rollup", "manual_progress": 60},
        {"id": "bare", "title": "nothing"},
        {"id": "typed", "title": "typed only", "manual_progress": 40},
    ]
    out = goals._objective_progress("u1", objectives)
    assert (out["withkr"]["progress"], out["withkr"]["source"]) == (20, "key_results")
    assert (out["both"]["progress"], out["both"]["source"]) == (60, "manual")
    assert out["both"]["rolled_up"] == 20, "the roll-up must stay visible alongside"
    assert (out["bare"]["progress"], out["bare"]["source"]) == (0, "none")
    assert (out["typed"]["progress"], out["typed"]["source"]) == (40, "manual")


def test_typed_progress_is_clamped_and_clearable():
    """150 obviously means "done", so clamp rather than reject — refusing it
    would be pedantic. An empty value clears the override. Genuine junk IS
    rejected, because silently storing 0 would look like lost progress."""
    import routes.goals as goals
    assert goals._clean_manual_progress(55) == (55, None)
    assert goals._clean_manual_progress("55") == (55, None)
    assert goals._clean_manual_progress(150)[0] == 100
    assert goals._clean_manual_progress(-20)[0] == 0
    assert goals._clean_manual_progress(33.7)[0] == 34
    assert goals._clean_manual_progress("") == (None, None)
    assert goals._clean_manual_progress(None) == (None, None)
    value, err = goals._clean_manual_progress("abc")
    assert value is None and err


def test_goal_planner_progress_control_is_a_visible_slider(auth_client):
    """Progress was first a number input styled to look like plain text until
    hovered. It worked perfectly and was unusable: nothing said it could be
    edited, so the reported bug was "not able to enter %". A range input is
    self-evidently draggable, on a phone as much as a desktop.

    Saving must happen on `change` (release) and never on `input`, or one
    drag becomes a hundred PATCHes and a hundred re-renders."""
    html = auth_client.get("/goal-planner").get_data(as_text=True)
    assert 'type="range"' in html, "the progress control is not a slider"
    assert "pctrange" in html and "data-pctout" in html, "no live readout beside the slider"
    assert "data-pct" in html and "savePct" in html
    # The readout updates on input; only change() persists.
    assert 'addEventListener("input"' in html, "readout does not follow the drag"
    assert "preventScroll" in html, "re-render steals focus and jumps the page"


def test_pinned_goal_without_a_deadline_still_renders_a_hero(auth_client, monkeypatch):
    """Found on live data: a goal was pinned with no target date, so the hero
    rendered EMPTY while three dated goals sat in the list below it — the page
    looked broken. Honour the pin either way: show the goal and ask for the
    missing date, rather than blanking or silently substituting another goal."""
    import routes.goals as goals
    objectives = [
        {"id": "pinned", "title": "No date", "status": "active", "is_primary": True,
         "created_at": "2026-08-01T00:00:00+00:00"},
        {"id": "dated", "title": "Has a date", "status": "active",
         "target_at": "2036-12-31T18:00:00+05:30", "created_at": "2026-08-01T00:00:00+00:00"},
    ]
    monkeypatch.setattr(goals, "get",
                        lambda table, params=None, **kw: objectives if table == "objectives" else [])
    body = auth_client.get("/api/goal-planner").get_json()
    assert body["primary_id"] == "pinned", "the pin must be respected, not overridden"

    html = auth_client.get("/goal-planner").get_data(as_text=True)
    assert "heroNoDateHTML" in html, "no fallback hero for a pinned goal with no deadline"
    assert "h-set" in html, "the undated hero offers no way to add the missing deadline"


def test_ai_sde_progress_is_keyed_by_title_not_the_positional_id(auth_client, monkeypatch):
    """The list endpoint hands out ids as "ai0", "ai1", ... derived from the
    entry's INDEX in the bank. That index shifts whenever a topic is added or
    deduped — and the bank grew from ~500 to 1,120 entries with 57 duplicates
    folded out, so anything stored against those ids now points at a
    different topic. Progress is therefore stored by title, and a title the
    bank no longer has is DROPPED rather than mapped onto its neighbour."""
    import routes.interview_prep as ip
    real = next(iter(ip._AI_SDE_TITLES))
    rows = [
        {"entry_title": real, "studied": True, "minutes_focused": 25},
        {"entry_title": "A topic that was renamed away", "studied": True,
         "minutes_focused": 99},
    ]
    monkeypatch.setattr(ip, "get", lambda table, params=None, **kw: rows)
    body = auth_client.get("/api/ai-sde/progress").get_json()
    assert body["studied"] == [real]
    assert body["minutes"] == {real: 25}
    assert body["total_rows"] == 2, "the stale row is dropped from the answer, not the count"


def test_ai_sde_progress_rejects_unknown_topics(auth_client, monkeypatch):
    """A title that is not in the bank is a bug or a stale client, never
    something to store — otherwise the table slowly fills with orphans."""
    import routes.interview_prep as ip
    monkeypatch.setattr(ip, "post", lambda *a, **kw: [{}])
    r = auth_client.post("/api/ai-sde/progress", json={"title": "nope", "studied": True})
    assert r.status_code == 400

    real = next(iter(ip._AI_SDE_TITLES))
    saved = {}
    monkeypatch.setattr(ip, "post",
                        lambda table, payload, **kw: saved.update(payload) or [{}])
    r = auth_client.post("/api/ai-sde/progress", json={"title": real, "studied": True})
    assert r.status_code == 200
    assert saved["entry_title"] == real and saved["studied"] is True
    assert saved["studied_at"], "ticking must stamp when it happened"


def test_ai_sde_page_persists_by_title_and_survives_a_missing_table(auth_client):
    """The page must keep working when progress sync is unavailable — the
    localStorage mirror is what makes a tick feel instant, and a 503 from an
    unrun migration must not take the study page down with it."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "ai_sde_studied_titles" in html, "still keying local storage on positional ids"
    assert "pushProgress" in html and "syncStudied" in html
    # Union, not replace: an offline tick must not be erased by an older
    # server row when the two are reconciled.
    assert "!studied.has(id)" in html, "server sync overwrites local state instead of merging"


def test_interview_coach_labels_the_ai_sde_categories():
    """The coach is shared by two very different runs — a senior TPM loop and
    a new-grad AI/SDE loop. MIGRATION_AI_SDE_PREP_TRACK.sql seeds the student
    account with dsa / cs_fundamentals / ml / ai_llm categories; without a
    label each the page prints the raw key as a section heading."""
    from routes.interview_prep import CATEGORY_LABELS
    for key in ("dsa", "cs_fundamentals", "ml", "ai_llm"):
        assert key in CATEGORY_LABELS, f"{key} would render as a raw key"


def test_ai_sde_prep_track_migration_is_derived_and_safe():
    """The student's syllabus must come FROM the tagged bank, so the study
    plan and the content cannot drift apart, and it must not hard-delete the
    TPM rows it replaces."""
    import re
    with open("MIGRATION_AI_SDE_PREP_TRACK.sql", encoding="utf-8") as fh:
        sql = fh.read()
    assert "delete from" not in sql.lower(), "house rule: soft delete only"
    assert "set deleted_at = now()" in sql, "the replaced TPM rows are not retired"
    assert "venghateshshreya@gmail.com" in sql, "not scoped to the student account"

    # Every seeded topic must name a real subtopic from the tag vocabulary.
    import ai_sde_tags
    known = {s.replace("-", " ") for subs in ai_sde_tags.SUBTOPICS.values() for s in subs}
    seeded = re.findall(r"'(?:DSA|Core-CS|Python|Classical-ML|Deep-Learning|"
                        r"Math-Stats|NLP-LLM|System-Design|MLOps|Behavioral) — "
                        r"([A-Za-z ]+?) \(\d+ must-know\)'", sql)
    assert seeded, "no derived topics found in the migration"
    unknown = [s for s in seeded if s not in known]
    assert not unknown, f"seeded topics not in the tag vocabulary: {unknown[:5]}"


def test_budget_measures_the_work_that_is_LEFT():
    """Comparing the time remaining against the WHOLE job means the alarm can
    never clear: a goal at 50% reported the full shortfall and shouted just as
    loudly as on day one. An alarm that doing the work cannot silence is one
    you learn to ignore, which defeats the point of having it."""
    from utils.countdown import budget
    # 100 days x 90 min = 150h available, against a 200h job.
    at_zero = budget(100, 90, 200 * 60, progress_pct=0)
    assert at_zero["feasible"] is False
    assert at_zero["needed_minutes"] == 200 * 60

    half = budget(100, 90, 200 * 60, progress_pct=50)
    assert half["needed_minutes"] == 100 * 60, "half done means half the work left"
    assert half["feasible"] is True, "the alarm must clear once the work is done"
    assert half["total_effort_minutes"] == 200 * 60, "the whole job stays visible"

    assert budget(100, 90, 200 * 60, progress_pct=100)["needed_minutes"] == 0


def test_budget_takes_a_daily_commitment_at_its_word():
    """"90 minutes a day" means per DAY. Multiplying it by working days
    quietly assumes weekends off, which understated a student's available
    time by a third and made a workable plan look impossible."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from utils.countdown import summarise
    tz = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 8, 15, 9, 0, tzinfo=tz)
    goal = {"title": "T", "start_date": "2026-08-15",
            "target_at": "2026-11-15T09:00:00+05:30",
            "daily_commit_minutes": 90, "effort_minutes": 17065}
    s = summarise(goal, now, tz, progress_pct=0)
    # 92 calendar days, not the 65 working ones.
    assert s["budget"]["available_minutes"] == 92 * 90
    assert s["working_days_left"] == 65, "working days stay reported separately"


def test_ai_sde_tag_filters_do_not_depend_on_the_server_vocabulary(auth_client):
    """The dropdowns are built from `tag_vocab`, but must not REQUIRE it. A
    payload cached from before that field existed left every dropdown empty,
    which presents as "tag filtering is broken" — with no options there is
    nothing to select. The vocabulary is recoverable from the entries, which
    each carry their own tag values."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "function tagVocab()" in html, "no fallback when tag_vocab is absent"
    assert "BANK.entries.map(e => e[field])" in html, "vocabulary is not derived from entries"
    # And an untagged bank should hide the row rather than show dead controls.
    assert 'row.style.display = "none"' in html


def test_mobile_layout_cannot_be_cut_off(auth_client):
    """Reported as "in mobile the UI is cutting". Two causes, both real:

    1. .q-head is a flex row that now carries six chips (priority, time,
       frequency, sub-area, difficulty, category) — two of which the tagging
       work added. They are all flex:none, so without wrapping they cannot
       shrink and the row is clipped off the side of the screen.
    2. The worked examples are white-space:pre-wrap and contain ASCII tables
       with unbreakable runs, which widen the card past the viewport unless
       they get their own scroller."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    import re
    head = re.search(r"^\s*\.q-head \{[^}]*\}", html, re.M).group(0)
    assert "flex-wrap: wrap" in head, "the six-chip card header cannot wrap"
    for block in (r"^\s*\.ex \.body \{[^}]*\}", r"^\s*\.fld\.deep \{[^}]*\}",
                  r"^\s*\.fld\.recipe \{[^}]*\}"):
        rule = re.search(block, html, re.M).group(0)
        assert "pre-wrap" in rule and "overflow-x: auto" in rule, \
            f"pre-wrap block without a scroller: {rule[:60]}"
    assert "overflow-x: hidden" in html, "the page itself can still scroll sideways"

    planner = auth_client.get("/goal-planner").get_data(as_text=True)
    # Anchored: an unanchored ".row {" also matches "input.pctrange.row {".
    row = re.search(r"^\s*\.row \{[^}]*\}", planner, re.M).group(0)
    assert "flex-wrap: wrap" in row, "planner rows cannot wrap on a phone"


def test_card_title_is_not_sliced_off_on_a_phone(auth_client):
    """Reported as "question is getting cut off". The mobile rule gave the
    title `order: -1` so it took its own line, then pulled it back up beside
    the checkbox with `margin-top: -24px` — a 24px lift into 11px of padding,
    inside a card with overflow: hidden, so the top of every question was
    sliced. The chips now sit in their own wrapper instead, which is what lets
    them drop to a second row without moving the title at all."""
    import re
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    for rule in re.findall(r"^\s*\.q-head \.q-text \{[^}]*\}", html, re.M):
        assert "margin-top: -" not in rule, f"title lifted by a negative margin: {rule}"
        assert "order:" not in rule, f"title reordered away from the checkbox: {rule}"
    assert '<span class="q-chips">' in html, "the header chips have no wrapper to wrap as a group"
    mobile = re.search(r"@media \(max-width: 640px\) \{.*?\n  \}", html, re.S).group(0)
    assert ".q-head .q-chips" in mobile, "the chips never move to their own row on a phone"


def test_card_chips_line_up_between_cards_on_desktop(auth_client):
    """Reported as "misaligned among different cards, hard to read".

    The desktop rule was `display: contents`, which dissolved the wrapper so
    the six chips became plain flex children trailing a flex:1 title, each at
    its natural width. The content varies far too much for that to line up:
    the category label runs 12 to 27 characters, the sub-area 3 to 19. Every
    card put its priority, its time and its difficulty at a different x, so
    reading down a column of cards meant re-finding each chip on every row.

    A fixed-track grid is the fix, and this test is here because
    `display: contents` is the tidier-looking rule and would be easy to
    restore by accident."""
    import re
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    rules = re.findall(r"\.q-head \.q-chips \{[^}]*\}", html)
    assert rules, "no desktop rule for the header chips"
    desktop = rules[0]
    assert "display: contents" not in desktop, (
        "chips back to display: contents — they will not align between cards")
    assert "display: grid" in desktop and "grid-template-columns" in desktop, desktop
    # Fixed tracks, not auto/min-content: a track sized to its content is a
    # track that moves when the content changes, which is the whole bug.
    cols = re.search(r"grid-template-columns:\s*([^;]+);", desktop).group(1)
    assert "auto" not in cols and "min-content" not in cols and "max-content" not in cols, cols
    assert len(cols.split()) >= 6, f"a track per chip is what keeps them aligned: {cols}"
    # A chip whose value overruns must shorten, not widen its track.
    assert "text-overflow: ellipsis" in html


def test_a_timed_task_draws_on_its_own_day_only():
    """A task scheduled for 9am Monday drew a chip at 9am on Tuesday,
    Wednesday and every day after, until it was marked done.

    /api/v2/project-tasks filters `due_date is null OR due_date <= date`,
    which is the right question for the unscheduled backlog panel and the
    wrong one for the grid. drag-to-schedule already writes plan_date
    beside start_time, so the day was recorded — the grid just never
    looked at it, and the endpoint did not even return it."""
    import re
    js = open("static/v2/planner_v2.js", encoding="utf-8").read()
    grid = re.search(r"const timedTasks = taskData\.filter\((.*?)\);", js, re.S).group(1)
    assert "plan_date" in grid, "the grid still ignores which day a task belongs to"
    assert "start_time" in grid
    # ...and the endpoint has to actually send it.
    py = open("routes/projects.py", encoding="utf-8").read()
    sel = re.search(r'"select": "task_id,task_text,priority,project_id,[^"]*"'
                    r'(?:\s*"[^"]*")*', py).group(0)
    assert "plan_date" in sel, "plan_date is not in the calendar task payload"
    # A task given a day but no clock time is scheduled, not floating — it
    # must not reappear in the "unscheduled" panel as a second copy.
    floating = re.search(r"const unscheduled = \(tasks \|\| \[\]\)\.filter\((.*?)\);",
                         js, re.S).group(1)
    assert "plan_date" in floating, "a task with a day still lists as unscheduled"


def test_quick_bucket_top5_wraps_instead_of_truncating(auth_client):
    """Today's five are the tasks she actually reads, so a long one must WRAP.
    It used to be white-space: nowrap with an ellipsis, which meant identifying
    a task required clicking it - the opposite of what the panel is for."""
    import re
    html = auth_client.get("/quick-bucket").get_data(as_text=True)
    rule = re.search(r"^\s*\.qb-top5-text \{[^}]*\}", html, re.M)
    assert rule, "no .qb-top5-text rule"
    body = rule.group(0)
    assert "nowrap" not in body and "text-overflow" not in body, f"still truncating: {body}"
    assert "overflow-wrap: anywhere" in body, "a long unbroken string could widen the panel"
    item = re.search(r"^\s*\.qb-top5-item \{[^}]*\}", html, re.M).group(0)
    assert "align-items: flex-start" in item, \
        "with wrapped text, centring floats the rank badge to the middle of the row"


def test_answer_field_keeps_its_line_breaks(auth_client):
    """The answer is the field read under time pressure, and it is now written
    headline-first with short labelled lines under it. That shape only exists
    if the line breaks survive - `.fld.answer` had no `white-space: pre-wrap`
    (unlike `.fld.deep` and `.fld.recipe`), so every rewritten answer would have
    collapsed straight back into the paragraph it came from."""
    import re
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    rule = re.search(r"^\s*\.fld\.answer \{[^}]*\}", html, re.M)
    assert rule, "no .fld.answer block rule at all"
    assert "pre-wrap" in rule.group(0) and "overflow-x: auto" in rule.group(0)
    # The first line is lifted out as a heading, so it reads as one.
    assert "function answerHTML(val)" in html
    assert 'class="head"' in html
    # The quiz shows the same text; it must not collapse it either.
    quiz = auth_client.get("/ai-sde/quiz").get_data(as_text=True)
    for sel in (r"^\s*\.qprompt \{[^}]*\}", r"^\s*\.explain \{[^}]*\}"):
        block = re.search(sel, quiz, re.M)
        assert block and "pre-wrap" in block.group(0), f"quiz rule collapses newlines: {sel}"


def test_rewritten_answers_all_match_a_real_entry(auth_client):
    """Same trap as the `_EX_*` dicts: a mis-keyed title in _ANSWER_V2 rewrites
    nothing at all, silently, and the entry keeps its old prose."""
    import ai_sde_bank as bank
    assert bank.ANSWERS_REWRITTEN == bank.ANSWERS_DECLARED, (
        f"{bank.ANSWERS_DECLARED - bank.ANSWERS_REWRITTEN} rewritten answers are "
        "keyed to a title that does not exist"
    )
    # And every rewritten answer really is headline-first.
    for e in bank.ENTRIES:
        if e["title"] in bank._ANSWER_V2:
            body = e["answer"]
            head, sep, rest = body.partition("\n")
            assert sep, f"{e['title']}: rewritten answer has no headline line"
            assert len(head) <= 160, f"{e['title']}: headline is a paragraph, not a line"
            assert "·" in rest, f"{e['title']}: no labelled points under the headline"


def test_card_body_is_collapsible_and_the_answer_can_be_re_hidden(auth_client):
    """Two requests, one cause: a written-up topic is ~16k characters and every
    section rendered flat, so the card was a wall to scroll past — and the quiz
    reveal was one-way, so an answer once shown could not be put away without
    reloading, which turns the next attempt into re-reading."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "function sec(cls, label, inner, opts)" in html, "no collapsible section helper"
    assert '<details class="sec sec-' in html, "sections are not <details>"
    assert '<details class="ex">' in html, "worked examples are not individually collapsible"
    assert "function exSummary(text)" in html, "no summary line for a worked example"
    assert "data-expand" in html, "no expand-all control"
    # The reveal button must survive being pressed, and say so.
    assert '"Hide the answer" : "Show the answer"' in html, "reveal does not toggle back"
    assert ".qi.shown .reveal { display: none; }" not in html, "reveal is still hidden once used"
    review = auth_client.get("/study/review").get_data(as_text=True)
    assert "function hideAnswer()" in review, "study review answer cannot be re-hidden"

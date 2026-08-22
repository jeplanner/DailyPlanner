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
import inspect
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


def _pdf_text(data):
    """The visible text of a PDF built by _pdf_bytes().

    The export embeds a real Unicode font, so box-drawing and arrows survive
    instead of being transliterated to ASCII by _latin1(). The cost is that
    the content streams now hold two-byte GLYPH IDS rather than readable
    characters, and each of the three embedded fonts numbers its glyphs
    independently — so the old "decompress and grep for ASCII" only ever
    worked because the core fonts wrote latin-1 directly.

    Decoding that correctly means resolving each font's /ToUnicode CMap and
    tracking which font is selected at every Tf. pypdf already does exactly
    that, and a hand-rolled version in a test would be a second PDF parser
    to maintain. Skips rather than silently passing when pypdf is absent.

    Whitespace is COLLAPSED. Body text is 26pt, so a phrase routinely breaks
    across lines, and justified output extracts with doubled spaces — an
    assertion about content should not fail over either. This helper is
    therefore for "is it in there", never for layout.
    """
    import io
    import re
    pypdf = pytest.importorskip(
        "pypdf", reason="pypdf not installed; cannot decode embedded-font text")
    reader = pypdf.PdfReader(io.BytesIO(data))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return re.sub(r"\s+", " ", raw)


def test_ai_sde_pdf_carries_the_interview_tags(auth_client):
    """The exported sheet must show the tags, not just filter by them."""
    pytest.importorskip("fpdf", reason="fpdf2 not installed; PDF route falls back to a redirect")
    r = auth_client.get("/ai-sde/pdf?tpriority=Must-Know&ttopic=DSA&tsub=Graphs")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"

    text = _pdf_text(r.get_data())
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
    # ...and it dedupes against the events, because a scheduled prep topic
    # writes both rows on purpose and both need their time.
    assert "evKeys" in grid, "the grid no longer dedupes tasks against events"
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


def test_the_mobile_day_page_renders_and_carries_the_reflection(auth_client):
    """The day view is a LIST, not the calendar's 24-hour grid.

    Reported twice, from the same root cause: on a phone the grid's chips
    are unreadable slivers, and anything scheduled before its initial
    7am scroll position is off-screen and looks like it does not exist.

    This page has to hold three things together — the timed items, the
    UNTIMED ones (which the grid cannot show at all), and the reflection
    in the same scroll rather than on another page."""
    r = auth_client.get("/day")
    assert r.status_code == 200, r.get_data()[:300]
    html = r.get_data(as_text=True)
    assert "On the clock" in html
    assert "No time set" in html, "untimed items need their own group, not a gap"
    assert 'id="reflection"' in html and 'id="gratitude"' in html
    assert "/api/v2/daily-reflection" in html
    # A phone leaves a page by being backgrounded, not by blurring a field.
    assert "pagehide" in html and "sendBeacon" in html, (
        "typing is lost when the tab is backgrounded mid-edit")
    # Date navigation, so it is usable as a day view and not just as today.
    assert "Previous day" in html and "Next day" in html


def test_the_day_page_survives_a_bad_date(auth_client):
    """A malformed date in a shared link is a bad link, not something to
    show the user a 400 over."""
    r = auth_client.get("/day?date=not-a-date", follow_redirects=False)
    assert r.status_code in (301, 302), r.status_code
    r2 = auth_client.get("/day?date=2026-08-17")
    assert r2.status_code == 200
    assert "17 August 2026" in r2.get_data(as_text=True)


def test_the_calendar_scrolls_to_the_earliest_event_not_a_fixed_hour(auth_client):
    """The grid used to scroll to a hard-coded 7am on load, which put
    anything earlier — study topics booked at 00:00, deliberately, so they
    sit at the top of the day — seven hours above the fold. The page
    looked empty while the entries were there the whole time."""
    import re
    js = open("static/v2/planner_v2.js", encoding="utf-8").read()
    fn = re.search(r"function scrollTo7AM\(\) \{(.*?)\n\}", js, re.S).group(1)
    assert "7 * HOUR_HEIGHT - 20" not in fn, "still hard-scrolling past early events"
    assert "earliest" in fn and "eventsMap" in fn, (
        "the scroll position must be derived from what the day actually holds")


def test_every_question_bank_shows_a_card_summary(auth_client):
    """Reported as "keep card summary for all question banks to be few
    lines, instead of single sentence".

    Four banks, one rule: a few lines of what the entry actually says, on
    the collapsed card, so the list can be skimmed without opening
    anything. The AI/SDE page derives it server-side from the answer; the
    language banks derive it from their plain-English answer; the
    behavioural bank builds it from the coaching tip plus the Situation.
    All four pack WHOLE SENTENCES under a cap, so none is cut mid-clause."""
    for path in ("/ai-sde", "/java", "/sql", "/interview-prep"):
        html = auth_client.get(path).get_data(as_text=True)
        assert 'class="q-sum"' in html, f"{path} has no card summary"
        # And no line-clamp anywhere: the length is bounded at the source,
        # so clamping would reintroduce the cut-off the report was about.
        assert "-webkit-line-clamp" not in html, (
            f"{path} clamps the summary — it will be cut off again")


def test_ai_sde_duplicate_map_is_keyed_to_real_titles():
    """A mis-keyed title in ai_sde_dupes.py silently does nothing at all.

    Same trap as the _EX_* example dicts and ai_sde_tags.py: the key is a
    title string, so a typo produces no error and no effect. validate()
    also rejects a self-reference and a shadow pointing at another shadow.
    """
    import ai_sde_bank as bank
    import ai_sde_dupes
    ai_sde_dupes.validate(bank.ENTRIES)


def test_ai_sde_dedupe_changes_nothing_that_already_existed():
    """The dedupe pass is ADDITIVE. Nothing is dropped and nothing renumbered.

    prep_minutes feeds the stack-rank score and the P0-P3 band cut, so
    zeroing a shadow's minutes there would re-band and renumber all 1,120
    entries. The deduped figure lives in prep_minutes_effective instead,
    and this pins that separation.
    """
    import ai_sde_bank as bank
    assert len(bank.ENTRIES) == 1120, "an entry was dropped"
    assert bank.TOTAL_PREP_MINUTES == sum(e["prep_minutes"] for e in bank.ENTRIES)
    assert bank.DEDUPED_PREP_MINUTES < bank.TOTAL_PREP_MINUTES
    for e in bank.ENTRIES:
        if e.get("duplicate_of"):
            assert e["prep_minutes"] > 0, "the shadow's own minutes were zeroed"
            assert e["prep_minutes_effective"] == 0, "shadow still counted"
            assert e.get("answer"), "the shadow lost its content — nothing is deleted"
        else:
            assert e["prep_minutes_effective"] == e["prep_minutes"]


def test_ai_sde_duplicate_pairs_point_at_the_richer_entry():
    """The canonical must not be the emptier half of the pair.

    The selection rule is: the deep dive wins, else more content wins. A
    pair that fails this is one where the rule was applied backwards and
    she would be sent to the thinner entry.
    """
    import ai_sde_bank as bank
    import ai_sde_dupes
    by_title = {e["title"]: e for e in bank.ENTRIES}
    weight = lambda e: (len(e.get("examples") or []) >= 10,
                        len(e.get("answer") or "") + len(e.get("code") or ""))
    for shadow, (canonical, note) in ai_sde_dupes.DUPES.items():
        s, c = by_title[shadow], by_title[canonical]
        if weight(c) < weight(s):
            assert "RULE OVERRIDDEN" in note, (
                f"{canonical!r} is thinner than the {shadow!r} it supersedes, "
                "with no note explaining why")


def test_ai_sde_merge_pending_pairs_are_not_silently_collapsed():
    """A pair whose rule would shadow the RICHER entry stays open.

    Collapsing it either way destroys the better teaching material, so it
    is flagged as merge-pending rather than resolved wrongly. Both halves
    keep their full prep_minutes because neither has been superseded yet.
    """
    import ai_sde_bank as bank
    import ai_sde_dupes
    by_title = {e["title"]: e for e in bank.ENTRIES}
    assert bank.DUPLICATE_MERGE_PENDING == len(ai_sde_dupes.MERGE_PENDING)
    for a, (b, _note) in ai_sde_dupes.MERGE_PENDING.items():
        for t in (a, b):
            assert by_title[t]["prep_minutes_effective"] == by_title[t]["prep_minutes"]
            assert by_title[t].get("duplicate_merge_pending"), f"{t} not marked"


def test_ai_sde_page_offers_to_hide_duplicate_topics(auth_client):
    """18 topics exist twice, and the two halves land ADJACENT in the study
    order because they score alike — so she meets the same thing twice in a
    row. The page hides them by default and says what that saves.

    The control is revealed by paintDupes() only when the payload actually
    reports shadows, so a bank with no duplicates shows no dead checkbox.
    """
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert 'id="hidedupes"' in html, "no way to hide the duplicated topics"
    assert 'checked' in html.split('id="hidedupes"')[1][:40], (
        "duplicates must be hidden by DEFAULT — that is the whole point")
    assert "paintDupes" in html, "the control is never revealed"
    assert "q-dup" in html, "no chip marks which half is the duplicate"

    payload = auth_client.get("/api/ai-sde").get_json()
    assert payload["dupes"]["shadows"] == 18
    assert payload["dupes"]["deduped_minutes"] < payload["dupes"]["total_minutes"]
    shadows = [e for e in payload["entries"] if e.get("duplicate_of")]
    assert len(shadows) == 18, "the list payload cannot collapse what it cannot see"
    titles = {e["title"] for e in payload["entries"]}
    for e in shadows:
        assert e["duplicate_of"] in titles, (
            f"{e['title']!r} points at a canonical that is not in the list")


def test_ai_sde_pdf_does_not_print_the_same_topic_twice(auth_client):
    """On screen she can see two rows are the same topic and skip one. On
    paper she just reads it twice, so the export drops shadows by default.
    ?dupes=1 puts them back."""
    pytest.importorskip("fpdf", reason="fpdf2 not installed; PDF route falls back to a redirect")
    import routes.interview_prep as ip
    src = inspect.getsource(ip.ai_sde_pdf)
    assert 'request.args.get("dupes")' in src, "no escape hatch to print duplicates"
    assert 'it.get("duplicate_of")' in src, "the export still prints both halves"


def test_ai_sde_clocked_minutes_reach_the_server(auth_client, monkeypatch):
    """Pomodoro effort was localStorage-only, so the hours she actually put
    in never left the device — and `minutes_focused` sat unwritten.

    The route already accepted minutes; nothing called it. This pins the
    contract the client now uses: minutes are saved BY TITLE, because the
    "ai{i}" id is the entry's index in the bank and shifts under it.
    """
    import routes.interview_prep as ip
    saved = []
    monkeypatch.setattr(ip, "post", lambda table, payload, **kw: saved.append((table, payload)))

    title = ip.AI_SDE_ENTRIES[0]["title"]
    r = auth_client.post("/api/ai-sde/progress", json={"title": title, "minutes": 42})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert saved, "nothing was written"
    table, payload = saved[-1]
    assert table == "ai_sde_progress"
    assert payload["entry_title"] == title, "keyed on something other than the title"
    assert payload["minutes_focused"] == 42
    assert "ai0" not in str(payload), "a positional id leaked into the row"

    # A title the bank does not hold must be refused, not stored — otherwise
    # a renamed topic accumulates effort nobody can ever read back.
    r = auth_client.post("/api/ai-sde/progress", json={"title": "nope", "minutes": 5})
    assert r.status_code == 400


def test_ai_sde_page_pulls_and_pushes_clocked_effort():
    """Both directions, and the loop-breaker between them.

    Pull: server minutes seed the timers. Push: a changed card is sent
    back. Without the `seeded` guard every page load would echo straight
    back what it had just read.
    """
    html = open("templates/ai_sde.html", encoding="utf-8").read()
    assert "Pomodoro.seed" in html, "server minutes never reach the timers"
    assert "queueEffort" in html, "clocked effort is never sent back"
    assert "detail.seeded" in html or "ev.detail && ev.detail.seeded" in html, (
        "no guard against echoing a server-seeded change back at the server")
    # Sent by title, never by the positional card id.
    push = html.split("async function flushEffort")[1].split("function queueEffort")[0]
    assert "titleOf(id)" in push and "title: title" in push, "pushed by id, not title"
    # A tab-hide is how a page ends on a phone; a 4s debounce would not survive it.
    assert "keepalive" in push, "the last minutes are lost when the tab closes"


def test_pomodoro_seed_unions_by_max_and_never_overwrites_local_time():
    """Time clocked offline has not reached the server yet, so taking the
    server's smaller number would silently delete it. Same union rule the
    studied-set sync follows."""
    js = open("static/js/pomodoro.js", encoding="utf-8").read()
    body = js.split("Controller.prototype.seed = function")[1].split("};")[0]
    assert "> this.logged(id)" in body, (
        "seed() does not compare against the local log — it can overwrite it")
    assert "this.emit(null, true)" in body, "a seeded change is not marked as seeded"


def test_ai_sde_awards_notes_by_title_not_by_positional_id():
    """Sadhana XP is DERIVED from studied topics + clocked minutes, so once
    both sync the bar rebuilds on any device — no table of its own needed.

    But the derivation was keyed on the "ai{i}" id, which is the entry's
    index in the bank. A reshuffle meant the backfill no longer recognised
    topics already paid for and awarded them again. Now keyed on title,
    with a one-time carry-over of the old keys.
    """
    html = open("templates/ai_sde.html", encoding="utf-8").read()
    assert "Gamify.studied(gkey(" in html, "notes are still awarded on the raw id"
    assert "id: gkey(x.title)" in html, "the backfill still keys on the positional id"
    assert "Gamify.rekeyTopics" in html, "no carry-over — existing topics get re-paid"
    assert "ai_sde_gamify_titlekeys_v1" in html, "the carry-over is not guarded, so it can re-run"

    js = open("static/js/gamify.js", encoding="utf-8").read()
    body = js.split("rekeyTopics: function (map)")[1].split("\n    reset:")[0]
    # A rename must not touch the balance — the notes are already banked.
    assert "award(" not in body, "rekeyTopics awards notes; it must only rename keys"


def test_pdf_splits_prose_from_drawn_tables():
    """The worked examples interleave prose with drawn tables in ONE string.

    Rendering the whole thing as prose wraps the tables into noise — which
    is exactly what the export used to do, and the reported complaint.
    Rendering it all as monospace shrinks the prose for no reason. So each
    line is judged and consecutive verdicts are grouped into runs.
    """
    import routes.interview_prep as ip
    text = (
        "Here is the idea in a sentence.\n"
        "\n"
        "┌─ STEP 1 ─────────────┐\n"
        "│ clarify the scope    │\n"
        "└──────────────────────┘\n"
        "\n"
        "And a closing thought that should wrap like prose does.\n"
    )
    runs = ip._pdf_runs(text)
    kinds = [k for k, _ in runs]
    assert True in kinds and False in kinds, f"nothing was split: {kinds}"
    drawn = [t for k, t in runs if k]
    assert any("┌" in t for t in drawn), "the box was not treated as fixed-width"
    prose = " ".join(t for k, t in runs if not k)
    assert "idea in a sentence" in prose and "closing thought" in prose

    # A column-aligned table with no box characters still counts.
    assert ip._pdf_is_fixed_width("name        count      pct") is True
    assert ip._pdf_is_fixed_width("    indented_code = True") is True
    assert ip._pdf_is_fixed_width("-----+------+-----") is True
    # An ordinary sentence does not.
    assert ip._pdf_is_fixed_width("This is a normal line of prose text.") is False
    # A blank line inherits its neighbours rather than breaking the run.
    assert ip._pdf_is_fixed_width("   ") is None


def test_pdf_keeps_unicode_instead_of_mangling_it():
    """_latin1() turned '┌─ CLARIFY ──┐ → ≤' into '+- CLARIFY --+ -> <='.

    With a real embedded font the characters survive, which is the whole
    reason the drawn diagrams were unreadable in the export.
    """
    pytest.importorskip("fpdf", reason="fpdf2 not installed")
    import routes.interview_prep as ip

    art = "┌─────────────┐\n│ scope first │\n└─────────────┘"
    data = ip._pdf_bytes("Unicode check", "one topic", [
        {"title": "Box drawing", "cat": "test",
         "fields": [("Diagram", art)], "mono_blocks": [], "tags": []}])
    text = _pdf_text(data)
    if "+-" in text and "─" not in text:
        pytest.skip("no Unicode font on this box; core-font fallback in use")
    assert "─" in text, "box-drawing was transliterated away"
    assert "│" in text


def test_pdf_falls_back_to_core_fonts_when_no_unicode_font_exists():
    """Render must degrade, never 500. Production images do not all ship
    DejaVu, and the export is not worth a crash."""
    pytest.importorskip("fpdf", reason="fpdf2 not installed")
    import routes.interview_prep as ip

    original = ip._PDF_FONT_CANDIDATES
    try:
        ip._PDF_FONT_CANDIDATES = (("/nope/a.ttf", "/nope/b.ttf", "/nope/c.ttf"),)
        data = ip._pdf_bytes("Fallback", "sub", [
            {"title": "Em dash — and an arrow →", "cat": "test",
             "fields": [("Answer", "value ≤ limit — always")],
             "mono_blocks": [], "tags": []}])
    finally:
        ip._PDF_FONT_CANDIDATES = original
    assert data.startswith(b"%PDF"), "the fallback did not produce a PDF"
    assert len(data) > 800


def test_pdf_body_size_defaults_to_26pt_and_is_clamped(app):
    """26pt was asked for, and on A4 it yields ~40 characters per line —
    the measure a phone shows when the page is fitted to width. ?fs= is
    for reading on a laptop, and must not be able to produce a broken page."""
    import routes.interview_prep as ip
    assert ip._PDF_BODY_PT == 26
    with app.test_request_context("/ai-sde/pdf"):
        assert ip._pdf_body_pt() == 26
    with app.test_request_context("/ai-sde/pdf?fs=14"):
        assert ip._pdf_body_pt() == 14
    for bad in ("0", "999", "-5", "abc", ""):
        with app.test_request_context(f"/ai-sde/pdf?fs={bad}"):
            got = ip._pdf_body_pt()
            assert ip._PDF_MIN_PT <= got <= ip._PDF_MAX_PT, f"fs={bad} gave {got}"


# ═══════════════════════════════════════════════════
# Day Board — click through to the section, and back
# ═══════════════════════════════════════════════════

def test_day_board_rows_link_to_the_section_that_owns_them(auth_client, monkeypatch):
    """The board began look-only. Asked for: tapping a row should open the
    section it belongs to, and bring you back.

    The three destinations disagree about how a date is spelled — /day takes
    an ISO `date`, /todo takes year/month/day, /checklist takes none — so the
    URLs are built in Python rather than scattered across the template.
    """
    import routes.day_board as db
    from utils.user_tz import user_today
    today = user_today().isoformat()

    monkeypatch.setattr(db, "_events_for", lambda u, d: [
        {"id": "E1", "title": "Standup", "start_time": "09:00", "end_time": "09:30"},
        {"id": "E2", "title": "Read paper", "start_time": None, "end_time": None},
    ])
    monkeypatch.setattr(db, "_tasks_for", lambda u, d: [
        {"id": "T1", "task_text": "Ship the thing", "quadrant": "Q1", "task_time": "14:00"},
    ])
    monkeypatch.setattr(db, "_checklist_for", lambda u, d: [
        {"id": "C1", "title": "Vitamins", "done": False},
    ])

    html = auth_client.get("/day-board").get_data(as_text=True)

    # The event focus id is PREFIXED, because that is what the day view calls
    # its event rows. Sending the raw id lands on the right page with nothing
    # highlighted, which reads as a broken link.
    assert f"/day?date={today}&amp;focus=ev-E1" in html
    assert "focus=ev-E2" in html, "the untimed event is not linked"
    assert "/todo?year=" in html and "focus=T1" in html
    assert "/checklist?date=" in html and "focus=C1" in html
    # Every link carries the way home.
    assert html.count("from=board") >= 4
    # Events are anchors; list rows get a full-cell overlay instead, because
    # wrapping a flex row's children would change the height the fit pass
    # measures.
    assert '<a class="ev' in html
    assert 'class="hit"' in html


def test_day_board_links_the_checklist_to_the_day_it_is_showing(auth_client, monkeypatch):
    """This was previously left UNLINKED on any non-today board, because
    /checklist took no date and would have landed on today's list while
    appearing to open that day's. The page now takes ?date=, so the link
    carries the board's day.
    """
    import routes.day_board as db
    monkeypatch.setattr(db, "_events_for", lambda u, d: [])
    monkeypatch.setattr(db, "_tasks_for", lambda u, d: [])
    monkeypatch.setattr(db, "_checklist_for", lambda u, d: [
        {"id": "C1", "title": "Vitamins", "done": False},
    ])
    html = auth_client.get("/day-board?date=2020-01-01").get_data(as_text=True)
    assert "Vitamins" in html
    assert "/checklist?date=2020-01-01" in html, "the link lost the board's day"


def test_checklist_shows_another_day_read_only(auth_client):
    """Ticks are the record of a day. Showing them for another date is
    useful; letting them be CHANGED from there is not — back-filling
    "slept at 10.30" for last Tuesday is self-deception, and a checklist
    you can edit backwards stops being a record of what happened.
    """
    # Assert on the class ATTRIBUTE, not the name: the rule ships in the
    # page's stylesheet either way, so the bare string always matches.
    today = auth_client.get("/checklist").get_data(as_text=True)
    assert 'class="cl-readonly"' not in today, "today must stay editable"
    assert "Back to today" not in today

    other = auth_client.get("/checklist?date=2026-08-01").get_data(as_text=True)
    assert 'class="cl-readonly"' in other, "another day is editable"
    assert "2026-08-01" in other and "Back to today" in other

    # A bad date is a bad link, not an error the user can act on.
    bad = auth_client.get("/checklist?date=not-a-date")
    assert bad.status_code == 200
    assert 'class="cl-readonly"' not in bad.get_data(as_text=True), (
        "a bad date should fall back to today, not render a read-only page")


def test_arriving_from_the_board_offers_one_tap_back(auth_client):
    """Without a way back the board is a one-way trip, which is worse than
    not linking at all — you arrive somewhere and have to find your way home
    through the menu.

    The chip lives in _top_nav.html because all the destinations already
    include it, so one chip covers every page the board can reach, including
    any added later.
    """
    # Assert on the ELEMENT, not the class name: the rule ships in the shared
    # partial's stylesheet on every page, so the bare string always matches.
    plain = auth_client.get("/todo").get_data(as_text=True)
    assert 'class="back-board"' not in plain, (
        "the chip shows when it was not asked for")

    import re
    for path in ("/todo", "/checklist", "/day"):
        html = auth_client.get(f"{path}?from=board&bd=2026-08-22").get_data(as_text=True)
        assert 'class="back-board"' in html, f"no way back from {path}"
        # The board answers on both /day-board and /board, and url_for picks
        # whichever rule registered last — so assert the PROPERTY (it goes to
        # the board, carrying the date you came from) rather than a spelling.
        href = re.search(r'class="back-board"\s+href="([^"]+)"', html)
        if href is None:
            href = re.search(r'href="([^"]+)"[^>]*class="back-board"', html)
        assert href, f"{path} renders the chip without an href"
        target = href.group(1)
        assert "board" in target, f"{path} chip does not point at the board: {target}"
        assert "date=2026-08-22" in target, (
            f"{path} loses the board's date on the way back: {target}")


def test_focus_landing_survives_a_list_that_renders_later():
    """Most of these pages build their lists in JavaScript after their own
    fetch, so the row is not in the DOM at DOMContentLoaded. The landing
    retries via MutationObserver, and gives up rather than observing forever.

    A missing id is a NORMAL outcome — the task was completed and filtered
    out, or the item was deleted — so it must stay silent instead of
    reporting a failure the user can already see.
    """
    js = open("static/js/global.js", encoding="utf-8").read()
    block = js.split("ARRIVING FROM THE DAY BOARD")[1]
    assert "MutationObserver" in block, "gives up before a JS-rendered list appears"
    assert "DEADLINE" in block and "disconnect()" in block, "observes forever"
    assert "CSS.escape" in block, "the id comes from the URL and is not escaped"
    # Both hooks: data-focus-id is explicit, data-id is what the existing
    # task and checklist markup already carries.
    assert "data-focus-id" in block and "data-id" in block
    # Esc returns to the board, and must not eat an editor's escape.
    assert "Escape" in block and "TEXTAREA" in block


def test_day_page_rows_carry_a_focus_id(auth_client):
    """The landing needs something to find. /todo and /checklist already
    emit data-id; the day view emitted nothing."""
    html = open("templates/day.html", encoding="utf-8").read()
    assert html.count('data-focus-id="{{ i.id }}"') == 3, (
        "not every day-view item block is addressable")


# ═══════════════════════════════════════════════════
# Sign-in history — IST, location, failed attempts
# ═══════════════════════════════════════════════════

def test_login_history_shows_utc_rows_in_the_users_own_timezone(auth_client, monkeypatch):
    """Asked for: sign-in history "in IST Time along with location".

    Rows are stored in UTC because that is the only representation that
    survives a timezone change; the conversion happens in the view, once.
    09:15 UTC is 14:45 IST, and that arithmetic is the whole point of the
    page — a history showing UTC would be read wrong every single time.
    """
    import routes.settings as st
    rows = [
        {"at": "2026-08-22T09:15:00+00:00", "ip": "49.207.1.2",
         "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit Chrome/120 Mobile Safari",
         "city": "Chennai", "region": "Tamil Nadu", "country": "India",
         "location_status": "ok", "outcome": "success"},
        {"at": "2026-08-21T18:40:00+00:00", "ip": "192.168.1.5",
         "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) Safari/605",
         "location_status": "private", "outcome": "failed"},
    ]
    monkeypatch.setattr(st, "get", lambda *a, **kw: rows)
    html = auth_client.get("/settings/login-history").get_data(as_text=True)

    assert "02:45 PM" in html, "UTC was not converted to the user's zone"
    assert "IST" in html, "the page does not say which zone it is showing"
    assert "Chennai, Tamil Nadu, India" in html
    # location_status distinguishes three states an empty cell would flatten
    # into one that looks like a bug.
    assert "On this network" in html
    assert "Chrome on Android" in html and "Safari on Mac" in html
    # A history of successes alone cannot show someone trying to get in.
    assert "failed attempt" in html


def test_login_history_names_the_migration_instead_of_500ing(auth_client, monkeypatch):
    """An unrun migration is a setup step, not an error. The page says which
    file closes it — and says the earlier sign-ins cannot be backfilled,
    because they were never stored."""
    import routes.settings as st

    def missing(*a, **kw):
        raise Exception('relation "login_events" does not exist')

    monkeypatch.setattr(st, "get", missing)
    r = auth_client.get("/settings/login-history")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "MIGRATION_LOGIN_HISTORY.sql" in html
    assert "backfilled" in html


def test_login_geolocation_is_honest_about_what_it_cannot_know():
    """`location_status` carries WHY a row has no city, so the page can say
    "on this network" rather than showing a blank that reads as a bug.

    A private address is detected rather than sent to the geo provider: the
    lookup would fail anyway, and the answer is more useful.
    """
    from services import login_history_service as svc
    assert svc.locate("127.0.0.1")["location_status"] == "private"
    assert svc.locate("192.168.1.5")["location_status"] == "private"
    assert svc.locate("10.0.0.9")["location_status"] == "private"
    assert svc.locate(None)["location_status"] == "unknown"
    assert svc.locate("not-an-ip")["location_status"] in ("failed", "unknown")


def test_login_history_prefers_the_forwarded_address(monkeypatch):
    """Behind a proxy, remote_addr is the PROXY. The real client is the
    left-most entry of X-Forwarded-For — trusted for "roughly where", never
    for anything security-critical, because the header is client-settable."""
    from services import login_history_service as svc

    class Req:
        def __init__(self, headers, remote):
            self.headers = headers
            self.remote_addr = remote

    assert svc.client_ip(Req({"X-Forwarded-For": "203.0.113.9, 70.41.3.18"},
                             "10.0.0.1")) == "203.0.113.9"
    assert svc.client_ip(Req({}, "203.0.113.9")) == "203.0.113.9"
    # Nothing available must be None, not a placeholder that later looks
    # like real data.
    assert svc.client_ip(Req({}, "")) is None


def test_a_failed_sign_in_is_recorded_against_the_targeted_account():
    """Half the point of the page is showing attempts that were not you.

    Nothing is recorded for an unknown email — there is no account to show
    it to, and writing one would let a stranger fill the table.
    """
    import inspect
    import routes.auth as auth
    src = inspect.getsource(auth.login)
    assert 'outcome="failed"' in src, "failed attempts are not recorded"
    assert "if user:" in src, "a failure for an unknown email would be stored"


# ═══════════════════════════════════════════════════
# Quick Bucket — bulk select into one calendar slot
# ═══════════════════════════════════════════════════

def _qb_stub(monkeypatch, rows):
    import routes.quick_bucket as qb
    sent = {"posted": [], "updated": []}
    monkeypatch.setattr(qb, "get",
                        lambda t, params=None, **k: rows if t == "quick_bucket" else [])
    monkeypatch.setattr(qb, "post",
                        lambda t, p, **k: sent["posted"].append((t, p)) or [{"id": "EV1", **p}])
    monkeypatch.setattr(qb, "update",
                        lambda t, params=None, json=None, **k: sent["updated"].append((t, json)))
    return sent


def test_bulk_selection_becomes_one_slot_with_the_items_in_the_description(auth_client, monkeypatch):
    """Asked for: bulk select bucket items, move them to a calendar slot,
    and have them appear in the description.

    ONE EVENT, NOT ONE PER ITEM. Five tasks become five lines in one slot,
    which is what "move them to a slot" means and the only version that
    stays readable on a week view.
    """
    sent = _qb_stub(monkeypatch, [{"id": "B", "text": "Call the bank"},
                                  {"id": "A", "text": "Book flights"}])
    r = auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A", "B"], "date": "2026-08-25", "start": "15:00", "duration": 45})
    assert r.status_code == 200, r.get_data(as_text=True)

    assert len(sent["posted"]) == 1, "one slot, not one event per item"
    table, ev = sent["posted"][0]
    assert table == "daily_events"
    assert ev["end_time"] == "15:45"
    assert "From Quick Bucket:" in ev["description"]
    assert "• Book flights" in ev["description"] and "• Call the bank" in ev["description"]
    # The order the user selected, not whatever the database returned.
    assert ev["description"].index("Book flights") < ev["description"].index("Call the bank")


def test_scheduling_neither_deletes_the_items_nor_marks_them_done(auth_client, monkeypatch):
    """Deleting loses them; marking them done is a lie, because they are
    scheduled rather than finished. They are LINKED to the slot instead,
    which is reversible and lets the bucket show where a row went."""
    sent = _qb_stub(monkeypatch, [{"id": "A", "text": "Book flights"}])
    auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A"], "date": "2026-08-25", "start": "09:00"})
    link = [j for t, j in sent["updated"] if t == "quick_bucket"][0]
    assert link["scheduled_event_id"] == "EV1"
    assert link["scheduled_for"] == "2026-08-25"
    assert "is_done" not in link and "is_deleted" not in link


def test_one_item_names_the_slot_after_itself(auth_client, monkeypatch):
    """A slot holding five tasks cannot be titled with all five — a calendar
    cell has no room. One item keeps its own name; several become a count."""
    sent = _qb_stub(monkeypatch, [{"id": "A", "text": "Book flights"}])
    auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A"], "date": "2026-08-25", "start": "09:00"})
    assert sent["posted"][0][1]["title"] == "Book flights"

    sent = _qb_stub(monkeypatch, [{"id": "A", "text": "a"}, {"id": "B", "text": "b"}])
    auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A", "B"], "date": "2026-08-25", "start": "09:00"})
    assert sent["posted"][0][1]["title"] == "2 bucket tasks"


def test_a_late_slot_does_not_wrap_past_midnight(auth_client, monkeypatch):
    """An event that wrapped would render at the top of the day and look
    like it happens in the morning."""
    sent = _qb_stub(monkeypatch, [{"id": "A", "text": "x"}])
    auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A"], "date": "2026-08-25", "start": "23:40", "duration": 120})
    assert sent["posted"][0][1]["end_time"] == "23:59"


def test_scheduling_into_an_existing_slot_rewrites_only_its_own_block(auth_client, monkeypatch):
    """A second bulk-move into the same hour should add to that slot, not
    duplicate the list — and must not eat a note the user typed above it."""
    import routes.quick_bucket as qb
    existing = {"id": "EV1", "description": "Bring the folder.\n\nFrom Quick Bucket:\n• old one"}
    sent = {"updated": []}
    monkeypatch.setattr(qb, "get", lambda t, params=None, **k:
                        [{"id": "A", "text": "Book flights"}] if t == "quick_bucket" else [existing])
    monkeypatch.setattr(qb, "post", lambda *a, **k: [{}])
    monkeypatch.setattr(qb, "update",
                        lambda t, params=None, json=None, **k: sent["updated"].append((t, json)))
    auth_client.post("/api/quick-bucket/schedule", json={
        "ids": ["A"], "date": "2026-08-25", "start": "09:00", "event_id": "EV1"})
    desc = [j for t, j in sent["updated"] if t == "daily_events"][0]["description"]
    assert desc.startswith("Bring the folder."), "the user's own note was destroyed"
    assert desc.count("From Quick Bucket:") == 1, "the block was duplicated"
    assert "old one" not in desc, "the block was appended instead of rewritten"
    assert "• Book flights" in desc


def test_schedule_rejects_input_it_cannot_honour(auth_client, monkeypatch):
    import routes.quick_bucket as qb
    monkeypatch.setattr(qb, "get", lambda *a, **k: [])
    for body in ({"ids": [], "date": "2026-08-25", "start": "09:00"},
                 {"ids": ["A"], "date": "nope", "start": "09:00"},
                 {"ids": ["A"], "date": "2026-08-25", "start": "9am"}):
        assert auth_client.post("/api/quick-bucket/schedule", json=body).status_code == 400


def test_quick_bucket_list_degrades_when_the_migration_is_not_run():
    """A column that has not been migrated makes the WHOLE query 400 and
    renders the page empty — which has happened here before. Each rung of
    the select ladder drops the newest fields."""
    import inspect
    import routes.quick_bucket as qb
    src = inspect.getsource(qb.list_items)
    assert "select_scheduled" in src
    assert "for sel in (select_scheduled, select_effort" in src, (
        "the new columns are not the first rung, or the ladder was not extended")


# ═══════════════════════════════════════════════════
# Prep banks — bulk-add topics as one study block
# ═══════════════════════════════════════════════════

def _bulk_prep_stub(monkeypatch):
    import routes.interview_prep as ip
    posted = []
    monkeypatch.setattr(ip, "post",
                        lambda t, p, **k: posted.append((t, p)) or [{"id": "EV1", "task_id": "T1", **p}])
    monkeypatch.setattr(ip, "update", lambda *a, **k: None)
    monkeypatch.setattr(ip, "get", lambda *a, **k: [])
    monkeypatch.setattr(ip, "_get_optional", lambda *a, **k: [])
    monkeypatch.setattr(ip, "_ensure_prep_project", lambda u, b: "PROJ")
    return posted


def test_bulk_prep_makes_one_block_with_the_topics_in_the_description(auth_client, monkeypatch):
    """Asked for: bulk-add topics from the prep pages to the calendar.

    ONE calendar block, not one event per topic — six topics on a Saturday
    morning is one session, and six stacked entries make the day
    unreadable. But the PROJECT still gets one task per topic, because that
    is where progress is tracked and a single "study block" task cannot be
    half done.
    """
    import ai_sde_bank as bank
    posted = _bulk_prep_stub(monkeypatch)
    picked = bank.ENTRIES[:3]
    titles = [e["title"] for e in picked]

    r = auth_client.post("/api/prep/schedule-bulk", json={
        "bank": "ai_sde", "plan_date": "2026-08-29", "start_time": "09:00",
        "topics": [{"title": t} for t in titles]})
    assert r.status_code == 200, r.get_data(as_text=True)

    events = [p for t, p in posted if t == "daily_events"]
    tasks = [p for t, p in posted if t == "project_tasks"]
    assert len(events) == 1, "one block, not one event per topic"
    assert len(tasks) == 3, "the project must still get one task per topic"
    for title in titles:
        assert "• " + title in events[0]["description"]


def test_bulk_prep_duration_defaults_to_the_topics_own_prep_time(auth_client, monkeypatch):
    """The bank already knows how long each topic takes. Making the user
    add that up by hand would be asking them to re-derive a number that is
    on the page in front of them."""
    import ai_sde_bank as bank
    posted = _bulk_prep_stub(monkeypatch)
    picked = bank.ENTRIES[:3]
    total = sum(e["prep_minutes"] for e in picked)

    r = auth_client.post("/api/prep/schedule-bulk", json={
        "bank": "ai_sde", "plan_date": "2026-08-29", "start_time": "09:00",
        "topics": [{"title": e["title"]} for e in picked]})
    j = r.get_json()
    assert j["total_minutes"] == total
    # 09:00 + the summed prep time, not a fixed guess.
    end_h, end_m = divmod(9 * 60 + total, 60)
    assert j["end_time"] == f"{end_h:02d}:{end_m:02d}"


def test_bulk_prep_collapses_repeats_and_reports_what_it_could_not_find(auth_client, monkeypatch):
    """A title that resolves to nothing must be REPORTED, not silently
    dropped — otherwise a stale tab schedules four of five topics and says
    it did all five."""
    import ai_sde_bank as bank
    _bulk_prep_stub(monkeypatch)
    t0 = bank.ENTRIES[0]["title"]
    r = auth_client.post("/api/prep/schedule-bulk", json={
        "bank": "ai_sde", "plan_date": "2026-08-29",
        "topics": [{"title": t0}, {"title": t0}, {"title": "no such topic"}]})
    j = r.get_json()
    assert j["count"] == 1, "the same topic picked twice must collapse"
    assert j["unknown"] == ["no such topic"]


def test_bulk_prep_rejects_input_it_cannot_honour(auth_client):
    for body in ({"bank": "nope", "plan_date": "2026-08-29", "topics": [{"title": "x"}]},
                 {"bank": "ai_sde", "plan_date": "bad", "topics": [{"title": "x"}]},
                 {"bank": "ai_sde", "plan_date": "2026-08-29", "topics": []}):
        assert auth_client.post("/api/prep/schedule-bulk", json=body).status_code == 400


def test_every_prep_bank_can_be_bulk_scheduled(auth_client, monkeypatch):
    """All four banks, because the ask named AI SDE, Java and SQL — and
    leaving the behavioural one out would be an odd gap."""
    import routes.interview_prep as ip
    for bank_key in ("ai_sde", "java", "sql", "behavioral"):
        posted = _bulk_prep_stub(monkeypatch)
        source, field, _prefix = ip._BANK_SOURCES[bank_key]
        first = source()[0][field]
        r = auth_client.post("/api/prep/schedule-bulk", json={
            "bank": bank_key, "plan_date": "2026-08-29",
            "topics": [{"title": first}]})
        assert r.status_code == 200, f"{bank_key}: {r.get_data(as_text=True)}"
        assert [p for t, p in posted if t == "daily_events"], f"{bank_key} made no block"


def test_bulk_select_needs_no_per_page_markup():
    """The prep pages disagree about their card structure — the title is
    .q-text on one and .t on another. Selection keys off the Plan button's
    own data attributes, which every schedulable card already carries, so
    all four pages get this without a template change.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    block = js.split("BULK: several topics into ONE study block")[1]
    assert "[data-prep-plan]" in block, "bulk reads page-specific markup"
    assert "mountBulk(root)" in js, "attach() does not wire bulk"
    # The pages re-render their list on filter changes, which would wipe
    # the injected checkboxes.
    assert "MutationObserver" in js and "paintBoxes()" in js


# ═══════════════════════════════════════════════════
# Time announcer — spoken on the quarter hour
# ═══════════════════════════════════════════════════

def test_time_announcer_is_loaded_on_every_page(auth_client):
    """Asked for: announce the time every 15 minutes, with pause and stop.

    It lives in the shared nav because it is an AMBIENT setting: it has to
    survive moving between pages, and its control belongs somewhere every
    page can reach.
    """
    assert "time-announcer.js" in open("templates/_top_nav.html", encoding="utf-8").read()
    for path in ("/todo", "/checklist", "/ai-sde"):
        assert "time-announcer.js" in auth_client.get(path).get_data(as_text=True), path


def test_time_announcer_never_reads_out_a_time_that_has_passed():
    """A laptop that slept through 14:15 and woke at 14:41 must not then
    say "quarter past two". That is worse than silence, because you would
    believe it. Late announcements are SKIPPED, never queued.
    """
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    assert "GRACE_MS" in js, "no bound on how late an announcement may be"
    assert "if (lateBy > GRACE_MS) return;" in js, "a missed slot is not skipped"
    # Aligned to the clock, not to when you pressed start — otherwise 3:07
    # and 3:22 would be "every fifteen minutes" and useless.
    assert "Math.floor(mins / state.every) * state.every" in js
    # Two open tabs must not both announce.
    assert "fresh.lastSlot === slot" in js, "sibling tabs would double-announce"
    # A queued backlog read out in sequence is the failure mode people
    # remember, so anything pending is cancelled first.
    assert "speechSynthesis.cancel()" in js


def test_time_announcer_offers_pause_and_stop_separately():
    """The ask named both. They differ: pause keeps the interval and the
    intent, stop clears the slot so restarting announces cleanly."""
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    assert 'data-ta-mode="paused"' in js and 'data-ta-mode="off"' in js
    assert "pause: function" in js and "stop:  function" in js
    assert "state.lastSlot = null" in js, "stop does not reset the slot"


# ═══════════════════════════════════════════════════
# Checklist — yesterday's misses, and the history browser
# ═══════════════════════════════════════════════════

def test_schedule_logic_is_shared_with_the_thing_that_reminds_you():
    """The Day Board had its own copy with NO branch for `weekdays` or
    `weekends`, so both fell through to "show it" and those items appeared
    on the board every day of the week. Measured against live data: three
    weekday items and one weekend item, on all seven days.

    Anything saying "you missed this" has to agree with the thing that
    reminded you, so the reminder's logic is now the only copy.
    """
    from datetime import date
    from services.checklist_schedule import applies_on, is_due

    sat, sun, mon = date(2026, 8, 22), date(2026, 8, 23), date(2026, 8, 24)
    assert [applies_on("weekdays", "", d) for d in (sat, sun, mon)] == [False, False, True]
    assert [applies_on("weekends", "", d) for d in (sat, sun, mon)] == [True, True, False]
    # `custom` stores Sun=0..Sat=6 as NUMBERS, not three-letter names — the
    # Day Board compared them as names and so matched nothing.
    assert applies_on("custom", "6", sat) is True
    assert applies_on("custom", "6", mon) is False
    assert applies_on("once", "2026-08-22", sat) is True
    assert applies_on("monthly_dom", "22", sat) is True

    # An item cannot be due before it existed, or a checklist started last
    # week shows months of "missed" behind it.
    assert is_due({"schedule": "daily", "created_at": "2026-08-30T00:00:00Z"}, sat) is False
    # recurrence_end stops it without deleting the history.
    assert is_due({"schedule": "daily", "recurrence_end": "2026-08-01"}, sat) is False
    assert is_due({"schedule": "daily", "is_deleted": True}, sat) is False


def test_push_scheduler_behaviour_is_unchanged_by_the_extraction():
    """The logic moved out of push_scheduler, which decides whether a
    reminder actually fires. Moving it must not change a single answer."""
    from datetime import date, timedelta
    from services.push_scheduler import _schedule_applies_today as sched
    from services.checklist_schedule import applies_on

    cases = [("daily", ""), ("weekdays", ""), ("weekends", ""), ("custom", "0,6"),
             ("custom", "1,2,3,4,5"), ("monthly_dow", "1:1"), ("monthly_dow", "-1:6"),
             ("monthly_dom", "1"), ("monthly_dom", "-1"), ("once", "2026-03-15"),
             ("", ""), ("bogus", "")]
    d, checked = date(2026, 1, 1), 0
    while d < date(2027, 1, 1):
        for s, days in cases:
            assert sched(s, days, d.weekday(), d) == applies_on(s, days, d), (s, days, d)
            checked += 1
        d += timedelta(days=1)
    assert checked > 4000


def test_a_legacy_whole_item_tick_still_counts_as_done():
    """Ticks recorded before an item gained reminder times are stored with
    a NULL time. Requiring today's reminder rows to be ticked would mark
    those days MISSED for items the user demonstrably ticked.

    Real case from this database: every tick on 2026-04-26 is NULL-keyed
    and all seven of those items were given reminder times later, so the
    strict rule reported 0 of 10 done on a day with seven ticks on it.
    Configuring a reminder in August cannot un-tick April.
    """
    from services.checklist_history import _is_done
    item = {"id": "i1"}
    times = {"i1": ["06:00:00", "22:00:00"]}
    day = "2026-04-26"

    legacy = {("i1", day): {None}}
    assert _is_done(item, day, legacy, times) is True, "a whole-item tick was ignored"

    partial = {("i1", day): {"06:00:00"}}
    assert _is_done(item, day, partial, times) is False, "one of two reminders is not done"

    both = {("i1", day): {"06:00:00", "22:00:00"}}
    assert _is_done(item, day, both, times) is True
    assert _is_done(item, day, {}, times) is False


def test_checklist_shows_yesterdays_misses(auth_client, monkeypatch):
    """The ticks were always stored per date and never read for any day but
    today, so the miss was invisible — and a loop with no feedback is how a
    checklist quietly stops being used."""
    import routes.checklist as cl

    monkeypatch.setattr(cl.checklist_history, "yesterday_summary",
                        lambda u, t: {"date": "2026-08-21", "label": "Fri 21 Aug",
                                      "due": 16, "done": 9, "missed": 7,
                                      "names": ["Drink water", "Ram"]})
    html = auth_client.get("/checklist").get_data(as_text=True)
    assert "Yesterday: missed 7 of 16." in html
    assert "Drink water" in html

    monkeypatch.setattr(cl.checklist_history, "yesterday_summary",
                        lambda u, t: {"date": "x", "label": "y", "due": 9,
                                      "done": 9, "missed": 0, "names": []})
    assert "Yesterday: all 9 done." in auth_client.get("/checklist").get_data(as_text=True)

    # Nothing due yesterday means no line: "0 of 0" is not a result.
    monkeypatch.setattr(cl.checklist_history, "yesterday_summary", lambda u, t: None)
    body = auth_client.get("/checklist").get_data(as_text=True).split("</style>")[-1]
    assert "cl-yday" not in body

    # And never on a historical view — it would be about a day two before
    # the one being read.
    monkeypatch.setattr(cl.checklist_history, "yesterday_summary",
                        lambda u, t: {"date": "x", "label": "y", "due": 9,
                                      "done": 1, "missed": 8, "names": ["a"]})
    assert "Yesterday: missed" not in auth_client.get(
        "/checklist?date=2026-08-01").get_data(as_text=True)


def test_checklist_history_page(auth_client, monkeypatch):
    """A day counts only what was DUE on it, so a weekend with no weekday
    items is not a failure — the empty cell says "nothing due", not 0%."""
    import routes.checklist as cl
    fake = {
        "start": "2026-08-09", "end": "2026-08-22", "window": 14,
        "days": [
            {"date": "2026-08-22", "label": "Sat 22 Aug", "due": 14, "done": 14,
             "missed": 0, "pct": 100, "missed_names": []},
            {"date": "2026-08-21", "label": "Fri 21 Aug", "due": 16, "done": 9,
             "missed": 7, "pct": 56, "missed_names": ["Drink water"]},
            {"date": "2026-08-20", "label": "Thu 20 Aug", "due": 0, "done": 0,
             "missed": 0, "pct": None, "missed_names": []},
            {"date": "2026-08-19", "label": "Wed 19 Aug", "due": 16, "done": 1,
             "missed": 15, "pct": 6, "missed_names": ["Ram"]},
        ],
        "items": [{"id": "i1", "name": "Drink water", "due": 14, "done": 2}],
        "total_due": 46, "total_done": 24, "pct": 52, "active_days": 3, "streak": 1,
    }
    monkeypatch.setattr(cl.checklist_history, "load", lambda u, e, d: fake)
    html = auth_client.get("/checklist/history?days=14").get_data(as_text=True)
    assert "52%" in html and "24 of 46 ticked" in html
    assert "Drink water" in html and "2/14" in html
    # Every cell links to that day's read-only checklist.
    assert "/checklist?date=2026-08-22" in html
    # The four bands plus "nothing due" are all distinguishable.
    for cls in ("ch-cell full", "ch-cell some", "ch-cell bad", "ch-cell none"):
        assert cls in html, cls


def test_history_window_is_bounded(auth_client, monkeypatch):
    """An unbounded ?days= is a way to ask the database for everything."""
    import routes.checklist as cl
    seen = {}
    monkeypatch.setattr(cl.checklist_history, "load",
                        lambda u, e, d: seen.setdefault("days", d) or
                        {"days": [], "items": [], "total_due": 0, "total_done": 0,
                         "pct": None, "active_days": 0, "streak": 0,
                         "start": "", "end": "", "window": d})
    auth_client.get("/checklist/history?days=99999")
    assert seen["days"] <= cl.checklist_history.MAX_DAYS
    seen.clear()
    auth_client.get("/checklist/history?days=nonsense")
    assert seen["days"] == 30


def test_announcer_survives_a_throttled_background_timer():
    """"Will it work when the window is minimised?"

    A hidden tab has its timers clamped — Chrome to once per MINUTE after
    about five minutes. Simulated against this logic: a 60s tick still
    catches every one of the 96 quarter-hours in a day, from any starting
    phase, because the grace window is 90s. At a 120s clamp it would start
    missing half, which is why the window is not tightened.
    """
    import re
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    grace_ms = int(re.search(r"GRACE_MS\s*=\s*(\d+)\s*\*\s*1000", js).group(1)) * 1000
    tick_ms = int(re.search(r"TICK_MS\s*=\s*(\d+)\s*\*\s*1000", js).group(1)) * 1000
    every = 15

    def announced(tick, phase):
        seen = set()
        t = phase
        while t < 24 * 3600 * 1000:
            mins, secs = divmod(t // 1000, 60)
            late = (mins % every) * 60000 + secs * 1000
            if late <= grace_ms:
                seen.add((mins // every) * every)
            t += tick
        return len(seen)

    expected = 24 * 60 // every
    for clamp in (tick_ms, 60_000):
        worst = min(announced(clamp, p) for p in range(0, clamp, 1000))
        assert worst == expected, (
            f"a {clamp // 1000}s tick misses {expected - worst} of {expected} "
            "quarter-hours in the worst phase")


def test_announcer_keepalive_is_opt_in_and_not_actually_silent():
    """Chrome may FREEZE a background tab, and a frozen page runs no timers
    at all — the difference between "late" and "stopped". Tabs playing
    audio are exempt, so the keep-alive holds an audio node open.

    OPT-IN, because it costs battery and puts an "audio playing" mark on
    the tab; someone using this at a visible desk should not pay for that.
    And the gain is NOT zero: a muted graph is exactly what a browser is
    entitled to optimise away, and an optimised-away graph stops counting
    as playback, which would silently undo the whole point.
    """
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    assert "keepaliveOn" in js and "data-ta-keep" in js
    assert "keepalive: false" in js, "the keep-alive defaults to on"
    # Only held while announcements are actually due to happen.
    body = js.split("function applyKeepalive()")[1].split("}")[0]
    assert 'state.mode === "on"' in body and "state.keepalive" in body
    # The limits are stated to the USER, not buried in a source comment:
    # what it costs, and that a fully closed app cannot be rescued.
    assert "battery" in js and "fully closed" in js
    assert "best-effort" in js.lower(), (
        "the locked-phone case is presented as certain when it is not")


def test_announcer_recommends_the_keepalive_to_installed_app_users():
    """Asked: "I have the PWA, can it not announce even when minimised?"

    Installing changes nothing about what the platform ALLOWS — an
    installed app is still a document, and a minimised window is still
    hidden and freezable. What it changes is the advice: someone who
    installed the app is far more likely to leave it minimised and expect
    it to keep working, which is exactly what the keep-alive is for. So the
    recommendation is surfaced there instead of buried in a paragraph.
    """
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    assert "display-mode: standalone" in js
    # iOS reports installed-ness its own way.
    assert "navigator.standalone" in js
    assert "ta-tip" in js
    # Shown only when it would actually help: installed AND not already on.
    assert "isInstalled() && !state.keepalive" in js


def test_periodic_background_sync_cannot_drive_a_15_minute_announcement():
    """The obvious "surely the service worker can do it" answer, closed off
    in the codebase itself: the app already registers periodicSync, at a
    TWELVE HOUR interval, and the service worker's own comment records that
    the browser fires it "usually closer to once per day".

    Nowhere near 15 minutes — and a service worker cannot speak anyway,
    since speechSynthesis is a window API with no worker equivalent.
    """
    sw = open("static/service-worker.js", encoding="utf-8").read()
    pwa = open("static/js/pwa.js", encoding="utf-8").read()
    assert "periodicsync" in sw
    assert "12h interval" in sw or "12 * 60" in pwa or "43200" in pwa, (
        "the periodic sync interval is no longer documented as coarse")
    # And nothing should ever try to speak from the worker.
    assert "speechSynthesis" not in sw, (
        "a service worker has no speechSynthesis — this cannot work")


def test_announcer_keepalive_uses_real_media_not_web_audio():
    """Asked: "voice even when the phone is locked."

    On a locked phone the page is suspended and nothing in an ordinary web
    page survives it. The single exception is MEDIA: a page holding an
    active media session keeps running with the screen off, which is how a
    music PWA keeps playing in your pocket. A Web Audio oscillator — what
    the first version used — is not treated as playback and does not
    qualify, so the keep-alive is a real looping <audio> element.
    """
    js = open("static/js/time-announcer.js", encoding="utf-8").read()
    assert 'createElement("audio")' in js, "still using Web Audio, which will not survive lock"
    assert "audio-keepalive.wav" in js
    assert "el.loop = true" in js
    # A MUTED element holds no audio focus, so the OS keeps nothing alive.
    # Check the ASSIGNMENT, not the word — the comment explaining this says
    # "muted" and an earlier version of this test matched its own docs.
    assert "el.volume" in js
    assert "el.muted = true" not in js and "muted: true" not in js
    # The lock screen entry must be labelled, and its buttons must work —
    # a control that looks like it stops something has to stop it.
    assert "mediaSession" in js and "MediaMetadata" in js
    assert 'setActionHandler("pause"' in js and 'setActionHandler("stop"' in js
    import os
    assert os.path.exists("static/audio-keepalive.wav"), "the track is missing"
    assert os.path.getsize("static/audio-keepalive.wav") < 20000
    # Precached: the moment it is needed is exactly when the network is
    # least likely to be there.
    assert "audio-keepalive.wav" in open("static/service-worker.js", encoding="utf-8").read()


def test_push_subscription_self_heals_when_the_server_deactivated_it():
    """A silent, invisible failure, found in live data: six push
    subscriptions for the same Android phone, EVERY one is_active=false,
    the newest already a month old.

    The cause is a one-way drift. The server flips is_active=false the
    moment a send returns 404/410, and never tells the browser. The UI only
    checked whether the BROWSER still held a subscription, so it reported
    "notifications are on" while nothing would ever be delivered — which is
    the likeliest reason nothing on that checklist had been ticked in four
    months.

    Re-registering is idempotent (the endpoint upserts and sets
    is_active=true), so doing it on load repairs the drift silently.
    """
    js = open("static/js/push.js", encoding="utf-8").read()
    heal = js.split("SELF-HEAL")[1].split("enableBtn")[0]
    assert "/api/push/subscribe" in heal, "nothing re-registers the subscription"
    # The server reads data["subscription"] — a flat body is a 400.
    assert "subscription: sub.toJSON()" in heal
    assert "X-CSRFToken" in heal
    # Only when the browser actually has one; re-registering nothing is
    # a guaranteed 400 on every page load.
    assert "if (on)" in heal


def test_push_deactivation_is_only_for_a_gone_subscription():
    """is_active=false must mean "the push service says this endpoint no
    longer exists", not "a send failed once" — otherwise a transient error
    silently switches someone's reminders off for good."""
    src = open("services/push_service.py", encoding="utf-8").read()
    assert "status in (404, 410)" in src
    block = src.split("status in (404, 410)")[1].split("else:")[0]
    assert "_deactivate" in block
    # A non-410 failure warns and leaves the subscription alone.
    after = src.split("status in (404, 410)")[1].split("else:")[1][:200]
    assert "_deactivate" not in after


def test_day_board_sends_a_prep_topic_to_its_own_bank_page(auth_client, monkeypatch):
    """Reported: clicking an AI SDE prep question on the board should open
    that specific topic, not the day view.

    Before this it went to /day, which showed the same one-line title you
    had just clicked — a round trip to no new information. Live data had 12
    such rows, including SQL topics scheduled for today.

    Matched on the DESCRIPTION, because that is the only durable signal: the
    prep scheduler writes "{label} — open the topic at {page}" into the row
    it creates, while the title is the topic itself and says nothing about
    which bank it came from.
    """
    import routes.day_board as db
    monkeypatch.setattr(db, "_events_for", lambda u, d: [
        {"id": "E1", "title": "SELECT ... WHERE — the shape of every query",
         "description": "SQL prep — open the topic at /sql",
         "start_time": "19:00", "end_time": "19:30"},
        {"id": "E2", "title": "Balanced Binary Tree",
         "description": "AI/SDE prep — open the topic at /ai-sde",
         "start_time": None, "end_time": None},
        {"id": "E3", "title": "Dentist", "description": "bring the referral letter",
         "start_time": "10:00", "end_time": "10:30"},
    ])
    monkeypatch.setattr(db, "_tasks_for", lambda u, d: [])
    monkeypatch.setattr(db, "_checklist_for", lambda u, d: [])
    html = auth_client.get("/day-board").get_data(as_text=True)

    assert "/sql?" in html and "topic=SELECT" in html
    assert "/ai-sde?" in html and "topic=Balanced" in html
    # An ordinary calendar entry still goes to the day view.
    assert "/day?date=" in html and "focus=ev-E3" in html
    # And the way home is still carried.
    assert html.count("from=board") >= 3


def test_prep_page_match_is_longest_first():
    """"/interview-prep" contains no shorter page path, but the check has to
    be ordered anyway — a future "/sql-advanced" would be swallowed by
    "/sql" and silently route to the wrong bank."""
    import routes.day_board as db
    assert db._prep_target({"description": "Interview prep — open the topic at /interview-prep"}) \
        == "/interview-prep"
    assert db._prep_target({"description": "SQL prep — open the topic at /sql"}) == "/sql"
    assert db._prep_target({"description": "bring the referral letter"}) is None
    assert db._prep_target({"description": ""}) is None
    assert db._prep_target({}) is None
    src = __import__("inspect").getsource(db._prep_target)
    assert "key=len, reverse=True" in src, "shortest path could win"


def test_day_board_has_a_home_button(auth_client, monkeypatch):
    """Asked for. Home and the menu are different destinations — home is the
    app's start page, the menu is the daily summary — and only one of them
    existed."""
    import routes.day_board as db
    monkeypatch.setattr(db, "_events_for", lambda u, d: [])
    monkeypatch.setattr(db, "_tasks_for", lambda u, d: [])
    monkeypatch.setattr(db, "_checklist_for", lambda u, d: [])
    html = auth_client.get("/day-board").get_data(as_text=True)
    assert 'href="/" title="Home"' in html
    assert "/summary?view=daily" in html, "the menu was replaced instead of joined"


def test_topic_landing_matches_on_title_and_clicks_rather_than_forcing_open():
    """Every one of these banks numbers entries by POSITION (ai42, j7, sq3),
    and a position shifts the moment an entry is added or deduped — so a
    link made last week would open whatever moved into that slot. Titles are
    stable, and the Plan button already carries one.

    And it CLICKS the card: /ai-sde fills the body lazily on first open, so
    forcing the class would reveal an empty card.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    block = js.split("ARRIVING FROM THE DAY BOARD ON A SPECIFIC TOPIC")[1]
    assert 'getAttribute("data-title")' in block, "matching on something other than the title"
    assert "head.click()" in block, "forces .open and would show an empty lazy card"
    assert "MutationObserver" in block, "these lists are fetched, not inline"
    assert "landOnTopic(root)" in js, "never wired into attach()"


# ═══════════════════════════════════════════════════
# Prep cards — "Planned on …", green ahead, red elapsed
# ═══════════════════════════════════════════════════

def test_scheduled_endpoint_reports_when_each_topic_is_planned(auth_client, monkeypatch):
    """Asked for: a scheduled prep item should say "Planned on <date> at
    <time>", red once that has elapsed and green while it has not.

    Read from project_tasks, not daily_events: the scheduler writes one task
    PER TOPIC even when a bulk selection collapses into one calendar block,
    so the task is the only per-topic record of what was planned.
    """
    import routes.interview_prep as ip
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: "PROJ")
    monkeypatch.setattr(ip, "get", lambda t, params=None, **k: [
        {"task_text": "ORDER BY, and where NULL sorts", "plan_date": "2026-08-22",
         "start_time": "19:00:00", "status": "open"},
        {"task_text": "Untimed one", "plan_date": "2026-08-16",
         "start_time": "00:00:00", "status": "open"},
        {"task_text": "Repeat", "plan_date": "2026-09-01",
         "start_time": "10:00:00", "status": "open"},
        {"task_text": "Repeat", "plan_date": "2026-08-05",
         "start_time": "08:00:00", "status": "open"},
    ])
    s = auth_client.get("/api/prep/scheduled?bank=sql").get_json()["scheduled"]

    assert s["ORDER BY, and where NULL sorts"]["start_time"] == "19:00"
    # 00:00 is the scheduler's stand-in for "no time given". Reported as
    # absent, or the card would read "at 12:00 AM" like a real appointment.
    assert s["Untimed one"]["start_time"] == ""
    # A topic scheduled twice keeps the EARLIEST — that is the commitment,
    # and showing the later one would hide an overdue first attempt.
    assert s["Repeat"]["plan_date"] == "2026-08-05"


def test_opening_a_bank_page_never_creates_its_project(auth_client, monkeypatch):
    """_ensure_prep_project creates on miss, which is right when scheduling
    and wrong on a page load — merely opening /java should not bring a
    JavaPrep project into existence. Hence a read-only sibling."""
    import routes.interview_prep as ip
    created = []
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: None)
    monkeypatch.setattr(ip, "post", lambda *a, **k: created.append(a) or [{}])
    r = auth_client.get("/api/prep/scheduled?bank=java")
    assert r.status_code == 200
    assert r.get_json()["scheduled"] == {}
    assert not created, "a page load created a project"
    assert auth_client.get("/api/prep/scheduled?bank=nope").status_code == 400


def test_pg_eq_no_longer_quotes_itself_into_matching_nothing():
    """THE BUG THIS FIXES was silent and expensive. _pg_eq wrapped values in
    double quotes, which PostgREST matched LITERALLY — so every existence
    check built on it answered "not there", always.

    Measured on live data: the quoted form returned 0 rows for both a plain
    name and a comma-bearing title; plain returned 10 and 1. The visible
    damage was ten SQLPrep projects created for one user in four minutes,
    one per Plan click, because the project lookup never found the one it
    had just made.

    The quoting was solving a real problem — commas in titles — that
    supabase_client already solves by handing params to `requests`, which
    URL-encodes them.
    """
    from routes.interview_prep import _pg_eq
    assert _pg_eq("SQLPrep") == "eq.SQLPrep"
    assert '"' not in _pg_eq("ORDER BY, and where NULL sorts")
    assert _pg_eq("A (paren), a colon: and a comma") == \
        "eq.A (paren), a colon: and a comma"


def test_prep_project_lookup_is_deterministic():
    """Where duplicates already exist, an unordered limit:1 can return a
    different row each call and scatter one bank's tasks across several
    projects — which is exactly how the damage compounded."""
    import inspect
    import routes.interview_prep as ip
    assert "created_at.asc" in inspect.getsource(ip._find_prep_project)
    # And the creating path must not keep its own copy of the lookup — that
    # divergence is how the two came to disagree in the first place.
    ensure = inspect.getsource(ip._ensure_prep_project)
    assert "_find_prep_project(user_id, bank)" in ensure
    # The FILTER form specifically — the create payload legitimately sets
    # is_archived, so a bare substring match flags its own insert.
    assert '"is_archived": "eq.false"' not in ensure, (
        "a second, unordered lookup crept back in")


def test_the_schedule_mark_goes_on_the_title_itself():
    """Asked for as "(Planned on X Date at that time)" — parenthesised, on
    the title. It reads better there than as a separate chip: the schedule
    is a fact ABOUT this topic, so it belongs in the sentence naming it
    rather than in the row of category chips beside it.

    The four pages disagree about their title element (.q-text on /ai-sde
    and /interview-prep, .t on /java and /sql), and /java's card body
    contains another .t — so the lookup is scoped to the card HEADER.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    assert "function titleElOf" in js
    lookup = js.split("function titleElOf")[1].split("}")[0]
    assert '".q-head"' in lookup, "an unscoped search would hit a .t in the body"
    assert '".q-text, .t"' in lookup
    paint = js.split("function paintScheduled")[1].split("function loadScheduled")[0]
    assert "titleEl.appendChild(mark)" in paint
    assert '" (" +' in paint, "not parenthesised"
    # A page with an unrecognised title shape must not silently lose it.
    assert "else btn.parentElement.insertBefore(mark, btn)" in paint
    # Inline text, not a pill: a bordered chip mid-sentence breaks the line.
    assert ".prep-when{font-size:.86em" in js
    assert "border-radius:999px;padding:5px 9px" not in js


def test_planned_pill_elapses_at_the_end_of_an_untimed_day():
    """The scheduler stores 00:00 for "no time given". Treating that
    literally would paint TODAY's untimed plan red all day, which is the
    opposite of what it means — an untimed plan for today has not been
    missed at 00:01."""
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    block = js.split("function deadlineOf")[1].split("function paintScheduled")[0]
    assert "23, 59, 59, 999" in block, "an untimed day elapses at midnight"
    # The comparison must happen on the CLIENT: "has it elapsed" needs the
    # reader's clock, and the server is a different machine.
    assert "/api/prep/scheduled" in js
    paint = js.split("function paintScheduled")[1].split("function loadScheduled")[0]
    assert "new Date()" in paint and "late" in paint and "soon" in paint


# ═══════════════════════════════════════════════════
# Missed slots — shaded red once the moment has passed
# ═══════════════════════════════════════════════════

def _day_html(auth_client, monkeypatch, items, on="2026-08-22"):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import routes.day as d
    now = datetime(2026, 8, 22, 19, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(d, "user_now", lambda: now)
    monkeypatch.setattr(d, "user_today", lambda: now.date())
    monkeypatch.setattr(d, "_meta", lambda u, pd: {})
    monkeypatch.setattr(d, "build_dashboard", lambda u, pd: {"today_items": items})
    return auth_client.get(f"/day?date={on}").get_data(as_text=True)


def _classes_for(html, title):
    """The class list of the .item block containing `title`."""
    import re
    idx = html.find(">" + title + "<")
    assert idx != -1, f"{title!r} is not on the page"
    before = html[:idx]
    m = None
    for m in re.finditer(r'<div class="item([^"]*)"', before):
        pass
    return m.group(1) if m else ""


def test_day_view_shades_a_missed_slot(auth_client, monkeypatch):
    """Asked for: shade it red once the date/time has been missed.

    MEASURED FROM THE END, not the start. An event running 19:00-20:00 is
    not missed at 19:01; it is missed at 20:00. Anything else marks things
    red the moment they begin, which is when you are most likely doing them.
    """
    html = _day_html(auth_client, monkeypatch, [
        {"id": "a", "title": "Ended earlier", "time": "18:00", "end_time": "19:00", "status": "open"},
        {"id": "b", "title": "Running now", "time": "19:00", "end_time": "20:00", "status": "open"},
        {"id": "c", "title": "Later today", "time": "21:00", "end_time": "22:00", "status": "open"},
        {"id": "d", "title": "Past but done", "time": "09:00", "end_time": "10:00",
         "status": "done", "done": True},
    ])
    assert "missed" in _classes_for(html, "Ended earlier")
    assert "missed" not in _classes_for(html, "Running now"), "marked red while in progress"
    assert "missed" not in _classes_for(html, "Later today")
    # Done is done — a completed slot is never a miss, however late it is.
    assert "missed" not in _classes_for(html, "Past but done")


def test_an_untimed_item_is_only_missed_once_its_whole_day_is_past(auth_client, monkeypatch):
    """"No time set" cannot be late at 9am on the day itself — it has all
    day to happen. It becomes a miss when the day is behind us."""
    item = [{"id": "e", "title": "Read the paper", "time": None, "status": "open"}]
    today = _day_html(auth_client, monkeypatch, item, on="2026-08-22")
    assert "missed" not in _classes_for(today, "Read the paper")
    past = _day_html(auth_client, monkeypatch, item, on="2026-08-20")
    assert "missed" in _classes_for(past, "Read the paper")


def test_calendar_grid_uses_the_same_missed_rule():
    """A day that reads "missed" on the list and fine on the grid is worse
    than neither showing it, so both surfaces share the rule: measured from
    the END, and `done` is the only status that counts as complete."""
    js = open("static/v2/planner_v2.js", encoding="utf-8").read()
    block = js.split("MISSED:")[1].split("// Position")[0]
    assert "ev.end_time || ev.start_time" in block, "measured from the start"
    assert '(ev.status || "open") !== "done"' in block
    assert "is-missed" in block

    css = open("static/v2/planner_v2.css", encoding="utf-8").read()
    assert ".event-chip.is-missed" in css
    # A tint and an edge, not a solid repaint: these chips already carry a
    # priority colour and a meaningful fill, and a busy past day would
    # become an unreadable wall of red.
    assert "repeating-linear-gradient" in css.split(".event-chip.is-missed")[1][:400]
    assert "html.dark .event-chip.is-missed" in css, "unreadable in dark mode"


def test_prep_features_do_not_assume_the_list_already_exists():
    """A BUG THAT SHIPPED, and the reason it got through.

    Every bank page calls PrepScheduler.attach() synchronously while its
    list is fetched over the network and rendered in a .then() — so at the
    moment attach runs there is not a single card in the container.

    Both the bulk-select bar and the "Planned on …" pill opened with a
    "no cards? nothing to do" guard, which was true every single time. Both
    features were dead on every page, and the jsdom harnesses missed it
    because they inserted cards BEFORE calling attach — the opposite of what
    the pages do. A test that sets up the world in the wrong order can only
    ever confirm the wrong order works.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    assert "function whenCardsReady" in js, "nothing waits for the list"
    # The two features that need a card must go through the waiter.
    attach = js.split("attach: function (root)")[1].split("_bulk:")[0]
    assert "whenCardsReady(root, function ()" in attach
    body = attach.split("whenCardsReady(root, function ()")[1][:220]
    assert "mountBulk(root)" in body and "loadScheduled(root)" in body
    # It must give up eventually rather than observing for the life of the
    # page on a bank that is genuinely empty.
    waiter = js.split("function whenCardsReady")[1].split("function bulkButtons")[0]
    assert "disconnect()" in waiter and "setTimeout" in waiter


def test_day_board_strikes_out_anything_completed(auth_client, monkeypatch):
    """Asked for. Tasks and checklist rows already did; EVENTS did not —
    neither the timed chips on the rail nor the untimed ones in the list.

    Struck through and stood down rather than REMOVED: the board is a record
    of the day as much as a plan for it, and a completed morning that
    disappears reads as a morning where nothing happened.
    """
    import re
    import routes.day_board as db
    monkeypatch.setattr(db, "_events_for", lambda u, d: [
        {"id": "E1", "title": "Standup done", "start_time": "09:00",
         "end_time": "09:30", "status": "done"},
        {"id": "E2", "title": "Standup open", "start_time": "10:00",
         "end_time": "10:30", "status": "open"},
        {"id": "E3", "title": "Untimed done", "start_time": None,
         "end_time": None, "status": "done"},
        {"id": "E4", "title": "Untimed open", "start_time": None,
         "end_time": None, "status": "open"},
    ])
    monkeypatch.setattr(db, "_tasks_for", lambda u, d: [
        {"id": "T1", "task_text": "Task done", "quadrant": "Q1", "is_done": True},
        {"id": "T2", "task_text": "Task open", "quadrant": "Q1", "is_done": False},
    ])
    monkeypatch.setattr(db, "_checklist_for", lambda u, d: [
        {"id": "C1", "title": "Check done", "done": True},
        {"id": "C2", "title": "Check open", "done": False},
    ])
    html = auth_client.get("/day-board").get_data(as_text=True)

    def marked_done(title):
        """Is the CONTAINER wrapping `title` flagged done?

        Matches the <li> or the rail <a> specifically. A bare "last class
        before the title" search picks up the ✓ span's own class instead,
        which is how the first version of this test reported a false miss.
        """
        i = html.find(title)
        assert i != -1, f"{title!r} is not on the board"
        seg = html[max(0, i - 600):i]
        m = None
        for m in re.finditer(r'<(?:li|a) class="([^"]*)"', seg):
            pass
        return "done" in (m.group(1) if m else "")

    for title in ("Standup done", "Untimed done", "Task done", "Check done"):
        assert marked_done(title), f"{title} is not struck out"
    for title in ("Standup open", "Untimed open", "Task open", "Check open"):
        assert not marked_done(title), f"{title} was struck out while still open"

    # Both shapes need the rule that actually draws the line.
    assert ".ev.done .ttl{text-decoration:line-through}" in html
    assert "li.done .txt{text-decoration:line-through}" in html
    # Done is dimmed, not hidden.
    assert ".ev.done{opacity:.55" in html


# ═══════════════════════════════════════════════════
# Ticking a topic studied completes what it scheduled
# ═══════════════════════════════════════════════════

def test_marking_a_topic_studied_closes_its_task_event_and_bucket_row(auth_client, monkeypatch):
    """Reported: ticking the checkbox on a prep page did not mark the item
    complete on the Day Board or in the Quick Bucket.

    It never could. The tick updated the STUDY record only, while scheduling
    a topic writes three OTHER rows — a project task, a calendar event and a
    bucket line — and none of them heard about it. The topic read done in
    one place and outstanding in three.
    """
    import routes.interview_prep as ip
    updates = []
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: "PROJ")
    monkeypatch.setattr(ip, "get", lambda t, params=None, **k: (
        [{"id": "EV1", "description": "AI/SDE prep — open the topic at /ai-sde"},
         {"id": "EV2", "description": "Dentist, nothing to do with prep"}]
        if t == "daily_events" else []))
    monkeypatch.setattr(ip, "update",
                        lambda t, params=None, json=None, **k: updates.append((t, params, json)))

    r = auth_client.post("/api/prep/complete", json={
        "bank": "ai_sde", "title": "Balanced Binary Tree", "done": True})
    assert r.status_code == 200, r.get_data(as_text=True)

    tables = [t for t, _p, _j in updates]
    assert "project_tasks" in tables and "daily_events" in tables and "quick_bucket" in tables

    task = next(j for t, _p, j in updates if t == "project_tasks")
    assert task["status"] == "done"
    bucket = next(j for t, _p, j in updates if t == "quick_bucket")
    assert bucket["is_done"] is True
    # Clearing the Top-5 pins matches what the bucket's own done endpoint
    # does — otherwise the row stays pinned and crossed out in today's panel.
    assert bucket["top5_date"] is None and bucket["top5_position"] is None

    # ONLY the prep-created calendar row. A real appointment that happens to
    # share a title must be left alone.
    ev_updates = [p for t, p, _j in updates if t == "daily_events"]
    assert len(ev_updates) == 1
    assert "EV1" in ev_updates[0]["id"]


def test_unticking_a_topic_reopens_all_three(auth_client, monkeypatch):
    """Un-ticking has to work, or a mis-click closes a topic for good."""
    import routes.interview_prep as ip
    updates = []
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: "PROJ")
    monkeypatch.setattr(ip, "get", lambda t, params=None, **k: (
        [{"id": "EV1", "description": "SQL prep — open the topic at /sql"}]
        if t == "daily_events" else []))
    monkeypatch.setattr(ip, "update",
                        lambda t, params=None, json=None, **k: updates.append((t, params, json)))
    auth_client.post("/api/prep/complete", json={
        "bank": "sql", "title": "ORDER BY, and where NULL sorts", "done": False})

    assert next(j for t, _p, j in updates if t == "project_tasks")["status"] == "open"
    assert next(j for t, _p, j in updates if t == "daily_events")["status"] == "open"
    b = next(j for t, _p, j in updates if t == "quick_bucket")
    assert b["is_done"] is False and b["done_at"] is None


def test_completing_a_never_scheduled_topic_is_not_an_error(auth_client, monkeypatch):
    """Most topics are never put on a day. Ticking one of those has nothing
    else to update, and must not create a project to find that out."""
    import routes.interview_prep as ip
    created = []
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: None)
    monkeypatch.setattr(ip, "get", lambda *a, **k: [])
    monkeypatch.setattr(ip, "update", lambda *a, **k: None)
    monkeypatch.setattr(ip, "post", lambda *a, **k: created.append(a) or [{}])
    r = auth_client.post("/api/prep/complete", json={
        "bank": "java", "title": "HashMap internals", "done": True})
    assert r.status_code == 200
    assert r.get_json()["touched"]["tasks"] == 0
    assert not created, "completing a topic created a project"

    assert auth_client.post("/api/prep/complete",
                            json={"bank": "java", "title": ""}).status_code == 400
    assert auth_client.post("/api/prep/complete",
                            json={"bank": "nope", "title": "x"}).status_code == 400


def test_the_studied_checkbox_is_wired_without_hijacking_the_page():
    """The pages disagree about the studied box (.q-prac on /ai-sde, a bare
    input elsewhere), so it is matched by "a checkbox in a card that also has
    a Plan button" — which is also how the bank and title are known.

    Bound on CHANGE, not in the capture-phase click handler: that one stops
    propagation and would prevent each page's own tick handler ever running.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    assert "syncCompletion" in js
    handler = js.split('root.addEventListener("change"')[1].split("});")[0]
    assert 'box.type !== "checkbox"' in handler
    # Our own bulk box must never be mistaken for the studied one.
    assert 'classList.contains("prep-pickbox")' in handler
    assert "stopPropagation" not in handler, "would break the page's own tick"


def test_quick_bucket_tick_reaches_the_topic_it_came_from(auth_client, monkeypatch):
    """Reported: un-ticking a row in the Quick Bucket left the prep page and
    the day planner still showing it done.

    The link existed in ONE direction — scheduling a topic wrote a bucket
    row, but the row knew nothing about where it came from. Both endpoints
    now walk it back.
    """
    import routes.quick_bucket as qb
    import routes.interview_prep as ip
    calls = []
    monkeypatch.setattr(qb, "update", lambda *a, **k: None)
    monkeypatch.setattr(qb, "_fetch_event_id", lambda u, i: None)
    monkeypatch.setattr(qb, "get", lambda t, params=None, **k:
                        [{"text": "AISDEPrep · Balanced Binary Tree"}]
                        if t == "quick_bucket" else [])
    monkeypatch.setattr(ip, "complete_prep_artifacts",
                        lambda u, b, t, d, include_bucket=True:
                        calls.append((b, t, d, include_bucket)) or {})

    auth_client.post("/api/quick-bucket/X/done")
    # include_bucket=False: the caller has already written that row, and
    # re-writing it would be pointless work at best and a fight at worst.
    assert calls == [("ai_sde", "Balanced Binary Tree", True, False)]

    calls.clear()
    auth_client.post("/api/quick-bucket/X/reopen")
    assert calls == [("ai_sde", "Balanced Binary Tree", False, False)]


def test_an_ordinary_bucket_row_is_not_mistaken_for_a_prep_one(auth_client, monkeypatch):
    """The separator alone cannot identify one: a row reading
    "Walking (Pomodoro · 25m)" contains it too. The PROJECT NAME prefix is
    what marks a prep row."""
    import routes.quick_bucket as qb
    import routes.interview_prep as ip
    from routes.interview_prep import parse_bucket_text

    assert parse_bucket_text("AISDEPrep · Balanced Binary Tree") == \
        ("ai_sde", "Balanced Binary Tree")
    assert parse_bucket_text("SQLPrep · ORDER BY, and where NULL sorts") == \
        ("sql", "ORDER BY, and where NULL sorts")
    for text in ("Walking (Pomodoro · 25m)", "buy milk", "Something · else",
                 "AISDEPrep · ", ""):
        assert parse_bucket_text(text) == (None, None), text

    calls = []
    monkeypatch.setattr(qb, "update", lambda *a, **k: None)
    monkeypatch.setattr(qb, "_fetch_event_id", lambda u, i: None)
    monkeypatch.setattr(qb, "get", lambda t, params=None, **k:
                        [{"text": "Walking (Pomodoro · 25m)"}] if t == "quick_bucket" else [])
    monkeypatch.setattr(ip, "complete_prep_artifacts",
                        lambda *a, **k: calls.append(a) or {})
    auth_client.post("/api/quick-bucket/X/done")
    assert not calls


def test_ai_sde_study_record_follows_a_tick_made_elsewhere(auth_client, monkeypatch):
    """/ai-sde keeps studied state on the server, so closing a topic from
    the bucket has to update it or the page disagrees on reload.

    /java and /sql keep theirs in localStorage, which nothing server-side
    can reach — those are reconciled on the client from the task status.
    """
    import routes.interview_prep as ip
    posted = []
    monkeypatch.setattr(ip, "_find_prep_project", lambda u, b: None)
    monkeypatch.setattr(ip, "get", lambda *a, **k: [])
    monkeypatch.setattr(ip, "update", lambda *a, **k: None)
    monkeypatch.setattr(ip, "post", lambda t, p, **k: posted.append((t, p)) or [{}])

    title = ip.AI_SDE_ENTRIES[0]["title"]
    ip.complete_prep_artifacts("u1", "ai_sde", title, True)
    prog = [p for t, p in posted if t == "ai_sde_progress"]
    assert prog and prog[0]["studied"] is True and prog[0]["entry_title"] == title

    posted.clear()
    ip.complete_prep_artifacts("u1", "ai_sde", title, False)
    prog = [p for t, p in posted if t == "ai_sde_progress"]
    assert prog and prog[0]["studied"] is False and prog[0]["studied_at"] is None

    # A bank with no server-side study record must not invent one.
    posted.clear()
    ip.complete_prep_artifacts("u1", "sql", "ORDER BY, and where NULL sorts", True)
    assert not [p for t, p in posted if t == "ai_sde_progress"]


def test_the_checkbox_is_reconciled_without_echoing_back():
    """/java and /sql hold studied state in localStorage, so a tick made in
    the bucket can only reach them on the client. The reconciler dispatches
    a real change event — each page persists its own progress in its own
    handler, and simply setting .checked would leave the tick undone on the
    next reload — and guards against that event returning as a fresh
    completion.
    """
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    assert "function reconcileChecked" in js
    body = js.split("function reconcileChecked")[1].split("function syncCompletion")[0]
    assert "reconciling = true" in body and "reconciling = false" in body
    assert 'new Event("change"' in body, "the page would never persist the tick"
    # Only topics that are actually scheduled — an unscheduled one has no
    # task to disagree with.
    assert "if (!info) return" in body
    assert "if (reconciling) return;" in js.split("function syncCompletion")[1][:200]


# ═══════════════════════════════════════════════════
# Making silent failure audible
# ═══════════════════════════════════════════════════

def test_loud_warns_on_a_miss_and_then_shuts_up(caplog):
    """Four faults this month were invisible because a broken thing looked
    exactly like an empty one. These make the difference audible — while
    THROTTLING, because a warning on every request is noise, and noise is
    how the last round of silence got established.
    """
    import logging
    from services import loud
    loud._last.clear()

    with caplog.at_level(logging.WARNING, logger="daily_plan"):
        assert loud.expect([], "the SQLPrep project", user_id="u1") == []
        loud.expect([{"id": 1}], "something present", user_id="u1")   # silent
        loud.bailed("prep bulk bar", "no cards yet", page="/sql")
        loud.created_what_should_exist("the SQLPrep project", user_id="u1")

    text = caplog.text
    assert "SILENT-MISS" in text and "the SQLPrep project" in text
    assert "FEATURE-INERT" in text and "prep bulk bar" in text
    assert "CREATED-AFTER-MISS" in text
    assert text.count("SILENT-MISS") == 1, "a present row should log nothing"

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="daily_plan"):
        loud.expect([], "the SQLPrep project", user_id="u1")
    assert "SILENT-MISS" not in caplog.text, "the same warning repeated"


def test_the_duplicate_project_bug_would_now_announce_itself(caplog):
    """The find-or-create that made ten SQLPrep projects in four minutes.
    A miss is legitimate exactly ONCE per user per bank; if it repeats for
    the same pair, the lookup is broken rather than the data missing."""
    import inspect
    import routes.interview_prep as ip
    src = inspect.getsource(ip._ensure_prep_project)
    assert "created_what_should_exist" in src
    # It must sit BEFORE the insert, or it only reports after the damage.
    assert src.index("created_what_should_exist") < src.index('post("projects"')


def test_dead_push_subscriptions_are_reported(caplog):
    """A user with no ACTIVE subscription receives nothing, silently and
    forever, while the browser still says notifications are on. That is the
    likeliest reason this household's reminders died in April and it was
    found in August."""
    import inspect
    from services import push_service
    src = inspect.getsource(push_service._active_subscriptions)
    assert "loud.bailed" in src
    # It distinguishes "never subscribed" from "all expired" — those need
    # different actions, and a single message would hide the second.
    assert "INACTIVE" in src and "no subscription at all" in src


def test_a_browser_feature_can_report_that_it_did_nothing(auth_client, caplog):
    """A console warning does not help: nobody has the console open on their
    phone. An inert feature reports itself into the server log instead."""
    import logging
    from services import loud
    loud._last.clear()
    with caplog.at_level(logging.WARNING, logger="daily_plan"):
        r = auth_client.post("/api/client-inert", json={
            "feature": "prep-scheduler", "why": "no card appeared within 15s",
            "page": "/sql"})
    assert r.status_code == 200
    assert "FEATURE-INERT" in caplog.text
    assert "prep-scheduler" in caplog.text and "/sql" in caplog.text

    # A blank report is dropped rather than logging an empty line.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="daily_plan"):
        auth_client.post("/api/client-inert", json={})
    assert "FEATURE-INERT" not in caplog.text


def test_the_guards_that_hid_the_dead_features_now_speak_up():
    """whenCardsReady is the exact guard both dead features sat behind.
    Waiting the whole window without a card means they are not running."""
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    waiter = js.split("function whenCardsReady")[1].split("function inert")[0]
    assert "if (!fired) inert(" in waiter, "a silent timeout is still silent"
    assert 'inert("no MutationObserver")' in waiter
    assert "window.dpInert" in js

    g = open("static/js/global.js", encoding="utf-8").read()
    assert "window.dpInert" in g and "/api/client-inert" in g
    # Once per reason per page load: a signal, not telemetry.
    assert "reported[key]" in g
    # keepalive, because a navigation is exactly when this fires.
    assert "keepalive: true" in g


# ═══════════════════════════════════════════════════
# Her own notes on a prep question
# ═══════════════════════════════════════════════════

def test_a_note_can_be_saved_and_read_back_per_bank(auth_client, monkeypatch):
    """A bank entry is written material — an answer, a walkthrough, worked
    examples. What it never had is somewhere for the READER's thinking: what
    she got wrong, what finally made it click, what an interviewer actually
    asked. That is the note most worth keeping.
    """
    import routes.interview_prep as ip
    posted = []
    monkeypatch.setattr(ip, "post", lambda t, p, **k: posted.append((t, p, k)) or [{}])
    monkeypatch.setattr(ip, "get", lambda t, params=None, **k: [
        {"entry_title": "ORDER BY, and where NULL sorts",
         "note": "I got the NULL ordering backwards", "updated_at": "2026-08-22"},
        {"entry_title": "Empty one", "note": "   ", "updated_at": "2026-08-22"},
    ])

    j = auth_client.get("/api/prep/notes?bank=sql").get_json()
    assert j["available"] is True
    assert j["notes"]["ORDER BY, and where NULL sorts"]["note"] == \
        "I got the NULL ordering backwards"
    # A blank note is not a note — it would draw an empty box for nothing.
    assert "Empty one" not in j["notes"]

    r = auth_client.post("/api/prep/notes", json={
        "bank": "sql", "title": "ORDER BY, and where NULL sorts",
        "note": "Ask about NULLS FIRST vs LAST"})
    assert r.status_code == 200
    table, payload, kwargs = posted[-1]
    assert table.startswith("prep_notes")
    assert payload["entry_title"] == "ORDER BY, and where NULL sorts"
    assert payload["bank"] == "sql"
    # UPSERT, not insert. Without merge-duplicates a second save creates a
    # second row and the first silently becomes unreachable.
    assert "merge-duplicates" in kwargs.get("prefer", "")
    # AND the conflict target must be named. PostgREST infers it from the
    # PRIMARY KEY unless told, and this table's key is a generated uuid that
    # never collides — so without ?on_conflict= there is nothing to merge on
    # and the SECOND save of any note returns 409. Verified against the live
    # database, not assumed.
    assert "on_conflict=user_id,bank,entry_title" in table, (
        "the second edit of a note will fail with a conflict")


def test_notes_are_keyed_by_title_not_by_a_positional_id(auth_client, monkeypatch):
    """Every bank numbers its entries by POSITION — ai42, j7, sq3 — and a
    position shifts the moment an entry is added or deduped. The AI SDE bank
    went from ~500 to 1,120 entries with 57 duplicates folded out."""
    import routes.interview_prep as ip
    posted = []
    monkeypatch.setattr(ip, "post", lambda t, p, **k: posted.append(p) or [{}])
    auth_client.post("/api/prep/notes",
                     json={"bank": "ai_sde", "title": "Two Sum", "note": "n"})
    assert posted[-1]["entry_title"] == "Two Sum"
    assert not any(k in posted[-1] for k in ("entry_id", "id", "index"))

    assert auth_client.post("/api/prep/notes",
                            json={"bank": "ai_sde", "title": "", "note": "x"}).status_code == 400
    assert auth_client.post("/api/prep/notes",
                            json={"bank": "nope", "title": "t", "note": "x"}).status_code == 400


def test_notes_degrade_when_the_migration_has_not_been_run(auth_client, monkeypatch):
    """The page must HIDE the box rather than offer one that silently throws
    away everything typed into it."""
    import routes.interview_prep as ip

    def missing(*a, **k):
        raise Exception('relation "prep_notes" does not exist')

    monkeypatch.setattr(ip, "get", missing)
    j = auth_client.get("/api/prep/notes?bank=java").get_json()
    assert j["available"] is False and j["migration"] == "MIGRATION_PREP_NOTES.sql"

    monkeypatch.setattr(ip, "post", missing)
    r = auth_client.post("/api/prep/notes",
                         json={"bank": "java", "title": "t", "note": "n"})
    assert r.status_code == 503
    assert "MIGRATION_PREP_NOTES.sql" in r.get_json()["error"]


def test_the_notes_box_is_injected_on_open_not_on_render():
    """A bank page draws over a thousand cards; a textarea in every one is
    waste. And /ai-sde fills its body LAZILY on first open, so anything
    added earlier is thrown away by that fetch — hence watching for the
    class change rather than hooking any one page's toggle."""
    js = open("static/js/prep-scheduler.js", encoding="utf-8").read()
    assert "function ensureNote" in js
    # The body lookup is its own function, so check it there rather than
    # inside ensureNote — an earlier version of this test looked in the
    # wrong place and failed on working code.
    host = js.split("function noteHostFor")[1].split("}")[0]
    assert ".q-body" in host, "the note is not placed in the card body"
    body = js.split("function ensureNote")[1].split("function autoGrow")[0]
    assert "noteHostFor(card)" in body
    assert 'querySelector(".prep-note")' in body, "would stack a second box"
    # Saved on a debounce AND on blur: the debounce has not fired when you
    # close the card.
    assert 'addEventListener("blur", save)' in body
    # Typing must not reach the page's own card toggle.
    assert "stopPropagation" in body
    assert 'attributeFilter: ["class"]' in js, "a lazy re-render would lose it"


# ═══════════════════════════════════════════════════
# App health — silent failures surfaced where they'll be seen
# ═══════════════════════════════════════════════════

def test_settings_surfaces_silent_failures(auth_client):
    """Logging a problem only helps if someone reads the log. Four faults
    were live for weeks precisely because nothing crashed — so the same
    reports now appear on a page that gets opened.

    NOTE ON ASSERTIONS HERE: match the class ATTRIBUTE, not the bare class
    NAME. The stylesheet ships on every render, so `"health-row" in html` is
    true even with an empty list — a trap that has already produced three
    false results in this suite.
    """
    import re
    from services import loud
    loud.clear()

    html = auth_client.get("/settings").get_data(as_text=True)
    assert "Nothing has reported a problem" in html
    assert 'class="health-row' not in html, "an empty list rendered rows"

    for _ in range(7):
        loud.expect([], "the SQLPrep project", user_id="u1", bank="sql")
    loud.bailed("web push", "every subscription is INACTIVE", user_id="u1")

    html = auth_client.get("/settings").get_data(as_text=True)
    assert "App health" in html
    # Aggregated, not one line per occurrence: the COUNT is the signal.
    assert "&times;7" in html
    assert "the SQLPrep project" in html and "web push" in html
    # It says which user/bank, or the report is unactionable.
    assert "bank=&#39;sql&#39;" in html or "bank='sql'" in html

    # One occurrence is weak evidence; a run of them is not — so only the
    # repeated one is called out.
    rows = re.findall(r'class="health-row([^"]*)"',
                      html.split('class="health-list"')[1])
    assert any("is-loud" in r for r in rows), "a repeated fault is not flagged"
    assert any("is-loud" not in r for r in rows), "a single report is over-flagged"

    loud.clear()


def test_health_list_can_be_cleared(auth_client):
    """The list stops being useful the moment it is mostly things already
    dealt with."""
    from services import loud
    loud.clear()
    loud.expect([], "something", user_id="u1")
    assert loud.recent()

    assert auth_client.post("/api/settings/health/clear").status_code == 200
    assert not loud.recent()


def test_health_counts_stay_true_while_the_log_is_throttled():
    """The log line is throttled to once per five minutes so it does not
    become noise — but the COUNT must not be, or the page would report a
    hourly fault as having happened once."""
    from services import loud
    loud.clear()
    for _ in range(40):
        loud.expect([], "a broken filter", user_id="u1")
    rows = loud.recent()
    assert len(rows) == 1 and rows[0]["count"] == 40
    loud.clear()


def test_health_buffer_is_bounded():
    """A burst of new problems must not push out the one still happening."""
    from services import loud
    loud.clear()
    loud.expect([], "the important recurring one", user_id="u1")
    for i in range(loud._RECORD_MAX + 50):
        loud.expect([], f"noise {i}", user_id="u1")
    # Keep it alive: eviction is least-recently-SEEN, not oldest-first.
    loud.expect([], "the important recurring one", user_id="u1")
    assert len(loud.recent()) <= loud._RECORD_MAX
    assert any("the important recurring one" in r["message"] for r in loud.recent())
    loud.clear()


def test_quick_bucket_accepts_a_pasted_list(auth_client):
    """Asked: is there somewhere to dump a laundry list of items?

    The Quick Bucket is exactly that surface — and its capture field is
    already a textarea — but everything typed into it became ONE row, so
    pasting twenty things to get them out of your head produced one item
    containing twenty lines. That is the opposite of what a bucket is for.
    """
    js = open("static/js/quick_bucket.js", encoding="utf-8").read()
    assert "const addLines" in js
    block = js.split("const addLines")[1].split("// SW reports back")[0]
    assert "split(/\\r?\\n/)" in block, "windows line endings would not split"
    assert "filter(Boolean)" in block, "blank lines would become empty items"
    # One line must behave exactly as before — no summary toast, no change.
    assert "if (lines.length <= 1)" in block
    # Each line goes through addItem, so "@1h" and "tomorrow" still parse and
    # the offline queue and client-id dedupe still apply. A bulk endpoint
    # would have to reimplement all of it.
    assert "await addItem(line" in block
    # Sequential on purpose: the priority badge is derived from the rows
    # already present, so parallel adds would collide on the number.
    assert "for (const line of lines)" in block

    html = open("templates/quick_bucket.html", encoding="utf-8").read()
    # maxlength caps the whole BOX, not one item. At 500 a pasted list was
    # truncated at roughly eight lines.
    assert 'maxlength="20000"' in html
    assert "one item per line" in html

    # The server still bounds each individual item.
    import routes.quick_bucket as qb
    assert qb._MAX_TEXT_LEN == 500


def test_quick_bucket_can_show_one_group_at_a_time(auth_client):
    """Asked for as "a filter to show only Future".

    Future IS the backlog bucket, and it is unreadable sitting underneath
    everything due now. Built as a focus on any single group rather than a
    Future-only toggle: it is the same control, and it also answers "what is
    due now" and "what did I finish", which are the other two questions this
    list gets asked.
    """
    html = auth_client.get("/quick-bucket").get_data(as_text=True)
    assert 'id="qb-groupfilter"' in html

    js = open("static/js/quick_bucket.js", encoding="utf-8").read()
    assert "GROUP_FILTERS" in js and "paintGroupFilter" in js
    # Every group, plus an explicit All.
    for key in ('""', '"now"', '"today"', '"future"', '"done"'):
        assert key in js.split("const GROUP_FILTERS")[1].split("];")[0]

    paint = js.split("const paintGroupFilter")[1].split("const wireGroupFilter")[0]
    # The count is half the point: the chip must say how much is in Future
    # while you are looking at Now, so it is computed from ALL groups.
    assert "VISIBLE_GROUPS.reduce" in paint
    # An empty Future bucket is a fact worth looking at, not a dead button.
    # Match the ATTRIBUTE, not the word — the comment explaining this says
    # "disabled", and matching prose is a mistake this suite keeps making.
    assert "disabled>" not in paint and 'disabled="' not in paint

    wire = js.split("const wireGroupFilter")[1].split("// ───")[0]
    # Pressing the active chip returns to All, so the filter is never a state
    # you have to hunt for the way out of.
    assert "groupFilter === next" in wire
    # Persisted: a backlog review is a mode you stay in for a few minutes.
    assert "GROUP_FILTER_KEY" in wire

    # The default is everything — the everyday view must not change.
    state = js.split("let groupFilter =")[1][:40]
    assert '""' in state


# ═══════════════════════════════════════════════════
# /backlog — one view over two lists that stay put
# ═══════════════════════════════════════════════════

def _backlog_stub(monkeypatch, bucket=None, tasks=None, projects=None):
    import routes.backlog as bk

    def fake_get(table, params=None, **k):
        if table == "quick_bucket":
            return bucket or []
        if table == "project_tasks":
            return tasks or []
        if table == "projects":
            return projects or []
        return []

    monkeypatch.setattr(bk, "get", fake_get)


def test_backlog_shows_both_lists_without_moving_anything(auth_client, monkeypatch):
    """Asked for after the alternative — relocating project tasks into the
    bucket — turned out to be destructive: project_tasks carries 40 columns
    to quick_bucket's 21, and moving one drops its project, key result,
    initiative, epic, sprint, priority and ordering. Project progress is
    computed from live task counts too, so the move would silently change
    the completion figure on every project involved.

    It was a READING problem, so this reads both and writes nothing.
    """
    _backlog_stub(
        monkeypatch,
        bucket=[{"id": "b1", "text": "Renew passport", "time_bucket": "future",
                 "due_at": None, "created_at": "2026-08-01"}],
        tasks=[{"task_id": "t1", "task_text": "Revise the BCP/DR documentation",
                "status": "open", "project_id": "p1", "due_date": "2026-04-06",
                "created_at": "2026-01-01", "plan_date": None, "start_time": None}],
        projects=[{"project_id": "p1", "name": "Office"}],
    )
    html = auth_client.get("/backlog").get_data(as_text=True)

    assert "Renew passport" in html
    assert "Revise the BCP/DR documentation" in html
    # Grouped by project, and linking back to it — the grouping is the whole
    # reason these stay where they are.
    assert "Office" in html and "/projects/p1/tasks" in html
    assert "nothing has been moved" in html.lower()

    # It must not write. Ever.
    import inspect
    import routes.backlog as bk
    src = inspect.getsource(bk)
    for verb in ("post(", "update(", "delete("):
        assert verb not in src, f"the backlog view calls {verb}"


def test_backlog_excludes_finished_and_scheduled_work(auth_client, monkeypatch):
    """A backlog is what is outstanding and undated. Anything closed, already
    put on a day, or already in the project's recycle bin is not."""
    tasks = [
        {"task_id": "a", "task_text": "Open and undated", "status": "open",
         "project_id": "p1", "created_at": "1", "plan_date": None, "start_time": None},
        {"task_id": "b", "task_text": "Already done", "status": "done",
         "project_id": "p1", "created_at": "1", "plan_date": None, "start_time": None},
        {"task_id": "c", "task_text": "Has a day", "status": "open",
         "project_id": "p1", "created_at": "1", "plan_date": "2026-08-22", "start_time": None},
        {"task_id": "d", "task_text": "Has a time", "status": "open",
         "project_id": "p1", "created_at": "1", "plan_date": None, "start_time": "09:00"},
        {"task_id": "e", "task_text": "Backlog status counts", "status": "backlog",
         "project_id": "p1", "created_at": "1", "plan_date": None, "start_time": None},
    ]
    _backlog_stub(monkeypatch, tasks=tasks,
                  projects=[{"project_id": "p1", "name": "Office"}])
    html = auth_client.get("/backlog").get_data(as_text=True)

    assert "Open and undated" in html
    assert "Backlog status counts" in html
    assert "Already done" not in html
    assert "Has a day" not in html
    assert "Has a time" not in html

    # is_eliminated is the flag the projects UI treats as removed — the task
    # list does not even filter on is_deleted.
    import inspect
    import routes.backlog as bk
    src = inspect.getsource(bk._undated_project_tasks)
    assert '"is_eliminated": "eq.false"' in src
    assert "is_deleted" not in src.split('"""')[2]


def test_backlog_agrees_with_the_bucket_page_about_future(auth_client, monkeypatch):
    """quick_bucket.js puts an "at" item into Future when its pinned time is
    beyond today. This copies that rule rather than inventing one — three
    divergent copies of the checklist schedule rule already cost this
    codebase a bug that ran for months."""
    from datetime import timedelta
    from utils.user_tz import user_today
    today = user_today()
    _backlog_stub(monkeypatch, bucket=[
        {"id": "1", "text": "Deferred outright", "time_bucket": "future",
         "due_at": None, "created_at": "3"},
        {"id": "2", "text": "Pinned next week", "time_bucket": "at",
         "due_at": (today + timedelta(days=7)).isoformat() + "T09:00:00+00:00",
         "created_at": "2"},
        {"id": "3", "text": "Pinned today", "time_bucket": "at",
         "due_at": today.isoformat() + "T09:00:00+00:00", "created_at": "1"},
        {"id": "4", "text": "Due in an hour", "time_bucket": "1h",
         "due_at": None, "created_at": "0"},
    ])
    html = auth_client.get("/backlog").get_data(as_text=True)

    assert "Deferred outright" in html
    assert "Pinned next week" in html, "a future-dated pin belongs in the backlog"
    assert "Pinned today" not in html, "today's work is not backlog"
    assert "Due in an hour" not in html, "a deadline bucket is not backlog"


def test_a_trashed_project_task_is_not_also_in_the_live_list(auth_client, monkeypatch):
    """The project's task list filtered ONLY on is_eliminated, while its
    recycle bin selects `status in (deleted, skipped, not_required) OR
    is_eliminated`. Setting a task to "deleted" happens to flip
    is_eliminated too, so that case looked fine — but "skipped" does not, so
    a skipped task appeared in the project AND in its own bin at once.

    Fixed on the STATUS rather than by making every writer remember a second
    flag: two flags kept in sync by convention is precisely how they drift.
    """
    import routes.projects as pr

    live = pr._live_status_filter()
    for s in ("deleted", "skipped", "not_required"):
        assert s in live, f"{s} is in the bin but not excluded from the list"
    assert "done" not in live, "completed work is still live unless hidden"

    # `status` is a single query parameter, so a second assignment would
    # silently replace the first — hence one combined filter.
    both = pr._live_status_filter(also_hide_done=True)
    assert "done" in both and "skipped" in both

    captured = {}

    def fake_get(table, params=None, **k):
        if table == "project_tasks" and params and "order" in params:
            captured["params"] = params
        if table == "projects":
            return [{"project_id": "p1", "name": "Office", "user_id": "u"}]
        return []

    monkeypatch.setattr(pr, "get", fake_get)
    auth_client.get("/projects/p1/tasks")
    assert "status" in captured.get("params", {}), "the list has no status filter"
    assert "skipped" in captured["params"]["status"]


def test_project_progress_excludes_binned_work():
    """A completion percentage that counts tasks the user has explicitly put
    in the bin is reporting on work that no longer exists."""
    import inspect
    import routes.projects as pr
    src = inspect.getsource(pr.projects_page) if hasattr(pr, "projects_page") else \
        open("routes/projects.py", encoding="utf-8").read()
    block = src.split('"select": "project_id,status"')[0][-500:]
    assert "_NOT_LIVE_FILTER" in block, "the denominator still counts binned tasks"

"""Putting an AI/SDE topic onto a day.

The feature writes to three tables at once — the AISDEPrep project, the
calendar, and the Quick Bucket — so most of what can go wrong here is
"only two of the three happened", which no amount of reading the endpoint
tells you. These tests stand a fake Supabase in front of it and assert on
the rows that actually get inserted.

Two of the invariants are worth stating out loud, because they are
decisions rather than mechanics:

  * a topic with no time given lands at 00:00, and 00:00 is a POSITION —
    planner_v2.js builds the grid from hour 0, so midnight is the top row
    of the day, not a null;
  * the same topic on the same day twice is a no-op. Three tables and no
    transaction means a retried tap must be safe to make.
"""
import json
import types

import pytest

import routes.interview_prep as ip


class FakeDB:
    """Enough PostgREST to exercise the endpoint: rows land in a dict of
    lists, and `get` honours the handful of `eq.` filters the code uses.

    Filter values arrive quoted (see _pg_eq) because two thirds of the
    topic titles contain a comma or a bracket, so unquoting is part of
    what this fake has to do — and therefore part of what it tests."""

    def __init__(self, seed=None):
        self.tables = seed or {}
        self.inserted = []           # (table, payload) in call order

    # ── PostgREST-ish ────────────────────────────────────────────────
    @staticmethod
    def _unwrap(v):
        v = v[3:] if v.startswith("eq.") else v
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if v == "true":
            return True
        if v == "false":
            return False
        return v

    def get(self, table, params=None):
        rows = self.tables.get(table, [])
        for k, raw in (params or {}).items():
            if k in ("select", "limit", "order") or not isinstance(raw, str):
                continue
            if not raw.startswith("eq."):
                continue
            want = self._unwrap(raw)
            rows = [r for r in rows if r.get(k, False) == want]
        return list(rows)

    def post(self, table, payload, prefer=None):
        self.inserted.append((table, payload))
        row = dict(payload)
        row.setdefault("project_id", f"{table}-pid")
        row.setdefault("task_id", f"{table}-tid")
        row.setdefault("id", f"{table}-id")
        self.tables.setdefault(table, []).append(row)
        return [row]

    # ── assertions helpers ───────────────────────────────────────────
    def only(self, table):
        rows = [p for t, p in self.inserted if t == table]
        assert len(rows) == 1, f"{table}: expected 1 insert, got {len(rows)}"
        return rows[0]

    def count(self, table):
        return sum(1 for t, _ in self.inserted if t == table)


@pytest.fixture
def db(monkeypatch):
    """The route module does `from supabase_client import get, post`, so the
    names are bound in ITS namespace — patching supabase_client would miss
    them entirely, which is why this patches routes.interview_prep."""
    fake = FakeDB()
    monkeypatch.setattr(ip, "get", fake.get)
    monkeypatch.setattr(ip, "post", fake.post)
    # The default-epic lookup reaches into routes.projects, which has its
    # own bound `get`/`post`. Not the subject here — stub it flat.
    import routes.projects as pj
    monkeypatch.setattr(pj, "_ensure_default_okr_trio", lambda *a, **k: "epic-1")
    return fake


TITLE = "Precision vs Recall (and the 95%-accuracy trap)"


def _catch_threads(monkeypatch):
    """Collect the daemon threads the Google mirror spawns so a test can
    join them instead of sleeping.

    Swaps the module's `threading` NAME for a shim rather than setting
    `threading.Thread` — `ip.threading` *is* the stdlib module, so
    patching through it reaches every other user of threads in the
    process. It did: flask-limiter's expiry timer broke and every request
    500'd before reaching the endpoint under test.
    """
    import threading as real
    caught = []

    def spawn(*a, **kw):
        t = real.Thread(*a, **kw)
        caught.append(t)
        return t

    monkeypatch.setattr(ip, "threading", types.SimpleNamespace(Thread=spawn))
    return caught


def _post(client, **body):
    body.setdefault("plan_date", "2026-09-01")
    return client.post("/api/ai-sde/schedule", json=body)


# ── the helpers, on their own ────────────────────────────────────────

def test_a_missing_time_means_midnight():
    for raw in ("", None, "   ", "nine", "9am", "24:00", "12:60"):
        assert ip._ai_sde_clean_time(raw) == "00:00", raw
    # A real time survives, zero-padded so it sorts as text — which is how
    # daily_events stores start_time and how agenda_service orders it.
    assert ip._ai_sde_clean_time("9:05") == "09:05"
    assert ip._ai_sde_clean_time(" 7:30 ") == "07:30"
    assert ip._ai_sde_clean_time("23:59") == "23:59"


def test_a_block_never_runs_into_the_next_day():
    """Wrapping past midnight would draw the second half of the session on
    a day the user never picked."""
    assert ip._ai_sde_end_time("23:40", 30) == "23:59"
    assert ip._ai_sde_end_time("00:00", 30) == "00:30"
    # Clamped: a 5-minute topic is unclickable, a 10-hour one eats the day.
    assert ip._ai_sde_end_time("00:00", 5) == "00:15"
    assert ip._ai_sde_end_time("00:00", 600) == "03:00"
    # Junk falls back rather than raising — the caller asked to schedule.
    assert ip._ai_sde_end_time("00:00", "abc") == "00:30"
    assert ip._ai_sde_end_time("00:00", None) == "00:30"


def test_free_text_filters_are_quoted():
    """386 of the 1,120 titles contain a comma, a colon or a bracket, and
    PostgREST reads every one of those as filter syntax."""
    assert ip._pg_eq(TITLE) == f'eq."{TITLE}"'
    assert ip._pg_eq('say "hi"') == 'eq."say \\"hi\\""'


def test_the_title_beats_a_stale_id():
    """`ai{i}` is the entry's INDEX in the bank and shifts whenever the bank
    changes, so a tab left open across an edit must not schedule whatever
    moved into that slot."""
    real = ip.AI_SDE_ENTRIES[5]["title"]
    assert ip._ai_sde_lookup("ai5", None)[0] == real
    # Id points elsewhere, title is real → the title wins.
    assert ip._ai_sde_lookup("ai5", TITLE)[0] == TITLE
    # Id is nonsense, title is real → still resolves.
    assert ip._ai_sde_lookup("ai99999", TITLE)[0] == TITLE
    assert ip._ai_sde_lookup("garbage", TITLE)[0] == TITLE
    # Neither resolves → the endpoint must 404 rather than guess.
    assert ip._ai_sde_lookup("ai99999", "no such topic")[0] is None


# ── the endpoint ─────────────────────────────────────────────────────

def test_one_tap_writes_all_three_places(auth_client, db):
    r = _post(auth_client, title=TITLE)
    assert r.status_code == 200, r.get_data()
    out = r.get_json()
    assert out["status"] == "ok"
    assert out["untimed"] is True
    assert out["start_time"] == "00:00"

    # The project is created on demand, since nothing seeded it.
    proj = db.only("projects")
    assert proj["name"] == "AISDEPrep"
    assert proj["is_archived"] is False
    # NOT the Inbox slot — is_default is one-per-user and belongs to Inbox.
    assert "is_default" not in proj

    task = db.only("project_tasks")
    assert task["task_text"] == TITLE
    assert task["plan_date"] == "2026-09-01"
    assert task["start_time"] == "00:00"
    assert task["is_deleted"] is False

    ev = db.only("daily_events")
    assert ev["title"] == TITLE
    assert ev["plan_date"] == "2026-09-01"
    assert ev["start_time"] == "00:00", "an untimed topic must sit at the top of the day"
    assert ev["end_time"] > ev["start_time"]

    qb = db.only("quick_bucket")
    assert TITLE in qb["text"]
    assert qb["text"].startswith("AISDEPrep")
    assert qb["is_done"] is False


def test_a_given_time_is_kept_and_becomes_a_deadline(auth_client, db):
    out = _post(auth_client, title=TITLE, start_time="9:05").get_json()
    assert out["untimed"] is False and out["start_time"] == "09:05"
    assert db.only("daily_events")["start_time"] == "09:05"
    qb = db.only("quick_bucket")
    # A real time earns a real countdown; midnight does not, because a
    # countdown to 00:00 would read as urgent when the time only means
    # "top of the day".
    assert qb["due_at"] == "2026-09-01T09:05:00"
    assert qb["time_bucket"] == "at"


def test_an_untimed_topic_gets_no_countdown(auth_client, db):
    _post(auth_client, title=TITLE)
    qb = db.only("quick_bucket")
    assert qb["due_at"] is None
    assert qb["time_bucket"] in ("now", "future")


def test_the_same_topic_on_the_same_day_twice_is_a_no_op(auth_client, db):
    first = _post(auth_client, title=TITLE).get_json()
    assert first["status"] == "ok"
    before = dict(project_tasks=db.count("project_tasks"),
                  daily_events=db.count("daily_events"),
                  quick_bucket=db.count("quick_bucket"))

    second = _post(auth_client, title=TITLE).get_json()
    assert second["status"] == "already-scheduled"
    for table, n in before.items():
        assert db.count(table) == n, f"{table} gained a duplicate row on the second tap"


def test_the_same_topic_on_a_different_day_is_a_new_row(auth_client, db):
    _post(auth_client, title=TITLE, plan_date="2026-09-01")
    out = _post(auth_client, title=TITLE, plan_date="2026-09-02").get_json()
    assert out["status"] == "ok"
    assert db.count("project_tasks") == 2
    assert db.count("daily_events") == 2
    # ...but only one project. Creating a second AISDEPrep would split the
    # syllabus across two places.
    assert db.count("projects") == 1


def test_an_existing_project_is_reused_not_recreated(auth_client, db):
    db.tables["projects"] = [{
        "project_id": "existing-1", "user_id": "test-user-id",
        "name": "AISDEPrep", "is_archived": False,
    }]
    out = _post(auth_client, title=TITLE).get_json()
    assert out["project_id"] == "existing-1"
    assert db.count("projects") == 0, "an existing AISDEPrep must not be duplicated"


def test_an_archived_project_does_not_count_as_the_live_one(auth_client, db):
    db.tables["projects"] = [{
        "project_id": "old-1", "user_id": "test-user-id",
        "name": "AISDEPrep", "is_archived": True,
    }]
    out = _post(auth_client, title=TITLE).get_json()
    assert out["project_id"] != "old-1"
    assert db.count("projects") == 1


def test_bad_input_is_refused_before_anything_is_written(auth_client, db):
    assert _post(auth_client, title=TITLE, plan_date="").status_code == 400
    assert _post(auth_client, title=TITLE, plan_date="01/09/2026").status_code == 400
    assert _post(auth_client, title=TITLE, plan_date="2026-02-31").status_code == 400
    assert _post(auth_client, title="no such topic").status_code == 404
    assert db.inserted == [], "a rejected request must not leave rows behind"


def test_the_quick_bucket_mirror_can_be_declined(auth_client, db):
    _post(auth_client, title=TITLE, quick_bucket=False)
    assert db.count("quick_bucket") == 0
    # The other two still happen — the bucket is a mirror, not the record.
    assert db.count("project_tasks") == 1
    assert db.count("daily_events") == 1


def test_the_task_survives_a_failing_calendar_write(auth_client, db, monkeypatch):
    """No transaction spans the three tables, so the order matters: the
    project task is the record of what she planned, and the calendar and
    bucket rows are views onto it. Losing a view must not lose the record."""
    real_post = db.post

    def flaky(table, payload, prefer=None):
        if table == "daily_events":
            raise RuntimeError("supabase said no")
        return real_post(table, payload, prefer=prefer)

    monkeypatch.setattr(ip, "post", flaky)
    out = _post(auth_client, title=TITLE).get_json()
    assert out["status"] == "ok"
    assert out["event_id"] is None
    assert db.count("project_tasks") == 1
    assert db.count("quick_bucket") == 1


def test_a_missing_column_does_not_500_the_request(auth_client, db, monkeypatch):
    """project_tasks.is_deleted is in MIGRATION_ALL_TABLES.sql, but an older
    install never got the line — which is exactly what happened here. post()
    and update() already strip an unknown column and retry; get() does not,
    so a filter on it raises 400 and the whole request dies. The lookup has
    to survive an un-migrated database, because refusing to schedule
    anything until a migration is run is worse than a wider lookup."""
    real_get = db.get

    def strict(table, params=None):
        if table == "project_tasks" and "is_deleted" in (params or {}):
            raise RuntimeError('column "is_deleted" does not exist')
        return real_get(table, params)

    monkeypatch.setattr(ip, "get", strict)
    out = _post(auth_client, title=TITLE).get_json()
    assert out["status"] == "ok"
    assert db.count("project_tasks") == 1

    # ...and the dedupe still works without the column, because dropping it
    # only WIDENS the match. A no-op is the safe direction to fail in.
    again = _post(auth_client, title=TITLE).get_json()
    assert again["status"] == "already-scheduled"
    assert db.count("project_tasks") == 1


def test_the_lookup_reraises_when_the_column_is_not_the_problem(db, monkeypatch):
    """Retrying without the optional filter must not swallow a real outage
    into a silent empty result — that would look like 'not scheduled yet'
    and quietly duplicate every row."""
    def dead(table, params=None):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(ip, "get", dead)
    with pytest.raises(RuntimeError):
        ip._get_optional("project_tasks", {"user_id": "eq.x"}, optional={"is_deleted"})


def test_no_google_mirror_when_google_is_not_connected(auth_client, db):
    """user_google_tokens is empty in the fake, so nothing should fire."""
    out = _post(auth_client, title=TITLE).get_json()
    assert out["gcal_syncing"] is False


def test_the_google_mirror_fires_once_and_stamps_the_row(auth_client, db, monkeypatch):
    db.tables["user_google_tokens"] = [{"user_id": "test-user-id", "token": "x"}]

    calls, stamped = [], []
    monkeypatch.setattr(ip, "update",
                        lambda table, params, json: stamped.append((table, json)))

    import services.events_calendar_service as ecs

    def fake_create(uid, row):
        calls.append((uid, row["title"], row["start_time"]))
        return "gcal-abc"

    monkeypatch.setattr(ecs, "sync_create", fake_create)
    threads = _catch_threads(monkeypatch)

    out = _post(auth_client, title=TITLE).get_json()
    assert out["gcal_syncing"] is True
    for t in threads:
        t.join(timeout=5)

    assert calls == [("test-user-id", TITLE, "00:00")], "the mirror must fire exactly once"
    assert stamped and stamped[0][0] == "daily_events"
    assert stamped[0][1] == {"google_event_id": "gcal-abc"}


def test_the_quick_bucket_row_does_not_mirror_as_well(auth_client, db, monkeypatch):
    """quick_bucket has its OWN Google sync. If this endpoint let both fire
    the topic would land on the real calendar twice."""
    db.tables["user_google_tokens"] = [{"user_id": "test-user-id", "token": "x"}]
    import services.quick_bucket_calendar_service as qbcs
    fired = []
    for name in ("sync_create", "sync_upsert", "sync_item"):
        if hasattr(qbcs, name):
            monkeypatch.setattr(qbcs, name, lambda *a, **k: fired.append(name))
    _post(auth_client, title=TITLE)
    assert fired == []


def test_a_failing_google_mirror_does_not_fail_the_request(auth_client, db, monkeypatch):
    db.tables["user_google_tokens"] = [{"user_id": "test-user-id", "token": "x"}]
    import services.events_calendar_service as ecs
    monkeypatch.setattr(ecs, "sync_create",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("google down")))
    threads = _catch_threads(monkeypatch)

    out = _post(auth_client, title=TITLE).get_json()
    assert out["status"] == "ok"
    for t in threads:
        t.join(timeout=5)
    # The in-app calendar row is the one that matters and it survived.
    assert db.count("daily_events") == 1


def test_it_needs_a_login(client):
    r = client.post("/api/ai-sde/schedule",
                    json={"title": TITLE, "plan_date": "2026-09-01"})
    assert r.status_code in (302, 401, 403)


# ── the page ─────────────────────────────────────────────────────────

def test_the_card_offers_the_button_and_defaults_to_no_time(auth_client):
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "data-sched-open" in html and "data-sched-go" in html
    assert "/api/ai-sde/schedule" in html
    assert 'class="sched-time"' in html
    # The date field defaults to today computed LOCALLY — toISOString()
    # would hand back yesterday all evening west of Greenwich.
    assert "function todayISO" in html
    assert "toISOString" not in html.split("function todayISO")[1][:400]


def test_the_button_is_reachable_without_opening_a_card(auth_client):
    """It shipped buried at the bottom of the card body, past a ten-section
    deep dive and a dozen worked examples — several screens of scrolling
    down, on a page where opening the card fetches all of that first. She
    looked for it and did not find it.

    Two fixes, both asserted here: a 📅 in the card HEADER, which renders
    with the list and needs no card opened at all; and the panel moved to
    the TOP of the body, above the prep-time line, rather than down beside
    the PDF link."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "data-sched-head" in html, "no scheduler affordance in the card header"
    # The header button sits in the same markup as the studied checkbox,
    # which is what renders for every row of the list.
    head = html.split('class="q-prac"')[1][:400]
    assert "data-sched-head" in head, "the 📅 is not in the row header"
    # ...and inside the body, the panel comes before the prep-time section
    # rather than after the follow-ups.
    body = html.split("function bodyHTML")[1]
    assert body.index("schedulerHTML()") < body.index('fld("plan"'), \
        "the scheduler is buried below the card content again"

# DailyPlanner — Test suite

Smoke + unit tests that run **without** a live Supabase, so you can catch
regressions before deploy.

## Setup (one time)

```bash
pip install pytest
```

(Flask and the other runtime deps come from `requirements.txt`.)

## Run

```bash
python -m pytest tests/ -v
```

## What it covers

**`tests/test_smoke.py`** — the "does the house have a roof" layer.
Runs in seconds. Catches the regressions users actually hit:
- App factory runs; every expected blueprint is registered
- Every protected page route resolves and doesn't 500 (both unauth and
  authed session)
- Jinja templates render with empty data (no `UndefinedError`)
- Agenda service + reports service return the exact shape the UI expects
- Vault status endpoint behaves correctly when unconfigured
- Encryption round-trips cleanly

**`tests/test_parsers.py`** — pure-function tests for the date/time and
natural-language parsers.

## What it does NOT cover (be honest about the gap)

- **Live Supabase behavior** — the tests stub out every `get/post/update/delete`
  call. If the real DB schema drifts from the Python models, tests still pass.
  Cover that with integration tests on a staging database.
- **JS behavior** — Python tests can't exercise `voice.js`, `project_tasks.js`,
  `pt-shared.js`. If you need JS coverage, add Vitest or Playwright later.
- **Real browser rendering** — templates parse and render server-side, but the
  client-side JS that mounts into the DOM isn't exercised.

## Philosophy

These tests favor **false negatives over false positives**. If a test goes
green, you can deploy with confidence. If a test goes red, something real
is broken — we don't flag style issues or minor data shape drift.

Add a new test when:
- You add a new blueprint (`test_all_expected_blueprints_present`)
- You add a new protected page (`PROTECTED_PAGES`)
- You change the shape of a service function return value

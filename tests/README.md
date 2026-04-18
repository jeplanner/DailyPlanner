# DailyPlanner — Test suite

Smoke + unit tests that run **without** a live Supabase. Catches
regressions before you push to Render.

## First-time setup

From the project root (the folder containing `app.py`):

```bash
# 1. Create an isolated environment
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate           # Linux / macOS
# .venv\Scripts\activate            # Windows (PowerShell)

# 3. Install runtime deps + pytest
pip install -r requirements.txt pytest
```

## Run the tests

```bash
source .venv/bin/activate            # any time you open a new shell
python -m pytest tests/ -v
```

Takes about 7 seconds. You should see:

```
============================== 44 passed in 6.74s ==============================
```

## Run once, before every push

A short pre-push habit:

```bash
source .venv/bin/activate && python -m pytest tests/ -v && git push
```

If anything goes red, fix it before the push hits Render.

## What's covered

**`tests/test_smoke.py`** — the "does the house have a roof" layer:
- `create_app()` boots cleanly; all 17 blueprints register
- Every protected page (15 of them) resolves for unauth visitors (redirect)
- Every protected page renders (200) with a seeded session + empty DB
- `build_dashboard()` and the four report functions return the exact
  dict shape the UI depends on
- Vault status endpoint behaves correctly when unconfigured
- Encryption round-trips cleanly

**`tests/test_parsers.py`** — pure-function tests for date/overdue
helpers (no Flask needed).

## What it does NOT cover

- **Live Supabase schema drift.** Tests stub out every DB call. If a
  column gets renamed in the real DB, tests still pass. Cover that
  separately with integration tests on a staging DB if needed.
- **JavaScript execution.** Python tests can't exercise `voice.js`,
  `project_tasks.js`, etc. If you break voice dictation or the task
  panel, tests won't catch it. Add Playwright/Vitest later if you want
  JS coverage.
- **Real browser rendering.** Templates parse and render server-side,
  but client-side JS mounting isn't exercised.

## Troubleshooting

### "ImportError: cannot import name 'create_app' from 'app'"
There's an orphan `app.py` one directory up (`/mnt/.../GitHub/app.py`
shadows this project's own `app.py`). The conftest works around this
with an explicit file-path import, so you shouldn't hit this on a
clean machine. If you do, delete the stray parent file.

### "ModuleNotFoundError: No module named 'flask'" (or openai, bleach…)
Run `pip install -r requirements.txt` inside the venv. Forgot to
activate the venv? Run `source .venv/bin/activate` first.

### "AssertionError: blueprints missing: {'inbox'}"
Flask blueprints are keyed by their `Blueprint("name", ...)` first
arg, not the Python variable name. If you add a blueprint, match its
registered name in `test_all_expected_blueprints_present`.

## Adding a test

- Add a new protected page → add its URL to `PROTECTED_PAGES` in
  `test_smoke.py`
- Add a new blueprint → add its registered name to `expected` in
  `test_all_expected_blueprints_present`
- Add a new service function → write a small test that hits it with
  empty / happy-path / edge-case inputs. `test_reports_productivity_empty_safe`
  is a good template

## Philosophy

Tests favor **high signal over complete coverage**. If they go green,
you can deploy. If they go red, something real is broken — not a style
issue or brittle brittle data-shape check.

Aim for ~20 seconds total test time. Past that, people stop running
them pre-push, which defeats the purpose.

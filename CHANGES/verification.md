# Phase 5 — verification receipts

## Test suite
```
$ .venv/bin/python -m pytest test_parser.py tests/ -q

................................................................
64 passed in 28.79s
```
All 64 tests pass — includes:
- Test-suite-wide boot (17 blueprint registrations, Jinja rendering)
- Every public + protected route returns 200 / 302 as expected for both unauth and authed test clients
- Parsers (date, time, planner input, agenda)
- Encryption round-trips
- Report services with empty data
- The pre-existing `test_title_cleanup` regression — exposed *after* fixing the broken imports; the fix lives in `utils/planner_parser.py` (Q[1-4] is only treated as a quadrant marker at end-of-string).

## Python AST check
```
All Python files parse cleanly.
```

## App boot (production mode with a real secret set)
```
Blueprints: ['ai', 'auth', 'events', 'goals', 'habits', 'health', 'inbox_bp',
             'notes', 'planner', 'portfolio', 'projects', 'refcards',
             'references', 'reports', 'system', 'timeline', 'todo']
App boots.
```

## Production secret guard
```
$ unset FLASK_SECRET_KEY
$ python -c "from settings import ProductionConfig; ProductionConfig()"
RuntimeError: FLASK_SECRET_KEY must be set to a strong random value in production.
```

## Open-redirect guard
```
OK  _safe_next_url(None)                         -> None
OK  _safe_next_url('')                           -> None
OK  _safe_next_url('/')                          -> '/'
OK  _safe_next_url('/projects/1/tasks')          -> '/projects/1/tasks'
OK  _safe_next_url('//evil.example')             -> None   ← blocks protocol-relative
OK  _safe_next_url('https://evil.example/phish') -> None
OK  _safe_next_url('javascript:alert(1)')        -> None
OK  _safe_next_url('http:whatever')              -> None
```

## Gantt calendar progress
```
a (start 2026-04-10, 10d, 3/10 h) → progress 90%, effort_progress 30%
b (done, 5d window)               → progress 100%, effort_progress 0%
c (future window)                 → progress 0%,   effort_progress 0%
```
Previously `a` would have shown **30% complete** because the code reported
effort-progress as calendar progress. Now it shows 90% calendar / 30% effort
— exactly what a Gantt chart should convey.

## Supabase log PII redaction
```
{'email':'a@b','password_hash':'secret','api_key':'k1','ciphertext':'abc','ok':'visible'}
   →  {'email':'a@b','password_hash':'[REDACTED]','api_key':'[REDACTED]',
       'ciphertext':'[REDACTED]','ok':'visible'}

{'nested':{'token':'yes','foo':'bar'}}
   →  {'nested':{'token':'[REDACTED]','foo':'bar'}}
```

## CSS sanity
```
static/design-system.css: 13 rules, 10158 bytes — OK
static/components.css:   105 rules, 17639 bytes — OK
static/auth.css:          32 rules,  4846 bytes — OK
```
Brace count balanced in all three new/expanded stylesheets.

## Auth page HTTP smoke
```
/login    -> [status 200, skip-link present, design-system.css linked, auth.css linked, NO inline <style>]
/register -> [same]
```

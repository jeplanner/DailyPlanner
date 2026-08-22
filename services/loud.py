"""Make silent failure audible.

WHY THIS EXISTS
---------------
Four separate faults in this codebase were invisible for weeks or months,
and every one of them looked exactly like an empty result:

  * `_pg_eq` quoted its PostgREST filters, so every existence check answered
    "not there" — creating ten duplicate projects, one per click.
  * push subscriptions went inactive server-side while the UI said "on",
    which is the likeliest reason the checklist reminders stopped arriving.
  * two client features bailed out of initialising because they ran before
    the list they needed existed, so they never appeared anywhere.
  * a test was pinning the first bug and passing happily.

The common shape is not a crash. It is a `try/except` that swallows, a
filter that returns `[]`, or a guard that returns early — and a BROKEN thing
then looks identical to an EMPTY one. Defensive degradation is worth having;
being unable to tell it apart from a fault is not.

WHAT THIS DOES
--------------
Two calls, both cheap, both no-ops in the happy path:

    expect(rows, "the AISDEPrep project", user_id=uid)
    bailed("prep bulk bar", "no cards in the list yet")

They log at WARNING with a stable, greppable prefix, and they THROTTLE — a
warning that fires on every request is noise, and noise is how the last
round of silence got established. Nothing here changes behaviour; a caller
that was going to create the row still creates it.

WHERE TO USE IT
---------------
`expect()` on a lookup you believe should MATCH — the row you just wrote,
the project that must exist, the subscription the UI says is active. Not on
a genuine search, where empty is a normal answer.
"""

import logging
import threading
import time

logger = logging.getLogger("daily_plan")

#: One warning per (message, context) per window. Long enough that a broken
#: filter on a hot path reports a handful of times an hour rather than
#: thousands — the point is to be noticed, not to fill the log.
THROTTLE_SECONDS = 300

_last = {}
_lock = threading.Lock()


def _throttled(key):
    """True if this exact warning was logged recently."""
    now = time.time()
    with _lock:
        prev = _last.get(key)
        if prev is not None and now - prev < THROTTLE_SECONDS:
            return True
        # Cheap bound: the key space is code sites, not user input, so this
        # only grows if someone passes something unbounded as context.
        if len(_last) > 2000:
            _last.clear()
        _last[key] = now
    return False


def _fmt(ctx):
    return " ".join(f"{k}={v!r}" for k, v in sorted(ctx.items())) if ctx else ""


def expect(rows, what, **ctx):
    """Return `rows`, warning if it is empty when it should not be.

    Deliberately pass-through, so it can be wrapped around an existing call
    without restructuring anything:

        rows = expect(get("projects", params=...), "the SQLPrep project",
                      user_id=user_id)
    """
    if rows:
        return rows
    key = ("expect", what, _fmt(ctx))
    if not _throttled(key):
        logger.warning("SILENT-MISS: expected to find %s but matched nothing. %s",
                       what, _fmt(ctx))
    return rows


def bailed(feature, why, **ctx):
    """Record that a feature declined to do its job.

    For the early-return case: a guard that is *supposed* to be rare, and
    which — if it stops being rare — means the feature is simply not running.
    """
    key = ("bail", feature, why, _fmt(ctx))
    if not _throttled(key):
        logger.warning("FEATURE-INERT: %s did nothing — %s. %s",
                       feature, why, _fmt(ctx))


def created_what_should_exist(what, **ctx):
    """A lookup missed and we are about to CREATE the thing it looked for.

    This is the exact signature of the duplicate-project bug: find-or-create
    where the find is broken silently produces a new row every time, and the
    only visible symptom is a slowly filling table.
    """
    key = ("create", what, _fmt(ctx))
    if not _throttled(key):
        logger.warning("CREATED-AFTER-MISS: creating %s because the lookup "
                       "found none — if this repeats for the same context, "
                       "the lookup is broken. %s", what, _fmt(ctx))

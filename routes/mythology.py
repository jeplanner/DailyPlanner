"""
Mythology — five date-stable stories per day from the Ramayana and
Mahabharata corpus. Same calendar day always shows the same five
stories on every refresh so the page has the rhythm of a daily
practice rather than a slot-machine.

Schema lives in MIGRATION_MYTHOLOGY_STORIES.sql:
    mythology_stories(id, epic, title, characters, summary, moral,
                      source_ref, is_active, created_at)
"""
import logging
import random
from datetime import date

from flask import Blueprint, jsonify, render_template, request

from auth import login_required
from supabase_client import get

logger = logging.getLogger("daily_plan")
mythology_bp = Blueprint("mythology", __name__)


def _date_seed(d=None):
    """Stable integer seed from a calendar date — used to shuffle the
    corpus deterministically per day. Same day → same 5 stories."""
    d = d or date.today()
    return int(d.strftime("%Y%m%d"))


def _fetch_all(epic=None):
    params = {
        "is_active": "eq.true",
        "select": "id,epic,title,characters,summary,moral,source_ref",
        "limit": "500",
    }
    if epic:
        params["epic"] = f"eq.{epic}"
    try:
        return get("mythology_stories", params=params) or []
    except Exception as e:
        logger.warning("mythology_stories fetch failed (migration missing?): %s", e)
        return []


def _pick_daily(rows, count=5, ref_date=None):
    """Pick `count` stories with a date-stable shuffle. We want a mix
    across both epics on most days, so we interleave: shuffle Ramayana
    and Mahabharata pools separately, then zip-pick alternately.
    Falls back to a flat shuffle if either pool is empty."""
    if not rows:
        return []
    rng = random.Random(_date_seed(ref_date))

    rama = [r for r in rows if (r.get("epic") or "").lower() == "ramayana"]
    maha = [r for r in rows if (r.get("epic") or "").lower() == "mahabharata"]

    if not rama or not maha:
        pool = list(rows)
        rng.shuffle(pool)
        return pool[:count]

    rng.shuffle(rama)
    rng.shuffle(maha)

    out = []
    i = j = 0
    # Alternate epics — Ramayana first on even days, Mahabharata first
    # on odd days, just for variety.
    rama_first = _date_seed(ref_date) % 2 == 0
    while len(out) < count and (i < len(rama) or j < len(maha)):
        if rama_first:
            if i < len(rama): out.append(rama[i]); i += 1
            if len(out) < count and j < len(maha): out.append(maha[j]); j += 1
        else:
            if j < len(maha): out.append(maha[j]); j += 1
            if len(out) < count and i < len(rama): out.append(rama[i]); i += 1
    return out[:count]


@mythology_bp.route("/mythology", methods=["GET"])
@login_required
def mythology_page():
    """Daily 5 stories. Optional query params:
       ?epic=ramayana | ?epic=mahabharata  → scope to one epic
       ?count=N                            → override picker count (1..20)
    """
    epic = (request.args.get("epic") or "").strip().lower() or None
    if epic and epic not in ("ramayana", "mahabharata"):
        epic = None
    try:
        count = max(1, min(20, int(request.args.get("count") or 5)))
    except (TypeError, ValueError):
        count = 5

    rows = _fetch_all(epic=epic)
    stories = _pick_daily(rows, count=count) if not epic else (rows[:count] if rows else [])

    # When epic is set, just shuffle deterministically and slice — no
    # need for the alternating-epics interleave.
    if epic and rows:
        rng = random.Random(_date_seed())
        pool = list(rows)
        rng.shuffle(pool)
        stories = pool[:count]

    return render_template(
        "mythology.html",
        stories=stories,
        epic=epic,
        total=len(rows),
        today=date.today().strftime("%A, %B %-d"),
    )


@mythology_bp.route("/api/mythology/today", methods=["GET"])
@login_required
def api_today():
    """JSON variant — useful if a future widget wants today's picks
    without a full page render."""
    epic = (request.args.get("epic") or "").strip().lower() or None
    if epic and epic not in ("ramayana", "mahabharata"):
        epic = None
    rows = _fetch_all(epic=epic)
    return jsonify({"stories": _pick_daily(rows), "total": len(rows)})

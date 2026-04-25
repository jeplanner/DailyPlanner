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
    """Daily 5 stories. The page renders all three filter views
    (Both / Ramayana / Mahabharata) server-side and JS toggles which
    one is visible — that way switching tabs feels instant and never
    flashes white during navigation. Initial visible view is driven
    by ?epic=<name>; missing or unknown values fall back to "both"."""
    epic = (request.args.get("epic") or "").strip().lower() or None
    if epic and epic not in ("ramayana", "mahabharata"):
        epic = None
    try:
        count = max(1, min(20, int(request.args.get("count") or 5)))
    except (TypeError, ValueError):
        count = 5

    # Fetch the full corpus once — it's small enough to slice in
    # Python without three separate DB hits.
    all_rows = _fetch_all()
    rama_rows = [r for r in all_rows if (r.get("epic") or "").lower() == "ramayana"]
    maha_rows = [r for r in all_rows if (r.get("epic") or "").lower() == "mahabharata"]

    rng_seed = _date_seed()

    def _shuffled(pool):
        rng = random.Random(rng_seed)
        out = list(pool)
        rng.shuffle(out)
        return out

    stories_both = _pick_daily(all_rows, count=count)
    stories_rama = _shuffled(rama_rows)[:count]
    stories_maha = _shuffled(maha_rows)[:count]

    return render_template(
        "mythology.html",
        stories_both=stories_both,
        stories_rama=stories_rama,
        stories_maha=stories_maha,
        active_epic=epic or "both",
        total=len(all_rows),
        ramayana_total=len(rama_rows),
        mahabharata_total=len(maha_rows),
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

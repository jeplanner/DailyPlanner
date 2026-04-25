"""
Quotes — daily motivational corpus served from the `quotes` table.

The Eisenhower page used to ship a hardcoded JS array of 41 quotes.
This blueprint backs that surface (and any future "browse / pick by
category" UI) with the database, so adding entries is just an INSERT
rather than a code deploy.

Endpoints:
    GET  /api/quotes/today              — date-stable pick for the day
    GET  /api/quotes/random             — uniform random
    GET  /api/quotes/categories         — list with counts
    Both /today and /random accept ?category=<name> to scope.

Performance notes:
    Quote rows are tiny (~150 bytes each) and the corpus is in the
    low hundreds. We pull once per request and pick in Python — no
    PostgREST RANDOM() trick, no separate index. Hot path is fine.
"""
import logging
from collections import Counter
from datetime import date

from flask import Blueprint, jsonify, request

from auth import login_required
from supabase_client import get

logger = logging.getLogger("daily_plan")
quotes_bp = Blueprint("quotes", __name__)


def _fetch_active(category=None, limit=500):
    params = {
        "is_active": "eq.true",
        "select": "id,text,author,category,tags,source,era",
        "limit": str(limit),
    }
    if category:
        params["category"] = f"eq.{category}"
    try:
        return get("quotes", params=params) or []
    except Exception as e:
        logger.warning("quotes fetch failed (migration missing?): %s", e)
        return []


def _date_index(rows, ref_date=None):
    """Stable date-based index — same calendar day picks the same row.
    Returns 0 when rows is empty so callers can early-return."""
    if not rows:
        return 0
    d = ref_date or date.today()
    key = f"{d.year}-{d.month}-{d.day}"
    h = 0
    for ch in key:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h % len(rows)


@quotes_bp.route("/api/quotes/today", methods=["GET"])
@login_required
def quote_today():
    """Stable quote-of-the-day. Optional ?category=<name> scopes the pool."""
    category = (request.args.get("category") or "").strip() or None
    rows = _fetch_active(category=category)
    if not rows:
        return jsonify({"quote": None})
    pick = rows[_date_index(rows)]
    return jsonify({"quote": pick, "total": len(rows)})


@quotes_bp.route("/api/quotes/random", methods=["GET"])
@login_required
def quote_random():
    """Uniform random pick. Honours ?category= and ?exclude_id= so the
    "shuffle" button never serves the same row twice in a row."""
    import random
    category = (request.args.get("category") or "").strip() or None
    exclude  = (request.args.get("exclude_id") or "").strip() or None
    rows = _fetch_active(category=category)
    if not rows:
        return jsonify({"quote": None})
    if exclude and len(rows) > 1:
        candidates = [r for r in rows if r.get("id") != exclude]
    else:
        candidates = rows
    pick = random.choice(candidates)
    return jsonify({"quote": pick, "total": len(rows)})


@quotes_bp.route("/api/quotes/categories", methods=["GET"])
@login_required
def quote_categories():
    """List every category surfaced in the active corpus, with counts.
    Used by future filter UIs (e.g. weekly theme picker)."""
    rows = _fetch_active()
    counts = Counter((r.get("category") or "").strip() for r in rows)
    out = [
        {"name": name, "count": n}
        for name, n in counts.most_common()
        if name
    ]
    return jsonify({"categories": out, "total": len(rows)})

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

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update
from supabase_client import delete as sb_delete

logger = logging.getLogger("daily_plan")
quotes_bp = Blueprint("quotes", __name__)


def _fetch_active(category=None, limit=500):
    params = {
        "is_active": "eq.true",
        # added_by surfaces so the page can show "delete" on rows the
        # current user contributed. Falls back gracefully if the
        # quotes_user_added migration hasn't run — supabase_client.get
        # returns the rows minus the unknown column when * is used,
        # but we ask explicitly here so a missing column 400s and we
        # log it. Drop added_by from the select if you hit that.
        "select": "id,text,author,category,tags,source,era,added_by",
        "limit": str(limit),
    }
    if category:
        params["category"] = f"eq.{category}"
    try:
        return get("quotes", params=params) or []
    except Exception as e:
        logger.warning("quotes fetch failed (migration missing?): %s", e)
        # Retry without the new column so the page still loads even
        # if MIGRATION_QUOTES_USER_ADDED hasn't been applied yet.
        try:
            params["select"] = "id,text,author,category,tags,source,era"
            return get("quotes", params=params) or []
        except Exception:
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


# ─────────── Browse + favorites ───────────────────────────────────

def _user_favorite_ids(user_id):
    """Set of quote_ids the user has starred. Best-effort — if the
    favorites migration hasn't been applied yet, returns empty."""
    try:
        rows = get(
            "quote_favorites",
            params={"user_id": f"eq.{user_id}", "select": "quote_id", "limit": "1000"},
        ) or []
    except Exception as e:
        logger.warning("quote_favorites fetch failed (migration missing?): %s", e)
        return set()
    return {r["quote_id"] for r in rows}


@quotes_bp.route("/quotes", methods=["GET"])
@login_required
def quotes_browse_page():
    """Browse Quotes page — server-renders the initial list to avoid a
    flash-of-empty-grid on first load. Filtering happens client-side
    over the rendered set; no need to paginate at this corpus size."""
    user_id = session["user_id"]
    rows = _fetch_active(limit=1000)
    favorites = _user_favorite_ids(user_id)

    counts = Counter((r.get("category") or "").strip() for r in rows)
    categories = [{"name": n, "count": c}
                  for n, c in counts.most_common() if n]

    enriched = []
    for r in rows:
        enriched.append({
            "id":       r.get("id"),
            "text":     r.get("text"),
            "author":   r.get("author"),
            "category": r.get("category"),
            "tags":     r.get("tags") or [],
            "era":      r.get("era"),
            "is_favorite": r.get("id") in favorites,
            # is_mine controls whether the delete button shows on the
            # card — only for quotes the logged-in user contributed.
            "is_mine":  r.get("added_by") == user_id and r.get("added_by") is not None,
        })

    # Favorites first when any are starred — gives the page a bias
    # toward what the user already cares about.
    enriched.sort(key=lambda q: (not q["is_favorite"], (q.get("category") or ""), (q.get("author") or "")))

    return render_template(
        "quotes_browse.html",
        quotes=enriched,
        categories=categories,
        favorites_count=len(favorites),
    )


# ─────────── Create / delete (user-added) ─────────────────────────

_VALID_ERAS = {"ancient", "classical", "modern"}
_MAX_TEXT_LEN = 600


@quotes_bp.route("/api/quotes", methods=["POST"])
@login_required
def create_quote():
    """Add a new quote to the corpus, attributed to the logged-in user.
    Body: { text, author?, category?, tags? (string[] | comma string),
            era? }"""
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Quote text is required"}), 400
    if len(text) > _MAX_TEXT_LEN:
        return jsonify({"error": f"Quote too long (max {_MAX_TEXT_LEN} characters)"}), 400

    author = (data.get("author") or "").strip()[:120] or None

    category = (data.get("category") or "").strip().lower()
    if not category:
        category = "wisdom"
    elif len(category) > 40:
        category = category[:40]
    # Restrict to a-z + dashes for stability of filter chips. Anything
    # weirder gets normalised. Empty after normalisation → fallback.
    import re
    category = re.sub(r"[^a-z\-]+", "-", category).strip("-") or "wisdom"

    raw_tags = data.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [t for t in (s.strip() for s in raw_tags.split(",")) if t]
    raw_tags = [str(t)[:40] for t in raw_tags if t][:10]

    era = (data.get("era") or "").strip().lower() or None
    if era and era not in _VALID_ERAS:
        era = None

    payload = {
        "text": text,
        "author": author,
        "category": category,
        "tags": raw_tags,
        "era": era,
        "is_active": True,
        "added_by": user_id,
    }
    try:
        rows = post("quotes", payload)
    except Exception as e:
        logger.error("quote insert failed: %s", e)
        return jsonify({"error": "Couldn't save quote — please try again."}), 502

    new_row = rows[0] if rows else None
    return jsonify({
        "ok": True,
        "id": new_row["id"] if new_row else None,
        "quote": new_row,
    })


@quotes_bp.route("/api/quotes/<quote_id>/delete", methods=["POST"])
@login_required
def delete_quote(quote_id):
    """Soft-delete a user-added quote. Seed rows (added_by IS NULL)
    are protected — only the original author can delete their own."""
    user_id = session["user_id"]
    rows = get(
        "quotes",
        params={
            "id": f"eq.{quote_id}",
            "added_by": f"eq.{user_id}",
            "select": "id",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found, or this isn't yours to delete."}), 403
    update(
        "quotes",
        params={"id": f"eq.{quote_id}", "added_by": f"eq.{user_id}"},
        json={"is_active": False},
    )
    return jsonify({"ok": True})


@quotes_bp.route("/api/quotes/favorite/<quote_id>", methods=["POST"])
@login_required
def toggle_favorite(quote_id):
    """Toggle favorite. Body: { favorite: true|false }, omitted = flip."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    # Resolve current state if caller didn't pre-decide.
    if "favorite" in data:
        want = bool(data["favorite"])
    else:
        existing = get(
            "quote_favorites",
            params={
                "user_id": f"eq.{user_id}",
                "quote_id": f"eq.{quote_id}",
                "select": "quote_id", "limit": "1",
            },
        ) or []
        want = not bool(existing)

    if want:
        # Idempotent insert — primary key on (user_id, quote_id) makes
        # this safe; PostgREST raises 409 on duplicate, which we swallow.
        try:
            post("quote_favorites", {"user_id": user_id, "quote_id": quote_id})
        except Exception as e:
            logger.info("favorite insert (likely duplicate, ok): %s", e)
    else:
        sb_delete(
            "quote_favorites",
            params={"user_id": f"eq.{user_id}", "quote_id": f"eq.{quote_id}"},
        )
    return jsonify({"ok": True, "is_favorite": want})

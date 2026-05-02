"""
Bedtime Stories — Indian + global moral tales backed by the
bedtime_stories table. Visibility is gated by a simple email
allowlist (BEDTIME_STORIES_USER_EMAILS env var). Users not on the
list see a 404 so the route is invisible to them and the nav link
is hidden by a context flag.

Schema and seed corpus both live in MIGRATION_BEDTIME_STORIES.sql.
Add new rows by editing the migration's INSERT block, or by running
INSERT statements directly against Supabase.
"""
import logging
import os
from flask import Blueprint, abort, render_template, request
from flask_login import current_user

from auth import login_required
from supabase_client import get

logger = logging.getLogger("daily_plan")
bedtime_stories_bp = Blueprint("bedtime_stories", __name__)

PAGE_SIZE = 20  # stories per index page


def _allowlist():
    """Lowercased set of emails allowed to see Bedtime Stories. Empty
    means feature is off for everyone — that's the safe default."""
    raw = os.environ.get("BEDTIME_STORIES_USER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def user_allowed(user=None):
    """Used by the route guard and by the context processor that hides
    the nav link from non-allowed users."""
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    email = (getattr(user, "email", "") or "").lower()
    return email in _allowlist()


def _fetch_all():
    """Fetch the full active corpus once. With ~500-1000 rows of small
    body text the table is small enough that one trip + Python slicing
    is faster than paginating against PostgREST per page."""
    try:
        return get("bedtime_stories", params={
            "is_active": "eq.true",
            "select": "slug,source,title,body,moral,sort_order",
            "order": "sort_order.asc,title.asc",
            "limit": "2000",
        }) or []
    except Exception as e:
        logger.warning("bedtime_stories fetch failed (migration missing?): %s", e)
        return []


def _split_paragraphs(body):
    """body is stored as a single TEXT column with paragraphs joined by
    a blank line. Splitting here keeps the templates dumb."""
    if not body:
        return []
    return [p.strip() for p in body.split("\n\n") if p.strip()]


# ─────────────────────── routes ────────────────────────
@bedtime_stories_bp.route("/bedtime-stories", methods=["GET"])
@login_required
def stories_index():
    """Paginated list with optional source filter. ?source=Aesop, ?page=2.
    Non-allowlisted users see a 404 so the feature is invisible."""
    if not user_allowed():
        abort(404)

    rows = _fetch_all()
    sources = sorted({r.get("source", "") for r in rows if r.get("source")})

    # Optional ?source=… filter.
    source_filter = (request.args.get("source") or "").strip()
    if source_filter:
        rows = [r for r in rows if (r.get("source") or "") == source_filter]

    # Pagination.
    try:
        page = max(1, int(request.args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    total = len(rows)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    page_rows = rows[start:start + PAGE_SIZE]

    # Pre-compute teaser (first paragraph) for each card so the template
    # stays linear.
    cards = []
    for i, r in enumerate(page_rows):
        paras = _split_paragraphs(r.get("body") or "")
        cards.append({
            "slug": r.get("slug"),
            "source": r.get("source"),
            "title": r.get("title"),
            "teaser": paras[0] if paras else "",
            "number": start + i + 1,
        })

    return render_template(
        "bedtime_stories.html",
        cards=cards,
        sources=sources,
        active_source=source_filter,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@bedtime_stories_bp.route("/bedtime-stories/<slug>", methods=["GET"])
@login_required
def story_detail(slug):
    if not user_allowed():
        abort(404)

    rows = _fetch_all()
    idx = next((i for i, r in enumerate(rows) if r.get("slug") == slug), -1)
    if idx < 0:
        abort(404)

    row = rows[idx]
    story = {
        "slug": row.get("slug"),
        "source": row.get("source"),
        "title": row.get("title"),
        "body": _split_paragraphs(row.get("body") or ""),
        "moral": row.get("moral") or "",
    }
    prev_story = rows[idx - 1] if idx > 0 else None
    next_story = rows[idx + 1] if idx + 1 < len(rows) else None
    return render_template(
        "bedtime_story.html",
        story=story,
        prev_story=prev_story,
        next_story=next_story,
    )

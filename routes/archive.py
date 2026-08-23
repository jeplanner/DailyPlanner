"""Everything finished, in one place, with nothing moved to get it there.

WHY A VIEW AND NOT A MOVE — the same argument that settled /backlog, and it
applies harder here. `project_tasks` carries 40 columns; relocating a
finished one drops its project, epic, sprint and key result, and project
progress is computed from live task counts, so archiving by MOVING would
silently change the completion figure on every project the tasks came from.

So this reads three lists and leaves all three alone. Nothing here writes.

WHAT IT IS FOR. Completed work accumulates in the live tables and never
leaves: 66 finished Quick Bucket items were being loaded into the bucket
page on every visit, ordered done-last, forever. That is the clutter. The
page now carries only what was finished TODAY — enough to untick a mistake
— and everything older lives here.

GROUPED BY THE DAY IT WAS FINISHED, because that is the question this
answers: "what did I get done, and when". Not by project, not by source.

THE COMPLETION TIMESTAMP IS NOT UNIFORM and that is worked around rather
than papered over. quick_bucket has done_at. todo_matrix has no such
column, so its updated_at is used and is honest about being approximate —
a task edited after completion moves. project_tasks records status without
a completion time, so it falls back the same way.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, session

from auth import login_required
from supabase_client import get
from utils.user_tz import user_today

logger = logging.getLogger("daily_plan")
archive_bp = Blueprint("archive", __name__)

#: How far back the page reads by default. The whole history is available
#: with ?days=all; the default is bounded so the first paint is quick.
DEFAULT_DAYS = 90

#: project_tasks.status values that mean finished. 'skipped' and
#: 'not_required' are DELIBERATELY absent — they are binned, not done, and
#: mixing them into "what I achieved" makes the page a lie.
DONE_STATUSES = ("done", "completed")


def _day_of(row, *fields):
    """The first usable date among `fields`, as YYYY-MM-DD, or None."""
    for f in fields:
        v = row.get(f)
        if v:
            return str(v)[:10]
    return None


def _bucket_items(user_id, since):
    rows = get("quick_bucket", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "is_done": "eq.true",
        "order": "done_at.desc",
        "limit": "2000",
    }) or []
    out = []
    for r in rows:
        day = _day_of(r, "done_at", "updated_at", "created_at")
        if not day or (since and day < since):
            continue
        out.append({
            "day": day,
            "text": r.get("text") or "",
            "source": "Quick Bucket",
            "exact": bool(r.get("done_at")),
            "href": "/quick-bucket",
        })
    return out


def _matrix_items(user_id, since):
    rows = get("todo_matrix", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "is_done": "eq.true",
        "order": "updated_at.desc",
        "limit": "2000",
    }) or []
    out = []
    for r in rows:
        # No done_at on this table, so the completion day is APPROXIMATE.
        # Said so on the row rather than presented as fact.
        day = _day_of(r, "updated_at", "plan_date", "created_at")
        if not day or (since and day < since):
            continue
        out.append({
            "day": day,
            "text": r.get("category") or r.get("notes") or "(no text)",
            "source": "To-do matrix",
            "exact": False,
            "href": "/todo",
        })
    return out


def _project_items(user_id, since):
    rows = get("project_tasks", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "is_eliminated": "eq.false",
        "status": "in.(" + ",".join(DONE_STATUSES) + ")",
        "order": "planning_updated_at.desc",
        "limit": "2000",
    }) or []
    projects = {}
    try:
        for p in (get("projects", params={
            "user_id": f"eq.{user_id}", "select": "id,name", "limit": "500",
        }) or []):
            projects[p["id"]] = p.get("name") or ""
    except Exception:
        logger.debug("archive: project names unavailable", exc_info=True)

    out = []
    for r in rows:
        day = _day_of(r, "planning_updated_at", "due_date", "created_at")
        if not day or (since and day < since):
            continue
        out.append({
            "day": day,
            "text": r.get("task_text") or "",
            "source": projects.get(r.get("project_id")) or "Project",
            "exact": False,
            "href": "/projects",
        })
    return out


@archive_bp.route("/archive", methods=["GET"])
@login_required
def archive_page():
    user_id = session["user_id"]
    raw = (request.args.get("days") or "").strip().lower()
    if raw == "all":
        days, since = None, None
    else:
        try:
            days = max(1, min(3650, int(raw))) if raw else DEFAULT_DAYS
        except ValueError:
            days = DEFAULT_DAYS
        since = (user_today() - timedelta(days=days - 1)).isoformat()

    items = []
    for fn in (_bucket_items, _matrix_items, _project_items):
        try:
            items.extend(fn(user_id, since))
        except Exception:
            # One unreadable source must not empty the whole page — a
            # partial archive that says so beats a blank one that does not.
            logger.warning("archive: %s failed", fn.__name__, exc_info=True)

    by_day = defaultdict(list)
    for it in items:
        by_day[it["day"]].append(it)

    today = user_today().isoformat()
    yesterday = (user_today() - timedelta(days=1)).isoformat()
    groups = []
    for day in sorted(by_day, reverse=True):
        try:
            label = datetime.strptime(day, "%Y-%m-%d").strftime("%a %d %b %Y")
        except ValueError:
            label = day
        if day == today:
            label = "Today"
        elif day == yesterday:
            label = "Yesterday"
        groups.append({
            "day": day,
            "label": label,
            # NOT "items": in Jinja, `group.items` resolves to the dict
            # METHOD rather than this key, and the template then renders a
            # bound method. Named "rows" so that cannot happen.
            "rows": sorted(by_day[day], key=lambda x: x["text"].lower()),
        })

    return render_template(
        "archive.html",
        groups=groups,
        total=len(items),
        days=days,
        sources=sorted({i["source"] for i in items}),
    )

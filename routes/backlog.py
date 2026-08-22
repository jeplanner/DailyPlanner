"""One backlog view over two lists that must stay where they are.

WHY A VIEW AND NOT A MOVE
-------------------------
The obvious answer to "I want one place to see everything outstanding" is to
move it all into one table. That was proposed here and it was wrong:
`project_tasks` carries 40 columns to `quick_bucket`'s 21, and moving one
drops its project, its key result, its initiative, its epic, its sprint, its
priority and its ordering. Project progress is computed from live task counts
too, so relocating tasks silently changes the completion figure on every
project they came from, for a reason nothing on screen would explain.

The want was a READING problem. So this reads both lists and leaves both
alone. Nothing here writes.

WHAT COUNTS AS BACKLOG
----------------------
Two different shapes of "no date on it yet":

  * Quick Bucket items in the FUTURE bucket — deliberately deferred, no
    deadline, no alarm.
  * Project tasks with no plan_date and no start_time — real work inside a
    project that has never been put on a day.

THE FUTURE RULE IS COPIED FROM THE PAGE, NOT REINVENTED. quick_bucket.js
groups an "at" item into Future when its pinned time falls beyond today, so
this does the same. A backlog that disagreed with the bucket page about what
is in Future would be worse than not having one — that lesson cost this
codebase three separate copies of the checklist schedule rule, each with a
different answer.
"""

import logging
from datetime import date, datetime

from flask import Blueprint, render_template, session

from services.login_service import login_required
from supabase_client import get
from utils.user_tz import user_now, user_today

logger = logging.getLogger("daily_plan")
backlog_bp = Blueprint("backlog", __name__)

#: Statuses that mean the task is no longer outstanding. Matches
#: routes/todo.py's vocabulary, plus the two the project trash uses.
_CLOSED = {"done", "skipped", "deleted", "not_required"}


def _future_bucket(user_id, today):
    """Quick Bucket rows that are deferred with no deadline."""
    rows = get("quick_bucket", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "is_done": "eq.false",
        "select": "id,text,time_bucket,due_at,priority_label,created_at",
        "limit": "1000",
    }) or []

    out = []
    for r in rows:
        bucket = (r.get("time_bucket") or "").lower()
        if bucket == "future":
            out.append({**r, "when": None})
            continue
        # An "at" item is Future only when its pinned moment is past today —
        # the same test the bucket page applies.
        if bucket == "at" and r.get("due_at"):
            try:
                due = datetime.fromisoformat(
                    r["due_at"].replace("Z", "+00:00")).astimezone(user_now().tzinfo)
            except (ValueError, TypeError):
                continue
            if due.date() > today:
                out.append({**r, "when": due.strftime("%d %b")})
    out.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
    return out


def _undated_project_tasks(user_id):
    """Open project tasks that have never been put on a day.

    `is_eliminated` is the flag the projects UI treats as removed — NOT
    `is_deleted`, which the project task list does not even filter on.
    """
    rows = get("project_tasks", params={
        "user_id": f"eq.{user_id}",
        "is_eliminated": "eq.false",
        "select": "task_id,task_text,status,project_id,due_date,priority,created_at,"
                  "plan_date,start_time",
        "limit": "2000",
    }) or []

    tasks = [
        r for r in rows
        if not r.get("plan_date") and not r.get("start_time")
        and (r.get("status") or "open").lower() not in _CLOSED
    ]

    names = {}
    ids = {r.get("project_id") for r in tasks if r.get("project_id")}
    if ids:
        projects = get("projects", params={
            "user_id": f"eq.{user_id}",
            "project_id": f"in.({','.join(str(i) for i in ids)})",
            "select": "project_id,name",
            "limit": "500",
        }) or []
        names = {p["project_id"]: p.get("name") or "Untitled project"
                 for p in projects}

    # Grouped by project, because the grouping is the whole reason these
    # stay where they are. A flat list here would be the move it is meant
    # to avoid, just rendered.
    groups = {}
    for t in tasks:
        pid = t.get("project_id")
        g = groups.setdefault(pid, {"project_id": pid,
                                    "name": names.get(pid, "No project"),
                                    "tasks": []})
        g["tasks"].append(t)
    ordered = sorted(groups.values(),
                     key=lambda g: (-len(g["tasks"]), g["name"].lower()))
    for g in ordered:
        g["tasks"].sort(key=lambda t: (t.get("due_date") or "9999",
                                       t.get("created_at") or ""))
    return ordered, len(tasks)


@backlog_bp.route("/backlog")
@login_required
def backlog_page():
    user_id = session["user_id"]
    today = user_today()

    try:
        future = _future_bucket(user_id, today)
    except Exception:
        logger.warning("backlog: bucket read failed", exc_info=True)
        future = []
    try:
        projects, task_count = _undated_project_tasks(user_id)
    except Exception:
        logger.warning("backlog: project task read failed", exc_info=True)
        projects, task_count = [], 0

    return render_template(
        "backlog.html",
        future=future,
        projects=projects,
        task_count=task_count,
        total=len(future) + task_count,
        today=today.isoformat(),
    )

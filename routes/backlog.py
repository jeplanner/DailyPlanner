"""The capture inbox: one place to dump every task, and the router out.

WHAT THIS IS FOR
----------------
"it should be one source stop for capturing all the laundry list of my
tasks and then i should be able to send it to various things like quick
bucket, projects, inbox, references etc."

So Backlog is where a thought lands when there is no time to decide where
it belongs, and the Quick Bucket is the shorter list of things actually
prioritised to be done. Capture here, route out from here.

WHY THE PROJECT TASKS ARE STILL NOT RELOCATED
---------------------------------------------
This page used to be read-only, for a reason that still holds for one of
the two lists: `project_tasks` carries 40 columns to `quick_bucket`'s 21,
and physically moving a row drops its project, key result, initiative,
epic, sprint, priority and ordering. Project progress is computed from
live task counts, so relocating tasks would silently change the completion
figure on every project they came from.

The routes below therefore write in two different ways on purpose:

  * A CAPTURED item is a quick_bucket row, and routing it really does move
    it — it is created here and has nothing to lose.
  * A PROJECT task is never moved. Promoting one writes a bucket row that
    POINTS at it (quick_bucket.source_task_id) and dates the task for
    today. Both stay in place, the project's figures stay honest, and
    ticking the bucket item closes the task with it. A plain copy was the
    obvious alternative and it lies: two rows for one piece of work makes
    the planner report more outstanding than exists.

Inbox and References are NOT written from here. Both are URL pipelines with
metadata fetching, AI description and auto-categorising behind them; the
browser posts to their own endpoints and then calls /api/backlog/drop, so
there is one implementation of each rather than a poorer second one.

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

from flask import Blueprint, jsonify, render_template, request, session

from services.login_service import login_required
from supabase_client import get, post, update
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

    try:
        picker = get("projects", params={
            "user_id": f"eq.{user_id}",
            "select": "project_id,name",
            "order": "name.asc",
            "limit": "500",
        }) or []
    except Exception:
        logger.warning("backlog: project picker read failed", exc_info=True)
        picker = []

    return render_template(
        "backlog.html",
        all_projects=picker,
        future=future,
        projects=projects,
        task_count=task_count,
        total=len(future) + task_count,
        today=today.isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────
# CAPTURE AND ROUTE
# ─────────────────────────────────────────────────────────────────────

def _own_bucket_row(user_id, item_id):
    rows = get("quick_bucket", params={
        "id": f"eq.{item_id}",
        "user_id": f"eq.{user_id}",
        "select": "id,text,time_bucket,is_deleted",
        "limit": "1",
    }) or []
    return rows[0] if rows else None


def _own_task_row(user_id, task_id):
    rows = get("project_tasks", params={
        "task_id": f"eq.{task_id}",
        "user_id": f"eq.{user_id}",
        "select": "task_id,task_text,project_id,plan_date,status",
        "limit": "1",
    }) or []
    return rows[0] if rows else None


@backlog_bp.route("/api/backlog/capture", methods=["POST"])
@login_required
def capture():
    """Dump one or many lines into the backlog.

    Pasting a list is the whole point of a laundry list, so every non-blank
    LINE becomes its own item. The bucket page's "@5m" and "@1pm" tokens are
    deliberately NOT parsed here: those pin a time, and a thing with a time
    on it is not backlog.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    raw = (data.get("text") or "")

    lines = [ln.strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln][:100]
    if not lines:
        return jsonify({"error": "Text required"}), 400

    made = []
    for ln in lines:
        try:
            res = post("quick_bucket", {
                "user_id": user_id,
                "text": ln[:2000],
                "time_bucket": "future",
                "is_done": False,
                "is_deleted": False,
            })
            if res:
                made.append(res[0])
        except Exception:
            logger.exception("backlog capture failed for one line")

    if not made:
        return jsonify({"error": "Could not save"}), 500
    return jsonify({"status": "ok", "created": made})


@backlog_bp.route("/api/backlog/drop", methods=["POST"])
@login_required
def drop():
    """Soft-delete a captured item once the browser has routed it onward.

    Used by the Inbox and References routes, which are posted straight to
    their own endpoints so their metadata pipelines still run. NEVER a hard
    delete — the row stays, flagged.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    item_id = data.get("id")
    if not item_id:
        return jsonify({"error": "id required"}), 400
    if not _own_bucket_row(user_id, item_id):
        return jsonify({"error": "Not found"}), 404
    update("quick_bucket",
           {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
           {"is_deleted": True})
    return jsonify({"status": "ok"})


@backlog_bp.route("/api/backlog/send", methods=["POST"])
@login_required
def send():
    """Route one backlog entry to where it actually belongs.

    `kind` says which of the two lists the row came from, because they are
    treated differently on purpose — see the module docstring.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    kind = (data.get("kind") or "bucket").strip().lower()
    dest = (data.get("to") or "").strip().lower()
    item_id = data.get("id")

    if not item_id:
        return jsonify({"error": "id required"}), 400

    # ── a project task: dated, never relocated ───────────────────────
    if kind == "task":
        if dest != "quick":
            return jsonify({"error": "A project task can only be sent to the "
                                     "Quick Bucket"}), 400
        task = _own_task_row(user_id, item_id)
        if not task:
            return jsonify({"error": "Not found"}), 404

        today = user_today().isoformat()
        try:
            res = post("quick_bucket", {
                "user_id": user_id,
                "text": (task.get("task_text") or "Task")[:2000],
                "time_bucket": "now",
                "is_done": False,
                "is_deleted": False,
                "source_task_id": task["task_id"],
            })
        except Exception:
            logger.exception("backlog: promoting a project task failed")
            return jsonify({"error": "Could not promote. If this persists the "
                                     "MIGRATION_BACKLOG_ROUTING.sql migration "
                                     "may not have been run."}), 500

        # Dating it is what takes it OUT of the backlog: backlog is defined
        # as "no plan_date and no start_time", so without this the task
        # would still sit here after being promoted.
        try:
            update("project_tasks",
                   {"task_id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                   {"plan_date": today})
        except Exception:
            logger.exception("backlog: dating the promoted task failed")

        return jsonify({"status": "ok", "created": (res or [None])[0],
                        "plan_date": today})

    # ── a captured item: really moved ────────────────────────────────
    row = _own_bucket_row(user_id, item_id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    text = (row.get("text") or "").strip()

    if dest == "quick":
        # Same table, same row — "prioritised" IS a bucket, so nothing is
        # copied and nothing can drift.
        update("quick_bucket",
               {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               {"time_bucket": "now", "due_at": None})
        return jsonify({"status": "ok"})

    if dest == "project":
        project_id = data.get("project_id")
        if not project_id:
            return jsonify({"error": "Pick a project"}), 400
        owns = get("projects", params={
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{user_id}",
            "select": "project_id",
            "limit": "1",
        }) or []
        if not owns:
            return jsonify({"error": "Not found"}), 404
        try:
            post("project_tasks", {
                "project_id": project_id,
                "user_id": user_id,
                "task_text": text[:2000],
                # The project's own backlog status, so it lands as work to
                # be planned rather than as work already underway.
                "status": "backlog",
                "start_date": user_today().isoformat(),
            })
        except Exception:
            logger.exception("backlog: creating the project task failed")
            return jsonify({"error": "Could not add to that project"}), 500
        update("quick_bucket",
               {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               {"is_deleted": True})
        return jsonify({"status": "ok"})

    if dest == "note":
        try:
            post("scribble_notes", {
                "user_id": user_id,
                "title": text[:120],
                "content": text,
                "notebook": "Backlog",
            })
        except Exception:
            logger.exception("backlog: creating the note failed")
            return jsonify({"error": "Could not save the note"}), 500
        update("quick_bucket",
               {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               {"is_deleted": True})
        return jsonify({"status": "ok"})

    return jsonify({"error": "Unknown destination"}), 400

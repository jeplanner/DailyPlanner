
from datetime import date, timedelta
import json

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from config import PRIORITY_MAP, SORT_PRESETS
import logger
from routes.todo import group_tasks_smart
from services.gantt_service import build_gantt_tasks
from services.login_service import login_required
from services.task_service import complete_task_occurrence, compute_next_occurrence
from supabase_client import get, post, update

projects_bp = Blueprint("projects", __name__)

@projects_bp.route("/projects")
@login_required
def projects():
    user_id = session["user_id"]

    include_archived = request.args.get("include_archived", "0") == "1"

    params = {
        "user_id": f"eq.{user_id}",
        "order": "created_at.asc",
    }
    if not include_archived:
        params["is_archived"] = "eq.false"

    projects = get("projects", params=params) or []

    # Batch-fetch task counts for all projects in one query
    if projects:
        ids_str = ",".join(str(p["project_id"]) for p in projects)
        all_tasks = get("project_tasks", params={
            "project_id": f"in.({ids_str})",
            "is_eliminated": "eq.false",
            "select": "project_id,status",
        }) or []

        task_counts, done_counts = {}, {}
        for t in all_tasks:
            pid = t["project_id"]
            task_counts[pid] = task_counts.get(pid, 0) + 1
            if t["status"] == "done":
                done_counts[pid] = done_counts.get(pid, 0) + 1

        for p in projects:
            pid = p["project_id"]
            total = task_counts.get(pid, 0)
            done = done_counts.get(pid, 0)
            p["task_count"] = total
            p["done_count"] = done
            p["completion_pct"] = round(done / total * 100) if total else 0

    return render_template(
        "projects.html",
        projects=projects,
        include_archived=include_archived,
    )

@projects_bp.route("/projects/<project_id>/set-sort", methods=["POST"])
@login_required
def set_project_sort(project_id):
    data = request.get_json() or {}
    sort = data.get("sort")

    if not sort:
        return jsonify({"error": "Missing sort"}), 400

    update(
        "projects",
        params={"project_id": f"eq.{project_id}"},
        json={"default_sort": sort}
    )

    return jsonify({"status": "ok"})

@projects_bp.route("/projects/<project_id>/tasks")
@login_required
def project_tasks(project_id):
    user_id = session["user_id"]

    # ---------------------------------
    # Load project
    # ---------------------------------
    rows = get(
        "projects",
        params={"project_id": f"eq.{project_id}", "user_id": f"eq.{user_id}"},
    )
    if not rows:
        return "Project not found", 404

    project = rows[0]

    # ---------------------------------
    # Read filters from URL
    # ---------------------------------
    hide_completed = request.args.get("hide_completed", "0") == "1"
    overdue_only   = request.args.get("overdue_only", "0") == "1"

    sort = request.args.get("sort") or project.get("default_sort", "smart")
    order = SORT_PRESETS.get(sort, SORT_PRESETS["smart"])

    # ---------------------------------
    # Fetch tasks (with server-side filtering)
    # ---------------------------------
    today = date.today()

    params = {
        "project_id": f"eq.{project_id}",
        "is_eliminated": "eq.false",
        "select": "task_id,task_text,status,due_date,due_time,priority,start_date,"
                  "duration_days,delegated_to,is_pinned,planned_hours,actual_hours,"
                  "is_recurring,recurrence_type,recurrence_days,recurrence_interval,"
                  "recurrence_end,auto_advance,order_index,created_at,"
                  "key_result_id,initiative_id",
        "order": order,
        "limit": 500,
    }

    # Push filters to database
    if hide_completed:
        params["status"] = "neq.done"
    if overdue_only:
        params["status"] = "neq.done"
        params["due_date"] = f"lt.{today.isoformat()}"

    raw_tasks = get("project_tasks", params=params) or []

    tasks = [_build_task_dict(t, project, today) for t in raw_tasks]

    # Resolve OKR identifiers for each task so the client can filter by
    # Objective / Key Result / Initiative. Walk task → initiative → KR →
    # objective. Legacy rows with only key_result_id set still resolve.
    _stamp_okr_ids(tasks, user_id)

    # Batch-load subtasks for all tasks in ONE query
    task_ids = [t["task_id"] for t in tasks]
    subtask_map = {}
    if task_ids:
        ids_str = ",".join(str(tid) for tid in task_ids)
        all_subtasks = get("project_subtasks", params={
            "parent_task_id": f"in.({ids_str})",
            "select": "id,parent_task_id,title,is_done",
            "order": "created_at.asc",
            "limit": 1000,
        }) or []
        for st in all_subtasks:
            pid = st.get("parent_task_id")
            subtask_map.setdefault(pid, []).append(st)

    # Attach subtasks to each task
    for t in tasks:
        t["subtasks"] = subtask_map.get(t["task_id"], [])

    grouped_tasks = group_tasks_smart(tasks)

    return render_template(
        "project_tasks.html",
        project=project,
        grouped_tasks=grouped_tasks,
        today=today.isoformat(),
        selected_date=today.isoformat(),
        sort=sort,
        hide_completed=hide_completed,
        overdue_only=overdue_only,
    )


@projects_bp.route("/projects/<project_id>/tasks/add", methods=["POST"])
@login_required
def add_project_task(project_id):
    text = request.form.get("task_text", "").strip()
    start_date = request.form.get("start_date") or date.today().isoformat()

    if not text:
        return redirect(url_for("projects.project_tasks", project_id=project_id))

    max_order = get_max_order_index(project_id)
    order_index = (max_order or 0) + 1

    post(
        "project_tasks",
        {
            "project_id": project_id,
            "user_id": session["user_id"],
            "task_text": text,
            "status": "backlog",
            "start_date": start_date,
            "order_index": order_index,
        },
    )

    return redirect(url_for("projects.project_tasks", project_id=project_id))


@projects_bp.route("/projects/tasks/send-to-eisenhower", methods=["POST"])
@login_required
def send_project_task_to_eisenhower():
    data = request.get_json() or {}

    task_id = data.get("task_id")
    plan_date = data.get("plan_date")
    quadrant = (data.get("quadrant") or "do").lower()

    if not task_id or not plan_date:
        return jsonify({"error": "Missing task_id or plan_date"}), 400

    rows = get(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"}
    )

    if not rows:
        return jsonify({"error": "Task not found"}), 404

    task = rows[0]
    existing = get(
    "todo_matrix",
    params={
        "source_task_id": f"eq.{task_id}",
        "plan_date": f"eq.{plan_date}",
    }
)

    if existing:
     return jsonify({"status": "already-sent"})

    post(
        "todo_matrix",
        {
            "task_text": task["task_text"],   # ✅ FIXED
            "plan_date": plan_date,           # ✅ REQUIRED
            "quadrant": quadrant,              # ✅ CHECK constraint
            "project_id": task.get("project_id"),
            "user_id": session["user_id"],     # ✅ IMPORTANT
            "source_task_id": task_id,
            "is_done": False,
        }
    )

    return jsonify({"status": "ok"})




@projects_bp.route("/projects/tasks/status", methods=["POST"])
@login_required
def update_project_task_status():
    data = request.get_json(force=True)

    task_id   = data["task_id"]
    status    = data["status"]
    task_date = data.get("date")
    user_id   = session["user_id"]

    # Load base task (rule)
    rows = get(
        "project_tasks",
        params={
            "task_id": f"eq.{task_id}",
            "user_id": f"eq.{user_id}"
        }
    )

    if not rows:
        return jsonify({"error": "Task not found"}), 404

    task = rows[0]

    # ------------------------------------------------
    # CASE 1: recurring + per-day completion
    # ------------------------------------------------
    if task_date and task.get("is_recurring"):
        if status == "done":
            complete_task_occurrence(
                user_id=user_id,
                task_id=task_id,
                task_date=task_date
            )

            # 🔁 AUTO-ADVANCE (if enabled)
            if task.get("auto_advance", True):
                next_date = compute_next_occurrence(
                    task,
                    date.fromisoformat(task_date)
                )

                if next_date:
                    update(
                        "project_tasks",
                        params={"task_id": f"eq.{task_id}"},
                        json={
                            "start_date": next_date.isoformat(),
                            "due_date": next_date.isoformat(),  # ✅ FIX
                            "status": "open"
                        }
                    )

        return jsonify({"status": "ok"})

    # ------------------------------------------------
    # CASE 2: normal (non-recurring) task
    # ------------------------------------------------
    # Normalize legacy "not_required" → "deleted"
    if status == "not_required":
        status = "deleted"

    patch = {"status": status}
    if status == "deleted":
        # Soft delete: flip is_eliminated so filtered listings stop showing it
        patch["is_eliminated"] = True
    elif status == "open":
        # Undo path — reopen also un-eliminates
        patch["is_eliminated"] = False

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}", "user_id": f"eq.{user_id}"},
        json=patch,
    )

    return jsonify({"status": "ok"})


# ==========================================================
# BULK UPDATE (selection mode)
# ==========================================================

_PT_VALID_PRIORITIES = {"low", "medium", "high"}
_PT_PRIORITY_RANK = {"high": 1, "medium": 2, "low": 3}
_PT_OPEN_STATUSES = {"open", "in_progress"}
_PT_RESOLVED_STATUSES = {"done", "skipped", "deleted"}
_PT_ALL_STATUSES = _PT_OPEN_STATUSES | _PT_RESOLVED_STATUSES

@projects_bp.route("/projects/tasks/bulk-update", methods=["POST"])
@login_required
def bulk_update_project_tasks():
    """
    Apply a patch to many project_tasks rows at once.

    Body: { ids: [task_id, ...], patch: { status?, priority? } }

    Soft-delete semantics: status='deleted' also sets is_eliminated=true.
    Setting priority also updates priority_rank (1=high, 2=medium, 3=low).
    All writes are scoped to the authenticated user.
    """
    data = request.get_json(force=True) or {}
    ids = data.get("ids") or []
    patch = data.get("patch") or {}

    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids required"}), 400
    if not isinstance(patch, dict) or not patch:
        return jsonify({"error": "patch required"}), 400

    user_id = session["user_id"]

    # Build the DB patch
    db_patch = {}

    if "status" in patch:
        status = (patch["status"] or "").strip().lower()
        # Legacy alias
        if status == "not_required":
            status = "deleted"
        if status not in _PT_ALL_STATUSES:
            return jsonify({"error": "invalid status"}), 400
        db_patch["status"] = status
        if status == "deleted":
            db_patch["is_eliminated"] = True
        elif status == "open":
            # Reopening un-eliminates (symmetric with per-row update)
            db_patch["is_eliminated"] = False

    if "priority" in patch:
        priority = (patch["priority"] or "").strip().lower()
        if priority not in _PT_VALID_PRIORITIES:
            return jsonify({"error": "invalid priority"}), 400
        db_patch["priority"] = priority
        db_patch["priority_rank"] = _PT_PRIORITY_RANK[priority]

    if not db_patch:
        return jsonify({"error": "no valid fields in patch"}), 400

    # Sanitize IDs: keep non-empty strings only
    clean_ids = [str(i) for i in ids if isinstance(i, (str, int)) and str(i)]
    if not clean_ids:
        return jsonify({"error": "no valid ids"}), 400

    # Single bulk UPDATE scoped to the user
    update(
        "project_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "task_id": f"in.({','.join(clean_ids)})",
        },
        json=db_patch,
    )

    return jsonify({"status": "ok", "updated": len(clean_ids)})


@projects_bp.route("/projects/tasks/unsend", methods=["POST"])
@login_required
def unsend_task_from_eisenhower():
    data = request.get_json() or {}

    task_id = data.get("task_id")
    scope = data.get("scope", "today_future")  # optional

    if not task_id:
        return jsonify({"error": "Missing task_id"}), 400

    today = date.today().isoformat()

    # ---------------------------------------------
    # Remove Eisenhower entries linked to this task
    # ---------------------------------------------
    params = {
        "source_task_id": f"eq.{task_id}",
        "is_deleted": "eq.false",
    }

    # Optional safety: only today & future
    if scope == "today_future":
        params["plan_date"] = f"gte.{today}"

    update(
        "todo_matrix",
        params=params,
        json={"is_deleted": True},
    )

    return jsonify({"status": "ok"})



@projects_bp.route("/projects/tasks/update-date", methods=["POST"])
@login_required
def update_project_task_date():
    data = request.get_json() or {}
    task_id = data.get("task_id")
    due_date = data.get("due_date")

    if not task_id:
        return jsonify({"error": "Missing task id"}), 400

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={"due_date": due_date},
    )
    logger.info(f"👉 task_id={task_id}, new_date={due_date}")
    return jsonify({"status": "ok"})
@projects_bp.route("/projects/tasks/<task_id>/update", methods=["POST"])
@login_required
def update_task(task_id):
    data = request.json or {}

    # Build update payload safely (PATCH semantics)
    updates = {}

    allowed_fields = [
        "task_text",
        "start_date",
        "due_date",
        "due_time",
        "notes",
        "status",
        "planned_hours",
        "actual_hours",
        "priority",
        "elimination_reason",
        "duration_days",
        "delegated_to",
        "is_recurring",
        "recurrence_type",
        "recurrence_days",
        "recurrence_interval",
        "recurrence_end",
        "auto_advance",
        "quadrant",
        "key_result_id",
        "initiative_id",
    ]

    for field in allowed_fields:
        if field in data:
            updates[field] = data[field]

    # 🔒 Safety: never allow task_text to be null
    if "task_text" in updates and updates["task_text"] is None:
        return jsonify({
            "error": "task_text cannot be null"
        }), 400

    # 🛑 No-op protection
    if not updates:
        return jsonify({"status": "noop"})
    if "start_time" in updates and updates["start_time"] == "":
        updates["start_time"] = None
    # Empty string → NULL for key_result_id so the FK doesn't blow up
    if "key_result_id" in updates and updates["key_result_id"] == "":
        updates["key_result_id"] = None
    if "initiative_id" in updates and updates["initiative_id"] == "":
        updates["initiative_id"] = None

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json=updates
    )

    return jsonify({"status": "ok"})



@projects_bp.route("/projects/tasks/update-duration", methods=["POST"])
@login_required
def update_task_duration():
    data = request.get_json()

    task_id = data["task_id"]
    duration_days = int(data["duration_days"])

    # 1️⃣ Fetch start_date from DB (source of truth)
    rows = get(
        "project_tasks",
        params={
            "task_id": f"eq.{task_id}",
            "select": "start_date",
        },
    )

    if not rows or not rows[0].get("start_date"):
        return jsonify({"error": "Missing start date"}), 400

    start_date = date.fromisoformat(rows[0]["start_date"])

    # 2️⃣ ✅ Compute due date HERE
    due_date = compute_due_date(start_date, duration_days)

    # 3️⃣ Persist everything
    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={
            "duration_days": duration_days,
            "due_date": due_date.isoformat(),
        },
    )

    return jsonify({
        "due_date": due_date.isoformat()
    })


@projects_bp.route("/projects/tasks/update-delegation", methods=["POST"])
@login_required
def update_delegation():
    data = request.get_json()

    update(
        "project_tasks",
        params={"task_id": f"eq.{data['id']}"},
        json={
            "delegated_to": data.get("delegated_to")
        }
    )

    return "", 204

@projects_bp.route("/projects/tasks/eliminate", methods=["POST"])
@login_required
def eliminate_task():
    data = request.get_json()

    task_id = data["id"]
    reason = data.get("reason")

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={
            "is_eliminated": True,
            "elimination_reason": reason,
        }
    )

    return "", 204

@projects_bp.route("/projects/tasks/update-time", methods=["POST"])
@login_required
def update_due_time():
    data = request.get_json()

    update(
        "project_tasks",
        params={"task_id": f"eq.{data['id']}"},
        json={
            "due_time": data.get("due_time")
        }
    )

    return "", 204
@projects_bp.route("/projects/tasks/update-planning", methods=["POST"])
@login_required
def update_task_planning():
    data = request.get_json()

    task_id = data.get("task_id")
    start_str = (data.get("start_date") or "").strip()

    if not task_id or not start_str:
        return jsonify({"error": "task_id and start_date are required"}), 400

    try:
        start = date.fromisoformat(start_str)
    except ValueError:
        return jsonify({"error": "Invalid start_date format"}), 400

    days    = int(data.get("duration_days") or 1)

    due_date = start + timedelta(days=days)  # noqa: F821

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={
            "start_date": str(start),
            "duration_days": days,
            "due_date": str(due_date),
        }
    )

    return jsonify({
        "due_date": str(due_date)
    })
@projects_bp.route("/projects/<project_id>/gantt")
@login_required
def project_gantt(project_id):
    tasks = get(
        "project_tasks",
        params={
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{session['user_id']}",
            "is_eliminated": "eq.false",
            "select": "task_id,task_text,start_date,duration_days,planned_hours,actual_hours",
            "order": "start_date.asc",
            "limit": 500,
        },
    ) or []

    gantt_tasks = build_gantt_tasks(tasks)

    # Pass the list directly; the template renders it via `| tojson`.
    return render_template(
        "project_gantt.html",
        project_id=project_id,
        gantt_tasks=gantt_tasks,
    )
@projects_bp.route("/projects/tasks/update-planned", methods=["POST"])
@login_required
def update_planned():
    data = request.get_json()
    update(
        "project_tasks",
        params={"task_id": f"eq.{data['task_id']}"},
        json={"planned_hours": data["planned_hours"]}
    )
    return "", 204


@projects_bp.route("/projects/tasks/update-actual", methods=["POST"])
@login_required
def update_actual():
    data = request.get_json()
    update(
        "project_tasks",
        params={"task_id": f"eq.{data['task_id']}"},
        json={"actual_hours": data["actual_hours"]}
    )
    return "", 204
@projects_bp.route("/projects/tasks/update-priority", methods=["POST"])
@login_required
def update_priority():
    data = request.get_json()
    task_id = data["task_id"]
    priority = data["priority"]

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={
            "priority": priority,
            "priority_rank": PRIORITY_MAP.get(priority, 2)
        }
    )

    return {"status": "ok"}


@projects_bp.route("/projects/<project_id>/archive", methods=["POST"])
@login_required
def archive_project(project_id):
    """
    Soft-delete a project. The row stays in the DB with is_archived=true.
    Listings filter by is_archived=eq.false, so an archived project
    disappears from the UI but can be restored (see restore_project).

    Tasks under the project are not cascaded — they keep their current
    is_eliminated state. Archiving a project is reversible; a user who
    wanted to also delete the tasks would do that step explicitly.
    """
    update(
        "projects",
        params={
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{session['user_id']}",
        },
        json={"is_archived": True},
    )
    return jsonify({"status": "ok"})


@projects_bp.route("/projects/<project_id>/restore", methods=["POST"])
@login_required
def restore_project(project_id):
    """Un-archive a previously soft-deleted project."""
    update(
        "projects",
        params={
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{session['user_id']}",
        },
        json={"is_archived": False},
    )
    return jsonify({"status": "ok"})


@projects_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def create_project():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            return "Project name is required", 400

        post(
            "projects",
            {
                "name": name,
                "description": description or None,
                "user_id": session.get("user_id")
            }
        )

        return redirect("/projects")

    return render_template("project_new.html")

@projects_bp.route("/projects/tasks/bulk-add", methods=["POST"])
@login_required
def bulk_add_tasks():
    data = request.json or {}

    project_id = data.get("project_id")
    tasks = data.get("tasks", [])

    if not project_id:
        return jsonify({"error": "project_id missing"}), 400

    if not tasks:
        return jsonify({"error": "no tasks provided"}), 400

    today = date.today().isoformat()

    # Fetch max order_index ONCE (not per task)
    max_order = get_max_order_index(project_id) or 0

    rows = []
    for idx, text in enumerate(tasks):
        if not text.strip():
            continue

        rows.append({
            "project_id": project_id,
            "task_text": text.strip(),
            "start_date": today,
            "priority": "medium",
            "priority_rank": PRIORITY_MAP["medium"],
            "order_index": max_order + idx + 1,
            "duration_days": 0,
            "status": "open",
            "user_id": session["user_id"]
        })

    if not rows:
        return jsonify({"error": "no valid tasks"}), 400

    insert_many("project_tasks", rows)

    return jsonify({
        "status": "ok",
        "count": len(rows)
    })
@projects_bp.route("/projects/<project_id>/export-csv")
@login_required
def export_csv(project_id):
    """Export all tasks and subtasks as CSV."""
    from flask import Response
    import csv
    import io

    user_id = session["user_id"]

    # Verify project ownership
    proj = get("projects", params={
        "project_id": f"eq.{project_id}", "user_id": f"eq.{user_id}",
        "select": "name"
    })
    if not proj:
        return "Project not found", 404

    project_name = proj[0]["name"]

    # Fetch tasks
    tasks = get("project_tasks", params={
        "project_id": f"eq.{project_id}",
        "is_eliminated": "eq.false",
        "select": "task_id,task_text,status,priority,start_date,due_date,due_time,"
                  "duration_days,planned_hours,actual_hours,delegated_to,notes,"
                  "is_pinned,is_recurring,recurrence_type",
        "order": "order_index.asc",
    }) or []

    # Batch-fetch subtasks
    task_ids = [t["task_id"] for t in tasks]
    subtask_map = {}
    if task_ids:
        ids_str = ",".join(str(tid) for tid in task_ids)
        subtasks = get("project_subtasks", params={
            "parent_task_id": f"in.({ids_str})",
            "select": "parent_task_id,title,is_done",
            "order": "created_at.asc",
        }) or []
        for st in subtasks:
            subtask_map.setdefault(st["parent_task_id"], []).append(st)

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "task", "parent", "status", "priority", "start_date", "due_date",
        "due_time", "duration", "planned_hours", "actual_hours",
        "delegated_to", "is_pinned", "recurring", "notes"
    ])

    for t in tasks:
        writer.writerow([
            t.get("task_text", ""),
            "",  # no parent — it's a task
            t.get("status", ""),
            t.get("priority", ""),
            t.get("start_date", ""),
            t.get("due_date", ""),
            t.get("due_time", ""),
            t.get("duration_days", ""),
            t.get("planned_hours", ""),
            t.get("actual_hours", ""),
            t.get("delegated_to", ""),
            "yes" if t.get("is_pinned") else "",
            t.get("recurrence_type", "") if t.get("is_recurring") else "",
            t.get("notes", ""),
        ])

        # Write subtasks for this task
        for st in subtask_map.get(t["task_id"], []):
            writer.writerow([
                st.get("title", ""),
                t.get("task_text", ""),  # parent = task name
                "done" if st.get("is_done") else "open",
                "", "", "", "", "", "", "", "", "", "", "",
            ])

    csv_data = output.getvalue()
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_tasks.csv"'}
    )


@projects_bp.route("/projects/tasks/import-csv", methods=["POST"])
@login_required
def import_csv():
    """Import tasks and subtasks from parsed CSV data (sent as JSON from client)."""
    data = request.get_json() or {}
    project_id = data.get("project_id")
    rows = data.get("rows", [])

    if not project_id or not rows:
        return jsonify({"error": "project_id and rows required"}), 400

    user_id = session["user_id"]
    max_order = get_max_order_index(project_id) or 0

    created_tasks = 0
    created_subtasks = 0

    # First pass: create all tasks
    task_map = {}  # row_index -> task_id
    for idx, row in enumerate(rows):
        task_text = (row.get("task") or "").strip()
        if not task_text:
            continue

        # Skip if this is a subtask row (has parent)
        if row.get("parent"):
            continue

        result = post("project_tasks", {
            "project_id": project_id,
            "user_id": user_id,
            "task_text": task_text,
            "status": row.get("status", "open"),
            "priority": row.get("priority", "medium"),
            "start_date": row.get("start_date") or date.today().isoformat(),
            "due_date": row.get("due_date") or None,
            "duration_days": int(row["duration"]) if row.get("duration") else 0,
            "planned_hours": float(row["planned_hours"]) if row.get("planned_hours") else None,
            "notes": row.get("notes") or None,
            "order_index": max_order + idx + 1,
            "priority_rank": PRIORITY_MAP.get(row.get("priority", "medium"), 2),
        })

        if result:
            task_id = result[0].get("task_id")
            task_map[task_text] = task_id
            created_tasks += 1

    # Second pass: create subtasks
    for row in rows:
        parent_name = (row.get("parent") or "").strip()
        subtask_text = (row.get("task") or "").strip()

        if not parent_name or not subtask_text:
            continue

        parent_task_id = task_map.get(parent_name)
        if not parent_task_id:
            continue

        try:
            post("project_subtasks", {
                "project_id": project_id,
                "parent_task_id": parent_task_id,
                "title": subtask_text,
                "is_done": False,
            })
            created_subtasks += 1
        except Exception:
            pass  # Skip FK failures

    return jsonify({
        "status": "ok",
        "tasks_created": created_tasks,
        "subtasks_created": created_subtasks,
    })


@projects_bp.route("/projects/tasks/pin", methods=["POST"])
@login_required
def toggle_pin():
    data = request.get_json() or {}

    task_id = data.get("task_id")
    is_pinned = data.get("is_pinned")

    if not task_id:
        return jsonify({"error": "Missing task_id"}), 400

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={"is_pinned": bool(is_pinned)}
    )

    return jsonify({"status": "ok"})
@projects_bp.route("/projects/tasks/reorder", methods=["POST"])
@login_required
def reorder_tasks():
    data = request.get_json() or {}

    dragged = data.get("dragged_id")
    target = data.get("target_id")

    if not dragged or not target:
        return jsonify({"error": "Missing task ids"}), 400

    rows = get(
        "project_tasks",
        params={
            "task_id": f"in.({dragged},{target})",
            "select": "task_id,order_index,due_date,priority_rank,is_pinned"
        }
    )

    if len(rows) != 2:
        return jsonify({"error": "Tasks not found"}), 404

    a, b = rows
    if (
    a.get("due_date") != b.get("due_date")
    or a.get("priority_rank") != b.get("priority_rank")
    or a.get("is_pinned") != b.get("is_pinned")
    ):
        return jsonify({"error": "Tasks must have the same due date, priority, and pin status to reorder"}), 400
    # 🔄 swap order_index
    update(
        "project_tasks",
        params={"task_id": f"eq.{a['task_id']}"},
        json={"order_index": b["order_index"]}
    )
    update(
        "project_tasks",
        params={"task_id": f"eq.{b['task_id']}"},
        json={"order_index": a["order_index"]}
    )

    return jsonify({"status": "ok"})
@projects_bp.route("/api/v2/project-tasks")
@login_required
def get_project_tasks():
    user_id = session["user_id"]
    date = request.args.get("date")

    if not date:
        return jsonify([])

    try:
        tasks = get(
            "project_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "is_eliminated": "eq.false",
                "status": "neq.done",
                "or": f"(due_date.is.null,due_date.lte.{date})",
                "select": "task_id,task_text,priority,project_id,start_time,due_date,"
                          "is_recurring,recurrence_type",
                "limit": 200,
            }
        ) or []
    except Exception as e:
        import logging
        logging.getLogger("daily_plan").error("project-tasks API error: %s", str(e))
        tasks = []

    return jsonify(tasks)

@projects_bp.route("/api/v2/project-tasks/<task_id>/schedule", methods=["POST"])
@login_required
def schedule_project_task(task_id):
    data = request.json

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={
            "plan_date": data["plan_date"],
            "start_time": data["start_time"],
        }
    )

    return {"ok": True}
@projects_bp.route("/api/v2/project-tasks/<task_id>", methods=["GET"])
@login_required
def get_single_project_task(task_id):

    task = get(
        "project_tasks",
        params={
            "task_id": f"eq.{task_id}",
            "select": "*"
        }
    )

    return jsonify(task[0] if task else {})
@projects_bp.route("/api/v2/project-tasks/<task_id>", methods=["PUT"])
@login_required
def update_project_task(task_id):

    data = request.get_json(silent=True) or {}

    allowed_fields = {
        "task_text",
        "notes",
        "status",
        "priority",
        "planned_hours",
        "actual_hours",
        "duration_days",
        "due_date",
        "start_time",
        "recurrence",
        "recurrence_type",
        "recurrence_interval",
        "recurrence_end"
    }

    update_payload = {
        k: v for k, v in data.items()
        if k in allowed_fields
    }

    # ✅ normalize empty strings safely
    update_payload = {
        k: (None if isinstance(v, str) and v.strip() == "" else v)
        for k, v in update_payload.items()
    }

    # ✅ normalize numeric fields
    for field in ["planned_hours", "actual_hours", "duration_days"]:
        if field in update_payload:
            val = update_payload[field]

            if val is None:
                continue

            try:
                update_payload[field] = int(float(val))
            except:
                update_payload[field] = None

    # ✅ normalize date/time fields
    for field in ["due_date", "start_time"]:
        if field in update_payload:
            val = update_payload[field]

            if val is None:
                continue

            val = str(val).strip()
            update_payload[field] = val if val else None

    if not update_payload:
        return jsonify({"error": "No valid fields to update"}), 400

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json=update_payload
    )

    return jsonify({"success": True})


@projects_bp.route("/api/v2/project-tasks/<task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):
    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={"is_completed": True}
    )

    return {"ok": True}

@projects_bp.route("/subtask/list/<task_id>")
@login_required
def list_subtasks(task_id):
    rows = get(
        "project_subtasks",
        params={
            "parent_task_id": f"eq.{task_id}",
            "select": "id,title,is_done",
            "order": "id.asc",
        }
    ) or []
    return jsonify(rows)


@projects_bp.route("/subtask/add", methods=["POST"])
@login_required
def add_subtask():
    data = request.get_json()
    title = (data.get("title") or "").strip()

    if not title:
        return jsonify({"error": "Subtask title required"}), 400

    task_id = data.get("task_id")
    project_id = data.get("project_id")

    # IMPORTANT: Run this SQL in Supabase to fix FK (points to todo_matrix instead of project_tasks):
    #   ALTER TABLE project_subtasks DROP CONSTRAINT project_subtasks_parent_task_id_fkey;
    #   ALTER TABLE project_subtasks ADD CONSTRAINT project_subtasks_parent_task_id_fkey
    #     FOREIGN KEY (parent_task_id) REFERENCES project_tasks(task_id) ON DELETE CASCADE;

    try:
        rows = post(
            "project_subtasks",
            {
                "project_id": project_id,
                "parent_task_id": task_id,
                "title": title,
                "is_done": False,
            },
        )
        if rows:
            return jsonify(rows[0])
    except Exception as e:
        logger.error("Subtask add failed: %s", str(e))
        return jsonify({"error": "Failed to add subtask. Check database constraints."}), 500

    return jsonify({"id": None, "title": title, "is_done": False})

@projects_bp.route("/subtask/toggle", methods=["POST"])
@login_required
def toggle_subtask():
    data = request.get_json(force=True)

    update(
        "project_subtasks",
        params={"id": f"eq.{data['id']}"},
        json={"is_done": bool(data.get("is_done"))},
    )
    
    return ("", 204)

def _stamp_okr_ids(tasks, user_id):
    """Resolve and attach objective_id / key_result_id / initiative_id to each task.

    Tasks link to an Initiative; KR and Objective are resolved by walking up
    (initiative → key_result → objective). Legacy tasks that still have a
    direct key_result_id (pre-Initiative layer) also get objective_id filled.
    """
    initiative_ids = {t["initiative_id"] for t in tasks if t.get("initiative_id")}
    legacy_kr_ids = {
        t["key_result_id"] for t in tasks
        if t.get("key_result_id") and not t.get("initiative_id")
    }

    initiative_rows = []
    if initiative_ids:
        initiative_rows = get(
            "initiatives",
            params={
                "user_id": f"eq.{user_id}",
                "id": f"in.({','.join(str(i) for i in initiative_ids)})",
                "is_deleted": "eq.false",
                "select": "id,key_result_id",
                "limit": 500,
            },
        ) or []
    initiative_to_kr = {r["id"]: r.get("key_result_id") for r in initiative_rows}

    kr_ids_needed = set(initiative_to_kr.values()) | legacy_kr_ids
    kr_ids_needed = {k for k in kr_ids_needed if k}

    kr_to_objective = {}
    if kr_ids_needed:
        kr_rows = get(
            "key_results",
            params={
                "user_id": f"eq.{user_id}",
                "id": f"in.({','.join(str(i) for i in kr_ids_needed)})",
                "is_deleted": "eq.false",
                "select": "id,objective_id",
                "limit": 500,
            },
        ) or []
        kr_to_objective = {r["id"]: r.get("objective_id") for r in kr_rows}

    for t in tasks:
        init_id = t.get("initiative_id")
        kr_id = initiative_to_kr.get(init_id) if init_id else t.get("key_result_id")
        obj_id = kr_to_objective.get(kr_id) if kr_id else None
        t["key_result_id"] = kr_id
        t["objective_id"] = obj_id


def _build_task_dict(t, project, today):
    """Build a normalised task dict for template rendering."""
    due = t.get("due_date")

    # Pre-format due label server-side to avoid client-side flash
    due_label = None
    if due:
        try:
            due_d = date.fromisoformat(due)
            diff = (due_d - today).days
            if diff == 0:
                due_label = "⏰ Today"
            elif diff == 1:
                due_label = "⏰ Tomorrow"
            elif diff < 0:
                due_label = f"⚠ {abs(diff)}d overdue"
            else:
                due_label = f"📅 In {diff}d"
        except ValueError:
            due_label = f"📅 {due}"

    return {
        "task_id": t["task_id"],
        "task_text": t["task_text"],
        "status": t.get("status"),
        "done": t.get("status") == "done",
        "start_date": t.get("start_date"),
        "duration_days": t.get("duration_days") or 0,
        "due_date": due,
        "due_label": due_label,
        "due_time": t.get("due_time"),
        "delegated_to": t.get("delegated_to"),
        "project_name": project["name"],
        "priority": t.get("priority", "medium"),
        "priority_rank": PRIORITY_MAP.get(t.get("priority"), 2),
        "is_pinned": t.get("is_pinned", False),
        "planned_hours": t.get("planned_hours") or 0,
        "actual_hours": t.get("actual_hours") or 0,
        "is_recurring": t.get("is_recurring", False),
        "recurrence_type": t.get("recurrence_type", "none"),
        "recurrence_days": t.get("recurrence_days"),
        "recurrence_interval": t.get("recurrence_interval"),
        "recurrence_end": t.get("recurrence_end"),
        "auto_advance": t.get("auto_advance", True),
        "recurrence_badge": build_recurrence_badge(t),
        "occurrence_date": due or today.isoformat(),
        "eisenhower_sent": False,
        "missed_eisenhower": False,
        "eisenhower_plan_date": None,
        "key_result_id": t.get("key_result_id"),
        "initiative_id": t.get("initiative_id"),
    }


@projects_bp.route("/projects/<project_id>/tasks/add-ajax", methods=["POST"])
@login_required
def add_project_task_ajax(project_id):
    """Async task add — returns rendered card HTML + task_id."""
    data = request.get_json() or {}
    text = (data.get("task_text") or "").strip()
    if not text:
        return jsonify({"error": "Task text required"}), 400

    priority = data.get("priority", "medium")
    start_date = data.get("start_date") or date.today().isoformat()

    max_order = get_max_order_index(project_id)
    result = post("project_tasks", {
        "project_id": project_id,
        "user_id": session["user_id"],
        "task_text": text,
        "status": "open",
        "priority": priority,
        "priority_rank": PRIORITY_MAP.get(priority, 2),
        "start_date": start_date,
        "order_index": (max_order or 0) + 1,
    })

    if not result:
        return jsonify({"error": "Insert failed"}), 500

    raw = result[0]
    today = date.today()

    # Minimal project stub for _build_task_dict
    project_stub = {"name": ""}
    task = _build_task_dict(raw, project_stub, today)

    html = render_template(
        "_project_task_card.html",
        task=task,
        today=today.isoformat(),
    )
    return jsonify({"html": html, "task_id": raw["task_id"]})


def compute_due_date(start_date, duration_days):
    return start_date + timedelta(days=duration_days)


def get_max_order_index(project_id):
    rows = get(
        "project_tasks",
        params={
            "project_id": f"eq.{project_id}",
            "select": "order_index",
            "order": "order_index.desc",
            "limit": 1
        }
    )
    return rows[0]["order_index"] if rows else None

def build_recurrence_badge(t):
    if not t.get("is_recurring"):
        return None

    rtype = t.get("recurrence_type")

    if rtype == "daily":
        return "🔁 Daily"

    if rtype == "weekly":
        return "🔁 Weekly"

    if rtype == "monthly":
        return "🔁 Monthly"

    return "🔁"
def insert_many(table, rows, prefer="return=representation"):
    """
    Insert multiple rows into a Supabase table.
    rows: list[dict]
    """
    return post(table, rows, prefer=prefer)





@projects_bp.route("/projects/list")
@login_required
def list_projects():

    projects = get(
        "projects",
        params={
            "user_id": f"eq.{session['user_id']}",
            "order": "name.asc"
        }
    )

    return jsonify(projects or [])
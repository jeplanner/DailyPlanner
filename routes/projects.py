
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

    projects = get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "is_archived": "eq.false",
            "order": "created_at.asc",
        },
    ) or []

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
    # Fetch tasks (no filtering in SQL)
    # ---------------------------------
    raw_tasks = get(
        "project_tasks",
        params={
            "project_id": f"eq.{project_id}",
            "is_eliminated": "eq.false",   # ✅ ADD THIS
            "order": order,
        },
    ) or []

    today = date.today()

    tasks = []
    for t in raw_tasks:
        status = t.get("status")
        due    = t.get("due_date")

        # ❌ Hide completed
        if hide_completed and status == "done":
            continue

        # ❌ Overdue only
        if overdue_only:
            if not due:
                continue
            due_date = date.fromisoformat(due)
            if due_date >= today or status == "done":
                continue

        tasks.append({
            "task_id": t["task_id"],
            "task_text": t["task_text"],
            "status": status,
            "done": status == "done",
            "start_date": t.get("start_date"),
            "duration_days": t.get("duration_days"),
            "due_date": due,
            "due_time": t.get("due_time"),
            "delegated_to": t.get("delegated_to"),
            "elimination_reason": t.get("elimination_reason"),
            "project_name": project["name"],
            "priority": t.get("priority", "medium"),
            "urgency": None,
            "priority_rank": PRIORITY_MAP.get(t.get("priority"), 2),
            "is_pinned": t.get("is_pinned", False),
            "planned_hours": t.get("planned_hours", 0),
            "actual_hours": t.get("actual_hours", 0),
            "is_recurring": t.get("is_recurring", False),
            "recurrence_type": t.get("recurrence_type", "none"),
            "recurrence_days": t.get("recurrence_days"),
            "recurrence_interval": t.get("recurrence_interval"),
            "recurrence_end": t.get("recurrence_end"),
            "auto_advance": t.get("auto_advance", True),
            "recurrence_badge": build_recurrence_badge(t),
            # used by task card for date-aware actions (e.g. recurring completion)
            "occurrence_date": due or date.today().isoformat(),
            # Eisenhower fields (safe defaults — full feature requires eisenhower query)
            "eisenhower_sent": False,
            "missed_eisenhower": False,
            "eisenhower_plan_date": None,
        })

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
    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={"status": status}
    )

    return jsonify({"status": "ok"})

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
        params={"project_id": f"eq.{project_id}"}
    )

    gantt_tasks = build_gantt_tasks(tasks)

    return render_template(
        "project_gantt.html",
        project_id=project_id,
        gantt_tasks=json.dumps(gantt_tasks)
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

    rows = []
    for idx,text in enumerate(tasks):
        if not text.strip():
            continue

        rows.append({
            "project_id": project_id,          # ✅ guaranteed non-empty
            "task_text": text.strip(),
            "start_date": today,
            "priority": "medium",
            "priority_rank": PRIORITY_MAP["medium"],
            "order_index": idx,          # ✅ THIS LINE
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

    tasks = get(
        "project_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "is_eliminated": "eq.false",
            "status": "neq.done",
            "or": f"(due_date.is.null,due_date.eq.{date},due_date.lt.{date})",
            "select": """
                task_id,
                task_text,
                priority,
                project_id,
                start_time,
                due_date,
                projects(name)
            """
        }
    )

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

@projects_bp.route("/subtask/add", methods=["POST"])
@login_required
def add_subtask():
    data = request.get_json()

    post(
        "project_subtasks",
        {
            "project_id": data["project_id"],
            "parent_task_id": data["task_id"],
            "title": data["title"],
        },
    )
    return ("", 204)

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
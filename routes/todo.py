import calendar
from collections import OrderedDict
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, render_template_string, request, session, url_for

from auth import login_required
from config import IST
from services.eisenhower_service import autosave_task, copy_open_tasks_from_previous_day, enable_travel_mode
from services.task_service import update_task_occurrence
from supabase_client import get, post, update
from templates.todo import TODO_TEMPLATE
import logging
logger = logging.getLogger(__name__)

todo_bp = Blueprint("todo", __name__)

# ==========================================================
# ROUTES – EISENHOWER MATRIX
# ==========================================================
@todo_bp.route("/todo", methods=["GET"])
@login_required
def todo():
    expire_old_eisenhower_tasks(session["user_id"])

    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    day = int(request.args.get("day", date.today().day))

    plan_date = date(year, month, day)

    user_id = session["user_id"]

    # 1️⃣ Fetch standalone Eisenhower tasks
    raw_tasks = get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date.isoformat()}",
            "is_deleted": "eq.false"
        }
    )

    # 2️⃣ Fetch projects for labeling
    projects = get("projects", params={"user_id": f"eq.{user_id}"})
    project_map = {p["project_id"]: p["name"] for p in projects}

    # 3️⃣ Normalize standalone tasks
    tasks = []
    for t in raw_tasks:
        tasks.append({
            "id": t["id"],
            "task_text": t["task_text"],
            "quadrant": t["quadrant"],
            "is_done": t.get("is_done", False),
            "project_id": t.get("project_id"),
            "project_name": project_map.get(t.get("project_id")),
            "source_task_id": t.get("source_task_id"),
            "source": "matrix",
        })

    # 4️⃣ Fetch planner events with quadrant set for this date
    events_with_q = get("daily_events", params={
        "user_id": f"eq.{user_id}",
        "plan_date": f"eq.{plan_date.isoformat()}",
        "is_deleted": "eq.false",
        "quadrant": "neq.",
        "select": "id,title,quadrant,status,start_time,end_time",
    }) or []

    for e in events_with_q:
        if e.get("quadrant"):
            tasks.append({
                "id": f"ev-{e['id']}",
                "task_text": f"📅 {e.get('start_time','')[:5]} {e['title']}",
                "quadrant": e["quadrant"],
                "is_done": e.get("status") == "done",
                "project_id": None,
                "project_name": None,
                "source_task_id": None,
                "source": "event",
            })

    # 5️⃣ Fetch project tasks with quadrant set, due today or earlier
    proj_tasks_q = get("project_tasks", params={
        "user_id": f"eq.{user_id}",
        "is_eliminated": "eq.false",
        "quadrant": "neq.",
        "or": f"(due_date.is.null,due_date.lte.{plan_date.isoformat()})",
        "select": "task_id,task_text,quadrant,status,priority,project_id",
        "limit": 100,
    }) or []

    for t in proj_tasks_q:
        if t.get("quadrant"):
            tasks.append({
                "id": f"pt-{t['task_id']}",
                "task_text": f"📋 {t['task_text']}",
                "quadrant": t["quadrant"],
                "is_done": t.get("status") == "done",
                "project_id": t.get("project_id"),
                "project_name": project_map.get(t.get("project_id")),
                "source_task_id": None,
                "source": "project",
            })

    # 4️⃣ Build Eisenhower view (NO due-date logic here)
    todo = build_eisenhower_view(tasks, plan_date)
    quadrant_counts = compute_quadrant_counts(todo)

    # 5️⃣ Render
    days = calendar.monthrange(year, month)[1]

    from datetime import datetime as dt
    from config import IST
    today = dt.now(IST).date().isoformat()

    return render_template(
        "todo.html",
        todo=todo,
        plan_date=plan_date,
        year=year,
        month=month,
        today=today,
        quadrant_counts=quadrant_counts,
    )


@todo_bp.route("/todo/toggle-done", methods=["POST"])
@login_required
def toggle_todo_done():
    data = request.get_json()

    task_id = data.get("id")
    is_done = bool(data.get("is_done"))

    if not task_id:
        return jsonify({"error": "Missing task id"}), 400

    status = "done" if is_done else "open"

    # 1️⃣ Fetch source_task_id BEFORE update (avoids extra fetch after)
    source_task_id = None
    if is_done:
        rows = get(
            "todo_matrix",
            params={"id": f"eq.{task_id}", "select": "source_task_id"},
        )
        if rows:
            source_task_id = rows[0].get("source_task_id")

    # 2️⃣ Update Eisenhower task
    update(
        "todo_matrix",
        params={"id": f"eq.{task_id}"},
        json={"is_done": is_done, "status": status},
    )

    # 3️⃣ Sync back to project task (using pre-fetched source_task_id)
    if source_task_id:
        update(
            "project_tasks",
            params={"task_id": f"eq.{source_task_id}"},
            json={"status": "done"},
        )

    return jsonify({"status": "ok"})


@todo_bp.route("/todo/copy-prev", methods=["POST"])
@login_required
def copy_prev_todo():
    today = datetime.now(IST).date()

    year = int(request.form.get("year", today.year))
    month = int(request.form.get("month", today.month))
    day = int(request.form.get("day", today.day))
    plan_date = date(year, month, day)

    copied = copy_open_tasks_from_previous_day(plan_date)
    logger.info(f"Copied {copied} Eisenhower tasks from previous day")

    return redirect(url_for("todo.todo", year=plan_date.year, month=plan_date.month, day=plan_date.day, copied=1))
@todo_bp.route("/todo/move", methods=["POST"])
@login_required
def move_eisenhower_task():
    data = request.get_json()
    task_id = data["id"]
    quadrant = data["quadrant"]
    

    update(
        "todo_matrix",
        params={"id": f"eq.{task_id}"},
        json={"quadrant": quadrant}
    )

    return jsonify({"status": "ok"})


@todo_bp.route("/todo/travel-mode", methods=["POST"])
@login_required
def travel_mode():
    year = int(request.form["year"])
    month = int(request.form["month"])
    day = int(request.form["day"])
    plan_date = date(year, month, day)

    added = enable_travel_mode(plan_date)
    logger.info(f"Travel Mode enabled: {added} tasks added")

    return redirect(url_for("todo.todo", year=plan_date.year, month=plan_date.month, day=plan_date.day, travel=1))

@todo_bp.route("/todo/autosave", methods=["POST"])
@login_required
def todo_autosave():
    data = request.get_json(force=True)
    logger.info("AUTOSAVE DATA: %s", data)

    # 🛑 HARD GUARD — ignore anything not from Eisenhower
    if "id" not in data or "plan_date" not in data or "quadrant" not in data:
        return jsonify({"ignored": True})

    task_id = data["id"]

    # 🔹 FULL EISENHOWER AUTOSAVE
    result = autosave_task(
        plan_date=data["plan_date"],
        task_id=task_id,
        quadrant=data["quadrant"],
        text=data.get("task_text"),
        is_done=data.get("is_done", False),
    )

    # 🔒 Preserve project_id if present
    if "project_id" in data:
        update(
            "todo_matrix",
            params={"id": f"eq.{task_id}"},
            json={"project_id": data["project_id"]},
        )

    # 🔁 Sync completion back to project task (if linked)
    if "is_done" in data:
        row = get(
            "todo_matrix",
            params={"id": f"eq.{task_id}"},
            single=True
        )

        if row and row.get("source_task_id"):
            update(
                "project_tasks",
                params={"task_id": f"eq.{row['source_task_id']}"},
                json={
                    "status": "done" if data["is_done"] else "open"
                }
            )

    return jsonify(result)

@todo_bp.route("/todo/set-project", methods=["POST"])
@login_required
def todo_set_project():
    data = request.get_json(force=True)

    task_id = data.get("id")
    project_id = data.get("project_id")

    if not task_id:
        return jsonify({"error": "Missing task id"}), 400

    update(
        "todo_matrix",
        params={"id": f"eq.{task_id}"},
        json={"project_id": project_id},
    )

    return jsonify({"status": "ok"})
# ==========================================================
# ROUTES – DAILY PLANNER
# ==========================================================


def empty_quadrant():
    return {"tasks": []}



def build_eisenhower_view(tasks, plan_date):
    """
    Build Eisenhower matrix ONLY from todo_matrix tasks.
    No inference. No due-date logic. No urgency computation.
    """

    todo = {
        "do": empty_quadrant(),
        "schedule": empty_quadrant(),
        "delegate": empty_quadrant(),
        "eliminate": empty_quadrant(),
    }

    for t in tasks:
        quadrant = t.get("quadrant")
        if quadrant not in todo:
            continue  # safety guard

        task = {
            "id": t["id"],
            "task_text": t["task_text"],
            "is_done": t.get("is_done", False),
            "project_id": t.get("project_id"),
            "project_name": t.get("project_name"),
            "source_task_id": t.get("source_task_id"),
        }

        # Each quadrant has a single bucket
        todo[quadrant]["tasks"].append(task)

    return todo

def parse_date(d):
    if isinstance(d, str):
        return datetime.fromisoformat(d).date()
    return d

def compute_quadrant_counts(todo):
    counts = {}

    for q, data in todo.items():
        tasks = data["tasks"]
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("is_done"))

        counts[q] = {
            "total": total,
            "done": done
        }

    return counts



def compute_urgency(due_date, due_time):
    # 🚫 Missing date or time → no urgency
    if not due_date or not due_time:
        return None

    # Normalize due_time (Supabase may return HH:MM or HH:MM:SS)
    if isinstance(due_time, str):
        parsed = None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                parsed = datetime.strptime(due_time, fmt).time()
                break
            except ValueError:
                continue
        due_time = parsed

    if not due_time:
        return None

    now = datetime.now()
    due_dt = datetime.combine(due_date, due_time)

    if due_dt < now:
        return "overdue"    # 🔴
    elif due_dt <= now + timedelta(hours=2):
        return "soon"       # 🟠
    return None


def normalize_task(t, project_name=None):
    return {
        "task_id": t["task_id"],
        "text": t.get("task_text") or t.get("text"),
        "status": t.get("status"),
        "done": t.get("status") == "done",
        "due_date": parse_date(t.get("due_date")),
        "due_time": t.get("due_time"),
        "delegated_to": t.get("delegated_to"),
        "elimination_reason": t.get("elimination_reason"),
        "project_id": t.get("project_id"),
        "project_name": project_name,
        "recurring": bool(t.get("recurrence")),
        "recurrence": t.get("recurrence"),
    }
def expire_old_eisenhower_tasks(user_id):
    today = date.today().isoformat()

    rows = get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "is_done": "eq.false",
            "is_deleted": "eq.false",
            "plan_date": f"lt.{today}",
            "select": "id,source_task_id",
            "limit": 500,
        }
    )

    if not rows:
        return

    # Batch update: mark all expired tasks as deleted in ONE call
    expired_ids = ",".join(str(r["id"]) for r in rows)
    update(
        "todo_matrix",
        params={"id": f"in.({expired_ids})"},
        json={"is_deleted": True}
    )

    # Batch restore: reopen linked project tasks in ONE call
    source_ids = [str(r["source_task_id"]) for r in rows if r.get("source_task_id")]
    if source_ids:
        update(
            "project_tasks",
            params={"task_id": f"in.({','.join(source_ids)})"},
            json={"status": "open"}
        )


@todo_bp.route("/set_recurrence", methods=["POST"])
@login_required
def set_recurrence():
    data = request.get_json()
    task_id = data["task_id"]
    recurrence = data.get("recurrence")

    # Safety: block unsaved tasks
    if task_id.startswith("new_"):
        return ("", 204)

    # Load the task instance
    task = get("todo_matrix", params={"id": f"eq.{task_id}"})[0]

    # ----------------------------
    # FIX 3: prevent duplicate rules
    # ----------------------------
    existing = get(
        "recurring_tasks",
        params={
            "task_text": f"eq.{task['task_text']}",
            "quadrant": f"eq.{task['quadrant']}",
            "start_date": f"eq.{task['plan_date']}",
            "is_active": "eq.true",
        },
    )

    if existing:
        # Rule already exists → do nothing (idempotent)
        return ("", 204)

    # ----------------------------
    # Create recurring rule
    # ----------------------------
    rule=post(
        "recurring_tasks",
        {
            "quadrant": task["quadrant"],
            "task_text": task["task_text"],
            "recurrence": recurrence,
            "start_date": task["plan_date"],
            "is_active": True,
            "category": task.get("category") or "General",
            "subcategory": task.get("subcategory") or "General",
            "day_of_month": (
            date.fromisoformat(task["plan_date"]).day
            if recurrence == "monthly"
            else None
            ),
            "days_of_week": (
                [date.fromisoformat(task["plan_date"]).weekday()]
                if recurrence == "weekly"
                else None
            ),
         },
    )
    update(
    "todo_matrix",
    params={"id": f"eq.{task_id}"},
    json={"recurring_id": rule[0]["id"]},
    )

    return ("", 204)

@todo_bp.route("/delete_recurring", methods=["POST"])
@login_required
def delete_recurring():
    data = request.get_json()
    task_id = data["task_id"]

    # Load the task instance for TODAY
    task = get(
        "todo_matrix",
        params={"id": f"eq.{task_id}"},
    )[0]

    recurring_id = task.get("recurring_id")
    if not recurring_id:
        return ("", 204)

    # Stop recurrence from yesterday onwards
    end_date = date.fromisoformat(task["plan_date"]) - timedelta(days=1)

    update(
        "recurring_tasks",
        params={"id": f"eq.{recurring_id}"},
        json={"end_date": str(end_date)},
    )

    # Also remove TODAY's instance
    update("todo_matrix", params={"id": f"eq.{task_id}"}, json={"is_deleted": True})

    return ("", 204)



def group_tasks_smart(tasks):
    today = date.today()
    tomorrow = today + timedelta(days=1)            

    # Week ends on Sunday
    end_of_week = today + timedelta(days=(6 - today.weekday()))

    # End of month
    next_month = today.replace(day=28) + timedelta(days=4)
    end_of_month = next_month.replace(day=1) - timedelta(days=1)

    groups = OrderedDict({
        "Today": [],
        "Tomorrow": [],
        "This Week": [],
        "This Month": [],
        "Later": []
    })

    for t in tasks:
        d = t.get("start_date") or t.get("due_date")

        if not d:
            groups["Later"].append(t)
            continue

        if isinstance(d, str):
            d = date.fromisoformat(d)

        if d == today:
            groups["Today"].append(t)
        elif d == tomorrow:
            groups["Tomorrow"].append(t)
        elif tomorrow < d <= end_of_week:
            groups["This Week"].append(t)
        elif d <= end_of_month:
            groups["This Month"].append(t)
        else:
            groups["Later"].append(t)

    # Optional: sort inside each group
    for key in groups:
        groups[key].sort(key=_sort_key)

    return groups

@todo_bp.route("/tasks/occurrence/update", methods=["POST"])
@login_required
def update_task_occurrence_route():
    data = request.get_json()

    update_task_occurrence(
        user_id=session["user_id"],
        task_id=data["task_id"],
        task_date=data["date"],
        title=data.get("title"),
        status=data.get("status")
    )

    return "", 204

def _sort_key(task):
    """
    Normalizes start_date / due_date for safe sorting.
    Handles:
    - datetime.date
    - ISO date strings
    - None
    """
    d = task.get("start_date") or task.get("due_date")

    if not d:
        return date.max

    if isinstance(d, str):
        return date.fromisoformat(d)

    return d
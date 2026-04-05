import calendar
from collections import OrderedDict
from datetime import date, datetime, timedelta

# Unified status set (matches project_tasks status dropdowns)
_OPEN_STATUSES = {"open", "in_progress"}
_RESOLVED_STATUSES = {"done", "not_required", "skipped"}
_ALL_STATUSES = _OPEN_STATUSES | _RESOLVED_STATUSES

# Priority vocabulary shared with project_tasks
_VALID_PRIORITIES = {"low", "medium", "high"}

# Schema note — run once in Supabase if not already present:
#   alter table todo_matrix add column if not exists priority text default 'medium';

from flask import Blueprint, jsonify, redirect, render_template, render_template_string, request, session, url_for

from auth import login_required
from config import IST
from services.eisenhower_service import (
    autosave_task,
    copy_open_tasks_from_previous_day,
    enable_travel_mode,
    list_travel_categories,
    list_travel_tasks,
)
from supabase_client import delete as sb_delete
from services.recurring_service import materialize_recurring_tasks
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

    # 0️⃣ Materialize recurring tasks for this date (idempotent — safe to call always)
    try:
        materialize_recurring_tasks(plan_date, user_id)
    except Exception as e:
        logger.warning("Failed to materialize recurring tasks: %s", e)

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

    # 2b️⃣ Build recurrence map for badge display
    recurring_ids = {t.get("recurring_id") for t in raw_tasks if t.get("recurring_id")}
    recurrence_map = {}
    if recurring_ids:
        rules = get(
            "recurring_tasks",
            params={
                "id": f"in.({','.join(str(r) for r in recurring_ids)})",
                "select": "id,recurrence",
            },
        ) or []
        recurrence_map = {r["id"]: r.get("recurrence") for r in rules}

    # 3️⃣ Normalize standalone tasks
    tasks = []
    for t in raw_tasks:
        tasks.append({
            "id": t["id"],
            "task_text": t["task_text"],
            "quadrant": t["quadrant"],
            "is_done": t.get("is_done", False),
            "status": t.get("status") or ("done" if t.get("is_done") else "open"),
            "priority": (t.get("priority") or "medium"),
            "recurrence": recurrence_map.get(t.get("recurring_id")),
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
        "select": "id,title,quadrant,status,start_time,end_time,priority",
    }) or []

    for e in events_with_q:
        if e.get("quadrant"):
            tasks.append({
                "id": f"ev-{e['id']}",
                "task_text": f"📅 {e.get('start_time','')[:5]} {e['title']}",
                "quadrant": e["quadrant"],
                "is_done": e.get("status") == "done",
                "status": e.get("status") or "open",
                "priority": (e.get("priority") or "medium"),
                "recurrence": None,
                "project_id": None,
                "project_name": None,
                "source_task_id": None,
                "source": "event",
            })

    # 5️⃣ Fetch project tasks with quadrant set
    # Include: non-recurring tasks due on/before selected date, OR any recurring task
    proj_tasks_q = get("project_tasks", params={
        "user_id": f"eq.{user_id}",
        "is_eliminated": "eq.false",
        "quadrant": "neq.",
        "select": "task_id,task_text,quadrant,status,priority,project_id,"
                  "due_date,is_recurring,recurrence_type,recurrence_days",
        "limit": 200,
    }) or []

    target_weekday = plan_date.weekday()

    for t in proj_tasks_q:
        if not t.get("quadrant"):
            continue

        # Skip completed tasks (unless we want to show them)
        if t.get("status") == "done":
            continue

        is_recurring = t.get("is_recurring")
        due_date_str = t.get("due_date")

        # Determine if this task applies to the selected date
        applies = False

        if is_recurring:
            # Recurring task — check if it matches the selected date
            rec_type = t.get("recurrence_type")
            if rec_type == "daily":
                applies = True
            elif rec_type == "weekly":
                days = t.get("recurrence_days") or []
                if target_weekday in days:
                    applies = True
            elif rec_type == "monthly":
                # Show on same day of month as due_date if set, else every day
                if due_date_str:
                    try:
                        dd = date.fromisoformat(due_date_str)
                        if plan_date.day == dd.day:
                            applies = True
                    except (ValueError, TypeError):
                        pass
            else:
                applies = True  # Unknown recurrence — show it
        else:
            # Non-recurring — show if due on or before selected date
            if not due_date_str:
                # No due date → show today only
                if plan_date == date.today():
                    applies = True
            else:
                try:
                    dd = date.fromisoformat(due_date_str)
                    if dd <= plan_date:
                        applies = True
                except (ValueError, TypeError):
                    pass

        if not applies:
            continue

        recur_badge = ""
        if is_recurring:
            icons = {"daily": "🔁", "weekly": "🔁", "monthly": "🔁"}
            recur_badge = icons.get(t.get("recurrence_type"), "🔁") + " "

        tasks.append({
            "id": f"pt-{t['task_id']}",
            "task_text": f"📋 {t['task_text']}",
            "quadrant": t["quadrant"],
            "is_done": t.get("status") == "done",
            "status": t.get("status") or "open",
            "priority": (t.get("priority") or "medium"),
            "recurrence": t.get("recurrence_type") if is_recurring else None,
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
        projects=projects,
    )


@todo_bp.route("/todo/toggle-done", methods=["POST"])
@login_required
def toggle_todo_done():
    data = request.get_json()

    task_id = data.get("id")

    if not task_id:
        return jsonify({"error": "Missing task id"}), 400

    # Unified status: open | in_progress | done | not_required | skipped
    req_status = (data.get("status") or "").strip().lower()
    if req_status in _ALL_STATUSES:
        status = req_status
    else:
        # Legacy checkbox path: is_done flag decides
        status = "done" if bool(data.get("is_done")) else "open"

    is_done = status in _RESOLVED_STATUSES

    # 1️⃣ Fetch task (need source_task_id + recurring_id before update)
    rows = get(
        "todo_matrix",
        params={
            "id": f"eq.{task_id}",
            "select": "source_task_id,recurring_id,plan_date,quadrant,task_text,category,subcategory,project_id",
        },
    )
    task_row = rows[0] if rows else None

    # 2️⃣ Update Eisenhower task
    update(
        "todo_matrix",
        params={"id": f"eq.{task_id}"},
        json={"is_done": is_done, "status": status},
    )

    # 3️⃣ Sync back to project task (non-recurring only)
    if is_done and task_row:
        source_task_id = task_row.get("source_task_id")
        recurring_id = task_row.get("recurring_id")
        if source_task_id and not recurring_id:
            update(
                "project_tasks",
                params={"task_id": f"eq.{source_task_id}"},
                json={"status": "done"},
            )

    # 4️⃣ Recurring: pre-create the next occurrence so it appears on the next matching date
    next_occurrence_iso = None
    if is_done and task_row and task_row.get("recurring_id"):
        try:
            next_occurrence_iso = _create_next_recurring_instance(
                user_id=session["user_id"],
                recurring_id=task_row["recurring_id"],
                current_plan_date=date.fromisoformat(str(task_row["plan_date"])),
                fallback_quadrant=task_row.get("quadrant"),
                fallback_text=task_row.get("task_text"),
                fallback_category=task_row.get("category"),
                fallback_subcategory=task_row.get("subcategory"),
                fallback_project_id=task_row.get("project_id"),
            )
        except Exception as e:
            logger.warning("Failed to pre-create next recurring occurrence: %s", e)

    return jsonify({"status": "ok", "next_occurrence": next_occurrence_iso})


def _next_recurrence_date(rule, from_date):
    """Return the first date strictly after `from_date` that matches the rule, or None."""
    rtype = rule.get("recurrence")
    end = rule.get("end_date")
    end_date = date.fromisoformat(end) if end else None

    # Daily: next day
    if rtype == "daily":
        nxt = from_date + timedelta(days=1)
        return nxt if (not end_date or nxt <= end_date) else None

    # Weekly: scan next 7 days for matching weekday
    if rtype == "weekly":
        days = rule.get("days_of_week") or []
        if not days:
            return None
        for i in range(1, 8):
            nxt = from_date + timedelta(days=i)
            if nxt.weekday() in days:
                return nxt if (not end_date or nxt <= end_date) else None
        return None

    # Monthly: same day_of_month next month (clamped to last day of that month)
    if rtype == "monthly":
        dom = rule.get("day_of_month") or from_date.day
        year = from_date.year
        month = from_date.month + 1
        if month > 12:
            month = 1
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        nxt = date(year, month, min(dom, last_day))
        return nxt if (not end_date or nxt <= end_date) else None

    return None


def _create_next_recurring_instance(user_id, recurring_id, current_plan_date,
                                    fallback_quadrant, fallback_text,
                                    fallback_category, fallback_subcategory,
                                    fallback_project_id):
    """
    Look up the recurring rule and insert a todo_matrix row for the next
    matching date. Idempotent — skips if a row already exists for that rule+date.
    Returns the ISO date of the next occurrence (or None).
    """
    rule_rows = get(
        "recurring_tasks",
        params={"id": f"eq.{recurring_id}", "is_active": "eq.true"},
    ) or []
    if not rule_rows:
        return None
    rule = rule_rows[0]

    next_date = _next_recurrence_date(rule, current_plan_date)
    if not next_date:
        return None

    # Idempotency guard
    existing = get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "recurring_id": f"eq.{recurring_id}",
            "plan_date": f"eq.{next_date.isoformat()}",
            "is_deleted": "eq.false",
            "select": "id",
            "limit": 1,
        },
    ) or []
    if existing:
        return next_date.isoformat()

    payload = {
        "user_id": user_id,
        "plan_date": next_date.isoformat(),
        "task_date": next_date.isoformat(),
        "quadrant": rule.get("quadrant") or fallback_quadrant,
        "task_text": rule.get("task_text") or fallback_text,
        "category": rule.get("category") or fallback_category or "General",
        "subcategory": rule.get("subcategory") or fallback_subcategory or "General",
        "is_done": False,
        "is_deleted": False,
        "status": "open",
        "recurring_id": recurring_id,
    }
    if fallback_project_id:
        payload["project_id"] = fallback_project_id

    try:
        post("todo_matrix", payload)
    except Exception as e:
        logger.warning("Insert next recurring instance failed: %s", e)
        return None

    return next_date.isoformat()


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

    # Optional travel template category (e.g. "Domestic", "International").
    # When omitted, ALL of the user's travel_tasks are applied.
    category = (request.form.get("category") or "").strip() or None

    added = enable_travel_mode(plan_date, category=category)
    logger.info(f"Travel Mode enabled: {added} tasks added (category={category})")

    return redirect(url_for(
        "todo.todo",
        year=plan_date.year, month=plan_date.month, day=plan_date.day,
        travel=1,
    ))


# ==========================================================
# ROUTES – TRAVEL TEMPLATE CRUD
# ==========================================================

@todo_bp.route("/travel/categories", methods=["GET"])
@login_required
def travel_categories():
    return jsonify({"categories": list_travel_categories(session["user_id"])})


@todo_bp.route("/travel/tasks", methods=["GET"])
@login_required
def travel_tasks_list():
    category = (request.args.get("category") or "").strip() or None
    return jsonify({"tasks": list_travel_tasks(session["user_id"], category=category)})


@todo_bp.route("/travel/tasks", methods=["POST"])
@login_required
def travel_tasks_create():
    data = request.get_json(force=True) or {}
    text = (data.get("task_text") or "").strip()
    if not text:
        return jsonify({"error": "task_text required"}), 400

    category = (data.get("category") or "Default").strip() or "Default"
    quadrant = (data.get("quadrant") or "do").strip().lower()
    if quadrant not in ("do", "schedule", "delegate", "eliminate"):
        quadrant = "do"
    subcategory = (data.get("subcategory") or "General").strip() or "General"

    # Place at end of the category's order
    existing = get(
        "travel_tasks",
        params={
            "user_id": f"eq.{session['user_id']}",
            "category": f"eq.{category}",
            "select": "order_index",
            "order": "order_index.desc",
            "limit": 1,
        },
    ) or []
    next_order = (existing[0]["order_index"] + 1) if existing else 0

    rows = post("travel_tasks", {
        "user_id": session["user_id"],
        "category": category,
        "quadrant": quadrant,
        "task_text": text,
        "subcategory": subcategory,
        "order_index": next_order,
    })
    return jsonify({"status": "ok", "task": rows[0] if rows else None})


@todo_bp.route("/travel/tasks/<int:task_id>", methods=["PATCH"])
@login_required
def travel_tasks_update(task_id):
    data = request.get_json(force=True) or {}
    allowed = {"category", "quadrant", "task_text", "subcategory", "order_index"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "no valid fields"}), 400

    if "quadrant" in patch:
        q = (patch["quadrant"] or "").strip().lower()
        if q not in ("do", "schedule", "delegate", "eliminate"):
            return jsonify({"error": "invalid quadrant"}), 400
        patch["quadrant"] = q
    if "task_text" in patch:
        patch["task_text"] = (patch["task_text"] or "").strip()
        if not patch["task_text"]:
            return jsonify({"error": "task_text required"}), 400

    update(
        "travel_tasks",
        params={
            "id": f"eq.{task_id}",
            "user_id": f"eq.{session['user_id']}",
        },
        json=patch,
    )
    return jsonify({"status": "ok"})


@todo_bp.route("/travel/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def travel_tasks_delete(task_id):
    sb_delete(
        "travel_tasks",
        params={
            "id": f"eq.{task_id}",
            "user_id": f"eq.{session['user_id']}",
        },
    )
    return jsonify({"status": "ok"})


@todo_bp.route("/travel/categories", methods=["POST"])
@login_required
def travel_categories_create():
    """
    Create a new travel category.

    Body accepts three shapes:
      1) { name, tasks: [{quadrant, task_text, subcategory}, ...] }
         Creates the category with exactly these rows (used by the Undo flow
         after a category delete).
      2) { name, source_category, template_ids: [int, ...] }
         Copies the specific IDs from any of the user's existing rows.
      3) { name, source_category }
         Copies every task from source_category (defaults to "Default").

    The new rows always get a fresh order_index starting at 0.
    """
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400

    user_id = session["user_id"]

    # Refuse if category already exists for this user
    existing_same = get(
        "travel_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "category": f"eq.{name}",
            "select": "id",
            "limit": 1,
        },
    ) or []
    if existing_same:
        return jsonify({"error": f'Category "{name}" already exists'}), 409

    # --- Shape 1: raw tasks (undo restore) ---
    raw_tasks = data.get("tasks")
    if isinstance(raw_tasks, list):
        payload = []
        for idx, t in enumerate(raw_tasks):
            text = (t.get("task_text") or "").strip()
            if not text:
                continue
            q = (t.get("quadrant") or "do").strip().lower()
            if q not in ("do", "schedule", "delegate", "eliminate"):
                q = "do"
            payload.append({
                "user_id": user_id,
                "category": name,
                "quadrant": q,
                "task_text": text,
                "subcategory": (t.get("subcategory") or "General").strip() or "General",
                "order_index": idx,
            })
        if not payload:
            return jsonify({"error": "tasks list is empty"}), 400
        post("travel_tasks", payload)
        return jsonify({"status": "ok", "copied": len(payload)})

    # --- Shapes 2 & 3: copy from an existing category ---
    # Ensure Default is seeded for first-run users
    from services.eisenhower_service import _seed_travel_tasks_if_empty
    _seed_travel_tasks_if_empty(user_id)

    template_ids = data.get("template_ids")
    source_category = (data.get("source_category") or "Default").strip() or "Default"

    if isinstance(template_ids, list) and template_ids:
        ids_csv = ",".join(str(int(i)) for i in template_ids if str(i).isdigit())
        if not ids_csv:
            return jsonify({"error": "template_ids must be integers"}), 400
        src = get(
            "travel_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "id": f"in.({ids_csv})",
                "select": "quadrant,task_text,subcategory,order_index",
                "order": "order_index.asc,id.asc",
                "limit": 5000,
            },
        ) or []
    else:
        src = get(
            "travel_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "category": f"eq.{source_category}",
                "select": "quadrant,task_text,subcategory,order_index",
                "order": "order_index.asc,id.asc",
                "limit": 5000,
            },
        ) or []

    if not src:
        # Create an empty category so the user can still add tasks to it
        post("travel_tasks", {
            "user_id": user_id,
            "category": name,
            "quadrant": "do",
            "task_text": "New travel task (edit me)",
            "subcategory": "General",
            "order_index": 0,
        })
        return jsonify({"status": "ok", "copied": 0, "placeholder": True})

    payload = []
    for idx, t in enumerate(src):
        payload.append({
            "user_id": user_id,
            "category": name,
            "quadrant": t.get("quadrant") or "do",
            "task_text": (t.get("task_text") or "").strip(),
            "subcategory": t.get("subcategory") or "General",
            "order_index": idx,
        })

    post("travel_tasks", payload)
    return jsonify({"status": "ok", "copied": len(payload)})


@todo_bp.route("/travel/categories/rename", methods=["POST"])
@login_required
def travel_categories_rename():
    data = request.get_json(force=True) or {}
    old = (data.get("old_name") or "").strip()
    new = (data.get("new_name") or "").strip()
    if not old or not new or old == new:
        return jsonify({"error": "old_name and new_name required and must differ"}), 400
    update(
        "travel_tasks",
        params={
            "user_id": f"eq.{session['user_id']}",
            "category": f"eq.{old}",
        },
        json={"category": new},
    )
    return jsonify({"status": "ok"})


@todo_bp.route("/travel/categories/delete", methods=["POST"])
@login_required
def travel_categories_delete():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    sb_delete(
        "travel_tasks",
        params={
            "user_id": f"eq.{session['user_id']}",
            "category": f"eq.{name}",
        },
    )
    return jsonify({"status": "ok"})

@todo_bp.route("/todo/autosave", methods=["POST"])
@login_required
def todo_autosave():
    data = request.get_json(force=True)
    logger.info("AUTOSAVE DATA: %s", data)

    if "plan_date" not in data or "quadrant" not in data:
        return jsonify({"ignored": True})

    # NEW task (no id) — insert directly
    if "id" not in data:
        user_id = session["user_id"]
        text = (data.get("task_text") or "").strip()
        if not text:
            return jsonify({"ignored": True})

        project_id = data.get("project_id") or None
        source_task_id = None

        quadrant = data["quadrant"]
        due_date = data.get("due_date") or data["plan_date"]
        task_time = data.get("task_time") or None
        delegated_to = data.get("delegated_to") or None
        priority = (data.get("priority") or "medium").strip().lower()
        if priority not in _VALID_PRIORITIES:
            priority = "medium"

        # Quadrant-specific date logic
        if quadrant == "eliminate":
            due_date = None

        # If project selected, also create a project_tasks row
        if project_id:
            try:
                _PRIO_RANK = {"high": 1, "medium": 2, "low": 3}
                pt_rows = post("project_tasks", {
                    "project_id": project_id,
                    "user_id": user_id,
                    "task_text": text,
                    "status": "open",
                    "priority": priority,
                    "priority_rank": _PRIO_RANK.get(priority, 2),
                    "start_date": data["plan_date"],
                    "due_date": due_date,
                    "due_time": task_time,
                    "delegated_to": delegated_to,
                    "quadrant": quadrant,
                    "order_index": 0,
                })
                if pt_rows:
                    source_task_id = pt_rows[0].get("task_id")
            except Exception as e:
                logger.warning("Failed to create project task from Eisenhower: %s", e)

        row_data = {
            "user_id": user_id,
            "plan_date": data["plan_date"],
            "quadrant": quadrant,
            "task_text": text,
            "is_done": bool(data.get("is_done", False)),
            "is_deleted": False,
            "task_date": due_date,
            "priority": priority,
        }
        if task_time:
            row_data["task_time"] = task_time
        if project_id:
            row_data["project_id"] = project_id
        if delegated_to:
            row_data["delegated_to"] = delegated_to
        if source_task_id:
            row_data["source_task_id"] = source_task_id

        # 🔁 Recurring rule — create if specified
        recurrence = (data.get("recurrence") or "").strip().lower() or None
        if recurrence in ("daily", "weekly", "monthly"):
            try:
                plan_d = date.fromisoformat(data["plan_date"])
                rule_payload = {
                    "user_id": user_id,
                    "quadrant": quadrant,
                    "task_text": text,
                    "recurrence": recurrence,
                    "start_date": data["plan_date"],
                    "is_active": True,
                    "category": "General",
                    "subcategory": "General",
                    "day_of_month": plan_d.day if recurrence == "monthly" else None,
                    "days_of_week": [plan_d.weekday()] if recurrence == "weekly" else None,
                }
                rule_rows = post("recurring_tasks", rule_payload)
                if rule_rows:
                    row_data["recurring_id"] = rule_rows[0]["id"]
            except Exception as e:
                logger.warning("Failed to create recurring rule from Eisenhower: %s", e)

        rows = post("todo_matrix", row_data)
        return jsonify({"status": "ok", "id": rows[0]["id"] if rows else None})

    task_id = data["id"]

    # 🔹 EXISTING task — full autosave
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
            "status": t.get("status"),
            "priority": t.get("priority") or "medium",
            "recurrence": t.get("recurrence"),
            "source": t.get("source", "matrix"),
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
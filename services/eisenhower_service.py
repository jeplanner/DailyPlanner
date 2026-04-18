import logging

from supabase_client import get, post, update  

from datetime import timedelta ,datetime,date
from config import TRAVEL_MODE_TASKS
from flask import session
from collections import defaultdict
logger = logging.getLogger(__name__)


# ==========================================================
# DATA ACCESS – EISENHOWER
# ==========================================================
def load_todo(plan_date):
    # ----------------------------
    # Load today's todo items
    # ----------------------------
    rows = (
        get(
            "todo_matrix",
            params={
                "plan_date": f"eq.{plan_date}",
                "is_deleted": "eq.false",
                "select": (
                    "id,quadrant,task_text,is_done,position,"
                    "task_date,task_time,recurring_id,"
                    "category,subcategory,project_id"
                ),
            },
        )
        or []
    )

    # ----------------------------
    # Load recurrence metadata
    # ----------------------------
    recurring_rows = (
        get(
            "recurring_tasks",
            params={"is_active": "eq.true", "select": "id,recurrence"},
        )
        or []
    )

    recurring_map = {r["id"]: r.get("recurrence") for r in recurring_rows}

    # ----------------------------
    # Build quadrant buckets
    # ----------------------------
    data = {"do": [], "schedule": [], "delegate": [], "eliminate": []}

    
    for r in rows:

        # --------------------------------------------------
        # 🔁 AUTO MOVE: Schedule → Do when date reaches today
        # --------------------------------------------------
        effective_quadrant = r["quadrant"]

        task_date = r.get("task_date")
        is_done = bool(r.get("is_done"))

        if not is_done and task_date:
            try:
                task_date_val = (
                    task_date if isinstance(task_date, date)
                    else date.fromisoformat(task_date)
                )
                if task_date_val > plan_date:
                    effective_quadrant = "schedule"
                else:
                    effective_quadrant = "do"
            except Exception:
                # fallback safely to stored quadrant
                pass

        data[effective_quadrant].append(
            {
                "id": r["id"],
                "text": r["task_text"],
                "done": is_done,
                "task_date": task_date,
                "task_time": r.get("task_time"),
                "recurring": bool(r.get("recurring_id")),
                "recurrence": recurring_map.get(r.get("recurring_id")),
                "category": r.get("category") or "General",
                "subcategory": r.get("subcategory") or "General",
                "project_id": r.get("project_id"),
                "subtasks": [],
            }
        )


    # ----------------------------
    # Sort within each quadrant
    # ----------------------------
    for q in data:
        data[q].sort(
        key=lambda t: (
                t["task_date"] is None,
                t["task_date"] or "",
                t["task_time"] is None,
                t["task_time"] or "",
            )
        )

    ### Category, Sub Category Changes start here ###

    grouped = {}

    for q in data:
        grouped[q] = {}
        for t in data[q]:
            cat = t["category"]
            sub = t["subcategory"]
            grouped[q].setdefault(cat, {}).setdefault(sub, []).append(t)
    # ----------------------------
    # Load subtasks for all tasks
    # ----------------------------
    task_ids = [
        t["id"]
        for q in grouped.values()
        for cat in q.values()
        for subs in cat.values()
        for t in subs
    ]

    if task_ids:
    # 🔑 Supabase requires quoted UUIDs for in.(...)
        quoted_ids = ",".join(f'"{tid}"' for tid in map(str, task_ids))

        subtask_rows = get(
            "project_subtasks",
            params={
                "parent_task_id": f"in.({quoted_ids})",
                "select": "id,parent_task_id,title,is_done",
            },
        ) or []



        subtask_map = defaultdict(list)
        for s in subtask_rows:
            subtask_map[str(s["parent_task_id"])].append(s)

        for q in grouped.values():
            for cat in q.values():
                for subs in cat.values():
                    for t in subs:
                        t["subtasks"] = subtask_map.get(str(t["id"]), [])
    # ----------------------------
    # Project progress
    # ----------------------------
    project_progress = defaultdict(lambda: {"done": 0, "total": 0})

    for q in grouped.values():
        for cat in q.values():
            for subs in cat.values():
                for t in subs:
                    pid = t.get("project_id")
                    if not pid:
                        continue
                    for s in t.get("subtasks", []):
                        project_progress[pid]["total"] += 1
                        if s["is_done"]:
                            project_progress[pid]["done"] += 1

    return grouped,project_progress


def save_todo(plan_date, form):
    logger.info("Saving Eisenhower matrix (batched)")
    logger.debug("Plan date: %s", plan_date)

    task_ids = [
        v for k, v in form.items()
        if k.endswith("_id[]") and not v.startswith("new_")
    ]
    logger.debug("Task IDs from form: %s", task_ids)

    moved_by_date = defaultdict(int)

    existing_rows = get(
        "todo_matrix",
        params={
            "id": f"in.({','.join(task_ids)})",
            "select": "id,plan_date,recurring_id",
        },
    ) or []

    logger.debug("Existing rows fetched: %s", existing_rows)

   
    existing_recurring_map = {
        str(r["id"]): r.get("recurring_id") for r in existing_rows
    }

    original_dates = {
        str(r["id"]): datetime.fromisoformat(r["plan_date"]).date()
        for r in existing_rows
    }
    logger.debug("Original dates snapshot: %s", original_dates)

    updates = []
    inserts = []

    # ==================================================
    # AUTHORITATIVE DELETE PASS (MUST BE FIRST)
    # ==================================================
    deleted_ids = set()
    for k, v in form.to_dict(flat=False).items():
        if "_deleted[" in k and v[-1] == "1":
            task_id = k.split("[", 1)[1].rstrip("]")
            deleted_ids.add(task_id)

    logger.debug("Deleted task IDs: %s", deleted_ids)

    if deleted_ids:
        safe_deleted_ids = [
            i for i in deleted_ids if not i.startswith("new_")
        ]

        logger.debug("Safe deleted IDs (DB): %s", safe_deleted_ids)

        if safe_deleted_ids:
            update(
                "todo_matrix",
                params={"id": f"in.({','.join(safe_deleted_ids)})"},
                json={"is_deleted": True},
            )

    # -----------------------------------
    # Process quadrants
    # -----------------------------------
    for quadrant in ["do", "schedule", "delegate", "eliminate"]:
        texts = form.getlist(f"{quadrant}[]")
        ids = form.getlist(f"{quadrant}_id[]")
        dates = form.getlist(f"{quadrant}_date[]")
        times = form.getlist(f"{quadrant}_time[]")
        categories = form.getlist(f"{quadrant}_category[]")
        subcategories = form.getlist(f"{quadrant}_subcategory[]")

        logger.debug(
            "Quadrant %s: %d tasks", quadrant, len(ids)
        )

        done_state = {}
        for k, v in form.to_dict(flat=False).items():
            if k.startswith(f"{quadrant}_done_state["):
                tid = k[len(f"{quadrant}_done_state["):-1]
                done_state[tid] = v

        for idx, text in enumerate(texts):
            if idx >= len(ids):
                continue

            task_id = str(ids[idx])

            if task_id in deleted_ids:
                logger.debug("Skipping deleted task %s", task_id)
                continue

            text = (text or "").strip()
            if not text:
                continue

            task_plan_date = (
                datetime.strptime(dates[idx], "%Y-%m-%d").date()
                if idx < len(dates) and dates[idx]
                else plan_date
            )

            original_date = original_dates.get(task_id, plan_date)

            logger.debug(
                "Task %s | original=%s | new=%s",
                task_id, original_date, task_plan_date
            )

            if original_date and task_plan_date != original_date:
                moved_by_date[task_plan_date] += 1
                logger.debug(
                    "Detected move: %s → %s",
                    original_date, task_plan_date
                )

            payload = {
                "quadrant": quadrant,
                "task_text": text,
                "task_date": str(task_plan_date),
                "task_time": (
                    times[idx] if idx < len(times) and times[idx]
                    else None
                ),
                "is_done": "1" in done_state.get(task_id, []),
                "position": idx,
                "is_deleted": False,
                "category": categories[idx] if idx < len(categories) else "General",
                "subcategory": subcategories[idx] if idx < len(subcategories) else "General",
            }

            if task_id.startswith("new_"):
                # autosave-created, never insert here
                continue

            # 🔑 ALWAYS update real IDs
            update_row = {
                "id": task_id,
                "plan_date": str(task_plan_date),
                **payload,
            }

            rid = existing_recurring_map.get(task_id)
            if rid:
                update_row["recurring_id"] = rid

            updates.append(update_row)


    updates = [
        u for u in updates
        if str(u.get("id")) not in deleted_ids
    ]

    logger.debug("Final updates count: %d", len(updates))
    logger.debug("Final inserts count: %d", len(inserts))

    if updates:
        post(
            "todo_matrix?on_conflict=id",
            updates,
            prefer="resolution=merge-duplicates",
        )

    # -----------------------------------
    # DEDUPE INSERTS
    # -----------------------------------
    seen = set()
    deduped_inserts = []

    for r in inserts:
        key = (
            r["plan_date"],
            r["quadrant"],
            r["task_text"].strip(),
            r.get("category"),
            r.get("subcategory"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped_inserts.append(r)

    inserts = deduped_inserts

    if inserts:
        for r in inserts:
            if not r.get("task_date"):
                r["task_date"] = str(plan_date)
        post("todo_matrix", inserts)

    logger.debug("Moved-by-date summary: %s", dict(moved_by_date))

    if moved_by_date:
        parts = []
        for d, count in sorted(moved_by_date.items()):
            label = "task" if count == 1 else "tasks"
            parts.append(f"{count} {label} → {d.strftime('%d %b')}")

        session["toast"] = {
            "type": "info",
            "message": "📅 " + " | ".join(parts),
        }
        logger.debug("Toast set: %s", session["toast"])

    logger.info(
        "Eisenhower save complete: %d updates, %d inserts, %d deletions",
        len(updates),
        len(inserts),
        len(deleted_ids),
    )


# Retired: copy_open_tasks_from_previous_day. The previous implementation
# duplicated yesterday's un-done rows forward as a mutation, which
# distorted historical analytics (Monday's "N tasks done" became a lie
# after Tuesday's copy-forward) and had two bugs — a NameError from
# `user_id=session[user_id]` and a missing user_id scope on the
# prev_rows fetch (data-leak across users).
#
# The replacement pattern is the Morning Dashboard (/summary?view=daily),
# which shows overdue tasks as a READ-THROUGH view without mutation.
# That page is now the app's default landing page, so overdue surfaces
# naturally on first open. If you ever need the copy-forward semantics
# back, write them with proper user scoping + audit log + undo toast.


### Travel mode Code Changes ###
#
# Travel templates are stored per-user in the `travel_tasks` table.
# Run this migration once in Supabase before using the new UI:
#
#   create table if not exists travel_tasks (
#     id bigserial primary key,
#     user_id uuid not null,
#     category text not null default 'Default',
#     quadrant text not null default 'do',
#     task_text text not null,
#     subcategory text default 'General',
#     order_index int default 0,
#     created_at timestamptz default now()
#   );
#   create index if not exists travel_tasks_user_cat_idx
#     on travel_tasks (user_id, category);
#
# On first use for a given user, we lazy-seed this table with the
# hardcoded list from config.TRAVEL_MODE_TASKS under a default
# category named "Default".


def _seed_travel_tasks_if_empty(user_id):
    """First-run seeding: copy config.TRAVEL_MODE_TASKS into travel_tasks
    under category 'Default'. Idempotent — only seeds if user has zero rows."""
    existing = get(
        "travel_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id",
            "limit": 1,
        },
    ) or []
    if existing:
        return 0

    payload = []
    for idx, (quadrant, text, subcat) in enumerate(TRAVEL_MODE_TASKS):
        payload.append({
            "user_id": user_id,
            "category": "Default",
            "quadrant": quadrant,
            "task_text": text,
            "subcategory": subcat,
            "order_index": idx,
        })
    if payload:
        try:
            post("travel_tasks", payload)
        except Exception as e:
            logger.warning("Travel-tasks seed failed: %s", e)
            return 0
    return len(payload)


def list_travel_categories(user_id):
    """Return sorted list of categories with task counts for a user."""
    _seed_travel_tasks_if_empty(user_id)
    rows = get(
        "travel_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "select": "category",
            "limit": 5000,
        },
    ) or []
    counts = {}
    for r in rows:
        c = r.get("category") or "Default"
        counts[c] = counts.get(c, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(counts.items())]


def list_travel_tasks(user_id, category=None):
    _seed_travel_tasks_if_empty(user_id)
    params = {
        "user_id": f"eq.{user_id}",
        "select": "id,category,quadrant,task_text,subcategory,order_index",
        "order": "order_index.asc,id.asc",
        "limit": 5000,
    }
    if category:
        params["category"] = f"eq.{category}"
    return get("travel_tasks", params=params) or []


def enable_travel_mode(plan_date, category=None):
    """
    Insert Travel Mode tasks for the day from the user's configured
    travel_tasks table, optionally filtered by category.
    Idempotent: skips tasks already present on the target day.
    """
    user_id = session["user_id"]

    # Lazy seed (no-op if user already has rows)
    _seed_travel_tasks_if_empty(user_id)

    # Load template tasks from DB
    tpl_params = {
        "user_id": f"eq.{user_id}",
        "select": "quadrant,task_text,subcategory,order_index",
        "order": "order_index.asc,id.asc",
        "limit": 5000,
    }
    if category:
        tpl_params["category"] = f"eq.{category}"

    templates = get("travel_tasks", params=tpl_params) or []
    if not templates:
        return 0

    # Existing tasks for the target day — idempotency guard
    existing = (
        get(
            "todo_matrix",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date}",
                "is_deleted": "eq.false",
                "select": "quadrant,task_text",
            },
        )
        or []
    )

    existing_keys = {
        (r["quadrant"], (r["task_text"] or "").strip().lower()) for r in existing
    }

    # Position seed per quadrant
    max_rows = (
        get(
            "todo_matrix",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date}",
                "is_deleted": "eq.false",
                "select": "quadrant,position",
            },
        )
        or []
    )
    position_map = {}
    for r in max_rows:
        q = r["quadrant"]
        position_map[q] = max(position_map.get(q, -1), r.get("position", -1))

    payload = []
    for t in templates:
        quadrant = t.get("quadrant") or "do"
        text = (t.get("task_text") or "").strip()
        if not text:
            continue

        key = (quadrant, text.lower())
        if key in existing_keys:
            continue

        pos = position_map.get(quadrant, -1) + 1
        position_map[quadrant] = pos

        payload.append({
            "plan_date": str(plan_date),
            "quadrant": quadrant,
            "task_text": text,
            "category": "Travel",
            "subcategory": t.get("subcategory") or "General",
            "is_done": False,
            "is_deleted": False,
            "position": pos,
            "user_id": user_id,
        })

    if payload:
        post("todo_matrix", payload)

    return len(payload)
def autosave_task(plan_date, task_id, quadrant, text=None, is_done=False, project_id=None):
    # -------------------------
    # NEW TASK → INSERT (Eisenhower direct entry)
    # -------------------------
    user_id=session["user_id"]
    if task_id.startswith("new_"):
        if not text:
            return {"id": task_id}

        rows = post(
            "todo_matrix?select=id",
            [{
                "plan_date": plan_date,
                "quadrant": quadrant,
                "task_text": text.strip(),
                "is_done": is_done,
                "is_deleted": False,
                "position": 999,
                "project_id": project_id,
                "user_id":user_id
            }],
            prefer="return=representation"
        ) or []

        if not rows:
            logger.error("Autosave insert failed for task: %s", task_id)
            return {"id": task_id}

        return {"id": str(rows[0]["id"])}

    # -------------------------
    # EXISTING TASK → DONE / UNDONE ONLY
    # -------------------------
    update(
        "todo_matrix",
        params={"id": f"eq.{task_id}","user_id":f"eq.{user_id}"},
        json={"is_done": is_done},
    )

    # -------------------------
    # 🔗 PROJECT SYNC (SAFE & ONE-WAY)
    # -------------------------
    if is_done:
        rows = get(
            "todo_matrix",
            params={
                "user_id":f"eq.{user_id}",
                "id": f"eq.{task_id}",
                "select": "source_task_id, recurring_instance_id",
            },
        )

        if not rows:
            return {"id": task_id}

        source_id = rows[0].get("source_task_id")
        recurring_instance_id = rows[0].get("recurring_instance_id")

        # ✅ Only non-recurring instances close the project task
        if source_id and not recurring_instance_id:
            update(
                "project_tasks",
                params={"task_id": f"eq.{source_id}","user_id":f"eq.{user_id}"},
                json={"status": "done"},
            )

    return {"id": task_id}

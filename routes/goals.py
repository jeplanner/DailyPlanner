"""
OKRs — 6-layer strategic hierarchy tied to the app's Project model.

    Project        (existing — the top container)
      └─ Objective        (strategic intent under a project)
           └─ Key Result  (measurable outcome proving the objective)
                └─ Initiative       (workstream grouping of tasks)
                     └─ Task        (project_tasks.initiative_id)
                          └─ Subtask (inherits parent task's initiative)

Design notes:
  * Objective.project_id is NULLABLE. Objectives without a project render
    in an "Unassigned" bucket on the /goals page for personal strategy.
  * Tasks now link to an Initiative (not directly to a KR). The task's
    KR and objective are resolved by walking up: task → initiative →
    key_result → objective. The legacy project_tasks.key_result_id
    column is preserved for backward compat but new code writes only
    initiative_id.
  * Progress is MANUAL for v1 — the user edits `current_value` on each
    KR. `progress_source` is reserved for a v2 auto roll-up.
  * Goal→Objective renaming: what earlier iterations called a "Goal" is
    now an "Objective" across the whole codebase. This route's file
    name is kept as routes/goals.py and its blueprint keeps the URL
    prefix "/goals" only so existing bookmarks and nav entries stay
    valid. Every internal noun is "objective".

─────────────────────────────────────────────────────────────────────
SCHEMA MIGRATION — run in Supabase
─────────────────────────────────────────────────────────────────────

-- Fresh install (no prior OKR schema present):

    create table if not exists objectives (
      id           uuid primary key default gen_random_uuid(),
      user_id      uuid not null,
      project_id   uuid references projects(project_id) on delete cascade,
      title        text not null,
      description  text,
      category     text,
      time_horizon text,                    -- annual | quarterly | monthly | ongoing
      start_date   date,
      target_date  date,
      status       text default 'active',   -- active | achieved | paused | abandoned
      color        text,
      order_index  int default 0,
      created_at   timestamptz default now()
    );
    create index if not exists objectives_user_idx    on objectives (user_id, status);
    create index if not exists objectives_project_idx on objectives (project_id);

    create table if not exists key_results (
      id              uuid primary key default gen_random_uuid(),
      user_id         uuid not null,
      objective_id    uuid not null references objectives(id) on delete cascade,
      title           text not null,
      metric_type     text,
      unit            text,
      start_value     numeric default 0,
      current_value   numeric default 0,
      target_value    numeric not null,
      direction       text default 'up',
      progress_source text default 'manual',
      order_index     int default 0,
      created_at      timestamptz default now()
    );
    create index if not exists kr_objective_idx on key_results (objective_id);

    create table if not exists initiatives (
      id            uuid primary key default gen_random_uuid(),
      user_id       uuid not null,
      key_result_id uuid not null references key_results(id) on delete cascade,
      title         text not null,
      description   text,
      status        text default 'active',
      order_index   int default 0,
      created_at    timestamptz default now()
    );
    create index if not exists initiatives_kr_idx on initiatives (key_result_id);

    alter table project_tasks
      add column if not exists initiative_id uuid references initiatives(id) on delete set null;
    create index if not exists project_tasks_initiative_idx on project_tasks (initiative_id);

    -- Legacy direct-KR column — kept for backward compat with earlier
    -- iterations. New code writes initiative_id, reads resolve the KR
    -- via the initiative. Safe to drop once no rows reference it:
    --   alter table project_tasks drop column if exists key_result_id;

-- Upgrading from the previous Project→Goal→KR schema (the one that had
-- a `goals` table with goal_id on key_results):

    -- 1) Rename goals table and its columns/indexes:
    alter table goals rename to objectives;
    alter index if exists goals_user_idx rename to objectives_user_idx;
    alter index if exists goals_project_idx rename to objectives_project_idx;

    -- 2) Rename key_results.goal_id → key_results.objective_id
    alter table key_results drop constraint if exists key_results_goal_fkey;
    alter table key_results rename column goal_id to objective_id;
    alter table key_results
      add constraint key_results_objective_fkey
      foreign key (objective_id) references objectives(id) on delete cascade;
    alter index if exists kr_goal_idx rename to kr_objective_idx;

    -- 3) Create initiatives table:
    create table if not exists initiatives (
      id            uuid primary key default gen_random_uuid(),
      user_id       uuid not null,
      key_result_id uuid not null references key_results(id) on delete cascade,
      title         text not null,
      description   text,
      status        text default 'active',
      order_index   int default 0,
      created_at    timestamptz default now()
    );
    create index if not exists initiatives_kr_idx on initiatives (key_result_id);

    -- 4) Add initiative_id to project_tasks:
    alter table project_tasks
      add column if not exists initiative_id uuid references initiatives(id) on delete set null;
    create index if not exists project_tasks_initiative_idx on project_tasks (initiative_id);

    -- 5) OPTIONAL data migration: if any tasks had a direct key_result_id,
    --    create a "General" initiative under each referenced KR and point
    --    those tasks at it. Skip if you want to manage the migration by hand.
    --
    --    insert into initiatives (user_id, key_result_id, title)
    --      select distinct user_id, key_result_id, 'General'
    --      from project_tasks
    --      where key_result_id is not null
    --      on conflict do nothing;
    --
    --    update project_tasks pt
    --       set initiative_id = (
    --         select id from initiatives i
    --          where i.key_result_id = pt.key_result_id and i.title = 'General'
    --          limit 1
    --       )
    --     where pt.initiative_id is null and pt.key_result_id is not null;

─────────────────────────────────────────────────────────────────────
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request, session

from services.login_service import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
goals_bp = Blueprint("goals", __name__)

_VALID_OBJECTIVE_STATUSES = {"active", "achieved", "paused", "abandoned"}
_VALID_HORIZONS = {"annual", "quarterly", "monthly", "ongoing"}
_VALID_DIRECTIONS = {"up", "down"}

# Every read filters this out. Every "delete" is a soft delete that
# flips this to true and stamps deleted_at. Restore is possible via
# the normal PATCH endpoint by sending {"is_deleted": false}.
_NOT_DELETED = {"is_deleted": "eq.false"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _soft_delete(table, params):
    """Soft-delete rows by flipping is_deleted=true and stamping deleted_at.

    Never falls back to a hard DELETE — if the schema is missing the
    soft-delete columns the exception will propagate and the caller
    returns a 500 with a real error message. The migration in the
    header docstring of this file must be run before soft-delete works.
    """
    update(table, params=params, json={"is_deleted": True, "deleted_at": _now_iso()})


# ──────────────────────────────────────────────────────────────────────
# PAGE RENDER
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/goals")
@login_required
def goals_page():
    return render_template("goals.html")


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _kr_progress(kr):
    start = float(kr.get("start_value") or 0)
    current = float(kr.get("current_value") or 0)
    target = float(kr.get("target_value") or 0)
    direction = kr.get("direction", "up")
    if target == start:
        return 0.0
    if direction == "up":
        pct = (current - start) / (target - start)
    else:
        pct = (start - current) / (start - target)
    return max(0.0, min(1.0, pct)) * 100.0


def recompute_kr_auto_progress(user_id, kr_id):
    """When a KR has auto_progress=true, derive current_value from the
    share of completed project_tasks that ladder up to it.

      current_value = start + (target - start) * (done / total)

    Tasks linked to one of the KR's initiatives count. Tasks linked
    directly via key_result_id (legacy) also count.

    Silently no-ops if auto_progress is false or the column doesn't
    exist (pre-migration). Logs failures but never raises — task
    toggles must not be blocked by KR roll-up issues.
    """
    try:
        kr_rows = get(
            "key_results",
            params={
                "id": f"eq.{kr_id}",
                "user_id": f"eq.{user_id}",
                "select": "id,start_value,target_value,auto_progress",
            },
        ) or []
        if not kr_rows:
            return
        kr = kr_rows[0]
        if not kr.get("auto_progress"):
            return

        # Collect all initiative ids under this KR
        init_rows = get(
            "initiatives",
            params={
                "key_result_id": f"eq.{kr_id}",
                "user_id": f"eq.{user_id}",
                "select": "id",
            },
        ) or []
        init_ids = [r["id"] for r in init_rows]

        # Count tasks linked via initiative OR (legacy) directly via KR.
        # Two queries summed for clarity — both small (per-user scope).
        total_done = 0
        total_all = 0

        if init_ids:
            ids_csv = ",".join(str(i) for i in init_ids)
            t_rows = get(
                "project_tasks",
                params={
                    "user_id": f"eq.{user_id}",
                    "is_deleted": "eq.false",
                    "is_eliminated": "eq.false",
                    "initiative_id": f"in.({ids_csv})",
                    "select": "task_id,status",
                },
            ) or []
            total_all += len(t_rows)
            total_done += sum(1 for r in t_rows if r.get("status") == "done")

        # Legacy: tasks linked directly via key_result_id (no initiative)
        legacy_rows = get(
            "project_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_eliminated": "eq.false",
                "key_result_id": f"eq.{kr_id}",
                "initiative_id": "is.null",
                "select": "task_id,status",
            },
        ) or []
        total_all += len(legacy_rows)
        total_done += sum(1 for r in legacy_rows if r.get("status") == "done")

        if total_all == 0:
            new_current = float(kr.get("start_value") or 0)
        else:
            start = float(kr.get("start_value") or 0)
            target = float(kr.get("target_value") or 0)
            ratio = total_done / total_all
            new_current = start + (target - start) * ratio

        update(
            "key_results",
            params={"id": f"eq.{kr_id}", "user_id": f"eq.{user_id}"},
            json={"current_value": round(new_current, 2)},
        )
    except Exception as e:
        # Don't let KR roll-up break a task toggle. Log + move on.
        import logging
        logging.getLogger(__name__).warning(
            "recompute_kr_auto_progress(%s) failed: %s", kr_id, e
        )


def recompute_kr_auto_progress_for_task(user_id, project_task_id):
    """Resolve the KR(s) a project task ladders up to and recompute.

    A task may link via initiative_id (preferred) or legacy key_result_id.
    Either path triggers a recompute of the parent KR.
    """
    try:
        rows = get(
            "project_tasks",
            params={
                "task_id": f"eq.{project_task_id}",
                "user_id": f"eq.{user_id}",
                "select": "initiative_id,key_result_id",
            },
        ) or []
        if not rows:
            return
        r = rows[0]
        kr_id = r.get("key_result_id")
        if not kr_id and r.get("initiative_id"):
            init_rows = get(
                "initiatives",
                params={"id": f"eq.{r['initiative_id']}", "select": "key_result_id"},
            ) or []
            if init_rows:
                kr_id = init_rows[0].get("key_result_id")
        if kr_id:
            recompute_kr_auto_progress(user_id, kr_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "recompute_kr_auto_progress_for_task(%s) failed: %s", project_task_id, e
        )


def _project_map(user_id):
    rows = get(
        "projects",
        params={"user_id": f"eq.{user_id}", "select": "project_id,name"},
    ) or []
    return {r["project_id"]: r["name"] for r in rows}


# ──────────────────────────────────────────────────────────────────────
# PICKER — used by the task-card Initiative dropdown
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/api/goals/picker")
@login_required
def picker():
    """
    Return active objectives → KRs → initiatives, optionally scoped to a project.

    Query params:
      project_id=<uuid>       limit to one project
      include_unassigned=1    also include objectives with no project_id
    """
    user_id = session["user_id"]
    project_id = request.args.get("project_id")
    include_unassigned = request.args.get("include_unassigned") == "1"

    objectives = get(
        "objectives",
        params={
            "user_id": f"eq.{user_id}",
            "status": "eq.active",
            "is_deleted": "eq.false",
            "select": "id,project_id,title,color,category,target_date",
            "order": "order_index.asc,created_at.asc",
            "limit": 500,
        },
    ) or []

    if project_id:
        if include_unassigned:
            objectives = [o for o in objectives if o.get("project_id") in (project_id, None)]
        else:
            objectives = [o for o in objectives if o.get("project_id") == project_id]

    if not objectives:
        return jsonify({"objectives": []})

    objective_ids = [o["id"] for o in objectives]
    krs = get(
        "key_results",
        params={
            "user_id": f"eq.{user_id}",
            "objective_id": f"in.({','.join(objective_ids)})",
            "is_deleted": "eq.false",
            "select": "id,objective_id,title,unit,current_value,target_value,direction",
            "order": "order_index.asc,created_at.asc",
            "limit": 2000,
        },
    ) or []

    kr_ids = [k["id"] for k in krs]
    initiatives = []
    if kr_ids:
        initiatives = get(
            "initiatives",
            params={
                "user_id": f"eq.{user_id}",
                "key_result_id": f"in.({','.join(kr_ids)})",
                "status": "eq.active",
                "is_deleted": "eq.false",
                "select": "id,key_result_id,title",
                "order": "order_index.asc,created_at.asc",
                "limit": 5000,
            },
        ) or []

    result = []
    for o in objectives:
        obj_krs = [k for k in krs if k["objective_id"] == o["id"]]
        result.append({
            "id": o["id"],
            "title": o["title"],
            "project_id": o.get("project_id"),
            "color": o.get("color"),
            "category": o.get("category"),
            "target_date": o.get("target_date"),
            "key_results": [
                {
                    "id": kr["id"],
                    "title": kr["title"],
                    "unit": kr.get("unit"),
                    "current_value": kr.get("current_value"),
                    "target_value": kr.get("target_value"),
                    "direction": kr.get("direction", "up"),
                    "initiatives": [
                        {"id": i["id"], "title": i["title"]}
                        for i in initiatives if i["key_result_id"] == kr["id"]
                    ],
                }
                for kr in obj_krs
            ],
        })

    return jsonify({"objectives": result})


# ──────────────────────────────────────────────────────────────────────
# FULL TREE — used by the /goals (OKRs) page
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/api/goals", methods=["GET"])
@login_required
def list_objectives():
    """
    Return objectives with nested KRs, nested initiatives, and computed progress.

    Query params:
      project_id=<uuid>       filter to one project
      include_archived=1      also surface paused/abandoned/achieved
      include_unassigned=1    also include objectives with no project_id
    """
    user_id = session["user_id"]
    project_id = request.args.get("project_id")
    include_archived = request.args.get("include_archived") == "1"
    include_unassigned = request.args.get("include_unassigned") == "1"

    params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "select": "*",
        "order": "order_index.asc,created_at.asc",
        "limit": 500,
    }
    if not include_archived:
        params["status"] = "eq.active"

    objectives = get("objectives", params=params) or []

    if project_id:
        if include_unassigned:
            objectives = [o for o in objectives if o.get("project_id") in (project_id, None)]
        else:
            objectives = [o for o in objectives if o.get("project_id") == project_id]

    pmap = _project_map(user_id)

    if not objectives:
        return jsonify({
            "objectives": [],
            "projects": sorted(pmap.items(), key=lambda x: x[1].lower()),
        })

    objective_ids = [o["id"] for o in objectives]
    krs = get(
        "key_results",
        params={
            "user_id": f"eq.{user_id}",
            "objective_id": f"in.({','.join(objective_ids)})",
            "is_deleted": "eq.false",
            "select": "*",
            "order": "order_index.asc,created_at.asc",
            "limit": 5000,
        },
    ) or []

    kr_ids = [k["id"] for k in krs]
    initiatives = []
    if kr_ids:
        initiatives = get(
            "initiatives",
            params={
                "user_id": f"eq.{user_id}",
                "key_result_id": f"in.({','.join(kr_ids)})",
                "is_deleted": "eq.false",
                "select": "*",
                "order": "order_index.asc,created_at.asc",
                "limit": 5000,
            },
        ) or []

    # Attach initiatives to their KRs, then compute progress bottom-up.
    for k in krs:
        k["initiatives"] = [i for i in initiatives if i["key_result_id"] == k["id"]]
        k["_progress"] = _kr_progress(k)

    for o in objectives:
        o["key_results"] = [k for k in krs if k["objective_id"] == o["id"]]
        o["_progress"] = (
            sum(k["_progress"] for k in o["key_results"]) / len(o["key_results"])
            if o["key_results"] else 0
        )
        o["project_name"] = pmap.get(o.get("project_id")) if o.get("project_id") else None

    return jsonify({
        "objectives": objectives,
        "projects": sorted(pmap.items(), key=lambda x: x[1].lower()),
    })


# ──────────────────────────────────────────────────────────────────────
# OBJECTIVES CRUD
# Route paths kept under /api/goals/* for URL backward compat.
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/api/goals", methods=["POST"])
@login_required
def create_objective():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400

    horizon = (data.get("time_horizon") or "ongoing").strip().lower()
    if horizon not in _VALID_HORIZONS:
        horizon = "ongoing"

    payload = {
        "user_id": session["user_id"],
        "project_id": data.get("project_id") or None,
        "title": title,
        "description": (data.get("description") or "").strip() or None,
        "category": (data.get("category") or "").strip() or None,
        "time_horizon": horizon,
        "start_date": data.get("start_date") or None,
        "target_date": data.get("target_date") or None,
        "color": (data.get("color") or "").strip() or None,
        "status": "active",
    }
    rows = post("objectives", payload)
    return jsonify({"status": "ok", "objective": rows[0] if rows else None})


@goals_bp.route("/api/goals/<objective_id>", methods=["PATCH"])
@login_required
def update_objective(objective_id):
    data = request.get_json(force=True) or {}
    allowed = {
        "project_id", "title", "description", "category", "time_horizon",
        "start_date", "target_date", "status", "color", "order_index",
        "is_deleted",  # allow restore via PATCH {is_deleted: false}
    }
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "no valid fields"}), 400

    if "project_id" in patch and patch["project_id"] == "":
        patch["project_id"] = None
    if "status" in patch and patch["status"] not in _VALID_OBJECTIVE_STATUSES:
        return jsonify({"error": "invalid status"}), 400
    if "time_horizon" in patch and patch["time_horizon"] not in _VALID_HORIZONS:
        return jsonify({"error": "invalid time_horizon"}), 400

    # Clear deleted_at when restoring
    if patch.get("is_deleted") is False:
        patch["deleted_at"] = None

    update(
        "objectives",
        params={"id": f"eq.{objective_id}", "user_id": f"eq.{session['user_id']}"},
        json=patch,
    )
    return jsonify({"status": "ok"})


@goals_bp.route("/api/goals/<objective_id>", methods=["DELETE"])
@login_required
def delete_objective(objective_id):
    """
    Soft delete an objective. Cascades in application code to every
    KR under the objective and every initiative under those KRs.
    Row data is preserved — restore via PATCH {is_deleted: false}.
    """
    user_id = session["user_id"]

    try:
        # 1) Fetch live KRs under this objective so we can cascade
        #    the soft-delete down to initiatives.
        krs = get(
            "key_results",
            params={
                "user_id": f"eq.{user_id}",
                "objective_id": f"eq.{objective_id}",
                "is_deleted": "eq.false",
                "select": "id",
                "limit": 500,
            },
        ) or []
        kr_ids = [k["id"] for k in krs]

        # 2) Cascade: initiatives under those KRs
        if kr_ids:
            _soft_delete(
                "initiatives",
                params={
                    "user_id": f"eq.{user_id}",
                    "key_result_id": f"in.({','.join(kr_ids)})",
                },
            )
            # 3) Cascade: the KRs themselves
            _soft_delete(
                "key_results",
                params={
                    "user_id": f"eq.{user_id}",
                    "id": f"in.({','.join(kr_ids)})",
                },
            )

        # 4) Finally, the objective itself
        _soft_delete(
            "objectives",
            params={"id": f"eq.{objective_id}", "user_id": f"eq.{user_id}"},
        )
    except Exception as e:
        logger.exception("delete_objective failed")
        return jsonify({"error": f"Delete failed: {e}"}), 500

    return jsonify({"status": "ok"})


# ──────────────────────────────────────────────────────────────────────
# KEY RESULTS CRUD
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/api/key-results", methods=["POST"])
@login_required
def create_key_result():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    objective_id = data.get("objective_id")
    target_value = data.get("target_value")

    if not title or not objective_id:
        return jsonify({"error": "title and objective_id required"}), 400
    try:
        target_value = float(target_value)
    except (TypeError, ValueError):
        return jsonify({"error": "target_value must be a number"}), 400

    direction = (data.get("direction") or "up").strip().lower()
    if direction not in _VALID_DIRECTIONS:
        direction = "up"

    payload = {
        "user_id": session["user_id"],
        "objective_id": objective_id,
        "title": title,
        "metric_type": (data.get("metric_type") or "count").strip().lower() or "count",
        "unit": (data.get("unit") or "").strip() or None,
        "start_value": float(data.get("start_value") or 0),
        "current_value": float(data.get("current_value") or 0),
        "target_value": target_value,
        "direction": direction,
        "progress_source": "manual",
    }
    rows = post("key_results", payload)
    return jsonify({"status": "ok", "key_result": rows[0] if rows else None})


@goals_bp.route("/api/key-results/<kr_id>", methods=["PATCH"])
@login_required
def update_key_result(kr_id):
    data = request.get_json(force=True) or {}
    allowed = {
        "title", "metric_type", "unit",
        "start_value", "current_value", "target_value",
        "direction", "order_index",
        "is_deleted",
        "auto_progress",  # opt-in to KR roll-up from completed tasks
    }
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "no valid fields"}), 400

    for numeric_key in ("start_value", "current_value", "target_value"):
        if numeric_key in patch:
            try:
                patch[numeric_key] = float(patch[numeric_key])
            except (TypeError, ValueError):
                return jsonify({"error": f"{numeric_key} must be a number"}), 400

    if "direction" in patch and patch["direction"] not in _VALID_DIRECTIONS:
        return jsonify({"error": "invalid direction"}), 400

    if patch.get("is_deleted") is False:
        patch["deleted_at"] = None

    update(
        "key_results",
        params={"id": f"eq.{kr_id}", "user_id": f"eq.{session['user_id']}"},
        json=patch,
    )
    # If we just turned auto_progress on, recompute immediately so the
    # KR's current_value reflects today's task completions.
    if patch.get("auto_progress") is True:
        recompute_kr_auto_progress(session["user_id"], kr_id)
    return jsonify({"status": "ok"})


@goals_bp.route("/api/key-results/<kr_id>", methods=["DELETE"])
@login_required
def delete_key_result(kr_id):
    """Soft delete. Cascades to initiatives under this KR."""
    user_id = session["user_id"]

    try:
        # Cascade to initiatives FIRST, then the KR itself.
        _soft_delete(
            "initiatives",
            params={
                "user_id": f"eq.{user_id}",
                "key_result_id": f"eq.{kr_id}",
            },
        )
        _soft_delete(
            "key_results",
            params={"id": f"eq.{kr_id}", "user_id": f"eq.{user_id}"},
        )
    except Exception as e:
        logger.exception("delete_key_result failed")
        return jsonify({"error": f"Delete failed: {e}"}), 500
    return jsonify({"status": "ok"})


# ──────────────────────────────────────────────────────────────────────
# INITIATIVES CRUD — new layer between KR and Task
# ──────────────────────────────────────────────────────────────────────

@goals_bp.route("/api/initiatives", methods=["POST"])
@login_required
def create_initiative():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    key_result_id = data.get("key_result_id")

    if not title or not key_result_id:
        return jsonify({"error": "title and key_result_id required"}), 400

    payload = {
        "user_id": session["user_id"],
        "key_result_id": key_result_id,
        "title": title,
        "description": (data.get("description") or "").strip() or None,
        "status": "active",
    }
    rows = post("initiatives", payload)
    return jsonify({"status": "ok", "initiative": rows[0] if rows else None})


@goals_bp.route("/api/initiatives/<initiative_id>", methods=["PATCH"])
@login_required
def update_initiative(initiative_id):
    data = request.get_json(force=True) or {}
    allowed = {"title", "description", "status", "order_index", "is_deleted"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "no valid fields"}), 400
    if "status" in patch and patch["status"] not in _VALID_OBJECTIVE_STATUSES:
        return jsonify({"error": "invalid status"}), 400

    if patch.get("is_deleted") is False:
        patch["deleted_at"] = None

    update(
        "initiatives",
        params={"id": f"eq.{initiative_id}", "user_id": f"eq.{session['user_id']}"},
        json=patch,
    )
    return jsonify({"status": "ok"})


@goals_bp.route("/api/initiatives/<initiative_id>", methods=["DELETE"])
@login_required
def delete_initiative(initiative_id):
    """Soft delete a single initiative. Linked tasks keep their
    initiative_id pointer so that if the initiative is restored, the
    task linkage is automatically intact again."""
    try:
        _soft_delete(
            "initiatives",
            params={"id": f"eq.{initiative_id}", "user_id": f"eq.{session['user_id']}"},
        )
    except Exception as e:
        logger.exception("delete_initiative failed")
        return jsonify({"error": f"Delete failed: {e}"}), 500
    return jsonify({"status": "ok"})

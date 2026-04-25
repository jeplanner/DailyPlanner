"""Focus Log — repository view of where time has gone.

Renders /focus-log and exposes a JSON API that aggregates time spent on
every adhoc_task. Totals are computed on the fly from task_time_logs so
there's no denormalised counter to keep in sync.

Schema lives in MIGRATION_ADHOC_TASKS.sql:
    adhoc_tasks(id, user_id, label, category, is_archived, created_at,
                last_used_at)
    task_time_logs.adhoc_task_id  ← back-pointer
"""

from collections import defaultdict
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

focus_log_bp = Blueprint("focus_log", __name__)


@focus_log_bp.route("/focus-log")
@login_required
def focus_log_page():
    """Render the page. Data hydrates client-side via the JSON API."""
    return render_template("focus_log.html")


@focus_log_bp.route("/api/focus-log/tasks", methods=["GET"])
@login_required
def list_focus_tasks():
    """Return every adhoc_task for the user with aggregated time stats.

    Query params:
        include_archived=1   — also return archived rows (default off)

    Response:
        { "tasks": [ { id, label, category, total_seconds, session_count,
                       last_session_at, is_archived } ],
          "totals": { total_seconds, session_count, label_count } }
    """
    user_id = session["user_id"]
    include_archived = request.args.get("include_archived") in ("1", "true", "yes")

    rows = get(
        "adhoc_tasks",
        params={
            "user_id": f"eq.{user_id}",
            **({} if include_archived else {"is_archived": "eq.false"}),
            "select": "id,label,category,is_archived,created_at,last_used_at",
            "order": "last_used_at.desc",
        },
    ) or []

    # Pull every adhoc-tagged time log in one go and bucket in memory.
    # Each log has duration_seconds (set on stop) for completed sessions.
    logs = get(
        "task_time_logs",
        params={
            "user_id": f"eq.{user_id}",
            "adhoc_task_id": "not.is.null",
            "select": "adhoc_task_id,duration_seconds,started_at,ended_at",
        },
    ) or []

    by_task = defaultdict(lambda: {"sec": 0, "n": 0, "last": None, "running": False})
    for log in logs:
        tid = log.get("adhoc_task_id")
        if not tid:
            continue
        bucket = by_task[tid]
        # Currently-running sessions have null ended_at; count them
        # separately so the row can flag "in progress" without skewing
        # totals.
        if log.get("ended_at") is None:
            bucket["running"] = True
            continue
        bucket["sec"] += int(log.get("duration_seconds") or 0)
        bucket["n"] += 1
        started = log.get("started_at")
        if started and (bucket["last"] is None or started > bucket["last"]):
            bucket["last"] = started

    out = []
    for r in rows:
        s = by_task.get(r["id"], {"sec": 0, "n": 0, "last": None, "running": False})
        out.append({
            **r,
            "total_seconds": s["sec"],
            "session_count": s["n"],
            "last_session_at": s["last"] or r.get("last_used_at"),
            "is_running": s["running"],
        })
    # Most time first; ties broken by recency.
    out.sort(key=lambda t: (-t["total_seconds"], (t.get("last_session_at") or "")), reverse=False)

    totals = {
        "total_seconds": sum(t["total_seconds"] for t in out),
        "session_count": sum(t["session_count"] for t in out),
        "label_count":   len([t for t in out if not t.get("is_archived")]),
    }
    return jsonify({"tasks": out, "totals": totals})


@focus_log_bp.route("/api/focus-log/tasks/<task_id>/sessions", methods=["GET"])
@login_required
def list_task_sessions(task_id):
    """Return the most recent N sessions for a single adhoc_task.
    Used to power the row-expand drilldown."""
    user_id = session["user_id"]
    limit = min(int(request.args.get("limit") or 50), 200)
    rows = get(
        "task_time_logs",
        params={
            "user_id": f"eq.{user_id}",
            "adhoc_task_id": f"eq.{task_id}",
            "select": "id,started_at,ended_at,duration_seconds,paused_seconds",
            "order": "started_at.desc",
            "limit": str(limit),
        },
    ) or []
    return jsonify({"sessions": rows})


@focus_log_bp.route("/api/focus-log/tasks/<task_id>", methods=["PATCH"])
@login_required
def update_focus_task(task_id):
    """Rename, recategorise, or archive an adhoc task."""
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    allowed = {"label", "category", "is_archived"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "nothing to update"}), 400
    if "label" in patch:
        patch["label"] = (patch["label"] or "").strip()
        if not patch["label"]:
            return jsonify({"error": "label can't be empty"}), 400
    update(
        "adhoc_tasks",
        params={"id": f"eq.{task_id}", "user_id": f"eq.{user_id}"},
        json=patch,
    )
    return jsonify({"ok": True})


# ── Helper used by routes/todo.py timer_start ──────────────────────────
# Find an adhoc_task by case-insensitive label, or create one. Returns the
# row id. Kept here so the Focus Log feature owns its own table — todo.py
# imports this function rather than reaching into the schema directly.
def find_or_create_adhoc_task(user_id, label):
    label = (label or "").strip()
    if not label:
        return None
    now_iso = datetime.now(timezone.utc).isoformat()
    # ilike with no wildcards is case-insensitive equality in PostgREST.
    existing = get(
        "adhoc_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "label": f"ilike.{label}",
            "is_archived": "eq.false",
            "select": "id",
            "limit": "1",
        },
    ) or []
    if existing:
        tid = existing[0]["id"]
        update(
            "adhoc_tasks",
            params={"id": f"eq.{tid}", "user_id": f"eq.{user_id}"},
            json={"last_used_at": now_iso},
        )
        return tid
    rows = post(
        "adhoc_tasks",
        {"user_id": user_id, "label": label, "last_used_at": now_iso},
    )
    return rows[0]["id"] if rows else None

"""
Family Tasks — cross-user assignment for allowlisted users.

Reuses the chat allowlist (CHAT_USER_EMAILS) — "family" means the
same set of people who can use the family chat room. A non-allowed
user gets a 404 on every endpoint and a hidden nav link.

Push fires to the assignee when they aren't the creator (no point
pinging yourself about a task you just made). Same daemon-thread
pattern as the chat fanout, swallowing failures so a slow push
endpoint never blocks the create response.

Names are denormalized at write time (created_by_name,
assigned_to_name) so listing doesn't need a join and renaming a user
later doesn't rewrite history. The matching uuids on the row stay
authoritative for permission checks.

Schema: see MIGRATION_FAMILY_TASKS.sql.
"""
import logging
import threading
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, render_template, request, session

from flask_login import current_user

from auth import login_required
from routes.chat import _allowlist, user_allowed
from services import push_service
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

family_tasks_bp = Blueprint("family_tasks", __name__)

MAX_TITLE = 300
MAX_NOTES = 2000


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def _gate():
    if not user_allowed():
        abort(404)


def _author_name():
    name = (getattr(current_user, "display_name", "") or "").strip()
    if name:
        return name[:80]
    email = (getattr(current_user, "email", "") or "").strip()
    if email:
        return email.split("@", 1)[0][:80]
    return "Someone"


def _family_members():
    """Resolve allowlisted emails to (id, name) tuples. Used both by
    the /members endpoint (for the assignee picker) and internally by
    push fanout. The users table is small enough that one trip per
    call is fine."""
    emails = list(_allowlist())
    if not emails:
        return []
    rows = get("users", {
        "email": f"in.({','.join(emails)})",
        "select": "id,display_name,email",
    }) or []
    out = []
    for r in rows:
        name = (r.get("display_name") or r.get("email", "").split("@", 1)[0] or "Someone").strip()
        out.append({"id": r["id"], "name": name[:80]})
    # Stable ordering so the dropdown doesn't shuffle between loads.
    out.sort(key=lambda x: x["name"].lower())
    return out


def _shape(row, viewer_id):
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "notes": row.get("notes") or "",
        "created_by": row.get("created_by"),
        "created_by_name": row.get("created_by_name") or "",
        "assigned_to": row.get("assigned_to"),
        "assigned_to_name": row.get("assigned_to_name") or "",
        "due_date": row.get("due_date"),
        "done_at": row.get("done_at"),
        "created_at": row.get("created_at"),
        "is_done": bool(row.get("done_at")),
        "mine": str(row.get("assigned_to")) == str(viewer_id),
        "by_me": str(row.get("created_by")) == str(viewer_id),
    }


# ── Page ────────────────────────────────────────────────────────


@family_tasks_bp.route("/family-tasks", methods=["GET"])
@login_required
def page():
    _gate()
    return render_template(
        "family_tasks.html",
        viewer_name=_author_name(),
    )


# ── API ─────────────────────────────────────────────────────────


@family_tasks_bp.route("/api/family-tasks/members", methods=["GET"])
@login_required
def list_members():
    """Used to populate the assignee dropdown."""
    _gate()
    return jsonify({"members": _family_members()})


@family_tasks_bp.route("/api/family-tasks", methods=["GET"])
@login_required
def list_tasks():
    """`view` selects the filter: 'mine' (assigned to me), 'by-me'
    (created by me), 'all' (every family task). Done tasks are hidden
    unless `show_done=1`. Always oldest-first within a list so adding
    a task appends — predictable ordering matches the chat page."""
    _gate()
    viewer_id = session["user_id"]
    view = (request.args.get("view") or "mine").strip().lower()
    show_done = (request.args.get("show_done") or "").strip() in ("1", "true", "yes")

    params = {
        "deleted_at": "is.null",
        "select": (
            "id,title,notes,created_by,created_by_name,"
            "assigned_to,assigned_to_name,due_date,done_at,created_at"
        ),
        # Order: open tasks first (NULL done_at), then by due date,
        # then by created_at as a stable tiebreaker.
        "order": "done_at.asc.nullsfirst,due_date.asc.nullslast,created_at.asc",
        "limit": "300",
    }
    if view == "mine":
        params["assigned_to"] = f"eq.{viewer_id}"
    elif view == "by-me":
        params["created_by"] = f"eq.{viewer_id}"
    # 'all' = no extra filter

    if not show_done:
        params["done_at"] = "is.null"

    try:
        rows = get("family_tasks", params) or []
    except Exception as e:
        logger.exception("family_tasks list failed: %s", e)
        return jsonify({"error": "Couldn't load tasks"}), 502

    return jsonify({"tasks": [_shape(r, viewer_id) for r in rows]})


@family_tasks_bp.route("/api/family-tasks", methods=["POST"])
@login_required
def create_task():
    _gate()
    viewer_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    title = title[:MAX_TITLE]

    notes = (data.get("notes") or "").strip()
    notes = notes[:MAX_NOTES] if notes else None

    assigned_to = (data.get("assigned_to") or "").strip()
    if not assigned_to:
        return jsonify({"error": "Assignee required"}), 400

    # Defense in depth: confirm the assignee is actually a family
    # member, not just any user_id the client made up.
    members = _family_members()
    member = next((m for m in members if str(m["id"]) == str(assigned_to)), None)
    if not member:
        return jsonify({"error": "Assignee is not a family member"}), 400

    due_date = (data.get("due_date") or "").strip() or None
    if due_date:
        # PostgREST will reject anything that isn't a YYYY-MM-DD;
        # we let it through and surface the error if so.
        pass

    payload = {
        "title": title,
        "notes": notes,
        "created_by": viewer_id,
        "created_by_name": _author_name(),
        "assigned_to": assigned_to,
        "assigned_to_name": member["name"],
        "due_date": due_date,
    }
    try:
        rows = post("family_tasks", payload)
    except Exception as e:
        logger.exception("family_tasks create failed: %s", e)
        return jsonify({"error": "Create failed"}), 502

    row = rows[0] if rows else payload
    # Notify the assignee — but skip self-assignments (no point
    # pinging yourself about a task you literally just typed).
    if str(assigned_to) != str(viewer_id):
        threading.Thread(
            target=_push_assignment,
            args=(assigned_to, _author_name(), title),
            daemon=True,
        ).start()
    return jsonify({"task": _shape(row, viewer_id)})


@family_tasks_bp.route("/api/family-tasks/<task_id>/done", methods=["POST"])
@login_required
def toggle_done(task_id):
    """Tick / untick. Either the assignee or the creator can flip it —
    it's a family group, not strict role enforcement. Body: {done: bool}
    (omit to toggle whatever the current state is)."""
    _gate()
    viewer_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    rows = get("family_tasks", {
        "id": f"eq.{task_id}",
        "deleted_at": "is.null",
        "select": "id,created_by,assigned_to,done_at",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    cur = rows[0]
    if str(cur.get("created_by")) != str(viewer_id) and str(cur.get("assigned_to")) != str(viewer_id):
        return jsonify({"error": "Not yours"}), 403

    if "done" in data:
        want_done = bool(data["done"])
    else:
        want_done = not bool(cur.get("done_at"))

    patch = {"done_at": _utcnow_iso() if want_done else None}
    try:
        update("family_tasks", params={"id": f"eq.{task_id}"}, json=patch)
    except Exception as e:
        logger.exception("family_tasks done toggle failed: %s", e)
        return jsonify({"error": "Save failed"}), 502
    return jsonify({"ok": True, "done": want_done})


@family_tasks_bp.route("/api/family-tasks/<task_id>/update", methods=["POST"])
@login_required
def update_task(task_id):
    """Edit title / notes / due / assignee. Only the creator can
    edit — assignees can mark done but not reassign or rename. Keeps
    the model simple at the cost of slight stiffness."""
    _gate()
    viewer_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    rows = get("family_tasks", {
        "id": f"eq.{task_id}",
        "deleted_at": "is.null",
        "select": "id,created_by,assigned_to,assigned_to_name,title",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    cur = rows[0]
    if str(cur.get("created_by")) != str(viewer_id):
        return jsonify({"error": "Only the creator can edit"}), 403

    patch = {}
    if "title" in data:
        v = (data.get("title") or "").strip()
        if not v:
            return jsonify({"error": "Title required"}), 400
        patch["title"] = v[:MAX_TITLE]
    if "notes" in data:
        v = (data.get("notes") or "").strip()
        patch["notes"] = v[:MAX_NOTES] if v else None
    if "due_date" in data:
        v = (data.get("due_date") or "").strip()
        patch["due_date"] = v or None
    reassigned_to = None
    if "assigned_to" in data:
        v = (data.get("assigned_to") or "").strip()
        if not v:
            return jsonify({"error": "Assignee required"}), 400
        member = next((m for m in _family_members() if str(m["id"]) == str(v)), None)
        if not member:
            return jsonify({"error": "Not a family member"}), 400
        patch["assigned_to"] = v
        patch["assigned_to_name"] = member["name"]
        if str(v) != str(cur.get("assigned_to")):
            reassigned_to = v

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update("family_tasks", params={"id": f"eq.{task_id}"}, json=patch)
    except Exception as e:
        logger.exception("family_tasks update failed: %s", e)
        return jsonify({"error": "Save failed"}), 502

    # Reassignment = the new assignee should be told. We use the
    # final title (post-patch) so an edit-and-reassign reads cleanly.
    if reassigned_to and str(reassigned_to) != str(viewer_id):
        new_title = patch.get("title") or cur.get("title") or "A task"
        threading.Thread(
            target=_push_assignment,
            args=(reassigned_to, _author_name(), new_title),
            daemon=True,
        ).start()

    return jsonify({"ok": True, "patch": patch})


@family_tasks_bp.route("/api/family-tasks/<task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    """Soft-delete. Creator or assignee can remove."""
    _gate()
    viewer_id = session["user_id"]

    rows = get("family_tasks", {
        "id": f"eq.{task_id}",
        "deleted_at": "is.null",
        "select": "id,created_by,assigned_to",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    cur = rows[0]
    if (str(cur.get("created_by")) != str(viewer_id)
        and str(cur.get("assigned_to")) != str(viewer_id)):
        return jsonify({"error": "Not yours"}), 403

    try:
        update(
            "family_tasks",
            params={"id": f"eq.{task_id}"},
            json={"deleted_at": _utcnow_iso()},
        )
    except Exception as e:
        logger.exception("family_tasks delete failed: %s", e)
        return jsonify({"error": "Delete failed"}), 502
    return jsonify({"ok": True})


# ── Push helper ────────────────────────────────────────────────


def _push_assignment(assignee_id, creator_name, title):
    """Best-effort 'you have a new task' ping. Mirrors the chat
    fanout — swallows every exception so a slow or broken push
    endpoint can never wedge the create/update response."""
    try:
        preview = title if len(title) <= 120 else title[:119] + "…"
        push_service.send_to_user(
            user_id=assignee_id,
            title=f"{creator_name} assigned you a task",
            body=preview,
            url="/family-tasks",
            tag="family-task",
        )
    except Exception:
        logger.exception("family_tasks push to %s failed", assignee_id)

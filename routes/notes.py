"""Notes blueprint — Apple-Notes-style master/detail.

Endpoints:
    GET  /notes/scribble                 — list page (sidebar of folders + grid)
    GET  /notes/scribble/new             — editor (new note)
    GET  /notes/scribble/<id>            — editor (existing note)
    POST /notes/scribble/save            — create or update
    POST /notes/scribble/<id>/delete     — soft-delete (is_deleted = true)
    POST /notes/scribble/<id>/pin        — toggle is_pinned (idempotent: body { pinned: bool })
    POST /notes/scribble/<id>/move       — change notebook (body { notebook: "Work" })
    GET  /notes/scribble/api/folders     — distinct notebooks with counts (used by sidebar)
    POST /notes/scribble/checklist/preview  — parse @-tags, return preview
    POST /notes/scribble/checklist/convert  — parse + create project tasks

Schema lives in MIGRATION_NOTES_FOLDERS.sql. Folders are just a text
column on the note row; the distinct values become the folder list.
"""

import logging
from collections import defaultdict
from datetime import date

from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update
from utils.checklist_parser import parse_note as parse_checklist_note

logger = logging.getLogger("daily_plan")


notes_bp = Blueprint("notes", __name__)


def _get_one(table, params):
    rows = get(table, params=params)
    return rows[0] if rows else None


def _list_folders(user_id):
    """Return [{name, count}] for every distinct notebook the user has,
    plus an implicit "All Notes" bucket and a "Pinned" bucket so the
    sidebar can render them as first-class entries."""
    rows = get(
        "scribble_notes",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "notebook,is_pinned",
        },
    ) or []
    counts = defaultdict(int)
    pinned = 0
    for r in rows:
        nb = (r.get("notebook") or "All Notes").strip() or "All Notes"
        counts[nb] += 1
        if r.get("is_pinned"):
            pinned += 1
    folders = [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[0].lower())]
    return {
        "folders": folders,
        "total": sum(counts.values()),
        "pinned": pinned,
    }


@notes_bp.route("/notes/scribble", methods=["GET"])
@login_required
def scribble_list():
    user_id = session["user_id"]
    q = (request.args.get("q") or "").strip()
    folder = (request.args.get("folder") or "").strip()
    pinned_only = request.args.get("pinned") in ("1", "true", "yes")

    params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        # Pinned first, then most-recently-updated; PostgREST sorts in the
        # order the keys appear so this stable secondary sort works.
        "order": "is_pinned.desc,updated_at.desc",
    }
    if q:
        params["or"] = f"(title.ilike.*{q}*,content.ilike.*{q}*)"
    if folder and folder.lower() not in ("all", "all notes"):
        params["notebook"] = f"eq.{folder}"
    if pinned_only:
        params["is_pinned"] = "eq.true"

    notes = get("scribble_notes", params=params) or []
    sidebar = _list_folders(user_id)

    return render_template(
        "scribble_list.html",
        notes=notes,
        q=q,
        folder=folder,
        pinned_only=pinned_only,
        sidebar=sidebar,
    )


def _peers_in_folder(user_id, folder):
    """Return every note in `folder`, ordered the same way the list page
    orders them (pinned first, most-recent next). Used to power the
    editor's "notes in this folder" rail and the prev/next nav."""
    params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "select": "id,title,is_pinned,updated_at,notebook",
        "order": "is_pinned.desc,updated_at.desc",
        "limit": "200",
    }
    if folder and folder.lower() not in ("all", "all notes"):
        params["notebook"] = f"eq.{folder}"
    return get("scribble_notes", params=params) or []


@notes_bp.route("/notes/scribble/new")
@login_required
def scribble_new():
    user_id = session["user_id"]
    folder = request.args.get("folder", "")
    return render_template(
        "scribble_edit.html",
        note=None,
        sidebar=_list_folders(user_id),
        prefill_folder=folder,
        peers=_peers_in_folder(user_id, folder),
    )


@notes_bp.route("/notes/scribble/<note_id>")
@login_required
def scribble_edit(note_id):
    user_id = session["user_id"]
    note = _get_one(
        "scribble_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
    )
    if not note:
        abort(404)
    return render_template(
        "scribble_edit.html",
        note=note,
        sidebar=_list_folders(user_id),
        prefill_folder="",
        peers=_peers_in_folder(user_id, note.get("notebook") or ""),
    )


@notes_bp.route("/notes/scribble/save", methods=["POST"])
@login_required
def save_scribble():
    data = request.get_json() or {}
    user_id = session["user_id"]

    note_id = data.get("id")
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    notebook = (data.get("notebook") or "").strip() or "All Notes"
    is_pinned = bool(data.get("is_pinned"))

    payload = {
        "title": title,
        "content": content,
        "notebook": notebook,
        "is_pinned": is_pinned,
    }

    if note_id:
        update(
            "scribble_notes",
            params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
            json=payload,
        )
    else:
        payload["user_id"] = user_id
        res = post("scribble_notes", payload)
        note_id = res[0]["id"] if res else None

    return jsonify({"status": "ok", "id": note_id})


@notes_bp.route("/notes/scribble/<note_id>/delete", methods=["POST"])
@login_required
def delete_scribble(note_id):
    user_id = session["user_id"]
    update(
        "scribble_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )
    return jsonify({"status": "ok"})


@notes_bp.route("/notes/scribble/<note_id>/pin", methods=["POST"])
@login_required
def pin_scribble(note_id):
    """Toggle / set is_pinned. Body: { "pinned": true } (optional —
    omitted body flips the current state)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    if "pinned" in data:
        new_state = bool(data["pinned"])
    else:
        row = _get_one(
            "scribble_notes",
            params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}",
                    "select": "is_pinned"},
        )
        if not row:
            return jsonify({"error": "not found"}), 404
        new_state = not bool(row.get("is_pinned"))
    update(
        "scribble_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        json={"is_pinned": new_state},
    )
    return jsonify({"status": "ok", "is_pinned": new_state})


@notes_bp.route("/notes/scribble/<note_id>/move", methods=["POST"])
@login_required
def move_scribble(note_id):
    """Move the note to a different notebook. Body: { "notebook": "..." }
    Empty / "All Notes" lands the note in the default bucket."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    notebook = (data.get("notebook") or "").strip() or "All Notes"
    update(
        "scribble_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        json={"notebook": notebook},
    )
    return jsonify({"status": "ok", "notebook": notebook})


@notes_bp.route("/notes/scribble/api/folders", methods=["GET"])
@login_required
def api_folders():
    """Sidebar refresh hook — returns the current folder list with counts."""
    return jsonify(_list_folders(session["user_id"]))


@notes_bp.route("/notes/scribble/folder/rename", methods=["POST"])
@login_required
def rename_folder():
    """Bulk-rename a folder: every note where notebook=<from> gets
    notebook=<to>. Body: { "from": "Work", "to": "Work + Side projects" }
    Empty/missing fields are no-ops; renaming to "All Notes" is allowed
    (same as moving the contents to the default bucket)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    src = (data.get("from") or "").strip()
    dst = (data.get("to") or "").strip()
    if not src or not dst:
        return jsonify({"error": "from and to required"}), 400
    if src == dst:
        return jsonify({"ok": True, "noop": True})
    update(
        "scribble_notes",
        params={"user_id": f"eq.{user_id}", "notebook": f"eq.{src}"},
        json={"notebook": dst},
    )
    return jsonify({"ok": True, "from": src, "to": dst})


# ─────────── Checklist → Tasks (smart @-tag conversion) ──────────


def _ensure_default_project(user_id):
    """Return the project_id of the user's default project, creating
    one ("Inbox") on demand if it doesn't exist yet.

    Backed by the partial unique index from MIGRATION_DEFAULT_PROJECT.sql
    so a user can have at most one active default at a time.
    """
    rows = get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "is_default": "eq.true",
            "is_archived": "eq.false",
            "select": "project_id,name",
            "limit": "1",
        },
    ) or []
    if rows:
        return rows[0]["project_id"]

    # No default yet — try to "promote" any project literally named
    # "Inbox" first (so a user who already created one manually doesn't
    # end up with two). If none exists, create a fresh Inbox project.
    inbox_rows = get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "name": "ilike.Inbox",
            "is_archived": "eq.false",
            "select": "project_id",
            "limit": "1",
        },
    ) or []
    if inbox_rows:
        pid = inbox_rows[0]["project_id"]
        try:
            update(
                "projects",
                params={"project_id": f"eq.{pid}", "user_id": f"eq.{user_id}"},
                json={"is_default": True},
            )
        except Exception as e:
            logger.warning("could not flag existing Inbox as default: %s", e)
        return pid

    created = post(
        "projects",
        {
            "user_id": user_id,
            "name": "Inbox",
            "description": "Default landing project for tasks without an explicit @ProjectName.",
            "is_default": True,
            "is_archived": False,
        },
    )
    if not created:
        return None
    return created[0]["project_id"]


def _resolve_project(user_id, name):
    """Look up a project by case-insensitive name. Returns its id, or
    None if no active project matches."""
    if not name:
        return None
    rows = get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "name": f"ilike.{name}",
            "is_archived": "eq.false",
            "select": "project_id,name",
            "limit": "1",
        },
    ) or []
    return rows[0]["project_id"] if rows else None


def _build_task_payload(user_id, project_id, item, default_priority="medium"):
    """Translate a ParsedItem into the project_tasks insert payload."""
    payload = {
        "project_id": project_id,
        "user_id": user_id,
        "task_text": item.title,
        "status": "open",
        "priority": default_priority,
    }
    if item.due_date:
        payload["start_date"] = item.due_date.isoformat()
        payload["due_date"] = item.due_date.isoformat()
    if item.recurrence_type:
        payload["is_recurring"] = True
        payload["recurrence_type"] = item.recurrence_type
        if item.recurrence_days:
            payload["recurrence_days"] = item.recurrence_days
        # auto_advance keeps the next occurrence flowing once one is done.
        payload["auto_advance"] = True
    return payload


@notes_bp.route("/notes/scribble/checklist/preview", methods=["POST"])
@login_required
def checklist_preview():
    """Parse a note's checklist lines and report what would be created.

    Body: { content: "<note body>" }
    Response:
      {
        items: [
          {
            title, due_date, recurrence_type, recurrence_days,
            project_name, project_id, project_resolved (bool),
            already_checked
          },
          ...
        ],
        default_project: { project_id, name }
      }
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    content = data.get("content") or ""

    parsed = parse_checklist_note(content, date.today())
    if not parsed:
        return jsonify({"items": [], "default_project": None})

    default_pid = _ensure_default_project(user_id)
    default_name = "Inbox"
    if default_pid:
        rows = get(
            "projects",
            params={"project_id": f"eq.{default_pid}", "select": "name", "limit": "1"},
        ) or []
        if rows:
            default_name = rows[0].get("name") or "Inbox"

    out = []
    for item in parsed:
        d = item.to_dict()
        if item.project_name:
            pid = _resolve_project(user_id, item.project_name)
            d["project_id"] = pid or default_pid
            d["project_resolved"] = bool(pid)
            d["effective_project_name"] = item.project_name if pid else default_name
        else:
            d["project_id"] = default_pid
            d["project_resolved"] = True   # default is always resolvable
            d["effective_project_name"] = default_name
        out.append(d)

    return jsonify({
        "items": out,
        "default_project": {
            "project_id": default_pid,
            "name": default_name,
        } if default_pid else None,
    })


@notes_bp.route("/notes/scribble/checklist/convert", methods=["POST"])
@login_required
def checklist_convert():
    """Parse the note and create project_tasks rows for each line.

    Body:
      { content: "<note body>",
        skip_checked: true (default — don't re-create lines already
                            ticked off in the note) }

    Response:
      { created: N, skipped: M, errors: K, items: [...] }

    The endpoint is *idempotent on the note* — calling it twice will
    create the same tasks twice. Callers that want one-shot conversion
    should mark the lines as `[x]` after success (the UI does this).
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    content = data.get("content") or ""
    skip_checked = data.get("skip_checked", True)

    parsed = parse_checklist_note(content, date.today())
    if not parsed:
        return jsonify({"created": 0, "skipped": 0, "errors": 0, "items": []})

    default_pid = _ensure_default_project(user_id)
    if not default_pid:
        return jsonify({"error": "Could not create default project"}), 502

    # Cache project name lookups so we don't hit the DB once per line.
    project_cache = {}

    def _project_for(name):
        if not name:
            return default_pid, True   # default
        key = name.lower()
        if key in project_cache:
            pid = project_cache[key]
            return pid, pid != default_pid
        pid = _resolve_project(user_id, name)
        project_cache[key] = pid or default_pid
        return (pid or default_pid), bool(pid)

    created = 0
    skipped = 0
    errors = 0
    out_items = []
    for item in parsed:
        if skip_checked and item.already_checked:
            skipped += 1
            out_items.append({**item.to_dict(), "status": "skipped"})
            continue

        pid, resolved = _project_for(item.project_name)
        payload = _build_task_payload(user_id, pid, item)

        try:
            res = post("project_tasks", payload)
            if not res:
                errors += 1
                out_items.append({**item.to_dict(), "status": "error"})
                continue
            created += 1
            out_items.append({
                **item.to_dict(),
                "status": "created",
                "task_id": res[0].get("task_id"),
                "project_id": pid,
                "project_resolved": resolved,
            })
        except Exception as e:
            logger.warning("checklist convert failed for line %r: %s", item.title, e)
            errors += 1
            out_items.append({**item.to_dict(), "status": "error"})

    return jsonify({
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "items": out_items,
        "default_project_id": default_pid,
    })


@notes_bp.route("/notes/scribble/folder/delete", methods=["POST"])
@login_required
def delete_folder():
    """Soft-delete every note in a folder. Body: { "name": "Old folder" }
    Notes are flagged is_deleted=true (per the project's no-hard-delete
    rule) so they remain recoverable from the database if needed."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if name.lower() == "all notes":
        return jsonify({"error": "default folder can't be deleted"}), 400
    update(
        "scribble_notes",
        params={"user_id": f"eq.{user_id}", "notebook": f"eq.{name}"},
        json={"is_deleted": True},
    )
    return jsonify({"ok": True, "name": name})

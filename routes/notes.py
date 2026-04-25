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

Schema lives in MIGRATION_NOTES_FOLDERS.sql. Folders are just a text
column on the note row; the distinct values become the folder list.
"""

from collections import defaultdict

from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update


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


@notes_bp.route("/notes/scribble/new")
@login_required
def scribble_new():
    user_id = session["user_id"]
    return render_template(
        "scribble_edit.html",
        note=None,
        sidebar=_list_folders(user_id),
        prefill_folder=request.args.get("folder", ""),
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

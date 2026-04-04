
from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update


def get_one(table, params):
    rows = get(table, params=params)
    return rows[0] if rows else None

notes_bp = Blueprint("notes", __name__)
@notes_bp.route("/notes/scribble", methods=["GET"])
@login_required
def scribble_list():
    q = (request.args.get("q") or "").strip()

    params = {
        "user_id": f"eq.{session['user_id']}",
        "order": "updated_at.desc",
        "is_deleted": "eq.false",
    }

    if q:
        # search in title OR content (case-insensitive)
        params["or"] = f"(title.ilike.*{q}*,content.ilike.*{q}*)"

    notes = get("scribble_notes", params=params) or []

    return render_template(
        "scribble_list.html",
        notes=notes,
        q=q,
    )


@notes_bp.route("/notes/scribble/new")
@login_required
def scribble_new():
    return render_template("scribble_edit.html", note=None)
@notes_bp.route("/notes/scribble/<note_id>")
@login_required
def scribble_edit(note_id):

    note = get_one(
        "scribble_notes",
        params={
            "id": f"eq.{note_id}",
            "user_id": f"eq.{session['user_id']}"
        }
    )

    if not note:
        abort(404)

    return render_template(
        "scribble_edit.html",
        note=note
    )
    
   
@notes_bp.route("/notes/scribble/save", methods=["POST"])
@login_required
def save_scribble():
    data = request.get_json() or {}
    user_id = session["user_id"]

    note_id = data.get("id")
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if note_id:
        # 🔁 UPDATE existing note
        update(
            "scribble_notes",
            params={
                "id": f"eq.{note_id}",
                "user_id": f"eq.{user_id}"
            },
            json={
                "title": title,
                "content": content
            }
        )
    else:
        # ➕ CREATE new note
        res = post(
            "scribble_notes",
            {
                "user_id": user_id,
                "title": title,
                "content": content
            }
        )
        note_id = res[0]["id"] if res else None

    return jsonify({
        "status": "ok",
        "id": note_id
    })
    

@notes_bp.route("/notes/scribble/<note_id>/delete", methods=["POST"])
@login_required
def delete_scribble(note_id):

    update(
        "scribble_notes",
        params={
            "id": f"eq.{note_id}",
            "user_id": f"eq.{session['user_id']}"
        },
        json={"is_deleted": True}
    )

    return jsonify({"status": "ok"})
from flask import Blueprint, request, jsonify
from db import get_db
from services.inbox_service import detect_type, fetch_title, generate_summary
import uuid

inbox_bp = Blueprint("inbox_bp", __name__)


# ---------------- CREATE ----------------
@inbox_bp.route("/api/inbox", methods=["POST"])
def create_inbox():
    data = request.get_json() or {}

    user_id = data.get("user_id", "demo")
    url = data.get("url")
    description = data.get("description", "")

    if not url:
        return jsonify({"error": "url required"}), 400

    title = fetch_title(url)
    content_type = detect_type(url)
    summary = generate_summary(description)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        insert into inbox_links
        (id, user_id, url, title, description, content_type)
        values (%s,%s,%s,%s,%s,%s)
    """, (
        str(uuid.uuid4()),
        user_id,
        url,
        title,
        description,
        content_type
    ))

    conn.commit()

    return jsonify({"success": True})


# ---------------- LIST ----------------
@inbox_bp.route("/api/inbox", methods=["GET"])
def get_inbox():
    user_id = request.args.get("user_id", "demo")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        select id, url, title, description, content_type, is_favorite
        from inbox_links
        where user_id=%s
        order by created_at desc
    """, (user_id,))

    rows = cur.fetchall()

    return jsonify([
        {
            "id": r[0],
            "url": r[1],
            "title": r[2],
            "description": r[3],
            "type": r[4],
            "favorite": r[5]
        }
        for r in rows
    ])


# ---------------- FAVORITE ----------------
@inbox_bp.route("/api/inbox/<id>/favorite", methods=["POST"])
def favorite(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        update inbox_links
        set is_favorite = not is_favorite
        where id=%s
    """, (id,))

    conn.commit()

    return jsonify({"success": True})
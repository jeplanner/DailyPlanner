import uuid
from flask import Blueprint, request, jsonify, session, render_template
from supabase_client import get, post, update, delete
from services.login_service import login_required
from services.inbox_service import detect_type, fetch_meta, auto_categorize

inbox_bp = Blueprint("inbox_bp", __name__)

VALID_STATUSES = {"Unread", "Reading", "Done", "Saved"}


@inbox_bp.route("/inbox")
@login_required
def inbox_page():
    return render_template("inbox.html")


@inbox_bp.route("/api/inbox", methods=["POST"])
@login_required
def create_inbox():
    data = request.get_json() or {}
    user_id = session["user_id"]

    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400

    meta = fetch_meta(url)
    title = meta["title"]
    raw_desc = data.get("description", "").strip() or meta["description"]
    content_type = detect_type(url)
    category = auto_categorize(url, title, raw_desc)

    # AI-powered description if user didn't provide one and meta description is weak
    description = raw_desc
    if not data.get("description", "").strip() and len(raw_desc) < 50:
        try:
            from services.ai_service import call_gemini
            prompt = (
                f"Write a 1-2 sentence description of what this webpage is about. "
                f"Be concise and factual.\n\n"
                f"URL: {url}\nTitle: {title}\nMeta: {raw_desc}"
            )
            ai_desc = call_gemini(prompt)
            if ai_desc and len(ai_desc) > 10 and not ai_desc.startswith("AI service"):
                description = ai_desc.strip()[:500]
        except Exception:
            pass  # Fall back to raw meta description

    post("inbox_links", {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "url": url,
        "title": title,
        "description": description,
        "content_type": content_type,
        "category": category,
        "status": "Unread",
    })

    return jsonify({
        "success": True,
        "title": title,
        "description": description,
        "category": category,
        "content_type": content_type,
    })


@inbox_bp.route("/api/inbox", methods=["GET"])
@login_required
def get_inbox():
    user_id = session["user_id"]
    status_filter = request.args.get("status")
    category_filter = request.args.get("category")

    params = {
        "user_id": f"eq.{user_id}",
        "order": "created_at.desc",
        "select": "id,url,title,description,content_type,is_favorite,category,status,created_at",
    }
    if status_filter:
        params["status"] = f"eq.{status_filter}"
    if category_filter:
        params["category"] = f"eq.{category_filter}"

    rows = get("inbox_links", params=params) or []
    return jsonify(rows)


@inbox_bp.route("/api/inbox/<item_id>", methods=["PATCH"])
@login_required
def update_inbox(item_id):
    user_id = session["user_id"]
    data = request.get_json() or {}

    allowed = {}
    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": "invalid status"}), 400
        allowed["status"] = data["status"]
    if "category" in data:
        allowed["category"] = data["category"]
    if "title" in data:
        allowed["title"] = data["title"]
    if "description" in data:
        allowed["description"] = data["description"]

    if not allowed:
        return jsonify({"error": "nothing to update"}), 400

    update("inbox_links", params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"}, json=allowed)
    return jsonify({"success": True})


@inbox_bp.route("/api/inbox/<item_id>/favorite", methods=["POST"])
@login_required
def favorite(item_id):
    user_id = session["user_id"]

    rows = get("inbox_links", params={
        "id": f"eq.{item_id}",
        "user_id": f"eq.{user_id}",
        "select": "id,is_favorite",
    }) or []

    if not rows:
        return jsonify({"error": "not found"}), 404

    current = rows[0].get("is_favorite", False)
    update("inbox_links", params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"}, json={"is_favorite": not current})
    return jsonify({"success": True})


@inbox_bp.route("/api/inbox/<item_id>", methods=["DELETE"])
@login_required
def delete_inbox(item_id):
    user_id = session["user_id"]
    delete("inbox_links", params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"})
    return jsonify({"success": True})

import uuid
import os
import requests as http_requests
import logging
from flask import Blueprint, request, jsonify, session, render_template
from supabase_client import get, post, update, delete
from services.login_service import login_required
from services.inbox_service import detect_type, fetch_meta, auto_categorize

logger = logging.getLogger("daily_plan")

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


# Google API error reasons → human hints. Lets the Inbox surface the
# actual cause (e.g. key missing YouTube Data API in its allowlist)
# instead of a vague "search unavailable" so the user can fix it.
_GOOGLE_ERROR_HINTS = {
    "API_KEY_SERVICE_BLOCKED": (
        "API key isn't authorised for this service. In Google Cloud Console "
        "→ APIs & Services → Credentials, open the key, and either pick "
        "'Don't restrict key' or add this API to the allowed list."
    ),
    "API_DISABLED": (
        "API not enabled on this Google Cloud project. Enable it under "
        "APIs & Services → Library."
    ),
    "rateLimitExceeded": "Daily quota exceeded — try again tomorrow.",
    "quotaExceeded": "Daily quota exceeded — try again tomorrow.",
    "keyInvalid": "API key is invalid. Check GOOGLE_API_KEY in .env.",
    "keyExpired": "API key has expired.",
    "ipRefererBlocked": (
        "API key has HTTP-referrer / IP restrictions that block server-side "
        "calls. Remove or relax those restrictions on the key."
    ),
}


def _google_error_hint(payload):
    """Pull the actionable hint from a Google API error body. Looks at the
    structured `error.details[].reason` first (newer APIs), then falls back
    to legacy `error.errors[].reason`, then to `error.message`."""
    err = (payload or {}).get("error", {}) or {}
    for det in err.get("details", []) or []:
        reason = det.get("reason")
        if reason in _GOOGLE_ERROR_HINTS:
            return _GOOGLE_ERROR_HINTS[reason]
    for e in err.get("errors", []) or []:
        reason = e.get("reason")
        if reason in _GOOGLE_ERROR_HINTS:
            return _GOOGLE_ERROR_HINTS[reason]
    return err.get("message") or "Search unavailable"


def _cse_thumbnail(item):
    """CSE thumbnails appear under different pagemap keys depending on the
    site. Pick the first one that exists, return "" otherwise."""
    pagemap = item.get("pagemap", {}) or {}
    for k in ("cse_thumbnail", "cse_image"):
        arr = pagemap.get(k) or []
        if arr and arr[0].get("src"):
            return arr[0]["src"]
    return ""


@inbox_bp.route("/api/inbox/search", methods=["GET"])
@login_required
def search_web():
    """Search YouTube for videos matching a query."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return jsonify({"error": "GOOGLE_API_KEY not set in .env."}), 503

    try:
        r = http_requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 6,
                "key": api_key,
            },
            timeout=8,
        )
        if r.status_code != 200:
            try:
                payload = r.json()
            except Exception:
                payload = {}
            hint = _google_error_hint(payload)
            logger.warning("YouTube search failed: %s %s", r.status_code, hint)
            return jsonify({"error": f"YouTube: {hint}"}), 503

        results = []
        for item in r.json().get("items", []):
            vid = item["id"].get("videoId", "")
            snip = item.get("snippet", {})
            results.append({
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": snip.get("title", ""),
                "description": snip.get("description", "")[:200],
                "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "channel": snip.get("channelTitle", ""),
            })
        return jsonify(results)
    except Exception as e:
        logger.warning("YouTube search error: %s", e)
        return jsonify({"error": f"YouTube: {e}"}), 500


@inbox_bp.route("/api/inbox/search-articles", methods=["GET"])
@login_required
def search_articles():
    """Search articles via Google Programmable Search Engine (CSE).

    The CSE — created at https://programmablesearchengine.google.com/ —
    is the thing that decides which publishers are searched (Medium,
    Substack, dev.to, freecodecamp, etc.). This endpoint just relays
    the query and reformats results to match the YouTube payload shape
    so the frontend can render both side by side.
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cse_id = os.environ.get("GOOGLE_CSE_ID", "")
    if not api_key:
        return jsonify({"error": "GOOGLE_API_KEY not set in .env."}), 503
    if not cse_id:
        return jsonify({
            "error": (
                "Articles search not configured. Create a Programmable "
                "Search Engine at programmablesearchengine.google.com, set "
                "GOOGLE_CSE_ID in .env, and add 'Custom Search API' to your "
                "GOOGLE_API_KEY's allowed services."
            )
        }), 503

    try:
        r = http_requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "q": query,
                "cx": cse_id,
                "num": 6,
                "key": api_key,
                "safe": "off",
            },
            timeout=8,
        )
        if r.status_code != 200:
            try:
                payload = r.json()
            except Exception:
                payload = {}
            hint = _google_error_hint(payload)
            logger.warning("CSE search failed: %s %s", r.status_code, hint)
            return jsonify({"error": f"Articles: {hint}"}), 503

        results = []
        for item in r.json().get("items", []):
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "description": (item.get("snippet", "") or "")[:240],
                "source": item.get("displayLink", ""),
                "thumbnail": _cse_thumbnail(item),
            })
        return jsonify(results)
    except Exception as e:
        logger.warning("CSE search error: %s", e)
        return jsonify({"error": f"Articles: {e}"}), 500

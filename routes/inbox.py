import uuid
import os
import re
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

    # AI-powered description if user didn't provide one and meta description
    # is weak. Skipped entirely for YouTube URLs because fetch_meta() now
    # gets the real description via the YouTube Data API — no need to ask
    # the AI to invent one.
    description = raw_desc
    is_youtube = bool(re.search(r"(?:youtube\.com|youtu\.be)", url, re.IGNORECASE))
    if (
        not data.get("description", "").strip()
        and len(raw_desc) < 50
        and not is_youtube
    ):
        try:
            from services.ai_service import call_gemini
            # Prompt is explicit that the AI should NOT try to fetch the
            # URL — earlier prompts asked "describe what this webpage is
            # about" and Gemini interpreted that as needing to visit the
            # page, then refused with "I don't have the ability to access
            # the webpage directly..." which leaked into descriptions.
            prompt = (
                "Write a one-sentence factual description of this link "
                "based ONLY on the title and URL below. Do NOT try to "
                "fetch the page. If you have no useful information, "
                "reply with the single word: SKIP.\n\n"
                f"Title: {title}\n"
                f"URL: {url}"
            )
            ai_desc = (call_gemini(prompt) or "").strip()
            if _ai_response_is_useful(ai_desc):
                description = ai_desc[:500]
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


# LLM refusal phrases we don't want leaking into the description field.
# Gemini in particular loves to apologise when it can't do what you
# asked; these openers are the dead giveaway. Match is case-insensitive
# and only at the start of the response so legitimate descriptions
# containing these phrases are not over-filtered.
_AI_REFUSAL_PREFIXES = (
    "unfortunately",
    "i don't have",
    "i do not have",
    "i can't",
    "i cannot",
    "i'm unable",
    "i am unable",
    "without more",
    "without further",
    "as an ai",
    "i'm sorry",
    "i am sorry",
    "ai service",   # historic prefix our wrapper used for upstream errors
    "skip",         # explicit signal we asked for in the prompt
)


def _ai_response_is_useful(text):
    """Return True only if the AI gave us something we'd actually want to
    save as a description — long enough to be informative and not opening
    with a refusal / apology / SKIP signal."""
    if not text or len(text) < 15:
        return False
    lowered = text.lower().lstrip("*-_ \t\n")
    for prefix in _AI_REFUSAL_PREFIXES:
        if lowered.startswith(prefix):
            return False
    return True


def _cse_thumbnail(item):
    """CSE thumbnails appear under different pagemap keys depending on the
    site. Pick the first one that exists, return "" otherwise."""
    pagemap = item.get("pagemap", {}) or {}
    for k in ("cse_thumbnail", "cse_image"):
        arr = pagemap.get(k) or []
        if arr and arr[0].get("src"):
            return arr[0]["src"]
    return ""


def _key_fingerprint(api_key):
    """Render the API key as <first 8>...<last 5> so it's identifiable
    in logs without exposing the secret. Five trailing chars matches
    the user's request and makes it trivial to compare with what's in
    Google Cloud Console (which shows the full key on click)."""
    if not api_key:
        return "<missing>"
    if len(api_key) <= 13:
        return "<short:%d>" % len(api_key)
    return "%s...%s" % (api_key[:8], api_key[-5:])


def _log_google_failure(label, response, query, api_key, cx=None):
    """Dump everything useful from a Google API failure: status, the exact
    machine-readable reason codes (errors[].reason + details[].reason +
    metadata.consumer/service), the message, response headers that hint
    at quota / billing, and a truncated body. Lets a future read of the
    log answer "why did this 403?" without having to reproduce.

    project_number is parsed out of the consumer field ("projects/12345")
    and given its own slot so you can read it at a glance — answering
    "did Google see the call hit the project I expected?"."""
    try:
        payload = response.json()
    except Exception:
        payload = {}
    err = (payload or {}).get("error", {}) or {}
    reasons = [e.get("reason") for e in err.get("errors", []) or [] if e.get("reason")]
    detail_reasons = [d.get("reason") for d in err.get("details", []) or [] if d.get("reason")]
    consumer = service = None
    for d in err.get("details", []) or []:
        md = d.get("metadata") or {}
        if md.get("consumer") and not consumer:
            consumer = md["consumer"]
        if md.get("service") and not service:
            service = md["service"]
    project_number = None
    if consumer and consumer.startswith("projects/"):
        project_number = consumer.split("/", 1)[1]
    quota_headers = {
        k: response.headers.get(k)
        for k in ("X-Goog-Quota-User", "Retry-After", "X-RateLimit-Remaining")
        if response.headers.get(k)
    }
    logger.warning(
        "%s search FAILED: http=%s status=%s key=%s cx=%s "
        "project_number=%s service=%s reasons=%s details=%s "
        "quota_headers=%s msg=%r query=%r body=%r",
        label,
        response.status_code,
        err.get("status"),
        _key_fingerprint(api_key),
        cx or "<n/a>",
        project_number,
        service,
        reasons,
        detail_reasons,
        quota_headers,
        (err.get("message") or "")[:300],
        query[:80],
        response.text[:500],
    )


@inbox_bp.route("/api/inbox/search", methods=["GET"])
@login_required
def search_web():
    """Search YouTube for videos matching a query."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning("YouTube search: GOOGLE_API_KEY missing")
        return jsonify({"error": "GOOGLE_API_KEY not set in .env."}), 503

    logger.info("YouTube search: q=%r key=%s", query[:80], _key_fingerprint(api_key))

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
            _log_google_failure("YouTube", r, query, api_key)
            try:
                payload = r.json()
            except Exception:
                payload = {}
            hint = _google_error_hint(payload)
            return jsonify({"error": f"YouTube: {hint}"}), 503

        items = r.json().get("items", [])
        logger.info("YouTube search: q=%r items=%d", query[:80], len(items))
        results = []
        for item in items:
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
        logger.exception("YouTube search exception: q=%r err=%s", query[:80], e)
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
        logger.warning("CSE search: GOOGLE_API_KEY missing")
        return jsonify({"error": "GOOGLE_API_KEY not set in .env."}), 503
    if not cse_id:
        logger.warning("CSE search: GOOGLE_CSE_ID missing")
        return jsonify({
            "error": (
                "Articles search not configured. Create a Programmable "
                "Search Engine at programmablesearchengine.google.com, set "
                "GOOGLE_CSE_ID in .env, and add 'Custom Search API' to your "
                "GOOGLE_API_KEY's allowed services."
            )
        }), 503

    logger.info(
        "CSE search: q=%r key=%s cx=%s",
        query[:80], _key_fingerprint(api_key), cse_id,
    )

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
            _log_google_failure("CSE", r, query, api_key, cx=cse_id)
            try:
                payload = r.json()
            except Exception:
                payload = {}
            hint = _google_error_hint(payload)
            return jsonify({"error": f"Articles: {hint}"}), 503

        items = r.json().get("items", [])
        logger.info("CSE search: q=%r items=%d", query[:80], len(items))
        results = []
        for item in items:
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "description": (item.get("snippet", "") or "")[:240],
                "source": item.get("displayLink", ""),
                "thumbnail": _cse_thumbnail(item),
            })
        return jsonify(results)
    except Exception as e:
        logger.exception("CSE search exception: q=%r err=%s", query[:80], e)
        return jsonify({"error": f"Articles: {e}"}), 500

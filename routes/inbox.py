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


_YT_ID_RE_PY = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def _yt_extract_id(url: str) -> str | None:
    m = _YT_ID_RE_PY.search(url or "")
    return m.group(1) if m else None


def _yt_parse_duration(iso: str) -> int:
    """ISO 8601 duration ('PT1H23M45S', 'PT5M30S') → total seconds.
    Returns 0 for unparseable input rather than raising — view fields
    should never blow up the search response."""
    if not iso or not iso.startswith("PT"):
        return 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s


def _yt_enrich(items: list, api_key: str) -> list:
    """Decorate YouTube search results with duration, view count,
    channel id, and subscriber count. One videos.list call (≤50 ids)
    plus one channels.list call (≤50 ids) — 2 quota units total.

    Best-effort: any sub-call failure leaves the field as None and
    returns the items as-is rather than failing the whole search."""
    if not items:
        return items
    video_ids = [_yt_extract_id(it.get("url") or "") for it in items]
    video_ids = [v for v in video_ids if v]
    if not video_ids:
        return items

    # videos.list — duration + viewCount + channelId
    video_meta = {}
    try:
        r = http_requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "id": ",".join(video_ids),
                "part": "contentDetails,statistics,snippet",
                "key": api_key,
            },
            timeout=8,
        )
        if r.status_code == 200:
            for v in r.json().get("items", []):
                video_meta[v["id"]] = {
                    "duration_seconds": _yt_parse_duration(
                        v.get("contentDetails", {}).get("duration", "")
                    ),
                    "view_count": int(
                        v.get("statistics", {}).get("viewCount", 0) or 0
                    ),
                    "channel_id": v.get("snippet", {}).get("channelId", ""),
                }
        else:
            logger.warning("yt_enrich videos.list http=%s body=%r",
                           r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("yt_enrich videos.list exception: %s", e)

    # channels.list — subscriberCount
    channel_ids = list({m["channel_id"] for m in video_meta.values() if m.get("channel_id")})
    channel_subs = {}
    if channel_ids:
        try:
            r = http_requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "id": ",".join(channel_ids),
                    "part": "statistics",
                    "key": api_key,
                },
                timeout=8,
            )
            if r.status_code == 200:
                for c in r.json().get("items", []):
                    stats = c.get("statistics", {}) or {}
                    # YouTube hides subs for some channels; treat as None.
                    if stats.get("hiddenSubscriberCount"):
                        channel_subs[c["id"]] = None
                    else:
                        channel_subs[c["id"]] = int(stats.get("subscriberCount", 0) or 0)
            else:
                logger.warning("yt_enrich channels.list http=%s body=%r",
                               r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("yt_enrich channels.list exception: %s", e)

    # Merge back into the original items list, preserving order.
    enriched = []
    for it in items:
        vid = _yt_extract_id(it.get("url") or "") or ""
        meta = video_meta.get(vid, {})
        cid = meta.get("channel_id") or ""
        out = dict(it)
        out["duration_seconds"] = meta.get("duration_seconds", 0)
        out["view_count"] = meta.get("view_count", 0)
        out["channel_id"] = cid
        out["subscriber_count"] = channel_subs.get(cid)
        enriched.append(out)
    return enriched


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


def _extract_readable_html(html: str) -> dict:
    """Heuristic article-content extractor. Looks for the densest text
    container (<article>, <main>, or the <div> with the most direct text),
    strips chrome (nav/aside/footer/script), and sanitises with bleach
    so we never inject untrusted markup straight into the page.

    Returns {title, byline, content, length} where content is sanitised
    HTML safe to drop into innerHTML."""
    from bs4 import BeautifulSoup
    import bleach

    soup = BeautifulSoup(html or "", "lxml")

    # Title: prefer og:title, then <title>.
    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title and soup.title:
        title = (soup.title.get_text() or "").strip()

    # Byline: try common author meta tags.
    byline = ""
    for sel in (
        ("meta", {"name": "author"}),
        ("meta", {"property": "article:author"}),
    ):
        tag = soup.find(*sel)
        if tag and tag.get("content"):
            byline = tag["content"].strip()
            break

    # Strip stuff that's never article content. Removed in-place so the
    # remaining tree only has body-ish elements when we look for the
    # main container below.
    for tag_name in (
        "script", "style", "noscript", "iframe", "form", "button",
        "nav", "aside", "footer", "header", "menu",
    ):
        for tag in soup.find_all(tag_name):
            tag.decompose()
    # Strip elements with role="navigation" / "banner" / "contentinfo".
    for tag in soup.find_all(attrs={"role": ["navigation", "banner", "contentinfo"]}):
        tag.decompose()

    # Find the densest text container. <article> is the canonical hint;
    # fall back to <main>, then to whichever <div> has the most direct
    # paragraph text.
    container = soup.find("article") or soup.find("main")
    if not container:
        candidates = []
        for div in soup.find_all(["div", "section"]):
            text = div.get_text(" ", strip=True)
            if len(text) > 200:
                candidates.append((len(text), div))
        if candidates:
            candidates.sort(reverse=True)
            container = candidates[0][1]
    if not container:
        container = soup.body or soup

    # Sanitise — keep only readable tags + safe attrs.
    raw = str(container)
    allowed_tags = [
        "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
        "a", "ul", "ol", "li", "blockquote", "pre", "code",
        "em", "strong", "i", "b", "u", "s",
        "img", "figure", "figcaption",
        "table", "thead", "tbody", "tr", "th", "td",
        "div", "span",
    ]
    allowed_attrs = {
        "*": ["class"],
        "a": ["href", "title", "rel", "target"],
        "img": ["src", "alt", "width", "height"],
    }
    cleaned = bleach.clean(
        raw,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )
    # Force every link to open in a new tab — we're showing a remote
    # article inline, links should not nuke the planner page.
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[bleach.callbacks.target_blank, bleach.callbacks.nofollow],
        skip_tags=["pre", "code"],
    )

    return {
        "title": title,
        "byline": byline,
        "content": cleaned,
        "length": len(cleaned),
    }


@inbox_bp.route("/api/inbox/<item_id>/move-to-travel", methods=["POST"])
@login_required
def move_to_travel(item_id):
    """Copy an inbox item into travel_reads, then soft-delete the inbox row.
    Per project policy (no hard delete), the original is marked done so
    the user can still find it via the Done filter if they regret it."""
    user_id = session["user_id"]

    rows = get("inbox_links", params={
        "id": f"eq.{item_id}",
        "user_id": f"eq.{user_id}",
        "select": "id,url,title,description,content_type,category",
    }) or []
    if not rows:
        return jsonify({"error": "not found"}), 404

    src = rows[0]
    url = src.get("url") or ""
    if not url:
        return jsonify({"error": "saved row has no url"}), 422

    # Map inbox content_type → travel_reads kind. Inbox uses "video" for
    # YouTube already; everything else collapses to "article".
    kind = "video" if (src.get("content_type") or "").lower() == "video" else "article"
    domain = ""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).hostname or ""
        domain = domain.replace("www.", "")
    except Exception:
        pass

    # If it's a YouTube URL, fetch real duration so the queue total is
    # accurate without the user having to type a number.
    duration_minutes = None
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        vid = _yt_extract_id(url)
        if vid:
            try:
                r = http_requests.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"id": vid, "part": "contentDetails", "key": api_key},
                    timeout=6,
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if items:
                        secs = _yt_parse_duration(
                            items[0].get("contentDetails", {}).get("duration", "")
                        )
                        if secs:
                            duration_minutes = max(1, round(secs / 60))
            except Exception:
                pass

    travel_row = {
        "user_id": user_id,
        "url": url,
        "title": (src.get("title") or url)[:240],
        "description": (src.get("description") or "")[:600],
        "source": domain,
        "kind": kind,
        "priority": "medium",
        "status": "queued",
    }
    if duration_minutes:
        travel_row["duration_minutes"] = duration_minutes

    try:
        post("travel_reads", travel_row)
    except Exception as e:
        logger.warning("move_to_travel insert failed: %s", e)
        return jsonify({"error": "Could not add to TravelReads"}), 500

    # Soft-delete: mark Done in inbox so it disappears from the default
    # "Unread" filter but is still recoverable via the Done filter.
    update(
        "inbox_links",
        params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
        json={"status": "Done"},
    )
    return jsonify({"success": True, "kind": kind, "duration_minutes": duration_minutes})


@inbox_bp.route("/api/inbox/channel-uploads", methods=["GET"])
@login_required
def channel_uploads():
    """List recent uploads from a YouTube channel, given either the
    channel's id (cheaper, 2 calls) or a video id from that channel
    (3 calls — first looks up the channel from the video).

    Returns the same shape as /api/inbox/search results, including
    duration / view count, so the frontend can reuse its render path."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return jsonify({"error": "GOOGLE_API_KEY not set"}), 503

    channel_id = request.args.get("channelId", "").strip()
    video_id = request.args.get("videoId", "").strip()

    # If the caller only knows a video id, look up its channel first.
    if not channel_id and video_id:
        try:
            r = http_requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"id": video_id, "part": "snippet", "key": api_key},
                timeout=6,
            )
            if r.status_code != 200:
                return jsonify({"error": "Could not look up video"}), 502
            items = r.json().get("items", [])
            if not items:
                return jsonify({"error": "video not found"}), 404
            channel_id = items[0]["snippet"].get("channelId", "")
        except Exception as e:
            logger.warning("channel_uploads video lookup failed: %s", e)
            return jsonify({"error": "lookup failed"}), 500

    if not channel_id:
        return jsonify({"error": "channelId or videoId required"}), 400

    try:
        # channels.list → uploads playlist id + channel name + sub count
        r = http_requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "id": channel_id,
                "part": "contentDetails,snippet,statistics",
                "key": api_key,
            },
            timeout=8,
        )
        if r.status_code != 200:
            return jsonify({"error": "channel lookup failed"}), 502
        chans = r.json().get("items", [])
        if not chans:
            return jsonify({"error": "channel not found"}), 404
        chan = chans[0]
        uploads_id = (
            chan.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads", "")
        )
        chan_title = chan.get("snippet", {}).get("title", "")
        chan_thumb = (
            chan.get("snippet", {}).get("thumbnails", {})
                .get("default", {}).get("url", "")
        )
        chan_stats = chan.get("statistics", {}) or {}
        subs = (
            None if chan_stats.get("hiddenSubscriberCount")
            else int(chan_stats.get("subscriberCount", 0) or 0)
        )

        # playlistItems.list → 10 most recent uploads
        r = http_requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params={
                "playlistId": uploads_id,
                "part": "snippet",
                "maxResults": 10,
                "key": api_key,
            },
            timeout=8,
        )
        if r.status_code != 200:
            return jsonify({"error": "uploads lookup failed"}), 502
        uploads = []
        for it in r.json().get("items", []):
            snip = it.get("snippet", {}) or {}
            vid = (snip.get("resourceId") or {}).get("videoId", "")
            if not vid:
                continue
            uploads.append({
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": snip.get("title", ""),
                "description": (snip.get("description") or "")[:200],
                "thumbnail": (snip.get("thumbnails") or {})
                              .get("medium", {}).get("url", ""),
                "channel": chan_title,
                "channel_id": channel_id,
            })

        # Enrich with duration + view count for each. Reuses the same
        # helper the search endpoint uses, so the frontend can render
        # uploads with the exact same component.
        uploads = _yt_enrich(uploads, api_key)
        return jsonify({
            "channel": {
                "id": channel_id,
                "title": chan_title,
                "thumbnail": chan_thumb,
                "subscriber_count": subs,
            },
            "uploads": uploads,
        })
    except Exception as e:
        logger.warning("channel_uploads exception: %s", e)
        return jsonify({"error": f"failed: {e}"}), 500


@inbox_bp.route("/api/inbox/preview", methods=["GET"])
@login_required
def inbox_preview():
    """Server-side reader-mode for an article URL. Fetches the page,
    extracts the main content with BeautifulSoup heuristics, sanitises
    with bleach, and returns clean HTML the frontend can drop inline.

    Used by the Inbox "Read" button so users can read articles without
    leaving the planner — and works for sites that block iframe
    embedding via X-Frame-Options."""
    url = request.args.get("url", "").strip()
    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "valid URL required"}), 400

    try:
        r = http_requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DailyPlanner/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            allow_redirects=True,
        )
        if r.status_code >= 400:
            logger.warning("inbox_preview fetch %s: http=%s", url, r.status_code)
            return jsonify({"error": f"Source returned {r.status_code}"}), 502
        # Cap response size so a giant page can't blow up the parser.
        html = r.text[:1_000_000]
        result = _extract_readable_html(html)
        if not result.get("content") or result["length"] < 100:
            return jsonify({"error": "Could not extract readable content"}), 422
        return jsonify(result)
    except Exception as e:
        logger.warning("inbox_preview exception %s: %s", url, e)
        return jsonify({"error": f"Fetch failed: {e}"}), 500


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
        # Enrich with duration / view count / subscriber count so the
        # frontend can show "5:42 · 2.1M views · 240K subs" and the
        # user can decide whether to add or skip.
        results = _yt_enrich(results, api_key)
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

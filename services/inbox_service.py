import re
import os
import requests
import logging
from html.parser import HTMLParser

logger = logging.getLogger("daily_plan")


# ── HTML parser for title + meta description ──────────────────────────────────

class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta":
            attr_dict = dict(attrs)
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "")
            if name in ("description",) or prop in ("og:description",):
                if not self.description:
                    self.description = content
            if prop == "og:title" and not self.title:
                self.title = content

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title += data


_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def _extract_youtube_id(url: str) -> str | None:
    """Pull the 11-char video id out of any common YouTube URL form."""
    m = _YT_ID_RE.search(url or "")
    return m.group(1) if m else None


def _fetch_youtube_via_api(video_id: str) -> dict | None:
    """Hit the YouTube Data API for the real title + description + channel.
    Returns None if the API key is missing or the call fails — callers fall
    back to HTML scraping. The API gives the full uploader-written
    description, which the public HTML never serves until JavaScript runs."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"id": video_id, "part": "snippet", "key": api_key},
            timeout=6,
        )
        if r.status_code != 200:
            logger.warning(
                "fetch_meta YouTube API non-200: video_id=%s http=%s body=%r",
                video_id, r.status_code, r.text[:300],
            )
            return None
        items = r.json().get("items") or []
        if not items:
            return None
        snip = items[0].get("snippet") or {}
        title = snip.get("title") or ""
        desc = snip.get("description") or ""
        channel = snip.get("channelTitle") or ""
        published_at = snip.get("publishedAt") or ""
        # Compose a one-line description: first non-empty paragraph, with
        # the channel name prepended for context. YouTube uploader
        # descriptions are often paragraphs of links — we want the first
        # readable sentence.
        first_para = next((p.strip() for p in desc.split("\n\n") if p.strip()), "")
        composed = f"[{channel}] {first_para}".strip() if channel else first_para
        return {
            "title": title or video_id,
            "description": composed[:500],
            "published_at": published_at,
        }
    except Exception as e:
        logger.warning("fetch_meta YouTube API failed: video_id=%s err=%s", video_id, e)
        return None


def fetch_meta(url: str) -> dict:
    """Returns {title, description} fetched from the page.

    YouTube URLs go through the Data API first because their HTML doesn't
    include the real description (it's hydrated client-side). Everything
    else uses an HTML meta scrape with og:title/og:description/<title>."""
    yt_id = _extract_youtube_id(url)
    if yt_id:
        yt_meta = _fetch_youtube_via_api(yt_id)
        if yt_meta and (yt_meta.get("title") or yt_meta.get("description")):
            return yt_meta
        # Fall through to HTML scrape if API miss.

    try:
        r = requests.get(
            url, timeout=6,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        parser = _MetaParser()
        parser.feed(r.text[:8192])
        return {
            "title": parser.title.strip() or url,
            "description": parser.description.strip()[:300],
            "published_at": "",
        }
    except Exception as e:
        logger.warning("fetch_meta failed for %s: %s", url, e)
        return {"title": url, "description": "", "published_at": ""}


# kept for backward compat
def fetch_title(url: str) -> str:
    return fetch_meta(url)["title"]


# ── Content type detection ────────────────────────────────────────────────────

_TYPE_PATTERNS = [
    (r"youtube\.com|youtu\.be", "video"),
    (r"github\.com|gitlab\.com|bitbucket\.org", "code"),
    (r"twitter\.com|x\.com|linkedin\.com", "social"),
    (r"reddit\.com", "social"),
    (r"medium\.com|substack\.com|dev\.to|hashnode|blogger\.com|wordpress\.com", "article"),
    (r"\.(pdf)($|\?)", "pdf"),
    (r"\.(png|jpg|jpeg|gif|webp|svg)($|\?)", "image"),
    (r"docs\.|documentation\.|readthedocs\.", "docs"),
    (r"stackoverflow\.com|stackexchange\.com", "q&a"),
    (r"coursera\.org|udemy\.com|pluralsight\.com|edx\.org|khanacademy", "course"),
]

def detect_type(url: str) -> str:
    for pattern, content_type in _TYPE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return content_type
    return "link"


# ── Auto-categorisation ───────────────────────────────────────────────────────

_CATEGORY_URL_PATTERNS = [
    (r"youtube\.com|youtu\.be|vimeo\.com|twitch\.tv", "Entertainment"),
    (r"github\.com|gitlab\.com|stackoverflow\.com|dev\.to|hashnode|replit", "Programming"),
    (r"arxiv\.org|paperswithcode|huggingface\.co|openai\.com|anthropic\.com|deepmind|gemini|groq\.com", "AI / ML"),
    (r"moneycontrol|zerodha|groww|etmoney|economictimes|bloomberg|wsj\.com|finance\.yahoo|investopedia", "Finance"),
    (r"healthline|webmd|mayoclinic|pubmed|medscape|nih\.gov", "Health"),
    (r"coursera|udemy|edx|khanacademy|pluralsight|skillshare|leetcode|hackerrank", "Learning"),
    (r"producthunt\.com|alternativeto|techcrunch|theverge|wired\.com|ycombinator|news\.ycombinator", "Tech News"),
    (r"figma\.com|dribbble\.com|behance\.net|awwwards|css-tricks", "Design"),
    (r"notion\.so|airtable\.com|trello\.com|asana\.com|linear\.app|clickup", "Productivity"),
    (r"amazon\.|flipkart\.|myntra\.|meesho\.", "Shopping"),
]

def _categorize_by_url(url: str) -> str | None:
    for pattern, category in _CATEGORY_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return category
    return None


def auto_categorize(url: str, title: str, description: str) -> str:
    # Fast path: URL pattern match
    category = _categorize_by_url(url)
    if category:
        return category

    # Slow path: ask Groq
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        return "Uncategorized"

    prompt = f"""Classify this link into exactly ONE category from this list:
AI / ML, Programming, Finance, Health, Learning, Tech News, Design, Productivity, Entertainment, Science, Business, Shopping, Other

URL: {url}
Title: {title}
Description: {description}

Reply with only the category name, nothing else."""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10,
            },
            timeout=8,
        )
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"].strip()
            return result if result else "Uncategorized"
    except Exception as e:
        logger.warning("auto_categorize Groq call failed: %s", e)

    return "Uncategorized"


def generate_summary(description: str) -> str:
    return description.strip()[:500] if description else ""

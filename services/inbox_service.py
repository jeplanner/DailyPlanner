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


_ISO_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_iso_duration(iso: str) -> int:
    """ISO 8601 duration ('PT1H23M45S') → total seconds. Returns 0 for
    unparseable input rather than raising — duration is decorative."""
    if not iso or not iso.startswith("PT"):
        return 0
    m = _ISO_DURATION_RE.match(iso)
    if not m:
        return 0
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s


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
            params={
                "id": video_id,
                "part": "snippet,contentDetails",
                "key": api_key,
            },
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
        item0 = items[0]
        snip = item0.get("snippet") or {}
        title = snip.get("title") or ""
        desc = snip.get("description") or ""
        channel = snip.get("channelTitle") or ""
        published_at = snip.get("publishedAt") or ""
        duration_iso = (item0.get("contentDetails") or {}).get("duration", "")
        duration_seconds = _parse_iso_duration(duration_iso)
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
            "duration_seconds": duration_seconds,
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
            "duration_seconds": 0,
        }
    except Exception as e:
        logger.warning("fetch_meta failed for %s: %s", url, e)
        return {
            "title": url, "description": "",
            "published_at": "", "duration_seconds": 0,
        }


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


# ── Drive-mode label heuristics ───────────────────────────────────────────────
# Small fixed vocabulary the UI suggests on save. The user can toggle
# any of these on/off after the fact — these are seed values, not gospel.
#
#   drivable  🎧  audio-only safe (talks, podcasts, lectures)
#   visual    👀  needs the screen (code, demos, diagrams)
#   quick     ⚡  ≤10 min — fits a coffee break
#   long      🕐  ≥30 min — needs a real slot
#   priority  ⭐  user-only, never auto-set

_LABEL_DRIVABLE = "drivable"
_LABEL_VISUAL = "visual"
_LABEL_QUICK = "quick"
_LABEL_LONG = "long"

KNOWN_LABELS = {_LABEL_DRIVABLE, _LABEL_VISUAL, _LABEL_QUICK, _LABEL_LONG, "priority"}

# Title/description keywords that strongly suggest "I can listen while
# driving with the screen off". Compiled once at import.
_DRIVABLE_HINTS = re.compile(
    r"\b(podcast|interview|fireside|keynote|lecture|talk|conversation|"
    r"discussion|panel|debate|ama|episode|\bep\.?\s*\d|history of|story of|"
    r"explained|deep[\s-]?dive|q&a|narrative|memoir)\b",
    re.IGNORECASE,
)

# Counter-signals: the content needs you to look at the screen. These
# beat the drivable hints when both are present.
_VISUAL_HINTS = re.compile(
    r"\b(tutorial|walkthrough|demo|hands[\s-]?on|step[\s-]?by[\s-]?step|"
    r"build (?:a|an|with)|let'?s build|coding|code review|live[\s-]?coding|"
    r"how to (?:make|build|design|create|use)|screencast|screen[\s-]?cap|"
    r"diagram|whiteboard|figma|design (?:review|critique)|ui|dashboard)\b",
    re.IGNORECASE,
)

# Domains that are essentially audio-only (Spotify pages, podcast hosts).
_DRIVABLE_DOMAINS = re.compile(
    r"(open\.spotify\.com|podcasts\.apple\.com|soundcloud\.com|"
    r"overcast\.fm|pca\.st|anchor\.fm|simplecast\.com|libsyn\.com|"
    r"acast\.com|stitcher\.com|player\.fm)",
    re.IGNORECASE,
)


def auto_label(
    url: str,
    title: str,
    description: str,
    content_type: str = "",
    duration_seconds: int = 0,
) -> list[str]:
    """Suggest an initial set of labels for a freshly-saved item.

    Returns a sorted, de-duplicated list. Empty list is fine — better
    to under-label than to mis-label, since the user fixes labels by
    toggling chips. Heuristic priority:
      1. Length tag from duration (quick / long), if known.
      2. Drivable / visual mode from URL, content type, and keyword
         match in title+description. Visual hints win over drivable
         hints when both fire (a "podcast about UI design" with a
         demo segment is still a screen activity).
    """
    out: set[str] = set()
    haystack = f"{title or ''}\n{description or ''}"

    # Length — only emit when we actually know it.
    if duration_seconds:
        if duration_seconds <= 600:
            out.add(_LABEL_QUICK)
        elif duration_seconds >= 1800:
            out.add(_LABEL_LONG)

    # Mode — start with the most specific signal (audio-only domains)
    # then fall back to keyword scans.
    is_audio_domain = bool(_DRIVABLE_DOMAINS.search(url or ""))
    visual_hit = bool(_VISUAL_HINTS.search(haystack))
    drivable_hit = bool(_DRIVABLE_HINTS.search(haystack))

    if is_audio_domain and not visual_hit:
        out.add(_LABEL_DRIVABLE)
    elif (content_type or "").lower() == "podcast":
        out.add(_LABEL_DRIVABLE)
    elif visual_hit:
        out.add(_LABEL_VISUAL)
    elif drivable_hit:
        out.add(_LABEL_DRIVABLE)
    # Otherwise: leave mode unlabelled. The user can tag it.

    return sorted(out)

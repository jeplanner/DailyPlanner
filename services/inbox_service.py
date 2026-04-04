import re
import requests
from html.parser import HTMLParser


class _TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch_title(url: str) -> str:
    try:
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        parser = _TitleParser()
        parser.feed(r.text[:4096])
        return parser.title.strip() or url
    except Exception:
        return url


_TYPE_PATTERNS = [
    (r"youtube\.com|youtu\.be", "video"),
    (r"github\.com", "code"),
    (r"twitter\.com|x\.com", "social"),
    (r"reddit\.com", "social"),
    (r"medium\.com|substack\.com|dev\.to|hashnode", "article"),
    (r"\.(pdf)$", "pdf"),
    (r"\.(png|jpg|jpeg|gif|webp|svg)$", "image"),
]


def detect_type(url: str) -> str:
    for pattern, content_type in _TYPE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return content_type
    return "link"


def generate_summary(description: str) -> str:
    return description.strip()[:500] if description else ""

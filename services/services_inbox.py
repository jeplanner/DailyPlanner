import requests
from bs4 import BeautifulSoup

def detect_type(url):
    if "youtube" in url:
        return "youtube"
    if "news" in url:
        return "news"
    if "blog" in url or "medium" in url:
        return "blog"
    return "other"


def fetch_title(url):
    try:
        html = requests.get(url, timeout=3).text
        soup = BeautifulSoup(html, "html.parser")
        return soup.title.string if soup.title else ""
    except:
        return ""


def generate_summary(text):
    if not text:
        return ""
    return text[:150]   # later replace with AI
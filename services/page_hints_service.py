"""Highlights with hints on any page: the short answers.

A hint is a conversation about one highlighted passage (or, with no quote,
about the page). Each turn is answered in a background thread by the same
AI providers Random thoughts uses (Claude, then Gemini, then Groq), with
short-hint instructions instead of the full 8-section answer format.
"""
import logging
import threading
from datetime import datetime, timezone

from services import thoughts_service as ts
from supabase_client import get, update

logger = logging.getLogger(__name__)

TABLE = "page_hints"
MIGRATION = "MIGRATION_PAGE_HINTS.sql"
MAX_QUESTION = 1500
MAX_CONTEXT = 8000
MAX_TURNS = 30

HINT_SYSTEM = """You are a patient tutor and assistant inside a personal \
planner app. The reader highlighted a passage on a page (or asked about the \
page as a whole) and asked a question. Your reply is saved as a HINT and \
re-read later, so:
- Answer the question directly in the first sentence.
- Then explain in plain words: short sentences, define any term you use, and \
give one small concrete example if it helps.
- Stay consistent with the page text you are given; if the question goes \
beyond it, answer from general knowledge and say so in a few words.
- For a follow-up, build on the earlier turns instead of repeating them.
- 60 to 200 words. Markdown is fine (short bullet lists, **bold**, `code`). \
No headings, no tables, no diagrams."""


def audience(page):
    page = page or ""
    if page.startswith("/ai-sde"):
        return "The reader is a final-year student preparing for campus SDE / ML interviews; keep it simple."
    if page.startswith(("/interview-prep", "/tpm-rounds")):
        return "The reader is a senior engineering leader preparing for Director-level interviews."
    if page.startswith(("/java", "/sql")):
        return "The reader is learning this for coding interviews; be precise and show tiny code where it helps."
    return "The reader is using their own planner; answer for a capable adult."


def _now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(s, limit):
    return " ".join(str(s or "").split())[:limit]


def build_prompt(page, quote, context, thread):
    parts = []
    if context:
        parts.append("THE PAGE TEXT AROUND IT (for context):\n" + context[:MAX_CONTEXT])
    if quote:
        parts.append("THE HIGHLIGHTED PASSAGE:\n“" + quote + "”")
    else:
        parts.append("(No passage was highlighted: the question is about this page, " + page + ".)")
    earlier = [t for t in thread[:-1] if t.get("a")]
    if earlier:
        parts.append("EARLIER IN THIS HINT:\n" + "\n\n".join(
            "Q: " + t.get("q", "") + "\nA: " + t.get("a", "") for t in earlier[-6:]))
    parts.append("THE QUESTION" + (" (a follow-up)" if earlier else "") + ":\n" + thread[-1].get("q", ""))
    return "\n\n".join(parts)


def generate(page, quote, context, thread):
    prompt = build_prompt(page, quote, context, thread)
    system = HINT_SYSTEM + "\n" + audience(page)
    for fn in ts.PROVIDERS:
        try:
            text, model = fn(prompt, (), system=system)
        except Exception:
            logger.warning("page hints: %s failed", fn.__name__, exc_info=True)
            continue
        if text and text.strip():
            return text.strip(), model
    return None, None


def answer_in_background(hint_id, user_id, page, quote, context, turn_index):
    """Answer thread[turn_index] of one hint and save it back."""
    def run():
        where = {"id": f"eq.{hint_id}", "user_id": f"eq.{user_id}"}
        try:
            rows = get(TABLE, params=dict(where, select="thread", limit="1")) or []
            thread = (rows[0].get("thread") if rows else None) or []
            if turn_index >= len(thread):
                return
            text, model = generate(page, quote, context, thread[: turn_index + 1])
            turn = dict(thread[turn_index])
            if text:
                turn.update(a=text, status="ready", model=model, error=None)
            else:
                turn.update(status="failed", error=(
                    "No AI provider answered. Check ANTHROPIC_API_KEY, GOOGLE_API_KEY or "
                    "GROQ_API_KEY on the server, then tap Try again." if ts.any_provider() else
                    "No AI provider is configured on the server (ANTHROPIC_API_KEY, "
                    "GOOGLE_API_KEY or GROQ_API_KEY)."))
        except Exception as exc:
            logger.exception("page hints: generation crashed")
            turn = {"q": "", "status": "failed", "error": f"Generation failed: {str(exc)[:200]}"}
            rows = get(TABLE, params=dict(where, select="thread", limit="1")) or []
            thread = (rows[0].get("thread") if rows else None) or []
            if turn_index < len(thread):
                turn = dict(thread[turn_index], status="failed", error=turn["error"])
        try:
            # Re-read: the reader may have asked another follow-up meanwhile.
            rows = get(TABLE, params=dict(where, select="thread", limit="1")) or []
            latest = (rows[0].get("thread") if rows else None) or []
            if turn_index < len(latest):
                latest[turn_index] = turn
                update(TABLE, params=where, json={"thread": latest, "updated_at": _now()})
        except Exception:
            logger.exception("page hints: could not save the answer for %s", hint_id)

    t = threading.Thread(target=run, name=f"hint-{hint_id}", daemon=True)
    t.start()
    return t

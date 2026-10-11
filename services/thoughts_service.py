"""Random thoughts: questions that come to mind during interview prep,
answered in depth so they can be understood, not just looked up.

A question is saved first (status "pending"), then answered in a background
thread and the row updated ("ready" or "failed"). A detailed answer can take
30-90 seconds to generate, which is longer than a web request should be
held open, so the page polls instead of waiting.

Providers, best first, each used only if its key is set:
  ANTHROPIC_API_KEY -> Claude (THOUGHTS_ANTHROPIC_MODEL, default claude-sonnet-5-5)
  GOOGLE_API_KEY    -> Gemini (THOUGHTS_GEMINI_MODEL, default gemini-2.0-flash)
  GROQ_API_KEY      -> Llama 3.3 70B on Groq (THOUGHTS_GROQ_MODEL)
Each is asked for a long answer; the existing ai_service caps Groq at 1,024
tokens, which is far too short for this.
"""
import logging
import os
import threading
from datetime import datetime, timezone

import requests

from supabase_client import get, update

logger = logging.getLogger("daily_plan")

TABLE = "prep_thoughts"
MIGRATION = "MIGRATION_PREP_THOUGHTS.sql"
MAX_QUESTION = 2000
MAX_CONTEXT = 4000

SYSTEM = """You are a patient, expert tutor for a senior engineering leader \
(a Senior Engineering Manager at a large Indian e-commerce company, preparing \
for Director of Engineering and Director/VP of Technical Program Management \
interviews). He writes down questions that come to mind while preparing. Your \
job is to make him genuinely UNDERSTAND the answer, not just know it.

Write the answer in Markdown with exactly these sections, in this order:

## The short answer
Two to four sentences that directly answer the question.

## The intuition
Explain the core idea in plain English with an everyday analogy. Assume he is \
smart but may not know this specific topic. Define every technical term the \
first time you use it.

## How it actually works
Step by step, in depth. Use numbered steps or sub-headings. Include the real \
mechanics, numbers and trade-offs. If a picture helps, draw a small ASCII \
diagram inside a ``` code block (under 70 characters wide).

## A worked example
A concrete, realistic example - from large-scale e-commerce, payments, \
logistics or a well-known tech company where it fits - walked through end to end.

## Common misconceptions
Three to five things people commonly get wrong, each with the correction.

## How to say it in an interview
A short, confident spoken answer (60-90 seconds) at Director level, plus the \
follow-up questions an interviewer is likely to ask and how to answer them.

## Key takeaways
Five to eight bullets worth remembering.

## Check yourself
Three questions to test understanding, each followed by its answer on the \
next line starting with "Answer:".

Be accurate. If something is uncertain, debated or depends on context, say \
so plainly. Prefer clarity over jargon. Use **bold** for the few phrases that \
matter most. Do not add any preamble before the first section."""

FOLLOW_UP_HINT = """This is a FOLLOW-UP to an earlier question. The earlier \
question and answer are given for context. Answer the follow-up itself, \
building on what was already explained rather than repeating it. Use the same \
section structure, but keep sections short where the earlier answer already \
covered the ground."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _prompt(question, context, parent):
    parts = []
    if parent:
        parts.append(FOLLOW_UP_HINT)
        parts.append("EARLIER QUESTION:\n" + (parent.get("question") or ""))
        parts.append("EARLIER ANSWER:\n" + (parent.get("answer") or "")[:12000])
    if context:
        parts.append("WHAT PROMPTED THE QUESTION (his own note):\n" + context)
    parts.append("THE QUESTION:\n" + question)
    return "\n\n".join(parts)


def _anthropic(prompt):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_ANTHROPIC_MODEL", "claude-sonnet-5-5")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 8000, "system": SYSTEM,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=180,
    )
    if r.status_code != 200:
        logger.warning("thoughts: anthropic %s %s", r.status_code, r.text[:300])
        return None, None
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return (text or None), model


def _gemini(prompt):
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_GEMINI_MODEL", "gemini-2.0-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={"systemInstruction": {"parts": [{"text": SYSTEM}]},
              "contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.4}},
        timeout=120,
    )
    if r.status_code != 200:
        logger.warning("thoughts: gemini %s %s", r.status_code, r.text[:300])
        return None, None
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        return ("".join(p.get("text", "") for p in parts) or None), model
    except Exception:
        return None, None


def _groq(prompt):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_GROQ_MODEL", "llama-3.3-70b-versatile")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0.4, "max_tokens": 6000,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": prompt}]},
        timeout=120,
    )
    if r.status_code != 200:
        logger.warning("thoughts: groq %s %s", r.status_code, r.text[:300])
        return None, None
    try:
        return (r.json()["choices"][0]["message"]["content"] or None), model
    except Exception:
        return None, None


PROVIDERS = (_anthropic, _gemini, _groq)


def any_provider():
    return any(os.getenv(k) for k in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"))


def generate(question, context="", parent=None):
    """(answer, model) from the first provider that answers, else (None, None)."""
    prompt = _prompt(question, context, parent)
    for fn in PROVIDERS:
        try:
            text, model = fn(prompt)
        except Exception:
            logger.warning("thoughts: %s failed", fn.__name__, exc_info=True)
            continue
        if text and text.strip():
            return text.strip(), model
    return None, None


def answer_in_background(row_id, user_id, question, context="", parent=None):
    """Answer one saved question and write the result back to its row."""
    def run():
        try:
            text, model = generate(question, context, parent)
            patch = ({"answer": text, "model": model, "status": "ready", "error": None}
                     if text else
                     {"status": "failed",
                      "error": ("No AI provider answered. Check ANTHROPIC_API_KEY, "
                                "GOOGLE_API_KEY or GROQ_API_KEY on the server, then retry."
                                if any_provider() else
                                "No AI provider is configured on the server "
                                "(ANTHROPIC_API_KEY, GOOGLE_API_KEY or GROQ_API_KEY).")})
        except Exception as exc:
            logger.exception("thoughts: generation crashed")
            patch = {"status": "failed", "error": f"Generation failed: {str(exc)[:200]}"}
        patch["updated_at"] = _now()
        try:
            update(TABLE, params={"id": f"eq.{row_id}", "user_id": f"eq.{user_id}"}, json=patch)
        except Exception:
            logger.exception("thoughts: could not save the answer for %s", row_id)

    t = threading.Thread(target=run, name=f"thought-{row_id}", daemon=True)
    t.start()
    return t


SEED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "prep_thoughts_seed.json")
_seeded = set()          # user ids already checked in this process


def seeds():
    """Questions shipped with the app, already answered (prep_thoughts_seed.json)."""
    try:
        import json
        with open(SEED_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def ensure_seeds(user_id):
    """Add any shipped question this user has never had - checked once per
    process. Looks at deleted rows too, so deleting one keeps it deleted."""
    if user_id in _seeded:
        return 0
    added = 0
    from supabase_client import post
    for sd in seeds():
        have = get(TABLE, {"user_id": f"eq.{user_id}", "question": f"eq.{sd['question']}",
                           "select": "id", "limit": "1"}) or []
        if have:
            continue
        rows = post(TABLE, {"user_id": user_id, "question": sd["question"],
                            "answer": sd["answer"], "status": "ready",
                            "model": "written for you", "tags": sd.get("tags") or []})
        if rows and rows[0].get("id"):
            update(TABLE, params={"id": f"eq.{rows[0]['id']}", "user_id": f"eq.{user_id}"},
                   json={"root_id": rows[0]["id"]})
            added += 1
    _seeded.add(user_id)
    return added


def parent_of(user_id, parent_id):
    rows = get(TABLE, {"id": f"eq.{parent_id}", "user_id": f"eq.{user_id}",
                       "deleted_at": "is.null",
                       "select": "id,question,answer,root_id", "limit": "1"}) or []
    return rows[0] if rows else None

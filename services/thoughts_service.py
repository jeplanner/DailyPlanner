"""Random thoughts: questions that come to mind during interview prep,
answered in depth so they can be understood, not just looked up.

A question is saved first (status "pending"), then answered in a background
thread and the row updated ("ready" or "failed"). A detailed answer can take
30-90 seconds to generate, which is longer than a web request should be
held open, so the page polls instead of waiting.

Providers, best first, each used only if its key is set:
  ANTHROPIC_API_KEY -> Claude (THOUGHTS_ANTHROPIC_MODEL, default claude-sonnet-5-5)
  GOOGLE_API_KEY    -> Gemini (THOUGHTS_GEMINI_MODEL, default gemini-2.5-flash)
  GROQ_API_KEY      -> Llama 3.3 70B on Groq (THOUGHTS_GROQ_MODEL)
Each is asked for a long answer; the existing ai_service caps Groq at 1,024
tokens, which is far too short for this.
"""
import logging
import os
import threading
from datetime import datetime, timezone

import base64

import requests

from supabase_client import SUPABASE_KEY, SUPABASE_URL, get, update

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
mechanics, numbers and trade-offs. Include ONE diagram that makes the idea \
visible, as a Mermaid block:

```mermaid
flowchart LR
  A[Checkout] -->|OrderPlaced| B[(Kafka)]
  B --> C[Inventory]
```

Use flowchart (LR or TD) for architecture and flows, or sequenceDiagram for \
interactions over time. Keep it under 15 nodes, use short plain labels \
(letters, digits, spaces and simple punctuation; no quotes, parentheses or \
semicolons inside labels), and put the code block on its own lines.

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

If images are attached (his whiteboard sketches, screenshots or diagrams), \
look at them carefully, refer to what they show, and correct anything in \
them that is wrong.

Be accurate. If something is uncertain, debated or depends on context, say \
so plainly. Prefer clarity over jargon. Use **bold** for the few phrases that \
matter most. Do not add any preamble before the first section."""

# The AI SDE Prep page has its own Random thoughts shelf, for a final-year
# CS/AI student preparing for new-grad AI/ML SDE interviews. Same answer
# format; a different reader and level.
SYSTEM_STUDENT = (SYSTEM
    .replace("a senior engineering leader \
(a Senior Engineering Manager at a large Indian e-commerce company, preparing \
for Director of Engineering and Director/VP of Technical Program Management \
interviews). He writes down questions that come to mind while preparing. Your \
job is to make him genuinely UNDERSTAND", "a final-year computer science / AI \
student preparing for new-grad AI/ML Software Engineer interviews (Amazon, \
Google and Indian product companies). She writes down questions that come to \
mind while preparing. Your job is to make her genuinely UNDERSTAND")
    .replace("Assume he is", "Assume she is")
    .replace("at Director level", "at the level expected of a strong new-grad SDE")
    .replace("(his whiteboard", "(her whiteboard"))

SHELVES = ("tpm", "aisde")      # Interview Prep, AI SDE Prep
DEFAULT_SHELF = "tpm"


def clean_shelf(value):
    v = str(value or "").strip().lower()
    return v if v in SHELVES else DEFAULT_SHELF


def system_for(shelf):
    return SYSTEM_STUDENT if clean_shelf(shelf) == "aisde" else SYSTEM


# A HINT answers a question about one highlighted passage. It is re-read
# later when the reader taps the highlight, so it is short and plain - not
# the 8-section structure of a full answer.
HINT_SYSTEM = """You are a patient tutor. While reading a study answer, the \
reader highlighted a passage and asked a question about it. Your reply is \
saved as a HINT on that highlight and re-read later, so:
- Answer the question about the highlighted passage directly, in the first \
sentence.
- Then explain in plain words: short sentences, define any term you use, and \
give one small concrete example (an e-commerce or food-delivery app works \
well) if it helps.
- Stay consistent with the study answer you are given.
- 60 to 180 words. Markdown is fine (short bullet lists, **bold** for key \
terms, `code`). No headings, no tables, no diagrams."""

HINT_AUDIENCE = {
    "tpm": "The reader is a senior engineering leader preparing for Director-level interviews.",
    "aisde": "The reader is a final-year student preparing for campus SDE / ML interviews; keep it simple.",
}


def hint_prompt(quote, question, parent):
    parts = []
    if parent:
        parts.append("THE STUDY ANSWER (for context):\n" + (parent.get("answer") or "")[:12000])
    parts.append("THE HIGHLIGHTED PASSAGE:\n\u201c" + (quote or "") + "\u201d")
    parts.append("THE READER'S QUESTION ABOUT IT:\n" + (question or "Explain this part simply."))
    return "\n\n".join(parts)


def clean_highlight(raw):
    """{quote, prefix} from the page -> a bounded dict, or None."""
    if not isinstance(raw, dict):
        return None
    quote = " ".join(str(raw.get("quote") or "").split())[:500]
    if len(quote) < 2:
        return None
    prefix = " ".join(str(raw.get("prefix") or "").split())[-80:]
    return {"quote": quote, "prefix": prefix}


def shelf_missing(exc):
    """True when the database predates the `shelf` column."""
    t = str(exc)
    return "shelf" in t and ("does not exist" in t or "schema cache" in t or "column" in t)


def get_shelved(params, shelf):
    """get() limited to one shelf. Before MIGRATION_PREP_THOUGHTS.sql adds the
    shelf column, the Interview Prep shelf still works (every row is on it);
    the AI SDE shelf raises ShelfNotReady."""
    shelf = clean_shelf(shelf)
    try:
        return get(TABLE, dict(params, shelf=f"eq.{shelf}")) or []
    except Exception as exc:
        if not shelf_missing(exc):
            raise
        if shelf != DEFAULT_SHELF:
            raise ShelfNotReady() from exc
        return get(TABLE, params) or []


class ShelfNotReady(Exception):
    pass


FOLLOW_UP_HINT = """This is a FOLLOW-UP to an earlier question. The earlier \
question and answer are given for context. Answer the follow-up itself, \
building on what was already explained rather than repeating it. Use the same \
section structure, but keep sections short where the earlier answer already \
covered the ground."""


# Reuses the existing `user-photos` bucket (the Photos page's, see
# MIGRATION_USER_PHOTOS.sql) under its own "thoughts/" folder, so no new
# bucket is needed. The Photos page lists from its own table, so these
# never show up there. Its limit is 5 MB per file.
BUCKET = os.getenv("THOUGHTS_BUCKET", "user-photos")
KEY_PREFIX = "thoughts"
MAX_IMAGE = 5 * 1024 * 1024
MAX_IMAGES = 6
IMAGE_MIMES = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
               "image/webp": "webp", "image/gif": "gif"}


def _storage_headers(extra=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    h.update(extra or {})
    return h


def owner_prefix(user_id):
    """Every image key a user may read or delete starts with this."""
    return f"{KEY_PREFIX}/{user_id}/"


def store_image(user_id, data, mime):
    """Upload one image to the private bucket; returns its storage key."""
    import uuid
    key = f"{KEY_PREFIX}/{user_id}/{uuid.uuid4().hex}.{IMAGE_MIMES[mime]}"
    r = requests.post(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}",
                      headers=_storage_headers({"Content-Type": mime, "x-upsert": "false",
                                                "Cache-Control": "public, max-age=31536000, immutable"}),
                      data=data, timeout=60)
    if not r.ok:
        raise RuntimeError(f"storage {r.status_code}: {r.text[:200]}")
    return key


def fetch_image(key):
    """(bytes, content_type) of a stored image, or (None, None)."""
    r = requests.get(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}",
                     headers=_storage_headers(), timeout=60)
    if not r.ok:
        return None, None
    return r.content, r.headers.get("Content-Type") or "application/octet-stream"


def remove_image(key):
    try:
        requests.delete(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}",
                        headers=_storage_headers(), timeout=30)
    except Exception:
        logger.warning("thoughts: could not delete image %s", key)


def _load_images(images):
    """[(mime, base64)] for the images attached to a question, best effort."""
    out = []
    for im in (images or [])[:MAX_IMAGES]:
        data, ctype = fetch_image(im.get("key", ""))
        if data:
            mime = (im.get("mime") or ctype or "image/png").split(";")[0]
            if mime == "image/jpg":
                mime = "image/jpeg"
            out.append((mime, base64.b64encode(data).decode("ascii")))
    return out


def _now():
    return datetime.now(timezone.utc).isoformat()


def _prompt(question, context, parent):
    parts = []
    if parent:
        parts.append(FOLLOW_UP_HINT)
        parts.append("EARLIER QUESTION:\n" + (parent.get("question") or ""))
        parts.append("EARLIER ANSWER:\n" + (parent.get("answer") or "")[:12000])
    if context:
        parts.append("WHAT PROMPTED THE QUESTION (their own note):\n" + context)
    parts.append("THE QUESTION:\n" + question)
    return "\n\n".join(parts)


def _anthropic(prompt, images=(), system=None):
    system = system or SYSTEM
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_ANTHROPIC_MODEL", "claude-sonnet-5-5")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 8000, "system": system,
              "messages": [{"role": "user", "content": [
                  {"type": "image", "source": {"type": "base64", "media_type": m, "data": b}}
                  for m, b in images] + [{"type": "text", "text": prompt}]}]},
        timeout=180,
    )
    if r.status_code != 200:
        logger.warning("thoughts: anthropic %s %s", r.status_code, r.text[:300])
        return None, None
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return (text or None), model


def _gemini(prompt, images=(), system=None):
    system = system or SYSTEM
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_GEMINI_MODEL", "gemini-2.5-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"parts": [{"inline_data": {"mime_type": m, "data": b}}
                                      for m, b in images] + [{"text": prompt}]}],
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


def _groq(prompt, images=(), system=None):
    system = system or SYSTEM
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None, None
    model = os.getenv("THOUGHTS_GROQ_MODEL", "openai/gpt-oss-120b")
    if images:
        # This model reads text only; say so rather than answer as if it saw them.
        prompt += (f"\n\n(Note: {len(images)} image(s) were attached but this model "
                   "cannot see images. Answer from the text, and say that the "
                   "images were not reviewed.)")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0.4, "max_tokens": 6000,
              "messages": [{"role": "system", "content": system},
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


def generate(question, context="", parent=None, images=(), shelf=None, highlight=None):
    """(answer, model) from the first provider that answers, else (None, None).
    `images` is [(mime, base64)] - shown to providers that can see them.
    With `highlight` ({quote, prefix}) it writes a short hint instead."""
    if highlight:
        prompt = hint_prompt(highlight.get("quote"), question, parent)
        system = HINT_SYSTEM + "\n" + HINT_AUDIENCE[clean_shelf(shelf)]
    else:
        prompt = _prompt(question, context, parent)
        system = None
    for fn in PROVIDERS:
        try:
            if system:
                text, model = fn(prompt, images, system=system)
            elif shelf and clean_shelf(shelf) != DEFAULT_SHELF:
                text, model = fn(prompt, images, system=system_for(shelf))
            else:
                text, model = fn(prompt, images) if images else fn(prompt)
        except Exception:
            logger.warning("thoughts: %s failed", fn.__name__, exc_info=True)
            continue
        if text and text.strip():
            return text.strip(), model
    return None, None


def answer_in_background(row_id, user_id, question, context="", parent=None, images=None,
                         shelf=None, highlight=None):
    """Answer one saved question and write the result back to its row.
    `images` is the row's image list ([{key, mime}]); loaded in the thread."""
    def run():
        try:
            loaded = _load_images(images) if images else []
            text, model = generate(question, context, parent, loaded, shelf=shelf,
                                   highlight=highlight)
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
SEED_MODEL = "written for you"


def seeds():
    """Questions shipped with the app, already answered (prep_thoughts_seed.json)."""
    try:
        import json
        with open(SEED_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


# Topics for the shipped answers, in the order they are best studied.
CATEGORIES = [
    ("cs", "CS fundamentals"),
    ("code", "Coding principles and tools"),
    ("db", "Databases and consistency"),
    ("cache", "Caching and performance"),
    ("msg", "Kafka, queues and streaming"),
    ("arch", "Architecture and infrastructure"),
    ("rel", "Reliability and operations"),
    ("sec", "Security and login"),
    ("sd", "System design: classic problems"),
    ("ecom", "System design: e-commerce and payments"),
    ("ml", "AI and ML fundamentals"),
    ("llm", "AI engineering: LLM apps and agents"),
]
_META = None


def seed_meta():
    """question -> {title, category, campus, step, related:[{question, title}]}
    for the shipped answers. Read from prep_thoughts_seed.json once."""
    global _META
    if _META is None:
        all_seeds = seeds()
        titles = {sd["question"]: sd.get("title") or sd["question"] for sd in all_seeds}
        _META = {}
        for sd in all_seeds:
            if "step" not in sd:
                continue
            _META[sd["question"]] = {
                "title": sd.get("title") or sd["question"],
                "category": sd.get("category"),
                "campus": bool(sd.get("campus")),
                "step": sd["step"],
                "related": [{"question": q, "title": titles.get(q, q)}
                            for q in (sd.get("related") or []) if q in titles],
            }
    return _META


QUIZ_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "prep_thoughts_quiz.json")
_QUIZ = None


def quizzes():
    """question -> [{q, options[4], answer, why, level}] for the shipped answers
    ("choose the best answer" scenario questions)."""
    global _QUIZ
    if _QUIZ is None:
        try:
            import json
            with open(QUIZ_FILE, encoding="utf-8") as fh:
                _QUIZ = json.load(fh)
        except Exception:
            _QUIZ = {}
    return _QUIZ


def quiz_for_step(step):
    meta = seed_meta()
    for q, m in meta.items():
        if m["step"] == step:
            return q, quizzes().get(q, [])
    return None, []


def annotate(rows):
    """Add a shipped answer's topic, study step, campus flag and related
    questions to its row (in place). Your own questions are left as they are."""
    meta = seed_meta()
    for r in rows:
        if r.get("parent_id"):
            continue
        m = meta.get(r.get("question") or "")
        if m:
            r.update(m)
            r["quiz_count"] = len(quizzes().get(r["question"], []))
    return rows


# ---- Spaced repetition -------------------------------------------------
# Leitner-style boxes: after each successful recall the next review is further
# away. Marking a question "studied" puts it in box 0 (review tomorrow).
REVIEW_DAYS = (1, 3, 7, 14, 30, 60, 120)
REVIEW_COLS = ("review_stage", "next_review_at", "last_reviewed_at", "review_count")


def next_review(stage, rating, now=None):
    """(new_stage, next_review_at datetime) for a self-rating:
    again = forgot (back to box 0, see it tomorrow), hard = same box again,
    good = next box, easy = skip a box."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone.utc)
    stage = max(0, int(stage or 0))
    if rating == "again":
        stage = 0
    elif rating == "good":
        stage += 1
    elif rating == "easy":
        stage += 2
    elif rating != "hard":
        raise ValueError("rating must be again, hard, good or easy")
    stage = min(stage, len(REVIEW_DAYS) - 1)
    return stage, now + timedelta(days=REVIEW_DAYS[stage])


def review_missing(exc):
    """True when the database predates the spaced-repetition columns."""
    t = str(exc)
    return any(c in t for c in REVIEW_COLS) and ("does not exist" in t or "schema cache" in t or "column" in t)


def seed_shelves(sd):
    """Which shelves a shipped answer goes on (default: Interview Prep only)."""
    return [x for x in (sd.get("shelves") or [DEFAULT_SHELF]) if x in SHELVES]


def ensure_seeds(user_id, shelf=DEFAULT_SHELF):
    """Add any shipped question this user has never had on this shelf - checked
    once per process. Looks at deleted rows too, so deleting one keeps it deleted."""
    shelf = clean_shelf(shelf)
    if (user_id, shelf) in _seeded:
        return 0
    added = 0
    from supabase_client import post
    for sd in seeds():
        if shelf not in seed_shelves(sd):
            continue
        have = get_shelved({"user_id": f"eq.{user_id}", "question": f"eq.{sd['question']}",
                            "select": "id,answer,model,deleted_at", "limit": "1"}, shelf)
        if have:
            # Refresh a shipped answer that was improved later (diagrams were
            # added after the first version) - but only while it is still
            # untouched: an edit sets model to "edited by you".
            h = have[0]
            if (not h.get("deleted_at") and h.get("model") == SEED_MODEL
                    and (h.get("answer") or "") != sd["answer"]):
                update(TABLE, params={"id": f"eq.{h['id']}", "user_id": f"eq.{user_id}"},
                       json={"answer": sd["answer"], "updated_at": _now()})
            continue
        row = {"user_id": user_id, "question": sd["question"],
               "answer": sd["answer"], "status": "ready",
               "model": SEED_MODEL, "tags": sd.get("tags") or []}
        if shelf != DEFAULT_SHELF:
            row["shelf"] = shelf
        rows = post(TABLE, row)
        if rows and rows[0].get("id"):
            update(TABLE, params={"id": f"eq.{rows[0]['id']}", "user_id": f"eq.{user_id}"},
                   json={"root_id": rows[0]["id"]})
            added += 1
    _seeded.add((user_id, shelf))
    return added


def parent_of(user_id, parent_id):
    rows = get(TABLE, {"id": f"eq.{parent_id}", "user_id": f"eq.{user_id}",
                       "deleted_at": "is.null",
                       "select": "id,question,answer,root_id", "limit": "1"}) or []
    return rows[0] if rows else None

import json
import logging
import os
import urllib.parse

import bleach
import requests
from flask import Blueprint, jsonify, render_template, request, session
from bs4 import BeautifulSoup

from services.ai_service import call_gemini
from services.login_service import login_required
from supabase_client import get, post

logger = logging.getLogger("daily_plan")
references_bp = Blueprint("references", __name__)

# ── Constants ──────────────────────────────────────────────────────────────────

ALLOWED_TAGS = ["p", "br", "h1", "h2", "h3", "strong", "em", "ul", "ol", "li", "a"]
ALLOWED_ATTRIBUTES = {"a": ["href", "target", "rel"]}

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"


def _groq_headers():
    return {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY', '')}",
        "Content-Type": "application/json",
    }


# ── Add reference ──────────────────────────────────────────────────────────────

@references_bp.route("/references/add", methods=["POST"])
@login_required
def add_reference():
    data = request.get_json()
    user_id = session["user_id"]

    raw_tags = data.get("tags", [])
    tags = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, dict) and t.get("value"):
                tags.append(t["value"].strip().lower())
            elif isinstance(t, str):
                tags.append(t.strip().lower())
    elif isinstance(raw_tags, str):
        tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
    tags = list(set(tags))

    for tag in tags:
        existing = get("tags", {"user_id": f"eq.{user_id}", "name": f"eq.{tag}"})
        if not existing:
            post("tags", {"user_id": user_id, "name": tag})

    category = data.get("category")
    if not category:
        existing_refs = get("reference_links", {"user_id": f"eq.{user_id}"})
        scores = {}
        for ref in existing_refs:
            ref_cat = ref.get("category")
            for tag in tags:
                if tag in (ref.get("tags") or []) and ref_cat:
                    scores[ref_cat] = scores.get(ref_cat, 0) + 1
        if scores:
            category = max(scores, key=scores.get)
        elif tags:
            category = tags[0].capitalize()
        else:
            category = "Uncategorized"

    clean_description = bleach.clean(
        data.get("description") or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )

    post("reference_links", {
        "user_id": user_id,
        "title": data.get("title"),
        "description": clean_description,
        "url": data.get("url"),
        "tags": tags,
        "category": category,
    })

    return jsonify({"success": True})


# ── List references (page render) ─────────────────────────────────────────────

@references_bp.route("/references")
@login_required
def list_references():
    user_id  = session["user_id"]
    tag      = request.args.get("tag", "").strip().lower()
    category = request.args.get("category", "").strip()

    params = {"user_id": f"eq.{user_id}", "order": "created_at.desc"}
    if tag:
        params["tags"] = f"cs.{{{tag}}}"
    if category:
        params["category"] = f"eq.{category}"

    refs     = get("reference_links", params=params)
    all_refs = get("reference_links", {"user_id": f"eq.{user_id}"})
    categories = sorted({r["category"] for r in all_refs if r.get("category")})

    return render_template("reference.html", references=refs, categories=categories)


# ── List references (API / infinite scroll) ───────────────────────────────────

@references_bp.route("/references/list")
@login_required
def list_references_api():
    user_id  = session["user_id"]
    page     = int(request.args.get("page", 1))
    tags     = request.args.get("tags")
    search   = request.args.get("search")
    sort     = request.args.get("sort", "created_at_desc")
    category = request.args.get("category")
    limit    = 10
    offset   = (page - 1) * limit

    filters = {
        "user_id": f"eq.{user_id}",
        "limit": limit,
        "offset": offset,
        "order": {"created_at_asc": "created_at.asc", "title_asc": "title.asc"}.get(sort, "created_at.desc"),
    }

    and_conditions = []
    if tags:
        tag_or = ",".join(f"tags.cs.{{{t.strip()}}}" for t in tags.split(",") if t.strip())
        if tag_or:
            and_conditions.append(f"or({tag_or})")
    if search:
        and_conditions.append(f"or(title.ilike.%{search}%,description.ilike.%{search}%)")
    if category:
        and_conditions.append(f"category.eq.{category}")
    if and_conditions:
        filters["and"] = f"({','.join(and_conditions)})"

    rows = get("reference_links", filters)
    return jsonify({"items": rows, "has_more": len(rows) == limit})


# ── Tags ──────────────────────────────────────────────────────────────────────

@references_bp.route("/references/tags")
@login_required
def get_tags_with_counts():
    user_id = session["user_id"]
    rows = get("reference_links", {"user_id": f"eq.{user_id}"})

    grouped = {}
    for ref in rows:
        cat = ref.get("category") or "Uncategorized"
        grouped.setdefault(cat, {})
        for tag in (ref.get("tags") or []):
            grouped[cat][tag] = grouped[cat].get(tag, 0) + 1

    return jsonify(grouped)


@references_bp.route("/api/tags")
@login_required
def get_tags():
    user_id = session["user_id"]
    rows = get("tags", {"user_id": f"eq.{user_id}"})
    return jsonify([r["name"] for r in rows])


# ── Metadata fetch ────────────────────────────────────────────────────────────

@references_bp.route("/references/metadata", methods=["POST"])
@login_required
def fetch_metadata():
    data   = request.json
    url    = data.get("url")
    use_ai = data.get("use_ai", True)

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        page = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(page.text, "html.parser")

        # Title — prefer og:title, fall back to <title>
        og_title = soup.find("meta", property="og:title")
        title = (og_title["content"].strip() if og_title and og_title.get("content")
                 else (soup.title.string.strip() if soup.title else url))

        # Meta description — prefer og:description, then name=description
        og_desc = soup.find("meta", property="og:description")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_text = (
            (og_desc["content"].strip()   if og_desc   and og_desc.get("content")   else None)
            or (meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else None)
            or ""
        )

        if not use_ai:
            return jsonify({"title": title, "description": meta_text, "tags": [], "category": None})

        # Ask Groq for description + tags + category in one call
        prompt = f"""You are a knowledge base assistant. Analyze this webpage and return structured JSON.

URL: {url}
Title: {title}
Meta description: {meta_text[:300] if meta_text else "not available"}

Return ONLY valid JSON in this exact format:
{{
  "description": "4-6 sentence explanation of what this page is about, what you can learn from it, and why it is useful. Be specific and informative.",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "category": "one of: Technology, Health, Finance, Learning, AI / ML, Programming, Design, Productivity, Science, Business, Other"
}}

Rules: No markdown, no explanation, raw JSON only."""

        # Tracks why AI fell back so the UI can show a meaningful inline notice
        # ("AI unavailable — fill in manually") instead of an empty card.
        ai_data = {}
        ai_status = "ok"
        ai_error = None
        try:
            resp = requests.post(
                GROQ_URL,
                headers=_groq_headers(),
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                # Strip markdown code fences if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                ai_data = json.loads(content)
            else:
                ai_status = "error"
                ai_error = f"AI service returned {resp.status_code}"
        except requests.Timeout:
            ai_status = "timeout"
            ai_error = "AI service timed out"
            logger.warning("fetch_metadata Groq timeout for %s", url)
        except Exception as e:
            ai_status = "error"
            ai_error = "AI generation failed"
            logger.warning("fetch_metadata Groq call failed: %s", e)

        return jsonify({
            "title": title,
            "description": ai_data.get("description") or meta_text,
            "tags": ai_data.get("tags", []),
            "category": ai_data.get("category"),
            "ai_status": ai_status,
            "ai_error": ai_error,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI Generate (Gemini) ──────────────────────────────────────────────────────

@references_bp.post("/references/ai-generate")
@login_required
def ai_generate_reference():
    query  = request.json.get("query")
    prompt = f"""Generate ONE high-quality web reference for: "{query}"

Return strictly in JSON format:
{{
  "title": "",
  "url": "",
  "description": "",
  "category": "Learning",
  "tags": ["tag1","tag2"]
}}

Use a real public URL. No explanation. JSON only."""

    ai_text = call_gemini(prompt)
    try:
        data = json.loads(ai_text)
    except Exception:
        return jsonify({"error": "AI returned invalid JSON"}), 500

    return jsonify(data)


# ── AI Generate (Groq) ────────────────────────────────────────────────────────

@references_bp.route("/references/ai-generate-groq", methods=["POST"])
@login_required
def ai_generate_groq():
    query = request.get_json().get("query")

    system_prompt = """You are a knowledge reference generator for a personal study library.
Return ONLY valid JSON in this exact format:
{
  "title": "short clear title",
  "description": "Write a study-friendly description in this exact format:\\n\\nWhat it is: [1-2 sentence plain-English explanation]\\n\\nKey concepts: [3-4 bullet points of the most important ideas]\\n\\nWhy it matters: [1 sentence on practical relevance]",
  "tags": ["tag1", "tag2"],
  "category": "Technology | Health | Finance | Learning | AI / ML | Programming | Science | Business | Other",
  "url": "real public URL if known, otherwise null"
}
Rules: No markdown code fences, no extra explanation, only raw JSON."""

    response = requests.post(
        GROQ_URL,
        headers=_groq_headers(),
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.3,
        },
        timeout=15,
    )

    if response.status_code != 200:
        return jsonify({"error": "Groq failed"}), 500

    content = response.json()["choices"][0]["message"]["content"]
    try:
        structured = json.loads(content)
    except Exception:
        return jsonify({"error": "Invalid AI JSON format"}), 500

    if not structured.get("url"):
        structured["url"] = "https://www.google.com/search?q=" + urllib.parse.quote(query)

    structured.setdefault("title", query[:80])
    structured.setdefault("description", "No description generated.")
    structured.setdefault("tags", [])
    structured.setdefault("category", "Learning")

    return jsonify(structured)


# ── Delete reference ──────────────────────────────────────────────────────────

@references_bp.route("/references/<ref_id>", methods=["DELETE"])
@login_required
def delete_reference(ref_id):
    user_id = session["user_id"]
    from supabase_client import delete
    delete("reference_links", params={"id": f"eq.{ref_id}", "user_id": f"eq.{user_id}"})
    return jsonify({"success": True})


# ── Search references ─────────────────────────────────────────────────────────

@references_bp.get("/search_references")
@login_required
def search_references():
    user_id = session["user_id"]
    query   = request.args.get("q", "").strip()

    if not query:
        return jsonify({"results": []})

    rows = get("reference_links", {
        "user_id": f"eq.{user_id}",
        "or": f"(title.ilike.%{query}%,description.ilike.%{query}%)",
    })

    return jsonify({"results": rows})


# ── Study a reference ─────────────────────────────────────────────────────────

@references_bp.post("/references/study")
@login_required
def study_reference():
    user_id = session["user_id"]
    ref_id  = (request.json or {}).get("ref_id")

    if not ref_id:
        return jsonify({"error": "ref_id required"}), 400

    rows = get("reference_links", {
        "id": f"eq.{ref_id}",
        "user_id": f"eq.{user_id}",
        "limit": 1,
    })
    if not rows:
        return jsonify({"error": "Not found"}), 404

    ref = rows[0]
    soup = BeautifulSoup(ref.get("description") or "", "html.parser")
    desc_text = soup.get_text(separator=" ").strip()[:600]

    prompt = f"""You are a study coach using the Feynman technique. Create concise study notes for this topic.

Topic: {ref.get("title", "")}
URL: {ref.get("url", "")}
Description: {desc_text or "Not available"}
Tags: {", ".join(ref.get("tags") or [])}

Respond in this exact markdown format:

## What is it?
[2-3 sentence plain-English explanation for a curious learner]

## Key Concepts
- [Concept 1]
- [Concept 2]
- [Concept 3]

## Real-World Analogy
[One concrete analogy or example that makes the idea click]

## Why It Matters
[1-2 sentences on practical importance or application]

## Test Yourself
1. [Factual question]
2. [Conceptual question]
3. [Application question]

Keep it focused and use simple language. No filler."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers=_groq_headers(),
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            notes = resp.json()["choices"][0]["message"]["content"].strip()
        else:
            return jsonify({"error": "AI unavailable"}), 503
    except Exception as e:
        logger.error("study_reference failed: %s", e)
        return jsonify({"error": "AI service failed"}), 503

    return jsonify({
        "title": ref.get("title"),
        "url": ref.get("url"),
        "notes": notes,
    })


# ── Ask my references (Q&A) ───────────────────────────────────────────────────

@references_bp.post("/references/ask")
@login_required
def ask_references():
    user_id  = session["user_id"]
    question = (request.json.get("question") or "").strip()

    if not question:
        return jsonify({"error": "question required"}), 400

    # Search relevant references by title, description, tags
    keywords = [w for w in question.lower().split() if len(w) > 3][:5]

    candidates = []
    seen_ids = set()

    for kw in keywords:
        rows = get("reference_links", {
            "user_id": f"eq.{user_id}",
            "or": f"(title.ilike.%{kw}%,description.ilike.%{kw}%)",
            "limit": 5,
        }) or []
        for r in rows:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)

    # Fall back: get most recent references if no keyword matches
    if not candidates:
        candidates = get("reference_links", {
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": 10,
        }) or []

    # Cap at 8 references for context window
    sources = candidates[:8]

    if not sources:
        return jsonify({
            "answer": "You have no saved references yet. Add some references first, then ask questions about them.",
            "sources": [],
        })

    # Build context block
    context_lines = []
    for i, ref in enumerate(sources, 1):
        # strip HTML tags from description for clean context
        desc_soup = BeautifulSoup(ref.get("description") or "", "html.parser")
        desc_text = desc_soup.get_text(separator=" ").strip()[:300]
        context_lines.append(
            f"[{i}] {ref.get('title', 'Untitled')}\n"
            f"    URL: {ref.get('url', '')}\n"
            f"    Tags: {', '.join(ref.get('tags') or [])}\n"
            f"    Description: {desc_text}"
        )

    context = "\n\n".join(context_lines)

    prompt = f"""You are a study coach helping a learner understand topics from their personal knowledge base.

References:
{context}

Question: {question}

Answer in this format:

**Answer**
[Direct clear answer. Cite sources as [1], [2] etc.]

**Key Takeaway**
[The single most important thing to remember about this]

**Example or Analogy**
[A concrete real-world example or analogy that makes this stick]

Rules:
- Use simple, clear language.
- Cite using [1], [2] etc.
- If references lack enough info, say so honestly.
- Total response under 280 words."""

    try:
        response = requests.post(
            GROQ_URL,
            headers=_groq_headers(),
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=15,
        )
        if response.status_code == 200:
            answer = response.json()["choices"][0]["message"]["content"].strip()
        else:
            answer = call_gemini(prompt)
    except Exception as e:
        logger.error("ask_references AI call failed: %s", e)
        return jsonify({"error": "AI service unavailable"}), 503

    return jsonify({
        "answer": answer,
        "sources": [
            {"title": r.get("title") or r.get("url"), "url": r.get("url")}
            for r in sources
        ],
    })


# ── Normalize helper (kept for potential future use) ──────────────────────────

def normalize_category(name):
    return name.strip().lower().replace("-", " ").title()

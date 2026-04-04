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
    data    = request.json
    url     = data.get("url")
    use_ai  = data.get("use_ai", True)

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        page  = requests.get(url, timeout=5)
        soup  = BeautifulSoup(page.text, "html.parser")
        title = soup.title.string.strip() if soup.title else None

        if not use_ai:
            return jsonify({"title": title, "tags": [], "category": None})

        prompt = f"""Analyze this webpage title: "{title}"

Return JSON ONLY:
{{
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "Technology"
}}

Category must be one of: Technology, Health, Finance, Learning, AI / ML, Programming, Design, Productivity, Science, Business"""

        ai_response = call_gemini(prompt)
        try:
            ai_data = json.loads(ai_response)
        except Exception:
            ai_data = {}

        return jsonify({
            "title": title,
            "tags": ai_data.get("tags", []),
            "category": ai_data.get("category"),
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

    system_prompt = """You are a knowledge reference generator.
Return ONLY valid JSON in this exact format:
{
  "title": "short clear title",
  "description": "detailed 4-6 sentence explanation",
  "tags": ["tag1", "tag2"],
  "category": "Technology | Health | Finance | Learning",
  "url": "real public URL if known, otherwise null"
}
Rules: No markdown, no explanation, only raw JSON."""

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

    prompt = f"""You are a personal knowledge assistant. Answer the user's question using ONLY the references below.

References:
{context}

Question: {question}

Rules:
- Answer directly and clearly.
- Cite sources using [1], [2] etc.
- If the references don't contain enough info, say so honestly.
- Keep the answer under 200 words."""

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

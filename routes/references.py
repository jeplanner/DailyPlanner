import json
from flask import Blueprint, jsonify, render_template, request, session
import requests
from bs4 import BeautifulSoup
from services.ai_service import call_gemini
from services.login_service import login_required
from supabase_client import get, post
import bleach 
import os
import urllib.parse
references_bp = Blueprint("references", __name__)
@references_bp.route("/references/add", methods=["POST"])
@login_required
def add_reference():

    data = request.get_json()
    user_id = session["user_id"]

    raw_tags = data.get("tags", [])

    # ---------------------------------
    # Normalize Tags
    # ---------------------------------
    tags = []

    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, dict) and t.get("value"):
                tags.append(t["value"].strip().lower())
            elif isinstance(t, str):
                tags.append(t.strip().lower())

    elif isinstance(raw_tags, str):
        tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    # Remove duplicates
    tags = list(set(tags))

    # ---------------------------------
    # Auto-create missing tags
    # ---------------------------------
    for tag in tags:
        existing = get("tags", {
            "user_id": f"eq.{user_id}",
            "name": f"eq.{tag}"
        })

        if not existing:
            post("tags", {
                "user_id": user_id,
                "name": tag
            })

    # ---------------------------------
    # Category Handling
    # ---------------------------------
    category = data.get("category")

    if not category:

        # Fetch existing references
        existing_refs = get("reference_links", {
            "user_id": f"eq.{user_id}"
        })

        tag_category_scores = {}

        for ref in existing_refs:
            ref_category = ref.get("category")
            ref_tags = ref.get("tags", [])

            for tag in tags:
                if tag in ref_tags and ref_category:
                    tag_category_scores[ref_category] = (
                        tag_category_scores.get(ref_category, 0) + 1
                    )

        if tag_category_scores:
            # Pick highest scoring category
            category = max(tag_category_scores, key=tag_category_scores.get)

        elif tags:
            # 🔥 Create new category from strongest tag
            category = tags[0].capitalize()

        else:
            category = "Uncategorized"
    

    ALLOWED_TAGS = [
        "p", "br",
        "h1", "h2", "h3",
        "strong", "em",
        "ul", "ol", "li",
        "a"
    ]

    ALLOWED_ATTRIBUTES = {
        "a": ["href", "target", "rel"]
    }



    raw_description = data.get("description") or ""

    clean_description = bleach.clean(
        raw_description,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    # ---------------------------------
    # Save Reference
    # ---------------------------------
    post("reference_links", {
        "user_id": user_id,
        "title": data.get("title"),
        "description": clean_description,
        "url": data.get("url"),
        "tags": tags,
        "category": category
    })

    return jsonify({"success": True})
@references_bp.route("/references")
@login_required
def list_references():
    user_id = session["user_id"]
    tag = request.args.get("tag", "").strip().lower()
    category = request.args.get("category", "").strip()
    print("🔥 DEBUG /references")
    print("Query Params → tag:", tag)
    print("Query Params → category:", category)
    params = {
        "user_id": f"eq.{user_id}",
        "order": "created_at.desc"
    }

    if tag:
      params["tags"] = f"cs.{{{tag}}}"

    if category:
      params["category"] = f"eq.{category}"
    refs = get("reference_links", params=params)

    all_refs = get("reference_links", {
        "user_id": f"eq.{user_id}"
    })

    categories = sorted(
        list({r["category"] for r in all_refs if r.get("category")})
    )

    return render_template(
        "reference.html",
        references=refs,
        categories=categories
    )

@references_bp.post("/references/ai-generate")
@login_required
def ai_generate_reference():
    user_id = session["user_id"]
    query = request.json.get("query")

    prompt = f"""
    Generate ONE high-quality web reference for: "{query}"

    Return strictly in JSON format:

    {{
      "title": "",
      "url": "",
      "description": "",
      "category": "Learning",
      "tags": ["tag1","tag2"]
    }}

    Use a real public URL.
    No explanation. JSON only.
    """

    ai_text = call_gemini(prompt)

    data = json.loads(ai_text)

    return jsonify(data)


@references_bp.route("/references/metadata", methods=["POST"])
@login_required
def fetch_metadata():

    data = request.json
    url = data.get("url")
    use_ai = data.get("use_ai", True)

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        # Always fetch page title
        page = requests.get(url, timeout=5)
        soup = BeautifulSoup(page.text, "html.parser")
        title = soup.title.string.strip() if soup.title else None

        # If AI disabled → return only title
        if not use_ai:
            return jsonify({
                "title": title,
                "tags": [],
                "category": None
            })

        # AI enabled
        prompt = f"""
        Analyze this webpage title:
        "{title}"

        Return JSON ONLY like this:
        {{
          "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
          "category": "Technology"
        }}

        Category must be one of:
        Technology, Health, Finance, Learning
        """

        ai_response = call_gemini(prompt)

        import json
        ai_data = json.loads(ai_response)

        return jsonify({
            "title": title,
            "tags": ai_data.get("tags", []),
            "category": ai_data.get("category")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@references_bp.route("/references/tags")
@login_required
def get_tags_with_counts():

    user_id = session["user_id"]
    print("🔥 DEBUG /references/tags called")
    rows = get("reference_links", {
        "user_id": f"eq.{user_id}"
    })

    grouped_tags = {}

    for ref in rows:
        category = ref.get("category") or "Uncategorized"
        tags = ref.get("tags", [])

        if category not in grouped_tags:
            grouped_tags[category] = {}

        for tag in tags:
            grouped_tags[category][tag] = (
                grouped_tags[category].get(tag, 0) + 1
            )

    return jsonify(grouped_tags)

@references_bp.route("/references/list")
@login_required
def list_references_api():

    user_id = session["user_id"]
    page = int(request.args.get("page", 1))
    tags = request.args.get("tags")
    search = request.args.get("search")
    sort = request.args.get("sort", "created_at_desc")
    category = request.args.get("category")
    limit = 10
    offset = (page - 1) * limit

    filters = {
        "user_id": f"eq.{user_id}",
        "limit": limit,
        "offset": offset
    }

    # Sorting
    if sort == "created_at_asc":
        filters["order"] = "created_at.asc"
    elif sort == "title_asc":
        filters["order"] = "title.asc"
    else:
        filters["order"] = "created_at.desc"

    and_conditions = []

    # 1️⃣ Multi-tag OR block
    if tags:
        tag_list = tags.split(",")

        tag_or = ",".join([
            f"tags.cs.{{{tag.strip()}}}"
            for tag in tag_list if tag.strip()
        ])

        if tag_or:
            and_conditions.append(f"or({tag_or})")

    # 2️⃣ Search OR block
    if search:
        search_or = f"title.ilike.%{search}%,description.ilike.%{search}%"
        and_conditions.append(f"or({search_or})")
    if category:
     and_conditions.append(f"category.eq.{category}")
    # 3️⃣ Attach combined AND logic
    if and_conditions:
        filters["and"] = f"({','.join(and_conditions)})"
    print("🔥 DEBUG /references/list")
    print("Incoming → tags:", tags)
    print("Incoming → search:", search)
    print("Incoming → sort:", sort)
    print("Final filters →", filters)
    rows = get("reference_links", filters)

    return jsonify({
    "items": rows,
    "has_more": len(rows) == limit
    })

@references_bp.route("/references/ai-generate-groq", methods=["POST"])
@login_required
def ai_generate_groq():


    data = request.get_json()
    query = data.get("query")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    system_prompt = """
        You are a knowledge reference generator.

        Return ONLY valid JSON in this exact format:
        {
        "title": "short clear title",
        "description": "detailed 4-6 sentence explanation",
        "tags": ["tag1", "tag2"],
        "category": "Technology | Health | Finance | Learning",
        "url": "real public URL if known, otherwise null"
        }

        Rules:
        - No markdown
        - No explanation
        - Only raw JSON
        """

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.3
        }
    )

    if response.status_code != 200:
        return jsonify({"error": "Groq failed"}), 500

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    try:
        structured = json.loads(content)
    except Exception:
        return jsonify({"error": "Invalid AI JSON format"}), 500

    # 🔥 Fallback: If no URL, generate Google search link
    if not structured.get("url"):
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        structured["url"] = search_url

    # Safety defaults
    structured["title"] = structured.get("title") or query[:80]
    structured["description"] = structured.get("description") or "No description generated."
    structured["tags"] = structured.get("tags") or []
    structured["category"] = structured.get("category") or "Learning"

    return jsonify(structured)

@references_bp.route("/api/tags")
@login_required
def get_tags():
    user_id = session["user_id"]

    rows = get("tags", {
        "user_id": f"eq.{user_id}"
    })

    tag_list = [row["name"] for row in rows]

    return jsonify(tag_list)


@references_bp.get("/search_references")
def search_references():
    user_id = session["user_id"]
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"results": []})

    rows = get(
        "reference_links",
        {
            "user_id": f"eq.{user_id}",
            "tags": f"ilike.%{query}%"
        }
    )

    return jsonify({"results": rows})

def normalize_category(name):
    return name.strip().lower().replace("-", " ").title()


def process_tags(user_id, tag_list):
    processed_tags = []

    for tag in tag_list:
        tag = tag.strip().lower()

        # check if exists
        existing = get("tags", {
            "user_id": f"eq.{user_id}",
            "name": f"eq.{tag}"
        })

        if existing:
            processed_tags.append(tag)
        else:
            post("tags", {
                "user_id": user_id,
                "name": tag
            })
            processed_tags.append(tag)

    return processed_tags

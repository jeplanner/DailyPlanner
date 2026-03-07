from flask import Blueprint, jsonify, request, session
from services.ai_service import call_gemini
from services.login_service import login_required
from supabase_client import get
ai_bp = Blueprint("ai", __name__)
@ai_bp.post("/ai/reflection-summary")
@login_required
def reflection_summary():
    data = request.get_json(silent=True) or {}
    reflection_text = data.get("reflection", "").strip()

    if not reflection_text:
        return jsonify({"summary": ""})

    reflection_text = reflection_text[:4000]

    prompt = f"""
    Summarize this daily reflection.
    Extract:
    - Key wins
    - Challenges
    - Lessons learned
    - Improvement suggestions

    Reflection:
    {reflection_text}
    """

    try:
        summary = call_gemini(prompt)
    except Exception:
        return jsonify({"error": "AI unavailable"}), 503

    return jsonify({"summary": summary})

@ai_bp.post("/ai/generate-day-plan")
@login_required
def generate_day_plan():
    user_id = session["user_id"]
    plan_date = request.json.get("date")
    print("AI PLAN REQUEST", plan_date)
    user_id = session["user_id"]

    slots = get("daily_slots", {
        "user_id": f"eq.{user_id}",
        "plan_date": f"eq.{plan_date}",
        "select": "slot,plan,priority,category,tags",
        "order": "slot.asc"
    })

    prompt = f"""
        You are an elite productivity planner.

        The user maintains a 30-minute slot based daily planner.

        Each slot represents a time block.

        Today's scheduled tasks:

        {slots}

        Your job:

        1. Identify the most important tasks today.
        2. Suggest 2–3 focused work blocks.
        3. Identify schedule risks or inefficiencies.
        4. Suggest 2 improvements for productivity.

        Rules:
        - Do NOT invent tasks.
        - Only analyze the given schedule.
        - Keep the answer short and practical.
        - Maximum 120 words.
        """

    ai_output = call_gemini(prompt)

    return jsonify({"result": ai_output})

@ai_bp.post("/ai/assistant")
@login_required
def ai_assistant():
    message = request.json.get("message")

    prompt = f"""
    You are a productivity assistant for a Daily Planner app.
    Help the user improve time management.

    User says:
    {message}
    """

    response = call_gemini(prompt)

    return jsonify({"reply": response})
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
    You are a productivity AI assistant.

    Here is today's schedule:
    {slots}

    Generate:
    1. A prioritized plan
    2. Suggested focus blocks
    3. Risk areas
    4. Time optimization suggestions

    Keep it structured and concise.
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
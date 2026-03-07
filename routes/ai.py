from flask import Blueprint, jsonify, request, session
from services.ai_service import call_gemini
from services.login_service import login_required
from supabase_client import get
from openai import OpenAI
import os
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


groq = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1/chat/completions"
)

def call_groq(prompt):

    resp = groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a productivity assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    return resp.choices[0].message.content

@ai_bp.post("/ai/generate-day-plan")
@login_required
def generate_day_plan():

    user_id = session["user_id"]
    plan_date = request.json.get("date")

    print("AI PLAN REQUEST", plan_date)

    slots = get("daily_slots", {
        "user_id": f"eq.{user_id}",
        "plan_date": f"eq.{plan_date}",
        "select": "slot,plan,priority,category,tags",
        "order": "slot.asc"
    })
    schedule = "\n".join(
    f"Slot {s['slot']}: {s.get('plan','')}"
    for s in slots if s.get("plan")
    )
    prompt = f"""
        You are an elite productivity planner.

        The user maintains a 30-minute slot based daily planner.

        Each slot represents a time block.

        Today's scheduled tasks:

        {schedule}

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

    try:
        ai_output = call_gemini(prompt)
        print("AI USED: GEMINI")

    except Exception as e:

        print("Gemini failed → switching to Groq", e)

        try:
            ai_output = call_groq(prompt)
            print("AI USED: GROQ")

        except Exception as e2:

            print("Groq also failed", e2)

            ai_output = "⚠️ AI service temporarily unavailable. Please try again."

    return jsonify({
    "result": ai_output,
    "provider": provider
})

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
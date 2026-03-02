from flask import Blueprint, jsonify, render_template, request, session
from datetime import date, datetime, timedelta
from config import IST
from routes.habits import get_goal_for_date
from supabase_client import get, post
from services.planner_service import compute_health_streak
from app import login_required


health_bp = Blueprint("health", __name__)


# ==========================================================
# WEEKLY HEALTH
# ==========================================================

@health_bp.route("/api/v2/weekly-health")
@login_required
def weekly_health():
    user_id = session["user_id"]

    today = datetime.now(IST).date()
    start = today - timedelta(days=6)

    # Load last 7 days entries
    rows = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start.isoformat()}"
        }
    ) or []

    # Load active habits
    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{today.isoformat()}"
        }
    ) or []

    total = len(habit_defs)
    habit_map = {h["id"]: h for h in habit_defs}

    # Build date map
    date_map = {}
    for r in rows:
        date_map.setdefault(r["plan_date"], []).append(r)

    percentages = []

    for i in range(7):
        day = (start + timedelta(days=i)).isoformat()
        entries = date_map.get(day, [])

        completed = 0

        for e in entries:
            habit = habit_map.get(e["habit_id"])
            if not habit:
                continue

            goal = get_goal_for_date(habit["id"], day)
            value = float(e.get("value") or 0)

            if goal > 0 and value >= goal:
                completed += 1

        percent = round((completed / total) * 100) if total else 0
        percentages.append(percent)

    avg = round(sum(percentages) / len(percentages)) if percentages else 0

    # Best habit
    habit_totals = {}
    for r in rows:
        habit_totals[r["habit_id"]] = (
            habit_totals.get(r["habit_id"], 0)
            + float(r.get("value") or 0)
        )

    best_habit_id = max(habit_totals, key=habit_totals.get) if habit_totals else None
    best_name = habit_map.get(best_habit_id, {}).get("name") if best_habit_id else None

    return jsonify({
        "daily": percentages,
        "weekly_avg": avg,
        "best_habit": best_name
    })


# ==========================================================
# HEALTH DASHBOARD (HTML)
# ==========================================================

@health_bp.route("/health")
@login_required
def health_dashboard():
    user_id = session["user_id"]
    plan_date_str = request.args.get("date")

    plan_date = date.fromisoformat(plan_date_str) if plan_date_str else datetime.now(IST).date()
    plan_date_str = plan_date.isoformat()

    # Daily health
    health_rows = get(
        "daily_health",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}"
        }
    )
    health = health_rows[0] if health_rows else {}

    # Habits
    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{plan_date_str}"
        }
    ) or []

    habit_entries = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}"
        }
    ) or []

    entry_map = {h["habit_id"]: h["value"] for h in habit_entries}

    habit_list = []
    completed = 0

    for h in habit_defs:
        goal = get_goal_for_date(h["id"], plan_date_str)
        value = float(entry_map.get(h["id"], 0) or 0)

        if h.get("habit_type") == "boolean":
            if value == 1:
                completed += 1
        else:
            if goal > 0 and value >= goal:
                completed += 1

        habit_list.append({
            "id": h["id"],
            "name": h["name"],
            "unit": h["unit"],
            "goal": goal,
            "value": value
        })

    total = len(habit_defs)
    habit_percent = round((completed / total) * 100) if total else 0
    health_streak = compute_health_streak(user_id, plan_date)

    return render_template(
        "health_dashboard.html",
        plan_date=plan_date,
        health=health,
        habit_list=habit_list,
        habit_percent=habit_percent,
        health_streak=health_streak
    )


# ==========================================================
# DAILY HEALTH API
# ==========================================================

@health_bp.route("/api/v2/daily-health")
@login_required
def get_daily_health():
    user_id = session["user_id"]
    plan_date = request.args.get("date")

    if not plan_date:
        return jsonify({})

    # Load health
    health_rows = get(
        "daily_health",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}"
        }
    )

    if health_rows:
        health = health_rows[0]
    else:
        prev_rows = get(
            "daily_health",
            {
                "user_id": f"eq.{user_id}",
                "plan_date": f"lt.{plan_date}",
                "order": "plan_date.desc",
                "limit": 1
            }
        )
        health = {
            "goal": prev_rows[0].get("goal") if prev_rows else None,
            "height": prev_rows[0].get("height") if prev_rows else None,
            "weight": prev_rows[0].get("weight") if prev_rows else None
        }

    height = health.get("height")
    weight = health.get("weight")
    bmi = None

    try:
        if height and weight:
            height_m = float(height) / 100
            bmi = round(float(weight) / (height_m * height_m), 1)
    except Exception:
        pass

    # Habits
    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{plan_date}",
            "order": "position.asc"
        }
    ) or []

    habit_entries = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}"
        }
    ) or []

    entry_map = {h["habit_id"]: h["value"] for h in habit_entries}

    habit_list = []
    completed = 0

    for h in habit_defs:
        goal = get_goal_for_date(h["id"], plan_date)
        value = float(entry_map.get(h["id"], 0) or 0)

        if goal > 0 and value >= goal:
            completed += 1

        habit_list.append({
            "id": h["id"],
            "name": h["name"],
            "unit": h["unit"],
            "goal": goal,
            "value": value
        })

    total = len(habit_defs)
    habit_percent = round((completed / total) * 100) if total else 0

    if habit_percent >= 90:
        habit_label = "Excellent"
    elif habit_percent >= 70:
        habit_label = "Good"
    elif habit_percent >= 40:
        habit_label = "Moderate"
    else:
        habit_label = "Needs Work"

    # Weight trend (7 days)
    trend_rows = get(
        "daily_health",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"lte.{plan_date}",
            "order": "plan_date.desc",
            "limit": 30
        }
    ) or []

    weight_map = {r["plan_date"]: float(r["weight"]) for r in trend_rows if r.get("weight")}

    current = date.fromisoformat(plan_date)
    weight_trend = []
    last_weight = None

    for i in range(6, -1, -1):
        d = (current - timedelta(days=i)).isoformat()
        if d in weight_map:
            last_weight = weight_map[d]

        weight_trend.append({"date": d, "weight": last_weight})

    valid_weights = [w["weight"] for w in weight_trend if w["weight"]]
    weekly_change = round(valid_weights[-1] - valid_weights[0], 1) if len(valid_weights) >= 2 else None

    streak = compute_health_streak(user_id, current)

    return jsonify({
        **health,
        "bmi": bmi,
        "habits": habit_list,
        "habit_percent": habit_percent,
        "habit_score": habit_percent,
        "habit_label": habit_label,
        "weight_trend": weight_trend,
        "weekly_change": weekly_change,
        "streak": streak
    })


# ==========================================================
# SAVE DAILY HEALTH
# ==========================================================

@health_bp.route("/api/v2/daily-health", methods=["POST"])
@login_required
def save_daily_health():
    user_id = session["user_id"]
    data = request.json

    plan_date = data.get("plan_date")
    if not plan_date:
        return jsonify({"error": "plan_date required"}), 400

    payload = {
        "user_id": user_id,
        "plan_date": plan_date,
        "weight": clean_number(data.get("weight")),
        "height": clean_number(data.get("height")),
        "mood": data.get("mood"),
        "energy_level": int(data.get("energy_level")) if data.get("energy_level") else None,
        "notes": data.get("notes")
    }

    post("daily_health", payload, prefer="resolution=merge-duplicates")

    return jsonify({"success": True})


# ==========================================================
# SAVE HABIT VALUE
# ==========================================================

@health_bp.route("/api/save-habit-value", methods=["POST"])
@login_required
def save_habit_value():
    user_id = session["user_id"]
    data = request.json

    habit_id = data.get("habit_id")
    plan_date = data.get("plan_date")
    value = clean_number(data.get("value"))

    if not habit_id or not plan_date:
        return jsonify({"error": "Missing data"}), 400

    post(
        "habit_entries?on_conflict=user_id,habit_id,plan_date",
        {
            "user_id": user_id,
            "habit_id": habit_id,
            "plan_date": plan_date,
            "value": value
        },
        prefer="resolution=merge-duplicates"
    )

    return jsonify({"success": True})


# ==========================================================
# UTIL
# ==========================================================

def clean_number(val):
    return float(val) if val not in ("", None) else None
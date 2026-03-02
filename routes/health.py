from flask import Blueprint, jsonify, render_template, request, session
from datetime import date, datetime, timedelta
from config import IST
from routes.habits import get_goal_for_date
from supabase_client import get, post
from services.planner_service import compute_health_streak
from app import login_required  # IMPORTANT: import correctly

health_bp = Blueprint("health", __name__)

@health_bp.route("/api/v2/weekly-health")
@login_required
def weekly_health():
    user_id = session["user_id"]

    today = datetime.now(IST).date()
    start = today - timedelta(days=6)

    # ----------------------------------
    # Load habit entries (last 7 days)
    # ----------------------------------
    rows = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start.isoformat()}",
            "plan_date": f"lte.{today.isoformat()}"
        }
    ) or []

    # ----------------------------------
    # Load active habits
    # ----------------------------------
    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{today.isoformat()}"
        }
    ) or []

    total = len(habit_defs)

    # ----------------------------------
    # Load goal history (single query)
    # ----------------------------------
    if habit_defs:
        habit_ids = ",".join([h["id"] for h in habit_defs])

        goal_rows = get(
            "habit_goal_history",
            {
                "habit_id": f"in.({habit_ids})",
                "effective_from": f"lte.{today.isoformat()}",
                "order": "effective_from.asc"
            }
        ) or []
    else:
        goal_rows = []

    # ----------------------------------
    # Build goal history map
    # ----------------------------------
    goal_history_map = {}

    for row in goal_rows:
        hid = row["habit_id"]
        goal_history_map.setdefault(hid, []).append(row)

    # ----------------------------------
    # Helper: resolve goal for date
    # ----------------------------------
    def resolve_goal_local(habit_id, day):
        history = goal_history_map.get(habit_id, [])
        goal = 0
        for row in history:
            if row["effective_from"] <= day:
                goal = float(row["goal"])
            else:
                break
        return goal

    # ----------------------------------
    # Build entry map by date
    # ----------------------------------
    date_map = {}
    for r in rows:
        date_map.setdefault(r["plan_date"], []).append(r)

    habit_map = {h["id"]: h for h in habit_defs}

    # ----------------------------------
    # Compute daily percentages
    # ----------------------------------
    percentages = []

    for i in range(7):
        day = (start + timedelta(days=i)).isoformat()
        entries = date_map.get(day, [])

        completed = 0

        for e in entries:
            habit = habit_map.get(e["habit_id"])
            if not habit:
                continue

            goal = resolve_goal_local(habit["id"], day)
            value = float(e.get("value") or 0)

            if goal > 0 and value >= goal:
                completed += 1

        percent = round((completed / total) * 100) if total else 0
        percentages.append(percent)

    # ----------------------------------
    # Weekly average
    # ----------------------------------
    avg = round(sum(percentages) / len(percentages)) if percentages else 0

    # ----------------------------------
    # Best habit (by total value)
    # ----------------------------------
    habit_totals = {}

    for r in rows:
        habit_totals[r["habit_id"]] = (
            habit_totals.get(r["habit_id"], 0)
            + float(r.get("value") or 0)
        )

    best_habit_id = (
        max(habit_totals, key=habit_totals.get)
        if habit_totals else None
    )

    best_name = None
    if best_habit_id:
        best = habit_map.get(best_habit_id)
        if best:
            best_name = best["name"]

    return jsonify({
        "daily": percentages,
        "weekly_avg": avg,
        "best_habit": best_name
    })

@health_bp.route("/health")
@login_required
def health_dashboard():
    user_id = session["user_id"]
    plan_date = request.args.get("date")

    if plan_date:
        plan_date = date.fromisoformat(plan_date)
    else:
        plan_date = datetime.now(IST).date()

    plan_date_str = plan_date.isoformat()

    # -----------------------
    # Load daily health
    # -----------------------
    health_rows = get(
        "daily_health",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}"
        }
    )

    health = health_rows[0] if health_rows else {}

    # -----------------------
    # Load habits dynamically
    # -----------------------
    habit_defs = get("habit_master", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false"
    })

    habit_entries = get(
        "habit_entries",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}"
        }
    )

    entry_map = {h["habit_id"]: h["value"] for h in habit_entries}

    habit_list = []
    completed = 0

    for h in habit_defs:
        goal = get_goal_for_date(h["id"], plan_date)
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
            "goal": goal,   # ✅ ADD THIS
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


@health_bp.route("/api/v2/daily-health")
@login_required
def get_daily_health():
    user_id = session["user_id"]
    plan_date = request.args.get("date")

    if not plan_date:
        return jsonify({})

    # ---------------------
    # Load health
    # ---------------------
    health_rows = get(
        "daily_health",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}"
        }
    )

    if health_rows:
        health = health_rows[0]
    else:
        prev_rows = get(
            "daily_health",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"lt.{plan_date}",
                "order": "plan_date.desc",
                "limit": 1
            }
        )

        if prev_rows:
            prev = prev_rows[0]

            health = {
                "goal": prev.get("goal"),
                "height": prev.get("height"),
                "weight": prev.get("weight")
            }
        else:
            health = {}
    # ---------------------
    # Calculate BMI
    # ---------------------
    height = health.get("height")
    weight = health.get("weight")
    health.setdefault("goal", None)
    health.setdefault("height", None)
    health.setdefault("weight", None)
    bmi = None

    try:
        if height and weight:
            height_m = float(height) / 100
            bmi = round(float(weight) / (height_m * height_m), 1)
    except:
        pass
    
   
    # ---------------------
    # Load all habits (definitions)
    # ---------------------
    habit_defs = get(
        "habit_master",
        params={"user_id": f"eq.{user_id}","is_deleted": "is.false",
                 "start_date": f"lte.{plan_date}","order": "position.asc"},
        
    )

    # ---------------------
    # Load entries for date
    # ---------------------
    habit_entries = get(
        "habit_entries",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}"
        }
    )

    entry_map = {h["habit_id"]: h["value"] for h in habit_entries}

    habit_list = []
    completed = 0

    for h in habit_defs:

        goal = get_goal_for_date(h["id"], plan_date)
        value = float(entry_map.get(h["id"], 0) or 0)

        # Correct completion logic
        if goal > 0 and value >= goal:
            completed += 1

        habit_list.append({
            "id": h["id"],
            "name": h["name"],
            "unit": h["unit"],
            "goal": goal,      # 🔥 THIS WAS MISSING
            "value": value
        })

    total = len(habit_defs)
    habit_percent = round((completed / total) * 100) if total else 0
    habit_score = habit_percent

    if habit_score >= 90:
        habit_label = "Excellent"
    elif habit_score >= 70:
        habit_label = "Good"
    elif habit_score >= 40:
        habit_label = "Moderate"
    else:
        habit_label = "Needs Work"


    # ---------------------
    # Weight trend (last 7 days)
    # ---------------------
    trend_rows = get(
        "daily_health",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"lte.{plan_date}",
            "order": "plan_date.desc",
            "limit": 30
        }
    )

    weight_map = {}

    for r in trend_rows:
        if r.get("weight"):
            weight_map[r["plan_date"]] = float(r["weight"])

    weight_trend = []

    current = date.fromisoformat(plan_date)

    last_weight = None

    for i in range(6, -1, -1):

        d = (current - timedelta(days=i)).isoformat()

        if d in weight_map:
            last_weight = weight_map[d]

        weight_trend.append({
            "date": d,
            "weight": last_weight
        })
    weekly_change = None

    valid_weights = [w["weight"] for w in weight_trend if w["weight"]]

    if len(valid_weights) >= 2:
        weekly_change = round(valid_weights[-1] - valid_weights[0], 1)
    streak = compute_health_streak(user_id, date.fromisoformat(plan_date))

    return jsonify({
        **health,
        "bmi": bmi,
        "habits": habit_list,
        "habit_percent": habit_percent,
        "habit_score": habit_score,
        "habit_label": habit_label,
        "weight_trend": weight_trend,
        "weekly_change": weekly_change,
        "streak": streak
    })
    
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
    print("HEIGHT RAW:", data.get("height"))
    print("HEIGHT CLEAN:", clean_number(data.get("height")))
    # 🔥 UPSERT instead of check-then-update
    post(
        "daily_health",
        payload,
        prefer="resolution=merge-duplicates"
    )

    return jsonify({"success": True})

@health_bp.route("/api/v2/monthly-summary")
@login_required
def monthly_summary():

    user_id = session["user_id"]

    today = datetime.now(IST).date()
    start = today.replace(day=1)

    health_rows = get(
        "daily_health",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start.isoformat()}"
        }
    )

    habit_rows = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start.isoformat()}"
        }
    )

    days = len({h["plan_date"] for h in health_rows})
    avg_height = round(
        sum(float(h.get("height") or 0) for h in health_rows) / len(health_rows),
        1
    ) if health_rows else 0

    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{today.isoformat()}"
        }
    )

    total_habits = len(habit_defs)
    habit_map = {h["id"]: h for h in habit_defs}

    date_map = {}
    for r in habit_rows:
        date_map.setdefault(r["plan_date"], []).append(r)

    from calendar import monthrange
    num_days = monthrange(today.year, today.month)[1]

    percents = []

    for d in range(1, num_days + 1):

        day = today.replace(day=d).isoformat()
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

        percent = round((completed / total_habits) * 100) if total_habits else 0
        percents.append(percent)

    avg_percent = round(sum(percents) / len(percents)) if percents else 0
    weights = [float(h.get("weight") or 0) for h in health_rows if h.get("weight")]
    energy = [float(h.get("energy_level") or 0) for h in health_rows if h.get("energy_level")]

    weight_change = round(weights[-1] - weights[0], 1) if len(weights) >= 2 else 0
    avg_energy = round(sum(energy) / len(energy), 1) if energy else 0
    return jsonify({
        "days_tracked": days,
        "avg_percent": avg_percent,
        "weight_change": weight_change,
        "avg_energy": avg_energy,
        "avg_height":avg_height
    })
@health_bp.route("/api/v2/heatmap")
@login_required
def heatmap():
    user_id = session["user_id"]

    today = datetime.now(IST).date()
    start = today - timedelta(days=365)

    rows = get(
        "habit_entries",
        {
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start.isoformat()}"
        }
    )

    habit_defs = get(
        "habit_master",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "is.false",
            "start_date": f"lte.{today.isoformat()}"
        }
    )
    total = len(habit_defs)

    date_map = {}

    for r in rows:
        date_map.setdefault(r["plan_date"], []).append(r)

    heat = {}

    habit_map = {h["id"]: h for h in habit_defs}

    for day, entries in date_map.items():
        completed = 0

        for e in entries:
            habit = habit_map.get(e["habit_id"])
            if not habit:
                continue

            goal = float(habit.get("goal") or 0)
            value = float(e.get("value") or 0)

            if goal > 0 and value >= goal:
                completed += 1

        percent = round((completed / total) * 100) if total else 0
        heat[day] = percent

    return jsonify(heat)       

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


def clean_number(val):
    return float(val) if val not in ("", None) else None
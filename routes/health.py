from flask import Blueprint, jsonify, render_template, request, session
from datetime import date, datetime, timedelta
from auth import login_required
from config import IST
from supabase_client import get, post
from services.planner_service import compute_health_streak



health_bp = Blueprint("health", __name__)


def get_goals_batch(habit_ids, plan_date):
    """Fetch the effective goal for each habit in one query instead of N queries."""
    if not habit_ids:
        return {}
    ids_str = ",".join(str(h) for h in habit_ids)
    rows = get(
        "habit_goal_history",
        {
            "habit_id": f"in.({ids_str})",
            "effective_from": f"lte.{plan_date}",
            "order": "effective_from.desc,created_at.desc",
        }
    ) or []
    goals = {}
    for row in rows:
        hid = row["habit_id"]
        if hid not in goals:  # first row per habit = most recent (desc order)
            goals[hid] = float(row["goal"])
    return goals


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
    habit_ids = list(habit_map.keys())

    # Batch-fetch goals for all habits up to today (covers the whole week)
    goals_map = get_goals_batch(habit_ids, today.isoformat())

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
            if e["habit_id"] not in habit_map:
                continue

            goal = goals_map.get(e["habit_id"], 0)
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
    # Habits and health data are loaded by JS via /api/v2/daily-health.
    # Only the page shell is rendered here.
    return render_template("health_dashboard.html")


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

    habit_ids = [h["id"] for h in habit_defs]
    goals_map = get_goals_batch(habit_ids, plan_date)

    habit_list = []
    completed = 0

    for h in habit_defs:
        goal = goals_map.get(h["id"], 0)
        value = float(entry_map.get(h["id"], 0) or 0)

        if goal > 0 and value >= goal:
            completed += 1

        habit_list.append({
            "id": h["id"],
            "name": h["name"],
            "unit": h["unit"],
            "habit_type": h.get("habit_type"),
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
# HEATMAP — 30-day habit completion grid
# ==========================================================

@health_bp.route("/api/v2/heatmap", methods=["GET"])
@login_required
def heatmap():
    """Habit-completion percentage per day across an arbitrary window.

    Query params (both optional):
      start=YYYY-MM-DD   Start date (inclusive). Defaults to 29 days ago.
      end=YYYY-MM-DD     End date (inclusive). Defaults to today.

    Falls back to the legacy "last 30 days" behaviour when neither param
    is supplied, so older clients keep working.
    """
    from flask import request

    user_id = session["user_id"]
    today = datetime.now(IST).date()

    # Parse optional range params; clamp and sanity-check.
    raw_end = (request.args.get("end") or "").strip()
    raw_start = (request.args.get("start") or "").strip()

    try:
        end = datetime.fromisoformat(raw_end).date() if raw_end else today
    except ValueError:
        end = today
    try:
        start = datetime.fromisoformat(raw_start).date() if raw_start else (end - timedelta(days=29))
    except ValueError:
        start = end - timedelta(days=29)

    if start > end:
        start, end = end, start
    # Cap at a reasonable one-year window to avoid accidental huge reads.
    if (end - start).days > 365:
        start = end - timedelta(days=365)

    habits = get("habit_master", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "is.false"
    })
    if not habits:
        return jsonify({})

    total_habits = len(habits)

    # Use PostgREST's combined filter syntax so gte AND lte both apply.
    # The previous code had two `plan_date` keys in the same dict which
    # Python silently collapsed to the second one — only the upper bound
    # actually reached Supabase.
    entries = get("habit_entries", params={
        "user_id": f"eq.{user_id}",
        "plan_date": f"gte.{start.isoformat()}",
        "and": f"(plan_date.lte.{end.isoformat()})",
    }) or []

    day_counts = {}
    for e in entries:
        d = e["plan_date"]
        if e.get("value") and float(e["value"]) > 0:
            day_counts[d] = day_counts.get(d, 0) + 1

    result = {}
    span = (end - start).days + 1
    for i in range(span):
        d = (start + timedelta(days=i)).isoformat()
        count = day_counts.get(d, 0)
        result[d] = round((count / total_habits) * 100) if total_habits else 0

    return jsonify(result)


# ==========================================================
# MONTHLY SUMMARY
# ==========================================================

@health_bp.route("/api/v2/monthly-summary", methods=["GET"])
@login_required
def monthly_summary():
    user_id = session["user_id"]
    today = datetime.now(IST).date()
    start = today.replace(day=1).isoformat()

    habits = get("habit_master", params={
        "user_id": f"eq.{user_id}",
        "is_deleted": "is.false"
    })
    total_habits = len(habits) if habits else 1

    # PostgREST `and=()` keeps both range bounds; a duplicated dict key
    # silently collapses to one filter and read the entire table.
    entries = get("habit_entries", params={
        "user_id": f"eq.{user_id}",
        "and": f"(plan_date.gte.{start},plan_date.lte.{today.isoformat()})",
    })

    # Days tracked = unique dates with at least 1 entry
    days_with_entries = set()
    total_value_entries = 0
    for e in entries:
        if e.get("value") and float(e["value"]) > 0:
            days_with_entries.add(e["plan_date"])
            total_value_entries += 1

    days_tracked = len(days_with_entries)
    days_in_month = today.day
    avg_percent = round((total_value_entries / (days_in_month * total_habits)) * 100) if days_in_month else 0

    # Weight change this month
    health_rows = get("daily_health", params={
        "user_id": f"eq.{user_id}",
        "and": f"(plan_date.gte.{start},plan_date.lte.{today.isoformat()})",
        "order": "plan_date.asc",
    })
    weights = [r["weight"] for r in (health_rows or []) if r.get("weight")]
    weight_change = round(weights[-1] - weights[0], 1) if len(weights) >= 2 else 0

    energies = [r["energy_level"] for r in (health_rows or []) if r.get("energy_level")]
    avg_energy = round(sum(energies) / len(energies), 1) if energies else 0

    return jsonify({
        "days_tracked": days_tracked,
        "avg_percent": min(avg_percent, 100),
        "weight_change": weight_change,
        "avg_energy": avg_energy
    })


# ==========================================================
# UTIL
# ==========================================================

def clean_number(val):
    return float(val) if val not in ("", None) else None
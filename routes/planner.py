import calendar
from datetime import date, datetime, timedelta
import os

from flask import Blueprint, jsonify, redirect, render_template, render_template_string, request, session, url_for
from supabase_client import post
import pytz

from config import DEFAULT_STATUS, HABIT_ICONS, HABIT_LIST, IST, MIN_HEALTH_HABITS, QUADRANT_MAP, STATUSES, TOTAL_SLOTS
from logger import setup_logger
from services.login_service import login_required
from services.planner_service import compute_health_streak, ensure_daily_habits_row, fetch_daily_slots, generate_weekly_insight, get_daily_summary, get_weekly_summary, group_slots_into_blocks, is_health_day, load_day, save_day
from services.recurring_service import materialize_recurring_slots
from services.untimed_service import remove_untimed_task
from supabase_client import get, update
from templates.login import LOGIN_TEMPLATE
from templates.planner import PLANNER_TEMPLATE
from templates.summary import SUMMARY_TEMPLATE
from utils.calender_links import google_calendar_link
from utils.dates import safe_date
from utils.slots import current_slot, slot_label
from utils.smartplanner import parse_smart_sentence

planner_bp = Blueprint("planner", __name__)
APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
logger = setup_logger()
@planner_bp.route("/", methods=["GET", "POST"])
@login_required
def planner():
    user_id = session["user_id"]
    daily_slots = []
    if request.method == "HEAD":
        return "", 200
    today = datetime.now(IST).date()
    # ----------------------------------------------------------
# Auto-redirect root load to today (only if no date provided)
# ----------------------------------------------------------
    if request.method == "GET" and not request.args.get("day"):
        today = datetime.now(IST).date()
        return redirect(
            url_for(
                "planner.planner",
                year=today.year,
                month=today.month,
                day=today.day,
            )
        )

    if request.method == "POST":
        year = int(request.form["year"])
        month = int(request.form["month"])
        day = int(request.form["day"])
    else:
        year = int(request.args.get("year", today.year))
        month = int(request.args.get("month", today.month))
        day = int(request.args.get("day", today.day))

    plan_date = safe_date(year, month, day)
    formatted_date = plan_date.strftime("%d %B %Y").lstrip("0")


    if request.method == "POST":
        logger.info(f"Saving planner for date={plan_date}")
        save_day(plan_date, request.form)
        return redirect(
            url_for("planner.planner", year=plan_date.year, month=plan_date.month, day=plan_date.day, saved=1)
        )
    materialize_recurring_slots(plan_date, user_id)
    ensure_daily_habits_row(user_id, plan_date)
  
    plans, habits, reflection,untimed_tasks= load_day(plan_date)
 
    daily_slots = fetch_daily_slots(plan_date)
    blocks = group_slots_into_blocks(plans)



    days = [
        date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)
    ]

    reminder_links = {
        slot: google_calendar_link(plan_date, slot, plans[slot]["plan"])
        for slot in range(1, TOTAL_SLOTS + 1)
    }
   
    health_streak = compute_health_streak(user_id, plan_date)

    streak_active_today = is_health_day(set(habits))
    selected_date = date(year, month, day)
    today = date.today()
    # ✅ ADD THIS HERE
    timeline_days = [
        selected_date + timedelta(days=i)
        for i in range(-6, 7)
    ]

    # ✅ Month navigation helpers
    prev_month = (selected_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (selected_date.replace(day=28) + timedelta(days=4)).replace(day=1)
   # tasks = build_tasks_for_ui(plan_date)
   

    return render_template_string(
        PLANNER_TEMPLATE,
        year=year,
        month=month,
        days=days,
        selected_day=plan_date.day,
        today=today,
        plans=plans,
        statuses=STATUSES,
        slot_labels={i: slot_label(i) for i in range(1, TOTAL_SLOTS + 1)},
        reminder_links=reminder_links,
        now_slot=current_slot() if plan_date == today else None,
        saved=request.args.get("saved"),
        habits=habits,
        reflection=reflection,
        habit_list=HABIT_LIST,
        habit_icons=HABIT_ICONS,
        calendar=calendar,
        untimed_tasks=untimed_tasks,
        plan_date=plan_date,
        health_streak=health_streak,
        streak_active_today=streak_active_today,
        min_health_habits=MIN_HEALTH_HABITS,
        blocks=blocks,
        today_display=formatted_date,
        prev_month=prev_month,
        next_month=next_month,
        timeline_days=timeline_days,
        selected_date=selected_date,
       # tasks=tasks,
        daily_slots=daily_slots
        
    )
    

@planner_bp.route("/planner-v2")
def planner_v2():
    return render_template("planner_v2.html")

@planner_bp.route("/smart/add", methods=["POST"])
@login_required
def smart_add():
    data = request.get_json(force=True)

    text = data["text"]
    plan_date = date.fromisoformat(data["plan_date"])

    # 🔥 ALWAYS delegate to save_day
    # This ensures:
    # - smart parsing
    # - generate_half_hour_slots
    # - start_time / end_time persistence
    # - recurrence handling
    save_day(plan_date, {"smart_plan": text})

    return jsonify({"status": "ok"})


@planner_bp.route("/smart/preview", methods=["POST"])
@login_required
def smart_preview():
    data = request.get_json(force=True)

    text = data.get("text", "").strip()
    plan_date = data.get("plan_date")

    if not text or not plan_date:
        return jsonify({"conflicts": []})

    # Try parsing smart sentence
    try:
        parsed = parse_smart_sentence(text, date.fromisoformat(plan_date))
    except Exception:
        # If parsing fails → no conflicts, allow save
        return jsonify({"conflicts": []})

    start_slot = parsed["start_slot"]
    slot_count = parsed["slot_count"]

    # Fetch existing plans for those slots
    conflicts = []
    for i in range(slot_count):
        slot = start_slot + i
        existing = get_plan_for_slot(plan_date, slot)  # ← YOUR EXISTING helper
        if existing and existing.strip():
            conflicts.append({
                "time": f"Slot {slot}",
                "existing": existing,
                "incoming": parsed["text"]
            })

    return jsonify({"conflicts": conflicts})


@planner_bp.route("/slot/toggle-status", methods=["POST"])
@login_required
def toggle_slot_status():
    data = request.get_json()
    user_id = session["user_id"]
    update(
        "daily_slots",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{data['plan_date']}",
            "slot": f"eq.{data['slot']}",
        },
        json={"status": data["status"]},
    )

    return ("", 204)

@planner_bp.route("/untimed/slot-preview", methods=["POST"])
@login_required
def untimed_slot_preview():
    data = request.get_json()

    plan_date = date.fromisoformat(data["plan_date"])
    start_slot = int(data["start_slot"])
    slot_count = int(data["slot_count"])

    preview = []
    user_id = session["user_id"]
    for i in range(slot_count):
        slot = start_slot + i
        if not (1 <= slot <= TOTAL_SLOTS):
            continue

        row = get(
            "daily_slots",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date":f"eq.{plan_date.isoformat()}",
                "slot": f"eq.{slot}",
                "select": "slot,plan",
            },
        )

        preview.append({
            "slot": slot,
            "existing": row[0]["plan"] if row and row[0].get("plan") else ""
        })

    return preview, 200

@planner_bp.route("/slot/get")
@login_required
def get_slot():
    plan_date = request.args["date"]
    slot = int(request.args["slot"])
    user_id = session["user_id"]
    row = get(
        "daily_slots",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "slot": f"eq.{slot}",
            "select": "plan",
        },
    )
    return jsonify({"text": row[0]["plan"] if row else ""})
def slot_to_time(slot):
    minutes = slot * 30
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"
@planner_bp.route("/slot/update", methods=["POST"])
@login_required
def update_slot():
 
    data = request.get_json()

    plan_date = data["plan_date"]
    old_start = int(data["old_start"])
    old_end = int(data["old_end"])
    start = int(data["start_slot"])
    end = int(data["end_slot"])
    text = data["text"]
    priority=data["priority"]
    category=data["category"]
    user_id = session["user_id"]
    # 🛑 If dropped in same slot, do nothing
    if old_start == start and old_end == end:
        return ("", 204)
    logger.debug(
    "DRAG MOVE user=%s old=%s-%s new=%s-%s text=%s",
    user_id, old_start, old_end, start, end, text
    )
    

    # 1️⃣ Clear previous slots (single query)
    for slot in range(old_start, old_end + 1):
        update(
            "daily_slots",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date}",
                "slot": f"eq.{slot}",
            },
            json={
                "plan": None,
                "start_time": None,
                "end_time": None,
            },
        )
        

    # 2️⃣ Write new slots
    rows = []
    for slot in range(start, end + 1):
       start_time = slot_to_time(slot)
       end_time = slot_to_time(slot + 1)

       rows.append({
            "user_id": user_id,
            "plan_date": plan_date,
            "slot": slot,
            "plan": text,
            "start_time": start_time,
            "end_time": end_time,
            "priority":priority,
            "category":category
        })

    post(
        "daily_slots?on_conflict=user_id,plan_date,slot",
        rows,
        prefer="resolution=merge-duplicates"
    )

    return ("", 204)


@planner_bp.route("/untimed/promote", methods=["POST"])
@login_required
def promoteuntimed():
    data = request.get_json()

    user_id = session["user_id"]
    plan_date = date.fromisoformat(data["plan_date"])
    plan_date_str = plan_date.isoformat()
    task_id = data["id"]

    # -------------------------------------------------
    # Load untimed tasks from daily_meta
    # -------------------------------------------------
    rows = get(
        "daily_meta",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}",
            "select": "untimed_tasks",
        },
    )

    if not rows:
        return ("Untimed task not found", 404)

    untimed = rows[0].get("untimed_tasks") or []

    task = next(
        (t for t in untimed if isinstance(t, dict) and t.get("id") == task_id),
        None
    )
    if not task:
        return ("Untimed task not found", 404)

    text = task["text"]

    # -------------------------------------------------
    # Quadrant validation
    # -------------------------------------------------
    raw_q = data["quadrant"].upper()
    if raw_q not in QUADRANT_MAP:
        return ("Invalid quadrant", 400)

    quadrant = QUADRANT_MAP[raw_q]

    # -------------------------------------------------
    # Compute next position
    # -------------------------------------------------
    max_pos = get(
        "todo_matrix",
        params={
            "plan_date": f"eq.{plan_date_str}",
            "quadrant": f"eq.{quadrant}",
            "is_deleted": "eq.false",
            "select": "position",
            "order": "position.desc",
            "limit": 1,
        },
    )

    existing = get(
        "todo_matrix",
        params={
            "plan_date": f"eq.{plan_date_str}",
            "quadrant": f"eq.{quadrant}",
            "task_text": f"eq.{text}",
            "is_deleted": "eq.false",
        },
    )

    if existing:
        return ("Task already exists in the selected quadrant", 400)

    next_pos = max_pos[0]["position"] + 1 if max_pos else 0

    # -------------------------------------------------
    # Insert into Eisenhower matrix
    # -------------------------------------------------
    post(
        "todo_matrix",
        {
            "plan_date": plan_date_str,
            "quadrant": quadrant,
            "task_text": text,
            "is_done": False,
            "is_deleted": False,
            "position": next_pos,
            "category": "General",
            "subcategory": "General",
        },
    )

    # -------------------------------------------------
    # Remove from untimed list
    # -------------------------------------------------
    remove_untimed_task(user_id, plan_date, task_id)

    return ("", 204)

@planner_bp.route("/untimed/schedule", methods=["POST"])
@login_required
def schedule_untimed():
    data = request.get_json()

    user_id = session["user_id"]
    plan_date = date.fromisoformat(data["plan_date"])
    plan_date_str = plan_date.isoformat()

    if plan_date < datetime.now(IST).date():
        return ("Cannot schedule in the past", 400)

    task_id = data["id"]
    start_slot = int(data["start_slot"])
    slot_count = int(data["slot_count"])

    # -------------------------------------------------
    # Resolve untimed task from daily_meta (SOURCE OF TRUTH)
    # -------------------------------------------------
    rows = get(
        "daily_meta",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date_str}",
            "select": "untimed_tasks",
        },
    )

    if not rows:
        return ("Untimed task not found", 404)

    untimed = rows[0].get("untimed_tasks") or []

    task = next(
        (t for t in untimed if isinstance(t, dict) and t.get("id") == task_id),
        None
    )
    if not task:
        return ("Untimed task not found", 404)

    # Prefer confirmed text from client, fallback to stored text
    text = data.get("final_text") or task["text"]

    # -------------------------------------------------
    # Build slot payload
    # -------------------------------------------------
    payload = []
    for i in range(slot_count):
        slot = start_slot + i
        if 1 <= slot <= TOTAL_SLOTS:
            payload.append({
                "user_id": user_id,
                "plan_date": plan_date_str,
                "slot": slot,
                "plan": text,
                "status": DEFAULT_STATUS,
            })

    if not payload:
        return ("Invalid slot range", 400)

    # -------------------------------------------------
    # Insert / update daily slots
    # -------------------------------------------------
    post(
        "daily_slots?on_conflict=plan_date,slot",
        payload,
        prefer="resolution=merge-duplicates",
    )

    # -------------------------------------------------
    # Remove from untimed list
    # -------------------------------------------------
    remove_untimed_task(user_id, plan_date, task_id)

    return ("", 204)


@planner_bp.route("/summary")
@login_required
def summary():
    view = request.args.get("view", "daily")

    # -------------------------
    # DAILY DATE PARAM
    # -------------------------
    date_str = request.args.get("date")
    if date_str:
        plan_date = date.fromisoformat(date_str)
    else:
        plan_date = datetime.now(IST).date()

    # =========================
    # WEEKLY VIEW
    # =========================
    if view == "weekly":

        week_str = request.args.get("week")  # format: 2026-W07

        if week_str:
            try:
                year, week = week_str.split("-W")
                start = date.fromisocalendar(int(year), int(week), 1)
            except ValueError:
                start = plan_date - timedelta(days=plan_date.weekday())
        else:
            # fallback — current week
            start = plan_date - timedelta(days=plan_date.weekday())

        end = start + timedelta(days=6)

        data = get_weekly_summary(start, end)
        insights = generate_weekly_insight(data)

        return render_template_string(
            SUMMARY_TEMPLATE,
            view="weekly",
            data=data,
            start=start,
            end=end,  # ✅ FIXED (was plan_date)
            insights=insights,
            selected_week=start.strftime("%G-W%V"),  # for picker value
        )

    # =========================
    # DAILY VIEW
    # =========================
    data = get_daily_summary(plan_date)

    return render_template_string(
        SUMMARY_TEMPLATE,
        view="daily",
        data=data,
        date=plan_date,
    )
def get_plans_for_date(plan_date):
    return [
        p for p in session.get("plans", [])
        if p["plan_date"] == plan_date
    ]

def get_plan_for_slot(plan_date, slot):
    plans = get_plans_for_date(plan_date)  # DB / cache / session

    for plan in plans:
        if plan["start_slot"] <= slot < plan["start_slot"] + plan["slot_count"]:
            return plan["text"]

    return None

def load_slot_timeline(plan_date):
    user_id = session["user_id"]
    return get(
        "daily_slots",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date.isoformat()}",
            "select": "slot,plan,status",
            "order": "slot.asc"
        }
    ) or []


def build_slot_blocks(rows):
    slot_map = {r["slot"]: r for r in rows}
    blocks = []

    for slot in range(1, TOTAL_SLOTS + 1):
        r = slot_map.get(slot)

        blocks.append({
            "slot": slot,
            "label": slot_label(slot),
            "text": r["plan"] if r else "",
            "status": r["status"] if r else None
        })

    return blocks

def get_conflicts(user_id, plan_date, start_time, end_time, exclude_id=None):
    existing = get(
        "daily_events",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "is_deleted": "eq.false"
        }
    ) or []

    conflicts = []

    for e in existing:
        if exclude_id and str(e["id"]) == str(exclude_id):
            continue

        if not (
            end_time <= e["start_time"] or
            start_time >= e["end_time"]
        ):
            conflicts.append({
                "start_time": str(e["start_time"]),
                "end_time": str(e["end_time"]),
                "title": e["title"]
            })

    return conflicts

def build_google_datetime(plan_date, time_str):
    tz = pytz.timezone("Asia/Kolkata")

    # 🔥 Support both HH:MM and HH:MM:SS
    try:
        dt = datetime.strptime(f"{plan_date} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(f"{plan_date} {time_str}", "%Y-%m-%d %H:%M")

    dt = tz.localize(dt)
    return dt.isoformat()
@planner_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password")

        if password == APP_PASSWORD and username:
            session.clear()
            session["user_id"] = username
            session["authenticated"] = True

            print("USER ID:", username)

            return redirect(url_for("planner.planner"))

        return render_template_string(LOGIN_TEMPLATE, error="Invalid login")

    return render_template_string(LOGIN_TEMPLATE)

@planner_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("planner.login"))

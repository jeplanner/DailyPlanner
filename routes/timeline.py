from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from config import IST
from utils.user_tz import user_now, user_today
from routes.planner import build_slot_blocks, load_slot_timeline
from services.timeline_service import load_timeline_tasks
from supabase_client import get, update


timeline_bp = Blueprint("timeline", __name__)


def build_timeline_blocks(tasks, zoom="day"):
    """
    Group tasks into timeline blocks.
    zoom="day"  → one block per day
    zoom="week" → one block per ISO week
    Returns list of {date, label, tasks}
    """
    groups = defaultdict(list)

    for t in tasks:
        anchor = t.get("due_date") or t.get("start_date")
        if not anchor:
            continue
        if isinstance(anchor, str):
            anchor = date.fromisoformat(anchor)

        if zoom == "week":
            # Key = Monday of that ISO week
            monday = anchor - timedelta(days=anchor.weekday())
            key = monday
            label = f"Week of {monday.strftime('%b %d, %Y')}"
        else:
            key = anchor
            label = anchor.strftime("%a, %b %d %Y")

        groups[key].append(t)

    blocks = []
    for key in sorted(groups):
        block_date = key
        if zoom == "week":
            label = f"Week of {key.strftime('%b %d, %Y')}"
        else:
            label = key.strftime("%a, %b %d %Y")

        blocks.append({
            "date": block_date.isoformat(),
            "label": label,
            "tasks": groups[key],
        })

    return blocks
@timeline_bp.route("/projects/timeline")
@login_required
def task_timeline():
    user_id = session["user_id"]

    zoom = request.args.get("zoom", "day")          # day | week
    project_id = request.args.get("project")        # optional filter

    tasks = load_timeline_tasks(user_id, project_id=project_id)

    timeline_blocks = build_timeline_blocks(tasks, zoom)

    projects = get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "is_archived": "eq.false"
        }
    )

    return render_template(
        "project_timeline.html",
        timeline_blocks=timeline_blocks,
        zoom=zoom,
        projects=projects,
    )
    

@timeline_bp.route("/api/timeline/reschedule", methods=["POST"])
@login_required
def timeline_reschedule():
    data = request.get_json()

    task_id = data["task_id"]
    new_date = data["new_date"]

    update(
        "project_tasks",
        params={"task_id": f"eq.{task_id}"},
        json={"due_date": new_date}
    )

    return jsonify({"status": "ok"})

@timeline_bp.route("/timeline/day")
@login_required
def timeline_day():
    d = request.args.get("date")

    if d:
        plan_date = date.fromisoformat(d)
    else:
        plan_date = user_today()

    rows = load_slot_timeline(plan_date)
    blocks = build_slot_blocks(rows)

    return render_template(
        "timeline_day.html",
        blocks=blocks,
        plan_date=plan_date
    )

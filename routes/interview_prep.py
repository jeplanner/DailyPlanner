"""Interview Prep Coach — a motivating, on-track interview tracker.

Built for a senior run (Senior Director / Head of Technical Program
Management): a readiness score, a curated syllabus with confidence
levels, a STAR story bank, a daily practice log driving a streak, and a
coach that celebrates when you're ahead and *scolds* when you skip a day
or fall behind pace.

Readiness and streak are computed on the fly from topics / stories /
sessions — nothing to keep in sync. Schema: MIGRATION_INTERVIEW_PREP.sql.
Soft-delete only (deleted_at).
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update
from utils.user_tz import user_today

logger = logging.getLogger("daily_plan")
interview_prep_bp = Blueprint("interview_prep", __name__)

DEFAULT_ROLE = "Senior Director, Technical Program Management"
DEFAULT_TARGET_DAYS = 42          # ~6 weeks out
STORY_TARGET = 6                  # rehearsed stories that = "story ready"
_MAX_TITLE = 140
_MAX_TEXT = 4000
_MAX_MINUTES = 24 * 60

CATEGORIES = ("behavioral", "system_design", "tpm", "executive", "domain")
CATEGORY_LABELS = {
    "behavioral": "Behavioral / STAR",
    "system_design": "System Design",
    "tpm": "TPM Competencies",
    "executive": "Executive / Leadership",
    "domain": "Domain / Role-specific",
}

# Curated starter syllabus for a senior TPM / exec run. Seeded per-user on
# first visit, then fully editable (add / rename / delete / re-rate).
SEED_TOPICS = [
    ("behavioral", "Leading through ambiguity"),
    ("behavioral", "Influence without authority"),
    ("behavioral", "Cross-org conflict resolution"),
    ("behavioral", "Driving a company-scale program"),
    ("behavioral", "Recovering a failing program"),
    ("behavioral", "Managing up / disagreeing with an exec"),
    ("behavioral", "Hard prioritization & trade-off calls"),
    ("behavioral", "Building & scaling a team/org"),
    ("system_design", "Scalability: load balancing, caching, sharding"),
    ("system_design", "Reliability & resilience (redundancy, failover, SLAs)"),
    ("system_design", "Consistency & CAP trade-offs"),
    ("system_design", "Async & event-driven (queues, streams)"),
    ("system_design", "Data storage choices (SQL vs NoSQL, OLTP/OLAP)"),
    ("system_design", "Observability & incident management"),
    ("system_design", "Explaining technical trade-offs to execs"),
    ("tpm", "Program planning & roadmapping"),
    ("tpm", "Risk management (RAID) & mitigation"),
    ("tpm", "Dependency & critical-path management"),
    ("tpm", "Metrics, KPIs & OKRs"),
    ("tpm", "Operating cadence & governance"),
    ("tpm", "Executive status & escalation"),
    ("tpm", "Managing distributed / global teams"),
    ("executive", "Vision & strategy narrative"),
    ("executive", "Scope-of-impact stories (org / company-wide)"),
    ("executive", "Executive communication (concise, outcome-first)"),
    ("executive", "Business & financial acumen (budget, ROI)"),
    ("executive", "Talent development & culture"),
    ("executive", "\"Why you / why this role\" narrative"),
]

# STAR scaffolds so the story bank isn't a blank page.
SEED_STORIES = [
    ("Led through major ambiguity", "Ambiguity"),
    ("Recovered a failing program", "Recovery"),
    ("Influenced without authority", "Influence"),
    ("Resolved a cross-org conflict", "Conflict"),
    ("Delivered a company-scale program", "Delivery"),
    ("Made a hard prioritization call", "Prioritization"),
    ("Managed up / disagreed with a leader", "Managing up"),
    ("Built or scaled a team", "Talent"),
]

# Rotating grit / leadership quotes (deterministic pick by day).
QUOTES = [
    ("Amateurs sit and wait for inspiration; the rest of us just get up and go to work.", "Stephen King"),
    ("Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln"),
    ("The will to win means nothing without the will to prepare.", "Juma Ikangaa"),
    ("Under pressure you don't rise to the occasion — you sink to your level of preparation.", "Anonymous"),
    ("Success is the sum of small efforts repeated day in and day out.", "Robert Collier"),
    ("Do the hard jobs first. The easy jobs will take care of themselves.", "Dale Carnegie"),
    ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar"),
    ("Hard choices, easy life. Easy choices, hard life.", "Jerzy Gregorek"),
    ("The expert in anything was once a beginner.", "Helen Hayes"),
    ("What you do every day matters more than what you do once in a while.", "Gretchen Rubin"),
]


def _today():
    try:
        return user_today()
    except Exception:
        return date.today()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ensure_plan(user_id):
    """Return the user's plan row, creating it (and seeding the starter
    syllabus + story scaffolds) on first visit."""
    try:
        rows = get("interview_prep", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "*", "limit": "1",
        }) or []
    except Exception as e:
        logger.warning("interview_prep plan lookup failed (run migration?): %s", e)
        return None
    if rows:
        return rows[0]

    target = (_today() + timedelta(days=DEFAULT_TARGET_DAYS)).isoformat()
    try:
        created = post("interview_prep", {
            "user_id": user_id,
            "role_title": DEFAULT_ROLE,
            "target_date": target,
            "daily_goal_minutes": 45,
        })
    except Exception as e:
        logger.exception("interview_prep plan create failed: %s", e)
        return None

    # Seed the syllabus + story scaffolds (best-effort; page still works
    # if these fail — the user can add their own).
    try:
        post("interview_topics", [
            {"user_id": user_id, "category": c, "title": t, "position": i}
            for i, (c, t) in enumerate(SEED_TOPICS)
        ])
    except Exception:
        logger.exception("interview_prep seed topics failed")
    try:
        post("interview_stories", [
            {"user_id": user_id, "title": t, "competency": comp, "position": i}
            for i, (t, comp) in enumerate(SEED_STORIES)
        ])
    except Exception:
        logger.exception("interview_prep seed stories failed")

    return created[0] if created else None


def _streaks(by_day, goal, today):
    """(current_streak, best_streak) of consecutive days meeting the goal.
    A missed *today* doesn't zero a streak built through yesterday."""
    met = {d for d, m in by_day.items() if goal > 0 and m >= goal}
    # current
    cur = 0
    day = today if today.isoformat() in met else today - timedelta(days=1)
    while day.isoformat() in met:
        cur += 1
        day -= timedelta(days=1)
    # best
    best = run = 0
    prev = None
    for d in sorted(met):
        dd = date.fromisoformat(d)
        run = run + 1 if (prev and dd - prev == timedelta(days=1)) else 1
        best = max(best, run)
        prev = dd
    return cur, best


def _coach(readiness, days_left, expected, goal_met, minutes_today, goal, streak):
    """Pick a coach message + tone from the current state. Tones:
    scold (behind / skipping) · push (streak at risk) · cheer (on track)
    · celebrate (ahead / go-time)."""
    if days_left is not None and days_left < 0:
        return ("🎯 Interview time is here. You've done the reps — walk in as the "
                "calmest, best-prepared person in the room.", "celebrate")
    if days_left is not None and days_left <= 3 and readiness < 75:
        return (f"⏰ Only {days_left} day(s) left and you're at {readiness}%. This is "
                f"crunch time — kill the distractions and drill your weakest topics NOW.",
                "scold")
    if not goal_met:
        if streak > 0:
            return (f"🔥 Your {streak}-day streak is on the line and you're at "
                    f"{minutes_today}/{goal} min today. Don't you dare break the chain — "
                    f"finish it.", "push")
        return (f"🚫 {minutes_today}/{goal} minutes logged today. A Head-of-TPM seat "
                f"won't wait for someone who coasts. Sit down and put in the work — now.",
                "scold")
    gap = readiness - expected
    if gap < -12:
        return (f"📉 Goal met today — good. But you're behind pace at {readiness}% with "
                f"{days_left} day(s) left. You have ground to make up. Raise a weak topic "
                f"and rehearse a story tomorrow.", "scold")
    if gap > 10:
        return (f"🚀 Ahead of schedule at {readiness}% and goal met. This is exactly the "
                f"intensity that lands senior offers — keep it up.", "celebrate")
    return (f"✅ Goal met and on track at {readiness}%. Consistency like this is what gets "
            f"the offer. Same again tomorrow.", "cheer")


@interview_prep_bp.route("/interview-prep", methods=["GET"])
@login_required
def page():
    return render_template("interview_prep.html")


@interview_prep_bp.route("/api/interview-prep", methods=["GET"])
@login_required
def dashboard():
    """Everything the page needs in one payload: plan, computed stats +
    coach message, topics, stories, and recent sessions."""
    user_id = session["user_id"]
    plan = _ensure_plan(user_id)
    if plan is None:
        return jsonify({"migration_pending": True,
                        "plan": {"role_title": DEFAULT_ROLE, "target_date": None,
                                 "daily_goal_minutes": 45},
                        "stats": {}, "topics": [], "stories": [], "sessions": []})

    today = _today()
    goal = int(plan.get("daily_goal_minutes") or 0)

    try:
        topics = get("interview_topics", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "id,category,title,confidence,notes,position",
            "order": "category.asc,position.asc,created_at.asc", "limit": "500",
        }) or []
    except Exception:
        topics = []
    try:
        stories = get("interview_stories", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "id,title,competency,situation,task,action,result,rehearsed,position",
            "order": "position.asc,created_at.asc", "limit": "300",
        }) or []
    except Exception:
        stories = []
    try:
        sessions = get("interview_sessions", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "id,practiced_on,minutes,focus,reflection",
            "order": "practiced_on.desc,created_at.desc", "limit": "400",
        }) or []
    except Exception:
        sessions = []

    # ── Scores ──
    if topics:
        topic_score = sum(int(t.get("confidence") or 0) for t in topics) / (4.0 * len(topics))
    else:
        topic_score = 0.0
    rehearsed = sum(1 for s in stories if s.get("rehearsed"))
    story_score = min(rehearsed, STORY_TARGET) / float(STORY_TARGET)

    by_day = defaultdict(int)
    for s in sessions:
        by_day[s.get("practiced_on")] += int(s.get("minutes") or 0)
    week_ago = (today - timedelta(days=6)).isoformat()
    days_practiced_7 = sum(1 for d, m in by_day.items() if d and d >= week_ago and m > 0)
    consistency = min(days_practiced_7, 7) / 7.0

    readiness = round((0.55 * topic_score + 0.25 * story_score + 0.20 * consistency) * 100)
    cur_streak, best_streak = _streaks(by_day, goal, today)
    minutes_today = by_day.get(today.isoformat(), 0)
    goal_met = goal > 0 and minutes_today >= goal

    # ── Pace vs target date ──
    days_left = expected = None
    target = plan.get("target_date")
    if target:
        try:
            tdate = date.fromisoformat(target)
            days_left = (tdate - today).days
            start = date.fromisoformat((plan.get("created_at") or "")[:10]) if plan.get("created_at") else today
            total = max(1, (tdate - start).days)
            elapsed = max(0, min(total, (today - start).days))
            expected = round(elapsed / total * 100)
        except Exception:
            days_left = expected = None

    msg, tone = _coach(readiness, days_left,
                       expected if expected is not None else readiness,
                       goal_met, minutes_today, goal, cur_streak)
    quote_text, quote_by = QUOTES[today.toordinal() % len(QUOTES)]

    # ── Today's focus: weakest topics + stories still to rehearse ──
    weakest = sorted(
        ({"id": t["id"], "title": t["title"],
          "category": CATEGORY_LABELS.get(t.get("category"), t.get("category")),
          "confidence": int(t.get("confidence") or 0)} for t in topics),
        key=lambda t: (t["confidence"], t["title"].lower()),
    )[:3]
    to_rehearse = [
        {"id": s["id"], "title": s["title"], "competency": s.get("competency") or ""}
        for s in stories if not s.get("rehearsed")
    ][:2]

    return jsonify({
        "plan": {
            "role_title": plan.get("role_title") or DEFAULT_ROLE,
            "target_date": target,
            "daily_goal_minutes": goal,
        },
        "stats": {
            "readiness": readiness,
            "expected": expected,
            "days_left": days_left,
            "streak": cur_streak,
            "best_streak": best_streak,
            "minutes_today": minutes_today,
            "goal_met": goal_met,
            "topic_score": round(topic_score * 100),
            "story_score": round(story_score * 100),
            "consistency": round(consistency * 100),
            "rehearsed": rehearsed,
            "story_target": STORY_TARGET,
            "topics_total": len(topics),
            "topics_mastered": sum(1 for t in topics if int(t.get("confidence") or 0) >= 4),
            "coach": msg,
            "tone": tone,
            "quote": quote_text,
            "quote_by": quote_by,
            "weakest": weakest,
            "to_rehearse": to_rehearse,
        },
        "categories": [{"key": k, "label": CATEGORY_LABELS[k]} for k in CATEGORIES],
        "topics": topics,
        "stories": stories,
        "sessions": sessions[:30],
    })


# ─────────── plan settings ───────────────────────────────────

@interview_prep_bp.route("/api/interview-prep/plan", methods=["POST"])
@login_required
def update_plan():
    user_id = session["user_id"]
    _ensure_plan(user_id)
    data = request.get_json(silent=True) or {}
    patch = {}
    if "role_title" in data:
        patch["role_title"] = (data.get("role_title") or "").strip()[:_MAX_TITLE] or DEFAULT_ROLE
    if "target_date" in data:
        patch["target_date"] = (data.get("target_date") or "").strip() or None
    if "daily_goal_minutes" in data:
        try:
            g = int(data.get("daily_goal_minutes"))
            patch["daily_goal_minutes"] = max(0, min(_MAX_MINUTES, g))
        except (TypeError, ValueError):
            return jsonify({"error": "Enter a valid number of minutes"}), 400
    if not patch:
        return jsonify({"ok": True, "noop": True})
    patch["updated_at"] = _now_iso()
    try:
        update("interview_prep", params={"user_id": f"eq.{user_id}"}, json=patch)
    except Exception as e:
        logger.exception("interview_prep plan update failed: %s", e)
        return jsonify({"error": "Couldn't save"}), 502
    return jsonify({"ok": True})


# ─────────── topics ──────────────────────────────────────────

@interview_prep_bp.route("/api/interview-prep/topics", methods=["POST"])
@login_required
def add_topic():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:_MAX_TITLE]
    if not title:
        return jsonify({"error": "Give the topic a title"}), 400
    cat = (data.get("category") or "domain").strip().lower()
    if cat not in CATEGORIES:
        cat = "domain"
    try:
        rows = post("interview_topics", {
            "user_id": user_id, "category": cat, "title": title,
            "position": int(data.get("position") or 999),
        })
    except Exception as e:
        logger.exception("interview_prep add topic failed: %s", e)
        return jsonify({"error": "Couldn't add"}), 502
    return jsonify({"item": rows[0] if rows else None})


@interview_prep_bp.route("/api/interview-prep/topics/<item_id>", methods=["POST"])
@login_required
def update_topic(item_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    patch = {}
    if "confidence" in data:
        try:
            patch["confidence"] = max(0, min(4, int(data.get("confidence"))))
        except (TypeError, ValueError):
            return jsonify({"error": "Bad confidence"}), 400
    if "title" in data:
        v = (data.get("title") or "").strip()[:_MAX_TITLE]
        if not v:
            return jsonify({"error": "Title required"}), 400
        patch["title"] = v
    if "notes" in data:
        patch["notes"] = (data.get("notes") or "").strip()[:_MAX_TEXT] or None
    if "category" in data:
        c = (data.get("category") or "").strip().lower()
        if c in CATEGORIES:
            patch["category"] = c
    if not patch:
        return jsonify({"ok": True, "noop": True})
    patch["updated_at"] = _now_iso()
    try:
        update("interview_topics",
               params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"}, json=patch)
    except Exception as e:
        logger.exception("interview_prep update topic failed: %s", e)
        return jsonify({"error": "Couldn't save"}), 502
    return jsonify({"ok": True})


@interview_prep_bp.route("/api/interview-prep/topics/<item_id>/delete", methods=["POST"])
@login_required
def delete_topic(item_id):
    user_id = session["user_id"]
    try:
        update("interview_topics",
               params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               json={"deleted_at": _now_iso()})
    except Exception as e:
        logger.exception("interview_prep delete topic failed: %s", e)
        return jsonify({"error": "Couldn't delete"}), 502
    return jsonify({"ok": True})


# ─────────── stories (STAR bank) ─────────────────────────────

@interview_prep_bp.route("/api/interview-prep/stories", methods=["POST"])
@login_required
def add_story():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:_MAX_TITLE] or "New story"
    try:
        rows = post("interview_stories", {
            "user_id": user_id, "title": title,
            "competency": (data.get("competency") or "").strip()[:_MAX_TITLE] or None,
            "position": 999,
        })
    except Exception as e:
        logger.exception("interview_prep add story failed: %s", e)
        return jsonify({"error": "Couldn't add"}), 502
    return jsonify({"item": rows[0] if rows else None})


@interview_prep_bp.route("/api/interview-prep/stories/<item_id>", methods=["POST"])
@login_required
def update_story(item_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    patch = {}
    if "title" in data:
        v = (data.get("title") or "").strip()[:_MAX_TITLE]
        if not v:
            return jsonify({"error": "Title required"}), 400
        patch["title"] = v
    if "competency" in data:
        patch["competency"] = (data.get("competency") or "").strip()[:_MAX_TITLE] or None
    for f in ("situation", "task", "action", "result"):
        if f in data:
            patch[f] = (data.get(f) or "").strip()[:_MAX_TEXT] or None
    if "rehearsed" in data:
        patch["rehearsed"] = bool(data.get("rehearsed"))
    if not patch:
        return jsonify({"ok": True, "noop": True})
    patch["updated_at"] = _now_iso()
    try:
        update("interview_stories",
               params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"}, json=patch)
    except Exception as e:
        logger.exception("interview_prep update story failed: %s", e)
        return jsonify({"error": "Couldn't save"}), 502
    return jsonify({"ok": True})


@interview_prep_bp.route("/api/interview-prep/stories/<item_id>/delete", methods=["POST"])
@login_required
def delete_story(item_id):
    user_id = session["user_id"]
    try:
        update("interview_stories",
               params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               json={"deleted_at": _now_iso()})
    except Exception as e:
        logger.exception("interview_prep delete story failed: %s", e)
        return jsonify({"error": "Couldn't delete"}), 502
    return jsonify({"ok": True})


# ─────────── practice sessions ───────────────────────────────

@interview_prep_bp.route("/api/interview-prep/sessions", methods=["POST"])
@login_required
def add_session():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    try:
        minutes = int(data.get("minutes"))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter minutes practiced"}), 400
    if minutes <= 0 or minutes > _MAX_MINUTES:
        return jsonify({"error": "Minutes must be between 1 and 1440"}), 400
    payload = {
        "user_id": user_id,
        "practiced_on": (data.get("practiced_on") or "").strip() or _today().isoformat(),
        "minutes": minutes,
        "focus": (data.get("focus") or "").strip()[:_MAX_TITLE] or None,
        "reflection": (data.get("reflection") or "").strip()[:_MAX_TEXT] or None,
    }
    try:
        rows = post("interview_sessions", payload)
    except Exception as e:
        logger.exception("interview_prep add session failed: %s", e)
        return jsonify({"error": "Couldn't log — please try again"}), 502
    return jsonify({"item": rows[0] if rows else payload})


@interview_prep_bp.route("/api/interview-prep/sessions/<item_id>/delete", methods=["POST"])
@login_required
def delete_session(item_id):
    user_id = session["user_id"]
    try:
        update("interview_sessions",
               params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
               json={"deleted_at": _now_iso()})
    except Exception as e:
        logger.exception("interview_prep delete session failed: %s", e)
        return jsonify({"error": "Couldn't delete"}), 502
    return jsonify({"ok": True})

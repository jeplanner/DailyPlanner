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
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from flask import (Blueprint, Response, jsonify, redirect, render_template,
                   request, session, url_for)

from auth import login_required
from interview_question_bank import CATEGORIES as QUESTION_CATEGORIES, QUESTIONS
from tpm_round_bank import (ENTRIES as TPM_ROUND_ENTRIES, ROUNDS as TPM_ROUNDS,
                            ROUND_BRIEF as TPM_ROUND_BRIEF,
                            TOTAL_PREP_MINUTES as TPM_TOTAL_PREP_MINUTES)
from system_design_bank import (CATEGORIES as SD_CATEGORIES,
                                 DETAIL_ORDER as SD_DETAIL_ORDER,
                                 ENTRIES as SD_ENTRIES)
from ai_sde_bank import (CATEGORIES as AI_SDE_CATEGORIES,
                         ENTRIES as AI_SDE_ENTRIES)
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


# Whitelisted markdown prep guides shipped in the repo, surfaced in-app.
_GUIDES = {
    "ai-sde": ("AI_SDE_INTERVIEW_PLAN.md",
               "AI SDE Interview Plan (Amazon/Google)"),
    "system-design": ("SYSTEM_DESIGN_ECOMMERCE_BANK.md",
                      "System Design Bank (reference)"),
}


# ─────────── AI SDE prep bank (for the new-grad AI/ML SDE track) ──────

@interview_prep_bp.route("/ai-sde", methods=["GET"])
@login_required
def ai_sde_page():
    return render_template("ai_sde.html")


@interview_prep_bp.route("/api/ai-sde", methods=["GET"])
@login_required
def ai_sde_bank():
    """The AI SDE prep bank: DSA patterns (with worked code), ML/AI
    concepts, ML coding, ML system design, CS fundamentals, behavioral and
    company process — each explained in depth. Static reference content."""
    items = [{"id": f"ai{i}", **e} for i, e in enumerate(AI_SDE_ENTRIES)]
    return jsonify({
        "categories": [{"key": k, "label": v} for k, v in AI_SDE_CATEGORIES.items()],
        "entries": items, "total": len(items),
    })


@interview_prep_bp.route("/ai-sde/pdf", methods=["GET"])
@login_required
def ai_sde_pdf():
    """Server PDF of the AI SDE bank (same ?cat/?tag/?q/?id filters)."""
    items = [{"id": f"ai{i}", **e} for i, e in enumerate(AI_SDE_ENTRIES)]
    selected, label = _bank_select(items, ("title", "answer", "pitfalls"),
                                   AI_SDE_CATEGORIES, "title")
    # ?pri=P0 narrows the export to one priority band, and the export always
    # comes out in stack-rank order so the PDF reads as a study plan.
    pri = (request.args.get("pri") or "").strip().upper()
    if pri:
        selected = [it for it in selected if it.get("priority") == pri]
        label = f"{label} — {pri}" if label else f"Priority {pri}"
    selected.sort(key=lambda it: it.get("rank") or 0)
    heading = label or "AI SDE Prep Bank"
    _mins = sum(it.get("prep_minutes") or 0 for it in selected)
    _effort = f"{_mins // 60}h {_mins % 60}m of prep" if _mins else ""
    subtitle = " | ".join(x for x in [
        f"{len(selected)} topic{'' if len(selected) == 1 else 's'}", _effort,
        "DailyPlanner Interview Prep", _today().isoformat()] if x)
    sections = []
    for it in selected:
        _diff_freq = " | ".join(x for x in [
            (f"Difficulty: {it['difficulty']}" if it.get("difficulty") else ""),
            (it.get("frequency") or "")] if x)
        # Planning line: how long this takes and where it sits in the study order.
        _plan = " | ".join(x for x in [
            (f"Prep time: {it['prep_label']}" if it.get("prep_label") else ""),
            (f"Stack rank #{it['rank']} of {len(items)}" if it.get("rank") else ""),
            (it.get("priority_note") or "")] if x)
        fields = [("Prep time & priority", _plan or None),
                  ("Difficulty & interview frequency", _diff_freq or None),
                  ("Answer / reasoning", it.get("answer")),
                  ("Explained step by step", it.get("walkthrough")),
                  # The plain-English recipe comes before the code in the PDF
                  # too — read the steps, then read the implementation.
                  ("How to code it — plain English, step by step",
                   it.get("plain_algo")),
                  # Several worked examples when the topic has them, else the
                  # original single-line example.
                  (f"Worked examples ({len(it['examples'])})" if it.get("examples") else "Example",
                   "\n\n".join(f"{n}. {x}" for n, x in enumerate(it["examples"], 1))
                   if it.get("examples") else it.get("example")),
                  ("How to remember", it.get("mnemonic")),
                  ("Complexity", it.get("complexity")),
                  ("Pitfalls", it.get("pitfalls")),
                  ("Follow-ups", it.get("followups"))]
        mono = [("Code", it.get("code"))] if it.get("code") else []
        if it.get("diagram"):
            mono.append(("Diagram", it.get("diagram")))
        sections.append({
            "title": it["title"],
            "cat": AI_SDE_CATEGORIES.get(it.get("cat"), it.get("cat", "")),
            "fields": fields, "arch": None, "mono_blocks": mono, "tags": it.get("tags"),
        })
    try:
        pdf = _pdf_bytes(heading, subtitle, sections)
    except ImportError:
        return redirect(url_for("interview_prep.ai_sde_page"))
    fname = (selected[0]["id"] + ".pdf") if len(selected) == 1 else "ai-sde-bank.pdf"
    return _pdf_response(pdf, fname)


# ── AI SDE daily quiz (HackerRank-style multiple choice) ───────────────────
import hashlib as _hashlib
import random as _random

# Only these categories make good "identify the concept from its description"
# multiple-choice questions (they have a crisp term + explanation).
_QUIZ_CATS = ("glossary", "ml_concepts", "conceptual", "dsa", "ml_coding",
              "ml_system_design", "cs_fundamentals", "lld", "ai_llm", "ai_applied")


def _first_sentences(text, n=2, limit=460):
    """First n sentences of a field, capped, for a quiz prompt."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out = " ".join(parts[:n]).strip()
    return (out[:limit] + "...") if len(out) > limit else out


def _mask_title(prompt, title):
    """Hide the answer's name (and its longer words) inside the prompt so the
    question isn't a giveaway."""
    masked = re.sub(re.escape(title), "____", prompt, flags=re.IGNORECASE)
    for word in re.findall(r"[A-Za-z][A-Za-z0-9\-]{4,}", title):
        masked = re.sub(r"\b" + re.escape(word) + r"\b", "____", masked,
                        flags=re.IGNORECASE)
    return masked


def _build_quiz(entries, mode, cat, n, seed):
    """Deterministic multiple-choice quiz. Each question shows a masked
    description and asks which topic it describes; distractors come from the
    same category. Same seed -> same quiz (so a 'daily set' is stable)."""
    rng = _random.Random(seed)
    pool = [e for e in entries if e.get("answer") and e["cat"] in _QUIZ_CATS]
    if mode == "topic" and cat:
        pool = [e for e in pool if e["cat"] == cat]
    by_cat = defaultdict(list)
    for e in pool:
        by_cat[e["cat"]].append(e)
    if len(pool) < 4:
        return []
    rng.shuffle(pool)
    chosen = pool[:min(n, len(pool))]
    questions = []
    for e in chosen:
        siblings = [s["title"] for s in by_cat[e["cat"]] if s["title"] != e["title"]]
        if len(siblings) < 3:
            siblings = [s["title"] for s in pool if s["title"] != e["title"]]
        distractors = rng.sample(siblings, 3) if len(siblings) >= 3 else siblings[:3]
        options = distractors + [e["title"]]
        rng.shuffle(options)
        prompt = _mask_title(_first_sentences(e.get("answer", "")), e["title"])
        questions.append({
            "id": e["id"],
            "prompt": prompt,
            "options": options,
            "answer": e["title"],
            "correct_index": options.index(e["title"]),
            "difficulty": e.get("difficulty", ""),
            "frequency": e.get("frequency", ""),
            "cat": e["cat"],
            "cat_label": AI_SDE_CATEGORIES.get(e["cat"], e["cat"]),
            "explain": e.get("answer", ""),
            "mnemonic": e.get("mnemonic", ""),
            "example": e.get("example", ""),
            "diagram": e.get("diagram", ""),
        })
    return questions


@interview_prep_bp.route("/ai-sde/quiz", methods=["GET"])
@login_required
def ai_sde_quiz_page():
    return render_template("ai_sde_quiz.html")


@interview_prep_bp.route("/api/ai-sde/quiz", methods=["GET"])
@login_required
def ai_sde_quiz():
    """Generate a multiple-choice quiz from the AI SDE bank.

    mode=mixed (default) -> a stable DAILY set of 25 across all areas, seeded by
    today's date. mode=topic&cat=<key> -> fresh practice from one area."""
    items = [{"id": f"ai{i}", **e} for i, e in enumerate(AI_SDE_ENTRIES)]
    mode = (request.args.get("mode") or "mixed").strip()
    cat = (request.args.get("cat") or "").strip()
    try:
        n = max(5, min(25, int(request.args.get("n", 25))))
    except (TypeError, ValueError):
        n = 25
    if mode == "mixed":
        seed = f"mixed-{_today().isoformat()}"          # stable for the day
    else:
        # topic practice: fresh each load
        seed = f"topic-{cat}-{request.args.get('nonce', '')}-{_today().isoformat()}"
    quiz = _build_quiz(items, mode, cat, n, seed)
    return jsonify({
        "mode": mode, "cat": cat, "date": _today().isoformat(),
        "count": len(quiz), "questions": quiz,
        "categories": [{"key": k, "label": v} for k, v in AI_SDE_CATEGORIES.items()
                       if k in _QUIZ_CATS],
    })


@interview_prep_bp.route("/interview-prep/guides", methods=["GET"])
@interview_prep_bp.route("/interview-prep/guides/<slug>", methods=["GET"])
@login_required
def guides(slug=None):
    """Render a shipped markdown prep guide (e.g. the AI SDE plan) as a
    readable in-app page. Defaults to the AI SDE plan."""
    import os
    from flask import current_app, abort
    slug = slug or "ai-sde"
    entry = _GUIDES.get(slug)
    if not entry:
        abort(404)
    filename, title = entry
    path = os.path.join(current_app.root_path, filename)
    if not os.path.exists(path):
        path = os.path.join(os.getcwd(), filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.warning("guide read failed for %s: %s", filename, e)
        content = f"# {title}\n\nCould not load this guide."
    return render_template(
        "prep_guide.html", content=content, title=title, slug=slug,
        guides=[{"slug": s, "title": t} for s, (_, t) in _GUIDES.items()],
    )


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

def _valid_qid(qid):
    """True if qid is a real bank id like 'q17'."""
    if not (isinstance(qid, str) and qid.startswith("q")):
        return False
    try:
        return 0 <= int(qid[1:]) < len(QUESTIONS)
    except ValueError:
        return False


# Bank field -> override column. The bank uses short keys (s/t/a/r); the
# table stores full names.
_OVERRIDE_MAP = {"q": "question", "s": "situation", "t": "task",
                 "a": "action", "r": "result", "tip": "tip"}


@interview_prep_bp.route("/tpm-rounds", methods=["GET"])
@login_required
def tpm_rounds_page():
    """The two CASE rounds of a TPM loop — product thinking and program
    management. The behavioral round lives in the question bank and the
    design round in the system-design bank; these two had no coverage."""
    return render_template("tpm_rounds.html")


@interview_prep_bp.route("/api/tpm-rounds", methods=["GET"])
@login_required
def tpm_rounds_api():
    """Case-round bank: framework, worked answer, strong-vs-weak contrast,
    interviewer probes and pitfalls per question. Static reference content."""
    items = [{"id": f"t{i}", **e} for i, e in enumerate(TPM_ROUND_ENTRIES)]
    return jsonify({
        "rounds": [{"key": k, "label": v} for k, v in TPM_ROUNDS.items()],
        "briefs": TPM_ROUND_BRIEF,
        "entries": items,
        "total": len(items),
        "total_minutes": TPM_TOTAL_PREP_MINUTES,
    })


@interview_prep_bp.route("/api/interview-prep/questions", methods=["GET"])
@login_required
def question_bank():
    """The behavioral question bank: 100+ common questions with STAR model
    answers, grouped by competency. Static reference content, with each
    answer overlaid by the user's own edits (interview_question_overrides)
    when present, so edits persist across deploys."""
    user_id = session["user_id"]
    return jsonify({
        "categories": [{"key": k, "label": v} for k, v in QUESTION_CATEGORIES.items()],
        "questions": _beh_merged_items(user_id),
        "total": len(QUESTIONS),
    })


def _beh_merged_items(user_id):
    """Behavioral bank with the user's edits merged over the originals.
    Shared by the JSON API and the printable view."""
    items = [{"id": f"q{i}", **q, "edited": False} for i, q in enumerate(QUESTIONS)]
    try:
        overrides = get("interview_question_overrides", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "question_id,question,situation,task,action,result,tip",
            "limit": "1000",
        }) or []
    except Exception:
        overrides = []
    ovmap = {o.get("question_id"): o for o in overrides}
    for it in items:
        o = ovmap.get(it["id"])
        if not o:
            continue
        if (o.get("question") or "").strip():
            it["q"] = o["question"]
        for short, col in _OVERRIDE_MAP.items():
            if short == "q":
                continue
            if o.get(col) is not None:
                it[short] = o[col]
        it["edited"] = True
    return items


@interview_prep_bp.route("/interview-prep/behavioral/print", methods=["GET"])
@login_required
def behavioral_print():
    """Print-optimised page for the behavioral bank (browser Save-as-PDF).
    Filters: ?cat=<key>  ?tag=<tag>  ?q=<text>  ?id=qN."""
    user_id = session["user_id"]
    items = _beh_merged_items(user_id)
    cat = (request.args.get("cat") or "").strip()
    tag = (request.args.get("tag") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    one = (request.args.get("id") or "").strip()

    def _match(it):
        if one:
            return it["id"] == one
        if cat and it.get("cat") != cat:
            return False
        if tag and tag not in [t.lower() for t in (it.get("tags") or [])]:
            return False
        if q:
            hay = (it.get("q", "") + " " + " ".join(it.get("tags") or [])).lower()
            if q not in hay:
                return False
        return True

    selected = [it for it in items if _match(it)]
    label = "Behavioral Question Bank"
    if one and selected:
        label = selected[0]["q"][:80]
    elif cat:
        label = QUESTION_CATEGORIES.get(cat, cat)
    elif tag:
        label = f"Tag: #{tag}"
    elif q:
        label = f"Search: {q}"

    return render_template(
        "behavioral_print.html",
        questions=selected,
        category_labels=QUESTION_CATEGORIES,
        heading=label, count=len(selected), today=_today().isoformat(),
    )


@interview_prep_bp.route("/interview-prep/behavioral/pdf", methods=["GET"])
@login_required
def behavioral_pdf():
    """Server-generated PDF of the behavioral bank (STAR answers), same
    filters. Falls back to the print view if fpdf2 is unavailable."""
    user_id = session["user_id"]
    selected, label = _bank_select(
        _beh_merged_items(user_id), ("q",), QUESTION_CATEGORIES, "q")
    selected.sort(key=lambda it: it.get("rank") or 0)
    heading = label or "Behavioral Question Bank"
    _mins = sum(it.get("prep_minutes") or 0 for it in selected)
    subtitle = " | ".join(x for x in [
        f"{len(selected)} question{'' if len(selected) == 1 else 's'}",
        (f"{_mins // 60}h {_mins % 60}m of prep" if _mins else ""),
        "DailyPlanner Interview Prep", _today().isoformat()] if x)
    sections = [{
        "title": it["q"],
        "cat": QUESTION_CATEGORIES.get(it.get("cat"), it.get("cat", "")),
        # Planning line first, then STAR, then the two coaching blocks: what
        # separates a hire on this question, and the follow-ups they will push.
        "fields": [(" ".join(x for x in [
                        f"Prep time & priority",
                    ] if x),
                    " | ".join(x for x in [
                        (f"{it['prep_label']}" if it.get("prep_label") else ""),
                        (f"Stack rank #{it['rank']}" if it.get("rank") else ""),
                        (f"Story: {it['story_label']}" if it.get("story_label") else ""),
                        (it.get("priority_note") or "")] if x) or None),
                   ("Situation", it.get("s")), ("Task", it.get("t")),
                   ("Action", it.get("a")), ("Result", it.get("r")),
                   ("Tip", it.get("tip")),
                   ("Strong vs weak", it.get("strong_weak")),
                   ("They will push back",
                    "\n".join(f"{n}. {p}" for n, p in
                              enumerate(it.get("probes") or [], 1)) or None)],
        "arch": None, "tags": it.get("tags"),
    } for it in selected]
    try:
        pdf = _pdf_bytes(heading, subtitle, sections)
    except ImportError:
        return redirect(url_for("interview_prep.behavioral_print", **request.args.to_dict()))
    fname = (selected[0]["id"] + ".pdf") if len(selected) == 1 else "behavioral-bank.pdf"
    return _pdf_response(pdf, fname)


@interview_prep_bp.route("/api/interview-prep/questions/<qid>", methods=["POST"])
@login_required
def save_question_override(qid):
    """Upsert the user's edited copy of a bank question."""
    user_id = session["user_id"]
    if not _valid_qid(qid):
        return jsonify({"error": "Unknown question"}), 404
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()[:_MAX_TEXT]
    if not question:
        return jsonify({"error": "The question can't be empty"}), 400
    payload = {
        "user_id": user_id,
        "question_id": qid,
        "question": question,
        "situation": (data.get("situation") or "").strip()[:_MAX_TEXT] or None,
        "task": (data.get("task") or "").strip()[:_MAX_TEXT] or None,
        "action": (data.get("action") or "").strip()[:_MAX_TEXT] or None,
        "result": (data.get("result") or "").strip()[:_MAX_TEXT] or None,
        "tip": (data.get("tip") or "").strip()[:_MAX_TEXT] or None,
        "deleted_at": None,          # revive if it was previously reset
        "updated_at": _now_iso(),
    }
    try:
        post("interview_question_overrides?on_conflict=user_id,question_id",
             payload, prefer="resolution=merge-duplicates")
    except Exception as e:
        logger.exception("save question override failed: %s", e)
        return jsonify({"error": "Couldn't save — run MIGRATION_INTERVIEW_QUESTION_OVERRIDES.sql?"}), 502
    return jsonify({"ok": True})


@interview_prep_bp.route("/api/interview-prep/questions/<qid>/reset", methods=["POST"])
@login_required
def reset_question_override(qid):
    """Soft-delete the override so the original bank answer shows again."""
    user_id = session["user_id"]
    if not _valid_qid(qid):
        return jsonify({"error": "Unknown question"}), 404
    try:
        update("interview_question_overrides",
               params={"user_id": f"eq.{user_id}", "question_id": f"eq.{qid}"},
               json={"deleted_at": _now_iso()})
    except Exception as e:
        logger.exception("reset question override failed: %s", e)
        return jsonify({"error": "Couldn't reset"}), 502
    return jsonify({"ok": True})


# ─────────── system design bank ─────────────────────────────

_SD_FIELDS = ("title", "problem", "answer", "example", "use_cases",
              "arch", "disadvantages", "competing")


def _valid_sid(eid):
    if not (isinstance(eid, str) and eid.startswith("sd")):
        return False
    try:
        return 0 <= int(eid[2:]) < len(SD_ENTRIES)
    except ValueError:
        return False


# ─────────── PDF generation (server-side, pure Python) ──────

# Map the Unicode we use (box-drawing, arrows, smart punctuation) to ASCII
# so fpdf2's built-in latin-1 core fonts can render it without a bundled
# TTF. Anything still outside latin-1 is replaced rather than erroring.
_UNI_MAP = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "•": "-",
    "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "⇄": "<->", "▶": ">", "◀": "<", "▲": "^", "▼": "v",
    "─": "-", "━": "-", "│": "|", "┌": "+", "┐": "+",
    "└": "+", "┘": "+", "├": "+", "┤": "+", "┬": "+",
    "┴": "+", "┼": "+", "⬇": "v", "‹": "<", "›": ">",
    "✓": "[ok]", "≤": "<=", "≥": ">=", "²": "2",
    "₹": "Rs ", "″": '"', "′": "'",
}


def _latin1(s):
    if not s:
        return ""
    for k, v in _UNI_MAP.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _pdf_bytes(heading, subtitle, sections):
    """Build a PDF from sections. Each section:
    {title, cat, fields:[(label,text)...], arch, tags}. Raises ImportError
    if fpdf2 isn't installed (caller falls back to the print view)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    NX, NY = XPos.LMARGIN, YPos.NEXT  # each line returns to the left margin

    def cell(pdf, h, txt, **kw):
        pdf.multi_cell(0, h, txt, new_x=NX, new_y=NY, **kw)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    cell(pdf, 8, _latin1(heading))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    cell(pdf, 5, _latin1(subtitle))
    pdf.set_text_color(20, 20, 20)
    pdf.ln(2)

    for sec in sections:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(67, 56, 202)
        cell(pdf, 4, _latin1((sec.get("cat") or "").upper()))
        pdf.set_text_color(17, 24, 39)
        pdf.set_font("Helvetica", "B", 13)
        cell(pdf, 6, _latin1(sec["title"]))
        pdf.ln(0.5)
        for label, text in sec.get("fields", []):
            if not text:
                continue
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(107, 114, 128)
            cell(pdf, 4, _latin1(label.upper()))
            pdf.set_text_color(17, 24, 39)
            pdf.set_font("Helvetica", "", 10)
            cell(pdf, 4.6, _latin1(text))
            pdf.ln(0.4)
        if sec.get("arch"):
            pdf.set_font("Courier", "", 8)
            pdf.set_fill_color(245, 246, 250)
            cell(pdf, 3.8, _latin1(sec["arch"]), fill=True)
        # Optional monospace blocks (framework diagrams).
        for label, text in sec.get("mono_blocks", []):
            if not text:
                continue
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(107, 114, 128)
            cell(pdf, 4, _latin1(label.upper()))
            pdf.set_text_color(17, 24, 39)
            pdf.set_font("Courier", "", 8)
            pdf.set_fill_color(245, 246, 250)
            cell(pdf, 3.8, _latin1(text), fill=True)
        if sec.get("tags"):
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(67, 56, 202)
            cell(pdf, 4, _latin1("  ".join("#" + t for t in sec["tags"])))
            pdf.set_text_color(17, 24, 39)
        pdf.ln(3.5)

    return bytes(pdf.output())


def _bank_select(items, text_fields, categories, title_key):
    """Apply ?cat/?tag/?q/?id filters (from request.args) and return
    (selected_items, human_label)."""
    cat = (request.args.get("cat") or "").strip()
    tag = (request.args.get("tag") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    one = (request.args.get("id") or "").strip()

    def _match(it):
        if one:
            return it["id"] == one
        if cat and it.get("cat") != cat:
            return False
        if tag and tag not in [t.lower() for t in (it.get("tags") or [])]:
            return False
        if q:
            hay = " ".join(str(it.get(f) or "") for f in text_fields).lower()
            hay += " " + " ".join(it.get("tags") or [])
            if q not in hay:
                return False
        return True

    selected = [it for it in items if _match(it)]
    label = None
    if one and selected:
        label = str(selected[0].get(title_key, ""))[:80]
    elif cat:
        label = categories.get(cat, cat)
    elif tag:
        label = f"Tag: #{tag}"
    elif q:
        label = f"Search: {q}"
    return selected, label


def _pdf_response(pdf, filename):
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{filename}"',
    })


def _sd_merged_items(user_id):
    """The full system-design bank with the user's edits merged over the
    static originals. Shared by the JSON API and the printable view."""
    items = [{"id": f"sd{i}", **e, "edited": False} for i, e in enumerate(SD_ENTRIES)]
    try:
        overrides = get("system_design_overrides", {
            "user_id": f"eq.{user_id}", "deleted_at": "is.null",
            "select": "entry_id,title,problem,answer,example,use_cases,arch,disadvantages,competing",
            "limit": "1000",
        }) or []
    except Exception:
        overrides = []
    ovmap = {o.get("entry_id"): o for o in overrides}
    for it in items:
        o = ovmap.get(it["id"])
        if not o:
            continue
        if (o.get("title") or "").strip():
            it["title"] = o["title"]
        for f in _SD_FIELDS:
            if f == "title":
                continue
            if o.get(f) is not None:
                it[f] = o[f]
        it["edited"] = True
    return items


@interview_prep_bp.route("/api/interview-prep/system-design", methods=["GET"])
@login_required
def system_design_bank():
    """The system-design knowledge bank: building blocks, data stores,
    data platforms, analytics, data modeling, classic (Alex Xu) designs,
    AI solutions, information security and e-commerce scenarios — each
    with problem/answer/example/architecture/disadvantages/competing tech
    and tags. User edits (system_design_overrides) merged in."""
    user_id = session["user_id"]
    return jsonify({
        "categories": [{"key": k, "label": v} for k, v in SD_CATEGORIES.items()],
        "entries": _sd_merged_items(user_id),
        "total": len(SD_ENTRIES),
    })


@interview_prep_bp.route("/interview-prep/system-design/print", methods=["GET"])
@login_required
def system_design_print():
    """A clean, print-optimised page for the bank — one entry per section
    with every field. The browser's 'Save as PDF' turns it into a PDF
    (no server-side PDF library, no blobs in the DB). Filters:
    ?cat=<key>  ?tag=<tag>  ?q=<text>  ?id=sdN  (any combination)."""
    user_id = session["user_id"]
    items = _sd_merged_items(user_id)

    cat = (request.args.get("cat") or "").strip()
    tag = (request.args.get("tag") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    one = (request.args.get("id") or "").strip()

    def _match(it):
        if one:
            return it["id"] == one
        if cat and it.get("cat") != cat:
            return False
        if tag and tag not in [t.lower() for t in (it.get("tags") or [])]:
            return False
        if q:
            hay = " ".join(str(it.get(f) or "") for f in
                           ("title", "answer", "problem", "competing")).lower()
            hay += " " + " ".join(it.get("tags") or [])
            if q not in hay:
                return False
        return True

    selected = [it for it in items if _match(it)]

    # Human title for the header / filename hint.
    label = "System Design Bank"
    if one and selected:
        label = selected[0]["title"]
    elif cat:
        label = SD_CATEGORIES.get(cat, cat)
    elif tag:
        label = f"Tag: #{tag}"
    elif q:
        label = f"Search: {q}"

    return render_template(
        "system_design_print.html",
        entries=selected,
        category_labels=SD_CATEGORIES,
        detail_order=SD_DETAIL_ORDER,
        heading=label,
        count=len(selected),
        today=_today().isoformat(),
    )


@interview_prep_bp.route("/interview-prep/system-design/pdf", methods=["GET"])
@login_required
def system_design_pdf():
    """Server-generated PDF of the system-design bank (same ?cat/?tag/?q/?id
    filters, user edits merged). Falls back to the print view if fpdf2 is
    unavailable."""
    user_id = session["user_id"]
    selected, label = _bank_select(
        _sd_merged_items(user_id),
        ("title", "answer", "problem", "competing"), SD_CATEGORIES, "title")
    heading = label or "System Design Bank"
    subtitle = (f"{len(selected)} entr{'y' if len(selected) == 1 else 'ies'} "
                f"| DailyPlanner Interview Prep | {_today().isoformat()}")
    sections = []
    for it in selected:
        fields = [("Problem it solves", it.get("problem")),
                  ("Approach", it.get("answer")),
                  ("Example", it.get("example")),
                  ("Use cases", it.get("use_cases")),
                  ("Disadvantages", it.get("disadvantages")),
                  ("Competing technologies", it.get("competing"))]
        mono_blocks = []
        detail = it.get("detail")
        if detail:
            for key, label, is_mono in SD_DETAIL_ORDER:
                val = detail.get(key)
                if not val:
                    continue
                if is_mono:
                    mono_blocks.append((label, val))
                else:
                    fields.append((label, val))
        sections.append({
            "title": it["title"],
            "cat": SD_CATEGORIES.get(it.get("cat"), it.get("cat", "")),
            "fields": fields, "arch": it.get("arch"),
            "mono_blocks": mono_blocks, "tags": it.get("tags"),
        })
    try:
        pdf = _pdf_bytes(heading, subtitle, sections)
    except ImportError:
        return redirect(url_for("interview_prep.system_design_print", **request.args.to_dict()))
    fname = (selected[0]["id"] + ".pdf") if len(selected) == 1 else "system-design-bank.pdf"
    return _pdf_response(pdf, fname)


# ─────────── integration: pull related material from the user's library ──

_KW_STOP = {"design", "system", "service", "distributed", "scale", "real",
            "time", "with", "and", "the", "for", "your", "using", "based"}


def _entry_keywords(title, tags):
    kws = {t.lower() for t in (tags or []) if isinstance(t, str)}
    for w in re.split(r"[^a-z0-9+]+", (title or "").lower()):
        if len(w) > 3 and w not in _KW_STOP:
            kws.add(w)
    return kws


@interview_prep_bp.route("/api/interview-prep/system-design/<eid>/related", methods=["GET"])
@login_required
def system_design_related(eid):
    """Pull items from the user's own References and Travel Reads that
    relate to this design (by tag overlap / keyword), so the bank is
    seamlessly connected to their saved knowledge."""
    user_id = session["user_id"]
    if not _valid_sid(eid):
        return jsonify({"references": [], "travel_reads": []})
    entry = SD_ENTRIES[int(eid[2:])]
    kws = _entry_keywords(entry["title"], entry.get("tags"))
    long_kws = {k for k in kws if len(k) > 4}

    references = []
    try:
        rows = get("reference_links", {
            "user_id": f"eq.{user_id}",
            "select": "id,title,description,url,tags,category", "limit": "1000",
        }) or []
        scored = []
        for r in rows:
            rtags = {t.lower() for t in (r.get("tags") or []) if isinstance(t, str)}
            text = f"{r.get('title') or ''} {r.get('description') or ''}".lower()
            score = 2 * len(rtags & kws) + sum(1 for k in long_kws if k in text)
            if score:
                scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        references = [{"title": r.get("title") or r.get("url"), "url": r.get("url"),
                       "category": r.get("category"), "tags": r.get("tags") or []}
                      for _, r in scored[:6]]
    except Exception as e:
        logger.warning("related references lookup failed: %s", e)

    travel_reads = []
    try:
        rows = get("travel_reads", {
            "user_id": f"eq.{user_id}", "archived_at": "is.null",
            "select": "id,title,description,url,source,kind,status", "limit": "500",
        }) or []
        scored = []
        for t in rows:
            text = f"{t.get('title') or ''} {t.get('description') or ''} {t.get('source') or ''}".lower()
            score = sum(1 for k in long_kws if k in text)
            if score:
                scored.append((score, t))
        scored.sort(key=lambda x: -x[0])
        travel_reads = [{"title": t.get("title") or t.get("url"), "url": t.get("url"),
                         "source": t.get("source"), "kind": t.get("kind")}
                        for _, t in scored[:5]]
    except Exception as e:
        logger.warning("related travel_reads lookup failed: %s", e)

    # Knowledge Base: match PDF filenames in the user's Drive KB folder.
    # Best-effort — only if Drive is connected and the folder already
    # exists (we never create it here).
    knowledge_base = []
    try:
        from routes.knowledgebase import (_load_token_row, _row_has_drive_scope,
                                          _credentials_from_row, _refresh_if_needed,
                                          _build_drive)
        row = _load_token_row(user_id)
        folder = (row or {}).get("kb_folder_id")
        if row and folder and _row_has_drive_scope(row):
            service = _build_drive(_refresh_if_needed(_credentials_from_row(row), user_id))
            listed = service.files().list(
                q=f"'{folder}' in parents and mimeType='application/pdf' and trashed=false",
                fields="files(id,name,webViewLink)", pageSize=200,
            ).execute().get("files", [])
            scored = []
            for f in listed:
                name = (f.get("name") or "").lower()
                score = sum(1 for k in long_kws if k in name)
                if score:
                    scored.append((score, f))
            scored.sort(key=lambda x: -x[0])
            knowledge_base = [{"title": f.get("name"), "url": f.get("webViewLink")}
                              for _, f in scored[:5]]
    except Exception as e:
        logger.warning("related KB lookup failed: %s", e)

    return jsonify({"references": references, "travel_reads": travel_reads,
                    "knowledge_base": knowledge_base})


@interview_prep_bp.route("/api/interview-prep/system-design/<eid>/save-reference", methods=["POST"])
@login_required
def system_design_save_reference(eid):
    """Push a design into the user's References library (two-way link) so
    it's searchable alongside their saved articles."""
    user_id = session["user_id"]
    if not _valid_sid(eid):
        return jsonify({"error": "Unknown entry"}), 404
    items = _sd_merged_items(user_id)
    entry = next((it for it in items if it["id"] == eid), None)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    desc = (entry.get("problem") or "")
    if entry.get("answer"):
        desc = (desc + " — " + entry["answer"])[:600]
    payload = {
        "user_id": user_id,
        "title": entry["title"],
        "description": desc or None,
        "url": url_for("interview_prep.system_design_pdf", id=eid, _external=False),
        "tags": entry.get("tags") or [],
        "category": "System Design",
    }
    try:
        post("reference_links", payload)
    except Exception as e:
        logger.exception("save design to references failed: %s", e)
        return jsonify({"error": "Couldn't save to References"}), 502
    return jsonify({"ok": True})


@interview_prep_bp.route("/api/interview-prep/system-design/<eid>", methods=["POST"])
@login_required
def save_system_design_override(eid):
    user_id = session["user_id"]
    if not _valid_sid(eid):
        return jsonify({"error": "Unknown entry"}), 404
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:_MAX_TITLE]
    if not title:
        return jsonify({"error": "The title can't be empty"}), 400
    payload = {"user_id": user_id, "entry_id": eid, "title": title,
               "deleted_at": None, "updated_at": _now_iso()}
    for f in _SD_FIELDS:
        if f == "title":
            continue
        payload[f] = (data.get(f) or "").strip()[:_MAX_TEXT] or None
    try:
        post("system_design_overrides?on_conflict=user_id,entry_id",
             payload, prefer="resolution=merge-duplicates")
    except Exception as e:
        logger.exception("save system design override failed: %s", e)
        return jsonify({"error": "Couldn't save — run MIGRATION_SYSTEM_DESIGN_OVERRIDES.sql?"}), 502
    return jsonify({"ok": True})


@interview_prep_bp.route("/api/interview-prep/system-design/<eid>/reset", methods=["POST"])
@login_required
def reset_system_design_override(eid):
    user_id = session["user_id"]
    if not _valid_sid(eid):
        return jsonify({"error": "Unknown entry"}), 404
    try:
        update("system_design_overrides",
               params={"user_id": f"eq.{user_id}", "entry_id": f"eq.{eid}"},
               json={"deleted_at": _now_iso()})
    except Exception as e:
        logger.exception("reset system design override failed: %s", e)
        return jsonify({"error": "Couldn't reset"}), 502
    return jsonify({"ok": True})


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
    payload = {
        "user_id": user_id, "title": title,
        "competency": (data.get("competency") or "").strip()[:_MAX_TITLE] or None,
        "position": 999,
    }
    # Optional STAR prefill (used by "Use as my story" from the question bank).
    for f in ("situation", "task", "action", "result"):
        if data.get(f):
            payload[f] = str(data.get(f)).strip()[:_MAX_TEXT] or None
    try:
        rows = post("interview_stories", payload)
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

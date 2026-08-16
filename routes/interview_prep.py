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
import threading
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
# Imported for the scheduler's bank registry only. java_bank is a plain
# data module — it imports no routes, so this cannot cycle.
import java_bank
import ai_sde_recall
import ai_sde_summary
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
    # The AI SDE track (see MIGRATION_AI_SDE_PREP_TRACK.sql). The coach is
    # shared by two very different runs — a senior TPM loop and a new-grad
    # AI/SDE loop — and without these its own category headings would show
    # raw keys like "dsa" on the student's page.
    "dsa": "Coding & DSA",
    "cs_fundamentals": "CS Fundamentals",
    "ml": "ML & AI Concepts",
    "ai_llm": "LLMs & Modern AI",
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


# ── The list payload, and why it is only a sliver of each entry ───────
#
# The bank is 1,120 entries and a written-up topic runs to ~16k characters
# across answer / walkthrough / plain_algo / code / examples. Serialising all
# of it produced a 3 MB JSON body on every single page load — and the list
# screen shows NONE of it, because every card is collapsed until clicked.
# Worse, the client rebuilt all 1,120 card bodies as one HTML string on every
# keystroke in the search box.
#
# So the list ships only what the collapsed header, the filters and the sort
# actually read. Everything else arrives per-card from /api/ai-sde/entry/<id>
# when the card is opened. 3 MB -> ~700 KB, and ~80 KB once gzipped.
_AI_SDE_LIST_FIELDS = (
    # Header
    "title", "cat", "difficulty", "priority", "priority_note", "prep_label",
    "tag_priority", "tag_subtopic", "tag_topic",
    # Filters
    "tag_level", "tag_format", "tag_stage", "tag_time", "tag_flag",
    # Sort, the effort line, and the "prep time & priority" line in the body
    "rank", "cat_rank", "prep_minutes", "priority_label", "priority_rank",
    "priority_total", "priority_minutes_total", "priority_minutes_cumulative",
)

#: Fields the list deliberately omits — the body of the card. Kept as an
#: explicit list rather than "everything not in _AI_SDE_LIST_FIELDS" so that
#: adding a field to the bank is a conscious decision about which side of the
#: line it falls on, not a silent 3 MB regression.
_AI_SDE_BODY_FIELDS = (
    "frequency", "answer", "walkthrough", "plain_algo", "code", "diagram",
    "example", "mnemonic", "complexity", "pitfalls", "followups", "tags",
)


def _build_ai_sde_list():
    """The thin list, built once at import rather than per request.

    The bank is a static Python literal — it cannot change between requests,
    so rebuilding 1,120 dicts on every call was pure waste (~27 ms of the
    response, before any network).
    """
    items = []
    for i, e in enumerate(AI_SDE_ENTRIES):
        item = {"id": f"ai{i}", "example_count": len(e.get("examples") or [])}
        for k in _AI_SDE_LIST_FIELDS:
            v = e.get(k)
            # Drop empties: across 1,120 entries the absent keys alone are
            # tens of kilobytes of `"field":null`.
            if v not in (None, "", [], {}):
                item[k] = v
        items.append(item)
    return items


def _build_ai_sde_search_index():
    """One lowercase haystack per entry, for server-side search.

    Held in the process (~1.2 MB) rather than shipped to every client. This
    also WIDENS search: it used to match title / answer / tags only, because
    those were the only fields the browser had. It now covers the worked
    walkthrough, the plain-English recipe, the code and the examples, which
    is what you actually want when hunting for where `heapq` or "monotonic"
    is discussed.
    """
    index = []
    for e in AI_SDE_ENTRIES:
        parts = [str(e.get("title") or "")]
        for k in _AI_SDE_BODY_FIELDS:
            v = e.get(k)
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, (list, tuple)):
                parts.append(" ".join(str(x) for x in v))
        parts.extend(str(x) for x in (e.get("examples") or []))
        index.append(" ".join(parts).lower())
    return index


_AI_SDE_LIST = _build_ai_sde_list()
_AI_SDE_SEARCH = _build_ai_sde_search_index()

#: subtopic -> sibling titles, for the quiz's transfer question. Built once;
#: doing it per entry would be quadratic over 1,120 entries.
_AI_SDE_SIBLINGS = ai_sde_recall.build_sibling_index(AI_SDE_ENTRIES)

#: Built once at import, same reason as the list: the bank is a static
#: Python literal and cannot change between requests.
_AI_SDE_SUMMARIES = ai_sde_summary.build(AI_SDE_ENTRIES)
_AI_SDE_READING_COUNTS = ai_sde_summary.counts(AI_SDE_ENTRIES)


@interview_prep_bp.route("/api/ai-sde", methods=["GET"])
@login_required
def ai_sde_bank():
    """The AI SDE prep bank: DSA patterns (with worked code), ML/AI
    concepts, ML coding, ML system design, CS fundamentals, behavioral and
    company process — each explained in depth. Static reference content.

    Headers only — see _AI_SDE_LIST_FIELDS. Card bodies come from
    /api/ai-sde/entry/<id> as they are opened.
    """
    return jsonify({
        "categories": [{"key": k, "label": v} for k, v in AI_SDE_CATEGORIES.items()],
        "entries": _AI_SDE_LIST, "total": len(_AI_SDE_LIST),
        # The interview-tag vocabulary, so the filter dropdowns are built from
        # the single source of truth in ai_sde_tags.py rather than a hardcoded
        # copy in the template that would drift the moment a value is added.
        "tag_vocab": _ai_sde_tag_vocab(),
        # The must-read / optional split. The RULE travels rather than the
        # answer, so the page filters on tag_priority — which it already
        # has for every row — instead of the list carrying a second field
        # per entry that says the same thing.
        "reading": {
            "mandatory_tag": ai_sde_summary.MANDATORY_TAG,
            "mandatory_priority": ai_sde_summary.MANDATORY_PRIORITY,
            "rule": ai_sde_summary.RULE_TEXT,
            "counts": _AI_SDE_READING_COUNTS,
        },
    })


@interview_prep_bp.route("/api/ai-sde/summaries", methods=["GET"])
@login_required
def ai_sde_summaries():
    """One line per topic, for skimming without opening anything.

    A SEPARATE request on purpose. Folded into /api/ai-sde these take the
    list from 57 KB gzipped to 135 KB — more than doubling the payload
    that page load actually waits on, to add a line she may not read on
    most rows. Fetched after the list has rendered, they cost nothing
    anyone is waiting for, and a page that never gets them is a page
    without summaries rather than a page that failed.
    """
    return jsonify({"summaries": _AI_SDE_SUMMARIES,
                    "total": len(_AI_SDE_SUMMARIES)})


@interview_prep_bp.route("/api/ai-sde/search", methods=["GET"])
@login_required
def ai_sde_search():
    """Ids of the entries matching `q`, for the client to intersect with its
    own filters.

    Search moved to the server when the card bodies stopped being shipped —
    the browser no longer holds the prose to search. Returning ids rather
    than entries keeps this a few kilobytes and leaves every other filter
    (category, difficulty, the six interview tags, unstudied) client-side and
    instant.

    Multiple words are ANDed, which matches how people narrow a list.
    """
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"q": "", "ids": None, "total": len(_AI_SDE_LIST)})
    terms = [t for t in q.split() if t][:8]      # a cap, so a pasted essay is cheap
    ids = [f"ai{i}" for i, hay in enumerate(_AI_SDE_SEARCH)
           if all(t in hay for t in terms)]
    return jsonify({"q": q, "ids": ids, "total": len(ids)})


#: Query-string name -> entry field, for the six filterable interview tags.
_AI_SDE_TAG_PARAMS = {
    "tpriority": "tag_priority", "ttopic": "tag_topic", "tsub": "tag_subtopic",
    "tformat": "tag_format", "tstage": "tag_stage", "ttime": "tag_time",
    "tlevel": "tag_level",
}


def _ai_sde_tag_vocab():
    """The controlled vocabulary, plus the per-topic subtopic map."""
    import ai_sde_tags as tags
    return {
        "topic": list(tags.TOPICS), "level": list(tags.LEVELS),
        "priority": list(tags.PRIORITIES), "format": list(tags.FORMATS),
        "stage": list(tags.STAGES), "time": list(tags.TIMES),
        "subtopics": {k: list(v) for k, v in tags.SUBTOPICS.items()},
    }


def _ai_sde_tag_select(items):
    """Narrow by the interview tags. Returns (items, [label bits]).

    Unknown values are ignored rather than returning an empty page, because a
    stale bookmark should degrade to a wider list, not to nothing.
    """
    vocab = _ai_sde_tag_vocab()
    legal = {
        "tag_topic": set(vocab["topic"]), "tag_level": set(vocab["level"]),
        "tag_priority": set(vocab["priority"]), "tag_format": set(vocab["format"]),
        "tag_stage": set(vocab["stage"]), "tag_time": set(vocab["time"]),
        "tag_subtopic": {s for subs in vocab["subtopics"].values() for s in subs},
    }
    bits = []
    for param, field in _AI_SDE_TAG_PARAMS.items():
        value = (request.args.get(param) or "").strip()
        if not value or value not in legal[field]:
            continue
        items = [it for it in items if it.get(field) == value]
        bits.append(value)
    return items, bits


@interview_prep_bp.route("/api/ai-sde/entry/<entry_id>", methods=["GET"])
@login_required
def ai_sde_entry(entry_id):
    """The whole body of one topic, fetched when its card is opened.

    This used to return only `examples`. It now carries every field in
    _AI_SDE_BODY_FIELDS as well, because the list endpoint stopped shipping
    them — one request per card actually opened, instead of 1,120 bodies on
    page load for the handful anyone reads.
    """
    try:
        idx = int(entry_id[2:]) if entry_id.startswith("ai") else -1
    except ValueError:
        idx = -1
    if not 0 <= idx < len(AI_SDE_ENTRIES):
        return jsonify({"error": "unknown entry"}), 404
    e = AI_SDE_ENTRIES[idx]
    body = {k: e[k] for k in _AI_SDE_BODY_FIELDS if e.get(k) not in (None, "", [], {})}
    body["id"] = entry_id
    body["examples"] = e.get("examples") or []
    # The recall quiz rides along with the body rather than costing a second
    # round trip — it is derived from these very fields, so it is already
    # paid for. See ai_sde_recall.py for why none of it is hand-written.
    body["quiz"] = ai_sde_recall.build(e, _AI_SDE_SIBLINGS)
    return jsonify(body)


# ══════════════════════════════════════════════════════════════════════
# AI SDE → CALENDAR — drop a topic onto a specific day
#
# The ask was a study plan you can *see*: pick a topic on /ai-sde, pick a
# day, and have it show up in the three places that already exist rather
# than in a fourth one invented for it —
#
#   * the AISDEPrep project, so the whole syllabus has one home;
#   * the calendar grid for that day;
#   * the Quick Bucket, so it is in front of her without opening the
#     calendar at all.
#
# WHY MIDNIGHT WHEN NO TIME IS GIVEN. planner_v2.js builds the grid with
# `for (let hour = 0; hour < 24; hour++)`, so hour 0 is the first row on
# the page. A 00:00 start therefore pins the topic to the very top of the
# day the way an all-day row does in Google Calendar — visible the moment
# the day opens, and out of the way of anything actually timed. It is a
# deliberate position, not a null standing in for one.
#
# WHY THIS DOES NOT POST TO /api/v2/events. That endpoint runs
# get_conflicts() and returns 409 unless the caller forces it. Stacking
# five topics at 00:00 on the same morning is the *intended* use here, so
# every one after the first would be rejected for overlapping the last.
# This writes the daily_events row directly, which is the same table the
# calendar reads.
#
# Three inserts, no transaction. If a later one fails the earlier ones
# survive, which is the right way round: the project task is the record
# of what she planned to study, and the other two are views onto it.
# ══════════════════════════════════════════════════════════════════════

#: The banks that can be scheduled onto a day, and the project each one
#: lands in. Looked up by name — there is no project id stored anywhere,
#: because the name IS the handle.
#:
#: Each bank names the list its entries come from, the FIELD that holds
#: the topic's text (the behavioural bank calls it `q`, the other two
#: `title`), and the prefix its ids carry. Keeping the three differences
#: in a table beats three near-identical endpoints: the scheduling itself
#: — get-or-create the project, write the task, the event, the bucket row,
#: mirror to Google — is the same work whichever bank asked for it.
PREP_BANKS = {
    "ai_sde": {
        "project": "AISDEPrep",
        "desc": "AI/SDE interview prep. Topics scheduled from /ai-sde land here.",
        "label": "AI/SDE prep",
        "page": "/ai-sde",
    },
    "java": {
        "project": "JavaPrep",
        "desc": "Java core interview prep. Topics scheduled from /java land here.",
        "label": "Java prep",
        "page": "/java",
    },
    "behavioral": {
        "project": "InterviewPrep",
        "desc": "Behavioural / TPM interview prep. Questions scheduled from "
                "/interview-prep land here.",
        "label": "Interview prep",
        "page": "/interview-prep",
    },
}

#: bank key -> (entry list, the field holding the topic text, id prefix).
#: A callable for the list so the module-level import order cannot matter.
_BANK_SOURCES = {
    "ai_sde":     (lambda: AI_SDE_ENTRIES,     "title", "ai"),
    "java":       (lambda: java_bank.ENTRIES,  "title", "j"),
    "behavioral": (lambda: QUESTIONS,          "q",     "q"),
}

# Kept as the old names because MIGRATION_AISDEPREP.sql seeds this one by
# name and the tests assert on it.
AI_SDE_PROJECT_NAME = PREP_BANKS["ai_sde"]["project"]
AI_SDE_PROJECT_DESC = PREP_BANKS["ai_sde"]["desc"]

AI_SDE_MIDNIGHT = "00:00"

#: Bounds on the calendar block. The floor stops a 5-minute topic from
#: rendering as an unclickable sliver; the ceiling stops a 6-hour one
#: from swallowing the whole day in a single bar. Anything longer is a
#: multi-session topic and wants more than one calendar entry anyway.
AI_SDE_MIN_BLOCK = 15
AI_SDE_MAX_BLOCK = 180
AI_SDE_DEFAULT_BLOCK = 30

_AI_SDE_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_AI_SDE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _pg_eq(value):
    """A PostgREST ``eq.`` filter for a free-text value.

    386 of the 1,120 topic titles contain a comma, a parenthesis or a
    colon — "Precision vs Recall (and the 95%-accuracy trap)" — and
    PostgREST reads every one of those as filter syntax rather than as
    part of the value. Quoting turns it back into a value; a double quote
    inside is backslash-escaped, being the one character the quoting
    can't cover by itself.
    """
    return 'eq."' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _get_optional(table, params, optional):
    """``get()`` that survives a filter column the install doesn't have yet.

    ``post()`` and ``update()`` already strip a column Supabase reports as
    missing and retry; ``get()`` does not, so a filter on a column added by
    a migration that hasn't been run raises 400 and the whole request
    500s. That is exactly what happened here: ``project_tasks.is_deleted``
    is in MIGRATION_ALL_TABLES.sql but an older install never got the
    line, and the dedupe lookup filters on it.

    Retries once with `optional` keys dropped. Dropping them widens the
    result — a soft-deleted row would come back — and for the two callers
    here that is the safe direction: it makes "already scheduled" more
    likely, and the failure mode of that is a no-op instead of a
    duplicate.
    """
    try:
        return get(table, params=params) or []
    except Exception:
        trimmed = {k: v for k, v in params.items() if k not in optional}
        if trimmed == params:
            raise
        logger.warning("%s: retrying lookup without %s — run MIGRATION_AISDEPREP.sql",
                       table, ", ".join(sorted(optional)))
        return get(table, params=trimmed) or []


def _ai_sde_clean_time(raw):
    """``"9:05"`` → ``"09:05"``; empty or unparseable → midnight.

    An unreadable time is not an error here. The caller asked to schedule
    a topic; refusing over a malformed time field would throw the whole
    request away to protect a field that has a documented default.
    """
    m = _AI_SDE_TIME_RE.match((raw or "").strip())
    if not m:
        return AI_SDE_MIDNIGHT
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _ai_sde_end_time(start, minutes):
    """End of the calendar block, clamped inside the same day.

    A block that would spill past midnight is cut to 23:59 rather than
    wrapping — wrapping would put half the study session on a day the
    user never picked, and the grid would draw it there.
    """
    try:
        length = int(minutes)
    except (TypeError, ValueError):
        length = AI_SDE_DEFAULT_BLOCK
    length = max(AI_SDE_MIN_BLOCK, min(length or AI_SDE_DEFAULT_BLOCK, AI_SDE_MAX_BLOCK))

    base = datetime.strptime(start, "%H:%M")
    end = base + timedelta(minutes=length)
    if end.day != base.day:          # crossed into tomorrow
        return "23:59"
    return end.strftime("%H:%M")


def _ensure_prep_project(user_id, bank):
    """Return the project id for this bank, creating it if it isn't there.

    Select-then-insert, and on an insert failure it selects again: the
    partial unique index from MIGRATION_AISDEPREP.sql turns a double-tap
    race into a constraint error, and the row the other request just
    created is exactly what this one wanted. Returns None if the project
    genuinely cannot be resolved, and the caller reports that rather than
    scattering tasks into a project that doesn't exist.
    """
    spec = PREP_BANKS[bank]
    name = spec["project"]

    def _find():
        rows = get("projects", params={
            "user_id": f"eq.{user_id}",
            "name": _pg_eq(name),
            "is_archived": "eq.false",
            "select": "project_id",
            "limit": "1",
        }) or []
        return rows[0]["project_id"] if rows else None

    found = _find()
    if found:
        return found

    try:
        created = post("projects", {
            "user_id": user_id,
            "name": name,
            "description": spec["desc"],
            "is_archived": False,
        }, prefer="return=representation")
        if created:
            return created[0]["project_id"]
    except Exception:
        logger.warning("%s project insert failed; re-selecting", name, exc_info=True)

    return _find()


def _ensure_ai_sde_project(user_id):
    """Back-compat shim for the AI/SDE bank's own project."""
    return _ensure_prep_project(user_id, "ai_sde")


def _prep_lookup(bank, entry_id, title):
    """Resolve the topic being scheduled to (title, prep_minutes).

    The id is honoured when it still points at the same topic, but the
    TITLE is what decides — every one of these banks numbers its entries
    by POSITION (``ai42``, ``j7``, ``q19``), and a position shifts the
    moment an entry is added or deduped. It is the same reason progress
    and recall are keyed by title. A stale tab holding ``ai42`` must not
    schedule whatever moved into slot 42 since it loaded.

    Returns (None, None) when neither the id nor the title resolves, and
    the caller 404s rather than scheduling a guess.
    """
    source, field, prefix = _BANK_SOURCES[bank]
    entries = source()
    title = (title or "").strip()

    idx = -1
    if entry_id and entry_id.startswith(prefix):
        try:
            idx = int(entry_id[len(prefix):])
        except ValueError:
            idx = -1

    if 0 <= idx < len(entries):
        e = entries[idx]
        if not title or e[field] == title:
            return e[field], e.get("prep_minutes")

    # Id was missing, out of range, or has drifted — fall back to the title.
    for e in entries:
        if e[field] == title:
            return e[field], e.get("prep_minutes")
    return None, None


def _ai_sde_lookup(entry_id, title):
    """Back-compat shim for the AI/SDE bank."""
    return _prep_lookup("ai_sde", entry_id, title)


@interview_prep_bp.route("/api/prep/schedule", methods=["POST"])
@interview_prep_bp.route("/api/ai-sde/schedule", methods=["POST"])
@login_required
def prep_schedule():
    """Put one topic from one bank on one day.

    Body: ``{bank?, id?, title?, plan_date, start_time?, duration_min?,
    quick_bucket?}``. ``bank`` is a key of PREP_BANKS and decides which
    project the topic lands in; it defaults to ``ai_sde`` so the older
    /api/ai-sde/schedule path keeps working for a page served from cache.
    Either ``id`` or ``title`` identifies the topic; ``plan_date`` is
    required; everything else has a default.

    Idempotent per (bank, topic, day): tapping Plan twice for the same
    topic on the same date reports what is already there instead of
    stacking a second copy of it in all three places.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    bank = (data.get("bank") or "ai_sde").strip()
    if bank not in PREP_BANKS:
        return jsonify({"error": f"unknown bank {bank!r}"}), 400

    plan_date = (data.get("plan_date") or "").strip()
    if not _AI_SDE_DATE_RE.match(plan_date):
        return jsonify({"error": "plan_date must be YYYY-MM-DD"}), 400
    try:
        date.fromisoformat(plan_date)
    except ValueError:
        return jsonify({"error": "plan_date is not a real date"}), 400

    title, prep_minutes = _prep_lookup(bank, data.get("id"), data.get("title"))
    if not title:
        return jsonify({"error": "unknown topic"}), 404

    start_time = _ai_sde_clean_time(data.get("start_time"))
    end_time = _ai_sde_end_time(start_time, data.get("duration_min") or prep_minutes)
    untimed = start_time == AI_SDE_MIDNIGHT and not (data.get("start_time") or "").strip()

    spec = PREP_BANKS[bank]
    project_id = _ensure_prep_project(user_id, bank)
    if not project_id:
        return jsonify({"error": f"could not open the {spec['project']} project"}), 500

    # ── Already on this day? ────────────────────────────────────────
    existing = _get_optional("project_tasks", {
        "user_id": f"eq.{user_id}",
        "project_id": f"eq.{project_id}",
        "plan_date": f"eq.{plan_date}",
        "task_text": _pg_eq(title),
        "is_deleted": "eq.false",
        "select": "task_id",
        "limit": "1",
    }, optional={"is_deleted"})
    if existing:
        # The time comes from the daily_events row, not the task — the task
        # deliberately carries no start_time (see below) — and re-reading it
        # to echo it back is not worth a round trip. The day is the answer
        # she needs; the calendar shows the rest.
        return jsonify({
            "status": "already-scheduled",
            "project_id": project_id,
            "task_id": existing[0]["task_id"],
            "plan_date": plan_date,
            "message": f"Already on {plan_date}.",
        })

    # ── 1. The project task — the record of what she planned ────────
    #
    # NOTE THE ABSENT start_time. The calendar page draws BOTH sources:
    # planner_v2.js fetches /api/v2/events AND /api/v2/project-tasks, then
    # renders `taskData.filter(t => t.start_time)` as chips alongside the
    # events. Setting it here put the same topic on the grid twice — once
    # as its event, once as its task — which is what "tasks repeating
    # twice in the calendar" was.
    #
    # The event is the one that survives, because it is the row the grid
    # treats as a real appointment: its own end_time (so the block is the
    # topic's actual prep length rather than the flat 30 minutes the task
    # renderer assumes) and the Google mirror hangs off it. The task keeps
    # plan_date as the record of which day it belongs to.
    task_payload = {
        "user_id": user_id,
        "project_id": project_id,
        "task_text": title,
        "status": "open",
        "priority": "medium",
        "plan_date": plan_date,
        "due_date": plan_date,
        "notes": f"{spec['label']} topic · scheduled from {spec['page']}",
        "is_deleted": False,
    }
    if prep_minutes:
        task_payload["planned_hours"] = round(prep_minutes / 60.0, 2)
    # Link it to the project's default epic when the OKR trio resolves, so
    # the task appears in the project tree rather than only in flat views.
    try:
        from routes.projects import _default_epic_id
        epic_id = _default_epic_id(user_id, project_id)
        if epic_id:
            task_payload["epic_id"] = epic_id
    except Exception:
        logger.warning("%s: default epic unresolved, filing task flat", spec["project"],
                       exc_info=True)

    task_rows = post("project_tasks", task_payload, prefer="return=representation")
    task_id = (task_rows or [{}])[0].get("task_id")

    # ── 2. The calendar row ─────────────────────────────────────────
    # Written straight to daily_events, not through POST /api/v2/events —
    # see the block comment above for why the conflict check would reject
    # the second topic stacked at midnight.
    event_id, event_row = None, None
    try:
        ev = post("daily_events", {
            "user_id": user_id,
            "plan_date": plan_date,
            "start_time": start_time,
            "end_time": end_time,
            "title": title,
            "description": f"{spec['label']} — open the topic at {spec['page']}",
            "priority": "medium",
            "reminder_minutes": 10,
            "is_deleted": False,
        }, prefer="return=representation")
        event_row = (ev or [None])[0]
        event_id = (event_row or {}).get("id")
    except Exception:
        logger.exception("%s: calendar row failed for %r on %s", spec["project"], title, plan_date)

    # ── 2b. Mirror it to Google Calendar ────────────────────────────
    # Same shape as POST /api/v2/events: fire and forget on a daemon
    # thread, then stamp the returned google_event_id back onto the row.
    # The reason it runs off the request is that a Google round trip is
    # a second or more, and she is standing in front of a card waiting
    # for it to say "added" — the in-app calendar is already correct by
    # the time this starts, so the mirror is allowed to be late.
    #
    # NOT mirrored from the Quick Bucket row as well. quick_bucket has
    # its own Google sync, and letting both fire would put the same
    # topic on the real calendar twice.
    gcal_connected = False
    if event_row:
        try:
            gcal_connected = bool(get("user_google_tokens",
                                      params={"user_id": f"eq.{user_id}"}) or [])
        except Exception:
            logger.warning("%s: could not check Google connection", spec["project"], exc_info=True)
    if event_row and gcal_connected:
        def _mirror(row=event_row, uid=user_id):
            try:
                # Imported here rather than at module scope so a broken or
                # absent Google client library cannot stop /ai-sde loading.
                from services import events_calendar_service as events_cal
                gid = events_cal.sync_create(uid, row)
                if gid:
                    update("daily_events",
                           params={"id": f"eq.{row['id']}", "user_id": f"eq.{uid}"},
                           json={"google_event_id": gid})
            except Exception:
                logger.exception("Google mirror failed for %r", row.get("title"))
        threading.Thread(target=_mirror, daemon=True).start()

    # ── 3. The Quick Bucket row ─────────────────────────────────────
    # Prefixed so a line in the bucket says where it came from; the
    # bucket is a flat list with no project column to say it otherwise.
    bucket_id = None
    bucket_text = f"{spec['project']} · {title}"[:500]
    if data.get("quick_bucket", True):
        try:
            dupes = _get_optional("quick_bucket", {
                "user_id": f"eq.{user_id}",
                "text": _pg_eq(bucket_text),
                "is_deleted": "eq.false",
                "is_done": "eq.false",
                "select": "id",
                "limit": "1",
            }, optional={"is_deleted", "is_done"})
            if dupes:
                bucket_id = dupes[0]["id"]
            else:
                # A topic with a real time gets a real deadline, which is
                # what drives the countdown pill. A midnight default does
                # not — a countdown to 00:00 would read as urgent when the
                # time only means "top of the day".
                due_at = None
                if not untimed:
                    due_at = f"{plan_date}T{start_time}:00"
                today = user_today().isoformat()
                qb = post("quick_bucket", {
                    "user_id": user_id,
                    "text": bucket_text,
                    "time_bucket": "at" if due_at else ("now" if plan_date <= today else "future"),
                    "due_at": due_at,
                    "position": 0,
                    "is_done": False,
                    "is_deleted": False,
                }, prefer="return=representation")
                bucket_id = (qb or [{}])[0].get("id")
        except Exception:
            logger.exception("%s: quick bucket row failed for %r", spec["project"], title)

    when = "12:00 AM (top of the day)" if untimed else start_time
    return jsonify({
        "status": "ok",
        "project_id": project_id,
        "task_id": task_id,
        "event_id": event_id,
        "quick_bucket_id": bucket_id,
        "title": title,
        "plan_date": plan_date,
        "start_time": start_time,
        "end_time": end_time,
        "untimed": untimed,
        "bank": bank,
        "project": spec["project"],
        # Kicked off, not confirmed — the mirror finishes after this
        # response, so the wording on the page has to stay honest about
        # that ("sending to Google", never "on Google").
        "gcal_syncing": bool(gcal_connected and event_row),
        "message": f"On the calendar for {plan_date} at {when}.",
    })


# ══════════════════════════════════════════════════════════════════════
# AI SDE PROGRESS — server-side, so study follows the user between devices
#
# Keyed by TITLE, never by the "ai{i}" id the list endpoint hands out: that
# id is the entry's INDEX in the bank, and the index shifts every time an
# entry is added or deduped. See MIGRATION_AI_SDE_PROGRESS.sql.
# ══════════════════════════════════════════════════════════════════════

_AI_SDE_TITLES = {e["title"] for e in AI_SDE_ENTRIES}


@interview_prep_bp.route("/api/ai-sde/progress", methods=["GET"])
@login_required
def ai_sde_progress():
    """Every topic this user has ticked or clocked time against.

    Returns titles, not ids, and the client maps them onto whatever the
    bank currently holds — so a topic that has since been renamed or
    removed simply drops out instead of silently marking its neighbour.
    """
    try:
        rows = get("ai_sde_progress", params={
            "user_id": f"eq.{session['user_id']}",
            "is_deleted": "eq.false",
            "select": "entry_title,studied,studied_at,minutes_focused",
            "limit": 5000,
        }) or []
    except Exception as exc:
        return _ai_sde_progress_schema_error(exc)

    studied, minutes = [], {}
    for r in rows:
        title = r.get("entry_title")
        if title not in _AI_SDE_TITLES:
            continue          # renamed or removed since it was recorded
        if r.get("studied"):
            studied.append(title)
        if r.get("minutes_focused"):
            minutes[title] = int(r["minutes_focused"])
    return jsonify({"studied": studied, "minutes": minutes,
                    "total_rows": len(rows)})


@interview_prep_bp.route("/api/ai-sde/progress", methods=["POST"])
@login_required
def ai_sde_progress_save():
    """Upsert one topic's progress. Body: {title, studied?, minutes?}."""
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    if title not in _AI_SDE_TITLES:
        return jsonify({"error": "unknown topic"}), 400

    payload = {"user_id": session["user_id"], "entry_title": title,
               "updated_at": _iso_now()}
    if "studied" in data:
        payload["studied"] = bool(data["studied"])
        # Stamp the moment it was ticked; clear it when un-ticked so the
        # column never claims a date for something not actually done.
        payload["studied_at"] = _iso_now() if data["studied"] else None
    if "minutes" in data:
        try:
            payload["minutes_focused"] = max(0, int(data["minutes"]))
        except (TypeError, ValueError):
            return jsonify({"error": "minutes must be a number"}), 400
    if len(payload) <= 3:
        return jsonify({"error": "nothing to save"}), 400

    try:
        # Upsert on (user_id, entry_title) — the unique index in the
        # migration is what makes merge-duplicates the right resolution.
        post("ai_sde_progress", payload,
             prefer="resolution=merge-duplicates,return=minimal")
    except Exception as exc:
        return _ai_sde_progress_schema_error(exc)
    return jsonify({"status": "ok"})


def _iso_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _ai_sde_progress_schema_error(exc):
    """A missing table should name the migration, not surface a bare 500."""
    text = str(exc)
    if "ai_sde_progress" in text or "does not exist" in text or "schema cache" in text:
        logger.warning("ai-sde progress: table missing - %s", text)
        return jsonify({
            "error": "Progress sync is not set up yet. Run "
                     "MIGRATION_AI_SDE_PROGRESS.sql in Supabase.",
            "migration": "MIGRATION_AI_SDE_PROGRESS.sql",
        }), 503
    raise exc


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
    # The interview tags narrow it further, so "Must-Know / DSA / Graphs" on
    # the study page exports exactly the revision sheet you are looking at.
    selected, _tag_bits = _ai_sde_tag_select(selected)
    if _tag_bits:
        _tags = " · ".join(_tag_bits)
        label = f"{label} — {_tags}" if label else _tags
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
            # Rank within the band is the number you actually work from once
            # you have committed to finishing a priority level.
            (f"{it['priority_label']} in its band" if it.get("priority_label") else ""),
            (f"#{it['cat_rank']} within {AI_SDE_CATEGORIES.get(it.get('cat'), '')}"
             if it.get("cat_rank") else ""),
            (it.get("priority_note") or "")] if x)
        # The seven interview tags, on one line. This is the line you scan when
        # deciding whether a topic belongs in tonight's revision at all.
        _tags = " | ".join(x for x in [
            (f"{it['tag_priority']} for a new grad" if it.get("tag_priority") else ""),
            (f"{it['tag_topic']} / {it['tag_subtopic']}"
             if it.get("tag_topic") and it.get("tag_subtopic")
             else it.get("tag_topic") or ""),
            (it.get("tag_level") or ""),
            (f"{it['tag_format']} question" if it.get("tag_format") else ""),
            (f"{it['tag_stage']} round" if it.get("tag_stage") else ""),
            (f"{it['tag_time']} to answer" if it.get("tag_time") else "")] if x)
        if it.get("tag_flag"):
            _tags = f"{_tags}\nNote: {it['tag_flag']}" if _tags else f"Note: {it['tag_flag']}"
        fields = [("Prep time & priority", _plan or None),
                  ("Interview tags", _tags or None),
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

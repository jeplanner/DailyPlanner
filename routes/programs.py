"""Programs blueprint — IT program review decks for execs.

Endpoints:
    GET  /programs                          list page (one card per program)
    GET  /programs/new                      editor (new review)
    GET  /programs/<id>                     editor (existing review)
    GET  /programs/history/<program_name>   all reviews for one program
    POST /programs/save                     create or update
    POST /programs/<id>/delete              soft-delete
    POST /programs/<id>/clone               spawn next-month review from this one

Schema lives in MIGRATION_PROGRAM_REVIEWS.sql. JSONB columns
(workstreams, milestones, risks, decisions) hold the structured
data; long-form narrative bits live in plain text columns.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from urllib.parse import unquote

from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

programs_bp = Blueprint("programs", __name__)

VALID_RAGS = {"green", "amber", "red"}
VALID_CADENCES = {"weekly", "monthly", "quarterly", "board", "adhoc"}
VALID_MILESTONE_STATUSES = {"hit", "slipped", "missed", "upcoming"}

_MAX_SHORT = 240
_MAX_LONG = 12000


# ─── Helpers ─────────────────────────────────────────────────────


def _get_one(table, params):
    rows = get(table, params=params)
    return rows[0] if rows else None


def _short(s):
    return (s or "").strip()[:_MAX_SHORT] or None


def _long(s):
    return (s or "").strip()[:_MAX_LONG] or None


def _safe_num(v):
    """Coerce to float; return None on bad input or empty string."""
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clean_jsonb_list(raw, allowed_keys: set, max_items: int = 30):
    """Take whatever the client posted, return a sanitized list of dicts
    keeping only allowed string keys. Hardens against either prompt-injected
    payloads or stale fields lingering in the form."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:max_items]:
        if not isinstance(item, dict):
            continue
        cleaned = {}
        for k in allowed_keys:
            v = item.get(k)
            if v is None:
                continue
            # Coerce to string and bound length.
            cleaned[k] = str(v)[:500]
        if cleaned:
            out.append(cleaned)
    return out


def _milestone_counts(milestones):
    """Tally hit / slipped / missed / upcoming for the scorecard."""
    counts = {"hit": 0, "slipped": 0, "missed": 0, "upcoming": 0}
    for m in milestones or []:
        st = (m.get("status") or "").strip().lower()
        if st in counts:
            counts[st] += 1
    return counts


def _list_programs_summary(user_id: str):
    """Return one row per unique program_name — the latest review, with
    its scorecard fields. Used by /programs and the history sidebar."""
    rows = get(
        "program_reviews",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": (
                "id,program_name,review_date,cadence,overall_rag,overall_status,"
                "exec_summary,timeline_status,top_risk_headline,"
                "budget_total,budget_spent,budget_currency,"
                "workstreams,milestones,risks,updated_at"
            ),
            "order": "review_date.desc.nullslast,updated_at.desc",
            "limit": "500",
        },
    ) or []

    # Keep just the latest review per program_name.
    seen = {}
    history_counts = defaultdict(int)
    for r in rows:
        name = r.get("program_name") or "(untitled program)"
        history_counts[name] += 1
        if name not in seen:
            seen[name] = r

    # Augment with derived fields the UI wants.
    out = []
    for name, r in seen.items():
        r["_history_count"] = history_counts[name]
        r["_milestone_counts"] = _milestone_counts(r.get("milestones") or [])
        r["_workstream_count"] = len(r.get("workstreams") or [])
        r["_open_risk_count"] = len(r.get("risks") or [])
        out.append(r)

    # Sort: red programs first (they need attention), then amber, then green.
    rag_rank = {"red": 0, "amber": 1, "green": 2}
    out.sort(key=lambda r: (
        rag_rank.get(r.get("overall_rag") or "green", 2),
        -(int((r.get("review_date") or "0000-00-00").replace("-", "") or 0)),
        r.get("program_name") or "",
    ))
    return out


# ─── List ────────────────────────────────────────────────────────


@programs_bp.route("/programs", methods=["GET"])
@login_required
def programs_list():
    user_id = session["user_id"]
    summary = _list_programs_summary(user_id)
    return render_template(
        "program_list.html",
        programs=summary,
        rag_counts={
            "red": sum(1 for p in summary if p.get("overall_rag") == "red"),
            "amber": sum(1 for p in summary if p.get("overall_rag") == "amber"),
            "green": sum(1 for p in summary if p.get("overall_rag") == "green"),
        },
    )


@programs_bp.route("/programs/history/<program_name>", methods=["GET"])
@login_required
def programs_history(program_name):
    """Reverse-chronological list of every review for one program."""
    user_id = session["user_id"]
    name = unquote(program_name)
    rows = get(
        "program_reviews",
        params={
            "user_id": f"eq.{user_id}",
            "program_name": f"eq.{name}",
            "is_deleted": "eq.false",
            "order": "review_date.desc.nullslast,updated_at.desc",
            "limit": "200",
        },
    ) or []
    return render_template(
        "program_list.html",
        programs=[],
        history=rows,
        history_program_name=name,
        rag_counts={"red": 0, "amber": 0, "green": 0},
    )


# ─── Editor ──────────────────────────────────────────────────────


@programs_bp.route("/programs/new", methods=["GET"])
@login_required
def programs_new():
    """New review. Optionally pre-fill program_name (?program=Foo) so the
    editor opens scoped to a specific program."""
    user_id = session["user_id"]
    prefill_name = (request.args.get("program") or "").strip()
    return render_template(
        "program_review_edit.html",
        review=None,
        prefill_program=prefill_name,
        existing_programs=_distinct_program_names(user_id),
        history=[],
    )


def _distinct_program_names(user_id: str) -> list[str]:
    rows = get(
        "program_reviews",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "program_name",
            "limit": "500",
        },
    ) or []
    return sorted({(r.get("program_name") or "").strip() for r in rows if r.get("program_name")})


@programs_bp.route("/programs/<review_id>", methods=["GET"])
@login_required
def programs_edit(review_id):
    user_id = session["user_id"]
    review = _get_one(
        "program_reviews",
        params={"id": f"eq.{review_id}", "user_id": f"eq.{user_id}"},
    )
    if not review:
        abort(404)

    # History for the sidebar (every review of this program, newest first).
    history = []
    name = (review.get("program_name") or "").strip()
    if name:
        history = get(
            "program_reviews",
            params={
                "user_id": f"eq.{user_id}",
                "program_name": f"eq.{name}",
                "is_deleted": "eq.false",
                "select": "id,review_date,overall_rag,cadence,updated_at",
                "order": "review_date.desc.nullslast,updated_at.desc",
                "limit": "30",
            },
        ) or []

    return render_template(
        "program_review_edit.html",
        review=review,
        prefill_program="",
        existing_programs=_distinct_program_names(user_id),
        history=history,
    )


# ─── Save ────────────────────────────────────────────────────────


@programs_bp.route("/programs/save", methods=["POST"])
@login_required
def programs_save():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    review_id = data.get("id")

    cadence = (data.get("cadence") or "monthly").strip().lower()
    if cadence not in VALID_CADENCES:
        cadence = "monthly"

    overall_rag = (data.get("overall_rag") or "green").strip().lower()
    if overall_rag not in VALID_RAGS:
        overall_rag = "green"

    payload = {
        "program_name": _short(data.get("program_name")) or "(untitled program)",
        "review_date": (data.get("review_date") or "").strip() or None,
        "cadence": cadence,

        "overall_rag": overall_rag,
        "overall_status": _long(data.get("overall_status")),
        "exec_summary": _long(data.get("exec_summary")),
        "timeline_status": _short(data.get("timeline_status")),
        "top_risk_headline": _short(data.get("top_risk_headline")),

        "budget_total": _safe_num(data.get("budget_total")),
        "budget_spent": _safe_num(data.get("budget_spent")),
        "budget_currency": _short(data.get("budget_currency")) or "USD",
        "budget_variance_note": _long(data.get("budget_variance_note")),

        "objectives": _long(data.get("objectives")),

        "workstreams": _clean_jsonb_list(
            data.get("workstreams"),
            allowed_keys={"name", "owner", "rag", "update"},
        ),
        "milestones": _clean_jsonb_list(
            data.get("milestones"),
            allowed_keys={"label", "due_date", "status"},
        ),
        "risks": _clean_jsonb_list(
            data.get("risks"),
            allowed_keys={"risk", "likelihood", "impact", "mitigation", "owner", "target_date"},
        ),
        "decisions": _clean_jsonb_list(
            data.get("decisions"),
            allowed_keys={"title", "context", "options", "recommendation"},
        ),

        "business_impact": _long(data.get("business_impact")),
        "asks": _long(data.get("asks")),
    }

    if review_id:
        update(
            "program_reviews",
            params={"id": f"eq.{review_id}", "user_id": f"eq.{user_id}"},
            json=payload,
        )
    else:
        payload["user_id"] = user_id
        if data.get("previous_review_id"):
            payload["previous_review_id"] = data["previous_review_id"]
        res = post("program_reviews", payload)
        review_id = res[0]["id"] if res else None

    return jsonify({"status": "ok", "id": review_id})


# ─── Delete (soft) ──────────────────────────────────────────────


@programs_bp.route("/programs/<review_id>/delete", methods=["POST"])
@login_required
def programs_delete(review_id):
    user_id = session["user_id"]
    update(
        "program_reviews",
        params={"id": f"eq.{review_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )
    return jsonify({"status": "ok"})


# ─── Clone (spawn next-period review) ───────────────────────────


@programs_bp.route("/programs/<review_id>/clone", methods=["POST"])
@login_required
def programs_clone(review_id):
    """Create a new review row whose narrative + scorecard fields start
    blank but whose structural data (workstreams, milestones list,
    objectives) carries forward from the source. The user updates RAG
    + status fields for this period and ships the new review.

    Returns: { id: <new_id> }
    """
    user_id = session["user_id"]
    src = _get_one(
        "program_reviews",
        params={"id": f"eq.{review_id}", "user_id": f"eq.{user_id}"},
    )
    if not src:
        return jsonify({"error": "not found"}), 404

    # Carry milestones forward but strip their statuses so the user
    # re-evaluates each one for the new period.
    fresh_milestones = []
    for m in src.get("milestones") or []:
        fresh_milestones.append({
            "label": m.get("label") or "",
            "due_date": m.get("due_date") or "",
            "status": "upcoming",
        })

    # Workstreams carry name + owner; RAG and update reset.
    fresh_workstreams = []
    for w in src.get("workstreams") or []:
        fresh_workstreams.append({
            "name": w.get("name") or "",
            "owner": w.get("owner") or "",
            "rag": "green",
            "update": "",
        })

    payload = {
        "user_id": user_id,
        "program_name": src.get("program_name") or "",
        "review_date": date.today().isoformat(),
        "cadence": src.get("cadence") or "monthly",
        "overall_rag": "green",
        "overall_status": None,
        "exec_summary": None,
        "timeline_status": None,
        "top_risk_headline": None,
        "budget_total": src.get("budget_total"),
        "budget_spent": src.get("budget_spent"),
        "budget_currency": src.get("budget_currency") or "USD",
        "budget_variance_note": None,
        "objectives": src.get("objectives"),
        "workstreams": fresh_workstreams,
        "milestones": fresh_milestones,
        "risks": [],          # risk register starts blank — user adds what's hot now
        "decisions": [],
        "business_impact": None,
        "asks": None,
        "previous_review_id": src["id"],
    }
    res = post("program_reviews", payload)
    new_id = res[0]["id"] if res else None
    if not new_id:
        return jsonify({"error": "could not clone"}), 502
    return jsonify({"status": "ok", "id": new_id})

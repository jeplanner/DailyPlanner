"""Meetings blueprint — executive meeting prep sheets.

Endpoints:
    GET  /meetings                       list page (Upcoming / Past tabs)
    GET  /meetings/new                   editor (new prep)
    GET  /meetings/<id>                  editor (existing prep)
    POST /meetings/save                  create or update
    POST /meetings/<id>/delete           soft-delete
    POST /meetings/<id>/status           change status (upcoming/done/cancelled)

Schema lives in MIGRATION_MEETING_PREPS.sql. Each prep walks through
BLUF → SCQA → supporting points → anticipated Q&A → pre-brief plan,
then captures outcome + follow-ups + retro after the meeting happens.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

meetings_bp = Blueprint("meetings", __name__)

VALID_STATUSES = {"upcoming", "done", "cancelled"}

# Long-form fields are bounded to avoid pathological payloads.
_MAX_SHORT = 240
_MAX_LONG = 8000


# ─── Helpers ─────────────────────────────────────────────────────


def _get_one(table, params):
    rows = get(table, params=params)
    return rows[0] if rows else None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _short(s):
    return (s or "").strip()[:_MAX_SHORT] or None


def _long(s):
    return (s or "").strip()[:_MAX_LONG] or None


def _counts(user_id: str) -> dict:
    rows = get(
        "meeting_preps",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "status",
        },
    ) or []
    upcoming = sum(1 for r in rows if r.get("status") == "upcoming")
    done = sum(1 for r in rows if r.get("status") == "done")
    cancelled = sum(1 for r in rows if r.get("status") == "cancelled")
    return {
        "upcoming": upcoming,
        "done": done,
        "cancelled": cancelled,
        "total": upcoming + done + cancelled,
    }


# ─── List ────────────────────────────────────────────────────────


@meetings_bp.route("/meetings", methods=["GET"])
@login_required
def meetings_list():
    user_id = session["user_id"]
    status = (request.args.get("status") or "upcoming").strip().lower()
    q = (request.args.get("q") or "").strip()

    params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "limit": "300",
    }
    if status in VALID_STATUSES:
        params["status"] = f"eq.{status}"
        # Upcoming sorted by meeting_date ascending (next first), past
        # sorted descending (most-recent first).
        if status == "upcoming":
            params["order"] = "meeting_date.asc.nullslast,updated_at.desc"
        else:
            params["order"] = "meeting_date.desc.nullslast,updated_at.desc"
    elif status == "all":
        params["order"] = "meeting_date.desc.nullslast,updated_at.desc"
    else:
        status = "upcoming"
        params["status"] = "eq.upcoming"
        params["order"] = "meeting_date.asc.nullslast,updated_at.desc"

    if q:
        params["or"] = (
            f"(title.ilike.*{q}*,"
            f"attendees.ilike.*{q}*,"
            f"ask_recommendation.ilike.*{q}*,"
            f"scqa_answer.ilike.*{q}*,"
            f"outcome.ilike.*{q}*)"
        )

    preps = get("meeting_preps", params=params) or []
    return render_template(
        "meeting_list.html",
        preps=preps,
        active_status=status,
        q=q,
        counts=_counts(user_id),
        now_iso=_now_iso(),
    )


# ─── Editor ──────────────────────────────────────────────────────


@meetings_bp.route("/meetings/new", methods=["GET"])
@login_required
def meetings_new():
    user_id = session["user_id"]
    return render_template(
        "meeting_edit.html",
        prep=None,
        counts=_counts(user_id),
    )


@meetings_bp.route("/meetings/<prep_id>", methods=["GET"])
@login_required
def meetings_edit(prep_id):
    user_id = session["user_id"]
    prep = _get_one(
        "meeting_preps",
        params={"id": f"eq.{prep_id}", "user_id": f"eq.{user_id}"},
    )
    if not prep:
        abort(404)
    return render_template(
        "meeting_edit.html",
        prep=prep,
        counts=_counts(user_id),
    )


# ─── Save ────────────────────────────────────────────────────────


@meetings_bp.route("/meetings/save", methods=["POST"])
@login_required
def meetings_save():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    prep_id = data.get("id")

    # Meeting date may arrive as ISO 'YYYY-MM-DDTHH:MM' from <input
    # type=datetime-local> — pass it through as-is, Postgres parses it.
    meeting_date = (data.get("meeting_date") or "").strip() or None

    payload = {
        "title": _short(data.get("title")) or "Untitled meeting",
        "meeting_date": meeting_date,
        "attendees": _long(data.get("attendees")),

        "ask_recommendation": _long(data.get("ask_recommendation")),
        "ask_decision_needed": _long(data.get("ask_decision_needed")),
        "ask_by_when": _short(data.get("ask_by_when")),
        "ask_from_whom": _short(data.get("ask_from_whom")),

        "scqa_situation": _long(data.get("scqa_situation")),
        "scqa_complication": _long(data.get("scqa_complication")),
        "scqa_question": _long(data.get("scqa_question")),
        "scqa_answer": _long(data.get("scqa_answer")),

        "supporting_points": _long(data.get("supporting_points")),
        "anticipated_questions": _long(data.get("anticipated_questions")),
        "pre_brief_plan": _long(data.get("pre_brief_plan")),

        "outcome": _long(data.get("outcome")),
        "follow_ups": _long(data.get("follow_ups")),
        "retro": _long(data.get("retro")),
    }

    if prep_id:
        update(
            "meeting_preps",
            params={"id": f"eq.{prep_id}", "user_id": f"eq.{user_id}"},
            json=payload,
        )
    else:
        payload["user_id"] = user_id
        payload["status"] = "upcoming"
        res = post("meeting_preps", payload)
        prep_id = res[0]["id"] if res else None

    return jsonify({"status": "ok", "id": prep_id})


# ─── Delete (soft) ──────────────────────────────────────────────


@meetings_bp.route("/meetings/<prep_id>/delete", methods=["POST"])
@login_required
def meetings_delete(prep_id):
    user_id = session["user_id"]
    update(
        "meeting_preps",
        params={"id": f"eq.{prep_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )
    return jsonify({"status": "ok"})


# ─── Status change ──────────────────────────────────────────────


@meetings_bp.route("/meetings/<prep_id>/status", methods=["POST"])
@login_required
def meetings_set_status(prep_id):
    """Body: { status: 'upcoming' | 'done' | 'cancelled' }"""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip().lower()
    if new_status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400

    update(
        "meeting_preps",
        params={"id": f"eq.{prep_id}", "user_id": f"eq.{user_id}"},
        json={"status": new_status},
    )
    return jsonify({"status": "ok", "new_status": new_status})

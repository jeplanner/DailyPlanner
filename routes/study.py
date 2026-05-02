"""Study notes blueprint — Cornell + Feynman with spaced review.

Endpoints:
    GET  /study                              list page (Cornell / Feynman tabs)
    GET  /study/review                       spaced-review queue
    GET  /study/new?method=cornell|feynman   editor (new note)
    GET  /study/<id>                         editor (existing note)
    POST /study/save                         create or update
    POST /study/<id>/delete                  soft-delete
    POST /study/<id>/review                  advance / reset review stage
                                             body: { result: 'remembered' | 'forgot' }
    POST /study/<id>/iterate                 Feynman: spawn child note for next pass

Schema lives in MIGRATION_STUDY_NOTES.sql. Source URLs are auto-linked
to a matching travel_reads row at save time so the note knows which
queued article/video it came from.
"""

import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

study_bp = Blueprint("study", __name__)

# Leitner-style review intervals. Index = review_stage. Stage 5 = mastered
# (no further review). Tweak these if you want a more aggressive schedule.
REVIEW_INTERVALS_DAYS = [1, 1, 3, 7, 21, None]   # stage 0→1d, 1→1d, 2→3d, 3→7d, 4→21d, 5=done

VALID_METHODS = {"cornell", "feynman"}


# ─── Helpers ─────────────────────────────────────────────────────


def _get_one(table, params):
    rows = get(table, params=params)
    return rows[0] if rows else None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _next_review_iso(stage: int) -> str | None:
    """Return the ISO timestamp for the next review given the new stage,
    or None when the note is mastered (stage 5)."""
    if stage < 0 or stage >= len(REVIEW_INTERVALS_DAYS):
        return None
    days = REVIEW_INTERVALS_DAYS[stage]
    if days is None:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _resolve_travel_read(user_id: str, source_url: str) -> str | None:
    """If `source_url` matches a travel_reads row owned by the user,
    return its id so the study note can link back. Match is exact on
    the URL string (no normalization yet)."""
    if not source_url:
        return None
    rows = get(
        "travel_reads",
        params={
            "user_id": f"eq.{user_id}",
            "url": f"eq.{source_url}",
            "select": "id",
            "limit": "1",
        },
    ) or []
    return rows[0]["id"] if rows else None


def _counts(user_id: str) -> dict:
    """Sidebar counts: total per method + due-today review queue."""
    rows = get(
        "study_notes",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "method,review_stage,next_review_at",
        },
    ) or []
    cornell = sum(1 for r in rows if r.get("method") == "cornell")
    feynman = sum(1 for r in rows if r.get("method") == "feynman")
    now_iso = _now_iso()
    due = sum(
        1 for r in rows
        if (r.get("review_stage") or 0) < 5
        and (r.get("next_review_at") or "") <= now_iso
    )
    return {
        "cornell": cornell,
        "feynman": feynman,
        "total": cornell + feynman,
        "due": due,
    }


# ─── List page ───────────────────────────────────────────────────


@study_bp.route("/study", methods=["GET"])
@login_required
def study_list():
    user_id = session["user_id"]
    method = (request.args.get("method") or "all").strip().lower()
    q = (request.args.get("q") or "").strip()

    params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "order": "updated_at.desc",
        "limit": "300",
    }
    if method in VALID_METHODS:
        params["method"] = f"eq.{method}"
    if q:
        # Search across title + every long-form column. PostgREST `or`
        # filter takes a parenthesised list of column.op.value entries.
        params["or"] = (
            f"(title.ilike.*{q}*,"
            f"cornell_notes.ilike.*{q}*,"
            f"cornell_summary.ilike.*{q}*,"
            f"feynman_concept.ilike.*{q}*,"
            f"feynman_simple.ilike.*{q}*,"
            f"feynman_refined.ilike.*{q}*,"
            f"source_text.ilike.*{q}*)"
        )

    notes = get("study_notes", params=params) or []
    return render_template(
        "study_list.html",
        notes=notes,
        active_method=method if method in VALID_METHODS else "all",
        q=q,
        counts=_counts(user_id),
    )


# ─── Editor (new + existing) ────────────────────────────────────


@study_bp.route("/study/new", methods=["GET"])
@login_required
def study_new():
    user_id = session["user_id"]
    method = (request.args.get("method") or "cornell").strip().lower()
    if method not in VALID_METHODS:
        method = "cornell"

    # Optional pre-fill from a travel_reads row.
    travel_read_id = (request.args.get("source_id") or "").strip()
    prefill_url = ""
    prefill_title = ""
    if travel_read_id:
        row = _get_one(
            "travel_reads",
            params={
                "id": f"eq.{travel_read_id}",
                "user_id": f"eq.{user_id}",
                "select": "id,url,title",
            },
        )
        if row:
            prefill_url = row.get("url") or ""
            prefill_title = row.get("title") or ""

    template = (
        "study_edit_cornell.html" if method == "cornell" else "study_edit_feynman.html"
    )
    return render_template(
        template,
        note=None,
        method=method,
        prefill_url=prefill_url,
        prefill_title=prefill_title,
        counts=_counts(user_id),
        iteration_chain=[],
    )


@study_bp.route("/study/<note_id>", methods=["GET"])
@login_required
def study_edit(note_id):
    user_id = session["user_id"]
    note = _get_one(
        "study_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
    )
    if not note:
        abort(404)
    method = note.get("method") or "cornell"
    template = (
        "study_edit_cornell.html" if method == "cornell" else "study_edit_feynman.html"
    )

    # For Feynman, surface the iteration chain so the editor can show
    # earlier passes alongside the current one.
    chain = []
    if method == "feynman":
        chain = _build_feynman_chain(user_id, note)

    return render_template(
        template,
        note=note,
        method=method,
        prefill_url="",
        prefill_title="",
        counts=_counts(user_id),
        iteration_chain=chain,
    )


def _build_feynman_chain(user_id: str, note: dict) -> list[dict]:
    """Walk the parent chain upwards, then collect every direct child of
    the chain root, ordered by created_at. Returns a flat list of passes
    (oldest → newest) so the UI can render them as a vertical timeline."""
    # 1. Walk upward to find the root pass.
    seen = set()
    cursor = note
    while cursor and cursor.get("feynman_parent_id"):
        pid = cursor["feynman_parent_id"]
        if pid in seen:
            break  # paranoia: cycle guard
        seen.add(pid)
        parent = _get_one(
            "study_notes",
            params={"id": f"eq.{pid}", "user_id": f"eq.{user_id}",
                    "is_deleted": "eq.false"},
        )
        if not parent:
            break
        cursor = parent
    root = cursor or note

    # 2. Pull every descendant in the user's tree that points back to root,
    # plus root itself. Cheap because the index is on feynman_parent_id.
    rows = get(
        "study_notes",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "method": "eq.feynman",
            "or": f"(id.eq.{root['id']},feynman_parent_id.eq.{root['id']})",
            "select": "id,title,feynman_concept,feynman_parent_id,created_at",
            "order": "created_at.asc",
            "limit": "50",
        },
    ) or []
    return rows


# ─── Save (create + update) ─────────────────────────────────────


@study_bp.route("/study/save", methods=["POST"])
@login_required
def study_save():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    note_id = data.get("id")
    method = (data.get("method") or "").strip().lower()
    if method not in VALID_METHODS:
        return jsonify({"error": "invalid method"}), 400

    title = (data.get("title") or "").strip()[:240]
    source_url = (data.get("source_url") or "").strip()[:1000] or None
    source_text = (data.get("source_text") or "").strip()[:240] or None

    payload = {
        "method": method,
        "title": title,
        "source_url": source_url,
        "source_text": source_text,
        "travel_read_id": _resolve_travel_read(user_id, source_url) if source_url else None,
    }

    if method == "cornell":
        payload.update({
            "cornell_cues": (data.get("cornell_cues") or "").strip() or None,
            "cornell_notes": (data.get("cornell_notes") or "").strip() or None,
            "cornell_summary": (data.get("cornell_summary") or "").strip() or None,
        })
    else:
        payload.update({
            "feynman_concept": (data.get("feynman_concept") or "").strip() or None,
            "feynman_simple": (data.get("feynman_simple") or "").strip() or None,
            "feynman_gaps": (data.get("feynman_gaps") or "").strip() or None,
            "feynman_refined": (data.get("feynman_refined") or "").strip() or None,
        })
        # Parent linkage is set on creation only (via /iterate) — never
        # overwritten by a save, so children can never re-parent.
        if not note_id and data.get("feynman_parent_id"):
            payload["feynman_parent_id"] = data["feynman_parent_id"]

    if note_id:
        update(
            "study_notes",
            params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
            json=payload,
        )
    else:
        payload["user_id"] = user_id
        # New notes start with a 1-day review window so they show up in
        # /study/review tomorrow — that's the whole point of taking them.
        payload["next_review_at"] = (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat()
        res = post("study_notes", payload)
        note_id = res[0]["id"] if res else None

    return jsonify({"status": "ok", "id": note_id})


# ─── Delete (soft) ──────────────────────────────────────────────


@study_bp.route("/study/<note_id>/delete", methods=["POST"])
@login_required
def study_delete(note_id):
    user_id = session["user_id"]
    update(
        "study_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )
    return jsonify({"status": "ok"})


# ─── Spaced review ──────────────────────────────────────────────


@study_bp.route("/study/review", methods=["GET"])
@login_required
def study_review():
    """Show every note whose next_review_at has passed, oldest-due first."""
    user_id = session["user_id"]
    now_iso = _now_iso()
    notes = get(
        "study_notes",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "review_stage": "lt.5",
            "next_review_at": f"lte.{now_iso}",
            "order": "next_review_at.asc",
            "limit": "200",
        },
    ) or []
    return render_template(
        "study_review.html",
        notes=notes,
        counts=_counts(user_id),
    )


@study_bp.route("/study/<note_id>/review", methods=["POST"])
@login_required
def study_review_advance(note_id):
    """Advance or reset the spaced-review stage.

    Body: { "result": "remembered" | "forgot" }
      - remembered → stage += 1 (capped at 5 = mastered)
      - forgot     → stage = 1   (back to the 1-day bucket)

    Returns the new stage and next_review_at.
    """
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    result = (data.get("result") or "").strip().lower()
    if result not in {"remembered", "forgot"}:
        return jsonify({"error": "result must be 'remembered' or 'forgot'"}), 400

    row = _get_one(
        "study_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}",
                "select": "review_stage"},
    )
    if not row:
        return jsonify({"error": "not found"}), 404

    if result == "remembered":
        new_stage = min(5, (row.get("review_stage") or 0) + 1)
    else:
        new_stage = 1

    patch = {
        "review_stage": new_stage,
        "last_reviewed_at": _now_iso(),
        "next_review_at": _next_review_iso(new_stage),
    }
    update(
        "study_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        json=patch,
    )
    return jsonify({
        "status": "ok",
        "review_stage": new_stage,
        "next_review_at": patch["next_review_at"],
        "mastered": new_stage >= 5,
    })


# ─── Feynman: iterate (spawn next pass) ────────────────────────


@study_bp.route("/study/<note_id>/iterate", methods=["POST"])
@login_required
def study_iterate(note_id):
    """Create a new Feynman pass that points back to <note_id> as its
    parent. The new pass starts blank-ish — it copies the concept and
    title so the user picks up where they left off, but the simple/
    gaps/refined fields are empty for the next iteration.

    Returns: { id: <new_id> } so the client can navigate to it.
    """
    user_id = session["user_id"]
    parent = _get_one(
        "study_notes",
        params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}",
                "method": "eq.feynman"},
    )
    if not parent:
        return jsonify({"error": "not found"}), 404

    payload = {
        "user_id": user_id,
        "method": "feynman",
        "title": parent.get("title") or "",
        "source_url": parent.get("source_url"),
        "source_text": parent.get("source_text"),
        "travel_read_id": parent.get("travel_read_id"),
        "feynman_concept": parent.get("feynman_concept"),
        "feynman_parent_id": parent["id"],
        "next_review_at": (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat(),
    }
    res = post("study_notes", payload)
    new_id = res[0]["id"] if res else None
    if not new_id:
        return jsonify({"error": "could not create iteration"}), 502
    return jsonify({"status": "ok", "id": new_id})

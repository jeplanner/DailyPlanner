"""Highlights with hints, on every page.

GET  /api/hints?page=/ai-sde           your hints on that page
POST /api/hints                        {page, anchor?, quote?, prefix?, question?, context?}
POST /api/hints/<id>/ask               {question, context?}   a follow-up question
POST /api/hints/<id>/retry             answer the last question again
POST /api/hints/<id>/delete

Answers are written in the background (services/page_hints_service.py);
the page polls while a turn is pending. Each person sees only their own.
"""
import logging

from flask import Blueprint, jsonify, request, session

from auth import login_required
from extensions import limiter
from services import page_hints_service as svc
from supabase_client import get, post, update

logger = logging.getLogger(__name__)
page_hints_bp = Blueprint("page_hints", __name__)

COLS = "id,page,anchor,quote,prefix,thread,created_at,updated_at"


def _detail(exc):
    """Supabase's own error body. str(exc) is just "401 ... for url: .../page_hints",
    which names the table on EVERY failure, so it can't tell a missing table apart."""
    resp = getattr(exc, "response", None)
    return (getattr(resp, "text", "") or "") or str(exc)


def _missing(exc):
    t = _detail(exc)
    return "PGRST205" in t or "42P01" in t or ("page_hints" in t and "does not exist" in t)


def _missing_resp():
    return jsonify({"error": f"Highlights need {svc.MIGRATION} run in Supabase (safe to re-run).",
                    "migration": svc.MIGRATION, "available": False}), 503


def _failed_resp(exc):
    logger.exception("page hints: write failed")
    t = _detail(exc)
    if "42501" in t or "row-level security" in t:
        msg = ("Supabase refused the write (row-level security). The server's SUPABASE_KEY "
               "must be the secret/service key for page_hints.")
    else:
        msg = "Could not save the hint: " + t[:300]
    return jsonify({"error": msg}), 502


def _page(raw):
    p = str(raw or "").split("?")[0].split("#")[0].strip()[:300]
    return p if p.startswith("/") else ""


def _turn(q):
    return {"q": q, "a": "", "status": "pending", "error": None, "model": None, "at": svc._now()}


def _one(hid):
    rows = get(svc.TABLE, params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}",
                                  "deleted_at": "is.null", "select": COLS, "limit": "1"}) or []
    return rows[0] if rows else None


@page_hints_bp.route("/api/hints", methods=["GET"])
@login_required
def hints_list():
    page = _page(request.args.get("page"))
    if not page:
        return jsonify({"error": "page is required"}), 400
    try:
        rows = get(svc.TABLE, params={"user_id": f"eq.{session['user_id']}", "page": f"eq.{page}",
                                      "deleted_at": "is.null", "select": COLS,
                                      "order": "created_at.asc", "limit": "300"}) or []
    except Exception as exc:
        if _missing(exc):
            return jsonify({"available": False, "items": [], "migration": svc.MIGRATION})
        raise
    return jsonify({"available": True, "items": rows})


@page_hints_bp.route("/api/hints", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def hints_create():
    data = request.get_json(silent=True) or {}
    page = _page(data.get("page"))
    if not page:
        return jsonify({"error": "page is required"}), 400
    quote = svc.clean_text(data.get("quote"), 500)
    question = str(data.get("question") or "").strip()[:svc.MAX_QUESTION] or (
        "Explain this part simply, with a small example." if quote else "")
    if not question:
        return jsonify({"error": "Write your question first."}), 400
    context = str(data.get("context") or "")[:svc.MAX_CONTEXT]
    row = {"user_id": session["user_id"], "page": page,
           "anchor": svc.clean_text(data.get("anchor"), 200), "quote": quote,
           "prefix": svc.clean_text(data.get("prefix"), 200)[-80:], "thread": [_turn(question)]}
    try:
        created = post(svc.TABLE, row) or []
    except Exception as exc:
        if _missing(exc):
            return _missing_resp()
        return _failed_resp(exc)
    item = created[0] if created else None
    if not item or not item.get("id"):
        return jsonify({"error": "Could not save the highlight."}), 502
    svc.answer_in_background(item["id"], session["user_id"], page, quote, context, 0)
    return jsonify({"item": item}), 201


@page_hints_bp.route("/api/hints/<hid>/ask", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def hints_ask(hid):
    data = request.get_json(silent=True) or {}
    question = str(data.get("question") or "").strip()[:svc.MAX_QUESTION]
    if not question:
        return jsonify({"error": "Write your question first."}), 400
    try:
        h = _one(hid)
    except Exception as exc:
        if _missing(exc):
            return _missing_resp()
        return _failed_resp(exc)
    if not h:
        return jsonify({"error": "Not found."}), 404
    thread = list(h.get("thread") or [])
    if thread and thread[-1].get("status") == "pending":
        return jsonify({"error": "Wait for the last answer first."}), 409
    if len(thread) >= svc.MAX_TURNS:
        return jsonify({"error": "This hint is long enough - start a new highlight."}), 400
    thread.append(_turn(question))
    update(svc.TABLE, params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}"},
           json={"thread": thread, "updated_at": svc._now()})
    svc.answer_in_background(hid, session["user_id"], h["page"], h.get("quote") or "",
                             str(data.get("context") or "")[:svc.MAX_CONTEXT], len(thread) - 1)
    return jsonify({"item": dict(h, thread=thread)})


@page_hints_bp.route("/api/hints/<hid>/retry", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def hints_retry(hid):
    data = request.get_json(silent=True) or {}
    try:
        h = _one(hid)
    except Exception as exc:
        if _missing(exc):
            return _missing_resp()
        return _failed_resp(exc)
    if not h or not h.get("thread"):
        return jsonify({"error": "Not found."}), 404
    thread = list(h["thread"])
    if thread[-1].get("status") == "pending":
        return jsonify({"item": h})
    thread[-1] = dict(thread[-1], a="", status="pending", error=None)
    update(svc.TABLE, params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}"},
           json={"thread": thread, "updated_at": svc._now()})
    svc.answer_in_background(hid, session["user_id"], h["page"], h.get("quote") or "",
                             str(data.get("context") or "")[:svc.MAX_CONTEXT], len(thread) - 1)
    return jsonify({"item": dict(h, thread=thread)})


@page_hints_bp.route("/api/hints/<hid>/delete", methods=["POST"])
@login_required
def hints_delete(hid):
    try:
        update(svc.TABLE, params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}"},
               json={"deleted_at": svc._now()})
    except Exception as exc:
        if _missing(exc):
            return _missing_resp()
        return _failed_resp(exc)
    return jsonify({"status": "ok"})

"""Sharing items with the other people on this planner.

One blueprint for every kind of shareable thing, because "share this with
Shreya for Tuesday at 7" is one sentence whatever the thing is. The
composition lives in services/shared_items_service.py; this file is the
HTTP edge and, more importantly, the ownership checks.

    GET  /api/people                     who can be shared with
    GET  /api/shared/grants              current grants for one item
    POST /api/shared/share               replace the set of recipients
    GET  /api/shared/mine                what has been shared WITH me
    GET  /api/shared/sent                what I shared, and who finished
    POST /api/shared/<share_id>/complete tick it off (recipient only)

OWNERSHIP IS CHECKED BEFORE ANYTHING IS WRITTEN. For an inbox link that
means the row must be yours; without it, anyone who knew an id could
share someone else's item with themselves and read it. A prep topic has
no owner — the banks ship with the app and belong to nobody — so anyone
may share one, which is why the two kinds are checked differently and
explicitly rather than through one vague guard.
"""

import logging

from flask import Blueprint, jsonify, request, session

from services import shared_items_service as shares
from services.login_service import login_required
from supabase_client import get

logger = logging.getLogger("daily_plan")
shared_bp = Blueprint("shared", __name__)


def _owns_inbox_item(user_id, item_id):
    rows = get("inbox_links", params={
        "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
        "select": "id,title,url", "limit": "1",
    }) or []
    return rows[0] if rows else None


@shared_bp.route("/api/people", methods=["GET"])
@login_required
def people():
    return jsonify({"people": shares.people(session["user_id"])})


@shared_bp.route("/api/shared/grants", methods=["GET"])
@login_required
def grants():
    kind = (request.args.get("kind") or "").strip()
    ref = (request.args.get("item_ref") or "").strip()
    if kind not in shares.KINDS or not ref:
        return jsonify({"error": "kind and item_ref required"}), 400
    try:
        rows = shares.grants_for(session["user_id"], kind, ref)
    except Exception:
        logger.exception("shared: could not read grants")
        return jsonify({"grants": [], "unavailable": True})
    return jsonify({"grants": rows})


@shared_bp.route("/api/shared/share", methods=["POST"])
@login_required
def share():
    me = session["user_id"]
    data = request.get_json(silent=True) or {}
    kind = (data.get("kind") or "").strip()
    ref = (data.get("item_ref") or "").strip()
    if kind not in shares.KINDS or not ref:
        return jsonify({"error": "kind and item_ref required"}), 400
    if not isinstance(data.get("user_ids"), list):
        return jsonify({"error": "user_ids must be a list"}), 400

    title = (data.get("title") or "").strip()
    url = (data.get("url") or "").strip() or None
    bank = (data.get("bank") or "").strip() or None

    if kind == "inbox":
        # Yours to share, or not yours at all.
        row = _owns_inbox_item(me, ref)
        if not row:
            return jsonify({"error": "not found"}), 404
        # Trust the row over the client for what the thing is called.
        title = title or (row.get("title") or "")
        url = url or row.get("url")

    try:
        ids = shares.share(
            me, kind=kind, item_ref=ref, user_ids=data["user_ids"],
            title=title, url=url, bank=bank,
            due_date=data.get("due_date"), due_time=data.get("due_time"),
        )
    except Exception:
        logger.exception("shared: share failed")
        return jsonify({
            "error": "Could not share it. If this is the first time, the "
                     "shared_items table may not be created yet.",
        }), 500
    return jsonify({"user_ids": ids, "count": len(ids)})


@shared_bp.route("/api/shared/mine", methods=["GET"])
@login_required
def mine():
    try:
        return jsonify({"items": shares.assigned_to(session["user_id"])})
    except Exception:
        # A missing table must not break the chat page it is embedded in.
        logger.exception("shared: could not list what was shared with me")
        return jsonify({"items": [], "unavailable": True})


@shared_bp.route("/api/shared/sent", methods=["GET"])
@login_required
def sent():
    try:
        return jsonify({"items": shares.sent_by(session["user_id"])})
    except Exception:
        logger.exception("shared: could not list what I shared")
        return jsonify({"items": [], "unavailable": True})


@shared_bp.route("/api/shared/<share_id>/complete", methods=["POST"])
@login_required
def complete(share_id):
    data = request.get_json(silent=True) or {}
    done = data.get("done", True) is not False
    stamp = shares.set_completed(session["user_id"], share_id, done)
    if stamp is None:
        # Not addressed to you: say so rather than reporting a success
        # for a write that changed nothing.
        return jsonify({"error": "That item was not shared with you."}), 403
    return jsonify({"completed_at": stamp or None})

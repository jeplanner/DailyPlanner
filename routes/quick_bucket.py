"""Quick Bucket — the simple Tasks Bucket.

Just the bare minimum: type a one-liner, it lands in a "when" bucket
(Now / 4h / 8h / Future), one toggle button cycles the bucket. No
category classifier, no destination routing, no gamification — by
design, after the earlier richer version turned out to be too much.

Endpoints:
    GET  /quick-bucket                  page render
    GET  /api/quick-bucket               list active items
    POST /api/quick-bucket               add new item
    POST /api/quick-bucket/<id>/cycle    next time bucket
    POST /api/quick-bucket/<id>/update   edit text / set bucket directly
    POST /api/quick-bucket/<id>/done     mark complete
    POST /api/quick-bucket/<id>/archive  soft-delete

Soft-delete only — see project convention (memory: no-hard-delete).
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
quick_bucket_bp = Blueprint("quick_bucket", __name__)

# Buckets in cycle order. Clicking the toggle steps to the next one;
# wrapping around lets the user un-do an over-shoot without thinking.
BUCKETS = ["now", "4h", "8h", "future"]
BUCKET_SET = set(BUCKETS)
_MAX_TEXT_LEN = 500


def _next_bucket(cur):
    try:
        i = BUCKETS.index(cur or "now")
    except ValueError:
        return BUCKETS[0]
    return BUCKETS[(i + 1) % len(BUCKETS)]


# ─────────── page ─────────────────────────────────────────────

@quick_bucket_bp.route("/quick-bucket", methods=["GET"])
@login_required
def quick_bucket_page():
    return render_template("quick_bucket.html", buckets=BUCKETS)


# ─────────── list ────────────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket", methods=["GET"])
@login_required
def list_items():
    user_id = session["user_id"]
    try:
        rows = get(
            "quick_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_done": "eq.false",
                "select": "id,text,time_bucket,position,created_at,updated_at",
                "order": "position.asc,created_at.desc",
                "limit": "500",
            },
        ) or []
    except Exception:
        logger.exception("quick_bucket list failed")
        return jsonify({"items": [], "buckets": BUCKETS, "error": "Could not load"}), 200
    return jsonify({"items": rows, "buckets": BUCKETS})


# ─────────── create ──────────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket", methods=["POST"])
@login_required
def add_item():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text required"}), 400
    text = text[:_MAX_TEXT_LEN]

    bucket = (data.get("time_bucket") or "now").strip().lower()
    if bucket not in BUCKET_SET:
        bucket = "now"

    payload = {
        "user_id": user_id,
        "text": text,
        "time_bucket": bucket,
        "position": int(data.get("position") or 0),
        "is_done": False,
        "is_deleted": False,
    }
    try:
        rows = post("quick_bucket", payload)
    except Exception as e:
        logger.error("quick_bucket insert failed: %s", e)
        return jsonify({"error": "Couldn't add — please try again."}), 502
    return jsonify({"ok": True, "item": rows[0] if rows else None})


# ─────────── cycle bucket ────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/cycle", methods=["POST"])
@login_required
def cycle_bucket(item_id):
    user_id = session["user_id"]
    rows = get(
        "quick_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,time_bucket",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404

    nxt = _next_bucket(rows[0].get("time_bucket"))
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"time_bucket": nxt},
        )
    except Exception as e:
        logger.error("quick_bucket cycle failed: %s", e)
        return jsonify({"error": "Couldn't change — please try again."}), 502
    return jsonify({"ok": True, "time_bucket": nxt})


# ─────────── update text or set bucket directly ──────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/update", methods=["POST"])
@login_required
def update_item(item_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    patch = {}
    if "text" in data:
        v = (data.get("text") or "").strip()
        if not v:
            return jsonify({"error": "Text required"}), 400
        patch["text"] = v[:_MAX_TEXT_LEN]
    if "time_bucket" in data:
        v = (data.get("time_bucket") or "").strip().lower()
        if v not in BUCKET_SET:
            return jsonify({"error": "Invalid bucket"}), 400
        patch["time_bucket"] = v
    if "position" in data:
        try:
            patch["position"] = int(data["position"])
        except (TypeError, ValueError):
            pass

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("quick_bucket update failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502
    return jsonify({"ok": True, "patch": patch})


# ─────────── mark done ───────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/done", methods=["POST"])
@login_required
def mark_done(item_id):
    user_id = session["user_id"]
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_done": True, "done_at": datetime.utcnow().isoformat()},
        )
    except Exception as e:
        logger.error("quick_bucket done failed: %s", e)
        return jsonify({"error": "Couldn't update — please try again."}), 502
    return jsonify({"ok": True})


# ─────────── archive (soft-delete) ───────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/archive", methods=["POST"])
@login_required
def archive_item(item_id):
    """Soft-delete: hide the row but keep it in storage. No hard delete
    — see project convention (memory: no-hard-delete)."""
    user_id = session["user_id"]
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_deleted": True},
        )
    except Exception as e:
        logger.error("quick_bucket archive failed: %s", e)
        return jsonify({"error": "Couldn't remove — please try again."}), 502
    return jsonify({"ok": True})

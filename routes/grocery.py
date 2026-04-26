"""Grocery — a simple per-user shopping list.

Endpoints:
    GET  /grocery                         page render
    GET  /api/grocery                     list active items
    POST /api/grocery                     add new item
    POST /api/grocery/<id>/update         edit fields
    POST /api/grocery/<id>/toggle         toggle purchased
    POST /api/grocery/<id>/archive        soft delete
    POST /api/grocery/clear-purchased     archive every purchased item

Soft-delete only — see DECISIONS / memory:no-hard-delete. Items the
user "removes" set is_archived=true; the row stays so analytics or
future undo are possible.
"""

import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
grocery_bp = Blueprint("grocery", __name__)


# Suggested categories shown in the UI dropdown. Storage is free-form
# text — anything outside this list is accepted, but the UI nudges
# users toward consistent buckets so the grouped view stays useful.
SUGGESTED_CATEGORIES = [
    "produce",
    "dairy",
    "staples",
    "snacks",
    "household",
    "spices",
    "frozen",
    "beverages",
    "meat",
    "bakery",
    "other",
]

VALID_PRIORITIES = {"low", "medium", "high"}

_MAX_ITEM_LEN = 120
_MAX_QUANTITY_LEN = 40
_MAX_NOTES_LEN = 400
_MAX_CATEGORY_LEN = 40


def _normalize_category(raw):
    raw = (raw or "").strip().lower()
    if not raw:
        return "other"
    raw = re.sub(r"[^a-z\-]+", "-", raw).strip("-")
    return raw[:_MAX_CATEGORY_LEN] or "other"


def _normalize_priority(raw):
    raw = (raw or "").strip().lower()
    return raw if raw in VALID_PRIORITIES else "medium"


# ─────────── Page ────────────────────────────────────────────────


@grocery_bp.route("/grocery", methods=["GET"])
@login_required
def grocery_page():
    """Render the grocery list page. Initial data comes from the API
    (client-side fetch on load) so the template stays thin."""
    return render_template(
        "grocery.html",
        suggested_categories=SUGGESTED_CATEGORIES,
        priorities=sorted(VALID_PRIORITIES, key=lambda p: ["high", "medium", "low"].index(p)),
    )


# ─────────── API: list ───────────────────────────────────────────


@grocery_bp.route("/api/grocery", methods=["GET"])
@login_required
def list_grocery():
    """Return every active grocery item for the current user.

    Query params:
        include_purchased=1 → include purchased rows (default: yes)
        only_open=1         → exclude purchased rows
    """
    user_id = session["user_id"]

    only_open = request.args.get("only_open") == "1"
    params = {
        "user_id": f"eq.{user_id}",
        "is_archived": "eq.false",
        "select": "id,item,quantity,category,notes,priority,is_purchased,purchased_at,created_at,updated_at",
        "order": "is_purchased.asc,priority.asc,category.asc,created_at.desc",
        "limit": "1000",
    }
    if only_open:
        params["is_purchased"] = "eq.false"

    try:
        rows = get("groceries", params=params) or []
    except Exception as e:
        logger.warning("grocery list failed: %s", e)
        return jsonify({"items": [], "error": "Could not load list"}), 200

    # Stable client-side ordering: purchased to the bottom, then
    # priority (high first), then alpha by item.
    prio_rank = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda r: (
        bool(r.get("is_purchased")),
        prio_rank.get((r.get("priority") or "medium"), 1),
        (r.get("category") or "").lower(),
        (r.get("item") or "").lower(),
    ))

    return jsonify({
        "items": rows,
        "categories": SUGGESTED_CATEGORIES,
        "priorities": ["high", "medium", "low"],
    })


# ─────────── API: create ─────────────────────────────────────────


@grocery_bp.route("/api/grocery", methods=["POST"])
@login_required
def add_grocery():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    item = (data.get("item") or "").strip()
    if not item:
        return jsonify({"error": "Item name required"}), 400
    if len(item) > _MAX_ITEM_LEN:
        item = item[:_MAX_ITEM_LEN]

    quantity = (data.get("quantity") or "").strip()[:_MAX_QUANTITY_LEN] or None
    notes = (data.get("notes") or "").strip()[:_MAX_NOTES_LEN] or None
    category = _normalize_category(data.get("category"))
    priority = _normalize_priority(data.get("priority"))

    payload = {
        "user_id": user_id,
        "item": item,
        "quantity": quantity,
        "category": category,
        "notes": notes,
        "priority": priority,
        "is_purchased": False,
        "is_archived": False,
    }

    try:
        rows = post("groceries", payload)
    except Exception as e:
        logger.error("grocery insert failed: %s", e)
        return jsonify({"error": "Couldn't add — please try again."}), 502

    return jsonify({"ok": True, "item": rows[0] if rows else None})


# ─────────── API: update fields ──────────────────────────────────


@grocery_bp.route("/api/grocery/<grocery_id>/update", methods=["POST"])
@login_required
def update_grocery(grocery_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    patch = {}
    if "item" in data:
        v = (data.get("item") or "").strip()
        if not v:
            return jsonify({"error": "Item name required"}), 400
        patch["item"] = v[:_MAX_ITEM_LEN]
    if "quantity" in data:
        v = (data.get("quantity") or "").strip()
        patch["quantity"] = v[:_MAX_QUANTITY_LEN] or None
    if "notes" in data:
        v = (data.get("notes") or "").strip()
        patch["notes"] = v[:_MAX_NOTES_LEN] or None
    if "category" in data:
        patch["category"] = _normalize_category(data.get("category"))
    if "priority" in data:
        patch["priority"] = _normalize_priority(data.get("priority"))

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update(
            "groceries",
            params={"id": f"eq.{grocery_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("grocery update failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502

    return jsonify({"ok": True, "patch": patch})


# ─────────── API: toggle purchased ───────────────────────────────


@grocery_bp.route("/api/grocery/<grocery_id>/toggle", methods=["POST"])
@login_required
def toggle_purchased(grocery_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    if "purchased" in data:
        want = bool(data.get("purchased"))
    else:
        # Flip — fetch current state.
        rows = get(
            "groceries",
            params={
                "id": f"eq.{grocery_id}",
                "user_id": f"eq.{user_id}",
                "select": "is_purchased",
                "limit": "1",
            },
        ) or []
        if not rows:
            return jsonify({"error": "Not found"}), 404
        want = not bool(rows[0].get("is_purchased"))

    patch = {
        "is_purchased": want,
        "purchased_at": datetime.utcnow().isoformat() if want else None,
    }
    try:
        update(
            "groceries",
            params={"id": f"eq.{grocery_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("grocery toggle failed: %s", e)
        return jsonify({"error": "Couldn't update — please try again."}), 502

    return jsonify({"ok": True, "is_purchased": want})


# ─────────── API: archive ────────────────────────────────────────


@grocery_bp.route("/api/grocery/<grocery_id>/archive", methods=["POST"])
@login_required
def archive_grocery(grocery_id):
    """Soft-delete: hide the row from the list but keep it in storage.
    No hard delete — see project convention (memory: no-hard-delete)."""
    user_id = session["user_id"]
    try:
        update(
            "groceries",
            params={"id": f"eq.{grocery_id}", "user_id": f"eq.{user_id}"},
            json={"is_archived": True},
        )
    except Exception as e:
        logger.error("grocery archive failed: %s", e)
        return jsonify({"error": "Couldn't remove — please try again."}), 502

    return jsonify({"ok": True})


# ─────────── API: bulk clear purchased ───────────────────────────


@grocery_bp.route("/api/grocery/clear-purchased", methods=["POST"])
@login_required
def clear_purchased():
    """Archive every purchased item in one go — useful after a
    shopping run to reset the visible list without losing history."""
    user_id = session["user_id"]
    try:
        update(
            "groceries",
            params={
                "user_id": f"eq.{user_id}",
                "is_purchased": "eq.true",
                "is_archived": "eq.false",
            },
            json={"is_archived": True},
        )
    except Exception as e:
        logger.error("grocery clear-purchased failed: %s", e)
        return jsonify({"error": "Couldn't clear — please try again."}), 502

    return jsonify({"ok": True})

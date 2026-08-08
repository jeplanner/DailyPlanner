"""Investments — a simple net-worth tracker.

A deliberately small feature: each entry is one investment you hold,
recorded as just Name + Type + Date + Total Amount (INR). The page sums
them into a grand total. No live prices or symbols — that's the richer
/portfolio feature. This is the manual version.

Name and Type are free-text but auto-suggest values the user has used
before (built from their own history), so each field starts empty and
grows into a useful pick-list as they go.

Schema: see MIGRATION_INVESTMENTS.sql. Soft-delete only (deleted_at).
"""
import logging
from collections import Counter
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update
from utils.user_tz import user_today

logger = logging.getLogger("daily_plan")

investments_bp = Blueprint("investments", __name__)

_MAX_NAME = 80
_MAX_TYPE = 60
_SUGGESTIONS = 40
_SELECT = "id,name,type,invested_on,amount,created_at,updated_at"


def _today_iso():
    try:
        return user_today().isoformat()
    except Exception:
        return date.today().isoformat()


def _shape(row):
    return {
        "id": row.get("id"),
        "name": row.get("name") or "",
        "type": row.get("type") or "",
        "invested_on": row.get("invested_on"),
        "amount": float(row["amount"]) if row.get("amount") is not None else 0.0,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _parse_fields(data):
    """Shared parse/validate for add & edit. Returns (fragment, error)."""
    name = (data.get("name") or "").strip()[:_MAX_NAME]
    if not name:
        return None, "Give the investment a name"
    try:
        amount = round(float(data.get("amount")), 2)
    except (TypeError, ValueError):
        return None, "Enter a valid total amount"
    if amount < 0:
        return None, "Amount can't be negative"
    return {
        "name": name,
        "type": (data.get("type") or "").strip()[:_MAX_TYPE] or None,
        "invested_on": (data.get("invested_on") or "").strip() or _today_iso(),
        "amount": amount,
    }, None


@investments_bp.route("/investments", methods=["GET"])
@login_required
def investments_page():
    return render_template("investments.html", today=_today_iso())


@investments_bp.route("/api/investments", methods=["GET"])
@login_required
def list_investments():
    """Every live investment for the user, newest-first, plus the grand
    total of all their amounts."""
    user_id = session["user_id"]
    try:
        rows = get("investments", {
            "user_id": f"eq.{user_id}",
            "deleted_at": "is.null",
            "select": _SELECT,
            "order": "invested_on.desc,created_at.desc",
        }) or []
    except Exception as e:
        # Table not created yet (migration pending) — render cleanly.
        logger.warning("investments list failed (run MIGRATION_INVESTMENTS.sql?): %s", e)
        return jsonify({"items": [], "total": 0, "migration_pending": True})

    items = [_shape(r) for r in rows]
    total = round(sum(i["amount"] for i in items), 2)
    return jsonify({"items": items, "total": total})


@investments_bp.route("/api/investments/suggestions", methods=["GET"])
@login_required
def suggestions():
    """The user's previously-used names and types, most-used first —
    drives the dropdown suggestions. Empty lists for a new user."""
    user_id = session["user_id"]
    try:
        rows = get("investments", {
            "user_id": f"eq.{user_id}",
            "deleted_at": "is.null",
            "select": "name,type",
            "order": "created_at.desc",
            "limit": "1000",
        }) or []
    except Exception as e:
        logger.warning("investments suggestions lookup failed: %s", e)
        return jsonify({"names": [], "types": []})

    def _ranked(field):
        counts = Counter(
            (r.get(field) or "").strip()
            for r in rows if (r.get(field) or "").strip()
        )
        return sorted(counts, key=lambda c: (-counts[c], c.lower()))[:_SUGGESTIONS]

    return jsonify({"names": _ranked("name"), "types": _ranked("type")})


@investments_bp.route("/api/investments", methods=["POST"])
@login_required
def add_investment():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    frag, err = _parse_fields(data)
    if err:
        return jsonify({"error": err}), 400

    payload = {"user_id": user_id, **frag}
    try:
        rows = post("investments", payload)
    except Exception as e:
        logger.exception("add investment failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again"}), 502
    return jsonify({"item": _shape(rows[0] if rows else payload)})


@investments_bp.route("/api/investments/<item_id>", methods=["PUT", "PATCH"])
@login_required
def edit_investment(item_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    frag, err = _parse_fields(data)
    if err:
        return jsonify({"error": err}), 400

    frag["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        update(
            "investments",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
                    "deleted_at": "is.null"},
            json=frag,
        )
    except Exception as e:
        logger.exception("edit investment failed: %s", e)
        return jsonify({"error": "Couldn't save changes — please try again"}), 502

    try:
        rows = get("investments", {
            "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
            "select": _SELECT, "limit": "1",
        }) or []
    except Exception:
        rows = []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"item": _shape(rows[0])})


@investments_bp.route("/api/investments/<item_id>/delete", methods=["POST"])
@login_required
def delete_investment(item_id):
    user_id = session["user_id"]
    try:
        update(
            "investments",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"deleted_at": datetime.now(timezone.utc).isoformat()},
        )
    except Exception as e:
        logger.exception("delete investment failed: %s", e)
        return jsonify({"error": "Couldn't delete"}), 502
    return jsonify({"ok": True})

"""Relationship tracker — keep in touch with the people who matter.

Stores a list of people with a desired contact cadence (e.g. mom every
14 days, mentor every 30 days). The daily summary surfaces overdue
contacts based on (today - last_contact_date >= cadence_days).

Schema lives in MIGRATION_PHASE3.sql:
    relationships(id, user_id, name, relation, cadence_days,
                  last_contact_date, notes, is_archived,
                  created_at, updated_at)
"""

from datetime import date, datetime
from flask import Blueprint, jsonify, render_template, request, session

from services.login_service import login_required
from supabase_client import get, post, update

relationships_bp = Blueprint("relationships", __name__)


@relationships_bp.route("/relationships")
@login_required
def relationships_page():
    """Render the relationships page. Data is fetched client-side via
    the JSON API to keep the template thin."""
    return render_template("relationships.html")


@relationships_bp.route("/api/relationships", methods=["GET"])
@login_required
def list_relationships():
    user_id = session["user_id"]
    rows = get(
        "relationships",
        params={
            "user_id": f"eq.{user_id}",
            "is_archived": "eq.false",
            "select": "id,name,relation,cadence_days,last_contact_date,notes",
            "order": "name.asc",
        },
    ) or []

    today = date.today()
    out = []
    for r in rows:
        cadence = int(r.get("cadence_days") or 14)
        lc = r.get("last_contact_date")
        if lc:
            try:
                last = date.fromisoformat(lc)
                days_since = (today - last).days
                overdue_by = max(0, days_since - cadence)
            except ValueError:
                days_since = None
                overdue_by = 0
        else:
            days_since = None
            overdue_by = cadence  # treat "never contacted" as fully overdue
        out.append({**r, "days_since": days_since, "overdue_by": overdue_by})

    # Most overdue first, then alpha
    out.sort(key=lambda x: (-x["overdue_by"], (x.get("name") or "").lower()))
    return jsonify({"relationships": out})


@relationships_bp.route("/api/relationships", methods=["POST"])
@login_required
def add_relationship():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    payload = {
        "user_id": user_id,
        "name": name,
        "relation": (data.get("relation") or "").strip() or None,
        "cadence_days": int(data.get("cadence_days") or 14),
        "last_contact_date": data.get("last_contact_date") or None,
        "notes": (data.get("notes") or "").strip() or None,
    }
    rows = post("relationships", payload)
    return jsonify({"id": rows[0]["id"] if rows else None})


@relationships_bp.route("/api/relationships/<rel_id>", methods=["PATCH"])
@login_required
def update_relationship(rel_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    allowed = {"name", "relation", "cadence_days", "last_contact_date",
               "notes", "is_archived"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        return jsonify({"error": "nothing to update"}), 400
    patch["updated_at"] = datetime.utcnow().isoformat() + "Z"

    update(
        "relationships",
        params={"id": f"eq.{rel_id}", "user_id": f"eq.{user_id}"},
        json=patch,
    )
    return jsonify({"ok": True})


@relationships_bp.route("/api/relationships/<rel_id>/touch", methods=["POST"])
@login_required
def touch_relationship(rel_id):
    """Mark "I just contacted them" — sets last_contact_date to today."""
    user_id = session["user_id"]
    today_iso = date.today().isoformat()
    update(
        "relationships",
        params={"id": f"eq.{rel_id}", "user_id": f"eq.{user_id}"},
        json={"last_contact_date": today_iso,
              "updated_at": datetime.utcnow().isoformat() + "Z"},
    )
    return jsonify({"ok": True, "date": today_iso})

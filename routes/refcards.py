"""
Reference Cards — A hub for recurring tasks, important info, SOPs, credentials, and checklists.
Organized by context (Home, Office, etc.) and category (Bills, IT, Vehicle, Health, etc.)
"""
import uuid
from datetime import date, datetime
from flask import Blueprint, request, jsonify, session, render_template
from supabase_client import get, post, update, delete
from services.login_service import login_required
from config import IST
from utils.encryption import encrypt_fields, decrypt_fields, decrypt_rows

refcards_bp = Blueprint("refcards", __name__)

# Fields that contain sensitive data — encrypted at rest in Supabase
ENCRYPTED_FIELDS = ["account_number", "customer_id", "portal_url", "notes", "payment_method"]


# ═══════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════

@refcards_bp.route("/refcards")
@login_required
def refcards_page():
    return render_template("refcards.html")


# ═══════════════════════════════════════════════════
# CONTEXTS (homes / offices / vehicles / etc.)
# ═══════════════════════════════════════════════════

@refcards_bp.route("/api/refcards/contexts", methods=["GET"])
@login_required
def list_contexts():
    rows = get("ref_contexts", params={
        "user_id": f"eq.{session['user_id']}",
        "order": "position.asc,name.asc",
    }) or []
    return jsonify(rows)


@refcards_bp.route("/api/refcards/contexts", methods=["POST"])
@login_required
def add_context():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400

    rows = post("ref_contexts", {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "name": name,
        "address": (data.get("address") or "").strip(),
        "position": data.get("position", 0),
    })
    return jsonify(rows[0] if rows else {"name": name})


@refcards_bp.route("/api/refcards/contexts/<ctx_id>", methods=["PUT"])
@login_required
def update_context(ctx_id):
    data = request.get_json() or {}
    allowed = {}
    for f in ["name", "address", "position"]:
        if f in data:
            allowed[f] = data[f]
    if not allowed:
        return jsonify({"error": "Nothing to update"}), 400

    update("ref_contexts",
           params={"id": f"eq.{ctx_id}", "user_id": f"eq.{session['user_id']}"},
           json=allowed)
    return jsonify({"success": True})


@refcards_bp.route("/api/refcards/contexts/<ctx_id>", methods=["DELETE"])
@login_required
def delete_context(ctx_id):
    delete("ref_cards",
           params={"property_id": f"eq.{ctx_id}", "user_id": f"eq.{session['user_id']}"})
    delete("ref_contexts",
           params={"id": f"eq.{ctx_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# REFERENCE CARDS
# ═══════════════════════════════════════════════════

@refcards_bp.route("/api/refcards/cards", methods=["GET"])
@login_required
def list_cards():
    user_id = session["user_id"]
    ctx_id = request.args.get("context_id")
    category = request.args.get("category")
    search = request.args.get("q", "").strip()

    params = {
        "user_id": f"eq.{user_id}",
        "order": "category.asc,provider.asc",
    }
    if ctx_id:
        params["property_id"] = f"eq.{ctx_id}"
    if category:
        params["category"] = f"eq.{category}"

    rows = get("ref_cards", params=params) or []

    # Decrypt sensitive fields before search and return
    decrypt_rows(rows, ENCRYPTED_FIELDS)

    if search:
        s = search.lower()
        rows = [r for r in rows if
                s in (r.get("provider") or "").lower() or
                s in (r.get("category") or "").lower() or
                s in (r.get("notes") or "").lower() or
                s in (r.get("account_number") or "").lower() or
                s in (r.get("customer_id") or "").lower()]

    return jsonify(rows)


@refcards_bp.route("/api/refcards/cards", methods=["POST"])
@login_required
def add_card():
    data = request.get_json() or {}

    if not (data.get("category") or "").strip():
        return jsonify({"error": "Category is required"}), 400
    if not (data.get("provider") or "").strip():
        return jsonify({"error": "Title is required"}), 400

    card = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "property_id": data.get("property_id") or None,
        "category": data["category"].strip(),
        "provider": data["provider"].strip(),
        "account_number": (data.get("account_number") or "").strip() or None,
        "amount": float(data["amount"]) if data.get("amount") else None,
        "currency": data.get("currency", "INR"),
        "billing_cycle": data.get("billing_cycle") or None,
        "due_day": int(data["due_day"]) if data.get("due_day") else None,
        "auto_pay": bool(data.get("auto_pay", False)),
        "payment_method": (data.get("payment_method") or "").strip() or None,
        "portal_url": (data.get("portal_url") or "").strip() or None,
        "customer_id": (data.get("customer_id") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
        "status": data.get("status", "active"),
    }

    encrypt_fields(card, ENCRYPTED_FIELDS)

    rows = post("ref_cards", card)
    if rows:
        decrypt_fields(rows[0], ENCRYPTED_FIELDS)
    return jsonify(rows[0] if rows else data)


@refcards_bp.route("/api/refcards/cards/<card_id>", methods=["PUT"])
@login_required
def update_card(card_id):
    data = request.get_json() or {}
    allowed_fields = [
        "category", "provider", "account_number", "amount", "currency",
        "billing_cycle", "due_day", "auto_pay", "payment_method",
        "portal_url", "customer_id", "notes", "status", "property_id",
    ]
    payload = {f: data[f] for f in allowed_fields if f in data}

    if not payload:
        return jsonify({"error": "Nothing to update"}), 400

    encrypt_fields(payload, ENCRYPTED_FIELDS)

    update("ref_cards",
           params={"id": f"eq.{card_id}", "user_id": f"eq.{session['user_id']}"},
           json=payload)
    return jsonify({"success": True})


@refcards_bp.route("/api/refcards/cards/<card_id>", methods=["DELETE"])
@login_required
def delete_card(card_id):
    delete("ref_activity_log",
           params={"bill_id": f"eq.{card_id}", "user_id": f"eq.{session['user_id']}"})
    delete("ref_cards",
           params={"id": f"eq.{card_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# ACTIVITY LOG
# ═══════════════════════════════════════════════════

@refcards_bp.route("/api/refcards/log/<card_id>", methods=["GET"])
@login_required
def get_log(card_id):
    rows = get("ref_activity_log", params={
        "bill_id": f"eq.{card_id}",
        "user_id": f"eq.{session['user_id']}",
        "order": "paid_date.desc",
        "limit": 50,
    }) or []
    return jsonify(rows)


@refcards_bp.route("/api/refcards/log", methods=["POST"])
@login_required
def add_log():
    data = request.get_json() or {}
    card_id = data.get("card_id") or data.get("bill_id")
    if not card_id:
        return jsonify({"error": "card_id required"}), 400

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "bill_id": card_id,
        "paid_date": data.get("paid_date") or datetime.now(IST).date().isoformat(),
        "amount": float(data["amount"]) if data.get("amount") else None,
        "method": (data.get("method") or "").strip() or None,
        "reference": (data.get("reference") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
    }

    rows = post("ref_activity_log", entry)
    return jsonify(rows[0] if rows else entry)


# ═══════════════════════════════════════════════════
# DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════

@refcards_bp.route("/api/refcards/summary", methods=["GET"])
@login_required
def refcards_summary():
    user_id = session["user_id"]
    today = datetime.now(IST).date()

    cards = get("ref_cards", params={
        "user_id": f"eq.{user_id}",
        "status": "eq.active",
    }) or []

    total_monthly = 0
    upcoming = []
    overdue = []

    for b in cards:
        amt = b.get("amount") or 0
        cycle = b.get("billing_cycle") or ""
        if cycle == "monthly":
            total_monthly += amt
        elif cycle == "quarterly":
            total_monthly += amt / 3
        elif cycle in ("half-yearly", "half_yearly"):
            total_monthly += amt / 6
        elif cycle == "yearly":
            total_monthly += amt / 12

        due_day = b.get("due_day")
        if due_day:
            try:
                if today.day <= due_day:
                    next_due = today.replace(day=min(due_day, 28))
                else:
                    m = today.month + 1 if today.month < 12 else 1
                    y = today.year if today.month < 12 else today.year + 1
                    next_due = date(y, m, min(due_day, 28))

                days_until = (next_due - today).days
                info = {
                    "id": b["id"],
                    "provider": b["provider"],
                    "category": b["category"],
                    "amount": amt,
                    "due_date": next_due.isoformat(),
                    "days_until": days_until,
                }
                if days_until < 0:
                    overdue.append(info)
                elif days_until <= 7:
                    upcoming.append(info)
            except (ValueError, TypeError):
                pass

    cat_counts = {}
    for b in cards:
        c = b.get("category", "Other")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    return jsonify({
        "total_monthly": round(total_monthly, 2),
        "active_cards": len(cards),
        "upcoming": sorted(upcoming, key=lambda x: x["days_until"]),
        "overdue": sorted(overdue, key=lambda x: x["days_until"]),
        "categories": cat_counts,
    })

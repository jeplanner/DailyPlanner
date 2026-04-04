import uuid
from datetime import date, datetime
from flask import Blueprint, request, jsonify, session, render_template
from supabase_client import get, post, update, delete
from services.login_service import login_required
from config import IST

payments_bp = Blueprint("payments", __name__)


# ═══════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════

@payments_bp.route("/payments")
@login_required
def payments_page():
    return render_template("payments.html")


# ═══════════════════════════════════════════════════
# PROPERTIES (homes / locations)
# ═══════════════════════════════════════════════════

@payments_bp.route("/api/payments/properties", methods=["GET"])
@login_required
def list_properties():
    rows = get("payment_properties", params={
        "user_id": f"eq.{session['user_id']}",
        "order": "position.asc,name.asc",
    }) or []
    return jsonify(rows)


@payments_bp.route("/api/payments/properties", methods=["POST"])
@login_required
def add_property():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Property name required"}), 400

    rows = post("payment_properties", {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "name": name,
        "address": (data.get("address") or "").strip(),
        "position": data.get("position", 0),
    })
    return jsonify(rows[0] if rows else {"name": name})


@payments_bp.route("/api/payments/properties/<prop_id>", methods=["PUT"])
@login_required
def update_property(prop_id):
    data = request.get_json() or {}
    allowed = {}
    for f in ["name", "address", "position"]:
        if f in data:
            allowed[f] = data[f]
    if not allowed:
        return jsonify({"error": "Nothing to update"}), 400

    update("payment_properties",
           params={"id": f"eq.{prop_id}", "user_id": f"eq.{session['user_id']}"},
           json=allowed)
    return jsonify({"success": True})


@payments_bp.route("/api/payments/properties/<prop_id>", methods=["DELETE"])
@login_required
def delete_property(prop_id):
    # Delete all bills under this property first
    delete("payment_bills",
           params={"property_id": f"eq.{prop_id}", "user_id": f"eq.{session['user_id']}"})
    delete("payment_properties",
           params={"id": f"eq.{prop_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# BILLS (recurring payment references)
# ═══════════════════════════════════════════════════

@payments_bp.route("/api/payments/bills", methods=["GET"])
@login_required
def list_bills():
    user_id = session["user_id"]
    prop_id = request.args.get("property_id")

    params = {
        "user_id": f"eq.{user_id}",
        "order": "category.asc,provider.asc",
    }
    if prop_id:
        params["property_id"] = f"eq.{prop_id}"

    rows = get("payment_bills", params=params) or []
    return jsonify(rows)


@payments_bp.route("/api/payments/bills", methods=["POST"])
@login_required
def add_bill():
    data = request.get_json() or {}

    required = ["property_id", "category", "provider"]
    for f in required:
        if not data.get(f, "").strip():
            return jsonify({"error": f"{f} is required"}), 400

    bill = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "property_id": data["property_id"],
        "category": data["category"].strip(),
        "provider": data["provider"].strip(),
        "account_number": (data.get("account_number") or "").strip(),
        "amount": float(data["amount"]) if data.get("amount") else None,
        "currency": data.get("currency", "INR"),
        "billing_cycle": data.get("billing_cycle", "monthly"),
        "due_day": int(data["due_day"]) if data.get("due_day") else None,
        "auto_pay": bool(data.get("auto_pay", False)),
        "payment_method": (data.get("payment_method") or "").strip(),
        "portal_url": (data.get("portal_url") or "").strip(),
        "customer_id": (data.get("customer_id") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
        "status": data.get("status", "active"),
    }

    rows = post("payment_bills", bill)
    return jsonify(rows[0] if rows else bill)


@payments_bp.route("/api/payments/bills/<bill_id>", methods=["PUT"])
@login_required
def update_bill(bill_id):
    data = request.get_json() or {}
    allowed_fields = [
        "category", "provider", "account_number", "amount", "currency",
        "billing_cycle", "due_day", "auto_pay", "payment_method",
        "portal_url", "customer_id", "notes", "status", "property_id",
    ]
    payload = {}
    for f in allowed_fields:
        if f in data:
            payload[f] = data[f]

    if not payload:
        return jsonify({"error": "Nothing to update"}), 400

    update("payment_bills",
           params={"id": f"eq.{bill_id}", "user_id": f"eq.{session['user_id']}"},
           json=payload)
    return jsonify({"success": True})


@payments_bp.route("/api/payments/bills/<bill_id>", methods=["DELETE"])
@login_required
def delete_bill(bill_id):
    # Delete payment history for this bill
    delete("payment_history",
           params={"bill_id": f"eq.{bill_id}", "user_id": f"eq.{session['user_id']}"})
    delete("payment_bills",
           params={"id": f"eq.{bill_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# PAYMENT HISTORY (actual payments logged)
# ═══════════════════════════════════════════════════

@payments_bp.route("/api/payments/history/<bill_id>", methods=["GET"])
@login_required
def get_history(bill_id):
    rows = get("payment_history", params={
        "bill_id": f"eq.{bill_id}",
        "user_id": f"eq.{session['user_id']}",
        "order": "paid_date.desc",
        "limit": 24,
    }) or []
    return jsonify(rows)


@payments_bp.route("/api/payments/history", methods=["POST"])
@login_required
def log_payment():
    data = request.get_json() or {}
    bill_id = data.get("bill_id")
    if not bill_id:
        return jsonify({"error": "bill_id required"}), 400

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "bill_id": bill_id,
        "paid_date": data.get("paid_date") or datetime.now(IST).date().isoformat(),
        "amount": float(data["amount"]) if data.get("amount") else None,
        "method": (data.get("method") or "").strip(),
        "reference": (data.get("reference") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
    }

    rows = post("payment_history", entry)
    return jsonify(rows[0] if rows else entry)


# ═══════════════════════════════════════════════════
# DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════

@payments_bp.route("/api/payments/summary", methods=["GET"])
@login_required
def payment_summary():
    user_id = session["user_id"]
    today = datetime.now(IST).date()

    bills = get("payment_bills", params={
        "user_id": f"eq.{user_id}",
        "status": "eq.active",
    }) or []

    total_monthly = 0
    upcoming = []
    overdue = []

    for b in bills:
        amt = b.get("amount") or 0
        if b.get("billing_cycle") == "monthly":
            total_monthly += amt
        elif b.get("billing_cycle") == "quarterly":
            total_monthly += amt / 3
        elif b.get("billing_cycle") == "yearly":
            total_monthly += amt / 12

        due_day = b.get("due_day")
        if due_day:
            # Compute next due date
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
                "property_id": b.get("property_id"),
            }
            if days_until < 0:
                overdue.append(info)
            elif days_until <= 7:
                upcoming.append(info)

    return jsonify({
        "total_monthly": round(total_monthly, 2),
        "active_bills": len(bills),
        "upcoming": sorted(upcoming, key=lambda x: x["days_until"]),
        "overdue": sorted(overdue, key=lambda x: x["days_until"]),
    })

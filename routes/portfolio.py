"""
Portfolio Watchlist — Track stocks, mutual funds, ETFs, FDs, bonds, cash, gold, PPF, NPS, etc.
Import from ICICI Direct CSV. XIRR calculation. Field-level encryption.
"""
import uuid
import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify, session, render_template
from supabase_client import get, post, update, delete
from services.login_service import login_required
from config import IST
from utils.encryption import encrypt_fields, decrypt_fields, decrypt_rows

logger = logging.getLogger("daily_plan")
portfolio_bp = Blueprint("portfolio", __name__)

# Sensitive fields encrypted at rest
ENCRYPTED_FIELDS = ["name", "symbol", "folio_number", "broker", "notes",
                    "institution", "account_ref"]


# ═══════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/portfolio")
@login_required
def portfolio_page():
    return render_template("portfolio.html")


# ═══════════════════════════════════════════════════
# HOLDINGS CRUD
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio/holdings", methods=["GET"])
@login_required
def list_holdings():
    user_id = session["user_id"]
    asset_type = request.args.get("type")

    params = {
        "user_id": f"eq.{user_id}",
        "order": "asset_type.asc,name.asc",
    }
    if asset_type:
        params["asset_type"] = f"eq.{asset_type}"

    rows = get("portfolio_holdings", params=params) or []
    decrypt_rows(rows, ENCRYPTED_FIELDS)
    return jsonify(rows)


@portfolio_bp.route("/api/portfolio/holdings", methods=["POST"])
@login_required
def add_holding():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    holding = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "name": name,
        "symbol": (data.get("symbol") or "").strip().upper() or None,
        "asset_type": data.get("asset_type", "stock"),
        "exchange": (data.get("exchange") or "").strip().upper() or None,
        "quantity": float(data["quantity"]) if data.get("quantity") else 0,
        "avg_price": float(data["avg_price"]) if data.get("avg_price") else 0,
        "current_price": float(data["current_price"]) if data.get("current_price") else None,
        "currency": data.get("currency", "INR"),
        "folio_number": (data.get("folio_number") or "").strip() or None,
        "broker": (data.get("broker") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
        "sector": (data.get("sector") or "").strip() or None,
        # FD / Bond / PPF specific fields
        "institution": (data.get("institution") or "").strip() or None,
        "interest_rate": float(data["interest_rate"]) if data.get("interest_rate") else None,
        "maturity_date": data.get("maturity_date") or None,
        "start_date": data.get("start_date") or None,
        "account_ref": (data.get("account_ref") or "").strip() or None,
    }

    encrypt_fields(holding, ENCRYPTED_FIELDS)
    rows = post("portfolio_holdings", holding)
    if rows:
        decrypt_fields(rows[0], ENCRYPTED_FIELDS)
    return jsonify(rows[0] if rows else data)


@portfolio_bp.route("/api/portfolio/holdings/<hid>", methods=["PUT"])
@login_required
def update_holding(hid):
    data = request.get_json() or {}
    allowed = [
        "name", "symbol", "asset_type", "exchange", "quantity", "avg_price",
        "current_price", "currency", "folio_number", "broker", "notes", "sector",
        "institution", "interest_rate", "maturity_date", "start_date", "account_ref",
    ]
    payload = {f: data[f] for f in allowed if f in data}
    if not payload:
        return jsonify({"error": "Nothing to update"}), 400

    encrypt_fields(payload, ENCRYPTED_FIELDS)
    update("portfolio_holdings",
           params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}"},
           json=payload)
    return jsonify({"success": True})


@portfolio_bp.route("/api/portfolio/holdings/<hid>", methods=["DELETE"])
@login_required
def delete_holding(hid):
    delete("portfolio_holdings",
           params={"id": f"eq.{hid}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# BULK IMPORT (CSV parsed on client, sent as JSON)
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio/import", methods=["POST"])
@login_required
def import_holdings():
    data = request.get_json() or {}
    rows = data.get("rows", [])
    broker = data.get("broker", "ICICI Direct")

    if not rows:
        return jsonify({"error": "No rows to import"}), 400

    user_id = session["user_id"]
    created = 0

    for r in rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue

        try:
            row_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": name,
                "symbol": (r.get("symbol") or "").strip().upper() or None,
                "asset_type": r.get("asset_type", "stock"),
                "exchange": (r.get("exchange") or "").strip().upper() or None,
                "quantity": float(r["quantity"]) if r.get("quantity") else 0,
                "avg_price": float(r["avg_price"]) if r.get("avg_price") else 0,
                "current_price": float(r["current_price"]) if r.get("current_price") else None,
                "currency": r.get("currency", "INR"),
                "folio_number": (r.get("folio_number") or "").strip() or None,
                "broker": broker,
                "sector": (r.get("sector") or "").strip() or None,
            }
            encrypt_fields(row_data, ENCRYPTED_FIELDS)
            post("portfolio_holdings", row_data)
            created += 1
        except Exception as e:
            logger.warning("Import row failed: %s", str(e))

    return jsonify({"status": "ok", "imported": created})


# ═══════════════════════════════════════════════════
# BULK PRICE UPDATE
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio/update-prices", methods=["POST"])
@login_required
def update_prices():
    """Update current_price for multiple holdings at once."""
    data = request.get_json() or {}
    prices = data.get("prices", {})  # {holding_id: new_price}

    user_id = session["user_id"]
    updated = 0

    for hid, price in prices.items():
        try:
            update("portfolio_holdings",
                   params={"id": f"eq.{hid}", "user_id": f"eq.{user_id}"},
                   json={"current_price": float(price)})
            updated += 1
        except Exception:
            pass

    return jsonify({"status": "ok", "updated": updated})


# ═══════════════════════════════════════════════════
# TRANSACTIONS (buy/sell/dividend log for XIRR)
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio/transactions/<holding_id>", methods=["GET"])
@login_required
def list_transactions(holding_id):
    rows = get("portfolio_transactions", params={
        "holding_id": f"eq.{holding_id}",
        "user_id": f"eq.{session['user_id']}",
        "order": "txn_date.desc",
        "limit": 100,
    }) or []
    return jsonify(rows)


@portfolio_bp.route("/api/portfolio/transactions", methods=["POST"])
@login_required
def add_transaction():
    data = request.get_json() or {}
    holding_id = data.get("holding_id")
    if not holding_id:
        return jsonify({"error": "holding_id required"}), 400

    txn = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "holding_id": holding_id,
        "txn_type": data.get("txn_type", "buy"),
        "txn_date": data.get("txn_date") or datetime.now(IST).date().isoformat(),
        "quantity": float(data["quantity"]) if data.get("quantity") else 0,
        "price": float(data["price"]) if data.get("price") else 0,
        "amount": float(data["amount"]) if data.get("amount") else None,
        "notes": (data.get("notes") or "").strip() or None,
    }

    # Auto-calc amount if not provided
    if not txn["amount"] and txn["quantity"] and txn["price"]:
        txn["amount"] = round(txn["quantity"] * txn["price"], 2)

    rows = post("portfolio_transactions", txn)
    return jsonify(rows[0] if rows else txn)


@portfolio_bp.route("/api/portfolio/transactions/<txn_id>", methods=["DELETE"])
@login_required
def delete_transaction(txn_id):
    delete("portfolio_transactions",
           params={"id": f"eq.{txn_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# XIRR CALCULATION
# ═══════════════════════════════════════════════════

def _xirr(cashflows):
    """
    Compute XIRR (annualized IRR) using Newton's method.
    cashflows: list of (date, amount) tuples.
    Negative amounts = outflow (buy), positive = inflow (sell/current value).
    Returns annualized rate as decimal (0.12 = 12%), or None if can't converge.
    """
    if len(cashflows) < 2:
        return None

    from datetime import date as dt_date

    # Sort by date
    cashflows = sorted(cashflows, key=lambda x: x[0])
    d0 = cashflows[0][0]

    def _days(d):
        return (d - d0).days

    def _npv(rate):
        return sum(amt / (1 + rate) ** (_days(d) / 365.0) for d, amt in cashflows)

    def _dnpv(rate):
        return sum(-(_days(d) / 365.0) * amt / (1 + rate) ** (_days(d) / 365.0 + 1)
                    for d, amt in cashflows)

    # Newton's method
    guess = 0.1
    for _ in range(200):
        npv = _npv(guess)
        dnpv = _dnpv(guess)
        if abs(dnpv) < 1e-12:
            break
        new_guess = guess - npv / dnpv
        if abs(new_guess - guess) < 1e-9:
            return round(new_guess * 100, 2)
        guess = new_guess
        # Clamp to avoid divergence
        if guess < -0.99:
            guess = -0.99

    return round(guess * 100, 2)


@portfolio_bp.route("/api/portfolio/xirr/<holding_id>", methods=["GET"])
@login_required
def holding_xirr(holding_id):
    """Compute XIRR for a single holding from its transactions + current value."""
    user_id = session["user_id"]

    txns = get("portfolio_transactions", params={
        "holding_id": f"eq.{holding_id}",
        "user_id": f"eq.{user_id}",
        "order": "txn_date.asc",
    }) or []

    holding = get("portfolio_holdings", params={
        "id": f"eq.{holding_id}",
        "user_id": f"eq.{user_id}",
    })
    if not holding:
        return jsonify({"error": "Not found"}), 404

    h = holding[0]
    qty = float(h.get("quantity") or 0)
    cmp = float(h.get("current_price") or h.get("avg_price") or 0)

    cashflows = []
    for t in txns:
        d = date.fromisoformat(t["txn_date"])
        amt = float(t.get("amount") or 0)
        if t["txn_type"] == "buy":
            cashflows.append((d, -abs(amt)))
        elif t["txn_type"] in ("sell", "dividend"):
            cashflows.append((d, abs(amt)))

    # If no transactions, use avg_price as single buy
    if not cashflows:
        avg = float(h.get("avg_price") or 0)
        if avg and qty:
            buy_date = date.fromisoformat(h["created_at"][:10]) if h.get("created_at") else datetime.now(IST).date()
            cashflows.append((buy_date, -(qty * avg)))

    # Add current value as final "sell"
    if qty > 0 and cmp > 0:
        cashflows.append((datetime.now(IST).date(), qty * cmp))

    xirr = _xirr(cashflows) if len(cashflows) >= 2 else None

    return jsonify({"xirr": xirr, "cashflows_count": len(cashflows)})


@portfolio_bp.route("/api/portfolio/xirr", methods=["GET"])
@login_required
def portfolio_xirr():
    """Compute portfolio-level XIRR from all transactions."""
    user_id = session["user_id"]

    txns = get("portfolio_transactions", params={
        "user_id": f"eq.{user_id}",
        "order": "txn_date.asc",
    }) or []

    holdings = get("portfolio_holdings", params={
        "user_id": f"eq.{user_id}",
    }) or []

    cashflows = []

    # All transactions
    for t in txns:
        d = date.fromisoformat(t["txn_date"])
        amt = float(t.get("amount") or 0)
        if t["txn_type"] == "buy":
            cashflows.append((d, -abs(amt)))
        elif t["txn_type"] in ("sell", "dividend"):
            cashflows.append((d, abs(amt)))

    # If no transactions, derive from holdings
    if not cashflows:
        for h in holdings:
            qty = float(h.get("quantity") or 0)
            avg = float(h.get("avg_price") or 0)
            if qty and avg:
                buy_date = date.fromisoformat(h["created_at"][:10]) if h.get("created_at") else datetime.now(IST).date()
                cashflows.append((buy_date, -(qty * avg)))

    # Current portfolio value as final inflow
    today = datetime.now(IST).date()
    total_current = sum(
        float(h.get("quantity") or 0) * float(h.get("current_price") or h.get("avg_price") or 0)
        for h in holdings
    )
    if total_current > 0:
        cashflows.append((today, total_current))

    xirr = _xirr(cashflows) if len(cashflows) >= 2 else None

    return jsonify({"xirr": xirr, "cashflows_count": len(cashflows)})


# ═══════════════════════════════════════════════════
# PORTFOLIO SUMMARY
# ═══════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio/summary", methods=["GET"])
@login_required
def portfolio_summary():
    user_id = session["user_id"]

    holdings = get("portfolio_holdings", params={
        "user_id": f"eq.{user_id}",
    }) or []

    total_invested = 0
    total_current = 0
    by_type = {}

    for h in holdings:
        qty = float(h.get("quantity") or 0)
        avg = float(h.get("avg_price") or 0)
        cur = float(h.get("current_price") or avg)
        invested = qty * avg
        current = qty * cur

        total_invested += invested
        total_current += current

        t = h.get("asset_type", "other")
        if t not in by_type:
            by_type[t] = {"invested": 0, "current": 0, "count": 0}
        by_type[t]["invested"] += invested
        by_type[t]["current"] += current
        by_type[t]["count"] += 1

    total_pnl = total_current - total_invested
    total_pnl_pct = round((total_pnl / total_invested * 100), 2) if total_invested else 0

    return jsonify({
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "holdings_count": len(holdings),
        "by_type": by_type,
    })

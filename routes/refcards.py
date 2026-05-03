"""
Reference Cards — secure vault for financial instruments, identity documents,
credentials, and recurring bills. Supports Indian and US contexts.

Security model (Phase 1 — pragmatic medium-strength)
────────────────────────────────────────────────────
1. **Login auth** gates the whole app (@login_required).
2. **Vault password** — a separate password the user sets on first use.
   Required to unlock the page and any sensitive API endpoint.
   • Hashed with werkzeug's pbkdf2 hash (same convention as the rest of
     the app's password handling).
   • On unlock, the server stores a short-lived session flag
     `vault_unlocked_at` (epoch seconds). The flag auto-expires after
     `VAULT_SESSION_TTL_SECONDS` of inactivity.
   • Every sensitive endpoint re-checks the flag via the
     `@vault_unlocked_required` decorator — no "grant then forget."
3. **At-rest encryption** (unchanged from before): sensitive fields go
   through utils.encryption (Fernet / PBKDF2) using a server-side key.
   This is defense-in-depth for a DB-only breach.

What Phase 1 does NOT protect against
─────────────────────────────────────
• A compromised server (the ENCRYPTION_KEY lives server-side).
• A compromised device with an active vault-unlocked session.
• An attacker who obtained the user's login session AND vault password.

Phase 2 (deferred) — zero-knowledge client-side encryption with a
user-password-derived key via Web Crypto. The `details` JSON column is
designed so Phase 2 slots in without schema changes.

Database additions (run once against Supabase)
──────────────────────────────────────────────

    create table if not exists vault_settings (
      user_id         text primary key,
      password_hash   text not null,
      auto_lock_minutes integer default 15,
      created_at      timestamptz default now(),
      updated_at      timestamptz default now()
    );

    alter table ref_cards
      add column if not exists instrument_type text,
      add column if not exists country text,
      add column if not exists details text;
    -- `details` is encrypted JSON (Fernet ciphertext); kept as text so
    -- the column contract is "whatever encrypt() returns".
"""
import json
import logging
import time
import uuid
from datetime import date, datetime
from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import IST
from utils.user_tz import user_now, user_today
from services.login_service import login_required
from supabase_client import delete, get, post, update
from utils.encryption import (
    decrypt, decrypt_fields, decrypt_rows, encrypt, encrypt_fields,
    is_active as encryption_is_active,
)

logger = logging.getLogger(__name__)

refcards_bp = Blueprint("refcards", __name__)

# Fields encrypted at rest (server-side Fernet). `details` is the new
# JSON blob for instrument-specific attributes; encrypted as a whole.
ENCRYPTED_FIELDS = ["account_number", "customer_id", "portal_url", "notes", "payment_method", "details"]

# Default auto-lock window for a vault session. Can be overridden per user
# via vault_settings.auto_lock_minutes, clamped to [2, 60] minutes.
VAULT_SESSION_TTL_SECONDS_DEFAULT = 15 * 60
VAULT_TTL_MIN = 2 * 60
VAULT_TTL_MAX = 60 * 60


# ═══════════════════════════════════════════════════
# VAULT LOCK — session-based gate on top of @login_required
# ═══════════════════════════════════════════════════

def _vault_row(user_id):
    """Fetch the vault_settings row for a user; None if they haven't set
    a vault password yet."""
    try:
        rows = get("vault_settings", params={"user_id": f"eq.{user_id}", "limit": 1}) or []
        return rows[0] if rows else None
    except Exception as e:
        logger.warning("vault_row fetch failed: %s", e)
        return None


def _vault_ttl_seconds(vault_row):
    """Resolve the auto-lock window, in seconds, for this user."""
    if not vault_row:
        return VAULT_SESSION_TTL_SECONDS_DEFAULT
    try:
        mins = int(vault_row.get("auto_lock_minutes") or 15)
    except (ValueError, TypeError):
        mins = 15
    ttl = max(VAULT_TTL_MIN // 60, min(VAULT_TTL_MAX // 60, mins)) * 60
    return ttl


def _vault_is_unlocked(user_id):
    """True if the user has an active (non-expired) vault session."""
    unlocked_at = session.get("vault_unlocked_at")
    if not unlocked_at:
        return False
    try:
        unlocked_at = float(unlocked_at)
    except (ValueError, TypeError):
        return False
    vrow = _vault_row(user_id)
    ttl = _vault_ttl_seconds(vrow)
    return (time.time() - unlocked_at) <= ttl


def _vault_touch():
    """Slide the session TTL forward by updating the unlocked_at timestamp.
    Called implicitly on every authenticated sensitive endpoint."""
    session["vault_unlocked_at"] = time.time()


def vault_unlocked_required(fn):
    """Decorator: requires the vault to be unlocked in this session.
    Refreshes the TTL on success. Combines with @login_required on the
    call site (which must be applied first / outermost)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        vrow = _vault_row(user_id)
        if not vrow:
            # No password set — client should send the user through setup.
            return jsonify({"error": "Vault not configured", "code": "vault_not_set"}), 403
        if not _vault_is_unlocked(user_id):
            return jsonify({"error": "Vault is locked", "code": "vault_locked"}), 403
        _vault_touch()
        return fn(*args, **kwargs)
    return wrapper


def vault_gate_for_blueprint(page_label: str):
    """Blueprint-level vault gate. Returns a Flask response when the
    vault is unsetup or locked, else None to let the request proceed.

    Designed to be invoked from `before_request` on any blueprint that
    should sit behind the same vault password as /refcards. Distinguishes
    API vs page requests by URL prefix:
      - /api/* paths get a JSON 403 with a code the caller can act on.
      - Page paths render a standalone lock template that posts the
        password to the existing vault unlock endpoint, then reloads.

    Unauth requests return None so flask_login's redirect-to-login
    behaviour still wins on the per-route @login_required decorator."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    vrow = _vault_row(user_id)
    is_api = request.path.startswith("/api/")
    if not vrow:
        if is_api:
            return jsonify({
                "error": "Vault not configured",
                "code": "vault_not_set",
            }), 403
        # User hasn't set a vault password yet. Send them to /refcards
        # where the setup UI lives — re-implementing setup here would
        # duplicate code that's already polished.
        return redirect(url_for("refcards.refcards_page"))
    if not _vault_is_unlocked(user_id):
        if is_api:
            return jsonify({
                "error": "Vault is locked",
                "code": "vault_locked",
            }), 403
        return render_template(
            "vault_lock_gate.html",
            page_label=page_label,
            return_to=request.full_path.rstrip("?") or request.path,
        )
    _vault_touch()
    return None


# ─────────────────────────────────────────────────────
# VAULT SETUP / UNLOCK / LOCK / STATUS
# ─────────────────────────────────────────────────────

@refcards_bp.route("/api/refcards/vault/status", methods=["GET"])
@login_required
def vault_status():
    user_id = session["user_id"]
    vrow = _vault_row(user_id)
    unlocked = _vault_is_unlocked(user_id) if vrow else False
    ttl = _vault_ttl_seconds(vrow)
    return jsonify({
        "configured": bool(vrow),
        "unlocked": unlocked,
        "auto_lock_minutes": (vrow.get("auto_lock_minutes") if vrow else 15),
        "ttl_seconds": ttl,
    })


@refcards_bp.route("/api/refcards/vault/set-password", methods=["POST"])
@login_required
def vault_set_password():
    """First-time vault password setup. Refuses if a password is already
    set — use change-password for rotations."""
    user_id = session["user_id"]
    data = request.get_json() or {}
    password = (data.get("password") or "").strip()
    auto_lock = data.get("auto_lock_minutes")

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing = _vault_row(user_id)
    if existing:
        return jsonify({"error": "Vault password already set — use change-password instead"}), 409

    try:
        mins = int(auto_lock) if auto_lock else 15
    except (ValueError, TypeError):
        mins = 15
    mins = max(2, min(60, mins))

    row = {
        "user_id": user_id,
        "password_hash": generate_password_hash(password),
        "auto_lock_minutes": mins,
    }
    post("vault_settings", row)
    # First-time setup implicitly unlocks for this session.
    _vault_touch()
    return jsonify({"success": True, "unlocked": True})


@refcards_bp.route("/api/refcards/vault/change-password", methods=["POST"])
@login_required
@vault_unlocked_required
def vault_change_password():
    """Rotate the vault password. Must already be unlocked so a casual
    bystander can't change it from an active session."""
    user_id = session["user_id"]
    data = request.get_json() or {}
    current = (data.get("current_password") or "").strip()
    new_pw = (data.get("new_password") or "").strip()

    vrow = _vault_row(user_id)
    if not vrow or not check_password_hash(vrow.get("password_hash") or "", current):
        return jsonify({"error": "Current password is wrong"}), 403
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    update("vault_settings",
           params={"user_id": f"eq.{user_id}"},
           json={"password_hash": generate_password_hash(new_pw)})
    _vault_touch()
    return jsonify({"success": True})


@refcards_bp.route("/api/refcards/vault/unlock", methods=["POST"])
@login_required
def vault_unlock():
    user_id = session["user_id"]
    data = request.get_json() or {}
    password = (data.get("password") or "").strip()

    vrow = _vault_row(user_id)
    if not vrow:
        return jsonify({"error": "Vault not configured", "code": "vault_not_set"}), 403
    if not check_password_hash(vrow.get("password_hash") or "", password):
        # Sleep briefly to slow brute force; in-memory only — no DB counter.
        time.sleep(0.4)
        return jsonify({"error": "Wrong password"}), 403

    _vault_touch()
    return jsonify({"success": True, "ttl_seconds": _vault_ttl_seconds(vrow)})


@refcards_bp.route("/api/refcards/vault/lock", methods=["POST"])
@login_required
def vault_lock():
    session.pop("vault_unlocked_at", None)
    return jsonify({"success": True})


@refcards_bp.route("/api/refcards/vault/settings", methods=["PUT"])
@login_required
@vault_unlocked_required
def vault_update_settings():
    user_id = session["user_id"]
    data = request.get_json() or {}
    mins = data.get("auto_lock_minutes")
    try:
        mins = int(mins)
    except (ValueError, TypeError):
        return jsonify({"error": "auto_lock_minutes must be a number"}), 400
    mins = max(2, min(60, mins))
    update("vault_settings",
           params={"user_id": f"eq.{user_id}"},
           json={"auto_lock_minutes": mins})
    return jsonify({"success": True, "auto_lock_minutes": mins})


# ═══════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════

@refcards_bp.route("/refcards")
@login_required
def refcards_page():
    # encryption_active=False means ENCRYPTION_KEY is missing on the
    # server, so any vault writes are landing as plaintext. The
    # template renders a sticky warning banner so this can't silently
    # regress (e.g. if the env var gets cleared during a Render edit).
    return render_template(
        "refcards.html",
        encryption_active=encryption_is_active(),
    )


# ═══════════════════════════════════════════════════
# CONTEXTS (homes / offices / vehicles / owners)
# ═══════════════════════════════════════════════════

@refcards_bp.route("/api/refcards/contexts", methods=["GET"])
@login_required
@vault_unlocked_required
def list_contexts():
    rows = get("ref_contexts", params={
        "user_id": f"eq.{session['user_id']}",
        "order": "position.asc,name.asc",
    }) or []
    return jsonify(rows)


@refcards_bp.route("/api/refcards/contexts", methods=["POST"])
@login_required
@vault_unlocked_required
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
@vault_unlocked_required
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
@vault_unlocked_required
def delete_context(ctx_id):
    delete("ref_cards",
           params={"property_id": f"eq.{ctx_id}", "user_id": f"eq.{session['user_id']}"})
    delete("ref_contexts",
           params={"id": f"eq.{ctx_id}", "user_id": f"eq.{session['user_id']}"})
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════
# REFERENCE CARDS
# ═══════════════════════════════════════════════════

def _normalize_details(raw):
    """Store the instrument-specific JSON blob as a compact string;
    returns None for empty payloads so we don't carry empty ciphertext."""
    if raw is None:
        return None
    if isinstance(raw, str):
        raw_str = raw.strip()
        if not raw_str or raw_str in ("{}", "null"):
            return None
        return raw_str
    if isinstance(raw, (dict, list)):
        if not raw:
            return None
        return json.dumps(raw, separators=(",", ":"))
    return None


def _parse_details(value):
    """Ciphertext → JSON object. Returns {} on any parse error so the
    UI can still render the rest of the card."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


@refcards_bp.route("/api/refcards/cards", methods=["GET"])
@login_required
@vault_unlocked_required
def list_cards():
    user_id = session["user_id"]
    ctx_id = request.args.get("context_id")
    instrument = request.args.get("instrument_type")
    category = request.args.get("category")
    search = request.args.get("q", "").strip()

    params = {
        "user_id": f"eq.{user_id}",
        "order": "instrument_type.asc,category.asc,provider.asc",
    }
    if ctx_id:
        params["property_id"] = f"eq.{ctx_id}"
    if instrument:
        params["instrument_type"] = f"eq.{instrument}"
    if category:
        params["category"] = f"eq.{category}"

    rows = get("ref_cards", params=params) or []

    # Decrypt at-rest fields (including the `details` JSON blob) before
    # returning. Any row whose `details` is unreadable comes back with
    # details={} so the UI can still render the non-sensitive header.
    decrypt_rows(rows, ENCRYPTED_FIELDS)
    for r in rows:
        r["details"] = _parse_details(r.get("details"))

    if search:
        s = search.lower()
        def _match(r):
            hay = " ".join(str(r.get(f) or "") for f in (
                "provider", "category", "instrument_type", "notes",
                "account_number", "customer_id",
            ))
            if s in hay.lower():
                return True
            # Also match inside the decrypted details JSON
            det = r.get("details") or {}
            return s in json.dumps(det).lower()
        rows = [r for r in rows if _match(r)]

    return jsonify(rows)


@refcards_bp.route("/api/refcards/cards", methods=["POST"])
@login_required
@vault_unlocked_required
def add_card():
    data = request.get_json() or {}

    if not (data.get("provider") or "").strip():
        return jsonify({"error": "Title is required"}), 400

    # instrument_type is the new primary axis (bank, credit_card, passport, …).
    # category is kept for backwards compat / free-form grouping.
    instrument_type = (data.get("instrument_type") or "").strip() or None
    country = (data.get("country") or "").strip().upper() or None
    if country and country not in ("IN", "US", "BOTH", "OTHER"):
        country = None

    details_raw = _normalize_details(data.get("details"))

    card = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "property_id": data.get("property_id") or None,
        "instrument_type": instrument_type,
        "country": country,
        "category": (data.get("category") or instrument_type or "Other").strip(),
        "provider": data["provider"].strip(),
        "account_number": (data.get("account_number") or "").strip() or None,
        "amount": float(data["amount"]) if data.get("amount") else None,
        "currency": data.get("currency") or ("INR" if country == "IN" else "USD" if country == "US" else "INR"),
        "billing_cycle": data.get("billing_cycle") or None,
        "due_day": int(data["due_day"]) if data.get("due_day") else None,
        "auto_pay": bool(data.get("auto_pay", False)),
        "payment_method": (data.get("payment_method") or "").strip() or None,
        "portal_url": (data.get("portal_url") or "").strip() or None,
        "customer_id": (data.get("customer_id") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
        "details": details_raw,
        "status": data.get("status", "active"),
    }

    encrypt_fields(card, ENCRYPTED_FIELDS)

    rows = post("ref_cards", card)
    if rows:
        decrypt_fields(rows[0], ENCRYPTED_FIELDS)
        rows[0]["details"] = _parse_details(rows[0].get("details"))
    return jsonify(rows[0] if rows else data)


@refcards_bp.route("/api/refcards/cards/<card_id>", methods=["PUT"])
@login_required
@vault_unlocked_required
def update_card(card_id):
    data = request.get_json() or {}
    allowed_fields = [
        "instrument_type", "country",
        "category", "provider", "account_number", "amount", "currency",
        "billing_cycle", "due_day", "auto_pay", "payment_method",
        "portal_url", "customer_id", "notes", "status", "property_id",
        "details",
    ]
    payload = {f: data[f] for f in allowed_fields if f in data}

    if "country" in payload:
        v = (payload["country"] or "").strip().upper() or None
        if v and v not in ("IN", "US", "BOTH", "OTHER"):
            v = None
        payload["country"] = v

    if "details" in payload:
        payload["details"] = _normalize_details(payload["details"])

    if not payload:
        return jsonify({"error": "Nothing to update"}), 400

    encrypt_fields(payload, ENCRYPTED_FIELDS)

    update("ref_cards",
           params={"id": f"eq.{card_id}", "user_id": f"eq.{session['user_id']}"},
           json=payload)
    return jsonify({"success": True})


@refcards_bp.route("/api/refcards/cards/<card_id>", methods=["DELETE"])
@login_required
@vault_unlocked_required
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
@vault_unlocked_required
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
@vault_unlocked_required
def add_log():
    data = request.get_json() or {}
    card_id = data.get("card_id") or data.get("bill_id")
    if not card_id:
        return jsonify({"error": "card_id required"}), 400

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "bill_id": card_id,
        "paid_date": data.get("paid_date") or user_today().isoformat(),
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
@vault_unlocked_required
def refcards_summary():
    user_id = session["user_id"]
    today = user_today()

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
    instrument_counts = {}
    for b in cards:
        c = b.get("category", "Other")
        cat_counts[c] = cat_counts.get(c, 0) + 1
        it = b.get("instrument_type") or "other"
        instrument_counts[it] = instrument_counts.get(it, 0) + 1

    return jsonify({
        "total_monthly": round(total_monthly, 2),
        "active_cards": len(cards),
        "upcoming": sorted(upcoming, key=lambda x: x["days_until"]),
        "overdue": sorted(overdue, key=lambda x: x["days_until"]),
        "categories": cat_counts,
        "instruments": instrument_counts,
    })

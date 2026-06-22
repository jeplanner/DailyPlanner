"""Daily expenses — capture money spent on a day.

A deliberately small feature: amount + category + optional note, dated.
The category field is free-text but auto-suggests categories the user
has used before (built from their own history), so it's empty to start
and grows into a useful pick-list as they log spends.

Schema: see MIGRATION_EXPENSES.sql. Soft-delete only (deleted_at).
"""
import io
import logging
from collections import Counter
from datetime import date

from flask import Blueprint, jsonify, render_template, request, session, url_for

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from auth import login_required
from supabase_client import get, post, update
from utils.user_tz import user_today

logger = logging.getLogger("daily_plan")

expenses_bp = Blueprint("expenses", __name__)

_MAX_CATEGORY = 60
_MAX_NOTE = 300
_MAX_TAG = 40
_CATEGORY_SUGGESTIONS = 40

# Recurrence values and how many times each fires per year — used to
# normalise a recurring amount into a monthly / yearly projection.
_RECURRENCE = ("none", "daily", "monthly", "quarterly", "yearly")
_PER_YEAR = {"daily": 365.0, "monthly": 12.0, "quarterly": 4.0, "yearly": 1.0}
_NEED_WANT = ("need", "want", "saving")
_COST_TYPE = ("fixed", "variable")

# Fields the user can slice ("dissect") the monthly report by, mapped to
# the row column that carries them.
_DISSECT = {
    "category": "category",
    "need_want": "need_want",
    "cost_type": "cost_type",
    "tag": "tag",
    "recurrence": "recurrence",
}
_DISSECT_FALLBACK = {
    "category": "Uncategorised",
    "need_want": "Unclassified",
    "cost_type": "Unclassified",
    "tag": "Untagged",
    "recurrence": "single",
}
_MAX_RECEIPT_BYTES = 15 * 1024 * 1024  # 15 MB

# Drive folder layout for receipts:  dailyplanner / receipts
_RECEIPT_PARENT = "dailyplanner"
_RECEIPT_FOLDER = "receipts"


def _ensure_receipts_folder(service, user_id, row):
    """Return the Drive id of  dailyplanner/receipts , creating either
    folder on first use and caching the receipts id on the token row."""
    cached = (row or {}).get("receipts_folder_id")
    if cached:
        try:
            service.files().get(fileId=cached, fields="id, trashed").execute()
            return cached
        except HttpError:
            pass

    def _find_or_create(name, parent=None):
        q = (f"mimeType='application/vnd.google-apps.folder' and name='{name}' "
             "and trashed=false")
        if parent:
            q += f" and '{parent}' in parents"
        found = service.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
        if found:
            return found[0]["id"]
        body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent:
            body["parents"] = [parent]
        return service.files().create(body=body, fields="id").execute()["id"]

    parent_id = _find_or_create(_RECEIPT_PARENT)
    receipts_id = _find_or_create(_RECEIPT_FOLDER, parent_id)
    update("user_google_tokens", params={"user_id": f"eq.{user_id}"},
           json={"receipts_folder_id": receipts_id})
    return receipts_id


def _today_iso():
    try:
        return user_today().isoformat()
    except Exception:
        return date.today().isoformat()


def _shape(row):
    return {
        "id": row.get("id"),
        "kind": row.get("kind") or "expense",
        "spent_on": row.get("spent_on"),
        "amount": float(row["amount"]) if row.get("amount") is not None else 0.0,
        "category": row.get("category") or "",
        "note": row.get("note") or "",
        "recurrence": row.get("recurrence") or "none",
        "need_want": row.get("need_want") or "",
        "cost_type": row.get("cost_type") or "",
        "tag": row.get("tag") or "",
        "created_at": row.get("created_at"),
        "receipt_url": row.get("receipt_url") or "",
        "receipt_name": row.get("receipt_name") or "",
    }


# Columns we read back everywhere (kept in one place so list / report /
# print stay in sync).
_SELECT = ("id,kind,spent_on,amount,category,note,recurrence,need_want,"
           "cost_type,tag,created_at,receipt_url,receipt_name")


def _clean_enum(value, allowed):
    """Lower-cased value if it's one of `allowed`, else None."""
    v = (value or "").strip().lower()
    return v if v in allowed else None


def _parse_fields(data):
    """Shared parse/validate for the structured fields on add & edit.
    Returns (payload_fragment, error_or_None)."""
    try:
        amount = round(float(data.get("amount")), 2)
    except (TypeError, ValueError):
        return None, "Enter a valid amount"
    if amount < 0:
        return None, "Amount can't be negative"

    kind = (data.get("kind") or "expense").strip().lower()
    if kind not in ("expense", "income", "transfer"):
        kind = "expense"

    recurrence = _clean_enum(data.get("recurrence"), _RECURRENCE) or "none"

    frag = {
        "kind": kind,
        "spent_on": (data.get("spent_on") or "").strip() or _today_iso(),
        "amount": amount,
        "category": (data.get("category") or "").strip()[:_MAX_CATEGORY] or None,
        "note": (data.get("note") or "").strip()[:_MAX_NOTE] or None,
        "recurrence": recurrence,
        "need_want": _clean_enum(data.get("need_want"), _NEED_WANT),
        "cost_type": _clean_enum(data.get("cost_type"), _COST_TYPE),
        "tag": (data.get("tag") or "").strip()[:_MAX_TAG] or None,
    }
    return frag, None


def _month_bounds(month):
    """('YYYY-MM') → (first_day_iso, first_day_of_next_month_iso). Falls
    back to the current month on bad input."""
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
        if not (1 <= m <= 12):
            raise ValueError
    except Exception:
        t = date.today()
        y, m = t.year, t.month
    start = date(y, m, 1)
    nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return start.isoformat(), nxt.isoformat()


@expenses_bp.route("/expenses", methods=["GET"])
@login_required
def expenses_page():
    return render_template("expenses.html", today=_today_iso())


@expenses_bp.route("/api/expenses", methods=["GET"])
@login_required
def list_expenses():
    """Expenses for a day (default today), newest-first, plus the day's
    total. `?date=YYYY-MM-DD`."""
    user_id = session["user_id"]
    day = (request.args.get("date") or "").strip() or _today_iso()

    try:
        rows = get("expenses", {
            "user_id": f"eq.{user_id}",
            "spent_on": f"eq.{day}",
            "deleted_at": "is.null",
            "select": _SELECT,
            "order": "created_at.desc",
        }) or []
    except Exception as e:
        # Table not created yet (migration pending) — return empty rather
        # than 500 so the page renders cleanly.
        logger.warning("expenses list failed (run MIGRATION_EXPENSES.sql?): %s", e)
        return jsonify({"date": day, "items": [], "spent": 0, "received": 0, "net": 0,
                        "migration_pending": True})

    items = [_shape(r) for r in rows]
    spent = round(sum(i["amount"] for i in items if i["kind"] == "expense"), 2)
    received = round(sum(i["amount"] for i in items if i["kind"] == "income"), 2)
    moved = round(sum(i["amount"] for i in items if i["kind"] == "transfer"), 2)
    return jsonify({
        "date": day, "items": items,
        "spent": spent, "received": received, "moved": moved,
        "net": round(received - spent, 2),
    })


def _label_for(row, dim):
    """Human label for a row under the chosen dissect dimension."""
    col = _DISSECT[dim]
    raw = (row.get(col) or "").strip()
    if not raw:
        return _DISSECT_FALLBACK[dim]
    if dim == "recurrence":
        return "Single" if raw == "none" else raw.capitalize()
    if dim in ("need_want", "cost_type"):
        return raw.capitalize()
    return raw


def _build_report(user_id, month, dim):
    """Compute the monthly report payload, sliced by `dim`. Shared by the
    JSON API and the printable view. Raises on DB error."""
    start, end = _month_bounds(month)
    rows = get("expenses", {
        "user_id": f"eq.{user_id}",
        "and": f"(spent_on.gte.{start},spent_on.lt.{end})",
        "deleted_at": "is.null",
        "select": "kind,amount,category,need_want,cost_type,tag,recurrence",
        "limit": "100000",
    }) or []

    income = expense = transfers = 0.0
    by_dim = {}        # dissect label -> expense total
    inc_by_cat = {}
    proj_monthly = 0.0  # recurring expenses normalised to a monthly figure
    for r in rows:
        amt = float(r["amount"]) if r.get("amount") is not None else 0.0
        k = r.get("kind") or "expense"
        if k == "income":
            income += amt
            cat = (r.get("category") or "Uncategorised").strip() or "Uncategorised"
            inc_by_cat[cat] = round(inc_by_cat.get(cat, 0.0) + amt, 2)
        elif k == "transfer":
            transfers += amt
        else:
            expense += amt
            label = _label_for(r, dim)
            by_dim[label] = round(by_dim.get(label, 0.0) + amt, 2)
            rec = (r.get("recurrence") or "none").strip()
            if rec in _PER_YEAR:
                proj_monthly += amt * _PER_YEAR[rec] / 12.0

    breakdown = sorted(
        ({"label": c, "amount": a} for c, a in by_dim.items()),
        key=lambda x: -x["amount"],
    )
    income_by_category = sorted(
        ({"category": c, "amount": a} for c, a in inc_by_cat.items()),
        key=lambda x: -x["amount"],
    )
    return {
        "month": start[:7],
        "by": dim,
        "income": round(income, 2),
        "expense": round(expense, 2),
        "transfers": round(transfers, 2),
        "net": round(income - expense, 2),
        "breakdown": breakdown,
        # Kept for backward-compat with anything still reading by_category.
        "by_category": [{"category": b["label"], "amount": b["amount"]} for b in breakdown]
                       if dim == "category" else [],
        "income_by_category": income_by_category,
        "projected_monthly": round(proj_monthly, 2),
        "projected_yearly": round(proj_monthly * 12.0, 2),
    }


@expenses_bp.route("/api/expenses/report", methods=["GET"])
@login_required
def report():
    """Monthly report: income / expense totals, net, and a per-dimension
    breakdown of spend. `?month=YYYY-MM` (default current month) and
    `?by=category|need_want|cost_type|tag|recurrence` (default category).
    Also returns projected monthly / yearly totals of recurring spend."""
    user_id = session["user_id"]
    month = (request.args.get("month") or "").strip()
    dim = (request.args.get("by") or "category").strip().lower()
    if dim not in _DISSECT:
        dim = "category"
    try:
        return jsonify(_build_report(user_id, month, dim))
    except Exception as e:
        logger.warning("expenses report failed (run MIGRATION_EXPENSES*.sql?): %s", e)
        start, _ = _month_bounds(month)
        return jsonify({"month": start[:7], "by": dim, "income": 0, "expense": 0,
                        "transfers": 0, "net": 0, "breakdown": [], "by_category": [],
                        "income_by_category": [], "projected_monthly": 0,
                        "projected_yearly": 0, "migration_pending": True})


@expenses_bp.route("/api/expenses/categories", methods=["GET"])
@login_required
def list_categories():
    """The user's previously-used categories and tags, most-used first —
    drives the autocomplete suggestions. Empty lists for a new user."""
    user_id = session["user_id"]
    try:
        rows = get("expenses", {
            "user_id": f"eq.{user_id}",
            "deleted_at": "is.null",
            "select": "category,tag",
            "order": "created_at.desc",
            "limit": "1000",
        }) or []
    except Exception as e:
        logger.warning("expenses categories lookup failed: %s", e)
        return jsonify({"categories": [], "tags": []})

    def _ranked(field):
        counts = Counter(
            (r.get(field) or "").strip()
            for r in rows if (r.get(field) or "").strip()
        )
        # Most-used first, then alphabetical for ties.
        return sorted(counts, key=lambda c: (-counts[c], c.lower()))[:_CATEGORY_SUGGESTIONS]

    return jsonify({"categories": _ranked("category"), "tags": _ranked("tag")})


@expenses_bp.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    frag, err = _parse_fields(data)
    if err:
        return jsonify({"error": err}), 400

    payload = {"user_id": user_id, **frag}
    # Optional receipt (already uploaded to Drive via /api/expenses/receipt).
    rfid = (data.get("receipt_file_id") or "").strip()
    if rfid:
        payload["receipt_file_id"] = rfid
        payload["receipt_url"] = (data.get("receipt_url") or "").strip() or None
        payload["receipt_name"] = (data.get("receipt_name") or "").strip()[:200] or None
    try:
        rows = post("expenses", payload)
    except Exception as e:
        logger.exception("add expense failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again"}), 502

    return jsonify({"item": _shape(rows[0] if rows else payload)})


@expenses_bp.route("/api/expenses/<item_id>", methods=["PUT", "PATCH"])
@login_required
def edit_expense(item_id):
    """Edit an existing entry — amount, kind, date, category, note and the
    structured dissect fields (recurrence / need_want / cost_type / tag).
    Receipt is left untouched here; it's managed by the upload flow."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    frag, err = _parse_fields(data)
    if err:
        return jsonify({"error": err}), 400

    try:
        update(
            "expenses",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
                    "deleted_at": "is.null"},
            json=frag,
        )
    except Exception as e:
        logger.exception("edit expense failed: %s", e)
        return jsonify({"error": "Couldn't save changes — please try again"}), 502

    # Read the row back so the client renders exactly what's stored.
    try:
        rows = get("expenses", {
            "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
            "select": _SELECT, "limit": "1",
        }) or []
    except Exception:
        rows = []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"item": _shape(rows[0])})


@expenses_bp.route("/api/expenses/receipt", methods=["POST"])
@login_required
def upload_receipt():
    """Upload a receipt (image/PDF) to Drive  dailyplanner/receipts .

    If a file with the same name already exists there, returns 409
    {error:'exists'} so the client can ask the user to rename or
    overwrite. Pass overwrite=true (replaces the existing file's content,
    keeping the same id/link) or a new `name` to retry."""
    user_id = session["user_id"]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    mime = (f.mimetype or "application/octet-stream").lower()
    if not (mime.startswith("image/") or mime == "application/pdf"):
        return jsonify({"error": "Receipt must be an image or a PDF."}), 400
    blob = f.stream.read()
    if not blob:
        return jsonify({"error": "Empty file"}), 400
    if len(blob) > _MAX_RECEIPT_BYTES:
        return jsonify({"error": f"Too large (max {_MAX_RECEIPT_BYTES // (1024*1024)} MB)."}), 400

    name = (request.form.get("name") or f.filename or "receipt").strip()[:200]
    overwrite = (request.form.get("overwrite") or "").strip().lower() in ("1", "true", "yes")

    try:
        from routes.chat import _drive_service_for
        service, row = _drive_service_for(user_id)
    except RefreshError:
        return jsonify({"error": "refresh_failed", "connect_url": url_for("events.google_login")}), 401
    if not service:
        return jsonify({"error": "not_connected", "connect_url": url_for("events.google_login")}), 401

    try:
        folder = _ensure_receipts_folder(service, user_id, row)
        safe = name.replace("\\", "\\\\").replace("'", "\\'")
        existing = service.files().list(
            q=f"'{folder}' in parents and name='{safe}' and trashed=false",
            fields="files(id,name)", pageSize=1,
        ).execute().get("files", [])

        media = MediaIoBaseUpload(io.BytesIO(blob), mimetype=mime, resumable=False)
        if existing:
            if not overwrite:
                # Let the client prompt for rename / overwrite.
                return jsonify({"error": "exists", "name": name}), 409
            updated = service.files().update(
                fileId=existing[0]["id"], media_body=media,
                fields="id,name,webViewLink",
            ).execute()
            return jsonify({"file_id": updated["id"], "name": updated.get("name") or name,
                            "web_view": updated.get("webViewLink"), "overwritten": True})

        created = service.files().create(
            body={"name": name, "parents": [folder]}, media_body=media,
            fields="id,name,webViewLink",
        ).execute()
        return jsonify({"file_id": created["id"], "name": created.get("name") or name,
                        "web_view": created.get("webViewLink")})
    except HttpError as e:
        logger.exception("receipt upload failed: %s", e)
        return jsonify({"error": "Drive upload failed."}), 502


@expenses_bp.route("/api/expenses/<item_id>/delete", methods=["POST"])
@login_required
def delete_expense(item_id):
    user_id = session["user_id"]
    from datetime import datetime, timezone
    try:
        update(
            "expenses",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"deleted_at": datetime.now(timezone.utc).isoformat()},
        )
    except Exception as e:
        logger.exception("delete expense failed: %s", e)
        return jsonify({"error": "Couldn't delete"}), 502
    return jsonify({"ok": True})


# Pretty labels for the printable report.
_DIM_TITLES = {
    "category": "Category",
    "need_want": "Need / Want / Saving",
    "cost_type": "Fixed / Variable",
    "tag": "Tag",
    "recurrence": "Recurrence",
}


@expenses_bp.route("/expenses/print", methods=["GET"])
@login_required
def print_report():
    """A clean, print-optimised page for the month — totals, a breakdown
    for every dissect dimension, and the full itemised list. The browser's
    'Save as PDF' turns this into the expenses PDF (no server-side PDF
    library needed). `?month=YYYY-MM`."""
    user_id = session["user_id"]
    month = (request.args.get("month") or "").strip()
    start, end = _month_bounds(month)

    try:
        rows = get("expenses", {
            "user_id": f"eq.{user_id}",
            "and": f"(spent_on.gte.{start},spent_on.lt.{end})",
            "deleted_at": "is.null",
            "select": _SELECT,
            "order": "spent_on.desc,created_at.desc",
        }) or []
    except Exception as e:
        logger.warning("expenses print failed (run MIGRATION_EXPENSES*.sql?): %s", e)
        rows = []

    items = [_shape(r) for r in rows]
    income = round(sum(i["amount"] for i in items if i["kind"] == "income"), 2)
    expense = round(sum(i["amount"] for i in items if i["kind"] == "expense"), 2)
    transfers = round(sum(i["amount"] for i in items if i["kind"] == "transfer"), 2)

    # One breakdown per dissect dimension (expenses only).
    breakdowns = []
    proj_monthly = 0.0
    for r in rows:
        if (r.get("kind") or "expense") != "expense":
            continue
        rec = (r.get("recurrence") or "none").strip()
        if rec in _PER_YEAR:
            amt = float(r["amount"]) if r.get("amount") is not None else 0.0
            proj_monthly += amt * _PER_YEAR[rec] / 12.0
    for dim, title in _DIM_TITLES.items():
        agg = {}
        for r in rows:
            if (r.get("kind") or "expense") != "expense":
                continue
            amt = float(r["amount"]) if r.get("amount") is not None else 0.0
            label = _label_for(r, dim)
            agg[label] = round(agg.get(label, 0.0) + amt, 2)
        rows_sorted = sorted(({"label": k, "amount": v} for k, v in agg.items()),
                             key=lambda x: -x["amount"])
        if rows_sorted:
            breakdowns.append({"title": title, "rows": rows_sorted})

    return render_template(
        "expenses_print.html",
        month=start[:7],
        items=items,
        income=income, expense=expense, transfers=transfers,
        net=round(income - expense, 2),
        breakdowns=breakdowns,
        projected_monthly=round(proj_monthly, 2),
        projected_yearly=round(proj_monthly * 12.0, 2),
        generated_on=_today_iso(),
    )

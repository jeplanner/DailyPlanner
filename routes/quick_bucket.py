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
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from services import quick_bucket_calendar_service as cal_sync
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
quick_bucket_bp = Blueprint("quick_bucket", __name__)

# Buckets in display order. The pill on each row opens a popover that
# shows every option, so the order here is what the user sees in the
# picker — Now first, then minute buckets, then hour buckets, then
# Future.
BUCKETS = [
    "now",
    "5m", "15m", "30m", "45m",
    "1h", "2h", "3h", "4h", "5h", "6h", "7h", "8h",
    "future",
]
BUCKET_SET = set(BUCKETS)

# Map a deadline bucket to its delta. 'now' and 'future' have no
# countdown; everything in between gets a fresh deadline.
_MIN_BUCKETS = {"5m": 5, "15m": 15, "30m": 30, "45m": 45}
_HOUR_BUCKETS = {f"{n}h": n for n in range(1, 9)}

_MAX_TEXT_LEN = 500


def _next_bucket(cur):
    try:
        i = BUCKETS.index(cur or "now")
    except ValueError:
        return BUCKETS[0]
    return BUCKETS[(i + 1) % len(BUCKETS)]


# Deadline mapping. 'now' / 'future' have no countdown — they're either
# already actionable or deferred indefinitely. Picking an "Nh" bucket
# stamps a fresh deadline relative to the moment the user chose it, so
# changing 4h → 8h after 3h gives 8 fresh hours rather than 5 leftover
# ones.
def _due_at_for(bucket):
    now = datetime.now(timezone.utc)
    if bucket in _MIN_BUCKETS:
        return (now + timedelta(minutes=_MIN_BUCKETS[bucket])).isoformat()
    if bucket in _HOUR_BUCKETS:
        return (now + timedelta(hours=_HOUR_BUCKETS[bucket])).isoformat()
    return None


def _fetch_event_id(user_id, item_id):
    """Get the google_event_id for a row, tolerating installs that
    haven't run the latest migration (column missing → return None
    rather than 500-ing the request)."""
    try:
        rows = get(
            "quick_bucket",
            params={
                "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
                "select": "google_event_id", "limit": "1",
            },
        ) or []
    except Exception:
        return None
    return rows[0].get("google_event_id") if rows else None


# ─────────── page ─────────────────────────────────────────────

@quick_bucket_bp.route("/quick-bucket", methods=["GET"])
@login_required
def quick_bucket_page():
    # Cache-bust the JS by appending its mtime to the URL — without
    # this, the 30-day SEND_FILE_MAX_AGE_DEFAULT means deploys don't
    # reach the browser for weeks. New mtime = new URL = fresh fetch.
    import os
    from flask import current_app
    js_v = ""
    try:
        js_path = os.path.join(current_app.static_folder, "js", "quick_bucket.js")
        js_v = str(int(os.path.getmtime(js_path)))
    except Exception:
        pass
    return render_template("quick_bucket.html", buckets=BUCKETS, js_v=js_v)


# ─────────── list ────────────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket", methods=["GET"])
@login_required
def list_items():
    """Return both active AND closed rows so the page can show a 'Done'
    section. Archived (is_deleted) rows still stay hidden — that's the
    soft-delete bucket for items the user removed entirely."""
    user_id = session["user_id"]
    try:
        rows = get(
            "quick_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "select": "id,text,time_bucket,due_at,is_done,done_at,position,created_at,updated_at",
                "order": "is_done.asc,position.asc,created_at.desc",
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

    is_done = bool(data.get("is_done", False))
    payload = {
        "user_id": user_id,
        "text": text,
        "time_bucket": bucket,
        "due_at": _due_at_for(bucket) if not is_done else None,
        "position": int(data.get("position") or 0),
        "is_done": is_done,
        "is_deleted": False,
    }
    if is_done:
        payload["done_at"] = datetime.utcnow().isoformat()
    try:
        rows = post("quick_bucket", payload)
    except Exception as e:
        logger.error("quick_bucket insert failed: %s", e)
        return jsonify({"error": "Couldn't add — please try again."}), 502

    new_row = rows[0] if rows else None
    # Mirror to Google Calendar in the background — only if the user
    # picked a deadline bucket (not 'now' or 'future').
    if new_row and new_row.get("due_at"):
        cal_sync.sync_async(user_id, new_row["id"], new_row)

    return jsonify({"ok": True, "item": new_row})


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

    cur = rows[0]
    nxt = _next_bucket(cur.get("time_bucket"))
    nxt_due = _due_at_for(nxt)
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"time_bucket": nxt, "due_at": nxt_due},
        )
    except Exception as e:
        logger.error("quick_bucket cycle failed: %s", e)
        return jsonify({"error": "Couldn't change — please try again."}), 502

    # Calendar mirror: delete if we moved to now/future (no deadline);
    # otherwise sync the fresh due_at to the existing event (or create one).
    old_event_id = _fetch_event_id(user_id, item_id)
    item_after = {**cur, "time_bucket": nxt, "due_at": nxt_due, "google_event_id": old_event_id}
    cal_sync.sync_async(
        user_id, item_id, item_after,
        old_event_id=old_event_id,
        force_delete=(nxt_due is None and bool(old_event_id)),
    )
    return jsonify({"ok": True, "time_bucket": nxt, "due_at": nxt_due})


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
        patch["due_at"] = _due_at_for(v)
    if "position" in data:
        try:
            patch["position"] = int(data["position"])
        except (TypeError, ValueError):
            pass

    if not patch:
        return jsonify({"ok": True, "noop": True})

    # Pull the row (sans google_event_id, which may not exist yet on
    # installs that haven't run the latest migration).
    cur_rows = get(
        "quick_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,text,time_bucket,due_at,is_done,is_deleted",
            "limit": "1",
        },
    ) or []
    cur = cur_rows[0] if cur_rows else {}

    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("quick_bucket update failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502

    # If the time_bucket changed, sync (or delete) the calendar mirror.
    if "time_bucket" in patch and cur:
        old_event_id = _fetch_event_id(user_id, item_id)
        item_after = {**cur, **patch, "google_event_id": old_event_id}
        cal_sync.sync_async(
            user_id, item_id, item_after,
            old_event_id=old_event_id,
            force_delete=(patch.get("due_at") is None and bool(old_event_id)),
        )

    return jsonify({"ok": True, "patch": patch})


# ─────────── mark done ───────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/done", methods=["POST"])
@login_required
def mark_done(item_id):
    user_id = session["user_id"]
    old_event_id = _fetch_event_id(user_id, item_id)
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_done": True, "done_at": datetime.utcnow().isoformat()},
        )
    except Exception as e:
        logger.error("quick_bucket done failed: %s", e)
        return jsonify({"error": "Couldn't update — please try again."}), 502

    if old_event_id:
        cal_sync.sync_async(user_id, item_id, {}, old_event_id=old_event_id, force_delete=True)
    return jsonify({"ok": True})


@quick_bucket_bp.route("/api/quick-bucket/<item_id>/reopen", methods=["POST"])
@login_required
def reopen(item_id):
    """Bring a Done row back to active so the user can keep working on it."""
    user_id = session["user_id"]
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_done": False, "done_at": None},
        )
    except Exception as e:
        logger.error("quick_bucket reopen failed: %s", e)
        return jsonify({"error": "Couldn't reopen — please try again."}), 502

    # Re-create the calendar event if the row still has an active
    # deadline (i.e. it sat in a 5m..8h bucket when it was closed).
    cur_rows = get(
        "quick_bucket",
        params={
            "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
            "select": "id,text,time_bucket,due_at",
            "limit": "1",
        },
    ) or []
    if cur_rows and cur_rows[0].get("due_at"):
        cal_sync.sync_async(user_id, item_id, cur_rows[0])

    return jsonify({"ok": True})


# ─────────── route into a destination module ────────────────────
#
# When the user picks a category in the "Move to…" dialog, the form
# fields are POSTed here. We delegate to tasks_bucket._create_destination_row
# (already written, with per-category validation) so the schema-specific
# logic lives in one place. On success the quick-bucket row is archived
# — it has been "moved out" — and the destination row owns it from now
# on.

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/route", methods=["POST"])
@login_required
def route_item(item_id):
    from routes.tasks_bucket import _create_destination_row, ROUTABLE, CATEGORIES
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    cat = (data.get("category") or "").strip()
    fields = data.get("fields") or {}

    if cat not in CATEGORIES:
        return jsonify({"error": "Pick a category"}), 400
    if cat not in ROUTABLE:
        return jsonify({"error": "This category isn't routable yet."}), 400

    rows = get(
        "quick_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "id,text",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    item = rows[0]
    old_event_id = _fetch_event_id(user_id, item_id)

    dest_table, dest_id_or_msg = _create_destination_row(
        user_id, cat, item.get("text") or "", fields
    )
    if not dest_table:
        return jsonify({"error": dest_id_or_msg or "Couldn't move."}), 502

    # Archive the bucket row — it has lived its purpose.
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_deleted": True},
        )
    except Exception:
        logger.exception("quick_bucket route: post-archive failed")
        return jsonify({
            "ok": True,
            "warning": "Created in module but couldn't archive bucket row — refresh.",
            "destination_table": dest_table,
            "destination_id": dest_id_or_msg,
        })

    # Drop the calendar mirror — the destination module owns the
    # reminder now (checklist has its own calendar sync; the rest
    # don't push to calendar at all).
    if old_event_id:
        cal_sync.sync_async(user_id, item_id, {}, old_event_id=old_event_id, force_delete=True)

    return jsonify({
        "ok": True,
        "destination_table": dest_table,
        "destination_id": dest_id_or_msg,
    })


# ─────────── archive (soft-delete) ───────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/<item_id>/archive", methods=["POST"])
@login_required
def archive_item(item_id):
    """Soft-delete: hide the row but keep it in storage. No hard delete
    — see project convention (memory: no-hard-delete)."""
    user_id = session["user_id"]
    old_event_id = _fetch_event_id(user_id, item_id)
    try:
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_deleted": True},
        )
    except Exception as e:
        logger.error("quick_bucket archive failed: %s", e)
        return jsonify({"error": "Couldn't remove — please try again."}), 502

    if old_event_id:
        cal_sync.sync_async(user_id, item_id, {}, old_event_id=old_event_id, force_delete=True)
    return jsonify({"ok": True})

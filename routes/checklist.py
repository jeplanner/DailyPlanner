"""
Daily Checklist — recurring items the user wants to be reminded about
each day (take meds, stretch, drink water, etc). Each item can have an
optional reminder_time; if set, the push scheduler fires a Web Push
notification at that local time on the matching schedule.

Distinct from `habits`: habits track quantity/streak; checklists just
need to be ticked off for the day.
"""
import logging
import threading
from datetime import date, datetime
from datetime import time as dtime

from flask import Blueprint, jsonify, render_template, request, session
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

from auth import login_required
from services import checklist_calendar_service as cal_sync
from supabase_client import delete as sb_delete
from supabase_client import get, post, update
from utils.user_tz import user_today

checklist_bp = Blueprint("checklist", __name__)


VALID_SCHEDULES = {"daily", "weekdays", "weekends", "custom"}
VALID_TIMES_OF_DAY = {"morning", "afternoon", "evening", "anytime"}


def _parse_reminder_time(value):
    """Accept 'HH:MM' or 'HH:MM:SS' or empty string/None. Returns a
    Postgres-friendly string or None."""
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    parts = value.split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError(f"Invalid time: {value}")
    hh = int(parts[0])
    mm = int(parts[1])
    ss = int(parts[2]) if len(parts) == 3 else 0
    # Construct dtime to validate ranges, then format.
    return dtime(hh, mm, ss).isoformat()


def _parse_end_date(value):
    """Accept 'YYYY-MM-DD' or empty. Returns ISO string or None."""
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    # Validate by round-tripping through date.fromisoformat.
    return date.fromisoformat(value).isoformat()


def _serialize(item, tick_map):
    return {
        "id": item["id"],
        "name": item["name"],
        "notes": item.get("notes") or "",
        "schedule": item.get("schedule") or "daily",
        "schedule_days": item.get("schedule_days") or "",
        "time_of_day": item.get("time_of_day") or "anytime",
        "reminder_time": (item.get("reminder_time") or "")[:5],  # HH:MM
        "recurrence_end": item.get("recurrence_end") or "",
        "position": item.get("position") or 9999,
        "ticked": tick_map.get(item["id"], False),
    }


def _sync_calendar_async(user_id, item_id, item_row, old_event_id=None, force_delete=False):
    """Run Calendar sync in a background thread so the HTTP request
    returns immediately. The checklist row is written to Supabase first
    (source of truth); Calendar is a downstream mirror.

    force_delete=True unconditionally removes old_event_id (used when
    the reminder is cleared or the item is deleted)."""
    def _work():
        try:
            if force_delete and old_event_id:
                cal_sync.delete_from_calendar(user_id, old_event_id)
                update(
                    "checklist_items",
                    params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                    json={"google_event_id": None},
                )
                return
            if not item_row.get("reminder_time"):
                return  # nothing to mirror
            new_id = cal_sync.sync_to_calendar(user_id, item_row)
            if new_id and new_id != old_event_id:
                update(
                    "checklist_items",
                    params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                    json={"google_event_id": new_id},
                )
        except Exception:
            logger.exception("Background calendar sync failed for %s", item_id)

    t = threading.Thread(target=_work, name=f"cal-sync-{item_id}", daemon=True)
    t.start()


# ─────────────────────────────────────────────
#  PAGE
# ─────────────────────────────────────────────
@checklist_bp.route("/checklist")
@login_required
def checklist_page():
    return render_template("checklist.html", plan_date=user_today().isoformat())


# ─────────────────────────────────────────────
#  LIST
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/items", methods=["GET"])
@login_required
def list_items():
    user_id = session["user_id"]
    today = user_today().isoformat()

    items = get(
        "checklist_items",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "order": "position.asc,created_at.asc",
        },
    ) or []

    ticks = get(
        "checklist_ticks",
        {
            "user_id": f"eq.{user_id}",
            "tick_date": f"eq.{today}",
        },
    ) or []
    tick_map = {t["item_id"]: True for t in ticks}

    return jsonify({
        "items": [_serialize(i, tick_map) for i in items],
        "date": today,
    })


# ─────────────────────────────────────────────
#  CREATE
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/items", methods=["POST"])
@login_required
def create_item():
    user_id = session["user_id"]
    data = request.get_json() or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    schedule = (data.get("schedule") or "daily").strip()
    if schedule not in VALID_SCHEDULES:
        return jsonify({"error": f"Invalid schedule: {schedule}"}), 400

    time_of_day = (data.get("time_of_day") or "anytime").strip()
    if time_of_day not in VALID_TIMES_OF_DAY:
        return jsonify({"error": f"Invalid time_of_day: {time_of_day}"}), 400

    try:
        reminder_time = _parse_reminder_time(data.get("reminder_time"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    try:
        recurrence_end = _parse_end_date(data.get("recurrence_end"))
    except ValueError:
        return jsonify({"error": "Invalid end date"}), 400

    schedule_days = (data.get("schedule_days") or "").strip()

    try:
        inserted = post(
            "checklist_items",
            {
                "user_id": user_id,
                "name": name,
                "notes": (data.get("notes") or "").strip() or None,
                "schedule": schedule,
                "schedule_days": schedule_days or None,
                "time_of_day": time_of_day,
                "reminder_time": reminder_time,
                "recurrence_end": recurrence_end,
                "position": int(data.get("position") or 9999),
                "is_deleted": False,
            },
            prefer="return=representation",
        )
    except HTTPError as e:
        return jsonify({"error": f"Database error: {e}"}), 500

    row = inserted[0]

    # Kick off calendar mirroring in a background thread so the
    # browser gets its response in ~100ms instead of ~1s. Supabase is
    # the source of truth; Calendar is best-effort.
    if reminder_time:
        _sync_calendar_async(user_id, row["id"], row)

    return jsonify(_serialize(row, {}))


# ─────────────────────────────────────────────
#  UPDATE
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/items/<item_id>", methods=["PATCH"])
@login_required
def update_item(item_id):
    user_id = session["user_id"]
    data = request.get_json() or {}

    existing = get(
        "checklist_items",
        {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}", "is_deleted": "eq.false"},
    )
    if not existing:
        return jsonify({"error": "Item not found"}), 404

    patch = {}
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        patch["name"] = name
    if "notes" in data:
        patch["notes"] = (data["notes"] or "").strip() or None
    if "schedule" in data:
        if data["schedule"] not in VALID_SCHEDULES:
            return jsonify({"error": "Invalid schedule"}), 400
        patch["schedule"] = data["schedule"]
    if "schedule_days" in data:
        patch["schedule_days"] = (data["schedule_days"] or "").strip() or None
    if "time_of_day" in data:
        if data["time_of_day"] not in VALID_TIMES_OF_DAY:
            return jsonify({"error": "Invalid time_of_day"}), 400
        patch["time_of_day"] = data["time_of_day"]
    if "reminder_time" in data:
        try:
            patch["reminder_time"] = _parse_reminder_time(data["reminder_time"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    if "recurrence_end" in data:
        try:
            patch["recurrence_end"] = _parse_end_date(data["recurrence_end"])
        except ValueError:
            return jsonify({"error": "Invalid end date"}), 400
    if "position" in data:
        patch["position"] = int(data["position"])

    if not patch:
        return jsonify({"error": "Nothing to update"}), 400

    update(
        "checklist_items",
        params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
        json=patch,
    )

    # Re-fetch so we hand the calendar helper the fully-merged item.
    fresh_rows = get(
        "checklist_items",
        {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
    ) or []
    if fresh_rows:
        fresh = fresh_rows[0]
        old_event_id = existing[0].get("google_event_id")
        if fresh.get("reminder_time"):
            _sync_calendar_async(user_id, item_id, fresh, old_event_id=old_event_id)
        elif old_event_id:
            _sync_calendar_async(user_id, item_id, fresh,
                                 old_event_id=old_event_id, force_delete=True)

    return jsonify({"success": True})


# ─────────────────────────────────────────────
#  SOFT DELETE
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/items/<item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id):
    user_id = session["user_id"]

    existing = get(
        "checklist_items",
        {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
    ) or []
    old_event_id = existing[0].get("google_event_id") if existing else None

    update(
        "checklist_items",
        params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True, "google_event_id": None},
    )

    if old_event_id:
        # Fire-and-forget: Calendar cleanup shouldn't block the UI.
        def _cleanup():
            try:
                cal_sync.delete_from_calendar(user_id, old_event_id)
            except Exception:
                logger.exception("Background calendar delete failed")
        threading.Thread(target=_cleanup, daemon=True).start()

    return jsonify({"success": True})


# ─────────────────────────────────────────────
#  TICK / UNTICK
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/items/<item_id>/tick", methods=["POST"])
@login_required
def tick_item(item_id):
    user_id = session["user_id"]
    today = user_today().isoformat()

    # Ownership check — cheap, and guards against ticking someone else's id.
    owner = get(
        "checklist_items",
        {"id": f"eq.{item_id}", "user_id": f"eq.{user_id}", "is_deleted": "eq.false"},
    )
    if not owner:
        return jsonify({"error": "Item not found"}), 404

    try:
        post(
            "checklist_ticks",
            {"user_id": user_id, "item_id": item_id, "tick_date": today},
            prefer="return=minimal",
        )
    except HTTPError as e:
        # Unique (item_id, tick_date) — already ticked today is fine.
        if e.response is not None and e.response.status_code == 409:
            return jsonify({"success": True, "already": True})
        raise

    return jsonify({"success": True})


@checklist_bp.route("/api/checklist/items/<item_id>/untick", methods=["POST"])
@login_required
def untick_item(item_id):
    user_id = session["user_id"]
    today = user_today().isoformat()

    sb_delete(
        "checklist_ticks",
        {
            "user_id": f"eq.{user_id}",
            "item_id": f"eq.{item_id}",
            "tick_date": f"eq.{today}",
        },
    )
    return jsonify({"success": True})


# ─────────────────────────────────────────────
#  REORDER
# ─────────────────────────────────────────────
@checklist_bp.route("/api/checklist/sync-calendar", methods=["POST"])
@login_required
def sync_calendar():
    """Backfill: create Google Calendar events for every existing
    checklist item that has a reminder_time but no google_event_id yet.
    Safe to run multiple times — already-synced items are skipped."""
    user_id = session["user_id"]

    items = get(
        "checklist_items",
        {
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "reminder_time": "not.is.null",
            "google_event_id": "is.null",
        },
    ) or []

    synced = 0
    skipped = 0
    failed = 0
    for it in items:
        try:
            new_id = cal_sync.sync_to_calendar(user_id, it)
        except Exception:
            failed += 1
            continue
        if new_id:
            update(
                "checklist_items",
                params={"id": f"eq.{it['id']}", "user_id": f"eq.{user_id}"},
                json={"google_event_id": new_id},
            )
            synced += 1
        else:
            skipped += 1

    return jsonify({
        "success": True,
        "synced": synced,
        "skipped": skipped,
        "failed": failed,
        "total_candidates": len(items),
    })


@checklist_bp.route("/api/checklist/reorder", methods=["POST"])
@login_required
def reorder_items():
    user_id = session["user_id"]
    data = request.get_json() or {}
    order = data.get("order") or []

    for pos, item_id in enumerate(order):
        update(
            "checklist_items",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"position": pos},
        )
    return jsonify({"success": True})

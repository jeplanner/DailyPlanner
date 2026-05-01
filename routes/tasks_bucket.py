"""Tasks Bucket — frictionless inbox that auto-classifies into modules.

The user dictates or types a one-liner; after a short idle window the
client calls /classify, which runs the in-app Naive Bayes model
(`services.task_classifier`). For Grocery and Checklist (simple
schemas) the row is also routed into the destination module so the
user can act on it from there. Health, Portfolio, and TravelReads stay
in the bucket only — their schemas need details the user should fill
in by hand.

Endpoints (JSON; CSRF exempt — session auth is enforced via
@login_required):
    GET  /tasks-bucket                          page render
    GET  /api/tasks-bucket                      list active items
    POST /api/tasks-bucket                      add raw line
    POST /api/tasks-bucket/<id>/classify        run classifier
    POST /api/tasks-bucket/<id>/reclassify      manual category (and learn)
    POST /api/tasks-bucket/<id>/close           mark done
    POST /api/tasks-bucket/<id>/archive         soft-delete
    POST /api/tasks-bucket/reorder              drag-drop position update
    POST /api/tasks-bucket/sweep-closed         hide rows whose dest closed
    GET  /api/tasks-bucket/stats                gamification daily stats
"""

import logging
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from services.task_classifier import CATEGORIES, classify, learn
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
tasks_bucket_bp = Blueprint("tasks_bucket", __name__)

_MAX_TEXT_LEN = 500

# Effort options surfaced in the UI as a cycle: 5m → 15m → 30m → 1h →
# 2h → 3h → 4h → cleared. Stored as minutes so the value is sortable
# and survives label changes later.
VALID_EFFORTS = {5, 15, 30, 60, 120, 180, 240}


# ─────────── stat helper ───────────────────────────────────────

def _bump_stat(user_id, field, by=1):
    """Increment a daily counter for the gamification strip. Best-effort —
    a stat write failing should never break the user's action."""
    today = date.today().isoformat()
    try:
        rows = get(
            "tasks_bucket_stats",
            params={
                "user_id": f"eq.{user_id}",
                "stat_date": f"eq.{today}",
                "select": "id,captured,classified,closed",
                "limit": "1",
            },
        ) or []
    except Exception:
        logger.exception("stat fetch failed")
        return

    if rows:
        row = rows[0]
        new_val = int(row.get(field) or 0) + by
        try:
            update(
                "tasks_bucket_stats",
                params={"id": f"eq.{row['id']}", "user_id": f"eq.{user_id}"},
                json={field: new_val},
            )
        except Exception:
            logger.exception("stat update failed")
    else:
        payload = {
            "user_id": user_id,
            "stat_date": today,
            "captured": 0,
            "classified": 0,
            "closed": 0,
            field: by,
        }
        try:
            post("tasks_bucket_stats", payload)
        except Exception:
            logger.exception("stat insert failed")


# ─────────── routing into destination modules ─────────────────
#
# Two-step flow:
#   1. classify_item only sets the category — never auto-creates a
#      destination row. The user keeps control of what actually moves.
#   2. /route is called from the detail modal once the user has filled
#      in the destination-specific fields (quantity, schedule, URL, …)
#      and wants to commit. It builds the destination row with those
#      values and back-links destination_table/destination_id so the
#      bucket row mirrors the destination's status.
#
# Routable categories: Grocery, Checklist, TravelReads, ProjectTask
# (the last reuses checklist_items with group_name='Project Tasks').
# Health and Portfolio are intentionally not routable: their schemas
# need details (habit cadence, ticker, encrypted folio, …) that don't
# fit a quick-capture flow. Those rows stay in the bucket and the
# user closes them from there once handled.

VALID_GROCERY_CATEGORIES = {
    "produce", "dairy", "staples", "snacks", "household", "spices",
    "frozen", "beverages", "meat", "bakery", "other",
}
VALID_GROCERY_PRIORITIES = {"low", "medium", "high"}
VALID_CHECKLIST_SCHEDULES = {"daily", "weekdays", "weekends", "custom"}
VALID_CHECKLIST_TIMES = {"morning", "afternoon", "evening", "anytime"}
VALID_TR_KINDS = {"article", "video", "book", "podcast", "newsletter", "documentary", "other"}
VALID_TR_PRIORITIES = {"low", "medium", "high"}
ROUTABLE = {"Grocery", "Checklist", "TravelReads", "ProjectTask"}


def _create_destination_row(user_id, category, raw_text, fields):
    """Build the destination row from user-supplied form fields.
    Returns (table, dest_id) on success, (None, reason) on skip/failure."""
    text = (raw_text or "").strip()
    fields = fields or {}

    if category == "Grocery":
        item = (fields.get("item") or text or "").strip()[:120]
        if not item:
            return None, "Item name is required"
        cat = (fields.get("category") or "other").strip().lower()
        if cat not in VALID_GROCERY_CATEGORIES:
            cat = "other"
        prio = (fields.get("priority") or "medium").strip().lower()
        if prio not in VALID_GROCERY_PRIORITIES:
            prio = "medium"
        payload = {
            "user_id": user_id,
            "item": item,
            "quantity": ((fields.get("quantity") or "").strip() or None) and (fields.get("quantity") or "").strip()[:40],
            "category": cat,
            "notes": ((fields.get("notes") or "").strip() or None) and (fields.get("notes") or "").strip()[:400],
            "priority": prio,
            "is_purchased": False,
            "is_archived": False,
        }
        try:
            rows = post("groceries", payload)
            if rows:
                return "groceries", rows[0].get("id")
        except Exception:
            logger.exception("route: grocery insert failed")
        return None, "Couldn't create grocery item"

    if category in ("Checklist", "ProjectTask"):
        name = (fields.get("name") or text or "").strip()[:200]
        if not name:
            return None, "Name is required"
        sched = (fields.get("schedule") or "daily").strip().lower()
        if sched not in VALID_CHECKLIST_SCHEDULES:
            sched = "daily"
        tod = (fields.get("time_of_day") or "anytime").strip().lower()
        if tod not in VALID_CHECKLIST_TIMES:
            tod = "anytime"
        payload = {
            "user_id": user_id,
            "name": name,
            "schedule": sched,
            "time_of_day": tod,
        }
        # Reminder time: 'HH:MM' or 'HH:MM:SS'
        rt = (fields.get("reminder_time") or "").strip()
        if rt:
            payload["reminder_time"] = rt
        # Group name: defaults to "Project Tasks" for ProjectTask category
        group = (fields.get("group_name") or "").strip()
        if not group and category == "ProjectTask":
            group = "Project Tasks"
        if group:
            payload["group_name"] = " ".join(group.split()).title()
        re_end = (fields.get("recurrence_end") or "").strip()
        if re_end:
            payload["recurrence_end"] = re_end
        notes = (fields.get("notes") or "").strip()
        if notes:
            payload["notes"] = notes[:400]
        try:
            rows = post("checklist_items", payload)
            if rows:
                return "checklist_items", rows[0].get("id")
        except Exception:
            logger.exception("route: checklist insert failed")
        return None, "Couldn't create checklist item"

    if category == "TravelReads":
        title = (fields.get("title") or text or "").strip()[:200]
        if not title:
            return None, "Title is required"
        kind = (fields.get("kind") or "article").strip().lower()
        if kind not in VALID_TR_KINDS:
            kind = "article"
        prio = (fields.get("priority") or "medium").strip().lower()
        if prio not in VALID_TR_PRIORITIES:
            prio = "medium"
        payload = {
            "user_id": user_id,
            "title": title,
            "url": (fields.get("url") or "").strip() or None,
            "kind": kind,
            "priority": prio,
            "notes": (fields.get("notes") or "").strip() or None,
            "status": "queued",
        }
        try:
            rows = post("travel_reads", payload)
            if rows:
                return "travel_reads", rows[0].get("id")
        except Exception:
            logger.exception("route: travel_reads insert failed")
        return None, "Couldn't create reading-list item"

    # Health, Portfolio — not routable (schema mismatch with quick capture).
    return None, "This category stays in the bucket — handle from here."


# ─────────── page ─────────────────────────────────────────────

@tasks_bucket_bp.route("/tasks-bucket", methods=["GET"])
@login_required
def tasks_bucket_page():
    return render_template("tasks_bucket.html", categories=CATEGORIES)


# ─────────── list active items ────────────────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket", methods=["GET"])
@login_required
def list_items():
    user_id = session["user_id"]
    try:
        rows = get(
            "tasks_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "status": "in.(pending,classified,unclassified)",
                "select": (
                    "id,raw_text,category,confidence,matched_keywords,"
                    "status,manual_override,destination_table,destination_id,"
                    "position,is_priority,effort_minutes,"
                    "classified_at,created_at,updated_at"
                ),
                # Priority items always float to the top; within a
                # priority bucket, manual position wins over recency.
                "order": "is_priority.desc.nullslast,position.asc,created_at.desc",
                "limit": "500",
            },
        ) or []
    except Exception:
        logger.exception("tasks_bucket list failed")
        return jsonify({"items": [], "categories": CATEGORIES, "error": "Could not load list"}), 200
    return jsonify({"items": rows, "categories": CATEGORIES})


# ─────────── create ───────────────────────────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket", methods=["POST"])
@login_required
def add_item():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    text = (data.get("raw_text") or "").strip()
    if not text:
        return jsonify({"error": "Text required"}), 400
    text = text[:_MAX_TEXT_LEN]

    payload = {
        "user_id": user_id,
        "raw_text": text,
        "status": "pending",
        "position": int(data.get("position") or 0),
        "is_priority": bool(data.get("is_priority") or False),
    }
    eff = data.get("effort_minutes")
    if eff is not None:
        try:
            eff_int = int(eff)
            if eff_int in VALID_EFFORTS:
                payload["effort_minutes"] = eff_int
        except (TypeError, ValueError):
            pass
    try:
        rows = post("tasks_bucket", payload)
    except Exception as e:
        logger.error("tasks_bucket insert failed: %s", e)
        return jsonify({"error": "Couldn't add — please try again."}), 502

    _bump_stat(user_id, "captured", 1)
    return jsonify({"ok": True, "item": rows[0] if rows else None})


# ─────────── classify (auto) ──────────────────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/classify", methods=["POST"])
@login_required
def classify_item(item_id):
    user_id = session["user_id"]
    rows = get(
        "tasks_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,raw_text,status,manual_override",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    item = rows[0]

    # Manual override means the user has already labelled this — don't
    # let the auto-classifier silently overwrite their decision.
    if item.get("manual_override"):
        return jsonify({"ok": True, "skipped": "manual_override"})

    cat, conf, matched = classify(user_id, item.get("raw_text") or "")
    patch = {
        "category": cat,
        "confidence": conf,
        "matched_keywords": matched,
        "status": "classified" if cat else "unclassified",
        "classified_at": datetime.utcnow().isoformat(),
    }

    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("tasks_bucket classify-update failed: %s", e)
        return jsonify({"error": "Couldn't classify — please try again."}), 502

    if cat:
        _bump_stat(user_id, "classified", 1)
    return jsonify({
        "ok": True,
        "category": cat,
        "confidence": conf,
        "matched": matched,
    })


# ─────────── reclassify (manual; teaches the model) ───────────

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/reclassify", methods=["POST"])
@login_required
def reclassify_item(item_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    cat = data.get("category")
    if cat not in CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400

    rows = get(
        "tasks_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,raw_text,category,destination_table,destination_id,status",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    item = rows[0]

    was_classified = bool(item.get("category"))

    # Teach the classifier: append this labelled example to the corpus.
    learn(user_id, item.get("raw_text") or "", cat)

    patch = {
        "category": cat,
        "manual_override": True,
        "status": "classified",
        "classified_at": datetime.utcnow().isoformat(),
    }

    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("tasks_bucket reclassify failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502

    if not was_classified:
        _bump_stat(user_id, "classified", 1)
    return jsonify({"ok": True, "category": cat})


# ─────────── route into destination module ────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/route", methods=["POST"])
@login_required
def route_item(item_id):
    """Create a row in the destination module from user-supplied form
    fields. Called when the user clicks "Save & move" in the detail
    modal. Idempotent: if the bucket row is already linked to a
    destination, returns the existing link without creating a duplicate.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    fields = data.get("fields") or {}
    cat_override = data.get("category")

    rows = get(
        "tasks_bucket",
        params={
            "id": f"eq.{item_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,raw_text,category,destination_table,destination_id,status",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    item = rows[0]

    if item.get("destination_id"):
        return jsonify({
            "ok": True,
            "already_routed": True,
            "destination_table": item.get("destination_table"),
            "destination_id": item.get("destination_id"),
        })

    cat = cat_override or item.get("category")
    if cat not in CATEGORIES:
        return jsonify({"error": "Pick a category first"}), 400
    if cat not in ROUTABLE:
        return jsonify({"error": "This category stays in the bucket — Health and Portfolio entries aren't auto-moved."}), 400

    dest_table, dest_id_or_msg = _create_destination_row(
        user_id, cat, item.get("raw_text") or "", fields
    )
    if not dest_table:
        return jsonify({"error": dest_id_or_msg or "Couldn't move — please try again."}), 502

    patch = {
        "destination_table": dest_table,
        "destination_id": dest_id_or_msg,
        "category": cat,
        "status": "classified",
    }
    if cat_override:
        patch["manual_override"] = True
    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception:
        logger.exception("route_item: link update failed")
        return jsonify({
            "ok": True,
            "warning": "Created in module but couldn't update bucket — refresh the page.",
            "destination_table": dest_table,
            "destination_id": dest_id_or_msg,
        })

    return jsonify({
        "ok": True,
        "destination_table": dest_table,
        "destination_id": dest_id_or_msg,
    })


# ─────────── close ────────────────────────────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/close", methods=["POST"])
@login_required
def close_item(item_id):
    user_id = session["user_id"]
    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"status": "closed", "closed_at": datetime.utcnow().isoformat()},
        )
    except Exception as e:
        logger.error("close failed: %s", e)
        return jsonify({"error": "Couldn't close — please try again."}), 502
    _bump_stat(user_id, "closed", 1)
    return jsonify({"ok": True})


# ─────────── archive (soft-delete) ────────────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/archive", methods=["POST"])
@login_required
def archive_item(item_id):
    """Soft-delete: hide the row from the list but keep it in storage.
    No hard delete — see project convention (memory: no-hard-delete)."""
    user_id = session["user_id"]
    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"is_deleted": True},
        )
    except Exception as e:
        logger.error("archive failed: %s", e)
        return jsonify({"error": "Couldn't remove — please try again."}), 502
    return jsonify({"ok": True})


# ─────────── update inline fields (priority toggle, effort cycle) ──

@tasks_bucket_bp.route("/api/tasks-bucket/<item_id>/update", methods=["POST"])
@login_required
def update_item(item_id):
    """Patch a small set of inline fields on a bucket row. The UI uses
    this for the priority toggle and the effort cycle button without
    having to open the full detail modal."""
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    patch = {}
    if "is_priority" in data:
        patch["is_priority"] = bool(data.get("is_priority"))
    if "effort_minutes" in data:
        v = data.get("effort_minutes")
        if v in (None, "", "null"):
            patch["effort_minutes"] = None
        else:
            try:
                v_int = int(v)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid effort value"}), 400
            if v_int not in VALID_EFFORTS:
                return jsonify({"error": "Effort must be 5/15/30/60/120/180/240"}), 400
            patch["effort_minutes"] = v_int
    if "raw_text" in data:
        v = (data.get("raw_text") or "").strip()
        if not v:
            return jsonify({"error": "Text required"}), 400
        patch["raw_text"] = v[:_MAX_TEXT_LEN]
    if "position" in data:
        try:
            patch["position"] = int(data["position"])
        except (TypeError, ValueError):
            pass

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update(
            "tasks_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("tasks_bucket update failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502
    return jsonify({"ok": True, "patch": patch})


# ─────────── reorder / drag-drop between categories ───────────

@tasks_bucket_bp.route("/api/tasks-bucket/reorder", methods=["POST"])
@login_required
def reorder():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    items = data.get("items") or []  # [{id, position, category?}]
    moved_categories = 0
    for idx, it in enumerate(items):
        item_id = it.get("id")
        if not item_id:
            continue
        patch = {"position": int(it.get("position", idx))}
        new_cat = it.get("category")
        if new_cat in CATEGORIES:
            patch["category"] = new_cat
            patch["manual_override"] = True
            patch["status"] = "classified"
            moved_categories += 1
        try:
            update(
                "tasks_bucket",
                params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                json=patch,
            )
        except Exception:
            logger.exception("reorder failed for %s", item_id)
    return jsonify({"ok": True, "reclassified": moved_categories})


# ─────────── sweep: hide rows whose destination closed elsewhere ──

@tasks_bucket_bp.route("/api/tasks-bucket/sweep-closed", methods=["POST"])
@login_required
def sweep_closed():
    """Mark bucket rows as closed when the linked destination row has
    been completed/archived in its own module. Cheap to run on every
    page load so the bucket stays free of stale items."""
    user_id = session["user_id"]
    try:
        rows = get(
            "tasks_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "status": "in.(pending,classified,unclassified)",
                "destination_table": "not.is.null",
                "select": "id,destination_table,destination_id",
                "limit": "500",
            },
        ) or []
    except Exception:
        logger.exception("sweep: list failed")
        return jsonify({"ok": True, "swept": 0})

    swept = 0
    for r in rows:
        table = r.get("destination_table")
        dest_id = r.get("destination_id")
        if not (table and dest_id):
            continue
        try:
            done = False
            if table == "groceries":
                d = get(
                    "groceries",
                    params={
                        "id": f"eq.{dest_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "is_purchased,is_archived",
                        "limit": "1",
                    },
                ) or []
                done = bool(d and (d[0].get("is_purchased") or d[0].get("is_archived")))
            elif table == "checklist_items":
                d = get(
                    "checklist_items",
                    params={
                        "id": f"eq.{dest_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "is_deleted",
                        "limit": "1",
                    },
                ) or []
                done = bool(d and d[0].get("is_deleted"))
            if done:
                update(
                    "tasks_bucket",
                    params={"id": f"eq.{r['id']}", "user_id": f"eq.{user_id}"},
                    json={"status": "closed", "closed_at": datetime.utcnow().isoformat()},
                )
                _bump_stat(user_id, "closed", 1)
                swept += 1
        except Exception:
            logger.exception("sweep failed for %s", r.get("id"))
    return jsonify({"ok": True, "swept": swept})


# ─────────── stats (gamification strip) ───────────────────────

@tasks_bucket_bp.route("/api/tasks-bucket/stats", methods=["GET"])
@login_required
def stats():
    user_id = session["user_id"]
    try:
        rows = get(
            "tasks_bucket_stats",
            params={
                "user_id": f"eq.{user_id}",
                "select": "stat_date,captured,classified,closed",
                "order": "stat_date.desc",
                "limit": "60",
            },
        ) or []
    except Exception:
        logger.exception("stats fetch failed")
        rows = []

    by_date = {r["stat_date"]: r for r in rows}
    today_iso = date.today().isoformat()
    today_stats = by_date.get(today_iso) or {"captured": 0, "classified": 0, "closed": 0}

    # Streak counts consecutive days ending yesterday with at least one
    # closed item, plus today if the user has already closed something.
    streak = 0
    cur = date.today()
    if (today_stats.get("closed") or 0) > 0:
        streak = 1
    cur = cur - timedelta(days=1)
    while True:
        s = by_date.get(cur.isoformat())
        if s and (s.get("closed") or 0) > 0:
            streak += 1
            cur = cur - timedelta(days=1)
        else:
            break

    return jsonify({
        "today": {
            "captured": int(today_stats.get("captured") or 0),
            "classified": int(today_stats.get("classified") or 0),
            "closed": int(today_stats.get("closed") or 0),
        },
        "streak": streak,
        "history": rows,
    })

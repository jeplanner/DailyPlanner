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

def _route_to_module(user_id, category, raw_text):
    """Create a row in the destination module when the schema is simple
    enough (Grocery, Checklist). Returns (table, dest_id) or (None, None).

    Health, Portfolio, TravelReads need fields the user has to fill in
    by hand (vitals, ticker / quantity, URL) — leave those in the bucket
    only and let the user open the destination module to add details."""
    text = (raw_text or "").strip()
    if not text:
        return None, None

    if category == "Grocery":
        try:
            rows = post("groceries", {
                "user_id": user_id,
                "item": text[:120],
                "category": "other",
                "priority": "medium",
                "is_purchased": False,
                "is_archived": False,
            })
            if rows:
                return "groceries", rows[0].get("id")
        except Exception:
            logger.exception("route_to_module: grocery insert failed")
        return None, None

    if category == "Checklist":
        try:
            rows = post("checklist_items", {
                "user_id": user_id,
                "name": text[:200],
                "schedule": "daily",
                "time_of_day": "anytime",
            })
            if rows:
                return "checklist_items", rows[0].get("id")
        except Exception:
            logger.exception("route_to_module: checklist insert failed")
        return None, None

    return None, None


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
                    "position,classified_at,created_at,updated_at"
                ),
                "order": "position.asc,created_at.desc",
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
    }
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

    dest_table, dest_id = (None, None)
    if cat:
        dest_table, dest_id = _route_to_module(user_id, cat, item.get("raw_text"))
    if dest_table:
        patch["destination_table"] = dest_table
        patch["destination_id"] = dest_id

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
        "destination_table": dest_table,
        "destination_id": dest_id,
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

    # If we haven't routed yet (or category changed in a way we can route),
    # try to push into the destination module.
    dest_table, dest_id = (None, None)
    if not item.get("destination_id"):
        dest_table, dest_id = _route_to_module(user_id, cat, item.get("raw_text"))
    if dest_table:
        patch["destination_table"] = dest_table
        patch["destination_id"] = dest_id

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
    return jsonify({
        "ok": True,
        "category": cat,
        "destination_table": dest_table,
        "destination_id": dest_id,
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

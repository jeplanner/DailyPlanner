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
    POST /api/quick-bucket/top5          set today's Top-5 panel order

Soft-delete only — see project convention (memory: no-hard-delete).
"""

import logging
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from services import quick_bucket_calendar_service as cal_sync
from supabase_client import get, post, update
from utils.quick_time import parse_at_schedule
from utils.user_tz import user_today

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

# Cap for the "Today's Top 5" panel. Hard-enforced server-side so a
# misbehaving client can't pin a sixth task.
TOP5_LIMIT = 5


def _auto_roll_top5(user_id):
    """Bump any incomplete past-day top-5 rows to today AND scrub the
    panel pointers off any already-done row.

    Two passes, one filter-based PATCH each (single round-trip apiece):
      1. Past-day, not done, not deleted   → top5_date := today
      2. Already done (any top5_date set)  → top5_date / top5_position := NULL

    The second pass is a one-shot cleanup for done rows that were pinned
    before the /done endpoint started clearing the pointers itself. It
    no-ops on future loads because the predicate matches zero rows once
    everything's been scrubbed."""
    today = date.today().isoformat()
    try:
        # 1) Roll yesterday's actives forward.
        update(
            "quick_bucket",
            params={
                "user_id":    f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_done":    "eq.false",
                "top5_date":  f"lt.{today}",
            },
            json={"top5_date": today},
        )
        # 2) Sweep done rows out of the panel.
        update(
            "quick_bucket",
            params={
                "user_id":    f"eq.{user_id}",
                "is_done":    "eq.true",
                "top5_date":  "not.is.null",
            },
            json={"top5_date": None, "top5_position": None},
        )
    except Exception:
        logger.exception("auto-roll top5 failed for %s", user_id)


# Keys the effort tracker adds to a task. Kept in one place so the
# update path and its column-missing fallback stay in sync.
_EFFORT_KEYS = ("planned_minutes", "actual_minutes", "effort_date")
_MAX_MINUTES = 60 * 24 * 366  # sanity cap — no single task logs > a year


def _parse_minutes(raw):
    """('' / None → clear) or a non-negative whole number of minutes,
    capped. Returns (value, ok): value is None to clear, an int to set,
    and ok is False when the input was present but unparseable."""
    if raw is None:
        return None, True
    if isinstance(raw, str) and not raw.strip():
        return None, True
    try:
        v = int(round(float(raw)))
    except (TypeError, ValueError):
        return None, False
    if v < 0 or v > _MAX_MINUTES:
        return None, False
    return v, True


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
    from flask_login import current_user
    js_v = ""
    try:
        js_path = os.path.join(current_app.static_folder, "js", "quick_bucket.js")
        js_v = str(int(os.path.getmtime(js_path)))
    except Exception:
        pass
    # Just the first name for the welcome banner — "Welcome Venghatesh"
    # reads better than "Welcome Venghatesh Sankaranarayanan".
    first_name = ""
    try:
        full = (current_user.display_name or "").strip()
        first_name = full.split()[0] if full else ""
    except Exception:
        pass
    return render_template(
        "quick_bucket.html", buckets=BUCKETS, js_v=js_v, first_name=first_name,
    )


# ─────────── lookup: projects (used by the move dialog) ─────

@quick_bucket_bp.route("/api/quick-bucket/projects", methods=["GET"])
@login_required
def list_user_projects():
    """Return active projects for the current user so the front-end
    can populate a Projects dropdown when moving a task to a real
    Project Task."""
    user_id = session["user_id"]
    try:
        rows = get(
            "projects",
            params={
                "user_id": f"eq.{user_id}",
                "is_archived": "eq.false",
                "select": "project_id,name",
                "order": "name.asc",
                "limit": "200",
            },
        ) or []
    except Exception:
        logger.exception("quick_bucket projects lookup failed")
        rows = []
    return jsonify({"projects": rows})


# ─────────── list ────────────────────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket", methods=["GET"])
@login_required
def list_items():
    """Return both active AND closed rows so the page can show a 'Done'
    section. Archived (is_deleted) rows still stay hidden — that's the
    soft-delete bucket for items the user removed entirely."""
    user_id = session["user_id"]

    # Roll yesterday's incomplete top-5 items into today before we read
    # — so the panel "carries over" automatically.
    _auto_roll_top5(user_id)

    today_iso = date.today().isoformat()
    # Try the new schema (with priority_label) first; fall back to the
    # legacy one for environments where MIGRATION_QUICK_BUCKET_PRIORITY_LABEL
    # hasn't been applied yet. Without this fallback, a missing column
    # on Supabase makes the whole list query 400 and the page renders
    # empty — which is what just happened.
    # Most-preferred first. The ladder exists because a column that has not
    # been migrated yet makes the WHOLE query 400 and renders the page empty,
    # which has happened before — so each rung drops the newest fields.
    select_scheduled = (
        "id,text,time_bucket,due_at,is_done,done_at,position,"
        "top5_date,top5_position,priority_label,"
        "planned_minutes,actual_minutes,effort_date,"
        "scheduled_event_id,scheduled_for,"
        "created_at,updated_at"
    )
    select_effort = (
        "id,text,time_bucket,due_at,is_done,done_at,position,"
        "top5_date,top5_position,priority_label,"
        "planned_minutes,actual_minutes,effort_date,"
        "created_at,updated_at"
    )
    select_full = (
        "id,text,time_bucket,due_at,is_done,done_at,position,"
        "top5_date,top5_position,priority_label,"
        "created_at,updated_at"
    )
    select_legacy = (
        "id,text,time_bucket,due_at,is_done,done_at,position,"
        "top5_date,top5_position,"
        "created_at,updated_at"
    )
    # FINISHED WORK LEAVES THE PAGE THE NEXT DAY.
    #
    # This query used to return every non-deleted row, which meant 66
    # completed items being loaded and rendered on every visit, ordered
    # done-last, forever. Ticking things off made the page longer.
    #
    # Today's completions STAY, because unticking a mistake has to be
    # possible without going hunting. Everything older lives at /archive,
    # which reads it in place — nothing is moved, so no count anywhere
    # else changes.
    _today_iso = user_today().isoformat()
    base_params = {
        "user_id": f"eq.{user_id}",
        "is_deleted": "eq.false",
        "or": f"(is_done.eq.false,done_at.gte.{_today_iso})",
        "order": "is_done.asc,position.asc,created_at.desc",
        "limit": "500",
    }
    rows = None
    for sel in (select_scheduled, select_effort, select_full, select_legacy):
        try:
            rows = get("quick_bucket", params={**base_params, "select": sel}) or []
            break
        except Exception as e:
            logger.warning("quick_bucket list with select=%s failed: %s", sel.split(',')[-2:], e)
            continue
    if rows is None:
        logger.exception("quick_bucket list failed for both selects")
        return jsonify({"items": [], "buckets": BUCKETS, "error": "Could not load"}), 200
    return jsonify({
        "items": rows,
        "buckets": BUCKETS,
        "today": today_iso,
        "top5_limit": TOP5_LIMIT,
    })


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

    is_done = bool(data.get("is_done", False))

    # Inline "@1pm today" schedule token → pin an absolute due_at and a
    # special "at" bucket. The existing due_at → Google Calendar mirror
    # then creates the popup alarm at that time. Done tasks ignore it.
    scheduled_due = None
    if not is_done:
        try:
            cleaned, scheduled_due = parse_at_schedule(text)
            if scheduled_due:
                text = (cleaned[:_MAX_TEXT_LEN] or text)
        except Exception:
            logger.exception("quick_bucket @time parse failed; ignoring token")
            scheduled_due = None

    bucket = (data.get("time_bucket") or "now").strip().lower()
    if scheduled_due:
        bucket = "at"
    elif bucket not in BUCKET_SET:
        bucket = "now"
    # Pick up X-Client-Id (set by sync-queue.js on every mutating
    # request) or the in-body client_id, whichever was sent. Used by
    # the (user_id, client_id) unique index to dedupe SW replays.
    client_id = (
        request.headers.get("X-Client-Id")
        or (data.get("client_id") or "").strip()
        or None
    )
    payload = {
        "user_id": user_id,
        "text": text,
        "time_bucket": bucket,
        # Absolute pinned time wins; otherwise fall back to the relative
        # bucket delta (None for now/future/done).
        "due_at": scheduled_due if scheduled_due else (_due_at_for(bucket) if not is_done else None),
        "position": int(data.get("position") or 0),
        "is_done": is_done,
        "is_deleted": False,
    }
    # Optional client-supplied priority badge (1..N). Falls back to
    # NULL when missing; the front-end computes max+1 client-side so
    # the round badge is set the moment the row appears.
    if "priority_label" in data and data.get("priority_label") is not None:
        try:
            v = int(data["priority_label"])
            if v >= 1:
                payload["priority_label"] = v
        except (TypeError, ValueError):
            pass
    if is_done:
        payload["done_at"] = datetime.utcnow().isoformat()
    if client_id:
        payload["client_id"] = client_id
    def _do_insert(p):
        if client_id:
            return post(
                "quick_bucket?on_conflict=user_id,client_id",
                p,
                prefer="resolution=merge-duplicates",
            )
        return post("quick_bucket", p)
    try:
        # Upsert on the (user_id, client_id) partial unique index so a
        # replayed offline write returns the original row instead of
        # creating a duplicate. Falls back to a normal insert when no
        # client_id was sent (legacy callers / online path).
        rows = _do_insert(payload)
    except Exception as e:
        # If priority_label triggered the failure (column missing on
        # un-migrated environments), retry the insert without it so the
        # add still succeeds. Same fallback shape as the GET above.
        if "priority_label" in payload:
            logger.warning("quick_bucket insert retry without priority_label: %s", e)
            retry = {k: v for k, v in payload.items() if k != "priority_label"}
            try:
                rows = _do_insert(retry)
            except Exception as e2:
                logger.error("quick_bucket insert failed (both attempts): %s", e2)
                return jsonify({"error": "Couldn't add — please try again."}), 502
        else:
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
    if "priority_label" in data:
        # null/0/missing all clear the badge; positive ints persist.
        raw = data.get("priority_label")
        if raw is None:
            patch["priority_label"] = None
        else:
            try:
                v = int(raw)
                patch["priority_label"] = v if v >= 1 else None
            except (TypeError, ValueError):
                pass

    # Effort tracking: planned / actual minutes + the day they count for.
    for key in ("planned_minutes", "actual_minutes"):
        if key in data:
            val, ok = _parse_minutes(data.get(key))
            if not ok:
                return jsonify({"error": "Minutes must be a positive whole number"}), 400
            patch[key] = val
    if "effort_date" in data:
        d = (data.get("effort_date") or "").strip()
        patch["effort_date"] = d or None

    # If the user logged any minutes but didn't pin a date, default the
    # effort to today so it shows up in today's summary automatically.
    logging_minutes = (
        patch.get("planned_minutes") is not None or patch.get("actual_minutes") is not None
    )
    if logging_minutes and not patch.get("effort_date") and "effort_date" not in data:
        patch["effort_date"] = date.today().isoformat()

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
        # Same defensive fallback as the GET / create paths: if an
        # optional column (priority_label or the effort fields) triggered
        # the failure on an un-migrated environment, retry without those
        # so the core patch (text / time_bucket / position) still saves.
        optional = ("priority_label", *_EFFORT_KEYS)
        if any(k in patch for k in optional):
            logger.warning("quick_bucket update retry without optional cols: %s", e)
            retry = {k: v for k, v in patch.items() if k not in optional}
            if retry:
                try:
                    update(
                        "quick_bucket",
                        params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                        json=retry,
                    )
                except Exception as e2:
                    logger.error("quick_bucket update failed (both attempts): %s", e2)
                    return jsonify({"error": "Couldn't save — please try again."}), 502
        else:
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


# ─────────── daily effort summary (planned vs actual) ────────

@quick_bucket_bp.route("/api/quick-bucket/effort-summary", methods=["GET"])
@login_required
def effort_summary():
    """Planned vs actual productive minutes for one day (default today).

    `?date=YYYY-MM-DD`. Sums planned_minutes / actual_minutes across the
    user's non-archived tasks whose effort_date is that day, and returns
    the per-task breakdown so the page can show where the time went."""
    user_id = session["user_id"]
    day = (request.args.get("date") or "").strip() or date.today().isoformat()
    try:
        rows = get(
            "quick_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "effort_date": f"eq.{day}",
                "select": "id,text,planned_minutes,actual_minutes,is_done",
                "limit": "500",
            },
        ) or []
    except Exception as e:
        # Effort columns missing (migration pending) → empty summary
        # rather than a 500, so the page still renders.
        logger.warning(
            "quick_bucket effort summary failed (run MIGRATION_QUICK_BUCKET_EFFORT.sql?): %s", e
        )
        return jsonify({
            "date": day, "planned": 0, "actual": 0, "count": 0,
            "tasks": [], "migration_pending": True,
        })

    tasks = []
    planned = actual = 0
    for r in rows:
        p = int(r["planned_minutes"]) if r.get("planned_minutes") is not None else 0
        a = int(r["actual_minutes"]) if r.get("actual_minutes") is not None else 0
        planned += p
        actual += a
        tasks.append({
            "id": r.get("id"),
            "text": r.get("text") or "",
            "planned": p,
            "actual": a,
            "is_done": bool(r.get("is_done")),
        })
    # Most time-consuming first, so the summary reads top-down by effort.
    tasks.sort(key=lambda t: (-t["actual"], -t["planned"]))
    return jsonify({
        "date": day,
        "planned": planned,
        "actual": actual,
        "count": len(tasks),
        "tasks": tasks,
    })


# ─────────── mark done ───────────────────────────────────────

# ─────────── Today's Top 5 panel ─────────────────────────────

@quick_bucket_bp.route("/api/quick-bucket/top5", methods=["POST"])
@login_required
def set_top5():
    """Reconcile today's Top-5 panel against the client's ordered list.

    Body: { "ids": ["id1", "id2", ...] } — every row that should be in
    today's panel (active + done-pinned together), in display order.
    Server stamps positions 1..N.

    Active rows previously in today's panel but not in payload have
    their top5_date/top5_position cleared (drag-out semantics). Done
    rows in today's panel are preserved — the user can't drag them,
    and they should stay crossed-out for the rest of the day.
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    raw_ids = data.get("ids") or []
    if not isinstance(raw_ids, list):
        return jsonify({"error": "ids must be a list"}), 400

    seen = set()
    ids = []
    for x in raw_ids:
        if not x or x in seen:
            continue
        seen.add(x)
        ids.append(str(x))

    today = date.today().isoformat()

    # Defensive: append any done-pinned rows the client may have
    # omitted, so they stay in the panel. Done rows aren't draggable.
    try:
        done_pinned = get(
            "quick_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_done": "eq.true",
                "top5_date": f"eq.{today}",
                "select": "id",
                "limit": "10",
            },
        ) or []
    except Exception:
        logger.exception("top5: done count failed")
        done_pinned = []
    for r in done_pinned:
        if r["id"] not in seen:
            ids.append(r["id"])
            seen.add(r["id"])

    if len(ids) > TOP5_LIMIT:
        return jsonify({
            "error": f"Top 5 is full — {len(ids)} items (limit {TOP5_LIMIT})."
        }), 400

    # Stamp each id with its visual position (1..N).
    for idx, item_id in enumerate(ids):
        try:
            update(
                "quick_bucket",
                params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                json={"top5_date": today, "top5_position": idx + 1},
            )
        except Exception:
            logger.exception("top5 stamp failed for %s", item_id)

    # Clear top5 on any *active* rows that were in today's panel but
    # didn't make this submission. Done rows are not cleared here.
    keep_csv = ",".join(ids) if ids else "00000000-0000-0000-0000-000000000000"
    try:
        update(
            "quick_bucket",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_done": "eq.false",
                "top5_date": f"eq.{today}",
                "id": f"not.in.({keep_csv})",
            },
            json={"top5_date": None, "top5_position": None},
        )
    except Exception:
        logger.exception("top5 clear-stale failed")

    return jsonify({"ok": True, "count": len(ids), "limit": TOP5_LIMIT})


@quick_bucket_bp.route("/api/quick-bucket/reorder", methods=["POST"])
@login_required
def reorder():
    """Persist a new ordering after the user drag-drops rows.
    Body: { "ids": ["id1", "id2", ...] } in new visual order.
    Each id's `position` is set to its index so the next list
    fetch returns rows in that order (the list endpoint sorts
    by position asc)."""
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list):
        return jsonify({"error": "ids must be a list"}), 400
    for idx, item_id in enumerate(ids):
        if not item_id:
            continue
        try:
            update(
                "quick_bucket",
                params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
                json={"position": idx},
            )
        except Exception:
            logger.exception("quick_bucket reorder: position update failed for %s", item_id)
    return jsonify({"ok": True, "count": len(ids)})


def _propagate_prep(user_id, item_id, done):
    """A bucket row that came from a prep topic closes the topic too.

    Reported: un-ticking a row here left the prep page and the day planner
    still showing it as outstanding. The link existed in one direction only
    — scheduling a topic wrote a bucket row, but the bucket row knew nothing
    about where it came from.

    `include_bucket=False` because the caller has already updated this very
    row; re-writing it would be pointless work and, if the two ever
    disagreed, a fight.

    Best-effort and never raises: the bucket's own tick has to succeed
    whatever happens here.
    """
    try:
        rows = get("quick_bucket", params={
            "id": f"eq.{item_id}", "user_id": f"eq.{user_id}",
            "select": "text", "limit": "1",
        }) or []
        if not rows:
            return
        from routes.interview_prep import (complete_prep_artifacts,
                                           parse_bucket_text)
        bank, title = parse_bucket_text(rows[0].get("text"))
        if not bank:
            return                      # an ordinary bucket line
        complete_prep_artifacts(user_id, bank, title, done, include_bucket=False)
    except Exception:
        logger.warning("quick_bucket: prep propagation failed for %s",
                       item_id, exc_info=True)


@quick_bucket_bp.route("/api/quick-bucket/<item_id>/done", methods=["POST"])
@login_required
def mark_done(item_id):
    user_id = session["user_id"]
    old_event_id = _fetch_event_id(user_id, item_id)
    try:
        # Clear the Top-5 pointers on completion so the row drops out of
        # today's panel automatically. Without this, done items stayed
        # pinned (crossed out) until the user dragged them out manually.
        update(
            "quick_bucket",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={
                "is_done":       True,
                "done_at":       datetime.utcnow().isoformat(),
                "top5_date":     None,
                "top5_position": None,
            },
        )
    except Exception as e:
        logger.error("quick_bucket done failed: %s", e)
        return jsonify({"error": "Couldn't update — please try again."}), 502

    if old_event_id:
        cal_sync.sync_async(user_id, item_id, {}, old_event_id=old_event_id, force_delete=True)
    _propagate_prep(user_id, item_id, True)
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

    # Reopening here reopens the topic it came from, which is the half that
    # was reported missing: un-ticking a row left the prep page and the day
    # planner still showing it done.
    _propagate_prep(user_id, item_id, False)
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


# ── Bulk: bucket items -> one calendar slot ──────────────────────────
# Asked for: select several bucket items, drop them into a slot on the
# calendar, and have them show up in that event's DESCRIPTION.
#
# ONE EVENT, NOT ONE PER ITEM. Five items become five lines in one slot's
# description, not five overlapping calendar entries. That is what "move them
# to a slot" means, and it is also the only version that stays readable on a
# week view.
#
# THE ITEMS ARE NOT DELETED AND NOT MARKED DONE. Deleting loses them; marking
# them done is a lie, because they are scheduled rather than finished. They
# are linked to the event they went to (scheduled_event_id / scheduled_for),
# which is reversible and lets the bucket show where a row went.

#: The description is rebuilt from scratch on every scheduling, so it needs a
#: marker to know which part it owns. Anything the user typed above this line
#: is preserved.
_QB_DESC_HEADER = "From Quick Bucket:"


def _qb_description(texts, existing=""):
    """Build the event description, keeping anything the user wrote.

    Appending blindly would duplicate the list every time more items are
    scheduled into the same slot; replacing blindly would delete a note the
    user had typed. So the block below the marker is ours to rewrite and
    everything above it is theirs.
    """
    kept = (existing or "").split(_QB_DESC_HEADER)[0].rstrip()
    lines = [f"• {t}" for t in texts if t]
    block = _QB_DESC_HEADER + "\n" + "\n".join(lines)
    return (kept + "\n\n" + block).strip() if kept else block


def _add_minutes(hhmm, minutes):
    """Clock arithmetic that stops at 23:59 instead of wrapping into
    yesterday. An event that wrapped would render at the top of the day and
    look like it happens in the morning."""
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    total = min(h * 60 + m + minutes, 23 * 60 + 59)
    return f"{total // 60:02d}:{total % 60:02d}"


@quick_bucket_bp.route("/api/quick-bucket/schedule", methods=["POST"])
@login_required
def schedule_to_calendar():
    """Move a selection of bucket items into one calendar slot.

    Body: {ids: [...], date: 'YYYY-MM-DD', start: 'HH:MM',
           duration: minutes, title?: str, event_id?: str}

    `event_id` adds the selection to an EXISTING slot rather than creating a
    new one, which is what a second bulk-move into the same hour should do.
    """
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    ids = [str(i) for i in (data.get("ids") or []) if str(i).strip()]
    if not ids:
        return jsonify({"error": "Select at least one item first."}), 400

    plan_date = (data.get("date") or "").strip()
    start = (data.get("start") or "").strip()[:5]
    try:
        date.fromisoformat(plan_date)
        datetime.strptime(start, "%H:%M")
    except (ValueError, TypeError):
        return jsonify({"error": "Pick a valid date and time."}), 400

    try:
        duration = int(data.get("duration") or 30)
    except (TypeError, ValueError):
        duration = 30
    duration = max(5, min(600, duration))
    end = _add_minutes(start, duration)

    # Read the selected rows BACK from the database rather than trusting the
    # titles the client sent — the description must reflect what the bucket
    # actually holds, and this also scopes the ids to this user.
    try:
        rows = get("quick_bucket", params={
            "user_id": f"eq.{user_id}",
            "id": f"in.({','.join(ids)})",
            "is_deleted": "eq.false",
        }) or []
    except Exception as exc:
        logger.error("quick_bucket schedule read failed: %s", exc)
        return jsonify({"error": "Couldn't read those items — please retry."}), 502

    if not rows:
        return jsonify({"error": "Those items are no longer in the bucket."}), 404

    # Keep the order the user sees, not whatever the database returned.
    order = {str(i): n for n, i in enumerate(ids)}
    rows.sort(key=lambda r: order.get(str(r.get("id")), 999))
    texts = [(r.get("text") or "").strip() for r in rows]

    title = (data.get("title") or "").strip()
    if not title:
        # A slot holding one item should be named after it; several become a
        # count, because a title made of five concatenated tasks is unreadable
        # in a calendar cell.
        title = texts[0] if len(texts) == 1 else f"{len(texts)} bucket tasks"
    title = title[:200]

    event_id = (data.get("event_id") or "").strip()
    try:
        if event_id:
            existing = get("daily_events", params={
                "id": f"eq.{event_id}", "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
            }) or []
            if not existing:
                return jsonify({"error": "That calendar slot no longer exists."}), 404
            row = existing[0]
            update("daily_events",
                   params={"id": f"eq.{event_id}", "user_id": f"eq.{user_id}"},
                   json={"description": _qb_description(texts, row.get("description"))})
            created = row
        else:
            payload = {
                "user_id": user_id,
                "plan_date": plan_date,
                "start_time": start,
                "end_time": end,
                "title": title,
                "description": _qb_description(texts),
                "priority": "medium",
                "reminder_minutes": 10,
            }
            resp = post("daily_events", payload, prefer="return=representation")
            created = (resp or [{}])[0]
    except Exception as exc:
        logger.error("quick_bucket schedule write failed: %s", exc)
        return jsonify({"error": "Couldn't create the calendar slot."}), 502

    # Link the rows to where they went. Best-effort: the columns arrive with
    # MIGRATION_QUICK_BUCKET_SCHEDULE.sql, and the scheduling itself — the
    # thing that was asked for — must still work before that has been run.
    linked = False
    try:
        update("quick_bucket",
               params={"user_id": f"eq.{user_id}", "id": f"in.({','.join(ids)})"},
               json={"scheduled_event_id": created.get("id"),
                     "scheduled_for": plan_date})
        linked = True
    except Exception as exc:
        logger.warning("quick_bucket schedule link skipped — run "
                       "MIGRATION_QUICK_BUCKET_SCHEDULE.sql (%s)", str(exc)[:120])

    return jsonify({
        "ok": True,
        "event_id": created.get("id"),
        "title": title,
        "date": plan_date,
        "start": start,
        "end": end,
        "count": len(texts),
        "linked": linked,
    })

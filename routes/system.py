from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from supabase_client import get
from services.login_service import login_required

system_bp = Blueprint("system", __name__)


@system_bp.route("/ping")
def ping():
    return "OK", 200


@system_bp.route("/favicon.ico")
def favicon():
    return "", 204


@system_bp.route("/pending")
def pending_page():
    """Page that reads the offline-write queue out of the user's
    IndexedDB and lets them inspect or delete entries before they
    sync. Entirely client-rendered — the server holds nothing here."""
    return render_template("pending.html")


@system_bp.route("/open", methods=["GET", "POST"])
@login_required
def file_handler():
    """File Handler API + protocol handler entry point.

    Manifest's file_handlers route .ics / .md / .csv → /open. The
    browser POSTs a multipart form with one file field; we sniff the
    extension and redirect to the right surface. The protocol handler
    (web+dailyplanner://) hits the GET path with ?u=<encoded URL>.

    No file processing here yet — we just route. Each destination page
    can pull the file from sessionStorage on the client if it needs
    the contents."""
    # Protocol handler — incoming web+dailyplanner://something
    if request.method == "GET":
        url = (request.args.get("u") or "").strip()
        # Currently the only thing we route on is the path component.
        # Future: parse `add-task?text=...` style intents.
        if url.startswith("inbox"):
            return redirect(url_for("inbox_bp.inbox_page"))
        if url.startswith("check"):
            return redirect("/checklist")
        return redirect(url_for("inbox_bp.inbox_page"))

    # File handler — POST with multipart/form-data, one or more files.
    f = request.files.get("file") or next(iter(request.files.values()), None)
    if not f or not f.filename:
        return redirect(url_for("inbox_bp.inbox_page"))
    ext = (f.filename.rsplit(".", 1)[-1] or "").lower()
    # Stash the raw bytes briefly in the user's session so the
    # destination page can offer to import. Cap at 256 KB to stay
    # well under typical session-cookie size limits.
    try:
        blob = f.read(256 * 1024)
        session["pending_file"] = {
            "name": f.filename,
            "ext":  ext,
            # session can serialize bytes via flask's signed-cookie
            # only as a string — base64 keeps it round-trippable.
            "b64":  __import__("base64").b64encode(blob).decode("ascii"),
        }
    except Exception:
        pass

    if ext == "ics":
        return redirect("/planner")          # calendar import lives here
    if ext in ("md", "markdown"):
        return redirect("/scribble")         # notes
    if ext == "csv":
        return redirect("/portfolio")        # transactions / holdings import
    return redirect(url_for("inbox_bp.inbox_page"))


@system_bp.route("/offline")
def offline():
    # Self-contained page the service worker serves when a navigation
    # request fails (no network and no cached copy). Must NOT extend
    # base.html — base.html pulls runtime dependencies we may not have
    # cached. Login-free by design so it works in any auth state.
    return render_template("offline.html")


@system_bp.route("/api/badge")
@login_required
def badge_count():
    """Aggregate "needs your attention" count for the App Badging API.

    Combines:
      - Inbox unread items   (status = Unread, not archived)
      - Today's checklist items not yet ticked

    Schema notes:
      - inbox_links soft-delete uses `is_archived`, not `is_deleted`
      - checklist_items has no `is_done` column; completion is tracked
        in checklist_ticks(item_id, tick_date, reminder_time). An
        item is "done today" iff at least one tick row for that item
        exists with tick_date = today. Items with multiple reminder
        fires count as done when ANY fire is ticked — keeps the
        badge simple (rule the badge represents: "do I have anything
        outstanding today").
    """
    from datetime import date as _date
    user_id = session["user_id"]
    today = _date.today().isoformat()
    total = 0

    try:
        rows = get(
            "inbox_links",
            params={
                "user_id":     f"eq.{user_id}",
                "status":      "eq.Unread",
                "is_archived": "eq.false",
                "select":      "id",
                "limit":       200,
            },
        ) or []
        total += len(rows)
    except Exception:
        pass

    try:
        items = get(
            "checklist_items",
            params={
                "user_id":    f"eq.{user_id}",
                "is_deleted": "eq.false",
                "select":     "id",
                "limit":      500,
            },
        ) or []
        if items:
            ticks = get(
                "checklist_ticks",
                params={
                    "user_id":   f"eq.{user_id}",
                    "tick_date": f"eq.{today}",
                    "select":    "item_id",
                    "limit":     500,
                },
            ) or []
            ticked_ids = {t["item_id"] for t in ticks}
            total += sum(1 for i in items if i["id"] not in ticked_ids)
    except Exception:
        pass

    return jsonify({"count": total})


@system_bp.route("/api/search")
@login_required
def global_search():
    """Cross-table search palette (Cmd+K).

    Query params: q=<text>, limit=<int, default 30>

    Searches: project_tasks.task_text, todo_matrix.task_text,
    scribble_notes.title+body, reference_links.title+url,
    inbox_links.title+url, projects.name. Each result has a uniform
    shape: { type, id, title, snippet, url, badge }.

    Uses PostgREST `ilike` for case-insensitive substring match.
    Per-table limit caps blast radius; client de-dups by url.
    """
    user_id = session["user_id"]
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"results": []})

    try:
        limit = max(1, min(50, int(request.args.get("limit") or 30)))
    except (TypeError, ValueError):
        limit = 30
    per_table = max(3, limit // 5)
    pattern = f"ilike.*{q}*"
    out = []

    # 1. Project tasks
    try:
        rows = get(
            "project_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_eliminated": "eq.false",
                "task_text": pattern,
                "select": "task_id,task_text,project_id,status,due_date",
                "limit": per_table,
            },
        ) or []
        for r in rows:
            out.append({
                "type": "project_task",
                "id": r["task_id"],
                "title": r.get("task_text") or "(untitled task)",
                "snippet": (
                    f"Due {r['due_date']}" if r.get("due_date") else None
                ),
                "url": f"/projects/{r.get('project_id')}/tasks#{r['task_id']}"
                       if r.get("project_id") else "/projects",
                "badge": "Task",
            })
    except Exception:
        pass

    # 2. Matrix (Eisenhower) tasks
    try:
        rows = get(
            "todo_matrix",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "task_text": pattern,
                "select": "id,task_text,quadrant,task_date",
                "limit": per_table,
            },
        ) or []
        for r in rows:
            out.append({
                "type": "matrix_task",
                "id": r["id"],
                "title": r.get("task_text") or "(untitled)",
                "snippet": (
                    f"{r.get('quadrant') or ''}"
                    + (f" · {r['task_date']}" if r.get("task_date") else "")
                ),
                "url": "/todo",
                "badge": "Matrix",
            })
    except Exception:
        pass

    # 3. Scribble notes (title OR body match — two passes)
    try:
        for col in ("title", "body"):
            rows = get(
                "scribble_notes",
                params={
                    "user_id": f"eq.{user_id}",
                    "is_deleted": "eq.false",
                    col: pattern,
                    "select": "id,title,body",
                    "limit": per_table,
                },
            ) or []
            for r in rows:
                # Snippet: 80 chars of body around the match (best-effort)
                body = (r.get("body") or "").strip()
                snippet = body[:90] + ("…" if len(body) > 90 else "")
                out.append({
                    "type": "note",
                    "id": r["id"],
                    "title": r.get("title") or "(untitled note)",
                    "snippet": snippet,
                    "url": f"/scribble/{r['id']}",
                    "badge": "Note",
                })
    except Exception:
        pass

    # 4. Reference links
    try:
        for col in ("title", "url"):
            rows = get(
                "reference_links",
                params={
                    "user_id": f"eq.{user_id}",
                    "is_deleted": "eq.false",
                    col: pattern,
                    "select": "id,title,url,description",
                    "limit": per_table,
                },
            ) or []
            for r in rows:
                out.append({
                    "type": "reference",
                    "id": r["id"],
                    "title": r.get("title") or r.get("url") or "(link)",
                    "snippet": (r.get("description") or r.get("url") or "")[:90],
                    "url": r.get("url") or "/references",
                    "badge": "Reference",
                })
    except Exception:
        pass

    # 5. Inbox links
    try:
        for col in ("title", "url"):
            rows = get(
                "inbox_links",
                params={
                    "user_id": f"eq.{user_id}",
                    "is_deleted": "eq.false",
                    col: pattern,
                    "select": "id,title,url,note",
                    "limit": per_table,
                },
            ) or []
            for r in rows:
                out.append({
                    "type": "inbox",
                    "id": r["id"],
                    "title": r.get("title") or r.get("url") or "(link)",
                    "snippet": (r.get("note") or r.get("url") or "")[:90],
                    "url": r.get("url") or "/inbox",
                    "badge": "Inbox",
                })
    except Exception:
        pass

    # 6. Projects (by name)
    try:
        rows = get(
            "projects",
            params={
                "user_id": f"eq.{user_id}",
                "is_archived": "eq.false",
                "name": pattern,
                "select": "project_id,name,description",
                "limit": per_table,
            },
        ) or []
        for r in rows:
            out.append({
                "type": "project",
                "id": r["project_id"],
                "title": r.get("name") or "(unnamed)",
                "snippet": (r.get("description") or "")[:90],
                "url": f"/projects/{r['project_id']}/tasks",
                "badge": "Project",
            })
    except Exception:
        pass

    # De-dup by (type, id) and cap to limit
    seen = set()
    deduped = []
    for r in out:
        key = (r["type"], r["id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
        if len(deduped) >= limit:
            break

    return jsonify({"results": deduped, "query": q})


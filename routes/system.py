from flask import Blueprint, jsonify, request, session
from supabase_client import get
from services.login_service import login_required

system_bp = Blueprint("system", __name__)


@system_bp.route("/ping")
def ping():
    return "OK", 200


@system_bp.route("/favicon.ico")
def favicon():
    return "", 204


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


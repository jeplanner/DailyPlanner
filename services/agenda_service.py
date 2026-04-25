"""
services/agenda_service.py
──────────────────────────
Unified "agenda item" query layer. Normalizes calendar events, Eisenhower
matrix tasks, project tasks, and habits into a single `Item` shape that
views (morning dashboard, calendar, timeline, search) can consume without
each re-implementing the joins.

Design principles
─────────────────
1. **One shape for all sources.** Every fetcher returns `list[dict]` with
   the same keys. Views sort/filter without caring which table a row came
   from.
2. **One join per concern.** Project names, OKR titles, recurrence labels
   are resolved here once and stamped onto items. Views shouldn't issue
   secondary lookups.
3. **Soft-delete honored.** Callers pass `include_deleted=False` by
   default. No call site should have to remember the `is_deleted=eq.false`
   PostgREST filter.
4. **Idempotent failures.** Every supabase call is try/except with a
   logged warning and an empty list fallback — one failing table should
   never break the whole dashboard.

Item shape
──────────
    {
      "id":           str | int,          # raw row id, prefixed when
                                           # ambiguous across sources
                                           # ("pt-7", "ev-3", "hb-11")
      "type":         "meeting" | "task" | "habit",
      "source":       "matrix" | "project" | "event" | "habit",
      "title":        str,
      "time":         "HH:MM" | None,
      "end_time":     "HH:MM" | None,
      "date":         "YYYY-MM-DD" | None,
      "done":         bool,
      "status":       "open" | "in_progress" | "done" | ...,
      "priority":     "high" | "medium" | "low" | None,
      "context":      str | None,          # project name / quadrant
      "link":         str | None,          # deep link to editing surface
      "project_id":   str | None,
      "objective_id": int | None,
      "key_result_id": int | None,
      "initiative_id": int | None,
      "recurrence":   "daily" | "weekly" | "monthly" | None,
      "delegated_to": str | None,
      # habit-only (present when type == "habit"):
      "habit_goal":    float | None,
      "habit_value":   float | None,
      "habit_unit":    str | None,
      "habit_type":    "boolean" | "number" | None,
      "progress_pct":  int | None,
      # overdue-only (present on overdue items):
      "days_overdue":  int,
    }
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, Optional

from supabase_client import get

logger = logging.getLogger(__name__)

QUADRANT_LABELS = {
    "do": "Do Now",
    "schedule": "Schedule",
    "delegate": "Delegate",
    "eliminate": "Eliminate",
}

_SORT_PRIORITY_WEIGHT = {"high": 1, "medium": 2, "low": 3}


# ═══════════════════════════════════════════════════════════
# Shared lookup helpers
# ═══════════════════════════════════════════════════════════

def _to_iso(plan_date) -> str:
    """Accepts a date or an ISO string; returns the ISO string form."""
    return plan_date.isoformat() if hasattr(plan_date, "isoformat") else str(plan_date)


def _safe_get(table: str, *, params: dict, action: str) -> list:
    """Wrapped supabase GET that never raises: logs + returns []."""
    try:
        return get(table, params=params) or []
    except Exception as e:
        logger.warning("agenda_service: %s failed: %s", action, e)
        return []


def _project_name_map(user_id: str, project_ids: Iterable) -> dict:
    """Map project_id → name for the given ids. Empty dict if no ids."""
    ids = {p for p in project_ids if p}
    if not ids:
        return {}
    rows = _safe_get(
        "projects",
        params={
            "user_id": f"eq.{user_id}",
            "project_id": f"in.({','.join(str(p) for p in ids)})",
            "select": "project_id,name",
        },
        action="project name lookup",
    )
    return {r["project_id"]: r.get("name") for r in rows}


def _recurrence_map(recurring_ids: Iterable) -> dict:
    """Map recurring_id → recurrence type. Used by matrix tasks where the
    rule is stored separately in recurring_tasks."""
    ids = {r for r in recurring_ids if r}
    if not ids:
        return {}
    rows = _safe_get(
        "recurring_tasks",
        params={
            "id": f"in.({','.join(str(i) for i in ids)})",
            "select": "id,recurrence",
        },
        action="recurrence lookup",
    )
    return {r["id"]: r.get("recurrence") for r in rows}


def _days_overdue(due_date_iso, ref_date) -> int:
    """How many whole days in the past is due_date_iso relative to ref_date?
    Returns 0 when unparseable or not overdue."""
    if not due_date_iso:
        return 0
    try:
        dd = date.fromisoformat(str(due_date_iso))
        return max(0, (ref_date - dd).days)
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════
# Fetchers — one per source. Each returns list[dict] in the Item shape.
# ═══════════════════════════════════════════════════════════

def fetch_events(user_id: str, plan_date) -> list[dict]:
    """Calendar meetings for a single day from `daily_events`."""
    date_iso = _to_iso(plan_date)
    rows = _safe_get(
        "daily_events",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{date_iso}",
            "is_deleted": "eq.false",
            "select": "id,title,description,start_time,end_time,status,priority,quadrant",
            "order": "start_time.asc",
        },
        action="events fetch",
    )
    out = []
    for r in rows:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        start = (r.get("start_time") or "")[:5] or None
        end = (r.get("end_time") or "")[:5] or None
        out.append({
            "id": f"ev-{r.get('id')}",
            "type": "meeting",
            "source": "event",
            "title": title,
            "time": start,
            "end_time": end,
            "date": date_iso,
            "done": r.get("status") == "done",
            "status": r.get("status") or "open",
            "priority": r.get("priority"),
            "context": (r.get("description") or "").strip() or None,
            "link": "/planner",
            "project_id": None,
            "recurrence": None,
            "delegated_to": None,
        })
    return out


def fetch_matrix_items(
    user_id: str,
    plan_date=None,
    *,
    include_done: bool = True,
    include_deleted: bool = False,
    project_name_map: Optional[dict] = None,
) -> list[dict]:
    """Eisenhower matrix rows for a date (or across all dates if plan_date
    is None, used for overdue scans)."""
    params = {
        "user_id": f"eq.{user_id}",
        "select": "id,task_text,is_done,status,priority,quadrant,task_time,"
                  "task_date,plan_date,category,project_id,recurring_id",
    }
    if not include_deleted:
        params["is_deleted"] = "eq.false"
    if plan_date is not None:
        params["plan_date"] = f"eq.{_to_iso(plan_date)}"

    rows = _safe_get("todo_matrix", params=params, action="matrix fetch")
    rows = [r for r in rows if (r.get("category") or "") != "Travel-archived"]
    if not include_done:
        rows = [r for r in rows if not r.get("is_done")]

    # Lookups we need in bulk
    if project_name_map is None:
        project_name_map = _project_name_map(
            user_id,
            (r.get("project_id") for r in rows),
        )
    rec_map = _recurrence_map(r.get("recurring_id") for r in rows)

    out = []
    for r in rows:
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        tt = (r.get("task_time") or "")[:5] or None
        ctx = project_name_map.get(r.get("project_id")) or QUADRANT_LABELS.get(r.get("quadrant"))
        out.append({
            "id": r.get("id"),
            "type": "task",
            "source": "matrix",
            "title": title,
            "time": tt,
            "end_time": None,
            "date": r.get("task_date") or r.get("plan_date"),
            "done": bool(r.get("is_done")),
            "status": r.get("status") or "open",
            "priority": r.get("priority"),
            "context": ctx,
            "link": "/todo",
            "project_id": r.get("project_id"),
            "recurrence": rec_map.get(r.get("recurring_id")),
            "delegated_to": None,
            "_quadrant": r.get("quadrant"),  # raw for views that care
        })
    return out


def fetch_project_items(
    user_id: str,
    *,
    due_on: Optional[str] = None,
    overdue_before: Optional[str] = None,
    project_id: Optional[str] = None,
    include_done: bool = True,
    project_name_map: Optional[dict] = None,
) -> list[dict]:
    """Project tasks, optionally filtered to due-on-date or overdue-before.

    - `due_on`: only rows with due_date == this ISO date
    - `overdue_before`: only rows with due_date < this ISO date AND not done
    - `project_id`: scope to a single project
    """
    params = {
        "user_id": f"eq.{user_id}",
        "is_eliminated": "eq.false",
        "select": "task_id,task_text,status,priority,due_time,due_date,"
                  "project_id,initiative_id,key_result_id,delegated_to,is_recurring,"
                  "recurrence_type",
        "order": "due_date.asc",
        "limit": 400,
    }
    if project_id:
        params["project_id"] = f"eq.{project_id}"
    if due_on:
        params["due_date"] = f"eq.{due_on}"
    if overdue_before:
        params["due_date"] = f"lt.{overdue_before}"
        params["status"] = "neq.done"
    if not include_done:
        params["status"] = "neq.done"

    rows = _safe_get("project_tasks", params=params, action="project tasks fetch")

    if project_name_map is None:
        project_name_map = _project_name_map(
            user_id,
            (r.get("project_id") for r in rows),
        )

    out = []
    for r in rows:
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        out.append({
            "id": f"pt-{r.get('task_id')}",
            "type": "task",
            "source": "project",
            "title": title,
            "time": (r.get("due_time") or "")[:5] or None,
            "end_time": None,
            "date": r.get("due_date"),
            "done": r.get("status") == "done",
            "status": r.get("status") or "open",
            "priority": r.get("priority"),
            "context": project_name_map.get(r.get("project_id")),
            "link": f"/projects/{r.get('project_id')}/tasks" if r.get("project_id") else None,
            "project_id": r.get("project_id"),
            "initiative_id": r.get("initiative_id"),
            "key_result_id": r.get("key_result_id"),
            "recurrence": r.get("recurrence_type") if r.get("is_recurring") else None,
            "delegated_to": r.get("delegated_to"),
        })
    return out


def fetch_habits(user_id: str, plan_date) -> list[dict]:
    """Habits with today's progress. Each habit becomes one item. `done`
    is computed from goal + today's logged value (or boolean checked)."""
    date_iso = _to_iso(plan_date)
    habit_rows = _safe_get(
        "habit_master",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "id,name,unit,goal,habit_type,position",
            "order": "position.asc",
        },
        action="habit master fetch",
    )
    if not habit_rows:
        return []

    entry_rows = _safe_get(
        "habit_entries",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{date_iso}",
            "select": "habit_id,value",
        },
        action="habit entries fetch",
    )
    value_map = {r["habit_id"]: float(r.get("value") or 0) for r in entry_rows}

    out = []
    for h in habit_rows:
        goal = float(h.get("goal") or 0)
        value = value_map.get(h["id"], 0.0)
        is_boolean = (h.get("habit_type") == "boolean")
        done = (value >= 1) if is_boolean else (goal > 0 and value >= goal)
        pct = 100 if done else (int(round(value / goal * 100)) if goal > 0 else 0)
        pct = max(0, min(100, pct))
        # Habit items carry BOTH the normalized Item-dict keys (title/
        # habit_value/etc.) AND the short keys (name/value/goal/unit)
        # that the summary.html template reads directly. Keeping both
        # avoids touching the template and preserves the legacy contract
        # from before the agenda-service refactor.
        name = h.get("name") or ""
        unit = h.get("unit")
        out.append({
            "id": f"hb-{h['id']}",
            "type": "habit",
            "source": "habit",
            "title": name,
            "name": name,          # template expects this
            "time": None,
            "end_time": None,
            "date": date_iso,
            "done": done,
            "status": "done" if done else "open",
            "priority": None,
            "context": None,
            "link": "/health",
            # Normalized (new) field names
            "habit_goal": goal,
            "habit_value": value,
            "habit_unit": unit,
            "habit_type": h.get("habit_type"),
            "progress_pct": pct,
            # Template-compatibility short names (pre-agenda-service)
            "goal": goal,
            "value": value,
            "unit": unit,
        })
    return out


# ═══════════════════════════════════════════════════════════
# Composite views
# ═══════════════════════════════════════════════════════════

def fetch_done_today(user_id: str, plan_date) -> list[dict]:
    """All tasks the user marked done today — across both matrix and
    project sources. Used by the "Today's Recap" section at the bottom
    of the daily summary so completed work has a celebratory home and
    can still be unchecked if the user marked something done by mistake.

    "Today" is bounded by the plan_date the dashboard is being rendered
    for, not necessarily wall-clock today, so navigating to a past day's
    recap shows what was completed on that date.
    """
    iso = _to_iso(plan_date)
    day_start = f"{iso}T00:00:00"
    day_end = f"{iso}T23:59:59.999"

    # Matrix tasks: is_done=true, updated within the day
    matrix_rows = _safe_get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "is_done": "eq.true",
            "updated_at": f"gte.{day_start}",
            "and": f"(updated_at.lte.{day_end})",
            "select": "id,task_text,priority,task_date,plan_date,quadrant,"
                      "category,project_id,updated_at",
            "order": "updated_at.desc",
            "limit": 200,
        },
        action="done-today matrix fetch",
    )

    # Project tasks: status='done', updated within the day
    project_rows = _safe_get(
        "project_tasks",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "is_eliminated": "eq.false",
            "status": "eq.done",
            "updated_at": f"gte.{day_start}",
            "and": f"(updated_at.lte.{day_end})",
            "select": "task_id,task_text,priority,due_date,project_id,"
                      "initiative_id,key_result_id,delegated_to,updated_at",
            "order": "updated_at.desc",
            "limit": 200,
        },
        action="done-today project fetch",
    )

    project_name_map = _project_name_map(
        user_id,
        [r.get("project_id") for r in matrix_rows]
        + [r.get("project_id") for r in project_rows],
    )

    items = []
    for r in matrix_rows:
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        items.append({
            "id": r.get("id"),
            "type": "task",
            "source": "matrix",
            "title": title,
            "done": True,
            "status": "done",
            "priority": r.get("priority"),
            "date": r.get("task_date") or r.get("plan_date"),
            "context": project_name_map.get(r.get("project_id"))
                       or QUADRANT_LABELS.get(r.get("quadrant")),
            "link": "/todo",
            "project_id": r.get("project_id"),
            "category": r.get("category"),
            "completed_at": r.get("updated_at"),
        })
    for r in project_rows:
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        items.append({
            "id": f"pt-{r.get('task_id')}",
            "type": "task",
            "source": "project",
            "title": title,
            "done": True,
            "status": "done",
            "priority": r.get("priority"),
            "date": r.get("due_date"),
            "context": project_name_map.get(r.get("project_id")),
            "link": "/projects",
            "project_id": r.get("project_id"),
            "category": None,
            "completed_at": r.get("updated_at"),
        })

    items.sort(key=lambda x: x.get("completed_at") or "", reverse=True)
    return items


def fetch_overdue(user_id: str, plan_date) -> list[dict]:
    """All overdue items (both matrix + project) sorted most-overdue first.
    Stamps `days_overdue` onto each."""
    iso = _to_iso(plan_date)
    ref = plan_date if isinstance(plan_date, date) else date.fromisoformat(iso)

    # Project tasks with due_date in the past and still not done
    project_items = fetch_project_items(user_id, overdue_before=iso)

    # Matrix tasks with task_date < today and still not done.
    # fetch_matrix_items doesn't support `task_date<` filter directly, so we
    # hand-craft the query.
    matrix_rows = _safe_get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "is_done": "eq.false",
            "task_date": f"lt.{iso}",
            "select": "id,task_text,priority,task_date,quadrant,category,project_id",
            "order": "task_date.asc",
            "limit": 200,
        },
        action="overdue matrix fetch",
    )
    project_name_map = _project_name_map(
        user_id,
        [r.get("project_id") for r in matrix_rows] + [p.get("project_id") for p in project_items],
    )
    matrix_items = []
    for r in matrix_rows:
        if (r.get("category") or "") == "Travel-archived":
            continue
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        matrix_items.append({
            "id": r.get("id"),
            "type": "task",
            "source": "matrix",
            "title": title,
            "time": None,
            "end_time": None,
            "date": r.get("task_date"),
            "done": False,
            "status": "open",
            "priority": r.get("priority"),
            "context": project_name_map.get(r.get("project_id")) or QUADRANT_LABELS.get(r.get("quadrant")),
            "link": "/todo",
            "project_id": r.get("project_id"),
            "category": r.get("category"),
        })

    # Fill in project context names we already fetched.
    for it in project_items:
        if not it.get("context") and it.get("project_id"):
            it["context"] = project_name_map.get(it["project_id"])

    combined = matrix_items + project_items
    for it in combined:
        it["days_overdue"] = _days_overdue(it.get("date"), ref)

    combined.sort(key=lambda x: (-(x.get("days_overdue") or 0), x.get("title") or ""))
    return combined


def _sort_timed_then_untimed(items: list[dict]) -> None:
    """Sort in place: items with time first (ascending), then untimed
    (alphabetic tie-break by title), priority ties to highest first."""
    items.sort(key=lambda it: (
        it.get("time") is None,
        it.get("time") or "",
        _SORT_PRIORITY_WEIGHT.get(it.get("priority") or "", 4),
        (it.get("title") or "").lower(),
    ))


def build_dashboard(user_id: str, plan_date) -> dict:
    """Morning dashboard composition.

    Returns the same shape `get_morning_dashboard` did, so callers don't
    need to change. Under the hood it fans out to the fetchers above.
    """
    # Fetch the four pillars in parallel conceptually; supabase-py is
    # synchronous so they serialize, but each is guarded and failures
    # degrade gracefully rather than blowing up the whole dashboard.
    events = fetch_events(user_id, plan_date)
    matrix_items = fetch_matrix_items(user_id, plan_date)
    project_due_today = fetch_project_items(user_id, due_on=_to_iso(plan_date))
    habits = fetch_habits(user_id, plan_date)
    overdue = fetch_overdue(user_id, plan_date)
    done_today = fetch_done_today(user_id, plan_date)

    # The morning-agenda table merges meetings + today's tasks into one
    # chronological list. Habits render in their own band (no time).
    today_items = events + matrix_items + project_due_today
    _sort_timed_then_untimed(today_items)

    # Counts for the hero line
    meeting_count = sum(1 for it in today_items if it["type"] == "meeting")
    task_count = sum(1 for it in today_items if it["type"] == "task")
    habits_done = sum(1 for h in habits if h["done"])

    return {
        "today_items": today_items,
        "overdue": overdue,
        "done_today": done_today,
        "habits": habits,
        "counts": {
            "meetings": meeting_count,
            "tasks": task_count,
            "habits": len(habits),
            "habits_done": habits_done,
            "overdue": len(overdue),
            "done_today": len(done_today),
        },
    }

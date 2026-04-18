from datetime import timedelta, datetime, date


def build_gantt_tasks(tasks, today=None):
    """Convert project_tasks rows into Frappe Gantt payload.

    Skips rows that can't be positioned (missing start_date) and
    defends against NULL planned/actual hours that would otherwise
    raise TypeError on the > 0 comparison.

    Progress is **calendar-based** (where are we in the time window?).
    Effort progress (`actual_hours / planned_hours`) is exposed as a
    separate field so the UI can show both without conflating them —
    the previous behaviour labeled an effort number as "% complete".
    """
    gantt = []
    today = today or date.today()

    for t in tasks:
        if not t.get("start_date"):
            continue

        try:
            start = datetime.fromisoformat(t["start_date"]).date()
        except (TypeError, ValueError):
            continue

        # Duration in days: null/0 defaults to 1-day task
        duration_days = t.get("duration_days") or 1
        end = start + timedelta(days=max(1, int(duration_days)) - 1)

        # Calendar progress: where are we in [start, end]?
        # Done tasks render as 100; otherwise clamp to [0, 100].
        status = (t.get("status") or "").lower()
        if status == "done":
            calendar_progress = 100
        else:
            total_days = max((end - start).days, 0) + 1
            elapsed = (today - start).days + 1
            calendar_progress = max(0, min(100, round(elapsed / total_days * 100)))

        # Effort progress: how many of the planned hours have been logged?
        planned = float(t.get("planned_hours") or 0)
        actual  = float(t.get("actual_hours") or 0)
        effort_progress = 0
        if planned > 0:
            effort_progress = min(100, round((actual / planned) * 100))

        # The Supabase primary key is `task_id` — map it to Frappe Gantt's
        # expected `id` field. Use str() because Frappe Gantt keys ids.
        task_id = t.get("task_id") or t.get("id")
        if not task_id:
            continue

        gantt.append({
            "id": str(task_id),
            "name": t.get("task_text") or "(untitled)",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "progress": int(calendar_progress),
            "effort_progress": int(effort_progress),
            "status": status or "open",
            "priority": t.get("priority") or "Medium",
        })

    return gantt

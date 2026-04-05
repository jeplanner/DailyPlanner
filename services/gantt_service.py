from datetime import timedelta, datetime


def build_gantt_tasks(tasks):
    """Convert project_tasks rows into Frappe Gantt payload.

    Skips rows that can't be positioned (missing start_date) and
    defends against NULL planned/actual hours that would otherwise
    raise TypeError on the > 0 comparison.
    """
    gantt = []

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

        # Progress calculation is None-safe
        planned = float(t.get("planned_hours") or 0)
        actual  = float(t.get("actual_hours") or 0)
        progress = 0
        if planned > 0:
            progress = min(100, round((actual / planned) * 100))

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
            "progress": int(progress),
        })

    return gantt

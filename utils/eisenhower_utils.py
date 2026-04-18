from datetime import date

from utils.user_tz import user_today


def compute_eisenhower_quadrants(tasks):
    # Use the user's timezone so "today" matches what they see in the UI,
    # not the server's local clock.
    today = user_today()

    quadrants = {
        "do_now": [],
        "schedule": [],
        "delegate": [],
        "eliminate": [],
    }

    for task in tasks:
        if not task.get("due_date"):
            continue

        if task["due_date"] == today:
            quadrants["do_now"].append(task)
        elif task["due_date"] > today:
            quadrants["schedule"].append(task)

    return quadrants

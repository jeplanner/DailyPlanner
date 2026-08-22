"""The mobile day planner — one scrollable page for one day.

WHY THIS EXISTS ALONGSIDE /calendar. The calendar is a time GRID: 24 hours
of fixed-height rows, absolutely-positioned chips, a horizontal week. That
is the right shape on a laptop and the wrong one on a phone, where the
grid is too narrow to read, chips overlap into slivers, and — the thing
that actually prompted this — anything scheduled before the grid's initial
scroll position is simply off-screen and looks like it does not exist.

So this page is a LIST, not a grid. It scrolls the way a phone scrolls,
every item is full width, and nothing is positioned by clock arithmetic.
Timed items come first in order, untimed ones after, and the reflection
and gratitude fields are at the bottom of the same scroll rather than on
another page — because the whole point of a day view is that reviewing
the day is part of it.

It is server-rendered from services.agenda_service.build_dashboard, which
already assembles events, matrix tasks, project tasks and bucket items
into one chronological list. Nothing here re-implements that; the page is
a different SHAPE over the same data.
"""
import logging
from datetime import date, datetime, timedelta
from datetime import time as dtime

from flask import Blueprint, redirect, render_template, request, session, url_for

from auth import login_required
from services.agenda_service import build_dashboard
from supabase_client import get
from utils.user_tz import user_now, user_today

logger = logging.getLogger("daily_plan")
day_bp = Blueprint("day", __name__)


def _meta(user_id, plan_date):
    """The reflection and gratitude for one day.

    Returns empty strings rather than None so the template can render the
    textareas without a guard on every one.
    """
    try:
        rows = get("daily_meta", {
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "select": "reflection,gratitude",
            "limit": "1",
        }) or []
    except Exception:
        logger.warning("day view: daily_meta read failed", exc_info=True)
        rows = []
    row = rows[0] if rows else {}
    return {
        "reflection": row.get("reflection") or "",
        "gratitude": row.get("gratitude") or "",
    }


@day_bp.route("/day", methods=["GET"])
@login_required
def day_page():
    user_id = session["user_id"]

    raw = (request.args.get("date") or "").strip()
    try:
        plan_date = date.fromisoformat(raw) if raw else user_today()
    except ValueError:
        # A malformed date in the URL is a bad link, not an error worth
        # showing — fall back to today rather than a 400 the user cannot act on.
        return redirect(url_for("day.day_page"))

    dash = build_dashboard(user_id, plan_date)
    items = dash.get("today_items") or []

    # The list is already sorted timed-then-untimed by the service. Split it
    # so the template can label the two groups, because "no time set" is
    # information rather than a gap.
    timed = [i for i in items if i.get("time")]
    untimed = [i for i in items if not i.get("time")]

    # MISSED: the slot has gone by and nothing marked it done. Computed here
    # rather than in the template so the same rule the calendar grid uses
    # lives on both surfaces — a day that reads "missed" on one and fine on
    # the other is worse than neither showing it.
    #
    # Measured from the END where one is recorded: an event running
    # 19:00-20:00 is not missed at 19:01, it is missed at 20:00.
    now = user_now()
    for i in timed:
        i["missed"] = False
        if i.get("done") or (i.get("status") or "open") == "done":
            continue
        stamp = (i.get("end_time") or i.get("time") or "")[:5]
        if not stamp or ":" not in stamp:
            continue
        try:
            hh, mm = (int(x) for x in stamp.split(":", 1))
        except ValueError:
            continue
        due = datetime.combine(plan_date, dtime(hh, mm), tzinfo=now.tzinfo)
        i["missed"] = due < now
    # An UNTIMED item is only missed once its whole day is behind us —
    # "no time set" cannot be late at 9am on the day itself.
    day_is_past = plan_date < now.date()
    for i in untimed:
        i["missed"] = day_is_past and not (
            i.get("done") or (i.get("status") or "open") == "done")

    return render_template(
        "day.html",
        plan_date=plan_date,
        prev_date=plan_date - timedelta(days=1),
        next_date=plan_date + timedelta(days=1),
        is_today=(plan_date == user_today()),
        timed=timed,
        untimed=untimed,
        habits=dash.get("habits") or [],
        overdue=dash.get("overdue") or [],
        done_today=dash.get("done_today") or [],
        counts=dash.get("counts") or {},
        intent=dash.get("intent") or {},
        meta=_meta(user_id, plan_date),
    )

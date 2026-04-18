"""
Reports — one page, four lenses: productivity, habits, financial, overview.
Each lens is a JSON endpoint; the page renders them client-side so the
user can flip between tabs and date ranges without a round-trip.

Financial report reuses the vault_unlocked_required gate since it reads
ref_cards (same sensitivity profile as the vault page).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session

from config import IST
from utils.user_tz import user_now, user_today
from services.login_service import login_required
from services.reports_service import (
    financial_report, habits_report, narrative_insight, productivity_report,
)
from routes.refcards import vault_unlocked_required

logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports", __name__)


def _parse_range():
    """Parse ?range=week|month|quarter|year|custom + ?start/?end.
    Defaults to 'week' ending today."""
    today = user_today()
    rng = (request.args.get("range") or "week").lower()
    start_arg = request.args.get("start")
    end_arg = request.args.get("end")

    if rng == "custom" and start_arg and end_arg:
        try:
            start = date.fromisoformat(start_arg)
            end = date.fromisoformat(end_arg)
        except ValueError:
            return today - timedelta(days=6), today, "week"
    elif rng == "month":
        start = today.replace(day=1)
        end = today
    elif rng == "quarter":
        qmonth = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=qmonth, day=1)
        end = today
    elif rng == "year":
        start = today.replace(month=1, day=1)
        end = today
    else:
        rng = "week"
        start = today - timedelta(days=6)
        end = today

    if start > end:
        start, end = end, start
    return start, end, rng


@reports_bp.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html")


@reports_bp.route("/api/reports/productivity")
@login_required
def api_productivity():
    start, end, rng = _parse_range()
    data = productivity_report(session["user_id"], start, end)
    data["range"]["preset"] = rng
    return jsonify(data)


@reports_bp.route("/api/reports/habits")
@login_required
def api_habits():
    start, end, rng = _parse_range()
    data = habits_report(session["user_id"], start, end)
    data["range"]["preset"] = rng
    return jsonify(data)


@reports_bp.route("/api/reports/financial")
@login_required
@vault_unlocked_required
def api_financial():
    today = user_today()
    return jsonify(financial_report(session["user_id"], today))


@reports_bp.route("/api/reports/overview")
@login_required
def api_overview():
    """Compose a one-line headline + the three reports.

    Financial is optional (only runs when the vault is unlocked) so the
    overview still works when the vault has never been set up."""
    start, end, rng = _parse_range()
    user_id = session["user_id"]
    today = user_today()

    productivity = productivity_report(user_id, start, end)
    habits = habits_report(user_id, start, end)

    # Financial — only include if the vault is unlocked, so an overview
    # page doesn't force a lock challenge.
    financial = None
    try:
        # Import here to avoid import cycle
        from routes.refcards import _vault_is_unlocked, _vault_touch
        if _vault_is_unlocked(user_id):
            _vault_touch()
            financial = financial_report(user_id, today)
    except Exception as e:
        logger.warning("overview: financial branch skipped: %s", e)

    return jsonify({
        "range": {"start": start.isoformat(), "end": end.isoformat(), "preset": rng},
        "headline": narrative_insight(productivity, habits, financial),
        "productivity": productivity,
        "habits": habits,
        "financial": financial,
    })

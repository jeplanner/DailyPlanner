"""
services/reports_service.py
───────────────────────────
Aggregation layer for the Reports page. Pulls from the same sources
agenda_service + habit_entries + ref_cards use, then rolls them up
into the shapes the report templates render.

Four lenses:
    • productivity  — task throughput, completion rate, quadrant mix
    • habits        — streaks + consistency per habit
    • financial     — bills, upcoming expirations, net-worth snapshot
    • overview      — one-line narrative + all four tiles at-a-glance

All functions take a (user_id, start_date, end_date) tuple and return
plain dicts. Views can JSON-serialize directly. No database writes.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from supabase_client import get
from utils.encryption import decrypt_rows

logger = logging.getLogger(__name__)


def _to_iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def _safe_get(table: str, *, params: dict, action: str) -> list:
    try:
        return get(table, params=params) or []
    except Exception as e:
        logger.warning("reports_service: %s failed: %s", action, e)
        return []


# ═══════════════════════════════════════════════════
# PRODUCTIVITY
# ═══════════════════════════════════════════════════

def productivity_report(user_id: str, start: date, end: date) -> dict:
    """Summarize task activity over a date range.

    Pulls matrix tasks in the window (plan_date) and computes:
      • total created / completed / still open
      • completion rate (%)
      • daily completion histogram (for sparkline)
      • Eisenhower quadrant distribution
      • top project by completed tasks
    """
    iso_start, iso_end = _to_iso(start), _to_iso(end)

    rows = _safe_get(
        "todo_matrix",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{iso_start}",
            "and": f"(plan_date.lte.{iso_end})",
            "is_deleted": "eq.false",
            "select": "id,plan_date,task_text,is_done,status,priority,quadrant,category,project_id",
            "limit": 2000,
        },
        action="productivity matrix fetch",
    )

    total = len(rows)
    done = sum(1 for r in rows if r.get("is_done"))
    open_rows = [r for r in rows if not r.get("is_done") and r.get("status") not in ("skipped", "deleted")]
    skipped = sum(1 for r in rows if r.get("status") == "skipped")
    rate = round((done / total) * 100) if total else 0

    # Daily completion histogram (one bar per day in range)
    days = []
    d = start
    while d <= end:
        days.append(d.isoformat())
        d += timedelta(days=1)
    daily_done = {day: 0 for day in days}
    daily_total = {day: 0 for day in days}
    for r in rows:
        pd = r.get("plan_date")
        if not pd:
            continue
        if pd in daily_total:
            daily_total[pd] += 1
            if r.get("is_done"):
                daily_done[pd] += 1

    # Quadrant distribution of completed tasks — where you actually spent energy
    quad_counts = defaultdict(int)
    for r in rows:
        if r.get("is_done"):
            q = r.get("quadrant") or "unset"
            quad_counts[q] += 1

    # Project leaderboard (completed)
    proj_counts = defaultdict(int)
    for r in rows:
        if r.get("is_done") and r.get("project_id"):
            proj_counts[r["project_id"]] += 1
    top_projects = sorted(proj_counts.items(), key=lambda x: -x[1])[:5]
    # Resolve names
    proj_name_map = {}
    pids = [p[0] for p in top_projects]
    if pids:
        pr = _safe_get(
            "projects",
            params={
                "user_id": f"eq.{user_id}",
                "project_id": f"in.({','.join(str(p) for p in pids)})",
                "select": "project_id,name",
            },
            action="project names",
        )
        proj_name_map = {p["project_id"]: p.get("name") for p in pr}

    # Oldest open + high-priority — the "stuck" list worth surfacing
    stuck = [
        {
            "id": r["id"],
            "title": (r.get("task_text") or "").strip(),
            "plan_date": r.get("plan_date"),
            "days_old": (end - date.fromisoformat(r["plan_date"])).days if r.get("plan_date") else 0,
            "priority": r.get("priority"),
        }
        for r in open_rows
        if r.get("priority") == "high" and r.get("plan_date")
    ]
    stuck.sort(key=lambda x: -x["days_old"])
    stuck = stuck[:10]

    return {
        "range": {"start": iso_start, "end": iso_end, "days": (end - start).days + 1},
        "totals": {"total": total, "done": done, "open": len(open_rows), "skipped": skipped, "rate": rate},
        "daily": [{"date": d, "done": daily_done[d], "total": daily_total[d]} for d in days],
        "quadrants": dict(quad_counts),
        "top_projects": [
            {"project_id": pid, "name": proj_name_map.get(pid, "—"), "count": cnt}
            for pid, cnt in top_projects
        ],
        "stuck_high_priority": stuck,
    }


# ═══════════════════════════════════════════════════
# HABITS
# ═══════════════════════════════════════════════════

def habits_report(user_id: str, start: date, end: date) -> dict:
    """Per-habit consistency + current streak + adherence in the window."""
    iso_start, iso_end = _to_iso(start), _to_iso(end)

    masters = _safe_get(
        "habit_master",
        params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "select": "id,name,unit,goal,habit_type,position",
            "order": "position.asc",
        },
        action="habit master",
    )
    if not masters:
        return {"range": {"start": iso_start, "end": iso_end}, "habits": []}

    entries = _safe_get(
        "habit_entries",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{iso_start}",
            "and": f"(plan_date.lte.{iso_end})",
            "select": "habit_id,plan_date,value",
            "limit": 3000,
        },
        action="habit entries range",
    )

    # Build habit_id → {plan_date: value}
    by_habit = defaultdict(dict)
    for e in entries:
        by_habit[e.get("habit_id")][e.get("plan_date")] = float(e.get("value") or 0)

    all_days = []
    d = start
    while d <= end:
        all_days.append(d.isoformat())
        d += timedelta(days=1)
    total_days = len(all_days)

    habits = []
    for h in masters:
        is_boolean = h.get("habit_type") == "boolean"
        goal = float(h.get("goal") or 0)
        values = by_habit.get(h["id"], {})

        # Per-day "met the goal" flag
        met = []
        for day in all_days:
            v = values.get(day, 0)
            if is_boolean:
                met.append(v >= 1)
            else:
                met.append(goal > 0 and v >= goal)
        met_days = sum(1 for m in met if m)
        adherence = round((met_days / total_days) * 100) if total_days else 0

        # Current streak — count back from end working backwards
        streak = 0
        for i in range(len(met) - 1, -1, -1):
            if met[i]:
                streak += 1
            else:
                break

        # Best streak within the window
        best = 0
        cur = 0
        for m in met:
            if m:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0

        habits.append({
            "id": h["id"],
            "name": h.get("name"),
            "unit": h.get("unit"),
            "goal": goal,
            "habit_type": h.get("habit_type"),
            "met_days": met_days,
            "total_days": total_days,
            "adherence": adherence,
            "current_streak": streak,
            "best_streak": best,
            "daily": [{"date": day, "value": values.get(day, 0), "met": met[i]} for i, day in enumerate(all_days)],
        })

    return {
        "range": {"start": iso_start, "end": iso_end, "days": total_days},
        "habits": habits,
    }


# ═══════════════════════════════════════════════════
# FINANCIAL
# ═══════════════════════════════════════════════════

ENCRYPTED_FIELDS = ["account_number", "customer_id", "portal_url", "notes", "payment_method", "details"]


def _parse_json(text):
    import json
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def financial_report(user_id: str, today: date) -> dict:
    """Snapshot of the vault as a financial portfolio:
      • bills this month: total monthly equivalent + upcoming due
      • expiring documents: passports, cards, FDs maturing in 90 days
      • portfolio: invested vs current value, asset allocation,
        concentration warning
      • ESOP vested value at FMV

    Unlike the other reports this one does NOT gate on vault unlock —
    the route hosting this should (callers apply @vault_unlocked_required).
    """
    rows = _safe_get(
        "ref_cards",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,provider,instrument_type,country,category,amount,billing_cycle,due_day,status,details,auto_pay",
            "limit": 1000,
        },
        action="ref cards for financial report",
    )
    decrypt_rows(rows, ENCRYPTED_FIELDS)
    for r in rows:
        r["details"] = _parse_json(r.get("details"))

    # ── Bills: monthly equivalent spend ────────────────
    monthly_total = 0.0
    upcoming = []      # due within 14 days
    expired_bills = [] # past due_day this month (not auto-pay)
    for r in rows:
        if r.get("status") == "inactive":
            continue
        amt = float(r.get("amount") or 0)
        cycle = r.get("billing_cycle") or ""
        if cycle == "monthly":
            monthly_total += amt
        elif cycle == "quarterly":
            monthly_total += amt / 3
        elif cycle in ("half-yearly", "half_yearly"):
            monthly_total += amt / 6
        elif cycle == "yearly":
            monthly_total += amt / 12

        due_day = r.get("due_day")
        if due_day and cycle in ("monthly", "quarterly", "half-yearly", "half_yearly", "yearly"):
            try:
                dd = int(due_day)
                # This month's occurrence
                this_month_due = today.replace(day=min(dd, 28))
                if this_month_due < today:
                    # Next month's
                    m = today.month + 1 if today.month < 12 else 1
                    y = today.year if today.month < 12 else today.year + 1
                    next_due = date(y, m, min(dd, 28))
                else:
                    next_due = this_month_due
                days_until = (next_due - today).days
                entry = {
                    "id": r["id"],
                    "provider": r.get("provider"),
                    "amount": amt,
                    "due_date": next_due.isoformat(),
                    "days_until": days_until,
                    "auto_pay": bool(r.get("auto_pay")),
                }
                if 0 <= days_until <= 14:
                    upcoming.append(entry)
            except (ValueError, TypeError):
                pass

    upcoming.sort(key=lambda x: x["days_until"])

    # ── Expiring documents (passport, DL, FD maturity, card expiry) ──
    expiring = []
    for r in rows:
        det = r.get("details") or {}
        exp_sources = [
            ("Expires", det.get("expiry_date")),
            ("Matures", det.get("maturity_date")),
            ("Renews", det.get("renewal_date")),
            ("Lock-up ends", det.get("lockup_until")),
            ("Options expire", det.get("expiration_date")),
        ]
        for label, exp in exp_sources:
            if not exp:
                continue
            try:
                d = date.fromisoformat(exp)
                days = (d - today).days
            except Exception:
                continue
            # Surface anything expiring within 90 days (or already expired within 365d)
            if -365 <= days <= 90:
                expiring.append({
                    "id": r["id"],
                    "provider": r.get("provider"),
                    "instrument_type": r.get("instrument_type"),
                    "label": label,
                    "date": exp,
                    "days": days,
                })
    expiring.sort(key=lambda x: x["days"])

    # ── Portfolio aggregation ──────────────────────────
    invested_cost = 0.0    # sum of cost basis (stocks)
    market_value = 0.0     # current market value (stocks + MF + FD + retirement)
    esop_vested = 0.0
    by_class = defaultdict(float)

    for r in rows:
        t = r.get("instrument_type")
        det = r.get("details") or {}
        amt = float(r.get("amount") or 0)

        if t in ("us_stock", "indian_stock"):
            shares = float(det.get("shares") or 0)
            avg_cost = float(det.get("avg_cost") or 0)
            cur = float(det.get("current_price") or 0)
            cost = shares * avg_cost
            mkt = shares * cur if cur else cost
            invested_cost += cost
            market_value += mkt
            by_class["Equity"] += mkt

        elif t == "esop":
            total = float(det.get("total_granted") or 0)
            fmv = float(det.get("current_fmv") or 0)
            strike = float(det.get("strike") or 0)
            # Apply a very lightweight linear-vesting approximation (server-side)
            grant = det.get("grant_date")
            cliff = float(det.get("vesting_cliff") or 0)
            total_months = float(det.get("vesting_total") or 0)
            override = det.get("vested_override")
            vested_shares = 0
            if override not in (None, ""):
                try:
                    vested_shares = float(override)
                except Exception:
                    pass
            elif grant and total_months > 0 and total:
                try:
                    g = date.fromisoformat(grant)
                    me = (today.year - g.year) * 12 + (today.month - g.month)
                    if me < cliff:
                        vested_shares = 0
                    elif me >= total_months:
                        vested_shares = total
                    else:
                        vested_shares = total * (me / total_months)
                except Exception:
                    pass
            if fmv:
                if strike > 0:
                    spread = max(0, fmv - strike)
                    val = spread * vested_shares
                else:
                    val = fmv * vested_shares
                esop_vested += val
                by_class["ESOP / RSU"] += val

        elif t == "mutual_fund":
            v = amt or (float(det.get("units") or 0) * float(det.get("nav") or 0))
            if v:
                market_value += v
                by_class["Mutual Fund"] += v

        elif t == "fixed_deposit":
            if amt:
                market_value += amt
                by_class["Fixed Deposit"] += amt

        elif t == "retirement":
            if amt:
                market_value += amt
                by_class["Retirement"] += amt

    allocation = []
    grand = sum(by_class.values())
    for cls, val in sorted(by_class.items(), key=lambda x: -x[1]):
        pct = (val / grand * 100) if grand > 0 else 0
        allocation.append({"class": cls, "value": round(val, 2), "pct": round(pct, 1)})

    gain = market_value - invested_cost if invested_cost > 0 else None
    gain_pct = (gain / invested_cost * 100) if (gain is not None and invested_cost > 0) else None

    # Concentration warning: any class > 60% of tracked portfolio
    warning = None
    if allocation and allocation[0]["pct"] >= 60:
        warning = f"{allocation[0]['class']} is {allocation[0]['pct']:.0f}% of your tracked portfolio."

    return {
        "today": today.isoformat(),
        "bills": {
            "monthly_equivalent": round(monthly_total, 2),
            "upcoming_14d": upcoming,
        },
        "expiring": expiring[:15],
        "portfolio": {
            "invested": round(invested_cost, 2),
            "market_value": round(market_value, 2),
            "gain": round(gain, 2) if gain is not None else None,
            "gain_pct": round(gain_pct, 2) if gain_pct is not None else None,
            "esop_vested": round(esop_vested, 2),
            "allocation": allocation,
            "concentration_warning": warning,
        },
    }


# ═══════════════════════════════════════════════════
# OVERVIEW — narrative insight line for the dashboard
# ═══════════════════════════════════════════════════

def narrative_insight(productivity: dict, habits: dict, financial: dict) -> str:
    """Compose a one-line narrative from the three reports. Deliberately
    terse — it's a headline, not a paragraph."""
    parts = []
    if productivity and productivity.get("totals"):
        t = productivity["totals"]
        if t["total"]:
            parts.append(f"{t['done']}/{t['total']} tasks done ({t['rate']}%)")
    if habits and habits.get("habits"):
        top = max(habits["habits"], key=lambda h: h["current_streak"], default=None)
        if top and top["current_streak"] >= 3:
            parts.append(f"{top['name'].title()} on a {top['current_streak']}-day streak")
    if financial:
        overdue_like = [e for e in financial.get("expiring", []) if e["days"] < 0]
        soon = [e for e in financial.get("expiring", []) if 0 <= e["days"] <= 30]
        if overdue_like:
            parts.append(f"⚠ {len(overdue_like)} expired document{'s' if len(overdue_like)>1 else ''}")
        elif soon:
            parts.append(f"{len(soon)} expiring in 30d")
    return " · ".join(parts) if parts else "Nothing to report yet — add some activity and come back."

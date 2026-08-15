"""
The goal planner's voice.

A countdown on its own only produces anxiety: it tells you time is going
without telling you what to do about it. This module turns the countdown
maths into one sentence that names the actual problem and the next move.

The register is deliberately blunt — the same tough-love tone the interview
prep coach uses — because a planner that congratulates you for being behind
is worse than no planner. It is not abusive, though: it scolds the SLIPPAGE,
never the person, and it always ends with something to do.

Tones (the page styles each one differently):
    celebrate  ahead of pace, or the goal is done
    cheer      on pace
    push       slightly behind, or a deadline closing while pace is fine
    scold      properly behind, or the budget says this cannot be done
    alarm      infeasible, or overdue

Order matters below: the checks run worst-news-first, because when a goal is
both behind AND impossible the impossibility is the thing worth saying.
"""

TONE_CELEBRATE = "celebrate"
TONE_CHEER = "cheer"
TONE_PUSH = "push"
TONE_SCOLD = "scold"
TONE_ALARM = "alarm"


def _hhmm(minutes):
    minutes = int(minutes or 0)
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"


def coach(summary, title, progress_pct):
    """One (message, tone) pair for a goal.

    `summary` is the dict from `utils.countdown.summarise`. Returns a
    neutral prompt when there is no deadline, because a goal with no date
    is a wish and saying so is more useful than inventing urgency.
    """
    if not summary or not summary.get("has_deadline"):
        return ("📅 No deadline on this goal yet. A goal without a date is a "
                "wish — give it a target and it becomes a plan.", TONE_PUSH)

    bd = summary["breakdown"]
    disp = summary["display"]
    pace = summary.get("pace")
    budget = summary.get("budget")
    days = bd["total_days"]
    progress = int(progress_pct or 0)

    # ── Overdue ────────────────────────────────────────────────────────
    if bd["overdue"]:
        if progress >= 100:
            return (f"🏁 Done, and past the date — but done. Close it out and "
                    f"set the next one.", TONE_CELEBRATE)
        return (f"🔴 {days} day(s) past the deadline at {progress}%. This one has "
                f"slipped. Either finish it this week or move the date honestly — "
                f"do not leave it rotting on the board.", TONE_ALARM)

    if progress >= 100:
        return (f"🏆 100% with {_period(bd)} still on the clock. That is what "
                f"finishing early looks like. Bank it and start the next goal.",
                TONE_CELEBRATE)

    # ── The budget says it cannot be done ──────────────────────────────
    # This outranks pace: being "on pace" for something arithmetically
    # impossible is the most dangerous state a plan can be in.
    if budget and not budget["feasible"]:
        short = _hhmm(budget["shortfall_minutes"])
        need = _hhmm(budget["required_daily_minutes"])
        have = _hhmm(budget["commit_minutes"])
        return (f"🚨 The maths does not work. {_period(bd)} at {have}/day gives you "
                f"{_hhmm(budget['available_minutes'])}, and this needs "
                f"{_hhmm(budget['needed_minutes'])} — you are {short} short. "
                f"Either go to {need}/day or cut scope today, while cutting is "
                f"still cheap.", TONE_ALARM)

    # ── Deadline imminent ──────────────────────────────────────────────
    if disp["tone"] == "urgent":
        if progress >= 80:
            return (f"⏳ {disp['value']} {disp['unit']} and you are at {progress}%. "
                    f"Nearly there — clear everything else and land it.", TONE_PUSH)
        return (f"⏰ {disp['value']} {disp['unit']} and only {progress}% done. "
                f"This is the last window. Stop planning and start closing.",
                TONE_ALARM)

    # ── Pace ───────────────────────────────────────────────────────────
    # Severity is RELATIVE, not a raw gap in percentage points. Fourteen
    # points behind when 24% was expected means you have done 40% of the
    # work you should have — serious. The same fourteen points when 90% was
    # expected is a rounding error. So the ratio decides the tone, with a
    # small absolute floor so the first few days of a goal (where `expected`
    # is tiny and the ratio is wild) cannot trigger a scolding over nothing.
    if pace:
        gap = pace["gap"]
        expected = pace["expected"]
        ratio = (pace["progress"] / expected) if expected > 0 else 1.0
        if ratio < 0.5 and gap <= -8:
            return (f"📉 {progress}% done when you should be at {pace['expected']}% — "
                    f"{abs(pace['gap_days'])} days of slippage with {_period(bd)} left. "
                    f"You are not going to drift back on track. Pick the biggest "
                    f"piece and move it today.", TONE_SCOLD)
        if ratio < 0.85 and gap <= -4:
            return (f"⚠️ Slightly behind: {progress}% against a target of "
                    f"{pace['expected']}%, {_period(bd)} left. One focused session "
                    f"closes this. Do it before it becomes a real gap.", TONE_PUSH)
        if gap >= 15 or (ratio >= 1.25 and gap >= 8):
            return (f"🚀 {progress}% with only {pace['expected']}% expected by now — "
                    f"{_period(bd)} left and you are ahead. Keep this intensity or "
                    f"pull the deadline in.", TONE_CELEBRATE)
        surplus = (f" You have {_hhmm(budget['surplus_minutes'])} of slack — "
                   f"do not spend it all." if budget and budget["surplus_minutes"] else "")
        return (f"✅ On track: {progress}% with {_period(bd)} left.{surplus} "
                f"Same again tomorrow.", TONE_CHEER)

    # ── No start date, so no pace: fall back to the raw countdown ──────
    return (f"🎯 {_period(bd)} left on \"{title}\", {progress}% done. Set a start "
            f"date and a daily commitment and this page can tell you whether "
            f"that is fast enough.", TONE_PUSH)


def _period(bd):
    """The remaining time as a short phrase, matching the big number's unit."""
    if bd["total_seconds"] >= 3 * 604800:
        w = bd["total_seconds"] // 604800
        return f"{w} week{'s' if w != 1 else ''}"
    days = bd["total_days"]
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    hours = bd["total_hours"]
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return "under an hour"

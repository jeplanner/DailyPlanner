"""Parse an inline '@<time> [day]' schedule token out of a Quick Bucket
one-liner.

Examples that match:
    "Call mom @1pm today"      → text "Call mom",  1:00 PM today (IST)
    "Pay rent @13:00"          → text "Pay rent",  1:00 PM today/tomorrow
    "Standup @9:30am tomorrow" → text "Standup",   9:30 AM tomorrow
    "Review @5pm friday"       → text "Review",    5:00 PM next Friday

Times are interpreted in IST (the app's timezone, matching
utils.time_parser). The returned due_at is a UTC ISO string so it drops
straight into quick_bucket.due_at, which the calendar mirror turns into
a popup alarm at T-0.

A bare "@5" (no am/pm, no colon) is deliberately NOT treated as a time,
so an '@' used for any other reason doesn't get eaten.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from utils.time_parser import parse_time_token

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

_WEEKDAYS = {
    "mon": 0, "monday": 0,
    "tue": 1, "tues": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

# @<time>[ <day-word>]. Time chunk is validated below (must carry am/pm
# or a colon) so a lone "@5" isn't silently scheduled.
_AT_RE = re.compile(
    r"@\s*"
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)"
    # Day-word: longest alternatives first + a trailing \b so "tom"
    # can't match inside "tomorrow" (it'd leave an "orrow" fragment).
    r"(?:\s+(today|tonight|tomorrow|tmrw|tom|"
    r"monday|mon|tuesday|tues|tue|wednesday|wed|"
    r"thursday|thurs|thur|thu|friday|fri|saturday|sat|sunday|sun)\b)?",
    re.IGNORECASE,
)


def _resolve_date(word, today):
    """Map a day-word to a date. None ⇒ no day given (caller defaults to
    today, rolling forward if the time already passed)."""
    if not word:
        return None
    w = word.lower()
    if w in ("today", "tonight"):
        return today
    if w in ("tomorrow", "tmrw", "tom"):
        return today + timedelta(days=1)
    if w in _WEEKDAYS:
        delta = (_WEEKDAYS[w] - today.weekday()) % 7
        # "monday" when today is Monday means *next* Monday, not today.
        if delta == 0:
            delta = 7
        return today + timedelta(days=delta)
    return None


def parse_at_schedule(text, now=None):
    """Find an '@<time> [day]' token in `text`.

    Returns (cleaned_text, due_at_utc_iso). When no valid token is
    present, returns (text, None) unchanged.

    `now` (an IST-aware datetime) is injectable for testing.
    """
    now = now or datetime.now(IST)
    m = _AT_RE.search(text)
    if not m:
        return text, None

    time_chunk = m.group(1).strip()
    # Require am/pm or a colon — otherwise it's too ambiguous to eat.
    if not re.search(r"(am|pm|:)", time_chunk, re.IGNORECASE):
        return text, None

    day_word = m.group(2)
    target = _resolve_date(day_word, now.date())
    explicit_day = target is not None
    if target is None:
        target = now.date()

    try:
        dt = parse_time_token(time_chunk, target.isoformat())  # IST-aware
    except ValueError:
        return text, None

    # No explicit day and the time already passed today → roll to
    # tomorrow so the alarm is in the future, not silently in the past.
    if not explicit_day and dt <= now:
        try:
            dt = parse_time_token(
                time_chunk, (target + timedelta(days=1)).isoformat()
            )
        except ValueError:
            return text, None

    due_utc = dt.astimezone(UTC).isoformat()

    cleaned = (text[:m.start()] + text[m.end():])
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    # If the token was the entire message, keep the original text so the
    # task still has a label (the add endpoint rejects empty text).
    cleaned = cleaned or text.strip()
    return cleaned, due_utc

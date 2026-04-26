"""@-tag checklist parser.

Turns lines like:

    - [ ] Buy milk @Tomorrow @Groceries
    - [ ] Standup meeting @RecurrenceDaily @Work
    - [ ] Pay rent @2026-05-01 @RecurrenceMonthly @Bills

into structured task dicts:

    {
        "title": "Buy milk",
        "due_date": date(2026, 4, 27),
        "recurrence_type": None,
        "recurrence_days": None,
        "project_name": "Groceries",
        "raw": "<original line>",
    }

The parser is dumb on purpose — it only recognises a small, well-defined
vocabulary of @-tags. Anything else is treated as a *project name*
candidate, which the caller resolves against the user's projects (with
fallback to a default project).

Recognised tags (case-insensitive, dashes optional):

    @Today                    → due today
    @Tomorrow                 → due tomorrow
    @NextWeek                 → due next Monday
    @YYYY-MM-DD               → due that date
    @DDMmm  / @DD-Mmm         → due that day in current/next year
    @DD/MM   / @DD-MM (-YY)   → due that day
    @RecurrenceDaily          → recurrence: daily
    @RecurrenceWeekly         → recurrence: weekly (today's weekday)
    @RecurrenceMonthly        → recurrence: monthly
    @RecurrenceEvery<Day>     → weekly on the named day
                                (Monday/Mon/Tue/.../Sun)
    @<anythingElse>           → project name candidate

If `recurrence_type` is set without a date, we default `due_date` to
today so the first occurrence has somewhere to land.

Parser is pure (no DB) so it's easy to unit-test.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import List, Optional


WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Reserved date / recurrence keywords (lowercase, no @, no dashes).
_DATE_KEYWORDS = {"today", "tomorrow", "nextweek"}
_RECURRENCE_PREFIXES = ("recurrence",)

# A checklist line has a leading `- [ ]` / `- [x]` (or `* [ ]`); we
# strip it before parsing so the title doesn't include the box.
_CHECKLIST_PREFIX_RE = re.compile(r"^\s*[-*]\s*\[\s*[xX ]?\s*\]\s*")

# Match a single @-tag. We allow letters, digits, dashes, underscores,
# slashes, plus, and dots so things like @Q4-2026 or @2026-05-01 work.
_TAG_RE = re.compile(r"@([A-Za-z0-9][A-Za-z0-9\-_/+.]*)")


@dataclass
class ParsedItem:
    """A single parsed checklist line."""
    title: str
    raw: str
    due_date: Optional[date] = None
    recurrence_type: Optional[str] = None       # daily | weekly | monthly
    recurrence_days: Optional[List[int]] = None # weekday indices for weekly
    project_name: Optional[str] = None          # case-preserved candidate
    # Tags the parser couldn't resolve (kept for visibility / debugging)
    unresolved_tags: List[str] = field(default_factory=list)
    # Was the line already checked off? Lets the UI skip those.
    already_checked: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["due_date"] = self.due_date.isoformat() if self.due_date else None
        return d


# ─── Date-tag parser ─────────────────────────────────────────────


def _try_parse_date(tag: str, today: date) -> Optional[date]:
    """Return the date encoded in `tag`, or None if it isn't a date.

    Supports:
        2026-05-01
        15-May / 15May / 15-May-2026
        15/05 / 15-05 / 15/05/2026
    Two-digit year is interpreted as 20YY. A bare `15-May` rolls forward
    to next year if it's already in the past.
    """
    raw = tag.strip().lower()
    if not raw:
        return None

    # YYYY-MM-DD or YYYY/MM/DD
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # 15-May / 15May / 15May2026
    m = re.fullmatch(r"(\d{1,2})[-/]?([a-z]{3,9})(?:[-/]?(\d{2,4}))?", raw)
    if m:
        day = int(m.group(1))
        mon_key = m.group(2)[:3] if m.group(2) not in MONTHS else m.group(2)
        if mon_key in MONTHS:
            mon = MONTHS[mon_key]
            year = int(m.group(3)) if m.group(3) else today.year
            if 0 <= year < 100:
                year += 2000
            try:
                d = date(year, mon, day)
            except ValueError:
                return None
            # Roll forward if user wrote a bare date that's already past.
            if not m.group(3) and d < today:
                try:
                    d = date(year + 1, mon, day)
                except ValueError:
                    return None
            return d

    # DD/MM or DD-MM (with optional year)
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", raw)
    if m:
        day = int(m.group(1))
        mon = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if 0 <= year < 100:
            year += 2000
        try:
            d = date(year, mon, day)
        except ValueError:
            return None
        if not m.group(3) and d < today:
            try:
                d = date(year + 1, mon, day)
            except ValueError:
                return None
        return d

    return None


# ─── Recurrence-tag parser ───────────────────────────────────────


def _try_parse_recurrence(tag: str):
    """Return (recurrence_type, recurrence_days) if the tag is a
    recurrence keyword, else None.

    Examples:
        recurrencedaily    → ("daily", None)
        recurrenceweekly   → ("weekly", None) — uses today's weekday
        recurrencemonthly  → ("monthly", None)
        recurrenceeveryfri → ("weekly", [4])
        recurrence-every-monday → ("weekly", [0])
    """
    raw = tag.strip().lower().replace("-", "").replace("_", "")
    if not raw.startswith(_RECURRENCE_PREFIXES):
        return None

    body = raw[len("recurrence"):]
    if body == "daily":
        return ("daily", None)
    if body == "weekly":
        return ("weekly", None)
    if body == "monthly":
        return ("monthly", None)
    if body.startswith("every"):
        day_part = body[len("every"):]
        if day_part in WEEKDAYS:
            return ("weekly", [WEEKDAYS[day_part]])
    return None


# ─── Date-keyword parser ─────────────────────────────────────────


def _try_parse_keyword(tag: str, today: date) -> Optional[date]:
    raw = tag.strip().lower().replace("-", "").replace("_", "")
    if raw == "today":
        return today
    if raw == "tomorrow":
        return today + timedelta(days=1)
    if raw == "nextweek":
        # Next Monday — Apple Reminders / GCal default.
        offset = (0 - today.weekday()) % 7 or 7
        return today + timedelta(days=offset)
    return None


# ─── Top-level: parse a single line ──────────────────────────────


def parse_line(line: str, today: date) -> Optional[ParsedItem]:
    """Parse a single checklist line. Returns None if the line has no
    actual title text after stripping markers and tags."""
    if line is None:
        return None
    raw = line.rstrip("\n")
    # Detect already-checked state (`- [x]`) so the UI can skip those.
    already = bool(re.match(r"^\s*[-*]\s*\[\s*[xX]\s*\]", raw))

    # Strip leading `- [ ]` / `- [x]` if present.
    body = _CHECKLIST_PREFIX_RE.sub("", raw).strip()
    if not body:
        return None

    # Walk every @-tag in the line, classify it, and remove it from the
    # title. We process in-place so the title is what's left after.
    due_date: Optional[date] = None
    recurrence_type: Optional[str] = None
    recurrence_days: Optional[List[int]] = None
    project_name: Optional[str] = None
    unresolved: List[str] = []

    def _classify(tag: str) -> bool:
        nonlocal due_date, recurrence_type, recurrence_days, project_name

        # 1. Keyword (@today / @tomorrow / @nextweek)
        kw = _try_parse_keyword(tag, today)
        if kw is not None:
            due_date = kw
            return True

        # 2. Recurrence
        rec = _try_parse_recurrence(tag)
        if rec is not None:
            rt, rd = rec
            recurrence_type = rt
            if rd is not None:
                recurrence_days = rd
            return True

        # 3. Explicit date
        d = _try_parse_date(tag, today)
        if d is not None:
            due_date = d
            return True

        # 4. Project name candidate — first one wins (later @projects
        #    are treated as unresolved so we don't silently swap).
        if project_name is None and not _looks_date_ish(tag):
            project_name = tag
            return True

        unresolved.append(tag)
        return True   # remove from title regardless

    # Find all tags + remove them as we go.
    cleaned = body
    for m in list(_TAG_RE.finditer(body)):
        tag = m.group(1)
        _classify(tag)
        # Remove the entire @tag (with the @) from the cleaned title.
        cleaned = cleaned.replace("@" + tag, "", 1)

    title = re.sub(r"\s+", " ", cleaned).strip(" \t-—,")
    if not title:
        return None

    # Recurrence with no date → first occurrence is today.
    if recurrence_type and not due_date:
        due_date = today

    return ParsedItem(
        title=title,
        raw=raw,
        due_date=due_date,
        recurrence_type=recurrence_type,
        recurrence_days=recurrence_days,
        project_name=project_name,
        unresolved_tags=unresolved,
        already_checked=already,
    )


def _looks_date_ish(tag: str) -> bool:
    """Cheap guard so a literal date like "2026-05-01" (which we should
    have already classified) never falls into the project-name branch."""
    raw = tag.lower()
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", raw):
        return True
    if re.match(r"^\d{1,2}[-/]?[a-z]{3,9}", raw):
        return True
    if re.match(r"^\d{1,2}[/-]\d{1,2}", raw):
        return True
    return False


# ─── Top-level: parse a whole note ───────────────────────────────


def parse_note(content: str, today: date) -> List[ParsedItem]:
    """Find every checklist line in `content` and parse it.

    A "checklist line" is one starting with `- [ ]`, `- [x]`, `* [ ]`,
    etc. Plain bullets without the box are ignored — that keeps regular
    notes from getting accidentally swept into tasks.
    """
    if not content:
        return []
    out: List[ParsedItem] = []
    for raw_line in content.splitlines():
        if not _CHECKLIST_PREFIX_RE.match(raw_line):
            continue
        item = parse_line(raw_line, today)
        if item:
            out.append(item)
    return out

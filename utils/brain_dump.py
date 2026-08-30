"""Read a paragraph of prose and work out which tasks are hiding in it.

WHAT THIS IS FOR
----------------
"Is there a way i can type something like a paragraph. Code can decipher
and create tasks on quickbucket."

The Quick Bucket already accepts a pasted LIST — one item per line — and
that is a fine thing to accept from someone who has already done the work
of making a list. Nobody thinks in lines, though, and nobody dictates in
them: what actually comes out of a head (or a microphone) is

    "I need to call the plumber tomorrow morning, pay the electricity
     bill before Friday, and book the flight — that one is urgent. Also
     spend 30 mins reviewing the deck sometime next week."

which the old capture stored as ONE task with a paragraph for a title.

WHAT IT DOES AND, JUST AS IMPORTANTLY, WHAT IT DOES NOT
------------------------------------------------------
`read_dump()` returns CANDIDATES. It never writes anything, and the page
shows the result as an editable preview before a single row is created.
That is the whole safety model: a parser that guesses is fine as long as
it guesses in front of you. So every candidate carries `why` — the exact
signals that produced its bucket and its time — because a task that
silently acquired a 6am alarm is worse than no parsing at all.

WHY THE RULES COME FIRST AND THE MODEL SECOND
---------------------------------------------
An LLM is genuinely better than a regex at ONE part of this — deciding
where one task ends and the next begins in loose prose. It is not better
at "what time is 'by Friday'", and it cannot be trusted to be consistent
about it from one dump to the next. So the model, when it is used at all
(see services/brain_dump_service.py), is only ever allowed to hand back
task-shaped PHRASES; every phrase it returns is then read by the rules
below, which own every date, bucket and duration. Rules-only still works
with no network, no API key and no cost, which is what runs by default.

READING ORDER OF THE SIGNALS (first match wins, and says so)
-----------------------------------------------------------
    1. a clock time            "at 9:30am", "@1pm tomorrow"   → bucket "at"
    2. a relative deadline     "in 2 hours", "within an hour"  → 15m/2h/…
    3. urgency                 "asap", "right away"            → now
    4. deferral                "next week", "someday"          → future
    5. nothing                                                 → now

Effort ("spend 30 mins", "takes an hour") is read SEPARATELY from all of
those, because how long a thing takes and when it is due are different
questions that English happily expresses with the same words.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from utils.quick_time import parse_at_schedule

IST = ZoneInfo("Asia/Kolkata")

# Mirrors routes.quick_bucket.BUCKETS. Duplicated deliberately: this
# module is pure and must import nothing from the web layer, and a test
# pins the two lists together so they cannot drift.
MIN_BUCKETS = (5, 15, 30, 45)
HOUR_BUCKETS = tuple(range(1, 9))

MAX_ITEMS = 60          # one dump; past this it is a document, not a dump
MAX_TEXT_LEN = 500      # same cap the add endpoint applies


# ── the vocabulary ──────────────────────────────────────────────────
#
# Deliberately a plain list of the verbs a to-do actually starts with,
# not a part-of-speech tagger. The failure mode of a tagger here is that
# it is confidently wrong on fragments ("book flight" — noun or verb?),
# and fragments are the entire input.
ACTION_VERBS = {
    "add", "answer", "apply", "arrange", "ask", "book", "buy", "build",
    "call", "cancel", "change", "check", "clean", "clear", "close",
    "collect", "complete", "confirm", "connect", "cook", "create", "cut",
    "deliver", "deploy", "discuss", "do", "download", "draft", "drop",
    "email", "enter", "fetch", "file", "fill", "find", "finish", "fix",
    "follow", "get", "give", "go", "hand", "help", "install", "invite",
    "join", "learn", "list", "look", "mail", "make", "meet", "message",
    "move", "order", "organise", "organize", "pack", "pay", "phone",
    "pick", "plan", "post", "practice", "practise", "prepare", "print",
    "publish", "push", "read", "rebook", "record", "refill", "register",
    "remind", "renew", "reply", "research", "reserve", "reset", "review",
    "revise", "run", "schedule", "send", "set", "share", "ship", "shop",
    "sign", "sort", "speak", "spend", "start", "study", "submit",
    "sweep", "take", "talk", "test", "text", "tidy", "track", "train",
    "transfer", "update", "upload", "verify", "visit", "wash", "watch",
    "write",
    # Added 2026-08-30 from a real work dump that came back under-split:
    # "reflect feedback", "walk 10am", "pray 10.30" all failed the verb
    # test, and a verb list is only as good as the last list it met.
    "align", "approve", "attend", "brief", "chase", "circulate", "escalate",
    "flag", "forward", "groom", "log", "nudge", "pray", "prep",
    "prioritise", "prioritize", "raise", "reflect", "respond", "sanction",
    "sync", "triage", "walk",
}

# "I need to …" and friends. These are the strongest signal in the whole
# input — someone writing them is stating an obligation — and they are
# also noise in the title, so they are stripped after being counted.
_OBLIGATION_RE = re.compile(
    r"\b(?:i\s+)?(?:need|have|want|ought|going|got|plan|intend)\s+to\b"
    r"|\bi\s+(?:must|should|will|shall)\b"
    r"|\b(?:must|should)\b"
    r"|\bremember\s+to\b|\bdon'?t\s+forget\s+to\b|\bmake\s+sure\s+(?:to|i)\b"
    r"|\bgotta\b|\btodo\b|\bto\s*-?\s*do\b",
    re.IGNORECASE,
)

# Stripped from the FRONT of a title, repeatedly, until nothing matches.
# Order matters only in that the longest phrasing has to be listed before
# the shorter one it contains.
_LEAD_NOISE_RE = re.compile(
    r"^(?:\s*(?:and|also|then|plus|next|after\s+that|so|but|oh|well|"
    r"please|kindly|"
    r"i\s+really\s+need\s+to|i\s+need\s+to|i\s+have\s+to|i\s+want\s+to|"
    r"i\s+would\s+like\s+to|i'?d\s+like\s+to|i\s+must|i\s+should|"
    r"i\s+will|i'?ll|i\s+am\s+going\s+to|i'?m\s+going\s+to|"
    r"we\s+need\s+to|we\s+have\s+to|we\s+should|"
    r"need\s+to|have\s+to|got\s+to|gotta|must|should|"
    r"remember\s+to|remember|don'?t\s+forget\s+to|don'?t\s+forget|"
    r"make\s+sure\s+to|make\s+sure\s+i|make\s+sure|"
    r"todo\s*:?|to\s*-?\s*do\s*:?|task\s*:?|item\s*:?)"
    r"\s*[,:-]?\s+)",
    re.IGNORECASE,
)

_TRAILING_NOISE_RE = re.compile(
    r"[\s,;:.—–-]*\b(?:please|thanks|thank\s+you|okay|ok|etc\.?)\s*$",
    re.IGNORECASE,
)

# Sentences that are ABOUT the day rather than things to do in it. Kept
# in the preview (unticked) rather than deleted, because "feeling awful
# today" is exactly the kind of line a person then wants to turn into
# "book a doctor's appointment" by hand.
_NON_TASK_RE = re.compile(
    r"^(?:i\s*(?:'m|’m)\b"
    r"|i\s+(?:am|was|feel|felt|think|thought|guess|hope|wish)\b"
    r"|it\s+(?:is|'s|was)\b|that\s+(?:is|'s|was)\b|this\s+(?:is|'s|was)\b"
    r"|there\s+(?:is|'s|are|was|were)\b"
    r"|the\s+\w+\s+(?:is|was|were|are|said|told|asked|wants|wanted|"
    r"suggested|mentioned|thinks|reckons)\b)",
    re.IGNORECASE,
)

_WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3,
    "thurs": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_DAY_WORDS = (
    r"today|tonight|this\s+evening|this\s+afternoon|this\s+morning|"
    r"tomorrow|tmrw|tmw|"
    r"monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thur|thu|"
    r"friday|fri|saturday|sat|sunday|sun"
)


# ── 1. segmentation ─────────────────────────────────────────────────

# Full stops that must NOT end a sentence. Protected by swapping the dot
# for \x00 before the split and swapping it back after, which is uglier
# than a lookbehind and, unlike a lookbehind, actually handles "5 p.m.".
_PROTECT = (
    re.compile(r"\b[ap]\.\s?m\.?", re.IGNORECASE),        # a.m. / p.m.
    re.compile(r"\b(?:e\.g|i\.e)\.", re.IGNORECASE),      # e.g. / i.e.
    re.compile(r"\b(?:vs|mr|mrs|ms|dr|prof|sr|jr|st|no)\.", re.IGNORECASE),
    re.compile(r"\d\.\d"),                                # 3.30, 1.5
)

_BULLET_RE = re.compile(r"^\s*(?:[-*•·–—>]+|\d+[.)])\s+")

# " and then ", " then ", " after that " always split. A bare " and "
# splits only when what follows looks like another instruction — see
# _split_on_and — because "call the plumber and the electrician" is one
# task and "call the plumber and pay the bill" is two.
_HARD_CONNECTOR_RE = re.compile(
    r"\s*(?:,\s*)?\b(?:and\s+then|then\s+again|then|after\s+that|"
    r"afterwards|also,|,\s*also|;\s*also|plus,)\b\s*",
    re.IGNORECASE,
)
_AND_RE = re.compile(r"\s*(?:,\s*)?\band\s+(?:also\s+)?", re.IGNORECASE)
# A comma between two instructions is a list. A comma before anything
# else is punctuation — "book the flight, that one is urgent" is one
# task and splitting it loses the reason it is urgent.
# The space after the comma is optional: real typing produces
# "capacity requests,theme review calendar". Digits on both sides are
# excluded so "1,000" survives.
_COMMA_RE = re.compile(r"(?<!\d)\s*,\s*(?!\d)")

# Fragments that continue the sentence they are in rather than starting a
# new item. "book the flight, that one is urgent" must stay one task.
_CONTINUATION_RE = re.compile(
    r"^(?:that|which|who|whom|whose|it|its|it'?s|this|these|those|they|"
    r"he|she|we|i|one|because|since|so|but|though|although|if|when|"
    r"while|where|as|however|especially|mainly|ideally)\b",
    re.IGNORECASE,
)
# " — reply to the recruiter": a dash is a comma with better posture.
_DASH_RE = re.compile(r"\s+[-–—]+\s+")


def _protect_dots(s):
    """Every dot INSIDE a protected token becomes \x00 for the duration of
    the split. Replacing the whole match rather than reassembling it from
    groups is what keeps the trailing dot of "p.m." — losing it turned
    "5 p.m. sharp" into "5 p.m sharp" in the saved title."""
    for rx in _PROTECT:
        s = rx.sub(lambda m: m.group(0).replace(".", "\x00"), s)
    return s


def _restore_dots(s):
    return s.replace("\x00", ".")


_EFFORT_FILLER = {
    "on", "it", "a", "an", "the", "day", "days", "per", "daily", "every",
    "about", "around", "maybe", "perhaps", "probably", "of", "work",
    "each", "also",
}


def _is_only_effort(frag):
    """Is this fragment nothing but "how long"?

    "start the java prep, spend 45 mins a day on it" splits at the comma
    on the strength of the verb "spend", and produces a second task
    called "Spend 45 mins a day on it" — which is not a task, it is the
    first one's estimate. Left attached, the effort reader picks it up
    and puts 45 minutes on the right row.
    """
    left = _DURATION_RE.sub(" ", frag or "")
    words = [w for w in re.findall(r"[a-z0-9]+", left.lower())]
    return bool(words) is False or all(w in _EFFORT_FILLER for w in words)


def _starts_an_instruction(right):
    """Does this fragment begin something you could obey?

    The test a reader applies without noticing: "and pay the bill" does,
    "and the electrician" does not. Exact word, no stemming — "takes an
    hour" must NOT read as the verb "take", or "clean the garage, takes
    an hour" becomes two tasks and one of them is a duration.
    """
    frag = right.strip()
    first = re.split(r"[\s,]+", frag, maxsplit=1)[0].strip(",.;:").lower()
    # "urgent - reply to the recruiter email" is a new item whose first
    # word is a priority, not a verb. Requiring a verb SOMEWHERE keeps
    # "that one is urgent" attached to the task it is about.
    flagged = bool(_URGENT_RE.match(frag) or _DEFER_RE.match(frag)) and any(
        w.strip(",.;:").lower() in ACTION_VERBS for w in frag.split()
    )
    if _is_only_effort(frag):
        return False
    return (
        first in ACTION_VERBS
        or flagged
        or bool(_OBLIGATION_RE.match(frag))
        or bool(_LEAD_NOISE_RE.match(right))
    )


def _is_only_a_marker(frag):
    """Is this fragment nothing but WHEN or HOW URGENT?

    Two real cases, both of which produced a task made of one useless
    word and stole the qualifier from the task it belonged to:

        "urgent - reply to the recruiter email"  → a task called "Urgent"
        "Today - Reflect feedback before 12pm"   → a task called "Today"
    """
    left = _URGENT_RE.sub(" ", frag or "")
    left = _DEFER_RE.sub(" ", left)
    left = _DEFER_DATED_RE.sub(" ", left)
    left = _DAY_BEFORE_RE.sub(" ", left)
    left = _DAYPART_RE.sub(" ", left)
    left = _CLOCK_RE.sub(" ", left)
    left = _CLOCK_BARE_MERIDIEM_RE.sub(" ", left)
    return not re.sub(r"[^a-z0-9]+", "", left, flags=re.IGNORECASE)


def _is_list_item(right):
    """Is the text after this comma another ITEM, rather than more of the
    sentence?

    The verb test alone (see _starts_an_instruction) is right for prose
    and useless for the commonest work dump there is:

        "review deployment exceptions, traffic prioritisation, mail
         regarding capacity requests, theme review calendar"

    Not one of those has a verb, and they are obviously four tasks. What
    separates them from "book the flight, that one is urgent" is that a
    list item is a short noun phrase and a continuation is a clause.

    A ONE-WORD run is deliberately NOT a list: "pick up groceries — milk,
    eggs, bread" is one task with three things in it, and splitting that
    produces three tasks that each mean nothing on their own.
    """
    first = right.split(",")[0].strip(" \t.;:-")
    if not first:
        return False
    if _CONTINUATION_RE.match(first):
        return False
    if _is_only_effort(first) or _is_only_a_marker(first):
        return False
    # "meet Anita, 3pm at the office" — a fragment that opens with a time
    # is the previous item's when, not a new item.
    if _CLOCK_LEAD_RE.match(first):
        return False
    return 2 <= len(first.split()) <= 12


def _split_on(rx, chunk, is_boundary=None):
    """Split on `rx`, but only where a new instruction starts on the right.

    Scans left to right and KEEPS a separator that does not begin an
    instruction, so "buy milk, bread, and pay rent" breaks at the last
    comma rather than the first. Iterative rather than recursive: the
    input is a paste, and a paste can be pathological.
    """
    is_boundary = is_boundary or _starts_an_instruction
    out, buf, rest = [], "", chunk
    while True:
        m = rx.search(rest)
        if not m:
            buf += rest
            break
        left, right = rest[:m.start()], rest[m.end():]
        if (is_boundary(right) and len(right.split()) >= 2
                and (buf + left).strip()
                and not _is_only_a_marker(buf + left)):
            out.append(buf + left)
            buf = ""
        else:
            buf += rest[:m.end()]
        rest = right
    if buf.strip():
        out.append(buf)
    return out or [chunk]


def _split_on_and(chunk):
    return _split_on(_AND_RE, chunk)


# A line that opens with a short label — "Today:", "Work stuff:" — is a
# heading, not a task. Only stripped when the label carries no verb, so
# "Call John: ask about the invoice" keeps its instruction.
_HEADER_RE = re.compile(r"^([^:\n]{1,40}):\s+(?=\S)")


def _strip_header(line):
    m = _HEADER_RE.match(line)
    if not m:
        return line
    label = m.group(1)
    words = [w.strip(",.;:").lower() for w in label.split()]
    if len(words) > 4 or any(w in ACTION_VERBS for w in words):
        return line
    return line[m.end():]


def _clauses(sentence):
    """One sentence → its instructions, splitting only where a new one
    demonstrably begins (see _split_on)."""
    out = []
    for part in _HARD_CONNECTOR_RE.split(sentence):
        for commaed in _split_on(
                _COMMA_RE, part,
                lambda r: _starts_an_instruction(r) or _is_list_item(r)):
            for dashed in _split_on(_DASH_RE, commaed):
                out.extend(_split_on_and(dashed))
    return out


def segment(text):
    """Prose (or a list, or a mix) → the candidate clauses inside it.

    Lines win over sentences: someone who pressed Enter has already told
    us where the boundaries are, and a line ending without a full stop is
    the single most common shape a pasted list has.
    """
    if not text:
        return []
    chunks = []
    for raw_line in str(text).replace("\r\n", "\n").split("\n"):
        line = _strip_header(_BULLET_RE.sub("", raw_line).strip()).strip()
        if not line:
            continue
        protected = _protect_dots(line)
        for sentence in re.split(r"(?<=[.!?;])\s+|\s*\|\s*", protected):
            sentence = _restore_dots(sentence).strip(" \t.;")
            if not sentence:
                continue
            for piece in _clauses(sentence):
                piece = piece.strip(" \t,.;:-")
                if piece:
                    chunks.append(piece)
    return chunks


# ── 2. the signal readers ───────────────────────────────────────────
#
# Every one of these returns (cleaned_text, value, reason) and removes
# only the words it actually used, so what is left is the task title.

_DURATION_RE = re.compile(
    r"\b(?:maybe\s+|perhaps\s+|probably\s+)?"
    r"(?:spend(?:ing)?|takes?|taking|needs?|for|about|around|approx\.?|~)\s*"
    r"(?:me\s+)?(?:another\s+|an\s+|a\s+)?"
    r"(\d+(?:\.\d+)?|an|a|half\s+an)\s*"
    r"(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\b"
    r"(?:\s+(?:on|for|doing|of\s+work))?"
    r"(?:\s+(?:a|per)\s+day|\s+daily|\s+every\s+day|\s+on\s+it|"
    r"\s+of\s+work)*",
    re.IGNORECASE,
)
# "a 30 minute call", "30-min review" — the duration sits in front of
# the noun instead of after the verb.
_DURATION_ADJ_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)[\s-]*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)"
    r"[\s-]+(?=\w)",
    re.IGNORECASE,
)


def _minutes_from(qty, unit):
    unit = unit.lower()
    if isinstance(qty, str):
        q = qty.strip().lower()
        if q in ("a", "an"):
            qty = 1.0
        elif q.startswith("half"):
            qty = 0.5
        else:
            try:
                qty = float(q)
            except ValueError:
                return None
    mins = qty * 60 if unit.startswith("h") else qty
    mins = int(round(mins))
    if mins <= 0 or mins > 60 * 24:
        return None
    return mins


def extract_effort(text):
    """How LONG it takes — never when it is due."""
    m = _DURATION_RE.search(text)
    if m:
        mins = _minutes_from(m.group(1), m.group(2))
        if mins:
            cleaned = (text[:m.start()] + " " + text[m.end():])
            return _tidy(cleaned), mins, f"“{m.group(0).strip()}”"
    m = _DURATION_ADJ_RE.search(text)
    if m:
        mins = _minutes_from(m.group(1), m.group(2))
        if mins:
            # The adjective form describes the task, so the words stay in
            # the title — "30-min review" reads better than "review".
            return text, mins, f"“{m.group(0).strip()}”"
    return text, None, None


_DEADLINE_RE = re.compile(
    r"\b(?:in|within|inside|under)\s+"
    r"(?:the\s+next\s+|the\s+|a\s+|an\s+)?"
    r"(\d+(?:\.\d+)?|half\s+an|couple\s+of|few)?\s*"
    r"(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\b",
    re.IGNORECASE,
)
_EOD_RE = re.compile(
    r"\b(?:by\s+)?(?:end\s+of\s+(?:the\s+)?day|eod|before\s+the\s+day\s+ends)\b",
    re.IGNORECASE,
)


def _bucket_for_minutes(mins):
    """Snap a number of minutes onto the buckets the page actually has.

    Rounds to the NEAREST bucket rather than the next one up: a task due
    "in 20 minutes" put in the 30m bucket has a deadline ten minutes
    after the real one, and a deadline that is quietly generous is not a
    deadline.
    """
    if mins <= 0:
        return "now"
    if mins <= 50:
        return f"{min(MIN_BUCKETS, key=lambda b: abs(b - mins))}m"
    hours = max(1, min(8, int(round(mins / 60.0))))
    return f"{hours}h"


def extract_deadline(text):
    m = _DEADLINE_RE.search(text)
    if m:
        qty = m.group(1) or "1"
        q = qty.strip().lower()
        if q in ("couple of", "few"):
            qty = 2 if q == "couple of" else 3
        mins = _minutes_from(qty, m.group(2))
        if mins:
            cleaned = _tidy(text[:m.start()] + " " + text[m.end():])
            return cleaned, _bucket_for_minutes(mins), f"“{m.group(0).strip()}”"
    m = _EOD_RE.search(text)
    if m:
        cleaned = _tidy(text[:m.start()] + " " + text[m.end():])
        return cleaned, "8h", "“end of day”"
    return text, None, None


_URGENT_RE = re.compile(
    r"\b(?:asap|a\.s\.a\.p|urgent(?:ly)?|immediately|right\s+away|"
    r"straight\s*away|right\s+now|first\s+thing|top\s+priority|"
    r"as\s+soon\s+as\s+possible|today\s+itself)\b",
    re.IGNORECASE,
)
# "Sometime next week" says both things. Read the DATED half first: a
# leftmost-match regex would take "Sometime", leave "next week" stranded
# in the title and lose the only date in the sentence.
_DEFER_DATED_RE = re.compile(
    r"\b(?:some\s*time\s+|some\s*day\s+|maybe\s+)?"
    r"(?:next\s+week|next\s+month|this\s+weekend|next\s+weekend)\b",
    re.IGNORECASE,
)
_DEFER_RE = re.compile(
    r"\b(?:some\s*day|some\s*time|eventually|at\s+some\s+point|"
    r"when\s+i\s+(?:get|have)\s+(?:the\s+)?time|when\s+possible|"
    r"no\s+rush|not\s+urgent|whenever|later\s+on|sooner\s+or\s+later|"
    r"next\s+week|next\s+month|this\s+weekend|next\s+weekend|"
    r"in\s+the\s+coming\s+weeks?|later)\b",
    re.IGNORECASE,
)


def extract_urgency(text):
    m = _URGENT_RE.search(text)
    if not m:
        return text, None, None
    # The word STAYS in the title. "Book the flight (urgent)" carries its
    # own justification; a title with the urgency silently removed and a
    # bucket set instead loses the reason the moment it scrolls past.
    return text, "now", f"“{m.group(0).strip()}”"


def extract_deferral(text, now):
    m = _DEFER_DATED_RE.search(text) or _DEFER_RE.search(text)
    if not m:
        return text, None, None, None
    word = re.sub(r"^(?:some\s*time|some\s*day|maybe)\s+", "",
                  m.group(0).strip().lower())
    due = None
    today = now.date()
    if word == "next week":
        due = today + timedelta(days=7 - today.weekday())
    elif word == "next month":
        due = today + timedelta(days=30)
    elif "weekend" in word:
        ahead = (5 - today.weekday()) % 7 or 7
        if word.startswith("next"):
            ahead += 7
        due = today + timedelta(days=ahead)
    # UNLIKE urgency, these words come OUT of the title. "Sometime next
    # week I want to start the java prep" is a sentence about when;
    # "Start the java prep" with a Future pill and a date is the task,
    # and the words survive in `why` either way.
    cleaned = _tidy(text[:m.start()] + " " + text[m.end():])
    # "Next week sometime start the java prep" carries the vague word AND
    # the dated one. Removing only the half that matched leaves the other
    # stranded at the front of the title.
    other = _DEFER_RE if m.re is _DEFER_DATED_RE else _DEFER_DATED_RE
    cleaned = _tidy(other.sub(" ", cleaned))
    return (cleaned or text), "future", due, f"“{m.group(0).strip()}”"


_IN_DAYS_RE = re.compile(
    r"\b(?:in|within)\s+(\d{1,3}|a|two|three|four|five|six|seven)\s+"
    r"(day|days|week|weeks)\b",
    re.IGNORECASE,
)
_BY_DAY_RE = re.compile(
    r"\b(?:by|before|due(?:\s+on)?)\s+(" + _DAY_WORDS + r")\b",
    re.IGNORECASE,
)
_WORD_NUMS = {"a": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7}


def _resolve_day_word(word, today):
    w = word.lower().replace("  ", " ")
    if w in ("today", "tonight", "this evening", "this afternoon",
             "this morning"):
        return today
    if w in ("tomorrow", "tmrw", "tmw"):
        return today + timedelta(days=1)
    key = w.split()[-1]
    if key in _WEEKDAYS:
        delta = (_WEEKDAYS[key] - today.weekday()) % 7
        return today + timedelta(days=delta or 7)
    return None


def extract_day_deadline(text, now):
    """A DATE with no clock time — "by Friday", "in 3 days".

    Stored in backlog_due (the same column the Backlog page fills), not
    as due_at: due_at is an alarm, and an alarm at midnight for "by
    Friday" is a phone buzzing in the dark for no reason.
    """
    today = now.date()
    m = _IN_DAYS_RE.search(text)
    if m:
        n = _WORD_NUMS.get(m.group(1).lower())
        if n is None:
            try:
                n = int(m.group(1))
            except ValueError:
                n = None
        if n is not None:
            days = n * 7 if m.group(2).lower().startswith("week") else n
            if 0 < days <= 3650:
                cleaned = _tidy(text[:m.start()] + " " + text[m.end():])
                return (cleaned, today + timedelta(days=days),
                        f"“{m.group(0).strip()}”")
    m = _BY_DAY_RE.search(text)
    if m:
        d = _resolve_day_word(m.group(1), today)
        if d:
            return text, d, f"“{m.group(0).strip()}”"
    return text, None, None


# A clock time in ordinary English, normalised into the "@" token that
# utils.quick_time already knows how to resolve. Doing it this way means
# there is ONE implementation of "what does 9:30 tomorrow mean" in the
# codebase, and it is the one the manual "@1pm today" path has been
# using in production since it shipped.
_TAIL = r"(?:\s+(?:in\s+the\s+)?(morning|afternoon|evening|night))?"

# WITH a preposition. Only this form may guess at a bare hour, because
# "by 8" is a time and "8" on its own is a quantity.
_CLOCK_RE = re.compile(
    r"\b(?:at|by|around|@|before|till|until|due\s+by|latest\s+by)\s*"
    r"(\d{1,2})(?:[:.](\d{2}))?\s*"
    r"(a\.?m\.?|p\.?m\.?|o'?clock)?" + _TAIL,
    re.IGNORECASE,
)

# WITHOUT one — "walk 10am today", "pray 10.30 today". People write their
# own day like this constantly and the preposition is the first thing to
# go. It must carry a meridiem or real minutes, or "2 pager BBD Prep"
# becomes an alarm at 2pm.
_CLOCK_BARE_MERIDIEM_RE = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)" + _TAIL,
    re.IGNORECASE,
)
# "10.30" / "10:30" with no am/pm is only read when the clause names a
# day. Alone it is as likely to be a version number or a score.
_CLOCK_BARE_HHMM_RE = re.compile(
    r"\b(\d{1,2})[:.](\d{2})\b()" + _TAIL,
    re.IGNORECASE,
)

# Used by _is_list_item: does this fragment OPEN with a time?
_CLOCK_LEAD_RE = re.compile(
    r"^\s*\d{1,2}(?:[:.]\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|o'?clock)\b"
    r"|^\s*\d{1,2}[:.]\d{2}\b",
    re.IGNORECASE,
)
_DAY_BEFORE_RE = re.compile(r"\b(" + _DAY_WORDS + r")\b", re.IGNORECASE)


def _clock_match(text):
    """The first readable time in the clause, and whether a bare hour may
    be guessed at. Prepositional form first: it is the only one allowed
    to read "by 8", so it must win when both could match."""
    m = _CLOCK_RE.search(text)
    if m:
        return m, True
    m = _CLOCK_BARE_MERIDIEM_RE.search(text)
    if m:
        return m, False
    m = _CLOCK_BARE_HHMM_RE.search(text)
    if m and _DAY_BEFORE_RE.search(text):
        return m, False
    return None, False


def extract_clock(text, now):
    """Read "tomorrow at 9:30am" / "by 5pm friday" / "walk 10am today"."""
    m, may_guess = _clock_match(text)
    if not m:
        return text, None, None, None
    hour = int(m.group(1))
    if hour > 24:
        return text, None, None, None
    minute = m.group(2)
    meridiem = (m.group(3) or "").lower().replace(".", "")
    part = (m.group(4) or "").lower()

    guessed = False
    if meridiem.startswith("a"):
        suffix = "am"
    elif meridiem.startswith("p"):
        suffix = "pm"
    elif part in ("afternoon", "evening", "night"):
        suffix = "pm"
    elif part == "morning":
        suffix = "am"
    elif minute is not None and hour > 12:
        suffix = ""                      # 17:30 — already unambiguous
    elif minute is not None:
        suffix = ""                      # 9:30 — let quick_time decide
    elif not may_guess:
        # A bare "10.30" reached here only because the clause named a day;
        # read it on the 24-hour clock rather than inventing a meridiem.
        suffix = ""
    else:
        # A BARE HOUR IS A GUESS, AND IT SAYS SO. "at 9" is 9am or 9pm
        # and English does not say which. Taking the next 9 o'clock to
        # come round is what a person means often enough to be useful,
        # and the preview shows the resolved time before anything is
        # saved — a wrong guess costs one click, a dropped time costs a
        # missed task.
        suffix = "am" if 6 <= hour <= 11 else "pm"
        guessed = True

    day_word = None
    # SEARCH THE WHOLE CLAUSE. A 24-character window around the time was
    # the first attempt and it missed the commonest phrasing there is —
    # "Tomorrow I have to drop Shreya at school by 8" puts the day nine
    # words away from the clock. One clause is one task, so a day word
    # anywhere in it belongs to this time.
    dm = _DAY_BEFORE_RE.search(text)
    if dm:
        raw = dm.group(1).lower()
        day_word = {"tmrw": "tomorrow", "tmw": "tomorrow",
                    "tonight": "today", "this evening": "today",
                    "this afternoon": "today",
                    "this morning": "today"}.get(raw, raw.split()[-1])

    token = "@" + str(hour) + (f":{minute}" if minute else "") + suffix
    if day_word:
        token += " " + day_word
    _, due = parse_at_schedule(token, now=now)
    if not due:
        return text, None, None, None

    cleaned = _tidy(text[:m.start()] + " " + text[m.end():])
    # Strip the day word too, but only the one we actually consumed.
    if day_word:
        cleaned = _tidy(re.sub(
            r"\b(?:on\s+)?" + re.escape(dm.group(1)) + r"\b", " ", cleaned,
            count=1, flags=re.IGNORECASE))
    said = m.group(0).strip() + ((f" ({dm.group(1)})") if dm else "")
    why = f"“{said}”" + (" — read as the next one round, check it"
                                   if guessed else "")
    return cleaned, due, why, guessed


# "in the evening", "tomorrow morning" — a time with no number in it.
# Read only when no clock was found, and always flagged as a guess: 6pm
# for "evening" is a convention, not a fact the sentence stated.
_DAYPART_HOURS = {"morning": "9am", "afternoon": "2pm",
                  "evening": "6pm", "night": "9pm"}
_DAYPART_RE = re.compile(
    r"\b(?:(this|tomorrow|tonight)\s+)?(?:in\s+the\s+|during\s+the\s+)?"
    r"(morning|afternoon|evening|night)\b",
    re.IGNORECASE,
)


def extract_daypart(text, now):
    """"pick up groceries in the evening" → 6pm, and says it guessed."""
    m = _DAYPART_RE.search(text)
    if not m:
        return text, None, None
    qualifier = (m.group(1) or "").lower()
    part = m.group(2).lower()
    token = "@" + _DAYPART_HOURS[part]
    if qualifier == "tomorrow":
        token += " tomorrow"
    elif qualifier in ("this", "tonight"):
        token += " today"
    else:
        dm = _DAY_BEFORE_RE.search(text)
        if dm:
            word = dm.group(1).lower()
            token += " " + {"tmrw": "tomorrow", "tmw": "tomorrow",
                            "tonight": "today"}.get(word, word.split()[-1])
    _, due = parse_at_schedule(token, now=now)
    if not due:
        return text, None, None
    said = m.group(0).strip()
    return text, due, f"“{said}” — read as {_DAYPART_HOURS[part]}, check it"


# ── 3. titles ───────────────────────────────────────────────────────

def _tidy(s):
    """Collapse what pulling a phrase out of a sentence leaves behind.

    Removing "at 4:30 am tomorrow" from the middle turns "book cab for
    airport at 4:30 am tomorrow, urgent" into "book cab for airport ,
    urgent" — the space before the comma is the tell that a machine
    wrote it."""
    out = re.sub(r"\s{2,}", " ", (s or ""))
    out = re.sub(r"\s+([,;:.!?])", r"\1", out)
    out = re.sub(r"([(\[])\s+", r"\1", out)
    out = re.sub(r"\s+([)\]])", r"\1", out)
    out = re.sub(r"[,;:]\s*(?=[,;:])", "", out)
    return out.strip(" \t,;:-")


_DAYPART_WORDS = r"morning|afternoon|evening|night"
# A LEADING part of the day counts on its own. The clock reader removes
# the day word it used ("Tomorrow"), which turned "Tomorrow morning I
# must drop Shreya at school by 8" into a task called "Morning I must
# drop Shreya at school". The trailing form is deliberately NOT bare —
# "pick up groceries in the evening" reads well and keeping it costs
# nothing, since the resolved time is on the row beside it.
_LEADING_DAY_RE = re.compile(
    r"^(?:on\s+|by\s+)?(?:"
    r"(?:" + _DAY_WORDS + r")\b(?:\s+(?:in\s+the\s+)?(?:" + _DAYPART_WORDS + r"))?"
    r"|(?:in\s+the\s+|this\s+)?(?:" + _DAYPART_WORDS + r")\b"
    r")[\s,:-]*",
    re.IGNORECASE)
_TRAILING_DAY_RE = re.compile(
    r"[\s,:-]*\b(?:on\s+|by\s+)?(?:" + _DAY_WORDS + r")"
    r"(?:\s+(?:in\s+the\s+)?(?:" + _DAYPART_WORDS + r"))?\s*$",
    re.IGNORECASE)


def drop_used_day_word(text):
    """Remove a day word ONLY once its date has been captured elsewhere.

    "Tomorrow I have to drop Shreya at school by 8" should read "Drop
    Shreya at school" in the list — the tomorrow is in the timestamp. But
    a day word that was never resolved has to stay, or the one piece of
    timing information in the sentence disappears with it.
    """
    out = _LEADING_DAY_RE.sub("", text, count=1)
    out = _TRAILING_DAY_RE.sub("", out, count=1)
    return _tidy(out) or text


def clean_title(text):
    """Turn a clause into something worth reading in a list.

    "and also i need to call the plumber" is a faithful record of what
    was said and a terrible thing to see in a bucket at 6pm.
    """
    t = _tidy(text)
    for _ in range(4):
        new = _LEAD_NOISE_RE.sub("", t, count=1)
        if new == t:
            break
        t = _tidy(new)
    t = _tidy(_TRAILING_NOISE_RE.sub("", t))
    t = re.sub(r"^to\s+(?=\w)", "", t, flags=re.IGNORECASE)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t[:MAX_TEXT_LEN]


def looks_like_a_task(clause, title):
    """Is this an instruction, or is it someone thinking out loud?

    Returns (is_task, confidence). Nothing is ever discarded on the
    strength of this — a "no" only means the preview shows the row
    unticked, because the cost of dropping a real task silently is much
    higher than the cost of one unticked line.
    """
    words = re.split(r"[\s,]+", title.strip().lower())
    first = words[0].strip(".,;:!?").rstrip("s") if words and words[0] else ""
    first_full = words[0].strip(".,;:!?").lower() if words and words[0] else ""
    verb_first = first_full in ACTION_VERBS or first in ACTION_VERBS
    obliged = bool(_OBLIGATION_RE.search(clause))
    has_verb = any(
        w.strip(".,;:!?").rstrip("s") in ACTION_VERBS
        or w.strip(".,;:!?") in ACTION_VERBS
        for w in words
    )
    commentary = bool(_NON_TASK_RE.match(clause.strip()))

    if verb_first and not commentary:
        return True, "high"
    if obliged and has_verb:
        return True, "high"
    if obliged or (has_verb and not commentary):
        return True, "medium"
    if commentary:
        return False, "low"
    # A short noun phrase on its own line — "milk", "electricity bill" —
    # is how half of every real list is written. Treat it as a task.
    if len(words) <= 6:
        return True, "medium"
    return False, "low"


# ── 4. the whole thing ──────────────────────────────────────────────

def read_dump(text, now=None):
    """Paragraph in, candidate tasks out. Writes nothing, ever.

    Each candidate is a dict shaped for the preview UI and for
    /api/quick-bucket/bulk:

        text            the cleaned title
        time_bucket     now | 5m | 15m | 30m | 45m | 1h..8h | future | at
        due_at          UTC ISO string, only when a clock time was found
        backlog_due     ISO date, only when a day (not a time) was found
        planned_minutes int, only when an effort phrase was found
        use             whether the preview ticks it by default
        confidence      high | medium | low
        why             the signals that produced the above, verbatim
        source          the clause it came from, for "that's not what I said"
    """
    now = now or datetime.now(IST)
    out = []
    seen = set()

    for clause in segment(text)[:MAX_ITEMS * 3]:
        work = clause
        why = []

        work, minutes, r = extract_effort(work)
        if r:
            why.append(f"{minutes} min of effort from {r}")

        work, due_at, r, guessed = extract_clock(work, now)
        bucket = None
        if due_at:
            bucket = "at"
            why.append(f"scheduled from {r}")
        else:
            work, due_at, r = extract_daypart(work, now)
            if due_at:
                bucket = "at"
                why.append(f"scheduled from {r}")

        if not bucket:
            work, b, r = extract_deadline(work)
            if b:
                bucket = b
                why.append(f"due {b} from {r}")

        if not bucket:
            work, b, r = extract_urgency(work)
            if b:
                bucket = b
                why.append(f"urgent from {r}")

        backlog_due = None
        if not bucket:
            work, b, d, r = extract_deferral(work, now)
            if b:
                bucket, backlog_due = b, d
                why.append(f"deferred from {r}")

        if backlog_due is None:
            work, d, r = extract_day_deadline(work, now)
            if d:
                backlog_due = d
                why.append(f"due {d.isoformat()} from {r}")
                # A date with no clock time is not something to do in the
                # next four hours, unless the words already said it was.
                if not bucket and d > now.date():
                    bucket = "future"

        if due_at or backlog_due:
            work = drop_used_day_word(work)
        title = clean_title(work) or clean_title(clause)
        if not title:
            continue

        is_task, confidence = looks_like_a_task(clause, title)
        if confidence == "low" and (due_at or backlog_due or bucket):
            # It carried a TIME. People do not put deadlines on their
            # feelings — "I should sleep by 10pm" is a task in disguise.
            # A duration alone does not count: "the doctor said to walk 30
            # mins daily" is a fact about advice, not an item for tonight.
            is_task, confidence = True, "medium"

        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        if not bucket:
            bucket = "now"
            why.append("no timing found — defaulted to Now")

        out.append({
            "text": title,
            "time_bucket": bucket,
            "due_at": due_at,
            "backlog_due": backlog_due.isoformat() if backlog_due else None,
            "planned_minutes": minutes,
            "use": is_task,
            "confidence": confidence,
            "why": why,
            "source": clause[:MAX_TEXT_LEN],
        })
        if len(out) >= MAX_ITEMS:
            break

    return out

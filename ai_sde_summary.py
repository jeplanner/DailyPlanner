"""One-line summaries and the must-read / optional split, DERIVED.

Two problems, one cause: 1,120 topics is more than anyone can read, and a
list of 1,120 titles gives no way to decide which ones to skip. So the
page needs both a smaller default set and a way to skim what is outside
it — a title alone tells you a topic exists, not whether you already know
it.

WHY THE SUMMARIES ARE DERIVED, NOT WRITTEN. Writing 1,120 of them is a
content project of the same size as the bank itself, and a hand-written
summary drifts from the entry it summarises the moment either is edited.
This takes the opening sentence of the `answer` the entry already has.
Nothing here invents prose, nothing needs checking for accuracy, and the
summary cannot contradict the topic because it is made of the topic.
Improving an answer improves its summary for free. Same reasoning as
ai_sde_recall.py, which builds the quizzes the same way.

The cost of that choice is honest: an answer that opens with a throat-
clear gets a summary that opens with a throat-clear. In practice they
don't — the bank's answers were written to lead with the thesis, because
that is what makes an answer answerable out loud — and the fix when one
does is to fix the answer, which is the right place for it.

WHY "Must-Know" IS THE LINE. The alternative was the P0-P3 stack rank,
but that ranks the BACKLOG — how much of the syllabus is left, in what
order to work it — while must-read is a question about the INTERVIEW: is
this asked or isn't it. tag_priority is the field that answers that one.
It gives 278 must-read topics against 842 optional, which is the point:
278 is a set you can finish.

NOT A HIERARCHY OF WORTH. Optional here means "skim the summary, open it
if it is new to you", not "ignore". Nothing is hidden and nothing is
deleted — the split is a reading order, which is why the page still
offers All.
"""
import re

import ai_sde_recall

#: The tag_priority value that makes a topic must-read. One value, one
#: rule, stated on the page — a formula combining three fields would be
#: more precise and impossible to explain, and a split nobody can explain
#: gets ignored.
MANDATORY_TAG = "Must-Know"

#: Long enough to say what the topic IS, short enough that forty of them
#: scan as a list rather than as a page of prose. Also the difference
#: between a 64 KB payload and a 135 KB one, which is why the summaries
#: ship on their own endpoint rather than in the list.
SUMMARY_CAP = 150

#: Below this, one sentence has not said anything yet and the second is
#: worth its characters. Above it, the second sentence usually drags in
#: the first bullet of a list and reads as a fragment.
_ENOUGH = 90

_WS = re.compile(r"\s+")
_LEADING_BULLET = re.compile(r"^[\s·•\-\*–—]+")
#: A bullet MARKER is a "·" with whitespace on both sides. Without the
#: whitespace requirement this also matches the dot-product in
#: "p = 1/(1+e^-(w·x+b))", and the summary for logistic regression loses
#: its formula to a rule about list formatting.
_BULLET_HEAD = re.compile(r"^[·•]\s")


def summarise(entry, cap=SUMMARY_CAP):
    """The opening of an entry's answer, flattened to one line.

    The answers are laid out to be READ — bullet lists, hanging indents,
    hard wraps at about 78 columns — so the newlines have to go before
    any of this means anything as a single line.
    """
    text = (entry.get("answer") or "").strip()
    if not text:
        return ""
    text = _WS.sub(" ", _LEADING_BULLET.sub("", text)).strip()

    out = ai_sde_recall.first_sentences(text, count=1, cap=cap)
    if len(out) < _ENOUGH:
        two = ai_sde_recall.first_sentences(text, count=2, cap=cap)
        # Take the second sentence only if it is a sentence. Where the
        # answer opens with a thesis and then a bulleted list, what follows
        # the first full stop is the list's first item, and a summary that
        # trails off into "· STATE — what exactly does dp[i] mean?" reads
        # as truncated rather than as short.
        tail = two[len(out):].strip()
        if tail and not _BULLET_HEAD.match(tail):
            out = two
    return out.strip()


def is_mandatory(entry):
    """Must-read, or optional-and-summarised."""
    return (entry.get("tag_priority") or "") == MANDATORY_TAG


def reading_of(entry):
    """``"must"`` or ``"opt"`` — the key the page filters on."""
    return "must" if is_mandatory(entry) else "opt"


def build(entries, id_of=lambda i, e: f"ai{i}"):
    """``{entry_id: summary}`` for the whole bank.

    Built once by the caller at import: the bank is a static Python
    literal and cannot change between requests, so rebuilding it per
    request would be pure waste.
    """
    return {id_of(i, e): summarise(e) for i, e in enumerate(entries)}


def counts(entries):
    """``{"must": n, "opt": n, "total": n}`` for the section labels.

    The page shows these on the buttons, because "Must read" tells you
    nothing about whether the split helped and "Must read (278)" against
    "Optional (842)" tells you exactly.
    """
    must = sum(1 for e in entries if is_mandatory(e))
    return {"must": must, "opt": len(entries) - must, "total": len(entries)}

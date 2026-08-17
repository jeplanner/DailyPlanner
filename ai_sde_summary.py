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

WHERE THE LINE IS, AND WHY IT MOVED. The first version used tag_priority
alone: must-read meant "Must-Know", the field that answers the question
must-read is actually asking — is this asked in interviews or isn't it —
rather than the P0-P3 stack rank, which ranks the BACKLOG.

That reasoning was right about which field means what and wrong to make
it the only input. "Balanced Binary Tree" is tagged Common and ranked P0,
so it landed in optional; so did Dijkstra, Topological Sort, Union-Find,
Minimum Window Substring, Merge k Sorted Lists and 49 others. P0 is the
bank's own verdict that a topic is the first thing to work on. A P0 in
the pile marked "read this second" is a contradiction, and the reader
finding one there stops trusting the split — which costs more than the
split gains.

So must-read is the UNION: always asked, OR top of the stack rank. Still
two named fields and still one sentence. 332 topics against 788, about
30% of the bank, which is the point — 332 is a set you can finish.

NOT A HIERARCHY OF WORTH. Optional here means "skim the summary, open it
if it is new to you", not "ignore". Nothing is hidden and nothing is
deleted — the split is a reading order, which is why the page still
offers All.
"""
import re

import ai_sde_recall

#: Either of these makes a topic must-read. Two named fields, no weights
#: and no thresholds — a formula would be more precise and impossible to
#: explain, and a split nobody can explain gets ignored.
MANDATORY_TAG = "Must-Know"       # always asked
MANDATORY_PRIORITY = "P0"         # top of the bank's own stack rank

#: What the page prints under the buttons. Kept here rather than in the
#: template so the rule and its explanation cannot drift apart.
RULE_TEXT = ("Always asked in interviews (Must-Know), or top of the stack "
             "rank (P0). Either one is enough.")

#: Long enough to finish the thought, short enough that forty of them
#: still scan as a list. Raised from 150 after a report that summaries
#: were being cut off mid-sentence: at 150, 695 of the 1,120 summaries
#: ended in an ellipsis, which is a worse failure than being slightly
#: long, because a truncated explanation teaches nothing. At 340 with
#: whole-sentence packing (below) it is 5.
SUMMARY_CAP = 340

_WS = re.compile(r"\s+")
_LEADING_BULLET = re.compile(r"^[\s·•\-\*–—]+")
#: A bullet MARKER is a "·" with whitespace on both sides. Without the
#: whitespace requirement this also matches the dot-product in
#: "p = 1/(1+e^-(w·x+b))", and the summary for logistic regression loses
#: its formula to a rule about list formatting.
_BULLET_HEAD = re.compile(r"^[·•]\s")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def summarise(entry, cap=SUMMARY_CAP):
    """The opening of an entry's answer, flattened to one line.

    WHOLE SENTENCES ONLY. The first version took a fixed number of
    sentences and then hard-truncated to the cap, which left 695 of the
    1,120 summaries ending in an ellipsis mid-clause — "it does badly
    on …" teaches nothing and reads as a bug. This instead packs as many
    COMPLETE sentences as fit under the cap and stops, so the summary
    always finishes its thought. Only when a single sentence is longer
    than the cap on its own does it fall back to truncating, which
    happens to 5 entries.

    The answers are laid out to be READ — bullet lists, hanging indents,
    hard wraps at about 78 columns — so the newlines have to go before
    any of this means anything as a single line.
    """
    text = (entry.get("answer") or "").strip()
    if not text:
        return ""
    text = _WS.sub(" ", _LEADING_BULLET.sub("", text)).strip()

    out = ""
    for part in _SENTENCE.split(text):
        part = part.strip()
        # Where the answer stops being prose and becomes a bulleted list,
        # stop with it — a summary trailing off into "· STATE — what does
        # dp[i] mean?" reads as truncated rather than as short.
        if _BULLET_HEAD.match(part) or part.startswith(("·", "•")):
            break
        candidate = f"{out} {part}".strip() if out else part
        if len(candidate) > cap:
            break
        out = candidate

    if not out:                      # one sentence longer than the whole cap
        out = text[:cap].rsplit(" ", 1)[0] + " …"
    return out.strip()


def is_mandatory(entry):
    """Must-read, or optional-and-summarised.

    Either signal is enough. A topic that is always asked belongs in the
    first pass whatever its rank; a topic the bank ranks P0 belongs there
    whatever its tag. Requiring both would have cut the set to 58.
    """
    return ((entry.get("tag_priority") or "") == MANDATORY_TAG
            or (entry.get("priority") or "") == MANDATORY_PRIORITY)


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

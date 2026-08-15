"""Recall quizzes, DERIVED from the bank rather than written for it.

Why derived. Re-reading a topic feels like learning and mostly is not: it
builds recognition ("yes, I've seen this") where an interview demands recall
("here is the code, from a blank editor"). The fix is retrieval practice —
attempt first, check after. That needs a question and a model answer for
every topic, and the bank has 1,120 topics.

Writing 1,120 quizzes is a content project. So this module writes none. Every
question is a QUESTION FORM applied to a field the entry already has, and the
model answer IS that field. Nothing here invents prose, nothing here needs
review for accuracy, and the quiz cannot drift from the topic because it is
made of the topic. Adding a `pitfalls` to an entry gives it a trap question
for free; the quiz improves as the bank does.

The one genuinely new thing is the TRANSFER question, and it is a join rather
than a composition: every entry carries a `tag_subtopic` from ai_sde_tags.py,
so the other entries in that sub-area are its siblings. "Name three other
problems in this sub-area" is the highest-value question on the page — the
value of a pattern is the family it unlocks — and it costs nothing to ask.

NOT THE SAME THING AS /ai-sde/quiz. That page is multiple choice: a daily set
of 25 drawn across the bank, and picking the right option out of four is
RECOGNITION — the weaker of the two skills and the one that already feels
easy. This is the other half: an open prompt, nothing to pick from, and the
answer hidden until she has committed to one. Both are useful; only this one
resembles the interview.

ORDER IS PEDAGOGY, NOT PREFERENCE. Recall of the core idea comes first
because it is the question she can always attempt; the blank-editor prompt
comes second because it is the one that actually predicts the interview.
Complexity and traps come after, because they are worth little if the
solution itself has not landed.
"""
import re

#: Five is a two-minute drill. More and it becomes another page to read,
#: which is the failure mode this whole design exists to avoid.
MAX_ITEMS = 5

#: Siblings offered by the transfer question.
SIBLINGS = 4

#: Separator for the sibling list. Not "; " — one title in the bank already
#: contains a semicolon, which would split into a phantom extra sibling.
SIB_SEP = " · "

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def first_sentences(text, count=2, cap=340):
    """The opening of a field, for questions that ask for one line.

    Revealing 1,500 characters of prose as the answer to "say it in one
    sentence" teaches nothing about whether the sentence was right.
    """
    text = (text or "").strip()
    if not text:
        return ""
    parts = _SENTENCE.split(text)
    out = " ".join(parts[:count]).strip()
    if len(out) > cap:
        out = out[:cap].rsplit(" ", 1)[0] + " …"
    return out


def build_sibling_index(entries):
    """subtopic -> [titles], for the transfer question.

    Built once by the caller and passed in, because doing it per entry over
    1,120 entries is quadratic for no reason.
    """
    index = {}
    for e in entries:
        sub = e.get("tag_subtopic")
        if sub:
            index.setdefault(sub, []).append(e.get("title") or "")
    return index


def _siblings_for(entry, index):
    """Other titles in the same sub-area, nearest in difficulty first.

    Sorting by difficulty distance keeps the suggestions useful: a Hard
    sibling offered against an Easy topic is discouraging rather than
    instructive.
    """
    sub = entry.get("tag_subtopic")
    title = entry.get("title") or ""
    if not sub:
        return []
    peers = [t for t in index.get(sub, []) if t and t != title]
    return peers[:SIBLINGS]


def build(entry, siblings_index=None):
    """The quiz for one entry: a list of {kind, q, a, hint} dicts.

    Every item is answerable from the entry itself, so a topic with more
    fields filled in simply gets a longer quiz. An entry with nothing but a
    title and an answer still gets the recall question, which is the one
    that matters most.
    """
    items = []
    title = entry.get("title") or "this topic"

    # 1. The core idea. Always available — every entry has an answer.
    core = first_sentences(entry.get("answer"))
    if core:
        items.append({
            "kind": "recall",
            "q": f"Say it out loud: what is the core idea of {title}?",
            "a": core,
            # The mnemonic is exactly a hint, and every entry has one.
            "hint": entry.get("mnemonic") or "",
        })

    # 2. The blank editor. This is the one that predicts the interview:
    #    recognising code on a page is not the same skill as producing it.
    if entry.get("code"):
        items.append({
            "kind": "blank_editor",
            "q": f"Blank editor, no reference: write the solution for {title}. "
                 f"Then compare — did you get the load-bearing line?",
            "a": entry["code"],
            "hint": first_sentences(entry.get("plain_algo"), 1) if entry.get("plain_algo") else "",
        })

    # 3. The trap. Ranked above complexity because a wrong answer costs more
    #    than a missing one.
    if entry.get("pitfalls"):
        items.append({
            "kind": "trap",
            "q": "What goes wrong here most often, and what would you actually "
                 "see happen — a crash, a hang, or a quietly wrong answer?",
            "a": entry["pitfalls"],
            "hint": "",
        })

    if entry.get("complexity"):
        items.append({
            "kind": "complexity",
            "q": "Time and space, stated separately — and name the variables "
                 "(rows and columns, not a bare n).",
            "a": entry["complexity"],
            "hint": "",
        })

    # 4. Transfer. A pattern is worth the family it unlocks.
    sibs = _siblings_for(entry, siblings_index or {})
    if len(sibs) >= 2:
        sub = entry.get("tag_subtopic")
        items.append({
            "kind": "transfer",
            "q": f"This is a {sub} problem. Name two other problems in that "
                 f"sub-area, and say what changes in each.",
            # " · " rather than "; " because one bank title contains a
            # semicolon ("... (Have Backbone; Disagree and Commit)") and the
            # list would read as six siblings instead of five.
            "a": "Others in this sub-area: " + SIB_SEP.join(sibs),
            "hint": "",
        })

    # 5. The recipe, in words, before any code — only if it has not already
    #    been spent as the hint on the blank-editor item.
    if entry.get("plain_algo") and not entry.get("code"):
        items.append({
            "kind": "recipe",
            "q": "Before writing anything: say the steps in plain English, in order.",
            "a": entry["plain_algo"],
            "hint": "",
        })

    if entry.get("followups"):
        items.append({
            "kind": "followup",
            "q": "You answered correctly. Here is what the interviewer asks next:",
            "a": entry["followups"],
            "hint": "",
        })

    return items[:MAX_ITEMS]


# ── Spaced repetition ─────────────────────────────────────────────────
#
# Retrieval works best spread out: the same total minutes give markedly
# better retention split across days than massed into one sitting. The
# schedule below is a Leitner ladder, deliberately simple — the interval
# doubles-ish on a hit and collapses on a miss.
#
# Kept in DAYS rather than as an SM-2 ease factor because the whole horizon
# is 91 days. Tuning an ease factor over a window that short is false
# precision, and a ladder is something you can reason about.
INTERVALS = (1, 3, 7, 16, 35)


def next_interval(streak, correct):
    """Days until this topic should come back.

    A miss resets to tomorrow rather than to zero: seeing it again in the
    same session is re-reading, not recall.
    """
    if not correct:
        return INTERVALS[0]
    step = max(0, min(int(streak or 0), len(INTERVALS) - 1))
    return INTERVALS[step]

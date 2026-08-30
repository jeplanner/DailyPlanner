"""Turn a paragraph into Quick Bucket candidates — rules first, model second.

The rules live in `utils.brain_dump` and are the whole feature on their
own: no key, no network, no cost, same answer every time. This module
adds the one thing a model is genuinely better at — finding the seams in
loose prose, especially dictated prose with no punctuation at all —
and then puts what it returns straight back through the rules.

THE MODEL IS NEVER ALLOWED TO DECIDE A TIME.
It returns task-shaped PHRASES and nothing else. Every bucket, alarm,
date and duration is computed afterwards by `read_dump`, which is
deterministic and tested. So the worst a bad model day can do is split a
sentence badly — never book an alarm for the wrong hour, and never
quietly change what "by Friday" means from one dump to the next.

IT ALSO CANNOT INVENT WORK.
Every line it returns must share a real word with what was typed, or it
is dropped. A to-do list that grows tasks nobody wrote is worse than one
that misses a split, because you cannot tell by looking which is which.

AND IT CANNOT LOSE WORK.
The two readings are merged, not swapped: anything the rules found that
the model's version does not cover is added back. A model that returns
three tasks for a five-task paragraph must not be able to delete two.
"""

import logging
import re

from utils.brain_dump import MAX_ITEMS, read_dump

logger = logging.getLogger("daily_plan")

MAX_INPUT = 8000        # a dump, not a document
_MAX_PHRASE = 200

PROMPT = """Split this brain dump into separate to-do items.

RULES:
- One task per line. No numbering, no bullets, no headings, no commentary.
- Use the writer's own words. Do NOT rephrase, expand or invent tasks.
- KEEP every time, date, duration and priority word exactly as written
  ("tomorrow at 9am", "before Friday", "spend 30 mins", "urgent") in the
  line for the task it belongs to.
- If a sentence is a remark and not a task, output it unchanged on its
  own line anyway. Something else decides what to do with it.
- Output nothing except the lines.

BRAIN DUMP:
{text}"""


def _content_words(s):
    return {w for w in re.findall(r"[a-z0-9']{4,}", (s or "").lower())}


def _clean_phrases(raw, source):
    """Whatever the model said → lines we are willing to parse."""
    if not raw or not isinstance(raw, str):
        return []
    if raw.strip().lower().startswith("ai service"):
        return []                              # ai_service's own error string
    source_words = _content_words(source)
    out = []
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:[-*•·]|\d+[.)])\s*", "", line).strip()
        line = line.strip("`").strip()
        if not line or len(line) > _MAX_PHRASE:
            continue
        if line.lower().startswith(("here are", "sure,", "tasks:", "output:")):
            continue
        words = _content_words(line)
        # Nothing in common with the input means it was invented (or it is
        # the model talking to us). Either way it is not the user's task.
        if words and source_words and not (words & source_words):
            continue
        out.append(line)
        if len(out) >= MAX_ITEMS:
            break
    return out


def _key(title):
    return " ".join(sorted(_content_words(title))) or (title or "").lower()


def _covers(a, b):
    """Do these two candidate titles describe the same job?

    Overlap on the content words rather than string equality, because the
    two readings differ exactly where the model tidied the wording, which
    is the case this has to catch.
    """
    wa, wb = _content_words(a), _content_words(b)
    if not wa or not wb:
        return (a or "").strip().lower() == (b or "").strip().lower()
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.6


def _join(*bits):
    said = [b for b in bits if b]
    return " ".join(said) if said else None


def interpret(text, use_ai=False, now=None, ai_call=None):
    """→ (items, used_ai, note). Writes nothing.

    `ai_call` is injectable so the tests can drive the model path without
    a network — the merge and the guards are the part worth testing, and
    they are unreachable if the only way in is a live API key.
    """
    full = text or ""
    text = full[:MAX_INPUT]
    # SAY WHEN NOT ALL OF IT WAS READ. Silently dropping the tail of a
    # long paste is indistinguishable from the parser finding nothing in
    # it, and the missing tasks are the ones at the end.
    cut = (f"Only the first {MAX_INPUT} characters were read."
           if len(full) > MAX_INPUT else None)

    rule_items = read_dump(text, now=now)
    if not use_ai:
        return rule_items, False, cut

    if ai_call is None:
        from services.ai_service import call_ai as ai_call

    try:
        raw = ai_call(PROMPT.format(text=text))
    except Exception:
        logger.exception("brain dump: AI split failed")
        raw = None

    phrases = _clean_phrases(raw, text)
    if not phrases:
        # SAY SO. A silent fall back to the rules is how you end up
        # believing the model is working when the key expired in April.
        return rule_items, False, _join(
            cut, "AI could not be reached — read with the built-in rules.")

    ai_items = read_dump("\n".join(phrases), now=now)
    if not ai_items:
        return rule_items, False, _join(
            cut, "AI returned nothing usable — read with the built-in rules.")

    merged = list(ai_items)
    seen = {_key(i["text"]) for i in ai_items}
    added = 0
    for it in rule_items:
        if _key(it["text"]) in seen:
            continue
        if any(_covers(it["text"], a["text"]) for a in ai_items):
            continue
        merged.append(it)
        seen.add(_key(it["text"]))
        added += 1

    note = None
    if added:
        note = (f"AI found {len(ai_items)}; {added} more kept from the "
                f"built-in rules so nothing was dropped.")
    return merged[:MAX_ITEMS], True, _join(cut, note)

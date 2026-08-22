"""Near-duplicate pairs in ai_sde_bank.py: which one is canonical, and why.

Purely additive, exactly like ai_sde_tags.py.  `apply(entries)` attaches
fields by EXACT TITLE and nothing in ENTRIES is reworded, reordered,
renumbered or dropped.  No entry is ever deleted - the shadowed twin keeps
all of its content and stays fully readable; it is only marked so the study
UI can collapse it and so the effort budget stops counting the same topic
twice.

WHY THIS EXISTS.  ai_sde_tags.py flagged 75 rows, and that set has been
carried as a "dedupe backlog" ever since.  It is not one: 31 of those flags
say "LLD has no TOPIC value", 12 say "pattern entry, not a verbatim
question", 4 are study briefings, and ~9 more are one-off calibration notes.
Only 19 are genuine near-duplicate PAIRS.  Those 19 are the whole backlog and
they are enumerated below.

THE ACTUAL HARM, which is why the pairs matter.  The two halves of a pair
score almost identically, so they land ADJACENT in the stack rank - Bootstrap
at P3 #30 and #31, Bulkhead at #33 and #34, Imputation at #133 and #134,
Read-repair at #197 and #198, Vector database at #54 and #55.  She meets the
same topic twice in a row and pays the prep_minutes twice.

CANONICAL SELECTION RULE, applied in order:
    1. the entry that carries the ten-section deep dive (>=10 examples)
    2. else the entry with more content (len(answer) + len(code))
    3. else the lower priority_rank
Two pairs override the rule and say so in their note.

prep_minutes IS DELIBERATELY NOT MODIFIED.  It feeds the stack-rank score and
the P0-P3 band cut, so zeroing a shadow's minutes would re-band and renumber
the whole bank of 1,120 entries.  Instead every entry gets
`prep_minutes_effective` (0 for a shadow, prep_minutes otherwise) and this
module exposes DEDUPED_PREP_MINUTES next to the bank's TOTAL_PREP_MINUTES.
Nothing existing changes value.

THE "ENTRY ABOVE" FLAGS IN ai_sde_tags.py ARE STALE AND MUST NOT BE TRUSTED.
Four of them say "near-duplicate of the entry above"; the bank was reordered
after those flags were written, so the entry above is now something else
entirely (the DSU flag at index 32 points at "Linked Lists", the more-data
flag at 462 points at "Design a Lead Scoring system").  Every pair below was
re-resolved BY CONTENT, not by position - the same positional-id trap that
made the study progress table key on title.
"""

#: shadow title -> (canonical title, note).  The shadow keeps its content;
#: the canonical is the one the study page should send her to.
DUPES = {
    "Bootstrap (sampling)": (
        "Bootstrap sampling",
        "Both carry the deep dive; canonical has the fuller answer (310 vs 271)."),
    "Bulkhead pattern": (
        "Bulkhead isolation",
        "Both carry the deep dive; canonical has the fuller answer (450 vs 435)."),
    "Confusion Matrix (from scratch)": (
        "Confusion matrix from scratch",
        "Both deep; canonical carries more code (630 vs 501)."),
    "Design a Fraud Detection System": (
        "Design a Fraud / Payment-Risk Detection system",
        "Both deep; canonical answer is 1129 chars against 728."),
    "Design a YouTube-style Video Recommendation System": (
        "Design a Video Recommendation system (YouTube-style)",
        "Both deep, but the shadow's answer is a 150-char stub against 1067."),
    "Imputation": (
        "Imputation strategies",
        "Neither has a deep dive; canonical answer 345 vs 277."),
    "Health check (liveness vs readiness)": (
        "Liveness vs readiness probes",
        "Neither deep; canonical answer 548 vs 364."),
    "LoRA (Low-Rank Adaptation)": (
        "LoRA / PEFT",
        "Both deep; canonical answer 364 vs 256 and names PEFT, which is asked."),
    "Min-Max Scaler (from scratch)": (
        "Min-max scaling (numpy)",
        "Neither deep; canonical carries more code (492 vs 322)."),
    "Precision, recall, F1 from a confusion matrix (numpy)": (
        "Precision, Recall & F1 (from scratch)",
        "Canonical is the only one of the two with the ten-section deep dive."),
    "Read-repair": (
        "Read repair and anti-entropy",
        "Neither deep; canonical answer 559 vs 359 and covers anti-entropy too."),
    "TF-IDF from scratch (numpy)": (
        "TF-IDF (from scratch)",
        "Neither deep; canonical marginally fuller in both answer and code."),
    "Union-Find / Disjoint Set Union (DSU)": (
        "Union-Find (Disjoint Set Union)",
        "Both deep and both P0; canonical has 611+866 chars against 369+797."),
    "Vector database / ANN": (
        "Vector database",
        "Both deep; canonical answer 345 vs 258."),
    "Why do Transformers need positional encoding when RNNs don't?": (
        "Why do Transformers need positional encodings but RNNs don't?",
        "The singular/plural pair. Both deep; canonical answer 542 vs 514."),
    "Why does more data usually beat a cleverer algorithm?": (
        "Why does more/better data often beat a fancier algorithm?",
        "Both deep; canonical answer 601 vs 504."),
    "Why do we need a separate validation set AND a test set?": (
        "Why split data into train / validation / test — why not just train and test?",
        "Both deep; canonical answer 604 vs 440 and asks the fuller question."),
    "Few-shot vs zero-shot learning": (
        "Zero-shot / few-shot / in-context learning",
        "RULE OVERRIDDEN. The shadow has the longer answer (349 vs 287), but the "
        "canonical's scope is a strict superset - it also covers in-context "
        "learning, which is asked by name. Breadth beats 62 characters."),
}

#: Pairs that CANNOT be collapsed mechanically, because the rule would shadow
#: the richer entry.  Left as a genuine open item rather than resolved badly.
MERGE_PENDING = {
    "Why gradient-boosted trees still beat deep learning on tabular data": (
        "If deep learning is so powerful, why do gradient-boosted trees still win on tabular data?",
        "The rule picks the canonical (it has the ten-section dive; the shadow "
        "has none) - but the shadow holds 1868 chars of answer and 2738 of "
        "measured numpy code against the canonical's 533, and that measurement "
        "is the better teaching material. Collapsing either way destroys the "
        "good half. Needs a real content MERGE: fold the shadow's measured "
        "GBT-vs-MLP demonstration into the canonical's deep dive, then shadow "
        "it. Not done - flagged honestly rather than resolved wrongly."),
}


def apply(entries):
    """Attach duplicate fields in place. Returns (shadows, canonicals, pending).

    Adds to every entry:
        prep_minutes_effective  0 on a shadow, else prep_minutes
    Adds to a shadow:
        duplicate_of            canonical title
        duplicate_note          why that side won
    Adds to a canonical:
        duplicate_titles        list of titles it supersedes
    Adds to both halves of a pending pair:
        duplicate_merge_pending the other title
    """
    by_title = {e["title"]: e for e in entries}
    shadows = canonicals = pending = 0

    for e in entries:
        e["prep_minutes_effective"] = e.get("prep_minutes", 0)

    for shadow, (canonical, note) in DUPES.items():
        s = by_title.get(shadow)
        c = by_title.get(canonical)
        if s is None or c is None:
            continue
        s["duplicate_of"] = canonical
        s["duplicate_note"] = note
        s["prep_minutes_effective"] = 0
        c.setdefault("duplicate_titles", []).append(shadow)
        shadows += 1

    for e in entries:
        if e.get("duplicate_titles"):
            canonicals += 1

    for a, (bt, note) in MERGE_PENDING.items():
        ea, eb = by_title.get(a), by_title.get(bt)
        if ea is None or eb is None:
            continue
        ea["duplicate_merge_pending"] = bt
        eb["duplicate_merge_pending"] = a
        ea["duplicate_note"] = eb["duplicate_note"] = note
        pending += 1

    return shadows, canonicals, pending


def validate(entries=None):
    """Raise on a mis-keyed title, a self-reference, or a shadow-of-a-shadow.

    A mis-keyed title silently does nothing at all - the same trap the _EX_*
    dicts and ai_sde_tags.py both hit - so it is checked explicitly.
    """
    problems = []
    titles = {e["title"] for e in entries} if entries is not None else None

    for shadow, (canonical, note) in DUPES.items():
        if shadow == canonical:
            problems.append("%r is its own canonical" % shadow)
        if canonical in DUPES:
            problems.append("%r points at %r, which is itself a shadow"
                            % (shadow, canonical))
        if not note.strip():
            problems.append("%r has no note explaining the choice" % shadow)
        if titles is not None:
            if shadow not in titles:
                problems.append("shadow %r matches no entry" % shadow)
            if canonical not in titles:
                problems.append("canonical %r matches no entry" % canonical)

    for a, (bt, _note) in MERGE_PENDING.items():
        if a in DUPES or bt in DUPES:
            problems.append("%r is both merge-pending and collapsed" % a)
        if titles is not None:
            for t in (a, bt):
                if t not in titles:
                    problems.append("merge-pending %r matches no entry" % t)

    if problems:
        raise ValueError("ai_sde_dupes: %d problem(s):\n  %s"
                         % (len(problems), "\n  ".join(problems)))
    return True

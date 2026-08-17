"""Must-read / optional, and the one-line summaries that make the
optional half skimmable.

The point of both is the same: 1,120 topics is more than anyone can read,
and a list of 1,120 titles gives no way to decide what to skip. The split
shrinks the default set; the summary is what lets skipping a topic be a
decision rather than an oversight.

The size assertions here are load-bearing. The whole reason the summaries
live on their own endpoint is that folding them into the list more than
doubles the payload page load waits on — a regression that would be
invisible except as a slower page.
"""
import gzip
import json
import re

import pytest

import ai_sde_summary as S
from ai_sde_bank import ENTRIES


def _json(resp):
    data = resp.get_data()
    if resp.headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return json.loads(data)


# ── the summaries themselves ─────────────────────────────────────────

def test_every_entry_gets_a_summary():
    """A summary missing on some rows is worse than none on any: the eye
    reads the gap as "nothing to say about this one"."""
    out = S.build(ENTRIES)
    assert len(out) == len(ENTRIES)
    empty = [k for k, v in out.items() if not v.strip()]
    assert not empty, f"{len(empty)} topics have no summary, e.g. {empty[:3]}"


def test_a_summary_is_one_line_and_stays_bounded():
    """Forty of these have to scan as a LIST, so the length is capped at
    the source rather than clamped in CSS — the card shows all of it."""
    for i, e in enumerate(ENTRIES):
        s = S.summarise(e)
        assert "\n" not in s, e["title"]
        assert len(s) <= S.SUMMARY_CAP + 2, (e["title"], len(s))   # +2 for the " …"
        assert s == s.strip()


def test_summaries_finish_their_sentence():
    """Reported as summaries being cut off. At a 150-character hard cap,
    695 of the 1,120 ended in an ellipsis mid-clause — "it does badly
    on …" — which teaches nothing and reads as a bug.

    Packing WHOLE sentences under the cap fixes it for all but the
    handful whose first sentence is longer than the cap on its own."""
    truncated = [e["title"] for e in ENTRIES if S.summarise(e).endswith("…")]
    assert len(truncated) <= 15, (
        f"{len(truncated)} summaries end mid-sentence: {truncated[:5]}")
    # And the specific entry that was reported.
    bv = next(e for e in ENTRIES if e["title"].startswith("Bias-Variance"))
    s = S.summarise(bv)
    assert not s.endswith("…"), s
    assert "overfitting" in s, "the summary stops before it reaches the second half"


def test_a_summary_does_not_trail_off_into_a_bullet_list():
    """The answers are laid out for reading, so what follows the first full
    stop is often the list's first item, not a second sentence. Trailing
    off into "· STATE — what exactly does dp[i] mean?" reads as truncated
    rather than as short.

    A bullet MARKER has whitespace on both sides. Matching a bare "·"
    would also catch the dot-product in "p = 1/(1+e^-(w·x+b))" and cost
    logistic regression its formula — which is what the first version of
    both this test and the module did."""
    for e in ENTRIES:
        s = S.summarise(e)
        assert not re.search(r"\s[·•]\s", s), (e["title"], s)


def test_a_short_first_sentence_still_gets_a_second():
    """One sentence is the default, but "Two pointers." on its own says
    nothing — the second sentence is worth its characters when the first
    has not landed yet."""
    short = {"answer": "Cache the result. It turns the repeated subproblem "
                       "into a lookup, which is what makes the recursion "
                       "linear instead of exponential."}
    out = S.summarise(short)
    assert out.startswith("Cache the result.")
    assert "lookup" in out, "a too-short first sentence was left on its own"
    # ...but a bulleted list head is not a second sentence.
    bulleted = {"answer": "Say four things out loud.\n\n· STATE — what does dp[i] mean?"}
    assert S.summarise(bulleted) == "Say four things out loud."


def test_the_summary_is_derived_from_the_answer_not_invented():
    """Nothing here writes prose. That is what makes 1,120 of them
    possible and what stops one contradicting its own topic."""
    for e in ENTRIES[:120]:
        s = S.summarise(e).rstrip(" …")
        flat = re.sub(r"\s+", " ", e["answer"]).strip()
        head = s.split("·")[0].strip()[:60]
        assert head and head in flat, (e["title"], head)


# ── the split ────────────────────────────────────────────────────────

def test_the_split_is_two_named_fields_either_of_which_is_enough():
    """No weights, no thresholds — a formula would be more precise and
    impossible to explain, and a split nobody can explain gets ignored."""
    assert S.MANDATORY_TAG == "Must-Know"
    assert S.MANDATORY_PRIORITY == "P0"
    for e in ENTRIES:
        expected = (e.get("tag_priority") == "Must-Know"
                    or e.get("priority") == "P0")
        assert S.is_mandatory(e) == expected, e["title"]
        assert S.reading_of(e) in ("must", "opt")


def test_no_p0_topic_is_filed_as_optional():
    """The bug this rule was changed for. "Balanced Binary Tree" is tagged
    Common and ranked P0, so the tag-only rule filed it under "read this
    second" — along with Dijkstra, Topological Sort, Union-Find, Minimum
    Window Substring and 50 others.

    P0 is the bank's own verdict that a topic is the FIRST thing to work
    on. A P0 in the optional pile is a contradiction, and a reader who
    finds one there stops trusting the split, which costs more than the
    split gains."""
    stranded = [e["title"] for e in ENTRIES
                if e.get("priority") == "P0" and S.reading_of(e) != "must"]
    assert not stranded, f"{len(stranded)} P0 topics are optional: {stranded[:5]}"
    # The specific one that was reported.
    bbt = next(e for e in ENTRIES if e["title"] == "Balanced Binary Tree")
    assert S.reading_of(bbt) == "must"


def test_every_always_asked_topic_is_must_read():
    """The other half of the union — a topic that is always asked belongs
    in the first pass whatever its rank. Requiring BOTH signals instead of
    either would have cut the set from 332 to 58."""
    for e in ENTRIES:
        if e.get("tag_priority") == "Must-Know":
            assert S.reading_of(e) == "must", e["title"]


def test_the_must_read_set_is_small_enough_to_finish():
    """332 against 788 — about 30% of the bank. If "must read" were most of
    it, this would not be a split, it would be a relabelling."""
    c = S.counts(ENTRIES)
    assert c["must"] + c["opt"] == c["total"] == len(ENTRIES)
    assert c["must"] < c["total"] * 0.4, c
    assert c["must"] > 100, "a must-read set this small is hiding the syllabus"


def test_nothing_is_dropped_by_the_split():
    """Optional means "second", not "gone"."""
    must = {e["title"] for e in ENTRIES if S.reading_of(e) == "must"}
    opt = {e["title"] for e in ENTRIES if S.reading_of(e) == "opt"}
    assert not (must & opt)
    assert len(must | opt) == len({e["title"] for e in ENTRIES})


# ── the endpoints ────────────────────────────────────────────────────

def test_the_summaries_have_their_own_endpoint(auth_client):
    d = _json(auth_client.get("/api/ai-sde/summaries"))
    assert d["total"] == len(ENTRIES)
    assert d["summaries"]["ai0"]
    assert isinstance(d["summaries"]["ai0"], str)


def test_the_summaries_stay_out_of_the_list_payload(auth_client):
    """THE reason they are a second request. In the list they take it from
    57 KB gzipped to 135 KB — more than doubling what first paint waits
    on, for a line she may not read on most rows."""
    d = _json(auth_client.get("/api/ai-sde"))
    for e in d["entries"]:
        assert "summary" not in e
    gz = len(auth_client.get("/api/ai-sde",
                             headers={"Accept-Encoding": "gzip"}).get_data())
    assert gz < 120 * 1024, f"list payload back up to {gz/1024:.0f} KB"


def test_the_summaries_payload_is_worth_deferring_but_not_huge(auth_client):
    gz = len(auth_client.get("/api/ai-sde/summaries",
                             headers={"Accept-Encoding": "gzip"}).get_data())
    # Raised from 90 KB when SUMMARY_CAP went 150 -> 340 to stop summaries
    # being cut off mid-sentence. This payload is DEFERRED — it is fetched
    # after the list has rendered — so it costs nothing that first paint
    # waits on, which is what makes the trade acceptable. The list itself
    # is still held under 120 KB by the test above.
    assert gz < 150 * 1024, f"summaries {gz/1024:.0f} KB — shorten SUMMARY_CAP"


def test_the_list_ships_the_split_rule_not_a_second_field(auth_client):
    """The page filters on tag_priority and priority, both of which every
    row already carries. Shipping a per-entry "reading" field would add
    1,120 copies of a value derivable from two it already has."""
    d = _json(auth_client.get("/api/ai-sde"))
    assert d["reading"]["mandatory_tag"] == S.MANDATORY_TAG
    assert d["reading"]["mandatory_priority"] == S.MANDATORY_PRIORITY
    assert d["reading"]["rule"] == S.RULE_TEXT
    assert d["reading"]["counts"] == S.counts(ENTRIES)
    for e in d["entries"]:
        assert "reading" not in e


# ── the page ─────────────────────────────────────────────────────────

def test_the_page_opens_on_the_must_read_set(auth_client):
    """A default nobody chose is the one that decides what it feels like
    to open the page, and 1,120 rows on first paint is what made this one
    overwhelming."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert 'data-reading="must"' in html and 'data-reading="opt"' in html
    assert 'let reading = "must";' in html, "the page no longer defaults to must-read"
    # BOTH halves of the rule come from the server, so the page and the
    # module cannot disagree about what must-read means. Taking only the
    # tag is exactly how "Balanced Binary Tree" ended up optional.
    assert "BANK.reading.mandatory_tag" in html
    assert "BANK.reading.mandatory_priority" in html
    assert "e.priority === MANDATORY_PRI" in html, (
        "the page checks the tag but not the rank — P0 topics will read as optional")
    # And the card says which section it is in. The frequency chip beside
    # it says "Common", which is the vocabulary the rule is written in,
    # not the answer to "must I read this?".
    assert 'class="q-read read-' in html
    assert "📕 Must read" in html and "📗 Optional" in html
    # Summaries are fetched after the list, not with it.
    assert '/api/ai-sde/summaries' in html
    assert 'class="q-sum"' in html


def test_showing_everything_still_shows_the_split(auth_client):
    """With a section selected the list IS that section, so a heading would
    only repeat the pressed button. Showing everything is the case that
    needs them, or the split stops being visible at all."""
    html = auth_client.get("/ai-sde").get_data(as_text=True)
    assert "Optional reading" in html and "Must read" in html
    assert 'class="rung"' in html


# ── Java chip alignment ──────────────────────────────────────────────

def test_java_chips_line_up_between_cards(auth_client):
    """Plan, difficulty, trap and deep dive trailed a flex:1 title as plain
    flex children, so where each landed depended on how long that card's
    title happened to be — and titles here run to 83 characters.

    44 of the 45 entries have a trap. The one that does not was enough to
    slide deep-dive into trap's column, which is why every slot is emitted
    even when it is empty."""
    html = auth_client.get("/java").get_data(as_text=True)
    rule = re.search(r"\.q-head \.q-chips\{[^}]*\}", html).group(0)
    assert "display:grid" in rule and "grid-template-columns" in rule, rule
    cols = re.search(r"grid-template-columns:([^;}]+)", rule).group(1)
    assert "auto" not in cols and "max-content" not in cols, cols
    assert len(cols.split()) == 4, f"one track each for Plan/difficulty/trap/deep: {cols}"
    # The empty-slot placeholder is what holds a column when a chip is absent.
    assert "function slot(" in html
    assert 'e.has_trap ? chip("trap", "trap") : ""' in html

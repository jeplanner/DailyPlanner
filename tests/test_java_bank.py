"""Structural tests for java_bank.py.

These are not "does the module import" tests. Each one guards an invariant
that makes the FORMAT worth having — an entry violating any of them is not
untidy, it is unusable for the drill it was written for:

  * an entry with code and no stated output cannot be used for the
    predict-the-output drill, which is the whole point of a language bank;
  * a quiz whose explanation names only the correct option teaches nothing
    about why the distractors are tempting;
  * an explanation that labels options by number while the renderer labels
    them A-D points the reader at the wrong option, which is worse than
    saying nothing.
"""
import re

import java_bank as bank


def test_self_check_is_clean():
    problems = bank.self_check()
    assert problems == [], "java_bank self-check failures:\n  " + "\n  ".join(problems)


def test_every_entry_has_plain_english_first():
    """`plain` is required by Q() — this guards against it being padded out
    with the jargon it exists to avoid."""
    jargon = ("polymorphi", "invokevirtual", "bytecode", "erasure",
              "amortized", "IEEE 754", "JLS")
    for e in bank.ENTRIES:
        assert e["plain"].strip(), e["title"]
        # The plain answer may NAME a term, but the setup entry is the only
        # place a mechanism word belongs in it.
        if e["cat"] != "setup":
            hits = [w for w in jargon if w.lower() in e["plain"].lower()]
            assert not hits, f"{e['title']!r}: jargon in the plain answer: {hits}"


def test_code_always_has_a_stated_output():
    for e in bank.ENTRIES:
        if e["code"]:
            assert e["output"].strip(), f"{e['title']!r} has code but no output"


def test_quiz_distractors_are_explained():
    for e in bank.ENTRIES:
        q = e.get("quiz")
        if not q:
            continue
        assert len(q["options"]) == 4, e["title"]
        assert q["answer"] == 0, (
            f"{e['title']!r}: author the correct option first; presented_quiz shuffles")
        pairs = re.findall(r"Options? ([A-D])(?: and ([A-D]))?", q["why"])
        named = {x for pair in pairs for x in pair if x}
        assert len(named) >= 3, (
            f"{e['title']!r}: the explanation names only {sorted(named)} — it must "
            f"say why the distractors are wrong")
        assert not re.search(r"Option \d", q["why"]), (
            f"{e['title']!r}: label options by LETTER; the renderer shows A-D")


def test_presented_quiz_shuffles_and_relabels_consistently():
    """The shuffle must move the answer AND rewrite the letters in `why`,
    or the explanation points at the wrong option."""
    positions = set()
    for e in bank.ENTRIES:
        if not e.get("quiz"):
            continue
        shown = bank.presented_quiz(e)
        authored = e["quiz"]
        positions.add(shown["answer"])
        # the option text at the new index is still the authored correct one
        assert shown["options"][shown["answer"]] == authored["options"][authored["answer"]]
        # every option survives exactly once
        assert sorted(shown["options"]) == sorted(authored["options"])
        # the explanation names the NEW letter of the correct option
        assert f"Option {chr(65 + shown['answer'])}" in shown["why"], e["title"]
    assert len(positions) >= 3, (
        "the correct answer lands in too few distinct positions — a student "
        "would learn the position rather than the material")


def test_presented_quiz_is_stable():
    """Same entry, same layout, every time — she should not be re-learning a
    shuffled page on each reload."""
    for e in bank.ENTRIES:
        if e.get("quiz"):
            assert bank.presented_quiz(e) == bank.presented_quiz(e)


def test_recall_leads_with_predict_the_output():
    """Order is pedagogy: for a LANGUAGE bank the predict-the-output prompt is
    the one that most resembles the interview and least resembles re-reading,
    so it must come first wherever there is code."""
    for e in bank.ENTRIES:
        items = bank.recall_for(e)
        if e["output"].strip():
            assert items and items[0]["kind"] == "output", e["title"]
        assert len(items) <= bank.MAX_RECALL_ITEMS


def test_deep_dive_sections_are_the_full_ten():
    for e in bank.ENTRIES:
        if e["examples"]:
            assert len(e["examples"]) == 10, e["title"]
            for i, sec in enumerate(e["examples"], 1):
                assert sec.lstrip().startswith(f"{i}."), (e["title"], i)


def test_categories_are_a_teaching_ladder():
    assert list(bank.CATEGORIES) == bank.CATEGORY_ORDER
    for e in bank.ENTRIES:
        assert e["cat"] in bank.CATEGORIES, e["title"]


def test_render_produces_something_readable():
    text = bank.render(bank.ENTRIES[0])
    assert "IN PLAIN ENGLISH" in text
    assert "RECALL DRILL" in text
    assert len(text.splitlines()) > 20


# ── deep dives ──────────────────────────────────────────────────────────
import java_bank_deep


def test_deep_dives_are_attached():
    attached = {e["title"] for e in bank.ENTRIES if e["examples"]}
    for title in java_bank_deep.DEEP:
        assert title in attached, f"{title!r} declared a deep dive but has none attached"


def test_deep_dive_titles_must_match_an_entry():
    """A silent no-op here would mean renaming an entry quietly detaches its
    deep dive, and nobody would notice until the card was opened."""
    import pytest
    with pytest.raises(KeyError):
        java_bank_deep.apply([{"title": "no such entry", "examples": []}])


def test_deep_dives_are_ten_numbered_sections():
    for title, sections in java_bank_deep.DEEP.items():
        assert len(sections) == 10, title
        for i, sec in enumerate(sections, 1):
            assert sec.lstrip().startswith(f"{i}."), (title, i)
            assert len(sec) > 400, f"{title} section {i} is too thin to be a deep dive"


def test_deep_dives_stay_out_of_the_list_payload():
    """The thin-list split is the reason a 23,000-character deep dive can be
    added without touching page-load weight."""
    import routes.java_prep as jp
    for row in jp._LIST:
        assert "examples" not in row
        assert "answer" not in row

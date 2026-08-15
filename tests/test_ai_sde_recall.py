"""The derived recall quiz.

The point of these tests is that the quiz is DERIVED, never authored: every
question is a form applied to a field the entry already has, and the model
answer is that field. So the things worth pinning are coverage (no topic is
left without a quiz), honesty (the answer really is the entry's own text),
and the schedule.
"""
import gzip
import json

import ai_sde_recall as R
from ai_sde_bank import ENTRIES

SIBS = R.build_sibling_index(ENTRIES)


def test_every_topic_in_the_bank_gets_a_quiz():
    """1,120 topics. A topic with no quiz is a topic she cannot drill."""
    empty = [e["title"] for e in ENTRIES if not R.build(e, SIBS)]
    assert not empty, f"{len(empty)} topics have no quiz, e.g. {empty[:3]}"


def test_the_quiz_is_capped_so_it_stays_a_drill():
    assert all(len(R.build(e, SIBS)) <= R.MAX_ITEMS for e in ENTRIES)


def test_every_answer_is_the_entry_s_own_text():
    """Nothing here may invent content — that is the whole design. Each
    answer must be traceable to a field on the entry."""
    for e in ENTRIES[:200]:
        for item in R.build(e, SIBS):
            a = item["a"]
            if item["kind"] == "transfer":
                assert a.startswith("Others in this sub-area:")
                continue
            if item["kind"] == "recall":
                # Trimmed to the opening sentences, so it is a prefix.
                assert a.rstrip(" …")[:60] in e["answer"], e["title"]
                continue
            source = {"blank_editor": "code", "trap": "pitfalls",
                      "complexity": "complexity", "recipe": "plain_algo",
                      "followup": "followups"}[item["kind"]]
            assert a == e[source], f"{e['title']}: {item['kind']} drifted from {source}"


def test_the_hardest_question_comes_from_the_code_and_only_when_there_is_code():
    withcode = [e for e in ENTRIES if e.get("code")]
    without = [e for e in ENTRIES if not e.get("code")]
    assert any(i["kind"] == "blank_editor" for i in R.build(withcode[0], SIBS))
    assert not any(i["kind"] == "blank_editor" for i in R.build(without[0], SIBS))


def test_recall_comes_first_because_it_is_the_one_she_can_always_attempt():
    for e in ENTRIES[:50]:
        assert R.build(e, SIBS)[0]["kind"] == "recall"


def test_transfer_names_real_siblings_and_never_the_topic_itself():
    titles = {e["title"] for e in ENTRIES}
    checked = 0
    for e in ENTRIES:
        for item in R.build(e, SIBS):
            if item["kind"] != "transfer":
                continue
            checked += 1
            names = item["a"].split(":", 1)[1].split(R.SIB_SEP)
            for n in names:
                n = n.strip()
                assert n in titles, f"invented sibling {n!r}"
                assert n != e["title"], "a topic cannot be its own sibling"
    assert checked > 1000, "the transfer question should reach almost every topic"


def test_the_sibling_separator_cannot_split_a_title():
    """One bank title contains "; " — joining on it invented a sixth sibling."""
    assert all(R.SIB_SEP not in e["title"] for e in ENTRIES)


def test_first_sentences_trims_without_cutting_mid_word():
    long = "One. Two. " + "word " * 300
    out = R.first_sentences(long)
    assert out.startswith("One. Two.")
    assert len(out) <= 350
    assert R.first_sentences("") == "" and R.first_sentences(None) == ""


def test_the_review_ladder_steps_up_on_hits_and_collapses_on_a_miss():
    assert [R.next_interval(s, True) for s in range(6)] == [1, 3, 7, 16, 35, 35]
    # A miss goes to tomorrow, never to zero: revisiting in the same session
    # is re-reading, not recall.
    assert all(R.next_interval(s, False) == 1 for s in range(6))


def test_the_quiz_rides_along_with_the_card_body(auth_client):
    r = auth_client.get("/api/ai-sde/entry/ai7", headers={"Accept-Encoding": "identity"})
    d = json.loads(r.get_data())
    assert d["quiz"] and len(d["quiz"]) <= R.MAX_ITEMS
    assert {"kind", "q", "a", "hint"} == set(d["quiz"][0])


def test_the_quiz_is_not_in_the_list_payload(auth_client):
    """It would put the answers back into the 3 MB payload we just removed."""
    r = auth_client.get("/api/ai-sde", headers={"Accept-Encoding": "gzip"})
    d = json.loads(gzip.decompress(r.get_data()))
    assert all("quiz" not in e for e in d["entries"])

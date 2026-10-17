"""Random thoughts audio summaries: script cleanup, the recall pause, rebuilds."""
import pytest

from services import thoughts_audio as ta

# One gTTS-style frame: MPEG-2 layer III, 64 kbps, 24 kHz, mono = 192 bytes / 24 ms.
FRAME = b"\xff\xf3\x84\xc4" + bytes(188)


def test_speakable_drops_what_cannot_be_heard():
    md = ("## Heaps\nA **heap** keeps the `min` on top.\n```python\nheapq.heappush(h, x)\n```\n"
          "| op | cost |\n|---|---|\n| push | log n |\n- point one\n1. step\nSee [docs](https://x.y).")
    out = ta.speakable(md)
    assert "heappush" not in out and "|" not in out and "#" not in out and "**" not in out
    assert "A heap keeps the min on top." in out and "point one" in out and "See docs." in out


def test_trim_ends_on_a_sentence():
    text = "One two three. " * 100
    out = ta._trim_words(text, 50)
    assert len(out.split()) <= 50 and out.endswith(".")


def test_recall_pause_is_five_seconds_of_matching_frames():
    q = FRAME * 10
    s = ta.silence_like(q, 5)
    assert len(s) % 192 == 0 and len(s) // 192 == round(5 * 24000 / 576)
    assert s[:4] == FRAME[:4] and set(s[4:192]) == {0}
    assert ta.kbps_of(q) == 64
    assert ta.silence_like(b"not audio", 5) == b""


@pytest.fixture
def store(monkeypatch):
    row = {"id": "r1", "parent_id": None, "question": "What is a heap?", "answer": "A tree.",
           "status": "ready", "audio": None}
    calls = {"tts": 0, "saved": []}
    monkeypatch.setattr(ta, "get", lambda table, params=None: [dict(row)])

    def fake_update(table, params=None, json=None):
        row.update(json); calls["saved"].append(json["audio"])
    monkeypatch.setattr(ta, "update", fake_update)
    monkeypatch.setattr(ta, "make_script", lambda q, a: ("Spoken words " * 300, "fake-model"))

    def fake_tts(text):
        calls["tts"] += 1
        return FRAME * 50
    monkeypatch.setattr(ta, "_tts", fake_tts)
    monkeypatch.setattr(ta, "store", lambda uid, rid, h, data: f"{uid}/{rid}-{h}.mp3")
    return row, calls


def test_build_once_and_again_only_when_the_answer_changes(store):
    row, calls = store
    a = ta.build("r1", "u1")
    assert a["status"] == "ready" and a["key"] == f"u1/r1-{a['hash']}.mp3" and a["source"] == "fake-model"
    assert a["seconds"] == 7 and calls["tts"] == 2          # 50+208+50 frames x 24 ms
    assert ta.is_current(row)
    ta.build("r1", "u1")
    assert calls["tts"] == 2                                 # unchanged: not rebuilt
    row["answer"] = "A complete binary tree."
    assert not ta.is_current(row)
    assert ta.build("r1", "u1")["hash"] != a["hash"] and calls["tts"] == 4


def test_follow_ups_and_unanswered_get_no_audio(store):
    row, calls = store
    row["parent_id"] = "p1"
    assert ta.build("r1", "u1") is None
    row["parent_id"], row["status"] = None, "pending"
    assert ta.build("r1", "u1") is None and calls["tts"] == 0


def test_a_failure_is_saved_with_a_reason(store, monkeypatch):
    row, calls = store
    def boom(*a):
        raise RuntimeError("storage 404: Bucket not found")
    monkeypatch.setattr(ta, "store", boom)
    a = ta.build("r1", "u1")
    assert a["status"] == "failed" and "thought-audio" in a["error"]


def test_only_studied_or_already_spoken_questions_are_recorded(store, monkeypatch):
    row, calls = store
    queued = []
    monkeypatch.setattr(ta, "start", lambda rid, uid, force=False: queued.append(rid) or {"status": "pending"})
    row["understood"] = False
    assert ta.start_if_wanted("r1", "u1") is None and queued == []          # just opened: no audio
    row["understood"] = True
    assert ta.start_if_wanted("r1", "u1") == {"status": "pending"}          # studied: recorded
    row["understood"], row["audio"] = False, {"status": "ready", "hash": "old"}
    assert ta.start_if_wanted("r1", "u1") == {"status": "pending"}          # rewritten: re-recorded
    row["audio"] = {"status": "ready", "hash": ta.answer_hash(row["question"], row["answer"])}
    assert ta.start_if_wanted("r1", "u1") == row["audio"] and len(queued) == 2   # current: left alone

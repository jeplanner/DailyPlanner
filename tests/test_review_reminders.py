"""Revision reminders: a push at 08:00 / 20:00 when spaced reviews are due."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import requests

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def rr(monkeypatch):
    from services import review_reminders as rr
    state = {"rows": [], "claims": set(), "sent": [], "params": None}

    def fake_get(table, params=None):
        state["params"] = params
        return [dict(r) for r in state["rows"]]

    def fake_post(table, payload, prefer=None):
        key = (payload["item_id"], payload["sent_date"])
        if key in state["claims"]:
            resp = requests.Response(); resp.status_code = 409
            raise requests.HTTPError("409", response=resp)
        state["claims"].add(key)

    monkeypatch.setattr(rr, "get", fake_get)
    monkeypatch.setattr(rr, "post", fake_post)
    monkeypatch.setattr(rr.push_service, "send_to_user",
                        lambda uid, **kw: state["sent"].append(kw) or (1, 0))
    return rr, state


def test_sends_per_shelf_at_the_slot_once(rr):
    rr, st = rr
    st["rows"] = [{"shelf": "tpm"}, {"shelf": "tpm"}, {"shelf": "aisde"}]
    at8 = datetime(2026, 10, 17, 8, 0, tzinfo=IST)
    assert rr.fire("u1", at8) == [("aisde", 1), ("tpm", 2)]
    assert {s["url"] for s in st["sent"]} == {"/interview-prep/thoughts?review=1", "/ai-sde/thoughts?review=1"}
    assert "2 questions due for review today" in [s["body"] for s in st["sent"] if "interview" in s["url"]][0]
    # Due "by tonight": the filter is the end of the local day, in UTC.
    assert st["params"]["next_review_at"] == "lte.2026-10-17T18:30:00+00:00"
    assert st["params"]["understood"] == "is.true" and st["params"]["parent_id"] == "is.null"
    # A second worker (or a second tick in the same minute) sends nothing.
    assert rr.fire("u1", at8) == []
    # The evening slot is its own fire.
    assert rr.fire("u1", datetime(2026, 10, 17, 20, 0, tzinfo=IST)) == [("aisde", 1), ("tpm", 2)]
    assert "Still 2 questions" in st["sent"][-1]["body"]


def test_nothing_due_or_not_a_slot_sends_nothing(rr):
    rr, st = rr
    assert rr.fire("u1", datetime(2026, 10, 17, 8, 0, tzinfo=IST)) == []
    st["rows"] = [{"shelf": "tpm"}]
    assert rr.fire("u1", datetime(2026, 10, 17, 9, 0, tzinfo=IST)) == []
    assert st["sent"] == []


def test_the_page_opens_the_review_from_the_link():
    import pathlib
    js = (pathlib.Path(__file__).resolve().parent.parent / "static/js/prep_thoughts.js").read_text(encoding="utf-8")
    assert "review=1" in js and "endOfToday()" in js

"""The AI SDE list payload, and the ceiling that keeps it from growing back.

The bank shipped 3 MB of JSON on every page load to render content that is
collapsed until clicked. These tests exist so that stops being possible by
accident: the size assertion is the whole point, and a new heavy field added
to _AI_SDE_LIST_FIELDS will trip it.
"""
import gzip
import json

from routes.interview_prep import (_AI_SDE_BODY_FIELDS, _AI_SDE_LIST_FIELDS,
                                   _AI_SDE_LIST)


def _json(resp):
    data = resp.get_data()
    if resp.headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return json.loads(data)


def test_the_list_payload_stays_small(auth_client):
    """It was 3,035 KB. A regression here is a slow page for everyone."""
    r = auth_client.get("/api/ai-sde", headers={"Accept-Encoding": "identity"})
    raw = len(r.get_data())
    assert raw < 900 * 1024, f"list payload back up to {raw/1024:.0f} KB"
    g = len(auth_client.get("/api/ai-sde", headers={"Accept-Encoding": "gzip"}).get_data())
    assert g < 120 * 1024, f"gzipped list payload {g/1024:.0f} KB"


def test_the_list_carries_no_body_fields(auth_client):
    """The card body is fetched per-card. Nothing heavy belongs in the list."""
    d = _json(auth_client.get("/api/ai-sde"))
    assert d["total"] == len(_AI_SDE_LIST) > 1000
    seen = set()
    for e in d["entries"]:
        seen.update(e)
    leaked = seen & set(_AI_SDE_BODY_FIELDS)
    assert not leaked, f"body fields leaked into the list: {sorted(leaked)}"
    assert seen <= set(_AI_SDE_LIST_FIELDS) | {"id", "example_count"}


def test_the_list_still_carries_everything_the_card_header_needs(auth_client):
    """Thinning must not take a chip or a filter with it."""
    d = _json(auth_client.get("/api/ai-sde"))
    by_id = {e["id"]: e for e in d["entries"]}
    e = by_id["ai0"]
    for f in ("id", "title", "cat", "rank", "prep_minutes"):
        assert e.get(f) is not None, f
    # Every filter and sort the page offers must be satisfiable from the list.
    seen = set()
    for x in d["entries"]:
        seen.update(x)
    for f in ("difficulty", "priority", "prep_label", "tag_topic", "tag_priority",
              "tag_level", "tag_format", "tag_stage", "tag_time", "tag_subtopic"):
        assert f in seen, f"{f} missing — a filter would silently match nothing"


def test_a_card_body_arrives_whole(auth_client):
    d = _json(auth_client.get("/api/ai-sde/entry/ai7"))
    assert d["id"] == "ai7"
    assert isinstance(d["examples"], list)
    assert d.get("answer"), "the body must carry the answer"
    assert auth_client.get("/api/ai-sde/entry/ai99999").status_code == 404
    assert auth_client.get("/api/ai-sde/entry/nonsense").status_code == 404


def test_search_returns_ids_and_ands_its_terms(auth_client):
    one = _json(auth_client.get("/api/ai-sde/search?q=monotonic"))
    assert one["total"] > 0 and len(one["ids"]) == one["total"]
    assert all(i.startswith("ai") for i in one["ids"])
    # Two terms must narrow, never widen — they are ANDed.
    two = _json(auth_client.get("/api/ai-sde/search?q=monotonic+stack"))
    assert set(two["ids"]) <= set(one["ids"])
    # An empty query means "no constraint", which is not the same as no matches.
    empty = _json(auth_client.get("/api/ai-sde/search?q=+"))
    assert empty["ids"] is None
    # A term that appears nowhere returns an empty list, not everything.
    none = _json(auth_client.get("/api/ai-sde/search?q=zzqqxx"))
    assert none["ids"] == []


def test_search_reaches_prose_the_browser_no_longer_holds(auth_client):
    """Search moved server-side because the bodies stopped being shipped. The
    payoff is that it now covers the code and the worked examples too, which
    is what you want when hunting for where a library call is discussed."""
    d = _json(auth_client.get("/api/ai-sde/search?q=heapq"))
    assert d["total"] > 0, "search no longer reaches code blocks"

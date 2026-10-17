"""Highlights with hints on any page: API and answer prompt."""
import pytest


@pytest.fixture
def hints(monkeypatch):
    import routes.page_hints as ph
    from services import page_hints_service as svc
    rows, started = [], []

    def fake_get(table, params=None, **kw):
        out = [dict(r) for r in rows if f"eq.{r['user_id']}" == params.get("user_id")]
        if "id" in params:
            out = [r for r in out if f"eq.{r['id']}" == params["id"]]
        if "page" in params:
            out = [r for r in out if f"eq.{r['page']}" == params["page"]]
        if params.get("deleted_at") == "is.null":
            out = [r for r in out if not r.get("deleted_at")]
        return out

    def fake_post(table, payload, **kw):
        row = dict(payload, id=f"h{len(rows) + 1}", created_at="2026-10-17T00:00:00Z")
        rows.append(row)
        return [dict(row)]

    def fake_update(table, params=None, json=None, **kw):
        for r in rows:
            if all(f"eq.{r.get(k)}" == v for k, v in params.items()):
                r.update(json)

    for mod in (ph, svc):
        monkeypatch.setattr(mod, "get", fake_get)
        monkeypatch.setattr(mod, "update", fake_update)
    monkeypatch.setattr(ph, "post", fake_post)
    monkeypatch.setattr(svc, "answer_in_background", lambda *a, **k: started.append(a))
    return {"rows": rows, "started": started}


def test_highlight_and_follow_ups(auth_client, hints):
    r = auth_client.post("/api/hints", json={"page": "/ai-sde?x=1", "quote": "  two   pointers ",
                                             "prefix": "y" * 300, "question": "", "context": "page text"})
    assert r.status_code == 201
    item = r.get_json()["item"]
    assert item["page"] == "/ai-sde" and item["quote"] == "two pointers" and len(item["prefix"]) == 80
    assert item["thread"][0]["q"].startswith("Explain this part simply") and item["thread"][0]["status"] == "pending"
    assert hints["started"][-1][2:] == ("/ai-sde", "two pointers", "page text", 0)
    # A follow-up waits for the last answer.
    assert auth_client.post(f"/api/hints/{item['id']}/ask", json={"question": "Why?"}).status_code == 409
    hints["rows"][0]["thread"][0].update(status="ready", a="Because.")
    r = auth_client.post(f"/api/hints/{item['id']}/ask", json={"question": "Why?", "context": "c"})
    assert r.status_code == 200 and [t["q"] for t in r.get_json()["item"]["thread"]][1] == "Why?"
    assert hints["started"][-1][-1] == 1
    # List by page, retry, delete.
    assert len(auth_client.get("/api/hints?page=/ai-sde").get_json()["items"]) == 1
    assert auth_client.get("/api/hints?page=/java").get_json()["items"] == []
    hints["rows"][0]["thread"][1].update(status="failed")
    assert auth_client.post(f"/api/hints/{item['id']}/retry").get_json()["item"]["thread"][1]["status"] == "pending"
    auth_client.post(f"/api/hints/{item['id']}/delete")
    assert auth_client.get("/api/hints?page=/ai-sde").get_json()["items"] == []


def test_a_page_question_needs_words(auth_client, hints):
    assert auth_client.post("/api/hints", json={"page": "/notes", "question": ""}).status_code == 400
    assert auth_client.post("/api/hints", json={"page": "notes", "question": "x"}).status_code == 400
    r = auth_client.post("/api/hints", json={"page": "/notes", "question": "What is this page for?"})
    assert r.status_code == 201 and r.get_json()["item"]["quote"] == ""


def test_hint_prompt_carries_the_thread_and_audience(monkeypatch):
    from services import page_hints_service as svc
    from services import thoughts_service as ts
    seen = {}
    def fake(prompt, images=(), system=None):
        seen.update(prompt=prompt, system=system); return "ok", "fake"
    monkeypatch.setattr(ts, "PROVIDERS", [fake])
    thread = [{"q": "What is a heap?", "a": "A tree."}, {"q": "Why min?"}]
    assert svc.generate("/ai-sde", "min-heap of size k", "ctx text", thread) == ("ok", "fake")
    assert "student" in seen["system"] and seen["system"].startswith(svc.HINT_SYSTEM)
    assert "“min-heap of size k”" in seen["prompt"] and "Q: What is a heap?\nA: A tree." in seen["prompt"]
    assert "(a follow-up)" in seen["prompt"] and seen["prompt"].endswith("Why min?")


def test_page_hints_script_is_on_every_page():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    assert "page_hints.js" in (root / "templates/_pwa_head.html").read_text()
    js = (root / "static/js/page_hints.js").read_text()
    for needle in ("/api/hints", "MutationObserver", "Highlight & ask", "Ask a follow-up"):
        assert needle in js, needle

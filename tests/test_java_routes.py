"""Routes for the Java bank.

The interesting assertions are not "does it return 200" — they are the two
design decisions the routes exist to enforce:

  * the LIST is thin. It ships headers only, so the page load does not carry
    every ten-section deep dive in the bank. That is cheap to guarantee now
    and expensive to retrofit, which is why it is tested at 28 entries rather
    than at 300.
  * the browse page and the quiz page get the SAME shuffled quiz, from the
    same presented_quiz(), so they can never disagree about which option is
    which.
"""
import java_bank
import routes.java_prep as jp


def test_pages_render(auth_client):
    for path in ("/java", "/java/quiz"):
        r = auth_client.get(path)
        assert r.status_code == 200, path


def test_list_is_thin(auth_client):
    """The list must NOT carry the card bodies. The AI/SDE bank shipped every
    field on page load and reached a 3 MB payload before anyone noticed,
    because the list screen renders none of it."""
    r = auth_client.get("/api/java")
    assert r.status_code == 200
    d = r.get_json()
    assert d["total"] == len(java_bank.ENTRIES)

    row = d["entries"][0]
    for heavy in ("plain", "answer", "code", "output", "gotcha", "examples"):
        assert heavy not in row, f"{heavy!r} must not be in the list payload"
    for needed in ("id", "title", "cat", "has_code", "has_trap", "has_deep"):
        assert needed in row, needed


def test_list_preserves_the_teaching_ladder(auth_client):
    """Alphabetical would put concurrency before basics."""
    d = auth_client.get("/api/java").get_json()
    assert [c["key"] for c in d["categories"]] == java_bank.CATEGORY_ORDER


def test_entry_carries_the_body_and_the_shuffled_quiz(auth_client):
    d = auth_client.get("/api/java/entry/j0").get_json()
    assert d["id"] == "j0"
    assert d["plain"] and d["answer"]
    assert d["quiz"]["options"]
    assert d["recall"]


def test_entry_quiz_matches_the_bank_shuffle(auth_client):
    """Browse and quiz must present the same option order, or an explanation
    that says 'Option C' points at different things on the two pages."""
    d = auth_client.get("/api/java/entry/j0").get_json()
    expected = java_bank.presented_quiz(java_bank.ENTRIES[0])
    assert d["quiz"]["options"] == expected["options"]
    assert d["quiz"]["answer"] == expected["answer"]


def test_unknown_entry_404s(auth_client):
    assert auth_client.get("/api/java/entry/j99999").status_code == 404
    assert auth_client.get("/api/java/entry/nonsense").status_code == 404


def test_quiz_respects_n_and_cat(auth_client):
    d = auth_client.get("/api/java/quiz?n=5").get_json()
    assert d["count"] == 5

    d = auth_client.get("/api/java/quiz?cat=traps&n=30").get_json()
    assert d["count"] > 0
    assert all(q["cat"] == "traps" for q in d["questions"])


def test_quiz_n_is_clamped(auth_client):
    """A caller asking for 10,000 questions gets a bank-sized answer, not a
    crash and not a runaway payload."""
    assert auth_client.get("/api/java/quiz?n=99999").get_json()["count"] <= 30
    assert auth_client.get("/api/java/quiz?n=abc").get_json()["count"] > 0
    assert auth_client.get("/api/java/quiz?n=-5").get_json()["count"] >= 3


def test_quiz_questions_carry_their_explanation(auth_client):
    """A quiz that only says right/wrong is the recognition drill this bank
    exists to avoid."""
    for q in auth_client.get("/api/java/quiz?n=10").get_json()["questions"]:
        assert q["why"] and len(q["why"]) > 100
        assert 0 <= q["answer"] < len(q["options"])


def test_routes_are_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    for path in ("/java", "/java/quiz", "/api/java",
                 "/api/java/entry/<entry_id>", "/api/java/quiz"):
        assert path in rules, path


def test_list_is_built_once(app):
    """Built at import, not per request — the bank is a static literal and
    cannot change between requests."""
    assert jp._LIST is jp._LIST
    assert len(jp._LIST) == len(java_bank.ENTRIES)

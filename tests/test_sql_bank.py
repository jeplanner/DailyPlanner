"""The SQL bank — and the thing that makes it trustworthy.

The Java bank's outputs were reasoned by hand, because there is no JDK on
the build machine. This bank has no such excuse: sqlite3 is in the
standard library, so every stated result is RE-RUN here and compared. A
wrong expected value is a test failure rather than a reader's problem.
"""
import re

import sql_bank as SB


def test_self_check_is_clean():
    problems = SB.self_check()
    assert problems == [], "sql_bank self-check failures:\n  " + "\n  ".join(problems)


def test_every_stated_result_is_what_the_query_actually_returns():
    """THE POINT OF THIS BANK. Runs all 45 queries against their own schema
    in a fresh in-memory database and compares with the stated output.

    This has already caught one hand-typed expected value that was wrong,
    which is exactly the class of error a study bank cannot afford."""
    problems = SB.verify()
    assert problems == [], "stated output does not match reality:\n\n" + "\n\n".join(problems)


def test_a_query_without_a_stated_result_is_rejected():
    """Q() enforces it, the same way java_bank refuses code with no output —
    a query whose result nobody wrote down cannot be used for the drill the
    bank exists for."""
    import pytest
    with pytest.raises(ValueError):
        SB.Q("basics", "no result", "plain words", "the answer", "shop", ["x"],
             query="select 1")


def test_a_query_against_an_unknown_schema_is_rejected():
    """A typo in the schema name would make verify() skip the entry rather
    than check it, which would silently remove it from the guarantee above."""
    import pytest
    with pytest.raises(ValueError):
        SB.Q("basics", "bad schema", "plain words", "the answer", "nope", ["x"],
             query="select 1", output="1")


def test_every_entry_has_plain_english_first():
    """`plain` is required by Q(); this guards against it being padded out
    with the jargon it exists to avoid."""
    jargon = ("cardinality", "sargable", "three-valued", "cartesian",
              "correlated subquery", "b-tree")
    for e in SB.ENTRIES:
        assert e["plain"].strip(), e["title"]
        hits = [w for w in jargon if w in e["plain"].lower()]
        assert not hits, f"{e['title']!r}: jargon in the plain answer: {hits}"


def test_the_ladder_is_a_teaching_order():
    """Categories are ordered, not alphabetical — window functions must not
    come before SELECT."""
    assert list(SB.CATEGORIES) == SB.CATEGORY_ORDER
    seen = []
    for e in SB.ENTRIES:
        assert e["cat"] in SB.CATEGORIES, e["title"]
        if not seen or seen[-1] != e["cat"]:
            seen.append(e["cat"])
    # each category appears as one contiguous run, in ladder order
    assert seen == [c for c in SB.CATEGORY_ORDER if c in seen], seen


def test_the_null_rung_covers_the_traps_that_matter():
    """NULL is where SQL bites, and three specific behaviours account for
    most of it. If any of these ever drops out of the bank, someone has
    removed the most valuable entries in it."""
    titles = " | ".join(e["title"].lower() for e in SB.ENTRIES)
    for needed in ("= null", "is null", "not in", "not exists"):
        assert needed in titles, f"no entry covers {needed!r}"


def test_portability_notes_exist_where_engines_disagree():
    """This bank runs on SQLite. Any entry whose behaviour differs on
    Postgres or MySQL must say so, or a reader learns a SQLite-ism as
    though it were SQL."""
    by_title = {e["title"]: e for e in SB.ENTRIES}
    must_warn = [t for t in by_title
                 if "order by" in t.lower() and "null" in t.lower()]
    assert must_warn, "expected an ORDER BY / NULL entry"
    for t in must_warn:
        assert by_title[t]["portability"].strip(), (
            f"{t!r}: NULL ordering differs between engines and the entry does not say so")


def test_schemas_are_self_contained_and_runnable():
    """Every schema must build from nothing — that is what lets a reader
    paste it into any SQLite prompt and reproduce the page exactly."""
    for name in SB.SCHEMAS:
        con = SB._connect(name)
        try:
            tables = [r[0] for r in con.execute(
                "select name from sqlite_master where type='table'")]
            assert tables, f"schema {name!r} creates no tables"
            for t in tables:
                n = con.execute(f"select count(*) from {t}").fetchone()[0]
                assert n > 0, f"schema {name!r} table {t!r} has no rows to query"
        finally:
            con.close()


# ── the page ─────────────────────────────────────────────────────────

def test_the_page_and_its_api_respond(auth_client):
    import gzip, json
    r = auth_client.get("/sql")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "PrepScheduler.button(\"sql\"" in html, "no Plan button on the SQL cards"
    assert 'class="q-sum"' in html, "no card summary"

    data = auth_client.get("/api/sql").get_data()
    if auth_client.get("/api/sql").headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    d = json.loads(data)
    assert d["total"] == len(SB.ENTRIES)
    assert d["entries"][0]["summary"], "the list ships no summary"
    # The list is THIN: no query, no output, no prose.
    for e in d["entries"]:
        for heavy in ("query", "output", "plain", "answer"):
            assert heavy not in e, f"{heavy} leaked into the list payload"


def test_an_entry_body_arrives_whole(auth_client):
    import gzip, json
    r = auth_client.get("/api/sql/entry/sq0")
    d = json.loads(r.get_data())
    assert d["query"] and d["output"] and d["plain"]
    assert auth_client.get("/api/sql/entry/nope").status_code == 404


def test_the_schema_endpoint_returns_runnable_sql(auth_client):
    import json
    d = json.loads(auth_client.get("/api/sql/schema/shop").get_data())
    assert d["ddl"] and d["seed"]
    assert d["sql"].rstrip().endswith(";")
    assert auth_client.get("/api/sql/schema/nope").status_code == 404

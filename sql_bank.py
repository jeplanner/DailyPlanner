"""SQL question bank — the queries, run.

WHY THIS IS A SEPARATE BANK. SQL is not a topic inside "CS fundamentals",
it is a language, and a language bank needs what java_bank.py needed: a
question of the form "what does this return", a stated result, and a trap
worth knowing. The AI/SDE bank has plenty of database THEORY - indexes,
isolation levels, normalisation - and almost no SQL you can be asked to
write on a whiteboard. This is that half.

EVERY QUERY IN THIS FILE IS EXECUTED. `Q()` refuses an entry that has a
query and no stated result, exactly as java_bank does, and `verify()`
then runs each query against its own schema in sqlite and compares the
real output to the stated one. A wrong expected result is a test
failure, not a reader's problem. That is the whole reason this bank can
be trusted where a hand-written one cannot: the Java bank's outputs were
reasoned by hand because there is no JDK on the build machine, and
sqlite3 is in the standard library.

WHAT THAT COSTS, STATED UP FRONT. The engine is SQLite, and SQLite is not
Postgres. Where behaviour genuinely differs - RIGHT JOIN before 3.39,
`||` versus `CONCAT`, integer division, `NULLS FIRST` ordering, boolean
types - the entry says so in `portability`, and the stated output is
SQLite's. Every entry here was chosen so the LESSON is portable even
where the syntax is not; anything whose whole point was engine-specific
was left out rather than quietly fudged.

THE TEACHING LADDER, in order: reading rows, joining them, grouping them,
the NULL rules that break all three, window functions, subqueries and
CTEs, writing rows, what an index actually does, and then the traps -
short queries whose answer is not what it looks like.
"""
import re
import sqlite3

# ── the schemas ─────────────────────────────────────────────────────
# Entries name a schema rather than carrying their own DDL, so a reader
# who has understood `shop` once can read twenty queries without
# re-reading the tables. A schema is a list of statements; verify()
# executes them in order into a fresh in-memory database per entry.

SCHEMAS = {}

SCHEMAS["shop"] = [
    """create table customers (
         id       integer primary key,
         name     text not null,
         city     text,            -- deliberately nullable
         joined   text not null
       )""",
    """create table orders (
         id           integer primary key,
         customer_id  integer,     -- nullable: a guest checkout has none
         amount       real not null,
         status       text not null,
         placed       text not null
       )""",
    "insert into customers values (1,'Ana','London','2024-01-05')",
    "insert into customers values (2,'Bo','Paris','2024-02-11')",
    "insert into customers values (3,'Cy',null,'2024-02-14')",
    "insert into customers values (4,'Di','London','2024-03-02')",
    "insert into customers values (5,'Ed','Tokyo','2024-05-20')",
    "insert into orders values (10,1,120.0,'paid','2024-03-01')",
    "insert into orders values (11,1, 45.5,'paid','2024-03-09')",
    "insert into orders values (12,2, 80.0,'refunded','2024-03-11')",
    "insert into orders values (13,2,200.0,'paid','2024-04-02')",
    "insert into orders values (14,4, 15.0,'pending','2024-04-18')",
    "insert into orders values (15,null,60.0,'paid','2024-04-20')",   # guest
    "insert into orders values (16,1, 30.0,'paid','2024-05-01')",
]

SCHEMAS["staff"] = [
    """create table employees (
         id        integer primary key,
         name      text not null,
         manager   integer,          -- self-reference; null for the boss
         dept      text,
         salary    integer not null,
         hired     text not null
       )""",
    "insert into employees values (1,'Root',null,'exec',200000,'2019-01-01')",
    "insert into employees values (2,'Mira',1,'eng',150000,'2020-03-15')",
    "insert into employees values (3,'Nadia',2,'eng',120000,'2021-06-01')",
    "insert into employees values (4,'Omar',2,'eng',120000,'2021-09-12')",
    "insert into employees values (5,'Priya',1,'sales',110000,'2020-11-05')",
    "insert into employees values (6,'Quinn',5,'sales',90000,'2022-02-20')",
    "insert into employees values (7,'Rhys',5,'sales',null_or_zero,'2022-08-01')"
        .replace("null_or_zero", "90000"),
    "insert into employees values (8,'Sara',null,null,70000,'2023-04-04')",
]

SCHEMAS["events"] = [
    """create table pageviews (
         id      integer primary key,
         user_id integer not null,
         page    text not null,
         ts      text not null
       )""",
    "insert into pageviews values (1,1,'/home','2024-06-01 09:00')",
    "insert into pageviews values (2,1,'/pricing','2024-06-01 09:02')",
    "insert into pageviews values (3,1,'/signup','2024-06-01 09:05')",
    "insert into pageviews values (4,2,'/home','2024-06-01 10:00')",
    "insert into pageviews values (5,2,'/home','2024-06-01 10:04')",
    "insert into pageviews values (6,3,'/pricing','2024-06-02 11:00')",
    "insert into pageviews values (7,3,'/home','2024-06-02 11:30')",
    "insert into pageviews values (8,1,'/home','2024-06-03 08:00')",
]

CATEGORY_ORDER = [
    "basics", "joins", "aggregate", "nulls",
    "window", "subquery", "modify", "index", "traps",
]

CATEGORIES = {
    "basics":   "Reading rows — SELECT, WHERE, ORDER BY",
    "joins":    "Joining tables",
    "aggregate": "GROUP BY and aggregates",
    "nulls":    "NULL — the rules that break everything else",
    "window":   "Window functions",
    "subquery": "Subqueries and CTEs",
    "modify":   "Writing rows — INSERT, UPDATE, DELETE, UPSERT",
    "index":    "Indexes and what the planner actually does",
    "traps":    "Classic traps (what does this return?)",
}


def Q(cat, title, plain, answer, schema, tags,
      query="", output="", gotcha="", portability="", quiz=None,
      example="", pitfalls="", followups="", difficulty="", frequency="",
      mnemonic="", examples=None):
    """One bank entry.

    REQUIRED, and required for the same reasons java_bank requires them:
        plain  - no jargon. If you cannot say it plainly you cannot teach it.
        answer - the technical statement, free to use the words `plain` defined.
        output - if there is a query there is a result, and it is checked.

    `portability` is where an entry admits that SQLite and Postgres
    disagree. Empty means the behaviour is standard everywhere that
    matters; anything else is quoted in the rendered card so a reader
    never learns a SQLite-ism as though it were SQL.
    """
    if not plain.strip():
        raise ValueError(f"entry {title!r} has no plain-English answer")
    if query and not output.strip():
        raise ValueError(f"entry {title!r} has a query but no stated output")
    if query and schema not in SCHEMAS:
        raise ValueError(f"entry {title!r} names unknown schema {schema!r}")
    return {
        "cat": cat, "title": title, "plain": plain, "answer": answer,
        "schema": schema, "tags": tags, "query": query, "output": output,
        "gotcha": gotcha, "portability": portability, "quiz": quiz,
        "example": example, "pitfalls": pitfalls, "followups": followups,
        "difficulty": difficulty, "frequency": frequency,
        "mnemonic": mnemonic, "examples": list(examples or []),
    }


# ── running the queries ─────────────────────────────────────────────

def _connect(schema_name):
    con = sqlite3.connect(":memory:")
    for stmt in SCHEMAS[schema_name]:
        con.execute(stmt)
    con.commit()
    return con


def _fmt(rows, headers):
    """Render a result set the way the entries state it.

    Fixed-width columns with a header rule, because a result you cannot
    line up by eye is a result nobody checks.
    """
    if not rows:
        return "(0 rows)"
    cols = list(headers)
    table = [[("NULL" if v is None else
               (f"{v:g}" if isinstance(v, float) else str(v))) for v in r]
             for r in rows]
    widths = [max(len(cols[i]), max(len(r[i]) for r in table))
              for i in range(len(cols))]
    line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)).rstrip()
    rule = "  ".join("-" * widths[i] for i in range(len(cols)))
    body = ["  ".join(r[i].ljust(widths[i]) for i in range(len(cols))).rstrip()
            for r in table]
    n = len(rows)
    return "\n".join([line, rule] + body + [f"({n} row{'' if n == 1 else 's'})"])


def run(entry):
    """Execute one entry's query and return its rendered result.

    Multi-statement queries (a couple of the `modify` entries set up a
    row and then read it back) are split on a bare semicolon at end of
    line; only the LAST statement's result is rendered, which is what
    the entry is asking about.
    """
    con = _connect(entry["schema"])
    try:
        stmts = [s.strip() for s in re.split(r";\s*\n", entry["query"]) if s.strip()]
        cur = None
        for s in stmts:
            cur = con.execute(s.rstrip(";"))
        if cur.description is None:          # a write with nothing to show
            return f"({con.total_changes} row{'' if con.total_changes == 1 else 's'} affected)"
        headers = [d[0] for d in cur.description]
        return _fmt(cur.fetchall(), headers)
    finally:
        con.close()


def verify():
    """Run every query and compare with its stated output.

    Returns a list of problems, empty when the bank is honest. This is
    what the test calls, and it is the reason a claim in this file can
    be trusted: nothing here is a remembered result.
    """
    problems = []
    for e in ENTRIES:
        if not e["query"]:
            continue
        try:
            actual = run(e)
        except Exception as exc:            # a query that does not even run
            problems.append(f"{e['title']!r}: query failed: {exc}")
            continue
        if actual.strip() != e["output"].strip():
            problems.append(
                f"{e['title']!r}: stated output does not match.\n"
                f"  --- stated ---\n{e['output']}\n"
                f"  --- actual ---\n{actual}")
    return problems


def self_check():
    """Structural problems, in the shape java_bank.self_check() uses."""
    problems = []
    seen = set()
    for e in ENTRIES:
        if e["cat"] not in CATEGORIES:
            problems.append(f"{e['title']!r}: unknown category {e['cat']!r}")
        key = e["title"].strip().lower()
        if key in seen:
            problems.append(f"duplicate title: {e['title']!r}")
        seen.add(key)
        if not e["answer"].strip():
            problems.append(f"{e['title']!r}: no technical answer")
        if not e["tags"]:
            problems.append(f"{e['title']!r}: no tags")
    return problems


ENTRIES = []

from sql_bank_core import build as _build_core          # noqa: E402
from sql_bank_joins import build as _build_joins        # noqa: E402
from sql_bank_advanced import build as _build_advanced  # noqa: E402
from sql_bank_traps import build as _build_traps        # noqa: E402

ENTRIES += _build_core(Q)
ENTRIES += _build_joins(Q)
ENTRIES += _build_advanced(Q)
ENTRIES += _build_traps(Q)

# Stable order for the page: the teaching ladder, then insertion order
# within a rung.
ENTRIES.sort(key=lambda e: CATEGORY_ORDER.index(e["cat"]))


def render(entry):
    """Plain-text rendering, used by the CLI and the PDF export."""
    out = [entry["title"], "=" * len(entry["title"]), ""]
    out += ["IN PLAIN ENGLISH", entry["plain"], ""]
    out += ["THE ANSWER", entry["answer"], ""]
    if entry["query"]:
        out += ["THE QUERY", entry["query"], "", "RESULT", entry["output"], ""]
    for label, key in (("THE TRAP", "gotcha"), ("PORTABILITY", "portability"),
                       ("PITFALLS", "pitfalls"), ("FOLLOW-UPS", "followups"),
                       ("HOW TO REMEMBER", "mnemonic")):
        if entry.get(key):
            out += [label, entry[key], ""]
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    bad = self_check()
    if bad:
        print("STRUCTURE:")
        for b in bad:
            print("  " + b)
    bad2 = verify()
    if bad2:
        print("OUTPUT MISMATCHES:")
        for b in bad2:
            print("  " + b)
    print(f"\n{len(ENTRIES)} entries, "
          f"{sum(1 for e in ENTRIES if e['query'])} with a verified query")
    for c in CATEGORY_ORDER:
        n = sum(1 for e in ENTRIES if e["cat"] == c)
        print(f"  {c:10} {n:3}  {CATEGORIES[c]}")
    sys.exit(1 if (bad or bad2) else 0)

"""SQL bank — reading rows, grouping them, and the NULL rules.

The first three rungs of the ladder. `basics` is the vocabulary; `aggregate`
is where most reporting bugs live; `nulls` is where the other two quietly
stop meaning what you think.

Every stated output in this file came out of sqlite3 and is re-checked by
sql_bank.verify() on every test run.
"""


def build(Q):
    return [

    # ══════════════════ BASICS ══════════════════

    Q("basics", "SELECT ... WHERE — the shape of every query",
      "Pick the columns you want, from the table they are in, keeping only the "
      "rows that match a condition. Everything else in SQL is a variation on "
      "those three choices.",
      "SELECT names the output columns; FROM names the source; WHERE filters "
      "rows BEFORE grouping. The clauses are written in the order "
      "SELECT-FROM-WHERE-GROUP BY-HAVING-ORDER BY-LIMIT, but they are EVALUATED "
      "roughly FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY, LIMIT — which is "
      "why a column alias defined in SELECT can be used in ORDER BY (evaluated "
      "later) but not in WHERE (evaluated earlier).",
      "shop", ["select", "where", "order-by"],
      query="select name, city from customers where city = 'London' order by name",
      output="""name  city
----  ------
Ana   London
Di    London
(2 rows)""",
      gotcha="Try `select amount * 2 as double from orders where double > 100` and it "
             "fails: WHERE runs before SELECT, so the alias does not exist yet. Repeat "
             "the expression, or wrap the query in a subquery or CTE.",
      pitfalls="String comparison is case-sensitive in Postgres and case-INSENSITIVE for "
               "ASCII in SQLite and MySQL's default collation. `where city = 'london'` "
               "returning rows on one engine and nothing on another is a collation "
               "difference, not a bug in your data.",
      difficulty="Easy", frequency="Every SQL interview opens here",
      mnemonic="Written SELECT-first, evaluated FROM-first. That inversion explains most "
               "'why can't I use my alias' questions."),

    Q("basics", "ORDER BY, and where NULL sorts",
      "Sorting puts rows in an order you choose. The question nobody asks until it "
      "bites is where the rows with a missing value go — first or last.",
      "ORDER BY sorts by one or more expressions, ascending by default. NULL "
      "ordering is NOT standardised: SQLite and MySQL sort NULLs FIRST ascending; "
      "Postgres and Oracle sort them LAST. The SQL standard leaves it "
      "implementation-defined, and `NULLS FIRST` / `NULLS LAST` is the explicit "
      "form where it is supported.",
      "shop", ["order-by", "null", "portability"],
      query="select name, city from customers order by city, name",
      output="""name  city
----  ------
Cy    NULL
Ana   London
Di    London
Bo    Paris
Ed    Tokyo
(5 rows)""",
      portability="SQLite and MySQL put NULLs first on an ascending sort, as shown. "
                  "Postgres and Oracle put them LAST — the same query returns Cy at the "
                  "BOTTOM. Write `ORDER BY city NULLS LAST` (Postgres, Oracle, SQLite "
                  "3.30+) or `ORDER BY city IS NULL, city` (works everywhere) when it "
                  "matters, which for a paginated report it always does.",
      gotcha="An ORDER BY that is not a total order makes pagination unstable: two rows "
             "that tie can come back in either order, so page 2 can repeat a row from "
             "page 1 or skip one. Always append a unique tie-breaker — usually the "
             "primary key.",
      difficulty="Easy", frequency="The NULL-ordering half is a good senior question",
      mnemonic="NULL sorting is engine-specific. If it matters, say NULLS LAST out loud."),

    Q("basics", "LIMIT and the cost of OFFSET",
      "Return only the first few rows. Straightforward — until you use it to page "
      "through results, where asking for page 5,000 makes the database read "
      "everything before it and throw it away.",
      "LIMIT n caps the rows returned; OFFSET k skips the first k. The planner "
      "cannot skip rows without producing them, so OFFSET k is O(k) — page 1,000 of "
      "a 20-row page reads 20,000 rows to return 20. KEYSET PAGINATION replaces it: "
      "`WHERE id > :last_seen ORDER BY id LIMIT 20`, which uses the index and costs "
      "the same for every page.",
      "shop", ["limit", "pagination", "performance"],
      query="select id, amount from orders order by amount desc limit 3",
      output="""id  amount
--  ------
13  200
10  120
12  80
(3 rows)""",
      portability="`LIMIT n` in SQLite, Postgres and MySQL. SQL Server uses "
                  "`SELECT TOP n` or `OFFSET ... FETCH NEXT n ROWS ONLY`; Oracle uses "
                  "`FETCH FIRST n ROWS ONLY` (12c+) or a ROWNUM subquery before that.",
      gotcha="LIMIT without ORDER BY returns an ARBITRARY set of rows, not the 'first' "
             "ones — there is no first without an order. It will look stable in testing "
             "and change the day the planner picks a different access path.",
      pitfalls="Keyset pagination needs the sort key to be unique. Paging on a "
               "non-unique `created_at` skips rows sharing a timestamp; page on "
               "`(created_at, id)` instead.",
      difficulty="Easy", frequency="Very common — the OFFSET cost is the follow-up",
      mnemonic="OFFSET reads what it skips. Page by WHERE, not by counting."),

    Q("basics", "DISTINCT, and why it is usually a symptom",
      "Remove duplicate rows from the result. Useful, and also the thing people "
      "reach for when a join has quietly multiplied their rows.",
      "DISTINCT deduplicates the ENTIRE selected row, not the first column. It "
      "requires a sort or a hash of the whole result, so it is not free. When "
      "DISTINCT appears on a query that joins, the usual cause is a one-to-many "
      "join producing repeated left-hand rows, and the honest fix is to aggregate "
      "or use EXISTS rather than to deduplicate afterwards.",
      "shop", ["distinct", "duplicates"],
      query="select distinct status from orders order by status",
      output="""status
--------
paid
pending
refunded
(3 rows)""",
      gotcha="`SELECT DISTINCT a, b` is not `SELECT DISTINCT(a), b`. There is no "
             "per-column DISTINCT — the parentheses are just grouping and the "
             "deduplication still applies to the whole row. Writing it that way "
             "convinces the reader of something false.",
      pitfalls="COUNT(DISTINCT x) is markedly more expensive than COUNT(x) because it "
               "must materialise the distinct set. On large tables an approximate "
               "count (Postgres HLL, MySQL 8 window tricks) is often the right trade.",
      difficulty="Easy", frequency="Common, usually as 'why is DISTINCT here?'",
      mnemonic="DISTINCT on a joined query is a bug report about the join."),

    Q("basics", "LIKE, and the wildcard that disables your index",
      "Match text against a pattern. `%` stands for any run of characters, `_` for "
      "exactly one. The catch is that a pattern STARTING with `%` cannot use an "
      "index, because an index is sorted by the beginning of the string.",
      "LIKE compares against a pattern. A B-tree index on the column serves "
      "`LIKE 'abc%'` as a range scan, because all matches share a prefix and are "
      "therefore adjacent in the index. `LIKE '%abc'` and `LIKE '%abc%'` have no "
      "usable prefix and force a full scan. For contains-search at scale the answer "
      "is a trigram index (Postgres pg_trgm) or a full-text index, not a bigger "
      "machine.",
      "shop", ["like", "pattern", "index"],
      query="select name from customers where name like '%a%' order by name",
      output="""name
----
Ana
(1 row)""",
      gotcha="That result surprises people: only Ana matches, because SQLite's LIKE is "
             "case-insensitive for ASCII but the pattern still has to appear — 'Nadia' "
             "would match, 'Bo' and 'Cy' and 'Di' and 'Ed' contain no 'a'. Read the "
             "result against the data rather than assuming.",
      portability="LIKE is case-SENSITIVE in Postgres (use ILIKE for insensitive) and "
                  "case-INSENSITIVE in SQLite for ASCII and in MySQL under its default "
                  "collation. The same query genuinely returns different rows on "
                  "different engines.",
      pitfalls="A user-supplied search term containing % or _ becomes a wildcard. Escape "
               "it, or a search for '50%' matches everything starting '50'.",
      difficulty="Easy", frequency="Common — the leading-wildcard cost is the real question",
      mnemonic="A leading % throws the index away. Prefix search is fast; contains is not."),

    # ══════════════════ AGGREGATE ══════════════════

    Q("aggregate", "COUNT(*) vs COUNT(column) vs COUNT(DISTINCT column)",
      "Three different questions that look like one. COUNT(*) counts ROWS. "
      "COUNT(column) counts rows where that column is not missing. "
      "COUNT(DISTINCT column) counts how many different values there are.",
      "COUNT(*) counts rows and never skips any. COUNT(expr) counts rows where expr "
      "IS NOT NULL — this is the single most common source of a report that is "
      "quietly short. COUNT(DISTINCT expr) counts distinct non-null values. The gap "
      "between the first two is exactly the number of NULLs.",
      "shop", ["count", "aggregate", "null"],
      query="select count(*) as rows,\n       count(customer_id) as with_customer,\n"
            "       count(distinct customer_id) as distinct_customers\n  from orders",
      output="""rows  with_customer  distinct_customers
----  -------------  ------------------
7     6              3
(1 row)""",
      gotcha="7, 6, 3 from one table in one query. Seven orders exist; six have a "
             "customer (one is a guest checkout with customer_id NULL); those six come "
             "from three distinct customers. Anyone who writes COUNT(customer_id) "
             "meaning 'how many orders' is under-reporting by every guest order, "
             "silently and forever.",
      pitfalls="COUNT(*) is not slower than COUNT(1) — every serious planner treats them "
               "identically. The folklore that COUNT(1) is faster is decades out of date.",
      followups="Why can COUNT(*) on a large Postgres table be slow? Because MVCC means "
                "visibility is per-transaction, so it cannot be read from a stored "
                "counter — it must check rows. MyISAM kept an exact count and could "
                "answer instantly; InnoDB and Postgres cannot.",
      difficulty="Easy", frequency="Extremely common, and the NULL half separates people",
      mnemonic="COUNT(*) counts rows. COUNT(col) counts ANSWERS. The difference is the NULLs."),

    Q("aggregate", "GROUP BY and HAVING — filtering before and after",
      "GROUP BY collapses rows into one row per group. WHERE filters the rows "
      "BEFORE they are grouped; HAVING filters the GROUPS after. Putting a "
      "condition in the wrong one changes the answer, not just the speed.",
      "WHERE is evaluated before grouping, so it cannot reference an aggregate. "
      "HAVING is evaluated after, so it can. `WHERE status='paid'` removes rows and "
      "then counts what is left; `HAVING count(*) > 1` counts everything and then "
      "removes groups. Prefer WHERE where both are possible — it is strictly "
      "cheaper, because rows removed early are never grouped at all.",
      "shop", ["group-by", "having", "aggregate"],
      query="select status, count(*) as n, round(sum(amount),2) as total\n"
            "  from orders\n group by status\nhaving count(*) > 1\n order by status",
      output="""status  n  total
------  -  -----
paid    5  455.5
(1 row)""",
      gotcha="Every column in SELECT must either be in GROUP BY or wrapped in an "
             "aggregate. MySQL historically allowed bare columns and returned an "
             "arbitrary row's value — ONLY_FULL_GROUP_BY is on by default since 5.7 "
             "and rejects it. Postgres and SQL Server always rejected it. Code written "
             "against old MySQL fails to port for exactly this reason.",
      pitfalls="GROUP BY with no matching rows returns ZERO rows, not a row of zeros. A "
               "dashboard showing 'no data' where it should show 0 is usually this — the "
               "fix is a LEFT JOIN from a table of all the groups you want.",
      difficulty="Easy", frequency="Very common",
      mnemonic="WHERE filters rows, HAVING filters groups. If it mentions an aggregate it "
               "must be HAVING."),

    Q("aggregate", "GROUP BY over a LEFT JOIN — count the right column",
      "Counting after a LEFT JOIN is where reports go wrong. A customer with no "
      "orders still produces one row, with the order columns all missing — so "
      "COUNT(*) says 1 and COUNT(order_id) says 0. Only one of those is what you "
      "meant.",
      "A LEFT JOIN keeps every left row. Unmatched left rows get NULLs for the right "
      "table's columns. COUNT(*) then counts that placeholder row, giving 1 for a "
      "customer with no orders; COUNT(o.id) counts non-null order ids and correctly "
      "gives 0. THE COLUMN YOU COUNT IS THE QUESTION YOU ASKED.",
      "shop", ["group-by", "left-join", "count", "null"],
      query="select c.city, count(o.id) as orders\n"
            "  from customers c\n  left join orders o on o.customer_id = c.id\n"
            " group by c.city\n order by c.city",
      output="""city    orders
------  ------
NULL    0
London  4
Paris   2
Tokyo   0
(4 rows)""",
      gotcha="Tokyo shows 0 because Ed has no orders and COUNT(o.id) ignores the NULL. "
             "Change it to COUNT(*) and Tokyo becomes 1 — a customer, counted as an "
             "order. The NULL row at the top is Cy, whose city is missing: GROUP BY "
             "puts all NULLs in ONE group, even though NULL = NULL is never true.",
      pitfalls="Note the guest order (customer_id NULL, 60.00) appears in NO city group — "
               "a LEFT JOIN from customers cannot see orders with no customer. Summing "
               "the city totals would therefore not equal the company total, which is "
               "the kind of discrepancy that takes a day to find.",
      difficulty="Medium", frequency="Very common in take-homes and dashboards",
      mnemonic="LEFT JOIN then COUNT(*) counts customers. COUNT(right.column) counts matches."),

    Q("aggregate", "AVG, SUM and the rows they silently skip",
      "Aggregates ignore missing values. AVG divides by how many values it FOUND, "
      "not how many rows there were — so an average over a column with gaps is an "
      "average of the rows that happened to have data.",
      "SUM, AVG, MIN and MAX all skip NULLs. AVG(x) is SUM(x)/COUNT(x), not "
      "SUM(x)/COUNT(*) — so with 100 rows of which 40 are NULL, AVG divides by 60. "
      "If NULL means zero in your domain, say so explicitly with COALESCE(x, 0); if "
      "it means unknown, the skipping is correct and the number needs a caveat "
      "attached to it.",
      "shop", ["avg", "sum", "null", "aggregate"],
      query="select count(*) as rows,\n"
            "       sum(case when status='paid' then 1 else 0 end) as paid,\n"
            "       avg(amount) as avg_amount\n  from orders",
      output="""rows  paid  avg_amount
----  ----  ----------
7     5     78.6429
(1 row)""",
      gotcha="SUM over an EMPTY set returns NULL, not 0 — so "
             "`SUM(amount) WHERE status='cancelled'` on a table with no cancellations "
             "gives NULL and any arithmetic on it gives NULL. Wrap it: "
             "COALESCE(SUM(amount), 0). COUNT is the exception: COUNT of nothing is 0.",
      pitfalls="`SUM(CASE WHEN cond THEN 1 ELSE 0 END)` and "
               "`COUNT(CASE WHEN cond THEN 1 END)` both work as a conditional count, but "
               "`SUM(CASE WHEN cond THEN 1 END)` returns NULL when nothing matches "
               "rather than 0, because the implicit ELSE is NULL.",
      difficulty="Medium", frequency="Common — the empty-SUM NULL catches people",
      mnemonic="Aggregates skip NULLs. SUM of nothing is NULL; COUNT of nothing is 0."),

    # ══════════════════ NULLS ══════════════════

    Q("nulls", "= NULL returns nothing, and it is not an error",
      "NULL means 'unknown'. Asking whether an unknown value equals another value "
      "cannot be answered yes or no, so SQL answers 'unknown' — and rows whose "
      "condition is unknown are not returned. So `WHERE x = NULL` matches nothing, "
      "silently, including the rows where x really is missing.",
      "SQL uses THREE-VALUED LOGIC: TRUE, FALSE and UNKNOWN. Any comparison "
      "involving NULL yields UNKNOWN, and WHERE keeps only rows evaluating to TRUE. "
      "So `= NULL`, `<> NULL` and `!= NULL` all return zero rows. The test for "
      "missingness is IS NULL / IS NOT NULL, which are the only operators that "
      "return TRUE or FALSE for a NULL input.",
      "shop", ["null", "three-valued-logic", "where"],
      query="select name from customers where city = null",
      output="(0 rows)",
      gotcha="No error, no warning, zero rows — even though Cy's city genuinely is NULL. "
             "This is the single most expensive silent bug in SQL, because the query "
             "looks correct and the empty result looks like a legitimate answer.",
      pitfalls="MySQL, uniquely, offers `<=>` as a NULL-safe equality. Postgres and "
               "SQLite have `IS DISTINCT FROM` / `IS NOT DISTINCT FROM`, which is the "
               "standard spelling and the one to know.",
      difficulty="Easy", frequency="Asked in almost every SQL interview",
      mnemonic="NULL is not a value, it is the absence of one. You cannot compare it, only "
               "ask whether it is there."),

    Q("nulls", "IS NULL — the only comparison that works",
      "The way to find missing values. `IS NULL` and `IS NOT NULL` are the only "
      "operators that give a straight yes or no when the value is missing.",
      "IS NULL evaluates to TRUE or FALSE, never UNKNOWN, so it is usable in WHERE. "
      "It is a unary predicate, not a comparison, which is why it is spelled with a "
      "keyword rather than an operator. `IS NOT DISTINCT FROM` generalises it to a "
      "NULL-safe equality between two expressions, treating NULL as equal to NULL.",
      "shop", ["null", "is-null", "where"],
      query="select name from customers where city is null",
      output="""name
----
Cy
(1 row)""",
      example="To compare two nullable columns treating NULL as a value: "
              "`WHERE a IS NOT DISTINCT FROM b` (Postgres, SQLite) or `WHERE a <=> b` "
              "(MySQL) or the portable `WHERE (a = b) OR (a IS NULL AND b IS NULL)`.",
      pitfalls="An index CAN serve IS NULL in Postgres and SQLite. The old advice that "
               "'indexes do not store NULLs' is Oracle-specific — Oracle omits rows from "
               "a single-column B-tree index when the key is NULL, so IS NULL forces a "
               "full scan there and nowhere else.",
      difficulty="Easy", frequency="Universal",
      mnemonic="IS NULL, never = NULL. The keyword is the whole point."),

    Q("nulls", "NOT IN with a NULL in the list returns nothing",
      "The worst NULL trap, because the query is idiomatic, reviewed and wrong. If "
      "the list you are checking against contains even one missing value, "
      "`NOT IN` returns no rows at all — whatever your data says.",
      "`x NOT IN (a, b, NULL)` expands to `x <> a AND x <> b AND x <> NULL`. The "
      "last term is UNKNOWN, and TRUE AND UNKNOWN is UNKNOWN, so the whole condition "
      "can never be TRUE and no row is returned. `IN` does not have this problem for "
      "matches — a match short-circuits to TRUE — only for non-matches, which is why "
      "`IN` looks fine and `NOT IN` breaks.",
      "shop", ["null", "not-in", "subquery", "three-valued-logic"],
      query="select name from customers\n where id not in (select customer_id from orders)",
      output="(0 rows)",
      gotcha="THE CORRECT ANSWER IS Cy AND Ed — neither has ever ordered. The query "
             "returns nothing because one order is a guest checkout with a NULL "
             "customer_id, and that single NULL poisons the entire NOT IN. Add a "
             "customer with no orders and it still returns nothing. The query is not "
             "'a bit off'; it is unconditionally empty.",
      pitfalls="`NOT EXISTS` does not have this problem, and neither does a LEFT JOIN "
               "with `WHERE right.id IS NULL`. Both are also usually faster, because "
               "the planner can stop at the first match instead of materialising the "
               "whole list. There is no case where NOT IN over a nullable subquery is "
               "the right choice.",
      followups="Why does IN not break the same way? Because OR is different: "
                "`TRUE OR UNKNOWN` is TRUE, so a genuine match still returns the row. "
                "Only the absence of a match becomes UNKNOWN rather than FALSE.",
      difficulty="Hard", frequency="A favourite senior screening question",
      mnemonic="One NULL in a NOT IN list empties the whole result. Use NOT EXISTS."),

    Q("nulls", "NOT EXISTS — the version that is actually correct",
      "The right way to ask 'which rows have no match'. It checks each row "
      "individually and answers yes or no, so a missing value somewhere else cannot "
      "poison the answer.",
      "NOT EXISTS evaluates a correlated subquery per outer row and asks only "
      "whether it produced any rows. That is a two-valued question — rows or no "
      "rows — so three-valued logic never enters. It is also cheaper: the planner "
      "can stop at the first matching row (a semi-join) instead of building the "
      "full list.",
      "shop", ["null", "not-exists", "anti-join", "subquery"],
      query="select name from customers c\n"
            " where not exists (select 1 from orders o where o.customer_id = c.id)\n"
            " order by name",
      output="""name
----
Cy
Ed
(2 rows)""",
      gotcha="This is the SAME question as the NOT IN entry, on the SAME data, and it "
             "returns 2 rows where NOT IN returned 0. Nothing about the data changed. "
             "Run both against your own database before trusting either.",
      example="The third correct form is an anti-join: "
              "`SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
              "WHERE o.id IS NULL`. Same result, and on some planners the same plan.",
      pitfalls="`SELECT 1` inside EXISTS is conventional and means nothing — the "
               "subquery's columns are never read, only whether it produced a row. "
               "`SELECT *` is equally correct and equally fast.",
      difficulty="Medium", frequency="Very common; the pairing with NOT IN is the question",
      mnemonic="EXISTS asks 'are there any?' — a yes/no question NULL cannot make unknown."),

    Q("nulls", "Concatenating with NULL swallows the whole string",
      "Joining text together with a missing piece does not skip the piece — it "
      "makes the entire result missing. One absent field turns a whole label into "
      "nothing.",
      "In standard SQL, `a || b` is NULL if either operand is NULL, because NULL "
      "propagates through nearly every operator and function. The same is true of "
      "arithmetic: `price * quantity` with a NULL quantity is NULL, not the price. "
      "COALESCE(x, fallback) is the fix and it must be applied to EVERY nullable "
      "part, not just the one you noticed.",
      "shop", ["null", "concat", "coalesce"],
      query="select name, city, name || ', ' || city as label\n"
            "  from customers order by name",
      output="""name  city    label
----  ------  -----------
Ana   London  Ana, London
Bo    Paris   Bo, Paris
Cy    NULL    NULL
Di    London  Di, London
Ed    Tokyo   Ed, Tokyo
(5 rows)""",
      gotcha="Cy's label is NULL — not 'Cy, ' as most people expect. The name was "
             "perfectly good; the missing city destroyed the whole expression. In a "
             "report this shows as a blank cell where you expected a partial value.",
      portability="MySQL's `CONCAT()` deliberately SKIPS NULLs and returns the rest, "
                  "which is the opposite behaviour — but MySQL's `||` is logical OR by "
                  "default, not concatenation. Oracle's `||` also ignores NULLs, because "
                  "Oracle treats the empty string as NULL. Three engines, three answers, "
                  "which is why CONCAT_WS or explicit COALESCE is the portable choice.",
      example="`COALESCE(name,'?') || ', ' || COALESCE(city,'unknown')` gives "
              "'Cy, unknown'. Or CONCAT_WS(', ', name, city), which skips NULL parts and "
              "handles the separator for you.",
      difficulty="Medium", frequency="Common, usually discovered in production",
      mnemonic="NULL is contagious. One missing operand makes the whole expression missing."),

    Q("nulls", "GROUP BY puts all the NULLs in one group",
      "Grouping treats every missing value as the same missing value, even though "
      "comparing two missing values never returns true. It is an inconsistency in "
      "the language and you simply have to know it.",
      "GROUP BY, DISTINCT, UNION and window PARTITION BY all treat NULLs as EQUAL "
      "to each other for the purpose of forming groups, while the `=` operator "
      "treats them as not comparable. The standard defines grouping in terms of "
      "'not distinct from' rather than equality, which is what resolves the "
      "apparent contradiction — but it means the same two values are 'the same' in "
      "one clause and 'unknown' in another.",
      "shop", ["null", "group-by", "distinct"],
      query="select count(*) as rows, count(city) as cities,\n"
            "       count(distinct city) as distinct_cities\n  from customers",
      output="""rows  cities  distinct_cities
----  ------  ---------------
5     4       3
(1 row)""",
      gotcha="5 rows, 4 with a city, 3 distinct cities — and COUNT(DISTINCT city) does "
             "NOT count NULL as a value, even though GROUP BY city WOULD produce a NULL "
             "group. So `count(distinct city)` and `count(*) from (select distinct city)` "
             "differ by exactly one whenever any city is NULL.",
      pitfalls="UNION deduplicates and treats NULLs as equal; UNION ALL does not "
               "deduplicate at all and is faster. Reach for UNION ALL unless you "
               "specifically need duplicates removed.",
      difficulty="Medium", frequency="A good discriminating question",
      mnemonic="For GROUPING, NULLs are the same. For COMPARING, they are not. Both are true."),

    ]

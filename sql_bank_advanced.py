"""SQL bank — window functions, subqueries and CTEs, writes, and indexes.

The rungs that separate someone who can query from someone who can be given
a reporting problem. Window functions are the single highest-value thing on
this page: half the questions people solve with a self-join or a correlated
subquery are one window function.

Every stated output came out of sqlite3 and is re-checked by verify().
"""


def build(Q):
    return [

    # ══════════════════ WINDOW ══════════════════

    Q("window", "ROW_NUMBER and the top-N-per-group problem",
      "Number the rows within each group, in an order you choose, then keep the "
      "ones numbered 1 (or 1 to 3). This is how you answer 'the largest order per "
      "customer', 'the latest event per user', 'the top 3 products per category'.",
      "ROW_NUMBER() OVER (PARTITION BY x ORDER BY y) assigns 1, 2, 3... within each "
      "partition. Unlike GROUP BY it does NOT collapse rows — every input row comes "
      "out, with a number attached — so you keep every column and filter on the "
      "number in an outer query. Window functions cannot be used in WHERE (they are "
      "evaluated after it), so top-N always needs the extra layer.",
      "shop", ["window", "row-number", "top-n"],
      query="select id, customer_id, amount,\n"
            "       row_number() over (partition by customer_id order by amount desc) as rn\n"
            "  from orders\n where customer_id is not null\n"
            " order by customer_id, rn",
      output="""id  customer_id  amount  rn
--  -----------  ------  --
10  1            120     1
11  1            45.5    2
16  1            30      3
13  2            200     1
12  2            80      2
14  4            15      1
(6 rows)""",
      example="To keep only the biggest order per customer, wrap it:\n"
              "  SELECT * FROM (\n"
              "    SELECT ..., ROW_NUMBER() OVER (PARTITION BY customer_id\n"
              "                                   ORDER BY amount DESC) rn\n"
              "    FROM orders\n"
              "  ) WHERE rn = 1;",
      gotcha="You cannot write `WHERE row_number() OVER (...) = 1`. Window functions are "
             "evaluated AFTER WHERE, so the name is not available there. The subquery "
             "or CTE is not stylistic, it is required by the evaluation order.",
      pitfalls="ROW_NUMBER is non-deterministic when the ORDER BY has ties — two orders "
               "of the same amount could get 1 and 2 in either arrangement, so 'the top "
               "one' changes between runs. Add a tie-breaker (usually the primary key) "
               "whenever the result is persisted or paginated.",
      difficulty="Medium", frequency="Extremely common — the standard SQL screening question",
      mnemonic="GROUP BY collapses, OVER does not. Top-N-per-group is ROW_NUMBER then filter."),

    Q("window", "RANK vs DENSE_RANK vs ROW_NUMBER — the three are different",
      "All three number rows. They differ only in what they do about ties, and the "
      "difference is the whole question: does a tie share a number, and does the "
      "next number skip.",
      "ROW_NUMBER always gives 1,2,3,4 — ties get arbitrary distinct numbers. RANK "
      "gives tied rows the SAME number and then SKIPS: 1,2,3,3,5. DENSE_RANK gives "
      "tied rows the same number and does not skip: 1,2,3,3,4. RANK is what a sports "
      "league table does (two in third place, nobody in fourth); DENSE_RANK is what "
      "'the top 3 distinct salaries' needs.",
      "staff", ["window", "rank", "dense-rank", "row-number"],
      query="select name, dept, salary,\n"
            "       rank()       over (order by salary desc) as rnk,\n"
            "       dense_rank() over (order by salary desc) as dense,\n"
            "       row_number() over (order by salary desc) as rn\n"
            "  from employees\n order by salary desc, name",
      output="""name   dept   salary  rnk  dense  rn
-----  -----  ------  ---  -----  --
Root   exec   200000  1    1      1
Mira   eng    150000  2    2      2
Nadia  eng    120000  3    3      3
Omar   eng    120000  3    3      4
Priya  sales  110000  5    4      5
Quinn  sales  90000   6    5      6
Rhys   sales  90000   6    5      7
Sara   NULL   70000   8    6      8
(8 rows)""",
      gotcha="Read the Priya row: rank 5, dense_rank 4, row_number 5. RANK skipped 4 "
             "because two people tied at 3; DENSE_RANK did not. And read the last row: "
             "rank 8 against dense_rank 6 — after two ties the two columns are two "
             "apart, and which one is 'the answer' depends entirely on the question.",
      example="'Find the 3rd highest salary' is DENSE_RANK = 3 (110000, the third "
              "distinct salary). With RANK = 3 you would get 120000 and two people. "
              "The interview question is almost always asking for DENSE_RANK.",
      pitfalls="With no PARTITION BY the window is the whole result set, which is "
               "usually what a leaderboard wants and rarely what a per-group question "
               "wants. Forgetting PARTITION BY ranks everyone against everyone.",
      difficulty="Medium", frequency="Very common — 'Nth highest salary' is a stock question",
      mnemonic="ROW_NUMBER never ties. RANK ties and skips. DENSE_RANK ties and does not."),

    Q("window", "Running totals with a window frame",
      "Add up everything from the start of the result to the current row, on every "
      "row. A running balance, a cumulative revenue line, a burn-down.",
      "SUM(x) OVER (ORDER BY y) computes over a FRAME — the set of rows the "
      "aggregate sees for each output row. With an ORDER BY and no explicit frame, "
      "the default is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW, which is "
      "the running total. Writing the frame explicitly as ROWS is worth doing, "
      "because RANGE and ROWS differ when the ORDER BY has ties.",
      "shop", ["window", "running-total", "frame"],
      query="select id, amount,\n"
            "       sum(amount) over (order by id\n"
            "                         rows between unbounded preceding and current row) as running\n"
            "  from orders\n order by id",
      output="""id  amount  running
--  ------  -------
10  120     120
11  45.5    165.5
12  80      245.5
13  200     445.5
14  15      460.5
15  60      520.5
16  30      550.5
(7 rows)""",
      gotcha="ROWS and RANGE are not synonyms. ROWS counts physical rows; RANGE groups "
             "PEERS — all rows tying on the ORDER BY get the same frame and therefore "
             "the same running total. On a date column with several rows per day, RANGE "
             "gives every row of a day the day's full cumulative value and ROWS gives "
             "them a within-day sequence. Both are useful; only one is what you meant.",
      example="SUM(x) OVER () with an empty window is the GRAND TOTAL on every row, "
              "which is how you compute 'this row's share of the total' without a "
              "self-join: `amount / sum(amount) over ()`.",
      pitfalls="A window function does not filter. `SUM(...) OVER (...)` on a query "
               "returning 7 rows returns 7 rows. If you want one row, you wanted "
               "GROUP BY.",
      difficulty="Medium", frequency="Common in analytics-flavoured interviews",
      mnemonic="OVER (ORDER BY ...) with no frame is a running total. Say ROWS explicitly."),

    Q("window", "LAG and LEAD — comparing a row to its neighbour",
      "Look at the previous (or next) row from within the current one. Time between "
      "events, change since last reading, the page someone came from.",
      "LAG(expr, n=1, default=NULL) OVER (PARTITION BY ... ORDER BY ...) returns "
      "expr from n rows earlier in the partition. LEAD looks forward. The first row "
      "of each partition has no previous row, so LAG returns the default — NULL "
      "unless you supply one, which is why any arithmetic on a LAG result needs "
      "thinking about.",
      "events", ["window", "lag", "lead", "sessionisation"],
      query="select user_id, page, ts,\n"
            "       lag(page) over (partition by user_id order by ts) as prev_page\n"
            "  from pageviews\n order by user_id, ts",
      output="""user_id  page      ts                prev_page
-------  --------  ----------------  ---------
1        /home     2024-06-01 09:00  NULL
1        /pricing  2024-06-01 09:02  /home
1        /signup   2024-06-01 09:05  /pricing
1        /home     2024-06-03 08:00  /signup
2        /home     2024-06-01 10:00  NULL
2        /home     2024-06-01 10:04  /home
3        /pricing  2024-06-02 11:00  NULL
3        /home     2024-06-02 11:30  /pricing
(8 rows)""",
      gotcha="Each user's first row has prev_page NULL — the PARTITION BY resets the "
             "window, so user 2's first row does not see user 1's last. Without the "
             "PARTITION BY it would, and you would have invented a page transition "
             "between two different people.",
      example="Sessionisation in one expression: a new session starts wherever the gap "
              "from the previous event exceeds 30 minutes.\n"
              "  CASE WHEN julianday(ts) - julianday(LAG(ts) OVER w) > 30.0/1440\n"
              "       THEN 1 ELSE 0 END\n"
              "then a running SUM over that gives each row a session number.",
      pitfalls="LAG needs a deterministic ORDER BY. Two events with the same timestamp "
               "means 'the previous row' is arbitrary, and the derived durations flip "
               "sign between runs.",
      difficulty="Medium", frequency="Common in data-heavy roles",
      mnemonic="LAG looks back, LEAD looks forward, PARTITION BY stops it looking at "
               "someone else's rows."),

    Q("window", "Window vs GROUP BY — keeping the detail",
      "GROUP BY gives you one row per group and throws the individual rows away. A "
      "window function gives you the group's answer ATTACHED to every original row. "
      "When you want 'this employee's salary AND their department average' in one "
      "row, only the window can do it.",
      "AVG(salary) OVER (PARTITION BY dept) computes the department average and "
      "reports it on every row of that department, without collapsing anything. The "
      "equivalent with GROUP BY needs a second query and a join back to the detail. "
      "That is the whole reason window functions exist.",
      "staff", ["window", "group-by", "partition-by"],
      query="select name, dept, salary,\n"
            "       avg(salary) over (partition by dept) as dept_avg\n"
            "  from employees\n order by dept, name",
      output="""name   dept   salary  dept_avg
-----  -----  ------  --------
Sara   NULL   70000   70000
Mira   eng    150000  130000
Nadia  eng    120000  130000
Omar   eng    120000  130000
Root   exec   200000  200000
Priya  sales  110000  96666.7
Quinn  sales  90000   96666.7
Rhys   sales  90000   96666.7
(8 rows)""",
      gotcha="Sara has no department, and PARTITION BY puts all the NULLs in ONE "
             "partition — the same rule GROUP BY uses. She is her own department of one, "
             "so her 'department average' is her own salary. On real data with many "
             "unassigned rows that partition is large and the average is meaningless.",
      example="'Everyone paid above their department average' is now one query:\n"
              "  SELECT * FROM (\n"
              "    SELECT *, AVG(salary) OVER (PARTITION BY dept) a FROM employees\n"
              "  ) WHERE salary > a;\n"
              "Before window functions this needed a correlated subquery per row.",
      difficulty="Medium", frequency="Very common",
      mnemonic="GROUP BY collapses to one row per group. OVER attaches the group's answer "
               "to every row."),

    # ══════════════════ SUBQUERY ══════════════════

    Q("subquery", "CTEs — naming a subquery so the query reads top to bottom",
      "A WITH clause lets you name an intermediate result and then use it by name. "
      "The same query written with nested subqueries has to be read inside-out; "
      "with CTEs it reads in the order the work happens.",
      "A Common Table Expression is a named subquery available to the rest of the "
      "statement. Several can be chained, and later ones can reference earlier ones. "
      "It is primarily a READABILITY tool — most planners inline a CTE exactly as "
      "they would a subquery, so it usually costs nothing.",
      "shop", ["cte", "with", "readability"],
      query="with paid as (\n"
            "  select * from orders where status = 'paid'\n"
            ")\n"
            "select customer_id, count(*) as n, sum(amount) as total\n"
            "  from paid\n group by customer_id\n order by customer_id",
      output="""customer_id  n  total
-----------  -  -----
NULL         1  60
1            3  195.5
2            1  200
(3 rows)""",
      gotcha="The NULL group is the guest order. GROUP BY keeps it as its own group, so "
             "a report grouped by customer has a row belonging to no customer — which "
             "is correct, and which every downstream join will then drop.",
      portability="Postgres before v12 treated a CTE as an OPTIMISATION FENCE: it was "
                  "always materialised, never inlined, which was sometimes a useful "
                  "hint and often a performance trap. Since v12 it inlines by default "
                  "and `WITH x AS MATERIALIZED (...)` restores the old behaviour "
                  "explicitly. Advice written before 2019 about CTEs being slow in "
                  "Postgres is out of date.",
      pitfalls="A CTE referenced twice may be evaluated twice unless the planner "
               "materialises it. If the CTE is expensive and used in several places, "
               "measure — or materialise it explicitly.",
      difficulty="Easy", frequency="Common; expected vocabulary at senior level",
      mnemonic="WITH names a step. The query then reads in the order it happens."),

    Q("subquery", "Recursive CTEs — walking a hierarchy",
      "Follow a chain of arbitrary length: every employee under a manager, every "
      "comment under a comment, every part inside a part. A plain join reaches one "
      "level; recursion reaches all of them.",
      "A RECURSIVE CTE has two halves joined by UNION ALL: an ANCHOR that produces "
      "the starting rows, and a RECURSIVE TERM that references the CTE itself to "
      "produce the next level. It repeats until the recursive term returns nothing. "
      "A depth column is worth carrying whether or not you need it, because it is "
      "the only defence against a cycle in the data.",
      "staff", ["cte", "recursive", "hierarchy", "graph"],
      query="with recursive chain(id, name, depth) as (\n"
            "  select id, name, 0 from employees where manager is null\n"
            "  union all\n"
            "  select e.id, e.name, c.depth + 1\n"
            "    from employees e join chain c on e.manager = c.id\n"
            ")\n"
            "select depth, name from chain order by depth, name",
      output="""depth  name
-----  -----
0      Root
0      Sara
1      Mira
1      Priya
2      Nadia
2      Omar
2      Quinn
2      Rhys
(8 rows)""",
      gotcha="Sara appears at depth 0 alongside Root, because the anchor is 'manager IS "
             "NULL' and she has no manager either — she is an unassigned starter, not a "
             "second CEO. An anchor that says 'the root' should usually name the root "
             "explicitly rather than infer it from a NULL.",
      pitfalls="If the data contains a CYCLE — A manages B manages A, which a bad import "
               "can easily create — the recursion never terminates. Postgres has "
               "CYCLE detection; everywhere else you carry the path and add "
               "`WHERE NOT path LIKE '%' || e.id || '%'`, or simply cap the depth.",
      followups="UNION ALL, not UNION: UNION deduplicates on every iteration, which is "
                "both slower and can mask a cycle by silently discarding the repeat.",
      difficulty="Hard", frequency="Asked when the role touches hierarchical data",
      mnemonic="Anchor, UNION ALL, recursive term. Carry a depth so a cycle cannot hang it."),

    Q("subquery", "Correlated subqueries — one query per row",
      "A subquery that mentions a column from the outer query has to be re-evaluated "
      "for every outer row. Readable, and the classic reason a query that worked on "
      "test data crawls on production data.",
      "A correlated subquery is logically executed once per outer row: 1,000 outer "
      "rows means 1,000 executions. Modern planners often rewrite simple ones into a "
      "join or a semi-join, but the rewrite is not guaranteed and not universal. The "
      "same question expressed as a JOIN or a WINDOW FUNCTION is usually both "
      "clearer and reliably faster.",
      "shop", ["subquery", "correlated", "performance"],
      query="select c.name,\n"
            "       (select count(*) from orders o where o.customer_id = c.id) as orders\n"
            "  from customers c\n order by c.name",
      output="""name  orders
----  ------
Ana   3
Bo    2
Cy    0
Di    1
Ed    0
(5 rows)""",
      gotcha="A correlated subquery in the SELECT list returns 0 for Cy and Ed, where a "
             "LEFT JOIN with COUNT(*) would return 1. The scalar subquery gets it right "
             "for free, which is a genuine advantage — and it costs a query per row to "
             "get there.",
      example="The same result three ways, in increasing order of scalability:\n"
              "  scalar subquery per row      (shown above)\n"
              "  LEFT JOIN + GROUP BY         one pass, but you must COUNT the right column\n"
              "  a pre-aggregated CTE joined  one pass, and reusable",
      pitfalls="A scalar subquery must return AT MOST ONE ROW. Returning two is a "
               "runtime error in Postgres and SQL Server; SQLite quietly takes the "
               "first, which is worse — the query keeps working and the answer is "
               "arbitrary.",
      difficulty="Medium", frequency="Common; the performance follow-up is the point",
      mnemonic="Correlated means once per outer row. Fine on 100 rows, fatal on 10 million."),

    # ══════════════════ MODIFY ══════════════════

    Q("modify", "UPSERT — insert, or update if it is already there",
      "Insert a row; if one with that key already exists, update it instead. Doing "
      "this as a SELECT followed by an INSERT or UPDATE is a race: two callers can "
      "both find nothing and both insert.",
      "`INSERT ... ON CONFLICT (key) DO UPDATE SET ...` performs the check and the "
      "write as one atomic statement, so there is no window for a second writer. "
      "`excluded` refers to the row that was proposed for insertion, which is how "
      "the update clause reaches the new values. It requires a UNIQUE constraint or "
      "index on the conflict target — without one there is nothing to conflict with.",
      "shop", ["insert", "upsert", "concurrency"],
      query="insert into customers (id, name, city, joined)\n"
            "  values (1, 'Ana Updated', 'Berlin', '2024-01-05')\n"
            "  on conflict(id) do update set city = excluded.city;\n"
            "select id, name, city from customers where id = 1",
      output="""id  name  city
--  ----  ------
1   Ana   Berlin
(1 row)""",
      gotcha="The name is still 'Ana', not 'Ana Updated' — the DO UPDATE clause only "
             "set `city`, so every other proposed value was discarded. An upsert "
             "updates exactly the columns you list, and forgetting one is a silent "
             "partial write.",
      portability="Postgres and SQLite use `ON CONFLICT ... DO UPDATE`. MySQL uses "
                  "`ON DUPLICATE KEY UPDATE` with `VALUES(col)` instead of "
                  "`excluded.col`. SQL Server and Oracle use `MERGE`, which is more "
                  "general and notoriously easy to get wrong. There is no portable "
                  "spelling.",
      pitfalls="`ON CONFLICT DO NOTHING` is the other half, and it does not report "
               "whether it inserted. Add `RETURNING id` (Postgres, SQLite 3.35+) if the "
               "caller needs to know which happened.",
      difficulty="Medium", frequency="Common in system-design-adjacent questions",
      mnemonic="Check-then-insert is a race. UPSERT is one statement, and the database wins."),

    Q("modify", "UPDATE with a subquery, and the WHERE you must not forget",
      "Change rows that match a condition defined by another table. The dangerous "
      "part is that omitting the WHERE clause updates EVERY row, immediately, with "
      "no confirmation.",
      "UPDATE ... WHERE col IN (subquery) is the portable form; Postgres and MySQL "
      "also support UPDATE ... FROM and UPDATE ... JOIN respectively, which are "
      "usually faster because they can join rather than re-evaluate. Whichever "
      "form, the discipline is the same: write the SELECT first, read the row count, "
      "then convert it to an UPDATE.",
      "shop", ["update", "subquery", "safety"],
      query="update orders set status = 'void'\n"
            " where customer_id in (select id from customers where city is null);\n"
            "select id, status from orders order by id",
      output="""id  status
--  --------
10  paid
11  paid
12  refunded
13  paid
14  pending
15  paid
16  paid
(7 rows)""",
      gotcha="NOTHING WAS UPDATED to 'void' — and the reason is the NULL rule again. "
             "The subquery returns Cy's id, but Cy has no orders, so no order matches. "
             "The statement succeeded, changed nothing, and reported success. Always "
             "check the affected-row count against what you expected.",
      example="Order 12 already reads 'refunded' in the seed data — it was never "
              "touched by this statement. Every entry in this bank runs against its own "
              "fresh copy of the schema, so nothing another entry did can leak in, and "
              "the only changes visible here are the ones this query made. Which in "
              "this case is none.",
      pitfalls="Wrap destructive statements in a transaction while developing: "
               "`BEGIN; UPDATE ...; SELECT ...; ROLLBACK;` lets you see the effect and "
               "then undo it. Autocommit is the reason a missing WHERE is unrecoverable.",
      difficulty="Medium", frequency="Common as a safety question",
      mnemonic="Write it as a SELECT first. If the count surprises you, the WHERE is wrong."),

    Q("modify", "DELETE, and why the table does not get smaller",
      "Removing rows frees the space for that table to reuse. It does not give the "
      "space back to the operating system, and the file on disk stays exactly the "
      "same size.",
      "DELETE marks rows dead and updates every index that pointed at them. The "
      "pages become free for that table to reuse but are not returned to the "
      "filesystem — reclaiming them needs VACUUM (Postgres, SQLite) or OPTIMIZE "
      "TABLE (MySQL), which rewrites the table and takes a lock. TRUNCATE discards "
      "the storage wholesale instead, which is why it is fast and why it fires no "
      "row triggers.",
      "shop", ["delete", "truncate", "storage"],
      query="delete from orders where status = 'pending';\n"
            "select count(*) as remaining from orders",
      output="""remaining
---------
6
(1 row)""",
      gotcha="One row went, six remain, and the database file is exactly the size it was "
             "before. On a table where you have just deleted ten million rows that "
             "surprises people badly — the disk-space alert does not clear until a "
             "VACUUM runs.",
      pitfalls="A DELETE with no WHERE on a large table holds locks and grows the undo "
               "log for the whole duration. Batch it: "
               "`DELETE FROM t WHERE id IN (SELECT id FROM t WHERE ... LIMIT 10000)` in "
               "a loop, committing each batch, so the table stays usable.",
      followups="DELETE fires row triggers and is transactional everywhere. TRUNCATE "
                "fires none and, in MySQL and Oracle, COMMITS IMPLICITLY — so a "
                "TRUNCATE inside a transaction cannot be rolled back there, while in "
                "Postgres and SQLite it can.",
      difficulty="Medium", frequency="Common",
      mnemonic="DELETE frees pages for REUSE, not for the filesystem. VACUUM returns them."),

    # ══════════════════ INDEX ══════════════════

    Q("index", "What EXPLAIN actually tells you",
      "Ask the database what it PLANS to do before it does it. The one thing to look "
      "for is whether it will read the whole table or jump straight to the rows it "
      "needs.",
      "EXPLAIN shows the access path the planner chose. The words differ by engine — "
      "SQLite says SCAN and SEARCH, Postgres says Seq Scan and Index Scan, MySQL "
      "shows a `type` column — but the distinction is the same everywhere: a full "
      "scan reads every row, an index lookup reads only the matching ones. A scan is "
      "not automatically wrong (on a small table it is faster than an index), and on "
      "a large table it usually is.",
      "shop", ["index", "explain", "query-plan"],
      query="explain query plan select * from orders where customer_id = 1",
      output="""id  parent  notused  detail
--  ------  -------  -----------
2   0       0        SCAN orders
(1 row)""",
      gotcha="SCAN means every row is read to find the matching ones. On seven rows that "
             "is instant; on seven million it is the difference between a page that "
             "loads and one that times out. The word to look for is SCAN on a table you "
             "know is big.",
      portability="`EXPLAIN QUERY PLAN` is SQLite's spelling. Postgres uses `EXPLAIN` "
                  "and, crucially, `EXPLAIN ANALYZE` which actually RUNS the query and "
                  "reports real timings alongside the estimates — the gap between "
                  "estimated and actual rows is the single most useful diagnostic in "
                  "Postgres and has no SQLite equivalent.",
      difficulty="Medium", frequency="Very common",
      mnemonic="EXPLAIN before you optimise. SCAN on a big table is the thing you are looking for."),

    Q("index", "The same query with an index",
      "An index is a sorted copy of one or more columns, with pointers back to the "
      "rows. Because it is sorted, the database can jump to the right place instead "
      "of reading everything.",
      "Adding a B-tree index on the filtered column changes the plan from a full "
      "scan to an index seek. The cost is paid on WRITES — every INSERT, UPDATE and "
      "DELETE must maintain every index on the table — and in storage. An index is a "
      "read/write trade, deliberately made per column, not a thing you add to "
      "everything.",
      "shop", ["index", "b-tree", "explain"],
      query="create index ix_orders_customer on orders(customer_id);\n"
            "explain query plan select * from orders where customer_id = 1",
      output="""id  parent  notused  detail
--  ------  -------  ------------------------------------------------------------
3   0       0        SEARCH orders USING INDEX ix_orders_customer (customer_id=?)
(1 row)""",
      gotcha="Compare with the previous entry: SCAN became SEARCH USING INDEX, and the "
             "plan now names the index and the column it matched on. That named column "
             "is what tells you a COMPOSITE index is being used only partially - "
             "`(a=? AND b=?)` uses both, `(a=?)` on a two-column index means the second "
             "column is not helping.",
      example="A composite index on (a, b) serves `WHERE a = ?`, `WHERE a = ? AND b = ?` "
              "and `ORDER BY a, b`. It does NOT serve `WHERE b = ?` alone — the index is "
              "sorted by a first, so rows with a given b are scattered throughout it. "
              "This is the leftmost-prefix rule and it decides column order.",
      pitfalls="Every index makes writes slower and takes disk. On a write-heavy table "
               "an unused index is pure cost — most engines can report index usage "
               "statistics, and dropping the never-used ones is usually free "
               "performance.",
      difficulty="Medium", frequency="Universal",
      mnemonic="Index = sorted copy + pointers. Faster reads, slower writes, more disk."),

    Q("index", "Wrapping a column in a function disables its index",
      "An index stores the column's values. Ask a question about a FUNCTION of the "
      "column and the index cannot help, because it does not contain those values — "
      "so the database reads everything and computes the function on every row.",
      "A predicate is SARGABLE (Search ARGument able) when the indexed column appears "
      "bare on one side of the comparison. `WHERE substr(placed,1,7) = '2024-03'`, "
      "`WHERE UPPER(name) = 'ANA'` and `WHERE amount * 2 > 100` are all non-sargable "
      "and force a scan. Rewrite as a RANGE on the bare column — or build an "
      "expression index on exactly that function, which Postgres and SQLite support.",
      "shop", ["index", "sargable", "explain", "performance"],
      query="create index ix_orders_placed on orders(placed);\n"
            "explain query plan\n"
            "select * from orders where substr(placed,1,7) = '2024-03'",
      output="""id  parent  notused  detail
--  ------  -------  -----------
2   0       0        SCAN orders
(1 row)""",
      gotcha="The index on `placed` exists and is not used — SCAN, not SEARCH. The "
             "function around the column is the entire reason. This is the most common "
             "cause of 'we have an index and it is still slow', and EXPLAIN says so in "
             "one word.",
      example="The sargable rewrite of the same question:\n"
              "  WHERE placed >= '2024-03-01' AND placed < '2024-04-01'\n"
              "which uses the index as a range scan. The general shape: turn "
              "`f(column) = value` into `column BETWEEN a AND b`.\n"
              "Or build the index the query wants: "
              "`CREATE INDEX ... ON orders(substr(placed,1,7))`.",
      pitfalls="The same trap hides in implicit conversions. Comparing an indexed "
               "VARCHAR column to a number makes the engine cast the column, which is a "
               "function, which disables the index — and nothing in the query looks like "
               "a function call.",
      difficulty="Hard", frequency="Very common as a debugging question",
      mnemonic="Keep the indexed column bare on its side of the comparison."),

    ]

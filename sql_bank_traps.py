"""SQL bank — the traps.

Short queries whose answer is not what it looks like. This is the SQL
equivalent of java_bank's "what does this print" rung: the question is
always the same shape — read it, commit to an answer, then look.

Every result here came out of sqlite3. Where an engine genuinely disagrees
the entry says so, because a trap that only exists on one engine is worth
knowing as a portability fact rather than as a rule.
"""


def build(Q):
    return [

    Q("traps", "Integer division truncates, silently",
      "Dividing two whole numbers gives a whole number. 7 divided by 2 is 3, not "
      "3.5, and nothing warns you — the fractional part is simply discarded.",
      "In SQL, as in C and Java, division of two INTEGER operands is integer "
      "division. The result is truncated toward zero. Making either operand a REAL "
      "— by writing 2.0, or by CASTing — switches to floating-point division. This "
      "is the single most common cause of a percentage column that reads 0.",
      "shop", ["arithmetic", "cast", "type"],
      query="select 7/2 as int_div, 7.0/2 as real_div, cast(7 as real)/2 as cast_div",
      output="""int_div  real_div  cast_div
-------  --------  --------
3        3.5       3.5
(1 row)""",
      gotcha="The classic version is a rate: `select passed/total` where both are "
             "integer counts. Every result under 100% comes back as 0, the dashboard "
             "shows a column of zeros, and it looks like a data pipeline problem rather "
             "than an arithmetic one. `100.0 * passed / total` fixes it.",
      pitfalls="Order matters: `100 * passed / total` still truncates if passed/total is "
               "evaluated first — it is not, because * and / are left-associative, so "
               "this one is fine. But `passed / total * 100` truncates FIRST and then "
               "multiplies, giving 0 or 100 and nothing between.",
      portability="Postgres, SQL Server and Oracle all truncate integer division. MySQL "
                  "is the exception: `/` always produces a decimal, and `DIV` is its "
                  "integer division operator. Code that relies on truncation breaks "
                  "moving off MySQL, and code that relies on a decimal breaks moving TO "
                  "the others.",
      difficulty="Easy", frequency="Very common — and the cause of many silent zeros",
      mnemonic="int / int = int. Multiply by 100.0, not 100."),

    Q("traps", "UNION deduplicates; UNION ALL does not",
      "Stacking two result sets on top of each other. UNION quietly removes "
      "duplicate rows and pays for a sort to do it. UNION ALL keeps everything and "
      "is faster. Most code wants ALL and writes UNION out of habit.",
      "UNION performs a DISTINCT over the combined result, which requires a sort or "
      "hash of every row. UNION ALL concatenates. Where you know the two sets are "
      "disjoint — different date ranges, different statuses — the deduplication is "
      "pure cost and removes nothing.",
      "shop", ["union", "duplicates", "performance"],
      query="select count(*) as n\n"
            "  from (select city from customers\n"
            "        union all\n"
            "        select city from customers)",
      output="""n
--
10
(1 row)""",
      gotcha="10 with UNION ALL. Change it to UNION and it returns 4 — the four distinct "
             "cities including the NULL one, from ten rows. Not 5, because UNION treats "
             "the two NULLs as duplicates of each other, the same rule GROUP BY uses "
             "and the opposite of what `=` would say.",
      pitfalls="UNION requires the two sides to have the same number of columns and "
               "compatible types, and it takes the column names from the FIRST branch. "
               "A second branch whose columns are in a different order compiles fine "
               "and silently interleaves the wrong data.",
      difficulty="Easy", frequency="Common",
      mnemonic="UNION sorts to deduplicate. If the sets cannot overlap, say ALL."),

    Q("traps", "BETWEEN is inclusive at BOTH ends — and dates make that a bug",
      "BETWEEN a AND b includes a and includes b. For numbers that is usually what "
      "you want. For timestamps it is almost always wrong, because the end of a day "
      "is not midnight.",
      "`x BETWEEN a AND b` is exactly `x >= a AND x <= b`. With a DATE column that is "
      "fine. With a TIMESTAMP, `BETWEEN '2024-03-01' AND '2024-03-31'` includes only "
      "the instant midnight on the 31st and excludes the rest of that day — 23 hours "
      "and 59 minutes of data silently missing. The correct form for a range of days "
      "is a HALF-OPEN interval: `>= start AND < next_start`.",
      "shop", ["between", "dates", "range"],
      query="select id, placed\n"
            "  from orders\n"
            " where placed between '2024-03-01' and '2024-03-11'\n"
            " order by id",
      output="""id  placed
--  ----------
10  2024-03-01
11  2024-03-09
12  2024-03-11
(3 rows)""",
      gotcha="Both endpoints are included — order 10 on the 1st and order 12 on the 11th "
             "both appear. Here `placed` is a DATE-shaped string so it works. Store the "
             "same column as a timestamp and order 12 at 14:30 on the 11th would "
             "DISAPPEAR, because '2024-03-11' means '2024-03-11 00:00:00'.",
      example="The safe idiom, for any date-or-timestamp column:\n"
              "  WHERE placed >= '2024-03-01' AND placed < '2024-04-01'\n"
              "Half-open. It is correct for dates and timestamps alike, it needs no "
              "knowledge of the column's precision, and it is sargable so the index is "
              "still used.",
      pitfalls="`BETWEEN b AND a` with the arguments the wrong way round returns NOTHING "
               "— it is not commutative, and it does not error. A dynamically-built "
               "range with the bounds swapped fails silently.",
      difficulty="Medium", frequency="Very common; the timestamp half is a real bug source",
      mnemonic="BETWEEN includes both ends. For dates, use >= and < instead."),

    Q("traps", "COUNT(*) after a LEFT JOIN counts the row that isn't there",
      "A customer with no orders still produces one row after a LEFT JOIN, with the "
      "order columns empty. COUNT(*) counts that row. So 'orders per customer' "
      "reports 1 for a customer who has never ordered.",
      "COUNT(*) counts rows and never skips NULLs; COUNT(expr) skips them. After a "
      "LEFT JOIN the unmatched rows exist but have NULL in every right-hand column, "
      "so counting a right-hand column gives 0 and counting * gives 1. Both queries "
      "are valid SQL and only one answers the question.",
      "shop", ["count", "left-join", "null"],
      query="select c.name, count(*) as bad, count(o.id) as good\n"
            "  from customers c\n  left join orders o on o.customer_id = c.id\n"
            " where c.name = 'Ed'\n group by c.name",
      output="""name  bad  good
----  ---  ----
Ed    1    0
(1 row)""",
      gotcha="Ed has never ordered. One query says 1 and the other says 0, on the same "
             "row, in the same result. In a report summing to a total, the COUNT(*) "
             "version inflates the total by exactly the number of customers with no "
             "orders — which is invisible unless you happen to check one.",
      pitfalls="The same applies to SUM and AVG over a LEFT-joined column: SUM ignores "
               "the NULLs and gives 0-or-NULL correctly, but AVG divides by the count "
               "of non-nulls, so a customer with no orders contributes nothing to the "
               "average rather than contributing a zero. Which is right depends on "
               "whether 'no orders' means 'zero' or 'unknown'.",
      difficulty="Medium", frequency="Very common in take-home data tasks",
      mnemonic="After a LEFT JOIN, count the RIGHT table's key, never *."),

    Q("traps", "GROUP BY collects the NULLs into one group",
      "Grouping by a column that has missing values produces a group for the missing "
      "ones — a single group containing all of them, even though no two missing "
      "values are considered equal anywhere else in SQL.",
      "GROUP BY, DISTINCT, UNION and PARTITION BY all use 'not distinct from' rather "
      "than '=' to decide membership, so NULLs group together. This is deliberate "
      "and it is inconsistent with the WHERE clause, where NULL = NULL is UNKNOWN. "
      "Both behaviours are correct per the standard; you simply have to hold both.",
      "shop", ["group-by", "null"],
      query="select customer_id, count(*) as n\n"
            "  from orders\n group by customer_id\n order by customer_id",
      output="""customer_id  n
-----------  -
NULL         1
1            3
2            2
4            1
(4 rows)""",
      gotcha="There is a NULL group with one row in it — the guest checkout. That group "
             "belongs to no customer, so the moment this result is joined back to "
             "`customers` it silently disappears and the totals no longer add up. Any "
             "'per customer' report over a nullable foreign key has this hole.",
      pitfalls="ORDER BY put the NULL first here because SQLite sorts NULLs first. "
               "Postgres would put it LAST on the same query. If you are eyeballing a "
               "grouped report for a NULL group, it is at whichever end your engine "
               "chose, and it is easy to miss at the bottom of a long result.",
      difficulty="Medium", frequency="Common",
      mnemonic="One NULL group, always. For grouping they are equal; for comparing they "
               "are not."),

    Q("traps", "A NULL in NOT IN empties the whole result",
      "The worst one, repeated here because it is the trap most likely to be asked. "
      "`NOT IN` against a list containing a single missing value returns NO ROWS AT "
      "ALL, whatever the data says.",
      "`x NOT IN (a, b, NULL)` expands to `x <> a AND x <> b AND x <> NULL`. The last "
      "term is UNKNOWN, TRUE AND UNKNOWN is UNKNOWN, and WHERE keeps only TRUE. No "
      "row can ever satisfy it. `IN` is unaffected for matches, because "
      "TRUE OR UNKNOWN is TRUE — which is exactly why the positive form looks fine "
      "and the negative form is broken.",
      "shop", ["null", "not-in", "three-valued-logic"],
      query="select name from customers\n"
            " where id not in (select customer_id from orders)",
      output="(0 rows)",
      gotcha="The correct answer is Cy and Ed. One guest order with a NULL customer_id "
             "is enough to empty the entire result, and it will stay empty however much "
             "data you add. The query is not approximately wrong — it is "
             "unconditionally empty.",
      example="Three fixes, in order of preference:\n"
              "  NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)\n"
              "  LEFT JOIN orders o ON ... WHERE o.id IS NULL\n"
              "  NOT IN (SELECT customer_id FROM orders WHERE customer_id IS NOT NULL)\n"
              "The third works and requires you to remember forever; the first two are "
              "immune by construction and usually faster.",
      followups="Why is it not caught in review? Because the subquery looks obviously "
                "correct, the column is often declared NOT NULL in the developer's "
                "mental model, and the empty result reads as a legitimate answer. It is "
                "found in production, by someone noticing a report that is always blank.",
      difficulty="Hard", frequency="The single most-asked SQL trap",
      mnemonic="NOT IN plus one NULL equals nothing. Use NOT EXISTS."),

    Q("traps", "Aliases exist in ORDER BY and not in WHERE",
      "Name a computed column in SELECT and you can sort by that name — but you "
      "cannot filter by it. The clauses are evaluated in a different order from the "
      "one they are written in.",
      "Evaluation order is roughly FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY, "
      "LIMIT. WHERE runs BEFORE SELECT, so a SELECT alias does not exist yet; "
      "ORDER BY runs after, so it does. Repeat the expression in WHERE, or wrap the "
      "query in a subquery or CTE where the alias has become a real column.",
      "shop", ["alias", "evaluation-order", "where"],
      query="select id, amount * 2 as doubled\n"
            "  from orders\n order by doubled desc\n limit 3",
      output="""id  doubled
--  -------
13  400
10  240
12  160
(3 rows)""",
      gotcha="This works because the alias is used in ORDER BY. Move it to "
             "`WHERE doubled > 100` and it fails with 'no such column: doubled' — the "
             "same identifier, valid in one clause and not in another, for reasons that "
             "are invisible in the written order of the query.",
      portability="MySQL and SQLite permit a SELECT alias in HAVING and in GROUP BY; "
                  "Postgres permits it in GROUP BY and ORDER BY but not in HAVING when "
                  "it is ambiguous. Nobody permits it in WHERE. The portable answer is "
                  "always a subquery or CTE.",
      difficulty="Easy", frequency="Common early-career question",
      mnemonic="Written SELECT-first, run FROM-first. WHERE happens before the alias exists."),

    Q("traps", "An index you have does not mean an index you use",
      "The index exists, the column is in the WHERE clause, and the database reads "
      "the whole table anyway — because the query asks about a FUNCTION of the "
      "column, and the index stores the column.",
      "A predicate is only sargable when the indexed column appears bare. Wrapping it "
      "in SUBSTR, UPPER, DATE, a cast, or any arithmetic makes the stored values "
      "useless, because the index is sorted by the column and not by the function of "
      "it. The rewrite is always the same shape: turn `f(col) = v` into a RANGE on "
      "the bare column.",
      "shop", ["index", "sargable", "explain"],
      query="create index ix_placed on orders(placed);\n"
            "explain query plan\n"
            "select * from orders where substr(placed,1,7) = '2024-03'",
      output="""id  parent  notused  detail
--  ------  -------  -----------
2   0       0        SCAN orders
(1 row)""",
      gotcha="SCAN, with the index sitting right there unused. Nothing errors and "
             "nothing warns; the query is simply as slow as it was before you added the "
             "index, which is the most frustrating possible outcome because you have "
             "already 'fixed' it.",
      example="  slow:  WHERE substr(placed,1,7) = '2024-03'\n"
              "  fast:  WHERE placed >= '2024-03-01' AND placed < '2024-04-01'\n"
              "Same rows, and the second one is a range scan on the index.",
      pitfalls="The invisible version is an implicit cast: comparing an indexed text "
               "column to a number makes the engine cast the COLUMN, which is a "
               "function, which kills the index — and there is no function call written "
               "anywhere in the query.",
      difficulty="Hard", frequency="Very common as a real-world debugging question",
      mnemonic="Bare column on the left. Any function around it and the index is decoration."),

    ]

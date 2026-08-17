"""SQL bank — joining tables.

The rung where most real queries live and most real bugs start. Two things
carry the whole category: what a LEFT JOIN does to rows that do not match,
and the difference between a condition in ON and the same condition in
WHERE — which changes the answer, not the speed.

Every stated output came out of sqlite3 and is re-checked by verify().
"""


def build(Q):
    return [

    Q("joins", "INNER JOIN — only the rows that match, on both sides",
      "Stick two tables together where a column in one matches a column in the "
      "other. Rows with no match on EITHER side simply do not appear.",
      "An INNER JOIN produces one output row per matching pair. A customer with "
      "no orders vanishes; an order with no customer vanishes. Both are correct "
      "and both surprise people, because 'join the customers to their orders' "
      "sounds like it should still mention every customer.",
      "shop", ["join", "inner-join"],
      query="select c.name, o.id, o.amount\n"
            "  from customers c\n  join orders o on o.customer_id = c.id\n"
            " order by c.name, o.id",
      output="""name  id  amount
----  --  ------
Ana   10  120
Ana   11  45.5
Ana   16  30
Bo    12  80
Bo    13  200
Di    14  15
(6 rows)""",
      gotcha="Six rows from five customers and seven orders. Cy and Ed are missing "
             "because they have never ordered, and order 15 is missing because it is a "
             "guest checkout with no customer. AN INNER JOIN DROPS ROWS FROM BOTH "
             "SIDES, and neither loss is announced.",
      pitfalls="Note Ana appears three times. A one-to-many join MULTIPLIES the left "
               "row, so any aggregate over customer columns after this join "
               "double-counts. Summing a customer-level field across this result is one "
               "of the most common reporting bugs there is.",
      difficulty="Easy", frequency="Universal",
      mnemonic="INNER keeps matches. Anything unmatched, on either side, is gone."),

    Q("joins", "LEFT JOIN — keep every row on the left",
      "Keep all the rows from the first table whether or not they have a match, "
      "filling the second table's columns with 'missing' where there isn't one.",
      "A LEFT OUTER JOIN emits every left row at least once. Where the ON condition "
      "finds no match, one row is emitted with every right-hand column NULL. That "
      "NULL is the whole mechanism — it is what makes 'customers with no orders' "
      "expressible, and it is what makes COUNT(*) wrong afterwards.",
      "shop", ["join", "left-join", "null"],
      query="select c.name, count(o.id) as orders\n"
            "  from customers c\n  left join orders o on o.customer_id = c.id\n"
            " group by c.name\n order by c.name",
      output="""name  orders
----  ------
Ana   3
Bo    2
Cy    0
Di    1
Ed    0
(5 rows)""",
      gotcha="All five customers appear, and Cy and Ed correctly show 0 — but only "
             "because it counts o.id. COUNT(*) would give them 1 each, counting the "
             "placeholder row the LEFT JOIN invented. The column you count is the "
             "question you asked.",
      pitfalls="RIGHT JOIN is the mirror image and is almost never written, because "
               "swapping the table order makes it a LEFT JOIN and every reader finds "
               "left-to-right easier to follow. SQLite only gained RIGHT JOIN in 3.39 "
               "(2022) for exactly that reason.",
      difficulty="Easy", frequency="Universal",
      mnemonic="LEFT keeps every left row. The right side becomes NULL when there is no match."),

    Q("joins", "The anti-join — rows with NO match",
      "Find the rows in one table that have nothing matching them in another. "
      "'Customers who have never ordered', 'products never sold', 'users with no "
      "session'.",
      "Three equivalent spellings: LEFT JOIN with `WHERE right.key IS NULL`, "
      "`NOT EXISTS`, and `NOT IN`. The first two are correct and usually planned "
      "identically as an anti-join; NOT IN silently returns nothing if the subquery "
      "contains a single NULL. The LEFT JOIN form is the one to recognise on sight, "
      "because the IS NULL in the WHERE is doing something non-obvious: it is "
      "keeping exactly the rows the join failed to match.",
      "shop", ["join", "anti-join", "left-join", "null"],
      query="select c.name\n"
            "  from customers c\n  left join orders o on o.customer_id = c.id\n"
            " where o.id is null\n order by c.name",
      output="""name
----
Cy
Ed
(2 rows)""",
      gotcha="`WHERE o.id IS NULL` on a LEFT JOIN does not mean 'orders whose id is "
             "null' — no such order exists, id is the primary key. It means 'rows where "
             "the join found nothing', because that is the only way a primary key comes "
             "back NULL. Reading it literally is what makes this idiom hard to learn.",
      example="The same question three ways, all returning Cy and Ed:\n"
              "  LEFT JOIN ... WHERE o.id IS NULL\n"
              "  WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)\n"
              "  WHERE id NOT IN (...)   <- BROKEN here: returns 0 rows, see the NULL entry",
      difficulty="Medium", frequency="Very common — 'find the users who never X'",
      mnemonic="LEFT JOIN then WHERE right-key IS NULL. The IS NULL means 'no match', not 'null data'."),

    Q("joins", "A condition in ON is not a condition in WHERE",
      "On a LEFT JOIN, putting a filter next to the join condition and putting it "
      "in WHERE give different answers. One filters what counts as a match; the "
      "other throws away rows after the join has already happened.",
      "ON is evaluated DURING the join and decides which right-hand rows match. "
      "Unmatched left rows still survive, with NULLs. WHERE is evaluated AFTER the "
      "join, and a NULL fails almost every comparison — so any WHERE condition on a "
      "right-hand column silently converts a LEFT JOIN into an INNER JOIN.",
      "shop", ["join", "left-join", "on-vs-where", "null"],
      query="select c.name, o.id, o.status\n"
            "  from customers c\n"
            "  left join orders o on o.customer_id = c.id and o.status = 'paid'\n"
            " order by c.name, o.id",
      output="""name  id    status
----  ----  ------
Ana   10    paid
Ana   11    paid
Ana   16    paid
Bo    13    paid
Cy    NULL  NULL
Di    NULL  NULL
Ed    NULL  NULL
(7 rows)""",
      gotcha="SEVEN rows. Move `o.status = 'paid'` from ON to WHERE and the identical "
             "query returns FOUR — Cy, Di and Ed disappear, because their o.status is "
             "NULL and `NULL = 'paid'` is UNKNOWN. Di has an order, just not a paid "
             "one, and she vanishes along with the two who have no orders at all.",
      example="ON version:    every customer appears; unmatched ones show NULL.  7 rows\n"
              "WHERE version: only customers with a PAID order appear.            4 rows\n"
              "Both are legitimate questions. Only one of them is the one you meant.",
      pitfalls="The rule of thumb: a filter on the LEFT table belongs in WHERE (it "
               "reduces which rows you are reporting on); a filter on the RIGHT table "
               "of a LEFT JOIN belongs in ON (it reduces what counts as a match). "
               "Getting it backwards is the most common LEFT JOIN bug.",
      difficulty="Hard", frequency="A favourite senior question",
      mnemonic="ON decides what matches. WHERE decides what survives. On a LEFT JOIN "
               "they are not the same question."),

    Q("joins", "The accidental cross join",
      "If the join condition does not actually relate the two tables, every row of "
      "one is paired with every row of the other. The query runs, returns a "
      "plausible number of rows, and every total is wrong.",
      "A CROSS JOIN is the Cartesian product: n x m rows. It is occasionally what "
      "you want (generating a calendar, filling a grid) and usually an accident — a "
      "missing ON clause, a condition that references only one table, or a join key "
      "that is not actually a key. The symptom is row counts that are a multiple of "
      "what you expected, and sums that are exactly that multiple too high.",
      "shop", ["join", "cross-join", "cardinality"],
      query="select count(*) as rows\n"
            "  from orders o\n  join customers c on c.city = 'London'",
      output="""rows
----
14
(1 row)""",
      gotcha="14 = 7 orders x 2 London customers. The ON clause looks like a join "
             "condition and is actually just a filter on `customers` — it never "
             "mentions `orders` at all, so every order pairs with every London "
             "customer. Any SUM over this is exactly doubled, which looks like a data "
             "problem rather than a query one.",
      pitfalls="A full CROSS JOIN of these tables is 5 x 7 = 35 rows. On real tables "
               "the accident is not subtle: a million-row table joined to a "
               "thousand-row one with no condition is a billion rows, and the query "
               "either runs for hours or fills the disk with a temporary spill.",
      followups="How do you catch it? Compare the output row count with the row count "
                "of the table you expected to drive the query. If joining orders to "
                "customers returns MORE rows than there are orders, a one-to-many or a "
                "cross join is happening and you need to know which.",
      difficulty="Medium", frequency="Common as a debugging question",
      mnemonic="If the ON clause does not name BOTH tables, it is not a join condition."),

    Q("joins", "The self-join — a table joined to itself",
      "Some tables point at themselves: an employee's manager is another employee, "
      "a comment's parent is another comment. Joining the table to itself with two "
      "different aliases lets you see both ends of that relationship in one row.",
      "A self-join needs table ALIASES, because both sides are the same table and "
      "every column would otherwise be ambiguous. It is an ordinary join in every "
      "other respect — and it should be a LEFT join whenever the relationship is "
      "optional, which for a hierarchy it always is at the root.",
      "staff", ["join", "self-join", "hierarchy"],
      query="select e.name as employee, m.name as manager\n"
            "  from employees e\n  left join employees m on m.id = e.manager\n"
            " order by e.name",
      output="""employee  manager
--------  -------
Mira      Root
Nadia     Mira
Omar      Mira
Priya     Root
Quinn     Priya
Rhys      Priya
Root      NULL
Sara      NULL
(8 rows)""",
      gotcha="Use a plain JOIN instead of LEFT and Root and Sara disappear — the two "
             "people with no manager, which for an org chart is the CEO and an "
             "unassigned new starter. Both are exactly the rows someone looking at an "
             "org chart wants to see.",
      pitfalls="A self-join reaches ONE level. Two levels needs a second join, three "
               "needs a third, and an arbitrary depth needs a RECURSIVE CTE — which is "
               "why 'find everyone under this manager' is a different question from "
               "'find each person's manager'.",
      difficulty="Medium", frequency="Common — the org chart is the standard prompt",
      mnemonic="Same table, two aliases. LEFT, because the top of a hierarchy has no parent."),

    Q("joins", "FULL OUTER JOIN — everything from both sides",
      "Keep every row from both tables, matching them where you can and filling in "
      "'missing' where you cannot. Useful for reconciliation: what is in A and not "
      "B, and what is in B and not A, in one pass.",
      "FULL OUTER JOIN is a LEFT JOIN and a RIGHT JOIN at once. Its main practical "
      "use is finding the rows that DID NOT match on either side, which is the "
      "query below: filter to rows where one side's key is NULL and you have both "
      "orphan sets together.",
      "shop", ["join", "full-outer-join", "reconciliation"],
      query="select c.name, o.id\n"
            "  from customers c\n"
            "  full outer join orders o on o.customer_id = c.id\n"
            " where c.id is null or o.id is null\n"
            " order by c.name, o.id",
      output="""name  id
----  ----
NULL  15
Cy    NULL
Ed    NULL
(3 rows)""",
      gotcha="Read the three rows as two different problems in one result. Order 15 has "
             "no customer (a guest checkout, or an orphaned row). Cy and Ed are "
             "customers with no orders. A LEFT JOIN would have found the second pair "
             "and been blind to the first.",
      portability="Postgres, SQL Server and Oracle have had FULL OUTER JOIN for "
                  "decades. SQLite gained it in 3.39 (2022). MySQL STILL DOES NOT HAVE "
                  "IT — the portable substitute is a LEFT JOIN UNION'd with a RIGHT "
                  "JOIN, or two anti-joins UNION ALL'd together.",
      difficulty="Medium", frequency="Less common, and a good sign when someone reaches for it",
      mnemonic="FULL OUTER keeps orphans from both sides. Filter to the NULLs to see just them."),

    Q("joins", "Fan-out — why your SUM is too big after a join",
      "Joining a table to something that has many matching rows repeats the "
      "original row once per match. Anything you then add up from the original "
      "table is counted once per match, not once.",
      "A one-to-many join MULTIPLIES the left row. If a customer has three orders, "
      "any customer-level column now appears three times, and SUM over it triples. "
      "The fix is to aggregate the many-side FIRST — in a subquery or CTE — and "
      "join to that single row, or to use a window function which does not change "
      "the row count at all.",
      "shop", ["join", "fan-out", "aggregate", "cardinality"],
      query="select c.name, count(*) as rows, sum(o.amount) as total\n"
            "  from customers c\n  join orders o on o.customer_id = c.id\n"
            " group by c.name\n order by c.name",
      output="""name  rows  total
----  ----  -----
Ana   3     195.5
Bo    2     280
Di    1     15
(3 rows)""",
      gotcha="This query is correct, because it sums an ORDER column. Now imagine "
             "customers had a `credit_limit` and you wrote `sum(c.credit_limit)`: Ana's "
             "limit would be added three times, once per order. THE JOIN DID NOT CHANGE "
             "THE CUSTOMER, IT CHANGED HOW MANY TIMES SHE APPEARS.",
      example="Two joins to two different one-to-many tables is worse: orders AND "
              "support tickets means rows = orders x tickets, and BOTH sums are wrong. "
              "Aggregate each side separately, then join the two aggregates.",
      pitfalls="The tell is a row count larger than the driving table's. If you start "
               "with 5 customers and end with 6 rows, something fanned out - and the "
               "moment there are two such joins the multiplication is silent and large.",
      difficulty="Hard", frequency="Very common in take-homes; the classic wrong answer",
      mnemonic="Aggregate before you join, or the join multiplies what you are adding up."),

    ]

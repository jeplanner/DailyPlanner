"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it — no heredocs, pipes, or && chains.
Replace the BATCH list, run it, then git add/commit/push as separate
simple commands. Validates every code block (ast.parse), dedups against
existing titles, and checks every entry has an example before writing.
"""
import ast
import importlib
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())   # so `import ai_sde_bank` works from here

# ── The batch to add this iteration. ──
BATCH = [
    dict(cat="dsa", title="Swap Nodes in Pairs",
         answer="Swap every two adjacent nodes of a linked list and return the new head (swap the nodes, not just their values). A dummy head plus a 'prev' pointer makes the pointer surgery clean: for each pair, relink prev -> second -> first -> rest, then advance prev by two.",
         tags=["swap-pairs","linked-list","dummy-node","pointers","dsa"],
         code='''# Swap every two adjacent nodes and return the new head.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def swap_pairs(head):
    dummy = ListNode(0, head)
    prev = dummy
    while prev.next and prev.next.next:
        first = prev.next
        second = first.next
        # relink: prev -> second -> first -> rest
        first.next = second.next
        second.next = first
        prev.next = second
        prev = first            # advance two nodes
    return dummy.next''',
         complexity="Time O(n), space O(1).",
         pitfalls="Losing the rest of the list (set first.next before second.next); forgetting the dummy for the head.",
         example="1->2->3->4 becomes 2->1->4->3."),
    dict(cat="dsa", title="Odd Even Linked List",
         answer="Reorder a list so all ODD-position nodes come first, then all EVEN-position nodes, preserving relative order (by position, not value). Weave two pointers: an odd chain and an even chain built in one pass, then attach the even chain after the odd chain.",
         tags=["odd-even-list","linked-list","pointers","dsa"],
         code='''# Group odd-indexed nodes first, then even-indexed, preserving order.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def odd_even_list(head):
    if head is None:
        return None
    odd = head
    even = head.next
    even_head = even
    while even and even.next:
        odd.next = even.next    # link to the next odd node
        odd = odd.next
        even.next = odd.next    # link to the next even node
        even = even.next
    odd.next = even_head        # attach the even chain after the odds
    return head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting to save even_head; wrong loop condition leaving a dangling pointer.",
         example="1->2->3->4->5 becomes 1->3->5->2->4."),
    dict(cat="dsa", title="Palindrome Linked List",
         answer="Check if a singly linked list is a palindrome in O(1) space. Find the middle with fast/slow pointers, REVERSE the second half, then compare it node-by-node with the first half. (Optionally restore the list afterward.)",
         tags=["palindrome-linked-list","fast-slow-pointers","reverse","linked-list","dsa"],
         code='''# Is the linked list a palindrome? (reverse second half, compare)
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def is_palindrome(head):
    slow = fast = head
    while fast and fast.next:            # find the middle
        slow = slow.next
        fast = fast.next.next
    prev = None                          # reverse the second half
    while slow:
        slow.next, prev, slow = prev, slow, slow.next
    left, right = head, prev             # compare the two halves
    while right:
        if left.val != right.val:
            return False
        left = left.next
        right = right.next
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Comparing to the wrong end after reversal; mishandling odd-length middle.",
         example="1->2->2->1 -> True; 1->2->3 -> False."),
    dict(cat="dsa", title="Remove Duplicates from Sorted List",
         answer="Remove duplicate values from a SORTED linked list, keeping one node per value. Walk with a single pointer; when the next node has the same value, skip it (relink past it); otherwise advance. Sortedness means duplicates are always adjacent.",
         tags=["remove-duplicates-list","linked-list","pointers","dsa"],
         code='''# Remove duplicates from a SORTED linked list (keep one of each value).
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def delete_duplicates(head):
    current = head
    while current and current.next:
        if current.val == current.next.val:
            current.next = current.next.next   # skip the duplicate
        else:
            current = current.next
    return head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Advancing past a node before checking the next duplicate; assuming unsorted input.",
         example="1->1->2->3->3 becomes 1->2->3."),
    dict(cat="dsa", title="Rotate List",
         answer="Rotate a linked list to the RIGHT by k places. Find the length and tail, connect the tail to the head to form a CIRCLE, then walk length - (k mod length) steps to the new tail and break the circle there. The modulo handles k larger than the list.",
         tags=["rotate-list","linked-list","pointers","dsa"],
         code='''# Rotate the list to the right by k places.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def rotate_right(head, k):
    if head is None or head.next is None or k == 0:
        return head
    length = 1                           # find length and tail
    tail = head
    while tail.next:
        tail = tail.next
        length += 1
    k %= length
    if k == 0:
        return head
    tail.next = head                     # make the list circular
    steps = length - k                   # walk to the new tail
    new_tail = head
    for _ in range(steps - 1):
        new_tail = new_tail.next
    new_head = new_tail.next
    new_tail.next = None                 # break the circle
    return new_head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting k %= length (k can exceed the length); off-by-one on the new tail.",
         example="1->2->3->4->5 with k=2 -> 4->5->1->2->3."),
    dict(cat="dsa", title="Reverse Integer",
         answer="Reverse the digits of a signed 32-bit integer, returning 0 if the result OVERFLOWS the 32-bit range. Pop digits with %10 and build the reversed number with *10; apply the sign; then check the [-2^31, 2^31-1] bounds.",
         tags=["reverse-integer","math","overflow","dsa"],
         code='''# Reverse the digits of a signed 32-bit integer; return 0 on overflow.
def reverse_integer(x):
    sign = -1 if x < 0 else 1
    x = abs(x)
    result = 0
    while x:
        result = result * 10 + x % 10   # append the last digit
        x //= 10
    result *= sign
    if result < -2**31 or result > 2**31 - 1:   # 32-bit overflow check
        return 0
    return result''',
         complexity="Time O(digits), space O(1).",
         pitfalls="Not checking 32-bit overflow; mishandling the sign for negatives.",
         example="reverse_integer(123) -> 321; reverse_integer(-120) -> -21; reverse_integer(1534236469) -> 0."),
    dict(cat="dsa", title="Palindrome Number",
         answer="Determine whether an integer reads the same forwards and backwards WITHOUT converting to a string. Negatives are never palindromes. Rebuild the number reversed (pop digits with %10) and compare to the original.",
         tags=["palindrome-number","math","dsa"],
         code='''# Is an integer a palindrome (reads the same forwards and backwards)?
def is_palindrome_number(x):
    if x < 0:
        return False            # negatives aren't palindromes
    reversed_num = 0
    original = x
    while x:
        reversed_num = reversed_num * 10 + x % 10
        x //= 10
    return reversed_num == original''',
         complexity="Time O(digits), space O(1).",
         pitfalls="Treating negatives as palindromes; overflow in languages with fixed ints (reverse only half to avoid it).",
         example="is_palindrome_number(121) -> True; is_palindrome_number(-121) -> False; is_palindrome_number(10) -> False."),
    dict(cat="dsa", title="Fizz Buzz",
         answer="For 1..n, output 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for multiples of both, else the number as a string. Check the multiple-of-15 (both) case FIRST so it isn't shadowed by the individual checks.",
         tags=["fizzbuzz","math","simulation","dsa"],
         code='''# FizzBuzz: 1..n, multiples of 3 -> 'Fizz', 5 -> 'Buzz', both -> 'FizzBuzz'.
def fizz_buzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Checking 3/5 before 15 (misses 'FizzBuzz'); returning ints instead of strings.",
         example="fizz_buzz(5) -> ['1','2','Fizz','4','Buzz']."),
    dict(cat="glossary", title="Join algorithms (nested-loop / hash / sort-merge)",
         answer="How a database physically combines two tables. NESTED-LOOP: for each row of A, scan B — fine when one side is tiny or indexed, O(A*B) otherwise. HASH join: build a hash table on the smaller table's join key, probe with the larger — great for equi-joins on unsorted data, O(A+B). SORT-MERGE: sort both by the key then merge in lockstep — good when inputs are already sorted or for range joins. The optimizer picks based on sizes, indexes, and sortedness.",
         tags=["join-algorithms","hash-join","sort-merge-join","nested-loop","database"],
         example="Joining a 10-row dimension to a billion-row fact table, the optimizer builds a hash table on the 10 rows and probes it once per fact row (hash join) rather than a nested-loop scan."),
    dict(cat="glossary", title="Cost-based optimizer (query plan)",
         answer="The component that turns declarative SQL into an efficient EXECUTION PLAN by estimating the COST (I/O, CPU, rows) of alternative plans — join orders, join algorithms, index vs full scan — using table STATISTICS (row counts, histograms) and picking the cheapest. Stale/missing statistics lead to bad plans. You inspect its choice with EXPLAIN.",
         tags=["cost-based-optimizer","query-plan","statistics","explain","database"],
         example="For a 3-table join, the optimizer uses row-count stats to choose the join ORDER and hash-join the small table first, avoiding a plan that materializes a huge intermediate result."),
    dict(cat="glossary", title="Predicate pushdown",
         answer="A query optimization that pushes FILTERS (WHERE predicates) as close to the data as possible — applying them during the scan or even at the storage/file layer — so fewer rows flow up the plan. In columnar formats (Parquet) with engines like Spark, it skips row groups whose min/max stats can't match the predicate, reading far less data.",
         tags=["predicate-pushdown","query-optimization","parquet","spark","columnar"],
         example="SELECT ... WHERE year=2024 on Parquet: predicate pushdown skips every row group whose year min/max excludes 2024, reading only the relevant files instead of the whole dataset."),
    dict(cat="glossary", title="Columnar encoding (RLE / dictionary)",
         answer="Compression that exploits columnar storage where a column's values are similar. RUN-LENGTH ENCODING (RLE) stores a repeated value once with a count ('US x 1000'). DICTIONARY encoding maps distinct values to small integer codes plus a dictionary — great for low-cardinality columns. These shrink storage and speed scans (operate on compressed data), a key reason columnar analytics is fast.",
         tags=["columnar-encoding","rle","dictionary-encoding","compression","olap"],
         example="A 'country' column with 200 distinct values dictionary-encodes each as a 1-byte code, cutting size ~8x and letting the engine filter on integer codes directly."),
    dict(cat="glossary", title="Clustered vs non-clustered index",
         answer="A CLUSTERED index sets the PHYSICAL order of the table's rows (the data IS the index leaf) — one per table, and range scans on it are very fast (data is contiguous). A NON-CLUSTERED (secondary) index is a separate structure mapping keys to row locations/primary keys — you can have many, but a lookup may need an extra step to fetch the row (unless it's a 'covering' index). Pick the clustered key for your most common range/sort access.",
         tags=["clustered-index","non-clustered-index","secondary-index","database","indexing"],
         example="In InnoDB the PRIMARY KEY is the clustered index (rows stored in PK order), so range scans by PK are sequential; a secondary index on 'email' points back to the PK and needs a second lookup for other columns."),
    dict(cat="conceptual", title="Why is a columnar storage format faster for analytics than a row format?",
         answer="Analytics reads a FEW columns across MANY rows (e.g. SUM(revenue) over a billion rows), while OLTP reads whole rows. In ROW storage a row's columns sit together, so reading one column still pulls entire rows off disk — wasted I/O. In COLUMNAR storage each column is contiguous, so you read ONLY the columns you need. Columns also compress far better (adjacent values are similar -> RLE/dictionary/delta), shrinking data 5-10x and enabling vectorized/SIMD execution over tight arrays, plus per-block min/max stats power predicate pushdown to skip irrelevant blocks. The trade-off: updating one row touches many column files, so columnar is poor for OLTP — hence row-store for transactions, columnar for analytics.",
         tags=["columnar","row-store","olap","io","why"],
         example="SUM(price) over a billion-row table reads just the compressed 'price' column (a few GB) in a columnar store versus scanning entire multi-column rows (hundreds of GB) in a row store — often 10-100x less I/O."),
]


def qsrc(e):
    s = f"    Q({e['cat']!r}, {e['title']!r},\n      {e['answer']!r},\n      {e['tags']!r}"
    for f in ("code", "example", "complexity", "pitfalls", "followups"):
        if e.get(f):
            s += f",\n      {f}={e[f]!r}"
    return s + "),\n"


# Validate every code block parses before we touch the file.
for e in BATCH:
    if e.get("code"):
        ast.parse(e["code"])

# Skip any titles already present (so re-running never double-inserts).
_existing = {e["title"] for e in importlib.import_module("ai_sde_bank").ENTRIES}
BATCH = [e for e in BATCH if e["title"] not in _existing]
if not BATCH:
    print("nothing new to insert (all titles already present)")
    raise SystemExit(0)

block = "".join(qsrc(e) for e in BATCH)
path = "ai_sde_bank.py"
text = open(path).read()
marker = "),\n]\n\n# Fill tags: explicit + category-derived."
assert text.count(marker) == 1, "insert marker not found/unique"
text = text.replace(marker, "),\n" + block + "]\n\n# Fill tags: explicit + category-derived.")
open(path, "w").write(text)

b = importlib.import_module("ai_sde_bank")
importlib.reload(b)
for e in b.ENTRIES:
    if e.get("code"):
        ast.parse(e["code"])
missing = [e["title"] for e in b.ENTRIES if not e.get("example")]
assert not missing, f"missing example: {missing}"
print(f"inserted {len(BATCH)} | total {len(b.ENTRIES)} | missing example: {len(missing)}")

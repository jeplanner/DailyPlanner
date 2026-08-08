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
    dict(cat="dsa", title="Design HashMap",
         answer="Build a hash map from scratch supporting put/get/remove. Use an array of BUCKETS and SEPARATE CHAINING: hash the key to a bucket index, and store (key, value) pairs in that bucket's list; on collision, scan the bucket. Update in place if the key exists, else append.",
         tags=["design-hashmap","hash-table","separate-chaining","design","dsa"],
         code='''# A simple hash map using separate chaining (buckets of key-value pairs).
class MyHashMap:
    def __init__(self):
        self.size = 1000
        self.buckets = [[] for _ in range(self.size)]

    def _index(self, key):
        return key % self.size

    def put(self, key, value):
        bucket = self.buckets[self._index(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)   # update an existing key
                return
        bucket.append((key, value))         # otherwise insert a new key

    def get(self, key):
        for k, v in self.buckets[self._index(key)]:
            if k == key:
                return v
        return -1                           # key not found

    def remove(self, key):
        bucket = self.buckets[self._index(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                return''',
         complexity="Average O(1) per op (O(n/buckets) with collisions); space O(n).",
         pitfalls="Not updating an existing key (duplicate entries); a poor hash causing long chains.",
         example="m=MyHashMap(); m.put(1,10); m.get(1)->10; m.get(2)->-1; m.remove(1); m.get(1)->-1."),
    dict(cat="dsa", title="Implement Stack using Queues",
         answer="Build a LIFO stack from a FIFO queue. Make push the expensive operation: after appending the new element, ROTATE the queue so the newest element sits at the FRONT — then pop/top are O(1) and read from the front like a stack top.",
         tags=["stack-using-queues","queue","stack","design","dsa"],
         code='''# LIFO stack built from a single FIFO queue (push O(n), pop/top O(1)).
from collections import deque
class MyStack:
    def __init__(self):
        self.q = deque()

    def push(self, x):
        self.q.append(x)
        # rotate so the newest element becomes the front (the stack top)
        for _ in range(len(self.q) - 1):
            self.q.append(self.q.popleft())

    def pop(self):
        return self.q.popleft()

    def top(self):
        return self.q[0]

    def empty(self):
        return len(self.q) == 0''',
         complexity="push O(n); pop/top/empty O(1); space O(n).",
         pitfalls="Rotating the wrong number of times; reading from the back instead of the front.",
         example="s=MyStack(); s.push(1); s.push(2): top()->2, pop()->2, pop()->1."),
    dict(cat="dsa", title="Count and Say",
         answer="The count-and-say sequence: each term describes the previous one by reading off runs of equal digits as 'count digit'. Start from '1' and, for each step, scan the current string counting consecutive equal digits and append count+digit. Return the n-th term.",
         tags=["count-and-say","string","run-length","simulation","dsa"],
         code='''# The n-th term of the count-and-say sequence.
def count_and_say(n):
    result = "1"
    for _ in range(n - 1):
        next_term = []
        i = 0
        while i < len(result):
            count = 1
            while i + 1 < len(result) and result[i] == result[i + 1]:
                i += 1; count += 1        # count a run of the same digit
            next_term.append(str(count) + result[i])   # 'say' count + digit
            i += 1
        result = "".join(next_term)
    return result''',
         complexity="Time grows with term length; space O(term length).",
         pitfalls="Off-by-one on the number of iterations (start at '1'); mis-counting runs.",
         example="count_and_say(4) -> '1211'  (1 -> 11 -> 21 -> 1211)."),
    dict(cat="dsa", title="Transpose Matrix",
         answer="Return the transpose of a matrix — flip it over its main diagonal so element [r][c] becomes [c][r], turning an m×n matrix into n×m. Allocate a cols×rows result and copy each element to its swapped position.",
         tags=["transpose","matrix","dsa"],
         code='''# Return the transpose of a matrix (swap rows and columns).
def transpose(matrix):
    rows, cols = len(matrix), len(matrix[0])
    result = [[0] * rows for _ in range(cols)]
    for r in range(rows):
        for c in range(cols):
            result[c][r] = matrix[r][c]   # element [r][c] moves to [c][r]
    return result''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Sizing the result rows×cols instead of cols×rows; non-square in-place transpose is invalid.",
         example="transpose([[1,2,3],[4,5,6]]) -> [[1,4],[2,5],[3,6]]."),
    dict(cat="dsa", title="Matrix Diagonal Sum",
         answer="Sum both diagonals of a square matrix, counting the shared center element only once when n is odd. Add mat[i][i] (primary) and mat[i][n-1-i] (secondary) for each row, then subtract the center if n is odd.",
         tags=["diagonal-sum","matrix","dsa"],
         code='''# Sum both diagonals of a square matrix (counting a shared center once).
def diagonal_sum(mat):
    n = len(mat)
    total = 0
    for i in range(n):
        total += mat[i][i]                # primary diagonal
        total += mat[i][n - 1 - i]        # secondary diagonal
    if n % 2 == 1:
        total -= mat[n // 2][n // 2]      # remove the double-counted center
    return total''',
         complexity="Time O(n), space O(1).",
         pitfalls="Double-counting the center on odd n; wrong secondary-diagonal index.",
         example="diagonal_sum([[1,2,3],[4,5,6],[7,8,9]]) -> 25  (1+5+9 + 3+7)."),
    dict(cat="dsa", title="Convert Sorted Array to BST",
         answer="Build a HEIGHT-BALANCED binary search tree from a sorted array. Pick the MIDDLE element as the root (so left and right halves are equal-sized), then recursively build the left subtree from the left half and the right subtree from the right half. The sorted order guarantees the BST property.",
         tags=["sorted-array-to-bst","bst","divide-and-conquer","recursion","dsa"],
         code='''# Build a height-balanced BST from a sorted array (middle element as root).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def sorted_array_to_bst(nums):
    def build(lo, hi):
        if lo > hi:
            return None
        mid = (lo + hi) // 2              # middle keeps the tree balanced
        node = TreeNode(nums[mid])
        node.left = build(lo, mid - 1)
        node.right = build(mid + 1, hi)
        return node
    return build(0, len(nums) - 1)''',
         complexity="Time O(n), space O(log n) recursion.",
         pitfalls="Picking an end element as root (unbalanced); off-by-one on the half ranges.",
         example="sorted_array_to_bst([-10,-3,0,5,9]) builds a balanced BST rooted at 0."),
    dict(cat="dsa", title="Range Sum of BST",
         answer="Sum the values of all nodes whose value lies in [low, high] within a BST. Exploit the ordering to PRUNE: if a node's value is below low, only its right subtree can contain in-range values; if above high, only its left subtree; otherwise count the node and recurse both ways.",
         tags=["range-sum-bst","bst","pruning","recursion","dsa"],
         code='''# Sum values of all nodes with low <= val <= high in a BST.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def range_sum_bst(root, low, high):
    if root is None:
        return 0
    if root.val < low:
        return range_sum_bst(root.right, low, high)   # prune the left subtree
    if root.val > high:
        return range_sum_bst(root.left, low, high)    # prune the right subtree
    # in range: this node + both sides
    return root.val + range_sum_bst(root.left, low, high) + range_sum_bst(root.right, low, high)''',
         complexity="Time O(n) worst, better with pruning; space O(h).",
         pitfalls="Not pruning (ignores BST order, slower); wrong prune direction relative to low/high.",
         example="For BST 10 -> (5 -> (3,7), 15 -> (_,18)), range_sum_bst(root,7,15) -> 32 (7+10+15)."),
    dict(cat="dsa", title="Third Maximum Number",
         answer="Return the third distinct maximum in an array, or the maximum if there are fewer than three distinct values. Track the top three distinct values in one pass (using None as 'unset'), shifting them down when a larger distinct value appears.",
         tags=["third-maximum","array","tracking","dsa"],
         code='''# The third distinct maximum in an array, or the max if fewer than 3 distinct.
def third_max(nums):
    first = second = third = None
    for n in set(nums):                   # distinct values only
        if first is None or n > first:
            first, second, third = n, first, second
        elif second is None or n > second:
            second, third = n, second
        elif third is None or n > third:
            third = n
    return third if third is not None else first''',
         complexity="Time O(n), space O(n) for the set (O(1) trackers).",
         pitfalls="Counting duplicates as distinct (dedupe first); returning None instead of the max when <3 distinct.",
         example="third_max([2,2,3,1]) -> 1; third_max([1,2]) -> 2."),
    dict(cat="glossary", title="Split-brain",
         answer="A dangerous failure where a network PARTITION splits a cluster into groups that lose contact and each believes it's the sole active/leader group — so both accept writes and DIVERGE the data. Prevented by requiring a QUORUM (a minority side steps down), fencing tokens, or a witness/tiebreaker node. It's why clusters use consensus and odd node counts.",
         tags=["split-brain","partition","quorum","distributed-systems","consistency"],
         example="A 2-node cluster is split by a network fault; without quorum both nodes promote themselves to primary and accept conflicting writes — a split-brain that corrupts data on rejoin."),
    dict(cat="glossary", title="Blue-green vs canary deployment",
         answer="Two safe-release strategies. BLUE-GREEN runs two full environments; you deploy to the idle one (green), test it, then switch ALL traffic at once — instant rollback by switching back, but doubles infra. CANARY sends the new version to a SMALL fraction of traffic first, watches metrics, then gradually ramps to 100% — limited blast radius but slower and reliant on good monitoring/routing.",
         tags=["blue-green","canary","deployment","release","devops"],
         example="Blue-green flips 100% of traffic from v1 to v2 in one switch (rollback = flip back); a canary sends 1% to v2, checks error rates, then 5% -> 25% -> 100%."),
    dict(cat="glossary", title="Star vs snowflake schema",
         answer="Data-warehouse modeling. A STAR schema has a central FACT table surrounded by DENORMALIZED dimension tables — simple, fast joins, some redundancy. A SNOWFLAKE schema NORMALIZES those dimensions into sub-dimension tables — less redundancy/storage but more joins and complexity. Star is usually preferred for BI query speed; snowflake when dimensions are large or must be normalized.",
         tags=["star-schema","snowflake-schema","data-warehouse","dimensional-modeling"],
         example="A sales star schema joins fact_sales directly to dim_product; snowflaking splits dim_product into product -> category -> department tables, adding joins to save space."),
    dict(cat="glossary", title="Data lake vs warehouse vs lakehouse",
         answer="Three analytical storage paradigms. A DATA WAREHOUSE stores structured, schema-on-WRITE data optimized for BI/SQL (Snowflake/Redshift) — governed but rigid. A DATA LAKE stores raw, any-format data cheaply with schema-on-READ (files on S3) — flexible but can become a 'swamp'. A LAKEHOUSE adds warehouse-like ACID tables and schema management ON TOP of a lake (Delta Lake/Iceberg) — one system for both BI and ML.",
         tags=["data-lake","data-warehouse","lakehouse","delta-lake","analytics"],
         example="Raw clickstream JSON lands in a data lake; a lakehouse table (Iceberg) over it adds ACID + SQL so analysts query it like a warehouse without copying the data out."),
    dict(cat="glossary", title="Materialized view",
         answer="A PRECOMPUTED, stored result of a query (unlike a regular view, which re-runs the query each time). It trades storage + refresh cost for fast reads of expensive aggregations/joins, and must be REFRESHED (fully or incrementally) as base data changes — so it's slightly stale between refreshes. Ideal for dashboards and repeated heavy queries.",
         tags=["materialized-view","precomputation","database","aggregation","caching"],
         example="A daily 'revenue by region' dashboard reads a materialized view refreshed each night instead of re-scanning the billion-row sales table on every page load."),
    dict(cat="conceptual", title="Why denormalize a database if normalization is the 'correct' design?",
         answer="Normalization (no redundant data) optimizes WRITE integrity and storage — updates touch one place, no anomalies — but it forces JOINS to reassemble data on reads, which get expensive at scale or under read-heavy load. Denormalization deliberately DUPLICATES data (precomputed aggregates, embedded copies, wide rows) to make reads fast and avoid joins — trading write complexity and a risk of inconsistency for read performance. Denormalize when reads vastly outnumber writes, join cost dominates, you're on a NoSQL/wide-column store lacking cheap joins, or you must precompute heavy rollups — accepting that you now keep duplicated copies in sync (app logic, triggers, CDC, or eventual consistency). Normalize for correctness by default; denormalize deliberately where read performance demands it.",
         tags=["denormalization","normalization","database","read-performance","why"],
         example="A product page needing product + reviews + seller joins 5 normalized tables per view, so you denormalize into one document or a materialized wide row for a single fast read — accepting that a seller-name change must update many copies."),
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

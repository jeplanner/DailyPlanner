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
    dict(cat="dsa", title="N-th Tribonacci Number",
         answer="Like Fibonacci but each term sums the previous THREE: T0=0, T1=1, T2=1, Tn = Tn-1 + Tn-2 + Tn-3. Roll three variables forward to compute Tn in O(n) time, O(1) space.",
         tags=["tribonacci","dynamic-programming","fibonacci","dp","dsa"],
         code='''# The n-th Tribonacci number: T0=0, T1=1, T2=1, Tn=Tn-1+Tn-2+Tn-3.
def tribonacci(n):
    if n == 0:
        return 0
    if n <= 2:
        return 1
    a, b, c = 0, 1, 1
    for _ in range(3, n + 1):
        a, b, c = b, c, a + b + c   # slide the window of three
    return c''',
         complexity="Time O(n), space O(1).",
         pitfalls="Wrong base cases (T2 is 1); summing only two terms.",
         example="tribonacci(4) -> 4  (0,1,1,2,4); tribonacci(25) -> 1389537."),
    dict(cat="dsa", title="Integer Break (DP)",
         answer="Break an integer n into the sum of at least two positive integers to MAXIMIZE their product. DP: dp[i] = the best product for i; for each split point j, take the max of j*(i-j) (don't break further) and j*dp[i-j] (break the rest). Mathematically the optimum uses as many 3s as possible.",
         tags=["integer-break","dynamic-programming","math","dp","dsa"],
         code='''# Break n into >=2 positive integers to MAXIMIZE their product (DP).
def integer_break(n):
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        for j in range(1, i):
            # j*(i-j): don't break i-j ; j*dp[i-j]: break i-j further
            dp[i] = max(dp[i], j * (i - j), j * dp[i - j])
    return dp[n]''',
         complexity="Time O(n^2), space O(n).",
         pitfalls="Requiring the whole number unbroken (must be >=2 parts); forgetting the j*(i-j) option.",
         example="integer_break(10) -> 36  (3*3*4); integer_break(2) -> 1."),
    dict(cat="dsa", title="Ugly Number",
         answer="An ugly number is a POSITIVE integer whose only prime factors are 2, 3, and 5. Repeatedly divide out all factors of 2, 3, and 5; if nothing but 1 remains, it's ugly. (0 and negatives are not ugly.)",
         tags=["ugly-number","math","factorization","dsa"],
         code='''# Is n an ugly number? (positive, only prime factors 2, 3, 5)
def is_ugly(n):
    if n <= 0:
        return False
    for factor in (2, 3, 5):
        while n % factor == 0:
            n //= factor        # divide out all 2s, 3s, then 5s
    return n == 1               # ugly iff nothing else remains''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Treating 0/negatives as ugly; not fully dividing out each factor.",
         example="is_ugly(6) -> True (2*3); is_ugly(14) -> False (has factor 7)."),
    dict(cat="dsa", title="Wiggle Subsequence (greedy)",
         answer="Find the length of the longest subsequence whose consecutive differences strictly ALTERNATE between positive and negative. Greedy O(n): track the longest wiggle ending on an 'up' move and on a 'down' move; a rise extends a down-ending, a fall extends an up-ending. Equal neighbours are ignored.",
         tags=["wiggle-subsequence","greedy","dynamic-programming","array","dsa"],
         code='''# Length of the longest subsequence whose differences strictly alternate sign.
def wiggle_max_length(nums):
    if len(nums) < 2:
        return len(nums)
    up = down = 1               # longest wiggle ending going up / down
    for i in range(1, len(nums)):
        if nums[i] > nums[i - 1]:
            up = down + 1        # a rise extends a down-ending subsequence
        elif nums[i] < nums[i - 1]:
            down = up + 1        # a fall extends an up-ending subsequence
    return max(up, down)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Counting equal adjacent values as a wiggle; overcomplicating with full DP.",
         example="wiggle_max_length([1,7,4,9,2,5]) -> 6; wiggle_max_length([1,2,2,2,3,4]) -> 2."),
    dict(cat="dsa", title="Backspace String Compare",
         answer="Two strings are equal if, after applying backspaces (where '#' deletes the preceding character), the results match. Build each final string with a stack (push normal chars, pop on '#'), then compare. (An O(1)-space two-pointer scan from the end also works.)",
         tags=["backspace-compare","stack","string","two-pointers","dsa"],
         code='''# Do two strings equal after applying backspaces ('#' deletes previous char)?
def backspace_compare(s, t):
    def build(string):
        stack = []
        for ch in string:
            if ch != '#':
                stack.append(ch)
            elif stack:
                stack.pop()      # backspace removes the last kept char
        return stack
    return build(s) == build(t)''',
         complexity="Time O(n + m), space O(n + m) (O(1) with two pointers).",
         pitfalls="Popping an empty stack on a leading '#'; comparing before applying backspaces.",
         example="backspace_compare('ab#c','ad#c') -> True (both -> 'ac'); backspace_compare('a#c','b') -> False."),
    dict(cat="dsa", title="Add Strings",
         answer="Add two non-negative integers given as strings WITHOUT converting the whole strings to ints. Add digit by digit from the right with a carry (like elementary-school addition), building the result and reversing at the end.",
         tags=["add-strings","string","math","carry","dsa"],
         code='''# Add two non-negative integers given as strings, digit by digit.
def add_strings(num1, num2):
    i, j = len(num1) - 1, len(num2) - 1
    carry = 0
    result = []
    while i >= 0 or j >= 0 or carry:
        d1 = ord(num1[i]) - ord('0') if i >= 0 else 0
        d2 = ord(num2[j]) - ord('0') if j >= 0 else 0
        total = d1 + d2 + carry
        result.append(str(total % 10))
        carry = total // 10
        i -= 1; j -= 1
    return "".join(reversed(result))''',
         complexity="Time O(max(n, m)), space O(that).",
         pitfalls="Dropping the final carry; not handling unequal lengths.",
         example="add_strings('456','77') -> '533'."),
    dict(cat="dsa", title="Last Stone Weight (max-heap)",
         answer="Repeatedly smash the two heaviest stones: if unequal, the difference goes back; if equal, both are destroyed. Return the last remaining stone's weight, or 0. A MAX-heap (negate values in Python's min-heap) always gives the two heaviest in O(log n).",
         tags=["last-stone-weight","heap","priority-queue","simulation","dsa"],
         code='''# Smash the two heaviest stones repeatedly; return the last weight (or 0).
import heapq
def last_stone_weight(stones):
    heap = [-s for s in stones]    # max-heap via negatives
    heapq.heapify(heap)
    while len(heap) > 1:
        first = -heapq.heappop(heap)
        second = -heapq.heappop(heap)
        if first != second:
            heapq.heappush(heap, -(first - second))   # the difference remains
    return -heap[0] if heap else 0''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Forgetting Python's heap is a min-heap (negate for max); not handling an empty heap.",
         example="last_stone_weight([2,7,4,1,8,1]) -> 1."),
    dict(cat="dsa", title="Kth Largest Element in a Stream",
         answer="Support add(val) returning the kth largest element seen so far. Keep a MIN-heap of size k: its root is always the kth largest; on each add, push and, if the heap exceeds k, pop the smallest. O(log k) per add.",
         tags=["kth-largest-stream","heap","priority-queue","design","dsa"],
         code='''# Maintain the kth largest element as numbers stream in (min-heap of size k).
import heapq
class KthLargest:
    def __init__(self, k, nums):
        self.k = k
        self.heap = nums[:]
        heapq.heapify(self.heap)
        while len(self.heap) > k:
            heapq.heappop(self.heap)   # keep only the k largest

    def add(self, val):
        heapq.heappush(self.heap, val)
        if len(self.heap) > self.k:
            heapq.heappop(self.heap)   # evict the smallest
        return self.heap[0]            # heap root = kth largest''',
         complexity="add is O(log k); space O(k).",
         pitfalls="Using a max-heap of everything (O(n) memory); returning the wrong end of the heap.",
         example="KthLargest(3, [4,5,8,2]): add(3)->4, add(5)->5, add(10)->5, add(9)->8, add(4)->8."),
    dict(cat="glossary", title="Raft consensus",
         answer="A consensus algorithm (a more understandable alternative to Paxos) that keeps a replicated LOG consistent across nodes despite failures. One elected LEADER accepts all writes, appends them to its log, and replicates to followers; an entry is COMMITTED once a majority (quorum) stores it. Leader election uses randomized timeouts + monotonic terms, and a new leader must have the most up-to-date log. It powers etcd, Consul, and CockroachDB.",
         tags=["raft","consensus","replication","leader-election","distributed-systems"],
         example="In etcd, the Raft leader replicates each key write to followers; once a majority acknowledge it's committed, and if the leader dies the followers elect a new one that has the latest log."),
    dict(cat="glossary", title="Gossip protocol",
         answer="A decentralized way to spread information (membership, state, failures) across a cluster: each node periodically exchanges state with a few RANDOM peers, so information propagates EXPONENTIALLY like an epidemic. It's robust (no coordinator), scalable, and eventually consistent, with some propagation delay. Used for membership and failure detection in Cassandra, Consul, and DynamoDB.",
         tags=["gossip-protocol","membership","failure-detection","eventual-consistency","distributed-systems"],
         example="In Cassandra each node gossips with a few random peers every second, so a node failure becomes known cluster-wide within seconds without any central registry."),
    dict(cat="glossary", title="Read-repair",
         answer="An anti-entropy technique in eventually-consistent replicated stores: on a READ, the coordinator compares responses from multiple replicas and, if some are stale, writes the newest value back to them — repairing divergence during normal reads. It piggybacks on reads (cheap) and works alongside hinted handoff and background anti-entropy to converge replicas.",
         tags=["read-repair","anti-entropy","replication","eventual-consistency","dynamo"],
         example="A quorum read finds replica C returns an old value while A and B return the new one; the coordinator returns the new value AND writes it back to C, healing the staleness."),
    dict(cat="glossary", title="Change Data Capture (CDC)",
         answer="A technique that captures row-level CHANGES (inserts/updates/deletes) from a database — typically by tailing its write-ahead log / binlog — and streams them to other systems in near-real-time. It keeps caches, search indexes, and warehouses in sync WITHOUT dual-writes or batch ETL. Debezium + Kafka is the common stack.",
         tags=["cdc","change-data-capture","debezium","streaming","data-integration"],
         example="Debezium reads MySQL's binlog and publishes each row change to Kafka, so a search index and a cache update within seconds of a DB write — no app-level dual-write needed."),
    dict(cat="glossary", title="OLAP vs OLTP",
         answer="Two database workloads. OLTP (transactional) handles many small, fast reads/writes of individual rows (orders, payments) — row-oriented, normalized, low-latency, high concurrency (Postgres/MySQL). OLAP (analytical) runs large aggregate SCANS over huge datasets for reporting/BI — column-oriented, denormalized, throughput-optimized (Snowflake/BigQuery/Redshift). You typically ETL/CDC from OLTP into an OLAP warehouse rather than analyzing the live transactional DB.",
         tags=["olap","oltp","columnar","data-warehouse","database"],
         example="Checkout writes to an OLTP Postgres (fast single-row insert); nightly, sales load into a columnar OLAP warehouse where 'revenue by region this quarter' scans billions of rows efficiently."),
    dict(cat="conceptual", title="Why do we need consensus algorithms (Raft/Paxos) instead of a naive majority vote?",
         answer="A naive vote breaks under distributed-system realities: messages are delayed, reordered, duplicated, or lost; nodes crash and restart; and network PARTITIONS can split the cluster so two halves each think they have a majority (SPLIT-BRAIN) and accept conflicting writes. Consensus solves agreement SAFELY: a quorum (majority) so any two decisions overlap on at least one node (preventing two conflicting commits), monotonic TERMS/epochs to fence out stale leaders, and a replicated log with a single leader so all nodes apply the same operations in the same order. The hard part isn't counting votes — it's guaranteeing safety (never two different committed values) AND liveness under arbitrary failures, which is subtle (see FLP). That's why you use a proven protocol.",
         tags=["consensus","raft","paxos","split-brain","quorum","why"],
         example="Without consensus, a partition could elect two leaders that accept different writes; Raft's terms + quorum ensure only the leader with majority support commits, so both sides can't make conflicting progress."),
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

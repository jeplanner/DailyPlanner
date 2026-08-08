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
    dict(cat="dsa", title="Assign Cookies (greedy)",
         answer="Maximize the number of content children: child i is content if given a cookie of size >= their greed g[i]. Sort both greeds and cookie sizes, then greedily give the smallest sufficient cookie to the least-greedy remaining child using two pointers.",
         tags=["assign-cookies","greedy","two-pointers","sorting","dsa"],
         code='''# Max children satisfied: child i needs a cookie of size >= greed g[i].
def find_content_children(g, s):
    g.sort(); s.sort()
    child = cookie = 0
    while child < len(g) and cookie < len(s):
        if s[cookie] >= g[child]:
            child += 1              # this cookie satisfies the child
        cookie += 1                 # advance the cookie pointer regardless
    return child''',
         complexity="Time O(n log n + m log m), space O(1).",
         pitfalls="Not sorting both arrays; advancing the child pointer on a non-match.",
         example="find_content_children([1,2,3],[1,1]) -> 1."),
    dict(cat="dsa", title="Lemonade Change (greedy)",
         answer="Each lemonade costs $5; customers pay with $5, $10, or $20 bills and you must give correct change. Greedily track your $5 and $10 counts; for a $20 prefer paying with a $10 + $5 (keeping $5s, which are more useful) and fall back to three $5s. Return False if you ever can't make change.",
         tags=["lemonade-change","greedy","simulation","dsa"],
         code='''# Can you give correct change selling lemonade at $5 (bills 5, 10, 20)?
def lemonade_change(bills):
    fives = tens = 0
    for bill in bills:
        if bill == 5:
            fives += 1
        elif bill == 10:
            if fives == 0:
                return False
            fives -= 1; tens += 1
        else:                        # a $20: prefer a 10 + 5, else three 5s
            if tens > 0 and fives > 0:
                tens -= 1; fives -= 1
            elif fives >= 3:
                fives -= 3
            else:
                return False
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Giving three $5s when a $10+$5 is available (wastes flexible $5s); no $20 bank needed.",
         example="lemonade_change([5,5,5,10,20]) -> True; lemonade_change([5,5,10,10,20]) -> False."),
    dict(cat="dsa", title="Can Place Flowers (greedy)",
         answer="Given a flowerbed (0=empty, 1=planted) where no two flowers may be adjacent, decide if n new flowers can be planted. Greedily plant in any empty spot whose neighbours are also empty. Padding the bed with 0 sentinels on both ends removes boundary special-cases.",
         tags=["can-place-flowers","greedy","array","dsa"],
         code='''# Can you plant n new flowers with no two adjacent? (0=empty, 1=planted)
def can_place_flowers(flowerbed, n):
    count = 0
    bed = [0] + flowerbed + [0]      # sentinels avoid boundary checks
    for i in range(1, len(bed) - 1):
        if bed[i - 1] == 0 and bed[i] == 0 and bed[i + 1] == 0:
            bed[i] = 1               # plant here
            count += 1
    return count >= n''',
         complexity="Time O(n), space O(n) (O(1) without the padding copy).",
         pitfalls="Boundary index errors (use sentinels); not marking a planted spot before checking the next.",
         example="can_place_flowers([1,0,0,0,1], 1) -> True; can_place_flowers([1,0,0,0,1], 2) -> False."),
    dict(cat="dsa", title="Array Partition I",
         answer="Split 2n numbers into n pairs to MAXIMIZE the sum of each pair's minimum. Sorting and pairing adjacent elements is optimal — take every element at an EVEN index (each pair's smaller element), because pairing a large number with the next-largest minimizes the 'loss' of the larger one.",
         tags=["array-partition","greedy","sorting","array","dsa"],
         code='''# Max sum of min(pairs) when pairing 2n numbers: sort, take every other.
def array_pair_sum(nums):
    nums.sort()
    return sum(nums[::2])            # sum of every element at an even index''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Pairing large with small (wastes the large one); summing odd indices.",
         example="array_pair_sum([1,4,3,2]) -> 4  (min(1,2) + min(3,4) = 1 + 3)."),
    dict(cat="dsa", title="Squares of a Sorted Array",
         answer="Given a sorted (possibly negative) array, return the squares sorted, in O(n). The largest squares come from the extremes, so use two pointers from both ends and fill the result array from the BACK with the larger square each step.",
         tags=["sorted-squares","two-pointers","array","dsa"],
         code='''# Squares of a sorted array, returned sorted, in O(n) (two pointers).
def sorted_squares(nums):
    n = len(nums)
    result = [0] * n
    left, right = 0, n - 1
    for i in range(n - 1, -1, -1):
        if abs(nums[left]) > abs(nums[right]):
            result[i] = nums[left] ** 2   # larger magnitude fills the back
            left += 1
        else:
            result[i] = nums[right] ** 2
            right -= 1
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Sorting after squaring (O(n log n) — the two-pointer fill is O(n)); filling from the front.",
         example="sorted_squares([-4,-1,0,3,10]) -> [0,1,9,16,100]."),
    dict(cat="dsa", title="Sort Array By Parity",
         answer="Rearrange an array so all EVEN numbers come before all odd numbers (any relative order). Two pointers from the ends: skip evens on the left and odds on the right, and swap when the left is odd and the right is even.",
         tags=["sort-by-parity","two-pointers","in-place","array","dsa"],
         code='''# Move all even numbers before all odd numbers (any order), two pointers.
def sort_array_by_parity(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        if nums[left] % 2 == 0:
            left += 1               # even already on the left
        elif nums[right] % 2 == 1:
            right -= 1              # odd already on the right
        else:
            nums[left], nums[right] = nums[right], nums[left]
    return nums''',
         complexity="Time O(n), space O(1).",
         pitfalls="Advancing both pointers on a swap without re-checking; infinite loop with wrong conditions.",
         example="sort_array_by_parity([3,1,2,4]) -> [4,2,1,3] (evens first; order may vary)."),
    dict(cat="dsa", title="Find the Difference (XOR)",
         answer="String t is string s shuffled with one EXTRA character added; find the extra one. XOR the char codes of every character in both strings — each character of s cancels its match in t, leaving only the code of the added character.",
         tags=["find-difference","xor","bit-manipulation","string","dsa"],
         code='''# t is s shuffled plus one extra char; find it via XOR (all pairs cancel).
def find_the_difference(s, t):
    result = 0
    for ch in s + t:
        result ^= ord(ch)          # each char in s cancels its match in t
    return chr(result)             # the lone extra char's code remains''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using counts (works but heavier); forgetting XOR of a value with itself is 0.",
         example="find_the_difference('abcd','abcde') -> 'e'."),
    dict(cat="dsa", title="Distribute Candies",
         answer="A person may eat only n/2 candies (n even). Maximize the number of DISTINCT flavours eaten. The answer is min(number of distinct types, n/2) — you can taste every type up to the eating limit.",
         tags=["distribute-candies","greedy","hash-set","array","dsa"],
         code='''# Max kinds of candy eaten if you eat exactly n/2 candies.
def distribute_candies(candy_type):
    kinds = len(set(candy_type))              # distinct flavours available
    return min(kinds, len(candy_type) // 2)   # capped by how many you eat''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting the n/2 cap; counting total candies instead of distinct types.",
         example="distribute_candies([1,1,2,2,3,3]) -> 3; distribute_candies([1,1,1,1]) -> 1."),
    dict(cat="glossary", title="Connection pooling",
         answer="Keeping a POOL of pre-established, reusable database connections instead of opening a new one per request. Opening a DB connection is expensive (TCP + TLS + auth + session setup, often milliseconds), and DBs cap concurrent connections. A pool lends an idle connection and reclaims it after use — cutting latency and protecting the DB from connection exhaustion. Size the pool to the DB's connection limit.",
         tags=["connection-pooling","database","performance","concurrency"],
         example="A web app with a pool of 20 connections serves thousands of requests/sec by reusing them, rather than paying the setup cost (and overwhelming the DB) on every request."),
    dict(cat="glossary", title="N+1 query problem",
         answer="A common ORM/data-access anti-pattern: fetching a list of N items triggers ONE query for the list plus N more (one per item) to load related data — N+1 queries instead of 1-2. Round-trip latency then dominates. Fixed by eager loading, a JOIN, or batching the related fetch into a single IN(...) query.",
         tags=["n-plus-one","orm","database","performance","query"],
         example="Loading 100 posts then lazily fetching each post's author fires 1 + 100 = 101 queries; a JOIN or 'authors WHERE id IN (...)' batch cuts it to 2."),
    dict(cat="glossary", title="Zero-copy",
         answer="An I/O optimization that moves data between a file and a socket WITHOUT copying it through user-space application buffers (and often fewer kernel copies), via calls like sendfile()/mmap. It saves CPU and memory bandwidth for high-throughput transfer. Kafka famously uses zero-copy to send log segments from the OS page cache straight to the network socket.",
         tags=["zero-copy","io","sendfile","performance","kafka"],
         example="Kafka serves a consumer by sendfile()-ing bytes directly from the OS page cache to the socket, skipping a copy into the JVM heap — a big reason it sustains such high throughput."),
    dict(cat="glossary", title="fsync (durability)",
         answer="A system call that forces buffered writes to be PHYSICALLY persisted to the storage device, not just held in the OS page cache — without it, a crash loses recently 'written' data still in memory. Databases fsync the WAL before acknowledging a commit to guarantee durability (the D in ACID), but fsync is slow (waits on the disk), so it's a core throughput/durability trade-off (group commit batches many fsyncs).",
         tags=["fsync","durability","wal","acid","storage"],
         example="Postgres fsyncs the WAL on commit so an acknowledged transaction survives power loss; disabling synchronous_commit skips the wait for higher throughput, risking loss of the last few transactions on a crash."),
    dict(cat="glossary", title="Prepared statement",
         answer="A parameterized SQL statement PARSED, PLANNED, and compiled ONCE, then executed many times with different bound parameter values. Benefits: performance (skip re-parsing/re-planning each run) and SECURITY — parameters are sent separately from the SQL text, so user input can't alter the query structure, preventing SQL INJECTION. Always prefer them over string-concatenated queries.",
         tags=["prepared-statement","sql-injection","database","security","performance"],
         example="'SELECT * FROM users WHERE email = ?' with a bound value is safe and fast; concatenating the email into the SQL string risks injection like ' OR '1'='1."),
    dict(cat="conceptual", title="Why use connection pooling instead of a database connection per request?",
         answer="Opening a DB connection is EXPENSIVE and slow: a TCP handshake, TLS negotiation, authentication, and server-side session/backend setup — often several milliseconds that dwarf a fast query and add up under load. Databases also CAP concurrent connections (each costs memory/a backend process), so connection-per-request under high concurrency exhausts the limit and the DB rejects or thrashes. A POOL fixes both: it keeps a fixed set of warm, authenticated connections and lends an idle one per request, returning it afterward — so requests pay ~zero setup cost and the DB never exceeds pool-size concurrency. The pool size doubles as a concurrency limiter/backpressure tuned to the DB's capacity. Trade-offs: managing sizing, timeouts, and dead-connection recovery — too small bottlenecks, too large overloads the DB.",
         tags=["connection-pooling","database","performance","backpressure","why"],
         example="Without pooling, 1000 req/s each opening a fresh connection would swamp Postgres's ~100-connection limit and pay ~2ms setup each; a pool of 20 warm connections serves all of them by reusing connections, keeping the DB healthy and latency low."),
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

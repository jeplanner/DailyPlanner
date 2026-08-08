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
    dict(cat="dsa", title="Rotate Image (in-place 90 degrees)",
         answer="Rotate an n×n matrix 90 degrees clockwise IN PLACE. Two-step trick: TRANSPOSE the matrix (swap element [i][j] with [j][i]), then REVERSE each row. Transpose flips across the main diagonal; reversing rows completes the clockwise rotation. O(1) extra space.",
         tags=["rotate-image","matrix","in-place","transpose","dsa"],
         code='''# Rotate an n x n matrix 90 degrees clockwise, in place.
def rotate_image(matrix):
    n = len(matrix)
    for i in range(n):                     # transpose across the main diagonal
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:                     # then reverse each row
        row.reverse()
    return matrix''',
         complexity="Time O(n^2), space O(1).",
         pitfalls="Transposing the full range (double-swaps back to original) — only j>i; reversing columns instead of rows.",
         example="rotate_image([[1,2,3],[4,5,6],[7,8,9]]) -> [[7,4,1],[8,5,2],[9,6,3]]."),
    dict(cat="dsa", title="Spiral Matrix II (generate)",
         answer="Generate an n×n matrix filled with 1..n^2 in spiral (clockwise) order. Maintain four shrinking boundaries (top, bottom, left, right) and walk the perimeter — top row left-to-right, right column top-to-bottom, bottom row right-to-left, left column bottom-to-top — writing an incrementing counter, shrinking the boundary after each side.",
         tags=["spiral-matrix","matrix","simulation","dsa"],
         code='''# Generate an n x n matrix filled 1..n^2 in spiral order.
def generate_spiral(n):
    matrix = [[0] * n for _ in range(n)]
    top, bottom, left, right = 0, n - 1, 0, n - 1
    num = 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            matrix[top][c] = num; num += 1
        top += 1
        for r in range(top, bottom + 1):
            matrix[r][right] = num; num += 1
        right -= 1
        for c in range(right, left - 1, -1):
            matrix[bottom][c] = num; num += 1
        bottom -= 1
        for r in range(bottom, top - 1, -1):
            matrix[r][left] = num; num += 1
        left += 1
    return matrix''',
         complexity="Time O(n^2), space O(n^2) for the output.",
         pitfalls="Not shrinking the boundaries; overwriting the center on odd n (the while bounds handle it).",
         example="generate_spiral(3) -> [[1,2,3],[8,9,4],[7,6,5]]."),
    dict(cat="dsa", title="Pow(x, n) — fast exponentiation",
         answer="Compute x^n in O(log n) using BINARY (fast) exponentiation: square the base while walking the bits of n, multiplying the result whenever a bit is set — because x^n = product of x^(2^k) for each set bit k. Handle negative n by inverting x and negating n.",
         tags=["fast-exponentiation","pow","bit-manipulation","math","dsa"],
         code='''# Compute x^n in O(log n) via fast (binary) exponentiation.
def my_pow(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    result = 1.0
    while n > 0:
        if n & 1:           # current bit set -> multiply in the current power
            result *= x
        x *= x              # square the base for the next bit
        n >>= 1
    return result''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Multiplying x by itself n times (O(n) — too slow); mishandling negative n.",
         example="my_pow(2.0, 10) -> 1024.0; my_pow(2.0, -2) -> 0.25."),
    dict(cat="dsa", title="Sqrt(x) — integer square root (binary search)",
         answer="Return the floor of the square root of a non-negative integer WITHOUT a float sqrt. Binary-search the answer in [1, x//2]: for a candidate mid, compare mid*mid to x and narrow the range. When the loop ends, the high pointer sits on floor(sqrt(x)).",
         tags=["sqrt","binary-search","math","dsa"],
         code='''# Integer square root of x (floor) via binary search, no float sqrt.
def my_sqrt(x):
    if x < 2:
        return x
    lo, hi = 1, x // 2
    while lo <= hi:
        mid = (lo + hi) // 2
        sq = mid * mid
        if sq == x:
            return mid
        if sq < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi                # hi ends on the floor of the square root''',
         complexity="Time O(log x), space O(1).",
         pitfalls="Overflow of mid*mid in low-level languages; returning lo instead of hi for the floor.",
         example="my_sqrt(8) -> 2; my_sqrt(16) -> 4."),
    dict(cat="dsa", title="Count Primes (Sieve of Eratosthenes)",
         answer="Count the primes strictly less than n. The Sieve of Eratosthenes marks composites: for each prime p, cross off its multiples starting at p*p (smaller multiples were already crossed by smaller primes). Only sieve p up to sqrt(n). The remaining unmarked numbers are prime.",
         tags=["count-primes","sieve-of-eratosthenes","math","dsa"],
         code='''# Count primes strictly less than n using the Sieve of Eratosthenes.
def count_primes(n):
    if n < 3:
        return 0
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p < n:
        if is_prime[p]:
            for multiple in range(p * p, n, p):   # cross off multiples of p
                is_prime[multiple] = False
        p += 1
    return sum(is_prime)''',
         complexity="Time O(n log log n), space O(n).",
         pitfalls="Starting the inner loop at 2*p instead of p*p (slower); sieving p beyond sqrt(n) (wasted work).",
         example="count_primes(10) -> 4  (2, 3, 5, 7)."),
    dict(cat="dsa", title="Happy Number",
         answer="A number is 'happy' if repeatedly replacing it with the sum of the squares of its digits eventually reaches 1; otherwise it loops forever. Detect the loop with a seen-set (or Floyd's cycle detection): if you revisit a number before hitting 1, it's not happy.",
         tags=["happy-number","hash-set","cycle-detection","math","dsa"],
         code='''# Is n 'happy'? Repeatedly sum squares of digits; happy if it reaches 1.
def is_happy(n):
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(d) ** 2 for d in str(n))   # sum of squared digits
    return n == 1''',
         complexity="Time O(log n) per step over few steps, space O(count of seen).",
         pitfalls="No cycle detection -> infinite loop for unhappy numbers; summing digits instead of their squares.",
         example="is_happy(19) -> True (1+81+... -> ... -> 1); is_happy(2) -> False."),
    dict(cat="dsa", title="Reverse Bits",
         answer="Reverse the bit order of a 32-bit unsigned integer. Build the result by repeatedly shifting it left and appending the current lowest bit of the input, while shifting the input right — 32 iterations move each bit to its mirrored position.",
         tags=["reverse-bits","bit-manipulation","dsa"],
         code='''# Reverse the bits of a 32-bit unsigned integer.
def reverse_bits(n):
    result = 0
    for _ in range(32):
        result = (result << 1) | (n & 1)   # shift result left, take n's low bit
        n >>= 1                             # drop n's low bit
    return result''',
         complexity="Time O(32) = O(1), space O(1).",
         pitfalls="Not fixing the 32-bit width; forgetting to shift the result left before OR-ing.",
         example="reverse_bits(43261596) -> 964176192."),
    dict(cat="dsa", title="Roman to Integer",
         answer="Convert a Roman numeral to an integer. Scan left to right adding each symbol's value, EXCEPT when a smaller value precedes a larger one (e.g. IV, IX, CM) — then subtract it. Checking the next symbol's value handles all six subtractive cases uniformly.",
         tags=["roman-to-integer","string","math","dsa"],
         code='''# Convert a Roman numeral string to an integer.
def roman_to_int(s):
    values = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    total = 0
    for i in range(len(s)):
        # a smaller value before a larger one is subtractive (IV = 4)
        if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
            total -= values[s[i]]
        else:
            total += values[s[i]]
    return total''',
         complexity="Time O(len(s)), space O(1).",
         pitfalls="Not handling the subtractive pairs; index out of range on the last char (guard i+1).",
         example="roman_to_int('MCMXCIV') -> 1994."),
    dict(cat="glossary", title="Bloom filter",
         answer="A space-efficient PROBABILISTIC set that answers 'is x possibly in the set?' with NO false negatives but some false positives. It hashes each element to k bits in a bit array and sets them; a lookup checks those k bits — any 0 means definitely absent, all 1s means probably present. Used to skip expensive lookups (does this key exist before I hit disk?).",
         tags=["bloom-filter","probabilistic","hashing","data-structure"],
         example="An LSM database checks a per-file Bloom filter before reading an SSTable from disk — if it says 'no', it skips the disk read entirely, saving I/O for keys that aren't there."),
    dict(cat="glossary", title="LSM tree vs B-tree",
         answer="Two storage-engine index structures. A B-TREE updates data in place (great for reads, range scans, and random access) — the classic relational-DB index. An LSM TREE (log-structured merge) buffers writes in memory then flushes sorted files to disk, merging them via background COMPACTION — optimized for high WRITE throughput (sequential writes) at some read/space-amplification cost. LSM powers write-heavy stores (Cassandra, RocksDB, LevelDB).",
         tags=["lsm-tree","b-tree","storage-engine","database","indexing"],
         example="A write-heavy ingest/time-series workload uses an LSM engine (RocksDB) for fast sequential writes; a read/update-heavy OLTP workload uses a B-tree (InnoDB/Postgres)."),
    dict(cat="glossary", title="Write-ahead log (WAL)",
         answer="A durability + crash-recovery technique: before applying a change to the database's data pages, first APPEND it to a sequential on-disk log. If the system crashes mid-operation, replaying the log restores committed changes and discards incomplete ones. Sequential log writes are fast, and the log doubles as the source for replication.",
         tags=["write-ahead-log","wal","durability","recovery","database"],
         example="Postgres writes every change to the WAL and fsyncs it before acknowledging a commit; after a crash it replays the WAL to recover, and replicas stream the WAL to stay in sync."),
    dict(cat="glossary", title="MVCC (Multi-Version Concurrency Control)",
         answer="A concurrency scheme where writers create NEW versions of rows instead of overwriting, so readers see a consistent SNAPSHOT without blocking writers (and vice versa). Each transaction reads the version valid as of its start. It gives high read concurrency and snapshot isolation; obsolete versions are garbage-collected. Used by Postgres, Oracle, and MySQL/InnoDB.",
         tags=["mvcc","concurrency","snapshot-isolation","database","transactions"],
         example="In Postgres, a long report reads a consistent snapshot as of its start time even as other transactions update rows — because each update writes a new row version rather than overwriting."),
    dict(cat="glossary", title="Quorum (read/write, W+R>N)",
         answer="In a system with N replicas, require W replicas to ack a write and R to answer a read. If W + R > N, the read set and write set OVERLAP on at least one replica, so a read always sees the latest write — tunable consistency. Larger W/R means stronger consistency but lower availability/higher latency; it's the classic Dynamo-style knob.",
         tags=["quorum","replication","consistency","distributed-systems","dynamo"],
         example="With N=3, W=2, R=2 (W+R=4>3), a write acked by 2 nodes and a read from 2 nodes always overlap on at least one up-to-date replica, so reads see the latest write."),
    dict(cat="conceptual", title="Why do databases use B-trees / LSM-trees instead of a hash index for most workloads?",
         answer="A hash index gives O(1) point lookups but CANNOT do range queries, ordered scans, or prefix searches, and it handles larger-than-memory data less gracefully. Most real workloads need WHERE x BETWEEN, ORDER BY, and range/prefix scans, which require an ORDERED structure. B-trees keep keys sorted in shallow, disk-friendly nodes (few seeks per lookup) and support ranges; LSM-trees keep sorted runs merged over time for write-heavy ordered data. Hash indexes fit only narrow exact-match, in-memory cases. Ordering + disk-efficiency + range support matter more than a marginally faster point lookup.",
         tags=["b-tree","lsm-tree","hash-index","database","why"],
         example="'SELECT * FROM orders WHERE created BETWEEN X AND Y ORDER BY created' is trivial on a B-tree (walk a sorted range) but impossible on a hash index, which stores keys in no meaningful order."),
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

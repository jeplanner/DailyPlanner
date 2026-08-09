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
    dict(cat="dsa", title="Find Words Containing Character",
         answer="Return the indices of all words that CONTAIN a given character x. A single filter over the words checking membership.",
         tags=["find-words-char","string","filtering","array","dsa"],
         code='''# Indices of words that contain the given character x.
def find_words_containing(words, x):
    return [i for i, w in enumerate(words) if x in w]''',
         complexity="Time O(total characters), space O(n).",
         pitfalls="Returning the words instead of their indices; case sensitivity.",
         example="find_words_containing(['leet','code'], 'e') -> [0,1]."),
    dict(cat="dsa", title="Largest Odd Number in String",
         answer="Given a numeric string, return the largest-valued ODD number that is a (non-empty) PREFIX of it, or '' if none. An odd number ends in an odd digit, so scan from the RIGHT for the last odd digit — the prefix up to and including it is the largest odd substring starting at index 0.",
         tags=["largest-odd-number","string","greedy","math","dsa"],
         code='''# Longest prefix of the digit string that forms an odd number (or '').
def largest_odd_number(num):
    for i in range(len(num) - 1, -1, -1):
        if int(num[i]) % 2 == 1:      # last odd digit from the right
            return num[:i + 1]         # that prefix is the largest odd number
    return ""''',
         complexity="Time O(n), space O(1).",
         pitfalls="Searching from the left (you want the longest valid prefix); returning a substring not anchored at index 0.",
         example="largest_odd_number('52') -> '5'; largest_odd_number('4206') -> ''."),
    dict(cat="dsa", title="Sum of Squares of Special Elements",
         answer="An element at 1-based index i is 'special' if i divides the array length n. Return the sum of the squares of the special elements. Iterate; include nums[i]^2 whenever (i+1) divides n.",
         tags=["sum-of-squares","math","divisors","array","dsa"],
         code='''# Sum of squares of elements at 1-based indices that divide n.
def sum_of_squares(nums):
    n = len(nums)
    return sum(nums[i] ** 2 for i in range(n) if n % (i + 1) == 0)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using 0-based index for divisibility (it's 1-based); squaring the index instead of the value.",
         example="sum_of_squares([1,2,3,4]) -> 21  (indices 1,2,4 divide 4: 1 + 4 + 16)."),
    dict(cat="dsa", title="Count Tested Devices After Test Operations",
         answer="Devices are tested in order; testing a device with positive battery decrements every LATER device's battery by 1. Count how many get tested. Track how many have been tested so far (= the accumulated decrement); a device is testable if its battery minus that count is still positive.",
         tags=["count-tested-devices","greedy","simulation","array","dsa"],
         code='''# Count devices tested: each test decrements all later devices' battery by 1.
def count_tested_devices(battery_percentages):
    tested = 0
    for b in battery_percentages:
        if b - tested > 0:      # battery after prior decrements is still > 0
            tested += 1
    return tested''',
         complexity="Time O(n), space O(1).",
         pitfalls="Actually mutating the array (O(n^2)); the running 'tested' count IS the accumulated decrement.",
         example="count_tested_devices([1,1,2,1,3]) -> 3."),
    dict(cat="dsa", title="Find First Palindromic String in the Array",
         answer="Return the FIRST string that reads the same forwards and backwards, or '' if none. Check each string against its reverse in order.",
         tags=["first-palindrome","string","palindrome","array","dsa"],
         code='''# First string that reads the same forwards and backwards, or ''.
def first_palindrome(words):
    for w in words:
        if w == w[::-1]:
            return w
    return ""''',
         complexity="Time O(total characters), space O(1).",
         pitfalls="Returning any palindrome instead of the first; forgetting the empty-result case.",
         example="first_palindrome(['abc','car','ada','racecar']) -> 'ada'."),
    dict(cat="dsa", title="Separate the Digits in an Array",
         answer="Replace each integer with its individual DIGITS (in the same order), flattening the result. Convert each number to a string and expand its characters into single digits.",
         tags=["separate-digits","array","digits","dsa"],
         code='''# Flatten each integer into its individual digits, preserving order.
def separate_digits(nums):
    result = []
    for n in nums:
        result.extend(int(d) for d in str(n))   # split each number into digits
    return result''',
         complexity="Time O(total digits), space O(total digits).",
         pitfalls="Reversing digits accidentally; keeping numbers as strings when ints are expected.",
         example="separate_digits([13,25,83,77]) -> [1,3,2,5,8,3,7,7]."),
    dict(cat="dsa", title="Smallest Even Multiple",
         answer="Return the smallest positive integer that is a multiple of BOTH 2 and n — i.e. lcm(2, n). If n is already even it's n itself; otherwise it's 2*n.",
         tags=["smallest-even-multiple","math","lcm","dsa"],
         code='''# Smallest positive integer that is a multiple of both 2 and n.
def smallest_even_multiple(n):
    return n if n % 2 == 0 else n * 2   # lcm(2, n)''',
         complexity="Time O(1), space O(1).",
         pitfalls="Always returning 2*n (wrong when n is even); computing a full LCM when the parity check suffices.",
         example="smallest_even_multiple(5) -> 10; smallest_even_multiple(6) -> 6."),
    dict(cat="dsa", title="Remove Trailing Zeros From a String",
         answer="Given a numeric string, remove any TRAILING zeros. A single right-strip of '0' characters does it.",
         tags=["remove-trailing-zeros","string","dsa"],
         code='''# Remove trailing zeros from a numeric string.
def remove_trailing_zeros(num):
    return num.rstrip("0")   # strip '0' characters from the right end''',
         complexity="Time O(n), space O(n).",
         pitfalls="Stripping leading zeros too (only trailing); using strip() which trims both ends.",
         example="remove_trailing_zeros('51230100') -> '512301'."),
    dict(cat="glossary", title="mmap (memory-mapped files)",
         answer="Mapping a file (or device) directly into a process's virtual ADDRESS SPACE so it can be read/written like an in-memory array, with the OS paging data in/out on demand. Benefits: no explicit read/write syscall per access, lazy loading (only touched pages load), and a shared page cache (multiple processes map the same file cheaply). Great for large files, databases, and shared memory. Downside: I/O errors surface as page faults, and you need msync to control when writes hit disk.",
         tags=["mmap","memory-mapped","io","page-cache","operating-systems"],
         example="A database like LMDB or SQLite mmaps its data file so it reads pages straight from the OS page cache as memory, avoiding a read() syscall per access."),
    dict(cat="glossary", title="Buffered vs direct I/O",
         answer="Two ways an app does disk I/O. BUFFERED (default) goes through the OS PAGE CACHE — reads are cached (fast repeats) and writes are buffered and flushed later; convenient but uses OS memory and adds a copy. DIRECT I/O (O_DIRECT) bypasses the page cache, transferring straight between the app buffer and disk — used by databases that manage their OWN cache (avoiding double-caching, gaining predictable I/O), at the cost of alignment rules and losing OS read-ahead.",
         tags=["direct-io","buffered-io","page-cache","o-direct","operating-systems"],
         example="Postgres uses buffered I/O (relying on the OS cache) while some databases use O_DIRECT to avoid double-buffering data they already cache in their own buffer pool."),
    dict(cat="glossary", title="TCP slow start",
         answer="A congestion-control phase where a new TCP connection starts by sending only a SMALL amount of data (a small congestion window) and DOUBLES it each round trip (exponential) until it hits a threshold or detects loss. It probes the available bandwidth cautiously instead of flooding an unknown-capacity path, preventing a new flow from overwhelming it. After the threshold it switches to slower linear congestion-avoidance growth.",
         tags=["tcp-slow-start","congestion-control","tcp","networking"],
         example="A fresh connection ramps the window 2->4->8->16 packets per RTT, which is why the first few round trips of a download are slower than steady state — and why keep-alive matters."),
    dict(cat="glossary", title="Nagle's algorithm",
         answer="A TCP optimization that reduces the overhead of many TINY packets by BUFFERING small writes until either a full-size segment accumulates OR the previously sent data is acknowledged. It improves efficiency for bulk small writes but adds LATENCY for interactive/real-time traffic (a small message may wait for an ACK). Latency-sensitive apps disable it with TCP_NODELAY; it can interact badly with delayed ACKs, causing stalls.",
         tags=["nagle","tcp-nodelay","tcp","latency","networking"],
         example="A chat or game protocol sets TCP_NODELAY to disable Nagle so each tiny message sends immediately instead of waiting to batch — trading efficiency for low latency."),
    dict(cat="glossary", title="TTL index",
         answer="A database feature that automatically EXPIRES and deletes records after a set time-to-live, based on a timestamp field — you declare 'delete rows older than N seconds' and the DB reclaims them in the background, no cleanup cron needed. Ideal for ephemeral data: sessions, caches, OTPs, logs, rate-limit counters. MongoDB TTL indexes and Redis key TTLs are common examples.",
         tags=["ttl-index","expiry","mongodb","redis","database"],
         example="A MongoDB TTL index on a sessions collection's createdAt with expireAfterSeconds=3600 auto-deletes each session an hour after creation — no cron job."),
    dict(cat="conceptual", title="Why does TCP start slow (slow start) instead of sending at full speed immediately?",
         answer="A new connection has NO IDEA how much bandwidth the path can handle or how congested the network is — the capacity across many links/routers is unknown and shifting. If every new flow blasted at full line rate immediately, they'd collectively overwhelm router buffers, cause mass packet loss, and trigger CONGESTION COLLAPSE (the network gets busier but throughput plummets as everyone retransmits). Slow start solves this by PROBING: begin with a tiny congestion window (a few packets), and since each successful round trip proves the path handled that much, DOUBLE the window each RTT — exponential growth reaching high throughput within a handful of RTTs while backing off instantly if loss appears. It's 'exponential but cautious': fast enough to ramp quickly, safe enough not to swamp an unknown path. Near the estimated capacity (a threshold or after a loss) it shifts to congestion AVOIDANCE (slow linear growth) to push the limit gently. The cost: short connections may finish while still in slow start and never reach full bandwidth — which is exactly why keep-alive, connection pooling, and 0-RTT resumption matter (they skip the ramp). Slow start is what lets millions of independent flows share the internet fairly and stably with no central coordinator.",
         tags=["tcp-slow-start","congestion-control","congestion-collapse","tcp","why"],
         example="Downloading a large file, the first ~50ms feels slower as the window ramps 2->4->8->16 packets/RTT, then hits full speed; a tiny API call may finish entirely during slow start — so reusing the warmed-up connection for the next call is much faster."),
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

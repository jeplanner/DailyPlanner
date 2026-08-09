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
    dict(cat="dsa", title="Day of the Year",
         answer="Given a 'YYYY-MM-DD' date, return its ordinal day number within the year (1-366). Sum the days of the months before it plus the day, adjusting February to 29 in leap years (divisible by 4, except centuries not divisible by 400).",
         tags=["day-of-year","date","math","dsa"],
         code='''# Ordinal day-of-year for a 'YYYY-MM-DD' date (handles leap years).
def day_of_year(date):
    year, month, day = map(int, date.split('-'))
    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    # leap year: divisible by 4, except centuries not divisible by 400
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_month[1] = 29
    return sum(days_in_month[:month - 1]) + day''',
         complexity="Time O(1), space O(1).",
         pitfalls="Wrong leap-year rule (the century exception); off-by-one summing months before the current one.",
         example="day_of_year('2019-01-09') -> 9; day_of_year('2019-02-10') -> 41."),
    dict(cat="dsa", title="Minimum Recolors to Get K Consecutive Black Blocks",
         answer="A string of 'B'/'W' blocks; find the fewest recolors (W->B) so some window of k consecutive blocks is all black. Sliding window: the recolors for a window equal its number of W's; slide the window of size k and track the minimum W count.",
         tags=["min-recolors","sliding-window","string","dsa"],
         code='''# Fewest recolors so some window of k blocks is all black ('B'); 'W'=white.
def minimum_recolors(blocks, k):
    whites = blocks[:k].count('W')     # recolors needed for the first window
    best = whites
    for i in range(k, len(blocks)):
        whites += (blocks[i] == 'W') - (blocks[i - k] == 'W')   # slide window
        best = min(best, whites)
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Recounting the whole window each step (O(n*k)); off-by-one on the window slide.",
         example="minimum_recolors('WBBWWBBWBW', 7) -> 3."),
    dict(cat="dsa", title="Number of Senior Citizens",
         answer="Each passenger detail is a fixed-format string (10-digit phone, 1 gender char, 2-digit age, 2-digit seat). Count passengers strictly OLDER than 60 by parsing the age substring at positions 11-12.",
         tags=["senior-citizens","string","parsing","array","dsa"],
         code='''# Count passengers strictly older than 60, reading age from the ticket string.
def count_seniors(details):
    # each detail: 10 digits phone + 1 gender char + 2 digit age + 2 digit seat
    return sum(1 for d in details if int(d[11:13]) > 60)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Wrong substring offsets for the age; using >= instead of > (strictly older).",
         example="count_seniors(['7868190130M7522','5303914400F9211','9273338290F4010']) -> 2."),
    dict(cat="dsa", title="Sum of Values at Indices With K Set Bits",
         answer="Sum the elements whose INDEX has exactly k set bits (1s) in binary. Iterate indices, count each index's popcount, and add the value when it equals k.",
         tags=["sum-k-set-bits","bit-manipulation","array","dsa"],
         code='''# Sum of nums[i] where the index i has exactly k set bits in binary.
def sum_indices_with_k_set_bits(nums, k):
    return sum(nums[i] for i in range(len(nums)) if bin(i).count('1') == k)''',
         complexity="Time O(n log n) for the bit counts, space O(1).",
         pitfalls="Counting set bits of the VALUE instead of the index; miscounting popcount.",
         example="sum_indices_with_k_set_bits([5,10,1,5,2], 1) -> 13  (indices 1,2,4)."),
    dict(cat="dsa", title="Triangle (Minimum Path Sum)",
         answer="Find the minimum top-to-bottom path sum in a triangle where each step moves to an adjacent number in the row below. BOTTOM-UP DP: start from the last row and, for each cell above, add it to the smaller of its two children — the top cell ends with the answer. O(n) extra space.",
         tags=["triangle","minimum-path-sum","dynamic-programming","dp","dsa"],
         code='''# Minimum top-to-bottom path sum in a triangle (bottom-up DP).
def minimum_total(triangle):
    dp = triangle[-1][:]              # start from the bottom row
    for row in range(len(triangle) - 2, -1, -1):
        for col in range(len(triangle[row])):
            # each cell + the smaller of its two children below
            dp[col] = triangle[row][col] + min(dp[col], dp[col + 1])
    return dp[0]''',
         complexity="Time O(n^2) over the triangle cells, space O(n).",
         pitfalls="Top-down without memoization (exponential); wrong adjacency (col and col+1 below).",
         example="minimum_total([[2],[3,4],[6,5,7],[4,1,8,3]]) -> 11  (2+3+5+1)."),
    dict(cat="dsa", title="Longest Palindromic Subsequence",
         answer="Find the length of the longest subsequence of a string that is a palindrome. Interval DP: dp[i][j] is the answer for s[i..j]; if the ends match, dp[i][j] = dp[i+1][j-1] + 2, else the max of dropping either end. Fill by increasing interval length.",
         tags=["longest-palindromic-subsequence","dynamic-programming","interval-dp","string","dp","dsa"],
         code='''# Length of the longest palindromic subsequence (interval DP).
def longest_palindrome_subseq(s):
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        dp[i][i] = 1                 # a single char is a palindrome of length 1
        for j in range(i + 1, n):
            if s[i] == s[j]:
                dp[i][j] = dp[i + 1][j - 1] + 2   # extend the inner palindrome
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]''',
         complexity="Time O(n^2), space O(n^2).",
         pitfalls="Confusing subsequence (gaps allowed) with substring (contiguous); wrong fill order for intervals.",
         example="longest_palindrome_subseq('bbbab') -> 4  ('bbbb')."),
    dict(cat="dsa", title="Best Time to Buy and Sell Stock with Cooldown",
         answer="Maximize profit with unlimited transactions but a 1-day COOLDOWN after each sale (can't buy the day after selling). Track three rolling states: HOLD (own a stock), SOLD (just sold today), REST (idle, free to buy). Each day update them from the previous day's states.",
         tags=["stock-cooldown","dynamic-programming","state-machine","dp","dsa"],
         code='''# Max profit with unlimited transactions and a 1-day cooldown after selling.
def max_profit_cooldown(prices):
    if not prices:
        return 0
    hold = float('-inf')     # best profit while holding a stock
    sold = 0                 # best profit having just sold (cooldown next)
    rest = 0                 # best profit resting (free to buy)
    for price in prices:
        prev_sold = sold
        sold = hold + price              # sell today
        hold = max(hold, rest - price)   # keep holding, or buy today
        rest = max(rest, prev_sold)      # rest, or come off cooldown
    return max(sold, rest)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Buying the day right after selling (the cooldown forbids it); mixing up state transitions.",
         example="max_profit_cooldown([1,2,3,0,2]) -> 3  (buy1 sell3, cooldown, buy0 sell2)."),
    dict(cat="dsa", title="Minimum Right Shifts to Sort the Array",
         answer="Find the minimum number of right-shifts (rotate the whole array right by one) to sort a distinct array, or -1 if impossible. A right-shift-sortable array has at most ONE 'break' (an index where the value exceeds its circular successor); if there's exactly one at index i, the answer is n-1-i; zero breaks means already sorted; more than one means -1.",
         tags=["min-right-shifts","rotation","array","dsa"],
         code='''# Min number of right-shifts (rotate right) to sort the array, or -1.
def minimum_right_shifts(nums):
    n = len(nums)
    breaks = 0
    break_index = 0
    for i in range(n):
        if nums[i] > nums[(i + 1) % n]:   # a descent (circularly)
            breaks += 1
            break_index = i
    if breaks == 0:
        return 0                     # already sorted
    if breaks == 1:
        return n - 1 - break_index   # shifts to bring the tail to the front
    return -1                        # can't be sorted by right shifts''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not checking circularly (wrap-around break); wrong shift count formula.",
         example="minimum_right_shifts([3,4,5,1,2]) -> 2; minimum_right_shifts([2,1,4]) -> -1."),
    dict(cat="glossary", title="Bulkhead pattern",
         answer="A resilience pattern (named after a ship's watertight compartments) that ISOLATES resources into separate pools so a failure or overload in one part can't sink the whole system. Give each downstream dependency its own thread/connection pool and concurrency limit — a hung dependency exhausts only ITS bulkhead, leaving other requests unaffected. It prevents one slow service from consuming all threads and cascading into total failure.",
         tags=["bulkhead","resilience","isolation","microservices","fault-tolerance"],
         example="An API calls services A, B, C; with bulkheads a hung C exhausts only C's 10-thread pool, so calls to A and B keep working — without them, all threads block on C and the whole API goes down."),
    dict(cat="glossary", title="Geospatial index",
         answer="A database index optimized for LOCATION queries — 'points within a radius/box/polygon' or 'nearest N'. It maps 2-D coordinates to a locality-preserving 1-D key (geohash, S2/H3 cells) or uses a spatial tree (R-tree/quadtree), so nearby points cluster and radius/range queries scan few candidates. Used by PostGIS, MongoDB 2dsphere, Redis GEO, and Elasticsearch geo.",
         tags=["geospatial-index","geohash","r-tree","spatial","database"],
         example="A 'restaurants near me' query uses a geospatial index to fetch only candidates in nearby cells, then filters by exact distance — instead of scanning every restaurant."),
    dict(cat="glossary", title="Full-text index",
         answer="An index built for searching WORDS inside text (not exact-match on a whole value). It tokenizes documents, normalizes (lowercase, stemming, stop-word removal), and builds an INVERTED INDEX mapping each term to the documents/positions containing it — enabling fast keyword and phrase search with relevance ranking (BM25/TF-IDF). Used by Elasticsearch/Lucene, Postgres tsvector, MySQL FULLTEXT.",
         tags=["full-text-index","inverted-index","search","tokenization","database"],
         example="A product search for 'wireless earbuds' uses a full-text index's inverted lists to instantly find and rank documents with those (stemmed) terms, rather than a LIKE '%...%' scan of every row."),
    dict(cat="glossary", title="Thundering herd problem",
         answer="When MANY clients/threads all wait on the same event and are ALL released at once, they stampede a shared resource simultaneously and overwhelm it. Classic case: a popular cache key expires and thousands of requests hit the DB at the same instant to recompute it (cache stampede). Mitigations: request coalescing / single-flight (one recomputes, others wait for it), jittered/staggered expiry, and a lock so exactly one does the expensive work.",
         tags=["thundering-herd","cache-stampede","single-flight","concurrency","caching"],
         example="A homepage's cached feed expires and 10,000 concurrent requests all miss and query the DB at once; single-flight lets one rebuild the cache while the rest wait for its result."),
    dict(cat="glossary", title="Negative caching",
         answer="Caching the fact that something DOESN'T exist or that a request FAILED (a 404, an empty lookup, a DNS NXDOMAIN) for a short time, so repeated queries for the missing thing don't keep hitting the expensive backend. It protects against 'cache penetration' — where requests for non-existent keys always miss the cache and hammer the DB (sometimes maliciously). Use a SHORT TTL since the missing thing might soon exist.",
         tags=["negative-caching","cache-penetration","caching","ttl","performance"],
         example="Repeated lookups for a non-existent user id would miss the cache and hit the DB every time; caching the 'not found' for 30 seconds absorbs the load, and a short TTL lets a newly-created user appear quickly."),
    dict(cat="conceptual", title="Why use the bulkhead pattern to isolate resources instead of a shared pool?",
         answer="With a SHARED resource pool (one thread/connection pool serving all downstream calls), one slow or hung dependency creates hidden coupling: requests to it pile up holding their threads while waiting, and since the pool is shared those blocked resources are NO LONGER available for calls to the HEALTHY dependencies. Eventually every thread is stuck on the one sick service, so requests that don't even touch it start failing too — a localized problem CASCADES into a total outage. The BULKHEAD pattern gives each dependency its OWN isolated pool with its own concurrency limit, so a hung dependency can exhaust only ITS compartment (say 10 threads) while the other pools stay full and responsive — containing the blast radius to just the calls that need the failing service. It also gives natural backpressure/load-shedding: once a bulkhead is full, new calls to that dependency fail FAST (reject rather than queue forever), which beats blocking. Combined with timeouts and circuit breakers, bulkheads keep one bad dependency from taking down the whole service. The cost is resource fragmentation (you can't share spare capacity across compartments, so you size each pool and may need more total threads) — but that isolation is the point: trade a little efficiency for the guarantee that a single failure stays contained.",
         tags=["bulkhead","isolation","cascading-failure","resilience","why"],
         example="Without bulkheads a hung recommendation service consumes all 200 API worker threads and the whole site goes down; with a 20-thread bulkhead per dependency, recommendation calls exhaust only their 20 threads (and fail fast), so checkout and search keep serving."),
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

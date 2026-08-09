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
    dict(cat="dsa", title="Find the Highest Altitude",
         answer="A trip's net altitude gains per step are given; the starting altitude is 0. Return the HIGHEST altitude reached. Keep a running altitude (a prefix sum of the gains) and track its maximum.",
         tags=["highest-altitude","prefix-sum","array","dsa"],
         code='''# Highest altitude on a trip given net gain per step (prefix max of prefix sum).
def largest_altitude(gain):
    altitude = 0
    highest = 0
    for g in gain:
        altitude += g          # running altitude
        highest = max(highest, altitude)
    return highest''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting the starting altitude 0 is a candidate; summing without tracking the max.",
         example="largest_altitude([-5,1,5,0,-7]) -> 1."),
    dict(cat="dsa", title="Water Bottles",
         answer="You start with numBottles full bottles; you can EXCHANGE numExchange empty bottles for one full bottle. Count the total bottles you can drink. Greedily drink all, then keep exchanging empties for new fulls (whose empties add back) until you can't exchange anymore.",
         tags=["water-bottles","greedy","simulation","math","dsa"],
         code='''# Total bottles drunk: exchange num_exchange empties for a full one.
def num_water_bottles(num_bottles, num_exchange):
    total = num_bottles
    empty = num_bottles
    while empty >= num_exchange:
        new_full = empty // num_exchange           # fulls bought with empties
        total += new_full
        empty = empty % num_exchange + new_full    # leftover + newly emptied
    return total''',
         complexity="Time O(log num_bottles), space O(1).",
         pitfalls="Forgetting the leftover empties carry over; not adding the new empties after drinking.",
         example="num_water_bottles(9, 3) -> 13."),
    dict(cat="dsa", title="Find Target Indices After Sorting Array",
         answer="Sort the array ascending, then return all indices where the target appears (a 'target index' is a position holding the target in the sorted order). Sort and collect matching indices.",
         tags=["target-indices","sorting","array","dsa"],
         code='''# Indices where the target sits after sorting the array ascending.
def target_indices(nums, target):
    nums.sort()
    return [i for i, n in enumerate(nums) if n == target]''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Returning indices before sorting; using the original positions.",
         example="target_indices([1,2,5,2,3], 2) -> [1,2]."),
    dict(cat="dsa", title="Number of Arithmetic Triplets",
         answer="Count triplets (i<j<k) with nums[j]-nums[i] == diff and nums[k]-nums[j] == diff (the array is strictly increasing). Put the values in a set; for each value v, if v+diff and v+2*diff both exist, it anchors one triplet. O(n).",
         tags=["arithmetic-triplets","hash-set","array","dsa"],
         code='''# Count triplets with nums[j]-nums[i]==diff and nums[k]-nums[j]==diff.
def arithmetic_triplets(nums, diff):
    present = set(nums)
    # each value that has value+diff and value+2*diff present anchors a triplet
    return sum(1 for n in nums if (n + diff) in present and (n + 2 * diff) in present)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Triple-nested loops (O(n^3)); the set lookup relies on strictly-increasing distinct values.",
         example="arithmetic_triplets([0,1,4,6,7,10], 3) -> 2  (0,4,7? no; 1,4,7 and 4,7,10)."),
    dict(cat="dsa", title="Kth Distinct String in an Array",
         answer="A 'distinct' string appears exactly once in the array; return the kth distinct string in ORIGINAL order, or '' if fewer than k exist. Count frequencies, then walk in order counting down k at each once-only string.",
         tags=["kth-distinct-string","counting","hash-map","string","dsa"],
         code='''# The kth string that appears exactly once (in original order), or ''.
from collections import Counter
def kth_distinct(arr, k):
    counts = Counter(arr)
    for s in arr:
        if counts[s] == 1:
            k -= 1
            if k == 0:
                return s
    return ""''',
         complexity="Time O(n), space O(n).",
         pitfalls="Iterating the counter (loses order); returning None instead of '' when k exceeds the count.",
         example="kth_distinct(['d','b','c','b','c','a'], 2) -> 'a'."),
    dict(cat="dsa", title="Maximum Product Difference Between Two Pairs",
         answer="Choose two pairs to maximize (a*b) - (c*d). The best product uses the two LARGEST values; the smallest product uses the two SMALLEST. Sort and compute largest*second-largest minus smallest*second-smallest.",
         tags=["max-product-difference","sorting","greedy","array","dsa"],
         code='''# (largest * 2nd-largest) - (smallest * 2nd-smallest).
def max_product_difference(nums):
    nums.sort()
    return nums[-1] * nums[-2] - nums[0] * nums[1]''',
         complexity="Time O(n log n) (O(n) with a scan for extremes), space O(1).",
         pitfalls="Assuming positive numbers only (this pairing still works for the stated problem); wrong index pairing.",
         example="max_product_difference([5,6,2,7,4]) -> 34  (7*6 - 2*4)."),
    dict(cat="dsa", title="Sort Array by Increasing Frequency",
         answer="Sort by ASCENDING frequency; when two values have the same frequency, order them by DECREASING value. Count frequencies, then sort with a composite key (frequency ascending, value descending).",
         tags=["frequency-sort","counting","sorting","array","dsa"],
         code='''# Sort by ascending frequency; ties broken by decreasing value.
from collections import Counter
def frequency_sort(nums):
    counts = Counter(nums)
    # frequency ascending, then value descending within the same frequency
    return sorted(nums, key=lambda x: (counts[x], -x))''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Wrong tie-break direction (value must be descending); sorting by value alone.",
         example="frequency_sort([1,1,2,2,2,3]) -> [3,1,1,2,2,2]."),
    dict(cat="dsa", title="Count Elements With Strictly Smaller and Greater Elements",
         answer="Count elements that have BOTH a strictly smaller AND a strictly greater element in the array — i.e. every value that isn't the global minimum or maximum. Find the min and max, then count values strictly between them.",
         tags=["count-elements-between","array","min-max","dsa"],
         code='''# Count elements with both a strictly smaller and a strictly greater element.
def count_elements(nums):
    lo, hi = min(nums), max(nums)
    return sum(1 for n in nums if lo < n < hi)   # exclude the extremes''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using <= (would wrongly include ties with min/max); edge case where all values are equal (answer 0).",
         example="count_elements([11,7,2,15]) -> 2  (11 and 7)."),
    dict(cat="glossary", title="Observability: the three pillars",
         answer="The three data types used to understand a system from the outside. LOGS: discrete, timestamped event records (detailed 'what happened') — best for debugging specifics. METRICS: numeric time-series aggregates (rate, errors, latency, CPU) — cheap, best for dashboards/alerts and trends. TRACES: the end-to-end path of one request across services (spans) — best for latency/dependency analysis. Together: detect with metrics, diagnose with traces, drill in with logs.",
         tags=["observability","logs","metrics","traces","monitoring"],
         example="A latency alert (metric) fires; you open a trace to see the payment call took 800ms, then read that service's logs to find the slow query — metrics -> traces -> logs."),
    dict(cat="glossary", title="RED vs USE metrics",
         answer="Two complementary monitoring methodologies. RED (for request-driven SERVICES): Rate (requests/sec), Errors (failed requests), Duration (latency) — the user-facing health of a service. USE (for RESOURCES): Utilization (% busy), Saturation (queue/wait depth), Errors — the health of a resource (CPU, disk, queue). RED tells you IF users are hurting; USE helps find WHICH resource is the bottleneck.",
         tags=["red-metrics","use-metrics","monitoring","sre","observability"],
         example="RED shows the API's error rate spiking and latency climbing (users hurting); USE reveals the database CPU is saturated with a full run queue — the resource bottleneck behind it."),
    dict(cat="glossary", title="Metric cardinality",
         answer="The number of unique time-series a metric produces, driven by the combinations of its LABEL/tag values — each distinct combination (endpoint × status × region × ...) is a separate stored series. HIGH cardinality (especially unbounded labels like user_id, request_id, or full URLs) explodes storage/query cost and can crash a metrics system. Keep labels low-cardinality and bounded; put high-cardinality detail in logs/traces instead.",
         tags=["cardinality","metrics","labels","prometheus","observability"],
         example="Adding a 'user_id' label to a request-count metric creates one series per user (millions), blowing up the metrics DB; keep labels low-cardinality (endpoint, status) and log the user_id instead."),
    dict(cat="glossary", title="Structured logging & log levels",
         answer="STRUCTURED logging emits logs as machine-parseable key/value records (usually JSON) so they can be filtered/searched/aggregated by field (user_id, request_id, latency) — essential at scale. LOG LEVELS (DEBUG < INFO < WARN < ERROR < FATAL) categorize severity to filter noise and set alert thresholds; prod usually runs at INFO/WARN with DEBUG enabled temporarily. Include a correlation/trace id to tie logs to a request.",
         tags=["structured-logging","log-levels","json-logs","observability"],
         example="Logging {level:'error', trace_id:'abc', user:'123', msg:'payment failed'} as JSON lets you query all errors for trace abc across services — impossible with a plain-text line."),
    dict(cat="glossary", title="Sampling in observability",
         answer="Keeping only a SUBSET of telemetry (traces/verbose logs) to control cost/volume, since storing 100% at scale is prohibitive. HEAD sampling decides at the start (e.g. keep 1%) — cheap but may drop the rare slow/errored trace. TAIL sampling buffers a trace and keeps it based on outcome (always keep errors and slow requests) — better signal, more memory. Metrics are usually NOT sampled (they're already aggregates).",
         tags=["sampling","tracing","head-sampling","tail-sampling","observability"],
         example="A service keeps 1% of normal traces (head) but 100% of any trace with an error or >1s latency (tail), capturing the interesting ones without storing billions of boring ones."),
    dict(cat="conceptual", title="Why sample traces/logs instead of collecting everything?",
         answer="At scale, telemetry volume rivals the application traffic itself: a service at 100k rps, each request emitting a multi-span trace and several log lines, produces terabytes/hour — the COST (storage, ingestion, indexing) and operational load of keeping it all would dwarf running the service, and emitting/exporting telemetry isn't free (it can slow the app). Most of that data is REDUNDANT too: the 99.9% of fast successes look alike, so keeping every one buys little. Sampling keeps a representative or INTERESTING subset. HEAD sampling (decide up front, keep 1%) is cheap and gives valid rates/trends but blindly drops the rare error/slow trace you need in an incident. TAIL sampling defers the keep/drop decision until the request finishes, so you ALWAYS retain errors and high-latency traces (the signal) while sampling the boring majority — at the cost of buffering traces in memory. The nuance: METRICS shouldn't be sampled (they're aggregates; sampling would distort counts), so keep 100% of metrics for exact alerting and sample the expensive per-request detail (traces, verbose logs), often combining always-keep-errors with a low baseline rate. It's a cost/signal trade-off: you can't afford everything and don't need everything — you need the anomalies plus enough baseline to stay statistically sound.",
         tags=["sampling","observability","tracing","cost","why"],
         example="Keeping 100% of traces at 100k rps is unaffordable and mostly duplicate 'fast success' traces; sampling 1% of successes but 100% of errors/slow requests captures every problem for a fraction of the storage, while metrics stay unsampled so error-rate alerts remain exact."),
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

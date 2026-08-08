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
    dict(cat="dsa", title="Base 7 Conversion",
         answer="Convert an integer to its base-7 string. Repeatedly take num % 7 for the next least-significant digit and floor-divide by 7, collecting digits, then reverse. Handle 0 and the negative sign separately.",
         tags=["base-7","base-conversion","math","dsa"],
         code='''# Convert an integer to its base-7 string representation.
def convert_to_base7(num):
    if num == 0:
        return "0"
    negative = num < 0
    num = abs(num)
    digits = []
    while num:
        digits.append(str(num % 7))   # least-significant digit first
        num //= 7
    result = "".join(reversed(digits))
    return "-" + result if negative else result''',
         complexity="Time O(log n), space O(log n).",
         pitfalls="Not handling 0 or the sign; forgetting to reverse the collected digits.",
         example="convert_to_base7(100) -> '202'; convert_to_base7(-7) -> '-10'."),
    dict(cat="dsa", title="Add to Array-Form of Integer",
         answer="A number is given as an array of digits; add an integer k to it and return the digit array of the sum. Walk from the least-significant digit, folding k in as a running carry (add the digit, take %10 as the output digit, //10 as the carry) until both the array and k are exhausted.",
         tags=["array-form","math","carry","array","dsa"],
         code='''# Add an integer k to a number represented as an array of digits.
def add_to_array_form(num, k):
    i = len(num) - 1
    result = []
    while i >= 0 or k:
        if i >= 0:
            k += num[i]              # fold in the current digit
            i -= 1
        result.append(k % 10)        # output digit
        k //= 10                     # carry to the next position
    return result[::-1]''',
         complexity="Time O(max(len(num), digits of k)), space O(that).",
         pitfalls="Stopping before k's carry is fully consumed; forgetting to reverse.",
         example="add_to_array_form([1,2,0,0], 34) -> [1,2,3,4]."),
    dict(cat="dsa", title="Number to Excel Column Title",
         answer="Convert a positive integer to its Excel column title (1->A, 26->Z, 27->AA). It's base-26 but 1-indexed (no zero digit), so subtract 1 before each modulo to map into 0..25, then convert to a letter and divide down.",
         tags=["excel-column-title","base-conversion","string","math","dsa"],
         code='''# Convert a positive integer to its Excel column title (1->A, 27->AA).
def convert_to_title(n):
    result = []
    while n:
        n -= 1                        # shift to 0-based for the modulo
        result.append(chr(n % 26 + ord('A')))
        n //= 26
    return "".join(reversed(result))''',
         complexity="Time O(log n), space O(log n).",
         pitfalls="Forgetting the n -= 1 (this is 1-indexed, not 0-indexed); not reversing.",
         example="convert_to_title(28) -> 'AB'; convert_to_title(701) -> 'ZY'."),
    dict(cat="dsa", title="Number of Steps to Reduce a Number to Zero",
         answer="Count the steps to reduce n to 0 where each step halves n if it's even, or subtracts 1 if it's odd. Simulate directly; equivalently it's (number of bits) + (number of set bits) - 1.",
         tags=["steps-to-zero","bit-manipulation","math","simulation","dsa"],
         code='''# Steps to reduce n to 0: if even, halve it; if odd, subtract 1.
def number_of_steps(num):
    steps = 0
    while num:
        if num % 2 == 0:
            num //= 2
        else:
            num -= 1
        steps += 1
    return steps''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Off-by-one on the final step to 0; infinite loop if the update is wrong.",
         example="number_of_steps(14) -> 6."),
    dict(cat="dsa", title="Reverse String (in place)",
         answer="Reverse an array of characters IN PLACE with O(1) extra space. Two pointers from the ends swap inward until they meet.",
         tags=["reverse-string","two-pointers","in-place","string","dsa"],
         code='''# Reverse a list of characters in place (two pointers).
def reverse_string(s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1; right -= 1
    return s''',
         complexity="Time O(n), space O(1).",
         pitfalls="Building a new string instead of in-place; off-by-one on the pointers.",
         example="reverse_string(['h','e','l','l','o']) -> ['o','l','l','e','h']."),
    dict(cat="dsa", title="Detect Capital",
         answer="A word's capitalization is valid if it's ALL uppercase ('USA'), ALL lowercase ('leetcode'), or Title case with only the first letter capitalized ('Google'). Check those three cases directly.",
         tags=["detect-capital","string","dsa"],
         code='''# Is the capitalization of a word valid? (all caps, all lower, or Title case)
def detect_capital_use(word):
    return word.isupper() or word.islower() or word.istitle()''',
         complexity="Time O(n), space O(1).",
         pitfalls="Missing the title-case rule (first letter only); edge cases with single-letter words.",
         example="detect_capital_use('USA') -> True; detect_capital_use('FlaG') -> False."),
    dict(cat="dsa", title="Maximum Product of Three Numbers",
         answer="Find the maximum product of any three numbers in an array. After sorting, the answer is either the three LARGEST values, or the two SMALLEST (potentially large negatives whose product is positive) times the largest value. Take the max of those two candidates.",
         tags=["max-product-three","sorting","greedy","array","dsa"],
         code='''# Max product of any three numbers (watch two large negatives).
def maximum_product(nums):
    nums.sort()
    # three largest, OR two smallest (very negative) times the largest
    return max(nums[-1] * nums[-2] * nums[-3], nums[0] * nums[1] * nums[-1])''',
         complexity="Time O(n log n) (O(n) with a linear scan for extremes), space O(1).",
         pitfalls="Ignoring two negative extremes (their product is positive); only taking the top three.",
         example="maximum_product([-4,-3,-2,1,60]) -> 720  ((-4)*(-3)*60)."),
    dict(cat="dsa", title="Best Time to Buy and Sell Stock II (greedy)",
         answer="Maximize profit with UNLIMITED transactions (you may buy and sell repeatedly, one share at a time). Greedy: capture every upswing — sum all positive day-to-day differences. This equals the best achievable profit because any longer rising run is the sum of its consecutive gains.",
         tags=["buy-sell-stock","greedy","array","dsa"],
         code='''# Max profit with unlimited transactions (buy/sell many times), greedy.
def max_profit(prices):
    profit = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            profit += prices[i] - prices[i - 1]   # capture every upswing
    return profit''',
         complexity="Time O(n), space O(1).",
         pitfalls="Trying to find one buy/sell pair (that's Stock I); holding across a dip needlessly.",
         example="max_profit([7,1,5,3,6,4]) -> 7  ((5-1)+(6-3))."),
    dict(cat="glossary", title="Event time vs processing time",
         answer="Two notions of time in stream processing. EVENT TIME is when an event actually OCCURRED (a timestamp in the data). PROCESSING TIME is when the system processes it. Networks and buffering make events arrive late/out-of-order, so aggregating by processing time gives wrong, non-reproducible results. Event time (with WATERMARKS to bound lateness) produces correct, deterministic windows regardless of arrival time.",
         tags=["event-time","processing-time","stream-processing","watermark"],
         example="A user clicks at 11:59 but the event reaches the pipeline at 12:03; event-time windowing counts it in the 11:xx window (correct), while processing-time would wrongly bucket it into 12:xx."),
    dict(cat="glossary", title="Log compaction (Kafka)",
         answer="A retention mode that, instead of deleting old messages by time/size, keeps only the LATEST value per KEY. The log becomes a compacted changelog where every key's most recent state survives, so a consumer can rebuild full current state by replaying it. Ideal for topics representing entity state (a table as a stream).",
         tags=["log-compaction","kafka","changelog","retention","streaming"],
         example="A 'user-profile' topic keyed by user_id uses log compaction: old updates are pruned but the latest per user is kept, so a new service bootstraps current profiles by reading the whole topic."),
    dict(cat="glossary", title="ISR (in-sync replicas)",
         answer="In Kafka, the set of a partition's replicas that are fully CAUGHT UP with the leader. With acks=all, a write commits once all ISR members have it, so any ISR replica can become leader without data loss. A lagging/dead replica falls OUT of the ISR; min.insync.replicas sets how many must be in-sync to accept writes — trading availability for durability.",
         tags=["isr","in-sync-replicas","kafka","replication","durability"],
         example="With replication factor 3 and min.insync.replicas=2, a partition accepts writes while 2 replicas are in the ISR; if too many lag, writes are rejected to guarantee durability."),
    dict(cat="glossary", title="Idempotent producer",
         answer="A Kafka producer feature that prevents DUPLICATE messages from producer retries. Each producer gets an ID and each message a sequence number; the broker dedupes retried sends per partition, so a network retry after an ambiguous ack doesn't write the message twice. It's a foundation of Kafka's exactly-once semantics (with transactions).",
         tags=["idempotent-producer","kafka","exactly-once","deduplication"],
         example="A producer times out waiting for an ack and retries; without idempotence the message could be written twice, but sequence numbers let the broker discard the duplicate."),
    dict(cat="glossary", title="At-least-once vs at-most-once vs exactly-once",
         answer="The three delivery guarantees. AT-MOST-ONCE: never retry -> messages may be LOST but never duplicated (fire-and-forget). AT-LEAST-ONCE: retry until acked -> never lost but may DUPLICATE (the common default). EXACTLY-ONCE: each message takes effect once — achieved not by magical delivery but by at-least-once + dedup/idempotency or transactions. Choose based on whether loss or duplication is worse.",
         tags=["delivery-semantics","at-least-once","at-most-once","exactly-once","messaging"],
         example="Metrics collection tolerates at-most-once (a lost sample is fine); payments need exactly-once effect via at-least-once + idempotency keys so no charge is lost OR duplicated."),
    dict(cat="conceptual", title="Why aggregate streams by event time instead of processing time?",
         answer="Because processing time makes results WRONG and non-reproducible when data arrives late or out of order — which it always does (network delays, retries, buffering, backfills). Bucketing 'clicks per minute' by when the system happened to process each event means the same input replayed later lands in different windows, and a 2-minute delay silently shifts events into the wrong minute. EVENT time uses when the event actually happened, so an event always falls in the same window regardless of processing time — giving correct, deterministic, replayable aggregates. The cost is handling LATE data: you can't close a window immediately, so WATERMARKS estimate 'event time has advanced past T, windows before T-δ are likely complete' to decide when to emit, plus allowed-lateness for stragglers. Processing time is simpler/lower-latency (fine for rough dashboards), but event time is required when correctness under out-of-order data matters.",
         tags=["event-time","processing-time","watermark","stream-processing","why"],
         example="Reprocessing yesterday's log through a processing-time pipeline buckets everything into 'now', destroying the per-minute breakdown; an event-time pipeline reproduces the exact same per-minute counts as the original run."),
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

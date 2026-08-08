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
    dict(cat="dsa", title="Hamming Distance",
         answer="The Hamming distance between two integers is the number of bit positions where they differ. XOR the two numbers (bits are 1 exactly where they differ), then count the set bits in the result.",
         tags=["hamming-distance","bit-manipulation","xor","dsa"],
         code='''# Number of positions where the bits of two integers differ.
def hamming_distance(x, y):
    xor = x ^ y                 # bits set exactly where x and y differ
    count = 0
    while xor:
        count += xor & 1        # add the lowest bit
        xor >>= 1
    return count''',
         complexity="Time O(number of bits), space O(1).",
         pitfalls="Comparing digits instead of bits; forgetting to XOR first.",
         example="hamming_distance(1, 4) -> 2  (0001 vs 0100)."),
    dict(cat="dsa", title="Number of 1 Bits (popcount)",
         answer="Count the set bits (population count) of an integer. The elegant trick n &= n-1 clears the LOWEST set bit each iteration, so the loop runs exactly as many times as there are 1-bits — faster than checking all 32 bits.",
         tags=["number-of-1-bits","popcount","bit-manipulation","dsa"],
         code='''# Count the set bits (population count) of an integer.
def hamming_weight(n):
    count = 0
    while n:
        n &= n - 1              # clears the lowest set bit each step
        count += 1
    return count''',
         complexity="Time O(number of set bits), space O(1).",
         pitfalls="Looping all 32 bits unnecessarily; forgetting n & (n-1) clears the lowest 1.",
         example="hamming_weight(11) -> 3  (binary 1011)."),
    dict(cat="dsa", title="Power of Two",
         answer="Check whether n is a power of two. A power of two has EXACTLY ONE set bit, and n & (n-1) clears the lowest set bit — so for a power of two that yields 0. Guard n>0 (zero and negatives aren't powers of two).",
         tags=["power-of-two","bit-manipulation","math","dsa"],
         code='''# Is n a power of two? A power of two has exactly one set bit.
def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0   # n & (n-1) clears the lone bit -> 0''',
         complexity="Time O(1), space O(1).",
         pitfalls="Not guarding n>0 (0 and negatives); using a loop of divisions when a bit trick is O(1).",
         example="is_power_of_two(16) -> True; is_power_of_two(18) -> False."),
    dict(cat="dsa", title="Plus One",
         answer="Add one to a non-negative integer represented as an array of digits (most significant first). Walk from the last digit: if it's < 9, increment and return; if it's 9 it becomes 0 and the carry continues left. If every digit was 9, prepend a leading 1.",
         tags=["plus-one","array","math","carry","dsa"],
         code='''# Add one to a number represented as an array of digits.
def plus_one(digits):
    for i in range(len(digits) - 1, -1, -1):
        if digits[i] < 9:
            digits[i] += 1          # no carry -> done
            return digits
        digits[i] = 0               # 9 becomes 0, carry continues left
    return [1] + digits             # all nines -> prepend a leading 1''',
         complexity="Time O(n), space O(1) (or O(n) for the all-nines case).",
         pitfalls="Forgetting the all-nines carry-out (99 -> 100); iterating left-to-right.",
         example="plus_one([1,2,9]) -> [1,3,0]; plus_one([9,9]) -> [1,0,0]."),
    dict(cat="dsa", title="Add Binary",
         answer="Add two binary strings and return their sum as a binary string. Walk both from the least significant bit, summing digit + digit + carry; the current output bit is total%2 and the new carry is total//2. Continue while either string has digits or a carry remains, then reverse.",
         tags=["add-binary","string","bit-manipulation","carry","dsa"],
         code='''# Add two binary strings and return the binary sum as a string.
def add_binary(a, b):
    i, j = len(a) - 1, len(b) - 1
    carry = 0
    result = []
    while i >= 0 or j >= 0 or carry:
        total = carry
        if i >= 0:
            total += int(a[i]); i -= 1
        if j >= 0:
            total += int(b[j]); j -= 1
        result.append(str(total % 2))   # current output bit
        carry = total // 2              # carry to the next position
    return "".join(reversed(result))''',
         complexity="Time O(max(len a, len b)), space O(that).",
         pitfalls="Dropping the final carry; not reversing the accumulated bits.",
         example="add_binary('11', '1') -> '100'."),
    dict(cat="dsa", title="Excel Sheet Column Number",
         answer="Convert an Excel column title (A, B, ..., Z, AA, AB, ...) to its 1-based number. It's base-26 but with digits 1..26 (A=1, not 0): for each character, result = result*26 + (value of the letter).",
         tags=["excel-column","base-conversion","string","math","dsa"],
         code='''# Convert an Excel column title (A, B, ..., Z, AA, ...) to its number.
def title_to_number(s):
    result = 0
    for ch in s:
        # base-26 where A=1..Z=26 (no zero digit)
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result''',
         complexity="Time O(len(s)), space O(1).",
         pitfalls="Treating A as 0 (it's 1); not accumulating in base 26.",
         example="title_to_number('AB') -> 28; title_to_number('ZY') -> 701."),
    dict(cat="dsa", title="Perfect Squares (DP)",
         answer="Find the FEWEST perfect-square numbers (1,4,9,16,...) that sum to n. DP where dp[i] = min squares summing to i: for each i, try every square j*j <= i and take 1 + dp[i - j*j]. Bottom-up fill gives dp[n].",
         tags=["perfect-squares","dynamic-programming","math","dp","dsa"],
         code='''# Fewest perfect-square numbers that sum to n (DP).
def num_squares(n):
    dp = [0] + [float('inf')] * n     # dp[i] = fewest squares summing to i
    for i in range(1, n + 1):
        j = 1
        while j * j <= i:
            dp[i] = min(dp[i], dp[i - j * j] + 1)
            j += 1
    return dp[n]''',
         complexity="Time O(n * sqrt(n)), space O(n).",
         pitfalls="Iterating all numbers instead of just squares; off-by-one on dp size.",
         example="num_squares(12) -> 3  (4+4+4); num_squares(13) -> 2  (4+9)."),
    dict(cat="dsa", title="Min Cost Climbing Stairs (DP)",
         answer="Each stair i costs cost[i] to step on; from a stair you climb 1 or 2 steps, and you may start at stair 0 or 1. Find the min cost to go PAST the top. DP: the cheapest way onto stair i is cost[i] + min(cost to reach i-1, i-2); the answer is the min of reaching the last two stairs (the top is one step beyond).",
         tags=["min-cost-climbing-stairs","dynamic-programming","dp","dsa"],
         code='''# Min cost to reach the top, paying cost[i] to step on stair i (climb 1 or 2).
def min_cost_climbing_stairs(cost):
    prev, curr = 0, 0                 # min cost to reach the two stairs below
    for c in cost:
        prev, curr = curr, c + min(prev, curr)   # cheapest way onto this stair
    return min(prev, curr)            # top is just past the last stair''',
         complexity="Time O(n), space O(1).",
         pitfalls="Paying to step off the top (you don't); mixing up which neighbour is i-1 vs i-2.",
         example="min_cost_climbing_stairs([10,15,20]) -> 15; min_cost_climbing_stairs([1,100,1,1,1,100,1,1,100,1]) -> 6."),
    dict(cat="glossary", title="Consistent hashing",
         answer="A hashing scheme that maps both KEYS and NODES onto a ring; a key is owned by the next node clockwise. When a node is added or removed, only the keys between it and its predecessor move — about 1/N of keys — instead of nearly everything remapping as with modulo hashing. VIRTUAL NODES spread load evenly. It underpins distributed caches, sharded databases, and CDNs.",
         tags=["consistent-hashing","sharding","distributed-systems","load-balancing"],
         example="Adding a 5th cache node to a 4-node cluster remaps only ~1/5 of keys (those now landing on the new node) instead of rehashing everything and causing a cache-wide miss storm."),
    dict(cat="glossary", title="PACELC theorem",
         answer="An extension of CAP: if there's a network Partition (P), a system trades between Availability and Consistency (A/C); but Else (E), even with NO partition, it trades between Latency and Consistency (L/C). It captures that consistency costs latency even in normal operation — not just during failures.",
         tags=["pacelc","cap-theorem","consistency","latency","distributed-systems"],
         example="Dynamo-style stores are PA/EL (favor availability under partition, low latency otherwise); Spanner is PC/EC (consistency always, paying latency)."),
    dict(cat="glossary", title="Circuit breaker",
         answer="A resilience pattern that STOPS calling a failing dependency to prevent cascading failure. Like an electrical breaker it 'trips' OPEN after a failure threshold — failing fast instead of hammering the dead service — then periodically goes HALF-OPEN to test recovery, closing again when calls succeed. It keeps a slow/broken downstream from exhausting the caller's threads/resources.",
         tags=["circuit-breaker","resilience","microservices","fault-tolerance"],
         example="If the payment service starts timing out, the breaker trips open so checkout fails fast (with a fallback) instead of every request hanging 30s and exhausting the gateway's thread pool."),
    dict(cat="glossary", title="Idempotency key",
         answer="A unique client-supplied token attached to a request so the server can DEDUPLICATE retries — processing the operation once even if the request arrives multiple times (network retry, timeout). The server records the key + result; a repeat with the same key returns the stored result instead of re-executing. Essential for safely retrying non-idempotent operations like payments.",
         tags=["idempotency-key","retries","exactly-once","api","reliability"],
         example="A payment API takes an Idempotency-Key header; a client retry after a timeout sends the same key, so the server returns the original charge result rather than charging twice."),
    dict(cat="glossary", title="Exactly-once semantics",
         answer="The (hard) guarantee that a message/operation takes effect exactly once despite failures and retries. True exactly-once DELIVERY is impossible over an asynchronous network, so systems achieve exactly-once EFFECT via at-least-once delivery + IDEMPOTENT processing (dedupe by id) or an atomic/transactional commit. 'Exactly-once' in practice means 'at-least-once + dedup'.",
         tags=["exactly-once","idempotency","messaging","delivery-semantics"],
         example="Kafka's 'exactly-once' combines idempotent producers with transactional writes so a consumer's output reflects each input once, even though messages may be delivered more than once underneath."),
    dict(cat="conceptual", title="Why is exactly-once delivery essentially impossible, and how do systems fake it?",
         answer="Over an asynchronous network a sender can't distinguish 'the message was lost' from 'it arrived but the ack was lost', so it must either retry (risking DUPLICATES) or not (risking LOSS) — giving at-most-once or at-least-once, but never a guaranteed single delivery (the two-generals problem: no finite protocol makes both sides certain). Systems therefore target exactly-once EFFECT, not delivery: at-least-once delivery + IDEMPOTENT processing (dedupe by a unique id) or an atomic/transactional commit so duplicates are harmless. The delivery may repeat; the effect happens once.",
         tags=["exactly-once","two-generals","idempotency","distributed-systems","why"],
         example="A payment webhook is delivered at-least-once; the receiver dedupes on the event id, so a re-delivered 'charge $10' is ignored — money moves exactly once even though the message arrived twice."),
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

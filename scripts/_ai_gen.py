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
    dict(cat="dsa", title="Minimum Number of Moves to Seat Everyone",
         answer="Given seat positions and student positions, each move shifts a student by 1; minimize total moves to seat everyone (one per seat). Greedy: SORT both, pair the i-th student with the i-th seat, and sum the absolute differences — matching sorted-to-sorted is optimal for L1 cost.",
         tags=["min-moves-seat","greedy","sorting","array","dsa"],
         code='''# Min total unit moves to seat each student (sorted pairing).
def min_moves_seat(seats, students):
    seats.sort()
    students.sort()
    total = 0
    for s, p in zip(seats, students):
        total += abs(s - p)            # cost to move this student to its seat
    return total''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Pairing without sorting (suboptimal); using squared distance instead of absolute.",
         example="min_moves_seat([3,1,5], [2,7,4]) -> 4."),
    dict(cat="dsa", title="Maximum Number of Coins You Can Get",
         answer="3n piles; repeatedly you pick the top 3 remaining piles, Alice takes the max, YOU take the second, Bob takes the min — maximize your total. Greedy: sort ascending; Bob takes the n smallest, then you take every OTHER pile from the largest side, i.e. the 2nd, 4th, ... from the top.",
         tags=["max-coins","greedy","sorting","array","dsa"],
         code='''# Your total coins when you always take the 2nd-largest of each chosen triple.
def max_coins(piles):
    piles.sort()
    n = len(piles) // 3
    total = 0
    # skip the n smallest (Bob's); take every second pile going down from the top
    i = len(piles) - 2
    for _ in range(n):
        total += piles[i]              # your pile (2nd largest of the triple)
        i -= 2                         # skip Alice's pile, move to the next triple
    return total''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Taking the largest (that's Alice's); miscounting the stride of 2 or the n Bob piles.",
         example="max_coins([2,4,1,2,7,8]) -> 9  (you take 7 and 2)."),
    dict(cat="dsa", title="Assign Cookies",
         answer="Each child has a greed factor g; each cookie a size s; a child is content if s >= g. Maximize content children. Greedy two-pointer: sort both, give the smallest sufficient cookie to the least greedy child, advancing pointers.",
         tags=["assign-cookies","greedy","two-pointers","sorting","dsa"],
         code='''# Max children satisfied (cookie size >= greed) via greedy two pointers.
def find_content_children(g, s):
    g.sort()
    s.sort()
    child = cookie = 0
    while child < len(g) and cookie < len(s):
        if s[cookie] >= g[child]:      # this cookie satisfies this child
            child += 1
        cookie += 1                    # move to the next cookie regardless
    return child''',
         complexity="Time O(n log n + m log m), space O(1).",
         pitfalls="Not advancing the cookie pointer when it's too small; sorting only one array.",
         example="find_content_children([1,2,3], [1,1]) -> 1; find_content_children([1,2], [1,2,3]) -> 2."),
    dict(cat="dsa", title="Boats to Save People",
         answer="Each boat holds at most 2 people and a weight limit; minimize boats. Greedy two-pointer: sort; pair the heaviest with the lightest if they fit together, else the heaviest goes alone — always advance the heavy pointer.",
         tags=["boats-save-people","greedy","two-pointers","sorting","dsa"],
         code='''# Min boats (cap 2 people, weight limit) via greedy two pointers.
def num_rescue_boats(people, limit):
    people.sort()
    light, heavy = 0, len(people) - 1
    boats = 0
    while light <= heavy:
        if people[light] + people[heavy] <= limit:
            light += 1                 # lightest rides with the heaviest
        heavy -= 1                     # heaviest always boards
        boats += 1
    return boats''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Pairing two heavy people (a boat holds at most 2 but must respect the limit); forgetting the heavy pointer always moves.",
         example="num_rescue_boats([3,2,2,1], 3) -> 3."),
    dict(cat="dsa", title="Largest Odd Number in String",
         answer="Given a numeric string, return the largest-value ODD substring that is a PREFIX ending at the last odd digit (any longer prefix including it is larger). Scan from the right for the first odd digit; the answer is the prefix up to and including it, else empty.",
         tags=["largest-odd-number","greedy","string","digits","dsa"],
         code='''# Largest odd-valued prefix substring of a numeric string.
def largest_odd_number(num):
    # find the rightmost odd digit; the prefix through it is the largest odd number
    for i in range(len(num) - 1, -1, -1):
        if int(num[i]) % 2 == 1:
            return num[:i + 1]
    return ''''',
         complexity="Time O(n), space O(1).",
         pitfalls="Returning just the digit instead of the whole prefix; scanning left-to-right (misses the longest prefix).",
         example="largest_odd_number('35427') -> '35427'; largest_odd_number('4206') -> ''."),
    dict(cat="dsa", title="Check if Two Strings Are Almost Equivalent",
         answer="Two strings are almost equivalent if the frequency of EVERY letter differs by at most 3 between them. Count letters in both; check |count1[c] - count2[c]| <= 3 for all 26 letters.",
         tags=["almost-equivalent","counting","hash-map","string","dsa"],
         code='''# True if every letter's frequency differs by at most 3 between the strings.
def check_almost_equivalent(word1, word2):
    from collections import Counter
    c1, c2 = Counter(word1), Counter(word2)
    for ch in set(word1) | set(word2):
        if abs(c1[ch] - c2[ch]) > 3:   # frequency gap too large
            return False
    return True''',
         complexity="Time O(n + m), space O(1) (bounded alphabet).",
         pitfalls="Only checking letters in one string (must union both); using > 3 vs >= 3 (threshold is inclusive at 3).",
         example="check_almost_equivalent('aaaa', 'bccb') -> False; check_almost_equivalent('abcdeef', 'abaaacc') -> True."),
    dict(cat="dsa", title="Count the Number of Consistent Strings",
         answer="Given an allowed set of characters and a list of words, count words whose characters are ALL in the allowed set. Put allowed chars in a set; a word is consistent if set(word) is a subset.",
         tags=["consistent-strings","hash-set","subset","string","dsa"],
         code='''# Count words made only of allowed characters.
def count_consistent(allowed, words):
    allowed_set = set(allowed)
    count = 0
    for word in words:
        if set(word) <= allowed_set:   # all characters are allowed
            count += 1
    return count''',
         complexity="Time O(total characters), space O(alphabet).",
         pitfalls="Checking membership char-by-char in a list (O(k) each) instead of a set; misusing subset direction.",
         example="count_consistent('ab', ['ad','bd','aaab','baa']) -> 2."),
    dict(cat="dsa", title="Sort Array By Parity",
         answer="Reorder so all even integers come before all odd ones (any order within). In-place two-pointer: swap an odd on the left with an even on the right, converging the pointers.",
         tags=["sort-by-parity","two-pointers","in-place","array","dsa"],
         code='''# Move all evens before all odds, in place, via two pointers.
def sort_array_by_parity(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        if nums[left] % 2 == 0:
            left += 1                  # already an even in place
        elif nums[right] % 2 == 1:
            right -= 1                 # already an odd in place
        else:
            nums[left], nums[right] = nums[right], nums[left]  # swap odd/even
    return nums''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using extra arrays when in-place is asked; advancing both pointers on a swap without re-checking.",
         example="sort_array_by_parity([3,1,2,4]) -> evens first, e.g. [4,2,1,3]."),
    dict(cat="dsa", title="Unique Number of Occurrences",
         answer="Return True if the number of occurrences of each value is unique. Count values, then check the multiset of counts has no duplicates (len(set(counts)) == len(counts)).",
         tags=["unique-occurrences","counting","hash-set","array","dsa"],
         code='''# True if every value's occurrence count is distinct.
def unique_occurrences(arr):
    from collections import Counter
    counts = list(Counter(arr).values())
    return len(counts) == len(set(counts))''',
         complexity="Time O(n), space O(n).",
         pitfalls="Comparing values instead of their counts; forgetting a set collapses duplicate counts.",
         example="unique_occurrences([1,2,2,1,1,3]) -> True; unique_occurrences([1,2]) -> False."),
    dict(cat="dsa", title="Sort Characters By Frequency",
         answer="Rearrange a string so characters appear in DESCENDING frequency order. Count characters, sort by count desc, then repeat each char count times.",
         tags=["sort-by-frequency","counting","sorting","string","dsa"],
         code='''# Rebuild the string with characters ordered by descending frequency.
def frequency_sort(s):
    from collections import Counter
    counts = Counter(s)
    # sort characters by count, most frequent first
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return ''.join(ch * cnt for ch, cnt in ordered)''',
         complexity="Time O(n + k log k), space O(n).",
         pitfalls="Sorting characters alphabetically instead of by count; forgetting to repeat each char its count times.",
         example="frequency_sort('tree') -> 'eert' or 'eetr' (e twice first)."),
    dict(cat="dsa", title="First Unique Character in a String",
         answer="Return the index of the first non-repeating character, or -1. Count characters in one pass, then scan again for the first with count 1.",
         tags=["first-unique-character","counting","hash-map","string","dsa"],
         code='''# Index of the first non-repeating character, else -1.
def first_uniq_char(s):
    from collections import Counter
    counts = Counter(s)
    for i, ch in enumerate(s):
        if counts[ch] == 1:            # first character seen exactly once
            return i
    return -1''',
         complexity="Time O(n), space O(1) (bounded alphabet).",
         pitfalls="Returning the character instead of its index; a single pass can't know future duplicates (need two passes).",
         example="first_uniq_char('leetcode') -> 0; first_uniq_char('aabb') -> -1."),
    dict(cat="dsa", title="Intersection of Two Arrays II",
         answer="Return the intersection including duplicates (each element appears as many times as it does in both). Count one array, then for each element of the other decrement and emit when the count is positive.",
         tags=["intersection-arrays","counting","hash-map","array","dsa"],
         code='''# Multiset intersection of two arrays (duplicates preserved).
def intersect(nums1, nums2):
    from collections import Counter
    counts = Counter(nums1)
    result = []
    for x in nums2:
        if counts[x] > 0:              # still available in nums1's multiset
            result.append(x)
            counts[x] -= 1
    return result''',
         complexity="Time O(n + m), space O(min(n, m)).",
         pitfalls="Using a set (drops duplicates); not decrementing the count so an element repeats too often.",
         example="intersect([1,2,2,1], [2,2]) -> [2,2]."),
    dict(cat="glossary", title="At-least-once vs at-most-once vs exactly-once",
         answer="Message DELIVERY GUARANTEES. AT-MOST-ONCE: fire-and-forget; a message may be lost but never duplicated (no retries) — cheapest, for tolerable-loss telemetry. AT-LEAST-ONCE: retried until acknowledged, so it's never lost but MAY be duplicated — the common default; consumers must be IDEMPOTENT. EXACTLY-ONCE: never lost and never duplicated — the strongest but hardest; true end-to-end exactly-once is often approximated via at-least-once delivery + idempotent processing (dedup keys, transactional writes), since perfect exactly-once across a network is famously difficult.",
         tags=["delivery-semantics","at-least-once","exactly-once","idempotency","messaging"],
         example="A payments pipeline uses at-least-once delivery (never drop a charge) plus an idempotency key on the consumer, giving effective exactly-once processing without needing the broker to guarantee it."),
    dict(cat="glossary", title="Backpressure",
         answer="A flow-control mechanism where a downstream component that can't keep up SIGNALS upstream to slow down, preventing unbounded queue growth and out-of-memory crashes. Implemented via bounded buffers, blocking/pausing producers, TCP-style windows, or reactive-streams request(n) demand. Without backpressure a fast producer overwhelms a slow consumer — queues grow until they exhaust memory or latency explodes. The alternatives when overwhelmed are to buffer (bounded), drop, or block; backpressure chooses to slow the source.",
         tags=["backpressure","flow-control","reactive-streams","bounded-buffer","reliability"],
         example="A Kafka consumer lagging behind pauses its fetch so the broker retains rather than floods it; a reactive stream signals request(10) so the publisher emits only 10 items until the subscriber asks for more."),
    dict(cat="glossary", title="Cache stampede",
         answer="Also 'thundering herd on cache' — when a popular cache key EXPIRES and many concurrent requests all miss simultaneously, they stampede the database to recompute the same value at once, spiking load. Mitigations: a LOCK/single-flight so only one request recomputes while others wait or serve stale; PROBABILISTIC early expiration (refresh a bit before TTL); staggered/jittered TTLs; and serving stale-while-revalidate. Common cause of correlated DB overload right after a cache flush or a hot key's expiry.",
         tags=["cache-stampede","thundering-herd","single-flight","stale-while-revalidate","caching"],
         example="A homepage's cached feed expires at a round minute; 10,000 requests miss together and hammer the DB. A single-flight lock lets one request rebuild it while the rest briefly serve the stale copy — flattening the spike."),
    dict(cat="glossary", title="Read-through vs write-through cache",
         answer="Cache-population strategies. READ-THROUGH: the cache sits in front of the DB; on a miss the CACHE loads from the DB, stores, and returns — the app only talks to the cache. WRITE-THROUGH: writes go to the cache AND synchronously to the DB together, keeping them consistent at the cost of write latency. Contrast write-BACK (write to cache, flush to DB async — fast but risks loss) and cache-aside (app manages loads/invalidations). Read-through simplifies reads; write-through keeps the cache fresh on writes but slows them.",
         tags=["read-through","write-through","write-back","cache-aside","caching"],
         example="A product catalog uses read-through so a miss transparently loads from the DB into Redis; an inventory counter uses write-through so each decrement updates Redis and the DB together, keeping reads consistent."),
    dict(cat="ml_coding", title="Min-max scaling (numpy)",
         answer="Min-max scaling maps each feature linearly to [0,1]: (x - min) / (max - min), fit per column on training data. Useful when you need bounded inputs (e.g. image pixels, some neural nets); sensitive to outliers (a single extreme value compresses the rest).",
         tags=["min-max-scaling","normalization","feature-scaling","preprocessing","ml-coding"],
         code='''# Scale each feature column to [0, 1]. ast.parse-only.
import numpy as np

def min_max_scale(x_train, x_test=None, eps=1e-8):
    mn = x_train.min(axis=0)                       # per-feature min (train)
    mx = x_train.max(axis=0)                       # per-feature max (train)
    train_scaled = (x_train - mn) / (mx - mn + eps)
    if x_test is None:
        return train_scaled
    test_scaled = (x_test - mn) / (mx - mn + eps)  # reuse train min/max
    return train_scaled, test_scaled''',
         complexity="Time O(n * features), space O(n * features).",
         pitfalls="Fitting on the full dataset (test leakage); divide-by-zero on constant features (add eps); per-row instead of per-column.",
         example="min_max_scale(np.array([[1.],[3.],[5.]])) -> [[0.],[0.5],[1.]]."),
    dict(cat="ml_coding", title="Gradient descent step (numpy)",
         answer="One step of batch gradient descent for linear regression: compute predictions X@w, the error, the gradient of MSE (X^T @ error * 2/n), and update w -= lr * grad. The core loop of most parametric learning.",
         tags=["gradient-descent","linear-regression","optimization","training","ml-coding"],
         code='''# One batch gradient-descent update for linear regression. ast.parse-only.
import numpy as np

def gd_step(X, y, w, lr):
    n = X.shape[0]
    pred = X @ w                                   # linear predictions
    error = pred - y                               # residuals
    grad = (X.T @ error) * (2.0 / n)               # dMSE/dw
    return w - lr * grad                           # step downhill''',
         complexity="Time O(n * features), space O(features).",
         pitfalls="Wrong gradient scale (missing 2/n); sign flipped (adding the gradient); not transposing X for the gradient.",
         example="gd_step(np.array([[1.,1.],[1.,2.]]), np.array([1.,2.]), np.zeros(2), 0.1) moves w toward the fit."),
    dict(cat="ml_coding", title="Euclidean distance matrix (numpy)",
         answer="Pairwise squared Euclidean distances between rows of A and rows of B via the identity ||a-b||^2 = ||a||^2 + ||b||^2 - 2 a·b — fully vectorized, avoiding Python loops. Take sqrt (clip negatives from float error) for actual distances.",
         tags=["euclidean-distance","vectorization","knn","pairwise","ml-coding"],
         code='''# Pairwise Euclidean distances between rows of A and B. ast.parse-only.
import numpy as np

def euclidean_distance_matrix(A, B):
    a_sq = np.sum(A ** 2, axis=1, keepdims=True)   # ||a||^2 column
    b_sq = np.sum(B ** 2, axis=1, keepdims=True).T # ||b||^2 row
    cross = A @ B.T                                # a . b
    sq = a_sq + b_sq - 2 * cross                   # squared distances
    sq = np.maximum(sq, 0)                         # clip tiny negatives
    return np.sqrt(sq)''',
         complexity="Time O(n * m * d), space O(n * m).",
         pitfalls="Forgetting to clip negatives before sqrt (NaN); transposing the wrong term; double Python loops instead of the identity.",
         example="euclidean_distance_matrix(np.zeros((1,2)), np.ones((1,2))) -> [[1.414...]]."),
    dict(cat="conceptual", title="Why do we need idempotent consumers with at-least-once delivery, and how do you make one?",
         answer="Most real message systems give AT-LEAST-ONCE delivery, not exactly-once, because guaranteeing a message is delivered exactly one time across an unreliable network is effectively impossible: the broker sends a message, the consumer processes it, but the ACK back to the broker can be lost (network blip, consumer crash after processing but before acking). The broker, seeing no ack, MUST redeliver — otherwise it would risk losing messages. So the same message can legitimately arrive more than once, and the consumer cannot tell a genuine first delivery from a redelivery. If processing has SIDE EFFECTS (charge a card, increment a counter, send an email), naive at-least-once means double-charges, inflated counts, and duplicate emails. The fix is to make the consumer IDEMPOTENT — processing the same message twice yields the same end state as processing it once. Techniques: (1) a DEDUP KEY / idempotency key — record each processed message id in a store and skip if already seen (must be atomic with the side effect, e.g. same DB transaction, or you re-introduce a gap); (2) design operations to be naturally idempotent — 'set status = shipped' instead of 'increment', or UPSERT instead of INSERT; (3) conditional writes / optimistic concurrency so a replay is a no-op; (4) for external effects that can't be deduped (emails), keep a sent-log keyed by message id. The subtlety is ATOMICITY: the dedup record and the side effect must commit together, otherwise a crash between them leaves you either double-processing or marking-done-without-doing. This is why 'exactly-once processing' is achievable (at-least-once delivery + idempotent consumer) even though 'exactly-once delivery' is not.",
         tags=["idempotency","at-least-once","exactly-once","dedup-key","why"],
         example="An order-paid consumer stores processed message ids in the same DB transaction that marks the order paid; a redelivery finds the id already recorded and skips — so a lost ack causing redelivery never double-charges the customer."),
    dict(cat="conceptual", title="Why does min-max scaling suffer from outliers while standardization is more robust?",
         answer="Min-max scaling maps a feature to [0,1] via (x - min)/(max - min). Its two anchor points are the extreme MIN and MAX of the data — the single most outlier-prone statistics there are. If one sample is a wild outlier (say a data-entry error of 1,000,000 in a column normally ranging 0–100), it becomes the max, and now EVERY other value is divided by ~1,000,000, so the entire normal range gets crushed into a tiny sliver near 0 — the feature loses almost all its resolution and becomes nearly useless to the model. A single bad point dictates the scale for all points. Standardization, (x - mean)/std, instead centers on the MEAN and scales by the STANDARD DEVIATION — both AGGREGATE statistics computed over all samples. An outlier still perturbs the mean and std, but its influence is diluted across n points (the mean moves by outlier/n, the std by a bounded amount), not made the sole anchor. So the bulk of the data keeps a sensible spread even with a few outliers. The trade-offs: min-max gives a guaranteed bounded range (needed for some algorithms and image inputs) but is fragile to outliers and to test values outside the training min/max (they fall outside [0,1]); standardization has an unbounded range but preserves relative spacing and handles outliers more gracefully. Best practice: standardize by default for most models; use min-max when you specifically need bounded inputs and the data is outlier-clean or clipped/winsorized first; use ROBUST scaling (median and IQR) when outliers are heavy and you still want bounded-ish behavior.",
         tags=["min-max-scaling","standardization","outliers","robust-scaling","why"],
         example="A salary column of [30k, 40k, 50k, 1,000k typo]: min-max squashes the three real values into [0, 0.01, 0.02] near zero (the typo owns the scale), while standardization keeps them near [-0.6, -0.5, -0.4] with the typo as a visible large positive z-score — the model still distinguishes the normal salaries."),
    dict(cat="behavioral", title="STAR: Earning trust after a mistake / owning an incident (Earn Trust / Ownership)",
         answer="Amazon LPs: EARN TRUST (leaders listen, speak candidly, treat others respectfully, are self-critical, and own mistakes) and OWNERSHIP (act on behalf of the whole company, never say 'that's not my job'). Show you owned a failure you caused, communicated transparently, fixed the root cause, and rebuilt trust — no blame-shifting.",
         tags=["behavioral","star","earn-trust","ownership","amazon-lp"],
         example="SITUATION: I shipped a config change that I believed was low-risk; it silently disabled retry-on-failure for a background job, and two days later we discovered ~4 hours of user exports had failed without alerting. TASK: The failure was mine and customers were affected; I had to own it, contain the damage, and make sure it couldn't recur. ACTION: I immediately raised it in the team channel rather than hoping it went unnoticed, wrote a plain-language summary of what I changed and its impact, and paged myself to lead the fix. I re-ran the failed exports for affected users after verifying the data, then addressed the real gap: the job had no alerting on a zero-retry failure, so I added monitoring and an alert, and added a test that would have caught the disabled retry. In the blameless post-mortem I was explicit that my change caused it and focused the actions on the systemic holes (no alert, no test) rather than on myself. RESULT: All affected exports were recovered within a day, the new alerting caught two unrelated failures the next month, and my manager later said owning it openly — instead of minimizing it — actually increased the team's trust in me. I turned a self-inflicted incident into durable monitoring the whole team now relies on."),
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

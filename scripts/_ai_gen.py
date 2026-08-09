"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it -- no heredocs, pipes, or && chains.
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
    dict(cat="dsa", title="Height Checker",
         answer="Students should stand in non-decreasing height order; count how many are out of place versus the sorted arrangement. Sort a copy and count positions that differ.",
         tags=["height-checker","counting-sort","sorting","array","dsa"],
         code='''# Count students not in their sorted (expected) height position.
def height_checker(heights):
    expected = sorted(heights)         # target non-decreasing order
    count = 0
    for actual, want in zip(heights, expected):
        if actual != want:
            count += 1                 # this position is out of order
    return count''',
         complexity="Time O(n log n) (or O(n) counting sort), space O(n).",
         pitfalls="Comparing to the reversed order; sorting the original in place and losing it.",
         example="height_checker([1,1,4,2,1,3]) -> 3."),
    dict(cat="dsa", title="Relative Sort Array",
         answer="Sort arr1 so elements follow the order in arr2; elements not in arr2 go last in ascending order. Count arr1, emit arr2's values in order (using counts), then the leftovers sorted.",
         tags=["relative-sort","counting","custom-order","array","dsa"],
         code='''# Sort arr1 by arr2's order; unlisted elements ascending at the end.
def relative_sort_array(arr1, arr2):
    from collections import Counter
    counts = Counter(arr1)
    result = []
    for x in arr2:                     # emit in arr2's prescribed order
        result.extend([x] * counts.pop(x, 0))
    for x in sorted(counts):           # leftovers ascending
        result.extend([x] * counts[x])
    return result''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Forgetting leftovers must be sorted; not removing consumed keys so they reappear.",
         example="relative_sort_array([2,3,1,3,2,4,6,7,9,2,19], [2,1,4,3,9,6]) -> [2,2,2,1,4,3,3,9,6,7,19]."),
    dict(cat="dsa", title="Find Words That Can Be Formed by Characters",
         answer="Given a set of available characters, return the total length of words that can be spelled using them (each char used at most as many times as it appears). For each word, check its letter counts fit within the available counts.",
         tags=["words-formed-by-chars","counting","hash-map","string","dsa"],
         code='''# Sum lengths of words spellable from the available characters.
def count_characters(words, chars):
    from collections import Counter
    available = Counter(chars)
    total = 0
    for word in words:
        wc = Counter(word)
        if all(wc[c] <= available[c] for c in wc):   # every letter fits
            total += len(word)
    return total''',
         complexity="Time O(total characters), space O(alphabet).",
         pitfalls="Only checking presence not counts; mutating the available counter across words.",
         example="count_characters(['cat','bt','hat','tree'], 'atach') -> 6  ('cat' + 'hat')."),
    dict(cat="dsa", title="Degree of an Array",
         answer="The degree is the max frequency of any element; find the shortest contiguous subarray with the same degree. Track first and last index of each value; for each value at max frequency, the window length is last-first+1; take the minimum.",
         tags=["degree-of-array","hash-map","first-last-index","array","dsa"],
         code='''# Shortest subarray whose degree equals the whole array's degree.
def find_shortest_subarray(nums):
    first, count = {}, {}
    last = {}
    for i, x in enumerate(nums):
        if x not in first:
            first[x] = i               # remember first occurrence
        last[x] = i                    # keep updating last occurrence
        count[x] = count.get(x, 0) + 1
    degree = max(count.values())
    best = len(nums)
    for x in count:
        if count[x] == degree:         # this value sets the degree
            best = min(best, last[x] - first[x] + 1)
    return best''',
         complexity="Time O(n), space O(n).",
         pitfalls="Only considering one max-frequency value (ties matter); off-by-one in the window length.",
         example="find_shortest_subarray([1,2,2,3,1,4,2]) -> 6."),
    dict(cat="dsa", title="Longest Common Prefix",
         answer="Find the longest common prefix among an array of strings. Compare characters column by column across all strings; stop at the first mismatch or the shortest string's end.",
         tags=["longest-common-prefix","string","vertical-scan","dsa"],
         code='''# Longest common prefix shared by all strings (vertical scan).
def longest_common_prefix(strs):
    if not strs:
        return ''
    for i, ch in enumerate(strs[0]):   # walk the first string's chars
        for other in strs[1:]:
            if i >= len(other) or other[i] != ch:
                return strs[0][:i]     # mismatch or ran off an end
    return strs[0]''',
         complexity="Time O(total characters), space O(1).",
         pitfalls="Not handling an empty list or empty string; indexing past a shorter string.",
         example="longest_common_prefix(['flower','flow','flight']) -> 'fl'."),
    dict(cat="dsa", title="Isomorphic Strings",
         answer="Two strings are isomorphic if characters in s can be consistently mapped to characters in t (a bijection preserving order). Keep two maps (s->t and t->s) and verify every pair is consistent both ways.",
         tags=["isomorphic-strings","hash-map","bijection","string","dsa"],
         code='''# True if s and t are isomorphic (consistent one-to-one char mapping).
def is_isomorphic(s, t):
    if len(s) != len(t):
        return False
    map_st, map_ts = {}, {}
    for a, b in zip(s, t):
        if a in map_st and map_st[a] != b:
            return False               # s-char already maps elsewhere
        if b in map_ts and map_ts[b] != a:
            return False               # t-char already claimed
        map_st[a] = b
        map_ts[b] = a
    return True''',
         complexity="Time O(n), space O(1) (bounded alphabet).",
         pitfalls="Using only one direction (misses two chars mapping to the same target); ignoring length mismatch.",
         example="is_isomorphic('egg','add') -> True; is_isomorphic('foo','bar') -> False."),
    dict(cat="dsa", title="Word Pattern",
         answer="Check a string of words follows a pattern (like 'abba'). Bijection between pattern letters and words; two maps enforce a one-to-one correspondence and lengths must match.",
         tags=["word-pattern","hash-map","bijection","string","dsa"],
         code='''# True if words follow the pattern via a one-to-one mapping.
def word_pattern(pattern, s):
    words = s.split()
    if len(pattern) != len(words):
        return False
    p2w, w2p = {}, {}
    for p, w in zip(pattern, words):
        if p in p2w and p2w[p] != w:
            return False               # pattern char maps to a different word
        if w in w2p and w2p[w] != p:
            return False               # word already bound to another char
        p2w[p] = w
        w2p[w] = p
    return True''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not checking both directions; forgetting the count of words must equal the pattern length.",
         example="word_pattern('abba', 'dog cat cat dog') -> True; word_pattern('abba', 'dog cat cat fish') -> False."),
    dict(cat="dsa", title="Ransom Note",
         answer="Can ransomNote be built from the letters in magazine (each letter used once)? Count magazine letters; verify every ransomNote letter has enough supply.",
         tags=["ransom-note","counting","hash-map","string","dsa"],
         code='''# True if ransomNote can be spelled from magazine's letters.
def can_construct(ransom_note, magazine):
    from collections import Counter
    supply = Counter(magazine)
    need = Counter(ransom_note)
    return all(supply[c] >= need[c] for c in need)''',
         complexity="Time O(n + m), space O(alphabet).",
         pitfalls="Checking presence instead of counts; scanning magazine per letter (O(n*m)).",
         example="can_construct('aa', 'aab') -> True; can_construct('aa', 'ab') -> False."),
    dict(cat="dsa", title="Find All Numbers Disappeared in an Array",
         answer="For nums in [1, n], find all values in [1, n] missing from the array. In-place trick: for each value, mark index abs(v)-1 negative; the indices still positive correspond to missing numbers.",
         tags=["disappeared-numbers","in-place","index-marking","array","dsa"],
         code='''# Missing values from [1..n] using in-place negative marking.
def find_disappeared_numbers(nums):
    for v in nums:
        idx = abs(v) - 1               # value maps to this index
        if nums[idx] > 0:
            nums[idx] = -nums[idx]     # mark 'seen'
    result = []
    for i, v in enumerate(nums):
        if v > 0:                      # never marked -> i+1 is missing
            result.append(i + 1)
    return result''',
         complexity="Time O(n), space O(1) (output aside).",
         pitfalls="Not using abs when re-reading marked values; off-by-one between value and index.",
         example="find_disappeared_numbers([4,3,2,7,8,2,3,1]) -> [5,6]."),
    dict(cat="dsa", title="Majority Element (Boyer-Moore)",
         answer="Find the element appearing more than n/2 times. Boyer-Moore voting: keep a candidate and a count; matching votes increment, differing decrement, and a zero count adopts a new candidate. The majority survives.",
         tags=["majority-element","boyer-moore","voting","array","dsa"],
         code='''# Majority element (> n/2) via Boyer-Moore voting.
def majority_element(nums):
    candidate = None
    count = 0
    for x in nums:
        if count == 0:
            candidate = x              # adopt a new candidate
        count += 1 if x == candidate else -1
    return candidate''',
         complexity="Time O(n), space O(1).",
         pitfalls="Assuming a majority always exists (verify if not guaranteed); resetting count incorrectly.",
         example="majority_element([2,2,1,1,1,2,2]) -> 2."),
    dict(cat="dsa", title="Single Number (XOR)",
         answer="Every element appears twice except one; find the single. XOR all elements: pairs cancel (x^x=0) and 0^single = single.",
         tags=["single-number","xor","bit-manipulation","array","dsa"],
         code='''# Find the element that appears once (all others twice) via XOR.
def single_number(nums):
    result = 0
    for x in nums:
        result ^= x                    # duplicates cancel out
    return result''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using a set/count (O(n) space) when XOR is O(1); assuming exactly-twice does not hold.",
         example="single_number([4,1,2,1,2]) -> 4."),
    dict(cat="dsa", title="Missing Number",
         answer="Array holds n distinct numbers from [0, n] with one missing; find it. Sum 0..n via n(n+1)/2 and subtract the array sum; the difference is the missing number (or XOR trick).",
         tags=["missing-number","math","xor","array","dsa"],
         code='''# Missing value from [0..n] via the expected-sum difference.
def missing_number(nums):
    n = len(nums)
    expected = n * (n + 1) // 2         # sum of 0..n
    return expected - sum(nums)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Off-by-one on n (range is 0..n inclusive); integer overflow in other languages (use XOR there).",
         example="missing_number([3,0,1]) -> 2."),
    dict(cat="glossary", title="Hedged requests",
         answer="A tail-latency reduction technique: after a request has been outstanding longer than, say, the 95th-percentile latency, send a DUPLICATE ('hedge') request to another replica and take whichever responds first, cancelling the other. It trims the slow tail (a single slow server no longer dictates p99) at the cost of a little extra load (bounded because hedges only fire for the slow fraction). Popularized by Google's 'The Tail at Scale'.",
         tags=["hedged-requests","tail-latency","p99","replicas","performance"],
         example="A read waits past its p95 (say 10ms) with no reply, so the client fires a second read to another replica; the first to answer wins -- so one GC-paused server no longer blows up p99, for only ~5% extra requests."),
    dict(cat="glossary", title="Load shedding",
         answer="Deliberately DROPPING or rejecting a fraction of incoming work when a system is overloaded, to protect the rest from collapse. Better to fail some requests fast (429/503) than to let queues grow until everything times out (congestion collapse). Often prioritized -- shed low-value/retry traffic first, keep health checks and paying users -- and paired with backpressure and admission control. The goal: degrade throughput gracefully instead of falling over entirely.",
         tags=["load-shedding","overload","admission-control","429","reliability"],
         example="At 100% CPU an API starts returning 503 to 20% of anonymous requests (keeping logged-in traffic) so latency stays bounded, instead of accepting everything and timing out for all."),
    dict(cat="glossary", title="Request coalescing",
         answer="Collapsing multiple identical in-flight requests into a SINGLE upstream call, sharing its result among all waiters (a.k.a. single-flight). When many callers ask for the same key at once (a hot cache miss), only the first triggers the expensive fetch; the rest wait and receive the same answer. Prevents duplicated work and cache stampedes; the cache-layer cousin of hedging's opposite -- fewer calls, not more.",
         tags=["request-coalescing","single-flight","cache-stampede","deduplication","performance"],
         example="1,000 concurrent requests miss the same cache key; a single-flight guard makes just one hit the database while the other 999 block on that one result -- collapsing 1,000 DB queries into 1."),
    dict(cat="glossary", title="Graceful degradation",
         answer="Designing a system so that when a dependency fails or load spikes, it drops to a REDUCED but still-useful mode instead of failing entirely. Non-essential features are disabled, stale/cached or default data is served, and the core function survives. Enabled by circuit breakers, fallbacks, feature toggles, and load shedding. The opposite of a brittle system where one failed dependency takes everything down.",
         tags=["graceful-degradation","fallback","circuit-breaker","resilience","reliability"],
         example="If the recommendation service is down, an e-commerce page hides the 'Recommended for you' carousel and serves a generic bestsellers list from cache -- the user can still browse and buy rather than seeing an error page."),
    dict(cat="ml_coding", title="PCA via SVD (numpy)",
         answer="PCA finds directions of maximum variance. Center the data, take the SVD (X = U S Vt); the rows of Vt are principal components (right singular vectors), and projecting onto the top-k gives the reduced representation. SVD is the numerically stable route (vs eigendecomposition of the covariance).",
         tags=["pca","svd","dimensionality-reduction","unsupervised","ml-coding"],
         code='''# PCA to k components via SVD. ast.parse-only.
import numpy as np

def pca(X, k):
    X_centered = X - X.mean(axis=0)               # center each feature
    # economy SVD; rows of Vt are the principal directions
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
    components = Vt[:k]                            # top-k directions
    projected = X_centered @ components.T         # reduced coordinates
    return projected, components''',
         complexity="Time O(n * d * min(n,d)), space O(n * d).",
         pitfalls="Forgetting to center (PCA assumes zero mean); using U instead of Vt for components; taking too many components.",
         example="pca(np.array([[2.,0.],[0.,2.],[ -2.,0.],[0.,-2.]]), 1) projects the 2-D points onto their top variance axis."),
    dict(cat="ml_coding", title="Dropout forward (numpy)",
         answer="Dropout randomly zeros a fraction p of activations during training to prevent co-adaptation, then scales survivors by 1/(1-p) (inverted dropout) so the expected value is unchanged and inference needs no scaling. At inference it is a no-op.",
         tags=["dropout","regularization","inverted-dropout","training","ml-coding"],
         code='''# Inverted dropout forward pass. ast.parse-only (rng passed in).
import numpy as np

def dropout_forward(x, p, training, rng):
    if not training or p == 0:
        return x                                  # no-op at inference
    keep = 1 - p
    mask = (rng.random(x.shape) < keep) / keep    # scaled keep-mask
    return x * mask                               # zero-and-scale survivors''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not scaling by 1/keep (train/inference mismatch); applying dropout at inference; dropping p vs keeping p confusion.",
         example="dropout_forward(x, 0.5, training=True, rng) zeros ~half of x and doubles the rest; training=False returns x unchanged."),
    dict(cat="ml_coding", title="Accuracy and confusion matrix (numpy)",
         answer="Accuracy = fraction correct. The confusion matrix C[i][j] counts samples of true class i predicted as class j; its diagonal is correct predictions. Build it by incrementing C[true, pred] per sample.",
         tags=["accuracy","confusion-matrix","classification-metrics","evaluation","ml-coding"],
         code='''# Accuracy and a confusion matrix for integer labels. ast.parse-only.
import numpy as np

def accuracy_and_confusion(y_true, y_pred, num_classes):
    accuracy = np.mean(y_true == y_pred)          # fraction correct
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1                             # true t predicted p
    return accuracy, cm''',
         complexity="Time O(n), space O(num_classes^2).",
         pitfalls="Swapping the (true, pred) axes; num_classes smaller than the max label; comparing floats for equality.",
         example="accuracy_and_confusion(np.array([0,1,1]), np.array([0,1,0]), 2) -> accuracy 0.667, cm [[1,0],[1,1]]."),
    dict(cat="conceptual", title="Why do hedged requests reduce tail latency, and why not just send duplicate requests always?",
         answer="Tail latency (p99, p999) in a large system is dominated not by the average server but by the occasional slow one: a server doing garbage collection, serving a cold cache, sharing a noisy CPU, or briefly queueing. In a request that fans out to many servers, the SLOWEST component gates the whole response, so even if each server is fast 99% of the time, a request touching 100 of them is very likely to hit at least one slow one -- tail latency compounds. HEDGED REQUESTS attack this directly: wait until a request is clearly running slow (past, say, the p95 for that operation), then send a second copy to a DIFFERENT replica and take whichever finishes first. Because the slowness of one server is usually independent of another, the probability that BOTH the original and the hedge are slow is much lower (roughly the product of the individual slow-probabilities), so the tail collapses toward the typical latency. The reason you DON'T just duplicate every request always is COST: sending two copies of everything doubles the load on the whole fleet, and a system running near capacity would tip into overload -- which itself creates queueing and makes latency worse, defeating the purpose. The elegance of the p95-triggered hedge is that hedges only fire for the small fraction of requests that are actually slow (~5%), so the extra load is bounded to a few percent while capturing almost all the tail-latency benefit. Refinements: 'tied requests' where the two copies tell each other to cancel once one starts executing (cutting wasted work further), and never hedging when the system is already hot (to avoid amplifying overload). The principle: spend a little redundant work precisely where it buys tail-latency improvement, not everywhere.",
         tags=["hedged-requests","tail-latency","p99","tail-at-scale","why"],
         example="A request fanning out to 100 leaf servers each with 1% chance of a 1s stall has a ~63% chance at least one stalls; hedging the slow 5% to a second replica makes both-slow astronomically rarer, so p99 drops from ~1s toward the ~10ms typical -- for only ~5% extra requests, whereas always-duplicating would add 100% load and risk overload."),
    dict(cat="conceptual", title="Why scale by 1/(1-p) in dropout, and why is inference a no-op?",
         answer="Dropout regularizes a network by randomly zeroing each activation with probability p during training, which forces the network not to rely on any single unit (preventing co-adaptation) and acts like training an ensemble of subnetworks. But zeroing units changes the EXPECTED MAGNITUDE of a layer's output: if a unit's normal output is a and it survives with probability keep = 1-p, then its expected contribution during training drops to keep*a. If you did nothing to correct this, the layer feeding into the next one would, on average, send a signal that is (1-p) times as large during training as it would be at inference (when all units are active) -- so the distributions of activations seen by downstream layers would MISMATCH between training and test, and the carefully-learned weights would be miscalibrated at inference, degrading accuracy. There are two ways to fix the mismatch. Classic dropout scales activations DOWN by keep at inference; but the modern standard is INVERTED DROPOUT, which instead scales the surviving activations UP by 1/keep = 1/(1-p) during training. That way the expected value of each activation during training becomes keep * (a/keep) = a -- exactly what it would be with no dropout -- so training-time activations already match the full-network scale. The payoff is that INFERENCE needs no special handling at all: you simply run the full network with every unit active and no scaling, which is faster and simpler (important because inference happens far more often than training and you don't want per-unit correction there). So the 1/(1-p) factor is a bookkeeping trick that moves the necessary rescaling into the training path, keeping expected activations invariant and making the test-time forward pass a clean no-op. A subtlety: the scaling preserves the MEAN but inflates the VARIANCE of activations during training, which is part of dropout's noise-injection regularization effect.",
         tags=["dropout","inverted-dropout","regularization","train-test-consistency","why"],
         example="With p=0.5 (keep=0.5), a unit that would output 4 is kept and multiplied by 1/0.5=2 to output 8 during training half the time and 0 the other half -- expected 4, matching the no-dropout value -- so at inference you just output 4 with no scaling."),
    dict(cat="behavioral", title="STAR: Disagreeing with a decision then fully committing (Have Backbone; Disagree and Commit)",
         answer="Amazon LP: HAVE BACKBONE; DISAGREE AND COMMIT -- leaders respectfully challenge decisions they disagree with, even when uncomfortable, but once a decision is made they commit wholly. Show you voiced a well-reasoned dissent with data, and then -- when overruled -- backed the decision genuinely rather than sabotaging it.",
         tags=["behavioral","star","disagree-and-commit","have-backbone","amazon-lp"],
         example="SITUATION: My team decided to build a new service on a NoSQL store I believed was the wrong fit -- our access patterns were highly relational with multi-entity transactions. TASK: As the senior engineer I owed the team my honest technical judgment, but the tech lead and two others favored NoSQL for its scaling story. ACTION: I wrote a one-page doc laying out the specific queries and the transactional consistency we needed, showed where NoSQL would force complex application-side joins and risk anomalies, and proposed Postgres with a clear scaling path. I presented it directly but without rancor, and asked hard questions. The group still chose NoSQL, weighting operational familiarity higher than I did. Rather than relitigate or quietly resist, I committed fully: I helped design the data model to minimize the join pain I'd worried about, wrote the access layer, and added integration tests around the consistency edge cases I'd flagged. RESULT: We shipped on time; two of the anomaly cases I'd raised did surface in testing and my guardrails caught them early, so we handled them cleanly instead of in production. Months later we did add a relational store for one subsystem -- but because I'd committed and built well, the team trusted my earlier dissent and brought me in to lead that migration. Voicing the disagreement AND committing wholeheartedly both mattered."),
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

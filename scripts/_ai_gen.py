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
    dict(cat="dsa", title="Single Number (XOR)",
         answer="Every element appears twice except one; find the single one using XOR. Because x ^ x = 0 and XOR is commutative, XOR-ing all numbers cancels the pairs and leaves the unique value. O(n) time, O(1) space — no hash set needed.",
         tags=["single-number","bit-manipulation","xor","dsa"],
         code='''# The element that appears exactly once (all others appear twice).
def single_number(nums):
    result = 0
    for x in nums:
        result ^= x       # XOR: equal pairs cancel to 0, the unique value remains
    return result''',
         complexity="Time O(n), space O(1).",
         pitfalls="A hash set works but uses O(n) space; XOR only works when the others appear exactly twice.",
         example="single_number([4,1,2,1,2]) -> 4."),
    dict(cat="dsa", title="Subarray Sum Equals K",
         answer="Count contiguous subarrays that sum to k. Track a RUNNING PREFIX SUM; a subarray ending at i sums to k iff some earlier prefix equals prefix[i] - k. Keep a hash map of how many times each prefix sum has occurred and add its count. O(n) — and it handles negatives (a sliding window would not).",
         tags=["subarray-sum","prefix-sum","hashmap","dsa"],
         code='''from collections import defaultdict

# Number of contiguous subarrays of nums that sum to k.
def subarray_sum(nums, k):
    count = 0
    prefix = 0
    seen = defaultdict(int)
    seen[0] = 1                    # the empty prefix (sum 0) seen once
    for x in nums:
        prefix += x                # running sum up to this element
        count += seen[prefix - k]  # earlier prefixes that make a k-sum here
        seen[prefix] += 1          # record this prefix sum
    return count''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting seen[0]=1 (misses subarrays starting at index 0); a sliding window fails with negative numbers.",
         example="subarray_sum([1,1,1], 2) -> 2; subarray_sum([1,2,3], 3) -> 2."),
    dict(cat="dsa", title="Next Greater Element (monotonic stack)",
         answer="For each element, find the next element to its right that is greater (or -1). Use a MONOTONIC decreasing STACK of indices: while the current value beats the value at the stack top, that top's 'next greater' is the current value — pop and record it. O(n), because each index is pushed and popped once.",
         tags=["next-greater-element","monotonic-stack","stack","dsa"],
         code='''# For each element, the next greater element to its right (or -1).
def next_greater(nums):
    res = [-1] * len(nums)
    stack = []                     # indices still waiting for a next-greater
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] < x:
            res[stack.pop()] = x   # x is the next greater for that popped index
        stack.append(i)
    return res''',
         complexity="Time O(n), space O(n).",
         pitfalls="A nested loop is O(n^2); push INDICES (not values) when you need positions.",
         example="next_greater([2,1,2,4,3]) -> [4,2,4,-1,-1]."),
    dict(cat="dsa", title="Sliding Window Maximum (deque)",
         answer="Return the maximum of every window of size k as it slides. Use a DEQUE of indices kept in decreasing value order: evict indices that fall out of the window (front) and pop smaller values off the back before adding the new index. The front is always the window's max. O(n) — each index enters and leaves the deque once.",
         tags=["sliding-window-maximum","deque","monotonic-queue","dsa"],
         code='''from collections import deque

# Maximum of each sliding window of size k.
def max_sliding_window(nums, k):
    dq = deque()                   # indices; their values decrease front -> back
    res = []
    for i, x in enumerate(nums):
        if dq and dq[0] <= i - k:  # the front index fell out of the window
            dq.popleft()
        while dq and nums[dq[-1]] <= x:
            dq.pop()               # x dominates smaller trailing values
        dq.append(i)
        if i >= k - 1:             # window is full -> record its max (the front)
            res.append(nums[dq[0]])
    return res''',
         complexity="Time O(n), space O(k).",
         pitfalls="Not evicting out-of-window indices; comparing values instead of indices for the window check.",
         example="max_sliding_window([1,3,-1,-3,5,3,6,7], 3) -> [3,3,5,5,6,7]."),
    dict(cat="dsa", title="Permutations (backtracking)",
         answer="Generate all orderings of a list. Backtracking: build a permutation by choosing each UNUSED element, recursing, then undoing the choice. Track which elements are used. There are n! permutations, so exponential time is expected.",
         tags=["permutations","backtracking","recursion","dsa"],
         code='''# All permutations of the list nums.
def permute(nums):
    res = []
    used = [False] * len(nums)
    path = []
    def backtrack():
        if len(path) == len(nums):     # a complete permutation
            res.append(path[:])        # append a COPY (path keeps changing)
            return
        for i in range(len(nums)):
            if used[i]:
                continue               # skip already-used elements
            used[i] = True
            path.append(nums[i])       # choose
            backtrack()                # explore
            path.pop()                 # un-choose (backtrack)
            used[i] = False
    backtrack()
    return res''',
         complexity="Time O(n * n!), space O(n).",
         pitfalls="Appending path instead of a copy; forgetting to reset used[i] after recursing.",
         example="permute([1,2,3]) -> [[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]."),
    dict(cat="glossary", title="Mutual information",
         answer="A measure of how much knowing one variable REDUCES uncertainty about another — the information they share. It is zero if and only if they are independent, and unlike correlation it captures ANY (even non-linear) dependence. Used in feature selection and analyzing representations.",
         tags=["mutual-information","statistics","feature-selection"],
         example="Mutual information between 'is raining' and 'ground is wet' is high — knowing one tells you a lot about the other."),
    dict(cat="glossary", title="MAP (Maximum A Posteriori)",
         answer="An estimate that picks the parameter maximizing the POSTERIOR (likelihood times prior), unlike MLE which ignores the prior. It is MLE plus a prior belief, and mathematically the prior acts like regularization. As data grows, MAP converges to MLE.",
         tags=["map","bayesian","statistics","mle"],
         example="With few coin flips, MAP with a 'probably fair' prior estimates P(heads) closer to 0.5 than MLE; with thousands of flips they agree."),
    dict(cat="glossary", title="Adversarial example",
         answer="An input with a TINY, deliberately crafted perturbation (often invisible to humans) that makes a model confidently WRONG. It exposes that models rely on brittle patterns rather than robust concepts. A common defense is adversarial training (training on such examples).",
         tags=["adversarial-example","ai-security","robustness","deep-learning"],
         example="Adding imperceptible noise to a panda photo makes a classifier label it 'gibbon' with 99% confidence."),
    dict(cat="glossary", title="SHAP / feature importance",
         answer="SHAP values explain a model's prediction by FAIRLY attributing it across features (using game-theory Shapley values): how much each feature pushed the prediction up or down. It answers 'WHY did the model decide this?' for any model — crucial for trust, fairness, and debugging.",
         tags=["shap","explainability","feature-importance","ml"],
         example="For a denied loan, SHAP shows 'low income' pushed the score down most and 'long credit history' pushed it up — an explainable reason."),
    dict(cat="glossary", title="Semi-supervised & active learning",
         answer="Two ways to cope with scarce labels. SEMI-SUPERVISED learning trains on a small labeled set PLUS a large unlabeled set (exploiting the unlabeled data's structure). ACTIVE learning has the model REQUEST labels for the most informative/uncertain examples, so humans label only what matters most.",
         tags=["semi-supervised","active-learning","labeling","ml"],
         example="Active learning: instead of labeling 10k random images, label the 500 the model is most unsure about — far more efficient."),
    dict(cat="cs_fundamentals", title="CAP theorem",
         answer="In a distributed system, during a network PARTITION you can guarantee at most TWO of: Consistency (every read sees the latest write), Availability (every request gets a response), and Partition tolerance (it keeps working despite dropped messages). Since partitions are unavoidable, the real choice is C vs A: CP systems refuse some requests to stay correct; AP systems answer with possibly-stale data.",
         tags=["cap","distributed-systems","consistency","cs"],
         example="A bank ledger picks CP (reject on partition rather than show a wrong balance); a social feed picks AP (show slightly stale posts but stay up)."),
    dict(cat="cs_fundamentals", title="Caching strategies",
         answer="Ways to keep a cache consistent with the database. CACHE-ASIDE: the app checks the cache, and on a miss reads the DB and populates it (most common). WRITE-THROUGH: writes go to cache and DB together (consistent, slower writes). WRITE-BACK: write to cache, flush to DB later (fast, risk of loss). Eviction by LRU/LFU/TTL; the hard part is invalidation.",
         tags=["caching","cache-aside","write-through","cs"],
         example="A product page uses cache-aside with a 5-min TTL; on a price change the app deletes the cache key so the next read repopulates it."),
    dict(cat="cs_fundamentals", title="Database normalization",
         answer="Organizing tables to reduce REDUNDANCY and update anomalies by splitting data into related tables (1NF: atomic values; 2NF/3NF: remove partial/transitive dependencies). Each fact lives in one place, so updates are simple — but reassembling data needs joins. You DENORMALIZE (duplicate) deliberately to speed reads.",
         tags=["normalization","database","3nf","cs"],
         example="Instead of repeating a customer's address on every order row, store it once in a customers table and reference it by id."),
    dict(cat="conceptual", title="Why does XOR let you find a unique number in O(1) space?",
         answer="XOR has two magic properties: x ^ x = 0 (a value cancels itself) and x ^ 0 = x, and it is commutative and associative (order doesn't matter). So if you XOR every number in a list where each appears twice except one, all the pairs cancel to 0 and only the lone value survives — using a single accumulator variable instead of a hash set. It is a beautiful example of using an algebraic property to trade extra memory for a clever operation.",
         tags=["xor","bit-manipulation","space-complexity","why"],
         example="[4,1,2,1,2]: 4^1^2^1^2 = 4^(1^1)^(2^2) = 4^0^0 = 4 — the pairs vanish, leaving 4."),
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

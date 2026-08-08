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
    dict(cat="dsa", title="Basic Calculator (with parentheses)",
         answer="Evaluate a string expression with +, -, non-negative integers, and nested parentheses. Scan left to right accumulating the current number and a running result with a sign; on '(' push the result and sign and reset; on ')' fold the inner result back using the saved sign and outer result. No operator precedence needed since only + and -.",
         tags=["basic-calculator","stack","expression","parsing","dsa"],
         code='''# Evaluate a string with +, -, non-negative ints, and parentheses.
def calculate(s):
    result = 0
    num = 0
    sign = 1                              # current sign: +1 or -1
    stack = []                            # saves (outer result, outer sign) at '('
    for ch in s:
        if ch.isdigit():
            num = num * 10 + int(ch)      # build a multi-digit number
        elif ch in '+-':
            result += sign * num          # apply the pending number
            num = 0
            sign = 1 if ch == '+' else -1
        elif ch == '(':
            stack.append(result)          # save context before recursing
            stack.append(sign)
            result, sign = 0, 1           # start fresh inside the parens
        elif ch == ')':
            result += sign * num          # finish the inner expression
            num = 0
            result *= stack.pop()         # apply the sign that preceded '('
            result += stack.pop()         # add back the saved outer result
    return result + sign * num            # apply any trailing number''',
         complexity="Time O(n), space O(n) for the stack depth.",
         pitfalls="Forgetting the trailing number after the loop; mixing up the push/pop order of sign and result.",
         example="calculate('(1+(4+5+2)-3)+(6+8)') -> 23."),
    dict(cat="dsa", title="Largest Number (custom sort)",
         answer="Arrange a list of non-negative integers to form the LARGEST possible concatenated number. The key is a custom comparator: a should come before b if the string a+b is greater than b+a. Sort by that rule and concatenate; handle the all-zeros edge case so you return '0', not '00'.",
         tags=["largest-number","custom-sort","comparator","greedy","dsa"],
         code='''# Arrange numbers to form the largest possible concatenated number.
import functools
def largest_number(nums):
    strs = [str(n) for n in nums]
    def cmp(a, b):
        if a + b > b + a:                 # a should come first
            return -1
        if a + b < b + a:
            return 1
        return 0
    strs.sort(key=functools.cmp_to_key(cmp))
    result = "".join(strs)
    return "0" if result[0] == "0" else result   # collapse all-zeros to zero''',
         complexity="Time O(n log n) comparisons of O(d)-length strings, space O(n).",
         pitfalls="Comparing numerically instead of by concatenation; returning '000...' for all-zero input.",
         example="largest_number([3,30,34,5,9]) -> '9534330'."),
    dict(cat="dsa", title="Meeting Rooms II (minimum rooms)",
         answer="Given meeting time intervals, find the minimum number of rooms needed (the peak number of simultaneous meetings). Sort by start time and keep a MIN-HEAP of end times of ongoing meetings; for each new meeting, free a room if the earliest end is <= its start, then occupy a room. The heap size is the answer.",
         tags=["meeting-rooms","heap","intervals","scheduling","dsa"],
         code='''# Minimum number of meeting rooms needed for overlapping intervals.
import heapq
def min_meeting_rooms(intervals):
    if not intervals:
        return 0
    intervals.sort(key=lambda x: x[0])    # sort by start time
    heap = []                             # end times of meetings in progress
    for start, end in intervals:
        if heap and heap[0] <= start:
            heapq.heappop(heap)           # earliest-ending room frees up
        heapq.heappush(heap, end)         # occupy a room until 'end'
    return len(heap)                      # peak concurrency = rooms needed''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Not sorting by start first; using < instead of <= when a meeting ends exactly as another starts.",
         example="min_meeting_rooms([[0,30],[5,10],[15,20]]) -> 2."),
    dict(cat="dsa", title="Partition Labels (greedy)",
         answer="Split a string into as many parts as possible so that each letter appears in at most one part; return the part sizes. Precompute the LAST index of every character. Sweep, extending the current partition's end to the furthest last-occurrence seen; when the scan index reaches that end, close the partition.",
         tags=["partition-labels","greedy","string","intervals","dsa"],
         code='''# Partition a string so each letter appears in only one part; return part sizes.
def partition_labels(s):
    last = {ch: i for i, ch in enumerate(s)}   # last index of each char
    result = []
    start = end = 0
    for i, ch in enumerate(s):
        end = max(end, last[ch])          # must extend to ch's last occurrence
        if i == end:                      # partition is self-contained
            result.append(end - start + 1)
            start = i + 1
    return result''',
         complexity="Time O(n), space O(1) (at most 26 keys).",
         pitfalls="Closing a partition before reaching the furthest last-index; off-by-one in the size.",
         example="partition_labels('ababcbacadefegdehijhklij') -> [9,7,8]."),
    dict(cat="dsa", title="Longest Consecutive Sequence",
         answer="Find the length of the longest run of consecutive integers in an unsorted array, in O(n) — no sorting. Put everything in a set; only start counting from a number that has no predecessor (n-1 absent), then walk upward while successors exist. Each number is visited at most twice, keeping it linear.",
         tags=["longest-consecutive","hash-set","array","dsa"],
         code='''# Length of the longest run of consecutive integers, O(n) with a set.
def longest_consecutive(nums):
    num_set = set(nums)
    best = 0
    for n in num_set:
        if n - 1 not in num_set:          # only start at a run's beginning
            length = 1
            while n + length in num_set:  # extend the run upward
                length += 1
            best = max(best, length)
    return best''',
         complexity="Time O(n), space O(n).",
         pitfalls="Starting a walk from every element (O(n^2)); the predecessor check is what keeps it linear.",
         example="longest_consecutive([100,4,200,1,3,2]) -> 4  ([1,2,3,4])."),
    dict(cat="dsa", title="Product of Array Except Self",
         answer="Return an array where each position holds the product of all OTHER elements — without using division. Two sweeps: first fill each slot with the running product of everything to its LEFT, then multiply in the running product of everything to its RIGHT. O(n) time, O(1) extra space beyond the output.",
         tags=["product-except-self","prefix-product","array","dsa"],
         code='''# For each index, the product of all other elements, without division.
def product_except_self(nums):
    n = len(nums)
    result = [1] * n
    prefix = 1
    for i in range(n):
        result[i] = prefix                # product of everything to the left
        prefix *= nums[i]
    suffix = 1
    for i in range(n - 1, -1, -1):
        result[i] *= suffix               # multiply in everything to the right
        suffix *= nums[i]
    return result''',
         complexity="Time O(n), space O(1) beyond the output.",
         pitfalls="Using division (fails on zeros); overwriting before you've used the left product.",
         example="product_except_self([1,2,3,4]) -> [24,12,8,6]."),
    dict(cat="dsa", title="Container With Most Water (two pointers)",
         answer="Given heights of vertical lines, find two that with the x-axis hold the most water. Two pointers at the ends: the area is the shorter height times the width; always move the SHORTER side inward, because moving the taller side can only shrink the area (width drops, height capped by the shorter line anyway).",
         tags=["container-most-water","two-pointers","array","greedy","dsa"],
         code='''# Max water a container can hold between two vertical lines (two pointers).
def max_area(height):
    left, right = 0, len(height) - 1
    best = 0
    while left < right:
        h = min(height[left], height[right])
        best = max(best, h * (right - left))   # area = shorter side * width
        if height[left] < height[right]:
            left += 1                     # move the shorter side inward
        else:
            right -= 1
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Moving the taller side (never helps); recomputing width incorrectly.",
         example="max_area([1,8,6,2,5,4,8,3,7]) -> 49."),
    dict(cat="dsa", title="Find the Duplicate Number (Floyd's cycle)",
         answer="An array of n+1 integers each in [1, n] has exactly one duplicate; find it WITHOUT modifying the array or extra space. Treat values as 'next' pointers — the duplicate creates a cycle. Use Floyd's tortoise-and-hare: find a meeting point in the cycle, then walk one pointer from the start until they meet at the cycle's entrance (the duplicate).",
         tags=["find-duplicate","floyd","cycle-detection","two-pointers","dsa"],
         code='''# Find the one duplicate in n+1 ints in [1,n] (Floyd's cycle detection).
def find_duplicate(nums):
    slow = fast = nums[0]
    while True:                           # phase 1: find a meeting point
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            break
    slow = nums[0]                        # phase 2: find the cycle entrance
    while slow != fast:
        slow = nums[slow]
        fast = nums[fast]
    return slow                           # the entrance == the duplicate''',
         complexity="Time O(n), space O(1).",
         pitfalls="Modifying the array (not allowed); stopping at phase 1 (that's not the duplicate yet).",
         example="find_duplicate([1,3,4,2,2]) -> 2."),
    dict(cat="glossary", title="Catastrophic forgetting",
         answer="When a neural network trained SEQUENTIALLY on new tasks/data abruptly loses performance on earlier ones — the new gradients overwrite the weights that encoded old knowledge. It's the central obstacle to CONTINUAL/lifelong learning. Mitigations: rehearsal (replay old data), regularization that protects important weights (EWC), or dedicated per-task parameters.",
         tags=["catastrophic-forgetting","continual-learning","training","stability"],
         example="A model fine-tuned on task B forgets task A almost entirely; replaying a small buffer of task-A examples during B training preserves both."),
    dict(cat="glossary", title="Domain adaptation",
         answer="Adapting a model trained on a SOURCE domain to work well on a related but different TARGET domain with little or no target labels (e.g. synthetic->real images, one hospital's scans->another's). Techniques align the source and target feature distributions (adversarial alignment, importance weighting) so the learned knowledge transfers despite the shift.",
         tags=["domain-adaptation","transfer-learning","distribution-shift","robustness"],
         example="A pedestrian detector trained on sunny daytime footage is domain-adapted to work at night by aligning day/night feature distributions, without labeling many night images."),
    dict(cat="glossary", title="Covariate shift vs label shift",
         answer="Two kinds of distribution shift between training and deployment. COVARIATE (feature) SHIFT: the input distribution P(x) changes but P(y|x) is stable (a new user mix, yet the feature->label rule holds). LABEL/PRIOR SHIFT: the label distribution P(y) changes while P(x|y) stays (a disease becomes more prevalent). Each needs a different correction — reweighting by density ratio vs by class prior.",
         tags=["covariate-shift","label-shift","distribution-shift","mlops"],
         example="A spam filter seeing more mail from a new region is covariate shift; the same filter during a spam surge (more spam overall) faces label shift — you'd recalibrate the class prior."),
    dict(cat="glossary", title="Exponential moving average (EMA)",
         answer="A running average that weights recent values more heavily, updated as ema = β·ema + (1-β)·x. In deep learning, keeping an EMA of the MODEL WEIGHTS during training often yields a smoother, better-generalizing final model than the raw last-step weights; it also smooths noisy metrics and underlies optimizer moment estimates (Adam).",
         tags=["ema","exponential-moving-average","training","optimization","smoothing"],
         example="Averaging model weights with β=0.999 over training gives a 'polished' EMA model that usually validates a bit higher than the last-step weights — common in modern image/LLM training."),
    dict(cat="ml_coding", title="Gaussian Naive Bayes (from scratch)",
         answer="A probabilistic classifier that assumes features are conditionally independent given the class. FIT: estimate each class's prior and, per feature, the mean and variance. PREDICT: for each class sum the log-prior and the log Gaussian likelihoods of the features (logs avoid underflow) and pick the highest. Fast, needs little data, and is a strong baseline.",
         tags=["naive-bayes","gaussian","probabilistic","classification","ml-coding"],
         code='''# Gaussian Naive Bayes: fit priors + per-feature mean/variance, then predict.
import math
def gnb_fit(X, y):
    classes = set(y)
    stats = {}                            # class -> (prior, [(mean, var) per feature])
    for c in classes:
        rows = [X[i] for i in range(len(X)) if y[i] == c]
        prior = len(rows) / len(X)
        feats = []
        for j in range(len(X[0])):
            col = [row[j] for row in rows]
            mean = sum(col) / len(col)
            var = sum((v - mean) ** 2 for v in col) / len(col) + 1e-9   # avoid /0
            feats.append((mean, var))
        stats[c] = (prior, feats)
    return stats

def gnb_predict(stats, x):
    best_c, best_log = None, float('-inf')
    for c, (prior, feats) in stats.items():
        log_prob = math.log(prior)        # log prior
        for (mean, var), xi in zip(feats, x):
            # add the log Gaussian likelihood of this feature
            log_prob += -0.5 * math.log(2 * math.pi * var) - (xi - mean) ** 2 / (2 * var)
        if log_prob > best_log:
            best_log, best_c = log_prob, c
    return best_c''',
         complexity="Fit O(n*d), predict O(classes*d); space O(classes*d).",
         pitfalls="Multiplying raw probabilities (underflow — sum logs instead); zero variance (add epsilon).",
         example="Fit on X=[[1.0],[1.2],[5.0],[5.2]], y=[0,0,1,1]; gnb_predict for [1.1] -> 0."),
    dict(cat="conceptual", title="Why do ensembles (bagging, boosting) usually beat a single model?",
         answer="Because they attack different parts of prediction error. BAGGING (random forests) trains many high-variance models on bootstrap samples and AVERAGES them, cancelling their uncorrelated errors and cutting VARIANCE without raising bias — averaging independent noisy estimates yields a steadier one. BOOSTING (gradient boosting) trains models SEQUENTIALLY, each correcting the prior ensemble's mistakes, which mainly reduces BIAS, turning weak learners into a strong one. Both rely on members making somewhat INDEPENDENT errors; ensembling identical/correlated models gains nothing.",
         tags=["ensemble","bagging","boosting","bias-variance","why"],
         example="One decision tree overfits (high variance); a 200-tree random forest averages that noise away, while boosting stacks shallow trees to steadily drive down error."),
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

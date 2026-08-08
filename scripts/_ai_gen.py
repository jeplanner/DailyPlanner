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
    dict(cat="dsa", title="Evaluate Reverse Polish Notation",
         answer="Evaluate an arithmetic expression written in postfix (Reverse Polish) form using a stack. Push numbers; on an operator, pop the two most recent operands, apply it, and push the result. Postfix needs no parentheses or precedence rules — the order encodes everything. Careful with operand order and integer division truncation.",
         tags=["reverse-polish-notation","stack","expression","dsa"],
         code='''# Evaluate an arithmetic expression in Reverse Polish (postfix) Notation.
def eval_rpn(tokens):
    stack = []
    ops = {'+', '-', '*', '/'}
    for tok in tokens:
        if tok in ops:
            b = stack.pop()               # right operand (popped first)
            a = stack.pop()               # left operand
            if tok == '+': stack.append(a + b)
            elif tok == '-': stack.append(a - b)
            elif tok == '*': stack.append(a * b)
            else: stack.append(int(a / b))   # truncate toward zero
        else:
            stack.append(int(tok))        # a number -> push it
    return stack[0]''',
         complexity="Time O(n), space O(n).",
         pitfalls="Swapping operand order for - and / (b is popped first); wrong truncation direction for division.",
         example="eval_rpn(['2','1','+','3','*']) -> 9  ((2+1)*3)."),
    dict(cat="dsa", title="Decode String (stack)",
         answer="Decode strings like '3[a2[c]]' into 'accaccacc'. Use a stack: build the current string and a running count; on '[' push the (string-so-far, count) and reset; on ']' pop and expand the bracket by repeating the inner string. Handles arbitrary nesting because the stack remembers each outer context.",
         tags=["decode-string","stack","string","nested","dsa"],
         code='''# Decode strings like '3[a2[c]]' -> 'accaccacc' using a stack.
def decode_string(s):
    stack = []                            # holds (previous string, repeat count)
    current = ""
    num = 0
    for ch in s:
        if ch.isdigit():
            num = num * 10 + int(ch)      # build a multi-digit number
        elif ch == '[':
            stack.append((current, num))  # save the outer context
            current, num = "", 0
        elif ch == ']':
            prev, count = stack.pop()
            current = prev + current * count   # expand the bracketed part
        else:
            current += ch
    return current''',
         complexity="Time O(output length), space O(depth).",
         pitfalls="Resetting num/current at the wrong moment; not supporting multi-digit counts.",
         example="decode_string('3[a2[c]]') -> 'accaccacc'."),
    dict(cat="dsa", title="Asteroid Collision (stack)",
         answer="Simulate asteroids on a line: positive values move right, negative move left; when a right-mover meets a left-mover the smaller explodes (both if equal). A stack holds surviving asteroids; each incoming left-mover is compared against the stack top while collisions can happen, popping or exploding as needed.",
         tags=["asteroid-collision","stack","simulation","dsa"],
         code='''# Positive asteroids move right, negative move left; equal sizes both explode.
def asteroid_collision(asteroids):
    stack = []
    for a in asteroids:
        alive = True
        while alive and a < 0 and stack and stack[-1] > 0:
            # a (moving left) meets stack top (moving right) -> collision
            if stack[-1] < -a:
                stack.pop()               # top is smaller -> it explodes, keep going
                continue
            elif stack[-1] == -a:
                stack.pop()               # equal -> both explode
            alive = False                 # incoming asteroid does not survive
        if alive:
            stack.append(a)
    return stack''',
         complexity="Time O(n), space O(n).",
         pitfalls="Only colliding when top>0 and a<0; forgetting the equal-size double-explosion.",
         example="asteroid_collision([5,10,-5]) -> [5,10]; asteroid_collision([8,-8]) -> []."),
    dict(cat="dsa", title="Daily Temperatures (monotonic stack)",
         answer="For each day, find how many days you must wait for a warmer temperature (0 if none). Keep a MONOTONIC decreasing stack of indices whose warmer day hasn't been found; when a warmer temperature arrives, pop all colder days and record the day gap. Each index is pushed/popped once, so O(n).",
         tags=["daily-temperatures","monotonic-stack","array","dsa"],
         code='''# For each day, how many days until a warmer temperature (monotonic stack).
def daily_temperatures(temps):
    result = [0] * len(temps)
    stack = []                            # indices of days awaiting a warmer day
    for i, t in enumerate(temps):
        while stack and temps[stack[-1]] < t:
            prev = stack.pop()
            result[prev] = i - prev       # number of days waited
        stack.append(i)
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Storing temperatures instead of indices (you need the gap); using <= (equal isn't warmer).",
         example="daily_temperatures([73,74,75,71,69,72,76,73]) -> [1,1,4,2,1,1,0,0]."),
    dict(cat="dsa", title="Next Greater Element II (circular)",
         answer="For each element in a CIRCULAR array, find the next greater element scanning forward with wrap-around (-1 if none). Trick: iterate 2n times using index i % n to simulate the wrap, maintaining a monotonic decreasing stack of indices; only push real indices on the first pass so answers aren't overwritten.",
         tags=["next-greater-element","monotonic-stack","circular","array","dsa"],
         code='''# Next greater element for each item in a circular array (-1 if none).
def next_greater_elements(nums):
    n = len(nums)
    result = [-1] * n
    stack = []                            # indices still awaiting an answer
    for i in range(2 * n):                # loop twice to simulate wrap-around
        num = nums[i % n]
        while stack and nums[stack[-1]] < num:
            result[stack.pop()] = num
        if i < n:
            stack.append(i)               # only push first-pass (real) indices
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Pushing indices on the second pass (double answers); forgetting the i % n wrap.",
         example="next_greater_elements([1,2,1]) -> [2,-1,2]."),
    dict(cat="dsa", title="K Closest Points to Origin (heap)",
         answer="Return the k points nearest the origin. Keep a MAX-heap of size k keyed by squared distance (no sqrt needed since it preserves order): push each point and, if the heap exceeds k, pop the farthest. What remains are the k closest. O(n log k) beats sorting all n points.",
         tags=["k-closest-points","heap","priority-queue","geometry","dsa"],
         code='''# The k points closest to the origin, using a size-k max-heap.
import heapq
def k_closest(points, k):
    heap = []                             # max-heap via negated distance
    for x, y in points:
        d = x * x + y * y                 # squared distance (sqrt unnecessary)
        heapq.heappush(heap, (-d, x, y))
        if len(heap) > k:
            heapq.heappop(heap)           # drop the current farthest
    return [[x, y] for _, x, y in heap]''',
         complexity="Time O(n log k), space O(k).",
         pitfalls="Taking sqrt (wastes time, same ordering); using a min-heap of size k (keeps the wrong points).",
         example="k_closest([[1,3],[-2,2],[5,8],[0,1]], 2) -> [[-2,2],[0,1]] (order may vary)."),
    dict(cat="dsa", title="Reorganize String (greedy heap)",
         answer="Rearrange a string so no two adjacent characters are equal, or return '' if impossible. Greedy: always place the MOST frequent remaining character that isn't the one just placed. A max-heap by count drives this; hold the previously placed char aside for one turn (to 'cool down') before pushing it back. Impossible iff some char exceeds (n+1)/2.",
         tags=["reorganize-string","heap","greedy","string","dsa"],
         code='''# Rearrange so no two adjacent chars match, or '' if impossible.
import heapq
from collections import Counter
def reorganize_string(s):
    counts = Counter(s)
    max_heap = [(-cnt, ch) for ch, cnt in counts.items()]
    heapq.heapify(max_heap)               # most frequent char on top
    result = []
    prev = None                           # char just placed (cools down one turn)
    while max_heap:
        cnt, ch = heapq.heappop(max_heap)
        result.append(ch)
        if prev and prev[0] < 0:
            heapq.heappush(max_heap, prev)   # re-add the cooled-down char
        prev = (cnt + 1, ch)              # used one occurrence (cnt is negative)
    res = "".join(result)
    return res if len(res) == len(s) else ""''',
         complexity="Time O(n log k), space O(k) for k distinct chars.",
         pitfalls="Pushing the previous char back too early (adjacent duplicates); mishandling the negated counts.",
         example="reorganize_string('aab') -> 'aba' (a valid arrangement)."),
    dict(cat="glossary", title="Data augmentation",
         answer="Artificially expanding a training set by applying LABEL-PRESERVING transformations to existing examples — cropping/flipping/rotating/colour-jittering images, synonym-swapping or back-translating text, adding noise to audio. It improves generalization and robustness by teaching the model useful invariances, and combats overfitting when data is scarce.",
         tags=["data-augmentation","regularization","vision","nlp","training"],
         example="Randomly flipping and cropping training photos of cats teaches a classifier a cat is a cat regardless of position or orientation — often adding a few points of accuracy for free."),
    dict(cat="glossary", title="SMOTE",
         answer="Synthetic Minority Over-sampling TEchnique — balances an imbalanced dataset by creating SYNTHETIC minority-class examples rather than just duplicating them. It interpolates between a minority point and its nearest minority neighbours, generating plausible new points along the connecting lines. This reduces the overfitting that naive duplication causes.",
         tags=["smote","imbalance","oversampling","synthetic-data"],
         example="For a fraud dataset with 1% positives, SMOTE synthesizes new fraud-like rows between real frauds, giving the classifier more varied positive examples to learn from."),
    dict(cat="glossary", title="Mixup",
         answer="A data-augmentation/regularization technique that trains on CONVEX COMBINATIONS of pairs of examples AND their labels: x = λ·x_i + (1-λ)·x_j and y = λ·y_i + (1-λ)·y_j. This linear-interpolation regularizer smooths decision boundaries, improves calibration, and increases robustness to noisy labels and adversarial examples.",
         tags=["mixup","data-augmentation","regularization","calibration"],
         example="Mixing a cat image (70%) with a dog image (30%) and training toward a 0.7-cat / 0.3-dog label makes the model less overconfident and generalize better."),
    dict(cat="glossary", title="Weak supervision",
         answer="Training with LARGE amounts of NOISY, imprecise, or programmatically-generated labels instead of scarce hand-labeled data — from heuristics, rules, distant supervision, or crowd labels. Frameworks like Snorkel combine many noisy 'labeling functions' and model their accuracies to produce probabilistic training labels at scale.",
         tags=["weak-supervision","labeling","snorkel","noisy-labels","data"],
         example="Instead of hand-labeling 100k emails, you write 20 heuristic rules ('contains an unsubscribe link -> promo'); a weak-supervision model reconciles their disagreements into training labels."),
    dict(cat="glossary", title="Stratified sampling",
         answer="Splitting or sampling data so each subgroup (stratum) appears in the same PROPORTION as in the full population — e.g. keeping the class ratio identical across train/test and every CV fold. It reduces evaluation variance and prevents a rare class from being absent in a fold, which matters a lot for imbalanced data.",
         tags=["stratified-sampling","cross-validation","imbalance","evaluation"],
         example="For a dataset that's 5% positive, stratified 5-fold CV ensures every fold has ~5% positives, so no fold accidentally has zero positives to validate on."),
    dict(cat="ml_system_design", title="Design a Churn Prediction system",
         answer="Predict which users/customers are likely to STOP using a product so you can intervene. (1) CLARIFY & SCALE: define churn precisely (e.g. no activity for 30 days, or a subscription cancellation) with a prediction horizon; the goal is enabling retention, so ranking at-risk users well matters most. (2) DATA & LABELS: historical users labeled churned/retained over a window; mind the label definition and survivorship. (3) FEATURES: engagement/usage TRENDS (declining activity is a strong signal), recency-frequency-monetary, tenure, support tickets, plan, product events. (4) MODEL: gradient-boosted trees on tabular features are the workhorse, outputting a churn probability. (5) EVAL: AUC/PR-AUC and — crucially — precision/recall at the top-k users you can actually target; calibrate probabilities; measure lift over baseline. (6) SERVING/MONITORING/AB: score users on a schedule, route high-risk users to retention campaigns, and A/B TEST the intervention (not just the model), since the real goal is reduced churn; monitor drift.",
         tags=["churn-prediction","retention","gradient-boosting","ml-system-design"],
         example="A user whose weekly logins dropped from 10 to 1 and who filed a support ticket scores high churn risk; the model flags them for a win-back offer, and an A/B test confirms the offer actually reduces churn versus a holdout."),
    dict(cat="ml_system_design", title="Design a Customer Lifetime Value (LTV) prediction system",
         answer="Predict the future LIFETIME VALUE a customer will generate, to guide acquisition spend and targeting. (1) CLARIFY & SCALE: define the LTV horizon (e.g. 12-month revenue/margin); it's used to bid for acquisition and prioritize high-value users. (2) DATA & LABELS: historical customers with realized spend over the horizon; needs customers old enough for a full label (right-censoring is the challenge). (3) FEATURES: EARLY behaviour (first-week/month activity and purchases), acquisition channel, demographics, engagement, RFM. (4) MODEL: a regression (gradient-boosted trees) or a two-stage 'will they buy?' × 'how much?' model; probabilistic BG/NBD + Gamma-Gamma for non-contractual settings. (5) EVAL: regression metrics (MAE, RMSE) plus decile/rank calibration (do predicted high-LTV users actually spend more?), validated on a future cohort. (6) SERVING/MONITORING/AB: batch-score new customers early, feed LTV into marketing bids and segmentation, watch for drift and feedback loops, and validate against realized value as cohorts mature.",
         tags=["ltv","lifetime-value","regression","marketing","ml-system-design"],
         example="From a new user's first-week purchases and channel, the model predicts a 12-month LTV of $180, so marketing will pay more to acquire similar users — later validated against what the cohort actually spent."),
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

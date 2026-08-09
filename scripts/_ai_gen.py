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
    dict(cat="dsa", title="Reverse Integer",
         answer="Reverse the digits of a 32-bit signed integer; return 0 on overflow. Pop digits with %10 and //10, push onto the result, and check the 32-bit bounds before it overflows.",
         tags=["reverse-integer","math","overflow","dsa"],
         code='''# Reverse a signed 32-bit integer's digits; 0 on overflow.
def reverse_integer(x):
    INT_MIN, INT_MAX = -2**31, 2**31 - 1
    sign = -1 if x < 0 else 1
    x = abs(x)
    result = 0
    while x:
        result = result * 10 + x % 10   # append the next digit
        x //= 10
    result *= sign
    if result < INT_MIN or result > INT_MAX:
        return 0                        # overflow -> 0
    return result''',
         complexity="Time O(log x), space O(1).",
         pitfalls="Not checking 32-bit overflow; mishandling the sign of negatives.",
         example="reverse_integer(-123) -> -321; reverse_integer(1534236469) -> 0 (overflow)."),
    dict(cat="dsa", title="Palindrome Number",
         answer="Determine if an integer reads the same forwards and backwards, without converting to a string. Negatives aren't palindromes; reverse only HALF the digits and compare to the other half.",
         tags=["palindrome-number","math","two-halves","dsa"],
         code='''# True if an integer is a palindrome (reversing half the digits).
def is_palindrome(x):
    if x < 0 or (x % 10 == 0 and x != 0):
        return False                    # negatives / trailing zero can't be palindromes
    reversed_half = 0
    while x > reversed_half:
        reversed_half = reversed_half * 10 + x % 10
        x //= 10
    # even length: x == reversed_half; odd: drop the middle digit
    return x == reversed_half or x == reversed_half // 10''',
         complexity="Time O(log x), space O(1).",
         pitfalls="Forgetting numbers ending in 0 (except 0) fail; mishandling the odd-length middle digit.",
         example="is_palindrome(121) -> True; is_palindrome(-121) -> False; is_palindrome(10) -> False."),
    dict(cat="dsa", title="Fizz Buzz",
         answer="For 1..n output 'Fizz' for multiples of 3, 'Buzz' for 5, 'FizzBuzz' for both, else the number. Build each string by concatenating the applicable words.",
         tags=["fizzbuzz","simulation","modulo","dsa"],
         code='''# Classic FizzBuzz for 1..n.
def fizz_buzz(n):
    out = []
    for i in range(1, n + 1):
        s = ''
        if i % 3 == 0:
            s += 'Fizz'
        if i % 5 == 0:
            s += 'Buzz'
        out.append(s or str(i))         # fall back to the number
    return out''',
         complexity="Time O(n), space O(n).",
         pitfalls="Checking 3 and 5 separately with elif (misses FizzBuzz); off-by-one on the range.",
         example="fizz_buzz(5) -> ['1','2','Fizz','4','Buzz']."),
    dict(cat="dsa", title="Add Digits (Digital Root)",
         answer="Repeatedly sum digits until one digit remains. Closed form (digital root): 0 for 0, else 1 + (n-1) % 9 -- an O(1) result from modular arithmetic.",
         tags=["add-digits","digital-root","math","dsa"],
         code='''# Digital root: repeated digit sum reduced to one digit, in O(1).
def add_digits(num):
    if num == 0:
        return 0
    return 1 + (num - 1) % 9''',
         complexity="Time O(1), space O(1).",
         pitfalls="Special-casing 0 wrong; using n % 9 directly (returns 0 for multiples of 9 instead of 9).",
         example="add_digits(38) -> 2  (3+8=11 -> 1+1=2)."),
    dict(cat="dsa", title="Number Complement",
         answer="Flip every bit of a positive integer within its own bit-length (not the full 32 bits). Build a mask of all 1s the same width as num, then XOR.",
         tags=["number-complement","bit-manipulation","mask","dsa"],
         code='''# Complement of a positive integer within its own bit width.
def find_complement(num):
    mask = 1
    while mask < num:
        mask = (mask << 1) | 1          # grow an all-ones mask to num's width
    return num ^ mask                   # flip only the meaningful bits''',
         complexity="Time O(number of bits), space O(1).",
         pitfalls="Using ~num (flips the sign bits too); mask too short or too long.",
         example="find_complement(5) -> 2  (101 -> 010)."),
    dict(cat="dsa", title="Find Pivot Index",
         answer="Find the index where the sum of the numbers to the left equals the sum to the right. Track a running left sum; the right sum is total - left - nums[i]. Return the first match, else -1.",
         tags=["pivot-index","prefix-sum","array","dsa"],
         code='''# Index where left-sum equals right-sum, else -1.
def pivot_index(nums):
    total = sum(nums)
    left = 0
    for i, x in enumerate(nums):
        if left == total - left - x:    # right sum equals left sum
            return i
        left += x
    return -1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Including nums[i] in either side; not returning the leftmost pivot.",
         example="pivot_index([1,7,3,6,5,6]) -> 3."),
    dict(cat="dsa", title="Running Sum of 1d Array",
         answer="Return the running (prefix) sum where result[i] = sum(nums[0..i]). Accumulate in place or into a new array.",
         tags=["running-sum","prefix-sum","array","dsa"],
         code='''# Prefix sums: result[i] = nums[0] + ... + nums[i].
def running_sum(nums):
    result = []
    total = 0
    for x in nums:
        total += x                      # accumulate
        result.append(total)
    return result''',
         complexity="Time O(n), space O(n) (or O(1) in place).",
         pitfalls="Resetting the accumulator inside the loop; off-by-one when writing in place.",
         example="running_sum([1,2,3,4]) -> [1,3,6,10]."),
    dict(cat="dsa", title="Richest Customer Wealth",
         answer="Each row is one customer's bank accounts; return the maximum total wealth across customers. Sum each row and take the max.",
         tags=["richest-customer","matrix","sum","array","dsa"],
         code='''# Maximum row-sum (customer with the most total wealth).
def maximum_wealth(accounts):
    return max(sum(customer) for customer in accounts)''',
         complexity="Time O(m * n), space O(1).",
         pitfalls="Summing columns instead of rows; empty input (guard if needed).",
         example="maximum_wealth([[1,2,3],[3,2,1]]) -> 6; maximum_wealth([[1,5],[7,3],[3,5]]) -> 10."),
    dict(cat="dsa", title="How Many Numbers Are Smaller Than the Current Number",
         answer="For each element, count how many others are strictly smaller. Counting-sort style: tally value frequencies (values bounded 0..100), then a prefix sum gives, for each value, how many are smaller.",
         tags=["smaller-than-current","counting-sort","prefix-sum","array","dsa"],
         code='''# For each element, count how many values are strictly smaller.
def smaller_numbers_than_current(nums):
    count = [0] * 102                   # values bounded 0..100
    for x in nums:
        count[x + 1] += 1               # shift so prefix sum = strictly-smaller
    for i in range(1, 102):
        count[i] += count[i - 1]        # prefix sum of frequencies
    return [count[x] for x in nums]''',
         complexity="Time O(n + range), space O(range).",
         pitfalls="Counting equal values as smaller (needs strict); off-by-one in the prefix shift.",
         example="smaller_numbers_than_current([8,1,2,2,3]) -> [4,0,1,1,3]."),
    dict(cat="dsa", title="Decompress Run-Length Encoded List",
         answer="Pairs (freq, val) describe a run-length encoding; expand to the full list. For each adjacent pair, append val freq times.",
         tags=["decompress-rle","run-length-encoding","array","dsa"],
         code='''# Expand run-length pairs [freq, val, freq, val, ...] into the full list.
def decompress_rle_list(nums):
    result = []
    for i in range(0, len(nums), 2):
        freq, val = nums[i], nums[i + 1]
        result.extend([val] * freq)     # repeat the value freq times
    return result''',
         complexity="Time O(total output), space O(total output).",
         pitfalls="Swapping freq and val; stepping by 1 instead of 2 over the pairs.",
         example="decompress_rle_list([1,2,3,4]) -> [2,4,4,4]."),
    dict(cat="dsa", title="Matrix Diagonal Sum",
         answer="Sum the primary and secondary diagonals of a square matrix, counting the center once if n is odd. Add mat[i][i] and mat[i][n-1-i]; subtract the center if double-counted.",
         tags=["matrix-diagonal-sum","matrix","array","dsa"],
         code='''# Sum both diagonals of a square matrix (center counted once).
def diagonal_sum(mat):
    n = len(mat)
    total = 0
    for i in range(n):
        total += mat[i][i]              # primary diagonal
        total += mat[i][n - 1 - i]      # secondary diagonal
    if n % 2 == 1:
        total -= mat[n // 2][n // 2]    # center added twice
    return total''',
         complexity="Time O(n), space O(1).",
         pitfalls="Double-counting the center on odd n; wrong secondary-diagonal index.",
         example="diagonal_sum([[1,2,3],[4,5,6],[7,8,9]]) -> 25."),
    dict(cat="dsa", title="Transpose Matrix",
         answer="Return the transpose of a matrix (rows become columns). Build result[j][i] = matrix[i][j]; works for non-square shapes.",
         tags=["transpose-matrix","matrix","array","dsa"],
         code='''# Transpose an m x n matrix into n x m.
def transpose(matrix):
    rows, cols = len(matrix), len(matrix[0])
    result = [[0] * rows for _ in range(cols)]
    for i in range(rows):
        for j in range(cols):
            result[j][i] = matrix[i][j] # swap indices
    return result''',
         complexity="Time O(m * n), space O(m * n).",
         pitfalls="Assuming square dimensions; allocating the result with swapped dimensions wrong.",
         example="transpose([[1,2,3],[4,5,6]]) -> [[1,4],[2,5],[3,6]]."),
    dict(cat="glossary", title="Circuit breaker states",
         answer="A CIRCUIT BREAKER protects a caller from a failing dependency by tracking failures and short-circuiting calls. Three states: CLOSED (normal -- requests flow, failures counted); OPEN (failure threshold exceeded -- requests fail fast without calling the dependency, giving it time to recover); HALF-OPEN (after a cooldown -- a few trial requests test recovery; success closes the breaker, failure re-opens it). Prevents a struggling service from being hammered and stops cascading failures/thread exhaustion in the caller.",
         tags=["circuit-breaker","closed-open-half-open","cascading-failure","resilience","reliability"],
         example="Payment service starts timing out; after 50% of calls fail the breaker trips OPEN and the checkout instantly returns a fallback for 30s, then goes HALF-OPEN to probe -- one success closes it, restoring normal calls without a thundering retry herd."),
    dict(cat="glossary", title="Bulkhead isolation",
         answer="A resilience pattern named after a ship's watertight compartments: partition resources (thread pools, connection pools, instances) so a failure or overload in one part CANNOT sink the whole system. If calls to a slow dependency get their own bounded pool, they can exhaust only that pool -- other features keep working instead of every thread blocking on the slow call. Combines with circuit breakers and timeouts; the core idea is fault CONTAINMENT.",
         tags=["bulkhead","isolation","resource-partitioning","fault-containment","reliability"],
         example="An app gives the flaky recommendations API its own 10-thread pool; when it hangs, only those 10 threads block and the recommendations feature degrades -- checkout and search, on separate pools, stay fully responsive."),
    dict(cat="glossary", title="Liveness vs readiness probes",
         answer="Two health-check types (e.g. in Kubernetes). LIVENESS answers 'is this process healthy or wedged?' -- if it fails, the orchestrator RESTARTS the container (fixes deadlocks/hangs). READINESS answers 'can it serve traffic right now?' -- if it fails, the pod is removed from the load-balancer rotation but NOT restarted (used during warmup, or when a dependency is temporarily unavailable). Confusing them is harmful: a readiness-style check wired to liveness will restart pods that are merely busy; there's also a STARTUP probe for slow-booting apps.",
         tags=["liveness","readiness","health-check","kubernetes","reliability"],
         example="An app with a 60s cache warmup fails READINESS during warmup (no traffic sent yet) but passes LIVENESS (process is fine); once warm, readiness passes and it joins the load balancer -- versus a hang, where liveness fails and the container is restarted."),
    dict(cat="glossary", title="Service mesh",
         answer="A dedicated INFRASTRUCTURE LAYER that handles service-to-service communication for a microservice system, moving cross-cutting concerns out of application code into SIDECAR proxies (e.g. Envoy) deployed next to each service. The mesh (data plane = proxies, control plane = config/policy) provides mTLS encryption, load balancing, retries/timeouts, circuit breaking, traffic shifting (canary), and observability (metrics/traces) UNIFORMLY, without each app implementing them. Trade-off: added latency (extra hop) and operational complexity. Examples: Istio, Linkerd.",
         tags=["service-mesh","sidecar","envoy","istio","microservices"],
         example="With Istio, an app calls another service by plain HTTP to its local Envoy sidecar; the mesh transparently adds mTLS, retries, a 2% canary split, and distributed traces -- none of it in the app's code."),
    dict(cat="ml_coding", title="R-squared (coefficient of determination) (numpy)",
         answer="R^2 measures the fraction of variance in the target explained by the model: 1 - SS_res/SS_tot, where SS_res = sum((y-pred)^2) and SS_tot = sum((y-mean(y))^2). 1 is perfect; 0 means no better than predicting the mean; negative means worse than the mean.",
         tags=["r2-score","regression-metric","variance-explained","evaluation","ml-coding"],
         code='''# R^2 (coefficient of determination) for regression. ast.parse-only.
import numpy as np

def r2_score(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)       # residual sum of squares
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)  # total variance
    return 1 - ss_res / ss_tot''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing by zero when y is constant (SS_tot=0); swapping SS_res and SS_tot; expecting R^2 in [0,1] (it can go negative).",
         example="r2_score(np.array([3.,5.,7.]), np.array([3.,5.,7.])) -> 1.0 (perfect fit)."),
    dict(cat="ml_coding", title="Train-test split (numpy)",
         answer="Randomly partition data into train and test sets by shuffling indices and slicing at test_size. Shuffling avoids order bias; keep X and y aligned by permuting the SAME index array.",
         tags=["train-test-split","data-splitting","shuffling","evaluation","ml-coding"],
         code='''# Shuffle and split X, y into train/test. ast.parse-only (rng passed in).
import numpy as np

def train_test_split(X, y, test_size, rng):
    n = X.shape[0]
    idx = rng.permutation(n)            # random shuffle of row indices
    cut = int(n * (1 - test_size))      # boundary between train and test
    train_idx, test_idx = idx[:cut], idx[cut:]
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]''',
         complexity="Time O(n), space O(n).",
         pitfalls="Shuffling X and y independently (breaks alignment); off-by-one on the cut; not stratifying for imbalanced classes.",
         example="train_test_split(X, y, 0.2, rng) yields ~80% train / 20% test rows, X and y still aligned."),
    dict(cat="ml_coding", title="Gradient clipping (numpy)",
         answer="Gradient clipping caps the gradient to prevent exploding gradients (common in RNNs). Clip-by-NORM: if the global L2 norm exceeds a threshold, scale the whole gradient down by threshold/norm so its direction is preserved but its magnitude is bounded.",
         tags=["gradient-clipping","exploding-gradients","rnn","training","ml-coding"],
         code='''# Clip a gradient by global L2 norm. ast.parse-only.
import numpy as np

def clip_by_norm(grad, max_norm):
    norm = np.linalg.norm(grad)                   # global L2 norm
    if norm > max_norm:
        grad = grad * (max_norm / norm)           # scale down, keep direction
    return grad''',
         complexity="Time O(size of grad), space O(size of grad).",
         pitfalls="Clipping each element independently (changes direction) vs by-norm; dividing by zero when norm is 0.",
         example="clip_by_norm(np.array([3.,4.]), 2.5) scales [3,4] (norm 5) down to [1.5, 2.0] (norm 2.5)."),
    dict(cat="conceptual", title="Why do you need both liveness and readiness probes, and what breaks if you conflate them?",
         answer="Liveness and readiness answer fundamentally different questions, and using one where you need the other causes distinct failure modes. LIVENESS asks 'is this process broken beyond self-recovery?' -- a deadlock, an unrecoverable hang, a corrupted internal state. The orchestrator's response to a failed liveness check is to RESTART the container, because the only fix for a wedged process is to kill and replace it. READINESS asks a different question: 'can this instance serve requests RIGHT NOW?' -- which can be temporarily 'no' for perfectly healthy reasons: it's still warming a cache, loading a model, running migrations, or a downstream dependency it needs is briefly unavailable. The response to a failed readiness check is to REMOVE the pod from the load balancer rotation (stop sending it traffic) WITHOUT restarting it, because there's nothing to fix -- it just needs a moment, and traffic should go to other ready pods meanwhile. Now the failure modes from conflating them: (1) If you wire a readiness-type condition into the LIVENESS probe -- say, liveness fails when a dependency is down -- then a transient dependency outage makes the orchestrator RESTART all your pods, turning a brief blip into a crash-loop that destroys in-flight work and, worse, hammers the recovering dependency with a fleet of cold-starting pods (a self-inflicted thundering herd). Even a slow-warming app can get killed mid-warmup and never come up. (2) If you use a LIVENESS-type check for READINESS -- e.g. readiness only checks the process is up, not that warmup finished -- the load balancer sends traffic to a pod before it can serve, causing errors/timeouts for real users during every deploy and scale-up. (3) Liveness probes that are too aggressive (short timeout, checking heavy dependencies) restart pods that are merely under load, reducing capacity exactly when you need it and amplifying the overload. The correct design: liveness should be a CHEAP, LOCAL check that only fails when the process is genuinely unrecoverable (never call external dependencies from it); readiness should reflect the FULL ability to serve, including warmup and critical dependencies, and is allowed to flap. Slow-starting apps additionally use a STARTUP probe so liveness doesn't fire during a long boot. The principle: restart is the remedy for a broken process; rotation-removal is the remedy for a temporarily-unable one -- and treating those two remedies as interchangeable is what breaks.",
         tags=["liveness","readiness","health-check","crash-loop","why"],
         example="A model server takes 90s to load weights and depends on a feature store: liveness is a trivial '/healthz returns 200' (so it isn't killed mid-load), while readiness returns 503 until weights are loaded AND the feature store is reachable -- so it joins the LB only when truly serviceable; wiring the feature-store check into liveness instead would crash-loop every pod during a feature-store blip."),
    dict(cat="conceptual", title="Why can R-squared be negative, and what does that tell you about a model?",
         answer="R^2 is defined as 1 - SS_res/SS_tot, where SS_res = sum of squared residuals of the MODEL (sum (y_i - pred_i)^2) and SS_tot = sum of squared deviations from the MEAN of y (sum (y_i - ybar)^2). SS_tot is exactly the residual sum of squares you'd get from the simplest possible 'model': always predict the mean of y, ignoring the inputs entirely. So R^2 is really a COMPARISON: it measures how much your model reduces squared error RELATIVE TO just predicting the mean. If the model is perfect, SS_res=0 and R^2=1. If the model does exactly as well as predicting the mean, SS_res=SS_tot and R^2=0. And crucially, if the model does WORSE than predicting the mean -- SS_res > SS_tot -- then SS_res/SS_tot > 1 and R^2 goes NEGATIVE. This is not a bug; it's information. On TRAINING data fit by ordinary least squares with an intercept, R^2 is mathematically guaranteed to be in [0,1] because OLS explicitly minimizes SS_res and can always at least match the mean. But R^2 can and does go negative in the situations that matter most: (1) evaluating on a TEST/holdout set, where a model that overfit the training data can predict worse than the test-set mean -- a strong signal of overfitting or distribution shift; (2) a badly MISSPECIFIED model or one fit without an intercept; (3) using a model trained on one distribution to predict another. So a negative R^2 is a red flag that says: 'you would have been better off ignoring your features and just predicting the average.' It typically indicates severe overfitting, a broken model, data leakage in the wrong direction, or a train/test mismatch -- and it's a reason to distrust the model rather than a mere low score. This is also why R^2 alone can mislead: it's relative to the variance of THIS dataset (a high-variance target inflates it, a low-variance one deflates it), so pair it with absolute error metrics (RMSE/MAE) and check it on held-out data.",
         tags=["r2-score","overfitting","model-evaluation","negative-r2","why"],
         example="A degree-15 polynomial fit to 20 training points scores R^2=0.99 on train but on a fresh test set its wild extrapolations give SS_res far above the test variance, yielding R^2=-3.2 -- telling you the model is worse than a constant mean predictor and has badly overfit."),
    dict(cat="behavioral", title="STAR: Raising the bar on hiring or quality (Hire and Develop the Best / Insist on Highest Standards)",
         answer="Amazon LPs: HIRE AND DEVELOP THE BEST (raise the performance bar with every hire/promotion, recognize exceptional talent, develop others) and INSIST ON THE HIGHEST STANDARDS (continually raise the bar, drive quality up, ensure defects don't get sent down the line). Show you improved a bar -- interview quality or engineering quality -- and the durable effect.",
         tags=["behavioral","star","highest-standards","hire-and-develop","amazon-lp"],
         example="SITUATION: Our team's code reviews had become rubber-stamps -- LGTMs within minutes, and defects were slipping to production because reviewers skimmed. TASK: As a senior engineer I wanted to raise the quality bar without turning reviews into a bottleneck people resented. ACTION: I first modeled it myself: I wrote thorough, kind reviews with concrete suggestions and rationale, and I authored a lightweight review checklist (tests present, edge cases, error handling, observability) so the bar was explicit rather than a matter of mood. I introduced a 'no self-merge for non-trivial changes' norm and paired with two junior engineers to teach them how to review well -- not just spot bugs but mentor authors. For a recurring class of defect (unhandled nulls from an upstream service) I added a lint rule so the bar was enforced automatically, keeping human review for judgment. RESULT: Escaped defects in that area dropped noticeably over the next two quarters, review turnaround stayed under a day because the checklist made reviews focused, and the two juniors became trusted reviewers others sought out -- one was promoted partly on that growth. The bar rose AND the team's overall skill rose, which is the durable win: quality became a habit and a teaching mechanism, not a gate one person enforced."),
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

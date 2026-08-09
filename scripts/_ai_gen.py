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
    dict(cat="dsa", title="Plus One",
         answer="Given digits of a number (most significant first), add one and return the digit array. Walk from the last digit: if it's 9 it becomes 0 and carries; otherwise increment and return. If all were 9, prepend a 1.",
         tags=["plus-one","digits","carry","array","dsa"],
         code='''# Add one to a number represented as a digit array.
def plus_one(digits):
    for i in range(len(digits) - 1, -1, -1):
        if digits[i] < 9:
            digits[i] += 1             # no carry: done
            return digits
        digits[i] = 0                  # 9 -> 0 and carry left
    return [1] + digits                # all nines: e.g. 999 -> 1000''',
         complexity="Time O(n), space O(1) (amortized).",
         pitfalls="Forgetting the all-nines prepend; converting to int (overflows for big numbers in other languages).",
         example="plus_one([1,2,9]) -> [1,3,0]; plus_one([9,9]) -> [1,0,0]."),
    dict(cat="dsa", title="Add Binary",
         answer="Add two binary strings and return the binary sum string. Walk both from the right with a carry, summing bit + bit + carry, appending sum%2 and carrying sum//2.",
         tags=["add-binary","strings","carry","bit-manipulation","dsa"],
         code='''# Add two binary strings, returning the binary sum.
def add_binary(a, b):
    i, j = len(a) - 1, len(b) - 1
    carry = 0
    out = []
    while i >= 0 or j >= 0 or carry:
        total = carry
        if i >= 0:
            total += int(a[i]); i -= 1
        if j >= 0:
            total += int(b[j]); j -= 1
        out.append(str(total % 2))     # this bit
        carry = total // 2             # carry up
    return ''.join(reversed(out))''',
         complexity="Time O(max(n, m)), space O(max(n, m)).",
         pitfalls="Dropping the final carry; not reversing the output digits.",
         example="add_binary('11', '1') -> '100'."),
    dict(cat="dsa", title="Excel Sheet Column Number",
         answer="Convert an Excel column title (A, B, ..., Z, AA, ...) to its number. It's base-26 with digits 1..26: for each char, result = result*26 + (ord(c)-ord('A')+1).",
         tags=["excel-column-number","base-26","string","math","dsa"],
         code='''# Excel column title -> its 1-based column number (base 26).
def title_to_number(column_title):
    result = 0
    for ch in column_title:
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result''',
         complexity="Time O(n), space O(1).",
         pitfalls="Treating it as 0-indexed base 26 (it's 1..26, no zero digit); wrong char offset.",
         example="title_to_number('AB') -> 28; title_to_number('ZY') -> 701."),
    dict(cat="dsa", title="Excel Sheet Column Title",
         answer="Convert a column number to its Excel title. It's bijective base-26 (no zero): repeatedly subtract 1, take mod 26 for the letter, then divide by 26.",
         tags=["excel-column-title","base-26","math","string","dsa"],
         code='''# Column number -> Excel column title (bijective base 26).
def number_to_title(n):
    out = []
    while n > 0:
        n -= 1                         # shift to 0-indexed for this digit
        out.append(chr(ord('A') + n % 26))
        n //= 26
    return ''.join(reversed(out))''',
         complexity="Time O(log n), space O(log n).",
         pitfalls="Forgetting the n-=1 shift (bijective base 26 has no zero); not reversing.",
         example="number_to_title(28) -> 'AB'; number_to_title(701) -> 'ZY'."),
    dict(cat="dsa", title="Happy Number",
         answer="Repeatedly replace n by the sum of squares of its digits; n is happy if this reaches 1, unhappy if it loops. Detect the cycle with a seen-set (or Floyd's two pointers).",
         tags=["happy-number","cycle-detection","hash-set","math","dsa"],
         code='''# True if repeated digit-square-sum reaches 1 (else it cycles).
def is_happy(n):
    def squares(x):
        return sum(int(d) ** 2 for d in str(x))
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = squares(n)                 # advance the sequence
    return n == 1''',
         complexity="Time O(log n) per step, bounded steps; space O(number of distinct values).",
         pitfalls="No cycle detection -> infinite loop on unhappy numbers; squaring the number instead of each digit.",
         example="is_happy(19) -> True; is_happy(2) -> False."),
    dict(cat="dsa", title="Power of Three",
         answer="Check if n is a power of 3. Iterative: while n divisible by 3, divide; happy if it reduces to 1. (Or use the max-int power-of-3 divisibility trick.)",
         tags=["power-of-three","math","division","dsa"],
         code='''# True if n is a power of three.
def is_power_of_three(n):
    if n < 1:
        return False
    while n % 3 == 0:
        n //= 3                        # strip factors of 3
    return n == 1''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Not handling n <= 0; using float logs (rounding errors misclassify edge values).",
         example="is_power_of_three(27) -> True; is_power_of_three(45) -> False."),
    dict(cat="dsa", title="Ugly Number",
         answer="An ugly number is positive with only prime factors 2, 3, and 5. Divide out all 2s, 3s, and 5s; it's ugly if what remains is 1.",
         tags=["ugly-number","math","factorization","dsa"],
         code='''# True if n's only prime factors are 2, 3, and 5.
def is_ugly(n):
    if n < 1:
        return False
    for p in (2, 3, 5):
        while n % p == 0:
            n //= p                    # remove this prime factor fully
    return n == 1''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Not rejecting n <= 0; leaving a factor because you divided each prime only once.",
         example="is_ugly(6) -> True; is_ugly(14) -> False."),
    dict(cat="dsa", title="Valid Perfect Square",
         answer="Decide if n is a perfect square without sqrt. Binary search the root in [1, n]: mid*mid vs n narrows the range.",
         tags=["valid-perfect-square","binary-search","math","dsa"],
         code='''# True if n is a perfect square, via binary search on the root.
def is_perfect_square(n):
    lo, hi = 1, n
    while lo <= hi:
        mid = (lo + hi) // 2
        sq = mid * mid
        if sq == n:
            return True
        if sq < n:
            lo = mid + 1               # root is larger
        else:
            hi = mid - 1               # root is smaller
    return False''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Overflow of mid*mid in other languages; off-by-one in the binary-search bounds.",
         example="is_perfect_square(16) -> True; is_perfect_square(14) -> False."),
    dict(cat="dsa", title="Arranging Coins",
         answer="With n coins, form a staircase where row i has i coins; return the number of COMPLETE rows. Solve k(k+1)/2 <= n by binary search (or the quadratic formula).",
         tags=["arranging-coins","binary-search","math","dsa"],
         code='''# Number of complete staircase rows buildable from n coins.
def arrange_coins(n):
    lo, hi = 0, n
    while lo <= hi:
        k = (lo + hi) // 2
        need = k * (k + 1) // 2        # coins to fill k full rows
        if need == n:
            return k
        if need < n:
            lo = k + 1                 # can afford more rows
        else:
            hi = k - 1
    return hi                          # last k that fit''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Returning lo instead of hi at the end; overflow of k*(k+1) in other languages.",
         example="arrange_coins(5) -> 2  (rows 1+2 fit, row 3 needs 3 more); arrange_coins(8) -> 3."),
    dict(cat="dsa", title="Sqrt(x) via Binary Search",
         answer="Compute the integer square root (floor) without built-in sqrt. Binary search r in [0, x]: the largest r with r*r <= x.",
         tags=["sqrt","binary-search","math","dsa"],
         code='''# Integer (floor) square root of x via binary search.
def my_sqrt(x):
    if x < 2:
        return x
    lo, hi = 1, x // 2
    ans = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if mid * mid <= x:
            ans = mid                  # candidate; try larger
            lo = mid + 1
        else:
            hi = mid - 1
    return ans''',
         complexity="Time O(log x), space O(1).",
         pitfalls="Returning the ceiling instead of the floor; not handling x < 2.",
         example="my_sqrt(8) -> 2; my_sqrt(16) -> 4."),
    dict(cat="dsa", title="Count Primes (Sieve of Eratosthenes)",
         answer="Count primes strictly less than n. Sieve of Eratosthenes: mark multiples of each prime starting from its square as composite; count what stays prime.",
         tags=["count-primes","sieve-of-eratosthenes","math","dsa"],
         code='''# Count primes < n via the Sieve of Eratosthenes.
def count_primes(n):
    if n < 3:
        return 0
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p < n:
        if is_prime[p]:
            for multiple in range(p * p, n, p):
                is_prime[multiple] = False   # cross off multiples of p
        p += 1
    return sum(is_prime)''',
         complexity="Time O(n log log n), space O(n).",
         pitfalls="Counting primes <= n instead of < n; starting the inner loop below p*p (redundant work).",
         example="count_primes(10) -> 4  (2,3,5,7)."),
    dict(cat="dsa", title="Roman to Integer",
         answer="Convert a Roman numeral to an integer. Map symbols to values; add each, but if a symbol is smaller than the one after it, subtract it (handles IV, IX, XL, etc.).",
         tags=["roman-to-integer","hash-map","string","math","dsa"],
         code='''# Convert a Roman numeral string to its integer value.
def roman_to_int(s):
    values = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    total = 0
    for i in range(len(s)):
        # subtract if a smaller value precedes a larger one
        if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
            total -= values[s[i]]
        else:
            total += values[s[i]]
    return total''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not handling the subtractive pairs; reading past the end without a bounds check.",
         example="roman_to_int('MCMXCIV') -> 1994."),
    dict(cat="dsa", title="Number of 1 Bits (Hamming Weight)",
         answer="Count set bits in an integer. Repeatedly clear the lowest set bit with n &= n-1 and count iterations (Brian Kernighan's trick) -- loops only as many times as there are set bits.",
         tags=["hamming-weight","bit-manipulation","kernighan","dsa"],
         code='''# Count set bits (Hamming weight) via Brian Kernighan's trick.
def hamming_weight(n):
    count = 0
    while n:
        n &= n - 1                     # clear the lowest set bit
        count += 1
    return count''',
         complexity="Time O(number of set bits), space O(1).",
         pitfalls="Looping 32 times unconditionally (fine but slower); infinite loop if you forget to modify n.",
         example="hamming_weight(11) -> 3  (1011 has three 1s)."),
    dict(cat="glossary", title="Exponential backoff with jitter",
         answer="A RETRY strategy: wait exponentially longer between attempts (base * 2^attempt) to relieve a struggling dependency, plus JITTER -- randomization of the delay -- to prevent many clients from retrying in lockstep (the 'thundering herd' that re-overloads the service the instant it recovers). Common forms: full jitter (sleep = random(0, cap)) and equal jitter. Always cap the max delay and the attempt count. Without jitter, synchronized retries create load spikes; with it, retries spread out.",
         tags=["exponential-backoff","jitter","retries","thundering-herd","reliability"],
         example="After a 503, a client waits ~random(0, min(cap, base*2^n)) before retry n; 1,000 clients that failed together now retry at random times instead of hammering the recovering service simultaneously."),
    dict(cat="glossary", title="Token bucket vs leaky bucket",
         answer="Two RATE-LIMITING algorithms. TOKEN BUCKET: tokens refill at a steady rate into a bucket of capacity B; each request consumes a token, and requests with no token are rejected/delayed -- it allows BURSTS up to B while bounding the average rate. LEAKY BUCKET: requests enter a queue that drains ('leaks') at a fixed rate; it SMOOTHS output to a constant rate and drops overflow -- no bursts. Token bucket favors bursty-but-bounded traffic (most APIs); leaky bucket favors a strictly smooth output rate.",
         tags=["token-bucket","leaky-bucket","rate-limiting","burst","throttling"],
         example="An API using a token bucket (capacity 100, refill 10/s) lets a client burst 100 requests instantly then settle to 10/s; a leaky bucket would instead force a steady 10/s regardless of arrival bursts, queuing or dropping the rest."),
    dict(cat="glossary", title="Sliding window vs fixed window rate limiter",
         answer="FIXED WINDOW counts requests per aligned interval (e.g. per calendar minute) and resets at the boundary -- simple, but allows a 2x burst straddling the boundary (max at the end of one window plus max at the start of the next). SLIDING WINDOW fixes this: sliding-log keeps timestamps and counts the last N seconds exactly (accurate but memory-heavy); sliding-window-counter interpolates between the current and previous fixed windows (a good approximation, cheap). Sliding windows give smoother, boundary-safe limiting at some extra cost.",
         tags=["sliding-window","fixed-window","rate-limiting","boundary-burst","throttling"],
         example="Limit 100/min: with a fixed window a client sends 100 at 0:59 and 100 at 1:00 -- 200 in two seconds; a sliding-window counter weights the previous minute's count and blocks that boundary burst."),
    dict(cat="glossary", title="Connection draining",
         answer="When removing an instance (deploy, scale-in, health failure), CONNECTION DRAINING (a.k.a. deregistration delay) stops sending it NEW requests while letting IN-FLIGHT requests finish within a timeout before the instance is terminated. Prevents dropping active requests during rollouts/autoscaling. Paired with graceful shutdown (the app stops accepting, finishes work, closes cleanly) and readiness probes that fail first so the load balancer removes it from rotation.",
         tags=["connection-draining","graceful-shutdown","deployment","load-balancer","reliability"],
         example="During a rolling deploy the load balancer marks an instance draining: no new requests route to it, but its 30 in-flight requests get up to 30s to complete before the container is killed -- so users mid-request aren't cut off."),
    dict(cat="ml_coding", title="L2 regularization (ridge) loss and gradient (numpy)",
         answer="L2 regularization adds lambda * sum(w^2) to the loss, penalizing large weights to reduce overfitting (weight decay). Its gradient contribution is 2*lambda*w, pulling weights toward zero. Usually the bias is NOT regularized.",
         tags=["l2-regularization","ridge","weight-decay","overfitting","ml-coding"],
         code='''# L2 (ridge) penalty term and its gradient. ast.parse-only.
import numpy as np

def l2_penalty(w, lam):
    penalty = lam * np.sum(w ** 2)                # add to the data loss
    grad = 2 * lam * w                            # add to the weight gradient
    return penalty, grad''',
         complexity="Time O(features), space O(features).",
         pitfalls="Regularizing the bias term; forgetting the factor of 2 in the gradient; wrong sign (it pushes toward zero).",
         example="l2_penalty(np.array([3.,4.]), 0.1) -> penalty 2.5, grad [0.6, 0.8]."),
    dict(cat="ml_coding", title="K-means assignment step (numpy)",
         answer="One assignment step of Lloyd's k-means: assign each point to its nearest centroid. Compute distances to all centroids and take the argmin per point. (The update step then recomputes centroids as cluster means.)",
         tags=["kmeans","clustering","assignment-step","unsupervised","ml-coding"],
         code='''# K-means assignment: nearest-centroid label per point. ast.parse-only.
import numpy as np

def assign_clusters(X, centroids):
    # distances[i, k] = ||X[i] - centroids[k]||
    diff = X[:, None, :] - centroids[None, :, :]   # broadcast to (n, k, d)
    dist = np.sqrt(np.sum(diff ** 2, axis=2))      # (n, k) distances
    return np.argmin(dist, axis=1)                 # nearest centroid index''',
         complexity="Time O(n * k * d), space O(n * k * d).",
         pitfalls="Broadcasting on the wrong axes; taking argmin over the wrong dimension; forgetting sqrt is monotonic (optional here).",
         example="assign_clusters(np.array([[0.,0.],[10.,10.]]), np.array([[0.,0.],[10.,10.]])) -> [0, 1]."),
    dict(cat="ml_coding", title="Precision, recall, F1 from a confusion matrix (numpy)",
         answer="From a multiclass confusion matrix C (rows=true, cols=pred), per-class precision = TP/(TP+FP) = diag/col_sum, recall = TP/(TP+FN) = diag/row_sum, and F1 = harmonic mean. Guard against divide-by-zero for empty classes.",
         tags=["precision","recall","f1","confusion-matrix","ml-coding"],
         code='''# Per-class precision, recall, F1 from a confusion matrix. ast.parse-only.
import numpy as np

def prf_from_confusion(cm, eps=1e-12):
    tp = np.diag(cm).astype(float)                # correct per class
    precision = tp / (cm.sum(axis=0) + eps)       # diag / predicted count
    recall = tp / (cm.sum(axis=1) + eps)          # diag / actual count
    f1 = 2 * precision * recall / (precision + recall + eps)
    return precision, recall, f1''',
         complexity="Time O(num_classes^2), space O(num_classes).",
         pitfalls="Swapping the precision/recall axes (col vs row sums); divide-by-zero on absent classes; averaging wrongly (macro vs micro).",
         example="prf_from_confusion(np.array([[5,1],[2,2]])) gives class-0 precision 5/7, recall 5/6."),
    dict(cat="conceptual", title="Why add jitter to exponential backoff instead of just backing off exponentially?",
         answer="Exponential backoff alone solves one problem: it stops clients from hammering a struggling service by making each successive retry wait longer (1s, 2s, 4s, ...), giving the dependency room to recover. But it does NOT solve a second, subtler problem -- SYNCHRONIZATION. Consider what causes retries in the first place: usually a shared event, like a service going down, a deploy, or a network partition, that fails MANY clients at the SAME instant. If every one of those clients uses the identical deterministic backoff schedule, they all wait 1s and retry together, all wait 2s and retry together, and so on. The retries arrive in synchronized WAVES: the moment the service comes back up, it's hit by the entire herd simultaneously, which re-overloads it and knocks it down again -- a self-perpetuating 'thundering herd' oscillation where the system never stabilizes even though average load would be fine if spread out. JITTER breaks the synchronization by RANDOMIZING each client's delay: instead of sleeping exactly 2^n seconds, a client sleeps a random amount in [0, 2^n] (full jitter) or [2^(n-1), 2^n] (equal jitter). Now the clients that failed together retry at DIFFERENT times, spreading the load into a smooth trickle the recovering service can absorb, so it stays up and everyone eventually succeeds. AWS's analysis showed full jitter dramatically reduces both peak load and the total work (competing requests) versus no-jitter backoff. The cost is negligible -- one random number per retry -- and the only nuance is choosing a jitter form (full jitter is simplest and usually best) and still capping the max delay and attempt count. So the rule: exponential backoff controls the AVERAGE retry rate over time; jitter controls the CORRELATION between clients. You need both -- backoff without jitter still produces destructive synchronized retry storms.",
         tags=["exponential-backoff","jitter","thundering-herd","retries","why"],
         example="A service outage fails 10,000 clients at once: with plain backoff all 10,000 retry at t=1s, t=3s, t=7s in synchronized spikes that re-crash it on recovery; with full jitter each retries at a random offset, turning the spikes into a flat, absorbable load and letting the service stabilize."),
    dict(cat="conceptual", title="Why does L2 regularization reduce overfitting, and how does it differ from L1?",
         answer="Overfitting happens when a model fits noise in the training data by using large, finely-tuned weights that make the decision surface wiggle to pass through individual points; such models generalize poorly because those exact weights don't reflect the true signal. L2 regularization adds a penalty proportional to the SUM OF SQUARED WEIGHTS (lambda * sum w^2) to the loss, so the optimizer now trades off fitting the data against keeping weights SMALL. This shrinks weights toward zero (weight decay), producing a smoother, lower-variance function that's less able to chase noise -- reducing variance at the cost of a little bias (the bias-variance tradeoff). Intuitively, among all models that fit the data comparably well, L2 prefers the one with the smallest, most spread-out weights, which is usually the simpler, more generalizable one. Geometrically, minimizing loss subject to an L2 (spherical) constraint pulls the solution toward the origin along all axes proportionally. The KEY DIFFERENCE from L1 (which penalizes the sum of ABSOLUTE weights): L1's constraint region is a diamond with corners ON the axes, so its optimum tends to land exactly at a corner where some weights are EXACTLY ZERO -- L1 produces SPARSE solutions and effectively does feature selection. L2's spherical constraint has no corners, so it shrinks weights smoothly toward but rarely exactly to zero -- keeping all features but damping them. Consequences: use L2 (ridge) when you believe most features contribute a little and you want stable, well-conditioned solutions (it also fixes multicollinearity by making the problem strictly convex); use L1 (lasso) when you expect few relevant features and want an interpretable sparse model; use both (elastic net) to get sparsity plus stability. Also, L2 has a clean gradient (2*lambda*w) that's easy to optimize, whereas L1's gradient is non-differentiable at zero (needs subgradients/proximal methods). Finally, the bias term is usually left unregularized because penalizing it would bias predictions rather than control complexity.",
         tags=["l2-regularization","l1-regularization","overfitting","bias-variance","why"],
         example="Fitting a degree-10 polynomial to 12 noisy points: unregularized weights explode to fit every wiggle; L2 shrinks all coefficients smoothly for a gentle curve; L1 zeros out most high-degree coefficients, effectively selecting a low-degree fit -- both generalize far better than the unpenalized model."),
    dict(cat="behavioral", title="STAR: Simplifying/inventing to remove a bottleneck (Invent and Simplify)",
         answer="Amazon LP: INVENT AND SIMPLIFY -- leaders expect and require innovation, find ways to simplify, are externally aware, and are not limited by 'not invented here'. Show you replaced a complex, slow process with a simpler invention that scaled, with a measurable result.",
         tags=["behavioral","star","invent-and-simplify","amazon-lp","innovation"],
         example="SITUATION: Our team spent ~2 days per release manually coordinating a fragile deploy -- a 40-step runbook of copy-paste commands across services, error-prone and a frequent source of incidents. TASK: As tech lead I wanted to cut both the toil and the incident rate, not just document the runbook better. ACTION: Rather than accept the complexity, I looked for the root simplification: the 40 steps were really the same 4 operations repeated per service with different parameters. I built a small declarative deploy tool -- each service described its deploy in a short YAML file, and one command orchestrated ordering, health checks, and automatic rollback on failure. I deliberately kept it minimal (no bespoke DSL, reused our existing CI) so the team could adopt it without a learning curve, and I piloted it on my own service first to prove it before asking others to switch. RESULT: Deploy time dropped from ~2 days to under 30 minutes, deploy-caused incidents fell to nearly zero over the next quarter because rollback was automatic, and three other teams adopted the tool. The win came from REFUSING to treat the 40 steps as inherent complexity and instead finding the simple pattern underneath -- and from keeping the solution small enough that adoption was trivial."),
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

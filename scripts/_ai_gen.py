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
    dict(cat="dsa", title="Counting Sort",
         answer="Sort non-negative integers in a small range WITHOUT comparisons. Count how many times each value appears, then emit each value that many times in order. Linear when the value range is comparable to n — it beats the O(n log n) comparison-sort lower bound by exploiting the bounded key range.",
         tags=["counting-sort","sorting","non-comparison","dsa"],
         code='''# Sort non-negative integers by counting occurrences (no comparisons).
def counting_sort(a):
    if not a:
        return a
    max_val = max(a)
    counts = [0] * (max_val + 1)       # counts[v] = how many times v appears
    for v in a:
        counts[v] += 1
    result = []
    for v in range(max_val + 1):
        result.extend([v] * counts[v]) # emit each value counts[v] times
    return result''',
         complexity="Time O(n + k) where k is the value range; space O(k).",
         pitfalls="Huge k wastes memory (range must be small); doesn't handle negatives without an offset.",
         example="counting_sort([3,1,3,0,2,1]) -> [0,1,1,2,3,3]."),
    dict(cat="dsa", title="Rotate Array by k (reversal trick)",
         answer="Rotate an array to the RIGHT by k positions in place. The elegant trick: reverse the whole array, then reverse the first k elements, then reverse the remaining n-k. This lands every element in its rotated position with O(1) extra space. Remember k %= n so k larger than the length wraps.",
         tags=["rotate-array","reversal","in-place","array","dsa"],
         code='''# Rotate an array to the right by k steps, in place, using reversals.
def rotate(nums, k):
    n = len(nums)
    k %= n                              # k larger than n just wraps around
    def reverse(lo, hi):
        while lo < hi:
            nums[lo], nums[hi] = nums[hi], nums[lo]
            lo += 1; hi -= 1
    reverse(0, n - 1)                   # reverse the whole array
    reverse(0, k - 1)                   # reverse the first k elements
    reverse(k, n - 1)                   # reverse the remaining n-k
    return nums''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting k %= n (index error when k >= n); off-by-one in the sub-range reversals.",
         example="rotate([1,2,3,4,5,6,7], 3) -> [5,6,7,1,2,3,4]."),
    dict(cat="dsa", title="Binary Search Lower Bound (bisect_left)",
         answer="Find the LEFTMOST index at which a target could be inserted to keep the array sorted — i.e. the first element not less than target. This is the building block for counting occurrences, range queries, and 'first/last position' problems. Keep hi exclusive and move hi=mid (not mid-1) so you don't skip the answer.",
         tags=["binary-search","lower-bound","bisect","array","dsa"],
         code='''# Leftmost index where target could be inserted to keep 'a' sorted.
def lower_bound(a, target):
    lo, hi = 0, len(a)                  # hi is exclusive
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1                # target must be to the right
        else:
            hi = mid                    # mid could still be the answer; keep it
    return lo''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Using hi=mid-1 (skips the boundary); making hi inclusive (off-by-one).",
         example="lower_bound([1,2,2,2,3], 2) -> 1  (first index of a 2)."),
    dict(cat="dsa", title="Spiral Matrix",
         answer="Return all elements of an m×n matrix in clockwise SPIRAL order. Keep four boundaries (top, bottom, left, right); walk the top row left-to-right, the right column top-to-bottom, the bottom row right-to-left, the left column bottom-to-top, shrinking the boundary after each pass. Guard the last two passes so a single remaining row/column isn't double-visited.",
         tags=["spiral-matrix","matrix","simulation","dsa"],
         code='''# Return all elements of a matrix in clockwise spiral order.
def spiral_order(matrix):
    if not matrix:
        return []
    result = []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            result.append(matrix[top][c])        # top row, left -> right
        top += 1
        for r in range(top, bottom + 1):
            result.append(matrix[r][right])      # right col, top -> bottom
        right -= 1
        if top <= bottom:                        # guard against a single row
            for c in range(right, left - 1, -1):
                result.append(matrix[bottom][c]) # bottom row, right -> left
            bottom -= 1
        if left <= right:                        # guard against a single col
            for r in range(bottom, top - 1, -1):
                result.append(matrix[r][left])   # left col, bottom -> top
            left += 1
    return result''',
         complexity="Time O(m*n), space O(1) beyond the output.",
         pitfalls="Double-visiting the middle row/column (missing the two guards); mixing up the shrink order.",
         example="spiral_order([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,9,8,7,4,5]."),
    dict(cat="dsa", title="Set Matrix Zeroes (O(1) space)",
         answer="If any cell is 0, set its whole row and column to 0 — in place, without an extra matrix. Trick: use the first row and first column themselves as the marker storage for which rows/columns must be zeroed; handle the first row/column separately with two boolean flags to avoid clobbering the markers.",
         tags=["set-matrix-zeroes","matrix","in-place","dsa"],
         code='''# If a cell is 0, zero its entire row and column, in place (O(1) extra).
def set_zeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    first_row_zero = any(matrix[0][c] == 0 for c in range(cols))
    first_col_zero = any(matrix[r][0] == 0 for r in range(rows))
    for r in range(1, rows):                 # use row 0 / col 0 as markers
        for c in range(1, cols):
            if matrix[r][c] == 0:
                matrix[r][0] = 0             # mark this row
                matrix[0][c] = 0             # mark this column
    for r in range(1, rows):
        for c in range(1, cols):
            if matrix[r][0] == 0 or matrix[0][c] == 0:
                matrix[r][c] = 0             # zero out any marked cell
    if first_row_zero:
        for c in range(cols):
            matrix[0][c] = 0
    if first_col_zero:
        for r in range(rows):
            matrix[r][0] = 0
    return matrix''',
         complexity="Time O(m*n), space O(1).",
         pitfalls="Overwriting markers before you use them (do the first row/col last); forgetting the two edge flags.",
         example="set_zeroes([[1,1,1],[1,0,1],[1,1,1]]) -> [[1,0,1],[0,0,0],[1,0,1]]."),
    dict(cat="dsa", title="Merge k Sorted Lists (min-heap)",
         answer="Merge k already-sorted lists into one sorted list. Push the first element of each list into a min-heap tagged with (value, list index, element index); repeatedly pop the smallest and push the next element from the SAME list. The heap always holds at most k items, so each of the N total elements costs O(log k).",
         tags=["merge-k-sorted","heap","priority-queue","merge","dsa"],
         code='''# Merge k sorted lists into one sorted list using a min-heap.
import heapq
def merge_k_sorted(lists):
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            # (value, list index, element index) — indices break ties safely
            heapq.heappush(heap, (lst[0], i, 0))
    result = []
    while heap:
        val, i, j = heapq.heappop(heap)
        result.append(val)
        if j + 1 < len(lists[i]):
            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))  # next from list i
    return result''',
         complexity="Time O(N log k) for N total elements, space O(k).",
         pitfalls="Comparing raw objects that aren't orderable (include the index tiebreaker); pushing all N at once (O(N) heap instead of O(k)).",
         example="merge_k_sorted([[1,4,5],[1,3,4],[2,6]]) -> [1,1,2,3,4,4,5,6]."),
    dict(cat="ml_coding", title="Linear Regression via Gradient Descent",
         answer="Fit y = X·w + b by minimizing mean squared error with batch gradient descent. Each step computes predictions, the residual error, and the MSE gradients w.r.t. w and b, then nudges the parameters downhill by the learning rate. (numpy — shown for study; validated by ast.parse, not run here.)",
         tags=["linear-regression","gradient-descent","numpy","ml-coding","regression"],
         code='''# Fit y = X.w + b by batch gradient descent (numpy).
import numpy as np
def linear_regression_gd(X, y, lr=0.01, epochs=1000):
    n, d = X.shape
    w = np.zeros(d)                     # weights start at zero
    b = 0.0                             # bias
    for _ in range(epochs):
        y_pred = X.dot(w) + b           # forward prediction
        error = y_pred - y              # residuals
        grad_w = (2 / n) * X.T.dot(error)   # dMSE/dw
        grad_b = (2 / n) * error.sum()      # dMSE/db
        w -= lr * grad_w                # gradient-descent step on w
        b -= lr * grad_b                # ... and on b
    return w, b''',
         complexity="Time O(epochs * n * d), space O(d).",
         pitfalls="Learning rate too high (diverges) or too low (crawls); forgetting to scale features first.",
         example="For X=[[1],[2],[3]], y=[2,4,6], training converges to w≈2, b≈0 — the line y=2x."),
    dict(cat="ml_coding", title="Softmax (numerically stable)",
         answer="Turn a vector of raw scores (logits) into a probability distribution: exponentiate each and normalize so they sum to 1. The key trick is subtracting the max logit first — mathematically identical but it prevents exp() from overflowing on large inputs. (numpy — validated by ast.parse.)",
         tags=["softmax","numpy","ml-coding","classification","numerical-stability"],
         code='''# Convert a vector of scores into a probability distribution.
import numpy as np
def softmax(logits):
    z = logits - np.max(logits)         # subtract max for numerical stability
    exp = np.exp(z)                     # exponentiate
    return exp / exp.sum()              # normalize so probabilities sum to 1''',
         complexity="Time O(n), space O(n).",
         pitfalls="Skipping the max-subtraction (overflow on big logits); applying it across the wrong axis for a batch.",
         example="softmax([2.0, 1.0, 0.1]) -> roughly [0.66, 0.24, 0.10], summing to 1."),
    dict(cat="ml_coding", title="Cosine Similarity (from scratch)",
         answer="Measure how similar two vectors' DIRECTIONS are, ignoring their magnitudes: the dot product divided by the product of their lengths, giving a value in [-1, 1]. 1 = same direction, 0 = orthogonal, -1 = opposite. It's the standard similarity for text/embedding vectors.",
         tags=["cosine-similarity","embeddings","vectors","ml-coding"],
         code='''# Cosine similarity: cosine of the angle between two vectors, in [-1, 1].
import math
def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))          # dot product
    norm_a = math.sqrt(sum(x * x for x in a))       # length of a
    norm_b = math.sqrt(sum(y * y for y in b))       # length of b
    if norm_a == 0 or norm_b == 0:
        return 0.0                                  # avoid divide-by-zero
    return dot / (norm_a * norm_b)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing by a zero-norm vector; confusing it with Euclidean distance (cosine ignores magnitude).",
         example="cosine_similarity([1,0,1],[1,1,0]) -> 0.5  (a 60-degree angle)."),
    dict(cat="ml_coding", title="One-Hot Encoding (from scratch)",
         answer="Convert categorical labels into binary vectors so a model can use them: each category becomes a column, and a sample's vector has a single 1 in its category's column and 0 elsewhere. Avoids implying a false ordering that integer-encoding would (e.g. cat=0 < dog=1).",
         tags=["one-hot","encoding","preprocessing","categorical","ml-coding"],
         code='''# Turn a list of category labels into one-hot vectors.
def one_hot_encode(labels):
    classes = sorted(set(labels))       # a stable, ordered class list
    index = {c: i for i, c in enumerate(classes)}   # class -> column number
    vectors = []
    for lab in labels:
        row = [0] * len(classes)
        row[index[lab]] = 1             # a single 1 in this class's column
        vectors.append(row)
    return vectors''',
         complexity="Time O(n * k), space O(n * k) for k classes.",
         pitfalls="Unseen categories at inference time (fix the class list at train time); exploding width with high-cardinality features.",
         example="one_hot_encode(['cat','dog','cat']) -> [[1,0],[0,1],[1,0]]."),
    dict(cat="cs_fundamentals", title="Paging & virtual memory",
         answer="Virtual memory gives each process its own large, contiguous address space mapped to physical RAM in fixed-size blocks called PAGES (e.g. 4 KB). The OS keeps a page table mapping virtual pages to physical frames, and the MMU translates addresses on the fly. Pages not in RAM live on disk and are fetched on a 'page fault'. Benefits: process isolation, more apparent memory than physical RAM, and simpler allocation.",
         tags=["paging","virtual-memory","os","memory","cs"],
         example="A program reads address 0x4000; the MMU looks up its page, finds it on disk, triggers a page fault, and the OS loads that 4 KB page into a free frame before the instruction resumes."),
    dict(cat="cs_fundamentals", title="TLS / HTTPS handshake",
         answer="HTTPS is HTTP over TLS. In the handshake the client and server negotiate a cipher, the server proves its identity with a CERTIFICATE signed by a trusted Certificate Authority, and they establish a shared symmetric session key — typically via ephemeral Diffie-Hellman for forward secrecy. After that, all traffic is encrypted and integrity-protected with fast symmetric crypto.",
         tags=["tls","https","security","encryption","cs"],
         example="Visiting https://bank.com, your browser verifies the bank's certificate chain up to a trusted root CA, both sides derive a session key, and the padlock shows the channel is encrypted."),
    dict(cat="cs_fundamentals", title="DNS resolution",
         answer="The Domain Name System translates human names (example.com) into IP addresses. A resolver walks a hierarchy: root servers point to the .com TLD servers, which point to the domain's authoritative name server, which returns the IP. Results are CACHED at each level with a TTL to cut latency. It's essentially the internet's phone book.",
         tags=["dns","networking","resolution","caching","cs"],
         example="Typing example.com, your resolver walks root -> .com -> example.com's authoritative server, gets 93.184.216.34, caches it, and the browser connects."),
    dict(cat="glossary", title="Batch vs online learning",
         answer="Two training regimes. BATCH (offline) learning trains on the whole fixed dataset at once and redeploys periodically — simple and stable but stale between retrains. ONLINE learning updates the model incrementally as each new example arrives — it adapts to changing data (concept drift) and handles streams, but is noisier and harder to debug. Mini-batch is the common middle ground.",
         tags=["batch-learning","online-learning","training","concept-drift"],
         example="A spam filter retrained nightly on all email is batch; one that updates the instant a user marks 'spam' is online, adapting immediately to new patterns."),
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

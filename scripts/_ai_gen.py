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
    dict(cat="dsa", title="3Sum",
         answer="Find all UNIQUE triplets that sum to zero. Sort the array, then fix each element and use TWO POINTERS on the rest to find pairs summing to its negation. Sorting lets you move the pointers based on the running sum and skip duplicates cleanly. O(n^2).",
         tags=["3sum","two-pointers","sorting","array","dsa"],
         code='''# All unique triplets in nums that sum to zero.
def three_sum(nums):
    nums.sort()                       # sorting enables two pointers + dedup
    res = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]:
            continue                  # skip duplicate first elements
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:
                lo += 1               # need a bigger sum
            elif s > 0:
                hi -= 1               # need a smaller sum
            else:
                res.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                hi -= 1
                while lo < hi and nums[lo] == nums[lo-1]:
                    lo += 1           # skip duplicate second elements
    return res''',
         complexity="Time O(n^2), space O(1) extra (besides the output).",
         pitfalls="Not sorting first; forgetting to skip duplicates (returns repeated triplets).",
         example="three_sum([-1,0,1,2,-1,-4]) -> [[-1,-1,2],[-1,0,1]]."),
    dict(cat="dsa", title="Container With Most Water",
         answer="Given vertical line heights, find two lines that with the x-axis hold the most water. Two pointers at both ends: area = min(height[l], height[r]) * (r-l). Always move the SHORTER wall inward, because the water is bounded by the shorter side — moving the taller wall can never increase the area. O(n).",
         tags=["container-with-most-water","two-pointers","array","dsa"],
         code='''# Max water trapped between two vertical lines.
def max_area(height):
    lo, hi = 0, len(height) - 1
    best = 0
    while lo < hi:
        area = min(height[lo], height[hi]) * (hi - lo)
        best = max(best, area)
        if height[lo] < height[hi]:   # the shorter wall bounds the water
            lo += 1                   #   move it inward hoping for a taller one
        else:
            hi -= 1
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Moving the taller wall (never helps); summing heights instead of taking the min.",
         example="max_area([1,8,6,2,5,4,8,3,7]) -> 49."),
    dict(cat="dsa", title="Spiral Matrix",
         answer="Return all elements of an m x n matrix in spiral (clockwise) order. Keep four boundaries (top, bottom, left, right) and peel layers: top row L->R, right column T->B, bottom row R->L, left column B->T, shrinking the boundaries after each pass until they cross.",
         tags=["spiral-matrix","matrix","simulation","dsa"],
         code='''# Elements of an m x n matrix in spiral (clockwise) order.
def spiral_order(matrix):
    if not matrix:
        return []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    res = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1):          # top row, left -> right
            res.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):          # right column, top -> bottom
            res.append(matrix[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):   # bottom row, right -> left
                res.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):   # left column, bottom -> top
                res.append(matrix[r][left])
            left += 1
    return res''',
         complexity="Time O(m*n), space O(1) extra.",
         pitfalls="Re-traversing a single leftover row/column (the two extra if-checks prevent it).",
         example="spiral_order([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,9,8,7,4,5]."),
    dict(cat="dsa", title="Coin Change II (count ways)",
         answer="Count the number of DISTINCT ways to make an amount from coins (unlimited of each). Unbounded-knapsack DP: dp[a] = ways to make amount a. Put the COINS in the outer loop and amounts inner, so each combination is counted once (order doesn't matter): dp[a] += dp[a-coin].",
         tags=["coin-change-2","dp","unbounded-knapsack","dsa"],
         code='''# Number of distinct ways to make `amount` using coins (unlimited each).
def change(amount, coins):
    dp = [0] * (amount + 1)
    dp[0] = 1                         # one way to make 0: use no coins
    for coin in coins:                # coin in the OUTER loop -> combinations
        for a in range(coin, amount + 1):
            dp[a] += dp[a - coin]     # add the ways that finish by using `coin`
    return dp[amount]''',
         complexity="Time O(amount * #coins), space O(amount).",
         pitfalls="Swapping the loop order (then it counts permutations, not combinations); forgetting dp[0]=1.",
         example="change(5, [1,2,5]) -> 4 (5; 2+2+1; 2+1+1+1; 1+1+1+1+1)."),
    dict(cat="glossary", title="F-beta score",
         answer="A generalization of F1 that weights recall beta times as much as precision: F_beta = (1+beta^2) * P * R / (beta^2 * P + R). beta > 1 favours recall (e.g. F2), beta < 1 favours precision (e.g. F0.5). Use it when the two error types have unequal costs.",
         tags=["f-beta","f1","metrics"],
         example="For disease screening (missing a case is worse than a false alarm), use F2 to weight recall more than precision."),
    dict(cat="glossary", title="Data augmentation",
         answer="Artificially expanding training data with label-PRESERVING transformations — flips, crops, rotations, colour shifts for images; synonym swaps or back-translation for text. It reduces overfitting and improves generalization by showing the model more variety without new labeling.",
         tags=["data-augmentation","regularization","deep-learning"],
         example="Training an image classifier on 10k photos, random flips and crops effectively multiply the dataset and cut overfitting."),
    dict(cat="glossary", title="Early stopping",
         answer="Stopping training when the VALIDATION loss stops improving (and starts rising), rather than running a fixed number of epochs. It prevents overfitting by not letting the model keep memorizing the training set past its best generalization point; you keep the weights from the best epoch.",
         tags=["early-stopping","overfitting","training"],
         example="Validation loss bottoms out at epoch 30 then climbs; early stopping halts there and restores the epoch-30 weights."),
    dict(cat="glossary", title="Bag-of-words & TF-IDF",
         answer="Bag-of-words represents a document as counts of its words, ignoring order. TF-IDF weights each word by how often it appears in THIS document (term frequency) times how RARE it is across all documents (inverse document frequency) — so common words like 'the' get low weight and distinctive words get high weight. A classic text-feature baseline.",
         tags=["bag-of-words","tf-idf","nlp","features"],
         example="In a doc about 'photosynthesis', TF-IDF gives 'photosynthesis' a high weight (rare overall, frequent here) and 'the' near zero."),
    dict(cat="glossary", title="Zero-shot / few-shot / in-context learning",
         answer="Ways to get an LLM to do a task WITHOUT training. ZERO-SHOT gives just the instruction; FEW-SHOT adds a few examples in the prompt. Both are 'in-context learning' — the model adapts from the prompt alone, its weights unchanged. More examples usually help, up to the context-length limit.",
         tags=["zero-shot","few-shot","in-context-learning","llm"],
         example="Few-shot: show the model 3 'review -> sentiment' example pairs in the prompt, then a new review; it infers the pattern and labels it."),
    dict(cat="cs_fundamentals", title="Database index (B-tree)",
         answer="An INDEX is a data structure (usually a B-tree / B+ tree) that lets the database find rows by a column value WITHOUT scanning the whole table — turning O(n) lookups into O(log n). B-trees stay balanced and pack many keys per node (matching disk pages), so even billions of rows take only a few disk reads. Indexes speed reads but slow writes and use extra space.",
         tags=["index","b-tree","database","cs"],
         example="An index on users(email) makes 'find the user with this email' instant instead of scanning millions of rows."),
    dict(cat="cs_fundamentals", title="ACID transactions",
         answer="The guarantees of a reliable database transaction. ATOMICITY: all-or-nothing (a transfer fully happens or not at all). CONSISTENCY: it moves the DB from one valid state to another. ISOLATION: concurrent transactions don't interfere, as if run one at a time. DURABILITY: once committed, it survives crashes. SQL databases provide ACID; many NoSQL stores trade some of it for scale.",
         tags=["acid","transactions","database","cs"],
         example="A bank transfer debits A and credits B in one transaction — atomicity guarantees you never lose money in between if the server crashes."),
    dict(cat="cs_fundamentals", title="TCP 3-way handshake",
         answer="How a TCP connection is established before any data flows: the client sends SYN, the server replies SYN-ACK, the client sends ACK — now both sides agree on sequence numbers and a reliable, ordered connection is open. (Teardown uses a 4-way FIN/ACK exchange.)",
         tags=["tcp","handshake","networking","cs"],
         example="Opening a website: your browser and the server first do SYN -> SYN-ACK -> ACK, then the TLS handshake, then the HTTP request."),
    dict(cat="conceptual", title="Why does a database index speed up reads but slow down writes?",
         answer="An index is a SEPARATE sorted structure (a B-tree) that points into the table. On a READ, the DB walks that tree in O(log n) instead of scanning every row — a huge win. But on every INSERT/UPDATE/DELETE, the DB must also update EVERY index that involves the changed column, keeping each tree sorted and balanced — extra work per write, plus storage. So an index is a trade: add them for columns you filter, join, or sort on often, but don't index everything or writes crawl.",
         tags=["index","database","tradeoff","why"],
         example="Adding 5 indexes makes queries fast, but each insert now also updates 5 B-trees — a heavy-write table feels the drag."),
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

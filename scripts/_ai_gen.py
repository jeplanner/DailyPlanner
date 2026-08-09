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
    dict(cat="dsa", title="Pacific Atlantic Water Flow",
         answer="Cells with heights; water flows to a lower-or-equal neighbor. Find cells from which water can reach BOTH oceans (top/left = Pacific, bottom/right = Atlantic). Reverse the flow: DFS/BFS INWARD from each ocean's border cells (going to higher-or-equal neighbors); answer is the intersection of the two reachable sets.",
         tags=["pacific-atlantic","dfs","bfs","grid","multi-source","dsa"],
         code='''# Cells that can drain to both oceans (reverse flow from borders).
def pacific_atlantic(heights):
    if not heights:
        return []
    rows, cols = len(heights), len(heights[0])
    pacific, atlantic = set(), set()
    def dfs(r, c, visited, prev):
        if (r < 0 or r >= rows or c < 0 or c >= cols or
                (r, c) in visited or heights[r][c] < prev):
            return
        visited.add((r, c))              # water can climb from here to the ocean
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            dfs(r + dr, c + dc, visited, heights[r][c])
    for c in range(cols):
        dfs(0, c, pacific, heights[0][c])            # top row -> Pacific
        dfs(rows - 1, c, atlantic, heights[rows-1][c])  # bottom -> Atlantic
    for r in range(rows):
        dfs(r, 0, pacific, heights[r][0])            # left col -> Pacific
        dfs(r, cols - 1, atlantic, heights[r][cols-1])  # right -> Atlantic
    return sorted(pacific & atlantic)''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Simulating forward flow from every cell (too slow); using < instead of >= for the reverse climb.",
         example="pacific_atlantic([[1,2,2,3,5],[3,2,3,4,4],[2,4,5,3,1],[6,7,1,4,5],[5,1,1,2,4]]) includes (0,4),(1,3),(2,2),(3,0),(3,1),(4,0)."),
    dict(cat="dsa", title="Surrounded Regions",
         answer="Flip all 'O's fully surrounded by 'X' to 'X'; 'O's connected to a BORDER survive. Mark border-connected 'O's (DFS from edges), then flip everything else.",
         tags=["surrounded-regions","dfs","grid","flood-fill","dsa"],
         code='''# Capture regions of 'O' not connected to any border.
def solve(board):
    if not board:
        return board
    rows, cols = len(board), len(board[0])
    def mark(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != 'O':
            return
        board[r][c] = 'S'                # survives (border-connected)
        mark(r+1, c); mark(r-1, c); mark(r, c+1); mark(r, c-1)
    for r in range(rows):
        mark(r, 0); mark(r, cols - 1)    # left/right borders
    for c in range(cols):
        mark(0, c); mark(rows - 1, c)    # top/bottom borders
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == 'O':
                board[r][c] = 'X'        # surrounded -> capture
            elif board[r][c] == 'S':
                board[r][c] = 'O'        # restore survivor
    return board''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Flipping border-connected regions; not restoring the survivor marker.",
         example="solve([['X','X','X'],['X','O','X'],['X','X','X']]) -> the inner O becomes X (surrounded)."),
    dict(cat="dsa", title="01 Matrix",
         answer="For each cell, the distance to the nearest 0. MULTI-SOURCE BFS from all 0-cells at once, filling distances outward.",
         tags=["01-matrix","bfs","multi-source","grid","dsa"],
         code='''# Distance from each cell to the nearest 0 (multi-source BFS).
from collections import deque

def update_matrix(mat):
    rows, cols = len(mat), len(mat[0])
    dist = [[-1] * cols for _ in range(rows)]
    queue = deque()
    for r in range(rows):
        for c in range(cols):
            if mat[r][c] == 0:
                dist[r][c] = 0
                queue.append((r, c))     # all zeros are sources
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return dist''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="BFS from each 1 separately (too slow); not seeding ALL zeros before expanding.",
         example="update_matrix([[0,0,0],[0,1,0],[1,1,1]]) -> [[0,0,0],[0,1,0],[1,2,1]]."),
    dict(cat="dsa", title="Unique Paths II (with obstacles)",
         answer="Count paths from top-left to bottom-right moving only right/down, where some cells are blocked (1). DP grid: a blocked cell contributes 0 paths; otherwise dp[i][j] = dp[i-1][j] + dp[i][j-1].",
         tags=["unique-paths","dynamic-programming","grid","obstacles","dp","dsa"],
         code='''# Count right/down paths avoiding obstacles, DP.
def unique_paths_with_obstacles(grid):
    if not grid or grid[0][0] == 1:
        return 0
    rows, cols = len(grid), len(grid[0])
    dp = [[0] * cols for _ in range(rows)]
    dp[0][0] = 1
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                dp[i][j] = 0             # blocked: no paths through here
                continue
            if i > 0:
                dp[i][j] += dp[i-1][j]   # from above
            if j > 0:
                dp[i][j] += dp[i][j-1]   # from the left
    return dp[rows-1][cols-1]''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Not zeroing the start when it's blocked; adding neighbors through an obstacle cell.",
         example="unique_paths_with_obstacles([[0,0,0],[0,1,0],[0,0,0]]) -> 2."),
    dict(cat="dsa", title="Decode Ways",
         answer="Count ways to decode a digit string where 1->A ... 26->Z. DP: dp[i] = dp[i-1] if the single digit is valid (1-9) + dp[i-2] if the two-digit number is 10-26.",
         tags=["decode-ways","dynamic-programming","string","dp","dsa"],
         code='''# Count decodings of a digit string (1..26 -> A..Z), DP.
def num_decodings(s):
    if not s or s[0] == '0':
        return 0
    n = len(s)
    prev2, prev1 = 1, 1                  # dp[-1]=1, dp[0]=1
    for i in range(1, n):
        curr = 0
        if s[i] != '0':
            curr += prev1                # single digit 1-9
        two = int(s[i-1:i+1])
        if 10 <= two <= 26:
            curr += prev2                # valid two-digit
        prev2, prev1 = prev1, curr
    return prev1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Mishandling '0' (only valid as part of 10/20); not rejecting leading zero.",
         example="num_decodings('226') -> 3  ('2 2 6','22 6','2 26'); num_decodings('06') -> 0."),
    dict(cat="dsa", title="Partition Equal Subset Sum",
         answer="Can the array be split into two subsets with equal sum? Equivalent to a subset summing to total/2 (0/1 knapsack). DP boolean set of reachable sums.",
         tags=["partition-equal-subset","dynamic-programming","knapsack","subset-sum","dp","dsa"],
         code='''# True if the array splits into two equal-sum subsets (subset-sum DP).
def can_partition(nums):
    total = sum(nums)
    if total % 2 == 1:
        return False                     # odd total can't split evenly
    target = total // 2
    reachable = {0}
    for x in nums:
        reachable |= {s + x for s in reachable if s + x <= target}
        if target in reachable:
            return True
    return target in reachable''',
         complexity="Time O(n * target), space O(target).",
         pitfalls="Forgetting the odd-total early exit; growing the set without the <= target cap (slow).",
         example="can_partition([1,5,11,5]) -> True  ([1,5,5] and [11]); can_partition([1,2,3,5]) -> False."),
    dict(cat="dsa", title="Word Search (grid DFS backtracking)",
         answer="Determine if a word exists in a grid by moving to 4-adjacent cells without reusing a cell. DFS/backtracking from each cell matching the first letter, marking cells visited and restoring on backtrack.",
         tags=["word-search","backtracking","dfs","grid","dsa"],
         code='''# True if word can be traced in the grid (DFS backtracking).
def exist(board, word):
    rows, cols = len(board), len(board[0])
    def dfs(r, c, i):
        if i == len(word):
            return True                  # matched all letters
        if (r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]):
            return False
        tmp, board[r][c] = board[r][c], '#'   # mark visited
        found = (dfs(r+1, c, i+1) or dfs(r-1, c, i+1) or
                 dfs(r, c+1, i+1) or dfs(r, c-1, i+1))
        board[r][c] = tmp                # restore
        return found
    for r in range(rows):
        for c in range(cols):
            if dfs(r, c, 0):
                return True
    return False''',
         complexity="Time O(rows*cols*4^L), space O(L) recursion.",
         pitfalls="Not restoring the cell on backtrack (blocks other paths); reusing a cell within one path.",
         example="exist([['A','B','C','E'],['S','F','C','S'],['A','D','E','E']], 'ABCCED') -> True."),
    dict(cat="dsa", title="Longest Consecutive Sequence",
         answer="Length of the longest run of consecutive integers, in O(n). Put nums in a set; for each value that is a SEQUENCE START (no value-1 present), count upward -- each element is visited at most twice.",
         tags=["longest-consecutive","hash-set","array","dsa"],
         code='''# Longest run of consecutive integers in O(n) using a set.
def longest_consecutive(nums):
    num_set = set(nums)
    best = 0
    for x in num_set:
        if x - 1 not in num_set:         # x starts a new sequence
            length = 1
            while x + length in num_set:
                length += 1
            best = max(best, length)
    return best''',
         complexity="Time O(n), space O(n).",
         pitfalls="Sorting (O(n log n)) when a set gives O(n); counting from non-start values (O(n^2)).",
         example="longest_consecutive([100,4,200,1,3,2]) -> 4  ([1,2,3,4])."),
    dict(cat="dsa", title="Min Stack",
         answer="Design a stack with push/pop/top and getMin all O(1). Keep an auxiliary stack of running minimums (or store pairs), so the current min is always the top of the min stack.",
         tags=["min-stack","stack","design","dsa"],
         code='''# Stack supporting O(1) getMin via a parallel min stack.
class MinStack:
    def __init__(self):
        self.stack = []
        self.mins = []                   # running minimums

    def push(self, x):
        self.stack.append(x)
        # track the min so far (duplicate the current min if x is larger)
        self.mins.append(x if not self.mins else min(x, self.mins[-1]))

    def pop(self):
        self.mins.pop()
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def get_min(self):
        return self.mins[-1]''',
         complexity="Time O(1) per op, space O(n).",
         pitfalls="Recomputing min on each call (O(n)); forgetting to pop the min stack in lockstep.",
         example="push 3, push 1, push 2; get_min -> 1; pop; get_min -> 1; pop; get_min -> 3."),
    dict(cat="dsa", title="Implement Trie (Prefix Tree)",
         answer="Design a trie supporting insert, search (full word), and startsWith (prefix). Each node holds a children map and an end-of-word flag; walk/create nodes char by char.",
         tags=["trie","prefix-tree","design","string","dsa"],
         code='''# Trie with insert / search / startsWith.
class Trie:
    def __init__(self):
        self.children = {}
        self.is_end = False

    def insert(self, word):
        node = self
        for ch in word:
            node = node.children.setdefault(ch, Trie())  # create if missing
            node = node
        node.is_end = True

    def _find(self, prefix):
        node = self
        for ch in prefix:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def search(self, word):
        node = self._find(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._find(prefix) is not None''',
         complexity="Time O(L) per op, space O(total chars).",
         pitfalls="Not marking end-of-word (search would match prefixes); mutating during traversal incorrectly.",
         example="insert 'apple'; search 'apple' -> True; search 'app' -> False; starts_with 'app' -> True."),
    dict(cat="dsa", title="LRU Cache (design)",
         answer="Design a cache with O(1) get and put that evicts the LEAST-RECENTLY-USED key at capacity. Hash map for O(1) lookup + doubly linked list for O(1) recency reordering (or an ordered dict).",
         tags=["lru-cache","design","hash-map","ordered-dict","dsa"],
         code='''# LRU cache with O(1) get/put via an ordered dict.
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)      # mark most-recently-used
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)   # evict least-recently-used''',
         complexity="Time O(1) per op, space O(capacity).",
         pitfalls="Not updating recency on get; evicting the wrong end (last=False is the oldest).",
         example="cap 2: put(1,1),put(2,2),get(1)->1,put(3,3) evicts 2, get(2)->-1."),
    dict(cat="dsa", title="Kth Largest Element in a Stream",
         answer="Design a class that returns the k-th largest element after each add, over a growing stream. Maintain a MIN-HEAP of size k: the root is always the k-th largest; on add, push and pop when size exceeds k.",
         tags=["kth-largest-stream","heap","design","streaming","dsa"],
         code='''# Kth largest in a stream via a size-k min-heap.
import heapq

class KthLargest:
    def __init__(self, k, nums):
        self.k = k
        self.heap = nums[:]
        heapq.heapify(self.heap)
        while len(self.heap) > k:
            heapq.heappop(self.heap)     # keep only the k largest

    def add(self, val):
        heapq.heappush(self.heap, val)
        if len(self.heap) > self.k:
            heapq.heappop(self.heap)     # drop the smallest
        return self.heap[0]              # root = kth largest''',
         complexity="Time O(log k) per add, space O(k).",
         pitfalls="Keeping all elements (O(n log n)); returning the max instead of the heap root.",
         example="k=3, nums=[4,5,8,2]; add(3)->4, add(5)->5, add(10)->5, add(9)->8, add(4)->8."),
    dict(cat="ml_system_design", title="Design a Fraud Detection System",
         answer="Flag fraudulent transactions in real time to block/deny or send for review, minimizing losses while limiting false positives (customer friction). Six-step frame below.",
         tags=["ml-system-design","fraud-detection","anomaly-detection","imbalanced","classification"],
         example="1) PROBLEM: binary classification (fraud vs legit) with an asymmetric cost -- a missed fraud (FN) costs the chargeback, a false positive (FP) blocks a good customer; optimize expected COST, not accuracy. Constraints: <100ms decision at auth time, extreme imbalance (<0.1% fraud), adversarial (fraudsters adapt), and label DELAY (chargebacks arrive weeks later). 2) DATA & LABELS: transaction (amount, merchant, time), account history, device/IP, velocity/aggregate features (spend in last hour/day), graph features (shared cards/devices). Labels from chargebacks/confirmed fraud -- noisy and delayed; use provisional labels + rules for cold start. 3) MODEL: gradient-boosted trees (XGBoost) are a strong tabular baseline; add graph-based features or a GNN for ring detection; anomaly detection (isolation forest/autoencoder) for novel patterns unseen in labels. Class weighting/focal loss for imbalance. 4) TRAINING & EVAL: time-based splits (never shuffle -- avoid leakage from future), evaluate with PR-AUC, precision@recall for the operating point, and dollar-weighted loss; monitor for concept drift and retrain frequently. 5) SERVING: real-time feature store with streaming aggregates (velocity), low-latency model, plus a RULES layer (hard blocks) and human-review queue for medium-risk. Decisions feed a case-management system. 6) MONITORING: track approval/decline rates, fraud loss, FP complaints, feature drift, and adversarial shifts; use champion/challenger and delayed-label backtesting. Follow-ups: feedback loops (blocked frauds never get labels), explainability for declines (regulatory), and threshold tuning per segment/cost."),
    dict(cat="ml_concepts", title="Why Residual (Skip) Connections Enable Very Deep Networks",
         answer="A residual connection adds a layer's INPUT to its output: y = F(x) + x, so the block learns a RESIDUAL F(x) = y - x rather than the full mapping. This solves the DEGRADATION problem where naively stacking many layers made training error WORSE (not just overfitting). Two mechanisms: (1) GRADIENT FLOW -- the +x identity path gives backprop a direct route, so gradients reach early layers without vanishing through many multiplications, enabling 100+ layer nets; (2) EASIER OPTIMIZATION -- if the optimal transform is near-identity, F just needs to learn ~0, which is easy, so extra layers never hurt. ResNets rely on this; it also underpins Transformer blocks (each sublayer is x + Sublayer(x)).",
         tags=["residual-connections","resnet","vanishing-gradients","deep-networks","ml-concepts"],
         example="A 56-layer plain net had HIGHER training error than a 20-layer one (degradation); adding skip connections (ResNet-56) fixed it -- the identity path let gradients flow and let redundant layers learn the identity (F=0) instead of corrupting the signal."),
    dict(cat="glossary", title="HyperLogLog",
         answer="A probabilistic algorithm for approximate CARDINALITY (count of DISTINCT elements) in a stream using tiny, fixed memory (~KBs for billions of items). It hashes each element and tracks the maximum number of leading zeros seen across buckets; long runs of leading zeros are rare, so they imply many distinct values (harmonic-mean averaging across buckets reduces variance). Gives ~2% error for a few KB, versus storing every unique id. Used for unique-visitor counts, distinct queries, and analytics at scale (Redis PFCOUNT).",
         tags=["hyperloglog","cardinality","probabilistic","streaming","approximation"],
         example="Counting unique visitors to a site with billions of hits: HyperLogLog estimates the distinct count within ~2% using ~12KB, instead of a set holding every visitor id (gigabytes)."),
    dict(cat="conceptual", title="Why must you use time-based splits (not random shuffling) when evaluating models on temporal data like fraud or forecasting?",
         answer="The core principle of honest model evaluation is that your test set must simulate how the model will actually be used: predicting the FUTURE from the PAST. Standard k-fold cross-validation SHUFFLES all data and randomly assigns rows to folds, which implicitly assumes examples are independent and identically distributed with no time ordering. For temporal data -- fraud, demand forecasting, click prediction, anything where the world evolves -- that assumption is false and shuffling introduces LOOKAHEAD LEAKAGE: the model gets trained on examples that occurred AFTER the ones it's tested on, effectively letting it 'see the future.' Concretely, several leaks happen. (1) DIRECT temporal leakage: if a fraud ring operated on a single day and you shuffle, some of that day's transactions land in train and some in test; the model memorizes the ring's fingerprint from the training half and trivially 'predicts' the test half -- inflating metrics for a pattern it could never have known in real deployment (the ring didn't exist yet when the model was trained). (2) FEATURE leakage via aggregates: many features are rolling statistics (spend in last 7 days, account's historical fraud rate). Computed over a shuffled dataset, a 'past' aggregate can incorporate future transactions, encoding the answer. (3) DISTRIBUTION drift masking: shuffling mixes old and new regimes so the test set looks like the train set, hiding the fact that the real future distribution has drifted (new fraud tactics, seasonality) -- so your offline metric is optimistic and collapses in production. The FIX is time-based (a.k.a. forward-chaining / walk-forward) splitting: train on data up to time T, validate on (T, T+delta], and slide the window forward, so every evaluation only uses information available at prediction time -- exactly the deployment condition. For cross-validation you use expanding or rolling time windows rather than random folds. You must also compute all features with a strict as-of cutoff (point-in-time correctness) so no feature peeks past its timestamp, and account for LABEL delay (in fraud, chargeback labels arrive weeks later, so a fair backtest must respect when the label would actually have been known, not when the event occurred). The consequence of getting this wrong is the most dangerous kind of error: a model that looks excellent offline (because leakage handed it the answers) and fails silently in production, which is worse than a model that looks mediocre but is honestly evaluated. The general rule: your validation protocol must reproduce the information boundary of real use -- for temporal problems that boundary is time, so the split must respect time.",
         tags=["time-based-split","data-leakage","cross-validation","temporal-data","why"],
         example="A fraud model random-shuffled scored 0.95 PR-AUC offline but ~0.60 in production; a fraud ring's transactions had been split across train/test so the model 'recognized' test frauds it had trained on. Re-evaluated with a walk-forward split (train on weeks 1-8, test week 9), the honest offline score matched production and revealed the real gap to fix."),
    dict(cat="behavioral", title="STAR: Acting decisively with incomplete information (Bias for Action)",
         answer="Amazon LP: BIAS FOR ACTION -- speed matters in business; many decisions are reversible and don't need extensive study; calculated risk-taking is valued. Show you moved fast with imperfect information on a REVERSIBLE (two-way-door) decision, de-risked it cheaply, and got a result -- distinguishing it from the few one-way doors that do warrant caution.",
         tags=["behavioral","star","bias-for-action","two-way-door","amazon-lp"],
         example="SITUATION: Mid-incident, our API latency spiked and we suspected a recently-deployed caching change, but we didn't have conclusive data and full root-causing would take hours while customers suffered. TASK: As on-call I had to decide whether to wait for certainty or act. ACTION: I classified the decision: rolling back the caching change was a REVERSIBLE two-way door (we could redeploy it in minutes if it wasn't the cause), so it didn't warrant the delay of full analysis. I rolled it back immediately behind a feature flag while simultaneously keeping the investigation running, and I set a clear success signal (latency returns to baseline within 10 minutes) and a revert-the-revert plan if it didn't help. Latency recovered within minutes, confirming the hypothesis. I explicitly noted that had the action been a one-way door -- say, a schema migration or deleting data -- I would NOT have rushed it and would have taken the time to be sure. RESULT: We cut the customer impact from a potential multi-hour outage to about 15 minutes, then did the thorough root cause calmly afterward and shipped a proper fix with a regression test. The judgment that mattered was recognizing a cheap, reversible action and taking it fast instead of over-indexing on certainty -- while still respecting that irreversible decisions deserve more caution."),
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

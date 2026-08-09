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
    dict(cat="dsa", title="Number of Islands",
         answer="Count connected groups of '1's (land) in a grid. Iterate cells; on each unvisited land cell, flood-fill (DFS/BFS) its whole island marking cells visited, and increment the island count once per fill.",
         tags=["number-of-islands","graph","dfs","flood-fill","grid","dsa"],
         code='''# Count islands (4-directionally connected '1's) via flood fill.
def num_islands(grid):
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    def sink(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != '1':
            return
        grid[r][c] = '0'                 # mark visited (sink the land)
        sink(r + 1, c)
        sink(r - 1, c)
        sink(r, c + 1)
        sink(r, c - 1)
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1               # a new island
                sink(r, c)
    return count''',
         complexity="Time O(rows*cols), space O(rows*cols) recursion worst case.",
         pitfalls="Not marking visited (infinite recursion); counting per cell instead of per connected component.",
         example="num_islands([['1','1','0'],['1','0','0'],['0','0','1']]) -> 2."),
    dict(cat="dsa", title="Rotting Oranges",
         answer="Grid cells are empty(0), fresh(1), or rotten(2); each minute rotten oranges rot 4-adjacent fresh ones. Return minutes until none are fresh, or -1 if impossible. MULTI-SOURCE BFS from all initially-rotten cells, counting levels.",
         tags=["rotting-oranges","bfs","multi-source","grid","dsa"],
         code='''# Minutes until all oranges rot via multi-source BFS.
from collections import deque

def oranges_rotting(grid):
    rows, cols = len(grid), len(grid[0])
    queue = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                queue.append((r, c, 0))  # all rotten start at minute 0
            elif grid[r][c] == 1:
                fresh += 1
    minutes = 0
    while queue:
        r, c, t = queue.popleft()
        minutes = max(minutes, t)
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                grid[nr][nc] = 2         # rot this fresh orange
                fresh -= 1
                queue.append((nr, nc, t + 1))
    return minutes if fresh == 0 else -1''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Single-source BFS (must start from ALL rotten at once); not returning -1 when fresh remain.",
         example="oranges_rotting([[2,1,1],[1,1,0],[0,1,1]]) -> 4."),
    dict(cat="dsa", title="Course Schedule (topological sort)",
         answer="Given prerequisite pairs, decide if all courses can be finished (no cycle in the dependency graph). Kahn's algorithm: repeatedly remove zero-indegree nodes; if you process all nodes there's no cycle.",
         tags=["course-schedule","topological-sort","kahn","graph","cycle-detection","dsa"],
         code='''# True if all courses can be finished (DAG has no cycle), Kahn's BFS.
from collections import deque, defaultdict

def can_finish(num_courses, prerequisites):
    graph = defaultdict(list)
    indegree = [0] * num_courses
    for course, prereq in prerequisites:
        graph[prereq].append(course)     # prereq -> course edge
        indegree[course] += 1
    queue = deque(i for i in range(num_courses) if indegree[i] == 0)
    done = 0
    while queue:
        node = queue.popleft()
        done += 1
        for nxt in graph[node]:
            indegree[nxt] -= 1           # remove this edge
            if indegree[nxt] == 0:
                queue.append(nxt)
    return done == num_courses           # all processed -> no cycle''',
         complexity="Time O(V + E), space O(V + E).",
         pitfalls="Reversing edge direction; concluding cycle-free without checking all nodes processed.",
         example="can_finish(2, [[1,0]]) -> True; can_finish(2, [[1,0],[0,1]]) -> False (cycle)."),
    dict(cat="dsa", title="Coin Change (fewest coins)",
         answer="Fewest coins summing to an amount (unbounded supply), or -1. DP: dp[a] = min over coins c of dp[a-c] + 1, building up from 0.",
         tags=["coin-change","dynamic-programming","unbounded-knapsack","dp","dsa"],
         code='''# Fewest coins to make 'amount' (or -1 if impossible), bottom-up DP.
def coin_change(coins, amount):
    INF = amount + 1
    dp = [0] + [INF] * amount            # dp[0] = 0 coins
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)   # take coin c
    return dp[amount] if dp[amount] != INF else -1''',
         complexity="Time O(amount * coins), space O(amount).",
         pitfalls="Confusing with counting combinations (this minimizes count); wrong sentinel making -1 detection fail.",
         example="coin_change([1,2,5], 11) -> 3  (5+5+1); coin_change([2], 3) -> -1."),
    dict(cat="dsa", title="Longest Increasing Subsequence",
         answer="Length of the longest strictly increasing subsequence. Patience-sorting / binary search: keep 'tails', the smallest possible tail for each length; for each num, replace the first tail >= num (or append). The tails length is the answer.",
         tags=["longest-increasing-subsequence","binary-search","patience-sorting","dp","dsa"],
         code='''# Length of the LIS in O(n log n) via the tails array.
import bisect

def length_of_lis(nums):
    tails = []
    for x in nums:
        i = bisect.bisect_left(tails, x)   # first tail >= x
        if i == len(tails):
            tails.append(x)                # x extends the longest subsequence
        else:
            tails[i] = x                   # x becomes a smaller tail for length i+1
    return len(tails)''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="tails is NOT an actual LIS (only its length is valid); bisect_right allows non-strict increases.",
         example="length_of_lis([10,9,2,5,3,7,101,18]) -> 4  ([2,3,7,101])."),
    dict(cat="dsa", title="Word Break",
         answer="Can a string be segmented into a space-separated sequence of dictionary words? DP over prefixes: dp[i] is True if some j<i has dp[j] True and s[j:i] is in the dictionary.",
         tags=["word-break","dynamic-programming","string","dp","dsa"],
         code='''# True if s can be segmented into dictionary words, DP over prefixes.
def word_break(s, word_dict):
    words = set(word_dict)
    n = len(s)
    dp = [False] * (n + 1)
    dp[0] = True                          # empty prefix is segmentable
    for i in range(1, n + 1):
        for j in range(i):
            if dp[j] and s[j:i] in words:  # split at j
                dp[i] = True
                break
    return dp[n]''',
         complexity="Time O(n^2) substrings (times substring hashing), space O(n).",
         pitfalls="Greedy matching (fails on ambiguous splits); not using a set for O(1) word lookup.",
         example="word_break('leetcode', ['leet','code']) -> True; word_break('catsandog', ['cats','dog','sand','and','cat']) -> False."),
    dict(cat="dsa", title="House Robber II (circular)",
         answer="Houses in a CIRCLE; can't rob two adjacent, and the first and last are adjacent. Run the linear house-robber DP twice -- once excluding the last house, once excluding the first -- and take the max.",
         tags=["house-robber","dynamic-programming","circular","dp","dsa"],
         code='''# Max robbery on houses in a circle (first and last are adjacent).
def rob(nums):
    if len(nums) == 1:
        return nums[0]
    def rob_line(houses):
        prev = curr = 0
        for money in houses:
            prev, curr = curr, max(curr, prev + money)  # take or skip
        return curr
    # exclude last, or exclude first, then take the better
    return max(rob_line(nums[:-1]), rob_line(nums[1:]))''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting the circular adjacency (first/last); mishandling the single-house case.",
         example="rob([2,3,2]) -> 3  (can't take both 2s); rob([1,2,3,1]) -> 4."),
    dict(cat="dsa", title="Edit Distance (Levenshtein)",
         answer="Minimum insert/delete/replace operations to turn word1 into word2. DP grid: dp[i][j] = edit distance of prefixes; if chars match take the diagonal, else 1 + min(insert, delete, replace).",
         tags=["edit-distance","levenshtein","dynamic-programming","string","dp","dsa"],
         code='''# Levenshtein edit distance via DP.
def min_distance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i                      # delete all of word1's prefix
    for j in range(n + 1):
        dp[0][j] = j                      # insert all of word2's prefix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]           # chars match, no op
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],      # delete
                                   dp[i][j - 1],      # insert
                                   dp[i - 1][j - 1])  # replace
    return dp[m][n]''',
         complexity="Time O(m*n), space O(m*n).",
         pitfalls="Missing the base-case row/column initialization; mixing up which neighbor is insert vs delete.",
         example="min_distance('horse', 'ros') -> 3."),
    dict(cat="dsa", title="Kth Largest Element in an Array",
         answer="Find the k-th largest value. A min-heap of size k keeps the k largest seen: push each element, pop when the heap exceeds k; the heap's root is the answer. (Quickselect gives average O(n).)",
         tags=["kth-largest","heap","priority-queue","quickselect","dsa"],
         code='''# Kth largest element using a size-k min-heap.
import heapq

def find_kth_largest(nums, k):
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)          # drop the smallest, keep k largest
    return heap[0]                       # root = kth largest''',
         complexity="Time O(n log k), space O(k).",
         pitfalls="Using a max-heap of all n (O(n log n)); popping before the size exceeds k.",
         example="find_kth_largest([3,2,1,5,6,4], 2) -> 5."),
    dict(cat="dsa", title="Top K Frequent Elements",
         answer="Return the k most frequent elements. Count frequencies, then either a size-k heap (O(n log k)) or BUCKET SORT by frequency (O(n)): index buckets by count and read from the highest.",
         tags=["top-k-frequent","bucket-sort","counting","heap","dsa"],
         code='''# K most frequent elements via bucket sort on frequency.
from collections import Counter

def top_k_frequent(nums, k):
    counts = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]   # index = frequency
    for value, freq in counts.items():
        buckets[freq].append(value)
    result = []
    for freq in range(len(buckets) - 1, 0, -1):    # high frequency first
        for value in buckets[freq]:
            result.append(value)
            if len(result) == k:
                return result
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Sorting all counts (O(n log n)) when buckets give O(n); bucket index off by one.",
         example="top_k_frequent([1,1,1,2,2,3], 2) -> [1,2]."),
    dict(cat="dsa", title="Merge Intervals",
         answer="Merge all overlapping intervals. Sort by start; sweep, extending the current interval's end when the next starts within it, else emitting the current and starting a new one.",
         tags=["merge-intervals","intervals","sorting","greedy","dsa"],
         code='''# Merge overlapping intervals.
def merge(intervals):
    intervals.sort(key=lambda x: x[0])   # by start
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)   # overlap: extend end
        else:
            merged.append([start, end])              # disjoint: new interval
    return merged''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Not sorting first; using < instead of <= (touching intervals [1,2],[2,3] should merge here).",
         example="merge([[1,3],[2,6],[8,10],[15,18]]) -> [[1,6],[8,10],[15,18]]."),
    dict(cat="dsa", title="Non-overlapping Intervals",
         answer="Minimum intervals to remove so the rest don't overlap. Greedy: sort by END; keep an interval only if it starts at/after the last kept end, otherwise it's a removal. (Activity selection.)",
         tags=["non-overlapping-intervals","greedy","intervals","sorting","dsa"],
         code='''# Fewest intervals to remove to make the rest non-overlapping.
def erase_overlap_intervals(intervals):
    intervals.sort(key=lambda x: x[1])   # sort by end
    removals = 0
    prev_end = float('-inf')
    for start, end in intervals:
        if start >= prev_end:
            prev_end = end               # keep this interval
        else:
            removals += 1                # overlaps -> remove it
    return removals''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Sorting by start (greedy breaks); using > vs >= for touching endpoints.",
         example="erase_overlap_intervals([[1,2],[2,3],[3,4],[1,3]]) -> 1."),
    dict(cat="ml_system_design", title="Design an Ad Click-Through-Rate (CTR) Prediction System",
         answer="Predict P(click | user, ad, context) to rank ads and price them, at very high QPS with sub-100ms latency. Six-step frame below.",
         tags=["ml-system-design","ctr-prediction","ranking","ads","recommendation"],
         example="1) PROBLEM: binary classification of click probability; business objective is expected revenue (CTR x bid) and long-term user value, not raw CTR. Constraints: >100k QPS, <50ms model latency, billions of daily events, heavy class imbalance (CTR often 1-5%). 2) DATA & LABELS: impression logs with click/no-click labels; features -- user (history, demographics, embeddings), ad (creative, advertiser, category embeddings), context (device, time, placement), and cross features. Beware POSITION BIAS (higher slots get more clicks) and delayed feedback (a click may arrive minutes later). 3) MODEL: start with logistic regression + massive sparse cross features (hashing trick) as a strong baseline; move to gradient-boosted trees or a DEEP model (Wide and Deep, DeepFM, DCN) that learns feature interactions via embeddings. Calibrate outputs (Platt/isotonic) because you need true probabilities for pricing, not just ranking. 4) TRAINING: negative downsampling for imbalance (then re-calibrate), online/continual learning to track drift, regularization, and careful train/serve feature parity. 5) EVALUATION: offline AUC and especially LOG-LOSS/calibration (probabilities matter for auctions); online A/B on revenue, CTR, and guardrails (latency, advertiser value); counterfactual/replay for policy changes. 6) SERVING & MONITORING: two-stage (candidate generation then heavy ranking), feature store for low-latency lookups, model versioning, real-time feature freshness, and monitoring for calibration drift, feature distribution shift, and feedback loops. Follow-ups: cold-start ads (exploration/Thompson sampling), position-bias correction (inverse propensity weighting), and privacy constraints."),
    dict(cat="ml_concepts", title="Bias-Variance Decomposition",
         answer="Expected test error of a model decomposes into three parts: BIAS^2 + VARIANCE + IRREDUCIBLE NOISE. Bias is error from wrong assumptions (too-simple model underfits -- misses the true relationship); variance is error from sensitivity to the particular training set (too-complex model overfits -- learns noise); irreducible noise is inherent randomness no model can remove. Formally, for squared loss, E[(y - f_hat(x))^2] = (Bias[f_hat])^2 + Var[f_hat] + sigma^2. The tradeoff: increasing model complexity lowers bias but raises variance; the goal is the sweet spot minimizing their sum. Techniques shift the balance -- regularization, bagging, and more data reduce variance; richer models/features reduce bias.",
         tags=["bias-variance","overfitting","underfitting","generalization","ml-concepts"],
         example="A degree-1 fit to a curvy relationship has high bias (underfits, ~same wrong line regardless of sample); a degree-15 fit has high variance (wildly different curves per sample, overfits); a degree-3 fit balances both for the lowest expected test error. More training data shrinks the variance term, letting you afford a more complex, lower-bias model."),
    dict(cat="ml_concepts", title="ROC-AUC vs Precision-Recall Curves",
         answer="Both evaluate a binary classifier across thresholds, but emphasize different things. ROC plots TPR (recall) vs FPR; AUC-ROC is the probability a random positive is ranked above a random negative -- threshold-independent and good for balanced data. PR plots precision vs recall; it's far more INFORMATIVE under heavy CLASS IMBALANCE because it ignores true negatives (which dominate and make FPR look deceptively good), focusing on the rare positive class. Rule: use PR curves / average precision when positives are rare and you care about them (fraud, disease, retrieval); ROC when classes are roughly balanced or you care about both errors symmetrically.",
         tags=["roc-auc","precision-recall","class-imbalance","evaluation","ml-concepts"],
         example="With 1 fraud per 10,000 transactions, a model can have AUC-ROC 0.99 yet terrible precision (flooding analysts with false positives); the PR curve exposes this because precision collapses when the huge negative class leaks in, while ROC's FPR stays tiny and flattering."),
    dict(cat="glossary", title="Bloom filter",
         answer="A space-efficient PROBABILISTIC set-membership structure. A bit array plus k hash functions: to add an element, set the k bits it hashes to; to query, check those k bits. If any is 0 the element is DEFINITELY NOT present; if all are 1 it's PROBABLY present (false positives possible, NO false negatives). You can't delete (without a counting variant). Trades a tunable false-positive rate for huge memory savings -- used to skip disk lookups (LSM/Cassandra/HBase), avoid duplicate work, and cache-miss filtering.",
         tags=["bloom-filter","probabilistic","membership","hashing","space-efficient"],
         example="A database checks a Bloom filter before hitting disk for a key: 'definitely not here' means skip the expensive read entirely; 'maybe here' triggers the read -- so most negative lookups are answered from a tiny in-memory bit array."),
    dict(cat="glossary", title="Consistent hashing with virtual nodes",
         answer="CONSISTENT HASHING maps both keys and servers onto a hash RING; a key is served by the next server clockwise, so adding/removing a server only remaps keys in ONE arc (K/N keys) instead of nearly all (as naive hash-mod-N would). VIRTUAL NODES fix its two weaknesses: place each physical server at MANY points on the ring (virtual nodes) so load spreads evenly (avoiding hot spots from uneven arcs) and so a failed server's load redistributes across MANY others rather than dumping entirely on its single successor. Core to Dynamo, Cassandra, and sharded caches.",
         tags=["consistent-hashing","virtual-nodes","sharding","load-balancing","distributed-systems"],
         example="A cache cluster grows from 4 to 5 nodes: consistent hashing remaps only ~1/5 of keys (not all), and each physical node's 150 virtual nodes keep every server's share within a few percent of even -- so no single node gets a disproportionate slice."),
    dict(cat="conceptual", title="Why does the tails array in the O(n log n) LIS algorithm give the correct length but not a valid subsequence?",
         answer="The O(n log n) longest-increasing-subsequence algorithm maintains an array 'tails' where, after processing some prefix of the input, tails[i] holds the SMALLEST possible tail value of any increasing subsequence of length i+1 seen so far. For each incoming number x, you binary-search for the first tails entry >= x: if none exists, x is larger than every current tail, so it extends the longest subsequence and you append it; otherwise you OVERWRITE that entry with x, because x is a smaller (better) tail for a subsequence of that length, giving future elements more room to extend it. The length of tails at the end is the LIS length. Here's the subtlety: tails is NOT itself a valid increasing subsequence of the input, even though it is always a sorted array and has the right LENGTH. The reason is that the overwrites happen at DIFFERENT TIMES and at different positions, so the values sitting in tails at the end may come from elements that appear in an order in the original array that does NOT form an actual subsequence. Concretely, tails[i] might be updated by a number that occurs LATE in the input while tails[i+1] still holds a number that occurred EARLIER -- so reading tails left to right could give you values whose original indices are not increasing, which violates the definition of a subsequence (a subsequence must preserve the original order). The array is a bookkeeping device that correctly tracks, for each achievable length, the best (smallest) tail to maximize extendability -- and that invariant is exactly what makes the final LENGTH correct (the number of distinct lengths you were able to build). But the specific VALUES are a mix-and-match across time that need not co-occur in order. To recover an ACTUAL longest subsequence (not just its length) you must augment the algorithm: record, for each element, the length of the LIS ending at it (the position where it was placed in tails) and a predecessor/parent pointer to the element that was at the previous tails slot when it was inserted; then backtrack from the element that achieved the maximum length. That reconstruction restores a genuine subsequence with increasing indices and increasing values. The lesson: tails answers 'how long' by maintaining an extendability frontier, which is a weaker and cheaper thing to maintain than an actual witness subsequence, and conflating the two is a classic mistake.",
         tags=["longest-increasing-subsequence","binary-search","invariants","reconstruction","why"],
         example="On [3,4,1,2], tails evolves [3]->[3,4]->[1,4]->[1,2], length 2 (correct: LIS is [3,4] or [1,2]). But reading tails=[1,2] as a subsequence would pick values 1 (index 2) then 2 (index 3) -- which happens to be valid here, yet on [10,20,1,2,3] tails ends [1,2,3] mixing the late small run with earlier structure; the length 3 is right but tails' values aren't guaranteed to be the indices of any single increasing run without predecessor tracking."),
    dict(cat="behavioral", title="STAR: Learning something hard and outside your expertise fast (Learn and Be Curious)",
         answer="Amazon LP: LEARN AND BE CURIOUS -- leaders are never done learning and always seek to improve themselves; they are curious about new possibilities and act to explore them. Show you deliberately ramped on an unfamiliar, hard domain under time pressure and turned that learning into a delivered result.",
         tags=["behavioral","star","learn-and-be-curious","amazon-lp","growth"],
         example="SITUATION: My team inherited a legacy search service written in a language and using an information-retrieval stack (inverted indexes, BM25 ranking) I had no background in, and its relevance was degrading with no one left who understood it. TASK: I volunteered to become the owner and fix relevance, which meant learning IR fundamentals and the codebase quickly enough to make safe changes within a quarter. ACTION: I structured the learning instead of flailing: I read the core IR chapters on tokenization, inverted indexes, TF-IDF/BM25, and evaluation metrics (nDCG, MRR) over two weeks, and in parallel instrumented the service to log queries and results so I could ground the theory in our actual data. I reproduced a few bad queries, formed hypotheses (poor tokenization of hyphenated terms, a mis-tuned BM25 k1/b), and validated them offline with an nDCG harness I built from human-judged query/result pairs before touching production. I asked a former maintainer targeted questions rather than general ones, which respected their time and sped my ramp. RESULT: Within the quarter I shipped tokenization and ranking-parameter fixes that measurably improved nDCG on our judged set and cut 'no good result' complaints, and I wrote up an IR primer + runbook so the team was no longer single-threaded on lost knowledge. The curiosity to actually learn the theory -- not just pattern-match code -- was what let me diagnose root causes instead of guessing, and it turned a scary black box into a service the team could confidently own."),
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

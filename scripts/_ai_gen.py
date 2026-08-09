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
    dict(cat="dsa", title="Number of Provinces",
         answer="Given an adjacency matrix of cities, count connected components (provinces). UNION-FIND: union directly-connected cities, then count distinct roots.",
         tags=["number-of-provinces","union-find","dsu","graph","connected-components","dsa"],
         code='''# Count connected components (provinces) via union-find.
def find_circle_num(is_connected):
    n = len(is_connected)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]   # path compression
            x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j] == 1:
                union(i, j)
    return len({find(i) for i in range(n)})  # distinct roots''',
         complexity="Time O(n^2 * alpha), space O(n).",
         pitfalls="Counting parents instead of roots (find each first); iterating the full matrix twice unnecessarily.",
         example="find_circle_num([[1,1,0],[1,1,0],[0,0,1]]) -> 2."),
    dict(cat="dsa", title="Redundant Connection",
         answer="A tree had one extra edge added forming a cycle; return that edge. UNION-FIND: process edges; the first edge whose two endpoints already share a root is the redundant one.",
         tags=["redundant-connection","union-find","dsu","cycle","graph","dsa"],
         code='''# Find the edge that creates a cycle (union-find).
def find_redundant_connection(edges):
    parent = list(range(len(edges) + 1))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            return [a, b]                # already connected -> this closes a cycle
        parent[ra] = rb                  # union
    return []''',
         complexity="Time O(n * alpha), space O(n).",
         pitfalls="Returning the wrong (earliest vs last) edge; 1-indexed node ids needing size n+1.",
         example="find_redundant_connection([[1,2],[1,3],[2,3]]) -> [2,3]."),
    dict(cat="dsa", title="Word Ladder (shortest transformation)",
         answer="Shortest transformation from beginWord to endWord changing one letter at a time, each intermediate in the word list. BFS over words: neighbors are words differing by one letter; the level count is the answer.",
         tags=["word-ladder","bfs","shortest-path","graph","dsa"],
         code='''# Length of the shortest word-ladder transformation (BFS).
from collections import deque

def ladder_length(begin_word, end_word, word_list):
    words = set(word_list)
    if end_word not in words:
        return 0
    queue = deque([(begin_word, 1)])
    while queue:
        word, steps = queue.popleft()
        if word == end_word:
            return steps
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                candidate = word[:i] + c + word[i + 1:]
                if candidate in words:
                    words.remove(candidate)   # mark visited
                    queue.append((candidate, steps + 1))
    return 0''',
         complexity="Time O(N * L * 26), space O(N * L).",
         pitfalls="Not removing visited words (revisits/loops); returning steps off by one.",
         example="ladder_length('hit','cog',['hot','dot','dog','lot','log','cog']) -> 5."),
    dict(cat="dsa", title="Network Delay Time (Dijkstra)",
         answer="Time for a signal from node k to reach all nodes in a weighted directed graph; -1 if unreachable. DIJKSTRA with a min-heap: relax edges by shortest known distance; the answer is the max finalized distance.",
         tags=["network-delay","dijkstra","shortest-path","heap","graph","dsa"],
         code='''# Min time to reach all nodes from k (Dijkstra).
import heapq
from collections import defaultdict

def network_delay_time(times, n, k):
    graph = defaultdict(list)
    for u, v, w in times:
        graph[u].append((v, w))
    dist = {}
    heap = [(0, k)]                      # (distance, node)
    while heap:
        d, node = heapq.heappop(heap)
        if node in dist:
            continue                     # already finalized
        dist[node] = d
        for nei, w in graph[node]:
            if nei not in dist:
                heapq.heappush(heap, (d + w, nei))
    return max(dist.values()) if len(dist) == n else -1''',
         complexity="Time O(E log V), space O(V + E).",
         pitfalls="Not skipping already-finalized nodes; returning a sum instead of the max distance.",
         example="network_delay_time([[2,1,1],[2,3,1],[3,4,1]], 4, 2) -> 2."),
    dict(cat="dsa", title="Subsets (power set)",
         answer="Generate all subsets of a distinct-element list. Backtracking: at each index choose to include or skip; append a copy of the current subset at every node.",
         tags=["subsets","backtracking","power-set","recursion","dsa"],
         code='''# All subsets (the power set) via backtracking.
def subsets(nums):
    result = []
    def backtrack(start, current):
        result.append(current[:])        # record this subset
        for i in range(start, len(nums)):
            current.append(nums[i])      # include nums[i]
            backtrack(i + 1, current)
            current.pop()                # undo (skip nums[i])
    backtrack(0, [])
    return result''',
         complexity="Time O(n * 2^n), space O(n) recursion.",
         pitfalls="Appending the list by reference (must copy); revisiting earlier indices (start prevents duplicates).",
         example="subsets([1,2,3]) has 8 subsets including [], [1], [1,2], [1,2,3]."),
    dict(cat="dsa", title="Permutations",
         answer="Generate all orderings of distinct numbers. Backtracking with a used marker (or swapping): build a permutation position by position, choosing each unused element.",
         tags=["permutations","backtracking","recursion","dsa"],
         code='''# All permutations of distinct numbers via backtracking.
def permute(nums):
    result = []
    used = [False] * len(nums)
    def backtrack(current):
        if len(current) == len(nums):
            result.append(current[:])    # a complete permutation
            return
        for i in range(len(nums)):
            if not used[i]:
                used[i] = True
                current.append(nums[i])
                backtrack(current)
                current.pop()            # undo
                used[i] = False
    backtrack([])
    return result''',
         complexity="Time O(n * n!), space O(n).",
         pitfalls="Forgetting to reset the used flag on backtrack; appending by reference.",
         example="permute([1,2,3]) -> 6 permutations including [1,2,3] and [3,2,1]."),
    dict(cat="dsa", title="Combination Sum",
         answer="All unique combinations of candidates (reusable) summing to a target. Backtracking: at each step try candidates from the current index onward (allowing reuse), subtracting from the remaining target; prune when it goes negative.",
         tags=["combination-sum","backtracking","recursion","dsa"],
         code='''# All combinations (with reuse) summing to target, via backtracking.
def combination_sum(candidates, target):
    result = []
    def backtrack(start, remaining, current):
        if remaining == 0:
            result.append(current[:])    # exact hit
            return
        for i in range(start, len(candidates)):
            if candidates[i] <= remaining:
                current.append(candidates[i])
                backtrack(i, remaining - candidates[i], current)  # i (reuse allowed)
                current.pop()
    backtrack(0, target, [])
    return result''',
         complexity="Time exponential in target/candidates, space O(target).",
         pitfalls="Passing i+1 (forbids reuse); not pruning when candidate exceeds remaining (dupes/slow).",
         example="combination_sum([2,3,6,7], 7) -> [[2,2,3],[7]]."),
    dict(cat="dsa", title="Generate Parentheses",
         answer="Generate all valid combinations of n pairs of parentheses. Backtracking with counts: add '(' while open < n, add ')' while close < open; record when the string reaches length 2n.",
         tags=["generate-parentheses","backtracking","recursion","dsa"],
         code='''# All valid parenthesizations of n pairs via backtracking.
def generate_parenthesis(n):
    result = []
    def backtrack(current, open_count, close_count):
        if len(current) == 2 * n:
            result.append(current)       # a complete valid string
            return
        if open_count < n:
            backtrack(current + '(', open_count + 1, close_count)
        if close_count < open_count:
            backtrack(current + ')', open_count, close_count + 1)
    backtrack('', 0, 0)
    return result''',
         complexity="Time O(4^n / sqrt(n)) (Catalan), space O(n) recursion.",
         pitfalls="Allowing ')' when close >= open (invalid); wrong termination length.",
         example="generate_parenthesis(3) -> ['((()))','(()())','(())()','()(())','()()()']."),
    dict(cat="dsa", title="Product of Array Except Self",
         answer="Return an array where each element is the product of all others, WITHOUT division and in O(n). Two passes: prefix products left-to-right, then multiply by suffix products right-to-left.",
         tags=["product-except-self","prefix-suffix","array","dsa"],
         code='''# Product of all elements except self, no division, O(n).
def product_except_self(nums):
    n = len(nums)
    result = [1] * n
    prefix = 1
    for i in range(n):
        result[i] = prefix              # product of everything to the left
        prefix *= nums[i]
    suffix = 1
    for i in range(n - 1, -1, -1):
        result[i] *= suffix             # multiply by product to the right
        suffix *= nums[i]
    return result''',
         complexity="Time O(n), space O(1) (output aside).",
         pitfalls="Using division (fails on zeros); an extra array when the output can hold prefixes.",
         example="product_except_self([1,2,3,4]) -> [24,12,8,6]."),
    dict(cat="dsa", title="Longest Substring Without Repeating Characters",
         answer="Length of the longest substring with all distinct characters. SLIDING WINDOW with a last-seen map: expand the right edge; when a repeat is inside the window, jump the left edge past its previous position.",
         tags=["longest-substring-no-repeat","sliding-window","hash-map","string","dsa"],
         code='''# Longest substring with all-unique characters (sliding window).
def length_of_longest_substring(s):
    last_seen = {}
    left = 0
    best = 0
    for right, ch in enumerate(s):
        if ch in last_seen and last_seen[ch] >= left:
            left = last_seen[ch] + 1     # shrink past the previous occurrence
        last_seen[ch] = right
        best = max(best, right - left + 1)
    return best''',
         complexity="Time O(n), space O(min(n, alphabet)).",
         pitfalls="Not checking last_seen >= left (stale positions outside the window); recomputing the window length wrong.",
         example="length_of_longest_substring('abcabcbb') -> 3  ('abc')."),
    dict(cat="dsa", title="Subarray Sum Equals K",
         answer="Count contiguous subarrays summing to k. PREFIX SUM + hash map: as you sweep, the number of earlier prefix sums equal to (current_prefix - k) is how many subarrays ending here sum to k.",
         tags=["subarray-sum-k","prefix-sum","hash-map","array","dsa"],
         code='''# Count subarrays summing to k via prefix sums.
def subarray_sum(nums, k):
    from collections import defaultdict
    counts = defaultdict(int)
    counts[0] = 1                        # empty prefix
    prefix = 0
    total = 0
    for x in nums:
        prefix += x
        total += counts[prefix - k]      # earlier prefixes that complete a sum of k
        counts[prefix] += 1
    return total''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting counts[0]=1 (misses subarrays starting at index 0); adding to the map before querying.",
         example="subarray_sum([1,1,1], 2) -> 2; subarray_sum([1,2,3], 3) -> 2."),
    dict(cat="ml_system_design", title="Design a YouTube-style Video Recommendation System",
         answer="Recommend the next videos to watch to maximize long-term engagement (watch time / satisfaction), personalized, at massive scale. Six-step frame below.",
         tags=["ml-system-design","recommendations","youtube","ranking","retrieval"],
         example="1) PROBLEM: rank a personalized set of videos to maximize long-term user satisfaction, proxied by expected WATCH TIME and explicit signals (likes, 'not interested'), NOT just clicks (avoid clickbait). Constraints: billions of videos, hundreds of millions of users, <a few hundred ms, constant fresh content and cold-start. 2) DATA & LABELS: implicit feedback (watch time, completion rate, skips), explicit (like/dislike/subscribe), context (time, device, prior session). Beware feedback loops (the model shapes what's watched) and position/popularity bias. 3) TWO-STAGE ARCHITECTURE: (a) CANDIDATE GENERATION -- from billions to hundreds via cheap retrieval: two-tower (user tower, item tower) producing embeddings + approximate nearest neighbor (ANN) search, plus collaborative-filtering and subscription/trending sources; (b) RANKING -- a heavier model (deep network with rich cross features) scores the few hundred candidates on predicted watch time / multi-objective. 4) FEATURES/MODEL: user and video embeddings, watch history sequences (often a transformer/RNN over recent watches), video metadata, freshness; multi-task heads (watch time, like, share) combined with tuned weights. 5) EVALUATION: offline -- ranking metrics (nDCG, recall@k for retrieval, AUC/watch-time-weighted loss for ranking); ONLINE A/B on watch time, session length, next-day retention, with guardrails against clickbait and diversity collapse. 6) SERVING & MONITORING: precomputed item embeddings + ANN index refreshed continuously, real-time user features, candidate/ranker model versioning; monitor for staleness, popularity bias, filter bubbles, and freshness of new uploads. Follow-ups: cold-start (content features/exploration), diversity and fairness re-ranking, and exploration via bandits to avoid rich-get-richer."),
    dict(cat="ml_concepts", title="Class Imbalance Strategies",
         answer="When one class vastly outnumbers others, models trivially favor the majority and the minority (often the important one) is ignored. Strategies span four levels. DATA: oversample the minority (random or SMOTE-synthetic), undersample the majority, or combine. ALGORITHM: class-weighted loss (penalize minority errors more), focal loss (down-weight easy examples), threshold moving. EVALUATION: use PR-AUC/F1/recall not accuracy (which is misleading), and pick the operating threshold from the business cost of FP vs FN. ENSEMBLE: balanced bagging/boosting. Also reframe extreme cases as anomaly detection. Always evaluate on the ORIGINAL imbalanced distribution and re-calibrate probabilities if you resampled.",
         tags=["class-imbalance","smote","class-weights","focal-loss","ml-concepts"],
         example="Fraud at 0.2%: a model predicting 'never fraud' scores 99.8% accuracy but is useless; class-weighting + threshold tuning to maximize recall at acceptable precision, evaluated by PR-AUC, actually catches fraud -- and if you oversampled, you re-calibrate the output probabilities before using them for expected-loss decisions."),
    dict(cat="ml_concepts", title="Attention Mechanism Intuition",
         answer="Attention lets a model DYNAMICALLY focus on the most relevant parts of its input when producing each output, instead of compressing everything into one fixed vector. Each position emits a QUERY, KEY, and VALUE; the query is compared (dot product) to all keys to get relevance SCORES, which are softmax-normalized into weights, and the output is the weighted sum of VALUES. So each token 'looks at' every other token and pulls in information proportional to relevance -- resolving long-range dependencies a fixed-window/RNN struggles with. SELF-attention (queries/keys/values from the same sequence) is the core of Transformers; scaling by sqrt(d_k) keeps the softmax stable, and MULTI-HEAD attention runs several attentions in parallel to capture different relation types.",
         tags=["attention","transformers","self-attention","query-key-value","ml-concepts"],
         example="Translating 'the animal didn't cross the street because it was tired', self-attention lets 'it' attend strongly to 'animal' (not 'street'), pulling that meaning into its representation -- a dynamic, content-based link no fixed positional rule could reliably capture."),
    dict(cat="glossary", title="Count-min sketch",
         answer="A probabilistic structure for approximate FREQUENCY counts in a stream using sublinear memory. A 2-D array of counters with d hash functions (one row each); to add an item, increment counters[i][hash_i(item)] for all rows; to query, take the MINIMUM of those counters (min reduces the effect of hash collisions, which only ever INFLATE counts). It OVERESTIMATES (never underestimates) with a bounded error. Used for heavy-hitters, streaming analytics, and rate limiting where exact counts are too memory-heavy.",
         tags=["count-min-sketch","probabilistic","streaming","frequency","heavy-hitters"],
         example="Tracking approximate hit counts for billions of URLs in a stream: a fixed-size count-min sketch answers 'roughly how many times this URL appeared' in KBs instead of storing every URL, taking the min across rows to limit collision inflation."),
    dict(cat="conceptual", title="Why do recommendation and ad systems use a two-stage retrieval-then-ranking architecture instead of one big model?",
         answer="The fundamental tension is between SCALE and QUALITY. A recommender or ad system must select a handful of items to show from a CORPUS of millions to billions (videos, products, ads), and it must do so in tens of milliseconds per request at enormous QPS. You cannot run a rich, accurate scoring model over the entire corpus per request: even a modest deep model at, say, 1ms per item would take hours to score a billion items -- utterly infeasible online. But you also don't want a cheap model making the final decision, because ranking quality (the precise ordering of what the user sees) directly drives revenue and satisfaction and benefits from heavy models with many cross features. The two-stage architecture resolves this by SPLITTING the problem into two sub-problems with opposite optimization targets. STAGE 1, CANDIDATE GENERATION (retrieval), optimizes for RECALL AND SPEED: from the billion-item corpus it must cheaply narrow to a few hundred plausible candidates without missing good ones. It uses lightweight methods -- typically a TWO-TOWER model that embeds the user and each item independently into the same vector space, so item embeddings can be PRECOMPUTED offline and indexed; at request time you embed only the user and do an APPROXIMATE NEAREST NEIGHBOR search over the index, which is sublinear (not per-item scoring). It doesn't need precise ordering, just a high-recall shortlist. STAGE 2, RANKING, optimizes for PRECISION: now that the set is only a few hundred items, you can afford an expensive model with rich features -- user-item CROSS features (interactions the two-tower deliberately avoided so it could precompute), full histories, real-time context, multi-task heads -- to score and order them accurately. The key architectural insight is WHY the towers must be separate in stage 1 but can be joined in stage 2: precomputation. A two-tower model keeps user and item encoders independent precisely so item vectors don't depend on the user and can be indexed ahead of time (enabling ANN); a ranking model can use joint user-item features because it only runs on a few hundred candidates, where per-item compute is affordable. The trade-off is that stage 1 sacrifices some accuracy (no cross features) for the ability to search billions fast, and stage 2 recovers accuracy on the small set -- together achieving both scale and quality that neither could alone. Systems often add more stages (a cheap pre-ranker between them, and a final re-ranker for diversity/business rules). The same pattern appears in web search (cheap retrieval then learning-to-rank) and is the standard answer to 'select-few-from-enormous under latency'. A subtlety: the stages must be co-designed -- if retrieval systematically misses items the ranker would love, no amount of ranking quality recovers them (recall is an upper bound on the final quality), which is why stage-1 recall and candidate-source diversity matter enormously.",
         tags=["two-stage","retrieval-ranking","two-tower","recommendations","why"],
         example="YouTube can't score a billion videos with a deep ranker in 200ms; a two-tower retrieval embeds the user and ANN-searches a precomputed video index to ~500 candidates (fast, high recall), then a heavy multi-task ranker with user-video cross features orders those 500 by predicted watch time (accurate) -- the split is what makes both the latency and the quality achievable."),
    dict(cat="behavioral", title="STAR: Insisting on the right long-term solution over a quick hack (Are Right, A Lot / Insist on Highest Standards)",
         answer="Amazon LPs: ARE RIGHT, A LOT (leaders have strong judgment and seek diverse perspectives to disconfirm their beliefs) and INSIST ON THE HIGHEST STANDARDS. Show you resisted a tempting quick fix, sought data/other views to check yourself, and drove the durable solution -- with a result that validated the judgment.",
         tags=["behavioral","star","are-right-a-lot","highest-standards","amazon-lp"],
         example="SITUATION: A high-severity bug -- duplicate charges under a race condition -- was hitting a small number of customers, and the pressure was to ship a quick guard (a short client-side lock) to stop the bleeding before a big sale. TASK: I owned the payments path and had to both stop the immediate harm AND not entrench a fix that would fail under real concurrency. ACTION: I shipped the quick mitigation to stop customer impact immediately -- but I flagged clearly that it was a band-aid, not the fix, because the real race was server-side and the client lock wouldn't hold under retries or multiple devices. To check my own judgment rather than assume, I pulled the actual failure traces and asked two engineers to poke holes in my analysis; the data confirmed the duplicates came from non-idempotent server writes. I then drove the durable solution: an idempotency key on the charge API with a uniqueness constraint so a retry could never double-charge, plus a test reproducing the concurrency. I made the case to the PM with the trace data that skipping this would just reintroduce the bug at higher volume during the sale. RESULT: We shipped the idempotency fix before the sale; duplicate charges went to zero and stayed there through the peak traffic that would have broken the client-side hack. Seeking the traces and disconfirming views kept me from being confidently wrong, and insisting on the real fix -- while still stopping the bleeding fast -- protected customers when load spiked."),
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

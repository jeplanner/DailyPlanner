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
    dict(cat="dsa", title="Climbing Stairs",
         answer="Count the distinct ways to climb n stairs taking 1 or 2 steps at a time. The count follows Fibonacci: ways(n) = ways(n-1) + ways(n-2), because the last move is either a 1-step (from n-1) or a 2-step (from n-2). Track two rolling values for O(1) space.",
         tags=["climbing-stairs","dynamic-programming","fibonacci","dp","dsa"],
         code='''# Number of distinct ways to climb n stairs taking 1 or 2 steps.
def climb_stairs(n):
    if n <= 2:
        return n
    prev, curr = 1, 2                 # ways to reach step 1 and step 2
    for _ in range(3, n + 1):
        prev, curr = curr, prev + curr   # ways(i) = ways(i-1) + ways(i-2)
    return curr''',
         complexity="Time O(n), space O(1).",
         pitfalls="Off-by-one in the base cases; recomputing recursively without memoization (exponential).",
         example="climb_stairs(5) -> 8."),
    dict(cat="dsa", title="Coin Change (fewest coins)",
         answer="Find the minimum number of coins that make a target amount, or -1 if impossible. Unbounded-knapsack DP: dp[a] is the fewest coins to make amount a; for each amount try each coin and take 1 + dp[a-coin]. Initialize dp[0]=0 and the rest to infinity.",
         tags=["coin-change","dynamic-programming","unbounded-knapsack","dp","dsa"],
         code='''# Fewest coins to make 'amount', or -1 if impossible.
def coin_change(coins, amount):
    dp = [0] + [float('inf')] * amount   # dp[a] = min coins to make a
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1''',
         complexity="Time O(amount * len(coins)), space O(amount).",
         pitfalls="Confusing with counting the NUMBER of ways (different DP); forgetting the -1 impossible case.",
         example="coin_change([1,2,5], 11) -> 3  (5+5+1)."),
    dict(cat="dsa", title="Unique Paths",
         answer="Count the paths from the top-left to bottom-right of an m×n grid moving only right or down. DP where each cell's count is the sum of the cell above and the cell to the left; a single rolling row gives O(n) space. (It's also the binomial coefficient C(m+n-2, m-1).)",
         tags=["unique-paths","dynamic-programming","grid","combinatorics","dp","dsa"],
         code='''# Number of paths from top-left to bottom-right moving only right or down.
def unique_paths(m, n):
    dp = [1] * n                      # dp[j] = paths to the current row's cell j
    for _ in range(1, m):
        for j in range(1, n):
            dp[j] += dp[j - 1]        # from top (dp[j]) + from left (dp[j-1])
    return dp[-1]''',
         complexity="Time O(m*n), space O(n).",
         pitfalls="Wrong base row/column initialization; off-by-one on grid dimensions.",
         example="unique_paths(3, 7) -> 28."),
    dict(cat="dsa", title="Minimum Path Sum",
         answer="Find the minimum sum along a path from the top-left to bottom-right of a grid, moving only right or down. DP where each cell holds the cheapest cost to reach it: the cell value plus the min of the cost from above and from the left. A rolling row keeps space O(cols).",
         tags=["minimum-path-sum","dynamic-programming","grid","dp","dsa"],
         code='''# Minimum sum path from top-left to bottom-right moving right/down.
def min_path_sum(grid):
    rows, cols = len(grid), len(grid[0])
    dp = [0] * cols
    dp[0] = grid[0][0]
    for j in range(1, cols):
        dp[j] = dp[j - 1] + grid[0][j]   # first row: only from the left
    for i in range(1, rows):
        dp[0] += grid[i][0]              # first column: only from above
        for j in range(1, cols):
            dp[j] = min(dp[j], dp[j - 1]) + grid[i][j]
    return dp[-1]''',
         complexity="Time O(rows*cols), space O(cols).",
         pitfalls="Forgetting to seed the first row/column; mixing up which neighbour is 'above' vs 'left'.",
         example="min_path_sum([[1,3,1],[1,5,1],[4,2,1]]) -> 7  (1->3->1->1->1)."),
    dict(cat="dsa", title="Search Insert Position",
         answer="In a sorted array of distinct integers, return the index of a target, or the index where it would be inserted to keep the array sorted. It's exactly a lower-bound binary search (bisect_left): move hi=mid when nums[mid] >= target so you converge on the first position not less than target.",
         tags=["search-insert","binary-search","lower-bound","array","dsa"],
         code='''# Index where target is, or where it would be inserted to stay sorted.
def search_insert(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Using hi=len-1 with the wrong loop condition; returning mid instead of the insertion point.",
         example="search_insert([1,3,5,6], 5) -> 2; search_insert([1,3,5,6], 2) -> 1."),
    dict(cat="dsa", title="Find First and Last Position (sorted array)",
         answer="Find the first and last index of a target in a sorted array with duplicates, in O(log n). Two binary searches: bisect_left gives the first index; bisect_right - 1 gives the last. If the left index is out of range or doesn't hold the target, it isn't present.",
         tags=["search-range","binary-search","bisect","array","dsa"],
         code='''# First and last index of target in a sorted array (two binary searches).
import bisect
def search_range(nums, target):
    left = bisect.bisect_left(nums, target)
    if left == len(nums) or nums[left] != target:
        return [-1, -1]                  # target not present
    right = bisect.bisect_right(nums, target) - 1
    return [left, right]''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Not checking presence after bisect_left; off-by-one converting bisect_right to the last index.",
         example="search_range([5,7,7,8,8,10], 8) -> [3,4]."),
    dict(cat="dsa", title="Summary Ranges",
         answer="Given a sorted array of unique integers, collapse consecutive runs into range strings like 'a->b' (or a single number when the run has length 1). Sweep once, extending each run while the next value is exactly one more, then emit the appropriate string.",
         tags=["summary-ranges","array","two-pointers","string","dsa"],
         code='''# Summarize a sorted unique int array into range strings.
def summary_ranges(nums):
    result = []
    i = 0
    n = len(nums)
    while i < n:
        start = nums[i]
        while i + 1 < n and nums[i + 1] == nums[i] + 1:
            i += 1                       # extend the consecutive run
        if start == nums[i]:
            result.append(str(start))    # a single number
        else:
            result.append(str(start) + "->" + str(nums[i]))
        i += 1
    return result''',
         complexity="Time O(n), space O(1) beyond the output.",
         pitfalls="Off-by-one on run boundaries; emitting 'a->a' for singletons.",
         example="summary_ranges([0,1,2,4,5,7]) -> ['0->2','4->5','7']."),
    dict(cat="dsa", title="Set Mismatch",
         answer="An array should hold 1..n but one number is duplicated and another is missing; find both. A set (or a count array) reveals the value seen twice; scanning 1..n for the absent value gives the missing one. (A math approach using sum and sum-of-squares does it in O(1) space.)",
         tags=["set-mismatch","hash-set","array","dsa"],
         code='''# Find the duplicated number and the missing number in [1..n].
def find_error_nums(nums):
    n = len(nums)
    seen = set()
    duplicate = -1
    for x in nums:
        if x in seen:
            duplicate = x                # this value appears twice
        seen.add(x)
    missing = -1
    for v in range(1, n + 1):
        if v not in seen:
            missing = v                  # this value never appears
            break
    return [duplicate, missing]''',
         complexity="Time O(n), space O(n) (O(1) with the math trick).",
         pitfalls="Assuming the duplicate and missing are related; off-by-one on the 1..n range.",
         example="find_error_nums([1,2,2,4]) -> [2,3]."),
    dict(cat="dsa", title="Single Number III (two uniques)",
         answer="Every element appears twice except TWO that appear once — find both in O(n) time, O(1) space. XOR everything to get a^b (the two singles). A set bit in a^b marks a position where they differ; partition all numbers by that bit and XOR each group to isolate a and b.",
         tags=["single-number","bit-manipulation","xor","array","dsa"],
         code='''# Two elements appear once, all others twice; find both (XOR + bit split).
def single_number_iii(nums):
    xor_all = 0
    for n in nums:
        xor_all ^= n                     # becomes a ^ b (pairs cancel)
    diff = xor_all & (-xor_all)          # lowest bit where a and b differ
    a = b = 0
    for n in nums:
        if n & diff:
            a ^= n                       # group with that bit set
        else:
            b ^= n                       # group without it
    return [a, b]''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not isolating a distinguishing bit; XOR-ing without partitioning (gives only a^b).",
         example="single_number_iii([1,2,1,3,2,5]) -> [3,5]  (order may vary)."),
    dict(cat="dsa", title="Majority Element II (> n/3)",
         answer="Find all elements appearing more than n/3 times — there can be at most two. Extend Boyer-Moore voting to TWO candidates and two counters; a third distinct value decrements both. A final verification pass confirms each candidate actually exceeds n/3 (voting alone can produce false positives here).",
         tags=["majority-element","boyer-moore","voting","array","dsa"],
         code='''# All elements appearing more than n/3 times (at most 2).
def majority_element_ii(nums):
    count1 = count2 = 0
    cand1, cand2 = None, None
    for n in nums:
        if cand1 == n:
            count1 += 1
        elif cand2 == n:
            count2 += 1
        elif count1 == 0:
            cand1, count1 = n, 1
        elif count2 == 0:
            cand2, count2 = n, 1
        else:
            count1 -= 1
            count2 -= 1
    # verify: candidates must truly exceed n/3
    return [c for c in (cand1, cand2) if c is not None and nums.count(c) > len(nums) // 3]''',
         complexity="Time O(n), space O(1).",
         pitfalls="Skipping the verification pass (false positives); mishandling the two-candidate bookkeeping.",
         example="majority_element_ii([1,1,1,3,3,2,2,2]) -> [1,2]."),
    dict(cat="dsa", title="Subsets (power set)",
         answer="Generate every subset (the power set) of a list of distinct integers. Iterative doubling: start with the empty subset, and for each new number append it to copies of all existing subsets — doubling the count each time until all 2^n subsets exist. (Backtracking gives the same result.)",
         tags=["subsets","power-set","backtracking","bit-manipulation","dsa"],
         code='''# All subsets (the power set) of a list of distinct integers.
def subsets(nums):
    result = [[]]
    for num in nums:
        # each existing subset spawns a new one with 'num' added
        result += [subset + [num] for subset in result]
    return result''',
         complexity="Time O(n * 2^n), space O(n * 2^n).",
         pitfalls="Mutating subsets in place instead of copying; expecting a specific ordering.",
         example="subsets([1,2,3]) -> 8 subsets including [], [1], [1,2], [1,2,3]."),
    dict(cat="dsa", title="Letter Combinations of a Phone Number",
         answer="Given digits 2-9, return all letter strings they could spell on an old phone keypad. Build combinations iteratively: start with [''] and, for each digit, replace the running list with every existing prefix extended by each letter that digit maps to (a Cartesian product).",
         tags=["letter-combinations","backtracking","cartesian-product","string","dsa"],
         code='''# All letter combinations a phone-keypad digit string can spell.
def letter_combinations(digits):
    if not digits:
        return []
    mapping = {'2':'abc','3':'def','4':'ghi','5':'jkl',
               '6':'mno','7':'pqrs','8':'tuv','9':'wxyz'}
    result = ['']
    for d in digits:
        result = [prefix + ch for prefix in result for ch in mapping[d]]
    return result''',
         complexity="Time O(4^n) combinations, space O(4^n).",
         pitfalls="Returning [''] for empty input (should be []); wrong keypad mapping for 7 and 9 (4 letters).",
         example="letter_combinations('23') -> ['ad','ae','af','bd','be','bf','cd','ce','cf']."),
    dict(cat="dsa", title="House Robber",
         answer="Maximize the money robbed from a row of houses where you can't rob two ADJACENT houses. DP with two rolling values: at each house choose the max of skipping it (keep curr) or robbing it (prev + money). Classic linear-DP recurrence.",
         tags=["house-robber","dynamic-programming","dp","dsa"],
         code='''# Max money from non-adjacent houses in a row.
def rob(nums):
    prev, curr = 0, 0
    for money in nums:
        prev, curr = curr, max(curr, prev + money)   # skip vs rob this house
    return curr''',
         complexity="Time O(n), space O(1).",
         pitfalls="Robbing adjacent houses (the recurrence prevents it); mishandling the empty list.",
         example="rob([2,7,9,3,1]) -> 12  (2 + 9 + 1)."),
    dict(cat="dsa", title="Maximum Product Subarray",
         answer="Find the largest product of any contiguous subarray. Unlike max-sum, a NEGATIVE number can flip a small (very negative) product into a large one, so track BOTH the running max and running min at each step; a new element may pair best with either. Update both before taking the answer.",
         tags=["max-product-subarray","dynamic-programming","array","dp","dsa"],
         code='''# Largest product of a contiguous subarray (track min and max for negatives).
def max_product(nums):
    best = cur_max = cur_min = nums[0]
    for n in nums[1:]:
        # a negative n swaps the roles of max and min, so consider all three
        candidates = (n, cur_max * n, cur_min * n)
        cur_max = max(candidates)
        cur_min = min(candidates)
        best = max(best, cur_max)
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Tracking only the max (negatives break it); forgetting to consider n alone (restart).",
         example="max_product([2,3,-2,4]) -> 6  ([2,3])."),
    dict(cat="glossary", title="Multicollinearity / VIF",
         answer="Multicollinearity is when two or more features are highly CORRELATED, so a linear model can't separate their individual effects — coefficients become unstable and hard to interpret (though predictions may still be fine). The Variance Inflation Factor (VIF) quantifies it per feature; a VIF above ~5-10 flags trouble. Fix by dropping/combining features or using regularization.",
         tags=["multicollinearity","vif","linear-regression","features","statistics"],
         example="Height-in-cm and height-in-inches are perfectly collinear; a linear model's coefficients on them become arbitrary, VIF explodes — drop one."),
    dict(cat="glossary", title="Cardinality (of a feature)",
         answer="The number of DISTINCT values a feature can take. LOW cardinality (gender, country) one-hot encodes easily; HIGH cardinality (user ID, URL, zip code) blows up dimensionality and causes sparsity/overfitting, needing feature hashing, target encoding, or embeddings. Cardinality drives your encoding choice.",
         tags=["cardinality","features","encoding","high-cardinality"],
         example="A 'country' column (~200 values) one-hot encodes fine; a 'user_id' column (10M values) is high-cardinality and needs an embedding or hashing instead."),
    dict(cat="glossary", title="Imputation strategies",
         answer="Ways to fill MISSING values so models (which usually can't handle NaNs) can train. Simple: mean/median/mode or a constant sentinel. Better: model-based (KNN or regression imputation predicting the value from other features), plus adding a 'was-missing' INDICATOR feature since missingness itself can be informative. Fit imputation on train only.",
         tags=["imputation","missing-data","preprocessing","features"],
         example="For missing income, median-impute and add an 'income_was_missing' flag — the flag lets the model learn that missingness itself correlates with the target."),
    dict(cat="glossary", title="Guardrail metric",
         answer="A metric you monitor in an experiment NOT to improve but to PROTECT — it must not get worse even if your primary metric improves. Guardrails catch harmful side effects of a change (latency, crash rate, unsubscribes, revenue). A launch that boosts clicks but trips a guardrail is blocked.",
         tags=["guardrail-metric","ab-testing","experimentation","metrics"],
         example="A new ranking model raises engagement (primary) but you also watch latency and complaint rate as guardrails — if latency regresses past a threshold, you don't ship."),
    dict(cat="glossary", title="Interleaving (online evaluation)",
         answer="An efficient online evaluation for RANKING where, instead of splitting users into A/B groups, you MERGE two rankers' results into one list for the SAME user and see which ranker's items get more clicks. Because every user compares both systems, it's far more sensitive than A/B testing and needs much less traffic to detect a difference.",
         tags=["interleaving","ranking","online-evaluation","ab-testing"],
         example="To compare two search rankers, interleave their results into one page; whichever contributed more of the clicked results wins — with a fraction of the users an A/B test needs."),
    dict(cat="ml_coding", title="TF-IDF (from scratch)",
         answer="Turn documents into weighted term vectors. TERM FREQUENCY (tf) is how often a term appears in a document (normalized by length); INVERSE DOCUMENT FREQUENCY (idf) down-weights terms common across many documents (log(N / df)). The product tf·idf is high for terms frequent in one document but rare overall — the discriminative words.",
         tags=["tfidf","nlp","text-vectorization","ml-coding"],
         code='''# Compute TF-IDF vectors for a small corpus of tokenized documents.
import math
def tfidf(corpus):
    # corpus: list of documents, each a list of tokens
    n_docs = len(corpus)
    df = {}                                       # document frequency per term
    for doc in corpus:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    vectors = []
    for doc in corpus:
        counts = {}
        for term in doc:
            counts[term] = counts.get(term, 0) + 1
        vec = {}
        for term, cnt in counts.items():
            tf = cnt / len(doc)                   # term frequency
            idf = math.log(n_docs / df[term])     # inverse document frequency
            vec[term] = tf * idf
        vectors.append(vec)
    return vectors''',
         complexity="Time O(total tokens), space O(vocab * docs).",
         pitfalls="Dividing by zero for out-of-corpus terms; idf=0 for terms in every document (log(1)).",
         example="For [['the','cat'],['the','dog']], 'the' gets weight 0 (idf=log 1) while 'cat'/'dog' get positive weights."),
    dict(cat="ml_system_design", title="Design a Lead Scoring system",
         answer="Rank sales LEADS by likelihood to convert so reps focus on the best. (1) CLARIFY & SCALE: prioritize finite sales capacity with a probability/score per lead; the real goal is more closed deals per rep-hour. (2) DATA & LABELS: historical leads labeled converted/not over a window; mind label delay and that reps only worked SOME leads (selection bias). (3) FEATURES: firmographics (company size, industry), behavioural (site visits, email opens, demo requests), source/channel, engagement recency. (4) MODEL: gradient-boosted trees outputting a calibrated conversion probability. (5) EVAL: AUC/PR-AUC plus precision/recall at the top-k leads reps can actually call, and lift over random calling. (6) SERVING/MONITORING/AB: score leads as they arrive, route high scores to reps with an explanation, A/B TEST whether score-driven prioritization lifts conversions versus the old process, and monitor drift and feedback loops.",
         tags=["lead-scoring","conversion","gradient-boosting","sales","ml-system-design"],
         example="A lead that requested a demo, visited pricing 3x, and is from a 500-person company scores 0.72; it's routed to a rep immediately, and an A/B test confirms score-prioritized calling closes more deals than chronological order."),
    dict(cat="conceptual", title="Why does more/better data often beat a fancier algorithm?",
         answer="Because most real-world error comes from the DATA, not the model class. More representative data reduces variance and covers edge cases an algorithm can't invent; better labels and features fix systematic errors no tuning will. Simple models on large data often beat sophisticated models on small data ('the unreasonable effectiveness of data'). The caveats: this holds until you hit data-quality or irreducible-noise limits, and some structured problems truly need the right inductive bias. Practically: invest in data coverage, labels, features, and leakage-free splits before chasing exotic models.",
         tags=["data-centric","more-data","generalization","why"],
         example="A plain logistic regression on 10M clean, well-featured examples usually beats a deep net on 10k noisy ones — collecting representative data moved the needle more than swapping the model."),
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

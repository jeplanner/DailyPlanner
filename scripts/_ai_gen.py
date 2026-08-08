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
    dict(cat="dsa", title="Edit Distance (Levenshtein DP)",
         answer="Minimum number of single-character edits (insert, delete, replace) to turn string a into string b. Classic 2-D DP: dp[i][j] is the distance between the first i chars of a and first j of b. If the current chars match, carry the diagonal; else 1 + the min of delete (up), insert (left), and replace (diagonal). Base cases turn a prefix into the empty string.",
         tags=["edit-distance","levenshtein","dynamic-programming","string","dp","dsa"],
         code='''# Minimum single-char edits (insert/delete/replace) to turn a into b.
def edit_distance(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i            # delete all i chars of a
    for j in range(n + 1):
        dp[0][j] = j            # insert all j chars of b
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1]        # chars match -> no cost
            else:
                dp[i][j] = 1 + min(dp[i-1][j],     # delete from a
                                   dp[i][j-1],     # insert into a
                                   dp[i-1][j-1])   # replace
    return dp[m][n]''',
         complexity="Time O(m*n), space O(m*n) (reducible to O(n)).",
         pitfalls="Forgetting the base-case row/column; mixing up which neighbour is insert vs delete.",
         example="edit_distance('horse','ros') -> 3  (horse->rorse->rose->ros)."),
    dict(cat="dsa", title="Longest Common Subsequence (DP)",
         answer="Find the length of the longest subsequence common to two strings (characters in order but not necessarily contiguous). 2-D DP: if the current characters match, extend the diagonal by 1; otherwise take the better of dropping one character from either string. The backbone of diff tools and DNA alignment.",
         tags=["longest-common-subsequence","lcs","dynamic-programming","string","dp","dsa"],
         code='''# Length of the longest common subsequence of two strings.
def longest_common_subsequence(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1    # extend the common subsequence
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])  # drop one character
    return dp[m][n]''',
         complexity="Time O(m*n), space O(m*n).",
         pitfalls="Confusing subsequence (order kept, gaps allowed) with substring (contiguous); off-by-one indexing into the strings.",
         example="longest_common_subsequence('abcde','ace') -> 3  ('ace')."),
    dict(cat="dsa", title="Coin Change II (number of ways)",
         answer="Count the number of distinct combinations of coins (each denomination usable unlimited times) that sum to a target amount. Unbounded-knapsack DP: iterate COINS in the outer loop and amounts inner — this counts combinations (order-independent) rather than permutations. dp[a] += dp[a-coin].",
         tags=["coin-change","dynamic-programming","unbounded-knapsack","dp","dsa"],
         code='''# Number of ways to make 'amount' using unlimited coins of each value.
def change(amount, coins):
    dp = [0] * (amount + 1)
    dp[0] = 1                    # one way to make 0: use nothing
    for coin in coins:          # coins OUTSIDE -> count combinations, not perms
        for a in range(coin, amount + 1):
            dp[a] += dp[a - coin]   # add the ways that use this coin
    return dp[amount]''',
         complexity="Time O(amount * len(coins)), space O(amount).",
         pitfalls="Swapping the loop order (counts permutations, over-counts); forgetting dp[0]=1.",
         example="change(5, [1,2,5]) -> 4  (5 | 2+2+1 | 2+1+1+1 | 1+1+1+1+1)."),
    dict(cat="dsa", title="Partition Equal Subset Sum",
         answer="Decide whether an array can be split into two subsets with equal sums. If the total is odd it's impossible; otherwise it reduces to a SUBSET-SUM problem: can any subset reach total/2? Use a boolean DP over achievable sums, iterating each number and updating sums from high to low so each number is used at most once.",
         tags=["partition-equal-subset","subset-sum","dynamic-programming","0-1-knapsack","dp","dsa"],
         code='''# Can the array be split into two subsets with equal sum? (subset-sum DP)
def can_partition(nums):
    total = sum(nums)
    if total % 2 != 0:
        return False            # an odd total can't split evenly
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True                # a sum of 0 is always achievable
    for num in nums:
        for s in range(target, num - 1, -1):   # go DOWN so each num is used once
            dp[s] = dp[s] or dp[s - num]
    return dp[target]''',
         complexity="Time O(n * target), space O(target).",
         pitfalls="Iterating sums upward (lets a number be reused); forgetting the odd-total shortcut.",
         example="can_partition([1,5,11,5]) -> True  ([1,5,5] and [11], each summing to 11)."),
    dict(cat="dsa", title="Longest Palindromic Substring (expand around center)",
         answer="Find the longest contiguous substring that reads the same forwards and backwards. For each of the 2n-1 possible centers (each character, and each gap between characters), expand outward while the two ends match, tracking the widest palindrome found. Simple O(n^2) time, O(1) space — no DP table needed.",
         tags=["longest-palindromic-substring","expand-around-center","string","two-pointers","dsa"],
         code='''# Longest substring of s that is a palindrome (expand around center).
def longest_palindrome(s):
    if not s:
        return ""
    start, end = 0, 0
    def expand(left, right):
        while left >= 0 and right < len(s) and s[left] == s[right]:
            left -= 1; right += 1
        return left + 1, right - 1        # last valid palindrome bounds
    for i in range(len(s)):
        l1, r1 = expand(i, i)             # odd-length center at i
        l2, r2 = expand(i, i + 1)         # even-length center between i, i+1
        if r1 - l1 > end - start:
            start, end = l1, r1
        if r2 - l2 > end - start:
            start, end = l2, r2
    return s[start:end + 1]''',
         complexity="Time O(n^2), space O(1).",
         pitfalls="Handling only odd centers (misses even palindromes); off-by-one when returning the bounds after the loop overshoots.",
         example="longest_palindrome('babad') -> 'bab'  (or 'aba')."),
    dict(cat="dsa", title="Kth Smallest Element in a BST",
         answer="Return the kth smallest value in a Binary Search Tree. An IN-ORDER traversal of a BST visits values in sorted order, so do an iterative in-order walk (go left as far as possible using a stack, visit, then go right) and stop at the kth visited node. No need to traverse the whole tree.",
         tags=["kth-smallest-bst","bst","in-order","stack","binary-tree","dsa"],
         code='''# The kth smallest value via in-order traversal (BST in-order = sorted).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def kth_smallest(root, k):
    stack = []
    node = root
    while stack or node:
        while node:               # go as far left as possible
            stack.append(node)
            node = node.left
        node = stack.pop()        # the smallest unvisited node
        k -= 1
        if k == 0:
            return node.val       # this is the kth smallest
        node = node.right         # then explore its right subtree
    return -1''',
         complexity="Time O(h + k), space O(h) for the stack.",
         pitfalls="Traversing the entire tree (stop early at k); decrementing k in the wrong place.",
         example="For a BST built from [3,1,4,2], kth_smallest(root, 1) -> 1 and kth_smallest(root, 2) -> 2."),
    dict(cat="ml_coding", title="Precision, Recall & F1 (from scratch)",
         answer="Core classification metrics from raw predictions. PRECISION = of everything predicted positive, how much was right (TP/(TP+FP)). RECALL = of all actual positives, how many were caught (TP/(TP+FN)). F1 = harmonic mean of the two, punishing an imbalance between them. Guard against divide-by-zero when a denominator is 0.",
         tags=["precision","recall","f1","metrics","classification","ml-coding"],
         code='''# Precision, recall, and F1 from true and predicted binary labels.
def precision_recall_f1(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0   # of predicted positives
    recall = tp / (tp + fn) if (tp + fn) else 0.0      # of actual positives
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)            # harmonic mean
    return precision, recall, f1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing by zero when there are no positive predictions/labels; confusing precision with recall.",
         example="precision_recall_f1([1,1,0,0],[1,0,0,0]) -> (1.0, 0.5, 0.667)."),
    dict(cat="ml_coding", title="Confusion Matrix (from scratch)",
         answer="Tally the four outcomes of binary classification: true positives, false positives, true negatives, false negatives. Every other metric (precision, recall, accuracy, specificity) is derived from these four counts, so it's the foundation for evaluating a classifier.",
         tags=["confusion-matrix","metrics","classification","evaluation","ml-coding"],
         code='''# 2x2 confusion-matrix counts for binary labels.
def confusion_matrix(y_true, y_pred):
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == 1 and p == 1:
            tp += 1     # correctly predicted positive
        elif t == 0 and p == 1:
            fp += 1     # false alarm
        elif t == 0 and p == 0:
            tn += 1     # correctly predicted negative
        else:
            fn += 1     # missed a positive
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}''',
         complexity="Time O(n), space O(1).",
         pitfalls="Swapping FP and FN (a common source of metric bugs); assuming labels are 0/1 when they might be strings.",
         example="confusion_matrix([1,0,1,0],[1,0,0,0]) -> {'tp':1,'fp':0,'tn':2,'fn':1}."),
    dict(cat="ml_coding", title="ROC AUC (rank-based, from scratch)",
         answer="Area Under the ROC Curve measures how well scores rank positives above negatives; 1.0 is perfect, 0.5 is random. Instead of integrating the curve, use the equivalent Mann-Whitney formulation: sort by score, sum the ranks of the positive examples, and normalize. It equals the probability a random positive outranks a random negative.",
         tags=["auc","roc","ranking","metrics","evaluation","ml-coding"],
         code='''# Area under the ROC curve via the rank-based (Mann-Whitney) formula.
def roc_auc(y_true, scores):
    paired = sorted(zip(scores, y_true))      # sort by score ascending
    pos = sum(1 for t in y_true if t == 1)
    neg = len(y_true) - pos
    if pos == 0 or neg == 0:
        return 0.0                            # AUC undefined with one class
    rank_sum = 0
    for rank, (s, label) in enumerate(paired, start=1):
        if label == 1:
            rank_sum += rank                  # sum ranks of positive examples
    # Mann-Whitney U converted to AUC
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)''',
         complexity="Time O(n log n) for the sort, space O(n).",
         pitfalls="Not handling all-one-class inputs; tied scores need average ranks for exactness.",
         example="roc_auc([0,0,1,1],[0.1,0.4,0.35,0.8]) -> 0.75."),
    dict(cat="glossary", title="Retrieval-Augmented Generation (RAG)",
         answer="A technique that combines a language model with an external knowledge store. At query time it RETRIEVES relevant documents (via embedding similarity search over a vector database) and feeds them into the model's context, so the model answers from up-to-date, source-grounded facts rather than only its frozen parameters. It reduces hallucination and lets you update knowledge without retraining.",
         tags=["rag","retrieval-augmented-generation","llm","vector-database","grounding"],
         example="A support bot embeds the user's question, retrieves the 5 most relevant help-center articles from a vector DB, and prompts the LLM to answer using them — citing current docs instead of guessing."),
    dict(cat="glossary", title="Hallucination (LLMs)",
         answer="When a language model generates fluent, confident text that is FACTUALLY WRONG or unsupported — inventing citations, numbers, or events. It happens because the model predicts plausible next tokens, not verified truth. Mitigations include retrieval grounding (RAG), asking for sources, lowering temperature, and adding verification steps.",
         tags=["hallucination","llm","reliability","factuality"],
         example="Asked for a citation, an LLM may fabricate a real-sounding paper title, authors, and year that don't actually exist — a hallucination."),
    dict(cat="glossary", title="Temperature (sampling)",
         answer="A knob controlling randomness when a model samples the next token. Logits are divided by the temperature T before softmax: T<1 SHARPENS the distribution (more deterministic, safe), T>1 FLATTENS it (more diverse and creative but riskier), and T->0 approaches greedy decoding. It trades coherence against variety.",
         tags=["temperature","sampling","decoding","llm","generation"],
         example="At temperature 0.2 a model gives near-identical safe answers; at 1.2 it produces varied, creative — but occasionally incoherent — completions."),
    dict(cat="glossary", title="Top-p (nucleus) sampling",
         answer="A decoding method that samples the next token from the SMALLEST set of tokens whose cumulative probability exceeds a threshold p (e.g. 0.9), then renormalizes over that set. Unlike top-k (a fixed count), the nucleus adapts: it's wide when the model is uncertain and narrow when it's confident — avoiding both bland and nonsensical output.",
         tags=["top-p","nucleus-sampling","decoding","llm","generation"],
         example="With top-p=0.9, if one token already holds 0.92 probability the model almost always picks it; if probability is spread out, it considers many candidates."),
    dict(cat="conceptual", title="Why train classifiers with cross-entropy loss instead of accuracy?",
         answer="Accuracy is a step function of the predictions — flat almost everywhere and jumping at decision boundaries — so its gradient is zero or undefined and you can't do gradient descent on it. Cross-entropy is a smooth, DIFFERENTIABLE surrogate with a useful gradient everywhere: it rewards not just the correct class but CONFIDENCE in it, pushing predicted probabilities toward the truth. It's also convex for linear models and better calibrated. You still REPORT accuracy, but you OPTIMIZE the differentiable proxy.",
         tags=["cross-entropy","loss","optimization","gradient","why"],
         example="If the true label is class 1 and the model outputs 0.51 vs 0.99, accuracy is identical (both correct) but cross-entropy is far lower for 0.99 — giving a gradient that keeps improving confidence, which accuracy never would."),
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

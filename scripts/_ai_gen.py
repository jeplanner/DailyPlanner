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
    dict(cat="dsa", title="Clone Graph (DFS)",
         answer="Deep-copy a connected undirected graph. DFS from the start node, keeping a map from each ORIGINAL node to its CLONE. Register the clone in the map BEFORE recursing into neighbours — that's what stops infinite loops on cycles. Each neighbour's clone is fetched from the map or created on first visit.",
         tags=["clone-graph","dfs","graph","hash-map","dsa"],
         code='''# Deep-copy a connected undirected graph via DFS with a visited map.
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []

def clone_graph(node):
    if node is None:
        return None
    cloned = {}                        # original node -> its clone
    def dfs(cur):
        if cur in cloned:
            return cloned[cur]          # already copied -> reuse it
        copy = Node(cur.val)            # make the clone first
        cloned[cur] = copy              # register BEFORE recursing (cycles!)
        for nb in cur.neighbors:
            copy.neighbors.append(dfs(nb))  # clone each neighbour
        return copy
    return dfs(node)''',
         complexity="Time O(V+E), space O(V).",
         pitfalls="Registering the clone AFTER recursing (infinite loop on cycles); sharing neighbour lists with the original.",
         example="Cloning a triangle A-B-C yields three brand-new Node objects with the same values and edges."),
    dict(cat="dsa", title="Word Search (backtracking)",
         answer="Return True if a word can be traced through a grid by moving to adjacent (up/down/left/right) cells, using each cell at most once. From every starting cell, backtrack letter by letter: mark the current cell visited, try all four directions for the next letter, then restore the cell so other paths can use it.",
         tags=["word-search","backtracking","grid","dfs","dsa"],
         code='''# True if 'word' can be traced in the grid via adjacent cells (no reuse).
def exist(board, word):
    if not board:
        return False
    rows, cols = len(board), len(board[0])
    def backtrack(r, c, i):
        if i == len(word):
            return True                 # matched every letter
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:
            return False                # off-grid or wrong letter
        tmp = board[r][c]
        board[r][c] = '#'               # mark visited so we don't reuse it
        found = (backtrack(r+1, c, i+1) or backtrack(r-1, c, i+1) or
                 backtrack(r, c+1, i+1) or backtrack(r, c-1, i+1))
        board[r][c] = tmp               # restore for other paths
        return found
    for r in range(rows):
        for c in range(cols):
            if backtrack(r, c, 0):
                return True
    return False''',
         complexity="Time O(rows*cols*4^L) worst case (L=word length), space O(L).",
         pitfalls="Not restoring the cell after backtracking; reusing a cell within one path.",
         example="exist([['A','B','C'],['S','F','C'],['A','D','E']], 'ABCCED') -> True."),
    dict(cat="dsa", title="Subsets II (with duplicates)",
         answer="Generate all UNIQUE subsets of a list that may contain duplicate values. Sort first so duplicates are adjacent; then in the backtracking loop, skip a value if it equals the previous one AT THE SAME DEPTH (i > start) — that avoids generating the same subset twice.",
         tags=["subsets","backtracking","deduplication","dsa"],
         code='''# All unique subsets of a list that may contain duplicates.
def subsets_with_dup(nums):
    nums.sort()                         # group duplicates together
    result = []
    def backtrack(start, path):
        result.append(path[:])          # every prefix is a valid subset
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i-1]:
                continue                # skip a duplicate at the same depth
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()                  # undo the choice
    backtrack(0, [])
    return result''',
         complexity="Time O(n * 2^n), space O(n) recursion.",
         pitfalls="Forgetting to sort (dup skip fails); using i>0 instead of i>start (skips valid subsets).",
         example="subsets_with_dup([1,2,2]) -> [[],[1],[1,2],[1,2,2],[2],[2,2]]."),
    dict(cat="dsa", title="Combination Sum (reusable candidates)",
         answer="Find all combinations of candidates that sum to a target, where each candidate may be used unlimited times. Backtrack: at each step try every candidate from 'start' onward, subtracting it from the remaining target; recurse with the SAME index i (so it can be reused). Prune when remaining goes negative.",
         tags=["combination-sum","backtracking","dsa"],
         code='''# All combinations of candidates (reusable) that sum to target.
def combination_sum(candidates, target):
    result = []
    def backtrack(start, remaining, path):
        if remaining == 0:
            result.append(path[:])      # exact hit -> record it
            return
        if remaining < 0:
            return                      # overshoot -> prune
        for i in range(start, len(candidates)):
            path.append(candidates[i])
            # pass 'i' (not i+1) so the same number can be reused
            backtrack(i, remaining - candidates[i], path)
            path.pop()
    backtrack(0, target, [])
    return result''',
         complexity="Exponential in the number of combinations; space O(target/min) recursion.",
         pitfalls="Passing i+1 (forbids reuse); not pruning on negative remaining (slow).",
         example="combination_sum([2,3,6,7], 7) -> [[2,2,3],[7]]."),
    dict(cat="dsa", title="Minimum Window Substring (sliding window)",
         answer="Find the smallest substring of s that contains every character of t (with multiplicity). Expand a right pointer, counting how many required chars are still 'missing'; once the window covers all of t (missing==0), shrink from the left to minimize it, recording the best window seen.",
         tags=["minimum-window-substring","sliding-window","string","hard","dsa"],
         code='''# Smallest substring of s that contains all chars of t (with multiplicity).
from collections import Counter
def min_window(s, t):
    if not s or not t:
        return ""
    need = Counter(t)                   # counts of chars still required
    missing = len(t)                    # total required chars not yet covered
    left = start = 0
    end = float('inf')
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1                # covered one required char
        need[ch] -= 1                   # (can go negative for extras)
        while missing == 0:             # window covers all of t
            if right - left < end - start:
                start, end = left, right   # record a smaller window
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1            # dropped a required char -> stop
            left += 1
    return "" if end == float('inf') else s[start:end + 1]''',
         complexity="Time O(len(s) + len(t)), space O(unique chars in t).",
         pitfalls="Off-by-one on the returned slice; incrementing 'missing' only when a needed char is dropped.",
         example="min_window('ADOBECODEBANC','ABC') -> 'BANC'."),
    dict(cat="dsa", title="Lowest Common Ancestor of a BST",
         answer="Find the deepest node that is an ancestor of both p and q in a Binary Search Tree. Use the BST ordering: from the root, if both values are smaller go left, if both larger go right; the FIRST node where they split (one on each side, or equal to the node) is the LCA. Iterative, no extra space.",
         tags=["lowest-common-ancestor","bst","binary-tree","dsa"],
         code='''# Lowest common ancestor of p and q in a Binary Search Tree.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def lowest_common_ancestor(root, p, q):
    node = root
    while node:
        if p.val < node.val and q.val < node.val:
            node = node.left            # both smaller -> go left
        elif p.val > node.val and q.val > node.val:
            node = node.right           # both larger -> go right
        else:
            return node                 # they split here -> this is the LCA
    return None''',
         complexity="Time O(h) where h is tree height, space O(1).",
         pitfalls="Using the general-tree LCA (ignores BST order, slower); off-by-one when p or q equals the node.",
         example="In a BST rooted at 6: LCA(2, 8) = 6; LCA(2, 4) = 2."),
    dict(cat="dsa", title="Quickselect (kth largest)",
         answer="Find the kth largest element in O(n) AVERAGE time without fully sorting. Partition the array around a pivot (Lomuto): elements smaller go left, the pivot lands at its final sorted index. If that index is the target (n-k), you're done; otherwise recurse into only the side that contains the target. This is the selection cousin of quicksort.",
         tags=["quickselect","partition","selection","array","dsa"],
         code='''# Find the kth largest element in O(n) average time (Lomuto partition).
def find_kth_largest(nums, k):
    target = len(nums) - k              # kth largest sits here once sorted
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        pivot = nums[hi]                # choose the last element as pivot
        p = lo
        for i in range(lo, hi):
            if nums[i] < pivot:
                nums[i], nums[p] = nums[p], nums[i]  # push smaller left
                p += 1
        nums[p], nums[hi] = nums[hi], nums[p]        # put pivot in place
        if p == target:
            return nums[p]              # pivot landed on the answer
        if p < target:
            lo = p + 1                  # answer is to the right
        else:
            hi = p - 1                  # answer is to the left
    return -1''',
         complexity="Average O(n), worst O(n^2); space O(1).",
         pitfalls="Off-by-one mapping kth-largest to index n-k; worst-case pivots (shuffle or median-of-three to mitigate).",
         example="find_kth_largest([3,2,1,5,6,4], 2) -> 5."),
    dict(cat="dsa", title="Quick Sort",
         answer="The classic in-place divide-and-conquer sort. Pick a pivot, PARTITION so smaller elements go left and larger go right (Lomuto scheme places the pivot at its final index), then recursively sort each side. O(n log n) average with small constants and no extra array, but O(n^2) worst case on bad pivots and NOT stable.",
         tags=["quick-sort","divide-and-conquer","sorting","in-place","dsa"],
         code='''# Classic in-place quicksort with the Lomuto partition scheme.
def quick_sort(a):
    def partition(lo, hi):
        pivot = a[hi]                   # last element as the pivot
        p = lo
        for i in range(lo, hi):
            if a[i] < pivot:
                a[i], a[p] = a[p], a[i] # move smaller elements to the left
                p += 1
        a[p], a[hi] = a[hi], a[p]       # place pivot at its sorted position
        return p
    def qs(lo, hi):
        if lo < hi:
            mid = partition(lo, hi)
            qs(lo, mid - 1)             # sort the left partition
            qs(mid + 1, hi)             # sort the right partition
    qs(0, len(a) - 1)
    return a''',
         complexity="Average O(n log n), worst O(n^2); space O(log n) recursion.",
         pitfalls="Already-sorted input causes worst case with a fixed last pivot; it is not stable.",
         example="quick_sort([5,2,4,1,3]) -> [1,2,3,4,5]."),
    dict(cat="glossary", title="Silhouette score",
         answer="A metric to judge clustering quality WITHOUT labels. For each point it compares closeness to its own cluster (cohesion a) vs the nearest other cluster (separation b): score = (b - a) / max(a, b), ranging -1 to +1. Near +1 = well clustered; near 0 = on a boundary; negative = probably in the wrong cluster. Average over all points to compare different k.",
         tags=["silhouette-score","clustering","evaluation","unsupervised"],
         example="Trying k=2,3,4 for k-means, you pick the k with the highest average silhouette — say 0.7 at k=3 beats 0.5 at k=2."),
    dict(cat="glossary", title="Elbow method",
         answer="A heuristic for choosing the number of clusters k. Plot the within-cluster sum of squared distances (inertia) against k: it always drops as k grows, but at some 'elbow' the improvement flattens. That elbow is a good k — more clusters past it barely help. It's visual and subjective, often paired with the silhouette score.",
         tags=["elbow-method","clustering","k-means","model-selection"],
         example="Inertia falls sharply from k=1 to 3 then levels off; the bend at k=3 suggests three natural clusters."),
    dict(cat="glossary", title="Triplet loss",
         answer="A loss for learning EMBEDDINGS where similar items sit close and dissimilar ones far apart. It uses a triplet (anchor, positive, negative) and pushes the anchor closer to the positive than to the negative by at least a margin: max(0, d(a,p) - d(a,n) + margin). It powers face recognition and metric learning.",
         tags=["triplet-loss","embeddings","metric-learning","loss"],
         example="For face recognition, the anchor and a positive (same person) are pulled together while a negative (different person) is pushed away by a margin."),
    dict(cat="glossary", title="Hinge loss",
         answer="The loss behind support-vector machines. For a label y in {-1,+1} and score s, hinge loss = max(0, 1 - y*s): zero when the prediction is correct AND confident (beyond the margin), otherwise growing linearly. It creates a MARGIN, penalizing points that are correct but sit too close to the decision boundary.",
         tags=["hinge-loss","svm","margin","loss","classification"],
         example="A point correctly classified with score 2 (y=+1) has loss 0; one with score 0.3 still incurs loss 0.7 for sitting inside the margin."),
    dict(cat="glossary", title="Isolation forest",
         answer="An unsupervised anomaly-detection algorithm. It builds random trees that split on random features/values; ANOMALIES get isolated in fewer splits (shorter tree paths) because they're rare and different. The average path length across trees scores how anomalous a point is. Fast and scalable — great for fraud and outlier detection.",
         tags=["isolation-forest","anomaly-detection","unsupervised","trees"],
         example="In card transactions, a fraudulent outlier gets separated after a couple of random splits while normal transactions need many — flagging the fraud."),
    dict(cat="glossary", title="Curriculum learning",
         answer="A training strategy that presents examples in a MEANINGFUL ORDER — easy first, then progressively harder — mimicking how humans learn. It can speed convergence and improve final accuracy versus random ordering, especially on hard tasks, because early easy examples steer the model into a good region before the difficult ones.",
         tags=["curriculum-learning","training","optimization","deep-learning"],
         example="Training a translation model on short simple sentences first, then long complex ones, often converges faster than shuffling all lengths together."),
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

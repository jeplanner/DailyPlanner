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
    dict(cat="dsa", title="Binary Tree Right Side View",
         answer="Return the values visible from the RIGHT side of a binary tree, top to bottom — i.e. the last node in each level. Do a BFS level-order traversal and record the final node dequeued in each level. (A right-first DFS tracking depth also works.)",
         tags=["right-side-view","bfs","binary-tree","level-order","dsa"],
         code='''# The values visible from the right side of a binary tree, top to bottom.
from collections import deque
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def right_side_view(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        n = len(queue)
        for i in range(n):
            node = queue.popleft()
            if i == n - 1:               # last node of this level = rightmost
                result.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Taking the rightmost child instead of the last node in the level (a left child can be rightmost if the right side is short).",
         example="right_side_view of 1 -> (2 -> (_,5), 3 -> (_,4)) gives [1,3,4]."),
    dict(cat="dsa", title="Sum Root to Leaf Numbers",
         answer="Each root-to-leaf path spells a number (root is the most significant digit); return the sum of all such numbers. DFS carrying the running number: at each node do current = current*10 + node.val, and when you hit a leaf add the completed number to the total.",
         tags=["sum-root-to-leaf","binary-tree","dfs","recursion","dsa"],
         code='''# Sum of all root-to-leaf numbers, each path read as a digit string.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def sum_numbers(root):
    def dfs(node, current):
        if node is None:
            return 0
        current = current * 10 + node.val    # extend the number by one digit
        if node.left is None and node.right is None:
            return current                   # a leaf completes one number
        return dfs(node.left, current) + dfs(node.right, current)
    return dfs(root, 0)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Adding at every node instead of only at leaves; not resetting the number per path (recursion handles this).",
         example="For the tree 1 -> (2, 3), the numbers are 12 and 13, summing to 25."),
    dict(cat="dsa", title="Count Good Nodes in a Binary Tree",
         answer="A node is 'good' if no node on the path from the root down to it has a GREATER value. Count them with a DFS that carries the maximum value seen on the current path: a node is good when its value is >= that running max, and you pass the updated max down to its children.",
         tags=["count-good-nodes","binary-tree","dfs","recursion","dsa"],
         code='''# A node is 'good' if no node on the root->node path is greater than it.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def good_nodes(root):
    def dfs(node, max_so_far):
        if node is None:
            return 0
        good = 1 if node.val >= max_so_far else 0    # >= path max -> good
        new_max = max(max_so_far, node.val)
        return good + dfs(node.left, new_max) + dfs(node.right, new_max)
    return dfs(root, float('-inf'))''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Using > instead of >= (the root and ties must count); not updating the max before recursing.",
         example="For 3 -> (1 -> 3, 4 -> (1, 5)), there are 4 good nodes (3, the deeper 3, 4, and 5)."),
    dict(cat="dsa", title="Subtree of Another Tree",
         answer="Check whether a tree contains a subtree that is IDENTICAL (structure and values) to a given smaller tree. At each node of the big tree, test whether the subtree rooted there equals the target using a same-tree helper; otherwise recurse into the children.",
         tags=["subtree","binary-tree","recursion","dfs","dsa"],
         code='''# Does 'root' contain a subtree identical to 'sub'?
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def is_subtree(root, sub):
    def same(a, b):
        if a is None and b is None:
            return True
        if a is None or b is None or a.val != b.val:
            return False
        return same(a.left, b.left) and same(a.right, b.right)
    if root is None:
        return False
    if same(root, sub):                  # does a match start right here?
        return True
    return is_subtree(root.left, sub) or is_subtree(root.right, sub)''',
         complexity="Time O(m*n) worst case, space O(h).",
         pitfalls="Matching only values without full structure; treating a partial (non-leaf-aligned) match as success.",
         example="root 3 -> (4 -> (1,2), 5) contains sub 4 -> (1,2) -> True."),
    dict(cat="dsa", title="Construct Binary Tree from Preorder and Inorder",
         answer="Rebuild a unique binary tree from its preorder and inorder traversals. The FIRST preorder value is the root; its position in inorder splits the inorder into left and right subtrees. Consume preorder left-to-right (a moving pointer) and recurse on the inorder index ranges. A value->index map makes the split O(1).",
         tags=["construct-tree","preorder","inorder","recursion","divide-and-conquer","dsa"],
         code='''# Rebuild a binary tree from its preorder and inorder traversals.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def build_tree(preorder, inorder):
    idx = {v: i for i, v in enumerate(inorder)}   # value -> index in inorder
    pos = [0]                                       # pointer into preorder
    def build(lo, hi):
        if lo > hi:
            return None
        root_val = preorder[pos[0]]
        pos[0] += 1
        root = TreeNode(root_val)
        mid = idx[root_val]                         # split inorder at the root
        root.left = build(lo, mid - 1)              # left first (preorder order)
        root.right = build(mid + 1, hi)
        return root
    return build(0, len(inorder) - 1)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Building the right subtree before the left (breaks the preorder pointer); assuming duplicate values (indices become ambiguous).",
         example="preorder [3,9,20,15,7], inorder [9,3,15,20,7] rebuilds the tree with root 3, left 9, right 20 -> (15,7)."),
    dict(cat="dsa", title="Binary Tree Maximum Path Sum",
         answer="Find the maximum sum of any path (from any node to any node, following parent-child edges) in a binary tree. Post-order DFS: each node returns the best DOWNWARD gain (its value plus the larger positive child gain); meanwhile track a global best that may 'turn' through a node using BOTH children. Clamp negative gains to 0.",
         tags=["max-path-sum","binary-tree","dfs","recursion","hard","dsa"],
         code='''# Maximum sum of any node-to-node path in a binary tree.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def max_path_sum(root):
    best = float('-inf')
    def gain(node):
        nonlocal best
        if node is None:
            return 0
        left = max(gain(node.left), 0)    # drop negative contributions
        right = max(gain(node.right), 0)
        best = max(best, node.val + left + right)   # path turning through node
        return node.val + max(left, right)          # best straight-down gain
    gain(root)
    return best''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Returning left+right upward (a path can't split then continue); forgetting to clamp negatives to 0.",
         example="For -10 -> (9, 20 -> (15, 7)), the best path is 15+20+7 = 42."),
    dict(cat="glossary", title="BLEU",
         answer="A metric for machine translation (and other generation) that measures how much the model's output OVERLAPS with reference translations via n-gram precision (n=1..4), with a BREVITY PENALTY so it can't win by being too short. It ranges 0-100; higher is closer to the references. It rewards exact n-gram matches, not meaning.",
         tags=["bleu","machine-translation","evaluation","metric","nlp"],
         example="If the reference is 'the cat is on the mat' and the model outputs 'the cat is on mat', BLEU counts the matching 1-4 grams and applies a brevity penalty for the missing word."),
    dict(cat="glossary", title="Target leakage",
         answer="When information that won't be available at prediction time (or that encodes the label itself) sneaks into the training features, producing amazing offline scores that collapse in production. It's a top cause of 'too good to be true' models. Prevent it with strict point-in-time feature construction and by asking 'would I actually know this at prediction time?'",
         tags=["target-leakage","data-leakage","features","mlops","pitfall"],
         example="Including 'account_closed_date' to predict churn leaks the answer — that date only exists after churn, so the model looks perfect offline but is useless live."),
    dict(cat="glossary", title="Mean Reciprocal Rank (MRR)",
         answer="A ranking metric focused on the position of the FIRST relevant result. For each query take 1/(rank of the first correct item), then average across queries. It rewards putting a right answer high and is ideal when there's a single correct answer, like question answering or 'I'm feeling lucky' search.",
         tags=["mrr","ranking","evaluation","metric","information-retrieval"],
         example="If the correct answer is at rank 2 for one query (1/2) and rank 1 for another (1/1), MRR = (0.5 + 1)/2 = 0.75."),
    dict(cat="glossary", title="Recall@k",
         answer="Of all the relevant items for a query, the fraction that appear in the top-k retrieved results. It measures how much of the good stuff your retrieval CAPTURES within a cutoff — crucial for the candidate-generation stage of search/recommendations, where missing relevant items before a precise re-ranker is costly.",
         tags=["recall-at-k","ranking","retrieval","evaluation","metric"],
         example="If a query has 5 relevant docs and 3 of them land in your top-10, recall@10 = 3/5 = 0.6."),
    dict(cat="glossary", title="Pointwise vs pairwise vs listwise ranking",
         answer="Three learning-to-rank formulations. POINTWISE predicts an absolute relevance score per item independently (regression/classification). PAIRWISE learns which of two items should rank higher, optimizing correct orderings (e.g. RankNet). LISTWISE optimizes a metric over the WHOLE ordered list directly (e.g. LambdaMART toward NDCG). Pairwise/listwise usually rank better because ranking is inherently relative.",
         tags=["learning-to-rank","pointwise","pairwise","listwise","ranking"],
         example="Pointwise scores each result 0-1; pairwise learns 'doc A > doc B'; listwise directly pushes the ordering that maximizes NDCG for the whole page."),
    dict(cat="ml_coding", title="Gini, Entropy & Information Gain (from scratch)",
         answer="The impurity measures a decision tree uses to choose splits. GINI = 1 - sum of squared class proportions (0 = pure). ENTROPY = -sum p*log2(p) (0 = pure, higher = mixed). INFORMATION GAIN = parent entropy minus the weighted average entropy of the child splits; the tree picks the split that maximizes it.",
         tags=["gini","entropy","information-gain","decision-tree","ml-coding"],
         code='''# Gini impurity, entropy, and information gain for a decision-tree split.
import math
def gini(labels):
    n = len(labels)
    if n == 0:
        return 0.0
    counts = {}
    for y in labels:
        counts[y] = counts.get(y, 0) + 1
    return 1.0 - sum((c / n) ** 2 for c in counts.values())   # 1 - sum p^2

def entropy(labels):
    n = len(labels)
    if n == 0:
        return 0.0
    counts = {}
    for y in labels:
        counts[y] = counts.get(y, 0) + 1
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def information_gain(parent, left, right):
    n = len(parent)
    # parent entropy minus the size-weighted entropy of the two children
    child = (len(left) / n) * entropy(left) + (len(right) / n) * entropy(right)
    return entropy(parent) - child''',
         complexity="Time O(n) per measure, space O(unique classes).",
         pitfalls="log2(0) blows up (only sum over present classes); forgetting to weight children by their size.",
         example="gini([0,0,1,1]) -> 0.5; information_gain([0,0,1,1],[0,0],[1,1]) -> 1.0 (a perfect split)."),
    dict(cat="ml_coding", title="Min-Max Scaler (from scratch)",
         answer="Rescale a feature so its values map linearly onto [0, 1]: subtract the min and divide by the range (max - min). Unlike standardization (z-score), it bounds the output but is sensitive to outliers (a single extreme value squashes everything else). Handle a constant feature (range 0) to avoid divide-by-zero.",
         tags=["min-max-scaler","normalization","preprocessing","feature-scaling","ml-coding"],
         code='''# Scale a feature column to the [0, 1] range (min-max normalization).
def min_max_scale(column):
    lo = min(column)
    hi = max(column)
    if hi == lo:
        return [0.0 for _ in column]           # constant feature -> all zeros
    span = hi - lo
    return [(x - lo) / span for x in column]    # min -> 0, max -> 1''',
         complexity="Time O(n), space O(n).",
         pitfalls="Divide-by-zero on a constant column; fitting min/max on test data (fit on train, apply to test).",
         example="min_max_scale([10, 20, 30]) -> [0.0, 0.5, 1.0]."),
    dict(cat="behavioral", title="Tell me about a time you did more with less (LP: Frugality)",
         answer="Use STAR. SITUATION: Our student project had no cloud budget but a model that seemed to need an expensive GPU to train and serve. TASK: Ship the full demo at (near) zero infra cost. ACTION: I trained on a free-tier Colab GPU, used mixed precision + gradient accumulation to fit a larger effective batch in limited memory, quantized the final model to run inference on CPU, and cached results to avoid recomputation. RESULT: We shipped the complete demo for $0 in infrastructure, with inference under 200ms on a laptop. LESSON: Constraints forced sharper engineering, not a worse product. HOW TO TELL IT: show resourcefulness and that the constraint led to a smarter solution, quantifying the savings.",
         tags=["behavioral","star","frugality","amazon-lp"],
         example="Shipped a full ML demo for $0 infra — free Colab GPU, mixed precision + grad accumulation to train, and CPU quantization for <200ms inference."),
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

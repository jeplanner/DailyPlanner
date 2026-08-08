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
    dict(cat="dsa", title="Insert Interval",
         answer="Insert a new interval into a list of SORTED, non-overlapping intervals and merge any overlaps. Three passes in one sweep: (1) copy all intervals that end before the new one starts, (2) merge every interval that overlaps the new one by expanding the new interval's bounds, (3) copy the rest. No re-sorting needed since the input is already sorted.",
         tags=["insert-interval","intervals","merge","array","dsa"],
         code='''# Insert a new interval into a sorted, non-overlapping list and merge.
def insert_interval(intervals, new):
    result = []
    i, n = 0, len(intervals)
    while i < n and intervals[i][1] < new[0]:      # ends before new starts
        result.append(intervals[i]); i += 1
    while i < n and intervals[i][0] <= new[1]:      # overlaps new -> merge
        new[0] = min(new[0], intervals[i][0])
        new[1] = max(new[1], intervals[i][1])
        i += 1
    result.append(new)
    while i < n:                                    # the rest, after new
        result.append(intervals[i]); i += 1
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Re-sorting unnecessarily (input is already sorted); wrong overlap test — use intervals[i][0] <= new[1].",
         example="insert_interval([[1,3],[6,9]], [2,5]) -> [[1,5],[6,9]]."),
    dict(cat="dsa", title="Gas Station (greedy circuit)",
         answer="Find the starting station index to complete a circular route, or -1 if impossible. Key insights: if the TOTAL gas is at least the total cost, a solution exists and is unique. Track a running tank; whenever it dips below 0, no station up to here can be the start, so reset the candidate start to the next station and zero the tank. One pass.",
         tags=["gas-station","greedy","array","dsa"],
         code='''# Index of the station to start from to complete the circuit, else -1.
def can_complete_circuit(gas, cost):
    total = 0        # net gas over the whole loop
    tank = 0         # running tank from the current candidate start
    start = 0
    for i in range(len(gas)):
        diff = gas[i] - cost[i]
        total += diff
        tank += diff
        if tank < 0:          # can't reach station i+1 from 'start'
            start = i + 1     # next station becomes the candidate start
            tank = 0
    return start if total >= 0 else -1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Returning start without the total>=0 feasibility check; resetting to i instead of i+1.",
         example="can_complete_circuit([1,2,3,4,5],[3,4,5,1,2]) -> 3."),
    dict(cat="dsa", title="Task Scheduler (cooldown)",
         answer="Given tasks and a cooldown n (same task can't run within n units), find the minimum total time. The bottleneck is the MOST frequent task: arrange (max_count-1) frames of size (n+1), then append the tasks that share the max frequency. If there are enough distinct tasks to fill the idle gaps, the answer is just len(tasks). Take the max of the two.",
         tags=["task-scheduler","greedy","scheduling","counting","dsa"],
         code='''# Minimum time units to run all tasks with cooldown n between same tasks.
from collections import Counter
def least_interval(tasks, n):
    counts = Counter(tasks)
    max_count = max(counts.values())              # most frequent task's count
    num_max = sum(1 for c in counts.values() if c == max_count)  # how many tie
    # (max_count-1) gaps of size (n+1), plus the final group of max tasks
    intervals = (max_count - 1) * (n + 1) + num_max
    return max(intervals, len(tasks))             # never fewer than #tasks''',
         complexity="Time O(t) for t tasks, space O(1) (at most 26 keys).",
         pitfalls="Forgetting max(..., len(tasks)) when there are many distinct tasks; miscounting the tied maxima.",
         example="least_interval(['A','A','A','B','B','B'], 2) -> 8  (A B idle A B idle A B)."),
    dict(cat="dsa", title="Non-overlapping Intervals (min removals)",
         answer="Find the minimum number of intervals to remove so the rest don't overlap. Greedy: sort by END time and always keep the interval that ends earliest; any later interval that starts before the kept one's end must be removed. Ending earliest leaves the most room for future intervals — the classic activity-selection argument.",
         tags=["non-overlapping-intervals","greedy","intervals","dsa"],
         code='''# Min intervals to remove so the rest are non-overlapping (greedy by end).
def erase_overlap_intervals(intervals):
    if not intervals:
        return 0
    intervals.sort(key=lambda x: x[1])   # sort by END time
    removals = 0
    prev_end = intervals[0][1]
    for start, end in intervals[1:]:
        if start < prev_end:              # overlaps -> remove this one
            removals += 1
        else:
            prev_end = end                # keep it; advance the boundary
    return removals''',
         complexity="Time O(n log n) for the sort, space O(1).",
         pitfalls="Sorting by start instead of end (greedy breaks); using <= instead of < (touching endpoints don't overlap here).",
         example="erase_overlap_intervals([[1,2],[2,3],[3,4],[1,3]]) -> 1  (remove [1,3])."),
    dict(cat="dsa", title="Top-K Frequent Elements (bucket sort)",
         answer="Return the k most frequent elements. Count frequencies, then BUCKET numbers by their frequency (index = count). Walk buckets from highest frequency down, collecting until you have k. This is O(n) — better than sorting by count (O(n log n)) or a heap (O(n log k)).",
         tags=["top-k-frequent","bucket-sort","hash-map","counting","dsa"],
         code='''# The k most frequent elements, using buckets indexed by frequency.
from collections import Counter
def top_k_frequent(nums, k):
    counts = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]  # buckets[f] = nums seen f times
    for num, freq in counts.items():
        buckets[freq].append(num)
    result = []
    for freq in range(len(buckets) - 1, 0, -1):   # highest frequency first
        for num in buckets[freq]:
            result.append(num)
            if len(result) == k:
                return result
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Sizing buckets wrong (max freq is len(nums)); iterating buckets low-to-high (gives least frequent).",
         example="top_k_frequent([1,1,1,2,2,3], 2) -> [1,2]."),
    dict(cat="dsa", title="Validate Binary Search Tree",
         answer="Verify a binary tree is a valid BST: every node's value must lie strictly within an allowed (low, high) range that tightens as you descend. Going left caps the high bound at the parent's value; going right raises the low bound. A naive 'check node vs its two children' check is WRONG — it misses violations deeper in the subtree.",
         tags=["validate-bst","bst","binary-tree","recursion","dsa"],
         code='''# Check a binary tree is a valid BST via tightening (low, high) bounds.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def is_valid_bst(root):
    def valid(node, low, high):
        if node is None:
            return True                     # an empty subtree is valid
        if not (low < node.val < high):
            return False                    # value violates the allowed range
        # left subtree must stay < node.val; right must stay > node.val
        return valid(node.left, low, node.val) and valid(node.right, node.val, high)
    return valid(root, float('-inf'), float('inf'))''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Only comparing a node to its direct children (misses far violations); using <= where strict < is required.",
         example="Tree 2 with children 1 and 3 is valid; a tree 5 whose right child is 4 is NOT."),
    dict(cat="dsa", title="Diameter of a Binary Tree",
         answer="The diameter is the number of EDGES on the longest path between any two nodes (it need not pass through the root). Compute each node's depth with a post-order DFS; at every node, the longest path THROUGH it is left_depth + right_depth. Track the global max of that while returning 1 + max(left, right) as the node's own depth.",
         tags=["diameter","binary-tree","dfs","recursion","dsa"],
         code='''# Length (in edges) of the longest path between any two nodes.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def diameter_of_binary_tree(root):
    best = 0
    def depth(node):
        nonlocal best
        if node is None:
            return 0
        left = depth(node.left)             # depth of the left subtree
        right = depth(node.right)           # depth of the right subtree
        best = max(best, left + right)      # longest path through this node
        return 1 + max(left, right)         # this node's own depth
    depth(root)
    return best''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Returning left+right as the depth (should be 1+max); counting nodes instead of edges.",
         example="For root 1 with left 2 (children 4,5) and right 3, the diameter is 3 edges (4-2-1-3)."),
    dict(cat="glossary", title="Byte-Pair Encoding (BPE)",
         answer="A subword tokenization method. Start from characters, then repeatedly MERGE the most frequent adjacent pair into a new token, building a vocabulary of common subword units. It balances vocabulary size against sequence length and handles rare/unknown words by splitting them into known pieces — the tokenizer behind GPT and many LLMs.",
         tags=["bpe","byte-pair-encoding","tokenization","nlp","subword"],
         example="'lower' and 'lowest' share the subword 'low'; BPE learns 'low' as one token so a rare word like 'lowishly' still splits into known pieces instead of an <UNK>."),
    dict(cat="glossary", title="Positional encoding",
         answer="Because a Transformer's self-attention is ORDER-AGNOSTIC (it sees a set, not a sequence), positional encodings inject each token's position. Classic sinusoidal encodings add position-dependent sine/cosine patterns to the embeddings; learned and rotary (RoPE) variants are common now. Without them the model couldn't tell 'dog bites man' from 'man bites dog'.",
         tags=["positional-encoding","transformer","attention","nlp"],
         example="Adding sinusoidal position vectors lets attention distinguish the first 'the' from the second, so word order carries meaning."),
    dict(cat="glossary", title="Teacher forcing",
         answer="A training technique for sequence models where, at each step, the model is fed the GROUND-TRUTH previous token rather than its own previous prediction. It speeds and stabilizes training, but creates 'exposure bias': at inference the model must consume its own (possibly wrong) outputs — a distribution it never saw during training.",
         tags=["teacher-forcing","seq2seq","training","exposure-bias","nlp"],
         example="Training a translator, you feed the correct French word at each step regardless of the model's guess; at test time it must use its own predictions, so early mistakes can compound."),
    dict(cat="glossary", title="Label smoothing",
         answer="A regularization trick for classification: instead of hard one-hot targets (1 for the true class, 0 for the rest), use SOFT targets (e.g. 0.9 for the true class and the remaining 0.1 split across the others). It discourages over-confidence, improves calibration and generalization, and is standard in training modern image and language models.",
         tags=["label-smoothing","regularization","classification","calibration"],
         example="For a 5-class problem, the true class target becomes 0.9 and each other class gets 0.025, so the model doesn't push logits to infinity chasing a perfect 1.0."),
    dict(cat="glossary", title="Weight decay (L2 regularization)",
         answer="Adding a penalty proportional to the squared magnitude of the weights to the loss — equivalently, shrinking weights slightly each update. It discourages large weights, reducing overfitting and favouring simpler models. In modern optimizers (AdamW) it's DECOUPLED from the adaptive gradient for correctness.",
         tags=["weight-decay","l2-regularization","overfitting","optimization"],
         example="Training with weight decay 1e-4 keeps weights small so the model fits the signal without memorizing noise — often the most effective regularizer alongside dropout."),
    dict(cat="glossary", title="Knowledge distillation",
         answer="Training a small 'student' model to mimic a large 'teacher' by matching the teacher's SOFT probability outputs (which carry rich 'dark knowledge' about class similarities) rather than just hard labels. The student captures much of the teacher's accuracy at a fraction of the size and latency — key for deploying big models cheaply.",
         tags=["knowledge-distillation","model-compression","student-teacher","efficiency"],
         example="A large BERT teacher's softened outputs train a 6-layer DistilBERT student that runs ~2x faster while keeping ~97% of the accuracy."),
    dict(cat="conceptual", title="Why do Transformers need positional encoding when RNNs don't?",
         answer="An RNN processes tokens one at a time in order, so position is baked into the computation itself. A Transformer's self-attention instead relates ALL tokens simultaneously as an unordered set — permuting the inputs would give the same result. That property is exactly what makes it parallelizable and great at long-range dependencies, but it means order information must be ADDED explicitly via positional encodings; otherwise 'the cat chased the dog' and 'the dog chased the cat' would look identical to the model.",
         tags=["positional-encoding","transformer","rnn","attention","why"],
         example="Remove positional encodings and a Transformer's accuracy collapses on any task where word order matters — it literally can't tell reordered sentences apart."),
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

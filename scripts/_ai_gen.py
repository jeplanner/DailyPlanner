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
    dict(cat="glossary", title="KL divergence",
         answer="A measure of how one probability distribution differs from another — how much information is lost approximating P with Q. It is asymmetric (KL(P||Q) != KL(Q||P)) and always >= 0, hitting zero only when the distributions are identical. It underlies cross-entropy loss, variational methods, and knowledge distillation.",
         tags=["kl-divergence","statistics","deep-learning"],
         example="Distillation minimizes the KL divergence between the student's and teacher's output distributions so the student mimics the teacher."),
    dict(cat="glossary", title="Softmax temperature",
         answer="A knob T applied before softmax (dividing the logits by T) that controls how 'peaky' the output probabilities are. High T gives softer, more uniform outputs (more random/creative sampling); low T gives sharper, more confident outputs (near-greedy). It is how you dial an LLM's randomness and how teacher outputs are softened in distillation.",
         tags=["temperature","softmax","llm","sampling"],
         example="An LLM at temperature 0.2 gives focused, repetitive answers; at 1.2 it becomes more creative and varied."),
    dict(cat="glossary", title="Tokenization / BPE",
         answer="Splitting text into TOKENS (subword units) a model can process. Byte-Pair Encoding (BPE) starts from characters and greedily merges the most frequent pairs into subwords, so common words become a single token while rare words split into pieces — balancing a small vocabulary with the ability to represent any word.",
         tags=["tokenization","bpe","nlp","llm"],
         example="'tokenization' might split into 'token' + 'ization'; a rare name like 'Xylophone' splits into several subword tokens."),
    dict(cat="glossary", title="Contrastive learning",
         answer="A self-supervised technique that learns representations by pulling SIMILAR (positive) pairs together and pushing DIFFERENT (negative) pairs apart in embedding space. It learns powerful features from unlabeled data (SimCLR for images, CLIP for image-text).",
         tags=["contrastive-learning","self-supervised","embeddings"],
         example="Two random crops of the SAME photo are a positive pair (pulled together); crops of different photos are negatives (pushed apart) — the model learns what makes an image itself."),
    dict(cat="glossary", title="Diffusion model",
         answer="A generative model that creates data by REVERSING a gradual noising process: it is trained to denoise images step by step, so starting from pure noise it can generate a realistic image. It powers modern text-to-image tools (Stable Diffusion, DALL-E).",
         tags=["diffusion","generative","deep-learning"],
         example="Give a diffusion model 'an astronaut riding a horse'; it starts from noise and denoises over ~50 steps into a coherent image."),
    dict(cat="glossary", title="RLHF (Reinforcement Learning from Human Feedback)",
         answer="How LLMs are aligned to be helpful and safe: humans rank model outputs, a REWARD MODEL learns to predict those preferences, and the LLM is fine-tuned with reinforcement learning to maximize that reward. It is what turns a raw next-token predictor into a helpful assistant.",
         tags=["rlhf","alignment","llm","reinforcement-learning"],
         example="Humans rate ChatGPT answers; the model is then tuned to produce the kinds of answers people preferred — making it more helpful and less toxic."),
    dict(cat="glossary", title="PR-AUC (Precision-Recall AUC)",
         answer="The area under the Precision-Recall curve. Unlike ROC-AUC it focuses on the POSITIVE class, making it the better metric for heavily IMBALANCED problems where positives are rare. Higher is better, and the random baseline equals the positive class's prevalence.",
         tags=["pr-auc","auc","metrics","imbalance"],
         example="For fraud at 0.5% prevalence, a PR-AUC of 0.6 is strong (baseline 0.005), while ROC-AUC would look deceptively high."),
    dict(cat="dsa", title="Longest Palindromic Substring",
         answer="Find the longest palindromic substring. Elegant O(n^2)/O(1) approach: every palindrome has a center, and there are 2n-1 possible centers (each character, and each gap between two characters). Expand outward from each center while both sides match, tracking the longest.",
         tags=["longest-palindrome","expand-around-center","string","dsa"],
         code='''# Longest palindromic substring of s.
def longest_palindrome(s):
    if not s:
        return ""
    start, end = 0, 0                 # best palindrome span so far
    def expand(l, r):                 # widen while s[l] == s[r]
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1
            r += 1
        return l + 1, r - 1           # last valid (inclusive) bounds
    for i in range(len(s)):
        l1, r1 = expand(i, i)         # odd-length center (a single char)
        l2, r2 = expand(i, i + 1)     # even-length center (between chars)
        if r1 - l1 > end - start:
            start, end = l1, r1
        if r2 - l2 > end - start:
            start, end = l2, r2
    return s[start:end + 1]''',
         complexity="Time O(n^2), space O(1).",
         pitfalls="Only checking odd centers (misses even-length palindromes); off-by-one on the returned bounds.",
         example="longest_palindrome('babad') -> 'bab' (or 'aba')."),
    dict(cat="dsa", title="Meeting Rooms II (minimum rooms)",
         answer="Given meeting intervals, find the minimum number of rooms needed. Sort by start time and keep a MIN-HEAP of end times. For each meeting, if the earliest-ending room is free by its start, reuse it (pop); otherwise open a new room. The heap size is rooms in use; its peak is the answer.",
         tags=["meeting-rooms","heap","intervals","dsa"],
         code='''import heapq

# Minimum meeting rooms needed for the given [start, end] intervals.
def min_meeting_rooms(intervals):
    if not intervals:
        return 0
    intervals.sort(key=lambda x: x[0])   # process meetings by start time
    heap = []                            # min-heap of end times (rooms in use)
    for start, end in intervals:
        if heap and heap[0] <= start:    # earliest room frees before this starts
            heapq.heapreplace(heap, end) #   reuse it (pop old end, push new)
        else:
            heapq.heappush(heap, end)    #   otherwise open a new room
    return len(heap)                     # peak simultaneous rooms''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="end<=start vs end<start (meetings that just touch can share a room); forgetting to sort by start.",
         example="min_meeting_rooms([[0,30],[5,10],[15,20]]) -> 2."),
    dict(cat="dsa", title="Validate Binary Search Tree",
         answer="Check whether a binary tree is a valid BST (every node greater than all left-subtree nodes and less than all right-subtree nodes). Recurse carrying a valid (low, high) RANGE: each node must fall strictly inside it, and its children inherit tightened ranges. The classic bug is only comparing a node to its immediate children.",
         tags=["validate-bst","tree","recursion","dsa"],
         code='''# True if the binary tree is a valid BST.
def is_valid_bst(root):
    def valid(node, low, high):
        if not node:                  # an empty subtree is valid
            return True
        if not (low < node.val < high):   # node must fall in the allowed range
            return False
        # left subtree must stay < node.val; right subtree must stay > node.val
        return valid(node.left, low, node.val) and valid(node.right, node.val, high)
    return valid(root, float('-inf'), float('inf'))''',
         complexity="Time O(n), space O(height).",
         pitfalls="Only comparing a node to its direct children (misses distant violations); < vs <= for duplicates.",
         example="A tree with root 5, right child 4 holding a left child 3 is NOT valid — 3 is in 5's right subtree but 3 < 5."),
    dict(cat="ml_coding", title="Implement Softmax (from scratch)",
         answer="Turn a vector of raw scores (logits) into a probability distribution. Subtract the max first for NUMERICAL STABILITY (prevents exp overflow), then exponentiate and divide by the sum. Interviewers love the max-subtraction trick because it shows you understand floating-point overflow.",
         tags=["softmax","numerical-stability","ml-coding"],
         code='''import numpy as np

# Convert logits into a probability distribution that sums to 1.
def softmax(logits):
    z = logits - np.max(logits)   # subtract the max for numerical stability
    exp = np.exp(z)               # exponentiate (now safe from overflow)
    return exp / exp.sum()        # normalize so the outputs sum to 1''',
         complexity="Time O(n), space O(n).",
         pitfalls="Skipping the max-subtraction -> exp overflow (inf/nan) on large logits.",
         example="softmax(np.array([2.0, 1.0, 0.1])) -> ~[0.659, 0.242, 0.099] (sums to 1)."),
    dict(cat="ml_coding", title="Confusion matrix from scratch",
         answer="Build the four counts (TP, FP, TN, FN) that every classification metric derives from, given true labels and predictions (0/1); precision, recall, and accuracy fall right out. Interviewers use this to check you truly understand the metrics rather than just calling a library.",
         tags=["confusion-matrix","metrics","ml-coding"],
         code='''# Build a binary confusion matrix and derive precision/recall.
def confusion(y_true, y_pred):
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == 1 and p == 1: tp += 1     # correctly predicted positive
        elif t == 0 and p == 1: fp += 1   # false alarm
        elif t == 0 and p == 0: tn += 1   # correctly predicted negative
        else: fn += 1                     # missed a real positive
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
            'precision': precision, 'recall': recall}''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing by zero when a class is absent; mixing up FP and FN.",
         example="confusion([1,1,0,0], [1,0,0,1]) -> tp=1, fp=1, tn=1, fn=1, precision=0.5, recall=0.5."),
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

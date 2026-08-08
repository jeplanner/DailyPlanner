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
    dict(cat="behavioral", title="Tell me about a time you simplified something complex (LP: Invent and Simplify)",
         answer="Use STAR. SITUATION: Our research lab tracked experiments in scattered spreadsheets, so people constantly lost hyperparameters and re-ran work. TASK: Reduce the time everyone wasted on bookkeeping. ACTION: I wrote a tiny 30-line Python wrapper that auto-logged each run's config, git commit, and metrics to one shared dashboard — no behaviour change required from users, just import and go. RESULT: Experiment setup dropped from ~30 minutes to ~2, duplicate runs nearly vanished, and the whole lab adopted it within a week. LESSON: The best simplification removes work without adding process. HOW TO TELL IT: emphasize you invented a lightweight tool, removed complexity for others, and quantify the time saved.",
         tags=["behavioral","star","invent-and-simplify","amazon-lp"],
         example="Wrote a 30-line auto-logger that cut experiment setup from 30 min to 2 and was adopted lab-wide in a week."),
    dict(cat="behavioral", title="Tell me about a time you made a good call with limited data (LP: Are Right A Lot)",
         answer="Use STAR. SITUATION: For a class project with only ~800 labeled examples, a teammate pushed for a deep neural net because it sounded impressive. TASK: Choose the approach most likely to actually work. ACTION: I reasoned that with so little data a big model would overfit, and proposed a regularized gradient-boosted tree with solid feature engineering; I backed the judgment with a quick 5-fold cross-validation comparison rather than just opinion. RESULT: The simpler model beat the deep net by 9 F1 points and trained in seconds. LESSON: Good judgment uses both intuition (data size vs model capacity) and evidence, and I stayed open to being wrong by testing it. HOW TO TELL IT: show the reasoning, the evidence you gathered, and that you sought input and could have updated.",
         tags=["behavioral","star","are-right-a-lot","amazon-lp"],
         example="Argued a boosted tree would beat a deep net on 800 examples, proved it with 5-fold CV (+9 F1), and it trained in seconds."),
    dict(cat="behavioral", title="Tell me about a time you refused to lower the quality bar (LP: Insist on the Highest Standards)",
         answer="Use STAR. SITUATION: Close to a project deadline, a teammate reported 95% accuracy — but I noticed it was measured on the TRAINING data. TASK: Make sure we reported an honest, trustworthy number even if it looked worse. ACTION: I insisted we build a proper held-out test set and re-evaluate; I did the split and re-ran it despite the time pressure. RESULT: Real accuracy was 78%, so we spent the remaining days actually improving the model instead of shipping a false result — and finished at a genuine 84%. LESSON: A metric you can't trust is worse than no metric. HOW TO TELL IT: show you held the bar under pressure and that it prevented a real mistake.",
         tags=["behavioral","star","highest-standards","amazon-lp"],
         example="Caught a '95%' that was measured on training data; insisted on a real test set (true 78%), then improved it to an honest 84%."),
    dict(cat="behavioral", title="Tell me about a time you thought bigger than the immediate task (LP: Think Big)",
         answer="Use STAR. SITUATION: I was asked to build a single weekly data report for one course project. TASK: Deliver that report. ACTION: While building it I realized several teammates were each hand-pulling the same data differently, so I proposed and prototyped a small shared data-loading module with clean, reusable queries — beyond my assigned scope. RESULT: The report shipped, and the shared module was adopted by four other sub-teams, eliminating inconsistent numbers across the whole project. LESSON: Solving the general problem behind a specific task multiplies the impact. HOW TO TELL IT: show the bigger vision AND that you still delivered the concrete first step.",
         tags=["behavioral","star","think-big","amazon-lp"],
         example="Asked for one report, I built a reusable shared data module that four other sub-teams adopted, killing inconsistent numbers."),
    dict(cat="behavioral", title="Tell me about a time you earned others' trust (LP: Earn Trust)",
         answer="Use STAR. SITUATION: I joined a new project team mid-semester where I was the unknown newcomer. TASK: Become someone the team could rely on. ACTION: I started by delivering small, reliable wins on time; when I introduced a bug that broke a shared notebook, I flagged it openly the same hour, fixed it, and added a test so it couldn't recur; and I consistently credited others' ideas in reviews. RESULT: Within a month I was the person teammates came to for code reviews and design questions. LESSON: Trust is built through consistency, candor about mistakes, and giving credit. HOW TO TELL IT: emphasize owning a mistake openly, dependable delivery, and listening.",
         tags=["behavioral","star","earn-trust","amazon-lp"],
         example="As the new teammate, I built trust with reliable delivery and by openly owning a bug I caused (fixed it + added a test the same hour)."),
    dict(cat="behavioral", title="Tell me about a time you disagreed but committed (LP: Have Backbone; Disagree and Commit)",
         answer="Use STAR. SITUATION: My team chose accuracy as the success metric for a heavily imbalanced fraud dataset (only 3% positives). TASK: Voice a real concern without stalling the team. ACTION: I respectfully disagreed, showing with a quick analysis that a model predicting 'never fraud' would score 97% accuracy while catching zero fraud, and recommended precision/recall or F1. The team still preferred accuracy for simplicity, so I committed fully — helped optimize it AND quietly tracked recall on the side. RESULT: Two weeks in, recall was near zero as I'd warned; because I had the data ready, we switched to F1 quickly with no drama. LESSON: Disagree with evidence, then commit genuinely — and keep watching. HOW TO TELL IT: show respectful, data-backed pushback followed by true commitment.",
         tags=["behavioral","star","have-backbone","disagree-and-commit","amazon-lp"],
         example="Warned that accuracy on a 3%-positive fraud set was misleading, committed anyway, tracked recall, and had the data ready when we switched to F1."),
    dict(cat="glossary", title="LoRA / PEFT",
         answer="Low-Rank Adaptation, a Parameter-Efficient Fine-Tuning method. Instead of updating all of a large model's weights, LoRA FREEZES them and injects small trainable low-rank matrices into each layer, training only those (a tiny fraction of parameters). You get most of full fine-tuning's quality at a fraction of the memory/compute, and can hot-swap adapters per task.",
         tags=["lora","peft","fine-tuning","efficiency","llm"],
         example="Fine-tuning a 7B model with LoRA trains only ~0.1% of the parameters, so it fits on one GPU and yields a few-MB adapter you can swap per task."),
    dict(cat="glossary", title="Flash attention",
         answer="A memory- and speed-optimized EXACT attention algorithm. It computes attention in tiles that stay in fast on-chip SRAM, avoiding materializing the huge N×N attention matrix in slow GPU memory (HBM). The math is identical but memory traffic drops sharply — enabling much longer context windows and faster training/inference.",
         tags=["flash-attention","attention","gpu","efficiency","transformer"],
         example="Flash attention lets a Transformer handle sequences of tens of thousands of tokens without running out of memory, by never storing the full attention matrix."),
    dict(cat="glossary", title="Perplexity",
         answer="A standard metric for language models measuring how 'surprised' the model is by a test text — the exponential of the average negative log-likelihood per token. Lower is better: it roughly equals the effective number of equally-likely choices the model weighs at each step. A perplexity of 10 means it's as uncertain as choosing uniformly among 10 words.",
         tags=["perplexity","language-model","evaluation","metric","nlp"],
         example="If model A has perplexity 20 and model B has 15 on the same test set, B predicts the text better (it's less surprised)."),
    dict(cat="glossary", title="K-fold cross-validation",
         answer="A robust way to estimate model performance with limited data. Split the data into k equal folds; train on k-1 folds and validate on the held-out fold, rotating so each fold is the validation set exactly once; average the k scores. It uses all data for both training and validation and gives a more stable estimate than a single split.",
         tags=["cross-validation","k-fold","evaluation","model-selection","validation"],
         example="5-fold CV trains 5 models, each validated on a different 20% slice; averaging their scores (say 0.81 ± 0.02) estimates generalization more reliably than one train/test split."),
    dict(cat="dsa", title="Flatten Binary Tree to Linked List",
         answer="Flatten a binary tree into a 'linked list' that follows PRE-ORDER, using the right pointers (left pointers become null), in place. Morris-style trick: for each node with a left child, find the rightmost node of that left subtree, attach the node's current right subtree there, then move the whole left subtree to the right. O(1) extra space.",
         tags=["flatten-tree","binary-tree","morris","in-place","dsa"],
         code='''# Flatten a binary tree into a right-pointer linked list in pre-order, in place.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def flatten(root):
    node = root
    while node:
        if node.left:
            rightmost = node.left           # find the left subtree's tail
            while rightmost.right:
                rightmost = rightmost.right
            rightmost.right = node.right     # splice current right after it
            node.right = node.left           # move left subtree to the right
            node.left = None                 # clear the left pointer
        node = node.right                    # advance down the flattened list
    return root''',
         complexity="Time O(n), space O(1).",
         pitfalls="Forgetting to null the left pointer; losing the original right subtree (attach it to the left subtree's tail first).",
         example="The tree 1 -> (2 -> (3,4), 5 -> (_,6)) flattens to 1,2,3,4,5,6 along right pointers."),
    dict(cat="dsa", title="Path Sum (root-to-leaf boolean)",
         answer="Decide whether the tree has any ROOT-TO-LEAF path whose node values add up to a target. Recurse subtracting the current node's value from the remaining target; at a LEAF, success is remaining == the leaf's value. A node with one child is not a leaf, so don't treat it as one.",
         tags=["path-sum","binary-tree","dfs","recursion","dsa"],
         code='''# Is there a root-to-leaf path whose values sum to target?
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def has_path_sum(root, target):
    if root is None:
        return False
    if root.left is None and root.right is None:    # a leaf
        return root.val == target
    remaining = target - root.val
    return has_path_sum(root.left, remaining) or has_path_sum(root.right, remaining)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Checking the sum at a null child instead of at a leaf (mishandles single-child nodes); forgetting the empty-tree case.",
         example="For the tree 5 -> (4 -> 11 -> (7,2), 8) with target 22, the path 5->4->11->2 sums to 22 -> True."),
    dict(cat="dsa", title="Path Sum II (all root-to-leaf paths)",
         answer="Return every ROOT-TO-LEAF path whose values sum to a target. Backtracking DFS: append the current node to the path, and when you reach a leaf whose remaining target equals its value, record a copy of the path; otherwise recurse into children with the reduced target, then pop the node on the way back up.",
         tags=["path-sum","backtracking","binary-tree","dfs","dsa"],
         code='''# All root-to-leaf paths whose values sum to target.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def path_sum(root, target):
    result = []
    def dfs(node, remaining, path):
        if node is None:
            return
        path.append(node.val)
        if node.left is None and node.right is None and remaining == node.val:
            result.append(path[:])          # a valid leaf path -> copy it
        else:
            dfs(node.left, remaining - node.val, path)
            dfs(node.right, remaining - node.val, path)
        path.pop()                          # backtrack
    dfs(root, target, [])
    return result''',
         complexity="Time O(n^2) worst case (copying paths), space O(h).",
         pitfalls="Appending the path reference instead of a copy; forgetting to pop when backtracking.",
         example="For the tree 1 -> (2, 3) with target 3, path_sum returns [[1,2]]."),
    dict(cat="dsa", title="Lowest Common Ancestor of a Binary Tree",
         answer="Find the deepest node that is an ancestor of both p and q in a GENERAL binary tree (not a BST). Recurse: if the current node is null or is p or q, return it. If p and q are found in DIFFERENT subtrees (both recursive calls return non-null), the current node is the LCA; otherwise pass up whichever side found something.",
         tags=["lowest-common-ancestor","binary-tree","recursion","dfs","dsa"],
         code='''# Lowest common ancestor of p and q in a general binary tree.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def lowest_common_ancestor(root, p, q):
    if root is None or root is p or root is q:
        return root                     # found a target (or hit empty)
    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)
    if left and right:
        return root                     # p and q split here -> this is the LCA
    return left or right                # both on one side (or neither found)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Assuming BST ordering (this must work without it); returning early before checking both subtrees.",
         example="In the tree 3 -> (5, 1), the LCA of nodes 5 and 1 is 3 (they're in different subtrees)."),
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

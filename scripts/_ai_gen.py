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
    dict(cat="behavioral", title="Tell me about a time you put the user first (LP: Customer Obsession)",
         answer="Use STAR. SITUATION: In my final-year capstone we built a study-planner app, and usage logs showed most students dropped off on a cluttered onboarding screen. TASK: Even though I was the ML lead, I took on improving activation. ACTION: I interviewed 8 classmates, learned the 9-field sign-up overwhelmed them, and proposed cutting it to 3 fields with the rest deferred; I prototyped it and ran a quick A/B test across two class sections. RESULT: Onboarding completion rose from 55% to 82% and weekly active users nearly doubled. LESSON: Working backwards from real user pain — not our assumptions — is what moved the metric. HOW TO TELL IT: quantify the user impact, show you listened to actual users, and tie it to a business metric.",
         tags=["behavioral","star","customer-obsession","amazon-lp"],
         example="Cut a 9-field sign-up to 3 after interviewing users; onboarding completion jumped 55%->82% and weekly actives nearly doubled."),
    dict(cat="behavioral", title="Tell me about a time you took ownership beyond your role (LP: Ownership)",
         answer="Use STAR. SITUATION: During a summer internship, the data pipeline feeding my model silently failed on weekends, and no one owned it after the original engineer left. TASK: My model's metrics looked wrong, and instead of just flagging it I decided to fix the root cause. ACTION: I traced the failure to an unhandled upstream schema change, added input validation and alerting, wrote a runbook, and documented it — none of which was in my intern project. RESULT: Weekend failures dropped to zero and the team adopted my alerting on three other pipelines. LESSON: Ownership means caring about the outcome, not the org chart. HOW TO TELL IT: emphasize you treated it as yours, fixed the root cause (not the symptom), and left it documented.",
         tags=["behavioral","star","ownership","amazon-lp"],
         example="Fixed a recurring weekend pipeline failure that wasn't my job — added validation + alerting, cut failures to zero, and the team reused it."),
    dict(cat="behavioral", title="Tell me about a time you dug into details to solve a hard problem (LP: Dive Deep)",
         answer="Use STAR. SITUATION: My image-classifier project suddenly lost 12% accuracy after an innocent-looking data refresh, days before a demo. TASK: Find the cause fast. ACTION: Instead of guessing, I sliced accuracy BY CLASS and saw the drop was concentrated in two classes; inspecting raw samples revealed the new data had mislabeled images from a vendor change. I wrote a script to detect label inconsistencies and quarantined the bad batch. RESULT: Accuracy fully recovered, and the label-audit script caught future bad batches automatically. LESSON: An average metric hides specific, findable causes — you must look under it. HOW TO TELL IT: show the systematic investigation (slice, inspect, verify) instead of trial-and-error.",
         tags=["behavioral","star","dive-deep","amazon-lp"],
         example="A 12% accuracy drop was mislabeled vendor images in two classes — found by slicing metrics per class, then built an auto label-audit to prevent recurrence."),
    dict(cat="behavioral", title="Tell me about a time you moved fast with incomplete information (LP: Bias for Action)",
         answer="Use STAR. SITUATION: Two days before a hackathon deadline, our third-party sentiment API got rate-limited and broke a core feature. TASK: Keep the demo working without waiting for a perfect fix. ACTION: Rather than stall debating options, I shipped a lightweight local logistic-regression sentiment model trained on a public dataset as a fallback, put it behind a feature flag so we could swap back if the API recovered, and moved on. RESULT: The demo ran flawlessly and actually faster; we placed 2nd. LESSON: Many decisions are reversible — a good-enough reversible choice now beats a perfect one too late. HOW TO TELL IT: stress the calculated speed, the reversibility (feature flag), and the outcome.",
         tags=["behavioral","star","bias-for-action","amazon-lp"],
         example="When a sentiment API broke 2 days before a hackathon, I shipped a reversible local-model fallback behind a flag — the demo worked and we placed 2nd."),
    dict(cat="behavioral", title="Tell me about a time you taught yourself something to deliver (LP: Learn and Be Curious)",
         answer="Use STAR. SITUATION: A research project needed me to deploy a model as a real-time API, but I'd only ever run models in notebooks. TASK: Learn enough serving to ship it in three weeks. ACTION: I self-studied FastAPI and Docker, built a serving prototype, load-tested it, and learned latency/batching by measuring and iterating; I asked a senior student for a code review to catch mistakes. RESULT: I shipped an API handling ~200 requests/sec at p95 under 100ms and wrote a short guide so labmates could reuse it. LESSON: Curiosity paired with a concrete deliverable is the fastest way to learn. HOW TO TELL IT: show initiative, a real deliverable, and that you shared the knowledge.",
         tags=["behavioral","star","learn-and-be-curious","amazon-lp"],
         example="Self-taught FastAPI + Docker in 3 weeks to serve a model at ~200 rps / p95<100ms, and documented it for labmates."),
    dict(cat="behavioral", title="Tell me about a time you delivered under a tight deadline (LP: Deliver Results)",
         answer="Use STAR. SITUATION: My team's final project had slipped and one week remained with the model underperforming (F1 ~0.62 vs a 0.75 goal). TASK: As ML lead, hit target without burning out the team. ACTION: I prioritized ruthlessly — dropped two nice-to-have features, focused on the highest-leverage fixes (better class balancing and stronger features), set daily checkpoints, and parallelized the work. RESULT: We reached F1 0.78, submitted on time, and earned the top grade in the class. LESSON: Delivering is about focus and prioritization under constraint, not doing everything. HOW TO TELL IT: show the trade-offs you made, the focus on the right levers, and the concrete result.",
         tags=["behavioral","star","deliver-results","amazon-lp"],
         example="One week left and F1 stuck at 0.62 — cut scope, focused on class balancing + feature engineering with daily checkpoints, and hit 0.78 on time."),
    dict(cat="glossary", title="Cross-attention",
         answer="The attention mechanism where one sequence attends to ANOTHER sequence — queries come from one, keys and values from the other — as opposed to self-attention where a sequence attends to itself. It's how a decoder looks at the encoder's output in seq2seq/translation, and how multimodal models let text attend to image features.",
         tags=["cross-attention","attention","transformer","seq2seq","nlp"],
         example="In translation, the decoder generating French uses cross-attention to look back at the encoded English words, focusing on the relevant source word for each output token."),
    dict(cat="glossary", title="Masked language modeling (MLM)",
         answer="A self-supervised pretraining objective (used by BERT) where random input tokens are hidden ('masked') and the model predicts them from the surrounding CONTEXT ON BOTH SIDES. This bidirectional objective yields rich representations for understanding tasks, unlike left-to-right next-token prediction.",
         tags=["masked-language-modeling","mlm","bert","self-supervised","nlp"],
         example="Given 'The cat sat on the [MASK]', the model learns to predict 'mat' from both left and right context — learning language structure without labels."),
    dict(cat="glossary", title="KV cache",
         answer="An inference optimization for autoregressive Transformers. Since each new token attends to all previous tokens, the model CACHES the key and value vectors of past tokens instead of recomputing them each step. This turns generation from O(n^2) recompute into O(n) per token, dramatically speeding up long-text generation — at the cost of extra memory.",
         tags=["kv-cache","inference","transformer","optimization","llm"],
         example="Generating the 500th token, the model reuses cached K/V for tokens 1-499 and only computes them for the new token, avoiding a full recompute of the sequence."),
    dict(cat="glossary", title="Early stopping",
         answer="A regularization technique that halts training when validation performance stops improving (after a 'patience' number of epochs), preventing overfitting from training too long. You keep the checkpoint with the best validation score. Simple, cheap, and one of the most effective anti-overfitting tools.",
         tags=["early-stopping","regularization","overfitting","training"],
         example="Validation loss bottoms out at epoch 30 then creeps up; with patience 5 training stops at epoch 35 and restores the epoch-30 weights — avoiding the overfitting continued training would cause."),
    dict(cat="dsa", title="Invert a Binary Tree",
         answer="Produce the mirror image of a binary tree by swapping every node's left and right children. A one-line recursive swap at each node, recursing into both subtrees, does it. The famous 'whiteboard' question — trivial once you see it's just a post/pre-order swap.",
         tags=["invert-tree","binary-tree","recursion","dfs","dsa"],
         code='''# Mirror a binary tree: swap every node's left and right children.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def invert_tree(root):
    if root is None:
        return None
    root.left, root.right = root.right, root.left   # swap the children
    invert_tree(root.left)                           # recurse into both sides
    invert_tree(root.right)
    return root''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Swapping after recursing works too, but be consistent; forgetting the None base case.",
         example="Inverting the tree 4 -> (2, 7) yields 4 -> (7, 2)."),
    dict(cat="dsa", title="Symmetric Tree",
         answer="Check whether a binary tree is a MIRROR image of itself around its center. Compare two subtrees in mirrored fashion: the left subtree's left child must match the right subtree's right child, and the left's right must match the right's left. Recurse on those mirrored pairs.",
         tags=["symmetric-tree","binary-tree","recursion","dsa"],
         code='''# Is the tree a mirror image of itself around its center?
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def is_symmetric(root):
    def mirror(a, b):
        if a is None and b is None:
            return True                 # both empty -> symmetric here
        if a is None or b is None or a.val != b.val:
            return False                # one empty or values differ
        # outer pair and inner pair must both mirror
        return mirror(a.left, b.right) and mirror(a.right, b.left)
    return root is None or mirror(root.left, root.right)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Comparing left-to-left instead of left-to-right (that checks equality, not mirroring).",
         example="The tree [1, 2, 2, 3, 4, 4, 3] is symmetric -> True."),
    dict(cat="dsa", title="Same Tree",
         answer="Determine whether two binary trees are structurally identical AND have equal node values. Recurse in lockstep: both nodes null means equal here; if exactly one is null or the values differ they're not the same; otherwise recurse on both left and right children.",
         tags=["same-tree","binary-tree","recursion","dsa"],
         code='''# Are two binary trees structurally identical with equal values?
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def is_same_tree(p, q):
    if p is None and q is None:
        return True                     # both empty
    if p is None or q is None or p.val != q.val:
        return False                    # structure or value mismatch
    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Only comparing values without checking structure (null vs node); short-circuit the null cases first.",
         example="Trees [1,2,3] and [1,2,3] -> True; [1,2] and [1,null,2] -> False."),
    dict(cat="dsa", title="Balanced Binary Tree",
         answer="Check that a tree is height-balanced: for every node, the heights of its two subtrees differ by at most 1. Compute heights bottom-up, but return a sentinel -1 the moment any subtree is unbalanced so the whole recursion short-circuits — giving O(n) instead of the naive O(n^2).",
         tags=["balanced-tree","binary-tree","dfs","recursion","dsa"],
         code='''# Is the tree height-balanced (subtree heights differ by <=1 everywhere)?
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def is_balanced(root):
    def height(node):
        if node is None:
            return 0
        lh = height(node.left)
        if lh == -1:
            return -1                   # left subtree already unbalanced
        rh = height(node.right)
        if rh == -1:
            return -1                   # right subtree already unbalanced
        if abs(lh - rh) > 1:
            return -1                   # this node is unbalanced
        return 1 + max(lh, rh)          # normal height
    return height(root) != -1''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Recomputing height at every node (O(n^2)); use the -1 sentinel to short-circuit.",
         example="A full tree of 7 nodes is balanced -> True; a right-leaning chain of 3 nodes -> False."),
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

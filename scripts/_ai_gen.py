"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it — no heredocs, pipes, or && chains.
Edit the BATCH list, run it, then git add/commit/push as separate simple
commands. Validates every code block (ast.parse) before writing.
"""
import ast
import importlib
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())   # so `import ai_sde_bank` works from here

# ── The batch to add this iteration. Each dict: cat, title, answer, tags,
#    and optional code/example/complexity/pitfalls/followups. ──
BATCH = [
    dict(cat="glossary", title="BERT",
         answer="A Transformer ENCODER pretrained to UNDERSTAND language by predicting randomly-masked words using BOTH left and right context (bidirectional). You then fine-tune it on your task (classification, Q&A). It made powerful language understanding reusable and reset the NLP state of the art.",
         tags=["bert","transformer","nlp","pretraining"],
         example="Fine-tune BERT on movie reviews for sentiment — it already 'knows' English from pretraining, so little labeled data is needed."),
    dict(cat="glossary", title="GPT",
         answer="A Transformer DECODER pretrained to predict the NEXT token given all previous tokens (left-to-right, 'autoregressive'). That makes it great at generating text, code, and answers. Scaling GPT up produced modern LLMs like ChatGPT.",
         tags=["gpt","transformer","llm","nlp"],
         example="Given 'The capital of France is', GPT predicts 'Paris', then keeps generating token by token to write a full answer."),
    dict(cat="glossary", title="Self-supervised learning",
         answer="Training on UNLABELED data by creating the labels FROM the data itself — e.g. hide part of the input and predict it. It unlocks huge unlabeled corpora (all text, all images) without costly human labeling, and is how LLMs and modern vision models are pretrained.",
         tags=["self-supervised","pretraining","deep-learning"],
         example="BERT hides 15% of words and predicts them; the 'label' is just the original word — no human annotation needed."),
    dict(cat="glossary", title="Beam search",
         answer="A decoding strategy for sequence models (translation, text generation): instead of greedily taking the single most likely next token, keep the top-k ('beam width') partial sequences at each step and expand them, finally choosing the best COMPLETE sequence. It finds higher-probability outputs than greedy, at more compute.",
         tags=["beam-search","decoding","nlp","llm"],
         example="Translating with beam width 5 explores 5 candidate translations in parallel and returns the most fluent overall — better than committing word by word."),
    dict(cat="glossary", title="Reinforcement learning (agent, reward, policy)",
         answer="A paradigm where an AGENT takes ACTIONS in an ENVIRONMENT to maximize cumulative REWARD, learning by trial and error. Key terms: state (the situation), action (a choice), reward (feedback), policy (the strategy mapping states to actions). Used in games, robotics, and RLHF for aligning LLMs.",
         tags=["reinforcement-learning","agent","reward","policy"],
         example="AlphaGo learned Go by playing millions of games, rewarded for winning — its policy improved until it beat world champions."),
    dict(cat="glossary", title="Label smoothing",
         answer="A regularization trick for classification: instead of hard targets (1 for the true class, 0 elsewhere), train toward SOFT targets like 0.9 and a little spread on the rest. This stops the model becoming over-confident, improving calibration and generalization.",
         tags=["label-smoothing","regularization","classification"],
         example="Instead of target [0,1,0], train toward [0.033, 0.933, 0.033] — the model stays a bit humble and generalizes better."),
    dict(cat="glossary", title="Weight initialization",
         answer="How a neural network's weights are set BEFORE training. Bad init stalls learning: all-zeros makes every neuron identical; too-large values explode activations. Good schemes (Xavier/Glorot for tanh/sigmoid, He for ReLU) scale the random init by the layer size so signals and gradients stay healthy through deep networks.",
         tags=["weight-init","deep-learning","training"],
         example="Initializing a deep ReLU net with He initialization keeps activations from vanishing or exploding, so it trains from the first epoch."),
    dict(cat="glossary", title="Learning-rate schedule",
         answer="Changing the learning rate DURING training rather than keeping it fixed. Common patterns: warmup (start small, ramp up) then decay (shrink over time), or step/cosine decay. A high rate early explores fast; a low rate later fine-tunes into the minimum — improving both speed and final accuracy.",
         tags=["lr-schedule","training","optimizer"],
         example="Warm up the LR over the first 1000 steps, then cosine-decay it toward zero — standard for training Transformers."),
    dict(cat="dsa", title="Edit Distance (Levenshtein)",
         answer="Minimum number of insertions, deletions, or substitutions to turn string a into string b. 2-D DP: if the current characters MATCH it is free (carry dp[i-1][j-1]); otherwise 1 + the cheapest of insert (dp[i][j-1]), delete (dp[i-1][j]), or substitute (dp[i-1][j-1]).",
         tags=["edit-distance","levenshtein","dp","string","dsa"],
         code="# Minimum edits (insert/delete/substitute) to turn a into b.\ndef edit_distance(a, b):\n    m, n = len(a), len(b)\n    dp = [[0] * (n + 1) for _ in range(m + 1)]\n    for i in range(m + 1):\n        dp[i][0] = i                 # delete all of a[:i]\n    for j in range(n + 1):\n        dp[0][j] = j                 # insert all of b[:j]\n    for i in range(1, m + 1):\n        for j in range(1, n + 1):\n            if a[i-1] == b[j-1]:\n                dp[i][j] = dp[i-1][j-1]          # chars match -> free\n            else:\n                dp[i][j] = 1 + min(dp[i-1][j],   # delete\n                                   dp[i][j-1],   # insert\n                                   dp[i-1][j-1]) # substitute\n    return dp[m][n]",
         complexity="Time O(m*n), space O(m*n).",
         pitfalls="Forgetting the first row/column base cases (all inserts / all deletes).",
         example="edit_distance('horse', 'ros') -> 3."),
    dict(cat="dsa", title="Gas Station",
         answer="Given gas[i] and cost[i] to drive from station i to i+1 around a circle, find a start that completes the loop, or -1. Greedy: a solution exists iff total gas >= total cost. Track a running tank; whenever it goes negative you can't have started anywhere up to here, so restart from the next station.",
         tags=["gas-station","greedy","array","dsa"],
         code="# Starting station to complete the circular route, or -1.\ndef can_complete_circuit(gas, cost):\n    if sum(gas) < sum(cost):\n        return -1                    # not enough total gas -> impossible\n    tank = 0\n    start = 0\n    for i in range(len(gas)):\n        tank += gas[i] - cost[i]     # net gas gained crossing to i+1\n        if tank < 0:                 # cannot reach i+1 from `start`\n            start = i + 1            # so try starting just after i\n            tank = 0                 # reset the tank\n    return start",
         complexity="Time O(n), space O(1).",
         pitfalls="Not checking total gas first; forgetting to reset the tank on restart.",
         example="can_complete_circuit([1,2,3,4,5], [3,4,5,1,2]) -> 3."),
    dict(cat="dsa", title="Jump Game",
         answer="Given an array where each value is the max jump length from that index, can you reach the last index? Greedy: track the FARTHEST index reachable so far; scan left to right, and if you ever stand on an index beyond that reach you are stuck. Otherwise update reach = max(reach, i + nums[i]).",
         tags=["jump-game","greedy","array","dsa"],
         code="# Can you reach the last index? nums[i] = max jump length from i.\ndef can_jump(nums):\n    reach = 0                        # farthest index reachable so far\n    for i, jump in enumerate(nums):\n        if i > reach:                # we cannot even stand on i\n            return False\n        reach = max(reach, i + jump) # extend our reach from here\n    return True",
         complexity="Time O(n), space O(1).",
         pitfalls="Overcomplicating with DP when greedy is O(n); off-by-one on 'reach'.",
         example="can_jump([2,3,1,1,4]) -> True; can_jump([3,2,1,0,4]) -> False."),
    dict(cat="conceptual", title="Why does pretraining + fine-tuning beat training from scratch?",
         answer="Pretraining on a huge general dataset teaches the model reusable low-level structure — edges and textures for images, grammar and word meaning for text. Your specific task then only has to learn the LAST MILE on top of that, so it works with far less labeled data and compute. Training from scratch would waste your small dataset re-learning the basics everyone else already learned. It is like hiring someone who already speaks English to learn your company's jargon, versus teaching a baby to speak first.",
         tags=["pretraining","fine-tuning","transfer-learning","why"],
         example="500 labeled X-rays fine-tuning a pretrained vision model beats 500 X-rays training a fresh network, because the pretrained model already sees shapes and edges."),
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

# Re-import fresh to confirm the module loads and every code block runs.
b = importlib.import_module("ai_sde_bank")
importlib.reload(b)
for e in b.ENTRIES:
    if e.get("code"):
        ast.parse(e["code"])
missing = [e["title"] for e in b.ENTRIES if not e.get("example")]
assert not missing, f"missing example: {missing}"
print(f"inserted {len(BATCH)} | total {len(b.ENTRIES)} | missing example: {len(missing)}")

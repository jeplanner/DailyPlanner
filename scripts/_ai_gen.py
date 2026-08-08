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
    dict(cat="glossary", title="Residual connection (skip connection)",
         answer="A shortcut that ADDS a layer's input to its output (output = F(x) + x), so the network only has to learn the RESIDUAL (the change) rather than the full transformation. This lets gradients flow directly backward, enabling very deep networks (ResNet's hundreds of layers) that otherwise wouldn't train due to vanishing gradients.",
         tags=["residual","skip-connection","resnet","deep-learning"],
         example="ResNet-152 trains 152 layers only because skip connections let the gradient bypass blocks; without them, past ~20 layers accuracy actually degrades."),
    dict(cat="glossary", title="Layer normalization",
         answer="Normalizes each training example ACROSS ITS OWN FEATURES to zero mean and unit variance (unlike batch norm, which normalizes across the batch). It stabilizes training and works well for sequences and small batches, which is why Transformers use it.",
         tags=["layer-norm","normalization","transformer","deep-learning"],
         example="Every token's feature vector in a Transformer is layer-normalized so its scale stays consistent regardless of batch size."),
    dict(cat="glossary", title="Positional encoding",
         answer="Because a Transformer processes all tokens in parallel with no built-in notion of ORDER, positional encodings add position information to each token's embedding (via fixed sinusoids or learned vectors) so the model knows which word came first.",
         tags=["positional-encoding","transformer","nlp"],
         example="Without positional encoding, 'dog bites man' and 'man bites dog' would look identical to a Transformer."),
    dict(cat="glossary", title="Top-p (nucleus) sampling",
         answer="An LLM decoding method: instead of always taking the most likely token (greedy) or sampling from the whole vocabulary, sample only from the smallest set of top tokens whose probabilities sum to p (e.g. 0.9). It adapts how many options to consider based on the model's confidence — more diverse than greedy, safer than full sampling.",
         tags=["top-p","nucleus-sampling","llm","decoding"],
         example="With top-p 0.9, a confident step samples from just 2-3 tokens; an uncertain one considers 20 — balancing coherence and creativity."),
    dict(cat="glossary", title="Chain-of-thought prompting",
         answer="Prompting an LLM to reason STEP BY STEP (e.g. 'let us think step by step') before giving the final answer. Making the intermediate reasoning explicit dramatically improves accuracy on math and logic, because the model works through the problem instead of guessing the answer in one shot.",
         tags=["chain-of-thought","prompting","llm","reasoning"],
         example="Asked '23 x 17', a chain-of-thought prompt makes the model compute 23x10=230, 23x7=161, sum=391 — far more reliable than a direct guess."),
    dict(cat="glossary", title="Hallucination (LLM)",
         answer="When a language model produces text that is fluent and confident but FACTUALLY WRONG or fabricated — because it predicts plausible-sounding tokens, not verified facts. Mitigations: retrieval-augmented generation (grounding in real documents), requiring citations, and lower temperature.",
         tags=["hallucination","llm","rag","reliability"],
         example="Ask an LLM for a citation and it may invent a realistic-looking but nonexistent paper title and authors."),
    dict(cat="glossary", title="Cosine similarity",
         answer="A measure of how similar two vectors are by the ANGLE between them (not their length): 1 = same direction, 0 = orthogonal (unrelated), -1 = opposite. It is the standard way to compare EMBEDDINGS for search and recommendations because it ignores magnitude and focuses on direction (meaning).",
         tags=["cosine-similarity","embeddings","search","vectors"],
         example="To find documents similar to a query, embed both and rank by cosine similarity; the closest angles are the most relevant."),
    dict(cat="glossary", title="Vector database / ANN",
         answer="A database that stores EMBEDDINGS and finds the nearest ones to a query vector fast, using Approximate Nearest Neighbor (ANN) indexes like HNSW instead of comparing against every vector. It powers semantic search and RAG at scale (Pinecone, FAISS, pgvector).",
         tags=["vector-db","ann","hnsw","rag","embeddings"],
         example="A RAG chatbot embeds your question and asks the vector DB for the 5 most similar document chunks in milliseconds, out of millions."),
    dict(cat="dsa", title="Longest Increasing Subsequence",
         answer="Find the length of the longest strictly-increasing subsequence. The O(n^2) DP is dp[i] = 1 + max(dp[j]) over j<i with nums[j]<nums[i]. The elegant O(n log n) approach uses 'patience sorting': keep an array 'tails' where tails[k] is the smallest possible tail of an increasing subsequence of length k+1, and binary-search each number's slot.",
         tags=["longest-increasing-subsequence","dp","binary-search","dsa"],
         code='''import bisect

# Length of the longest strictly increasing subsequence of nums.
def length_of_lis(nums):
    tails = []                        # tails[k] = smallest tail of an LIS of length k+1
    for x in nums:
        i = bisect.bisect_left(tails, x)   # where x would extend/replace
        if i == len(tails):
            tails.append(x)           # x extends the longest subsequence
        else:
            tails[i] = x              # x gives a smaller tail for that length
    return len(tails)                 # number of piles = LIS length''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="bisect_left (strictly increasing) vs bisect_right (non-decreasing); the tails array is NOT the actual subsequence.",
         example="length_of_lis([10,9,2,5,3,7,101,18]) -> 4 (e.g. [2,3,7,18])."),
    dict(cat="dsa", title="Word Break",
         answer="Given a string and a dictionary, can the string be segmented into a space-separated sequence of dictionary words? DP over prefixes: dp[i] is True if s[:i] can be segmented, which holds when some j<i has dp[j] True AND s[j:i] is in the dictionary.",
         tags=["word-break","dp","string","dsa"],
         code='''# Can s be segmented into words from the set `words`?
def word_break(s, words):
    words = set(words)                # O(1) membership
    dp = [False] * (len(s) + 1)
    dp[0] = True                      # empty prefix is trivially segmentable
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in words:   # prefix ok + suffix is a word
                dp[i] = True
                break
    return dp[len(s)]''',
         complexity="Time O(n^2 * k), space O(n).",
         pitfalls="Not using a set for the dictionary (slow); forgetting dp[0]=True.",
         example="word_break('leetcode', ['leet','code']) -> True; word_break('catsandog', ['cats','dog','sand','and','cat']) -> False."),
    dict(cat="dsa", title="Rotate Image (90 degrees, in place)",
         answer="Rotate an n x n matrix 90 degrees clockwise IN PLACE. Trick: TRANSPOSE the matrix (swap across the diagonal), then REVERSE each row. Transpose turns rows into columns; reversing each row completes the clockwise rotation.",
         tags=["rotate-image","matrix","in-place","dsa"],
         code='''# Rotate an n x n matrix 90 degrees clockwise, in place.
def rotate(matrix):
    n = len(matrix)
    # 1) Transpose: swap matrix[i][j] with matrix[j][i] (upper triangle only)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    # 2) Reverse each row to finish the clockwise rotation
    for row in matrix:
        row.reverse()
    return matrix''',
         complexity="Time O(n^2), space O(1) (in place).",
         pitfalls="Swapping the whole grid (only the upper triangle, j from i+1); reversing columns instead of rows gives a counter-clockwise turn.",
         example="rotate([[1,2,3],[4,5,6],[7,8,9]]) -> [[7,4,1],[8,5,2],[9,6,3]]."),
    dict(cat="conceptual", title="Why do Transformers need positional encodings but RNNs don't?",
         answer="An RNN reads tokens ONE AT A TIME in order, so position is baked into WHEN each token is processed — order is implicit. A Transformer processes all tokens SIMULTANEOUSLY through self-attention, which is permutation-invariant (it sees a 'bag' of tokens with no inherent order). So we must explicitly ADD position information to each token's embedding, or 'dog bites man' and 'man bites dog' would be indistinguishable. It is the price of parallelism: you gain speed and long-range attention but must re-inject the ordering an RNN got for free.",
         tags=["positional-encoding","transformer","rnn","why"],
         example="Shuffle the words fed to a Transformer with no positional encoding and the output is unchanged — proof it is order-blind without them."),
    dict(cat="ml_system_design", title="Design a Fraud Detection System",
         answer="1) CLARIFY: block fraudulent transactions in real time; metric = fraud caught (recall) vs false blocks (precision), latency <100ms. 2) FRAME as ML: binary classification (fraud/legit), heavily imbalanced. 3) DATA & FEATURES: amount, velocity (txns per minute), device/IP, geo-mismatch, account age; labels come from chargebacks (which arrive late). 4) MODEL: gradient-boosted trees or a neural net; handle imbalance with class weights; a rules layer for known patterns. 5) SERVING: score inline in the payment path; allow / review / deny by threshold; a feature store for real-time features. 6) EVALUATION: precision/recall + PR-AUC offline, then online with a manual-review feedback loop; monitor for drift as fraudsters adapt.",
         tags=["fraud-detection","ml-system-design","imbalance","real-time"],
         example="A charge from a new device in a new country for 10x the usual amount scores high-risk and is sent to manual review before completing."),
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

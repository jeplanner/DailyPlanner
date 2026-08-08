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
    dict(cat="dsa", title="Trapping Rain Water (two pointers)",
         answer="Compute how much water is trapped between bars of a histogram after rain. Water above any bar is bounded by the shorter of the tallest bar to its left and to its right. Two-pointer trick: move the side with the smaller running max inward, adding (that side's max - current height) each step — O(n) time, O(1) space, no precomputed arrays.",
         tags=["trapping-rain-water","two-pointers","array","hard","dsa"],
         code='''# Total water trapped between bars after rain (two-pointer).
def trap(height):
    if not height:
        return 0
    left, right = 0, len(height) - 1
    left_max, right_max = height[left], height[right]
    water = 0
    while left < right:
        if left_max < right_max:        # the left side bounds the water
            left += 1
            left_max = max(left_max, height[left])
            water += left_max - height[left]
        else:                           # the right side bounds the water
            right -= 1
            right_max = max(right_max, height[right])
            water += right_max - height[right]
    return water''',
         complexity="Time O(n), space O(1).",
         pitfalls="Moving the wrong pointer (always advance the smaller-max side); adding water before updating that side's max.",
         example="trap([0,1,0,2,1,0,1,3,2,1,2,1]) -> 6."),
    dict(cat="dsa", title="Largest Rectangle in Histogram (monotonic stack)",
         answer="Find the largest rectangle that fits under a histogram. Keep a stack of indices with INCREASING heights; when a shorter bar appears, pop taller bars and compute the rectangle each can form — its height is the popped bar, its width spans from the previous shorter bar to the current index. A sentinel 0 at the end flushes the stack.",
         tags=["largest-rectangle","monotonic-stack","histogram","hard","dsa"],
         code='''# Area of the largest rectangle under a histogram (monotonic stack).
def largest_rectangle_area(heights):
    stack = []                 # indices of bars with increasing height
    max_area = 0
    heights = heights + [0]    # sentinel forces the stack to flush
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            top = stack.pop()
            height = heights[top]
            # width runs from the previous shorter bar (exclusive) to i
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    return max_area''',
         complexity="Time O(n) amortized, space O(n).",
         pitfalls="Getting the width wrong after popping (use the new stack top); forgetting the trailing sentinel.",
         example="largest_rectangle_area([2,1,5,6,2,3]) -> 10  (the 5,6 pair widened)."),
    dict(cat="dsa", title="Longest Increasing Subsequence (patience + binary search)",
         answer="Length of the longest strictly increasing subsequence in O(n log n). Maintain 'tails', where tails[i] is the smallest possible tail of an increasing subsequence of length i+1. For each number, binary-search its insertion point: if it extends the array it lengthens the LIS, otherwise it replaces a tail to keep options open. The length of tails is the answer.",
         tags=["longest-increasing-subsequence","binary-search","patience-sorting","dp","dsa"],
         code='''# Length of the longest strictly increasing subsequence (patience sorting).
import bisect
def length_of_lis(nums):
    tails = []          # tails[i] = smallest tail of an LIS of length i+1
    for num in nums:
        pos = bisect.bisect_left(tails, num)   # where num belongs
        if pos == len(tails):
            tails.append(num)      # num extends the longest subsequence
        else:
            tails[pos] = num       # num improves an existing length's tail
    return len(tails)''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Using bisect_right (allows equal values -> non-strict); thinking 'tails' is an actual LIS (only its length is meaningful).",
         example="length_of_lis([10,9,2,5,3,7,101,18]) -> 4  ([2,3,7,101])."),
    dict(cat="dsa", title="Word Break (DP)",
         answer="Decide whether a string can be segmented into a sequence of dictionary words. DP over prefixes: dp[i] is True if s[:i] can be fully segmented. For each end i, look for a split point j where s[:j] is already breakable AND s[j:i] is a dictionary word. A set gives O(1) word lookups.",
         tags=["word-break","dynamic-programming","string","dp","dsa"],
         code='''# Can s be segmented into a space-separated sequence of dictionary words?
def word_break(s, word_dict):
    words = set(word_dict)
    dp = [False] * (len(s) + 1)
    dp[0] = True                     # the empty prefix is trivially breakable
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in words:   # s[:j] breakable AND s[j:i] a word
                dp[i] = True
                break
    return dp[len(s)]''',
         complexity="Time O(n^2) (times substring cost), space O(n).",
         pitfalls="Greedy matching (must try all split points); not using a set (slow lookups).",
         example="word_break('leetcode', ['leet','code']) -> True."),
    dict(cat="dsa", title="Generate Parentheses (backtracking)",
         answer="Generate all combinations of n well-formed pairs of parentheses. Backtrack while maintaining counts of open and close brackets used: you may add '(' while open < n, and add ')' only while close < open (never close more than you've opened). A complete string of length 2n is a valid result.",
         tags=["generate-parentheses","backtracking","recursion","dsa"],
         code='''# All combinations of n well-formed pairs of parentheses.
def generate_parenthesis(n):
    result = []
    def backtrack(current, open_count, close_count):
        if len(current) == 2 * n:
            result.append(current)          # used all n pairs
            return
        if open_count < n:
            backtrack(current + "(", open_count + 1, close_count)   # add '('
        if close_count < open_count:        # only close what is open
            backtrack(current + ")", open_count, close_count + 1)
    backtrack("", 0, 0)
    return result''',
         complexity="Time O(4^n / sqrt(n)) (Catalan number of results), space O(n) recursion.",
         pitfalls="Allowing ')' when close >= open (invalid strings); generating all 2^(2n) strings then filtering (wasteful).",
         example="generate_parenthesis(3) -> ['((()))','(()())','(())()','()(())','()()()']."),
    dict(cat="dsa", title="Palindrome Partitioning (backtracking)",
         answer="Return every way to cut a string so that all pieces are palindromes. Backtrack from a start index, trying each possible next cut end; only recurse into a piece if it's a palindrome. When the start reaches the end of the string, the accumulated path is one valid partition.",
         tags=["palindrome-partitioning","backtracking","string","recursion","dsa"],
         code='''# All ways to partition s so every substring is a palindrome.
def partition(s):
    result = []
    def is_pal(sub):
        return sub == sub[::-1]
    def backtrack(start, path):
        if start == len(s):
            result.append(path[:])          # reached the end with a valid cut
            return
        for end in range(start + 1, len(s) + 1):
            piece = s[start:end]
            if is_pal(piece):               # only recurse on palindromic pieces
                path.append(piece)
                backtrack(end, path)
                path.pop()
    backtrack(0, [])
    return result''',
         complexity="Time O(n * 2^n) worst case, space O(n) recursion.",
         pitfalls="Forgetting to copy path[:] when recording; re-checking palindromes redundantly (can memoize).",
         example="partition('aab') -> [['a','a','b'],['aa','b']]."),
    dict(cat="glossary", title="Beam search",
         answer="A decoding strategy that keeps the top-B most probable partial sequences ('beams') at each step, instead of committing to one (greedy) or sampling. It explores several hypotheses in parallel and returns the highest-scoring complete sequence — better quality than greedy for translation/summarization at B times the compute. Larger B isn't always better (can get bland).",
         tags=["beam-search","decoding","nlp","generation"],
         example="With beam width 4, a translator keeps the 4 best partial translations at each step, expands each, and finally returns the most probable full sentence — often better than greedy's single path."),
    dict(cat="glossary", title="Embedding",
         answer="A dense, low-dimensional vector representation of a discrete object (word, user, item, image) learned so that SIMILAR objects land near each other. Embeddings turn sparse categorical data into a compact space where distance means semantic similarity — powering search, recommendations, and as inputs to neural nets.",
         tags=["embedding","representation","vectors","similarity","ml"],
         example="Word2Vec places 'king' and 'queen' close together, and 'king' - 'man' + 'woman' lands near 'queen' — the geometry captures meaning."),
    dict(cat="glossary", title="Vector database",
         answer="A database optimized for storing high-dimensional EMBEDDING vectors and finding the nearest ones to a query vector fast (approximate nearest-neighbour search). It's the backbone of semantic search and RAG: embed items once, index them, then retrieve by similarity in milliseconds even over billions of vectors. Examples: FAISS, Pinecone, Milvus.",
         tags=["vector-database","embeddings","ann","semantic-search","rag"],
         example="A RAG system stores document embeddings in a vector DB; a user query is embedded and the DB returns the top-k most similar chunks to feed the LLM."),
    dict(cat="glossary", title="Approximate Nearest Neighbor (ANN / HNSW)",
         answer="ANN search trades a little accuracy for HUGE speed when finding the closest vectors among millions — exact search is too slow. HNSW (Hierarchical Navigable Small World) is a popular graph-based ANN index: it builds layered proximity graphs so a search greedily hops toward the query in near-logarithmic time. It powers vector databases.",
         tags=["approximate-nearest-neighbor","ann","hnsw","vector-search","indexing"],
         example="Finding the 10 most similar product embeddings to a query among 100M items, HNSW returns them in milliseconds at ~99% recall instead of scanning all 100M."),
    dict(cat="glossary", title="Chain-of-thought prompting",
         answer="A prompting technique that asks a model to produce intermediate REASONING STEPS before its final answer, rather than answering immediately. Externalizing the reasoning markedly improves performance on multi-step arithmetic, logic, and commonsense tasks, because the model 'thinks out loud' and builds on earlier steps.",
         tags=["chain-of-thought","prompting","reasoning","llm"],
         example="Instead of blurting '27', a model prompted to 'think step by step' writes '3 groups of 9 is 27' — and gets multi-step math right far more often."),
    dict(cat="glossary", title="Few-shot vs zero-shot learning",
         answer="Ways an LLM tackles a task from the prompt alone, with no weight updates. ZERO-SHOT: you just describe the task ('Translate to French:') and the model does it. FEW-SHOT: you include a handful of worked EXAMPLES in the prompt so the model infers the pattern (in-context learning). Few-shot usually beats zero-shot on tricky or unusual output formats.",
         tags=["few-shot","zero-shot","in-context-learning","llm","prompting"],
         example="Zero-shot: 'Classify sentiment: I loved it.' Few-shot: show 3 labeled examples first, then ask — the examples pin down your exact label format and boost accuracy."),
    dict(cat="glossary", title="Data drift vs concept drift",
         answer="Two ways a deployed model degrades. DATA (covariate) DRIFT: the input distribution changes but the input->output relationship holds (e.g. a new user demographic appears). CONCEPT DRIFT: the relationship itself changes — the same inputs now map to different outputs (e.g. spam tactics evolve). Both demand monitoring and retraining, but concept drift is harder because the labels' meaning shifted.",
         tags=["data-drift","concept-drift","monitoring","mlops"],
         example="A demand model sees data drift when a new city's traffic patterns appear; it sees concept drift when a pandemic changes how everyone shops, breaking the old feature-to-demand mapping."),
    dict(cat="conceptual", title="Why does dropout act as a regularizer?",
         answer="Dropout randomly zeroes a fraction of neurons on each training step, so the network can't rely on any single neuron or a fragile co-adaptation of neurons — each must learn features useful on their own. It's effectively training an ENSEMBLE of exponentially many weight-sharing sub-networks and averaging them at test time, which cuts variance and overfitting. At inference dropout is off and activations are scaled to match the training-time expectation.",
         tags=["dropout","regularization","overfitting","ensemble","why"],
         example="A big net that memorized training data through a few 'super-neuron' pathways can't do that with dropout — knocking out random units forces redundant, robust features, so validation accuracy rises even as training accuracy drops."),
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

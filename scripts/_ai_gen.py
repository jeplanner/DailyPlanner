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
    dict(cat="dsa", title="Number of Islands (DFS flood-fill)",
         answer="Count connected groups of '1' (land) in a 2-D grid of '1'/'0'. Scan every cell; when you hit unvisited land, increment the count and DFS/flood-fill its whole landmass, sinking each visited cell to '0' so it isn't counted again. Explores 4-directional neighbours.",
         tags=["number-of-islands","dfs","grid","flood-fill","graph","dsa"],
         code='''# Count connected groups of '1' (land) in a grid via DFS flood-fill.
def num_islands(grid):
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    def sink(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != '1':
            return                # off-grid or water/visited -> stop
        grid[r][c] = '0'          # mark visited by sinking the land
        sink(r+1, c); sink(r-1, c); sink(r, c+1); sink(r, c-1)  # 4 neighbours
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1        # a fresh island
                sink(r, c)        # sink its whole landmass
    return count''',
         complexity="Time O(rows*cols), space O(rows*cols) worst-case recursion.",
         pitfalls="Not marking cells visited (infinite loop / double count); mixing up row/col bounds.",
         example="num_islands([['1','1','0'],['1','0','0'],['0','0','1']]) -> 2."),
    dict(cat="dsa", title="Word Ladder (shortest transformation, BFS)",
         answer="Find the length of the shortest chain from begin to end where each step changes ONE letter and every intermediate word is in the dictionary. BFS explores words level by level, so the first time you reach 'end' you've used the fewest steps. Remove words as you visit them to avoid revisiting.",
         tags=["word-ladder","bfs","graph","shortest-path","dsa"],
         code='''# Shortest transformation length from begin to end, one letter at a time.
from collections import deque
def ladder_length(begin, end, word_list):
    words = set(word_list)            # O(1) membership tests
    if end not in words:
        return 0
    queue = deque([(begin, 1)])       # (current word, steps taken so far)
    while queue:
        word, steps = queue.popleft()
        if word == end:
            return steps              # BFS guarantees this is shortest
        for i in range(len(word)):
            for ch in "abcdefghijklmnopqrstuvwxyz":
                nxt = word[:i] + ch + word[i+1:]   # change one letter
                if nxt in words:
                    words.remove(nxt)              # mark visited
                    queue.append((nxt, steps + 1))
    return 0''',
         complexity="Time O(N * L * 26) where N=words, L=word length; space O(N).",
         pitfalls="Using DFS (won't give shortest); not marking visited (revisits explode).",
         example="ladder_length('hit','cog',['hot','dot','dog','lot','log','cog']) -> 5."),
    dict(cat="dsa", title="Binary Tree Zigzag Level-Order Traversal",
         answer="Traverse a binary tree level by level, but ALTERNATE direction: left-to-right on the first level, right-to-left on the next, and so on. Standard BFS by levels; use a deque per level and append to the front when going right-to-left, then flip the direction each level.",
         tags=["zigzag","bfs","binary-tree","level-order","dsa"],
         code='''# Level-order traversal alternating left->right / right->left per level.
from collections import deque
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def zigzag_level_order(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    left_to_right = True
    while queue:
        level = deque()
        for _ in range(len(queue)):       # process exactly one level
            node = queue.popleft()
            if left_to_right:
                level.append(node.val)      # normal order
            else:
                level.appendleft(node.val)  # reversed order
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(list(level))
        left_to_right = not left_to_right   # flip direction each level
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Reversing the whole result at the end (wrong per-level flip); losing the level boundary (fix the for-loop count up front).",
         example="Tree 3 -> (9, 20 -> (15, 7)) gives [[3],[20,9],[15,7]]."),
    dict(cat="dsa", title="Decode Ways (DP)",
         answer="Count how many ways a digit string can be decoded where 1->A, 2->B, ..., 26->Z. It's a Fibonacci-like DP: at each position you can take one digit (if not '0') or two digits (if they form 10..26). dp[i] = dp[i-1] (single) + dp[i-2] (pair). Track two rolling values for O(1) space.",
         tags=["decode-ways","dynamic-programming","string","dp","dsa"],
         code='''# Count ways to decode a digit string where 1->A ... 26->Z.
def num_decodings(s):
    if not s or s[0] == '0':
        return 0                       # leading zero can't decode
    prev, curr = 1, 1                  # dp[i-2], dp[i-1]
    for i in range(1, len(s)):
        cur = 0
        if s[i] != '0':                # single-digit decode is valid
            cur += curr
        two = int(s[i-1:i+1])          # the two-digit number
        if 10 <= two <= 26:            # valid pair 10..26
            cur += prev
        prev, curr = curr, cur
    return curr''',
         complexity="Time O(n), space O(1).",
         pitfalls="Mishandling '0' (only valid as part of 10/20); off-by-one in the two-digit slice.",
         example="num_decodings('226') -> 3  (2 2 6 | 22 6 | 2 26)."),
    dict(cat="dsa", title="Unique Paths II (grid with obstacles)",
         answer="Count paths from top-left to bottom-right moving only right or down, where some cells are obstacles (1) you can't enter. DP where dp[c] = paths from top + paths from left; an obstacle zeroes its cell. A single rolling row gives O(cols) space.",
         tags=["unique-paths","dynamic-programming","grid","obstacles","dp","dsa"],
         code='''# Count right/down paths top-left to bottom-right, avoiding obstacles (1).
def unique_paths_with_obstacles(grid):
    if not grid or grid[0][0] == 1:
        return 0                       # blocked start -> no paths
    cols = len(grid[0])
    dp = [0] * cols
    dp[0] = 1                          # one way to be at the start
    for row in grid:
        for c in range(cols):
            if row[c] == 1:
                dp[c] = 0              # no path through an obstacle
            elif c > 0:
                dp[c] += dp[c-1]       # from top (dp[c]) + from left (dp[c-1])
    return dp[-1]''',
         complexity="Time O(rows*cols), space O(cols).",
         pitfalls="Forgetting to zero an obstacle cell; not handling a blocked start/end.",
         example="unique_paths_with_obstacles([[0,0,0],[0,1,0],[0,0,0]]) -> 2."),
    dict(cat="dsa", title="Maximal Square (DP)",
         answer="Find the largest square containing only 1's in a binary matrix and return its area. DP where dp[r][c] = side length of the largest square whose bottom-right corner is (r,c). If the cell is 1, it's 1 + min of the top, left, and top-left neighbours (all three must support the square). Answer is best_side squared.",
         tags=["maximal-square","dynamic-programming","matrix","dp","dsa"],
         code='''# Area of the largest all-1's square in a binary matrix.
def maximal_square(matrix):
    if not matrix:
        return 0
    rows, cols = len(matrix), len(matrix[0])
    dp = [[0] * (cols + 1) for _ in range(rows + 1)]   # padded with a 0 border
    best = 0
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            if matrix[r-1][c-1] == 1:
                # a square here is limited by its smallest neighbour + 1
                dp[r][c] = min(dp[r-1][c], dp[r][c-1], dp[r-1][c-1]) + 1
                best = max(best, dp[r][c])
    return best * best''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Returning the side instead of the area; forgetting the min-of-three (any smaller neighbour caps the square).",
         example="maximal_square([[1,0,1,0,0],[1,0,1,1,1],[1,1,1,1,1],[1,0,0,1,0]]) -> 4."),
    dict(cat="dsa", title="House Robber II (circular street)",
         answer="Max money robbing houses arranged in a CIRCLE where adjacent houses can't both be robbed (and the first and last are adjacent). Trick: the first and last can never both be taken, so run the linear house-robber twice — once excluding the last house, once excluding the first — and take the better result.",
         tags=["house-robber","dynamic-programming","circular","dp","dsa"],
         code='''# Max non-adjacent sum where houses form a circle (first & last adjacent).
def rob_circular(nums):
    if len(nums) == 1:
        return nums[0]
    def rob_line(houses):
        prev, curr = 0, 0
        for money in houses:
            prev, curr = curr, max(curr, prev + money)  # skip vs take
        return curr
    # never rob both ends: try [0..n-2] and [1..n-1], keep the max
    return max(rob_line(nums[:-1]), rob_line(nums[1:]))''',
         complexity="Time O(n), space O(1).",
         pitfalls="Applying the linear solution directly (double-counts the wrap-around adjacency); mishandling the single-house case.",
         example="rob_circular([2,3,2]) -> 3  (can't take both end 2's since they're adjacent)."),
    dict(cat="dsa", title="Jump Game II (fewest jumps)",
         answer="Given nums where nums[i] is the max jump length from index i, return the FEWEST jumps to reach the last index. Greedy BFS-by-levels: track the farthest index reachable in the current jump; when you reach the end of the current jump's range, you must jump, so increment the count and extend the reach to the farthest seen.",
         tags=["jump-game","greedy","array","bfs","dsa"],
         code='''# Fewest jumps to reach the last index; nums[i] = max jump from i.
def jump(nums):
    jumps = 0
    current_end = 0        # boundary reachable with the jumps taken so far
    farthest = 0           # farthest index seen while scanning this level
    for i in range(len(nums) - 1):     # no need to jump from the last index
        farthest = max(farthest, i + nums[i])
        if i == current_end:           # reached the edge -> must jump now
            jumps += 1
            current_end = farthest      # new boundary is the farthest reach
    return jumps''',
         complexity="Time O(n), space O(1).",
         pitfalls="Iterating to the last index (adds a phantom jump); confusing 'farthest' with 'current_end'.",
         example="jump([2,3,1,1,4]) -> 2  (index 0 -> 1 -> 4)."),
    dict(cat="glossary", title="Greedy decoding",
         answer="In sequence generation (translation, text), greedy decoding picks the single HIGHEST-probability token at each step and feeds it back to generate the next. Fast and deterministic, but short-sighted: a locally best token can lead to a worse overall sentence. Beam search and sampling exist to explore alternatives greedy misses.",
         tags=["greedy-decoding","nlp","generation","decoding"],
         example="A model doing greedy decoding might commit to 'The' early and never recover if a better sentence started with 'A' — beam search keeps several candidates to avoid that trap."),
    dict(cat="glossary", title="Prompt engineering",
         answer="The practice of crafting the input text (the 'prompt') to steer a large language model toward a desired output — via clear instructions, worked examples (few-shot), role framing, or step-by-step ('chain-of-thought') cues. Since the model conditions entirely on its context, small wording changes can shift quality a lot.",
         tags=["prompt-engineering","llm","nlp","in-context-learning"],
         example="Adding 'Let's think step by step' to a math prompt often makes the model show its reasoning and get the right answer, versus blurting a wrong one."),
    dict(cat="glossary", title="ROUGE",
         answer="A family of metrics for summarization/translation that measures OVERLAP between generated text and reference text — mainly recall of n-grams (ROUGE-N) or longest common subsequence (ROUGE-L). Higher means more of the reference's content was captured. It rewards content overlap, not fluency or meaning.",
         tags=["rouge","nlp","evaluation","summarization","metric"],
         example="If the reference is 'the cat sat on the mat' and the model outputs 'the cat sat', ROUGE-1 recall counts how many reference words were recovered."),
    dict(cat="glossary", title="n-gram",
         answer="A contiguous sequence of n items (usually words or characters) from text: unigrams are single words, bigrams pairs, trigrams triples. Classic language models estimate the next word's probability from the previous n-1 words. Simple and fast, but blind to long-range context and exploding in count as n grows.",
         tags=["n-gram","nlp","language-model","statistics"],
         example="For 'I love NLP', the bigrams are ('I','love') and ('love','NLP') — a bigram model predicts the next word from just the one before."),
    dict(cat="glossary", title="Stemming vs Lemmatization",
         answer="Two ways to reduce word variants to a base form. STEMMING chops suffixes with crude rules (running->run, studies->studi) — fast but can produce non-words. LEMMATIZATION uses a dictionary and part-of-speech to return a real base word (studies->study, better->good) — slower but linguistically correct.",
         tags=["stemming","lemmatization","nlp","preprocessing"],
         example="Stemming can turn 'caring' into 'car' (wrong!); lemmatization correctly returns 'care'."),
    dict(cat="glossary", title="Named-entity recognition (NER)",
         answer="An NLP task that finds and classifies named entities in text — people, organizations, locations, dates, amounts. It's a token-labeling problem used to extract structured facts from unstructured text; it powers search, question answering, and knowledge-graph building.",
         tags=["ner","named-entity-recognition","nlp","information-extraction"],
         example="In 'Sundar Pichai leads Google in California', NER tags 'Sundar Pichai'=PERSON, 'Google'=ORG, 'California'=LOCATION."),
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

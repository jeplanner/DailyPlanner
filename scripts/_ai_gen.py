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
    dict(cat="dsa", title="Majority Element (Boyer-Moore voting)",
         answer="Find the element appearing more than n/2 times. Boyer-Moore voting keeps a candidate and a count: when count hits 0, adopt the current element as the candidate; then increment if it matches, decrement if not. The majority element survives because it outnumbers all others combined. O(n) time, O(1) space.",
         tags=["majority-element","boyer-moore","voting","array","dsa"],
         code='''# The element appearing more than n/2 times (assumed to exist).
def majority_element(nums):
    candidate = None
    count = 0
    for x in nums:
        if count == 0:
            candidate = x         # adopt a new candidate when the count is 0
        count += 1 if x == candidate else -1   # vote for or against
    return candidate''',
         complexity="Time O(n), space O(1).",
         pitfalls="Assumes a majority exists; if unsure, verify the candidate with a second pass.",
         example="majority_element([2,2,1,1,1,2,2]) -> 2."),
    dict(cat="dsa", title="Missing Number",
         answer="An array holds n distinct numbers from 0..n with exactly one missing; find it. The sum of 0..n is n(n+1)/2; subtract the actual array sum to get the gap. (XOR also works and avoids overflow.) O(n) time, O(1) space.",
         tags=["missing-number","math","array","dsa"],
         code='''# The missing number from an array containing 0..n with one gap.
def missing_number(nums):
    n = len(nums)
    expected = n * (n + 1) // 2    # sum of 0, 1, ..., n
    return expected - sum(nums)    # the gap is exactly what's missing''',
         complexity="Time O(n), space O(1).",
         pitfalls="Integer overflow in low-level languages (use XOR instead); off-by-one on the range.",
         example="missing_number([3,0,1]) -> 2."),
    dict(cat="dsa", title="Move Zeroes",
         answer="Move all zeros to the end of an array IN PLACE while keeping the order of the non-zeros. Use a 'write' pointer for the next non-zero slot: scan and pack each non-zero toward the front, then fill the rest with zeros. O(n) time, O(1) space.",
         tags=["move-zeroes","two-pointers","array","in-place","dsa"],
         code='''# Move all zeros to the end in place, preserving non-zero order.
def move_zeroes(nums):
    write = 0                      # next slot for a non-zero value
    for x in nums:
        if x != 0:
            nums[write] = x        # pack non-zeros toward the front
            write += 1
    for i in range(write, len(nums)):
        nums[i] = 0                # fill the remainder with zeros
    return nums''',
         complexity="Time O(n), space O(1).",
         pitfalls="Breaking the relative order of non-zeros; forgetting to zero-fill the tail.",
         example="move_zeroes([0,1,0,3,12]) -> [1,3,12,0,0]."),
    dict(cat="dsa", title="Implement a Queue using two Stacks",
         answer="Build a FIFO queue from two LIFO stacks. Push onto an 'in' stack. To pop/peek, if the 'out' stack is empty, pour everything from 'in' into 'out' (which reverses the order), then take from 'out'. Each element is moved at most once, so operations are O(1) AMORTIZED.",
         tags=["queue-using-stacks","stack","queue","design","dsa"],
         code='''# A FIFO queue built from two LIFO stacks.
class MyQueue:
    def __init__(self):
        self.in_stack = []
        self.out_stack = []

    def push(self, x):
        self.in_stack.append(x)        # newest goes on the 'in' stack

    def _move(self):
        if not self.out_stack:         # only refill when 'out' is empty
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())  # reverses order

    def pop(self):
        self._move()
        return self.out_stack.pop()    # oldest element is now on top of 'out'

    def peek(self):
        self._move()
        return self.out_stack[-1]

    def empty(self):
        return not self.in_stack and not self.out_stack''',
         complexity="Amortized O(1) per operation; space O(n).",
         pitfalls="Refilling 'out' when it is not empty (breaks FIFO order); forgetting the amortized argument.",
         example="push(1), push(2): peek()->1, pop()->1, pop()->2."),
    dict(cat="dsa", title="Merge Sort",
         answer="The classic divide-and-conquer STABLE sort: recursively split the array in half, sort each half, then MERGE the two sorted halves by repeatedly taking the smaller front element. O(n log n) always, O(n) extra space, and stable.",
         tags=["merge-sort","divide-and-conquer","sorting","stable","dsa"],
         code='''# Stable O(n log n) sort by divide-and-conquer.
def merge_sort(a):
    if len(a) <= 1:
        return a                  # a single element is already sorted
    mid = len(a) // 2
    left = merge_sort(a[:mid])    # sort each half recursively
    right = merge_sort(a[mid:])
    res = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:   # <= (not <) keeps the sort STABLE
            res.append(left[i]); i += 1
        else:
            res.append(right[j]); j += 1
    res.extend(left[i:])          # append whichever half still has elements
    res.extend(right[j:])
    return res''',
         complexity="Time O(n log n) always, space O(n).",
         pitfalls="Using < instead of <= (loses stability); off-by-one in the merge loop.",
         example="merge_sort([5,2,4,1,3]) -> [1,2,3,4,5]."),
    dict(cat="glossary", title="Encoder-decoder (seq2seq)",
         answer="An architecture for turning one sequence into another (translation, summarization): the ENCODER reads the input into a context representation, and the DECODER generates the output token by token from it. Modern versions add attention so the decoder can look back at any input position. It is the shape behind machine translation and the original Transformer.",
         tags=["encoder-decoder","seq2seq","nlp","transformer"],
         example="Translating English to French: the encoder reads the English sentence; the decoder emits French words one at a time, attending to the relevant English words."),
    dict(cat="glossary", title="Focal loss",
         answer="A loss for extreme class imbalance (e.g. object detection) that DOWN-WEIGHTS easy, already-correct examples so training focuses on the HARD ones. It multiplies cross-entropy by (1-p)^gamma, shrinking the loss for confident-correct predictions and preventing many easy negatives from swamping the gradient.",
         tags=["focal-loss","imbalance","loss","deep-learning"],
         example="In detection where 99% of image regions are 'background', focal loss stops those easy backgrounds from drowning out the rare objects."),
    dict(cat="glossary", title="Huber loss",
         answer="A regression loss that behaves like squared error (MSE) for SMALL errors but like absolute error (MAE) for LARGE ones — combining MSE's smoothness with MAE's robustness to outliers. A threshold delta controls where it switches.",
         tags=["huber-loss","regression","loss","robustness"],
         example="Predicting house prices with a few extreme outliers: Huber loss won't let those outliers dominate training the way MSE would."),
    dict(cat="glossary", title="t-SNE / UMAP",
         answer="Techniques to project high-dimensional data (like embeddings) down to 2-D for VISUALIZATION, preserving local neighborhoods so similar points cluster together. t-SNE gives great visuals but is slow and non-deterministic; UMAP is faster and keeps more global structure. Use them to SEE the data, not as downstream features.",
         tags=["t-sne","umap","dimensionality-reduction","visualization"],
         example="Plot word embeddings with UMAP and you'll see clusters of related words (animals, countries) — a quick sanity check on what the model learned."),
    dict(cat="glossary", title="DBSCAN",
         answer="A clustering algorithm that groups points that are DENSELY packed together and marks isolated points as noise/outliers. Unlike k-means it finds arbitrary-shaped clusters and does not need you to pick the number of clusters (you set a neighborhood radius and a min-points threshold). Great for spatial data and anomaly detection.",
         tags=["dbscan","clustering","unsupervised","anomaly-detection"],
         example="Clustering GPS check-ins, DBSCAN finds dense hotspots (a mall, a stadium) and labels lone points in empty areas as noise."),
    dict(cat="cs_fundamentals", title="Deadlock (the four conditions)",
         answer="A deadlock is when processes are stuck forever, each waiting for a resource another holds. It requires ALL FOUR conditions at once: mutual exclusion (resources non-shareable), hold-and-wait (hold one while waiting for another), no preemption (can't force a release), and circular wait (a cycle of waiters). Break any ONE to prevent it — e.g. impose a global lock ordering to kill circular wait.",
         tags=["deadlock","concurrency","os","cs"],
         example="Thread A holds lock 1 and wants lock 2; thread B holds lock 2 and wants lock 1 — circular wait, both stuck. Always acquiring locks in the same order prevents it."),
    dict(cat="cs_fundamentals", title="Sharding vs Replication",
         answer="Two ways to scale a database. SHARDING splits data ACROSS servers (each holds a subset, e.g. by hash of user-id) to handle more data and writes — but cross-shard queries are hard. REPLICATION copies the SAME data to multiple servers for availability and read scaling — but writes must propagate (replication lag). They are often combined.",
         tags=["sharding","replication","database","scaling","cs"],
         example="Shard orders by hash(user_id) across 10 servers for write scale, and give each shard 2 read replicas for availability and read throughput."),
    dict(cat="cs_fundamentals", title="Load balancing",
         answer="Distributing incoming requests across multiple servers so no single one is overwhelmed, using algorithms like round-robin, least-connections, or IP-hash. It enables horizontal scaling and high availability (a dead server is removed via health checks). Layer-4 balances on IP/port; Layer-7 on HTTP content.",
         tags=["load-balancing","scaling","availability","cs"],
         example="A load balancer spreads traffic across 5 app servers; if one crashes, health checks route around it with no downtime."),
    dict(cat="conceptual", title="Why can two O(n log n) sorts (merge sort vs quicksort) perform so differently?",
         answer="Big-O hides the CONSTANTS and the worst case. Quicksort is O(n log n) on AVERAGE and usually faster in practice because it sorts in place (cache-friendly, low memory) with small constants — but its WORST case is O(n^2) on already-sorted or adversarial input (bad pivots). Merge sort is O(n log n) GUARANTEED and stable, but uses O(n) extra memory and has worse cache behaviour. So the 'same' complexity can mean very different real-world speed, memory, and stability — which is why libraries use hybrids (Timsort, introsort).",
         tags=["sorting","big-o","constants","why"],
         example="Python's sort (Timsort) is a merge-sort variant chosen for stability and real-world speed; C++ std::sort uses introsort (quicksort that falls back to heapsort to dodge the O(n^2) trap)."),
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

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
    dict(cat="dsa", title="Bellman-Ford (shortest path with negative edges)",
         answer="Compute shortest distances from a source in a graph that MAY have negative edge weights (where Dijkstra fails). Relax every edge V-1 times — after k rounds all shortest paths using at most k edges are correct. A final relaxation pass that still improves any distance proves a reachable NEGATIVE CYCLE exists.",
         tags=["bellman-ford","shortest-path","negative-weights","graph","dynamic-programming","dsa"],
         code='''# Shortest distances from source, allowing negative edges; detects neg cycles.
def bellman_ford(n, edges, source):
    # edges: list of (u, v, weight); nodes 0..n-1
    dist = [float('inf')] * n
    dist[source] = 0
    for _ in range(n - 1):            # relax all edges n-1 times
        for u, v, w in edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    for u, v, w in edges:             # one more pass -> detects a negative cycle
        if dist[u] != float('inf') and dist[u] + w < dist[v]:
            return None               # negative cycle reachable from source
    return dist''',
         complexity="Time O(V*E), space O(V).",
         pitfalls="Skipping the unreachable (inf) guard before relaxing; forgetting the negative-cycle detection pass.",
         example="bellman_ford(3, [(0,1,4),(0,2,5),(1,2,-3)], 0) -> [0,4,1]."),
    dict(cat="dsa", title="Flood Fill",
         answer="The 'paint bucket' operation: starting at a pixel, recolor it and every 4-connected neighbour of the SAME original color to a new color. DFS/BFS from the start, stopping at cells that don't match the original color. Guard the no-op case where the new color equals the old (else infinite recursion).",
         tags=["flood-fill","dfs","grid","recursion","dsa"],
         code='''# Fill a region starting at (sr, sc) with new_color, like a paint bucket.
def flood_fill(image, sr, sc, new_color):
    rows, cols = len(image), len(image[0])
    old_color = image[sr][sc]
    if old_color == new_color:
        return image                  # nothing to change (avoids infinite loop)
    def dfs(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or image[r][c] != old_color:
            return
        image[r][c] = new_color       # paint this cell
        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)
    dfs(sr, sc)
    return image''',
         complexity="Time O(rows*cols), space O(rows*cols) recursion.",
         pitfalls="Infinite loop when new_color == old_color; checking color equality after painting.",
         example="flood_fill([[1,1,1],[1,1,0],[1,0,1]], 1, 1, 2) -> [[2,2,2],[2,2,0],[2,0,1]]."),
    dict(cat="dsa", title="01 Matrix (distance to nearest zero)",
         answer="For each cell in a binary matrix, compute the distance to the nearest 0. MULTI-SOURCE BFS: seed the queue with every 0 (distance 0) at once and expand outward; the first time BFS reaches a cell is its shortest distance. Doing BFS from each 1 separately would be far slower.",
         tags=["01-matrix","bfs","multi-source","grid","dsa"],
         code='''# Distance from each cell to the nearest 0 (multi-source BFS from all zeros).
from collections import deque
def update_matrix(mat):
    rows, cols = len(mat), len(mat[0])
    dist = [[-1] * cols for _ in range(rows)]
    queue = deque()
    for r in range(rows):
        for c in range(cols):
            if mat[r][c] == 0:
                dist[r][c] = 0        # zeros are the BFS sources
                queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1   # first visit = shortest
                queue.append((nr, nc))
    return dist''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Running single-source BFS per 1 (too slow); revisiting cells (mark with -1 sentinel).",
         example="update_matrix([[0,0,0],[0,1,0],[1,1,1]]) -> [[0,0,0],[0,1,0],[1,2,1]]."),
    dict(cat="dsa", title="Redundant Connection (Union-Find)",
         answer="A graph is a tree of n nodes plus ONE extra edge that creates a cycle; find that redundant edge (the last one that closes a cycle). Process edges with Union-Find: for each edge, if its two endpoints are already connected (same root), that edge is the redundant one; otherwise union them.",
         tags=["redundant-connection","union-find","cycle-detection","graph","dsa"],
         code='''# In a graph that's a tree plus one extra edge, find the edge to remove.
def find_redundant_connection(edges):
    parent = list(range(len(edges) + 1))   # 1-indexed nodes
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]   # path compression
            x = parent[x]
        return x
    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru == rv:
            return [u, v]             # this edge closes a cycle -> redundant
        parent[ru] = rv               # union the two components
    return []''',
         complexity="Time O(n * α(n)) ~ O(n), space O(n).",
         pitfalls="Sizing parent by node count not edge count; returning the first cycle edge instead of the closing one.",
         example="find_redundant_connection([[1,2],[1,3],[2,3]]) -> [2,3]."),
    dict(cat="dsa", title="Network Delay Time (Dijkstra application)",
         answer="A signal starts at node k and travels along directed edges with given delays; return the time for ALL n nodes to receive it, or -1 if some can't. It's single-source shortest paths (Dijkstra): the answer is the MAXIMUM of the shortest distances to every node (the last one to hear the signal).",
         tags=["network-delay","dijkstra","shortest-path","graph","heap","dsa"],
         code='''# Time for a signal from node k to reach ALL nodes (Dijkstra); -1 if unreachable.
import heapq
def network_delay_time(times, n, k):
    graph = {i: [] for i in range(1, n + 1)}
    for u, v, w in times:
        graph[u].append((v, w))
    dist = {}
    heap = [(0, k)]                   # (elapsed time, node)
    while heap:
        d, node = heapq.heappop(heap)
        if node in dist:
            continue                  # already finalized
        dist[node] = d
        for nbr, w in graph[node]:
            if nbr not in dist:
                heapq.heappush(heap, (d + w, nbr))
    return max(dist.values()) if len(dist) == n else -1''',
         complexity="Time O(E log V), space O(V+E).",
         pitfalls="Returning the sum instead of the max distance; forgetting the -1 case when a node is unreachable.",
         example="network_delay_time([[2,1,1],[2,3,1],[3,4,1]], 4, 2) -> 2."),
    dict(cat="dsa", title="Shortest Path in Binary Matrix (8-directional BFS)",
         answer="Find the shortest clear path from the top-left to the bottom-right cell of an n×n 0/1 grid, moving in any of 8 directions through 0-cells; return the number of cells on it, or -1. Unweighted shortest path = BFS: expand level by level from the start, marking visited cells, and return the length when you reach the target.",
         tags=["shortest-path-binary-matrix","bfs","grid","8-directional","dsa"],
         code='''# Shortest clear path top-left to bottom-right in a 0/1 grid (8-directional).
from collections import deque
def shortest_path_binary_matrix(grid):
    n = len(grid)
    if grid[0][0] == 1 or grid[n-1][n-1] == 1:
        return -1                     # blocked start or end
    queue = deque([(0, 0, 1)])        # (row, col, cells in path so far)
    seen = {(0, 0)}
    while queue:
        r, c, length = queue.popleft()
        if r == n - 1 and c == n - 1:
            return length
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    queue.append((nr, nc, length + 1))
    return -1''',
         complexity="Time O(n^2), space O(n^2).",
         pitfalls="Skipping diagonal moves (8-directional, not 4); not marking cells seen when enqueuing (duplicates).",
         example="shortest_path_binary_matrix([[0,0,0],[1,1,0],[1,1,0]]) -> 4."),
    dict(cat="glossary", title="p-value",
         answer="In hypothesis testing, the probability of observing data at least as extreme as yours IF the null hypothesis were true. A small p-value (e.g. <0.05) means the data would be surprising under the null, so you reject it. It is NOT the probability the hypothesis is true, and 'not significant' isn't proof of no effect — always report an effect size too.",
         tags=["p-value","hypothesis-testing","statistics","significance"],
         example="An A/B test shows a 2% lift with p=0.01: if the change truly did nothing, you'd see a lift this big only 1% of the time — evidence the lift is real."),
    dict(cat="glossary", title="Confidence interval",
         answer="A range of plausible values for an unknown quantity, computed so that if you repeated the experiment many times, X% (e.g. 95%) of such intervals would contain the true value. Wider intervals mean more uncertainty (small samples). It conveys precision, not just a single point estimate.",
         tags=["confidence-interval","statistics","uncertainty","estimation"],
         example="A model's accuracy is 0.86 with a 95% CI of [0.83, 0.89] — narrow enough to trust it's meaningfully above 0.80, unlike a wide [0.70, 0.95]."),
    dict(cat="glossary", title="Statistical power",
         answer="The probability that a test correctly DETECTS a real effect (rejects a false null) — i.e. 1 minus the false-negative rate. Power rises with larger sample size, a bigger true effect, and lower noise. Under-powered experiments miss real effects and give unreliable, often exaggerated results when they do 'find' something.",
         tags=["statistical-power","hypothesis-testing","sample-size","experimentation"],
         example="To detect a 1% conversion lift at 80% power, an A/B test may need hundreds of thousands of users; run it under-powered and you'll likely see 'no significant effect' even if the lift is real."),
    dict(cat="glossary", title="Simpson's paradox",
         answer="A trend that appears in separate groups can REVERSE when the groups are combined (or vice versa), usually due to a lurking confounder or unequal group sizes. It's a warning that aggregated statistics can mislead — always check whether a relationship holds within the relevant subgroups.",
         tags=["simpsons-paradox","statistics","confounding","aggregation","bias"],
         example="A treatment looks worse overall but is actually better for BOTH mild and severe patients — the aggregate flipped because severe cases (lower success rate) were over-represented in the treatment group."),
    dict(cat="glossary", title="Confounding variable",
         answer="A variable that influences BOTH the supposed cause and the effect, creating a spurious association between them. Ignoring it leads to wrong causal conclusions; you control for it via randomization, stratification, or by including it in the model. It's the core reason correlation isn't causation.",
         tags=["confounding","causal-inference","bias","statistics"],
         example="Ice-cream sales correlate with drownings — but 'hot weather' is the confounder driving both; controlling for temperature makes the ice-cream/drowning link vanish."),
    dict(cat="ml_coding", title="k-Nearest Neighbors (from scratch)",
         answer="A lazy, non-parametric classifier: to predict a query's label, find the k training points closest to it (by Euclidean distance) and take the majority vote of their labels. There's no training beyond storing the data; all work happens at query time, which makes prediction O(n) per query.",
         tags=["knn","k-nearest-neighbors","classification","distance","ml-coding"],
         code='''# k-Nearest-Neighbors: predict the majority label among the k closest points.
import math
from collections import Counter
def knn_predict(train_X, train_y, query, k):
    dists = []
    for x, y in zip(train_X, train_y):
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(x, query)))  # Euclidean
        dists.append((d, y))
    dists.sort(key=lambda t: t[0])                # nearest first
    top_k = [label for _, label in dists[:k]]
    return Counter(top_k).most_common(1)[0][0]    # majority vote''',
         complexity="Time O(n*d + n log n) per query, space O(n*d).",
         pitfalls="Not scaling features (large-range features dominate the distance); even k causing vote ties.",
         example="knn_predict([[0,0],[0,1],[5,5],[5,4]], [0,0,1,1], [0,0.5], 3) -> 0."),
    dict(cat="ml_coding", title="Logistic Regression prediction (from scratch)",
         answer="A logistic-regression model outputs a probability by squashing a linear combination of features through the SIGMOID: p = 1/(1+e^-(w·x+b)). Classify positive when p >= 0.5. This is the forward/prediction pass (training would fit w and b via gradient descent on log-loss).",
         tags=["logistic-regression","sigmoid","classification","ml-coding"],
         code='''# Logistic regression prediction: sigmoid of a linear score -> probability.
import math
def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))

def logistic_predict(weights, bias, x):
    z = sum(w * xi for w, xi in zip(weights, x)) + bias   # linear score
    prob = sigmoid(z)                                      # squash to (0,1)
    return prob, 1 if prob >= 0.5 else 0                   # probability and class''',
         complexity="Time O(d) per prediction, space O(1).",
         pitfalls="math.exp overflow for very negative z (clip z or use a stable sigmoid); wrong decision threshold for imbalanced data.",
         example="logistic_predict([0.5, -0.5], 0.0, [2, 0]) -> (~0.73, 1)."),
    dict(cat="conceptual", title="Why is accuracy a poor metric for imbalanced classification?",
         answer="When one class dominates (say 99% negatives), a trivial model that always predicts the majority class scores 99% accuracy while being useless — it never catches the rare positive you actually care about (fraud, disease). Accuracy rewards the easy majority and hides failure on the minority. Use precision/recall, F1, PR-AUC, or class-weighted metrics that focus on the rare class, and choose the threshold by the real cost of false positives vs false negatives.",
         tags=["imbalance","accuracy","metrics","precision-recall","why"],
         example="A fraud detector that flags nothing gets 99.8% accuracy on a 0.2%-fraud dataset yet catches zero fraud — recall (0%) exposes it instantly where accuracy lied."),
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

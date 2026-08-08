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
    dict(cat="dsa", title="Dijkstra's Shortest Path (min-heap)",
         answer="Find the shortest distance from a source to every node in a weighted graph with NON-NEGATIVE edge weights. Use a min-heap keyed by tentative distance: pop the closest unfinalized node, relax its neighbours (update if a shorter path is found and push them). Skip stale heap entries whose distance is worse than the best known. Greedy and correct because non-negative weights mean the first time you pop a node it's final.",
         tags=["dijkstra","shortest-path","graph","heap","greedy","dsa"],
         code='''# Shortest distances from a source in a weighted graph (non-negative weights).
import heapq
def dijkstra(graph, source):
    # graph: dict node -> list of (neighbour, weight)
    dist = {source: 0}
    heap = [(0, source)]              # (distance so far, node)
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, float('inf')):
            continue                  # stale entry -> skip
        for nbr, w in graph.get(node, []):
            nd = d + w
            if nd < dist.get(nbr, float('inf')):
                dist[nbr] = nd        # found a shorter path
                heapq.heappush(heap, (nd, nbr))
    return dist''',
         complexity="Time O((V+E) log V), space O(V).",
         pitfalls="Using it with negative weights (use Bellman-Ford instead); not skipping stale heap entries.",
         example="graph {A:[(B,1),(C,4)], B:[(C,2)], C:[]}, dijkstra from A -> {A:0, B:1, C:3}."),
    dict(cat="dsa", title="Topological Sort (Kahn's algorithm)",
         answer="Produce a linear ordering of a Directed Acyclic Graph where every edge u->v has u before v. Kahn's BFS approach: compute in-degrees, start a queue with all zero-in-degree nodes, repeatedly pop one into the order and decrement its neighbours' in-degrees, enqueueing any that hit zero. If the order doesn't include all nodes, the graph had a CYCLE.",
         tags=["topological-sort","kahn","graph","bfs","dag","dsa"],
         code='''# Topological order of a DAG via Kahn's algorithm (BFS on in-degrees).
from collections import deque
def topological_sort(num_nodes, edges):
    graph = {i: [] for i in range(num_nodes)}
    indegree = [0] * num_nodes
    for u, v in edges:                # edge u -> v
        graph[u].append(v)
        indegree[v] += 1
    queue = deque(i for i in range(num_nodes) if indegree[i] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph[node]:
            indegree[nbr] -= 1        # remove this edge
            if indegree[nbr] == 0:
                queue.append(nbr)
    return order if len(order) == num_nodes else []   # [] signals a cycle''',
         complexity="Time O(V+E), space O(V+E).",
         pitfalls="Not detecting cycles (check the output length); assuming a unique order (many are valid).",
         example="4 nodes, edges [(0,1),(0,2),(1,3),(2,3)] -> [0,1,2,3] (one valid order)."),
    dict(cat="dsa", title="Union-Find / Disjoint Set Union (DSU)",
         answer="A data structure that tracks a partition of elements into disjoint sets, supporting near-O(1) 'find which set' and 'union two sets'. Two optimizations make it almost constant: PATH COMPRESSION (flatten the tree during find) and UNION BY RANK (attach the shorter tree under the taller). It underpins Kruskal's MST, connectivity, and cycle detection in undirected graphs.",
         tags=["union-find","dsu","disjoint-set","graph","path-compression","dsa"],
         code='''# Disjoint-Set Union with path compression and union by rank.
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))   # each node starts as its own root
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]   # path compression
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False               # already in the same set
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra            # attach the smaller tree under the larger
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True''',
         complexity="Near O(1) amortized per op (inverse-Ackermann), space O(n).",
         pitfalls="Skipping path compression or union by rank (degrades to O(n)); forgetting union returns False when already joined.",
         example="uf=UnionFind(5); uf.union(0,1); uf.union(1,2): find(0)==find(2) is True, find(0)==find(3) is False."),
    dict(cat="dsa", title="Course Schedule (cycle detection)",
         answer="Given course prerequisites, decide whether ALL courses can be finished — equivalently, whether the prerequisite directed graph is acyclic. Run Kahn's topological sort and count how many nodes you can process; if you process all of them there's no cycle (a valid order exists), otherwise a cycle blocks completion.",
         tags=["course-schedule","cycle-detection","topological-sort","graph","dsa"],
         code='''# Can all courses be finished? (no cycle in the prerequisite graph)
from collections import deque
def can_finish(num_courses, prerequisites):
    graph = {i: [] for i in range(num_courses)}
    indegree = [0] * num_courses
    for course, prereq in prerequisites:   # must take prereq before course
        graph[prereq].append(course)
        indegree[course] += 1
    queue = deque(i for i in range(num_courses) if indegree[i] == 0)
    taken = 0
    while queue:
        node = queue.popleft()
        taken += 1
        for nbr in graph[node]:
            indegree[nbr] -= 1
            if indegree[nbr] == 0:
                queue.append(nbr)
    return taken == num_courses            # all taken -> acyclic''',
         complexity="Time O(V+E), space O(V+E).",
         pitfalls="Reversing the edge direction (prereq -> course); comparing to the wrong count.",
         example="can_finish(2, [[1,0]]) -> True; can_finish(2, [[1,0],[0,1]]) -> False (mutual prereqs = cycle)."),
    dict(cat="dsa", title="Number of Connected Components",
         answer="Count the connected components of an undirected graph. Build an adjacency list, then iterate all nodes; each unvisited node starts a new component and a DFS/BFS marks everything reachable from it. The number of times you launch a fresh traversal is the component count. (Union-Find also solves this.)",
         tags=["connected-components","graph","dfs","union-find","dsa"],
         code='''# Count connected components in an undirected graph using DFS.
def count_components(n, edges):
    graph = {i: [] for i in range(n)}
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)
    seen = set()
    def dfs(node):
        seen.add(node)
        for nbr in graph[node]:
            if nbr not in seen:
                dfs(nbr)
    count = 0
    for i in range(n):
        if i not in seen:
            count += 1                # a new component
            dfs(i)
    return count''',
         complexity="Time O(V+E), space O(V+E).",
         pitfalls="Treating the graph as directed (add both directions); recursion depth on huge graphs (use iterative BFS).",
         example="count_components(5, [[0,1],[1,2],[3,4]]) -> 2  ({0,1,2} and {3,4})."),
    dict(cat="dsa", title="Bipartite Graph Check (BFS 2-coloring)",
         answer="Decide whether a graph's nodes can be 2-colored so that no edge connects same-colored nodes (equivalently, the graph has no odd-length cycle). BFS from each uncolored node, coloring neighbours the opposite color; if you ever find an edge whose endpoints already share a color, it's not bipartite.",
         tags=["bipartite","graph","bfs","coloring","dsa"],
         code='''# Is the graph 2-colorable (bipartite)? BFS coloring.
from collections import deque
def is_bipartite(graph):
    # graph: adjacency list (list of lists) over nodes 0..n-1
    color = {}
    for start in range(len(graph)):
        if start in color:
            continue
        color[start] = 0
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nbr in graph[node]:
                if nbr not in color:
                    color[nbr] = 1 - color[node]   # opposite color
                    queue.append(nbr)
                elif color[nbr] == color[node]:
                    return False       # same color across an edge -> not bipartite
    return True''',
         complexity="Time O(V+E), space O(V).",
         pitfalls="Not handling disconnected components (loop over all start nodes); coloring with the same value.",
         example="is_bipartite([[1,3],[0,2],[1,3],[0,2]]) -> True (a 4-cycle); a triangle is False."),
    dict(cat="dsa", title="Rotting Oranges (multi-source BFS)",
         answer="In a grid of empty(0)/fresh(1)/rotten(2) cells, each minute every rotten orange rots its 4-adjacent fresh neighbours; return the minutes until none are fresh, or -1 if some fresh orange can never rot. Multi-source BFS: seed the queue with ALL rotten oranges at time 0 and spread outward level by level, tracking the max time and counting remaining fresh cells.",
         tags=["rotting-oranges","bfs","grid","multi-source","dsa"],
         code='''# Minutes until all fresh oranges (1) rot from rotten ones (2); -1 if impossible.
from collections import deque
def oranges_rotting(grid):
    rows, cols = len(grid), len(grid[0])
    queue = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                queue.append((r, c, 0))   # (row, col, minute) - all sources
            elif grid[r][c] == 1:
                fresh += 1
    minutes = 0
    while queue:
        r, c, t = queue.popleft()
        minutes = max(minutes, t)
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                grid[nr][nc] = 2          # this fresh orange rots now
                fresh -= 1
                queue.append((nr, nc, t + 1))
    return minutes if fresh == 0 else -1  # -1 if any fresh orange is unreachable''',
         complexity="Time O(rows*cols), space O(rows*cols).",
         pitfalls="Seeding BFS from one source (must be all rotten at once); returning minutes when fresh remain.",
         example="oranges_rotting([[2,1,1],[1,1,0],[0,1,1]]) -> 4."),
    dict(cat="glossary", title="Cosine annealing (LR schedule)",
         answer="A learning-rate schedule that smoothly decreases the LR along a COSINE curve from its initial value down to near zero over training (or a cycle). The curved decay — fast at first, slow near the end — often generalizes better than step decay; 'warm restarts' periodically reset it to help escape and explore multiple minima.",
         tags=["cosine-annealing","learning-rate","schedule","optimization","training"],
         example="Over 100 epochs, cosine annealing eases the LR from 0.1 to ~0 along a half-cosine, spending more time at low LR to fine-tune near the minimum."),
    dict(cat="glossary", title="Group vs Layer normalization",
         answer="Normalization layers that, unlike batch norm, don't depend on the batch. LAYER NORM normalizes across all features of a SINGLE example (used in Transformers; works for any batch size or sequence length). GROUP NORM splits channels into groups and normalizes within each group (used in vision with tiny batches). Both stabilize training without coupling to batch statistics.",
         tags=["group-norm","layer-norm","normalization","deep-learning"],
         example="Transformers use layer norm so each token is normalized independently of the batch; a detection model with batch size 2 uses group norm because batch norm's statistics would be too noisy."),
    dict(cat="glossary", title="Calibration (Platt / isotonic)",
         answer="Making a classifier's predicted PROBABILITIES match real-world frequencies — if it says 0.8, about 80% of such cases should be positive. Many models (SVMs, boosted trees, deep nets) are miscalibrated. PLATT SCALING fits a logistic function to the scores; ISOTONIC REGRESSION fits a flexible monotonic mapping. It's measured with reliability diagrams / Expected Calibration Error.",
         tags=["calibration","platt-scaling","isotonic","probability","evaluation"],
         example="A boosted tree that outputs overconfident 0.95s is passed through isotonic regression so a 0.95 really means ~95% positive — important when the probability feeds a downstream decision."),
    dict(cat="glossary", title="Bootstrap sampling",
         answer="Estimating the uncertainty of a statistic by resampling your dataset WITH REPLACEMENT many times, computing the statistic on each resample, and inspecting the spread. It needs no distributional assumptions and yields confidence intervals for almost anything; it's also the 'bagging' that powers random forests.",
         tags=["bootstrap","resampling","statistics","confidence-interval","bagging"],
         example="For a confidence interval on a model's AUC, resample the test set 1000 times with replacement, compute AUC each time, and take the 2.5th-97.5th percentiles."),
    dict(cat="glossary", title="Inverse propensity weighting (IPW)",
         answer="A technique to correct for BIAS in logged/observational data where some items were shown more than others. Weight each observed example by 1/(probability it was shown) — its 'propensity' — so under-exposed items count more, approximating what a randomized experiment would have shown. It's core to off-policy evaluation of recommenders and ads.",
         tags=["inverse-propensity-weighting","ipw","off-policy","causal-inference","debiasing"],
         example="Evaluating a new ranking policy from logs where popular items dominated, IPW up-weights the rare-item impressions so the estimate isn't skewed toward what the old system happened to show."),
    dict(cat="behavioral", title="Tell me about your biggest failure and what you learned (behavioral: failure)",
         answer="Use STAR. SITUATION: I led a team ML project and, overconfident in the model, skipped a proper validation split and tests to 'save time'. TASK: deliver a working classifier on schedule. ACTION / what went wrong: two days before the deadline we found our 95% accuracy was inflated by DATA LEAKAGE — an ID feature correlated with the label — and the real model was far worse; we scrambled to fix it. RESULT: we salvaged it but shipped late and below target. LESSON: I now treat a clean validation setup and leakage checks as non-negotiable FIRST steps, not afterthoughts — and I've caught two leaks since. HOW TO TELL IT: own the failure honestly, focus on the concrete lesson and the behaviour change, and show growth rather than blame.",
         tags=["behavioral","star","failure","lesson-learned"],
         example="Skipped a proper validation split to save time; a data leak inflated accuracy to 95% and we shipped late — now leak checks are my non-negotiable first step."),
    dict(cat="behavioral", title="Tell me about a time you received difficult feedback (behavioral: feedback)",
         answer="Use STAR. SITUATION: A mentor told me my code worked but was unreadable — nobody could review or reuse it. TASK: take the criticism constructively and improve. ACTION: instead of getting defensive, I asked for specific examples, studied a well-structured open-source codebase, adopted clear naming, docstrings, and smaller functions, then asked the mentor to re-review. RESULT: my next PR was approved with zero readability comments and a teammate reused my module. LESSON: feedback about my work isn't a judgment of me; acting on it quickly built credibility. HOW TO TELL IT: show you sought specifics, acted fast, and it paid off — with no defensiveness.",
         tags=["behavioral","star","feedback","growth"],
         example="A mentor said my code was unreadable; I asked for specifics, refactored with clear naming + docstrings, and my next PR passed review with a teammate reusing it."),
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

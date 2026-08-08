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
    dict(cat="ml_system_design", title="Design a Trending / Hot-content ranking system",
         answer="Surface content that is 'hot' RIGHT NOW (news, posts, videos). (1) CLARIFY & SCALE: rank by recent MOMENTUM, not all-time popularity; react within minutes, resist gaming, stay fresh. (2) DATA: real-time engagement events (views, likes, shares, comments) with timestamps. (3) SIGNALS/FEATURES: velocity (engagement per unit time), acceleration (is it speeding up?), and TIME DECAY so old items fade (e.g. score = engagement / (age+2)^gravity, the Hacker-News/Reddit trick), normalized by content age and base rate. (4) MODEL/SCORING: often a hand-tuned decay formula for interpretability, optionally a learned model predicting near-future engagement; then de-dup and add diversity. (5) EVAL: offline correlation with what actually trended next; online CTR/dwell on the trending module. (6) SERVING/MONITORING/AB: streaming aggregation over sliding time windows in a fast store, recompute scores every few minutes, filter bots and cap per-user influence, A/B on engagement and freshness.",
         tags=["trending","hot-ranking","time-decay","streaming","ml-system-design"],
         example="A Reddit-style hot score divides upvotes by (age_hours + 2)^1.8 so a post with 100 upvotes in 1 hour outranks one with 500 over 3 days — trending reflects momentum, not raw totals."),
    dict(cat="ml_system_design", title="Design a Similar-items / Related-products system",
         answer="Show items related to the one a user is viewing ('customers also viewed / bought'). (1) CLARIFY & SCALE: relevant complements/substitutes, low latency, billions of item pairs, cold-start for new items. (2) DATA & LABELS: co-view / co-purchase logs (items in the same session/order) plus item metadata. (3) REPRESENTATION: item embeddings from co-occurrence (item2vec) or content (text/image), category, price band. (4) METHODS: collaborative 'bought together' via co-occurrence with popularity normalization, content-based similarity (embedding cosine + ANN) for cold items, usually blended; a re-ranker adds business rules (margin, in-stock). (5) EVAL: offline recall of actual co-purchases; online CTR / attach rate / revenue per view. (6) SERVING/MONITORING/AB: precompute top-k similar items per item into a KV store (nightly + near-real-time refresh), A/B on attach rate, and filter out-of-stock items and the current item itself.",
         tags=["similar-items","related-products","item2vec","ann","ml-system-design"],
         example="Viewing a phone, the 'related' rail blends co-purchased accessories (cases, chargers) from order co-occurrence with semantically similar phones from embedding ANN — precomputed per item for instant serving."),
    dict(cat="ml_system_design", title="Design a Session-based Recommendation system",
         answer="Recommend the next item from the user's CURRENT session behaviour, even for anonymous users with no history. (1) CLARIFY & SCALE: capture short-term intent (what they're doing now), which can differ from long-term taste; real-time, works logged-out. (2) DATA & LABELS: sequences of in-session events (clicks/views) with the next item as the label. (3) FEATURES: the ordered sequence of recent item IDs/embeddings, dwell time, category transitions, time of day. (4) MODEL: sequence models — a GRU/Transformer (GRU4Rec, SASRec) that encodes the session and predicts the next item — or a simple item-to-item Markov transition model as a baseline. (5) EVAL: next-item Recall@k / MRR on held-out sessions; beware temporal leakage (train on past, test on future). (6) SERVING/MONITORING/AB: hold the session state, run the sequence model with ANN over item embeddings, A/B on session conversion / add-to-cart, and fall back to popularity for the very first click.",
         tags=["session-based","sequential-recommendation","gru4rec","sasrec","ml-system-design"],
         example="An anonymous shopper clicks tent -> sleeping bag -> stove; a session Transformer infers a 'camping trip' intent and next-recommends a lantern, even with zero prior history."),
    dict(cat="ml_system_design", title="Design an LLM Chatbot with RAG",
         answer="Build a question-answering assistant grounded in a company's knowledge base. (1) CLARIFY & SCALE: accurate, up-to-date, SOURCE-CITED answers with low hallucination; latency budget; knowledge changes often. (2) DATA: the document corpus (docs, tickets, wikis) chunked into passages; optionally labeled Q&A for eval. (3) INGESTION: chunk documents, embed each chunk, index in a vector DB, store metadata (source, recency, permissions). (4) PIPELINE: at query time embed the question, RETRIEVE top-k relevant chunks (ANN), optionally re-rank, then prompt an LLM to answer USING those chunks and cite them; refuse when no good context exists. (5) EVAL: retrieval recall@k, answer faithfulness/groundedness and helpfulness (human or LLM-as-judge), hallucination rate. (6) SERVING/MONITORING/AB: cache embeddings, refresh the index on doc changes, enforce access control AT retrieval, log queries + citations, monitor hallucinations/staleness, A/B on resolution rate.",
         tags=["rag","llm","chatbot","retrieval","vector-database","ml-system-design"],
         example="Asked 'how do I reset my password?', the bot embeds the query, pulls the 4 most relevant help articles from the vector DB, and the LLM answers strictly from them with links — escalating if nothing relevant is found."),
    dict(cat="ml_system_design", title="Design a Content Moderation / Toxicity system",
         answer="Detect and act on harmful content (toxicity, hate, spam, violence) at scale. (1) CLARIFY & SCALE: high recall on real harms with low false positives on benign speech; multilingual, ADVERSARIAL (users evade), huge volume, low latency; policy-defined categories. (2) DATA & LABELS: human-moderated labels per policy category and user reports; class imbalance and labeling subjectivity; keep a gold eval set. (3) FEATURES: text (transformer embeddings), image/video signals, user/behavioural context, obfuscation-robust normalization, regex for known slurs. (4) MODEL: fine-tuned multi-label transformer classifiers per category, plus rules for clear violations and an escalation path; calibrate a threshold per category by harm severity. (5) EVAL: precision/recall per category at chosen thresholds, PR-AUC, and fairness checks across groups/languages. (6) SERVING/MONITORING/AB: real-time scoring + async human review for borderline, tiered enforcement (down-rank -> warn -> remove -> ban), appeals feed back as labels, and audits for bias and evasion drift.",
         tags=["content-moderation","toxicity","classification","trust-and-safety","ml-system-design"],
         example="A comment with a lightly obfuscated slur is normalized, scored above the hate threshold, auto-hidden pending review, and the reviewer's decision becomes a fresh training label."),
    dict(cat="ml_system_design", title="Design a Demand Forecasting system",
         answer="Predict future demand (sales, orders, traffic) to drive inventory/staffing/pricing. (1) CLARIFY & SCALE: forecast per item/store/region over a horizon (hours to weeks) WITH uncertainty; thousands-to-millions of series; strong seasonality. (2) DATA & LABELS: historical demand time series plus calendar, promotions, weather, price, holidays; handle intermittent/missing series. (3) FEATURES: lags and rolling stats, seasonality (day-of-week, month), holidays/events, price/promo, hierarchy (item->category->store). (4) MODEL: classical baselines (ARIMA/ETS/Prophet), gradient-boosted trees on engineered features, or GLOBAL deep models (DeepAR / Temporal Fusion Transformer) learning across series; predict QUANTILES for uncertainty. (5) EVAL: backtesting with rolling-origin splits; MAPE/SMAPE/WAPE and pinball loss for quantiles; NEVER shuffle time. (6) SERVING/MONITORING/AB: batch forecasts refreshed daily, monitor error and drift, reconcile hierarchical forecasts, alert on big misses, and A/B downstream on stockouts/waste.",
         tags=["demand-forecasting","time-series","quantile","temporal-fusion-transformer","ml-system-design"],
         example="For each store-SKU, a Temporal Fusion Transformer uses lagged sales + upcoming promotions + holidays to predict next week's demand at the 10th/50th/90th percentiles, so high-margin items are stocked to the 90th percentile."),
    dict(cat="glossary", title="Feature hashing (the hashing trick)",
         answer="Map high-cardinality categorical features (e.g. millions of user or URL IDs) into a fixed-size vector by HASHING each feature to an index, instead of maintaining a giant vocabulary. It bounds memory and handles unseen categories at inference, at the cost of occasional hash COLLISIONS (two features share a slot). Common in large-scale linear/CTR models.",
         tags=["feature-hashing","hashing-trick","high-cardinality","ctr","features"],
         example="Hashing 10M URL strings into a ~1M-dim space lets a logistic CTR model run in fixed memory; rare collisions add a little noise but avoid storing a 10M-entry vocabulary."),
    dict(cat="glossary", title="Negative sampling",
         answer="A training shortcut for problems with a huge output space (word2vec, recommendations, retrieval) where scoring against ALL negatives is too expensive. Instead of contrasting the positive against every negative, sample a small set of random negatives per positive and train to score the positive higher. It makes training tractable and is the core of word2vec's skip-gram.",
         tags=["negative-sampling","word2vec","retrieval","training","contrastive"],
         example="Training a retrieval model, for each (query, clicked-item) positive you sample 5 random non-clicked items as negatives instead of scoring against the whole billion-item catalog."),
    dict(cat="glossary", title="Target encoding",
         answer="Encode a high-cardinality categorical feature by replacing each category with a statistic of the TARGET for that category (e.g. the mean label). Compact and powerful, but prone to LEAKAGE/overfitting — mitigate with smoothing toward the global mean and out-of-fold computation (encode each row using folds that exclude it).",
         tags=["target-encoding","categorical","features","leakage","encoding"],
         example="Replace each 'city' with its historical average conversion rate — but compute that average out-of-fold so a row's own label doesn't leak into its own feature."),
    dict(cat="glossary", title="Selection bias",
         answer="When the collected data isn't representative of the population you care about because of HOW samples were selected, leading models to conclusions that don't generalize. Survivorship bias is a special case (only 'survivors' are observed). Fix it by understanding the sampling mechanism, reweighting, or collecting representative data.",
         tags=["selection-bias","survivorship-bias","sampling","bias","statistics"],
         example="Training a loan-default model only on APPROVED applicants (rejected ones have no outcome) biases it — it never learned from the risky applications that were screened out."),
    dict(cat="dsa", title="Kruskal's Minimum Spanning Tree",
         answer="Find the minimum total weight to connect all nodes of a weighted undirected graph. Kruskal's greedy approach: sort all edges by weight ascending, then add each edge if it connects two DIFFERENT components (checked with Union-Find), skipping edges that would form a cycle. Stop once n-1 edges are chosen.",
         tags=["kruskal","mst","minimum-spanning-tree","union-find","greedy","dsa"],
         code='''# Minimum Spanning Tree total weight via Kruskal (sort edges + union-find).
def kruskal_mst(n, edges):
    # edges: list of (weight, u, v); nodes 0..n-1
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    total = 0
    used = 0
    for w, u, v in sorted(edges):        # cheapest edges first
        ru, rv = find(u), find(v)
        if ru != rv:                     # adding it won't form a cycle
            parent[ru] = rv
            total += w
            used += 1
            if used == n - 1:            # spanning tree is complete
                break
    return total''',
         complexity="Time O(E log E) for the sort, space O(n).",
         pitfalls="Forgetting the cycle check (Union-Find); not stopping at n-1 edges.",
         example="kruskal_mst(4, [(1,0,1),(2,1,2),(3,0,2),(4,2,3)]) -> 7."),
    dict(cat="dsa", title="Prim's Minimum Spanning Tree",
         answer="Build a Minimum Spanning Tree by GROWING it from a start node: repeatedly add the cheapest edge that connects the current tree to a new node, using a min-heap of candidate edges. Skip nodes already in the tree. Complements Kruskal — Prim is often better for dense graphs.",
         tags=["prim","mst","minimum-spanning-tree","heap","greedy","dsa"],
         code='''# Minimum Spanning Tree total weight via Prim (grow tree with a min-heap).
import heapq
def prim_mst(n, graph):
    # graph: adjacency dict node -> list of (neighbour, weight)
    visited = set()
    heap = [(0, 0)]                      # (edge weight, node); start at node 0
    total = 0
    while heap and len(visited) < n:
        w, node = heapq.heappop(heap)
        if node in visited:
            continue                     # already in the tree
        visited.add(node)
        total += w                       # add this edge to the MST
        for nbr, weight in graph.get(node, []):
            if nbr not in visited:
                heapq.heappush(heap, (weight, nbr))
    return total''',
         complexity="Time O(E log V), space O(V+E).",
         pitfalls="Adding a node twice (check visited on pop); starting total at the first pop of weight 0.",
         example="prim_mst(4, {0:[(1,1),(2,3)], 1:[(0,1),(2,2)], 2:[(1,2),(0,3),(3,4)], 3:[(2,4)]}) -> 7."),
    dict(cat="dsa", title="Cheapest Flights Within K Stops (Bellman-Ford)",
         answer="Find the cheapest price from src to dst using at most k stops. It's a bounded Bellman-Ford: relax all edges k+1 times (k stops = k+1 flights), but crucially use a SNAPSHOT of last round's distances each pass so a single relaxation round can't chain multiple flights and exceed the stop limit.",
         tags=["cheapest-flights","bellman-ford","shortest-path","bounded","graph","dsa"],
         code='''# Cheapest price from src to dst using at most k stops (bounded Bellman-Ford).
def find_cheapest_price(n, flights, src, dst, k):
    INF = float('inf')
    dist = [INF] * n
    dist[src] = 0
    for _ in range(k + 1):               # at most k stops == k+1 edges
        new_dist = dist[:]               # snapshot: only use last round's values
        for u, v, price in flights:
            if dist[u] != INF and dist[u] + price < new_dist[v]:
                new_dist[v] = dist[u] + price
        dist = new_dist
    return dist[dst] if dist[dst] != INF else -1''',
         complexity="Time O(k*E), space O(n).",
         pitfalls="Relaxing in place (lets one round chain multiple flights, breaking the k-stop bound); off-by-one on k+1.",
         example="find_cheapest_price(3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 1) -> 200."),
    dict(cat="conceptual", title="Why do we scale/normalize features before training many models?",
         answer="Because many algorithms are SENSITIVE TO FEATURE MAGNITUDES. Distance-based methods (KNN, k-means, SVM-RBF) let a large-range feature (income in thousands) dominate a small one (age); gradient descent zig-zags and converges slowly when features have wildly different scales (an elongated loss surface); and L1/L2 regularization penalizes coefficients unfairly if features aren't comparable. Scaling (standardization or min-max) puts features on comparable ranges so each contributes fairly and optimization is well-conditioned. Tree-based models are the exception — they split on thresholds and ignore scale.",
         tags=["feature-scaling","normalization","gradient-descent","knn","why"],
         example="Without scaling, KNN on {age 20-70, income 20k-200k} ranks neighbours almost entirely by income; standardizing both to mean 0 / std 1 lets age matter too."),
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

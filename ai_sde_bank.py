"""AI SDE interview prep bank — an interactive, detailed study bank for a
new-grad targeting AI/ML Software Development Engineer roles (Amazon /
Google). Companion to AI_SDE_INTERVIEW_PLAN.md, but structured so each
topic is browsable, searchable, tagged, and explained in depth (with
worked code, complexity, pitfalls, and follow-ups) so a beginner can
actually learn from it.

Served read-only by routes/interview_prep.py at /api/ai-sde.
Fields: title (the question/topic), answer (detailed reasoning), code
(worked solution, monospace), example, complexity, pitfalls, followups,
tags. Optional fields are "" when unused.
"""

CATEGORIES = {
    "mindset": "Mindset & Strategy",
    "dsa": "Coding & DSA",
    "ml_concepts": "ML & AI Concepts",
    "ml_coding": "ML Coding (from scratch)",
    "ml_system_design": "ML System Design",
    "cs_fundamentals": "CS Fundamentals",
    "behavioral": "Behavioral (student)",
    "company": "Amazon & Google Process",
}

_CATEGORY_TAGS = {
    "mindset": ["mindset"], "dsa": ["dsa", "coding"], "ml_concepts": ["ml"],
    "ml_coding": ["ml", "coding"], "ml_system_design": ["ml", "system-design"],
    "cs_fundamentals": ["cs"], "behavioral": ["behavioral"], "company": ["process"],
}


def Q(cat, title, answer, tags, code="", example="", complexity="", pitfalls="", followups=""):
    return {"cat": cat, "title": title, "answer": answer, "code": code,
            "example": example, "complexity": complexity, "pitfalls": pitfalls,
            "followups": followups, "tags": tags}


ENTRIES = [
    # ─────────── Mindset & Strategy ───────────
    Q("mindset", "How should I approach a coding interview (out loud)?",
      "Interviewers score HOW you think, not just the final code. Follow a repeatable script every single time: (1) Clarify — restate the problem in your own words and ask about input size, ranges, duplicates, empty inputs. (2) Examples — walk through a small example by hand. (3) Brute force first — say the obvious O(n^2) idea so you have something correct, then say 'can we do better?'. (4) Optimize — name the pattern (sliding window, hashing, etc.) and explain WHY it helps. (5) Code — narrate as you type, using clear names. (6) Test — trace an example and check edge cases. Silence is the enemy: a wrong-but-explained approach scores far better than a right-but-silent one.",
      ["mindset", "coding", "communication", "framework"],
      pitfalls="Jumping straight to code without clarifying; going silent when stuck; not stating time/space complexity; not testing edge cases.",
      followups="What if you get stuck? Say what you've tried, restate the goal, try a smaller example — a structured struggle still scores."),
    Q("mindset", "A realistic study plan and the '70% rule'",
      "Consistency beats cramming: 2-3 focused hours daily for ~12-16 weeks (~300h) beats panicked weekends. Practice by PATTERN, never random — after each problem write a one-line 'recognition note' ('saw contiguous + longest -> sliding window') because recognizing the pattern from the prompt is the real skill. Attack your WEAKEST area first each week (it feels bad, that's the point). The '70% rule': in interviews you decide with ~70% certainty and a plan to close the rest — perfectionism freezes you. Do a timed mock every week from week 3; you cannot get good at interviews without doing interviews.",
      ["mindset", "study-plan", "patterns", "mock"],
      followups="How many problems? Quality over quantity — ~150 pattern-organized problems solved OUT LOUD beats 500 skimmed."),

    # ─────────── Coding & DSA ───────────
    Q("dsa", "Two Pointers — recognize & apply",
      "Trigger words: a SORTED array, finding a pair/triplet, comparing from both ends, or in-place work. Idea: use two indices moving toward each other (or one fast, one slow) so you scan in O(n) instead of checking all O(n^2) pairs. Because the array is sorted, if the current pair's sum is too small you move the LEFT pointer right (increase), too big you move the RIGHT pointer left (decrease) — each element is visited once.",
      ["two-pointers", "array", "sorted"],
      code="def two_sum_sorted(a, target):\n    i, j = 0, len(a) - 1\n    while i < j:\n        s = a[i] + a[j]\n        if s == target: return [i, j]\n        if s < target: i += 1   # need a bigger sum\n        else:          j -= 1   # need a smaller sum\n    return []",
      complexity="Time O(n), space O(1).",
      pitfalls="Only works on sorted data (or sort first, O(n log n)); watch i<j bounds to avoid using the same element twice.",
      followups="Three-sum? Fix one element, two-pointer the rest. Container with most water? Move the shorter wall inward."),
    Q("dsa", "Sliding Window — recognize & apply",
      "Trigger words: 'contiguous subarray/substring' + 'longest/shortest/at-most-k' with a condition. Idea: expand a window by moving RIGHT; when the window violates the condition, shrink from the LEFT until valid again, tracking the best window. Each element enters and leaves the window at most once, so it's O(n) instead of checking every subarray O(n^2).",
      ["sliding-window", "string", "array"],
      code="def longest_unique(s):\n    seen = {}          # char -> last index\n    left = best = 0\n    for right, ch in enumerate(s):\n        if ch in seen and seen[ch] >= left:\n            left = seen[ch] + 1   # jump past the duplicate\n        seen[ch] = right\n        best = max(best, right - left + 1)\n    return best",
      complexity="Time O(n), space O(min(n, alphabet)).",
      pitfalls="Forgetting to only shrink while invalid; off-by-one in window length (right-left+1).",
      followups="At most K distinct chars? Same skeleton, condition becomes len(window_counts) > K -> shrink."),
    Q("dsa", "Binary Search — including 'search on the answer'",
      "Trigger: a SORTED array, OR a problem asking to 'minimize the maximum / maximize the minimum' where you can check 'is X feasible?'. Idea: halve the search space each step -> O(log n). The powerful variant is binary-searching the ANSWER: if feasible(mid) is monotonic (true past some threshold), binary-search the smallest feasible value.",
      ["binary-search", "sorted", "search-on-answer"],
      code="def search(a, target):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if a[mid] == target: return mid\n        if a[mid] < target: lo = mid + 1\n        else:               hi = mid - 1\n    return -1",
      complexity="Time O(log n), space O(1).",
      pitfalls="Overflow in mid (use lo+(hi-lo)//2 in C++/Java); infinite loops from wrong lo/hi updates; boundary (<= vs <).",
      followups="Rotated sorted array? One half is always sorted — decide which side to search. Koko eating bananas? Binary search the eating speed."),
    Q("dsa", "Trees — BFS vs DFS",
      "Rule of thumb: LEVELS -> BFS (a queue); PATHS or SUBTREE work -> DFS (recursion/stack). DFS has three orders (preorder root-first, inorder left-root-right which yields sorted order for a BST, postorder children-first). Most tree problems are 'do something at each node and combine children's results' — that's postorder recursion.",
      ["tree", "bfs", "dfs", "recursion"],
      code="from collections import deque\ndef level_order(root):\n    if not root: return []\n    q, out = deque([root]), []\n    while q:\n        level = []\n        for _ in range(len(q)):     # process one full level\n            n = q.popleft(); level.append(n.val)\n            if n.left:  q.append(n.left)\n            if n.right: q.append(n.right)\n        out.append(level)\n    return out",
      complexity="Time O(n) nodes, space O(width) for BFS / O(height) for DFS.",
      pitfalls="Recursion depth on skewed trees (use an explicit stack); forgetting the base case (None).",
      followups="Validate a BST? Track (min,max) bounds down the recursion. Lowest common ancestor? Recurse and bubble up where both sides are found."),
    Q("dsa", "Graphs — BFS, DFS, and when to use each",
      "A grid or network of connectivity -> graph traversal. BFS (queue) finds the SHORTEST path in an UNWEIGHTED graph and explores level by level; DFS (stack/recursion) explores deep, good for connectivity/components/cycles. Mark nodes visited to avoid infinite loops. For a grid, neighbors are up/down/left/right.",
      ["graph", "bfs", "dfs", "grid"],
      code="def num_islands(grid):\n    if not grid: return 0\n    R, C, count = len(grid), len(grid[0]), 0\n    def sink(r, c):\n        if r<0 or c<0 or r>=R or c>=C or grid[r][c] != '1': return\n        grid[r][c] = '0'                      # mark visited\n        sink(r+1,c); sink(r-1,c); sink(r,c+1); sink(r,c-1)\n    for r in range(R):\n        for c in range(C):\n            if grid[r][c]=='1': count+=1; sink(r,c)\n    return count",
      complexity="Time O(V+E) (or O(rows*cols) for a grid), space O(V).",
      pitfalls="Forgetting visited-marking -> infinite loop; DFS stack overflow on huge grids (use BFS/iterative).",
      followups="Shortest path unweighted? BFS. With prerequisites/ordering? Topological sort. Weighted shortest path? Dijkstra."),
    Q("dsa", "Dynamic Programming — the 4-question method",
      "DP fits problems with OVERLAPPING subproblems and OPTIMAL substructure — usually phrased 'number of ways', 'min/max cost', 'can we reach'. Don't panic: always say four things out loud — (1) STATE: what does dp[i] mean? (2) TRANSITION: how does dp[i] use smaller states? (3) BASE CASE. (4) ANSWER: which dp value. If you can state those, you've solved it. Start top-down (recursion + memo) to find the recurrence, then convert to bottom-up (a table) to avoid recursion limits.",
      ["dp", "dynamic-programming", "memoization"],
      code="def coin_change(coins, amount):\n    # dp[a] = fewest coins to make amount a\n    INF = amount + 1\n    dp = [0] + [INF] * amount        # base: dp[0]=0\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a:\n                dp[a] = min(dp[a], dp[a-c] + 1)   # transition\n    return dp[amount] if dp[amount] != INF else -1  # answer",
      complexity="Time O(amount * #coins), space O(amount).",
      pitfalls="Wrong state definition (the #1 cause of failure); wrong iteration order; forgetting the base case.",
      followups="Grid paths? dp[r][c]=dp[r-1][c]+dp[r][c-1]. Edit distance / LCS? 2D DP on two strings."),
    Q("dsa", "Hashing — the 'have I seen this?' pattern",
      "Whenever you find yourself asking 'have I seen X before?', 'what's the count of X?', or 'does the complement exist?', reach for a hash map/set — it turns an O(n) inner search into O(1) average, dropping many O(n^2) solutions to O(n). Classic: Two Sum in one pass — for each number, check if (target - number) is already in the map.",
      ["hashing", "hashmap", "set"],
      code="def two_sum(nums, target):\n    seen = {}                     # value -> index\n    for i, x in enumerate(nums):\n        if target - x in seen:    # complement already seen?\n            return [seen[target-x], i]\n        seen[x] = i\n    return []",
      complexity="Time O(n), space O(n).",
      pitfalls="Hash lookups are O(1) AVERAGE (worst case O(n) with collisions); can't rely on ordering.",
      followups="Group anagrams? Key by the sorted string. Longest consecutive sequence? Use a set to check x-1 existence."),
    Q("dsa", "Heap / Top-K — when 'K largest/most frequent' appears",
      "Trigger: 'K largest / smallest / most frequent', or streaming data where you can't sort everything. A heap (priority queue) gives O(log k) insert/extract. For 'K largest', keep a MIN-heap of size k: if a new value beats the smallest, replace it — you keep only the top k in memory. Sorting everything is O(n log n); the heap approach is O(n log k), better when k << n.",
      ["heap", "priority-queue", "top-k"],
      code="import heapq\ndef k_largest(nums, k):\n    h = []                        # min-heap of size k\n    for x in nums:\n        heapq.heappush(h, x)\n        if len(h) > k:\n            heapq.heappop(h)      # drop the smallest\n    return sorted(h, reverse=True)",
      complexity="Time O(n log k), space O(k).",
      pitfalls="Python's heapq is a MIN-heap; negate values for a max-heap. Don't sort the whole array if k is small.",
      followups="Top K frequent? Count with a hash map, then heap by count. Merge K sorted lists? Heap of the list heads."),

    # ─────────── ML & AI Concepts ───────────
    Q("ml_concepts", "Bias-Variance trade-off (explained simply)",
      "Think of two failure modes. BIAS = the model is too simple and misses the real pattern (e.g., a straight line through curvy data) — it does badly on BOTH training and test data (underfitting). VARIANCE = the model is too complex and memorizes noise in the training data — great on training, bad on test (overfitting). Total error is roughly bias^2 + variance + irreducible noise. As you add complexity, bias drops but variance rises; the goal is the sweet spot with the lowest TEST error. To fix high bias: richer model / better features. To fix high variance: more data / regularization / simpler model.",
      ["bias-variance", "overfitting", "underfitting", "fundamentals"],
      example="A degree-1 polynomial on wavy data = high bias. A degree-15 polynomial = high variance (wiggles through every point). Degree-3 might be just right.",
      pitfalls="Confusing the two; only looking at training accuracy (always check the train-vs-validation gap).",
      followups="How do ensembles help? Bagging (Random Forest) reduces variance; boosting reduces bias."),
    Q("ml_concepts", "Overfitting — what it is and how to prevent it",
      "Overfitting = the model learns the training data's noise, so it performs great on training but poorly on new/validation data (a big gap between the two curves is the tell). Prevention toolkit, in rough order: (1) more or augmented data; (2) regularization (L1/L2, dropout); (3) a simpler model / fewer parameters; (4) early stopping (stop when validation loss starts rising); (5) cross-validation to detect it; (6) for trees, pruning / limiting depth. Always diagnose by plotting training vs validation performance.",
      ["overfitting", "regularization", "dropout", "early-stopping"],
      pitfalls="Tuning on the test set (leakage) — use a separate validation set; assuming more epochs are always better.",
      followups="What's underfitting? The opposite — too simple; fix with a more expressive model or better features."),
    Q("ml_concepts", "L1 vs L2 regularization",
      "Both add a penalty on the weights to the loss to discourage complexity. L2 (Ridge) penalizes the SQUARE of the weights -> shrinks them smoothly toward (but not exactly) zero; handles correlated features well; the default. L1 (Lasso) penalizes the ABSOLUTE value -> drives some weights EXACTLY to zero, giving automatic feature selection / sparsity. Rule of thumb: L1 when you suspect many useless features and want a sparse model; L2 as a general smoother. Elastic Net combines both.",
      ["regularization", "l1", "l2", "lasso", "ridge", "feature-selection"],
      followups="Why does L1 give sparsity? Its diamond-shaped constraint region has corners on the axes, so the optimum often lands where some weights are exactly 0."),
    Q("ml_concepts", "How gradient descent works (batch vs SGD vs mini-batch)",
      "Gradient descent minimizes a loss by repeatedly stepping the parameters in the direction that most reduces error — the NEGATIVE gradient: w <- w - lr * gradient. The learning rate (lr) sets the step size: too big -> it overshoots/diverges; too small -> it crawls. Variants differ by how much data each step uses: BATCH uses the whole dataset (stable, slow, memory-heavy); STOCHASTIC (SGD) uses one example (noisy, fast, can escape shallow minima); MINI-BATCH uses ~32-256 examples — the practical default. Momentum, RMSProp, and Adam adapt the step per-parameter and speed convergence.",
      ["gradient-descent", "sgd", "optimizer", "learning-rate", "adam"],
      pitfalls="Picking a bad learning rate; not normalizing features (makes the loss surface skewed and slow).",
      followups="What is Adam? Adaptive per-parameter learning rates using running averages of the gradient and its square — a strong default optimizer."),
    Q("ml_concepts", "Precision vs Recall (and the 95%-accuracy trap)",
      "From the confusion matrix: Precision = TP/(TP+FP) = 'of the ones I flagged positive, how many were right?'. Recall = TP/(TP+FN) = 'of all the actual positives, how many did I catch?'. Choose by the COST of each error: a spam filter favors PRECISION (don't trash real email); cancer screening / fraud favors RECALL (don't miss a real case). F1 is their harmonic mean when you want balance. The classic trap: a model with 95% accuracy can be useless if 95% of data is one class — it just predicts the majority. For imbalanced data, use precision/recall/F1 and PR-AUC, not accuracy.",
      ["precision", "recall", "f1", "metrics", "imbalance", "confusion-matrix"],
      example="1000 emails, 50 spam. 'Never spam' scores 95% accuracy but catches 0 spam (recall 0). Useless.",
      followups="How to fix class imbalance? Resample (SMOTE/undersample), class weights in the loss, and pick a threshold from the PR curve."),
    Q("ml_concepts", "The Transformer & self-attention (the big one)",
      "A Transformer processes a whole sequence IN PARALLEL and models relationships between all tokens using SELF-ATTENTION. Each token is projected into three vectors: Query, Key, Value. The attention weight between two tokens = softmax(Q . K^T / sqrt(d)) — i.e., each token 'looks at' every other token and weights them by relevance; the output is the weighted sum of Values. MULTI-HEAD attention does this in several subspaces at once (capturing syntax, meaning, etc.). Because there's no recurrence, POSITIONAL ENCODINGS inject word order. Why it won over RNNs: it's parallelizable (fast on GPUs) AND captures long-range dependencies far better. It's the foundation of BERT (encoder) and GPT (decoder).",
      ["transformer", "attention", "self-attention", "nlp", "llm", "deep-learning"],
      pitfalls="Saying 'it's just attention' without Q/K/V; forgetting positional encodings (order would be lost).",
      followups="Why divide by sqrt(d)? To keep the dot products from getting huge and saturating the softmax. Encoder vs decoder? BERT understands (encoder), GPT generates (decoder)."),
    Q("ml_concepts", "CNN vs RNN vs Transformer — when to use which",
      "CNNs exploit SPATIAL locality with shared filters -> images and grid/local-pattern data; parameter-efficient and parallel. RNNs/LSTMs process SEQUENCES with a hidden state carrying memory -> older NLP and time series; but they're sequential (slow) and struggle with long-range dependencies (vanishing gradients), which LSTMs' gates partly fix. TRANSFORMERS have largely replaced RNNs for sequence tasks because self-attention captures long dependencies and parallelizes. Quick pick: images -> CNN; sequences today -> Transformer; simple/tiny time series -> maybe an RNN/LSTM.",
      ["cnn", "rnn", "lstm", "transformer", "deep-learning"],
      followups="Why do RNNs struggle with long sequences? Gradients shrink across many steps (vanishing gradient); LSTMs add gates to remember/forget."),
    Q("ml_concepts", "What is an embedding?",
      "An embedding is a dense, low-dimensional vector that represents a discrete item (a word, user, or product) so that SEMANTIC similarity becomes GEOMETRIC closeness — similar items sit near each other. They're learned from data (e.g., word2vec, or jointly inside a network). They let models generalize (the famous 'king - man + woman ~ queen') and power search, recommendations, and all modern NLP. In practice you embed items, then use nearest-neighbor search to find similar ones.",
      ["embeddings", "vectors", "nlp", "similarity"],
      followups="How do you find similar embeddings fast at scale? Approximate nearest neighbor (ANN) indexes like HNSW / FAISS."),
    Q("ml_concepts", "Cross-validation — what and why",
      "Instead of a single train/test split (which can be lucky or unlucky), K-FOLD cross-validation splits the data into k parts, trains on k-1 and validates on the held-out fold, rotating k times and averaging the scores. This gives a more RELIABLE, lower-variance estimate of how the model generalizes, and uses the data efficiently — essential for hyperparameter tuning and small datasets. Use STRATIFIED k-fold for imbalanced classes so each fold keeps the class ratio.",
      ["cross-validation", "validation", "evaluation"],
      pitfalls="Leaking information across folds (e.g., scaling using the whole dataset before splitting)."),

    # ─────────── ML Coding (from scratch) ───────────
    Q("ml_coding", "Implement Logistic Regression with gradient descent",
      "They love 'code it from scratch' because it proves you understand the math under the library. Logistic regression predicts a probability with the sigmoid of a linear combination, and learns weights by gradient descent on the log-loss. The gradient of the log-loss w.r.t. weights is beautifully simple: X^T (predictions - y) / n.",
      ["logistic-regression", "gradient-descent", "from-scratch", "ml-coding"],
      code="import numpy as np\ndef sigmoid(z): return 1 / (1 + np.exp(-z))\n\ndef train(X, y, lr=0.1, epochs=1000):\n    n, d = X.shape\n    w, b = np.zeros(d), 0.0\n    for _ in range(epochs):\n        p = sigmoid(X @ w + b)          # predictions\n        error = p - y\n        w -= lr * (X.T @ error) / n     # gradient step\n        b -= lr * error.mean()\n    return w, b",
      complexity="Time O(epochs * n * d).",
      pitfalls="Not normalizing features; exp overflow in sigmoid (clip z); forgetting the bias term.",
      followups="Linear regression? Same loop with predictions = X@w+b and MSE loss (same gradient form)."),
    Q("ml_coding", "Implement K-Means clustering",
      "K-Means groups points into k clusters by repeating two steps until stable: (1) ASSIGN each point to its nearest centroid; (2) UPDATE each centroid to the mean of its assigned points. It minimizes within-cluster variance. It's simple and fast but sensitive to the initial centroids (use k-means++ init) and you must choose k (elbow method).",
      ["k-means", "clustering", "unsupervised", "from-scratch"],
      code="import numpy as np\ndef kmeans(X, k, iters=100):\n    centroids = X[np.random.choice(len(X), k, replace=False)]\n    for _ in range(iters):\n        d = ((X[:,None,:] - centroids[None,:,:])**2).sum(2)\n        labels = d.argmin(1)                     # assign\n        new = np.array([X[labels==j].mean(0) for j in range(k)])\n        if np.allclose(new, centroids): break    # converged\n        centroids = new\n    return labels, centroids",
      complexity="Time O(iters * n * k * d).",
      pitfalls="Bad init -> poor clusters (use k-means++); empty clusters; assumes spherical clusters.",
      followups="How to choose k? Elbow method (plot inertia vs k) or silhouette score."),

    # ─────────── ML System Design ───────────
    Q("ml_system_design", "The ML system design framework (6 steps)",
      "New-grad ML design is lighter but shows maturity. Use one spine for any prompt ('design recommendations / feed ranking / spam detection'): (1) CLARIFY & scope — the goal, the BUSINESS metric (engagement? revenue?), scale, latency, online vs batch. (2) FRAME as ML — what's the label and task (classification/ranking/regression/retrieval)? (3) DATA & features — sources, labels (implicit clicks vs explicit), features, and leakage traps. (4) MODEL — start simple (logistic regression / gradient-boosted trees baseline) then go deep; justify. (5) SERVING — the two-stage funnel: candidate generation (fast, high recall) -> ranking (heavier, high precision) -> re-rank (business rules/diversity). (6) EVALUATION — offline metrics (AUC, NDCG) AND online A/B tests on the business metric; monitor drift.",
      ["ml-system-design", "framework", "recommendation", "ranking"],
      followups="Why two stages? Millions of items are too many to score with a heavy model, so cheaply retrieve hundreds, then rank precisely."),
    Q("ml_system_design", "Design a recommendation system (worked example)",
      "Pick the metric first: long-term WATCH-TIME/engagement (not just clicks, to avoid clickbait). Two-stage funnel: (a) CANDIDATE GENERATION — a two-tower model (a user tower and an item tower) produces embeddings; retrieve the nearest few hundred items via ANN over millions — fast, recall-oriented. (b) RANKING — a deeper model scores those candidates on rich features (watch history, freshness, context) to predict engagement — precision-oriented. (c) RE-RANK for diversity, freshness, and business rules. Train offline, serve online, and evaluate with an A/B test; watch for feedback loops (popularity bias) and data drift.",
      ["recommendation", "two-tower", "ann", "ranking", "ml-system-design"],
      pitfalls="Optimizing clicks -> clickbait; cold start for new users/items; feedback loops amplifying popular items.",
      followups="Cold start? Use content features / popularity for new users; explore-exploit. Evaluate offline? NDCG, recall@k, then confirm with an online A/B test."),

    # ─────────── CS Fundamentals ───────────
    Q("cs_fundamentals", "Process vs Thread (and why it matters)",
      "A PROCESS is an independent running program with its OWN memory space; a THREAD is a lightweight unit of execution WITHIN a process that SHARES the process's memory. Threads are cheaper to create and switch between and can communicate via shared memory, but that sharing needs synchronization (locks) to avoid race conditions. Processes are isolated (a crash in one doesn't kill another) but heavier and communicate via IPC. Rule: use threads for shared-memory concurrency within an app; processes for isolation.",
      ["process", "thread", "concurrency", "os"],
      followups="What's a deadlock? Four conditions (mutual exclusion, hold-and-wait, no preemption, circular wait) — break any one to prevent it."),
    Q("cs_fundamentals", "SQL vs NoSQL — how to choose",
      "SQL databases (Postgres, MySQL) have a fixed SCHEMA, support relations/JOINs, give ACID transactions and strong consistency, and scale vertically — great for structured data and complex queries (orders, payments). NoSQL (key-value, document, wide-column, graph) has a flexible schema, scales horizontally, and often trades strong consistency for availability — great for massive scale, high write throughput, or flexible/denormalized data. Choose by your data shape, scale, query patterns, and consistency needs — many systems use both.",
      ["sql", "nosql", "database", "acid", "cs"],
      followups="What is ACID? Atomicity, Consistency, Isolation, Durability — the guarantees of a reliable transaction. What's an index? A structure (usually B-tree) that speeds reads at the cost of write speed/storage."),

    # ─────────── Behavioral (student) ───────────
    Q("behavioral", "STAR method + a strong student example",
      "Behavioral answers use STAR: Situation (context), Task (your responsibility), Action (spend MOST of your time here, use 'I' not 'we'), Result (quantify!). As a student your stories come from projects, hackathons, internships, research, teaching, clubs — impact matters more than title. Example (Ownership/Deliver Results): 'In my final-year capstone (S), our disease-classification model was stuck at 72% two weeks before the deadline (T). I dove into the errors, found class imbalance and overfitting, applied augmentation + class weights + dropout, and switched to transfer learning with a pretrained ResNet suited to our small dataset (A). Accuracy jumped to 93%, we demoed two days early, and it was graded the top capstone (R).' Note: specific root-cause, personal 'I', real ML depth, quantified result.",
      ["behavioral", "star", "student", "leadership-principles"],
      pitfalls="Saying 'we' instead of 'I'; no numbers; rambling past ~2 minutes; a vague action section.",
      followups="Prepare STAR stories for: a failure, a conflict, learning fast, tight deadline, and 'most proud'. For Amazon, map each to a Leadership Principle."),
    Q("behavioral", "'Why this company / why you?'",
      "Be specific and genuine — generic answers hurt. WHY THE COMPANY: connect their scale/mission/products to what you want to work on (e.g., 'Google's ML infrastructure lets me work on models at planet scale'; 'Amazon's ownership culture fits how I like to drive projects end-to-end'). WHY YOU: 3 concrete strengths tied to the role, each backed by a quick proof point from a project. Do your homework on the team/products so it doesn't sound templated. Close with authentic enthusiasm.",
      ["behavioral", "why-company", "motivation"],
      followups="For Amazon, weave in a Leadership Principle you embody; for Google, emphasize collaboration, humility, and comfort with ambiguity ('Googleyness')."),

    # ─────────── Amazon & Google Process ───────────
    Q("company", "Amazon: Leadership Principles & the Loop",
      "Amazon worships its 16 LEADERSHIP PRINCIPLES — roughly HALF of the loop is behavioral, and every behavioral answer should map to an LP. A trained 'Bar Raiser' in the loop keeps standards high and WILL dig with follow-ups. Prepare 12-15 STAR stories mapped to the heavy hitters: Customer Obsession, Ownership, Dive Deep, Deliver Results, Bias for Action, Invent and Simplify, Learn and Be Curious, Earn Trust. Coding is typically 2 mediums. Flow: Online Assessment -> phone/virtual -> the Loop (3-4 rounds mixing coding + LP behavioral).",
      ["amazon", "leadership-principles", "bar-raiser", "behavioral", "process"],
      followups="What is a Bar Raiser? A trained interviewer from another team whose job is to keep the hiring bar high; expect deep follow-ups."),
    Q("company", "Google: process, Googleyness & the committee",
      "Google weights raw DSA problem-solving and analytical CLARITY more heavily — expect harder algorithmic questions with escalating follow-ups, plus strong focus on communication and 'Googleyness' (humility, collaboration, comfort with ambiguity). Crucially, hiring is COMMITTEE-based: you're not hired by one interviewer — a packet of all your feedback goes to a hiring committee, so CONSISTENCY across every round matters. Then team matching. The process can be slow; keep other options warm.",
      ["google", "googleyness", "hiring-committee", "dsa", "process"],
      followups="What is 'Googleyness'? Comfort with ambiguity, collaboration, humility, and intellectual curiosity — demonstrated through how you communicate and handle hints."),
]

# Fill tags: explicit + category-derived.
for _e in ENTRIES:
    _e["tags"] = sorted(set([t.lower() for t in _e.get("tags", [])] + _CATEGORY_TAGS.get(_e["cat"], [])))

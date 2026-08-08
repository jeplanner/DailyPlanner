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
    dict(cat="ml_system_design", title="Design a Query Autocomplete (typeahead) system",
         answer="Suggest completions as the user types a query prefix. (1) CLARIFY & SCALE: return the top ~10 relevant completions within a few ms per keystroke; enormous query volume, personalized and fresh (trending). (2) DATA & LABELS: historical query logs with frequencies; clicks on suggestions as positive signal; time-decay to favour recent/trending queries. (3) FEATURES: prefix match, query popularity, recency/trending, user context (location, history), language. (4) STRUCTURE/MODEL: a TRIE (prefix tree) where each node caches its top-k completions by score gives O(prefix) lookup; scores blend popularity + personalization + recency; an optional learned ranker re-scores candidates. (5) EVAL: offline Mean Reciprocal Rank of the chosen suggestion and coverage; online suggestion CTR and characters saved. (6) SERVING/MONITORING/AB: in-memory sharded trie updated incrementally, cache hot prefixes, A/B on CTR and query success, and filter unsafe completions.",
         tags=["autocomplete","typeahead","trie","ranking","ml-system-design"],
         example="Typing 'new y', the trie node for that prefix returns its cached top completions ('new york', 'new year', 'new york times') ranked by popularity and your location in a couple milliseconds."),
    dict(cat="ml_system_design", title="Design a Fraud / Payment-Risk Detection system",
         answer="Score transactions/accounts for fraud risk in real time. (1) CLARIFY & SCALE: block fraud while minimizing false declines (they anger good customers); milliseconds per transaction, highly imbalanced, ADVERSARIAL and cost-sensitive (a missed fraud and a false decline have very different costs). (2) DATA & LABELS: confirmed chargebacks/fraud (delayed weeks) and manual review; noisy and imbalanced. (3) FEATURES: transaction (amount, merchant, time), account history & VELOCITY (spend rate, new device/IP, geo-distance from last txn), GRAPH features (cards/devices shared across accounts), windowed aggregates. (4) MODEL: gradient-boosted trees on tabular signals, plus graph/anomaly models for rings and a rules engine for hard blocks; increasingly deep models over transaction sequences. (5) EVAL: precision/recall at an operating threshold, PR-AUC, and DOLLAR-weighted metrics; choose the threshold by FP-vs-FN cost. (6) SERVING/MONITORING/AB: real-time scoring via a feature store, async deeper checks + human review queue, chargebacks retrain it, monitor for new attack patterns, and step-up auth (OTP) for borderline cases.",
         tags=["fraud-detection","payment-risk","imbalance","graph-features","ml-system-design"],
         example="A card swipe 500 miles from the last one, on a new device, for an unusual amount scores high risk; the model declines or triggers a one-time passcode, and a later confirmed chargeback becomes a fresh training label."),
    dict(cat="ml_system_design", title="Design for Recommendation Cold-Start",
         answer="Recommend well for NEW users or NEW items that have little or no interaction history. (1) CLARIFY & SCALE: standard collaborative filtering fails with no history; you still need sensible recs from day one. (2) DATA & LABELS: implicit feedback for warm entities; for cold ones lean on CONTENT/METADATA and onboarding signals. (3) FEATURES: item metadata (category, text, image embeddings), user profile/onboarding answers, demographics, context. (4) STRATEGIES: content-based recs for cold items (match item features to user preferences), popularity/trending fallbacks for cold users, HYBRID models combining content + collaborative signals, and EXPLORATION (multi-armed bandits) to gather feedback fast; ask onboarding preferences. (5) EVAL: measure on the cold segment specifically (new-user / new-item slices), not just overall. (6) SERVING/MONITORING/AB: gradually shift an entity from content-based to collaborative as data accrues; A/B the cold-start strategy on new-cohort retention.",
         tags=["cold-start","recommendation","content-based","bandit","ml-system-design"],
         example="A brand-new streaming user picks 3 favourite genres at signup; until they watch enough, recs come from content similarity + trending in those genres while a bandit explores to learn their taste quickly."),
    dict(cat="ml_system_design", title="Design a large-scale Image Classification pipeline",
         answer="Classify images into categories at scale (e.g. product/photo tagging). (1) CLARIFY & SCALE: N classes, millions-to-billions of images, target accuracy & latency, batch (offline tagging) vs real-time. (2) DATA & LABELS: labeled images (human annotation, weak labels from tags); handle class imbalance and label noise; augmentation (crop, flip, colour jitter). (3) REPRESENTATION: raw pixels into a CNN or Vision Transformer, usually starting from a PRETRAINED backbone (ImageNet) and fine-tuning (transfer learning). (4) MODEL: ResNet/EfficientNet or ViT; for huge label spaces use hierarchical or embedding-based retrieval. (5) TRAINING/EVAL: cross-entropy with label smoothing; top-1/top-5 accuracy and per-class recall for rare classes; validate on a held-out set. (6) SERVING/MONITORING/AB: batch GPU inference for offline, quantized/distilled models for real-time; monitor accuracy drift and emerging categories; a data flywheel sends low-confidence images to human labeling.",
         tags=["image-classification","cnn","transfer-learning","vision","ml-system-design"],
         example="An e-commerce catalog fine-tunes a pretrained EfficientNet on its product categories; low-confidence predictions are routed to human reviewers whose labels feed the next training round."),
    dict(cat="ml_system_design", title="Design a Feature Store",
         answer="A central system to define, compute, store, and serve ML FEATURES consistently for training and inference. (1) CLARIFY & SCALE: eliminate training-serving SKEW (a feature computed identically offline and online) and enable feature reuse across teams; low-latency online reads plus large offline reads. (2) DATA: raw event/log/table sources feed feature pipelines. (3) COMPONENTS: an OFFLINE store (columnar warehouse for training, with point-in-time-correct joins to prevent label leakage) and an ONLINE store (low-latency KV like Redis for serving); a shared feature registry; batch + streaming ingestion. (4) GUARANTEES: identical transformation logic for both stores, point-in-time correctness (only features known at event time), and versioning. (5) OPS/EVAL: monitor feature freshness, null rates, and distribution drift. (6) SERVING: models fetch features by entity key in milliseconds; backfills recompute history. Examples: Feast, Tecton.",
         tags=["feature-store","mlops","training-serving-skew","serving","ml-system-design"],
         example="A fraud model's 'transactions in the last hour' feature is computed once by a streaming job and written to BOTH the offline store (for training) and Redis (for serving), so training and production see the exact same value — killing training-serving skew."),
    dict(cat="ml_system_design", title="Design an A/B Testing (experimentation) platform",
         answer="A platform to run controlled online experiments that measure the causal impact of changes. (1) CLARIFY & SCALE: reliably decide whether a change (new model/feature) improves a metric; thousands of concurrent experiments, millions of users. (2) ASSIGNMENT: randomly and DETERMINISTICALLY bucket users (hash user_id) into control/treatment; keep assignment consistent and use mutually-exclusive layers for conflicting tests. (3) METRICS: a north-star metric plus guardrails; log exposures and outcomes. (4) ANALYSIS: estimate the treatment effect with statistical significance (t-test, CUPED variance reduction), correct for multiple comparisons, and watch novelty effects and sample-ratio mismatch. (5) VALIDITY: enough statistical power (sample size), run across weekly seasonality, check for network interference. (6) SERVING/MONITORING: a config service delivers assignments, a pipeline builds results dashboards, and automatic guardrail alerts stop harmful experiments early.",
         tags=["ab-testing","experimentation","causal-inference","statistics","ml-system-design"],
         example="To test a new ranking model, 5% of users are hashed into treatment; after two weeks the platform reports +1.2% engagement (p<0.01) with no guardrail regressions, so it ships — while a sample-ratio-mismatch check confirms the split was truly random."),
    dict(cat="glossary", title="RLHF (Reinforcement Learning from Human Feedback)",
         answer="The technique that aligns LLMs to human preferences. Three steps: (1) collect human RANKINGS of model outputs, (2) train a REWARD MODEL to predict those preferences, (3) fine-tune the LLM with reinforcement learning (e.g. PPO) to maximize the reward while a KL penalty keeps it close to the original model. It's why modern assistants are helpful and far less toxic than the raw pretrained model.",
         tags=["rlhf","alignment","reward-model","ppo","llm"],
         example="Given two chatbot replies, humans mark which is better; a reward model learns that preference, then PPO nudges the LLM to produce more of the preferred style."),
    dict(cat="glossary", title="Mixture of Experts (MoE)",
         answer="An architecture with many specialized sub-networks ('experts') where a lightweight ROUTER activates only a few per input (sparse activation). Total parameters can grow enormously while compute per token stays roughly constant — giving huge model capacity at a fraction of the inference cost of a dense model of the same size.",
         tags=["mixture-of-experts","moe","sparse","routing","efficiency"],
         example="A MoE layer with 64 experts routes each token to its top-2 experts, so a trillion-parameter model runs only ~2 experts' worth of compute per token."),
    dict(cat="glossary", title="Contrastive learning",
         answer="A self-supervised approach that learns representations by pulling SIMILAR (positive) pairs together and pushing DISSIMILAR (negative) pairs apart in embedding space — no labels required. Positives are often two augmented views of the same item. It powers SimCLR, CLIP (image-text), and modern sentence embeddings.",
         tags=["contrastive-learning","self-supervised","embeddings","representation"],
         example="SimCLR treats two random crops of the same photo as a positive pair and crops of other photos as negatives, learning features that transfer well to downstream tasks with little labeled data."),
    dict(cat="glossary", title="Self-supervised learning",
         answer="Learning useful representations from UNLABELED data by inventing a pretext task whose labels come free from the data itself — e.g. predict a masked word, the next token, or whether two views match. It unlocks the internet's vast unlabeled data; the pretrained model is then fine-tuned on a small labeled set. It's the paradigm behind BERT, GPT, and modern vision models.",
         tags=["self-supervised","pretraining","representation-learning","pretext-task"],
         example="BERT masks 15% of words and trains to predict them from context — no human labels — producing representations that fine-tune to many NLP tasks with little data."),
    dict(cat="glossary", title="Quantization (model)",
         answer="Reducing the numerical PRECISION of a model's weights/activations (e.g. 32-bit floats to 8-bit or 4-bit integers) to shrink memory and speed up inference with minimal accuracy loss. Post-training quantization is quick; quantization-aware training recovers more accuracy. It's essential for running large models on phones/edge and for cutting serving cost.",
         tags=["quantization","efficiency","inference","edge","compression"],
         example="Quantizing a 7B-parameter LLM from FP16 to 4-bit cuts its memory ~4x, letting it run on a single consumer GPU with only a small quality drop."),
    dict(cat="dsa", title="LRU Cache (hash map + doubly linked list)",
         answer="Design a cache with O(1) get and put that evicts the LEAST-RECENTLY-USED key when full. Combine a hash map (key -> node) for O(1) lookup with a doubly linked list ordered by recency: move a node to the front on every access, and evict from the back (the LRU) when over capacity. Sentinel head/tail nodes simplify the pointer surgery.",
         tags=["lru-cache","hash-map","linked-list","design","dsa"],
         code='''# O(1) get/put cache that evicts the least-recently-used key.
class Node:
    def __init__(self, key=0, val=0):
        self.key = key; self.val = val
        self.prev = None; self.next = None

class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.map = {}                    # key -> Node
        self.head = Node()               # sentinel: most-recently-used side
        self.tail = Node()               # sentinel: least-recently-used side
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_front(self, node):          # just after head = most recent
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node); self._add_front(node)   # mark recently used
        return node.val

    def put(self, key, value):
        if key in self.map:
            self._remove(self.map[key])
        node = Node(key, value)
        self.map[key] = node
        self._add_front(node)
        if len(self.map) > self.cap:                 # over capacity -> evict LRU
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]''',
         complexity="Time O(1) per get/put, space O(capacity).",
         pitfalls="Forgetting to move a node to the front on get; not deleting the evicted key from the map.",
         example="cap=2: put(1,1), put(2,2), get(1)->1, put(3,3) evicts key 2, get(2)->-1."),
    dict(cat="dsa", title="Min Stack (O(1) getMin)",
         answer="A stack that supports push, pop, top, and getMin all in O(1). Keep a SECOND stack that tracks the running minimum: on each push, store min(new value, current min) alongside the main stack, so the top of the min-stack is always the minimum of the current contents. Pop both together.",
         tags=["min-stack","stack","design","dsa"],
         code='''# Stack with push/pop/top/getMin all O(1) via a second min-tracking stack.
class MinStack:
    def __init__(self):
        self.stack = []
        self.mins = []          # mins[-1] = minimum of the whole stack

    def push(self, x):
        self.stack.append(x)
        # carry the running minimum forward
        self.mins.append(x if not self.mins else min(x, self.mins[-1]))

    def pop(self):
        self.mins.pop()
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def get_min(self):
        return self.mins[-1]''',
         complexity="Time O(1) per operation, space O(n).",
         pitfalls="Storing only the single global min (breaks after popping it); forgetting to pop the min-stack in lockstep.",
         example="push(-2), push(0), push(-3): get_min()->-3; pop(); get_min()->-2."),
    dict(cat="dsa", title="Implement a Trie (prefix tree)",
         answer="A tree for storing strings by shared prefixes, supporting insert, exact-word search, and prefix search. Each node holds a map of child characters and a boolean marking the end of a complete word. Insert/search walk character by character; starts_with just checks the prefix path exists. Great for autocomplete and dictionary lookups.",
         tags=["trie","prefix-tree","string","design","dsa"],
         code='''# Prefix tree supporting insert, exact search, and prefix search.
class TrieNode:
    def __init__(self):
        self.children = {}      # char -> TrieNode
        self.is_end = False     # True if a word ends here

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True      # mark the end of a full word

    def _find(self, prefix):
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def search(self, word):
        node = self._find(word)
        return node is not None and node.is_end   # must be a complete word

    def starts_with(self, prefix):
        return self._find(prefix) is not None     # any word with this prefix''',
         complexity="Time O(len(word)) per op, space O(total chars inserted).",
         pitfalls="Confusing search (needs is_end) with starts_with (path exists); not handling the empty string.",
         example="insert('apple'): search('apple')->True, search('app')->False, starts_with('app')->True."),
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

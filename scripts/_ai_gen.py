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
    dict(cat="ml_system_design", title="Design a News Feed Ranking system",
         answer="Rank the posts in a user's feed to maximize meaningful long-term engagement. (1) CLARIFY & SCALE: objective is long-term engagement (not just clicks); billions of users, thousands of candidate posts per request, <200ms, fully personalized. (2) DATA & LABELS: implicit-feedback logs — impressions, clicks, likes, comments, shares, dwell time; hides/reports are strong negatives; build (user, post, context) -> engagement labels, and correct for position/exposure bias. (3) FEATURES: user (interests, past engagement, demographics), post/author (topic, age, media type, author affinity), user-author interaction history, context (time, device). (4) MODEL: two stages — a lightweight candidate GENERATOR (two-tower embeddings + approximate-nearest-neighbour retrieval) narrows thousands to hundreds, then a heavier RANKER (gradient-boosted trees or a deep multi-task net) predicts P(like)/P(comment)/P(share) and blends them. (5) TRAINING/EVAL: per-objective AUC and NDCG offline; calibrate probabilities; guard against feedback loops. (6) SERVING/MONITORING/AB: real-time feature store, log everything, A/B on north-star metrics (sessions, retention), monitor drift and integrity so you don't amplify clickbait.",
         tags=["news-feed","ranking","recommendation","two-tower","ml-system-design"],
         example="A feed system fetches ~500 candidates with a two-tower retrieval model, scores each for like/comment/share with a multi-task ranker, blends the scores, then re-ranks for diversity so you don't see five posts from one author."),
    dict(cat="ml_system_design", title="Design a Search Ranking system",
         answer="Rank documents for a text query by relevance. (1) CLARIFY & SCALE: return the most relevant results high on the page; billions of docs, tens-of-ms budget, judged by relevance + engagement. (2) DATA & LABELS: graded human relevance judgments (0-4) plus click logs; clicks are position/presentation biased, so debias or use pairwise preferences. (3) FEATURES: query (length, intent, entities), document (freshness, authority/PageRank, quality), query-document match (BM25, semantic-embedding similarity, exact/phrase match), user/context (location, personalization). (4) MODEL: multi-stage — cheap retrieval (inverted index + BM25, or ANN over embeddings) builds a candidate set, then LEARNING-TO-RANK (LambdaMART / GBTs, or a neural cross-encoder) reorders the top-k. (5) TRAINING/EVAL: a ranking loss; evaluate with NDCG, MRR, MAP offline. (6) SERVING/MONITORING/AB: latency-tiered (fast recall, slower precise re-rank), cache popular queries, A/B on click-through and query success, watch for relevance regressions.",
         tags=["search-ranking","learning-to-rank","information-retrieval","ndcg","ml-system-design"],
         example="For 'best running shoes', ~1000 docs are pulled by BM25+embedding recall, then LambdaMART re-ranks the top 100 by freshness/authority/semantic match; NDCG@10 tracks quality offline while CTR and query-reformulation rate track it online."),
    dict(cat="ml_system_design", title="Design an Ad Click-Through-Rate (CTR) prediction system",
         answer="Predict the probability a user clicks an ad so ads can be ranked by expected value. (1) CLARIFY & SCALE: goal is a well-CALIBRATED P(click) used in bid = P(click) x value; massive scale, <10ms, extreme class imbalance (clicks are rare). (2) DATA & LABELS: impression logs labeled clicked/not; huge, sparse, high-cardinality categoricals; handle delayed feedback and imbalance. (3) FEATURES: user (history, demographics), ad (advertiser, category, creative), context (page, device, time), and crucial CROSS features (user x ad-category). (4) MODEL: logistic regression with feature hashing was classic; now factorization machines / Wide & Deep / DeepFM capture feature interactions with embeddings for high-cardinality IDs. (5) TRAINING/EVAL: log-loss and AUC, but CALIBRATION matters most (predicted CTR must match actual) — check calibration plots; retrain often since data drifts fast. (6) SERVING/MONITORING/AB: streaming/online learning, feature store, monitor calibration drift and revenue; A/B on revenue and long-term experience, and cap ad load.",
         tags=["ad-ctr","calibration","deepfm","wide-and-deep","ml-system-design"],
         example="A DeepFM model embeds advertiser and query-category IDs and outputs 0.03; multiplied by the bid it sets the ad's rank. Nightly calibration checks catch it if predicted 3% but actual is 5% (bids systematically too low)."),
    dict(cat="ml_system_design", title="Design a Video Recommendation system (YouTube-style)",
         answer="Recommend the next videos to maximize long-term satisfaction/watch time. (1) CLARIFY & SCALE: optimize expected WATCH TIME/satisfaction, not raw clicks (avoid clickbait); billions of videos and users, fresh content, cold start. (2) DATA & LABELS: watch logs — impressions, clicks, watch duration, completion, likes, 'not interested'; use watch time as a weighted label. (3) FEATURES: user watch history (a sequence of video embeddings), video (topic, channel, age, length), context (device, time), demographics. (4) MODEL: two stages — a candidate GENERATION network learns user & video embeddings and retrieves hundreds via ANN from millions, then a RANKING network predicts expected watch time per candidate with rich features. (5) TRAINING/EVAL: weighted logistic/regression on watch time; offline held-out AUC and top-k recall; beware feedback loops narrowing interests. (6) SERVING/MONITORING/AB: continuously refreshed nearest-neighbour index, A/B on watch time, retention and diversity, add EXPLORATION for fresh/cold-start content, monitor for filter bubbles.",
         tags=["video-recommendation","watch-time","candidate-generation","exploration","ml-system-design"],
         example="A candidate generator turns your watch history into an embedding and retrieves ~500 videos via ANN, then a ranker orders them by predicted watch time; exploration mixes in a few new videos so recommendations don't stagnate."),
    dict(cat="ml_system_design", title="Design a Spam / Abuse Detection system",
         answer="Classify content/accounts as spam/abuse and act on them. (1) CLARIFY & SCALE: high recall on spam while keeping false positives low (don't punish real users); ADVERSARIAL (attackers adapt), high volume, low latency. (2) DATA & LABELS: user reports, human moderation, known campaigns; labels are noisy and delayed; positive class is rare. (3) FEATURES: content (text/URL/image signals), behavioural (send rate, account age, IP/device reputation, connection graph), velocity/anomaly features. (4) MODEL: gradient-boosted trees or neural nets, combined with RULES for known patterns and GRAPH features to catch coordinated rings; anomaly detection for novel attacks. (5) TRAINING/EVAL: precision/recall at chosen thresholds, PR-AUC (imbalance), cost-sensitive (false-positive vs false-negative costs differ); retrain often as adversaries evolve. (6) SERVING/MONITORING/AB: real-time scoring plus async deeper checks, human-in-the-loop for borderline, appeals feed back as labels, monitor evasion/drift; tiered enforcement (rate-limit -> challenge -> ban).",
         tags=["spam-detection","abuse","adversarial","imbalance","ml-system-design"],
         example="An email provider scores each message: a GBT plus reputation and velocity features flags a burst of identical links from a young account — high-confidence spam is quarantined, borderline gets a CAPTCHA, and 'report spam' clicks become fresh labels."),
    dict(cat="ml_system_design", title="Design a Near-Duplicate Detection system",
         answer="Detect items (documents, images, listings) that are near — not exact — duplicates at scale. (1) CLARIFY & SCALE: find 'almost the same' pairs among billions cheaply; used for dedup, plagiarism, spam clustering. (2) DATA & LABELS: pairs labeled duplicate/not (human review or known reposts); define the similarity threshold. (3) REPRESENTATION: shingles/n-grams for text, perceptual hashes for images, or learned embeddings — the goal is a compact fingerprint. (4) METHOD: Locality-Sensitive Hashing — MinHash for Jaccard set similarity, or SimHash for cosine — buckets similar items so you only compare candidates in the same bucket instead of all N^2 pairs; embeddings + ANN is the modern variant. (5) EVAL: precision/recall of duplicate pairs at the threshold; tune the number of hash bands vs buckets for the recall/precision trade-off. (6) SERVING/MONITORING/AB: index fingerprints, query new items against buckets in near-real-time, monitor false merges, allow human override.",
         tags=["near-duplicate","lsh","minhash","simhash","ml-system-design"],
         example="To dedup near-identical news articles, each article's MinHash signature is banded into buckets; only articles sharing a bucket are compared — turning an impossible N^2 comparison into near-linear work — and pairs above 0.8 Jaccard are merged."),
    dict(cat="glossary", title="Out-of-distribution (OOD)",
         answer="Data at inference time that differs from the training distribution — new classes, shifted feature ranges, or a different domain. Models are unreliable and often OVERCONFIDENT on OOD inputs, so detecting them (via confidence, density estimates, or dedicated OOD detectors) matters for safety. It's a systematic mismatch, distinct from random noise.",
         tags=["out-of-distribution","ood","robustness","safety"],
         example="A model trained only on daytime photos sees a night image at inference — that's OOD, and it may confidently give a wrong label unless an OOD detector flags it for a human."),
    dict(cat="glossary", title="Learning-rate warmup",
         answer="Starting training with a SMALL learning rate and ramping it up over the first few hundred/thousand steps before the normal schedule begins. Early on the weights are random and gradients noisy, so a large LR can destabilize training (especially for Transformers and large-batch runs); warmup lets the statistics settle first, then full-speed learning proceeds.",
         tags=["learning-rate-warmup","optimization","training","transformer"],
         example="Training a Transformer, the LR climbs linearly from 0 to its peak over the first 4000 steps then decays — skipping warmup often makes the loss diverge early."),
    dict(cat="glossary", title="Exploding gradient",
         answer="When gradients grow exponentially large during backpropagation (common in deep or recurrent nets), causing huge weight updates, NaNs, and divergence — the opposite of vanishing gradients. Fixes: GRADIENT CLIPPING (cap the norm), careful initialization, normalization layers, and smaller learning rates.",
         tags=["exploding-gradient","backpropagation","gradient-clipping","rnn"],
         example="An RNN on long sequences sees its loss suddenly jump to NaN; clipping the gradient norm to 1.0 stabilizes training."),
    dict(cat="glossary", title="Gradient accumulation",
         answer="A trick to simulate a LARGE batch size that won't fit in memory: run several small mini-batches, SUM (accumulate) their gradients, and only update the weights after N of them — as if you'd used a batch N times larger. It trades extra compute time for reduced memory.",
         tags=["gradient-accumulation","training","memory","large-batch"],
         example="You want an effective batch of 256 but only 32 fits on the GPU; accumulate gradients over 8 mini-batches of 32, then step once — mathematically like a batch of 256."),
    dict(cat="glossary", title="Mixed-precision training",
         answer="Training with a mix of 16-bit and 32-bit floating point: most operations run in fast, memory-light FP16/bfloat16 while a 32-bit master copy of the weights and a 'loss scale' preserve numerical stability. It roughly doubles throughput and halves memory on modern GPUs with little accuracy loss.",
         tags=["mixed-precision","fp16","training","gpu","efficiency"],
         example="Training a large model in FP16 on a GPU with tensor cores nearly doubles speed and fits a bigger batch, while loss scaling stops tiny gradients from underflowing to zero."),
    dict(cat="conceptual", title="Why can a model score great offline but fail once deployed online?",
         answer="Offline metrics measure the past under assumptions that break in production: (a) TRAINING-SERVING SKEW — features are computed differently offline vs online; (b) FEEDBACK LOOPS — the model changes user behaviour and thus future data (a recommender that only shows popular items makes them more popular); (c) DISTRIBUTION SHIFT — the world moves on from your frozen test set; (d) PROXY-METRIC MISMATCH — you optimized AUC but the business cares about retention; (e) position/selection BIAS baked into logged data. That's why online A/B tests on the true north-star metric, not offline scores alone, decide launches.",
         tags=["offline-online-gap","ab-testing","feedback-loop","distribution-shift","why"],
         example="A feed ranker with higher offline click-AUC ships and click-through rises, but time-spent and 7-day retention fall — it learned to surface clickbait, and only the A/B test on retention caught it."),
    dict(cat="conceptual", title="Why do we need a separate validation set AND a test set?",
         answer="You use the VALIDATION set repeatedly to tune hyperparameters and choose models, so information from it slowly LEAKS into your decisions — you implicitly overfit to it. The TEST set is touched only once, at the very end, to get an HONEST estimate of generalization on data that influenced no choice. Reusing the test set for tuning inflates your reported score. Train = learn weights; validation = tune/choose; test = final unbiased report.",
         tags=["validation-set","test-set","overfitting","generalization","why"],
         example="You try 50 hyperparameter settings and pick the best on validation (0.92); the untouched test set reads 0.88 — that 0.04 gap is the optimism you'd have wrongly reported if you'd tuned on the test set."),
    dict(cat="dsa", title="Merge Intervals",
         answer="Merge all overlapping intervals into a minimal set of non-overlapping ones. Sort by start time, then sweep left to right: if the next interval starts at or before the end of the last merged one, they overlap — extend the last one's end; otherwise it's disjoint, so start a new interval. Sorting dominates the cost.",
         tags=["merge-intervals","sorting","intervals","greedy","dsa"],
         code='''# Merge all overlapping intervals into non-overlapping ones.
def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])   # sort by start time
    merged = [intervals[0][:]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:        # overlaps the last merged interval
            merged[-1][1] = max(merged[-1][1], end)  # extend its end
        else:
            merged.append([start, end])   # disjoint -> start a new interval
    return merged''',
         complexity="Time O(n log n) for the sort, space O(n) for the output.",
         pitfalls="Forgetting to sort first; using max() (not just end) when extending — a nested interval must not shrink the end.",
         example="merge_intervals([[1,3],[2,6],[8,10],[15,18]]) -> [[1,6],[8,10],[15,18]]."),
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

"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it -- no heredocs, pipes, or && chains.
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
    dict(cat="ai_applied", title="Data drift and model monitoring in production",
         answer="In plain words: a model trained on last year's data slowly gets worse as the real world changes - drift monitoring catches that BEFORE users feel it. Two kinds. DATA (covariate) DRIFT: the input distribution shifts (new user behavior, a new product, seasonality) even if the relationship stays the same. CONCEPT DRIFT: the relationship between inputs and the label changes (what counted as fraud last year looks different now). You detect drift by comparing recent production data to the training/reference distribution - statistical tests (PSI, KL divergence, KS test) per feature, monitoring prediction distributions, and watching live metrics (accuracy where labels arrive, plus proxies like confidence, click-through, complaint rate). Responses: alert, investigate, and RETRAIN on fresh data (often on a schedule or triggered by drift). Because labels are often delayed (you learn the truth later), you rely on input-drift and proxy signals for early warning. Monitoring is what turns 'the model quietly rotted' into 'we caught it and retrained.'",
         tags=["data-drift", "concept-drift", "monitoring", "mlops", "retraining", "ai"],
         example="A demand-forecasting model degrades after a viral trend shifts buying patterns; a PSI alert on the 'category' feature fires days before accuracy would have visibly dropped, triggering a retrain on recent data - so the business never eats a week of bad forecasts.",
         difficulty="Medium",
         frequency="Very commonly asked in ML-engineer / applied-ML interviews - 'how do you know when a deployed model is going stale?'",
         mnemonic="Models rot as the world shifts: DATA drift (inputs change) vs CONCEPT drift (input->label rule changes). Detect with PSI/KL/KS per feature + proxy metrics (labels lag). Respond = alert + retrain. 'Watch the inputs, not just accuracy.'"),
    dict(cat="ai_applied", title="Feature stores (online vs offline features)",
         answer="In plain words: ML models need the same features at TRAINING time (in bulk, historical) and at SERVING time (one user, right now, in milliseconds) - a feature store computes and serves features consistently so training and production don't silently disagree. It has two sides. OFFLINE store: large historical feature tables (in a warehouse) for training and batch scoring - throughput matters. ONLINE store: a low-latency key-value store (Redis/DynamoDB) holding the latest feature values for real-time lookup during inference - latency matters. The whole point is to avoid TRAINING-SERVING SKEW: if 'average order value last 30 days' is computed one way in the training pipeline and another way at serving, the model sees inconsistent inputs and quietly underperforms. A feature store defines each feature ONCE, materializes it to both stores, and guarantees point-in-time correctness (no future leakage in training). It also enables feature REUSE across teams/models. Examples: Feast, Tecton.",
         tags=["feature-store", "online-features", "offline-features", "training-serving-skew", "mlops", "ai"],
         example="A fraud model uses 'transactions in last hour'. The feature store computes it once: the offline table backfills it point-in-time for training, and the online store keeps the live value so serving reads it in <10ms - the SAME definition both places, so no training-serving skew.",
         difficulty="Medium",
         frequency="Commonly asked in ML-infra/MLE interviews - 'how do you serve features in real time and keep training/serving consistent?'",
         mnemonic="One feature definition, two stores: OFFLINE (bulk history for training) + ONLINE (fast KV for serving). The point: kill TRAINING-SERVING SKEW + enable reuse. 'Define once, serve everywhere, no skew.'"),
    dict(cat="ai_applied", title="A/B testing an ML / LLM feature",
         answer="In plain words: to know a new model actually HELPS (not just looks better offline), you ship it to a random slice of users and compare against the old one on real business metrics. Randomly split users into CONTROL (old model) and TREATMENT (new model); pick a primary METRIC tied to the goal (conversion, watch time, resolution rate, revenue) plus GUARDRAIL metrics (latency, cost, error/complaint rate) that must not regress. Run long enough for STATISTICAL SIGNIFICANCE (power analysis for sample size), watch for novelty effects, and avoid peeking/p-hacking. For LLM features specifically: offline evals catch regressions cheaply first, then A/B validates real impact; you may need human eval or LLM-judge for quality since there's no single label. Ramp gradually (1% -> 10% -> 50%) with a canary and automatic rollback on guardrail breaches. The discipline: a model that wins offline can still lose online, so the online experiment is the source of truth.",
         tags=["ab-testing", "experimentation", "evaluation", "mlops", "applied", "ai"],
         example="A new recommendation model has higher offline nDCG, so it goes to a 5% A/B test; watch time is up 2% (significant) but p99 latency is up 40ms (within the guardrail), so it ramps to 100% - whereas an earlier candidate won offline but lost on watch time online and was killed.",
         difficulty="Medium",
         frequency="Very commonly asked - 'how do you know your model change is actually better?' A/B testing is the expected answer at product companies.",
         mnemonic="Offline eval says 'maybe'; the A/B test says 'yes/no'. Random control vs treatment, a primary metric + GUARDRAILS (latency/cost), enough samples for significance, ramp with canary + auto-rollback. 'Online is the source of truth.'"),
    dict(cat="ai_llm", title="GraphRAG (retrieval over a knowledge graph)",
         answer="In plain words: normal RAG retrieves independent text chunks, which struggles with questions that need CONNECTING facts across many documents ('how are X and Y related?', 'summarize themes across the whole corpus'). GraphRAG first builds a KNOWLEDGE GRAPH from your documents - an LLM extracts entities (people, orgs, concepts) and their relationships as nodes and edges - then answers by traversing and summarizing that graph. For broad 'sensemaking' questions it also pre-computes COMMUNITY summaries (clusters of related entities) so it can answer global questions no single chunk contains. Benefits: multi-hop reasoning, global/thematic questions, and explainable paths (you can see the connecting entities). Costs: the graph-building step is an expensive LLM pass over the corpus, and it's overkill for simple lookup questions. Use plain RAG for 'find the fact', GraphRAG when answers require relationships across many sources.",
         tags=["graphrag", "knowledge-graph", "rag", "multi-hop", "retrieval", "ai"],
         example="'What themes connect our top 3 customers' complaints?' Plain RAG returns a few unrelated tickets; GraphRAG extracted entities/relationships and community summaries across ALL tickets, so it can answer the cross-cutting, thematic question that no single chunk contains.",
         difficulty="Hard",
         frequency="Emerging topic in advanced RAG interviews - 'how would you handle multi-hop or corpus-wide questions RAG fails on?'",
         mnemonic="Build a knowledge GRAPH (entities + relationships) from the docs, then traverse/summarize it - great for multi-hop and 'themes across everything' questions plain chunk-RAG can't do. Pricey to build. 'Connect the dots, don't just fetch chunks.'"),
    dict(cat="ai_applied", title="Shadow deployment and canary for ML models",
         answer="In plain words: two safe ways to roll out a new model without risking users. SHADOW (dark launch): the new model runs on REAL traffic in parallel with the current one, but its predictions are LOGGED, not shown to users - so you compare its behavior/latency against production on live data with zero user risk. CANARY: the new model actually SERVES a small slice of traffic (say 1-5%), you watch its live metrics vs the rest, and ramp up if healthy or roll back if not. Use shadow to validate correctness/latency and catch training-serving skew before anyone sees the output; use canary to measure real user impact gradually. They complement A/B testing (which is about measuring which is BETTER) - shadow/canary are about safe ROLLOUT. Pair with automatic rollback on guardrail breaches and good monitoring.",
         tags=["shadow-deployment", "canary", "rollout", "mlops", "applied", "ai"],
         example="Before launching a new pricing model, it runs in SHADOW for a week - scoring live requests, predictions logged - revealing it mishandles a rare input (a skew bug) with zero customer impact. After the fix, a 2% CANARY confirms real metrics hold, then it ramps to 100%.",
         difficulty="Medium",
         frequency="Commonly asked in MLOps/deployment interviews - 'how do you safely roll out a new model?'",
         mnemonic="SHADOW = run new model on live traffic but LOG only (no user sees it) - catch bugs/skew safely. CANARY = serve a small % for real, ramp if healthy. Shadow/canary = safe ROLLOUT; A/B = which is better. 'Test in the dark, then trickle it out.'"),
    dict(cat="ai_applied", title="Human evaluation and inter-annotator agreement",
         answer="In plain words: for subjective AI tasks (is this answer good? is this content harmful?) there's no automatic ground truth, so you have HUMANS label/rate - but humans disagree, so you must measure how much they agree to trust the labels. Design: write clear GUIDELINES with examples/edge cases, have MULTIPLE annotators rate each item, and measure INTER-ANNOTATOR AGREEMENT with a metric that corrects for chance - Cohen's kappa (two raters) or Fleiss' kappa (many), or Krippendorff's alpha. Low agreement means your task/guidelines are ambiguous (fix the rubric or the task), not just 'noisy humans'. Aggregate labels by majority vote or a model that weights annotators by reliability. Use humans for the gold set that calibrates cheaper automatic metrics (LLM-as-judge), spot-checks, and final quality gates - not for scoring every request (too slow/costly). Watch annotator fatigue and bias, especially for distressing content.",
         tags=["human-evaluation", "inter-annotator-agreement", "kappa", "annotation", "evaluation", "ai"],
         example="Rating chatbot answers 1-5: three annotators score 500 answers; Fleiss' kappa is 0.4 (only fair agreement), revealing the rubric is vague on 'partially correct' - after clarifying the guideline with examples, kappa rises to 0.75 and the labels become a trustworthy gold set for tuning an LLM-judge.",
         difficulty="Medium",
         frequency="Asked in eval-focused / applied-scientist interviews - 'how do you evaluate subjective quality reliably?'",
         mnemonic="Humans label subjective tasks, but they disagree - measure agreement with kappa/alpha (chance-corrected). Low agreement = fix the GUIDELINES, not the humans. Use humans for the gold set that calibrates cheap auto-metrics. 'Clear rubric, multiple raters, measure agreement.'"),
    dict(cat="ai_llm", title="Reranker cross-encoders (precision after retrieval)",
         answer="In plain words: retrieval uses fast BI-ENCODERS (embed query and docs separately, compare vectors) - great for scanning millions quickly, but they never let the query and document 'read each other', so ranking is coarse. A cross-encoder RERANKER fixes the top results by reading the query and each candidate TOGETHER for a precise relevance score. The two-stage pattern: (1) retrieve ~50-100 candidates cheaply with the bi-encoder (recall), then (2) run a cross-encoder on just those pairs to reorder them by true relevance (precision). The cross-encoder is far more accurate because self-attention sees query and document jointly, catching nuances the separate embeddings miss - but it's too slow to run over the whole corpus, so you only apply it to the shortlist. This 'retrieve broad, rerank precise' step is one of the highest-ROI upgrades to a RAG or search system. Models: Cohere Rerank, bge-reranker, cross-encoder MS-MARCO.",
         tags=["reranker", "cross-encoder", "bi-encoder", "retrieval", "rag", "ai"],
         example="Query 'how to cancel auto-renewal'; the bi-encoder returns 50 candidates including 'how to enable auto-renewal' (embeds similarly). The cross-encoder reads query+doc together, understands cancel vs enable, and drops the wrong one to the bottom - so the right doc lands at rank 1.",
         difficulty="Medium",
         frequency="Commonly asked in search/RAG-quality interviews - 'bi-encoder vs cross-encoder, and where does each go?'",
         mnemonic="Bi-encoder = fast, separate embeddings (scan millions, coarse). Cross-encoder = reads query+doc TOGETHER (slow, precise). Retrieve broad with bi-encoder, then RERANK the top-k with the cross-encoder. Big cheap win. 'Scan fast, judge close.'"),
    dict(cat="ai_applied", title="Design a translation / localization pipeline",
         answer="In plain words: translate content (UI strings, docs, support) into many languages accurately, keeping meaning, tone, and formatting - harder than 'call a translate API' because context and consistency matter. Core: an LLM or NMT model does the translation, but the design is about QUALITY and SCALE. Give CONTEXT (surrounding text, a glossary of brand/product terms, a style guide) so terms translate consistently and correctly - 'Apple' the company vs the fruit. Preserve PLACEHOLDERS/markup ({name}, HTML) so you don't break the string. Use TRANSLATION MEMORY (reuse past approved translations) for consistency and cost. Handle plurals/gender/right-to-left and locale formatting (dates, currency, numbers). QUALITY: automatic metrics (BLEU/COMET) plus human review for high-visibility strings, and a feedback loop. For scale: cache/batch, and prioritize human review for user-facing/legal content while auto-publishing low-risk text. Grounding (glossary + context) and consistency (translation memory) are the differentiators.",
         tags=["translation", "localization", "nmt", "glossary", "applied", "ai", "system-design"],
         example="Localizing an app to Japanese: the pipeline passes each string WITH its UI context and a glossary ('Cart' -> a fixed approved term), preserves the {count} placeholder, reuses translation memory for repeated strings, auto-publishes minor labels, and routes the checkout/legal strings to a human reviewer.",
         difficulty="Medium",
         frequency="Commonly asked at global product companies - tests context/glossary grounding, placeholder handling, and quality/human-review design.",
         mnemonic="Not just 'call translate': give CONTEXT + a GLOSSARY (consistent terms), preserve placeholders/markup, reuse translation MEMORY, handle plurals/RTL/locale, eval with BLEU/COMET + human review for key strings. 'Context, glossary, memory, review.'"),
    dict(cat="ai_applied", title="Named-entity recognition and extraction at scale",
         answer="In plain words: pull structured entities out of text - names, companies, dates, amounts, product IDs, medical terms - so unstructured documents become queryable data. Approaches, cheapest to richest: (1) RULES/regex + gazetteers (lists) for well-formatted entities (emails, dates, IDs) - fast and precise where patterns hold. (2) A fine-tuned NER MODEL (transformer token-classifier like spaCy/BERT-NER) for names/orgs/locations - fast at scale once trained. (3) LLM zero/few-shot extraction for nuanced or novel entity types with no training data (costlier per doc). Design: often COMBINE them (rules for the easy stuff, model/LLM for the hard stuff), then NORMALIZE and LINK entities to canonical IDs (entity resolution - 'IBM' and 'International Business Machines' are the same). Handle overlapping/nested entities, domain jargon, and confidence-based human review. Metrics: entity-level precision/recall/F1. At scale, use the LLM to bootstrap labels, then a fast model for volume.",
         tags=["ner", "entity-extraction", "entity-linking", "information-extraction", "applied", "ai"],
         example="Processing millions of news articles: regex grabs dates/tickers, a fine-tuned NER model tags people/orgs/locations at high throughput, and entity linking maps 'Meta', 'Facebook', 'FB' to one canonical company ID - turning raw text into a searchable entity database.",
         difficulty="Medium",
         frequency="Commonly asked applied-NLP design - covers the rules-vs-model-vs-LLM tradeoff plus entity linking/normalization.",
         mnemonic="Extract entities: rules/regex (easy patterns) + fine-tuned NER model (scale) + LLM (novel/nuanced). Then NORMALIZE + LINK to canonical IDs (IBM = International Business Machines). Confidence -> human. 'Tag, normalize, link.'"),
    dict(cat="ai_applied", title="Design a churn prediction system",
         answer="In plain words: predict which customers are about to leave so the business can intervene (a discount, outreach) before they go. It's a binary classification with strong business framing. LABEL: define churn precisely (canceled, or no activity for N days) - the definition drives everything. FEATURES: usage trends (declining logins/engagement), tenure, support tickets/complaints, billing events, and especially CHANGES over time (a drop is a stronger signal than a level). MODEL: gradient-boosted trees are a strong tabular baseline; output a probability. The point isn't just accuracy - it's ACTIONABILITY: rank customers by churn risk, and target interventions where expected value (save probability x customer value x uplift) is highest, not just highest risk. Beware: label leakage (a feature that only exists because they already churned), class imbalance (churn is rare - use PR-AUC/recall), and that predicting churn is useless without a retention ACTION. Measure the intervention's lift with an A/B holdout, not just model AUC.",
         tags=["churn-prediction", "classification", "gradient-boosting", "business", "applied", "ai"],
         example="A SaaS flags accounts whose weekly active users dropped 40% and support tickets spiked as high churn-risk; the success team offers those with high account value a check-in call, and an A/B holdout shows the outreach cuts churn in that segment by 15% - the model's value is the retained revenue, not its AUC.",
         difficulty="Medium",
         frequency="Very commonly asked applied-ML case - tests business framing, feature engineering, imbalance, leakage, and measuring real impact.",
         mnemonic="Predict who'll leave -> intervene first. Define churn precisely; features = usage TRENDS/changes; GBTs output risk; target by expected VALUE not just risk; beware leakage + imbalance; prove it with an A/B holdout. 'Rank by savable value, then act.'"),
    dict(cat="ai_llm", title="Embedding model fine-tuning for your domain",
         answer="In plain words: off-the-shelf embedding models are trained on general text, so they can miss what 'similar' means in YOUR domain (legal, medical, your product's jargon) - fine-tuning them on your data makes retrieval much sharper. You train with CONTRASTIVE learning on pairs: positives that SHOULD be close (a question and its correct answer/passage, or two paraphrases) and negatives that should be far (especially HARD negatives - similar-looking wrong passages). The loss pulls positives together and pushes negatives apart in the vector space, so the model learns your domain's notion of relevance. Data can come from real query-click logs, human-labeled pairs, or LLM-generated pairs (synthetic). Even a light fine-tune on a few thousand good pairs often lifts retrieval recall noticeably over a generic model. Trade-offs: you now maintain/version the embedding model and must RE-EMBED your whole corpus when it changes. Alternatives if you can't fine-tune: better chunking, hybrid search, and a reranker.",
         tags=["embedding-fine-tuning", "contrastive-learning", "retrieval", "domain-adaptation", "ai"],
         example="A legal search tool: a generic embedder treats 'consideration' (contract term) like everyday 'consideration'. Fine-tuning on (legal query, correct clause) pairs with hard negatives teaches the domain meaning, lifting retrieval recall@10 from 0.7 to 0.85 - but the whole corpus must be re-embedded with the new model.",
         difficulty="Hard",
         frequency="Asked in retrieval/applied-scientist interviews - 'retrieval isn't good enough on our domain; would you fine-tune the embeddings?'",
         mnemonic="Generic embeddings miss domain 'similarity' - fine-tune with CONTRASTIVE pairs (positives together, HARD negatives apart) on your data. Big recall lift, but you must RE-EMBED the corpus. No fine-tune? use hybrid + reranker. 'Teach the model YOUR notion of similar.'"),
    dict(cat="ai_applied", title="Design a sentiment analysis system at scale",
         answer="In plain words: classify text (reviews, tweets, support chats) as positive/negative/neutral (or finer emotions) across huge volume, reliably and cheaply. Approaches: (1) a fine-tuned transformer classifier (or even a strong linear model on embeddings) for high-throughput, low-cost scoring once you have labels; (2) LLM zero/few-shot for nuance or when labels are scarce, but pricier per item. Design points that separate a good answer: ASPECT-based sentiment (a review can be positive about battery but negative about price - overall sentiment hides this), SARCASM/negation ('yeah, great, it broke again') which fools naive models, DOMAIN adaptation (movie vs finance sentiment differ), MULTILINGUAL handling, and calibrated confidence with human review for edge cases. Serve with batching for throughput; monitor drift as language/slang evolves. Common production pattern: LLM to bootstrap labels + a fast fine-tuned model for volume, with aspect extraction for actionable insight rather than a single score.",
         tags=["sentiment-analysis", "classification", "aspect-based", "nlp", "applied", "ai"],
         example="Analyzing 1M product reviews: a fine-tuned classifier scores each cheaply, and ASPECT extraction reveals sentiment is +for 'quality' but -for 'shipping' - far more actionable than an overall 3.5 stars; sarcastic reviews are caught by a model trained with negation examples.",
         difficulty="Medium",
         frequency="Commonly asked applied-NLP design - tests the classifier-vs-LLM tradeoff plus real nuances (aspect, sarcasm, domain).",
         mnemonic="Fine-tuned classifier (cheap scale) or LLM (nuance/no labels). The depth: ASPECT-based (per-topic, not one score), handle SARCASM/negation, domain + multilingual, confidence->human. 'Score fast, but per-aspect and sarcasm-aware.'"),
]


def qsrc(e):
    s = f"    Q({e['cat']!r}, {e['title']!r},\n      {e['answer']!r},\n      {e['tags']!r}"
    for f in ("code", "example", "complexity", "pitfalls", "followups",
              "difficulty", "frequency", "mnemonic", "diagram"):
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

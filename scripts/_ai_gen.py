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
    dict(cat="ai_llm", title="GPU memory math for serving LLMs",
         answer="In plain words: to know if a model fits on a GPU (and how many users you can serve), you add up three things: the WEIGHTS, the KV-cache, and some overhead. Quick math: WEIGHTS memory ~= (number of parameters) x (bytes per parameter). Bytes per param: FP16 = 2, INT8 = 1, INT4 = 0.5. So a 7B model in FP16 ~= 7e9 x 2 = ~14 GB; in 4-bit ~= ~3.5 GB. KV-CACHE per token ~= 2 (key+value) x (layers) x (hidden size) x (bytes) x (KV heads / heads for GQA), and it scales with sequence length x batch size - for long contexts and many users this can rival or exceed the weights. Add ~10-20% overhead for activations/fragmentation. This back-of-envelope tells you whether to quantize, how big a batch/context you can serve, and why GQA + paged KV-cache matter. Interviewers love a candidate who can estimate 'does a 13B model fit on a 24 GB GPU?' (FP16 ~26 GB no; 4-bit ~6.5 GB plus cache yes).",
         tags=["gpu-memory", "serving", "quantization", "kv-cache", "llm", "ai"],
         example="Will a 13B model serve on one 24 GB GPU? FP16 weights ~= 26 GB -> does NOT fit. Quantize to 4-bit -> ~6.5 GB weights, leaving ~17 GB for KV-cache + overhead -> fits, and you can serve a decent batch/context. That is the estimate an interviewer wants.",
         difficulty="Medium",
         frequency="Commonly asked in ML-infra/serving interviews (esp. NVIDIA) - 'will this model fit, and how many concurrent users can you serve?'",
         mnemonic="Weights = params x bytes/param (FP16=2, INT8=1, INT4=0.5). Add KV-cache (grows with length x batch) + ~15% overhead. 7B FP16 ~14GB; 4-bit ~3.5GB. 'Params times bytes, plus the cache.'"),
    dict(cat="ai_applied", title="Tool-calling errors and retries in agents",
         answer="In plain words: when an agent calls tools (APIs, code, databases), those calls FAIL - timeouts, bad arguments, rate limits, empty results - and a robust agent must handle failures instead of crashing or hallucinating a result. Design for it: (1) VALIDATE arguments before calling (schema/types) to catch the model's mistakes. (2) On failure, feed the ERROR MESSAGE back to the model so it can self-correct (fix the argument, pick another tool) - but CAP the retries to avoid infinite loops. (3) Use timeouts and RETRY-WITH-BACKOFF+JITTER for transient errors (network, rate limits), but do NOT blindly retry non-idempotent actions (a duplicate payment) - use idempotency keys. (4) Distinguish RETRYABLE (transient) from TERMINAL (bad request, permission) errors. (5) Have a FALLBACK: if a tool keeps failing, degrade gracefully or hand to a human, and never let the model invent the tool's output. (6) LOG every call/result for debugging. It's classic distributed-systems reliability applied to the agent's tool loop.",
         tags=["tool-use", "agents", "reliability", "retries", "error-handling", "applied", "ai"],
         example="An agent calls get_weather('Paaris') (typo); the API returns 'city not found'. The agent gets that error back, corrects to 'Paris', and succeeds - but capped at 3 tries. A flaky 500 error triggers retry-with-backoff; a duplicate 'charge_card' is guarded by an idempotency key so a retry can't double-charge.",
         difficulty="Medium",
         frequency="Increasingly asked in agent/production-LLM design - 'what happens when a tool call fails?' separates toy demos from real systems.",
         mnemonic="Tools fail, so: validate args, feed errors BACK for self-correction (capped retries), backoff+jitter for transient errors, idempotency keys for actions, fallback to human, log everything. 'Reliability engineering for the tool loop.'"),
    dict(cat="ai_applied", title="LLM observability and tracing",
         answer="In plain words: LLM apps are hard to debug because the model is non-deterministic and pipelines have many steps (retrieval, prompt build, model call, tool calls, parsing) - observability means capturing WHAT happened at each step so you can find and fix problems. Capture per request: the full PROMPT sent (after templating/RAG), the model OUTPUT, which chunks were retrieved and their scores, tool calls and results, token counts, latency per step, cost, and the model/version used. A TRACE ties all steps of one request together (like distributed tracing for microservices), so you can see a bad answer came from bad retrieval, not the model. Add: online METRICS (latency, cost, error/refusal rate), quality signals (user thumbs-up/down, LLM-judge scores), and alerts on drift. Tools: LangSmith, Langfuse, Arize, OpenTelemetry-based. This is what turns 'the bot sometimes gives wrong answers' into a specific, fixable root cause.",
         tags=["observability", "tracing", "monitoring", "llm-ops", "applied", "ai"],
         example="A user reports a wrong answer; the trace shows retrieval returned an outdated doc (score 0.62) and the model faithfully used it - so the fix is re-indexing, not the prompt. Without the trace you'd be guessing between retrieval, prompt, and model.",
         difficulty="Medium",
         frequency="Commonly asked in production-LLM/LLM-ops discussions - 'how do you debug and monitor an LLM app in production?'",
         mnemonic="Log every step of every request (prompt, retrieved chunks+scores, output, tools, tokens, latency, cost) and TRACE them together. Find whether a bad answer came from retrieval, prompt, or model. 'Distributed tracing for LLM pipelines.'"),
    dict(cat="ai_applied", title="RAGAS and RAG evaluation metrics",
         answer="In plain words: to score a RAG system automatically you need metrics for BOTH halves - did retrieval fetch the right context, and did the answer use it faithfully? RAGAS is a popular framework of such metrics, most computed by an LLM-judge so you don't need human labels for every run. Key metrics: FAITHFULNESS - is every claim in the answer supported by the retrieved context? (catches hallucination). ANSWER RELEVANCE - does the answer actually address the question? CONTEXT PRECISION - are the retrieved chunks relevant (not padded with junk)? CONTEXT RECALL - did retrieval fetch ALL the info needed to answer (needs a reference answer)? Together they localize failures: low context recall means fix retrieval/chunking; low faithfulness means the model is drifting from the context (tighten the prompt). You run these on a fixed eval set every change to catch regressions. Complement with latency/cost and periodic human review.",
         tags=["ragas", "rag-evaluation", "faithfulness", "context-recall", "llm-as-judge", "ai"],
         example="A docs bot scores faithfulness 0.95 but context recall 0.6 - retrieval is MISSING needed chunks (so answers are grounded but incomplete). The metric points you at chunking/retrieval, not the prompt - you increase chunk overlap and top-k, and recall rises.",
         difficulty="Medium",
         frequency="Commonly asked in RAG-quality interviews - 'how do you measure whether your RAG system is good?'",
         mnemonic="Score both halves: retrieval (context Precision = relevant? Recall = complete?) and generation (Faithfulness = grounded? Answer-relevance = on-topic?). LLM-judge computes them; run on a fixed set every change. 'Grade the fetch AND the answer.'"),
    dict(cat="ai_llm", title="Contextual retrieval and better chunk context",
         answer="In plain words: a chunk pulled from the middle of a document often loses the context that made it meaningful ('it costs $50' - what is 'it'?), so retrieval and the LLM get confused. Contextual retrieval fixes this by PREPENDING a short, chunk-specific context blurb to each chunk before embedding/indexing. Introduced by Anthropic: for each chunk, an LLM writes a 1-2 sentence description situating it within the whole document ('This chunk is from the 2023 pricing section and refers to the Pro plan'), and that blurb is stored WITH the chunk. Now the embedding captures the chunk's true meaning and keyword search has the right terms, so retrieval is much more accurate. Often combined with hybrid search (BM25 + embeddings) and a reranker for a big accuracy jump. Cost: a one-time LLM pass over all chunks at indexing (cacheable), for durable retrieval-quality gains.",
         tags=["contextual-retrieval", "chunking", "rag", "embeddings", "retrieval", "ai"],
         example="A chunk says 'The limit is 100 requests per minute.' Alone, it's ambiguous. Contextual retrieval prepends 'From the API rate-limits section for the Free tier:' before embedding it - so a query 'free tier rate limit?' now retrieves it reliably instead of missing it.",
         difficulty="Medium",
         frequency="Rising in advanced RAG interviews - 'how do you stop chunks from losing their context?'",
         mnemonic="A lone chunk loses its context ('it costs $50' - what?). Prepend an LLM-written 1-2 sentence blurb situating each chunk in its doc BEFORE embedding. Retrieval accuracy jumps. 'Give every chunk its backstory.'"),
    dict(cat="ai_llm", title="Hard-negative mining for embedding models",
         answer="In plain words: to train a good embedding/retrieval model you show it pairs that SHOULD be close (a question and its answer) and pairs that should be far apart (negatives). Random negatives are too easy - the model learns little. HARD negatives are wrong answers that look deceptively similar to the right one, and training on them is what makes retrieval sharp. A hard negative is a document that's topically similar but NOT the correct answer (e.g. for 'refund window', a chunk about 'exchange window'). You mine them by retrieving top candidates with a current model and taking the high-scoring WRONG ones. Contrastive training then pushes the query embedding toward the true answer and AWAY from these look-alikes, teaching fine distinctions. Caution: avoid FALSE negatives (a mined 'negative' that's actually a correct answer) - they hurt training; filter carefully. This is central to fine-tuning retrievers and rerankers that must separate near-duplicates.",
         tags=["hard-negative-mining", "embeddings", "contrastive-learning", "retrieval", "fine-tuning", "ai"],
         example="Training a support retriever: for 'how do I reset my password?', a RANDOM negative ('our office hours') is trivially far; a HARD negative ('how do I CHANGE my password?') looks similar but is a different intent - training against it teaches the model to tell reset from change, sharpening retrieval.",
         difficulty="Hard",
         frequency="Asked in retrieval/embedding-training and applied-scientist interviews - 'how do you fine-tune a retriever to be more precise?'",
         mnemonic="Train with tricky WRONG look-alikes (hard negatives), not easy random ones - that's what sharpens retrieval. Mine them as high-scoring wrong hits. Beware false negatives (real answers mislabeled). 'Learn from near-misses.'"),
    dict(cat="ai_applied", title="Design a SQL data-analysis agent",
         answer="In plain words: go beyond text-to-SQL - build an agent that answers analytical questions about data by writing SQL, running it, INSPECTING results, and iterating (charting, drilling down) like a data analyst. Pipeline: give the agent the schema (retrieve relevant tables via embeddings if the DB is huge) + examples; it writes SQL, you VALIDATE (read-only SELECT, limits, timeouts, read replica), run it, and feed results BACK so the agent can refine - ask a follow-up query, aggregate differently, or notice an anomaly. Add tools for charts/plots and for computing stats. Safety and correctness dominate: SELECT-only sandbox, row/time caps, self-correction from DB errors, and VERIFICATION (show the SQL, sanity-check numbers). Handle ambiguity by asking clarifying questions ('by revenue or by units?'). Evaluate on a labelled set of question->expected-result pairs, since a plausible-but-wrong number is worse than an error. It's agentic (loop over tool calls), grounded (schema), and safety-critical (sandboxed DB).",
         tags=["sql-agent", "text-to-sql", "agents", "data-analysis", "applied", "ai", "system-design"],
         example="'Which region grew fastest last quarter, and why?' The agent queries revenue by region and quarter, sees APAC grew most, then drills down with a follow-up query by product within APAC, and returns the finding with the SQL shown - all on a read-only replica with row limits.",
         difficulty="Medium",
         frequency="Commonly asked applied-LLM design - extends text-to-SQL into an agentic, safety-critical analytics tool.",
         mnemonic="Schema + examples -> write SQL -> VALIDATE (read-only, limits, replica) -> run -> feed results BACK to refine/drill down -> verify + show SQL. Agentic + grounded + sandboxed. 'An analyst that queries, looks, and iterates - safely.'"),
    dict(cat="ai_applied", title="Design an invoice / document extraction pipeline",
         answer="In plain words: turn messy documents (PDFs, scans, photos of invoices) into clean structured data (vendor, date, line items, total) reliably enough to feed accounting systems. Pipeline: (1) OCR / document parsing to get text + layout (position matters - tables, columns); modern approaches use vision-language models that read the image directly, preserving layout. (2) EXTRACT fields with a schema-constrained LLM prompt (or a layout-aware model), returning JSON matching your schema. (3) VALIDATE: types, required fields, and business rules (line items sum to the total; date is plausible; currency valid) - reject/flag on failure. (4) HUMAN-IN-THE-LOOP for low-confidence extractions (route to a reviewer) since accounting errors are costly. (5) Handle variety (every vendor's invoice looks different - avoid brittle templates; that's why LLMs beat regex here) and multi-page/multi-language docs. Metrics: field-level accuracy and the human-review rate. Grounding + validation + confidence-based routing are the backbone.",
         tags=["document-extraction", "ocr", "invoice", "structured-output", "applied", "ai", "system-design"],
         example="A scanned invoice: a vision-language model reads it into {vendor, date, line_items: [{desc, qty, price}], total}; validation checks the line items sum to the total (they're off by $2 -> flagged), so it routes to a human reviewer instead of silently posting a wrong amount to accounting.",
         difficulty="Medium",
         frequency="Commonly asked in enterprise/document-AI design rounds - covers OCR/VLMs, structured extraction, validation, and human-in-the-loop.",
         mnemonic="OCR/VLM (keep layout) -> schema-constrained extract to JSON -> VALIDATE with business rules (line items sum to total) -> low confidence goes to a HUMAN. LLMs beat brittle templates on variety. 'Read, extract, check, escalate.'"),
    dict(cat="ai_applied", title="Design an enterprise AI search assistant",
         answer="In plain words: a company-wide search that answers questions across all internal knowledge (docs, wikis, tickets, chat, code) grounded in sources - like a private ChatGPT that actually knows your company. Core: connectors ingest from many sources; content is chunked, embedded, and indexed (with metadata + source + timestamps); queries use hybrid search + reranking + RAG to answer with citations. The make-or-break concern unique to enterprise is PERMISSIONS: users must only see what they're allowed to - so you enforce ACL/permission filtering at retrieval time (never retrieve a doc the user can't access), which means storing per-document access metadata and filtering by the user's identity BEFORE the LLM sees anything. Also: freshness (re-sync sources, respect deletions), personalization/recency, handling many content types, cost at scale (caching), and evaluation on real employee questions. Answer with citations so users can verify and trust it.",
         tags=["enterprise-search", "rag", "permissions", "acl", "applied", "ai", "system-design"],
         example="An engineer asks 'what's our on-call escalation policy?'; the assistant retrieves ONLY docs that engineer can access (ACL filter), reranks, and answers with a citation to the runbook - while a contractor asking the same question, lacking access, doesn't get that internal doc at all.",
         difficulty="Hard",
         frequency="Very commonly asked at enterprises building internal AI - the PERMISSIONS/ACL angle is the differentiator interviewers probe.",
         mnemonic="RAG over all internal sources with citations - but the hard part is PERMISSIONS: filter retrieval by the user's ACLs BEFORE the LLM sees anything (never leak a doc they can't access). Plus freshness + many content types. 'Private ChatGPT that respects who-can-see-what.'"),
    dict(cat="ai_llm", title="Prompt caching (reuse a fixed prefix cheaply)",
         answer="In plain words: many requests share a big fixed chunk of prompt - a long system prompt, instructions, or a document you ask many questions about. Prompt caching stores the model's processed form of that PREFIX so repeat requests skip re-processing it, cutting cost and latency. When you send a prompt, the model computes internal state (the KV-cache) for every token. If a prefix is identical across calls, the provider can CACHE that computed state and reuse it, only processing the NEW suffix (the user's specific question). Providers charge much less for cached prefix tokens and return faster. Best when: a large static system prompt/instructions, few-shot examples, or a document reused across many queries. You structure prompts to put the STABLE part first (cacheable) and the variable part last. It's the LLM analogue of memoizing expensive shared work.",
         tags=["prompt-caching", "kv-cache", "cost-optimization", "latency", "llm", "ai"],
         example="A bot answers 50 questions about the same 20-page contract. Without caching, each call re-processes all 20 pages (~15k tokens) - slow and costly. With prompt caching, the contract prefix is processed once and reused, so each follow-up only pays for the short new question - big cost/latency savings.",
         difficulty="Medium",
         frequency="Commonly asked in LLM cost-optimization discussions - a practical lever with a clear 'put stable content first' design implication.",
         mnemonic="Reuse the processed form of a shared PREFIX (long system prompt / document) so repeats skip re-processing it - cheaper + faster. Put the STABLE part first, variable part last. 'Memoize the fixed prompt.'"),
    dict(cat="ai_llm", title="Synthetic data generation for training",
         answer="In plain words: when you lack enough labelled data, you can have an LLM GENERATE training data - questions, answers, instructions, edge cases - to fine-tune or evaluate a model. Uses: create instruction/response pairs to fine-tune a smaller model (often distilling a bigger model's outputs), generate diverse test cases for evaluation, augment rare classes for imbalance, or produce data for domains where real data is scarce or private. Techniques: prompt a strong model to write varied examples (with controlled diversity so they're not all similar), use self-instruct (bootstrap more instructions from a few seeds), and generate hard/edge cases deliberately. CRITICAL cautions: quality control (filter/verify - bad synthetic data teaches bad habits), DIVERSITY (avoid mode collapse to repetitive examples), and MODEL COLLAPSE - training repeatedly on a model's own outputs can degrade quality over generations, so mix in real data. Also watch for the teacher model's biases/errors propagating. Great accelerant, but verify and blend with real data.",
         tags=["synthetic-data", "fine-tuning", "distillation", "data-augmentation", "ai"],
         example="To fine-tune a small support model, you prompt a big model to generate 10k varied (customer question, ideal answer) pairs including tricky edge cases, filter out low-quality ones, mix with a few thousand real tickets, and fine-tune - getting a capable model without hand-labelling 10k examples.",
         difficulty="Medium",
         frequency="Increasingly asked as synthetic data becomes standard - 'how would you train a model with little labelled data?'",
         mnemonic="Have an LLM WRITE training/eval data (instruction pairs, edge cases, rare classes). Watch quality, DIVERSITY, and MODEL COLLAPSE (don't train only on model output - blend real data + verify). 'Generate data, but filter and mix.'"),
    dict(cat="ai_applied", title="Design a document classification system",
         answer="In plain words: automatically sort documents (emails, tickets, contracts, resumes) into categories - by type, topic, priority, or routing destination - at scale. Approaches, cheapest to richest: (1) EMBEDDINGS + a simple classifier (embed the doc, train logistic regression / kNN on labelled examples) - fast, cheap, great when you have labels. (2) ZERO/FEW-SHOT LLM - prompt an LLM with the categories and (optionally) examples; no training data needed, handles nuance, but costlier per doc. (3) Fine-tuned smaller model for high volume once you have data. Design points: long docs exceed context (embed/chunk or summarize first), MULTI-LABEL vs single-label, calibrated CONFIDENCE (route low-confidence to humans), class imbalance (rare categories), evaluation (per-class precision/recall, confusion matrix), and drift (new categories appear - monitor and retrain). Common pattern: LLM to bootstrap labels cheaply, then train a fast embedding classifier for production volume.",
         tags=["document-classification", "embeddings", "zero-shot", "classification", "applied", "ai"],
         example="Routing support tickets to teams: embed each ticket and run a logistic-regression classifier trained on past-routed tickets (fast, cheap at high volume); low-confidence tickets go to an LLM for a nuanced call or to a human - with per-class precision/recall tracked and rare new issue types monitored.",
         difficulty="Medium",
         frequency="Commonly asked applied-ML design - a clean test of the embeddings-classifier vs LLM tradeoff and production concerns.",
         mnemonic="Embeddings + simple classifier (cheap, needs labels) OR zero/few-shot LLM (no labels, pricier) OR fine-tune for volume. Handle long docs, multi-label, confidence->human, imbalance, drift. 'LLM to bootstrap labels, embeddings-classifier for scale.'"),
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

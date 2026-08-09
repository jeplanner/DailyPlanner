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
    # ---- AI (6) ----
    dict(cat="ai_applied", title="Design a time-series forecasting system",
         answer="In plain words: predict future numbers (sales, traffic, demand, server load) from history - but time data has structure (trend, seasonality) and strict rules that make it different from normal ML. Key ideas: decompose the signal into TREND (long-term direction), SEASONALITY (repeating cycles - daily/weekly/yearly), and NOISE. Models range from classical (ARIMA, exponential smoothing/Prophet - great baselines, interpretable) to ML (gradient-boosted trees on lag/rolling features) to deep (LSTM/Transformer for complex multivariate series). CRITICAL rules: never shuffle - split by TIME (train on past, test on future); engineer LAG features (value last week) and rolling stats WITHOUT leaking future; and evaluate with a rolling/backtest (walk-forward) using MAPE/RMSE. Handle multiple seasonalities, holidays/events, missing data, and cold-start for new series. Forecast INTERVALS (uncertainty), not just a point, because decisions depend on the range. It's the same 'respect time, no leakage' discipline as any temporal ML.",
         tags=["time-series", "forecasting", "arima", "seasonality", "applied", "ai"],
         example="Forecasting store demand: decompose into weekly seasonality + upward trend + holiday spikes; a GBT on lag features (sales last 1/7/28 days) trained on 2 years, backtested walk-forward, predicts next week WITH a confidence interval so inventory is stocked for the likely range, not a single guess.",
         difficulty="Medium",
         frequency="Very commonly asked applied-ML case (retail, infra, finance) - tests time-split discipline, seasonality, and no-leakage feature engineering.",
         mnemonic="Decompose: Trend + Seasonality + Noise. Split by TIME (past->future), lag/rolling features WITHOUT leakage, backtest walk-forward (MAPE/RMSE), predict an INTERVAL. Classical (ARIMA/Prophet) baselines before deep. 'Respect time, forecast a range.'"),
    dict(cat="ai_applied", title="Design an anomaly detection system",
         answer="In plain words: automatically flag the rare weird thing - fraud, a failing server, a security breach, a defective part - when you mostly have 'normal' data and few or no labels for 'bad'. Because anomalies are rare and varied, you usually can't train a normal classifier. Approaches: (1) STATISTICAL - model normal (mean/std, z-score; for time series, deviation from forecast) and flag outliers. (2) UNSUPERVISED ML - isolation forest (anomalies are 'easy to isolate'), one-class SVM, or an AUTOENCODER (train to reconstruct normal data; high reconstruction error = anomaly). (3) SUPERVISED if you do have labels (but handle extreme imbalance). Design points: define what 'anomaly' means (point vs contextual vs collective), set the threshold by the COST of false alarms vs misses (alert fatigue is real), handle seasonality (3am traffic isn't anomalous at 3am), adapt as normal drifts, and give humans context to triage. Evaluate with precision/recall at the chosen threshold, not accuracy.",
         tags=["anomaly-detection", "isolation-forest", "autoencoder", "unsupervised", "applied", "ai"],
         example="Server monitoring: an autoencoder trained on normal metrics reconstructs them well; when a memory-leak pattern appears, reconstruction error spikes above threshold and pages on-call - catching a failure mode nobody wrote a rule for, while seasonality-aware baselines avoid false alarms during nightly batch jobs.",
         difficulty="Medium",
         frequency="Commonly asked applied-ML design (security, infra, fraud, manufacturing) - tests unsupervised methods and threshold/cost thinking.",
         mnemonic="Mostly-normal data, rare varied 'bad' -> model NORMAL, flag deviations: stats (z-score), isolation forest, or autoencoder (high reconstruction error). Set threshold by cost of FP vs FN; respect seasonality; adapt to drift. 'Learn normal, alarm on surprise.'"),
    dict(cat="ai_llm", title="Model cards and responsible model documentation",
         answer="In plain words: a model card is a short standardized 'nutrition label' for an ML model - it documents what the model does, how it was trained, how well it works, and where it should NOT be used - so others can use it responsibly. Introduced by Google, a model card typically covers: intended USE (and out-of-scope uses), training DATA and its known biases/limitations, evaluation results BROKEN DOWN by subgroup (not just aggregate - to expose fairness gaps), performance metrics and the conditions they hold under, ethical considerations, and caveats/recommendations. Why it matters: it forces teams to state limitations explicitly, helps users avoid misusing a model outside its tested range, supports fairness/compliance (EU AI Act, audits), and improves reproducibility. Analogous artifacts: DATASHEETS for datasets and SYSTEM cards for whole AI systems. It's cheap documentation with outsized value for trust and governance.",
         tags=["model-cards", "responsible-ai", "documentation", "fairness", "governance", "ai"],
         example="A face-detection model's card states it was trained mostly on adult faces, reports accuracy per skin-tone and age group (revealing lower accuracy on children), and explicitly lists 'surveillance' as out-of-scope - so a downstream team knows not to deploy it for a kids' app without more testing.",
         difficulty="Easy",
         frequency="Asked in responsible-AI / senior ML discussions - shows you think about limitations, fairness, and governance, not just accuracy.",
         mnemonic="A 'nutrition label' for a model: intended use + OUT-of-scope, training data & biases, metrics BROKEN DOWN by subgroup, ethical caveats. Datasheets do this for data. Cheap doc, big trust/compliance value. 'State what it can't do, and for whom.'"),
    dict(cat="ai_applied", title="Cold-start problem in ML systems",
         answer="In plain words: recommenders and personalization need history to work, but new USERS, new ITEMS, and brand-new SYSTEMS have none - the cold-start problem is how to give good results before you've learned anything about them. Three flavors and fixes. NEW USER: no interaction history -> ask a few onboarding preferences, use demographics/context, or show popular/trending items until you learn. NEW ITEM: no one has interacted with it -> use CONTENT features (an LLM/embedding of its text/metadata puts it near similar known items) instead of collaborative signals. NEW SYSTEM: no data at all -> start with content-based or rules, log interactions, and transition to learned models as data accumulates. General tools: hybrid models (content + collaborative), embeddings from metadata, and EXPLORATION (bandits/Thompson sampling to try new things and gather data). The theme: lean on CONTENT and context when behavioral history is missing, and deliberately explore to collect it.",
         tags=["cold-start", "recommendation", "content-based", "exploration", "applied", "ai"],
         example="A streaming service adds a brand-new show with zero views; content embeddings from its description/genre place it near similar popular shows, so it's recommended to fans of those - and a small exploration budget shows it to some users to gather real interaction data fast (solving new-item cold-start).",
         difficulty="Medium",
         frequency="Very commonly asked in recommendation/personalization design - 'how do you recommend a new item or serve a brand-new user?'",
         mnemonic="No history yet -> lean on CONTENT + context, not collaborative signals. New user: onboarding/popular. New item: content embeddings. New system: rules then learn. Plus EXPLORATION (bandits) to gather data. 'Content when cold, explore to warm up.'"),
    dict(cat="ai_llm", title="Guardrail frameworks (Llama Guard, NeMo Guardrails)",
         answer="In plain words: guardrail frameworks are ready-made tools that wrap an LLM to enforce safety and scope rules - so you don't hand-build every check. They sit between the user and the model (and between the model and the user). LLAMA GUARD is a specialized classifier LLM that labels whether an input or output is safe across harm categories (violence, hate, self-harm, etc.) - you call it to screen prompts and responses. NEMO GUARDRAILS (NVIDIA) lets you define conversational RAILS in a config: allowed topics, refusal flows, fact-checking/grounding checks, and dialogue policies, so the bot stays on-topic and follows rules. Guardrails-AI and similar validate/repair structured output against a schema. In practice you compose them: an input rail (block disallowed/injection), output rails (toxicity, grounding/faithfulness, format validation, PII), and topic/scope rails. They implement the layered 'never trust the model alone' principle with reusable components instead of bespoke code - but you still tune and test them for your policies.",
         tags=["guardrails", "llama-guard", "nemo-guardrails", "llm-safety", "moderation", "ai"],
         example="A banking bot uses Llama Guard to screen every user message and reply for unsafe content, NeMo Guardrails to refuse off-topic requests ('I can only help with banking') and enforce a grounding check, and a schema validator on any JSON - a composed safety layer built from frameworks, not from scratch.",
         difficulty="Medium",
         frequency="Increasingly asked in production-LLM/safety interviews - naming concrete frameworks signals hands-on GenAI-safety experience.",
         mnemonic="Ready-made safety wrappers: Llama Guard (classify input/output as safe?), NeMo Guardrails (topic/refusal/grounding rails), schema validators. Compose input + output + topic rails. Reusable 'never trust the model alone'. Still tune/test."),
    dict(cat="ai_llm", title="Active learning (label the most useful examples)",
         answer="In plain words: labelling data is expensive, so instead of labelling everything randomly, active learning lets the MODEL pick the examples that would teach it the most - so you reach good accuracy with far fewer labels. The loop: train on a small labelled set, run the model on unlabelled data, and SELECT the most informative examples for a human to label, add them, retrain, repeat. How to pick 'informative': UNCERTAINTY sampling (examples the model is least confident on - near the decision boundary), QUERY-BY-COMMITTEE (examples an ensemble disagrees on), or DIVERSITY/representativeness (cover different regions, avoid labelling near-duplicates). It shines when unlabelled data is plentiful but labelling is costly (medical images, legal docs). Cautions: it can bias the labelled set toward boundary cases (mix in some random labels), and repeated uncertainty picks can waste effort on inherently ambiguous/noisy examples. Pairs well with LLMs that pre-label and route only the uncertain ones to humans.",
         tags=["active-learning", "labeling", "uncertainty-sampling", "data-efficiency", "ai"],
         example="Building a medical-image classifier with 100k unlabelled scans but a costly radiologist: active learning labels the 500 scans the model is MOST uncertain about each round instead of 500 random ones, reaching target accuracy with ~5x fewer labels than random labelling.",
         difficulty="Medium",
         frequency="Asked in data-efficiency / applied-ML interviews - 'labelling is expensive; how do you spend the budget well?'",
         mnemonic="Let the model choose what to label: pick the MOST UNCERTAIN (boundary) or most-disagreed examples, label those, retrain, repeat. Far fewer labels for the same accuracy. Mix in some random to avoid bias. 'Label what teaches the most.'"),
    # ---- ml_coding numpy (3, ast.parse-only) ----
    dict(cat="ml_coding", title="Sinusoidal positional encoding (numpy)",
         answer="In plain words: transformers process tokens in parallel with no built-in sense of order, so you ADD a position signal to each token embedding. The original Transformer uses fixed sine/cosine waves of different frequencies: even dimensions use sine, odd use cosine, and the wavelength grows with the dimension index - so each position gets a unique pattern and the model can learn relative offsets from the smooth wave structure.",
         tags=["positional-encoding", "transformer", "sinusoidal", "numpy", "ml-coding"],
         code='''# Sinusoidal positional encoding matrix (seq_len, d_model). ast.parse-only.
import numpy as np

def positional_encoding(seq_len, d_model):
    pos = np.arange(seq_len)[:, None]             # (seq_len, 1) positions
    i = np.arange(d_model)[None, :]               # (1, d_model) dimension idx
    # frequency term: 1 / 10000^(2*floor(i/2)/d_model)
    angle_rates = 1.0 / np.power(10000, (2 * (i // 2)) / d_model)
    angles = pos * angle_rates                    # (seq_len, d_model)
    pe = np.zeros((seq_len, d_model))
    pe[:, 0::2] = np.sin(angles[:, 0::2])         # even dims -> sine
    pe[:, 1::2] = np.cos(angles[:, 1::2])         # odd dims  -> cosine
    return pe''',
         complexity="Time O(seq_len * d_model), space O(seq_len * d_model).",
         pitfalls="Mixing sin/cos on the wrong (even/odd) dimensions; forgetting the 10000 base scales the wavelengths; adding vs concatenating (it's ADDED to embeddings).",
         example="positional_encoding(50, 512) gives a (50, 512) matrix ADDED to token embeddings so position 5 and position 40 have distinguishable, smoothly-varying signals.",
         difficulty="Medium",
         frequency="Commonly asked in transformer-implementation interviews - 'how are positions encoded (the original way)?'",
         mnemonic="Add waves: even dims = sin, odd dims = cos, wavelengths grow with dim (base 10000). Each position -> a unique smooth pattern the model reads as order. 'Stamp positions with layered sine waves.'"),
    dict(cat="ml_coding", title="TF-IDF from scratch (numpy)",
         answer="In plain words: TF-IDF scores how important a word is to a document within a collection. TERM FREQUENCY (TF) rewards words that appear often IN the document; INVERSE DOCUMENT FREQUENCY (IDF) down-weights words that appear in MANY documents (like 'the'). Multiply them: a word is important if it's frequent here but rare overall.",
         tags=["tf-idf", "nlp", "text-vectorization", "numpy", "ml-coding"],
         code='''# TF-IDF matrix from a list of token-lists. ast.parse-only.
import numpy as np

def tf_idf(docs, vocab):
    n_docs = len(docs)
    idx = {w: i for i, w in enumerate(vocab)}
    tf = np.zeros((n_docs, len(vocab)))
    for d, doc in enumerate(docs):
        for w in doc:
            if w in idx:
                tf[d, idx[w]] += 1                # raw counts
        if len(doc) > 0:
            tf[d] /= len(doc)                     # normalize by doc length
    # document frequency: in how many docs does each term appear
    df = (tf > 0).sum(axis=0)                      # (vocab,)
    idf = np.log((1 + n_docs) / (1 + df)) + 1      # smoothed idf
    return tf * idf                                # (n_docs, vocab)''',
         complexity="Time O(total tokens + n_docs*vocab), space O(n_docs*vocab).",
         pitfalls="Forgetting IDF smoothing (+1) -> divide-by-zero / log(0); not normalizing TF by length; counting a term's df multiple times per doc.",
         example="For docs about cats/dogs, 'the' gets a low TF-IDF (high df, low idf) while 'purr' scores high in the cat doc (frequent there, rare overall).",
         difficulty="Medium",
         frequency="Commonly asked classic NLP-coding question - 'implement TF-IDF' tests the TF x IDF intuition.",
         mnemonic="Important = frequent HERE (TF) but rare EVERYWHERE (IDF = log(N/df)). Multiply them. 'the' scores low, 'purr' scores high. Smooth the idf (+1) to avoid log(0)."),
    dict(cat="ml_coding", title="LSTM cell forward pass (numpy)",
         answer="In plain words: an LSTM remembers information over long sequences using a CELL STATE (long-term memory) plus three GATES that decide what to forget, what to add, and what to output. Each step: the FORGET gate drops old memory, the INPUT gate writes new candidate memory, the cell state updates, and the OUTPUT gate reads out the hidden state. Gates are sigmoids (0-1 'how much'); the candidate uses tanh.",
         tags=["lstm", "rnn", "gates", "sequence", "numpy", "ml-coding"],
         code='''# One LSTM cell step. ast.parse-only. Weights concatenated for [x, h_prev].
import numpy as np

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))

def lstm_step(x, h_prev, c_prev, Wf, Wi, Wc, Wo, bf, bi, bc, bo):
    z = np.concatenate([x, h_prev])               # stack input + prev hidden
    f = sigmoid(Wf @ z + bf)                       # forget gate: keep how much old memory
    i = sigmoid(Wi @ z + bi)                       # input gate: write how much new
    c_hat = np.tanh(Wc @ z + bc)                   # candidate memory
    c = f * c_prev + i * c_hat                     # new cell state (forget + add)
    o = sigmoid(Wo @ z + bo)                       # output gate
    h = o * np.tanh(c)                             # new hidden state (read-out)
    return h, c''',
         complexity="Time O(hidden * (input+hidden)), space O(hidden).",
         pitfalls="Using tanh where a sigmoid gate belongs (gates must be 0-1); forgetting to carry BOTH h and c to the next step; wrong concatenation order vs the weights.",
         example="Feeding a sentence word-by-word, the forget gate can drop irrelevant past words while the cell state carries a subject across many steps so a later verb agrees with it.",
         difficulty="Hard",
         frequency="Asked in deep-learning/NLP interviews - 'explain/implement an LSTM cell and its gates'.",
         mnemonic="Cell state = long memory; 3 gates (sigmoids): FORGET old, INPUT new (tanh candidate), OUTPUT read. c = f*c_prev + i*c_hat; h = o*tanh(c). 'Forget, write, remember, read.'"),
    # ---- cs_fundamentals (2) ----
    dict(cat="cs_fundamentals", title="Deadlock and its four necessary conditions",
         answer="In plain words: a deadlock is when two or more processes are stuck forever, each waiting for a resource the other holds - like two people in a hallway each refusing to step aside. It can ONLY happen when all FOUR Coffman conditions hold at once: (1) MUTUAL EXCLUSION - a resource can't be shared (only one holder). (2) HOLD AND WAIT - a process holds one resource while waiting for another. (3) NO PREEMPTION - you can't forcibly take a resource away; the holder must release it. (4) CIRCULAR WAIT - a cycle of processes each waiting on the next. Break ANY one condition and deadlock is impossible - the basis of prevention: e.g. impose a global ORDER on resource acquisition (kills circular wait), require all resources up front (kills hold-and-wait), or allow preemption/timeouts. Alternatives: deadlock AVOIDANCE (Banker's algorithm) and DETECTION + recovery (find a cycle, kill/rollback a process).",
         tags=["deadlock", "concurrency", "operating-systems", "coffman-conditions", "cs"],
         code='''# Ordered locking prevents deadlock by killing 'circular wait'.
import threading

lock_a = threading.Lock()
lock_b = threading.Lock()

def safe_transfer():
    # ALWAYS acquire in the same global order (a before b) in every thread
    with lock_a:              # acquire lower-ranked lock first
        with lock_b:          # then the higher-ranked one
            pass              # no thread can form a cycle -> no deadlock''',
         complexity="Prevention is a design constraint, not a runtime cost.",
         pitfalls="Acquiring locks in different orders in different code paths (classic cause); holding a lock while calling out to code that grabs another.",
         example="Thread 1 holds lock A wanting B; thread 2 holds B wanting A -> circular wait -> deadlock. Forcing every thread to grab A before B removes the cycle, so it can't happen.",
         difficulty="Medium",
         frequency="Very commonly asked OS/concurrency question - 'what causes deadlock and how do you prevent it?'",
         mnemonic="4 conditions (M-H-N-C): Mutual exclusion, Hold-and-wait, No-preemption, Circular-wait - ALL must hold. Break one to prevent (usually order your locks to kill circular wait). 'Same lock order, no deadlock.'"),
    dict(cat="cs_fundamentals", title="TCP three-way handshake",
         answer="In plain words: before TCP sends data it sets up a reliable connection with a three-message greeting so both sides agree they can hear each other and sync starting sequence numbers. (1) SYN - the client sends a SYN with its initial sequence number (ISN) x: 'let's talk, I start at x.' (2) SYN-ACK - the server replies with its own SYN (seq y) AND an ACK of x+1: 'got it, I start at y, expecting x+1.' (3) ACK - the client ACKs y+1: 'got yours.' Now both sides have confirmed send+receive works and synced sequence numbers, so ordered, reliable data can flow. The sequence numbers enable ordering and detecting lost/duplicate bytes. Teardown is a 4-way (FIN/ACK each direction). This setup cost (one round trip before data) is why connection reuse/keep-alive and protocols like QUIC/TLS 1.3 (0-RTT) matter for latency.",
         tags=["tcp", "handshake", "networking", "sequence-numbers", "cs"],
         diagram=r"""
client                     server
  |  --- SYN (seq=x) ------->  |   'I want to connect, I start at x'
  |  <-- SYN-ACK (y, ack=x+1)- |   'OK, I start at y, expecting x+1'
  |  --- ACK (ack=y+1) ------> |   'Got it' -> connection ESTABLISHED
""".strip("\n"),
         example="Loading a web page: your browser's TCP does SYN -> SYN-ACK -> ACK with the server (one round trip) before the HTTP request even goes out - which is why far-away servers feel slower and why keep-alive reuses the connection.",
         difficulty="Easy",
         frequency="Very commonly asked networking basic - 'walk me through the TCP handshake'.",
         mnemonic="SYN -> SYN-ACK -> ACK (client, server, client). Sync starting SEQUENCE NUMBERS + confirm two-way reachability before data. One round trip of setup. 'Knock, knock-back, confirmed.'"),
    # ---- conceptual (1) ----
    dict(cat="conceptual", title="Why does labeling by uncertainty (active learning) beat random labeling, and when can it backfire?",
         answer="Supervised models learn a decision boundary, and not all training examples are equally useful for finding it. Examples far from the boundary (obvious cats, obvious dogs) confirm what the model already knows and add little; examples NEAR the boundary (ambiguous, low-confidence) are where the model is wrong or unsure, and labeling those pins down the boundary precisely. Active learning exploits this: instead of labeling random examples (many of which are 'easy' and redundant), it repeatedly labels the examples the current model is most UNCERTAIN about, so each expensive human label removes the most confusion. Empirically this reaches a target accuracy with far fewer labels - a big deal when labeling is costly (radiologists, lawyers). Concretely the loop is: train on a seed set, score the unlabeled pool, pick the top-uncertainty items (or the items an ensemble most DISagrees on), get them labeled, retrain, repeat. WHEN IT BACKFIRES: (1) SAMPLING BIAS - by always chasing the boundary, the labeled set becomes unrepresentative of the true data distribution, which can hurt calibration and any model later trained on it (mitigate by mixing in some random labels and adding a diversity/representativeness criterion). (2) NOISY/AMBIGUOUS examples - the most 'uncertain' points can be inherently unlabelable garbage (mislabeled, corrupted, genuinely ambiguous), so the model burns its budget on examples that don't help and may even mislead (mitigate by filtering outliers or using query-by-committee). (3) The uncertainty estimate itself can be UNRELIABLE - a poorly-calibrated model is confidently wrong, so it won't flag the examples it should (mitigate with better uncertainty via ensembles/MC-dropout). (4) It's tied to ONE model - a set curated for model A's boundary may be a poor general-purpose dataset. The takeaway: uncertainty sampling is a powerful label-efficiency lever because it targets the most informative region, but it needs guardrails (diversity, some randomness, noise filtering, calibrated uncertainty) or its own selection bias undermines it.",
         tags=["active-learning", "uncertainty-sampling", "sampling-bias", "data-efficiency", "why"],
         example="Labeling 500 of 100k scans: uncertainty sampling picks the 500 borderline scans (max information) and hits target accuracy with 5x fewer labels than random - but if 50 of those are corrupted images the model finds 'uncertain', the budget is wasted, so you filter outliers and mix in random labels to keep the set representative.",
         difficulty="Hard",
         frequency="Asked in data-efficiency/applied-scientist interviews - 'why does active learning help, and what are its failure modes?'",
         mnemonic="Boundary examples teach the most, so label the UNCERTAIN ones -> fewer labels for the same accuracy. Backfires via sampling BIAS, noisy 'uncertain' junk, and bad calibration -> fix with diversity + some random + outlier filtering. 'Label the confusing, but don't only label the confusing.'"),
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

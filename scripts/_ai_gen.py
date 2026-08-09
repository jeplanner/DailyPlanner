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
    dict(cat="ai_llm", title="Grouped-Query Attention (GQA) and Multi-Query Attention",
         answer="In plain words: standard multi-head attention keeps a separate KEY and VALUE for every attention head, which makes the KV-cache huge and slow to read during generation. GQA and MQA shrink that by SHARING keys/values across heads, cutting memory and speeding up inference with almost no quality loss. Multi-Head Attention (MHA): each of the N heads has its own Q, K, V - most expressive but the KV-cache is N-sized. Multi-Query Attention (MQA): all heads share ONE K and V (only the queries differ) - tiny KV-cache, fastest, but a bit of quality drop. Grouped-Query Attention (GQA): the middle ground - split heads into a few GROUPS, each group shares one K/V - so you get most of MHA's quality with most of MQA's speed. GQA is now standard in models like Llama 2/3 because it makes long-context and high-throughput serving far cheaper (smaller KV-cache to store and stream).",
         tags=["gqa", "mqa", "attention", "kv-cache", "inference-optimization", "llm", "ai"],
         example="A model with 32 query heads: MHA stores 32 K/V sets (big cache); MQA stores 1 (fast, slight quality loss); GQA with 8 groups stores 8 - roughly MHA quality at roughly MQA speed, which is why Llama uses it for cheaper long-context serving.",
         difficulty="Hard",
         frequency="Asked in transformer-architecture/inference interviews (research, NVIDIA, infra) - 'how do modern LLMs shrink the KV-cache?'",
         mnemonic="Share keys/values across heads to shrink the KV-cache. MHA = every head its own (big). MQA = all share one (tiny, fast). GQA = groups share (best of both, the modern default)."),
    dict(cat="ai_llm", title="Sliding-window and sparse attention (long context cheaply)",
         answer="In plain words: full attention makes every token look at every other token, which costs grows with the SQUARE of the sequence length - unaffordable for very long inputs. Sparse and sliding-window attention let each token look at only SOME others, making long context cheaper. SLIDING-WINDOW attention: each token attends only to the last W tokens (a local window), so cost is linear in length; stacking layers still lets information flow far (like a receptive field growing with depth). Used in Mistral. Other SPARSE patterns mix local windows with a few GLOBAL tokens (that everyone attends to) or strided/block patterns (Longformer, BigBird) to keep some long-range links while staying cheap. Trade-off: you lose some direct long-range attention, so patterns are designed so important information can still propagate. These are key enablers of long-context models alongside FlashAttention and better positional encodings.",
         tags=["sparse-attention", "sliding-window", "long-context", "attention", "llm", "ai"],
         example="With a 32k-token document, full attention builds a 32k x 32k map (a billion entries per head - too much); sliding-window attention of size 4096 lets each token see its nearby 4096, and stacked layers still propagate information across the whole doc at a fraction of the cost.",
         difficulty="Hard",
         frequency="Asked in long-context/efficiency discussions in ML-research and infra interviews.",
         mnemonic="Full attention is quadratic (everyone sees everyone). Make it local: sliding WINDOW (see last W) + a few GLOBAL tokens = linear cost, long context. Depth still spreads info far. 'Look nearby, relay through layers.'"),
    dict(cat="ai_llm", title="RoPE scaling and extending context length",
         answer="In plain words: a model trained with a 4k context can't just be handed 32k tokens - its positional encoding never saw those far-apart positions, so quality collapses. RoPE scaling stretches the position signal so a pretrained model can handle longer inputs, often with a little extra fine-tuning. Since RoPE encodes position by rotating query/key vectors at various frequencies, you can extend range by SLOWING the rotations. POSITION INTERPOLATION squeezes new positions into the trained range (e.g. treat position 8000 as if it were 1000) so nothing is out-of-distribution; NTK-aware scaling and YaRN adjust frequencies more cleverly to preserve fine local detail while extending reach. A short fine-tune on long examples then adapts the model. This is how models get extended from a few thousand to tens or hundreds of thousands of tokens without retraining from scratch. Caveat: longer context still costs more compute/memory and quality can soften in the far middle.",
         tags=["rope-scaling", "long-context", "position-interpolation", "yarn", "llm", "ai"],
         example="A model pretrained at 4k context is extended to 32k by position interpolation (mapping the 32k positions into the 4k range RoPE understands) plus a brief fine-tune on long documents - so it can now summarize a whole book-length input it could never fit before.",
         difficulty="Hard",
         frequency="Asked in LLM-research/long-context interviews - 'how do you extend a model's context window?'",
         mnemonic="RoPE rotates by position; to go longer, SLOW the rotations / interpolate new positions into the trained range (PI, NTK, YaRN) + a short fine-tune. 'Squeeze far positions into familiar territory.'"),
    dict(cat="ai_llm", title="Hallucination detection methods",
         answer="In plain words: since LLMs can state false things confidently, you want automatic ways to CATCH likely hallucinations before they reach users. Approaches: (1) GROUNDING check (for RAG) - verify each claim is supported by the retrieved sources; an NLI/entailment model or an LLM-judge scores whether the answer follows from the context, and unsupported claims are flagged. (2) SELF-CONSISTENCY - sample the same question several times; if the answers disagree, the model is unsure (a hallucination signal). (3) UNCERTAINTY signals - low token probabilities/high entropy on the key claim suggest guessing. (4) LLM-as-critic - a second model checks the answer for unsupported facts. (5) FACT-CHECK against a trusted source/tool (search, DB, calculator). (6) Ask the model to CITE and then verify the citations actually say what's claimed. In practice you combine cheap signals (probabilities, self-consistency) with a grounding/entailment check, and route uncertain answers to a fallback ('I'm not sure') or a human.",
         tags=["hallucination-detection", "faithfulness", "nli", "self-consistency", "llm", "ai"],
         example="A medical Q&A bot answers, then an entailment model checks each sentence against the retrieved guideline; one sentence isn't supported, so it's dropped and the bot says 'I could not verify X in the sources' - instead of confidently stating an unsupported claim.",
         difficulty="Medium",
         frequency="Commonly asked in reliability-focused GenAI rounds - 'how would you detect when the model is making things up?'",
         mnemonic="Catch made-up claims: check GROUNDING (does the source support it? use NLI/judge), SELF-CONSISTENCY (do repeated samples agree?), UNCERTAINTY (low token prob?), and verify CITATIONS. Combine signals, fall back when unsure."),
    dict(cat="ai_applied", title="Agentic RAG (retrieval as a tool the model controls)",
         answer="In plain words: classic RAG retrieves once, up front, then answers. Agentic RAG lets the model DECIDE when and what to retrieve - it can search, look at results, refine the query, retrieve again, or use other tools - handling complex questions that a single retrieval can't. Instead of a fixed 'retrieve then generate' pipeline, retrieval becomes a TOOL the agent calls in a loop: it might break a multi-part question into sub-queries, retrieve for each, notice a gap and search again, or decide it has enough and answer. This handles multi-hop questions ('compare X in the 2022 vs 2023 report'), ambiguous queries (ask a clarifying question or try variants), and cases where the first retrieval misses. Costs: more LLM calls and latency, and loops that must be bounded. Related ideas: query rewriting, self-RAG (the model critiques its own retrieval/answer), and adaptive retrieval (only retrieve when the model is unsure).",
         tags=["agentic-rag", "rag", "agents", "multi-hop", "tool-use", "applied", "ai"],
         example="Question: 'Did our revenue grow faster than our main competitor last year?' Agentic RAG issues one search for our revenue, another for the competitor's, notices it needs the growth rates, retrieves those, then compares - a single up-front retrieval would have missed half the facts.",
         difficulty="Medium",
         frequency="Rising in advanced RAG/agent interviews - 'how do you handle multi-hop or complex questions RAG gets wrong?'",
         mnemonic="Let the model DRIVE retrieval in a loop: search -> look -> refine -> search again -> answer. Handles multi-hop/ambiguous questions a one-shot retrieve can't. Bound the loop. 'Retrieval as a tool, not a fixed step.'"),
    dict(cat="ai_applied", title="Query rewriting and HyDE for better retrieval",
         answer="In plain words: users write short, messy, or context-dependent queries that don't match how documents are written, so retrieval misses. Query rewriting reshapes the query BEFORE searching to improve what comes back. Techniques: (1) REWRITE/expand - an LLM turns 'and the second one?' (which needs chat history) into a standalone, keyword-rich query, or expands abbreviations and adds synonyms. (2) MULTI-QUERY - generate several paraphrases and retrieve for each, then merge (catches more relevant docs). (3) HyDE (Hypothetical Document Embeddings) - ask the LLM to WRITE a fake ideal answer to the question, then embed THAT and search - because a hypothetical answer is written in the same style/vocabulary as real documents, its embedding often retrieves better than the bare question's. (4) STEP-BACK - ask a broader version to get background context. These are cheap add-ons that noticeably lift retrieval recall in RAG.",
         tags=["query-rewriting", "hyde", "multi-query", "retrieval", "rag", "ai"],
         example="User asks 'why is it slow?' in a chat about database indexing. Rewriting turns it into 'why is a database query slow without an index?'; HyDE writes a short hypothetical answer about missing indexes and embeds that - both retrieve far better docs than the vague original.",
         difficulty="Medium",
         frequency="Commonly asked in RAG-quality discussions - 'retrieval is missing relevant docs; how do you improve it before touching the model?'",
         mnemonic="Fix the QUERY before searching: rewrite to standalone/keyword-rich, generate paraphrases (multi-query), or HyDE (embed a fake ideal ANSWER, since it looks like real docs). Cheap recall boost. 'Search like the docs are written.'"),
    dict(cat="ai_llm", title="LLM red-teaming (stress-testing for safety)",
         answer="In plain words: red-teaming is deliberately ATTACKING your own AI - trying to make it produce harmful, biased, or policy-violating output - so you find and fix weaknesses before real users (or bad actors) do. It's borrowed from security. Red-teamers probe with adversarial prompts: jailbreaks ('pretend you have no rules'), prompt injection, requests for disallowed content via roleplay or obfuscation, attempts to extract the system prompt or training data, and edge cases that trigger bias or unsafe tool actions. Findings feed back into fixes: better system prompts, guardrails/classifiers, RLHF/safety fine-tuning, and tool permission limits. Red-teaming can be manual (creative humans), automated (an attacker LLM generates many adversarial prompts), or crowd-sourced. It's continuous, not one-time, because new jailbreaks appear constantly. The goal is measured coverage across a taxonomy of harms plus a plan to close the gaps found.",
         tags=["red-teaming", "llm-safety", "jailbreak", "alignment", "security", "ai"],
         example="Before launch, a team tries 1000 adversarial prompts on a chatbot: some roleplay jailbreaks slip past, extracting instructions for a harmful task. Those cases become new guardrail rules and safety-tuning data, and the jailbreak family is added to a regression suite that runs every release.",
         difficulty="Medium",
         frequency="Increasingly asked at companies deploying LLMs - 'how do you make sure the model is safe before shipping?'",
         mnemonic="Attack your own AI first: jailbreaks, injection, bias, data-extraction. Feed failures into guardrails + safety tuning + a regression suite. Continuous, not one-time. 'Break it before the bad guys do.'"),
    dict(cat="ai_applied", title="Design a meeting-notes summarizer",
         answer="In plain words: take a meeting recording and produce a useful summary with decisions and action items. Pipeline: (1) TRANSCRIBE audio to text with an ASR model (e.g. Whisper), ideally with SPEAKER DIARIZATION (who said what) and timestamps. (2) CHUNK the transcript (long meetings exceed the context window) and summarize hierarchically - summarize each chunk, then summarize the summaries (map-reduce), or summarize incrementally. (3) EXTRACT structured outputs: a short overview, key decisions, and ACTION ITEMS (owner + task + due date) via a schema-constrained prompt. (4) Optionally link to timestamps so users can jump to the moment. Design points: handling long meetings (map-reduce summarization), faithfulness (don't invent action items - ground in the transcript), speaker attribution accuracy, privacy/PII (redact and secure), latency (batch/async since it's not real-time), and evaluation (do humans agree the decisions/actions are right and complete?).",
         tags=["summarization", "asr", "whisper", "map-reduce", "applied", "ai", "system-design"],
         example="A 60-minute sales call: Whisper transcribes with speakers, the transcript is chunked and map-reduce summarized, and a schema prompt extracts {overview, decisions[], action_items: [{owner, task, due}]} - so the team gets 'Alice to send the proposal by Friday' with a link to 12:34 in the recording.",
         difficulty="Medium",
         frequency="Commonly asked applied-LLM design - covers ASR, long-input summarization, and structured extraction.",
         mnemonic="Transcribe (Whisper + speakers) -> chunk + map-reduce summarize -> extract structured decisions/action-items (owner+task+due), grounded in the transcript. Async, faithful, privacy-safe. 'Audio in, decisions + to-dos out.'"),
    dict(cat="ai_applied", title="Design a resume screening system (and its bias risks)",
         answer="In plain words: use AI to help rank/filter job applicants against a role - powerful for volume, but DANGEROUS for fairness and legally sensitive, so the design centers on bias mitigation and human oversight. Core: parse resumes (OCR/text extraction), and score fit against the job description, often via embeddings (semantic match of skills/experience) plus an LLM to reason about qualifications, producing a ranked shortlist WITH explanations. Critical safeguards: (1) BIAS - models can learn to favor gender/race/age/school proxies from historical data (Amazon famously scrapped a tool that penalized 'women'); mitigate by removing/masking protected attributes and proxies, auditing outcomes for disparate impact across groups, and testing on counterfactual resumes. (2) HUMAN-IN-THE-LOOP - AI assists ranking, humans decide; never fully automate rejections. (3) TRANSPARENCY - explain scores; keep candidates' right to review. (4) VALIDATION against real job-performance, not past hiring bias. (5) LEGAL/compliance (EEOC, EU AI Act treats this as high-risk). The honest interview answer stresses fairness, auditing, and human control as much as the ML.",
         tags=["resume-screening", "bias", "fairness", "human-in-the-loop", "applied", "ai"],
         example="A hiring tool ranks 500 applicants by semantic match to the job; before use, it's audited by feeding identical resumes with only the name/gender swapped - if scores differ, that's bias to fix. Humans review the shortlist and make all reject/advance decisions.",
         difficulty="Medium",
         frequency="Commonly asked as a 'responsible AI' design - interviewers specifically look for bias, fairness, and human-oversight awareness, not just the ML.",
         mnemonic="Parse + embed + LLM rank -> shortlist WITH explanations. But the real answer is SAFEGUARDS: strip protected attributes/proxies, audit for disparate impact (swap-name test), human-in-the-loop, transparency, legal (high-risk). 'AI assists; humans decide; audit for bias.'"),
    dict(cat="ai_applied", title="Design an AI tutor",
         answer="In plain words: build a patient, personalized teacher that explains concepts, gives practice, checks answers, and adapts to the student's level - grounded in real curriculum so it doesn't teach wrong things. Core: RAG over trusted course materials so explanations are accurate and on-syllabus; a system prompt that sets a SOCRATIC style (guide with questions and hints rather than just handing answers); per-student MEMORY of what they know/struggle with to adapt difficulty and revisit weak spots (spaced repetition); and tools for exact tasks (a calculator/code-runner so math and code are correct, not hallucinated). Feedback: check the student's answer, explain WHY it's right/wrong, and give a tailored hint. Design points: pedagogy (don't just give the answer - scaffold), correctness (ground + tools to avoid teaching mistakes), safety/age-appropriateness and privacy for minors, motivation (encouragement, progress/streaks), and evaluation (does the student actually LEARN - measured by improvement, not just satisfaction).",
         tags=["ai-tutor", "education", "rag", "socratic", "personalization", "applied", "ai"],
         example="A student stuck on a physics problem: the tutor retrieves the relevant chapter, asks 'what forces act on the block?' (Socratic hint) instead of solving it, checks the student's free-body diagram, uses a calculator tool to verify the numbers, and notes they struggle with friction to revisit it later.",
         difficulty="Medium",
         frequency="Commonly asked applied-LLM design (big EdTech area) - tests grounding, pedagogy, personalization, and safety for a real user need.",
         mnemonic="RAG over the curriculum (accurate) + Socratic hints (don't just give answers) + per-student memory (adapt/spaced-repetition) + tools (exact math/code) + measure real LEARNING. 'Patient, grounded, guides not tells.'"),
    dict(cat="ai_applied", title="Embeddings for recommendation systems",
         answer="In plain words: recommendations are largely a similarity problem - represent users and items as vectors so 'what should I show this user?' becomes 'find items whose vectors are close to this user's.' Learn item embeddings (from content and/or co-interaction patterns - items bought/watched together end up close) and user embeddings (from their history). To recommend, look up the user's vector and do approximate nearest-neighbour search over item vectors (the two-tower + ANN pattern) for a fast candidate set, then a ranker refines. LLMs help by generating rich embeddings from item text/metadata (great for COLD-START - a brand-new item with no interactions still has a content embedding) and by understanding nuanced user intent. Concerns: cold-start (lean on content embeddings), popularity bias, freshness (re-embed new items), diversity (don't show 10 near-identical items), and evaluation (offline recall plus online A/B on engagement). It's the same retrieval machinery behind RAG, applied to products/content.",
         tags=["recommendation", "embeddings", "two-tower", "cold-start", "ann", "ai"],
         example="A streaming app embeds every show from its description + who-watched-what; a new user who watched two sci-fi films gets a user vector near sci-fi shows, and ANN search returns similar titles instantly - including a brand-new show that has no views yet but a matching content embedding (solving cold-start).",
         difficulty="Medium",
         frequency="Very commonly asked - recommendations are core at Amazon/Meta/Google/Netflix, and the embedding+ANN framing is standard.",
         mnemonic="Users and items as vectors; recommend = nearest items to the user (two-tower + ANN). LLM/content embeddings solve COLD-START (new items still have a vector). Watch popularity bias + diversity. 'Same retrieval trick as RAG, for products.'"),
    dict(cat="ai_llm", title="Data contamination in LLM benchmarks",
         answer="In plain words: if a model saw the test questions during training, its benchmark score is inflated and meaningless - like a student who memorized the exam. Data contamination is when benchmark/test data leaks into the massive pretraining corpus (which is scraped from the web, where benchmarks and their answers also live). It makes models look better than they are and makes comparisons unfair. Detecting it is hard: check for verbatim overlap between training data and test sets, look for suspiciously high confidence/perfect recall on specific test items, or use 'canary' strings benchmark authors embed to trace leakage. Mitigations: use FRESH/held-out benchmarks created AFTER a model's training cutoff, private test sets, dynamically generated problems, and report contamination analyses. It's a big reason to be skeptical of headline benchmark numbers and to value evaluation on your OWN recent, private data. Related: models can also overfit to benchmark STYLE even without exact leakage.",
         tags=["data-contamination", "benchmarks", "evaluation", "llm", "ai"],
         example="A model scores 95% on a coding benchmark, but many of those exact problems (with solutions) were on the web in its training data - so the score reflects memorization, not skill. Re-tested on brand-new problems written after its cutoff, it scores 70% - the honest number.",
         difficulty="Medium",
         frequency="Asked in ML-research/evaluation discussions - 'why might a high benchmark score be misleading?'",
         mnemonic="If the model trained on the test, the score is fake (memorized the exam). Web-scraped pretraining sucks in benchmarks. Trust fresh/private/post-cutoff evals + contamination checks. 'A leaked test proves nothing.'"),
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

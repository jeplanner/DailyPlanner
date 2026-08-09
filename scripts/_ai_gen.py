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
    dict(cat="ai_llm", title="Hybrid search (keyword + vector) and re-ranking",
         answer="In plain words: pure vector search finds things by meaning but can miss exact terms (a product code, a name); keyword search nails exact matches but misses paraphrases. Hybrid search runs BOTH and combines them, then a re-ranker sorts the merged shortlist by true relevance. Keyword search (BM25) scores exact/lexical overlap; vector (semantic) search scores meaning via embeddings. You fuse their result lists (e.g. Reciprocal Rank Fusion) to get the best of both. Then a cross-encoder RE-RANKER takes the top ~50 candidates and, unlike the fast bi-encoder used for retrieval, reads the query and each document TOGETHER to produce a precise relevance score - slow but accurate, so you only run it on the shortlist. This two-stage 'retrieve broadly, re-rank precisely' is a major quality lever in RAG.",
         tags=["hybrid-search", "bm25", "re-ranking", "cross-encoder", "rag", "ai"],
         example="Query 'error code E-4021 on model X100': vector search alone might return general troubleshooting; hybrid search also surfaces the exact doc mentioning 'E-4021' (keyword hit), and the re-ranker floats the most on-point page to the top.",
         difficulty="Medium",
         frequency="Commonly asked in RAG/search design rounds - shows you know retrieval quality is a two-stage problem, not just 'embed and match'.",
         mnemonic="Keyword (exact) + Vector (meaning) -> fuse the lists -> re-rank the top-k with a slow-but-accurate cross-encoder. 'Retrieve broadly, re-rank precisely.'"),
    dict(cat="ai_llm", title="Cosine similarity vs dot product vs Euclidean distance",
         answer="In plain words: these are three ways to measure how 'close' two embedding vectors are, and the right one depends on whether magnitude matters. COSINE similarity measures the ANGLE between vectors (ignores length) - so 'similar direction = similar meaning' regardless of vector size; it's the default for text embeddings. DOT PRODUCT multiplies magnitude AND angle, so longer vectors score higher - useful when magnitude encodes something (e.g. popularity or confidence) and common because it's fast; on NORMALIZED vectors dot product equals cosine. EUCLIDEAN (L2) distance is straight-line distance - smaller means closer; it cares about magnitude too. Practical rule: normalize embeddings and use cosine/dot for semantic search; make sure your vector DB's metric matches how the embedding model was trained (using the wrong metric quietly wrecks results).",
         tags=["cosine-similarity", "dot-product", "euclidean", "embeddings", "vector-search", "ai"],
         example="Two docs about 'refunds': one short, one long, both on-topic. Cosine sees them as very similar (same direction); raw Euclidean might call them far apart just because the longer doc's vector is bigger. That's why text search normalizes and uses cosine.",
         difficulty="Medium",
         frequency="Commonly asked alongside embeddings/vector-DB questions - 'which distance metric and why?' is a frequent follow-up.",
         mnemonic="Cosine = angle only (length-blind, text default). Dot = angle x length (magnitude matters; = cosine if normalized). Euclidean = straight-line gap. Match the metric to how the model was trained."),
    dict(cat="ai_llm", title="HNSW (how vector databases search fast)",
         answer="In plain words: finding the exact nearest vectors among millions is too slow, so vector DBs use HNSW - a clever graph you can hop across to reach a query's neighbours in a few steps instead of scanning everything. HNSW (Hierarchical Navigable Small World) builds a multi-LAYER graph: the top layer has a few nodes with long-range links (for big jumps across the space), and each lower layer adds more nodes with shorter links (for fine-grained local search). To query, you enter at the top, greedily hop toward the query, then drop a layer and refine, repeating down to the bottom - like zooming in on a map from country to street. It gives approximate nearest neighbours in roughly O(log n) time with high recall. Knobs: M (links per node) and efSearch (how hard to search) trade recall against speed/memory.",
         tags=["hnsw", "ann", "vector-database", "index", "semantic-search", "ai"],
         example="Searching 10M product embeddings: a brute-force scan checks all 10M; HNSW hops through its graph and finds the top-10 nearest in a few dozen comparisons, so semantic search answers in milliseconds. Pinecone, Weaviate, Milvus and FAISS all offer HNSW.",
         difficulty="Hard",
         frequency="Increasingly asked in search/infra and GenAI-platform interviews - 'how does approximate nearest-neighbour search actually work?'",
         mnemonic="A zoomable map: top layer = big jumps, lower layers = fine steps. Greedily hop toward the query, drop a layer, refine. ~O(log n) approx-NN. Tune M (links) and efSearch (effort)."),
    dict(cat="ai_llm", title="KV-cache (why LLM generation speeds up after the first token)",
         answer="In plain words: when an LLM generates text one token at a time, it would be hugely wasteful to re-process the entire sentence for every new token - the KV-cache stores past work so each new token is cheap. In attention, every token computes KEY and VALUE vectors. Since generation is left-to-right and past tokens don't change, the model CACHES their keys and values; to produce the next token it only computes the new token's query and attends against the cached keys/values, instead of recomputing all of them. This turns per-token cost from growing-with-length into roughly constant, making generation much faster. The catch: the cache grows with sequence length and batch size and eats GPU MEMORY - which is why long contexts and many concurrent users are memory-bound, and why tricks like paged / efficient KV-cache management (e.g. vLLM's PagedAttention) matter for serving.",
         tags=["kv-cache", "inference-optimization", "attention", "serving", "llm", "ai"],
         example="Generating a 500-token answer without a KV-cache re-runs attention over all prior tokens each step (slow, quadratic-ish); with the cache, each new token only attends to stored keys/values - so tokens stream out quickly, but the cache for a long chat can use gigabytes of GPU memory.",
         difficulty="Hard",
         frequency="Commonly asked in ML-inference/serving and NVIDIA-style interviews - 'why is the first token slow but the rest fast, and what limits throughput?'",
         mnemonic="Don't redo old work: cache past tokens' Keys and Values, so each new token is cheap. Speed up, but the cache grows with length x batch and hogs GPU memory. 'Remember the past, only compute the new.'"),
    dict(cat="ai_llm", title="Positional encoding (how transformers know word order)",
         answer="In plain words: attention by itself treats a sentence as a BAG of words - it has no built-in sense of order, so 'dog bites man' and 'man bites dog' would look the same. Positional encoding injects each token's POSITION into its representation so order matters. The original Transformer added fixed SINUSOIDAL patterns (different frequencies) to token embeddings. Modern LLMs mostly use ROPE (Rotary Position Embedding), which ROTATES the query/key vectors by an angle proportional to position - elegantly encoding RELATIVE distance (how far apart two tokens are), which generalizes better to longer sequences. ALiBi instead adds a distance-based penalty to attention scores. Position handling is central to LONG-CONTEXT: techniques that stretch/interpolate RoPE let models extend their context window beyond what they trained on.",
         tags=["positional-encoding", "rope", "alibi", "transformer", "long-context", "ai"],
         example="Without positional info, a translator couldn't tell 'the cat sat on the mat' from 'the mat sat on the cat'. RoPE rotates each token's vectors by its position so 'cat' at position 2 and 'cat' at position 7 are distinguishable, and the model learns their relative distance.",
         difficulty="Hard",
         frequency="Commonly asked in transformer-depth interviews (research/applied-scientist) - 'how does a transformer know word order?' and 'what is RoPE?'",
         mnemonic="Attention is order-blind (a bag of words), so stamp each token with its POSITION. Sinusoidal (original) -> RoPE (rotate by position, encodes RELATIVE distance, great for long context). 'Give every word a seat number.'"),
    dict(cat="ai_llm", title="Prompt engineering patterns that actually work",
         answer="In plain words: how you ASK changes what you get - a few reliable patterns dramatically improve LLM output without any training. (1) Be SPECIFIC about role, task, format, and constraints ('You are a senior editor. Rewrite in <=100 words, bullet points.'). (2) FEW-SHOT: show 1-3 examples of input->output so the model copies the pattern. (3) DELIMITERS: wrap inputs in clear markers (triple backticks, XML tags) so the model separates instructions from data (also helps against prompt injection). (4) CHAIN-OF-THOUGHT: ask it to reason step by step for hard problems. (5) Ask for STRUCTURED output (JSON with a schema) when a program will parse it. (6) Give it an OUT ('say I DON'T KNOW if unsure') to cut hallucination. (7) Iterate: test on real cases and refine. Prompting is the cheapest, fastest lever - try it before RAG or fine-tuning.",
         tags=["prompt-engineering", "few-shot", "prompting", "structured-output", "ai"],
         example="Bad: 'summarize this'. Good: 'Summarize the text between triple backticks in exactly 3 bullet points for a busy executive; if a fact is missing, do not invent it. ```<text>```' - specific role, format, delimiter, and an anti-hallucination out.",
         difficulty="Easy",
         frequency="Very commonly asked as a practical 'have you actually built with LLMs?' check - naming concrete patterns (few-shot, delimiters, structured output) signals real experience.",
         mnemonic="Be Specific, show Examples (few-shot), use Delimiters, ask for step-by-step, request JSON, and give an 'I don't know' out. Prompt first - it's the cheapest lever."),
    dict(cat="ai_llm", title="Structured output / JSON mode from LLMs",
         answer="In plain words: to plug an LLM into software you usually need machine-readable output (JSON), not prose - structured output makes the model return data your code can reliably parse. Approaches, weakest to strongest: (1) just ASK for JSON in the prompt (works often, but the model may add prose or malformed JSON). (2) JSON MODE - the API guarantees syntactically valid JSON. (3) SCHEMA-CONSTRAINED / function-calling - you give a schema and the decoder is constrained so the output MUST match the required fields and types (most reliable). Under the hood, constrained decoding masks the model's next-token choices to only those allowed by the grammar/schema. Always still VALIDATE the parsed object (types, ranges, required fields) and handle failures with a retry. This is what turns an LLM from a chatbot into a dependable component of a pipeline.",
         tags=["structured-output", "json-mode", "function-calling", "constrained-decoding", "applied", "ai"],
         example="An invoice extractor must return {vendor, date, total}. Prompt-only JSON sometimes wraps it in 'Here is the JSON:'; schema-constrained output forces exactly {vendor: str, date: str, total: number}, which your code parses without brittle string-scraping.",
         difficulty="Medium",
         frequency="Commonly asked in applied-AI/product interviews - 'how do you get reliable, parseable output from an LLM?'",
         mnemonic="Prose won't parse - demand JSON. Ladder: ask for JSON -> JSON mode (valid syntax) -> schema-constrained/function-calling (right fields/types). Then STILL validate + retry. 'Make the LLM speak your code's language.'"),
    dict(cat="ai_applied", title="Semantic caching for LLM apps",
         answer="In plain words: LLM calls are slow and cost money, and users often ask the SAME thing in different words - a semantic cache reuses a previous answer when a new question MEANS the same as an old one, not just when it's an exact string match. A normal cache keys on the exact text, so 'reset my password' and 'how do I change my password?' miss each other. A semantic cache embeds the query and looks for a past query whose embedding is close enough (above a similarity threshold); if found, it returns the cached answer instantly and for free. Benefits: big latency and cost savings on repetitive traffic. Risks: a too-loose threshold returns a subtly wrong answer for a different question, so you tune the threshold carefully, scope caches per user/context where needed, and expire entries when the underlying data changes.",
         tags=["semantic-cache", "caching", "cost-optimization", "embeddings", "applied", "ai"],
         example="A support bot gets 'reset password', 'forgot my password', 'change password' hundreds of times a day. A semantic cache embeds each, matches them to one cached answer, and serves it in ~10ms at zero LLM cost - instead of paying for the same generation over and over.",
         difficulty="Medium",
         frequency="Commonly asked in LLM cost/latency-optimization discussions - a practical lever that shows production thinking.",
         mnemonic="Cache by MEANING, not exact text: embed the query, reuse a past answer if similar enough. Huge cost/latency win on repetitive questions - but tune the threshold or you'll serve a close-but-wrong answer."),
    dict(cat="ai_llm", title="Multimodal models and CLIP",
         answer="In plain words: multimodal models handle more than text - images, audio, video - often by mapping different kinds of data into ONE shared meaning-space so the model can relate a picture to words. CLIP is the classic example: it trains an image encoder and a text encoder TOGETHER on hundreds of millions of (image, caption) pairs with a contrastive objective - pull the matching image and caption embeddings together, push mismatched ones apart. The result is a shared space where a photo of a dog and the text 'a dog' land close, enabling ZERO-SHOT image classification (compare an image's embedding to candidate label texts), image search by text, and grounding for image-generation and vision-language models. Modern multimodal LLMs (GPT-4o, Gemini) extend this idea to accept and reason over mixed text+image (+audio) inputs in one model.",
         tags=["multimodal", "clip", "contrastive-learning", "vision-language", "embeddings", "ai"],
         example="With CLIP you classify an image with NO task-specific training: embed the photo, embed the texts 'a cat'/'a dog'/'a car', and pick the closest - it works because image and text share one embedding space. The same trick powers 'search my photos for beach sunsets'.",
         difficulty="Medium",
         frequency="Commonly asked as multimodal AI rises - 'how do image and text end up comparable?' -> CLIP-style contrastive training.",
         mnemonic="Put images AND text in ONE shared space (CLIP: pull matching pairs together, push mismatches apart). Then a photo and its caption are 'close' - enabling zero-shot labels and text-to-image search. 'One meaning-space for eyes and words.'"),
    dict(cat="ai_llm", title="Diffusion models (how AI generates images)",
         answer="In plain words: diffusion models learn to create images by REVERSING a noising process - start from pure random static and repeatedly 'denoise' it, step by step, until a clear image emerges, guided by your text prompt. Training: take real images, gradually add Gaussian NOISE over many steps until they're static, and train a network to predict/remove the noise at each step. Generation (sampling): start from random noise and run the learned denoiser backwards many steps, each step nudging the noise toward something realistic; a text prompt CONDITIONS the denoising (via cross-attention to the prompt's embedding) so the result matches 'an astronaut riding a horse'. Modern systems (Stable Diffusion) do this in a compressed LATENT space for speed. It's the tech behind text-to-image and increasingly video.",
         tags=["diffusion", "image-generation", "text-to-image", "generative", "ai"],
         example="Stable Diffusion turning 'a cozy cabin in the snow at night' into an image: it begins with noise and denoises ~20-50 steps, the prompt steering each step, until a coherent snowy cabin appears - the reverse of slowly adding static to a real photo.",
         difficulty="Medium",
         frequency="Commonly asked in generative-AI/vision interviews - 'how do image generators work?' is a favorite as text-to-image goes mainstream.",
         mnemonic="Learn to un-noise: training adds static to images; generation starts from static and denoises step-by-step toward a picture, steered by your prompt. 'Sculpt an image out of noise.'"),
    dict(cat="ai_applied", title="LLM cost and latency optimization",
         answer="In plain words: LLMs are slow and priced per token, so productionizing them is largely about getting the same quality for less time and money. Levers: (1) RIGHT-SIZE the model - use the smallest model that passes your eval; route easy queries to a cheap model and only hard ones to a big one (a 'cascade'/router). (2) SHRINK tokens - trim the prompt, retrieve fewer/tighter RAG chunks, cap output length. (3) CACHE - exact and SEMANTIC caching for repeats; PROMPT/context caching to reuse a fixed system prompt cheaply. (4) BATCH - continuous batching on the server packs many requests together for GPU throughput. (5) QUANTIZE / distill the model for cheaper inference. (6) STREAM tokens so perceived latency drops even if total time is similar. (7) Do work OFFLINE/async when real-time isn't needed. Measure cost-per-request and p95 latency, then attack the biggest contributor.",
         tags=["cost-optimization", "latency", "serving", "caching", "applied", "ai"],
         example="A support copilot cuts cost 5x: route FAQ-like questions to a small quantized model, use a semantic cache for repeats, retrieve 3 tight chunks instead of 10, cap answers to 200 tokens, and stream the response so it FEELS instant - reserving the big model for genuinely hard tickets.",
         difficulty="Medium",
         frequency="Very commonly asked in applied-AI/product-engineering rounds - 'this LLM feature is too slow/expensive; how do you fix it?'",
         mnemonic="Right-size the model, shrink the tokens, cache the repeats, batch on the GPU, quantize, and stream. Route easy->cheap, hard->big. Measure cost/request + p95, kill the biggest cost first."),
    dict(cat="ai_applied", title="Design a natural-language-to-SQL system",
         answer="In plain words: let non-technical users ask questions in English and have an LLM translate them into SQL, run it, and return the answer - powerful but risky, so the design is about accuracy and safety. Pipeline: (1) give the LLM the SCHEMA (tables, columns, types, relationships) plus a few example question->SQL pairs (few-shot), and often a description of each table. (2) Ask it to generate SQL for the user's question (structured output). (3) VALIDATE before running: parse the SQL, allow only SELECT (no writes/drops), enforce row limits and timeouts, and run as a READ-ONLY user on a replica. (4) Execute and return results, optionally with the SQL shown for transparency. (5) Handle errors by feeding the DB error back to the LLM to self-correct. Concerns: schema too big for the context (retrieve relevant tables via embeddings), ambiguous questions (ask to clarify), joins/aggregations correctness (evaluate on a labelled question set), and SQL-injection/permission safety.",
         tags=["text-to-sql", "llm", "structured-output", "applied", "ai", "system-design"],
         example="User asks 'top 5 customers by revenue last quarter'. The system feeds the LLM the orders/customers schema + examples, gets 'SELECT c.name, SUM(o.total) ... GROUP BY ... ORDER BY ... LIMIT 5', validates it's a read-only SELECT, runs it on a replica, and returns the table - with the generated SQL shown so an analyst can verify.",
         difficulty="Medium",
         frequency="Commonly asked as an applied-LLM design question - tests grounding (schema), structured output, and especially SAFETY (read-only, validation).",
         mnemonic="Schema + few-shot -> LLM writes SQL -> VALIDATE (SELECT-only, limits, read-only replica) -> run -> on error, feed it back to self-correct. 'Translate English to SQL, but sandbox it.'"),
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

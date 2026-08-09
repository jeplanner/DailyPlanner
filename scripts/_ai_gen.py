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
    dict(cat="ai_llm", title="What is a Large Language Model (LLM)?",
         answer="In plain words: an LLM is a giant next-word predictor. Trained on enormous text, it learns to guess the next token given everything so far - and doing that well turns out to require real 'understanding' of grammar, facts, and reasoning. A Large Language Model is a transformer neural network with billions of parameters, PRETRAINED on huge text corpora with a simple self-supervised objective (predict the next token), then usually FINE-TUNED / aligned (instruction tuning + RLHF) to follow instructions helpfully and safely. At inference it generates text one token at a time, each token conditioned on the prompt plus what it has produced so far (autoregressive). Its knowledge is frozen at training time (the 'knowledge cutoff'), it has a finite CONTEXT WINDOW, and it can HALLUCINATE (state false things confidently).",
         tags=["llm", "language-model", "transformer", "genai", "ai"],
         example="GPT-4, Claude, Llama and Gemini are LLMs. Given 'The capital of France is', the model assigns the highest next-token probability to ' Paris' and emits it; feed the result back and it keeps going to write a whole paragraph.",
         difficulty="Easy",
         frequency="Very commonly asked (2024+) - a baseline concept in any AI/ML interview and increasingly in general SDE loops at Google, Meta, NVIDIA, OpenAI, Anthropic.",
         mnemonic="An LLM is 'autocomplete on steroids': a next-word guesser so good it looks like it thinks. Pretrain (learn language) -> fine-tune (follow instructions) -> generate one token at a time."),
    dict(cat="ai_llm", title="What is RAG (Retrieval-Augmented Generation)?",
         answer="In plain words: instead of hoping the model memorized a fact, you FETCH the relevant documents first and paste them into the prompt, so the model answers FROM them. RAG combines a RETRIEVER with a GENERATOR. Offline you chunk your documents, embed each chunk into a vector, and store them in a vector database. At query time you embed the user's question, retrieve the most similar chunks (semantic search), stuff those chunks into the LLM's context as grounding, and ask it to answer USING them (often 'cite your sources'). This gives the model fresh, private, or domain-specific knowledge WITHOUT retraining, cuts hallucinations (answers are grounded in retrieved text), and lets you update knowledge by just updating the index.",
         tags=["rag", "retrieval-augmented-generation", "vector-database", "embeddings", "genai", "ai"],
         example="A company support bot: the user asks 'what's our refund window?'; RAG embeds the question, retrieves the 3 most relevant policy chunks from the vector DB, and prompts the LLM: 'Using these policy excerpts, answer the question.' The bot answers '30 days' and cites the policy - no model retraining needed when the policy changes, just re-index.",
         difficulty="Medium",
         frequency="Very commonly asked - RAG is THE dominant pattern for grounding LLMs; expect it in GenAI, ML and applied-scientist interviews across product companies.",
         mnemonic="R-A-G literally: Retrieve the relevant chunks, Augment the prompt with them, Generate the grounded answer. 'Open-book exam' for the LLM."),
    dict(cat="ai_llm", title="What is MCP (Model Context Protocol)?",
         answer="In plain words: MCP is a standard 'USB port' for AI apps - one common way to plug an LLM into tools, data, and services, so you don't hand-code a custom integration for each. The Model Context Protocol (introduced by Anthropic, 2024) is an open standard that defines how an AI application (the HOST/CLIENT, e.g. Claude Desktop or an IDE) connects to external capabilities exposed by MCP SERVERS. A server can expose TOOLS (functions the model can call, like 'search_tickets'), RESOURCES (readable data/context, like files or DB rows), and PROMPTS (reusable templates). The client and server speak JSON-RPC over a transport (stdio or HTTP). Because the interface is standardized, any MCP-compatible model can use any MCP server - decoupling models from integrations the way a common protocol (USB, LSP) decouples devices from hosts.",
         tags=["mcp", "model-context-protocol", "tools", "agents", "genai", "ai"],
         example="An MCP server wraps your GitHub: it exposes tools like list_prs and create_issue. Claude (the MCP client) can then call those tools during a chat to open an issue - and the same server works with any other MCP-compatible AI app, no bespoke glue per model.",
         difficulty="Medium",
         frequency="Newer but rising fast (2024+) - increasingly asked as agent/tool-use and AI-integration questions appear; strong signal you follow current AI engineering.",
         mnemonic="MCP = a 'USB-C port for AI': one standard plug so any model connects to any tool/data source. Servers expose Tools (do things), Resources (read things), Prompts (templates)."),
    dict(cat="ai_llm", title="How does self-attention work (the Transformer core)?",
         answer="In plain words: each word looks at every other word and decides who to 'pay attention' to, then mixes in their meaning. That's how the model figures out that 'it' refers to 'the animal' and not 'the street'. Mechanically, every token is projected into three vectors: a QUERY (what I'm looking for), a KEY (what I offer), and a VALUE (what I'll pass on). For each token, you dot its query with every token's key to get relevance SCORES, scale by 1/sqrt(d_k) for stability, softmax the scores into weights that sum to 1, and take the weighted sum of VALUES - that weighted sum is the token's new, context-aware representation. MULTI-HEAD attention runs several of these in parallel (each head learns a different kind of relationship) and concatenates them. Self-attention lets every token directly reach every other token in one step (unlike RNNs), which is why Transformers capture long-range dependencies and parallelize well.",
         tags=["attention", "self-attention", "transformer", "query-key-value", "ai"],
         code='''# Single-head self-attention, numpy. ast.parse-only (illustrative).
import numpy as np

def self_attention(X, Wq, Wk, Wv):
    # X: (seq_len, d_model) token embeddings for one sequence
    Q = X @ Wq                                    # queries: what each token seeks
    K = X @ Wk                                    # keys: what each token offers
    V = X @ Wv                                    # values: what each token passes on
    d_k = Q.shape[1]
    scores = Q @ K.T / np.sqrt(d_k)               # (seq, seq) relevance, scaled
    scores = scores - scores.max(axis=1, keepdims=True)   # numerical stability
    weights = np.exp(scores)
    weights = weights / weights.sum(axis=1, keepdims=True) # softmax over keys
    return weights @ V                            # context-aware output per token''',
         complexity="Time O(seq_len^2 * d) - the quadratic cost in sequence length is why long contexts are expensive.",
         pitfalls="Forgetting the 1/sqrt(d_k) scaling (softmax saturates, gradients vanish); attending over the wrong axis; ignoring the causal mask in decoders (a token must not see the future).",
         example="For 'The animal didn't cross the street because it was tired', when encoding 'it' the attention weights put most mass on 'animal', so 'it' inherits the animal's meaning and the model resolves the pronoun correctly.",
         difficulty="Hard",
         frequency="Very commonly asked in ML/AI and applied-scientist interviews - 'explain attention' and 'why sqrt(d_k)' are classics at Google, Meta, NVIDIA, OpenAI, Anthropic.",
         mnemonic="Query asks, Key answers, Value is what you take. Score = Q.K, softmax, weighted-sum of Values. 'Each word decides who to listen to.'"),
    dict(cat="ai_llm", title="Pretraining vs Fine-tuning vs Prompting (how to adapt an LLM)",
         answer="In plain words: three ways to get an LLM to do YOUR task, from most to least effort. PRETRAINING builds the base model from scratch on trillions of tokens (self-supervised next-token prediction) - enormously expensive, done by a few labs. FINE-TUNING takes a pretrained model and trains it further on your smaller labelled/task data to specialize it (full fine-tuning updates all weights; PARAMETER-EFFICIENT methods like LoRA update a tiny fraction) - moderate cost, changes the weights, good when you need consistent behavior or new skills. PROMPTING (in-context learning) changes NOTHING in the weights - you just craft the input: zero-shot (instructions only), few-shot (show examples), or add retrieved context (RAG). Rule of thumb: try PROMPTING first (cheapest, instant), reach for RAG when the model lacks knowledge, and FINE-TUNE when you need a specific style/format/skill that prompting can't reliably produce.",
         tags=["fine-tuning", "prompting", "in-context-learning", "lora", "llm", "ai"],
         example="Customer-service bot: start with a good PROMPT ('You are a support agent...'); add RAG for product facts; only FINE-TUNE (e.g. LoRA on past transcripts) if you need it to consistently match your brand's exact tone and JSON format.",
         difficulty="Medium",
         frequency="Very commonly asked - 'when would you fine-tune vs use RAG vs just prompt?' is a staple GenAI design question.",
         mnemonic="Ladder of effort: Prompt (free, instant) -> RAG (add knowledge) -> Fine-tune (change the weights). Climb only as high as you must."),
    dict(cat="ai_llm", title="What is the context window, and why does it matter?",
         answer="In plain words: the context window is the model's short-term memory - the maximum amount of text (prompt + conversation + retrieved docs + its own answer) it can consider at once, measured in TOKENS. Anything beyond it is simply not seen. Because self-attention costs grow quadratically with sequence length, bigger windows are expensive in compute and memory. A finite window drives many design choices: you must FIT the system prompt, chat history, and any RAG context inside it (so you chunk/summarize/truncate); very long inputs suffer 'lost in the middle' (models attend best to the start and end); and long chats need memory strategies (summarize old turns, retrieve only relevant history). Modern models range from a few thousand to hundreds of thousands (even 1M+) tokens.",
         tags=["context-window", "tokens", "llm", "long-context", "ai"],
         example="With an 8k-token window, a 20-page document (~15k tokens) will not fit - so RAG retrieves only the few relevant chunks instead of pasting the whole doc. In a long chat, once history exceeds the window you summarize older turns to make room.",
         difficulty="Easy",
         frequency="Commonly asked - context-window limits underlie RAG, chunking and long-conversation design questions.",
         mnemonic="It's the model's desk space, measured in tokens: only what's ON the desk gets used. Too big to fit -> chunk, summarize, or retrieve just the relevant part."),
    dict(cat="ai_llm", title="Vector database & semantic search",
         answer="In plain words: a vector database finds things by MEANING, not exact keywords. You convert text (or images) into embeddings - lists of numbers where similar meanings are near each other - and the DB quickly finds the nearest vectors to your query vector. Because exact nearest-neighbor search is slow at scale, vector DBs use APPROXIMATE nearest-neighbor (ANN) indexes (HNSW graphs, IVF, product quantization) that trade a tiny bit of accuracy for huge speed. This powers semantic search, RAG retrieval, recommendations, and deduplication. Key knobs: the embedding model (quality of 'meaning'), the distance metric (cosine/dot/Euclidean), and the ANN index parameters (recall vs latency).",
         tags=["vector-database", "semantic-search", "embeddings", "ann", "rag", "ai"],
         example="Search 'how do I return an item?' and semantic search also surfaces a doc titled 'Refund & exchange policy' - no shared keywords, but their embeddings are close. Pinecone, Weaviate, Milvus, FAISS and pgvector are common vector stores.",
         difficulty="Medium",
         frequency="Commonly asked alongside RAG - expect 'how does semantic search / ANN work?' in GenAI and search interviews.",
         mnemonic="Turn meaning into arrows; find the nearest arrows fast. Exact NN is too slow at scale, so use Approximate NN (HNSW/IVF). 'Search by meaning, not by matching letters.'"),
    dict(cat="ai_llm", title="Why do LLMs hallucinate, and how do you reduce it?",
         answer="In plain words: an LLM is trained to produce PLAUSIBLE next words, not verified true ones - so when it doesn't know, it still generates a confident, fluent guess. A hallucination is fluent output that is factually wrong or unsupported. Causes: the model has no notion of truth (only likelihood), its knowledge is frozen and incomplete, it fills gaps to stay fluent, and it can't reliably say 'I don't know.' Reductions: GROUNDING with RAG (give it the facts and tell it to answer only from them + cite), lower the temperature for factual tasks, ask for citations and verify them, add guardrails/validators (check claims against a source), use tool-calling for exact operations (calculator, DB, code), fine-tune for honesty/refusal, and design the UX to show sources so users can check. You reduce hallucination; you don't fully eliminate it.",
         tags=["hallucination", "grounding", "rag", "reliability", "llm", "ai"],
         example="Ask an ungrounded model for a citation and it may invent a real-looking but fake paper title and DOI. With RAG ('answer only from these retrieved sources and quote them'), it instead answers from real documents or says the info isn't in the sources.",
         difficulty="Medium",
         frequency="Very commonly asked - 'why do LLMs hallucinate and how would you mitigate it?' is a flagship GenAI reliability question.",
         mnemonic="It's a fluent guesser, not a fact-checker - it says something plausible when it doesn't know. Fix by GROUNDING it (RAG + cite), lowering temperature, and verifying with tools."),
    dict(cat="ai_applied", title="Design a RAG-powered document Q&A chatbot",
         answer="In plain words: build a bot that answers questions about YOUR documents by retrieving the relevant parts and letting an LLM answer from them. Pipeline. INGEST (offline): load docs, CHUNK them (e.g. 300-800 tokens with overlap so context isn't cut mid-idea), embed each chunk, store vectors + metadata in a vector DB. QUERY (online): embed the user's question, retrieve top-k similar chunks (optionally re-rank them), build a prompt = system instructions + retrieved chunks + question, call the LLM asking it to answer ONLY from the chunks and cite them, then return the answer with sources. Concerns: chunking strategy, retrieval quality (recall), the context-window budget, prompt-injection from documents, latency (cache embeddings + answers), cost (smaller model + fewer chunks), evaluation (faithfulness + answer relevance), and freshness (re-index on document changes).",
         tags=["rag", "chatbot", "vector-database", "genai", "applied", "ai", "system-design"],
         example="An internal 'ask the handbook' bot: 500 HR PDFs are chunked and embedded once; an employee asks 'how many sick days do I get?', the bot retrieves the 3 most relevant handbook chunks, and the LLM answers '10 days per year' with a link to the exact policy section.",
         difficulty="Medium",
         frequency="Very commonly asked - the canonical GenAI system-design question at product companies building AI features.",
         mnemonic="Two phases: INGEST (chunk -> embed -> store) offline, QUERY (embed -> retrieve -> augment -> generate -> cite) online. Ground it, cite it, cache it."),
    dict(cat="ai_applied", title="What is an AI agent (tool use & the ReAct loop)?",
         answer="In plain words: an agent is an LLM that can DO things, not just talk - it decides which tool to use, uses it, looks at the result, and repeats until the task is done. Instead of answering in one shot, the model runs a loop: REASON about the goal, choose an ACTION (call a tool like web-search, a calculator, code execution, or an API), OBSERVE the tool's result, and continue - the 'ReAct' (Reason+Act) pattern. Tools are exposed to the model (increasingly via standards like MCP) with descriptions the model reads to decide when to call them. Agents can plan multi-step tasks, use memory, and self-correct. Risks to design for: getting stuck in loops, calling the wrong tool, cost/latency of many LLM calls, and safety (a tool that can act in the real world needs guardrails and approvals).",
         tags=["agents", "tool-use", "react", "mcp", "genai", "applied", "ai"],
         example="'Book me a table for 4 tomorrow': the agent reasons it needs availability -> calls a restaurant API (action) -> sees 7pm is open (observation) -> reasons that fits -> calls the booking tool -> confirms. Each step is an LLM decision plus a tool call.",
         difficulty="Medium",
         frequency="Rising fast - agent/tool-use design and 'how would you build an agent?' are increasingly common as AI products adopt agents.",
         mnemonic="Agent = LLM + tools + a loop. ReAct: Reason -> Act (call a tool) -> Observe -> repeat until done. 'A model with hands, not just a mouth.'"),
    dict(cat="ai_applied", title="How do you evaluate an LLM / GenAI system?",
         answer="In plain words: unlike a classifier, there's often no single 'correct' output, so you measure quality along several axes with a mix of automatic and human checks. For RAG: FAITHFULNESS (is the answer supported by the retrieved context, i.e. not hallucinated?), ANSWER RELEVANCE (does it address the question?), and CONTEXT/RETRIEVAL quality (did we retrieve the right chunks - recall/precision@k?). For generation quality: reference-based metrics (BLEU/ROUGE for summarization/translation, exact-match/F1 for QA), and increasingly LLM-AS-A-JUDGE (a strong model scores outputs against a rubric) plus human eval for nuanced tasks. Also track task success rate, latency, cost per query, and safety/toxicity. Best practice: build a fixed EVALUATION SET of representative queries with expected behavior, run it on every change (like unit tests), and watch for regressions.",
         tags=["evaluation", "llm-eval", "rag", "llm-as-judge", "genai", "ai"],
         example="A support bot's eval set has 200 real questions with ideal answers/sources; each release you auto-score faithfulness and relevance (LLM-as-judge), measure retrieval recall@5, and spot-check 20 by hand - if faithfulness drops from 0.92 to 0.85, you block the release.",
         difficulty="Medium",
         frequency="Commonly asked - 'how would you evaluate this LLM feature?' is a favorite because naive candidates forget it entirely.",
         mnemonic="No single right answer, so score multiple axes: Faithful (grounded?), Relevant (on-topic?), Retrieved-right (recall@k?), plus cost/latency/safety. Build an eval SET and treat it like unit tests."),
    dict(cat="ai_llm", title="What is fine-tuning with LoRA (parameter-efficient tuning)?",
         answer="In plain words: instead of retraining all of an LLM's billions of weights (expensive, storage-heavy), LoRA freezes the original model and trains only a tiny pair of small matrices per layer - getting most of the benefit for a fraction of the cost. LoRA (Low-Rank Adaptation) is based on the observation that the WEIGHT UPDATE needed to adapt a model is low-RANK, so it can be approximated by the product of two skinny matrices A (d x r) and B (r x d) with a small rank r (e.g. 8-64). You freeze the pretrained weights W and learn only A and B; the effective weight becomes W + BA. This slashes trainable parameters by ~100-1000x, needs far less memory, trains fast, and produces tiny 'adapter' files you can swap per task (many adapters over one base model). QLoRA adds 4-bit quantization of the base to shrink memory further.",
         tags=["lora", "fine-tuning", "peft", "quantization", "llm", "ai"],
         example="Adapting a 7B model to your company's writing style: full fine-tuning updates 7B weights (huge GPU + a 14GB copy per task); LoRA trains ~10M adapter weights (a few MB file) on one GPU in hours, and you keep one base model with many swappable adapters.",
         difficulty="Hard",
         frequency="Commonly asked in ML-engineer/applied-scientist interviews as LLM fine-tuning became routine - 'how would you fine-tune cheaply?' -> LoRA/QLoRA.",
         mnemonic="Freeze the giant model; learn a small 'diff' as two skinny matrices (low rank). Big adaptation, tiny cost. QLoRA = LoRA + a 4-bit-quantized base to fit on one GPU."),
    dict(cat="ai_llm", title="Temperature, top-k and top-p (controlling LLM output)",
         answer="In plain words: these knobs control how RANDOM vs SAFE the model's word choices are. At each step the model has a probability over next tokens; sampling settings reshape that choice. TEMPERATURE scales the sharpness: low (~0) makes it nearly deterministic and picks the most likely token (good for facts/code); high (>1) flattens the distribution for more varied, creative (and riskier) output. TOP-K sampling restricts choices to the k most likely tokens. TOP-P (nucleus) sampling keeps the smallest set of tokens whose probabilities sum to p (e.g. 0.9), adapting how many options are considered to the context. You typically combine them: low temperature + modest top-p for factual/deterministic tasks; higher temperature for brainstorming.",
         tags=["temperature", "sampling", "top-p", "top-k", "llm", "ai"],
         example="Generating code or a factual answer: temperature 0 (or ~0.2) so it reliably picks the best token. Writing marketing taglines: temperature 0.9 + top-p 0.95 so it explores creative wordings instead of the safest, blandest one.",
         difficulty="Easy",
         frequency="Commonly asked - a practical 'do you actually use LLMs?' check in GenAI interviews.",
         mnemonic="Temperature = creativity dial (0 = safe/factual, high = wild/creative). Top-k = 'pick from the k best'; Top-p = 'pick from the smallest set covering p% probability.' Facts -> low; brainstorming -> high."),
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

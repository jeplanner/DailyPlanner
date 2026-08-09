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
    dict(cat="ai_llm", title="Speculative decoding (faster LLM generation)",
         answer="In plain words: generating one token at a time is slow because each token needs a full pass through a huge model. Speculative decoding uses a small, fast 'draft' model to GUESS several next tokens, then the big model CHECKS them all in one pass - accepting the guesses it agrees with, so you get multiple tokens for roughly the cost of one big-model step. The draft model proposes k tokens cheaply; the target (big) model runs once over all k in parallel and, token by token, keeps each guess that matches what it would have produced and stops at the first mismatch (then produces the correct token itself). Because the outputs are verified by the big model, quality is IDENTICAL to normal decoding - it's a pure speedup (often 2-3x) with no accuracy loss. Works best when the draft model agrees often (easy, predictable text).",
         tags=["speculative-decoding", "inference-optimization", "latency", "serving", "llm", "ai"],
         example="A 1B draft model guesses 'the quick brown fox'; the 70B target verifies all four words in one forward pass, accepts 'the quick brown', rejects 'fox' (it wanted 'dog'), emits 'dog' - so 3-4 tokens came out in one big-model step instead of one.",
         difficulty="Hard",
         frequency="Asked in ML-inference/serving and NVIDIA-style interviews - 'how do you speed up generation without hurting quality?'",
         mnemonic="Small model DRAFTS several tokens, big model CHECKS them in one pass, keep the matches. Same quality, 2-3x faster. 'Guess ahead, verify in bulk.'"),
    dict(cat="ai_llm", title="FlashAttention (memory-efficient attention)",
         answer="In plain words: standard attention builds a giant scores matrix (every token vs every token) and writes it to slow GPU memory, which is the real bottleneck - FlashAttention computes the same result WITHOUT ever storing that full matrix, by processing it in tiles that stay in fast on-chip memory. The insight: attention is memory-bound, not compute-bound - the cost is shuffling the huge N-by-N matrix between the GPU's fast SRAM and slow HBM. FlashAttention tiles the computation, streams blocks through on-chip memory, and uses an online-softmax trick to accumulate the result correctly without materializing the whole matrix. Result: same exact output, but much less memory (linear instead of quadratic in sequence length for the intermediate) and 2-4x faster - which is a big enabler of longer context windows. It's an IO-aware algorithm: optimize for memory movement, not just FLOPs.",
         tags=["flashattention", "attention", "gpu", "inference-optimization", "long-context", "ai"],
         example="Training with 8k-token sequences, plain attention allocates a 8k x 8k scores matrix per head (huge, slow); FlashAttention never stores it fully - it tiles and streams - so the same model trains faster and fits longer sequences on the same GPU.",
         difficulty="Hard",
         frequency="Asked in ML-systems/GPU-performance interviews (esp. NVIDIA, infra teams) - 'why is attention slow and how is it optimized?'",
         mnemonic="Attention is memory-bound, not compute-bound. Don't store the giant scores matrix - TILE it through fast on-chip memory with online softmax. Same answer, less memory, 2-4x faster. 'IO-aware attention.'"),
    dict(cat="ai_applied", title="Continuous batching (serving many LLM requests)",
         answer="In plain words: GPUs are efficient only when kept busy with big batches, but LLM requests arrive at different times and finish at different lengths - continuous batching keeps the GPU packed by adding and removing requests from the running batch every step, instead of waiting for a whole fixed batch to finish. Naive (static) batching groups N requests, runs them together, and can't start new ones until ALL finish - so a fast request waits for the slowest, wasting the GPU. Continuous (a.k.a. in-flight/iteration-level) batching, used by vLLM and TensorRT-LLM, treats generation step-by-step: after each token, completed requests leave and queued ones join, so the batch is always full. Combined with efficient KV-cache management (PagedAttention), it dramatically raises throughput (tokens/sec served) and lowers cost per request. It's the key trick behind cheap, high-throughput LLM serving.",
         tags=["continuous-batching", "serving", "throughput", "vllm", "applied", "ai"],
         example="10 users hit a chatbot; one asks for a word, another for an essay. Static batching makes the short request wait for the essay to finish. Continuous batching lets the short one leave immediately and a new request take its slot - keeping the GPU ~full and roughly doubling throughput.",
         difficulty="Hard",
         frequency="Asked in ML-serving/infra interviews - 'how do you serve many LLM users cheaply and with high throughput?'",
         mnemonic="Keep the GPU always full: add/remove requests EVERY step instead of waiting for a fixed batch to all finish. Short requests don't wait for long ones. vLLM's trick for cheap serving. 'Rolling batch, never idle.'"),
    dict(cat="ai_applied", title="Agent memory (short-term vs long-term)",
         answer="In plain words: an AI agent needs to remember things - within a task (what it just did) and across sessions (what it learned about you) - but the context window is small and forgetful, so agents use explicit MEMORY systems. SHORT-TERM (working) memory is the current context window: the running conversation and recent tool results; when it fills up you SUMMARIZE older turns to make room. LONG-TERM memory lives OUTSIDE the model, usually in a vector store: you save important facts/interactions as embeddings and RETRIEVE the relevant ones into context when needed (semantic recall) - so the agent 'remembers' your preferences next week without them sitting in the prompt the whole time. Some designs add EPISODIC memory (past task traces) and PROCEDURAL memory (learned skills/tools). The pattern is: keep the window lean, offload the rest, and retrieve just-in-time.",
         tags=["agent-memory", "agents", "vector-store", "retrieval", "applied", "ai"],
         example="A personal assistant learns 'I'm vegetarian.' It stores that as a long-term memory; three weeks later you ask for dinner ideas and it retrieves that fact into context and suggests veggie recipes - even though the original conversation is long gone from the window.",
         difficulty="Medium",
         frequency="Increasingly asked in agent/GenAI design rounds - 'how does your agent remember across a long task or multiple sessions?'",
         mnemonic="Short-term = the context window (summarize when full). Long-term = a vector store outside the model (save embeddings, retrieve when relevant). 'Keep the desk clear, file the rest, fetch on demand.'"),
    dict(cat="ai_applied", title="Multi-agent systems (when many LLMs collaborate)",
         answer="In plain words: instead of one LLM doing everything, a multi-agent system splits work across several specialized agents that coordinate - like a team with a manager and workers - which can handle complex tasks better than a single overloaded prompt. Common patterns: ORCHESTRATOR-WORKER (a planner agent breaks a goal into subtasks and delegates to specialist agents, then combines results), PIPELINE (agents in sequence: researcher -> writer -> critic), and DEBATE/REVIEW (agents critique each other's output to catch errors). Benefits: separation of concerns, specialized tools/prompts per role, and self-correction via a critic. Costs and risks: many more LLM calls (cost/latency), error propagation between agents, coordination complexity, and loops that don't terminate. Rule of thumb: start with a single well-prompted agent; add more agents only when a task genuinely has distinct roles - simplicity usually wins.",
         tags=["multi-agent", "orchestration", "agents", "applied", "ai"],
         example="A 'write a market report' system: an orchestrator spawns a research agent (gathers data via web tools), a writer agent (drafts sections), and a critic agent (checks facts and flags gaps) - the orchestrator loops writer<->critic until the report passes, then returns it.",
         difficulty="Medium",
         frequency="Rising in agent-focused GenAI interviews - 'when would you use multiple agents vs one, and how do they coordinate?'",
         mnemonic="A team of specialist LLMs + a coordinator (orchestrator-worker, pipeline, or debate/critic). More power, more cost/complexity. 'Split the job into roles - but only when the job really has roles.'"),
    dict(cat="ai_llm", title="DPO vs PPO (aligning LLMs to human preferences)",
         answer="In plain words: both teach an LLM to prefer answers humans like, using preference data (pairs where a human picked the better of two answers), but they get there differently. PPO (the classic RLHF path) first trains a separate REWARD MODEL to score answers, then uses reinforcement learning (Proximal Policy Optimization) to push the LLM toward high-reward outputs, with a KL penalty to stay close to the original - powerful but complex, unstable, and compute-heavy (you juggle multiple models). DPO (Direct Preference Optimization) SKIPS the reward model and RL loop entirely: it derives a simple classification-style loss that directly increases the probability of the preferred answer and decreases the rejected one, optimized with plain gradient descent. DPO is much simpler, more stable, and cheaper, and often matches PPO quality - so it's become a popular default, though PPO/online RL can still edge ahead on some tasks.",
         tags=["dpo", "ppo", "rlhf", "alignment", "preference-optimization", "llm", "ai"],
         example="Given 50k (prompt, preferred answer, rejected answer) triples: PPO trains a reward model then runs RL against it; DPO just fine-tunes the model with a loss that says 'make the preferred answer more likely than the rejected one' - one training run, no reward model, no RL instability.",
         difficulty="Hard",
         frequency="Asked in ML/AI research and applied-scientist interviews as alignment becomes standard - 'how would you align a model, and why might you pick DPO over PPO?'",
         mnemonic="Both learn from human preference pairs. PPO = reward model + RL (powerful, complex, unstable). DPO = one simple loss, no reward model, no RL (stable, cheap, popular default). 'DPO: skip the RL, optimize preferences directly.'"),
    dict(cat="ai_llm", title="Catastrophic forgetting (and how fine-tuning can hurt)",
         answer="In plain words: when you fine-tune a model on new data, it can OVERWRITE and forget things it used to know - like cramming for one exam and forgetting last term's material. Neural nets store knowledge in shared weights, so training hard on a narrow new task shifts those weights and degrades unrelated abilities the model had. It's a real risk when fine-tuning an LLM on your niche data: it may get better at your task but worse at general reasoning, formatting, or safety. Mitigations: use PARAMETER-EFFICIENT fine-tuning (LoRA) that freezes the base and learns a small add-on, so the original knowledge is preserved; MIX in some general/original data during fine-tuning (rehearsal); use a small learning rate and few epochs; regularize toward the original weights; or avoid fine-tuning altogether and use RAG/prompting when you only need new KNOWLEDGE (not new behavior). Always evaluate on general benchmarks too, not just your task, to catch regressions.",
         tags=["catastrophic-forgetting", "fine-tuning", "lora", "continual-learning", "llm", "ai"],
         example="You fine-tune a chat model heavily on legal contracts; it now drafts clauses well but starts giving worse everyday answers and ignores formatting instructions - it 'forgot' general skills. Switching to LoRA + mixing in general data restores the balance.",
         difficulty="Medium",
         frequency="Commonly asked when fine-tuning comes up - 'what are the risks of fine-tuning and how do you avoid breaking the model?'",
         mnemonic="Train hard on new stuff -> overwrite old knowledge (cramming forgets last term). Avoid it with LoRA (freeze the base), rehearsal (mix old data), small LR, or just use RAG. 'New skill in, old skill out - unless you protect it.'"),
    dict(cat="ai_applied", title="PII redaction for LLM pipelines",
         answer="In plain words: before sending user text to an LLM (or storing it), you often must strip out personal data - names, emails, phone numbers, card numbers - to protect privacy and meet regulations, then optionally restore it in the output. A redaction pipeline: (1) DETECT PII using pattern rules (regex for emails/phones/SSNs/cards) plus an NER model or a purpose-built detector (e.g. Microsoft Presidio) for names, addresses, etc. (2) REPLACE each item with a placeholder token ('[EMAIL_1]') or a realistic fake (pseudonymization), keeping a secure mapping if you need to restore it. (3) Send the redacted text to the model. (4) Optionally RE-INSERT the real values into the model's output using the mapping. Concerns: detectors miss things (false negatives are the dangerous ones), context can re-identify people even without direct identifiers, and you must log/audit carefully. Defense-in-depth: redact, minimize what you send, and use providers with strong data agreements.",
         tags=["pii-redaction", "privacy", "security", "compliance", "applied", "ai"],
         example="A support tool logs 'Hi, I'm Jane Doe, jane@x.com, card 4111 1111 1111 1111.' The pipeline detects and swaps to 'Hi, I'm [NAME_1], [EMAIL_1], card [CARD_1]' before the LLM sees it, drafts a reply with placeholders, then re-inserts the real name for the final message to the customer.",
         difficulty="Medium",
         frequency="Asked in enterprise/regulated GenAI design rounds - 'how do you handle sensitive data when using an LLM?'",
         mnemonic="Detect (regex + NER/Presidio) -> Replace with placeholders (keep a secure map) -> send to LLM -> optionally restore. False negatives are the danger. 'Mask before you send, unmask after.'"),
    dict(cat="ai_applied", title="Design an AI coding assistant (Copilot-style)",
         answer="In plain words: build a tool that suggests code as you type and answers coding questions, grounded in your actual codebase. Two modes. INLINE COMPLETION: as the developer types, gather CONTEXT (the current file, nearby code, open tabs, cursor position), send it to a code LLM with low latency, and stream a suggestion - the hard parts are speed (must feel instant, so use a fast model, caching, and cancel stale requests), and relevant context selection (retrieve related files/functions via embeddings - 'repo-aware' completion). CHAT/AGENT mode: answer questions or make multi-file edits using RAG over the repo plus tools (read files, run tests, apply diffs). Cross-cutting concerns: fill-in-the-middle prompting (code has context on BOTH sides of the cursor), evaluation (does the suggestion compile / pass tests / get accepted?), privacy (don't leak proprietary code), guardrails (don't suggest secrets/licenses issues), and cost/latency. Measure ACCEPTANCE RATE and iteration.",
         tags=["code-assistant", "copilot", "rag", "fill-in-the-middle", "applied", "ai", "system-design"],
         example="A developer types a function signature; the assistant retrieves similar functions and the imported module's API from the repo (embeddings), prompts a fast code model with fill-in-the-middle context, and streams a completion - which the dev accepts with Tab. Acceptance rate is the north-star metric.",
         difficulty="Medium",
         frequency="Commonly asked, esp. at companies building dev tools - a rich applied-LLM design covering latency, retrieval, and evaluation.",
         mnemonic="Two modes: inline completion (fast, repo-aware context, fill-in-the-middle, stream) and chat/agent (RAG + tools over the repo). Optimize latency + context selection; measure ACCEPTANCE RATE. 'Grounded, instant, repo-aware.'"),
    dict(cat="ai_applied", title="Design a customer-support copilot",
         answer="In plain words: build an AI that helps support agents (or customers directly) resolve tickets by answering from your help docs and past tickets, and taking safe actions. Core: RAG over the knowledge base (docs, FAQs, resolved tickets) so answers are grounded and cite sources; the LLM drafts a reply the agent can edit ('human-in-the-loop' for trust). Add TOOL/function calls for real actions (look up an order, issue a refund within limits, create a ticket). Design points: GROUNDING (answer only from retrieved docs, say 'I don't know' otherwise) to avoid confidently wrong support; ESCALATION (detect frustration/complex cases and hand to a human); GUARDRAILS on actions (refund caps, verify identity, log everything); personalization from the customer's account/context; EVALUATION on a set of real tickets (resolution rate, faithfulness, CSAT); and freshness (re-index when docs/policies change). Start agent-assist (drafts for humans) before full automation.",
         tags=["support-copilot", "rag", "tool-use", "human-in-the-loop", "applied", "ai", "system-design"],
         example="A customer asks 'where's my order?'; the copilot retrieves the shipping-policy doc, calls get_order_status(order_id) for live tracking, drafts 'Your order ships tomorrow, here's the tracking...', and the agent sends it with one click - escalating to a human if the customer is angry or the case is unusual.",
         difficulty="Medium",
         frequency="Very commonly asked applied-LLM design - covers RAG, tools, safety, escalation, and evaluation in one realistic product.",
         mnemonic="RAG over docs+tickets (grounded, cite) + tools for safe actions + human-in-the-loop drafts + escalation + guardrails on actions. Measure resolution rate/CSAT. 'Assist agents first, automate later.'"),
    dict(cat="ai_applied", title="Content moderation with LLMs",
         answer="In plain words: automatically flag or block harmful content (hate, harassment, spam, self-harm, illegal) at scale, using LLMs/classifiers because humans can't review everything - but with humans in the loop for the hard calls. A layered system: fast, cheap CLASSIFIERS (or a moderation API) score every item across policy categories in real time; a threshold blocks the clearly-bad, allows the clearly-fine, and sends the UNCERTAIN middle to human reviewers. LLMs help with nuanced/contextual cases (sarcasm, coded language) and can explain WHY something violates a policy, but they're slower/costlier so you reserve them for the gray zone. Key challenges: adversarial evasion (users mask words), context (the same phrase is fine or not depending on setting), multilingual and multimodal content, fairness (avoid biased over-flagging of groups), the human cost of reviewing traumatic content, and clear appeals. Measure precision/recall per policy and tune thresholds to the cost of each error.",
         tags=["content-moderation", "safety", "classification", "human-in-the-loop", "applied", "ai"],
         example="A social platform: a fast classifier scores every post; 'kill this process' in a coding forum scores borderline for violence, so an LLM with context judges it benign and allows it, while genuine threats are blocked and edge cases go to human reviewers - with per-category precision/recall tracked.",
         difficulty="Medium",
         frequency="Commonly asked at platform/social companies - a trust-and-safety design testing classifiers, thresholds, human-in-the-loop, and fairness.",
         mnemonic="Cheap classifier scores everything -> block bad, allow good, send the UNCERTAIN middle to humans (LLM for nuance/context). Watch evasion, context, bias, and reviewer wellbeing. 'Automate the obvious, escalate the gray.'"),
    dict(cat="ai_applied", title="RAG evaluation with golden sets and regression testing",
         answer="In plain words: to trust a RAG system and improve it safely, you build a fixed set of test questions with known good answers/sources (a 'golden set') and score every change against it - like unit tests for your AI. Build a golden set of representative questions, each labelled with the correct answer and the source chunks that should be retrieved. On every change (new model, prompt, chunking, index), run the set and measure: RETRIEVAL quality (did the right chunks come back? recall@k, MRR), FAITHFULNESS (is the answer supported by retrieved context, not hallucinated?), ANSWER RELEVANCE/correctness (often scored by LLM-as-judge against the reference), plus latency and cost. Compare to the previous version to catch REGRESSIONS before shipping. Grow the golden set from real production failures. This turns 'it feels better' into measurable evidence and prevents a prompt tweak from silently breaking other cases.",
         tags=["rag-evaluation", "golden-set", "regression-testing", "faithfulness", "applied", "ai"],
         example="A docs bot's golden set has 150 Q+source pairs. A new chunking strategy improves one query but the nightly eval shows retrieval recall dropped from 0.88 to 0.79 across the set - a regression caught BEFORE release, so you fix chunking instead of shipping a quiet downgrade.",
         difficulty="Medium",
         frequency="Commonly asked - 'how do you know your RAG change actually helped?' separates rigorous candidates from those who eyeball a few examples.",
         mnemonic="Build a golden set (question + right answer + right sources), run it on EVERY change, score retrieval recall + faithfulness + correctness, diff vs last version to catch regressions. 'Unit tests for RAG.'"),
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

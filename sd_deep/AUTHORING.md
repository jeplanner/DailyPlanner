# How to write a deep dive (brief for authors)

You are writing system design study material for a senior engineering
leader (Senior Engineering Manager at a large Indian e-commerce company,
preparing for Director of Engineering / Director-VP TPM loops). He wants to
understand each design end to end AND be able to defend it to a panel.

Read `sd_deep/SCHEMA.md` first. Every design is one JSON file
`sd_deep/<slug>.json` that must pass:

    cd /home/claude/dailyplanner && python3 sd_deep_bank.py --check sd_deep/<slug>.json

## How to produce the file

Write a Python script in your scratch directory
(`/tmp/claude-0/-home-claude-dailyplanner/b1875ae0-38ed-5fc3-965f-121c1b3f2aff/scratchpad/sdgen/`,
NOT in the repo) that builds the dict and does
`json.dump(d, open("/home/claude/dailyplanner/sd_deep/<slug>.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)`.
Building it in Python avoids JSON quoting mistakes. Write one design per
script so a mistake costs one file. Re-run the checker until it prints OK.
Edit nothing else in the repo.

## Research

Use WebSearch / WebFetch to look at how good public write-ups and real
engineering blogs approach the design (e.g. engineering blogs of the company
that runs it, ByteByteGo, system-design-primer, highscalability, papers like
Dynamo, Spanner, Kafka, Bigtable). Use what you learn to make the design
REAL - actual techniques, real numbers, real failure stories - but write
every sentence yourself; never copy passages. `references` must only contain
URLs you actually saw in search results or fetched.

## Quality bar

- Specific, not generic. Real numbers in capacity math (QPS, storage/day,
  bandwidth, fan-out factors), named data structures, real config values
  (TTL 30s, p99 200ms, 3 replicas, quorum W=2 R=2).
- BRD is the business view (problem, goals, metrics, stakeholders, risks);
  PRD is the product view (personas, user stories, functional and
  non-functional requirements with targets, capacity estimates, out of
  scope); HLD is components, critical flows and an ASCII architecture
  diagram; LLD is APIs, data model per store with keys/partitioning,
  classes, algorithms with pseudocode, and an ASCII sequence diagram.
- framework: the Beyz "Clarify -> Design -> Defend" walkthrough. clarify =
  the questions and assumptions to state in the first minute; design = the
  baseline first, components, APIs, the critical path end to end; defend =
  the bottleneck, scaling reads, scaling writes, failure behaviour
  (timeouts, retries with jitter, fallbacks, bulkheads, degradation), and
  what you would measure. script = the 60-90 second spoken opener.
- concepts: EVERY distributed-systems concept the design actually relies on
  (e.g. consistent hashing, sharding, replication, quorum, leader election,
  CAP/PACELC, idempotency, exactly-once vs at-least-once, backpressure,
  geospatial indexing, CRDT/OT, caching patterns, rate limiting algorithms,
  vector clocks, event sourcing, CQRS, saga, outbox, ...). Teach each from
  first principles (150-400 words), then say exactly how it is used here,
  give 3-6 crisp key points, and >= 3 interview Q&A with strong answers.
- edge_cases: the nasty ones a senior interviewer probes (races, duplicates,
  clock skew, hot keys, partial failure, retries, region loss, abuse,
  boundary conditions, data skew, mobile networks).
- tech_stack: each technology with what it is (overview), why it fits here,
  and alternatives with the trade-off.
- quiz: "choose the best answer" MCQs that test understanding, not trivia.
  Four plausible options, the right answer spread across positions, and a
  `why` that explains the right answer and the most tempting wrong one.
  Mix: concept checks, scenario ("p99 jumps when..."), numbers ("roughly how
  many..."), trade-off choices.
- key_points: the cheat sheet - what to say out loud to sound senior.
- Plain text only. No Markdown symbols like ** or #. ASCII diagrams under
  100 columns.

When done, report back ONLY: each slug and the checker's OK line.

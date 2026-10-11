# System design deep dives — file format

One JSON file per design: `sd_deep/<slug>.json`, UTF-8, written with
`json.dump(obj, f, ensure_ascii=False, indent=1)`. `sd_deep_bank.py` loads
and validates every file; run

    python3 sd_deep_bank.py --check sd_deep/<slug>.json

after writing. It prints every problem and exits non-zero until the file is
complete.

Plain text everywhere (no Markdown, no HTML). Use "\n" for line breaks and
"  * " or "1. " for list lines inside long text. Diagrams are ASCII inside
the `diagram` / `pseudocode` / `sequence` fields and must stay under 100
columns wide.

## Top level

| key | type | rule |
|---|---|---|
| slug | str | file name without .json, lowercase-hyphenated |
| title | str | "Design Uber (ride-hailing)" style |
| prompt | str | the interview prompt exactly as asked (Beyz wording when from Beyz) |
| group | str | one of: classic, feeds, search, storage, caching, messaging, reliability, security, realtime, web |
| source | str | "beyz" or "web" |
| difficulty | str | "Medium" or "Hard" |
| minutes | int | realistic study time, 45-240 |
| summary | str | 2-4 sentences: what makes this design interesting / the core tension |
| framework | obj | Clarify -> Design -> Defend (see below) |
| brd | obj | business requirements |
| prd | obj | product requirements |
| hld | obj | high-level design |
| lld | obj | low-level design |
| edge_cases | list | {case, handling} |
| tech_stack | list | {name, layer, overview, why, alternatives} |
| concepts | list | distributed-systems concepts, deep (see below) |
| tradeoffs | list | {decision, options, choice, why} |
| failure_modes | list | {failure, behavior} |
| metrics | list[str] | what you would measure / alert on |
| follow_ups | list | {q, a} — the interviewer's push-backs and strong answers |
| key_points | list[str] | the 6-12 things to say out loud; the cheat sheet |
| quiz | list | {q, options[4], answer (0-3), why} |
| references | list | {title, url} — real, fetched URLs only |

## framework (Clarify -> Design -> Defend)

    "framework": {
      "clarify": ["question or assumption to state", ...],      # >= 6
      "design":  ["baseline step / component / API / critical path", ...],  # >= 5
      "defend":  ["bottleneck / scale reads / scale writes / failure / measure", ...],  # >= 5
      "script":  "a 60-90 second spoken opener that walks C->D->D"
    }

## brd

    {"problem": str, "goals": [str], "non_goals": [str],
     "stakeholders": [{"who": str, "needs": str}],
     "success_metrics": [{"metric": str, "target": str}],
     "constraints": [str], "risks": [{"risk": str, "mitigation": str}]}

## prd

    {"personas": [{"name": str, "needs": str}],
     "user_stories": [str],                       # "As a rider, I want ... so that ..."
     "functional": [str],
     "non_functional": [{"name": str, "target": str}],   # latency, availability, consistency, durability...
     "capacity": {"assumptions": [str], "math": [str], "summary": str},  # back-of-the-envelope, real numbers
     "out_of_scope": [str]}

## hld

    {"overview": str,
     "diagram": str,                               # ASCII architecture, < 100 cols
     "components": [{"name": str, "responsibility": str}],
     "flows": [{"name": str, "steps": [str]}],     # critical paths end to end
     "data_flow": str}

## lld

    {"apis": [{"method": str, "path": str, "request": str, "response": str, "notes": str}],
     "data_model": [{"entity": str, "store": str, "fields": [str], "keys": str, "notes": str}],
     "classes": [{"name": str, "responsibility": str, "methods": [str]}],
     "algorithms": [{"name": str, "explain": str, "pseudocode": str}],
     "sequence": str}                              # ASCII sequence diagram of the critical path

## concepts (the heart of it)

    {"name": "Geospatial indexing (geohash / H3 / quadtree)",
     "explain": str,          # teach it from first principles: 150-400 words
     "in_this_design": str,   # exactly how and why it is used here
     "key_points": [str],     # 3-6 crisp, quotable lines
     "qa": [{"q": str, "a": str}]}   # >= 3 interview Q&A per concept

## quiz (choose the best answer)

    {"q": str, "options": [str, str, str, str], "answer": 0-3, "why": str}

Distractors must be plausible (real misconceptions), never joke options.
Vary the position of the right answer. `why` explains why the right one is
right AND why the most tempting wrong one is wrong.

## Minimums (enforced)

| field | standard | flagship (uber) |
|---|---|---|
| framework.clarify/design/defend | 6 / 5 / 5 | 8 / 8 / 8 |
| brd.goals, non_goals | 4, 3 | 6, 4 |
| prd.user_stories, functional | 6, 6 | 12, 12 |
| prd.non_functional | 5 | 8 |
| hld.components, flows | 6, 2 | 12, 4 |
| lld.apis, data_model, classes, algorithms | 4, 3, 3, 2 | 10, 7, 8, 5 |
| edge_cases | 10 | 25 |
| tech_stack | 6 | 12 |
| concepts (each >= 3 qa) | 6 | 14 |
| tradeoffs | 5 | 10 |
| failure_modes | 5 | 10 |
| follow_ups | 6 | 15 |
| key_points | 6 | 10 |
| quiz | 20 | 60 |
| references | 2 | 6 |

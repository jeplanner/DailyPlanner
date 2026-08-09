"""Behavioral interview question bank — 100+ common questions with STAR
model answers, tuned for a senior Technical Program Management / Director
run.

These are ADAPTABLE TEMPLATES, not scripts. The model answers use a small
set of recurring "signature scenarios" (a platform migration, a payments
launch recovery, an operating-model change, a regulated launch, a Sev1
incident, an Eng/Product scope conflict) so they read coherently — swap in
your own experiences and real numbers (the [bracketed] bits) before you
rehearse. The value is the STRUCTURE and the altitude of the answer.

Served read-only by routes/interview_prep.py at /api/interview-prep/questions.
"""

CATEGORIES = {
    "leadership": "Leadership & Ownership",
    "ambiguity": "Ambiguity & Change",
    "conflict": "Conflict & Difficult People",
    "delivery": "Program Delivery & Execution",
    "failure": "Failure & Learning",
    "stakeholders": "Stakeholder & Exec Management",
    "prioritization": "Prioritization & Trade-offs",
    "collaboration": "Cross-functional Collaboration",
    "decision": "Decision-making & Judgment",
    "people": "People & Team Development",
    "strategy": "Strategy & Vision",
    "influence": "Influence Without Authority",
    "risk": "Risk & Crisis Management",
    "communication": "Communication",
    "customer": "Customer & Business Orientation",
    "growth": "Growth, Feedback & Positioning",
    # ── Executive depth (Senior Director / Head-of-function altitude) ──
    "orgdesign": "Org Design & Operating Model",
    "finance": "Budget, P&L & ROI",
    "board": "Board & Executive Communication",
    "talent": "Talent, Culture & Org Health",
}


def _q(cat, q, s, t, a, r, tip):
    return {"cat": cat, "q": q, "s": s, "t": t, "a": a, "r": r, "tip": tip}


# Behavioral theme vocabulary → tags, matched against each question so the
# bank is searchable by theme (e.g. "conflict", "failure", "ambiguity").
_BEH_VOCAB = {
    "leadership": ["lead", "led", "leading", "leader"],
    "ownership": ["own", "ownership", "responsib"],
    "conflict": ["conflict", "disagree", "difficult", "tension"],
    "failure": ["fail", "failed", "mistake", "regret", "wrong", "missed"],
    "ambiguity": ["ambigu", "unclear", "uncertain", "incomplete", "chaos"],
    "deadline": ["deadline", "tight", "aggressive", "pressure", "time"],
    "feedback": ["feedback", "criticism", "critique"],
    "influence": ["influence", "persuad", "convince", "authority", "buy-in", "coalition"],
    "stakeholder": ["stakeholder", "executive", "exec", "leadership team", "manage up", "managing up"],
    "prioritization": ["priorit", "trade-off", "tradeoff", "deprioriti"],
    "teamwork": ["team", "collaborat", "cross-functional", "silo", "partner"],
    "decision": ["decision", "decide", "judgment", "data-driven"],
    "people": ["mentor", "underperform", "hire", "coach", "develop", "morale", "delegat"],
    "strategy": ["strategy", "vision", "long-term", "roadmap"],
    "risk": ["risk", "crisis", "incident", "outage", "mitigat"],
    "communication": ["communicat", "present", "explain", "message", "bluf"],
    "customer": ["customer", "user"],
    "change": ["change", "transform", "reorg", "restructur", "migration"],
    "growth": ["learn", "quickly", "comfort zone", "improve", "grow"],
    "delivery": ["deliver", "launch", "ship", "program", "execution"],
    "orgdesign": ["org design", "operating model", "reorg", "span of control",
                  "charter", "governance", "structure", "cadence", "function"],
    "budget": ["budget", "p&l", "roi", "cost", "headcount", "business case",
               "build vs", "spend", "cfo", "capex", "opex", "savings"],
    "board": ["board", "ceo", "qbr", "business review", "narrative",
              "six-pager", "6-pager", "written", "exec update"],
    "talent": ["hiring bar", "succession", "attrition", "calibrat", "leveling",
               "manage out", "culture", "retention", "bench", "org health"],
}


def _beh_tags(q):
    text = (q["q"] + " " + q.get("s", "")).lower()
    tags = {q["cat"]}
    for tag, needles in _BEH_VOCAB.items():
        if any(n in text for n in needles):
            tags.add(tag)
    return sorted(tags)


QUESTIONS = [
    # ─────────── Leadership & Ownership ───────────
    _q("leadership",
       "Tell me about a time you led a team through a major change.",
       "Our org was migrating a legacy monolith to microservices across [8] teams with heavy skepticism.",
       "As TPM I owned landing the migration without stalling the product roadmap.",
       "I set a phased plan, created a shared scorecard, ran weekly de-risking reviews, and over-communicated the 'why' to every team.",
       "We migrated [80%] of services in [2] quarters with zero customer-facing incidents and lifted deploy frequency [3x].",
       "Anchor on how you carried people through the change emotionally, not just the mechanics."),
    _q("leadership",
       "Describe a time you led without any formal authority.",
       "I was accountable for a cross-org launch but none of the engineers reported to me.",
       "I had to align [5] teams that each had their own priorities and managers.",
       "I built credibility through a clear plan, made their wins visible upward, and removed blockers faster than anyone else could.",
       "Teams started routing decisions through me by choice; we shipped on the committed date.",
       "Emphasize influence earned through trust and usefulness, not title."),
    _q("leadership",
       "Give an example of motivating a demotivated or burned-out team.",
       "After a slipped payments launch, the team was demoralized and attrition risk was rising.",
       "I needed to rebuild momentum and belief without pretending the miss didn't happen.",
       "I ran a blameless retro, cut scope to a winnable milestone, celebrated small wins publicly, and protected the team's focus time.",
       "We shipped the reduced launch in [6] weeks and voluntary attrition dropped to zero that half.",
       "Show emotional intelligence: name the low, then engineer an early win."),
    _q("leadership",
       "Tell me about a time you took ownership of a problem outside your remit.",
       "A recurring data-quality issue was hurting [3] products but sat in nobody's charter.",
       "No single team owned it, so it kept getting dropped.",
       "I volunteered to own it end-to-end, mapped the root cause across teams, and stood up a lightweight governance forum.",
       "Defect rate fell [40%] and the forum became the permanent home for cross-cutting data issues.",
       "Great senior signal — you close ownership gaps instead of pointing at them."),
    _q("leadership",
       "Describe leading a high-stakes initiative with a tight, immovable deadline.",
       "We had a regulatory deadline to ship compliance changes or face fines.",
       "I owned delivery across Eng, Legal, and Ops with no room to slip.",
       "I built a critical-path plan, ran daily standups in the final stretch, pre-cleared decisions with Legal, and tracked risks in a live RAID log.",
       "We shipped [3] days early and passed the external audit clean.",
       "Show your operating cadence tightening as risk rises."),
    _q("leadership",
       "Tell me about a time you made an unpopular decision.",
       "Two teams wanted to keep building parallel internal tools that overlapped.",
       "I had to consolidate onto one platform, which meant sunsetting a team's pet project.",
       "I made the call transparently with the data, gave the losing team a real role on the surviving platform, and owned the message myself.",
       "We saved [~30%] of maintenance cost and the merged team shipped faster.",
       "Own the decision AND the fallout — don't hide behind consensus."),
    _q("leadership",
       "Describe a time you grew someone into a bigger role.",
       "A strong senior engineer wanted to move toward program leadership.",
       "I needed delivery help and they needed a stretch.",
       "I delegated a workstream to them, coached weekly, gave air cover, and made their impact visible to leadership.",
       "They were promoted to lead TPM within [a year] and now own that program.",
       "Senior leaders are measured by who they grow — make that explicit."),

    # ─────────── Ambiguity & Change ───────────
    _q("ambiguity",
       "Tell me about a time you had to make progress with incomplete information.",
       "We had to commit to a launch date before the architecture was fully scoped.",
       "Leadership needed a credible date; engineers wanted more certainty first.",
       "I framed assumptions explicitly, committed to a date with a confidence range, and set checkpoints to re-forecast as we learned.",
       "We hit the date within the stated range and leadership trusted the forecasting model afterward.",
       "Show comfort deciding with 70% information and a plan to close the rest."),
    _q("ambiguity",
       "Describe a project with unclear or constantly shifting requirements.",
       "A new product line had a vague brief and a founder who kept changing scope.",
       "I had to create enough stability for engineers to build.",
       "I drove a lightweight PRD, established a weekly scope-change board, and made trade-offs visible so every 'add' showed its cost.",
       "Churn dropped sharply and we shipped an MVP that validated the bet.",
       "Your job is turning ambiguity into structure others can execute against."),
    _q("ambiguity",
       "Tell me about a time priorities changed suddenly.",
       "Mid-quarter, leadership pulled us onto an urgent competitive response.",
       "I had to re-plan a committed roadmap in days without breaking trust.",
       "I re-sequenced work, renegotiated commitments with impacted stakeholders early, and protected one must-keep deliverable.",
       "We landed the competitive response on time and only slipped [one] non-critical item.",
       "Highlight fast, transparent re-commitment — not heroics."),
    _q("ambiguity",
       "Describe operating in a domain that was completely new to you.",
       "I moved into a payments program with deep regulatory complexity I didn't know.",
       "I had to lead credibly without the domain depth of my team.",
       "I ran a rapid learning plan, paired with SMEs, asked sharp questions, and focused my value on structure and decision-forcing.",
       "I was running the program confidently within [weeks] and caught two risks the team had missed.",
       "Senior leaders add value through judgment and structure, not being the SME."),
    _q("ambiguity",
       "Tell me about a time you created order out of chaos.",
       "A red program had [4] workstreams, no single plan, and constant surprises.",
       "I was brought in to stabilize it.",
       "I built one integrated plan, a single source of truth, a weekly operating rhythm, and a clear RAID log.",
       "Within [a month] the program was predictable and moved from red to green.",
       "This is the classic TPM turnaround — lead with your operating system."),
    _q("ambiguity",
       "Describe a decision that had no clear owner.",
       "A cross-team API contract was stuck because no one felt they owned the call.",
       "The stall was blocking [3] teams.",
       "I named the decision, gathered the trade-offs, proposed a default, and set a 'decide by' date that forced closure.",
       "We unblocked in [days] and I codified a decision-owner rule to prevent repeats.",
       "Show you drive decisions to closure, not just facilitate."),
    _q("ambiguity",
       "Tell me about navigating your team through a reorg or restructuring.",
       "Two teams merged and roles, ownership, and morale were all uncertain.",
       "I had to keep delivery going through the disruption.",
       "I clarified new ownership fast, over-communicated, protected key people, and kept one shared goal front and center.",
       "We held delivery steady and retained every key contributor.",
       "Stability and candor are the leadership signals here."),

    # ─────────── Conflict & Difficult People ───────────
    _q("conflict",
       "Tell me about a conflict with a peer or stakeholder.",
       "A product lead and I disagreed hard on cutting scope to hit a date.",
       "We needed one aligned plan and were running out of time.",
       "I moved the debate to shared data, separated the goal from the positions, and found a middle path that protected the launch-critical scope.",
       "We aligned, shipped on time, and the relationship got stronger from handling it well.",
       "Show you attack the problem, not the person, and reach durable alignment."),
    _q("conflict",
       "Describe a time you disagreed with your manager.",
       "My director wanted to commit to a date I believed was unrealistic.",
       "I had to push back without undermining them.",
       "I brought the risk data privately, proposed a phased alternative, and committed to fully support whatever they decided.",
       "They adjusted to a phased plan and later thanked me for the candid pushback.",
       "'Disagree and commit' — show the private candor and the public support."),
    _q("conflict",
       "Tell me about mediating a conflict between two teams.",
       "Eng and Data teams were blaming each other for a broken pipeline.",
       "The finger-pointing was stalling a fix customers needed.",
       "I got both in a room, focused on the shared customer impact, facilitated a joint root-cause, and split clear ownership of the fix.",
       "The pipeline was fixed in [days] and I set up a shared on-call to prevent repeats.",
       "Neutral facilitation plus a structural fix beats picking a winner."),
    _q("conflict",
       "Describe working with a difficult or resistant stakeholder.",
       "A senior stakeholder repeatedly blocked a change they saw as a threat.",
       "I needed their cooperation to land the program.",
       "I met them 1:1 to understand the real concern, addressed it directly, and gave them a visible stake in the outcome.",
       "They went from blocker to advocate and championed the rollout.",
       "Curiosity about the underlying fear usually unlocks the resistance."),
    _q("conflict",
       "Tell me about a time you received harsh or unfair criticism.",
       "In a review, an exec criticized my program's status as 'too optimistic'.",
       "I had to respond without defensiveness and rebuild confidence.",
       "I listened, acknowledged the valid part, tightened my risk reporting, and followed up with a more rigorous forecast.",
       "The exec's trust recovered and my reporting became the team's template.",
       "Show maturity: take the signal, drop the ego, improve the system."),
    _q("conflict",
       "Describe a time you had to say no to a senior leader.",
       "A VP wanted a feature added late that would have risked the launch.",
       "I had to decline while keeping the relationship intact.",
       "I said no with the trade-off math, offered a fast-follow path, and let them make the final informed call.",
       "They accepted the fast-follow; we launched safely and shipped their feature the next cycle.",
       "A confident, data-backed no with an alternative reads as senior, not obstinate."),
    _q("conflict",
       "Tell me about a disagreement on technical direction.",
       "Two staff engineers disagreed on build-vs-buy for a core component.",
       "As TPM I had to get to a decision without overreaching on tech I didn't own.",
       "I framed the decision criteria, ran a timeboxed spike, and forced a decision against the criteria rather than opinion.",
       "We chose buy, saved [a quarter] of build time, and both engineers backed the call.",
       "Own the decision PROCESS; let the experts own the technical depth."),

    # ─────────── Program Delivery & Execution ───────────
    _q("delivery",
       "Tell me about the most complex program you've delivered.",
       "I led a company-wide platform migration spanning [8] teams and [3] regions.",
       "I owned the plan, dependencies, risks, and the executive narrative.",
       "I built an integrated critical-path plan, ran a tight operating cadence, managed a live dependency map, and escalated early.",
       "We delivered on time, cut infra cost [~25%], and it became the template for future migrations.",
       "Pick your biggest scope-of-impact story and quantify it."),
    _q("delivery",
       "Describe delivering under an aggressive deadline.",
       "We had [10] weeks to launch a feature tied to a partner commitment.",
       "The original scope needed [16] weeks.",
       "I ruthlessly cut to the minimum lovable scope, parallelized workstreams, and pre-cleared decisions to remove wait time.",
       "We launched on the [10]-week date with the core value intact and fast-followed the rest.",
       "Show scope discipline and dependency parallelization, not just overtime."),
    _q("delivery",
       "Tell me about a launch that went really well.",
       "We launched a new checkout flow to millions of users.",
       "I owned the end-to-end launch and rollback readiness.",
       "I ran a staged rollout with clear go/no-go gates, real-time dashboards, and a war room for the first [48] hours.",
       "Zero Sev1s, conversion up [X%], and the playbook was reused for later launches.",
       "Highlight the launch rigor (gates, monitoring, rollback) that made 'went well' non-accidental."),
    _q("delivery",
       "Describe managing a program with many dependencies.",
       "My program depended on [6] other teams' deliverables to land.",
       "Any one slip could cascade into a miss.",
       "I mapped every dependency with owners and dates, tracked them weekly, and negotiated buffers on the riskiest ones.",
       "We absorbed [2] upstream slips without missing our date.",
       "Dependency management is the core TPM craft — show your system for it."),
    _q("delivery",
       "Tell me about how you track and drive a program to completion.",
       "I inherited a program with no reliable status signal.",
       "Leadership couldn't tell if we'd make it.",
       "I stood up a single source of truth, a red/amber/green scorecard, weekly reviews, and clear escalation paths.",
       "Status became trustworthy and we hit every remaining milestone.",
       "Describe your operating mechanisms concretely — that's the senior tell."),
    _q("delivery",
       "Describe a time you cut scope to hit a date.",
       "Halfway through a launch, our burn-up showed we'd miss by [3] weeks.",
       "The date was tied to a marketing moment we couldn't move.",
       "I ranked features by value, negotiated a v1 with stakeholders, and moved the rest to a committed fast-follow.",
       "We hit the date; the trimmed features shipped [3] weeks later with no customer impact.",
       "Show scope as a lever you manage deliberately, with stakeholder buy-in."),
    _q("delivery",
       "Tell me about coordinating a globally distributed team.",
       "My program ran across teams in [3] time zones with little overlap.",
       "Hand-offs were slow and context was getting lost.",
       "I set up async-first updates, a follow-the-sun hand-off ritual, and a couple of anchored overlap meetings.",
       "Cycle time dropped and the teams reported far less rework.",
       "Emphasize async operating design, not just 'we had more meetings'."),

    # ─────────── Failure & Learning ───────────
    _q("failure",
       "Tell me about a time you failed.",
       "I committed to a launch date on optimistic estimates and we missed by [a quarter].",
       "I owned the miss to leadership and the team.",
       "I ran a blameless post-mortem, fixed our estimation process with confidence ranges, and reset expectations transparently.",
       "The next two programs landed on time and my forecasting became a team standard.",
       "Own it cleanly, extract the systemic lesson, prove you changed."),
    _q("failure",
       "Describe a project that missed its deadline.",
       "A dependency-heavy program slipped because I under-managed an upstream risk.",
       "I had to recover the timeline and trust.",
       "I re-baselined honestly, added dependency buffers, and escalated the upstream risk to get it prioritized.",
       "We delivered [3] weeks late but with a plan that prevented the next slip.",
       "Don't hide the miss — show the diagnosis and the durable fix."),
    _q("failure",
       "Tell me about a decision you regret.",
       "I once deferred a tech-debt investment to protect a date.",
       "That debt later caused an incident.",
       "I owned the call, led the remediation, and built a policy to budget tech-debt into every plan.",
       "Incident rate dropped and debt stopped being an afterthought.",
       "Regret + learning + a system change is the arc they want."),
    _q("failure",
       "Describe a launch or release that went wrong.",
       "A release caused a partial outage for [some] users.",
       "I was the incident commander.",
       "I coordinated the rollback, ran clear comms, drove the root cause, and shipped preventive actions.",
       "We restored service in [under an hour] and the follow-ups eliminated that failure class.",
       "Show calm command and the preventive follow-through, not blame."),
    _q("failure",
       "Tell me about the biggest mistake you learned from.",
       "Early on I over-communicated detail and under-communicated the 'so what' to execs.",
       "It cost me influence in a key review.",
       "I learned to lead with BLUF, tailor altitude to the audience, and confirm the ask.",
       "My exec updates started driving faster decisions.",
       "A self-awareness answer lands well if the lesson is specific."),
    _q("failure",
       "Describe a time you had to recover a failing program.",
       "I was pulled into a red payments program slipping [2] quarters.",
       "I had to stabilize it and rebuild confidence.",
       "I re-scoped to a winnable milestone, rebuilt the plan and cadence, cleared the top [3] risks, and reset stakeholder expectations.",
       "We shipped the milestone, moved to green, and delivered the full launch the next quarter.",
       "This is a signature senior story — quantify the turnaround."),
    _q("failure",
       "Tell me about a risk that materialized despite your planning.",
       "A vendor missed a delivery I'd flagged as a risk but under-buffered.",
       "It threatened our launch date.",
       "I triggered a contingency, shifted work in-house temporarily, and renegotiated the vendor timeline.",
       "We protected the date and I tightened vendor SLAs afterward.",
       "Show that even a materialized risk had a contingency ready."),

    # ─────────── Stakeholder & Exec Management ───────────
    _q("stakeholders",
       "Tell me about managing senior/executive stakeholders.",
       "My program had [4] VPs with different definitions of success.",
       "I needed one aligned definition to avoid thrash.",
       "I ran 1:1 pre-reads, surfaced the conflicts explicitly, and drove a single success metric everyone signed.",
       "Reviews got faster and the program stopped getting re-litigated.",
       "Show you align execs BEFORE the room, not in it."),
    _q("stakeholders",
       "Describe delivering bad news to leadership.",
       "We were going to miss a committed date.",
       "I had to tell leadership early without losing their confidence.",
       "I led with the headline, the impact, the options, and my recommendation — no burying it.",
       "Leadership picked an option calmly and trusted my reporting more, not less.",
       "Bad news early + options + a recommendation = senior credibility."),
    _q("stakeholders",
       "Tell me about aligning stakeholders with competing goals.",
       "Sales wanted speed, Eng wanted quality, Legal wanted caution.",
       "I had to find a path all three would back.",
       "I made the trade-offs explicit, tied the decision to the shared business outcome, and got each to own a piece of the plan.",
       "We aligned on a phased launch that met the core of all three needs.",
       "Reframe competing goals against a shared higher outcome."),
    _q("stakeholders",
       "Describe influencing an executive decision.",
       "Leadership was leaning toward a big-bang launch I thought was too risky.",
       "I needed to shift them toward a phased approach.",
       "I brought a crisp risk-vs-reward analysis, a customer-impact scenario, and a concrete phased alternative.",
       "They chose the phased plan, which avoided a likely major incident.",
       "Influence with analysis + a ready alternative, not just concern."),
    _q("stakeholders",
       "Tell me about a difficult status update you had to give.",
       "My program went amber right before a board update.",
       "I had to represent it honestly without triggering panic.",
       "I gave a clear R/A/G with the specific risk, the mitigation, and the date confidence.",
       "The update built confidence and we got the support we asked for.",
       "Precision and a mitigation plan turn a scary update into a confident one."),
    _q("stakeholders",
       "Describe a time you managed up effectively.",
       "My director was going into a review missing context on a key risk.",
       "I needed them to look prepared and make a good call.",
       "I gave them a tight pre-read with the decision, the options, and my recommendation.",
       "They ran the review smoothly and made the right call fast.",
       "Managing up = making your leader effective, not just informed."),
    _q("stakeholders",
       "Tell me about building trust with a skeptical stakeholder.",
       "A skeptical eng director doubted TPM added value to his team.",
       "I needed his partnership to land the program.",
       "I focused on removing his team's blockers, kept commitments precisely, and let results speak before asking for anything.",
       "He became a strong advocate and requested TPM support for his next program.",
       "Trust is earned with delivered small commitments, fast."),

    # ─────────── Prioritization & Trade-offs ───────────
    _q("prioritization",
       "Tell me about handling competing priorities.",
       "I owned [3] programs all demanding the same scarce platform team.",
       "I couldn't fully staff them all.",
       "I ranked by business impact and risk, made the trade-offs transparent to sponsors, and sequenced rather than split thin.",
       "The top program shipped early; the others landed with clear expectations.",
       "Show a crisp framework (impact x effort x risk) and transparent trade-offs."),
    _q("prioritization",
       "Describe a hard trade-off you made.",
       "I had to choose between hitting a date and shipping a nice-to-have feature.",
       "Both mattered to different stakeholders.",
       "I chose the date, backed by customer and revenue data, and moved the feature to a committed fast-follow.",
       "We protected the revenue moment and shipped the feature [3] weeks later.",
       "Name the criteria that made the trade-off objective."),
    _q("prioritization",
       "Tell me about deprioritizing something important.",
       "A well-loved internal tool had to be paused to fund a strategic bet.",
       "The owning team was upset.",
       "I explained the strategic rationale, gave a revisit date, and preserved a minimal maintenance mode.",
       "The strategic bet paid off and the tool resumed the next half.",
       "Show empathy for what you cut and a path back."),
    _q("prioritization",
       "Describe allocating limited resources across demands.",
       "Headcount froze mid-year with [5] programs in flight.",
       "I had to keep the most valuable ones moving.",
       "I zero-based the portfolio, paused two low-ROI efforts, and concentrated people on the highest-leverage work.",
       "Throughput on the top programs actually rose despite the freeze.",
       "Concentration beats spreading thin — show the courage to pause things."),
    _q("prioritization",
       "Tell me about balancing speed versus quality.",
       "Leadership wanted a fast launch; the team feared quality risk.",
       "I had to find the right bar for this launch.",
       "I defined a quality gate that was non-negotiable and let everything above it flex for speed.",
       "We launched fast and clean, with no quality regressions past the gate.",
       "Make 'quality' concrete via a gate rather than a vibe."),
    _q("prioritization",
       "Describe saying no to a feature or request.",
       "A big customer requested a bespoke feature that would fragment the roadmap.",
       "I had to decline without damaging the relationship.",
       "I explained the platform cost, offered a configurable alternative, and escalated the revenue trade-off to the sponsor.",
       "We shipped the configurable path, serving that customer and [others].",
       "A principled no protects the many; show the alternative you offered."),
    _q("prioritization",
       "Tell me about reprioritizing a roadmap mid-flight.",
       "New data showed our top feature wouldn't move the metric.",
       "I had to redirect the team quickly.",
       "I brought the data, re-ranked the backlog with Product, and re-committed dates transparently.",
       "We pivoted to the higher-impact work and hit the metric that quarter.",
       "Show you follow the data even when it means reversing course."),

    # ─────────── Cross-functional Collaboration ───────────
    _q("collaboration",
       "Tell me about a strong cross-functional collaboration.",
       "A launch needed Eng, Design, Legal, Marketing, and Support in lockstep.",
       "I owned making the whole thing move as one.",
       "I built a shared plan with a single timeline, one status source, and a weekly cross-functional sync.",
       "Every function hit its gate and the launch went off without a hitch.",
       "Show the connective tissue you created across functions."),
    _q("collaboration",
       "Describe partnering with a team that was hard to work with.",
       "A partner team was overloaded and unresponsive to our dependency.",
       "I needed their deliverable without more escalation friction.",
       "I met their lead, reshaped the ask to fit their constraints, and traded help on something they needed.",
       "They delivered on a workable date and the relationship reset.",
       "Reciprocity and empathy for their load unlock stuck partnerships."),
    _q("collaboration",
       "Tell me about breaking down a silo.",
       "Two orgs were solving the same problem separately and duplicating work.",
       "I had to get them to collaborate.",
       "I convened a shared forum, surfaced the overlap with data, and proposed a joint roadmap.",
       "They merged efforts and cut duplicated work [~30%].",
       "Data on duplication plus a shared forum is a repeatable silo-buster."),
    _q("collaboration",
       "Describe building a coalition to get something done.",
       "A platform change needed buy-in from [6] team leads with no mandate.",
       "I had to build momentum voluntarily.",
       "I recruited an early champion, showed a quick win, then used that proof to bring the rest aboard.",
       "All [6] adopted within [a quarter] and the platform standardized.",
       "Champion → quick win → snowball is a strong influence pattern."),
    _q("collaboration",
       "Tell me about working with remote or distributed partners.",
       "Key partners were in another region with limited overlap hours.",
       "Collaboration was slow and easy to misread.",
       "I set async-first norms, crisp written decisions, and a small anchored overlap for the hard calls.",
       "Decision latency dropped and trust improved across the timezone gap.",
       "Async operating discipline is the differentiator for distributed work."),
    _q("collaboration",
       "Describe partnering with a vendor or external partner.",
       "A launch depended on a third-party integration with a shaky track record.",
       "I had to de-risk their delivery.",
       "I set clear SLAs, joint milestones, weekly syncs, and an in-house contingency for the riskiest piece.",
       "They delivered on the revised plan and my contingency was never needed but ready.",
       "Show you manage external partners like any critical dependency."),

    # ─────────── Decision-making & Judgment ───────────
    _q("decision",
       "Tell me about a data-driven decision you made.",
       "We debated whether to invest another quarter in a feature.",
       "Opinions were split and expensive.",
       "I pulled usage and funnel data, ran a small experiment, and let the results decide against pre-set criteria.",
       "The data said stop; we redirected the quarter to higher-impact work.",
       "Show the criteria set BEFORE the data, so it's judgment not cherry-picking."),
    _q("decision",
       "Describe a decision you made with imperfect data.",
       "We had to pick an architecture before load patterns were known.",
       "Waiting for perfect data would have blown the timeline.",
       "I made the reversible parts fast, protected the irreversible ones with more analysis, and set a re-evaluation trigger.",
       "The choice held up and the trigger let us adjust cheaply later.",
       "Distinguish one-way vs two-way doors — a classic senior judgment tell."),
    _q("decision",
       "Tell me about a quick decision under pressure.",
       "During a launch, a metric spiked wrong and we had minutes to decide.",
       "I had to call roll-forward vs rollback fast.",
       "I checked the blast radius, weighed the reversible option, and called an immediate rollback.",
       "We avoided customer impact and root-caused calmly after.",
       "Bias to the reversible option under time pressure reads as sound judgment."),
    _q("decision",
       "Describe a time you changed your mind.",
       "I initially pushed build over buy for a component.",
       "New cost and timeline data challenged my stance.",
       "I re-ran the analysis, admitted the new data changed the answer, and switched to buy.",
       "We saved [a quarter] and I modeled that being right matters more than being consistent.",
       "Changing your mind on evidence is strength, not weakness — say so."),
    _q("decision",
       "Tell me about weighing risk versus reward.",
       "A fast-launch option promised upside but carried real incident risk.",
       "I had to size both honestly.",
       "I quantified downside scenarios, added guardrails that capped the risk, and took the upside within those limits.",
       "We captured the upside with zero major incidents thanks to the guardrails.",
       "Show you took smart risk with guardrails, not reckless or timid."),
    _q("decision",
       "Describe a decision with significant consequences.",
       "I recommended sunsetting a revenue-generating legacy system.",
       "Getting it wrong would hit revenue.",
       "I modeled migration paths, de-risked with a pilot, and staged the cutover with rollback at each step.",
       "We retired it cleanly, cut cost [X], and kept revenue flat through the transition.",
       "Match the rigor of the process to the size of the stakes."),

    # ─────────── People & Team Development ───────────
    _q("people",
       "Tell me about developing a team member.",
       "A high-potential PM wanted to grow into program leadership.",
       "I needed to stretch them safely.",
       "I gave them a real workstream, coached weekly, and gradually widened their scope with air cover.",
       "They grew into leading it independently and were promoted.",
       "Concrete stretch + coaching + visible outcome is the arc."),
    _q("people",
       "Describe handling an underperformer.",
       "A team member's delivery was consistently slipping and affecting the program.",
       "I had to address it fairly and fast.",
       "I gave direct, specific feedback, co-created a clear plan with milestones, and supported them closely.",
       "They either turned it around to meet the bar or we managed a respectful transition.",
       "Show candor + support + a clear bar, not avoidance."),
    _q("people",
       "Tell me about building or scaling a team.",
       "A growing program needed a TPM function that didn't exist yet.",
       "I had to build it from scratch.",
       "I defined the roles, hired for complementary strengths, set operating norms, and onboarded deliberately.",
       "The team scaled to [N] and became the delivery backbone for the org.",
       "Talk about the bar you set and the culture you seeded."),
    _q("people",
       "Describe giving someone difficult feedback.",
       "A strong engineer's communication style was alienating partners.",
       "It was limiting their impact and the team's.",
       "I gave specific, kind, timely feedback with examples and a concrete alternative.",
       "Their partner relationships improved and it unblocked a stalled collaboration.",
       "Specific + timely + kind + actionable is the feedback formula."),
    _q("people",
       "Tell me about resolving a team morale problem.",
       "Morale dropped after a reorg left people unsure of their roles.",
       "I had to rebuild engagement while delivering.",
       "I listened in 1:1s, clarified ownership, restored a shared goal, and celebrated early wins.",
       "Engagement recovered and we retained the whole team.",
       "Listen first, then give clarity and a win."),
    _q("people",
       "Describe delegating an important task.",
       "I was overloaded across programs and holding too much myself.",
       "I needed to delegate a critical workstream.",
       "I picked the right owner, set the outcome and guardrails, and resisted micromanaging while staying available.",
       "They delivered it well and I freed capacity for higher-leverage work.",
       "Delegate the outcome, not the steps — and show you let go."),
    _q("people",
       "Tell me about losing a key team member.",
       "A lead engineer left mid-program with critical context.",
       "I had to protect delivery and morale.",
       "I captured their knowledge fast, redistributed ownership, and back-filled while keeping the team steady.",
       "We delivered on time and used the moment to reduce single-points-of-failure.",
       "Show resilience and turning a loss into a systemic improvement."),

    # ─────────── Strategy & Vision ───────────
    _q("strategy",
       "Tell me about setting a vision or strategy for your area.",
       "TPM in my org was seen as project bookkeeping, not strategic.",
       "I wanted to reposition it as a delivery advantage.",
       "I articulated a vision, tied it to business outcomes, and proved it with a flagship turnaround.",
       "TPM became a sought-after partner and the model expanded org-wide.",
       "Vision + a proof point is far stronger than vision alone."),
    _q("strategy",
       "Describe aligning a team to a long-term goal.",
       "A multi-year platform strategy felt abstract to engineers focused on sprints.",
       "I had to make the long game motivating day to day.",
       "I broke the vision into quarterly outcomes, connected each sprint to it, and showed progress on a visible roadmap.",
       "The team stayed motivated and we hit the multi-year milestones on track.",
       "Bridge the long-term to the daily with a milestone ladder."),
    _q("strategy",
       "Tell me about a strategic bet you made or drove.",
       "I pushed to invest early in a platform capability before demand was proven.",
       "It was a risk on limited signal.",
       "I framed it as a reversible pilot with clear success metrics and a kill criterion.",
       "The bet paid off and became a core capability [several] teams now depend on.",
       "Frame bets as measurable, reversible experiments."),
    _q("strategy",
       "Describe influencing the strategy of your org.",
       "Leadership's roadmap under-invested in reliability I saw as a growing risk.",
       "I had to shift investment upstream.",
       "I quantified the incident cost trend, tied it to revenue risk, and proposed a concrete reliability program.",
       "Leadership funded it and incident rate dropped [X%] the next year.",
       "Influence strategy with quantified risk tied to business impact."),
    _q("strategy",
       "Tell me about killing a project for strategic reasons.",
       "A project was progressing but no longer fit the company's direction.",
       "Sunk cost made stopping unpopular.",
       "I made the strategic misfit explicit, proposed redeploying the team to a priority, and owned the decision.",
       "We redeployed to higher-value work and the team ramped fast.",
       "Killing the wrong-but-progressing thing is a senior strength."),
    _q("strategy",
       "Describe connecting your work to business outcomes.",
       "My program was measured on delivery dates, not business impact.",
       "I wanted leadership to see the value, not just the schedule.",
       "I reframed reporting around the revenue and cost outcomes the program drove.",
       "The program's perceived value rose and it secured continued funding.",
       "Always ladder execution up to the business metric it serves."),

    # ─────────── Influence Without Authority ───────────
    _q("influence",
       "Tell me about influencing people you had no authority over.",
       "I needed [5] teams to adopt a shared release process, none reporting to me.",
       "I had to drive adoption voluntarily.",
       "I co-designed it with them, piloted with a willing team, and used the results to pull the rest in.",
       "All [5] adopted and release incidents fell.",
       "Co-creation beats mandates for lasting adoption."),
    _q("influence",
       "Describe persuading someone to your point of view.",
       "An eng lead resisted adding observability I believed was essential.",
       "I needed his team's effort without a mandate.",
       "I connected it to a pain he already felt, showed a low-cost start, and let a quick win prove it.",
       "He adopted it and later expanded it across his services.",
       "Anchor your ask to the other person's existing pain."),
    _q("influence",
       "Tell me about driving adoption of a new process or tool.",
       "A new planning process was met with 'not another process' fatigue.",
       "I had to get real usage, not compliance theater.",
       "I made it lightweight, removed an old step for every new one, and showed the time it saved.",
       "Adoption stuck because it net-reduced overhead.",
       "Adoption sticks when the new thing removes more pain than it adds."),
    _q("influence",
       "Describe getting buy-in across multiple orgs.",
       "A cross-org initiative needed sign-off from [3] VPs with different agendas.",
       "Any one could stall it.",
       "I pre-aligned each 1:1, addressed their specific concern, and brought a unified proposal to the group.",
       "All three signed and the initiative launched on schedule.",
       "Win the room before the room — align individually first."),
    _q("influence",
       "Tell me about championing an unpopular idea.",
       "I pushed to pause features for a tech-debt sprint everyone dreaded.",
       "The short-term optics were bad.",
       "I quantified the velocity drag, showed the payback, and secured a bounded, time-boxed investment.",
       "Post-sprint velocity rose [X%] and the skeptics became advocates.",
       "Make the invisible cost visible and bound the ask."),
    _q("influence",
       "Describe negotiating for resources or headcount.",
       "My program was under-staffed for its committed scope.",
       "I needed more people in a tight budget cycle.",
       "I tied the ask directly to at-risk revenue, offered scope options at each staffing level, and let leadership choose.",
       "I got the headcount for the revenue-critical scope.",
       "Frame resource asks as business trade-offs, not pleas."),

    # ─────────── Risk & Crisis Management ───────────
    _q("risk",
       "Tell me about identifying and mitigating a major risk.",
       "Early in a program I spotted a single-vendor dependency as a critical risk.",
       "A vendor slip would sink the launch.",
       "I logged it, built a contingency, negotiated a buffer, and tracked it weekly as a top risk.",
       "When the vendor slipped, the contingency kept us on date.",
       "Proactive risk logging + a ready contingency is the whole story."),
    _q("risk",
       "Describe managing a crisis or major incident.",
       "A Sev1 took down a core service during peak hours.",
       "I was incident commander.",
       "I established clear roles, ran tight comms, focused on restore-first, then drove root cause and prevention.",
       "We restored in [under an hour] and shipped fixes that closed the failure class.",
       "Calm command, restore-first, then prevention — in that order."),
    _q("risk",
       "Tell me about a security or compliance issue you handled.",
       "An audit flagged a data-handling gap before a regulated launch.",
       "We couldn't ship until it closed.",
       "I mobilized Eng and Legal, prioritized the fix on the critical path, and verified with the auditor.",
       "We closed the gap, passed the audit, and launched on time.",
       "Show you treat compliance as a hard gate, managed like any risk."),
    _q("risk",
       "Describe handling an outage or reliability problem.",
       "Recurring outages were eroding customer trust in a product.",
       "I had to break the pattern.",
       "I stood up an incident-review ritual, tracked action items to closure, and drove targeted reliability work.",
       "Outage frequency dropped [X%] and MTTR halved.",
       "Turn firefighting into a systemic reliability program."),
    _q("risk",
       "Tell me about a contingency plan that saved you.",
       "I'd pre-built a fallback for a risky third-party integration.",
       "The integration failed [days] before launch.",
       "I activated the in-house fallback I'd prepared and re-planned the final stretch.",
       "We launched on date; the fallback bridged the gap seamlessly.",
       "Pre-mortems and contingencies are cheap insurance — show you buy it."),
    _q("risk",
       "Describe escalating a risk at the right time.",
       "An upstream team's slip threatened my launch but they'd deprioritized it.",
       "I couldn't fix it at my level.",
       "I escalated early with the impact and a specific ask, not a complaint.",
       "Leadership reprioritized the upstream work and we held our date.",
       "Escalate early, with impact and a clear ask — that's a skill, not a failure."),

    # ─────────── Communication ───────────
    _q("communication",
       "Tell me about explaining something technical to a non-technical audience.",
       "I had to brief execs on a complex migration's risk.",
       "They needed to decide without the technical depth.",
       "I used a simple analogy, led with the business impact, and offered depth only on request.",
       "They made a fast, informed go decision.",
       "Lead with 'so what', keep depth on tap — don't drown them."),
    _q("communication",
       "Describe a time strong communication changed an outcome.",
       "A program was about to be cut on a misread status.",
       "I had one shot to reset the narrative.",
       "I reframed with a clear BLUF, the real progress, and a credible plan to green.",
       "Leadership kept funding it and it shipped successfully.",
       "A crisp reframing can save a program — practice your BLUF."),
    _q("communication",
       "Tell me about presenting to executives.",
       "I presented a portfolio review to the leadership team.",
       "I had [10] minutes for [5] programs.",
       "I opened with the headline, flagged only the decisions I needed, and kept detail in an appendix.",
       "We closed all decisions in the meeting with time to spare.",
       "Exec time is scarce — decisions first, detail on demand."),
    _q("communication",
       "Describe handling a serious miscommunication.",
       "Two teams built to different assumptions from a vague spec.",
       "The mismatch surfaced late and threatened rework.",
       "I owned the ambiguity, aligned both on a written source of truth, and salvaged the overlap.",
       "We minimized rework and I made written decisions the norm.",
       "Own the miscommunication and fix the system that allowed it."),
    _q("communication",
       "Tell me about tailoring a message to different audiences.",
       "The same launch needed framing for execs, engineers, and support.",
       "One message wouldn't land for all three.",
       "I tailored altitude and emphasis per audience while keeping the core facts consistent.",
       "Each group got what they needed and executed without confusion.",
       "Same truth, different altitude — show you flex the framing."),
    _q("communication",
       "Describe communicating through a period of uncertainty.",
       "During a reorg, my team was anxious and rumor-driven.",
       "I had to keep them steady and focused.",
       "I communicated frequently, was honest about what I did and didn't know, and set a clear near-term focus.",
       "The team stayed productive and trust in me grew.",
       "Frequent, honest 'here's what I know' beats waiting for certainty."),

    # ─────────── Customer & Business Orientation ───────────
    _q("customer",
       "Tell me about a time you championed the customer.",
       "A cost-cutting proposal would have degraded a key customer experience.",
       "I had to defend the customer without ignoring the business.",
       "I brought customer-impact data, proposed a cheaper option that preserved the experience, and won the trade-off.",
       "We cut cost [X] without hurting the experience or churn.",
       "Champion the customer WITH data and a business-viable alternative."),
    _q("customer",
       "Describe balancing customer needs with business constraints.",
       "Customers wanted a feature that was expensive to build broadly.",
       "I had to serve them within budget.",
       "I found a configurable path that met the core need at a fraction of the cost.",
       "We satisfied the customers and stayed within budget.",
       "Reframe 'either/or' into a cheaper 'both' where you can."),
    _q("customer",
       "Tell me about using customer feedback to change direction.",
       "Early feedback showed our planned flow confused users.",
       "I had to act before we over-invested.",
       "I brought the feedback to Product, ran a quick test of an alternative, and pivoted the design.",
       "The revised flow lifted completion [X%] at launch.",
       "Show you let real user signal override internal assumptions."),
    _q("customer",
       "Describe improving a customer experience measurably.",
       "A slow support-resolution path was hurting satisfaction.",
       "I owned a cross-team fix.",
       "I mapped the journey, cut the worst bottlenecks, and instrumented the outcome.",
       "Resolution time dropped [X%] and CSAT rose.",
       "Tie the CX improvement to a hard before/after metric."),
    _q("customer",
       "Tell me about handling a major customer escalation.",
       "A top customer escalated a recurring issue to executives.",
       "I had to resolve it and rebuild confidence.",
       "I owned the comms, drove a fast root-cause fix, and set up prevention plus a follow-up cadence.",
       "The issue was resolved, the account was retained, and trust recovered.",
       "Ownership + fix + prevention + follow-through saves the relationship."),

    # ─────────── Growth, Feedback & Positioning ───────────
    _q("growth",
       "Tell me about a time you received feedback and acted on it.",
       "A mentor told me my updates buried the key decision.",
       "It was limiting my influence in reviews.",
       "I adopted a BLUF-first structure and confirmed the ask every time.",
       "My reviews started driving faster decisions and the feedback stuck.",
       "Show a specific behavior change and its result."),
    _q("growth",
       "Describe learning a new skill or domain quickly.",
       "I had to lead a payments program without payments depth.",
       "I needed to be credible fast.",
       "I built a focused learning plan, paired with SMEs, and applied it immediately on the job.",
       "I was leading confidently within [weeks] and caught risks the team missed.",
       "Show a deliberate, fast learning method — not just 'I figured it out'."),
    _q("growth",
       "Tell me about stepping outside your comfort zone.",
       "I took on an org-wide operating-model change well beyond my prior scope.",
       "It was bigger and more political than anything I'd led.",
       "I leaned on structure, sought coaching, and built coalitions deliberately.",
       "The new model rolled out successfully and expanded my scope permanently.",
       "Stretch + how you de-risked it = growth mindset with judgment."),
    _q("growth",
       "Describe how you improved a process or yourself over time.",
       "Our launch process kept producing avoidable surprises.",
       "I wanted repeatable, boring launches.",
       "I built a launch checklist, go/no-go gates, and a post-launch review loop.",
       "Launch incidents dropped and the playbook became the team standard.",
       "Show continuous improvement as a system, not a one-off."),
    _q("growth",
       "Why this role, and why you? (positioning)",
       "This role sits exactly at the intersection of scale, ambiguity, and cross-org leadership.",
       "I want to drive company-level outcomes, not just program delivery.",
       "My track record is turning around red programs, building TPM functions, and influencing strategy without authority.",
       "That's precisely what a Head-of-TPM mandate needs, and where I do my best work.",
       "Tie your signature strengths directly to THIS role's mandate and scale."),

    # ══ Org Design & Operating Model ══════════════════════════════════════
    _q("orgdesign",
       "How would you design the TPM function for a company at our scale?",
       "I inherited [12] TPMs scattered under different VPs, with no shared bar, no ladder, and duplicated governance.",
       "I owned defining what the function is, where it reports, and what it is accountable for.",
       "I split the work into three tiers - portfolio/strategic, cross-org program, and team-level execution - staffed each tier deliberately, kept TPMs embedded with product/eng for context but centralized reporting for standards and career path, and published a charter naming what TPM owns (cross-team risk, dependencies, launch readiness, exec truth) and explicitly what it does not own (product strategy, engineering people management).",
       "Within [2] quarters we had a levelled ladder, one program bar, [30%] less governance overhead, and every tier-1 initiative had a named accountable owner.",
       "Answer with a MODEL - tiers, reporting line, charter, and what you deliberately do NOT own. Directors describe structure; ICs describe tasks."),
    _q("orgdesign",
       "Centralized vs. embedded TPM - which model do you prefer and why?",
       "We debated pulling TPMs into a central org versus leaving them reporting into each product line.",
       "I had to pick a model that gave both domain depth and a consistent bar.",
       "I chose a hybrid: solid-line into a central TPM function for hiring bar, leveling, calibration and mobility; dotted-line and physically embedded with the product/eng leadership they serve so they keep real context. I made the tie-breaker explicit - the embedded leader sets priorities, the central function sets standards - so nobody was stuck between two bosses.",
       "We kept domain credibility while raising consistency; internal partner satisfaction rose to [4.5/5] and TPM attrition dropped to [under 8%].",
       "Do not pick a side dogmatically - name the trade-off (context vs. consistency), state your default, and say what would make you choose the other."),
    _q("orgdesign",
       "Tell me about a reorg you designed or led.",
       "Delivery was slipping because [3] teams shared ownership of one critical surface and nobody was accountable end-to-end.",
       "I was asked to redesign the structure without losing people or stalling the roadmap.",
       "I started from the WORK, not the org chart: mapped value streams, found where handoffs created the most latency, then drew teams around end-to-end ownership of a surface. I pre-socialized the design one-on-one with every affected leader, named the losers of the change honestly, gave people landing spots before announcement day, and ran a [30/60/90] stabilization plan with explicit success metrics.",
       "Handoffs per feature dropped from [5] to [2], lead time improved [40%], and regretted attrition through the change was [under 5%].",
       "Show the sequence: work first, then structure, then people, then comms. And show you handled the human cost deliberately - that is what separates Director from Senior Director."),
    _q("orgdesign",
       "How do you decide span of control - when do you add a manager?",
       "My function grew from [8] to [22] people in a year and I was becoming the bottleneck on every decision.",
       "I had to decide where to add leadership layers without over-managing a senior team.",
       "I used signals rather than a fixed ratio: decision latency (things waiting on me), coaching debt (how long since each person got real development time), and blast radius (how much damage an unsupported miss would do). Senior ICs need a wider span; junior or high-ambiguity work needs a narrower one. I added leads at [6-8] reports for junior-heavy areas and kept [10-12] where the team was senior and self-directing, and I promoted from within where the bench was ready.",
       "Decision latency dropped from [9] days to [2], and I created [3] internal promotions instead of hiring managers externally.",
       "Give the SIGNALS you watch, not a magic number. Then show you used the growth as a development opportunity for your bench."),
    _q("orgdesign",
       "How do you set up portfolio governance without creating bureaucracy?",
       "We had [6] overlapping review forums and leaders were spending [10+] hours a week in status meetings.",
       "I was asked to give execs visibility while giving teams their time back.",
       "I collapsed everything into one tiered model: a monthly portfolio review for investment-level decisions, a weekly cross-org risk review that only discusses items that are RED or newly changed, and written async status for everything green. I made one rule - a forum exists only to make a DECISION; if it has no decision rights it becomes a document. I killed [4] forums outright.",
       "We cut leadership meeting load by [60%] while exec-reported visibility improved, because the remaining forums were about decisions, not recitation.",
       "The senior signal is DELETING governance. 'A forum without decision rights becomes a document' is the line to land."),
    _q("orgdesign",
       "Describe how you would define the operating cadence for an engineering org.",
       "The org ran on ad-hoc planning; priorities changed mid-quarter and teams were constantly re-planning.",
       "I owned installing a rhythm that created predictability without freezing the roadmap.",
       "I built nested loops: annual strategy and investment allocation, quarterly planning with committed vs. aspirational tiers, monthly business review on metrics, weekly risk and dependency review, and a daily incident path. I paired each loop with one artifact and one owner, and I deliberately left [20%] capacity uncommitted so mid-quarter change could be absorbed without re-planning everything.",
       "Quarterly commitment hit rate went from [55%] to [85%], and mid-quarter re-planning events dropped from [monthly] to [rare].",
       "Name the LOOPS and their frequency, then the artifact and owner for each. Bonus: the uncommitted buffer shows you plan for change instead of pretending it will not happen."),
    _q("orgdesign",
       "Tell me about a time the org structure itself was the root cause of a delivery problem.",
       "A flagship launch slipped [two] quarters and every retro blamed 'coordination', which is a symptom, not a cause.",
       "I had to find the real cause rather than add more coordination.",
       "I traced every slip to a decision that needed [3] VPs to agree because ownership of the shared platform was split three ways. Adding TPMs would have just made the handoffs prettier. I proposed consolidating platform ownership under one leader with a funded charter and a clear API contract to the consuming teams, and I brought the data - decision latency by type - so it was not an opinion fight.",
       "After consolidation the same class of decision moved in [days] not [weeks], and the re-planned launch landed on the revised date.",
       "Great senior answer: show you resisted the reflex to add process, diagnosed structurally, and used data to make an org change palatable."),
    _q("orgdesign",
       "How do you decide when a program needs a dedicated TPM versus shared coverage?",
       "Demand for TPM support was [3x] my supply and every leader believed their program was tier-1.",
       "I needed a defensible allocation model instead of loudest-voice-wins.",
       "I scored programs on four axes - number of teams involved, external commitment or regulatory exposure, ambiguity of the outcome, and cost of being late - and published the rubric. Tier-1 gets a dedicated TPM; tier-2 gets shared coverage plus the standard toolkit; tier-3 gets self-serve templates and no TPM. I reviewed the tiering quarterly and made the unstaffed list visible to execs so the trade-off was theirs, not hidden.",
       "Allocation debates ended, and exposing the unstaffed tier-1 list directly won me [4] additional headcount.",
       "Publish a RUBRIC and make scarcity visible upward. 'I showed them what we were not covering' is how Directors get funded."),

    # ══ Budget, P&L & ROI ═════════════════════════════════════════════════
    _q("finance",
       "Walk me through how you build a business case for a major investment.",
       "I proposed a [$4M] platform re-architecture that had no direct revenue attached to it.",
       "I had to get CFO-level approval against revenue-generating alternatives.",
       "I framed it in the CFO's language: current annual cost of the status quo (incident hours, duplicated builds, slowed feature delivery quantified as delayed revenue), the investment profile by quarter, the expected benefit with a stated confidence range, payback period, and the do-nothing scenario with its risk curve. I brought three options - do nothing, minimal patch, full re-architecture - with honest downsides for mine, and I named the assumptions that would invalidate the case.",
       "It was approved with a [staged] release of funds tied to milestone gates, and we hit payback in [14] months against a projected [18].",
       "Structure: cost of status quo, options with honest downsides, payback period, and the assumptions that would kill your own case. Offering staged funding shows you are a steward, not a spender."),
    _q("finance",
       "Tell me about a time you had to cut budget or headcount.",
       "We were told to reduce our run rate by [15%] mid-year with no change to top-line commitments.",
       "I owned deciding what stopped, and delivering the message.",
       "I refused an across-the-board haircut because it degrades everything equally. I ranked every initiative by strategic value and cost, killed [3] programs entirely rather than starving [10], protected the teams closest to committed customer outcomes, and separated one-time from recurring cost so the savings were real. I told the affected teams myself, in person, before the announcement, and I was explicit that this was a business decision and not a judgment on their work.",
       "We hit the [15%] target, the surviving programs stayed fully funded and on-schedule, and regretted attrition among affected staff was [under 10%].",
       "'Kill three, do not starve ten' is the judgment line. Then show you delivered the message yourself - owning the hard conversation is the executive signal."),
    _q("finance",
       "How do you make a build versus buy decision?",
       "We needed a [workflow orchestration] capability and the team badly wanted to build it.",
       "I had to make a decision that would hold up financially for [5] years.",
       "I asked one question first: is this a differentiator or a commodity? If customers will never choose us because of it, we buy. Then I modelled total cost of ownership honestly - build cost is never just the initial build, it is [3-5] engineers of perpetual maintenance, on-call, and opportunity cost - against vendor licence plus integration plus the switching risk. I also weighed time-to-value and whether buying locked us out of a future differentiator.",
       "We bought, redeployed [4] engineers onto revenue-facing work, and were live in [8] weeks instead of a projected [9] months.",
       "Lead with differentiator vs. commodity, then TCO including perpetual maintenance and opportunity cost. Engineers systematically under-estimate the maintenance tail - say so."),
    _q("finance",
       "Describe how you plan headcount for the year.",
       "I had to submit a headcount ask for a function growing faster than the company's hiring envelope.",
       "I needed an ask that was credible enough to survive the planning cycle.",
       "I built it bottom-up from committed work - demand by tier from the allocation rubric - then tested it top-down against a ratio benchmark so it passed a sanity check. I phased hires by quarter against when the work actually starts, accounted for ramp time and expected attrition, and presented a base ask plus a marginal tier that showed exactly what each additional head would unlock. I also named what I would stop doing if I got zero.",
       "I received [80%] of the ask, and because the marginal tier was explicit, the two roles I did not get came with an agreed reduction in scope rather than an unfunded expectation.",
       "The killer move is the marginal tier - 'here is what head number 5 buys you' - plus naming what you will STOP if funded at zero. That prevents unfunded mandates."),
    _q("finance",
       "Tell me about a time you delivered measurable cost savings.",
       "Our cloud spend was growing [40%] year over year while usage grew [15%].",
       "I owned closing the gap without slowing delivery.",
       "I made cost visible first - per-team dashboards with unit economics (cost per transaction), because unattributed cost is nobody's problem. Then I went after the top three drivers: idle non-production environments, over-provisioned instances, and a data retention policy nobody had revisited in [4] years. I set a target per team rather than dictating solutions, and I let teams keep part of the savings as capacity for their own tech debt.",
       "We reduced spend [28%] (roughly [$2.1M] annualized) in [two] quarters with no reliability regression, and the unit-cost metric stayed flat as usage grew.",
       "'Unattributed cost is nobody's problem' plus letting teams keep some savings shows you understand incentives, not just spreadsheets."),
    _q("finance",
       "How do you quantify ROI for infrastructure work with no direct revenue?",
       "A platform investment kept losing funding rounds to feature work because it had no revenue line.",
       "I had to make the value legible to a finance audience.",
       "I converted it into three quantifiable currencies: cost avoided (incident hours, support load, duplicated effort - all real dollars), velocity unlocked (engineer-days returned per quarter, priced at loaded cost and then at the revenue those days historically produce), and risk reduced (probability times impact of the outage or compliance failure we were preventing). I was explicit about which numbers were measured and which were estimated, with ranges rather than false precision.",
       "The investment was funded, and the engineer-days-returned metric became the standard way our org justified platform work.",
       "Name the three currencies - cost avoided, velocity unlocked, risk reduced - and flag your confidence level per number. Fake precision destroys credibility with a CFO."),
    _q("finance",
       "A program is 40% over budget at mid-year. What do you do?",
       "A [regulatory] program hit [40%] overrun by Q2 with a fixed external deadline.",
       "I owned the recovery plan and the message to the exec sponsor.",
       "First I established the truth - was this a scope problem, an estimation problem, or a burn-rate problem? It was scope creep from [6] uncontrolled additions. I froze scope, re-baselined against the regulatory minimum, moved the rest to a fast-follow, and cut contractor spend. Then I went to the sponsor early with the revised number, the options, and my recommendation - not with a surprise at year end.",
       "We landed the compliance date within [8%] of the original budget and the fast-follow shipped the next quarter.",
       "Diagnose the CATEGORY of overrun first (scope vs. estimate vs. burn) - that is the analytical signal. Then escalate early with options, never a year-end surprise."),
    _q("finance",
       "How do you talk about engineering cost with a CFO?",
       "Our CFO viewed engineering as an undifferentiated cost centre and pushed for flat headcount.",
       "I wanted to shift the conversation from cost to investment portfolio.",
       "I stopped presenting headcount and started presenting an investment portfolio: what percentage of engineering capacity went to run-the-business, grow-the-business, and transform-the-business, with the business outcome attached to each slice. I used unit economics they already trusted (cost per transaction, cost to serve), gave ranges with confidence rather than single numbers, and never over-claimed - when a projection missed, I said so first.",
       "The conversation moved from headcount to portfolio mix, and we secured a [multi-year] platform commitment instead of annual defensive negotiations.",
       "Speak in portfolio mix (run/grow/transform) and unit economics, not headcount. And say plainly that you flag your own misses first - CFO trust is built on that."),

    # ══ Board & Executive Communication ═══════════════════════════════════
    _q("board",
       "How do you structure an update for the board or CEO?",
       "I was asked to present a [multi-year transformation] to the board with [10] minutes and no appetite for detail.",
       "I had to land the message and get a decision, not narrate status.",
       "I led with the answer - BLUF: 'we are on track for [date], we need a decision on [X] today.' Then three things only: the one number that matters, the top risk with the mitigation and its owner, and the specific ask. I put everything else in an appendix and let questions pull the detail out. I never buried bad news, and I gave a confidence level with each date rather than a false-precision commitment.",
       "The board approved the decision in the room, and the CEO adopted the same three-part format for other functional updates.",
       "BLUF, then exactly three things, then the ask - detail lives in the appendix. Boards want a DECISION, not a status report. Never bury bad news past slide one."),
    _q("board",
       "Tell me about a time you delivered bad news to executives.",
       "[Six] weeks before a publicly announced launch date, I concluded we would miss it by [a quarter].",
       "I had to tell the exec team, knowing external commitments were already made.",
       "I went the same day I was confident, not after one more week of hoping. I brought the facts, the root cause, three options with honest trade-offs (cut scope and hold date, hold scope and move date, phase the launch), my recommendation, and what I had already put in motion. I owned the miss without spreading blame across teams, and I named exactly what signal I had missed earlier and what I was changing so it would surface sooner next time.",
       "We took the phased option, communicated externally on our own terms, and the sponsor told me the early honesty increased their trust in the program.",
       "Speed plus options plus ownership. 'The day I was confident, not after one more week of hoping' is the line that shows executive maturity."),
    _q("board",
       "How do you handle an executive who demands a date you do not believe in?",
       "A [SVP] committed to a customer date that my analysis said had roughly a [20%] chance of landing.",
       "I had to push back without being written off as negative.",
       "I did not argue about the date - I made the uncertainty visible. I showed the critical path, the specific assumptions the date depended on, and what would have to be true for it to hold. Then I offered what I could commit to at high confidence, what the date would cost in scope or quality, and a decision point where we could re-evaluate with real data. I made it their informed decision rather than my refusal.",
       "They chose a phased commitment; the first phase landed on the original date and the rest [six] weeks later with the customer aligned in advance.",
       "Never argue date-versus-date. Convert it into assumptions, cost, and a decision point - then let the exec own an informed choice."),
    _q("board",
       "Describe a written document that changed a decision.",
       "The org was heading toward a [buy] decision I believed was strategically wrong, and meeting debate kept going in circles.",
       "I wanted the decision made on analysis rather than on who spoke last.",
       "I wrote a [six-page] narrative - the decision to be made, the options, the data, the strongest version of the opposing case (steel-manned, not straw-manned), my recommendation, and the reversibility of each path. I pre-read it with the two most skeptical leaders and incorporated their objections before it went wide, so their concerns appeared in the document rather than as ambushes in the room.",
       "The group reversed direction in one meeting, and the document became the reference point every time the decision was re-litigated later.",
       "Steel-manning the opposing case and pre-reading with skeptics are both senior moves. Also mention reversibility - one-way vs. two-way doors."),
    _q("board",
       "How do you run a quarterly business review?",
       "Our QBRs had become [3] hours of slide-reading with no decisions coming out.",
       "I owned redesigning the forum to be worth the leadership time it consumed.",
       "I inverted it: metrics and status went out as a written pre-read [48] hours ahead, and the meeting itself was only for the [3] decisions and the [2] escalations that could not be resolved async. I opened with what changed since last quarter and what we got wrong, closed with explicit decisions, owners, and dates, and published notes within [24] hours. Anything that could be an email became one.",
       "The QBR went from [3] hours to [75] minutes and produced [6-8] decisions per session instead of [1-2].",
       "Written pre-read, meeting for decisions only, open with what you got WRONG. Self-criticism first is a strong executive credibility signal."),
    _q("board",
       "Tell me about a time two executives disagreed and you were caught in the middle.",
       "Our [CTO] wanted a full platform rebuild while the [CPO] wanted the quarter spent on customer commitments.",
       "I owned a program that could not proceed until they aligned.",
       "I refused to be the messenger between them. I met each separately to understand the underlying interest rather than the stated position - one feared compounding tech debt, the other feared losing a strategic account. Then I framed a shared objective and brought a single option set to a joint session showing what each path cost the OTHER person's goal, with data. I proposed a split that protected the account commitments while ring-fencing [20%] capacity for the highest-risk platform work.",
       "They aligned in one session, and I was asked to broker the next quarter's allocation as well.",
       "Interests, not positions. Separate conversations first, then ONE joint session with a shared frame - never ping-pong messages between two execs."),
    _q("board",
       "How do you communicate risk without causing panic?",
       "I identified a [single point of failure] that could take down our largest customer's integration.",
       "I needed action and funding without triggering a fire drill that would derail the quarter.",
       "I quantified it - probability, impact, and the specific trigger conditions - rather than describing it as scary. I paired every risk with a named owner, a mitigation, a cost, and a decision date, and I graded it against our other risks so it had proportion. I brought it to the regular risk forum rather than an emergency escalation, because how you escalate signals how urgent it is.",
       "It was funded and mitigated within [one] quarter with no disruption to other commitments, and the graded risk register became standard practice.",
       "Quantify (probability x impact), always pair risk with owner + mitigation + cost, and use the routine forum. The CHANNEL you choose is itself a signal of severity."),
    _q("board",
       "How do you keep exec reporting honest when status gets sanitized on the way up?",
       "I found that programs reported green at team level were arriving red at the exec review with no warning.",
       "I owned making the reporting chain trustworthy.",
       "I attacked the incentive, not the people. I defined objective criteria for red/amber/green so status was not a matter of optics, made 'red' a request for help rather than a mark of failure, and publicly thanked the first leader who turned something red early. I added a thin independent check - I sampled a few programs directly each month - and I never punished the messenger, which is the only thing that actually keeps the channel open.",
       "Average time from a problem appearing to it being visible at exec level dropped from [5] weeks to [under 1], and we stopped having surprise reds at quarter end.",
       "'Watermelon status' - green outside, red inside - is an incentive problem. Objective criteria, red-as-a-request-for-help, and visibly rewarding the first early red."),

    # ══ Talent, Culture & Org Health ══════════════════════════════════════
    _q("talent",
       "How do you hire senior TPMs - what is your bar?",
       "I had to grow the function by [10] senior hires in a market where the title means wildly different things.",
       "I owned defining a bar that would hold up as multiple hiring managers scaled it.",
       "I defined the bar on four dimensions: structured thinking under ambiguity, influence without authority, technical depth sufficient to be credible with staff engineers, and executive communication. I built a loop where each dimension had a named owner and a written rubric, added a work-sample exercise (walk a real messy program) instead of relying on hypotheticals, and required a written debrief before the room to prevent anchoring. I also held the bar personally - I would rather run short than lower it.",
       "Offer-accept rate reached [85%], and [90%] of hires from that loop were rated meets-or-exceeds at [12] months.",
       "Name your dimensions, one owner per dimension, work sample over hypotheticals, written debrief before discussion. 'I would rather run short than lower the bar' - then give an example of doing it."),
    _q("talent",
       "Tell me about a time you had to manage out a leader.",
       "A director on my team was technically strong but was driving attrition through how they treated their org.",
       "I owned addressing it, knowing they were seen as high-performing on delivery.",
       "I gave direct, specific feedback with examples rather than vague signals, set clear behavioural expectations with a timeline, and provided real support - coaching and a peer mentor. I documented honestly throughout. When the behaviour did not change within [two] months, I acted rather than waiting out another cycle. I handled the exit with dignity and I told their org only what was appropriate, without narrating the reasons.",
       "Team engagement in that group rose [20] points within [two] quarters and two people who had been about to resign stayed.",
       "The senior version: I moved too slowly is often the honest reflection. Say that results do not excuse behaviour, and that you gave real support before acting."),
    _q("talent",
       "How do you build a succession plan?",
       "I realized [three] critical roles in my org, including my own, had no ready successor.",
       "I owned de-risking the org against key-person dependency.",
       "I mapped every critical role and rated the bench as ready-now, ready-in-a-year, or a gap. For ready-soon people I created real stretch - having them run a forum I owned, lead a cross-org program, or present to the exec team with me in the room but silent. For the gaps I hired ahead or built a deliberate development plan. I reviewed the map with my leadership twice a year and I was explicit with people about what they were being developed FOR, without over-promising a specific job.",
       "Within [18] months two roles were filled internally and my own successor was identified, and the leadership bench depth doubled.",
       "Concrete stretch mechanisms beat generic 'I develop people'. Also handle the promise problem - 'developed for, not promised' is the mature framing."),
    _q("talent",
       "Describe how you handled a spike in attrition.",
       "We lost [4] senior engineers in [one] quarter, roughly double our normal rate.",
       "I had to understand the cause before reacting to the symptom.",
       "I read the exit interviews but did not trust them alone - people are polite on the way out - so I ran skip-levels with the people still there, which is where the truth is. The pattern was not compensation; it was lack of growth path and frustration with a decision process that ignored their input. I published a leveling guide with concrete examples, created two staff-level roles that had not existed, and changed how technical decisions were made so senior engineers had real authority.",
       "Attrition returned to [under 8%] within [two] quarters and we re-hired [two] of the leavers.",
       "'Exit interviews are polite, skip-levels are honest' is a strong line. Then show you fixed the SYSTEM (levels, decision rights), not just made a counter-offer."),
    _q("talent",
       "How do you calibrate performance fairly across teams?",
       "Ratings varied wildly between managers - one gave [40%] top ratings, another gave [5%].",
       "I owned making the process fair enough that people trusted it.",
       "I ran calibration with written evidence against level expectations rather than manager advocacy skill, required each manager to compare their people against peers at the same level across teams rather than only within their own, and challenged both the inflating and the harsh manager with the same rigour. I watched for the usual bias patterns - recency, visibility of loud work over quiet critical work, and proximity - and I named them out loud in the room when they appeared.",
       "Rating distributions converged, and the internal survey question on 'performance is evaluated fairly' rose [18] points.",
       "Evidence against level, cross-team comparison, and naming bias patterns in the room. Mention protecting the quiet high-impact work - that shows real judgment."),
    _q("talent",
       "How do you develop the next layer of leaders under you?",
       "My leadership team could execute well but escalated most cross-org decisions to me.",
       "I wanted leaders who operated at my level, not senior executors.",
       "I gave away real scope rather than tasks - each of them owned a company-level outcome with the exposure that came with it, including presenting to the exec team without me speaking. I coached with questions rather than answers, and I deliberately let them make reversible mistakes and then debriefed rather than intervening. I paired that with explicit feedback on the gap between their current altitude and the next one.",
       "Two were promoted within [a year], my escalation load dropped by [half], and the function kept running unchanged during a [six-week] absence.",
       "'The function ran fine while I was away' is the proof point. Give scope not tasks, coach with questions, allow reversible mistakes."),
    _q("talent",
       "Tell me about the culture you have built and how you enforced it.",
       "I took over a function where being the smartest voice in the room was rewarded and bad news travelled slowly.",
       "I wanted a culture of directness without cruelty, and early truth.",
       "I named the values concretely in behavioural terms - disagree openly then commit, escalate early, no surprises - and then made them real through what I rewarded and tolerated. I publicly thanked the first person to raise a red early, I gave hard feedback to a top performer whose behaviour violated the norms so people saw the standard applied at the top, and I modelled it myself by publishing my own mistakes in writing.",
       "Time-to-surface problems dropped sharply, and the function's engagement score on 'I can speak up' rose to [top quartile].",
       "Culture answers are only credible with ENFORCEMENT examples. The top performer you corrected is the proof - values that cost you nothing are not values."),
    _q("talent",
       "How do you keep a distributed or hybrid organization connected?",
       "My org spanned [3] time zones and the remote sites were consistently getting decisions made without them.",
       "I owned making location irrelevant to influence.",
       "I moved the default to written and async so decisions were legible to everyone rather than made in hallways, rotated meeting times so the same region was not always inconvenienced, and required that any decision made verbally be written up within [24] hours. I invested the travel budget in a small number of high-value in-person moments - planning and team formation - rather than spreading it thin, and I tracked promotion and visibility rates by location to check whether proximity bias was real.",
       "Promotion rates equalized across sites within [a year], and remote-site engagement matched headquarters for the first time.",
       "Measuring promotion rate BY LOCATION is the standout detail - it turns proximity bias from a belief into a metric you manage."),
]

# Derive searchable theme tags for every question.
for _q_item in QUESTIONS:
    _q_item["tags"] = _beh_tags(_q_item)


# ══ Difficulty, frequency & the "how to remember" hook ════════════════════
# Difficulty here is not "is the question hard to understand" - they are all
# plain English. It is how hard the question is to answer WELL at Senior
# Director / Head-of-TPM altitude, where a competent program-manager answer
# reads as junior. Anything needing real org, money or board numbers is Hard,
# because you cannot improvise those in the room.
_CAT_DIFFICULTY = {
    # Exec-depth: needs figures, org context and a point of view you have
    # actually held. These are where Director+ candidates get sorted.
    "board": "Hard",
    "finance": "Hard",
    "orgdesign": "Hard",
    "talent": "Hard",
    "strategy": "Hard",
    "failure": "Hard",          # the honesty/altitude trap question
    "conflict": "Hard",         # easy to answer defensively and lose the room
    # Core senior-PM ground, still expected to be crisp and quantified.
    "leadership": "Medium",
    "delivery": "Medium",
    "stakeholders": "Medium",
    "prioritization": "Medium",
    "influence": "Medium",
    "risk": "Medium",
    "decision": "Medium",
    "people": "Medium",
    "ambiguity": "Medium",
    "communication": "Medium",
    "collaboration": "Medium",
    "customer": "Medium",
    "growth": "Medium",
}

# How often this comes up in a Senior Director / Head-of-TPM loop specifically.
# Not "in interviews generally" - the mix shifts sharply upward at this level:
# execution questions shrink, org design and money grow.
_CAT_FREQUENCY = {
    "leadership": "Asked in essentially every loop - usually the opening question of at least one round.",
    "delivery": "Asked in essentially every loop - this is the baseline competence check.",
    "stakeholders": "Asked in essentially every loop, and almost always by the hiring manager.",
    "conflict": "Asked in essentially every loop - frequently as the follow-up to a delivery story.",
    "failure": "Asked in essentially every loop. At Director+ a shallow answer here is disqualifying.",
    "prioritization": "Very frequently asked - expect it from the product or business partner on the panel.",
    "influence": "Very frequently asked - it is the defining skill of the role and panels probe it hard.",
    "orgdesign": "Very likely at this level - often the round that separates Director from Senior Director.",
    "strategy": "Very likely at this level - usually from the skip-level or the exec panel.",
    "risk": "Commonly asked, often as a scenario rather than a 'tell me about a time'.",
    "decision": "Commonly asked, usually probing your judgment under incomplete information.",
    "communication": "Commonly asked, and continuously assessed by HOW you answer everything else.",
    "talent": "Expected at Head-of-function level - you are being hired to build the org, not just run it.",
    "finance": "Expected at Head-of-function level and a common gap in TPM candidates - a real differentiator.",
    "board": "Expected at Head-of-function level - asked by the exec panel and often decisive.",
    "people": "Commonly asked, especially if the role has direct reports.",
    "collaboration": "Commonly asked, though at this level it is usually folded into influence or conflict.",
    "ambiguity": "Commonly asked - the 'no clear owner, no clear requirements' scenario.",
    "customer": "Sometimes asked - more often in product-led companies than platform orgs.",
    "growth": "Sometimes asked, usually near the end of the loop or by the recruiter.",
}

# One memory hook per theme: the SHAPE of a strong answer, not its content.
# Under pressure you will not recall a script - you will recall a shape.
_CAT_HOOK = {
    "leadership": "Lead with the DECISION you owned, not the project you ran. 'I decided X against Y advice, here is the evidence, here is what it cost.' Ownership shows in what you chose, not what you coordinated.",
    "delivery": "Do not narrate the plan. Name the constraint, the mechanism you built to manage it, and the number at the end. Mechanism beats effort - 'I built a weekly risk review with named owners' beats 'I worked closely with the teams'.",
    "stakeholders": "Name the DISAGREEMENT and how you resolved it. A stakeholder story with no tension in it is a status report. Show you changed a senior person's mind, or that you changed yours with evidence.",
    "conflict": "Be generous about the other side's reasoning before you say what you did. The panel is testing whether you can be right without being contemptuous. Then land it on a shared metric, not on hierarchy.",
    "failure": "Own it in the first sentence, no shared blame, no 'we'. Then the SYSTEM fix, not the personal resolution - 'I now do X' is junior, 'I changed the mechanism so it cannot recur' is senior. Give the cost in numbers.",
    "prioritization": "Say what you KILLED and who was unhappy. Anyone can list what they funded. Naming the thing you stopped, and the exec you disappointed, is what makes it a real prioritization answer.",
    "influence": "No authority means no mandate, so show the currency you used: data, a coalition, a pilot, or reframing their goal as yours. Name which one and why it fit that person.",
    "risk": "Distinguish the risk you MANAGED from the one you ACCEPTED. Senior people accept risks deliberately and say so out loud, with the trigger that would change their mind.",
    "decision": "State the decision, the information you did NOT have, and the reversibility. One-way versus two-way door is the language they want, and the speed should follow the door.",
    "people": "Concrete behaviour, concrete feedback, concrete outcome - including the time it did not work out and you exited someone. Managers who have never exited anyone read as untested.",
    "strategy": "Start from the business outcome, not the roadmap. Then the bet you made, what you deliberately did NOT do, and the leading indicator you watched to know if you were wrong.",
    "communication": "BLUF - answer first, then at most three supporting points, then the ask. Demonstrate it in HOW you answer this question, because they are grading the delivery as much as the content.",
    "collaboration": "Show the seam you fixed between two functions, not the meeting you ran. The interesting part is always where the handoff was broken and what you changed structurally.",
    "ambiguity": "Show how you MANUFACTURED clarity - a written doc, a forced decision, a time-boxed spike - rather than waiting for it. Ambiguity answers are about the mechanism you imposed.",
    "customer": "Tie it to a number the business cares about, then to a customer behaviour you actually observed. Second-hand customer empathy is transparent.",
    "growth": "Name a real, current gap and the specific thing you are doing about it. A fake weakness ('I care too much') is the fastest way to lose credibility at this level.",
    "orgdesign": "Structure follows the decisions you want made fastest. Say which decisions were slow, what you changed (reporting lines, decision rights, forums), and what got worse - every org change trades something away.",
    "finance": "Talk in unit economics and opportunity cost, not budget size. 'I moved $Xm from A to B because the return per engineer was 3x' is the register. Know your numbers cold.",
    "board": "BLUF, exactly three things, then the ask. Boards want a DECISION, not status. Never bury bad news past the first slide, and give confidence levels rather than false-precision dates.",
    "talent": "Show the system you built - levels, calibration, growth paths - not the individual you saved. And show you applied the standard to a top performer, because values that cost nothing are not values.",
}

for _q_item in QUESTIONS:
    _q_item.setdefault("difficulty", _CAT_DIFFICULTY.get(_q_item["cat"], "Medium"))
    _q_item.setdefault("frequency", _CAT_FREQUENCY.get(
        _q_item["cat"], "Commonly asked at senior program-leadership level."))
    _q_item.setdefault("mnemonic", _CAT_HOOK.get(_q_item["cat"], ""))


# ══ Signature stories ═════════════════════════════════════════════════════
# The single biggest efficiency in behavioral prep: you do not need 134
# answers, you need about eight REAL stories, each rehearsed until you can
# tell it in two minutes, and the ability to re-aim one at whatever was
# actually asked. Every question below is mapped to the story that most
# naturally covers it, so you can see your coverage and prepare by STORY
# rather than by question.
STORY_SLOTS = {
    "turnaround": {
        "label": "The rescue",
        "brief": "A programme that was late, failing or off the rails when you took it, and what you changed. Your workhorse - it covers delivery, risk, conflict and leadership at once.",
    },
    "scale": {
        "label": "The scale-up",
        "brief": "Taking something from working-at-small-scale to working at 10x - traffic, headcount, markets or teams. Shows systems thinking rather than heroics.",
    },
    "org": {
        "label": "The org change",
        "brief": "A reorg, an operating-model change, or a decision-rights redesign you led. The story that proves you operate ABOVE the programme layer.",
    },
    "conflict": {
        "label": "The hard disagreement",
        "brief": "A senior person you disagreed with, and how it resolved - including a version where you were the one who changed their mind.",
    },
    "failure": {
        "label": "The failure",
        "brief": "Something that genuinely went wrong under your ownership, with the cost in numbers and the systemic fix. Must be real; panels can smell a safe one.",
    },
    "money": {
        "label": "The money call",
        "brief": "A budget, buy-versus-build, headcount or investment decision you owned, in unit economics. The most common gap in TPM candidates.",
    },
    "people": {
        "label": "The people call",
        "brief": "Growing someone into a bigger role, and separately, exiting someone. You need both halves - only the happy one reads as untested.",
    },
    "exec": {
        "label": "The exec moment",
        "brief": "Delivering hard news, or a decision, to a board or exec staff - and what you did when it did not land the first time.",
    },
}

# Which story each theme naturally draws on. A question can be answered from a
# different story if it fits better - this is a starting map, not a rule.
_CAT_STORY = {
    "delivery": "turnaround", "risk": "turnaround", "leadership": "turnaround",
    "ambiguity": "turnaround", "customer": "scale", "strategy": "scale",
    "orgdesign": "org", "collaboration": "org", "communication": "exec",
    "board": "exec", "stakeholders": "exec", "conflict": "conflict",
    "influence": "conflict", "decision": "conflict", "failure": "failure",
    "growth": "failure", "finance": "money", "prioritization": "money",
    "people": "people", "talent": "people",
}
for _q_item in QUESTIONS:
    _q_item.setdefault("story", _CAT_STORY.get(_q_item["cat"], "turnaround"))
    _q_item["story_label"] = STORY_SLOTS[_q_item["story"]]["label"]


# ══ Prep time & stack rank ════════════════════════════════════════════════
# prep_minutes is NOT reading time. Preparing a behavioral answer properly
# means: pick your real story, write the STAR, dig out the actual numbers,
# say it out loud twice, and cut it to two minutes. That is the work being
# costed here, which is why nothing is under ten minutes.
_CAT_PREP_MIN = {
    # Exec-depth answers need real figures you may have to go and find.
    "board": 30, "finance": 30, "orgdesign": 28, "talent": 25, "strategy": 25,
    # The high-stakes narrative answers - worth rehearsing until they are tight.
    "failure": 25, "conflict": 22, "influence": 20, "risk": 18, "decision": 18,
    # Core ground you can build once and re-aim.
    "leadership": 18, "delivery": 18, "stakeholders": 18, "prioritization": 18,
    "people": 18, "ambiguity": 15, "communication": 15, "collaboration": 15,
    "customer": 15, "growth": 12,
}


def _tpm_prep_minutes(q):
    mins = _CAT_PREP_MIN.get(q["cat"], 18)
    # A longer model answer carries more moving parts to internalise.
    _words = len((q.get("a") or "").split())
    mins += min(10, _words / 20.0)
    if q.get("difficulty") == "Hard":
        mins += 5                      # needs real numbers, so needs digging
    mins = max(10, min(60, mins))
    return int(round(mins / 5.0) * 5)


for _q_item in QUESTIONS:
    _q_item.setdefault("prep_minutes", _tpm_prep_minutes(_q_item))
    _m = _q_item["prep_minutes"]
    _q_item["prep_label"] = f"{_m} min" if _m < 60 else "1h"


# The questions that are close to guaranteed in a Head-of-TPM loop. These get
# a large boost so they sit at the very top of the study order regardless of
# what the category heuristic says.
_MUST_PREP = {
    # Verified against the actual question text in this bank. These are the
    # ones a Head-of-TPM loop asks in some form almost every time, plus the
    # exec-depth questions that most reliably separate candidates.
    "Describe a time you led without any formal authority.",
    "Tell me about the most complex program you've delivered.",
    "Tell me about a time you failed.",
    "Describe a time you had to recover a failing program.",
    "Tell me about a conflict with a peer or stakeholder.",
    "Describe a time you had to say no to a senior leader.",
    "Describe delivering bad news to leadership.",
    "Tell me about managing senior/executive stakeholders.",
    "Tell me about handling competing priorities.",
    "Describe a hard trade-off you made.",
    "Tell me about influencing people you had no authority over.",
    "Describe managing a crisis or major incident.",
    "Tell me about how you track and drive a program to completion.",
    "Describe a time you cut scope to hit a date.",
    "Tell me about setting a vision or strategy for your area.",
    "How would you design the TPM function for a company at our scale?",
    "Centralized vs. embedded TPM - which model do you prefer and why?",
    "How do you structure an update for the board or CEO?",
    "Tell me about a time you delivered bad news to executives.",
    "How do you handle an executive who demands a date you do not believe in?",
    "Walk me through how you build a business case for a major investment.",
    "How do you make a build versus buy decision?",
    "How do you quantify ROI for infrastructure work with no direct revenue?",
    "How do you hire senior TPMs - what is your bar?",
    "Tell me about a time you had to manage out a leader.",
    "Describe a decision you made with imperfect data.",
    "Describe a time you changed your mind.",
    "Why this role, and why you? (positioning)",
    "Tell me about a time the org structure itself was the root cause of a delivery problem.",
    "How do you set up portfolio governance without creating bureaucracy?",
}

_CAT_RANK_WEIGHT = {
    # What a Head-of-TPM loop actually weights most heavily.
    "leadership": 3.0, "delivery": 2.9, "stakeholders": 2.9, "failure": 2.9,
    "influence": 2.8, "conflict": 2.8, "prioritization": 2.7,
    "orgdesign": 2.7, "strategy": 2.6, "risk": 2.5, "decision": 2.5,
    "board": 2.5, "communication": 2.4, "finance": 2.4, "talent": 2.3,
    "people": 2.2, "ambiguity": 2.1, "collaboration": 2.0,
    "customer": 1.8, "growth": 1.6,
}


def _tpm_freq_tier(q):
    f = (q.get("frequency") or "").lower()
    if "essentially every loop" in f:
        return 3.0
    if "very frequently" in f or "very likely" in f or "expected at head" in f:
        return 2.4
    if "commonly" in f:
        return 1.8
    return 1.2


def _tpm_rank_score(q):
    score = 3.0 * _tpm_freq_tier(q)
    score += 2.0 * _CAT_RANK_WEIGHT.get(q["cat"], 2.0)
    if q["q"] in _MUST_PREP:
        score += 3.0
    # Cheap-and-common goes first: a 15-minute answer asked every time beats a
    # 30-minute one asked sometimes. Capped so the short ones cannot sweep.
    score += min(1.5, 30.0 / max(10, q.get("prep_minutes", 18)))
    return score


_ordered = sorted(QUESTIONS, key=lambda q: (-_tpm_rank_score(q), q["cat"], q["q"]))
_total = len(_ordered)
for _i, _q_item in enumerate(_ordered, 1):
    _q_item["rank"] = _i
    _pct = _i / _total
    _q_item["priority"] = ("P0" if _pct <= 0.18 else
                           "P1" if _pct <= 0.45 else
                           "P2" if _pct <= 0.75 else "P3")

_percat = {}
for _q_item in _ordered:
    _percat[_q_item["cat"]] = _percat.get(_q_item["cat"], 0) + 1
    _q_item["cat_rank"] = _percat[_q_item["cat"]]

_PRIORITY_NOTE = {
    "P0": "P0 - prepare these first. Near-certain to be asked, and a weak answer here costs you the loop.",
    "P1": "P1 - core. Expect several of these; have a story ready for each.",
    "P2": "P2 - depth. Prepare once P0 and P1 are rehearsed out loud.",
    "P3": "P3 - long tail. Skim for the shape; do not spend rehearsal time here.",
}
for _q_item in QUESTIONS:
    _q_item["priority_note"] = _PRIORITY_NOTE[_q_item["priority"]]

#: Total preparation time for the whole behavioral bank, in minutes.
TOTAL_PREP_MINUTES = sum(q["prep_minutes"] for q in QUESTIONS)


# ══ Follow-up probes & the strong/weak contrast ═══════════════════════════
# At Director+ the FIRST answer is never the test. You give a competent STAR,
# and then they push - "why that and not X?", "what would you do differently
# at 3x the scale?", "who disagreed?" - and the round is decided in those two
# minutes. Rehearsing the story without rehearsing the pushback is the single
# most common preparation gap.
#
# `probes` is what they will actually ask next. `strong_weak` is the contrast
# that separates a hire from a no-hire on that specific question - not generic
# advice, but what the good version sounds like against the mediocre one.
#
# Applied to the P0 set first, since those are near-certain to come up.
_PROBES = {}
_STRONG_WEAK = {}


def _P(title, probes, strong_weak):
    _PROBES[title] = probes
    _STRONG_WEAK[title] = strong_weak.strip("\n")


_P("Describe a time you led without any formal authority.",
   ["Who was the hardest person to bring along, and what specifically changed "
    "their mind?",
    "What would you have done if they had simply refused?",
    "How is this different from what you would have done WITH authority?",
    "Did you ever have to escalate? Why or why not?",
    "How long did it take to get alignment, and was that acceptable?"],
   """STRONG: names the specific CURRENCY you used - data, a pilot, a coalition,
or reframing their goal as yours - and says why that currency fitted that person.
Ends with the mechanism that made the alignment stick after the moment passed.

WEAK: "I built relationships and communicated well." Every candidate says this
and it distinguishes nobody. Also weak: a story where the influence worked
because you were secretly senior, or because an executive intervened - that is
authority, borrowed.

THE DETAIL THAT LANDS: naming someone you did NOT convince, and what you did
about the residual risk. It proves the story is real.""")

_P("Describe a time you cut scope to hit a date.",
   ["Who pushed back hardest, and how did that conversation end?",
    "What did you cut that you now think you should have kept?",
    "How did you decide WHAT to cut rather than how much?",
    "Did the customer notice?",
    "Would you have made the same call if the date had been soft?"],
   """STRONG: a stated decision RULE for what gets cut - what is load-bearing for
the launch promise versus what is desirable - plus the named person you
disappointed and how you handled them. Quantifies what shipping late would have
cost.

WEAK: "we descoped the nice-to-haves." That is a tautology; nice-to-haves are
defined as the things you cut. Say the actual features and the actual argument.

THE TRAP: describing a cut nobody objected to. If it was uncontroversial it was
not a trade-off, and the interviewer will read it as a soft example.""")

_P("Tell me about how you track and drive a program to completion.",
   ["What would tell you in week three that the date is at risk?",
    "How do you stop status being sanitised on the way up to you?",
    "What do you do personally versus what does the mechanism do?",
    "Which of your metrics would you drop if you could keep only two?",
    "Give me an example where your tracking caught something early."],
   """STRONG: names LEADING indicators - milestone date volatility, ageing
cross-team dependencies, integration test pass rate, buffer burn - and explains
what each would have caught. Treats "how bad news travels" as part of the answer,
not an afterthought.

WEAK: a list of artifacts - RAID log, RACI, weekly status, a dashboard. Artifacts
are not mechanisms. If you name one, immediately say what decision it drives and
what behaviour it changes.

THE DETAIL THAT LANDS: "if my dashboard is always green until it is suddenly red,
that is a culture problem I caused, not a measurement problem."''""")

_P("Tell me about the most complex program you've delivered.",
   ["What made it complex - scale, ambiguity, politics, or technology?",
    "What would have happened if you had not been there?",
    "What was the single decision that most changed the outcome?",
    "What did you get wrong?",
    "How would you run it differently today?"],
   """STRONG: defines the complexity precisely - twelve teams and three
regulators is a different problem from one team and an impossible deadline - then
narrates the two or three DECISIONS that mattered rather than the whole timeline.
Ends with a number.

WEAK: a chronological walk through the project. Interviewers stop listening
around minute three. Compress the situation into thirty seconds and spend the
time on the judgement calls.

THE TRAP: complexity described as effort ("it was very challenging, lots of
moving parts"). Complexity is structural - name the structure.""")

_P("Describe delivering bad news to leadership.",
   ["How much notice did they have before you told them?",
    "What did you bring besides the bad news?",
    "How did they react, and what did you do with that?",
    "Had you flagged the risk earlier? If not, why not?",
    "What changed afterwards so it would not happen again?"],
   """STRONG: told them EARLY, arrived with options and a recommendation rather
than a problem, took ownership without dramatising, and named the mechanism that
stopped a repeat. Ideally shows a moment where you volunteered news nobody had
asked for yet.

WEAK: a story where the bad news was already obvious to everyone, or where you
delivered it and the answer was simply "we moved the date". No options means no
judgement on display.

THE DETAIL THAT LANDS: "I would rather be the person who tells you in week four
than the person who is right in week twelve." Say the principle, then the
story.""")

_P("Tell me about managing senior/executive stakeholders.",
   ["Tell me about one you could NOT align. What happened?",
    "How do you handle two executives who want opposite things?",
    "What do you do when an exec keeps changing their mind?",
    "How do you say no to someone three levels above you?",
    "How do you know what they actually care about?"],
   """STRONG: shows a real DISAGREEMENT and how it resolved - including a version
where you changed your own mind on evidence. Demonstrates that you tailor to what
each executive optimises for rather than sending everyone the same update.

WEAK: "I kept them informed with regular updates and built trust." A stakeholder
story with no tension in it is a status report, and the interviewer will probe
until they find the tension or conclude there was none.

THE TRAP: describing management as communication frequency. Executives do not
want more updates; they want fewer, sharper ones with a decision attached.""")

_P("Describe a time you had to recover a failing program.",
   ["What did you find that the status reports had not shown?",
    "Was it scope growth, bad estimates, or blocked execution?",
    "Did you replace anyone? Why or why not?",
    "How did you rebuild credibility with the exec sponsor?",
    "What was in place at the end that had not been there before?"],
   """STRONG: separates the three causes - scope grew, estimates were wrong,
execution was blocked - and says which it was, because the fix differs entirely.
Gets ground truth BEFORE re-planning. Ends with a mechanism, not a heroic sprint.

WEAK: a rescue narrated as personal effort - "I worked weekends, I got everyone
in a room, I drove it home." That reads as someone who can be a hero once, not
someone who can run a portfolio.

THE DETAIL THAT LANDS: refusing to give a new date in week one, and saying what
you told the sponsor instead.""")

_P("Tell me about a time you failed.",
   ["What did it cost, in money or time or trust?",
    "At what point could you have caught it, and why did you not?",
    "What did you change about how you work?",
    "Has that change been tested since?",
    "Who else was affected, and how did you handle them?"],
   """STRONG: a real failure with your name on it, owned in the first sentence
with no shared blame and no "we". Quantifies the cost. The fix is SYSTEMIC - a
changed mechanism - not a personal resolution to try harder.

WEAK: a disguised strength ("I was too ambitious"), a failure that was really
someone else's, or one so small it cost nothing. At this level, a soft failure
answer is read as either evasion or a shallow career.

THE TEST: "I now do X" is junior. "I changed the process so it cannot happen
again, and here is the evidence it held" is senior. That is the whole
difference.""")

_P("Describe a time you had to say no to a senior leader.",
   ["What did you offer instead of just refusing?",
    "How did they take it, and what did you do next?",
    "Have you ever said no and been overruled? What then?",
    "How do you decide when it is worth spending the capital?",
    "What would have happened if you had said yes?"],
   """STRONG: never a flat no - always "not that, but here are two things I can
do, and here is what each costs". Shows you understood WHY they wanted it before
declining. If overruled, you committed fully and wrote the risk down once.

WEAK: a story where you were obviously right and they obviously wrong, told with
a hint of satisfaction. Panels notice contempt, and it is disqualifying at
leadership level.

THE DETAIL THAT LANDS: naming the cost of the no - what it spent politically -
which shows you understand that saying no is a finite resource.""")

_P("Tell me about a conflict with a peer or stakeholder.",
   ["What was their case, stated as they would state it?",
    "What did you concede?",
    "How is the relationship now?",
    "Would they tell this story the same way?",
    "When would you have escalated?"],
   """STRONG: presents the other side's reasoning GENEROUSLY and accurately
before saying what you did. Lands the resolution on a shared metric or a jointly
agreed experiment rather than on hierarchy. Names something you gave up.

WEAK: a conflict where you were entirely right, resolved by escalation, with the
other party characterised as unreasonable or political. That answer tells the
panel how you will describe THEM one day.

THE QUESTION BEHIND THE QUESTION: can you be right without being contemptuous?
The generosity you show the absent party is the actual signal.""")

_P("Tell me about influencing people you had no authority over.",
   ["What did you try first that did not work?",
    "How did you find out what they actually cared about?",
    "Did you use data, a pilot, a coalition, or reframing - and why that one?",
    "How did you keep it aligned after the initial agreement?",
    "Who is the hardest type of person for you to influence?"],
   """STRONG: names the specific lever and why it suited that person, and
includes a first attempt that FAILED. Real influence stories have a false start;
frictionless ones sound rehearsed.

WEAK: "I built trust and showed them the benefits." Also weak: influence that was
really just persistence, or that worked because their manager told them to.

THE DETAIL THAT LANDS: how you made the change durable once you were no longer
in the room - because influence that evaporates when you look away is not
influence.""")

_P("Describe a hard trade-off you made.",
   ["What was the case FOR the option you rejected?",
    "Who was hurt by the decision, and how did you handle them?",
    "What information would have changed your mind?",
    "Was it reversible? Did that affect how fast you moved?",
    "Looking back, was it right?"],
   """STRONG: presents the rejected option as genuinely attractive - if it was
obviously worse, it was not a trade-off. Names who lost, states the decision
criterion, and distinguishes one-way from two-way doors.

WEAK: a "trade-off" between a good option and a bad one, which is just a
decision. Or a trade-off with no named loser, which means nobody cared.

THE DETAIL THAT LANDS: "here is what would have made me choose differently" -
it shows the decision was reasoned rather than rationalised afterwards.""")

_P("Tell me about handling competing priorities.",
   ["What did you STOP doing?",
    "Who was unhappy, and did you tell them yourself?",
    "How did you decide - what was the actual criterion?",
    "What happened when a new priority arrived mid-quarter?",
    "How did you protect the team from thrash?"],
   """STRONG: leads with what was KILLED and who was disappointed. Names the
objective everything was ranked against. Shows a published not-doing list or an
equivalent mechanism that stopped the argument recurring weekly.

WEAK: "I prioritised using a framework and communicated the plan." Frameworks are
free; the hard part is holding the line, and that is what the story should be
about.

THE DETAIL THAT LANDS: telling the people whose work was cut yourself, before
the list was published. It costs an hour and it is the difference between a plan
that survives and one that gets relitigated.""")

_P("Describe a time you grew someone into a bigger role.",
   ["What was the gap, specifically?",
    "What did you give away that was uncomfortable to give away?",
    "Did they make a mistake on your watch? What did you do?",
    "How did you know they were ready?",
    "Tell me about someone who did NOT work out."],
   """STRONG: gave real SCOPE with real exposure rather than tasks, coached with
questions instead of answers, and deliberately allowed reversible mistakes. The
proof point is what they achieved without you - a promotion, or the function
running unchanged while you were away.

WEAK: mentoring described as regular one-to-ones and encouragement. That is
management hygiene, not development.

THE PAIRED STORY YOU NEED: have the one that did not work out ready too. Leaders
who have only success stories here read as untested, and the follow-up is
coming.""")

_P("Describe leading a high-stakes initiative with a tight, immovable deadline.",
   ["What made the date genuinely immovable?",
    "What did you sacrifice to hold it?",
    "How did you know in week two whether it was achievable?",
    "What was your fallback if it slipped?",
    "How did you protect the team from burning out?"],
   """STRONG: says immediately that with a fixed date, SCOPE is the only
variable - and shows the tiering agreed up front rather than negotiated in the
final month. Names the early signal that told you the date would hold.

WEAK: a story where the date was hit through overtime and heroics. It answers the
question and fails the seniority test - the panel is listening for mechanism, not
stamina.

THE DETAIL THAT LANDS: agreeing the must-have / should-have / nice-to-have tiers
at the START, when the conversation is abstract and unemotional.""")

_P("Give an example of motivating a demotivated or burned-out team.",
   ["What had actually caused it?",
    "What did you change structurally rather than emotionally?",
    "Did anyone leave anyway?",
    "How did you measure whether it worked?",
    "What would you spot earlier next time?"],
   """STRONG: diagnoses the CAUSE before acting - repeated thrash, no visible
progress, unclear ownership, an impossible commitment - and fixes the structure
that produced it. Morale is a symptom; the story should be about what you removed.

WEAK: motivation through recognition, team events and encouragement. Those help
at the margin and nobody was demotivated because of insufficient pizza.

THE DETAIL THAT LANDS: killing a workstream or renegotiating a commitment to give
the team a winnable goal. Removing something is usually the intervention that
works.""")

_P("Tell me about a time you led a team through a major change.",
   ["Who resisted, and were they right about anything?",
    "What did you communicate, and how often?",
    "What did you get wrong in the rollout?",
    "How did you know the change had actually taken?",
    "What did the change cost that you did not anticipate?"],
   """STRONG: takes the resistance seriously and concedes where the resisters had
a point. Distinguishes announcing a change from embedding it, and names how you
knew it had stuck - a behaviour that persisted after you stopped pushing.

WEAK: change described as a communication plan. Also weak: no resistance at all,
which means either it was not a major change or you did not hear the objections.

THE DETAIL THAT LANDS: what you changed about the plan BECAUSE of the pushback.
It shows the consultation was real rather than theatre.""")

_P("Tell me about a time you made an unpopular decision.",
   ["Who was most against it, and did you speak to them directly?",
    "What did you do to make it easier to accept?",
    "Was it still right in hindsight?",
    "How do you distinguish unpopular-and-right from unpopular-and-wrong?",
    "Did anyone leave over it?"],
   """STRONG: explains the reasoning in terms the objectors would recognise,
shows you delivered it yourself rather than through a proxy, and holds the
position without needing to be proved right by the outcome.

WEAK: unpopular decisions where the unpopularity was mild, or where you were
vindicated so cleanly that no judgement was required. Also weak: framing
unpopularity as evidence of courage - sometimes it is evidence of being wrong.

THE DETAIL THAT LANDS: acknowledging what the decision cost in goodwill and
saying you would spend it again - or, more interestingly, that you would not.""")

_P("Tell me about a time you took ownership of a problem outside your remit.",
   ["Why did you rather than someone else?",
    "How did you avoid stepping on the actual owner?",
    "Did you hand it back, and how?",
    "When is taking ownership the WRONG move?",
    "What did it cost you elsewhere?"],
   """STRONG: took it because nobody else would and the cost of waiting was real,
brought the rightful owner along rather than around, and handed it back with a
mechanism so it would not need rescuing again.

WEAK: a story that is really about being helpful, or one where you quietly did
someone else's job and are still slightly annoyed about it.

THE MATURITY SIGNAL: naming when ownership is the wrong move - when it removes
accountability from the person who should hold it. Volunteering that shows
judgement rather than eagerness.""")

_P("Centralized vs. embedded TPM - which model do you prefer and why?",
   ["We are embedded today. What would you change first?",
    "How do you stop centralised TPMs becoming process police?",
    "Who wins when the solid line and the dotted line disagree?",
    "What ratio of TPMs to engineers, and why?",
    "How would you know in six months whether the model was working?"],
   """STRONG: gives a DEFAULT with explicit conditions that would change it, and
names the costs of each model as precisely as the benefits. Raises the
independence problem - a TPM reviewed by the leader whose program they report on
will produce optimistic status, and that is incentives, not character.

WEAK: "it depends" with no position, which reads as inexperience. Equally weak:
importing your last company's structure with no reference to theirs.

THE DETAIL THAT LANDS: naming the arbitration mechanism for the matrix. Everyone
says hybrid; almost nobody says who decides when the two lines disagree.""")

_P("How do you set up portfolio governance without creating bureaucracy?",
   ["An exec wants every program reviewed monthly. How do you push back?",
    "What would you delete first in a typical PMO?",
    "How do you stop the ungoverned tier failing invisibly?",
    "How do you decide the tier thresholds?",
    "What if decision latency rises after your changes?"],
   """STRONG: leads with the test - what DECISION does this forum make, and who
would notice if it stopped? Governs by exception with explicit tiers, and offers
a measure of the governance itself (decision latency) plus a willingness to delete
your own process.

WEAK: describing a governance structure - steering committees, monthly reviews, a
dashboard - with no test for whether any of it earns its place. That IS the
bureaucracy the question is asking you to avoid.

THE DETAIL THAT LANDS: putting an expiry date on new process, so it has to
justify itself again in two quarters.""")

_P("How would you design the TPM function for a company at our scale?",
   ["What would you need to know before answering properly?",
    "What is the first thing you would change here?",
    "How do you justify the size of the function at budget time?",
    "What does a TPM do that an engineering manager cannot?",
    "How do you hire for it - what is your bar?"],
   """STRONG: asks where delivery actually breaks here - across teams or inside
them - because that single question determines the design. Gives a shape with
numbers, names what the function will NOT do, and says how it would be measured.

WEAK: a generic org chart with no reference to their situation, or a pure
listening answer with no point of view. They are hiring a point of view; bring
one and say you will test it.

THE DETAIL THAT LANDS: being explicit that the function must be able to justify
its own cost, and how you would demonstrate that.""")

_P("Tell me about a time the org structure itself was the root cause of a "
   "delivery problem.",
   ["How did you distinguish structure from execution as the cause?",
    "What did you change, and what got worse as a result?",
    "How long did the change take to show up in delivery?",
    "Did you have the authority to change it, or did you have to persuade?",
    "When is a reorg the wrong answer?"],
   """STRONG: shows the diagnosis - the same failure recurring across different
people, which is the signature of structure rather than capability - and names the
specific change (reporting lines, decision rights, a forum) plus what it cost.
Every org change trades something away; say what.

WEAK: a story where the structure was blamed but the fix was really better
communication. Also weak: a reorg with only upside described.

THE MATURITY SIGNAL: saying when a reorg is the wrong answer - it is the most
visible move available to a new leader and usually the most expensive.""")

_P("Tell me about setting a vision or strategy for your area.",
   ["What did you deliberately choose NOT to do?",
    "How did you know the strategy was working before the results came in?",
    "Who disagreed with it?",
    "What changed when reality pushed back?",
    "How did you make it real for an engineer three levels down?"],
   """STRONG: starts from a business outcome rather than a roadmap, names the BET
and the explicit not-doing list, and gives a LEADING indicator you watched to know
whether you were wrong before the lagging results arrived.

WEAK: a vision statement and a roadmap. A strategy that excludes nothing is not a
strategy, and the fastest way to expose that is the "what did you not do?"
follow-up - which is why it is always asked.

THE DETAIL THAT LANDS: how it changed a decision someone made without consulting
you. That is the only real evidence a strategy landed.""")


for _q_item in QUESTIONS:
    if _q_item["q"] in _PROBES:
        _q_item["probes"] = _PROBES[_q_item["q"]]
        _q_item["strong_weak"] = _STRONG_WEAK[_q_item["q"]]

"""Product-thinking and Program-management round bank for a Technical
Program Management loop (Senior Director / Head-of-TPM altitude).

A TPM loop at this level is normally four rounds:

  1. PRODUCT THINKING  - can you reason about users, value and metrics, or do
                         you only reason about dates? Covered here.
  2. DESIGN            - system/architecture depth. Covered by
                         `system_design_bank.py` (42 detailed classic designs).
  3. PROGRAM MANAGEMENT - the craft round: planning, dependencies, risk,
                         governance, recovery. Covered here.
  4. BEHAVIORAL        - STAR at exec altitude. Covered by
                         `interview_question_bank.py` (134 questions).

These two rounds are CASE rounds, not STAR rounds. The interviewer gives you a
scenario and watches how you think out loud. So every entry carries a
FRAMEWORK (the structure to impose on any question of that shape), a full
WORKED answer at the right altitude, the STRONG-versus-WEAK contrast that is
usually the difference between a hire and a no-hire, and the PROBES the panel
will push you with after your first answer - because at this level the first
answer is never the test.

Served read-only by routes/interview_prep.py.
"""

ROUNDS = {
    "product": "Product Thinking Round",
    "program": "Program Management Round",
    "close": "Questions You Ask Them",
}

#: What each round is actually assessing, shown at the top of the page. Being
#: explicit about this matters: candidates lose the product round by answering
#: it like a delivery round, and lose the program round by telling stories
#: instead of describing mechanisms.
ROUND_BRIEF = {
    "product": (
        "They are testing whether you can hold a POINT OF VIEW about the "
        "product, not whether you can run it. The failure mode for a TPM here "
        "is answering every question with process - 'I'd align with the PM and "
        "run a discovery phase'. That reads as someone who has no opinion. "
        "Lead with the user, the value and the metric; only then talk about "
        "how you would sequence it. Say 'I would build X and not Y, because Z' "
        "out loud at least once per answer."
    ),
    "close": (
        "Not a round of its own - it is the last five minutes of every round, "
        "and at Director+ it is scored. Your questions reveal what you think "
        "the job is and whether you are evaluating them back. Prepare eight to "
        "ten, ask two or three per interviewer, and follow up on the answer "
        "rather than moving to the next item on your list."
    ),
    "program": (
        "This is your home round and the bar is correspondingly higher - "
        "competent is not enough, they expect distinctive. The failure mode is "
        "listing artifacts (RAID log, status report, RACI) as if the artifact "
        "were the work. Every answer should name a MECHANISM and the "
        "behaviour it changes: what decision does this forum make, what would "
        "surface a slip a week earlier, who is accountable and how would you "
        "know they were not. Quantify everything you can."
    ),
}


def E(round_, title, what_they_test, framework, worked, strong_weak, probes,
      pitfalls, tags, difficulty="Medium", frequency="", prep_minutes=0):
    """One case-round entry. `framework` and `worked` carry the weight."""
    return {
        "round": round_, "title": title, "what_they_test": what_they_test,
        "framework": framework, "worked": worked, "strong_weak": strong_weak,
        "probes": probes, "pitfalls": pitfalls, "tags": tags,
        "difficulty": difficulty, "frequency": frequency,
        "prep_minutes": prep_minutes,
    }


ENTRIES = []

# ══════════════════════════════════════════════════════════════════════════
#  PRODUCT THINKING ROUND
# ══════════════════════════════════════════════════════════════════════════

ENTRIES.append(E(
    "product",
    "How would you improve [our product]?",
    "Whether you have an opinion, and whether that opinion is anchored in a "
    "user and a metric rather than in features you personally find "
    "interesting. Almost every product round opens with some version of this, "
    "and most TPM candidates answer it as a list of ideas with no ranking "
    "logic - which is the single most common way to fail this round.",
    """THE STRUCTURE - roughly 20 minutes, spoken out loud

1. PICK A USER AND SAY WHY (1-2 min)
   Do not improve "the product". Name a segment and why it is the one worth
   attacking now - biggest, fastest-growing, worst-served, or most strategic.
   "I'll focus on new admins in their first week, because activation is where
   the revenue leak usually is and it's the cheapest thing to move."

2. NAME THE GOAL METRIC BEFORE ANY IDEAS (1 min)
   State the ONE number you are trying to move and roughly where it sits.
   Everything after this is judged against it. Without it, your ideas cannot
   be ranked and the interviewer has nothing to push on.

3. WALK THE JOURNEY AND FIND THE PAIN (4-5 min)
   Go step by step through what that user actually does, and mark where they
   drop, wait, get confused, or have to leave the product. Three to five pain
   points. This is where you demonstrate you have USED the thing.

4. PICK THE BIGGEST PAIN AND SAY WHY THE OTHERS LOSE (2 min)
   Explicitly deprioritise. "The integrations gap is real but it affects 5% of
   accounts; the onboarding drop affects everyone, so I'd take that first."

5. THREE SOLUTIONS AT DIFFERENT SIZES (4-5 min)
   A cheap one (a week), a medium one (a quarter), and a bet (a year). This
   shows range and lets the interviewer choose where to dig.

6. RECOMMEND ONE, WITH THE TRADE-OFF (2 min)
   Commit. Name what it costs and who would object.

7. HOW YOU WOULD KNOW YOU WERE RIGHT (2 min)
   The success metric, the guardrail metric that must not degrade, and the
   experiment design. Name the result that would make you kill it.""",
    """A WORKED ANSWER - improving a B2B analytics product

USER: "I'll take the new workspace admin in their first week. In B2B
analytics, seats bought and seats activated diverge badly, and every
unactivated seat is churn queued up for renewal. It's also the cheapest
segment to move because the fixes are product, not sales."

METRIC: "Percentage of new workspaces with at least three weekly active users
by day 14. Say it's around 30% today - typical for this category."

JOURNEY AND PAIN:
  sign-up -> connect a data source -> build first dashboard -> share it ->
  come back next week
  * Connecting a source needs a credential the admin usually does not have.
    They have to go and ask a data engineer, and the momentum dies there.
  * The blank-canvas dashboard builder assumes they know what they want.
  * Sharing requires inviting people who then land on the same blank canvas.
  * Nothing brings them back - no digest, no alert, no reason to return.
  I'd guess the largest single drop is the credential wall on day one.

DEPRIORITISE: "The builder being hard matters, but it's downstream - people
who never connect a source never see it. Fix the top of the funnel first."

THREE SOLUTIONS:
  Cheap: a demo workspace with realistic sample data available before any
  credential is required, so the user reaches value in the first session.
  Medium: a delegated-connection flow - the admin sends a one-click request to
  whoever holds the credential, and the product tracks it as a task rather than
  dropping it into email.
  Bet: template packs per vertical and per role, so "first dashboard" is
  choosing from five relevant starting points rather than a blank canvas.

RECOMMEND: "Start with the sample workspace. It's roughly two engineer-weeks,
touches no security surface, and tests the hypothesis that the credential wall
is the real blocker. If activation doesn't move, my diagnosis was wrong and I
have spent very little to learn that - which is exactly why I'd sequence it
first rather than starting with the templates I actually think are the bigger
long-term play."

TRADE-OFF: "Sales will dislike sample data because it delays the moment the
customer sees their own numbers, and there's a real risk people mistake sample
data for their own. I'd watermark it heavily and cap it at seven days."

MEASUREMENT: "Success is day-14 three-WAU activation, target 30% to 40%.
Guardrail: no drop in paid conversion or in real-source connection rate within
30 days - if people happily play with fake data and never connect, I have made
things worse, not better. A/B at workspace level, powered to detect five
points, roughly four weeks at typical B2B sign-up volume." """,
    """STRONG sounds like: a named segment, one metric stated before any ideas,
an explicit "I am NOT doing X because", one recommendation with its cost, and a
kill condition. You should be able to hear the shape of a decision in it.

WEAK sounds like: "I'd talk to users and the PM to understand the problem
space, then run a discovery phase and prioritise with RICE." This is not
humility, it is the absence of a view - and it is exactly what makes a panel
think "good program manager, not a product partner". You are allowed, even
expected, to reason from assumptions in this round. Say "I'm assuming X - tell
me if that's wrong" and keep moving.

ALSO WEAK: five ideas of similar size with no ranking; improving a feature you
find interesting rather than one on the critical path; and any answer with no
number in it anywhere.""",
    ["Which of your three would you do if you had ten engineers and a year?",
     "Your sample-workspace test comes back flat. What now?",
     "How would you know the credential wall is the real problem before "
     "building anything?",
     "The PM disagrees and wants the templates first. How does that "
     "conversation go?",
     "What would you cut from the current product?"],
    """* Answering with process instead of a position - the number one killer.
* No metric, so nothing can be ranked and every idea sounds equally good.
* Improving the product you wish it were, rather than for a real segment.
* Forgetting the guardrail metric. Any activation idea can be gamed by making
  activation easier to reach without making it more valuable, and a panel that
  hears no guardrail assumes you have not thought about gaming.
* Running out of time in the journey walk. Watch the clock; the recommendation
  and the measurement are what they are actually scoring.""",
    ["product-sense", "metrics", "prioritization", "product"],
    difficulty="Hard",
    frequency="Opens the product round in the large majority of TPM loops.",
    prep_minutes=45,
))

ENTRIES.append(E(
    "product",
    "A key metric dropped 15% week over week. Diagnose it.",
    "Structured debugging under ambiguity, and whether you separate "
    "measurement problems from real problems before chasing causes. This is "
    "the most common analytical question in a product round and it is almost "
    "entirely about the ORDER in which you check things.",
    """THE STRUCTURE - the order matters more than the content

1. CLARIFY THE METRIC BEFORE ANYTHING (1 min)
   What exactly is it, how is it defined, what is the denominator? A "15% drop
   in engagement" could be a change in the definition of engagement.

2. IS IT REAL? Rule out instrumentation FIRST (2 min)
   Did a tracking library change, a release ship, a pipeline fail, a bot filter
   turn on? A startling share of real-world metric drops are logging bugs, and
   checking this first is the habit that marks an experienced operator. Ask:
   do other correlated metrics move together? If revenue is flat while sessions
   dropped 15%, suspect the instrument.

3. IS IT EXPECTED? Seasonality and known events (1 min)
   Same week last year, holiday, a large customer's fiscal cycle, a marketing
   campaign that ended, a pricing change, a competitor launch.

4. SEGMENT UNTIL IT STOPS BEING FLAT (5 min) - the core of the answer
   Cut the drop along every dimension and find where it CONCENTRATES:
     platform (iOS / Android / web)   - a bad release
     geography                        - an outage, a regulation, a CDN issue
     new versus returning users       - acquisition vs retention problem
     account size or plan tier        - one whale, or a segment-wide issue
     app or OS version                - a specific build
     entry point / channel            - SEO change, a broken email link
   A drop spread evenly across every segment is a different animal from one
   concentrated in Android 14 in Germany - and saying which you are looking for
   is the point.

5. INTERNAL OR EXTERNAL? (1 min)
   Internal: releases, experiments ramping, config changes, an expired
   certificate, a failed migration. External: a platform policy change, a
   competitor, a news event, an app-store ranking change.

6. FORM A HYPOTHESIS AND SAY HOW YOU'D CONFIRM IT (2 min)
   Name the one you believe and the specific query or check that would settle
   it. Then say what you would do in the meantime - at Director level, "I would
   also start the rollback conversation while investigating" is the right
   instinct.""",
    """A WORKED ANSWER

"First, what is the metric exactly - daily active users? And is the definition
unchanged this week? I'd want to know that before I believe the number.

Then I'd check whether it's real. Did we ship anything, did the analytics SDK
update, did an ETL job fail? The tell is whether correlated metrics moved
together: if sessions are down 15% but transactions and revenue are flat, I'm
looking at a measurement problem, not a user problem, and I'd stop the fire
drill immediately.

Assuming it's real, I'd check the calendar - same week last year, any holiday,
did a big campaign end, did we change pricing.

Then I'd segment, and I'd keep cutting until the drop stops being uniform. My
first cuts are platform, geography, and new versus returning, because those
three separate the three most common causes: a bad release, an
infrastructure or regulatory event, and an acquisition-versus-retention
problem. Say it concentrates in Android, new users, one region - now I have a
story: a release or an app-store issue affecting acquisition in that market.

I'd confirm by pulling the drop by app version and overlaying the release
timeline. If the drop starts exactly at a version boundary, that's the answer
and I'd be talking about a rollback before I finish the analysis.

One thing I'd say out loud to the room: if the drop is uniform across every
segment I cut, that usually means it is NOT a product bug - uniform drops point
at measurement, seasonality, or something happening upstream of the product
entirely." """,
    """STRONG sounds like: instrumentation checked before causes, explicit
segmentation with a reason for each cut, and a statement of what a UNIFORM drop
versus a CONCENTRATED drop would each imply. Bonus for saying what you would do
in parallel with the investigation.

WEAK sounds like: jumping straight to "maybe a competitor launched" or "maybe
the new feature confused users" - guessing causes before establishing the
shape. Also weak: listing twenty possible causes with no order. The interviewer
is scoring your search strategy, not your imagination.

THE DETAIL THAT IMPRESSES: correlated-metric triangulation. "If sessions fell
but revenue didn't, the instrument is lying" is a one-line demonstration of
real operating experience.""",
    ["It's uniform across every segment. Now what?",
     "You find it started at a release boundary but the release contains 40 "
     "changes. How do you narrow it?",
     "The CEO wants an answer in an hour and you are not sure yet. What do you "
     "tell them?",
     "How would you have caught this earlier?",
     "It turns out to be a competitor's promotion. Does that change what you "
     "do?"],
    """* Guessing causes before ruling out measurement. It reads as junior and it
  is the most common failure in this question.
* Segmenting without saying what each cut would tell you.
* Forgetting that "15% week over week" needs a baseline - is that outside
  normal variance? Ask what the weekly noise band looks like.
* Not saying anything about action. At Director level they want to hear you
  managing the response and the communication, not just the analysis.""",
    ["metrics", "analytics", "debugging", "product"],
    difficulty="Hard",
    frequency="Very common - the standard analytical question in a product round.",
    prep_minutes=40,
))

ENTRIES.append(E(
    "product",
    "What metrics would you use to measure the success of [feature/product]?",
    "Whether you can distinguish the metric that captures VALUE from the "
    "metrics that are merely easy to collect, and whether you think about "
    "gaming. Weak answers list every number available; strong answers pick one "
    "and defend it.",
    """THE STRUCTURE - one of each, and say why

1. THE ONE NORTH-STAR METRIC
   The single number that goes up only when real value is delivered. Force
   yourself to pick one. "If I could see only one number, it would be X."

2. INPUT METRICS (the levers)
   Two or three things the team can actually move that drive the north star.
   These are what you would review weekly - the north star usually moves too
   slowly to steer by.

3. GUARDRAIL / COUNTER METRICS
   What must NOT get worse. Every metric can be gamed, and naming the specific
   gaming path is what separates a real answer: "engagement can be raised by
   sending more notifications, so I'd guard on unsubscribe rate and on
   day-30 retention."

4. THE QUALITY OR HEALTH CUT
   Latency, error rate, support contact rate, review scores - whatever proves
   the experience did not degrade to buy the number.

5. HOW YOU'D SEGMENT IT
   An average hides everything. New versus returning, by tier, by platform.

6. WHAT WOULD MAKE YOU KILL IT
   Name the threshold and the horizon. Interviewers rarely hear this and it
   lands every time.""",
    """A WORKED ANSWER - a newly launched in-app messaging feature

NORTH STAR: "Weekly threads with a reply from a second person. Not messages
sent - messages sent rewards volume and one person shouting into the void.
The reply is what proves the feature created a conversation, which is the value
we claimed."

INPUTS: "Percentage of active users who send a first message in their first
week - that's adoption. Median time to first reply - that's whether the loop
closes. Threads per active sender - that's depth. Those three are what I'd put
on the weekly review, because the north star moves too slowly to steer by."

GUARDRAILS: "Notification opt-out rate and day-30 retention. This feature has
an obvious cheat: drive engagement with notification volume. If threads go up
while opt-outs climb, we're borrowing from the future, and I'd rather find that
in week three than in the renewal cycle. I'd also guard on support contacts
per thousand users, because a messy inbox generates tickets."

QUALITY: "Message delivery latency at p95 and delivery failure rate. A
messaging feature that is occasionally slow is worse than no messaging feature,
because people stop trusting it and there is no way to earn that back cheaply."

SEGMENTS: "By account size - I'd expect this to behave completely differently
in a five-person workspace than a five-thousand-person one - and new versus
existing workspaces, since existing ones already have habits formed elsewhere."

KILL CONDITION: "If after one quarter fewer than 15% of active users have ever
sent a message, and reply rate is under 30%, the feature has not found its
loop. I'd rather sunset it and free the maintenance cost than keep it on life
support - and I'd say that up front, when it is cheap to agree to, rather than
arguing about it later when everyone is attached." """,
    """STRONG sounds like: one north star, defended against an obvious
alternative ("replies, not messages sent, because..."); a named gaming path
with its guardrail; and a kill condition with a number and a date.

WEAK sounds like: DAU, MAU, retention, NPS, engagement, conversion - a list.
Also weak: choosing a metric the team cannot influence, or one that takes six
months to read.

THE DETAIL THAT IMPRESSES: naming the cheat before they ask. "The obvious way
to game this is X, so I'd guard on Y" demonstrates that you have watched teams
optimise a metric into uselessness before.""",
    ["Your north star takes a quarter to read. What do you steer by in week "
     "two?",
     "The feature is used heavily by 5% of users and ignored by everyone else. "
     "Success or failure?",
     "How would you set the target, not just the metric?",
     "Engineering says the guardrail metric is too expensive to instrument. "
     "What do you do?",
     "What would you have measured BEFORE building it?"],
    """* Listing metrics rather than choosing one and defending it.
* No guardrail, which reads as never having seen a metric gamed.
* Vanity metrics - total registered users, cumulative anything. Cumulative
  numbers only go up and therefore say nothing.
* No segmentation, so an average masks a feature that is loved by one group and
  irrelevant to everyone else.
* Forgetting the cost side - a metric that improves while support tickets
  double is not a win.""",
    ["metrics", "product-sense", "measurement", "product"],
    difficulty="Medium",
    frequency="Extremely common - appears in the product round and often again "
              "in the program round in disguise.",
    prep_minutes=35,
))

ENTRIES.append(E(
    "product",
    "Should we build this ourselves, buy it, or partner? Walk me through it.",
    "Commercial judgment - whether you can reason about total cost of "
    "ownership, strategic differentiation and opportunity cost rather than "
    "engineering preference. TPM candidates very often under-perform here, "
    "which makes it a cheap place to stand out.",
    """THE STRUCTURE

1. IS THIS CORE OR CONTEXT? (the deciding question)
   Core = it is how you win, customers notice it, it compounds. Context = it
   must exist and be adequate, and no customer will ever choose you for it.
   Build core. Buy context. Almost every build/buy answer reduces to this one
   judgment, so lead with it rather than burying it.

2. TOTAL COST OF OWNERSHIP, NOT PURCHASE PRICE
   Build: engineers x months x fully-loaded cost, PLUS the perpetual
   maintenance tail (rule of thumb: 15-25% of the build cost every year,
   forever), PLUS the on-call and security burden.
   Buy: licence, integration cost, the internal team you still need, and the
   price at renewal once you are dependent.
   Say the maintenance tail out loud. It is the number teams forget and the one
   a CFO will immediately recognise you for knowing.

3. TIME TO VALUE AND THE COST OF DELAY
   If buying gets you there in six weeks and building in nine months, what is
   nine months of not having it worth? Sometimes that dominates everything.

4. OPPORTUNITY COST - what those engineers would otherwise do
   This is the real cost of building, and it is the argument that usually
   settles it at exec level.

5. RISK ON EACH SIDE
   Buy: vendor lock-in, roadmap misalignment, the vendor being acquired or
   dying, data residency and compliance, renewal leverage.
   Build: schedule risk, key-person risk, and the fact that you now own it
   forever.

6. THE EXIT / REVERSIBILITY TEST
   How expensive is it to change your mind in two years? Prefer the reversible
   option when the decision is close - buying behind an abstraction layer is
   often the cheap way to keep the option open.

7. RECOMMEND, WITH THE TRIGGER THAT WOULD CHANGE IT
   "Buy now, and revisit if usage passes X or the vendor's price per unit
   exceeds our modelled internal cost." """,
    """A WORKED ANSWER - a feature-flag / experimentation platform

"Start with core or context. Experimentation is context for us - no customer
buys our product because our flag system is elegant. It has to be reliable and
it has to be fast, but it is not where we win. That biases me hard toward buy
before I look at a single number.

Cost. Building a credible one - targeting, gradual rollout, an audit trail, an
SDK for four languages - is realistically four engineers for six months, so
about two engineer-years, call it $600k fully loaded. Then the part people
forget: roughly 20% of that every year forever in maintenance, on-call and
security patching, so $120k a year and rising. Buying is maybe $150k a year at
our scale plus about six weeks of integration.

Time to value: six weeks versus nine months. If experimentation is currently
blocking the product team from shipping safely, nine months of not having it is
nine months of slower learning across every team, which dwarfs the licence
fee.

Opportunity cost: those four engineers are the strongest argument. If they
would otherwise be on the thing customers actually choose us for, building this
is spending our scarcest resource on a commodity.

Risk: the real buy risk is renewal leverage - once every service depends on the
vendor's SDK, the price goes up and you have no walk-away. I would mitigate
that at design time by putting our own thin interface in front of their SDK, so
swapping vendors is a contained project rather than a company-wide one. That
costs maybe two weeks now and buys us the option.

Recommendation: buy, behind our own abstraction. I'd revisit if our spend
passes roughly $400k a year - at that point the internal build pays back inside
two years - or if we hit a requirement the vendor structurally cannot meet,
data residency being the likely one." """,
    """STRONG sounds like: core-versus-context stated first as the deciding
frame; the maintenance tail quantified; opportunity cost named explicitly; and
a reversibility play (the abstraction layer) that keeps the option open. A
trigger for revisiting turns it from an opinion into a managed decision.

WEAK sounds like: "we should build it so we have full control and can
customise it" - engineering preference dressed as strategy. Also weak: a
comparison of purchase price against build cost with no maintenance tail, no
opportunity cost, and no time-to-value.

THE DETAIL THAT IMPRESSES: the renewal-leverage point. Very few candidates say
out loud that the vendor's price goes up once you are dependent, and that you
can buy the option to leave for two weeks of work today.""",
    ["The vendor gets acquired by a competitor. What is your plan?",
     "Your CTO wants to build it because the team is excited. How do you handle "
     "that conversation?",
     "How would you actually validate the four-engineers-six-months estimate?",
     "At what usage level does the maths flip to build?",
     "You bought it and two years on it is limiting you. Was the decision "
     "wrong?"],
    """* Treating it as a technical decision. It is a capital-allocation decision
  and should be argued in those terms.
* Omitting the maintenance tail, which is what makes build look artificially
  cheap.
* No opportunity cost - the single most persuasive number in the whole
  analysis.
* Ignoring reversibility. The best answer to a close call is usually the option
  that is cheapest to undo.
* Not committing. They asked what you would do.""",
    ["build-vs-buy", "finance", "strategy", "product"],
    difficulty="Hard",
    frequency="Very likely at Director+ - and a common weak spot for TPM "
              "candidates, so a strong answer stands out disproportionately.",
    prep_minutes=40,
))

# ══════════════════════════════════════════════════════════════════════════
#  PROGRAM MANAGEMENT ROUND
# ══════════════════════════════════════════════════════════════════════════

ENTRIES.append(E(
    "program",
    "You inherit a critical program that is three months late. Walk me through "
    "your first 30 days.",
    "The single most common program-management case question, and the one that "
    "most rewards structure. They are watching whether you stabilise before "
    "you re-plan, whether you get to ground truth independently of the "
    "existing status, and whether you can be decisive about scope without "
    "being reckless.",
    """THE STRUCTURE - three phases, and say the phase names out loud

DAYS 1-7: GROUND TRUTH (do not re-plan yet)
  * Do not trust the status report. Find out what is ACTUALLY done - demoed,
    merged, in production behind a flag - versus what is reported done.
    "Percent complete" is the least reliable number in program management.
  * Talk to the engineers doing the work, not just the leads, and separately
    from their managers. Ask one question: "what do you believe about this date
    that you don't think leadership has heard?"
  * Map the real dependency graph and find the critical path. Late programs
    are usually late for one or two structural reasons, not fifty small ones.
  * Establish why it slipped - and distinguish the three causes, because they
    have completely different fixes: scope grew, estimates were wrong, or
    execution is blocked. Treating one as another is how the next 30 days get
    wasted too.
  * Say nothing definitive to executives yet except "I am re-baselining and you
    will have a credible answer by [date]." Buying that window is itself a
    skill.

DAYS 8-14: RE-BASELINE
  * Rebuild the plan bottom-up from the teams, not top-down from the date.
  * Produce a range with confidence levels, not a single date. "70% confident
    by March, 90% by May" is a far more useful and more honest artefact than a
    point estimate, and it changes the conversation from "is it going to be
    late" to "how much risk do you want to carry".
  * Identify the scope you would cut to hit each date in the range. Have the
    cut list ready BEFORE the conversation - the version of this meeting where
    you arrive with options goes very differently from the one where you arrive
    with a problem.
  * Name the top three risks with owners and triggers.

DAYS 15-30: RESET AND EXECUTE
  * One honest executive communication: here is the real position, here is what
    caused it, here are the options with their trade-offs, here is my
    recommendation. No surprises after this point - that is the promise you are
    making.
  * Put in the mechanism that would have caught this: a weekly critical-path
    review with named owners, a definition of done that includes integration,
    and a leading indicator rather than a lagging one.
  * Fix the single biggest structural blocker rather than trying to fix
    everything.
  * Re-establish trust through small visible wins in the first fortnight.""",
    """A WORKED ANSWER - condensed to how you would say it

"I'd split it into three phases and I would not re-plan in week one.

First week is ground truth. I assume the status is wrong - not because anyone
is lying, but because 'percent complete' is optimistic everywhere by
construction. So I go and find out what is actually integrated and running, not
what's reported. I'd talk to engineers without their managers in the room and
ask what they believe about the date that leadership has not heard, because
that is where the real information is. And I'd map the critical path, because
programs this late are usually late for one or two structural reasons.

The thing I'd be trying hardest to establish is WHY it slipped, because the
three causes need completely different responses. If scope grew, this is a
governance problem and I need to fix the intake. If the estimates were always
wrong, this is a planning problem and re-planning with the same people the same
way gets me the same answer. If execution is blocked - a dependency, a missing
environment, an unavailable team - then the plan is fine and I need to clear
the blocker. Getting that diagnosis wrong is how a second 30 days gets wasted.

Second week I re-baseline bottom-up, and I'd give leadership a range with
confidence levels rather than a date. And I would walk in with a cut list
already prepared - here is what we can deliver by the original date if we
descope these three things, here is what full scope costs in time. Arriving
with options rather than a problem is the difference between that meeting going
well and going badly.

Then one honest communication, and after that no surprises. In the back half of
the month I'd install the mechanism that should have caught it - usually a
weekly critical-path review with named owners and a definition of done that
includes integration, because 'done' meaning 'my part is written' is the most
common cause of this exact situation.

One thing I'd be careful about: I would not fire anyone or reorganise in the
first month unless there's a clear capability gap. Late programs usually have
demoralised teams, and a new leader arriving and swinging costs you the
information flow you just spent a week establishing." """,
    """STRONG sounds like: named phases; ground truth BEFORE re-planning; the
three-causes diagnosis (scope grew / estimates wrong / execution blocked);
confidence ranges rather than a date; and arriving at the exec conversation with
a cut list. The restraint about not reorganising in month one reads as
experience.

WEAK sounds like: "I'd review the plan, meet the stakeholders, and put together
a recovery plan" - generic, no diagnosis, no mechanism. Also weak: immediately
promising a new date in week one, which is how you inherit someone else's
problem and make it yours.

THE DETAIL THAT IMPRESSES: refusing to give a date in week one while explicitly
buying a window. Most candidates either cave to the pressure or say nothing
about the pressure at all.""",
    ["The exec sponsor demands a date on day three. What do you say?",
     "You find the previous TPM knew and hid it. What do you do?",
     "Your re-baseline says six months, not three. How do you deliver that?",
     "Which of the three causes is most common in your experience, and why?",
     "What would you have in place so this never gets to three months late "
     "again?",
     "The team says the date was never achievable. Do you believe them?"],
    """* Re-planning before establishing ground truth - you rebuild on the same bad
  data.
* Giving a new date early to relieve the pressure. You get one re-baseline of
  credibility; spend it once, on a number you can defend.
* Treating it as a motivation problem when it is a structural one, or vice
  versa.
* No mechanism at the end. If nothing changed about how slips surface, the
  program will be late again and you will have no excuse the second time.
* Reorganising in month one. Sometimes right, usually premature, and it always
  costs you information.""",
    ["recovery", "planning", "risk", "stakeholders", "program"],
    difficulty="Hard",
    frequency="The single most likely case question in a TPM program round.",
    prep_minutes=45,
))

ENTRIES.append(E(
    "program",
    "How would you run a program with 12 teams and a hard external date?",
    "Whether you design a SYSTEM for coordination or plan to coordinate "
    "personally. At twelve teams, anything that depends on you being in the "
    "room does not scale, and the panel is listening specifically for that "
    "realisation.",
    """THE STRUCTURE

1. START FROM THE DATE AND WORK BACKWARDS
   A hard external date (a regulation, a partner launch, an event) means scope
   is the only variable. Say that explicitly in the first minute - it reframes
   everything that follows and it is the correct senior instinct.

2. FIND THE CRITICAL PATH, NOT THE FULL PLAN
   With twelve teams you cannot manage everything. Identify the chain that
   determines the date and manage that chain intensely; let the rest run on
   normal team process. Name the two or three teams that are ON the critical
   path and say you would spend most of your attention there.

3. DEFINE THE INTERFACES EARLY - this is the real work
   Twelve teams fail at the seams, not in the middle. Get API contracts,
   schemas and integration points agreed and STUBBED in the first few weeks so
   teams can build against something that exists. A mock that returns fake data
   in week two is worth more than a perfect specification in week eight.

4. INTEGRATE CONTINUOUSLY, NEVER AT THE END
   The classic failure is twelve teams that are each "done" and have never run
   together. Set integration milestones with real dates, and define "done" as
   integrated and demonstrated, not merged.

5. TIERED SCOPE, AGREED UP FRONT
   Must-have for the date, should-have, and nice-to-have - agreed with the
   sponsor at the START, when it is an abstract conversation, not in the final
   month when it is an emotional one. This one move prevents most late-program
   drama.

6. THE CADENCE - and what each forum DECIDES
   Not "we'll have meetings" - say what each one is for:
     Daily (critical path only, 15 min): blockers, during crunch phases only.
     Weekly (leads): risks, dependencies, decisions needed. Not status.
     Bi-weekly (sponsors): decisions and trade-offs, not a status report.
     Written status weekly so the meetings do not become status theatre.

7. LEADING INDICATORS, NOT LAGGING ONES
   "Percent complete" tells you nothing until it is too late. Watch integration
   test pass rate, open cross-team dependencies, defect find-versus-fix rate,
   and whether milestone dates are MOVING - the rate of change of the plan is
   the earliest warning you get.

8. BUFFER, HELD CENTRALLY AND VISIBLY
   Teams pad estimates privately; that padding gets consumed invisibly. Take
   the padding out, hold the buffer at the program level, and make its
   consumption public. Watching the buffer burn down is the best single
   predictor of whether a hard date will hold.""",
    """A WORKED ANSWER - the shape of it

"The first thing I'd say to the sponsor is that with a hard external date,
scope is the only variable, so we need to agree tiers now rather than argue in
month five.

Then I'd stop trying to manage twelve teams. I'd find the critical path -
usually two or three teams - and spend my attention there, letting the others
run on their own process with a light reporting line. A TPM who tries to be in
every team's stand-up at this scale becomes the bottleneck.

The highest-leverage early work is the interfaces. Twelve teams fail at the
seams. I'd want contracts agreed and stubbed in the first three weeks so
everyone is building against something real, and I'd set hard integration
milestones - a first end-to-end skeleton by a specific date, even if every
component is fake. The alternative is twelve teams that are all 'done' in month
five and have never once run together, which is the single most common way
programs like this fail.

For cadence, I'd be explicit about what each forum decides. Weekly leads
meeting is for risks and cross-team decisions, not status - status goes in
writing so the meeting is not consumed by it. Sponsor forum every two weeks is
for trade-offs, and I'd bring decisions, not updates.

On tracking: I would not steer by percent complete. I'd watch integration test
pass rate, the number of open cross-team dependencies, and whether milestone
dates are moving - a date that has moved twice will move a third time, and that
signal arrives weeks before the slip shows up in a status report.

And I'd hold the buffer centrally and visibly. Teams pad individually and that
padding disappears quietly. Held at program level and burnt down in public, it
becomes the single best early warning I have." """,
    """STRONG sounds like: scope is the variable, stated first; managing the
critical path rather than everything; interfaces stubbed early; integration as
a first-class milestone; leading indicators named specifically; and centrally
held buffer. Each of those is a MECHANISM, which is what this round rewards.

WEAK sounds like: a list of artifacts - "I'd set up a RAID log, a RACI, a
weekly status report and a program dashboard". Artifacts are not mechanisms. If
you name an artifact, immediately say what decision it drives and what
behaviour it changes.

ALSO WEAK: promising to attend every team's ceremonies. It signals you have not
run something at this scale.""",
    ["Two teams on the critical path disagree on the interface. How do you "
     "resolve it?",
     "One team is consistently missing its commitments. What do you do?",
     "The sponsor refuses to agree scope tiers up front. How do you handle "
     "that?",
     "You are eight weeks out and integration testing is failing badly. What "
     "now?",
     "How do you know, in week four, whether the date is at risk?",
     "How much buffer, and how did you decide?"],
    """* Managing all twelve teams equally - it does not scale and it signals
  inexperience.
* Leaving integration to the end. This is THE classic multi-team failure.
* Status-driven tracking. Percent complete is a lagging indicator dressed as a
  leading one.
* Agreeing scope tiers late, when the conversation is emotional.
* Listing artifacts without mechanisms.
* Hidden buffer. If you cannot see it burn, it is not managing anything.""",
    ["planning", "dependencies", "cadence", "integration", "program"],
    difficulty="Hard",
    frequency="Very common - the standard 'run a big program' case.",
    prep_minutes=45,
))

ENTRIES.append(E(
    "program",
    "How do you measure the health of a program? What is on your dashboard?",
    "Whether you can tell leading indicators from lagging ones, and whether "
    "your reporting is designed to surface bad news early or to look green. "
    "This question is a fast read on how experienced you actually are.",
    """THE STRUCTURE - lead with the principle, then the metrics

THE PRINCIPLE TO STATE FIRST
  "Most program dashboards are lagging indicators - they tell you that you are
  late once you are already late. I design for the earliest possible signal,
  and I explicitly design against the incentive to look green."

LEADING INDICATORS (these are the answer)
  * Milestone date VOLATILITY - how often dates have moved, and by how much.
    A date that has moved twice will move again. This is the single earliest
    warning available and almost nobody tracks it.
  * Open cross-team dependencies and their age. Ageing dependencies are where
    slips are born.
  * Integration/e2e test pass rate over time - the truth serum for "done".
  * Defect find rate versus fix rate. Find outpacing fix means the end date is
    moving whatever the plan says.
  * Scope added since baseline. Silent scope growth is the most common
    unreported cause of lateness.
  * Buffer consumed versus time elapsed. If you have burnt 60% of buffer in 30%
    of the schedule, you are in trouble regardless of what percent-complete
    says.

LAGGING (report but never steer by)
  Percent complete, tasks closed, story points burned, milestones hit.

QUALITATIVE - the one that catches what numbers miss
  A confidence poll of the team leads, collected privately and reported
  anonymously in aggregate: "how confident are you in this date, 1 to 5?" A
  falling average with green metrics is the most valuable signal on the whole
  dashboard, and it consistently leads the numbers by weeks.

THE ANTI-SANITISATION DESIGN
  Say how you stop status being laundered on the way up: red is a normal
  colour and never punished; the person closest to the work writes the status,
  not their manager; a red requires an ask, not an apology; and you personally
  thank the first person to raise one.""",
    """A WORKED ANSWER

"I'd start by saying that most program dashboards are useless because they are
lagging - they turn red the week you miss, when the information is worthless.
So I try to build one that would have told me six weeks earlier.

The metric I care most about, and the one that is almost never on anyone's
dashboard, is milestone date volatility - how many times has each milestone
moved and by how much. A date that has slipped twice is going to slip again,
and that pattern is visible long before percent-complete looks bad.

After that: open cross-team dependencies and their age, because slips are born
at the seams and an ageing dependency is a slip in gestation. Integration test
pass rate, because it is the only honest measure of 'done'. Defect find rate
versus fix rate - if finding is outpacing fixing, the date is moving no matter
what the plan says. Scope added since baseline, because silent scope growth
causes more lateness than bad estimation does. And buffer burnt versus time
elapsed.

I'd report percent complete because executives expect it, but I would not steer
by it.

The most valuable thing on my dashboard is not a number, though. It's an
anonymous weekly confidence poll of the team leads - 'how confident are you in
this date, one to five'. When that average falls while every metric is green,
something is wrong that the instrumentation has not caught yet, and in my
experience it leads the numbers by weeks.

And I'd design the reporting so bad news travels fast. Status is written by the
person closest to the work rather than their manager, red is a normal colour
that gets support rather than interrogation, and a red comes with an ask rather
than an apology. If your dashboard is always green until it is suddenly red,
you do not have a measurement problem, you have a culture problem." """,
    """STRONG sounds like: the leading-versus-lagging distinction stated as a
principle; milestone volatility and dependency ageing named specifically; the
confidence poll; and an explicit answer to how you stop status being sanitised.
That last one is what makes it a Director-level answer rather than a
practitioner one.

WEAK sounds like: "RAG status, burndown, percent complete, risks and issues" -
every one of which is lagging. Also weak: any dashboard with no human signal in
it.

THE DETAIL THAT IMPRESSES: milestone date volatility. Very few candidates name
it and it is genuinely the earliest quantitative warning available.""",
    ["Everything is green and then the program misses by two months. What went "
     "wrong with your dashboard?",
     "How do you stop teams gaming the metrics you just described?",
     "An exec wants a single RAG status. What do you give them?",
     "How would you set up the confidence poll so people answer honestly?",
     "Which of these would you drop if you could only keep three?"],
    """* An all-lagging dashboard. It is the default and it is the wrong answer.
* No human/qualitative signal.
* Not addressing sanitisation. At Director level, how bad news travels is more
  important than which metrics you picked.
* Too many metrics. A dashboard nobody reads is decoration - be ready to name
  your top three.
* Treating red as failure. If red is punished, you will never see one until it
  is too late, and you will have caused that yourself.""",
    ["metrics", "governance", "reporting", "risk", "program"],
    difficulty="Medium",
    frequency="Very common, and often the question that reveals seniority "
              "fastest.",
    prep_minutes=35,
))

ENTRIES.append(E(
    "program",
    "Two teams have a hard dependency and are blocking each other. How do you "
    "unblock it?",
    "Dependency management is the core craft of the role, and this question "
    "tests whether you resolve the instance or remove the class. Anyone can "
    "escalate; the senior answer decouples.",
    """THE STRUCTURE

1. ESTABLISH WHAT KIND OF BLOCK IT IS - the diagnosis decides everything
   * TECHNICAL: A genuinely needs A's code from B. Decouple it.
   * SEQUENCING: both could proceed but each is waiting for certainty.
     Usually solvable with a contract and a stub, today.
   * PRIORITY: B could do it but it is not top of B's list. This is not a
     technical problem and no amount of technical creativity will fix it -
     it needs a decision from whoever owns both priorities.
   * INTERPERSONAL: they have stopped talking. Different problem again.
   Naming which one it is, out loud, is the answer to this question. Most
   candidates jump to a solution without diagnosing, and half the time they
   solve the wrong problem.

2. FOR TECHNICAL AND SEQUENCING - decouple rather than sequence
   Agree the interface contract NOW and have each side build against a stub or
   mock. Both teams proceed in parallel and integrate later. This converts a
   blocking dependency into a scheduled integration risk, which is a far better
   thing to own. Feature flags, contract tests and fakes are the tools; say
   them by name.

3. FOR PRIORITY BLOCKS - escalate correctly, which is a skill
   Escalation is not complaining. Go to the lowest common manager with: the
   decision needed, the options, the cost of each, your recommendation, and the
   date by which the decision must be made or the option expires. Then let them
   decide and support the outcome publicly even if it is not what you wanted.

4. WHAT YOU DO WHILE YOU WAIT
   Never sit idle waiting for a resolution. Re-sequence the blocked team onto
   other work so the wait costs less, and say so - it shows you manage the cost
   of the block, not just the block.

5. FIX THE CLASS, NOT THE INSTANCE - this is the senior half of the answer
   Why did this surface only when it became urgent? Usually there is no
   dependency register, no forum where cross-team commitments are made
   visible, or teams that plan in isolation. Put in: dependencies declared and
   dated at planning time, with a named owner on each side and a needed-by
   date; a weekly review of the ageing ones; and the norm that accepting a
   dependency is a commitment, not an aspiration.""",
    """A WORKED ANSWER

"First I'd work out which of four things this actually is, because they need
completely different responses.

If it's technical - team A literally cannot run without B's service - then my
instinct is to decouple rather than sequence. Agree the interface contract
today and have A build against a mock while B builds the real thing. That turns
a blocking dependency into a scheduled integration, which is a much better risk
to own because it is visible and datable.

If it's a sequencing block - both could proceed but each is waiting for the
other to be certain - that is the same fix and it is usually solvable in an
afternoon. Most 'blocked' dependencies are this.

If it's a priority block - B could do it but it is not high enough on B's
list - then no amount of technical cleverness helps. That is a decision about
relative priority and it belongs with whoever owns both teams. I'd go to the
lowest common manager with the options and the cost of each, my recommendation,
and a date by which the decision has to be made. And then whatever they decide,
I'd back it publicly, because the fastest way to lose the ability to escalate
is to escalate and then relitigate.

If it's interpersonal - they've stopped talking and are now emailing evidence
at each other - that is a people problem and I'd get them in a room without
their managers first.

While any of that is happening, I'd re-sequence the blocked team onto other
work rather than letting them idle, because the cost of the block is mine to
manage.

The part I care most about, though, is why this became visible only when it
became urgent. That is almost always a missing mechanism - no dependency
register, or teams planning in isolation. I'd want dependencies declared at
planning time with an owner on each side and a needed-by date, and I'd review
the ageing ones weekly. Resolving this instance is table stakes; stopping the
next six is the actual job." """,
    """STRONG sounds like: the four-way diagnosis before any solution; decouple
via contract-and-stub as the default technical move; escalation framed as
bringing a decision rather than a complaint; managing the cost of the block
while it is unresolved; and closing with the systemic fix.

WEAK sounds like: "I'd get them in a room and facilitate a conversation" -
which is sometimes right but is not a diagnosis; or "I'd escalate to
leadership", which is what junior people do first and senior people do
deliberately and rarely.

THE DETAIL THAT IMPRESSES: naming the priority block as fundamentally not a
technical problem. Candidates who try to solve a priority conflict with
architecture reveal a lot.""",
    ["The lowest common manager is the CTO and they are unavailable for two "
     "weeks. Now what?",
     "You decouple with a mock and the real integration then fails badly. Was "
     "that the wrong call?",
     "Team B keeps agreeing to dates and missing them. What do you do?",
     "How do you make dependency declaration actually happen rather than being "
     "a form people fill in?",
     "When is escalating too early?"],
    """* Solving before diagnosing - the most common failure here.
* Escalating as a first move, or escalating without options.
* Treating a priority conflict as a communication problem.
* Letting the blocked team idle.
* Stopping at the instance. Without the systemic half, this reads as a
  competent coordinator rather than a program leader.""",
    ["dependencies", "escalation", "influence", "program"],
    difficulty="Medium",
    frequency="Very common - dependency management is the defining craft "
              "question of the round.",
    prep_minutes=35,
))

# ── Batch 2 ───────────────────────────────────────────────────────────────

_B2 = []

_B2.append(E(
    "program",
    "What would you do in your first 90 days as Head of TPM here?",
    "This is the closing question of most Head-of-function loops and it is "
    "frequently the one the decision turns on. They are testing whether you "
    "have a POINT OF VIEW about the function, whether you listen before you "
    "act, and whether you can sequence change without destabilising delivery. "
    "A generic 30-60-90 template is a wasted opportunity - this is where you "
    "show them what hiring you actually buys.",
    """THE STRUCTURE - three phases, and name the ONE thing you will change

DAYS 1-30: LISTEN, AND BE SPECIFIC ABOUT WHAT YOU ARE LISTENING FOR
  * Meet every TPM one to one, and ask two questions that get real answers:
    "what do you spend time on that you think is worthless?" and "what would
    you fix if you were me?"
  * Meet the engineering, product and design leaders your function serves, and
    ask a harder question: "what do TPMs do here that helps, and what do they
    do that is overhead?" You need to hear the uncomfortable version early.
  * Read the artefacts, not the org chart: the last three program post-mortems,
    the current status reports, the planning docs. How bad news is written down
    tells you more about the culture than any conversation.
  * Sit in the existing forums before changing any of them. You want to know
    what decision each one actually makes - many make none.
  * Deliberately change nothing structural. You are buying information and
    credibility, and both are cheap now and expensive later.

DAYS 31-60: DIAGNOSE AND SHARE THE DIAGNOSIS IN WRITING
  * Write the assessment down and circulate it. A written diagnosis is a
    forcing function for your own clarity and it lets people correct you before
    you act on a wrong read.
  * The diagnosis should answer: where does delivery actually break here - is
    it planning, dependencies, decision latency, quality, or capacity? Where is
    the function adding value and where is it adding ceremony? What is the
    single biggest structural problem?
  * Pick ONE thing. Not five. Name the one change with the largest effect and
    say what you are explicitly NOT doing this year.
  * Get one visible early win that costs nobody anything - usually killing a
    report or a meeting nobody values. Removing something is the fastest way to
    earn permission to add something later.

DAYS 61-90: CHANGE ONE THING, AND INSTRUMENT IT
  * Implement the one change, with a named owner and a measure.
  * Establish your own operating cadence: what you review weekly, what you
    review monthly, and what you will personally never be in the room for.
  * Set the standard for the function - what a good program plan looks like,
    what "done" means, how risks get raised. Publish it as an example rather
    than a policy.
  * Start the talent read: who is operating a level above their title, who is
    struggling, where the gaps are. Do not act on it yet, but know it.

THE THING TO SAY OUT LOUD
"I would not reorganise in the first 90 days unless something is on fire. New
leaders reorganise early because it is the most visible thing they can do, and
it usually costs more than it buys - you lose the information flow you just
spent a month building, right when you understand the least." """,
    """A WORKED ANSWER - the shape, compressed

"First month I would deliberately change nothing structural. I'd spend it on
two questions. To the TPMs: what do you do that you think is worthless. To the
engineering and product leaders we serve: what do TPMs here do that is genuinely
overhead. That second question is uncomfortable and it is the most valuable
information I will get all quarter, because a TPM function that has drifted into
ceremony rarely knows it.

I'd also read the last three post-mortems and the current status reports rather
than the org chart. How bad news is written down tells you what the culture
really is - if every status is green until it is suddenly red, I know what my
first problem is.

Second month I'd write the diagnosis and circulate it. Writing it forces me to
be clear and lets people correct me before I act on a wrong read. The diagnosis
has to answer one question: where does delivery actually break here. In my
experience it is one of four things - planning quality, cross-team dependencies,
decision latency, or simply too much work in flight - and they need completely
different fixes. Picking the wrong one costs you a quarter.

Then I'd pick one thing. Just one. And I'd say publicly what I am not doing this
year, because a new leader who announces five initiatives gets none of them.

I'd also want an early win that costs nobody anything, and the easiest one is
almost always killing a report or a meeting that everybody privately thinks is
useless. Removing something buys you the permission to add something later.

Third month I'd implement the one change with a named owner and a measure, and
set my own cadence - including being explicit about what I will never be in the
room for, because a Head of TPM who attends everything teaches the org to wait
for them.

The thing I would not do is reorganise in the first 90 days unless something is
genuinely on fire. It is the most visible move available and it is usually the
most expensive one, because you spend the credibility and the information you
just acquired at the exact moment you understand the least.

If I had to name the one change I'd expect to make - and I'd want to test this
against what I find - it would be moving the function from reporting on delivery
to de-risking it. Most TPM organisations spend their capacity describing the
future rather than changing it." """,
    """STRONG sounds like: a specific listening plan with the actual questions
you would ask; a written diagnosis; ONE change, with an explicit not-doing list;
an early win that removes rather than adds; and the deliberate restraint about
reorganising. Naming your hypothesis about what you would probably change - while
holding it loosely - shows you have a point of view without being arrogant about
a company you have not joined yet.

WEAK sounds like: the generic 30-60-90 - "learn, then plan, then execute" - with
no content. Also weak: arriving with a fixed plan that ignores what you find,
and its opposite, a pure listening tour with no hypothesis at all. They are
hiring a point of view; bring one and say you will test it.

THE DETAIL THAT IMPRESSES: asking the engineering leaders what TPMs do that is
overhead. Very few candidates volunteer to hear that answer, and it signals you
care about the function's value rather than its territory.""",
    ["What if what you find contradicts your hypothesis?",
     "You discover the function is genuinely not adding value. Then what?",
     "How would you know at day 90 whether you had made things better?",
     "Which of the four failure modes do you most often see, and why?",
     "What if the CEO wants a reorg in month one?",
     "Who would you want to keep, and how would you tell in 90 days?"],
    """* A template with no content. Everyone says listen-diagnose-act; the value
  is entirely in the specifics.
* Too many initiatives. Announcing five means delivering none, and experienced
  panels know it.
* No point of view at all. Pure listening reads as someone with nothing to
  bring.
* Reorganising early, or promising to.
* No measure. "I would improve delivery predictability" without saying how you
  would know is exactly the vagueness you would criticise in your own TPMs.""",
    ["leadership", "org-design", "first-90-days", "program"],
    difficulty="Hard",
    frequency="Very likely to close a Head-of-TPM loop, and often the question "
              "the decision turns on.",
    prep_minutes=45,
))

_B2.append(E(
    "program",
    "How do you estimate a program when the requirements are not fully known?",
    "Whether you can commit responsibly under uncertainty. The two failure "
    "modes are equally bad: refusing to give a number until everything is "
    "known (which reads as unable to operate), and giving a single confident "
    "date you cannot possibly justify (which reads as naive, and burns you "
    "later).",
    """THE STRUCTURE

1. REFUSE THE SINGLE DATE, BUT NEVER REFUSE THE QUESTION
   "I can give you a range with confidence levels today and a much tighter one
   in three weeks" is the senior answer. Silence is not.

2. DECOMPOSE UNTIL THE PIECES ARE COMPARABLE TO THINGS YOU HAVE DONE
   Estimation is unreliable on novel work and reasonably reliable on analogies.
   Break down until each piece resembles something the team has shipped before,
   then estimate by reference rather than by imagination.

3. SEPARATE THE KNOWN FROM THE UNKNOWN AND SIZE THEM DIFFERENTLY
   Known work: bottom-up estimate from the teams.
   Unknown work: do not estimate it - TIME-BOX a spike to resolve it. "We do
   not know how hard the migration is; we will spend two weeks finding out and
   re-estimate on [date]." That converts an unbounded risk into a scheduled
   one.

4. GIVE A RANGE WITH CONFIDENCE, NOT A POINT
   "70% confident by March, 90% by May." This is more honest AND more useful,
   and it changes the executive conversation from "will you hit it" to "how
   much risk do you want to carry" - which is the conversation you want.

5. STATE THE ASSUMPTIONS AS A VISIBLE LIST
   "This assumes the platform team delivers the API by June, no more than one
   person out at a time, and no change in scope." Assumptions are the mechanism
   by which a date is allowed to move later without it being a failure - if an
   assumption breaks, the date changes and everyone already agreed why.

6. RE-FORECAST ON A SCHEDULE, NOT ON PANIC
   Say when you will update: after the spike, at the end of design, at the
   first integration. A date that is re-forecast on a known cadence is
   trustworthy; one that changes only when someone asks is not.

7. USE THE CONE OF UNCERTAINTY EXPLICITLY
   Early estimates are routinely out by a factor of two to four in both
   directions, and narrow as you learn. Saying that out loud, and showing the
   range narrowing at each checkpoint, is how you make an early number safe to
   give.""",
    """A WORKED ANSWER

"I would never refuse to give a number - that reads as someone who cannot
operate under uncertainty, which is most of the job. But I would refuse to give
a single date, because I cannot defend one.

What I'd do is split the work into what we understand and what we do not.
For the understood part I estimate bottom-up with the teams and by analogy to
things we have actually shipped, because estimation is only reliable when it is
anchored to something real.

For the part we do not understand, I don't estimate it at all - I time-box it.
'We don't know how hard the data migration is. We will spend two weeks finding
out and re-estimate on the 14th.' That turns an unbounded unknown into a
scheduled decision point, which is a far better thing to put in front of an
executive than a made-up number.

Then I'd give a range with confidence levels - 70% by March, 90% by May - and a
visible list of the assumptions it rests on. The assumptions matter more than
the date, because they are the agreed mechanism for the date to move later. If
the platform API slips, the date moves, and nobody is surprised or blamed,
because we wrote it down when it was uncontroversial.

And I'd commit to a re-forecast cadence up front: after the spike, at the end of
design, at first integration. A number that updates on a schedule earns trust.
One that only changes when someone chases you destroys it.

The thing I try to communicate to executives is the cone of uncertainty - early
estimates are routinely out by two to four times, and the range narrows as we
learn. If I show them the range getting tighter at each checkpoint, they get
something more valuable than a date: they get to see the risk being retired." """,
    """STRONG sounds like: never refusing the question; time-boxing unknowns
rather than estimating them; a confidence range; a visible assumption list
framed as the mechanism for change; and a committed re-forecast cadence.

WEAK sounds like: "I'd work with the teams to get estimates and build a plan" -
no handling of the unknown at all. Also weak: "I can't estimate until
requirements are complete", which is true and useless; and padding a single date
by 50% silently, which is dishonest and destroys the buffer's usefulness.

THE DETAIL THAT IMPRESSES: assumptions as the pre-agreed mechanism for the date
to move. It reframes estimation from prediction to risk management, which is the
altitude they are hiring for.""",
    ["The exec says a range is not good enough and wants one date. What do you "
     "give them?",
     "Your spike overruns. What now?",
     "How do you stop teams padding their estimates?",
     "How much buffer do you add, and where do you hold it?",
     "What if the assumption you flagged breaks in week two?"],
    """* Refusing to answer. Under-committing reads as badly as over-committing.
* Estimating the unknown instead of time-boxing it.
* Hidden padding. If the buffer is invisible it gets consumed invisibly, and
  you lose the earliest warning signal you have.
* No assumptions list, so every later change looks like a failure rather than a
  known risk materialising.
* Re-forecasting only when challenged.""",
    ["estimation", "planning", "risk", "stakeholders", "program"],
    difficulty="Medium",
    frequency="Very common in the program round, and a frequent follow-up to "
              "any planning question.",
    prep_minutes=35,
))

_B2.append(E(
    "program",
    "A team has missed its committed dates three sprints in a row. What do you "
    "do?",
    "Diagnosis before intervention, and whether you distinguish a capability "
    "problem from a system problem. The tempting answer - escalate to their "
    "manager - is usually wrong and always premature.",
    """THE STRUCTURE

1. FIND OUT WHICH OF FIVE THINGS IS ACTUALLY HAPPENING
   The intervention is completely different in each case, and getting this
   wrong wastes weeks and damages the relationship:
   * OVER-COMMITTING: they estimate optimistically or feel unable to say no.
     Fix the planning process, not the people.
   * INTERRUPTED: they are being pulled onto production support, escalations or
     other teams' emergencies. Their committed capacity is fiction. Fix the
     intake and protect the capacity.
   * BLOCKED: waiting on dependencies, environments, reviews, approvals. Not
     their problem to solve; it is yours.
   * UNCLEAR REQUIREMENTS: they start, discover the ask is ambiguous, and
     rework. Fix upstream, in product or design.
   * GENUINE CAPABILITY GAP: skills, or a leadership gap on the team. The
     least common cause and the one people jump to first.
   The way to tell is to look at what actually happened to the work, not at the
   burndown: how much unplanned work entered the sprint, how long items sat
   blocked, how much was reworked.

2. GO AND LOOK, PRIVATELY AND WITHOUT AN AUDIENCE
   Talk to the team lead first, alone, framed as "help me understand what is
   getting in the way", not "why do you keep missing". You get the truth in the
   first conversation or you do not get it at all.

3. FIX THE SYSTEM CAUSE FIRST
   In my experience four of the five causes are system problems that belong to
   me, not to them. Interrupted capacity is the most common by a distance -
   teams commit to 100% of their time and then lose 30% to support.

4. IF IT IS OVER-COMMITMENT: change what you ask for
   Commit to a fraction of measured historical throughput rather than to
   ambition. Make the unplanned work visible so the capacity conversation is
   about data rather than willpower.

5. ONLY THEN, IF IT IS CAPABILITY - and handle it properly
   Be specific about the gap, agree a plan with their manager, and set a
   review date. This is a manager conversation, not a program conversation,
   and you own bringing the evidence rather than the verdict.

6. IN ALL CASES, FIX THE PREDICTION PROBLEM SEPARATELY
   Even a team that improves will miss sometimes. What is unacceptable is
   finding out on the due date. Ask for the signal earlier - a mid-sprint
   check on whether the commitment still holds - so a miss is a forecast rather
   than a surprise.""",
    """A WORKED ANSWER

"I'd want to know which of five things is happening before I do anything,
because they need opposite responses and the wrong one damages the relationship.

Are they over-committing? Are they being interrupted - pulled into support and
escalations so their committed capacity was never real? Are they blocked waiting
on someone else? Are the requirements unclear so they are reworking? Or is there
a genuine capability gap?

The way I'd tell is by looking at what happened to the work rather than at the
burndown chart: how much unplanned work entered the sprint, how long items sat
in a blocked state, how much got reworked. Those three numbers usually
distinguish the causes on their own.

I'd have the conversation with the lead privately and frame it as 'help me
understand what is getting in the way'. If I open with 'why do you keep missing',
I get a defensive answer and I have burned my only chance at the truth.

Four of those five causes are system problems that belong to me, not to them.
Interrupted capacity is by far the most common - a team commits to a full sprint
and then loses a third of it to production support that nobody counted. The fix
is not motivational, it is to make the unplanned work visible and then either
protect the capacity or plan for less of it.

If it is genuine over-commitment, I'd change what we ask for: commit to a
fraction of measured historical throughput instead of to ambition, and let the
data do the arguing.

If after all that it really is a capability gap, that is a conversation with
their manager, and my job is to bring the evidence, not the verdict.

But there's a second problem underneath the first, and I'd fix it either way:
the issue is not only that they missed, it's that we found out on the due date.
I'd want a mid-sprint signal on whether the commitment still holds, so a miss
becomes a forecast rather than a surprise. A team that misses but tells me early
is a manageable situation. A team that misses silently is not." """,
    """STRONG sounds like: the five-way diagnosis; looking at unplanned work,
blocked time and rework rather than at the burndown; owning four of the five
causes yourself; and separating the missing problem from the SURPRISE problem.
That last distinction is the senior move.

WEAK sounds like: escalating to their manager as a first step, or adding more
oversight - a daily check-in with the person who is already behind. Also weak:
treating it as a motivation problem when a third of their capacity is being
taken by someone else.

THE DETAIL THAT IMPRESSES: "committed capacity was never real". Experienced
operators know unplanned work is the usual culprit and that it is invisible by
default.""",
    ["You find they are losing 40% of capacity to support. What do you change?",
     "The team lead insists everything is fine. What now?",
     "How do you raise this with their manager without it becoming a "
     "performance conversation?",
     "What if it is genuinely a capability gap and you have no authority over "
     "them?",
     "How do you get an honest mid-sprint signal rather than a green one?"],
    """* Escalating first. It is available, it is fast, and it usually diagnoses
  nothing while costing you the relationship.
* Adding oversight to a team that is already blocked or interrupted - it slows
  them further and confirms their sense that nobody is listening.
* Jumping to the capability explanation, which is the least common cause.
* Fixing the miss and not the surprise.
* Making it about accountability language rather than about capacity
  arithmetic.""",
    ["delivery", "diagnosis", "influence", "program"],
    difficulty="Medium",
    frequency="Very common - a standard probe in the program round.",
    prep_minutes=35,
))

_B2.append(E(
    "program",
    "How do you run a launch? Take me through go / no-go.",
    "Whether you have actually shipped something consequential. This question "
    "is easy to answer plausibly and hard to answer credibly - the credible "
    "version is full of specifics that only come from having been in the room "
    "when it went wrong.",
    """THE STRUCTURE

1. LAUNCH CRITERIA AGREED IN ADVANCE, IN WRITING
   Define what "ready" means weeks before the date, when the conversation is
   unemotional. Functional completeness, performance targets, error budget,
   security and privacy sign-off, support readiness, docs, legal, and the
   rollback plan. The point of agreeing early is that on launch day you are
   checking against a standard rather than negotiating one under pressure.

2. NAMED OWNERS AND EXPLICIT SIGN-OFFS
   Every criterion has one accountable name. "Engineering is ready" is not a
   sign-off; a person saying "I am ready, here is my evidence" is.

3. DRESS REHEARSAL BEFORE THE REAL THING
   A game day or a dry run in production-like conditions. Test the rollback -
   an untested rollback plan is a wish. This is the single item most teams skip
   and most regret.

4. THE GO / NO-GO MEETING ITSELF
   * Held with enough time to actually stop - not two hours before.
   * Each owner states ready or not-ready with evidence.
   * ONE named decision-maker. Consensus go/no-go decisions do not converge.
   * Any not-ready is a no-go by default, and going anyway is a conscious,
     recorded exception with a named risk owner.
   * Agree the rollback trigger BEFORE launching: the specific metric and
     threshold at which you revert without reconvening. Deciding that during an
     incident is how teams talk themselves out of rolling back.

5. STAGED ROLLOUT RATHER THAN A BIG BANG
   Internal, then 1%, then 10%, then 50%, then all - with a defined soak time
   and pass criteria at each step. Big-bang launches exist for date-driven
   reasons, not technical ones, and you should say so.

6. THE WAR ROOM AND THE COMMS PLAN
   Who is watching which dashboard, for how long. Who talks to customers, who
   talks to executives, and how often - including when there is no news, which
   is when people start inventing it.

7. AFTER: MEASURE AND LEARN
   Watch the success metric AND the guardrails for a defined period. Then a
   blameless retro that produces owned actions, not observations.""",
    """A WORKED ANSWER - the parts that show you have done it

"The most important part happens weeks before the date: agreeing in writing what
'ready' means. Functional scope, performance targets, error budget, security and
privacy sign-off, support trained, docs done, rollback tested. Agreeing that
early matters because on launch day you want to be checking against a standard,
not negotiating one while everybody is tired and invested.

Every criterion gets one name against it. 'Engineering is ready' is not a
sign-off - a person saying 'I am ready and here is the evidence' is.

Before the real thing I want a dress rehearsal, and specifically I want the
rollback tested. An untested rollback plan is a wish, and the moment you need it
is the worst possible time to discover it does not work.

The go/no-go meeting itself: held early enough that stopping is genuinely still
an option, each owner declaring ready or not with evidence, and one named
decision-maker. Go/no-go by consensus does not converge - somebody has to own
it. Any not-ready is a no-go by default; going anyway is allowed but it is a
conscious recorded exception with a named risk owner, not a shrug.

The thing I insist on before we launch is the rollback trigger: the specific
metric and threshold at which we revert without reconvening. If you leave that
to be decided during the incident, teams talk themselves out of rolling back
every single time - there is always a reason to wait five more minutes.

Then staged rollout rather than big bang: internal, 1%, 10%, 50%, 100%, with a
soak time and pass criteria at each gate. If someone wants a big bang, that is a
date-driven decision rather than a technical one, and I'd want that said out
loud so the risk is owned.

During, a war room with named dashboard owners and a comms cadence that includes
updates when there is nothing to report - because when updates stop, people
invent their own version.

After, watch the guardrails as hard as the success metric for a defined period,
then a blameless retro that produces owned actions with dates. A retro that
produces observations is entertainment." """,
    """STRONG sounds like: criteria agreed in writing early; named sign-offs;
rollback TESTED; the rollback trigger agreed before launch; staged rollout with
soak times; and one named decision-maker. Each of these is a specific that only
comes from experience.

WEAK sounds like: "we'd have a checklist and a go/no-go meeting and monitor
after launch" - true, generic, and indistinguishable from someone who has read
about it. Also weak: no rollback plan, or a rollback plan nobody has run.

THE DETAIL THAT IMPRESSES: pre-agreeing the rollback trigger, with the reason -
that teams reliably talk themselves out of rolling back in the moment. It is a
statement about human behaviour under pressure, which is what launch management
actually is.""",
    ["One owner says not-ready two hours before a launch the CEO has announced "
     "publicly. What do you do?",
     "You are at 10% and the metric is ambiguous - not clearly bad. Continue or "
     "roll back?",
     "How long is the soak at each stage, and how did you choose?",
     "What do you do when rollback is not possible - a database migration, "
     "say?",
     "How do you run the retro so it produces change rather than a document?"],
    """* Treating go/no-go as a status meeting rather than a decision with an
  owner.
* An untested rollback.
* Big bang because the date demands it, without naming that as a risk decision.
* No pre-agreed rollback trigger - the single most consequential omission.
* Stopping the comms cadence when there is no news.
* A retro with no owned actions.""",
    ["launch", "risk", "governance", "operations", "program"],
    difficulty="Medium",
    frequency="Very common, and a reliable place to demonstrate real shipping "
              "experience.",
    prep_minutes=40,
))

_B2.append(E(
    "program",
    "How do you set up portfolio governance without creating bureaucracy?",
    "A Head-of-function question. They want to know whether you can build "
    "process that people would keep if it were optional. Everyone can add "
    "governance; the skill is adding the minimum that changes decisions.",
    """THE STRUCTURE

1. STATE THE TEST FIRST
   "Every forum and every artefact has to answer one question: what DECISION
   does this make, and who would notice if it stopped? If nobody would notice,
   it is theatre and I would delete it." Leading with this frames everything
   after it as deliberate rather than accumulated.

2. GOVERN BY EXCEPTION, NOT BY REVIEW
   Do not review everything monthly. Define thresholds - size, risk, cross-org
   blast radius - and only escalate what breaches them. Most programs should
   never reach a governance forum at all, and saying that out loud is the
   difference between governance and bureaucracy.

3. TIER THE PORTFOLIO EXPLICITLY
   Tier 1 (company-level bets): reviewed monthly by executives, full TPM
   coverage. Tier 2 (significant, cross-team): reviewed on exception, shared
   TPM. Tier 3 (team-local): not governed centrally at all - trust the team.
   Say the ratio you would expect: perhaps 5 / 20 / everything else.

4. ONE SOURCE OF TRUTH, ENTERED ONCE
   The fastest way to make governance hated is asking teams to report the same
   status in three places. Data entered once, read by many. If a report cannot
   be generated from where the work already lives, question whether it should
   exist.

5. DECISION LOG OVER STATUS ARCHIVE
   Record decisions, their rationale and their owner. Six months later nobody
   needs last April's RAG status; everybody needs to know why you chose the
   vendor.

6. TIME-BOX THE PROCESS ITSELF AND MEASURE IT
   Put an expiry on new process - "we will run this for two quarters and then
   justify it again". Track decision latency: how long from a decision being
   needed to being made. If governance is working, that number falls; if it is
   bureaucracy, it rises, and you now have the evidence to kill your own
   process.

7. BE WILLING TO DELETE YOUR OWN MECHANISMS
   Say you would audit the forums annually and remove any that no longer make
   decisions. Leaders who only add process are the reason people fear
   governance.""",
    """A WORKED ANSWER

"My test for any forum or artefact is: what decision does this make, and who
would notice if it stopped? If I cannot answer both, I delete it. I'd apply that
to what already exists before I add anything of my own.

Then I'd govern by exception rather than by review. The instinct is to review
everything monthly, which scales linearly with the portfolio and eventually
consumes the function. Instead I'd set thresholds - investment size, cross-org
blast radius, regulatory exposure - and only what breaches them comes to a
forum. Most programs should never appear in governance at all.

Concretely I'd tier the portfolio. Maybe five company-level bets reviewed
monthly with executives and full TPM coverage; twenty significant cross-team
programs reviewed only on exception with shared coverage; and everything else
governed by the teams themselves. I'd be explicit that tier three is not
neglected, it is trusted - if I cannot trust a team to run its own work, that is
a different problem and governance will not fix it.

Data gets entered once. The quickest way to make people hate governance is to
ask for the same status in three formats. If I cannot generate a report from
where the work already lives, I question whether the report should exist.

I'd keep a decision log rather than a status archive. In six months nobody needs
April's RAG status; everybody needs to know why we picked that vendor and who
owned it.

And I'd put an expiry date on my own process - we run it for two quarters and
then it has to justify itself again. The metric I'd watch is decision latency:
how long from a decision being needed to it being made. Good governance drives
that down. If it goes up, what I have built is bureaucracy and I should say so
and remove it." """,
    """STRONG sounds like: the what-decision-does-this-make test stated first;
governing by exception with explicit tiers and rough numbers; enter-once data;
a decision log; and - most of all - a measure of your own process and a
willingness to delete it.

WEAK sounds like: describing a governance structure - steering committees,
monthly reviews, a PMO dashboard - with no test for whether any of it earns its
place. That is precisely the bureaucracy the question is asking you to avoid.

THE DETAIL THAT IMPRESSES: decision latency as the metric for governance
quality, plus an expiry date on new process. It shows you hold your own
mechanisms to the same standard you hold everyone else's.""",
    ["An executive wants every program reviewed monthly. How do you push back?",
     "How do you decide the tier thresholds?",
     "What would you delete first in a typical PMO?",
     "How do you stop tier 3 programs from failing invisibly?",
     "What if decision latency rises after your changes?"],
    """* Adding structure without a test for whether it earns its place.
* Reviewing everything, which does not scale and trains people to prepare for
  meetings rather than to deliver.
* Multiple sources of truth and duplicate status entry.
* Status archives instead of decision logs.
* No measure of the process itself - which means you can never justify removing
  it later.""",
    ["governance", "org-design", "portfolio", "program"],
    difficulty="Hard",
    frequency="Expected at Head-of-function level; a strong differentiator.",
    prep_minutes=40,
))

_B2.append(E(
    "program",
    "A Sev1 is happening right now. What do you do in the first hour?",
    "Whether you know that incident command is a ROLE, not a title, and "
    "whether you separate the people restoring service from the people "
    "communicating. Under pressure most candidates conflate the two, which is "
    "exactly what goes wrong in real incidents.",
    """THE STRUCTURE - first hour, in order

1. ESTABLISH COMMAND (first 5 minutes)
   One incident commander, named out loud, and it is usually NOT the person
   with the deepest technical knowledge - you want your best engineer debugging,
   not coordinating. The commander runs the incident and makes calls; they do
   not fix.

2. SEPARATE THE THREE JOBS IMMEDIATELY
   * Restore service (the responders)
   * Communicate (a comms lead - internal, executive, customer)
   * Run the incident (the commander)
   Conflating these is the single most common failure: the person who knows the
   system ends up explaining it to executives instead of fixing it.

3. MITIGATE BEFORE YOU DIAGNOSE
   The goal in the first hour is to stop the bleeding, not to understand it.
   Roll back, fail over, disable the feature flag, shed load. Root cause is a
   tomorrow problem. Say this explicitly - it is the instinct that separates
   people who have run incidents from people who have read about them.

4. ASK THE FASTEST DIAGNOSTIC QUESTION: WHAT CHANGED?
   The overwhelming majority of incidents are caused by a change - a deploy, a
   config edit, a certificate, a feature ramp, a traffic shift. Check the change
   log before theorising.

5. SET A COMMS CADENCE AND HOLD IT
   Updates on a fixed interval - every 30 minutes - even when there is nothing
   new, because the moment updates stop, executives start pulling responders out
   of the incident to ask for them. Say what you know, what you do not, and when
   the next update comes.

6. PROTECT THE RESPONDERS
   One channel in and out. The commander absorbs the executive pressure so the
   engineers never feel it. "The single most useful thing a senior leader can do
   in an incident is stand between the engineers and everyone else."

7. TRACK A TIMELINE AS YOU GO
   Someone records actions and times live. Reconstructing it afterwards from
   memory is unreliable, and the timeline is what makes the post-mortem real.

8. DECIDE THE STAND-DOWN CRITERIA
   What does resolved mean - mitigated or fixed? Say which, because declaring
   victory on mitigation and going home is how you get the same incident twice
   in one night.""",
    """A WORKED ANSWER

"First thing, within five minutes: name an incident commander out loud, and it
should not be the person with the deepest knowledge of the failing system - I
want them debugging, not coordinating.

Then I'd split three jobs that get conflated under stress: restoring service,
communicating, and running the incident. The classic failure is that the one
engineer who understands the system spends the first forty minutes explaining it
to executives instead of fixing it.

The priority in the first hour is mitigation, not diagnosis. Roll back, fail
over, kill the feature flag, shed load - stop the bleeding. Root cause is a
tomorrow problem, and I'd say that explicitly because engineers naturally want
to understand before they act, and in an incident that instinct costs customers.

The fastest diagnostic question is 'what changed' - deploys, config, certs,
feature ramps, traffic shifts. Most incidents are a change, so I'd check the
change log before anyone theorises.

I'd set a comms cadence of every 30 minutes and hold it even when there is
nothing new, because the moment updates stop, executives start pulling
responders out to ask for one. Each update says what we know, what we do not,
and when the next one lands.

If I'm the senior person, my most useful contribution is to stand between the
engineers and everyone else. One channel in, one channel out. Nobody messages a
responder directly.

Somebody records a live timeline, because reconstructing it from memory
afterwards produces a fiction and the post-mortem depends on it.

And I'd be explicit about stand-down criteria - are we mitigated or actually
fixed? Declaring resolved on mitigation and standing everyone down is how you
get the same incident again at 3am." """,
    """STRONG sounds like: command established first; the three roles separated;
mitigate-before-diagnose stated as a principle; "what changed" as the first
diagnostic; a held comms cadence including no-news updates; and shielding the
responders. The stand-down distinction between mitigated and fixed is a
strong close.

WEAK sounds like: "I'd get everyone on a call and start troubleshooting" -
which is what actually happens in badly run incidents. Also weak: leading with
root cause analysis, or having the most senior engineer run comms.

THE DETAIL THAT IMPRESSES: "the most useful thing a senior leader can do is
stand between the engineers and everyone else." It is a leadership answer to a
technical question and it lands.""",
    ["The CEO joins the call and starts asking questions. What do you do?",
     "Mitigation would mean rolling back a release the business announced "
     "today. Do you roll back?",
     "Two hours in and you still do not know the cause. What changes?",
     "How do you decide the severity level in the first place?",
     "What does a good post-mortem look like the next day?"],
    """* Diagnosing before mitigating.
* No named commander, so decisions get made by whoever is loudest.
* The best debugger doing comms.
* Letting the comms cadence lapse during the hard part - precisely when people
  most need it.
* Standing down on mitigation without saying so.
* No live timeline, which makes the post-mortem guesswork.""",
    ["incident", "crisis", "communication", "operations", "program"],
    difficulty="Medium",
    frequency="Common, especially where the role owns operational readiness.",
    prep_minutes=35,
))

_B2.append(E(
    "product",
    "You have 20 things on the roadmap and capacity for 6. How do you choose?",
    "Whether you have a defensible prioritisation method and, more "
    "importantly, whether you can hold the line on the things you cut. The "
    "framework matters less than the fact that you have one and can explain "
    "its failure modes.",
    """THE STRUCTURE

1. ESTABLISH THE OBJECTIVE FIRST
   You cannot prioritise without knowing what you are optimising for this
   period - revenue, retention, cost, risk reduction, strategic position. If
   the objective is not agreed, the prioritisation argument is really a
   disagreement about strategy wearing a spreadsheet.

2. SIZE VALUE AND COST ROUGHLY, NOT PRECISELY
   RICE, weighted scoring, whatever you like - but say out loud that the score
   is a CONVERSATION STARTER, not a decision. Anyone who has used RICE knows the
   reach and impact numbers are estimates with a factor-of-three error, and
   pretending otherwise is how teams launder opinion as arithmetic.

3. SEPARATE THE THINGS THAT ARE NOT NEGOTIABLE
   Compliance, security, keeping the lights on, and paying down debt that is
   actively slowing delivery. These come off the top as a fixed allocation -
   typically 15-25% - rather than competing on ROI, because they always lose an
   ROI contest and then you have an outage.

4. CHECK THE PORTFOLIO SHAPE, NOT JUST THE RANKING
   A ranked list optimises each item and can still produce a terrible portfolio:
   six incremental improvements and no bet, or six bets and nothing that ships
   this quarter. I'd want a deliberate mix of near-term wins, one or two real
   bets, and the non-negotiables.

5. APPLY THE CONSTRAINT HONESTLY
   Six means six. The failure mode is starting fourteen at 40% staffing, which
   delivers nothing and looks busy. Work in progress is the enemy: half-finished
   work has delivered zero value and consumed real money.

6. PUBLISH THE NOT-DOING LIST - the part that matters most
   Explicitly name the fourteen you are not doing, and say when they will next
   be considered. Ambiguity about the cut items is what generates back-channel
   lobbying all quarter. A published, dated not-doing list converts an argument
   into a scheduled decision.

7. HAVE THE CONVERSATION WITH THE PEOPLE WHOSE ITEMS WERE CUT
   In person, before the list is published. Cheap to do and it buys most of the
   political cover you will need.""",
    """A WORKED ANSWER

"Before ranking anything I'd want to know what we are optimising for this
period. Most prioritisation arguments are actually disagreements about strategy
that nobody has surfaced, and a scoring spreadsheet will not settle them.

Then I'd take the non-negotiables off the top - compliance, security, and the
tech debt that is measurably slowing us down - as a fixed allocation of maybe
20%. They have to be carved out rather than scored, because they always lose an
ROI comparison and then you get an incident.

For the rest I'd score value against effort - RICE is fine - but I'd say
clearly that the score is a conversation starter, not a decision. The reach and
impact numbers are estimates with a large error bar, and treating the output as
arithmetic is how teams launder an opinion into a number.

Then I'd look at the SHAPE of the six, not just the ranking. A pure top-six by
score often gives you six incremental improvements and no bet at all, or the
reverse. I'd want a deliberate mix: a few things that ship this quarter, one or
two real bets, and the non-negotiables.

And six means six. The most common failure I see is starting fourteen at partial
staffing - it feels responsive, it delivers nothing, and half-finished work has
consumed real money for zero value.

The part I'd spend the most care on is publishing the not-doing list, with the
date when each item will next be considered. If you leave the cut items
ambiguous, you spend the whole quarter being lobbied. If they are explicitly out
until the next planning cycle, the argument becomes a scheduled decision rather
than a running one.

And I'd tell the people whose items were cut myself, before the list goes out.
It costs an hour and it buys most of the goodwill you need to hold the line." """,
    """STRONG sounds like: objective before scoring; non-negotiables carved out
rather than scored; scepticism about your own scoring method; portfolio shape as
well as ranking; the WIP argument; and above all the published, dated not-doing
list. That last one is what separates people who have actually held a roadmap.

WEAK sounds like: "I'd use RICE and take the top six" - a method with no
judgement. Also weak: no not-doing list, and any answer where the security and
compliance work competes on ROI.

THE DETAIL THAT IMPRESSES: telling the people who got cut personally, before
publication. Interviewers hear the framework a hundred times and the political
craft almost never.""",
    ["An exec adds a 21st item mid-quarter and says it is critical. What "
     "happens?",
     "Two items score identically. How do you break the tie?",
     "How do you defend the tech-debt allocation when revenue is under "
     "pressure?",
     "What would make you change the six mid-quarter?",
     "The team believes item 12 is the most important thing. How do you handle "
     "that?"],
    """* A scoring framework presented as objective truth.
* No explicit objective, so the ranking has no basis.
* Starting more than capacity allows - the most common and most expensive
  error.
* No not-doing list, which guarantees a quarter of lobbying.
* Letting non-negotiables compete on ROI.
* Optimising each item and ignoring the shape of the portfolio.""",
    ["prioritization", "roadmap", "stakeholders", "product"],
    difficulty="Medium",
    frequency="Very common - appears in the product round and again with "
              "different framing in the program round.",
    prep_minutes=35,
))

_B2.append(E(
    "product",
    "A competitor just launched a feature we do not have. How do you respond?",
    "Whether you can resist reflexive feature-matching and reason about "
    "whether the threat is real. The instinct to copy is strong and usually "
    "wrong, and panels use this question specifically to see whether you have "
    "it.",
    """THE STRUCTURE

1. RESIST THE REFLEX, OUT LOUD
   "My default is not to match. Most competitor launches do not require a
   response, and reflexive matching means your roadmap is set by someone else."
   Saying this first frames everything after it.

2. ESTABLISH WHETHER IT IS ACTUALLY A THREAT
   Three questions, in order:
   * Do OUR customers want it? Check support requests, sales-loss reasons,
     churn interviews, usage data. Not "is it clever" but "is anyone asking".
   * Does it change the BUYING DECISION? A feature that appears on a
     procurement checklist is a real threat; a feature that demos well and
     changes nobody's choice is not.
   * Is it strategic for them or opportunistic? Something that reinforces their
     core advantage matters far more than a side experiment.

3. GET EVIDENCE FAST, ON A DEADLINE
   Talk to sales about live deals, look at win/loss over the next few weeks,
   ask customer success what customers are asking. Give it two to three weeks
   with a decision date, so this does not become an open anxiety.

4. CHOOSE FROM FOUR RESPONSES - and say which and why
   * IGNORE: not our segment, not our strategy. The most common correct answer,
     and the hardest one to hold.
   * NEUTRALISE: build the minimum that removes it as a differentiator, and no
     more. Right when it is a checklist item rather than a real need.
   * DIFFERENTIATE: do not match; go harder where you are strong, so the
     comparison happens on your ground rather than theirs.
   * LEAPFROG: they have revealed a real unmet need and you can serve it better.
     Genuine, and rarer than people claim.

5. HANDLE THE INTERNAL PANIC, WHICH IS THE REAL PROBLEM
   The hardest part is usually not the analysis - it is an executive who saw the
   launch and wants a response by Friday. The move is to commit to a decision
   DATE rather than to a build, and to bring evidence to that date. That
   converts panic into a scheduled decision without dismissing the concern.

6. SAY WHAT WOULD CHANGE YOUR MIND
   "If we lose two deals in the next month with this named as the reason, I
   would reprioritise." A trigger makes ignoring it a managed position rather
   than a stubborn one.""",
    """A WORKED ANSWER

"My default is not to respond. Most competitor launches do not need one, and a
team that matches every launch has handed its roadmap to a competitor - you are
permanently one quarter behind, building their strategy with your engineers.

So first I'd establish whether it is actually a threat, and I'd answer three
questions. Do our customers want it - is it showing up in support requests,
lost-deal reasons, churn conversations? Does it change the buying decision, or
is it just impressive in a demo? And is it strategic for them or opportunistic -
something that reinforces their core advantage is far more serious than a side
experiment.

I'd give that two or three weeks with a hard decision date. Sales will know
within a fortnight whether it is coming up in live deals, and that is the
highest-signal evidence available.

Then one of four responses. Ignore, which is the most common correct answer and
the hardest to hold. Neutralise - build the minimum that removes it as a
differentiator and not one feature more, which is right when it is a
procurement-checklist item rather than a real need. Differentiate - go harder
where we are already strong so the comparison happens on our ground. Or leapfrog,
if they have revealed a genuine unmet need we can serve better.

Honestly, the hardest part of this question is rarely the analysis. It is the
executive who saw the launch on Monday and wants a response by Friday. What I'd
commit to is a decision DATE, not a build - 'you will have a recommendation with
evidence in three weeks'. That takes the concern seriously without spending
engineering capacity on an emotional reaction.

And I'd name the trigger that would change my mind: if we lose two deals in the
next month with this cited as the reason, I reprioritise. That makes ignoring it
a managed position rather than a stubborn one, which is also what makes it
survivable politically." """,
    """STRONG sounds like: default-not-to-match stated up front; evidence
gathering with a deadline; the four named responses with a reasoned choice;
handling the internal panic by committing to a decision date; and a named
trigger that would reverse the call.

WEAK sounds like: "we'd assess and add it to the roadmap" - which is matching
with extra steps. Also weak: dismissing it entirely with no evidence, which is
just a different reflex.

THE DETAIL THAT IMPRESSES: naming the internal panic as the real problem.
Everybody analyses the competitor; very few candidates acknowledge that the
actual work is managing an anxious executive, and that committing to a date
rather than a build is how you do it.""",
    ["Sales says they lost three deals this week because of it. Does that "
     "change your answer?",
     "Your CEO has already promised a customer you will build it. Now what?",
     "How do you tell the difference between a checklist feature and a real "
     "need?",
     "What if the competitor is much better resourced than you?",
     "When is fast-following actually the right strategy?"],
    """* Reflexive matching - the failure mode this question exists to detect.
* Analysis with no deadline, which becomes a permanent low-grade anxiety.
* Ignoring it without evidence, which is equally unthinking.
* No trigger to revisit, which turns a judgement into stubbornness.
* Not addressing the internal politics, which is the part that actually
  determines what happens.""",
    ["strategy", "competitive", "prioritization", "product"],
    difficulty="Medium",
    frequency="Common in the product round, especially in competitive markets.",
    prep_minutes=35,
))

_B2.append(E(
    "product",
    "How do you work with a PM when you disagree about priority or scope?",
    "The TPM-specific relationship question, and it is asked in most loops "
    "because the PM/TPM seam is where the role either works or does not. They "
    "want to know you understand the boundary - the PM owns WHAT and WHY, you "
    "own HOW and WHEN - and that you can disagree without either steamrolling "
    "or capitulating.",
    """THE STRUCTURE

1. STATE THE BOUNDARY, BECAUSE IT RESOLVES MOST DISAGREEMENTS
   The PM owns what we build and why. You own how and when it gets delivered,
   and the honesty of the plan. If the disagreement is about VALUE, they decide
   and you support it. If it is about FEASIBILITY, COST or RISK, that is your
   ground and you should hold it. Saying this clearly shows you know the role.

2. SEPARATE THE THREE KINDS OF DISAGREEMENT
   * "I think this is worth less than you do" - their call. Make your case once,
     then commit.
   * "This will take three times what you think" - your call. Bring the
     evidence, not the opinion.
   * "This sequence creates avoidable risk" - your call, and the one where TPMs
     add the most value and most often stay quiet.

3. ARGUE IN THE CURRENCY OF TRADE-OFFS, NOT OBJECTIONS
   Never "we can't do that by then". Always "we can have A by March, or A and B
   by May, or A and a reduced B by April - here is what each costs and what I
   recommend." You are handing them a decision rather than a wall, and it keeps
   ownership where it belongs.

4. MAKE THE DISAGREEMENT CHEAP TO RESOLVE
   Propose the smallest experiment that would settle it - a spike, a prototype,
   a week of data. Most PM/TPM disagreements are about an unknown that could be
   resolved for less than the cost of the argument.

5. DISAGREE AND COMMIT - VISIBLY
   Once decided, support it publicly and completely. If you were overruled and
   you believe it is genuinely risky, write the risk down once, with the
   trigger, and then get behind it. The written record is not for
   score-settling; it is so that if the risk lands, the conversation is about
   the response rather than about who said what.

6. IF IT KEEPS HAPPENING, FIX THE RELATIONSHIP, NOT THE INSTANCE
   Repeated conflict usually means unclear decision rights or a missing shared
   goal. Agree the boundary explicitly, and get on the same metric - a PM and
   TPM measured on different things will disagree forever, and no amount of
   good faith fixes it.""",
    """A WORKED ANSWER

"I start from a clear boundary: the PM owns what we build and why, I own how and
when, and the honesty of the plan. Most disagreements resolve the moment you
work out which side of that line you are on.

If we disagree about VALUE - they think a feature matters more than I do - that
is their call. I make my case once, properly, and then I commit. A TPM who
relitigates product decisions becomes someone the PM routes around.

If we disagree about FEASIBILITY or RISK, that is my ground and I hold it. But I
hold it with evidence rather than assertion - here is the dependency, here is
what the last three similar projects took, here is the specific thing I think
breaks.

And I try never to say 'we can't do that by then', because that is a wall. I say
'we can have A by March, or A and B by May, or a reduced B by April, and here is
what I recommend and why'. That hands them a decision rather than an obstacle,
which keeps the ownership in the right place and usually produces a better
outcome than either of our original positions.

Where I can, I make the disagreement cheap to settle. Most of them are actually
about an unknown, and a one-week spike often costs less than the argument.

Once it is decided I get behind it visibly. If I was overruled on something I
genuinely think is risky, I write the risk down once with a trigger, and then I
support the decision fully. That record isn't for saying I told you so - it is
so that if it happens, we spend the meeting on the response instead of on who
said what.

If it keeps happening with the same person, I'd stop treating the instances and
look at the relationship. Usually it is either unclear decision rights or the
two of us being measured on different things. A PM on feature delivery and a TPM
on predictability will disagree permanently, and that is a management problem,
not a personality one." """,
    """STRONG sounds like: the WHAT/WHY versus HOW/WHEN boundary stated
explicitly; different handling for value versus feasibility disagreements;
options-with-a-recommendation instead of objections; the cheap experiment; and
disagree-and-commit with a written risk rather than a grudge. The
different-metrics insight at the end is a Director-level observation.

WEAK sounds like: "I'd escalate to leadership" - which tells the panel you
cannot resolve a peer relationship. Also weak: always deferring, which makes you
a coordinator rather than a partner; or fighting on product ground, which makes
you an obstacle.

THE DETAIL THAT IMPRESSES: writing the risk down with a trigger and then
genuinely committing. It shows you can lose an argument professionally, which is
most of what senior collaboration actually is.""",
    ["The PM goes around you to your engineers. How do you handle it?",
     "You were overruled and the risk you flagged materialised. What do you do "
     "the next day?",
     "How do you disagree with a PM who is much more senior than you?",
     "What if the PM keeps changing scope mid-sprint?",
     "When is escalating actually the right call?"],
    """* Escalating a peer disagreement early - it reads as an inability to
  operate laterally.
* Fighting on product ground rather than delivery ground.
* Always deferring, which is the other failure and is just as visible.
* Saying no without options.
* Committing publicly while undermining privately - the most damaging pattern
  and the one people notice.""",
    ["collaboration", "influence", "product", "stakeholders"],
    difficulty="Medium",
    frequency="Asked in most TPM loops - the PM/TPM seam is a standard probe.",
    prep_minutes=30,
))

_B2.append(E(
    "product",
    "How would you decide whether to sunset a feature or product?",
    "Whether you can kill things. Organisations accumulate features because "
    "nobody is rewarded for removal, and a leader who can retire things "
    "cleanly is genuinely rare. The question is also testing whether you think "
    "about the customers you would harm.",
    """THE STRUCTURE

1. ESTABLISH THE TRUE COST OF KEEPING IT
   Not just maintenance engineering. The full cost is: on-call burden, security
   patching, the constraint it places on every future change, the testing
   surface, the support load, the documentation, and the cognitive cost to every
   engineer who has to reason around it. Most sunset arguments fail because only
   the first item is counted.

2. ESTABLISH WHO ACTUALLY USES IT - carefully
   Raw usage numbers mislead. Cut by: how many accounts, WHICH accounts (one
   feature used only by your three largest customers is not a candidate), how
   deeply, and whether it is load-bearing for a workflow that otherwise breaks.
   Low usage plus strategic customers equals do not touch.

3. ASK WHY IT FAILED - because it changes the decision
   Was it never valuable, or was it valuable and badly executed, undiscovered,
   or unsupported? Killing something that failed on execution rather than on
   premise means you may rebuild it in two years having learned nothing.

4. CONSIDER THE OPTIONS BETWEEN KEEP AND KILL
   Freeze (no new investment, keep it running). Narrow (support only the core
   use case). Migrate (build the replacement path first). Divest or open-source.
   Deprecate-then-remove on a long timeline. Sunset is rarely binary and saying
   so shows judgement.

5. PLAN THE MIGRATION BEFORE ANNOUNCING ANYTHING
   The order that goes wrong: announce, then work out the path. Have the
   alternative ready, and for the affected accounts, a named person and a plan
   before they hear about it publicly.

6. THE COMMUNICATION, WHICH IS MOST OF THE RISK
   Generous timelines - a year for anything enterprise. Direct contact for
   affected customers, not a blog post. Be honest that it is a business decision
   rather than pretending it is for their benefit. And never surprise sales or
   support - they will hear it from a customer, and you will have destroyed
   their credibility.

7. THE TRUST COST IS THE REAL COST
   Every sunset teaches customers something about whether to depend on you.
   That is why the migration path and the timeline matter more than the
   engineering saving.""",
    """A WORKED ANSWER

"I'd start with the true cost of keeping it, because that number is almost
always understated. It is not just the maintenance engineer - it is the on-call
burden, the security patching, the testing surface, and most importantly the
constraint it puts on every future change. A feature that forces every migration
to carry a special case is expensive in a way that never appears in a budget.

Then who actually uses it, and I'd be careful here because raw usage misleads.
I want to know which accounts, not how many. A feature used by 2% of users can
be untouchable if that 2% is your three largest customers, and I have seen teams
walk into that.

I'd also ask why it failed, because it changes the decision. If it was never
valuable, kill it. If it was valuable but undiscoverable or badly executed, then
killing it means we may rebuild the same thing in two years having learned
nothing.

And I'd resist treating it as binary. There is freeze, narrow to the core use
case, migrate people to a replacement, divest, or a long deprecation. Full
removal is often the most expensive option in trust terms for a modest
engineering saving.

The sequencing matters enormously: build the migration path BEFORE announcing.
The classic failure is announcing a sunset and then working out where people are
supposed to go, which turns a routine decision into a crisis.

On communication - generous timelines, a year for anything enterprise. Affected
customers hear it from a person, not a blog post. I'd be honest that it is a
business decision rather than dressing it up as being for their benefit, because
customers see through that and it costs more than the truth would have. And I'd
brief sales and support before anyone external hears it - if a customer tells
their account manager about our own sunset, we have damaged that relationship
for years.

The thing I'd hold onto is that the real cost of a sunset is not engineering, it
is what it teaches customers about depending on us. That is why the migration
path and the timeline are worth more than the saving." """,
    """STRONG sounds like: full cost including the constraint on future work;
WHICH accounts rather than how many; asking why it failed; the options between
keep and kill; migration path before announcement; and trust as the real cost.

WEAK sounds like: "low usage, so we'd deprecate it" - usage alone is the
shallowest possible read. Also weak: announcing before there is a migration
path, and forgetting that sales and support need to know first.

THE DETAIL THAT IMPRESSES: "a feature that failed on execution rather than on
premise" - it is the distinction that stops organisations rebuilding the same
mistake every three years.""",
    ["Your biggest customer uses it and threatens to leave. What now?",
     "Engineering wants it gone; sales wants it kept. Who wins?",
     "How long a deprecation window, and how did you pick it?",
     "How do you stop the org accumulating features like this in the first "
     "place?",
     "What if you sunset it and were wrong?"],
    """* Judging on raw usage without segmenting by account value.
* Announcing before the migration path exists.
* Treating it as binary when freeze or narrow is usually cheaper.
* Blindsiding sales and support.
* Pretending the sunset benefits the customer.
* Counting only the engineering saving and ignoring the trust cost.""",
    ["strategy", "product-lifecycle", "stakeholders", "product"],
    difficulty="Medium",
    frequency="Common at Director+ - a good signal of whether you can remove "
              "things, not just add them.",
    prep_minutes=35,
))

ENTRIES.extend(_B2)

# ── Batch 3: org-design cases, product sizing, and the questions YOU ask ───

_B3 = []

_B3.append(E(
    "program",
    "Centralised, embedded, or hybrid - how would you structure the TPM "
    "function here?",
    "The defining org-design question for a Head of TPM. They are testing "
    "whether you have a considered position rather than a preference, whether "
    "you can name what each model costs, and whether you would let the "
    "company's actual situation decide rather than your last job's answer.",
    """THE STRUCTURE

1. REFUSE THE FALSE CHOICE, THEN COMMIT ANYWAY
   "There is no universally right answer - the model should follow where
   delivery actually breaks here. But if you want my default, it is hybrid, and
   here is what would make me choose differently." Say this first: it shows
   judgement without dodging, which is exactly the balance being tested.

2. NAME WHAT EACH MODEL BUYS AND WHAT IT COSTS
   CENTRALISED (TPMs report into a TPM org, deployed onto programs)
     Buys: consistent standards, real career paths, the ability to move people
     to where the risk is, an independent view of status that has not been
     filtered by the delivering org.
     Costs: distance from the teams, "process police" perception, and TPMs who
     know the method but not the domain.
   EMBEDDED (TPMs report into engineering or product)
     Buys: deep domain knowledge, trust, presence in the real conversations.
     Costs: no consistency, no career path, TPMs quietly absorbed into
     scrum-master or chief-of-staff work, and - the one that matters most -
     status that reports up through the same person whose delivery it describes.
   HYBRID (solid line to TPM function, dotted to the org they serve)
     Buys: most of both.
     Costs: real matrix tension, and it needs an actual arbitration mechanism,
     not goodwill.

3. STATE THE DECIDING QUESTION
   "Where does delivery break here?" If it breaks ACROSS teams - dependencies,
   integration, portfolio decisions - you need central weight. If it breaks
   INSIDE teams - poor planning, unclear requirements - you need embedded
   depth. That single question does more work than any framework.

4. SAY WHAT ELSE WOULD MOVE YOU
   Company size and stage; how many programs genuinely cross org boundaries;
   whether engineering leadership already plans well; whether there is an
   existing TPM career ladder; and how much trust the function currently has -
   a distrusted function cannot be centralised into relevance.

5. NAME THE INDEPENDENCE PROBLEM OUT LOUD
   The strongest single argument against pure embedding: if a TPM's performance
   review is written by the person whose program they report on, the status
   will be optimistic and nobody will be lying. Structure decides what gets
   reported, and saying this shows you understand incentives, not just boxes.

6. SAY HOW YOU WOULD DECIDE, NOT JUST WHAT YOU PREFER
   "I'd spend my first month finding out which of those failure modes is
   actually present before proposing a structure" - and then say what you
   would expect to find at their size.""",
    """A WORKED ANSWER

"I don't think there's a universally right answer, but I'll give you my default
and what would change it.

My default is hybrid - solid line into the TPM function, dotted line into the
org served. The reason is that the two pure models each fail in a predictable
way, and hybrid buys most of both if you are honest about the tension.

Pure centralised gives you consistent standards, real career paths, and the
ability to move your strongest person to wherever the risk currently is - which
is genuinely valuable and hard to replicate. What it costs you is distance.
Centralised TPMs know the method and not the domain, and they get perceived as
process police, which is fatal to influence.

Pure embedded gives you domain depth and trust, and TPMs who are actually in the
conversations that matter. What it costs is consistency and career path - and
the thing I'd flag hardest, independence. If a TPM's performance review is
written by the leader whose program they report on, status will be optimistic
and nobody will be lying. That's not a character issue, it's an incentive one,
and structure is how you fix incentives.

So the question I'd actually want answered before proposing anything is: where
does delivery break here? If it breaks across teams - dependencies, integration,
portfolio-level choices - I need central weight. If it breaks inside teams -
weak planning, unclear requirements - then embedded depth is what buys the
improvement and centralising would just add a layer.

At most companies past a few hundred engineers, both are true to some degree,
which is why I land on hybrid - but with the arbitration mechanism written down.
Matrix models fail when nobody has said in advance who decides when the two
lines disagree, and that is a governance detail people skip and then suffer.

Concretely I'd expect to embed TPMs day to day with the orgs they serve, hold
standards, calibration, hiring and promotion in the function, and keep a small
central group for the cross-cutting programs that belong to nobody." """,
    """STRONG sounds like: a stated default with explicit conditions that would
change it; the costs of each model named as precisely as the benefits; "where
does delivery break here" as the deciding question; and the independence /
incentive argument, which is the point most candidates miss entirely.

WEAK sounds like: "it depends" with no position - the panel reads that as no
experience. The opposite failure is equally bad: "centralised, because that is
how we did it at my last company", with no reference to their situation.

THE DETAIL THAT IMPRESSES: naming the arbitration mechanism for the matrix.
Everyone says hybrid; almost nobody says who decides when the solid and dotted
lines disagree, which is precisely why hybrids fail in practice.""",
    ["We are 300 engineers and everything is embedded today. What would you "
     "change first?",
     "Engineering leaders will resist losing their TPMs. How do you handle "
     "that?",
     "How do you keep centralised TPMs from becoming process police?",
     "Who wins when the solid line and the dotted line disagree?",
     "What ratio of TPMs to engineers do you aim for, and why?",
     "How would you know in six months whether the model was working?"],
    """* No position. "It depends" without a default reads as inexperience.
* Importing your last company's structure without reference to theirs.
* Listing benefits of each model without the costs - the costs are what show
  you have lived with them.
* Missing the independence problem, which is the strongest structural argument
  available to you.
* Proposing a matrix without saying who arbitrates.""",
    ["org-design", "operating-model", "leadership", "program"],
    difficulty="Hard",
    frequency="Very likely for a Head-of-TPM role - often an entire round.",
    prep_minutes=45,
))

_B3.append(E(
    "program",
    "How do you decide which programs get a dedicated TPM, and what is your "
    "TPM-to-engineer ratio?",
    "A capacity and judgement question. They want to hear that you allocate "
    "your scarcest resource against RISK rather than spreading it evenly or "
    "assigning by org chart - and that you can say no to a request for "
    "coverage.",
    """THE STRUCTURE

1. START FROM WHAT A TPM IS FOR
   A TPM earns their place where COORDINATION COST is high - many teams, hard
   dependencies, external commitments, regulatory exposure, or a decision that
   nobody owns. A single team building a well-understood feature does not need
   one, and saying that out loud is what makes the rest credible.

2. GIVE THE ALLOCATION TEST, NOT A FORMULA
   Dedicated coverage when at least two of these hold:
   * Four or more teams must coordinate to deliver it
   * There is an external or immovable commitment (customer, regulator, event)
   * Cross-org dependencies with no single owning leader
   * High blast radius if it goes wrong
   * Significant investment - the size where the company would want to know
   Shared or light coverage otherwise. No coverage at all for team-local work,
   and be explicit that this is trust, not neglect.

3. GIVE A RATIO, WITH THE CAVEAT
   Rough industry range is one TPM per 30-60 engineers, but say why the range
   is so wide: it depends entirely on coordination complexity. Platform work
   with heavy interdependence might be 1:25; a set of independent product teams
   might be 1:80. A ratio is an outcome of the allocation test, not an input to
   it - offering the number without that caveat suggests you manage by
   headcount formula.

4. SAY HOW YOU FLEX IT
   Keep a small amount of the function uncommitted - maybe 15% - so you can
   surge onto whatever is on fire. A fully allocated function has no capacity
   to respond, and the things that need a TPM most are rarely predicted at
   planning time.

5. SAY HOW YOU SAY NO
   "A leader asks for a dedicated TPM because their peer has one. I'd take them
   through the allocation test rather than the queue - and if it does not meet
   the bar, I'd offer the mechanism instead of the person: help them set up the
   planning and dependency practice so they do not need one."

6. NAME THE FAILURE MODE YOU ARE AVOIDING
   Spreading thin. A TPM across five programs is a status aggregator on all
   five and is changing the outcome of none. Concentrated coverage on the
   things that matter beats thin coverage everywhere, and that is the choice
   you are actually making.""",
    """A WORKED ANSWER

"I'd allocate against coordination cost and risk, not against the org chart.
A TPM adds value where coordination is expensive - many teams, hard
dependencies, an external commitment, regulatory exposure. A single team
building something well understood does not need one, and I'd say that plainly,
because a function that claims everything needs coverage loses credibility fast.

My test for dedicated coverage is at least two of: four or more teams have to
coordinate; there is an immovable external commitment; there are cross-org
dependencies with no single owning leader; the blast radius is high; or the
investment is large enough that the company would want to know how it is going.

On ratio - the honest answer is somewhere between one per thirty and one per
sixty engineers, and the range is that wide because it is entirely driven by
coordination complexity. Deeply interdependent platform work might be one to
twenty-five; a set of genuinely independent product teams might be one to
eighty. I'd treat the ratio as an output of the allocation test rather than an
input, because managing to a headcount formula is how you end up with TPMs
assigned to work that does not need them.

I'd also hold back around fifteen percent of the function unallocated, so I can
surge onto whatever is actually on fire. A fully committed function cannot
respond, and the programs that most need help are rarely the ones you predicted
at planning time.

The failure mode I'm most trying to avoid is spreading thin. A TPM covering five
programs becomes a status aggregator on all five and changes the outcome of
none. I would rather cover three things properly and tell the truth about the
rest than claim coverage everywhere.

And when a leader asks for a dedicated TPM mainly because their peer has one,
I'd walk them through the allocation test rather than the queue - and if it does
not meet the bar, offer the mechanism instead of the person. Often what they
actually need is a better planning and dependency practice, and helping them set
that up is cheaper for both of us." """,
    """STRONG sounds like: allocation against risk and coordination cost; a
concrete test with named criteria; a ratio offered WITH the reason the range is
wide; reserved surge capacity; and a clear answer for how you decline a request.

WEAK sounds like: a flat ratio quoted as a standard, or "every program should
have a TPM", which is both unaffordable and untrue. Also weak: no answer for the
political request, which is the part of this job that actually consumes time.

THE DETAIL THAT IMPRESSES: offering the mechanism instead of the person. It
reframes the function from supplying bodies to raising the delivery capability
of the org, which is the Head-of-function altitude.""",
    ["Your best TPM is on a program that no longer needs them. What do you do?",
     "A VP escalates to the CTO because you declined coverage. How does that "
     "go?",
     "How do you justify the size of your function at budget time?",
     "What does a TPM actually do that an engineering manager cannot?",
     "How do you avoid TPMs becoming status reporters?"],
    """* A fixed ratio with no reasoning behind it.
* Claiming every program needs coverage - unaffordable and it devalues the
  function.
* Full allocation with no surge capacity.
* No mechanism for declining, which means allocation gets decided by whoever
  escalates hardest.
* Not naming the thin-coverage failure mode, which is the most common way TPM
  functions become irrelevant.""",
    ["org-design", "capacity", "operating-model", "program"],
    difficulty="Hard",
    frequency="Very likely at Head-of-function level, usually alongside the "
              "operating-model question.",
    prep_minutes=40,
))

_B3.append(E(
    "product",
    "Design a product (or feature) for [a specific user segment].",
    "Open-ended product sense. The panel wants to see structure imposed on a "
    "vague prompt, a real user need identified, and a solution that is chosen "
    "rather than listed. The single biggest differentiator is whether you "
    "narrow before you broaden.",
    """THE STRUCTURE - about 25 minutes

1. CLARIFY AND SCOPE, BRIEFLY (2 min)
   Ask two or three questions, not ten: what is the business goal, is there a
   platform constraint, are we assuming a new product or an addition. Then
   state your scope and move - long clarification reads as stalling.

2. PICK A SPECIFIC USER AND A SPECIFIC MOMENT (3 min)
   Not "commuters" but "a commuter who has just missed a connection and needs to
   re-plan while walking". The narrower the moment, the better every subsequent
   idea gets. Say why you chose this segment: size, pain, strategic value.

3. LIST THEIR JOBS AND PAIN POINTS (5 min)
   Three to five real needs, in their words rather than in feature language.
   Then pick ONE to solve and say explicitly why the others lose. This is where
   most candidates fail by trying to solve everything.

4. SOLUTIONS - THREE, AT DIFFERENT AMBITIONS (6 min)
   A minimal version, a fuller version, and a differentiated bet. Sketch the
   core flow of your recommendation in four or five steps so it becomes
   concrete rather than conceptual.

5. RECOMMEND AND JUSTIFY THE TRADE-OFF (3 min)
   Commit to one. Name what it costs, what you deliberately left out, and who
   would object.

6. METRICS AND VALIDATION (3 min)
   The success metric, a guardrail, and the cheapest way to test the core
   assumption before building - a concierge test, a fake door, ten user
   interviews.

7. RISKS AND WHAT WOULD KILL IT (2 min)
   The assumption most likely to be wrong, and what you would do if it is.

FOR A TPM SPECIFICALLY: after the product answer, add thirty seconds on how you
would SEQUENCE it - what ships first, what the riskiest technical unknown is,
what you would spike. That is your edge in this round and most candidates never
use it.""",
    """A WORKED ANSWER - a feature for enterprise admins, compressed

CLARIFY: "I'll assume this is an addition to our existing product, the goal is
retention rather than acquisition, and web is fine as a starting surface."

SEGMENT AND MOMENT: "I'll take the IT admin at a 2,000-person customer, in the
specific moment where someone has left the company and they need to remove
their access everywhere. I pick that moment because it is frequent, it is
security-sensitive so it has executive attention, and it is where admin tools
usually feel worst."

JOBS AND PAIN: "Their jobs are: know who has access to what; grant and revoke
quickly; prove compliance at audit; and not become the bottleneck for every
routine request. The pain: revoking access means visiting several systems and
they can never be certain they got everything, which is a real anxiety, not just
an inconvenience."

PICK ONE: "I'd solve certainty of revocation. Audit reporting matters but it is
periodic; self-service delegation is valuable but larger. Revocation is frequent,
anxious and security-critical - that combination is where a small amount of
product effort buys disproportionate trust."

SOLUTIONS: "Minimal - a single view of one person's access with a one-click
revoke-all and a receipt showing what was revoked. Fuller - integrate with the
HR system so departures trigger it automatically, with the admin approving.
The bet - continuous access intelligence: flag over-permissioned accounts and
unused access proactively, which turns the product from a tool into a posture."

RECOMMEND: "Start with the single view and revoke-all with a receipt. The
receipt is the actual product - the anxiety is not the clicking, it is the not
knowing. It is small, it is testable, and it earns the right to do the HR
integration next."

METRICS: "Time from departure to full revocation, and the share of revocations
completed in one action. Guardrail: accidental over-revocation, which would be
far worse than the original problem, so I'd want an undo window and I'd watch
support tickets."

VALIDATION: "Before building, I'd sit with five admins and watch them do a real
revocation. If the pain is elsewhere - say they cannot even get the list of
leavers - my whole solution is aimed at the wrong step."

TPM ADDENDUM: "On sequencing - the riskiest unknown is whether we can enumerate
access consistently across all our integrations. I'd spike that for two weeks
before committing to a date, because if enumeration is unreliable the receipt is
worthless and the feature is not worth shipping." """,
    """STRONG sounds like: a narrow user AND moment; one problem chosen with the
others explicitly declined; a concrete flow rather than a concept; a
recommendation with its cost; a cheap validation before building; and - for a
TPM - the sequencing and technical-risk addendum.

WEAK sounds like: designing for "users" in general; five features of equal
weight; no metric; and no commitment. Also weak: spending eight minutes on
clarifying questions, which panels read as avoidance.

THE DETAIL THAT IMPRESSES: identifying that the receipt, not the revoke, is the
product. Finding the emotional core of a workflow - the anxiety, not the
click - is what product sense actually is.""",
    ["Why that segment rather than a bigger one?",
     "Your five admin interviews say the real pain is elsewhere. What do you "
     "do?",
     "How would you price this, or does it change the price at all?",
     "What is the riskiest assumption in your recommendation?",
     "How would you sequence this across two quarters?",
     "What would you cut if you had half the time?"],
    """* Designing for a broad, unspecified user.
* Listing features rather than choosing one and defending it.
* No moment - a segment without a situation produces generic ideas.
* Over-clarifying at the start.
* No validation step, so the whole design rests on unexamined assumptions.
* Missing the TPM edge: sequencing and technical risk are yours to add and
  almost nobody does.""",
    ["product-sense", "design", "user-research", "product"],
    difficulty="Hard",
    frequency="Common as the main exercise in a product round.",
    prep_minutes=45,
))

_B3.append(E(
    "close",
    "What questions should YOU ask them - and what do they signal?",
    "At Director+ the questions you ask are graded as heavily as the answers "
    "you give. They reveal what you think the job is, whether you have "
    "diagnosed the organisation, and whether you are evaluating them back - "
    "which is what a genuine senior candidate does. Weak questions ('what does "
    "a typical day look like?') actively cost you.",
    """HOW TO USE THIS
Prepare eight to ten and pick per interviewer. Ask two or three per round -
enough to show engagement, not so many that you run the clock. The best ones
are specific to what that person just told you, so listen for the thread and
pull it.

FOR THE HIRING MANAGER - diagnose the actual job
* "What made you decide to hire for this now rather than a year ago?" -
  reveals whether this is growth, a gap, or a rescue.
* "What does this function need to be true in twelve months that is not true
  today?" - gets you the real mandate rather than the job description.
* "Where does delivery break most often here today - across teams or inside
  them?" - the single most useful diagnostic question available, and it signals
  that you already think in those terms.
* "What has been tried already that did not work?" - saves you proposing it in
  month two, and people are surprisingly candid.
* "Who are the two or three people whose support I would most need, and what
  would win them over?" - reads as someone planning to succeed rather than
  planning to arrive.

FOR ENGINEERING / PRODUCT PEERS - find out whether the function is valued
* "What do TPMs here do that genuinely helps, and what feels like overhead?" -
  the highest-signal question you can ask a peer, and it signals you care about
  value over territory.
* "When something slips, how do you usually find out?" - tells you everything
  about the reporting culture in one answer.
* "What is the last decision that took too long, and why?" - decision latency
  is the best single proxy for organisational health.

FOR THE SKIP-LEVEL OR EXEC PANEL - test the altitude
* "What is the biggest bet the company is making that most people here do not
  yet feel?" - invites a strategy conversation and shows you operate there.
* "How do you want to hear bad news, and how quickly?" - reveals whether the
  culture is honest, and demonstrates that you plan to deliver it.
* "What would make you regret this hire in a year?" - direct, slightly
  disarming, and the answer is genuinely useful. Use it once, with someone
  senior enough to enjoy it.

ABOUT THE ROLE'S REALITY - the ones that protect you
* "What is the decision-making authority of this role - what can I decide alone,
  what do I recommend?" - the most important question about the job and very
  few people ask it.
* "How is this function measured, and by whom?"
* "What does the first 90 days look like from your side?"

QUESTIONS TO AVOID
* Anything answerable from the website or the job description.
* "What does a typical day look like?" - reads as junior at this level.
* Compensation and benefits in a technical or panel round; that is a recruiter
  conversation.
* Anything that implies you have not researched the company.
* More than three per round - you are being timed too.""",
    """HOW TO DELIVER THEM

Ask them as though you are still deciding - because you should be. A senior
candidate evaluating the role is more attractive than one auditioning for it,
and the difference is audible.

Follow up on the answer rather than moving to the next question on your list.
"You said decisions take too long - where does the delay usually sit?" That
turns your questions into a conversation, which is what they will remember.

Write down what you hear about the same question from different people. If the
hiring manager says the function is valued and the engineering director
describes it as overhead, you have learned the single most important thing about
the job - and you can raise it, carefully, at offer stage.

THE ONE TO CLOSE ON
"Is there anything about my background that gives you hesitation, that I could
address now?" It takes nerve, it is occasionally uncomfortable, and it is the
only chance you will ever get to answer an objection instead of losing to it
silently. Use it at the end of the round with the hiring manager.""",
    """STRONG questions are diagnostic - they show you are already forming a
model of the organisation. "Where does delivery break, across teams or inside
them?" tells them how you think in nine words.

WEAK questions are informational - things you could have read, or things that
signal you are thinking about your comfort rather than about the job. At this
level, asking nothing at all is worse than asking something imperfect: it reads
as either disinterest or as having already decided.

THE ONE THAT MOST CHANGES THE ROOM: asking peers what TPMs do that feels like
overhead. It signals a leader who cares whether the function earns its cost,
which is exactly what a company hiring a Head of TPM is worried about.""",
    ["(Prepare an answer for) Why are you leaving your current role?",
     "(Prepare for) What are you looking for that you do not have today?",
     "(Prepare for) What other processes are you in?",
     "(Prepare for) What would you need to say yes?",
     "(Prepare for) Do you have any concerns about us?"],
    """* Having no questions. It is read as disinterest and it is the most common
  self-inflicted wound at this level.
* Asking only about the role and never about the business.
* Reading from a list without listening - the follow-up is what lands.
* Raising compensation in a panel round.
* Asking so many that you consume the interviewer's remaining time.""",
    ["closing", "positioning", "interview-craft"],
    difficulty="Medium",
    frequency="Every round ends here - guaranteed, and frequently scored.",
    prep_minutes=30,
))

ENTRIES.extend(_B3)


# ══ Tags, rounds and the planning layer ═══════════════════════════════════
# Same planning fields as the other banks so the whole prep has one currency:
# how long will this take, and what should I do first.

_DIFF_MULT = {"Easy": 0.8, "Medium": 1.0, "Hard": 1.25}

for _e in ENTRIES:
    if not _e.get("prep_minutes"):
        # Case answers are prepared by rehearsing the framework out loud until
        # you can produce it without the page, then adapting it to two or three
        # different scenarios. That is 30-45 minutes of real work.
        _base = 30 * _DIFF_MULT.get(_e["difficulty"], 1.0)
        _base += len((_e.get("worked") or "").split()) / 60.0
        _e["prep_minutes"] = int(round(min(60, _base) / 5.0) * 5)
    _m = _e["prep_minutes"]
    _e["prep_label"] = f"{_m} min" if _m < 60 else "1h"
    if not _e.get("frequency"):
        _e["frequency"] = "Commonly asked in a senior TPM loop."


def _freq_tier(e):
    f = (e.get("frequency") or "").lower()
    if "most likely" in f or "single most" in f or "large majority" in f:
        return 3.0
    if "extremely common" in f or "very common" in f or "very likely" in f:
        return 2.5
    if "common" in f:
        return 2.0
    return 1.4


# Cases where a weak answer costs you the loop outright, regardless of how
# often they are asked. The frequency tiers alone put "first 90 days" mid-pack
# on an alphabetical tie-break, which is wrong for a Head-of-function hire -
# it is frequently the question the decision turns on.
_MUST_REHEARSE = {
    "What would you do in your first 90 days as Head of TPM here?",
    "You inherit a critical program that is three months late. Walk me through "
    "your first 30 days.",
    "How would you improve [our product]?",
    "How would you run a program with 12 teams and a hard external date?",
    "How do you measure the health of a program? What is on your dashboard?",
    "How do you set up portfolio governance without creating bureaucracy?",
    "Design a product (or feature) for [a specific user segment].",
    "Centralised, embedded, or hybrid - how would you structure the TPM "
    "function here?",
    # Guaranteed in every round and frequently scored, so it cannot sit in the
    # long tail no matter what the frequency wording says.
    "What questions should YOU ask them - and what do they signal?",
}


def _rank_score(e):
    return _freq_tier(e) + (1.5 if e["title"] in _MUST_REHEARSE else 0.0)


_ordered = sorted(ENTRIES, key=lambda e: (-_rank_score(e), e["round"], e["title"]))
_total = max(1, len(_ordered))
for _i, _e in enumerate(_ordered, 1):
    _e["rank"] = _i
    _pct = _i / _total
    _e["priority"] = ("P0" if _pct <= 0.35 else "P1" if _pct <= 0.70 else "P2")

_PRIORITY_NOTE = {
    "P0": "P0 - rehearse this one out loud before the round.",
    "P1": "P1 - know the framework well enough to produce it without the page.",
    "P2": "P2 - read the framework; you can adapt from a neighbouring case.",
}
for _e in ENTRIES:
    _e["priority_note"] = _PRIORITY_NOTE[_e["priority"]]

#: Total rehearsal time for the case rounds, in minutes.
TOTAL_PREP_MINUTES = sum(e["prep_minutes"] for e in ENTRIES)

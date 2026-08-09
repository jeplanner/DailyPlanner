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


_ordered = sorted(ENTRIES, key=lambda e: (-_freq_tier(e), e["round"], e["title"]))
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

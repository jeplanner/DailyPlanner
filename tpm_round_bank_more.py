"""Additional case-round entries that extend `tpm_round_bank`.

`tpm_round_bank` holds the core 22 product, program and closing cases for a
Senior Director / Head-of-TPM loop. This module adds twelve more, written for
a candidate coming from a large e-commerce marketplace (tens of millions of
daily users, one enormous annual sale event) and targeting either Director of
Engineering or Director/VP TPM:

  * eight more PROGRAM cases - peak-event readiness, platform migration,
    executive status, budget cuts, killing programs, annual planning, shipping
    an LLM feature, and a vendor that will miss its date;
  * a new ENGINEERING round - the leadership/case round in a Director of
    Engineering loop: technical debt, reliability, an underperforming manager,
    and the hiring bar.

Usage from tpm_round_bank:

    from tpm_round_bank_more import build, EXTRA_ROUNDS, EXTRA_BRIEFS
    ENTRIES += build(E)

`build` takes the `E(...)` entry function as an argument so this module never
imports tpm_round_bank (and so cannot create an import cycle).
"""

EXTRA_ROUNDS = {"engineering": "Engineering Leadership Round"}

#: Same voice and purpose as tpm_round_bank.ROUND_BRIEF.
EXTRA_BRIEFS = {
    "engineering": (
        "In a Director of Engineering loop this round replaces the program "
        "round, and it is testing whether you run an ENGINEERING SYSTEM - "
        "quality, reliability, people, hiring - or just a delivery schedule. "
        "The failure mode for a strong delivery manager is answering every "
        "question as a project: 'I would put a plan together and track it "
        "weekly'. They want the operating model underneath: the policy you "
        "would sign, the metric you would review every week, the "
        "conversation you would have and the exact sentence you would open "
        "it with. Name what you would STOP doing as often as what you would "
        "start, and show you know that most engineering problems at this "
        "altitude are incentive problems wearing a technical costume."
    ),
}


def build(E):
    """Return the extra entries, built with the caller's `E(...)`."""
    out = []

    # ======================================================================
    #  PROGRAM MANAGEMENT ROUND - additional cases
    # ======================================================================

    out.append(E(
        "program",
        "Run readiness for the biggest sale event of the year.",
        "Whether you treat peak readiness as an engineering system with "
        "measurable exit criteria, or as a calendar of meetings that ends in "
        "a war room. At a large marketplace this is the one program everyone "
        "has an opinion about, so the panel is listening for the details only "
        "someone who has carried the pager on day one would know: that the "
        "peak is a minute not a day, that degradation is decided in advance, "
        "and that half the failures live in partners you do not control.",
        """THE STRUCTURE - work backwards from the first minute of the sale

T-12 WEEKS: FORECAST THE PEAK MINUTE, NOT THE DAY
  * The event is decided in the first 10-30 minutes after go-live, when every
    user who set an alarm arrives at once. Forecast peak requests per second
    per CRITICAL JOURNEY - home, search, product page, cart, checkout,
    payment, order confirmation - from last year's peak x traffic growth x
    the marketing plan (a top-of-hour flash deal is its own thundering herd).
  * Provision to roughly 1.5-2x forecast on checkout and payment, 1.3x
    elsewhere. The forecast WILL be wrong; the headroom is for that.
  * One accountable engineering owner per journey, named in writing.

T-10 TO T-3 WEEKS: PROVE IT - LOAD TESTS AND GAME DAYS
  * At least three production-scale load-test rounds replaying last year's
    traffic SHAPE, not a flat ramp. Each round produces a bottleneck list;
    the exit criterion is "1.5x forecast sustained for 60 minutes with p99
    inside SLO on every critical journey".
  * Game days that break things on purpose: kill a zone, a cache cluster, a
    payment gateway, the feature-flag service. Measure time to detect and
    time to mitigate, not just whether it recovered.
  * Map the hidden dependencies - auth, config, OTP/SMS, notifications,
    the offer and pricing engine. They are where last year's outage was.

THE DEGRADATION LADDER AND KILL SWITCHES
  * An ordered list of what you switch off as load rises: recommendations,
    reviews, personalised widgets, search suggestions, non-essential
    notifications, then a virtual waiting room in front of checkout.
  * Every rung has an owner, a tested switch, and a measured load saving.
    The war-room commander can pull rungs 1-3 WITHOUT asking anyone - decide
    the decision rights now, not at 00:04 on sale night.

CODE FREEZE AND CHANGE CONTROL
  * Freeze the checkout and payment path at T-7 days, everything at T-3.
    Config and feature-flag changes count as changes. Exceptions need a named
    approver and a rehearsed rollback.

PARTNERS AND VENDORS
  * Payment gateways, issuing banks running card offers, logistics, OTP
    providers, CDN. Get capacity commitments in transactions per second in
    writing, test gateway failover routing end to end, and validate every
    bank-offer configuration before go-live - a misconfigured offer is a
    finance incident, not an engineering one.

GO / NO-GO (T-2 DAYS)
  * Binary criteria: load-test exit met, every ladder rung tested, freeze
    holding, partner sign-offs in, on-call roster staffed with 12-hour shift
    caps. A "no" on one journey means a mitigation, not cancelling the sale.

THE WAR ROOM
  * One incident commander per shift, a separate comms lead, one screen of
    six to eight BUSINESS metrics (orders per minute versus forecast, payment
    success rate per gateway, checkout p99, cart error rate), and a 30-minute
    business sync so leaders stop walking into the bridge.

POST-EVENT REVIEW (within two weeks)
  * What NEARLY broke, not only what broke; forecast accuracy by journey;
    and scale-down of the extra capacity so the cloud bill does not become
    the second incident.""",
        """A WORKED ANSWER - condensed to how you would say it

"I'd run it backwards from the first minute of the sale, because that's where
the event is won or lost. Everybody who set an alarm arrives in the same ten
minutes, so I forecast peak requests per second per critical journey - search,
product page, cart, checkout, payment - not daily orders. Then I provision
checkout and payment to about twice that forecast, because the forecast will
be wrong and I'd rather pay for idle capacity for a week than lose the first
hour.

From about ten weeks out the program is evidence, not status. Three rounds of
production-scale load tests replaying last year's traffic shape, each one
ending with a bottleneck list and an owner per item. The exit criterion is
written down: one and a half times forecast for an hour, p99 inside SLO on
every journey. Alongside that, game days where we kill a cache cluster or a
payment gateway on purpose and time how long it takes us to notice.

The piece I'd spend most effort on is the degradation ladder. Before the
event we agree, in order, what we switch off as load climbs - recommendations
first, then reviews and personalisation, and finally a waiting room in front
of checkout. Every rung is tested in a game day and the incident commander
can pull the first three without calling anybody. Nobody should be debating
whether to turn off recommendations at four minutes past midnight.

Then partners. Half of last year's pain at most marketplaces is outside the
building - a payment gateway that tops out below its contract, an OTP
provider that throttles, a bank offer configured wrong. I want their
capacity in transactions per second in writing and I want gateway failover
tested end to end.

Freeze the checkout path a week out, everything three days out, and config
counts as code. Go/no-go two days before with binary criteria. In the war
room, one commander per shift, a separate comms lead, and one screen of
business metrics - orders per minute against forecast and payment success by
gateway tell me more than any CPU graph.

And within two weeks, a review of what nearly broke, because the near-misses
are next year's outage." """,
        """STRONG sounds like: peak MINUTE per journey rather than daily volume;
load-test exit criteria stated as a number; a degradation ladder with
pre-agreed decision rights; partners treated as first-class failure points;
config changes inside the freeze; and business metrics, not infrastructure
metrics, on the war-room screen.

WEAK sounds like: "I'd set up a readiness tracker, run weekly reviews with
all the teams, do load testing and have a war room on the day." Every item is
true and none of it is a mechanism - there is no threshold, no decision
right and nothing that would fail a team.

THE DETAIL THAT IMPRESSES: "the incident commander can pull the first three
rungs without asking anyone." It shows you know that the cost of an outage on
sale night is mostly the minutes spent deciding, not the minutes spent
fixing.""",
        ["The load test passes at 1.2x but not 1.5x, and you are two weeks out. "
         "What do you do?",
         "Marketing adds a surprise flash deal at 8pm the week before. How do "
         "you respond?",
         "Twenty minutes in, payment success drops from 92% to 70% on one "
         "gateway. Walk me through the next ten minutes.",
         "A VP wants an exception to the code freeze for a revenue feature. "
         "Do you grant it?",
         "How do you decide how much over-provisioning is worth the cost?",
         "What did you change after the last event you ran?"],
        """* Forecasting daily orders instead of peak requests per second per
  journey. The day is fine; the minute is what falls over.
* Load tests with a flat ramp and no exit criterion - you learn the system
  survives a load it will never see.
* A degradation plan that exists as a document but has never been exercised,
  or one that needs a VP on the phone before anyone can pull a switch.
* Forgetting that config and feature-flag changes are changes.
* Ignoring partners: gateways, banks, OTP and logistics providers are where a
  large share of peak-day incidents actually start.
* No post-event review of near-misses, and no capacity scale-down plan.""",
        ["peak-readiness", "capacity", "reliability", "e-commerce", "program"],
        difficulty="Hard",
        frequency="Very likely for any e-commerce or consumer-scale role - "
                  "often the anchor case of the program round.",
        prep_minutes=45,
    ))

    out.append(E(
        "program",
        "Plan a large platform migration - monolith to services, or a database "
        "cutover - without stopping the business.",
        "Whether you understand that a migration is a risk-management program "
        "with a business running on top of it, not an engineering project with "
        "a launch date. The panel is listening for incremental cutover, proven "
        "equivalence before switching, a written point of no return, and the "
        "recognition that the long tail and decommissioning are where these "
        "programs actually die.",
        """THE STRUCTURE

1. STATE THE WHY AND THE REAL FINISH LINE
   Name the business reason (deploy velocity, scale ceiling, licence cost,
   an end-of-life database). Then define done as "the old system is switched
   off and its cost is gone" - not "the new system is live". Running two
   systems forever is the most common outcome and the most expensive one.

2. INVENTORY FROM TRAFFIC, NOT FROM DOCUMENTATION
   Find every caller and every consumer from access logs and query logs. The
   ones that hurt are invisible: nightly batch jobs, finance reconciliation,
   a reporting extract someone built in 2019, a partner hitting an old
   endpoint.

3. STRANGLE IT, ONE SEAM AT A TIME
   Put a routing facade in front of the old system so traffic can be moved a
   path at a time. Carve along domain seams. Start with a low-risk READ path
   to prove the machinery, then one write path, then the rest. Never a big
   bang.

4. PROVE EQUIVALENCE BEFORE YOU SWITCH
   * Shadow traffic: send real requests to both, serve the old answer, diff
     the new one. Target a mismatch rate below roughly 0.01% and explain
     every class of mismatch.
   * Dual-write with a reconciliation job that runs continuously and pages on
     drift. Backfill history before cutover, not after.

5. WRITTEN, BINARY CUTOVER CRITERIA
   e.g. shadow diff under threshold for 14 consecutive days; reconciliation
   showing zero unexplained mismatches for 7; p99 within 10% of the old path;
   rollback rehearsed IN PRODUCTION; on-call for the new service trained and
   staffed.

6. RAMP, ROLLBACK, AND THE POINT OF NO RETURN
   Ramp 1 -> 5 -> 25 -> 50 -> 100% with hold periods. Rollback is one switch
   until you stop dual-writing; that moment is the point of no return, and it
   is a named decision with a named approver, not something that just
   happens.

7. RESPECT THE BUSINESS CALENDAR
   No cutover steps inside the sale-event freeze window or month-end close.
   Plan the timeline around the calendar, not the other way round.

8. RUN THE LONG TAIL AS ITS OWN PROGRAM
   The last 10% of callers takes half the time. A tracker per caller, a
   published deprecation date, scheduled brownouts of the old endpoint, and
   escalation for teams that do not move.

9. DECOMMISSION IS THE FINISH LINE
   Delete the code, drop the database, cancel the licence, and report the
   saving. Celebrate the deletion, not the launch.""",
        """A WORKED ANSWER - a checkout database cutover

"First I'd define the finish line as the old database switched off and its
licence cancelled. If I let the team declare victory when the new system takes
traffic, I've just doubled our running cost indefinitely, and that is how most
migrations actually end.

Then inventory from logs, not from the architecture diagram. Every query
against that database for thirty days, grouped by caller. I'd expect to find
three or four consumers nobody listed - a finance reconciliation job, an
analytics extract, something a partner integration still calls.

The approach is strangler, never big bang. A routing layer in front so we can
move one path at a time. First a read path that doesn't matter much - order
history, say - purely to prove the shadowing, diffing and rollback machinery
works. Then one write path. Then the rest.

Before any path switches, I want equivalence proven, not asserted. Shadow
real traffic to the new store, keep serving from the old one, and diff every
response. Dual-write with a reconciliation job that pages on drift. The
cutover criteria are written and binary: fourteen days under the diff
threshold, a week of zero unexplained reconciliation mismatches, p99 within
ten percent, and a rollback we have actually executed in production, not just
written down.

Then ramp - one, five, twenty-five, fifty, a hundred - with holds. The
moment we stop dual-writing is the point of no return, and I'd make that an
explicit decision with my name and the engineering owner's on it.

Two things I'd protect hard. The business calendar: nothing moves inside the
sale freeze or month-end close, so the plan is built around those windows.
And the long tail. The last ten percent of callers will take half the
elapsed time, so I'd run it as a program of its own - a tracker per caller, a
published deprecation date, and brownouts of the old endpoint a month before
so the stragglers find out in a controlled way rather than on shutdown day.

And I'd report the program as complete only when the decommissioning saving
shows up in the cost report." """,
        """STRONG sounds like: decommissioning defined as done; inventory from
traffic; strangler with a deliberately boring first path; shadow diffing and
reconciliation as the proof; written cutover criteria; an explicitly named
point of no return; and the long tail treated as a program.

WEAK sounds like: a phased plan of "design, build, test, migrate, go live"
with a date at the end. That is a project plan for a greenfield system; it
has nothing in it about running two systems at once, which is the actual
problem.

THE DETAIL THAT IMPRESSES: brownouts. Deliberately failing the old endpoint
for an hour a month before shutdown flushes out unknown callers safely, and
almost nobody mentions it.""",
        ["Shadow diffs show 0.3% mismatches you cannot explain. Do you cut "
         "over?",
         "The migration is 80% done and the team wants to move on to new "
         "features. What do you do?",
         "How do you handle a schema change in the middle of dual-write?",
         "When is a big-bang cutover actually the right call?",
         "A team owning a critical caller refuses to prioritise moving. "
         "How do you get them to move?",
         "How would you report progress on this to the CEO?"],
        """* Defining done as "new system live" - you will run both forever.
* Inventory from documentation. The undocumented consumers are the ones that
  page you at 3am after cutover.
* Big-bang cutover to save time. It saves time right up until it fails.
* Cutover criteria that are judgement calls ("looks stable") rather than
  numbers.
* No named point of no return, so nobody realises when rollback stopped being
  possible.
* Scheduling risky steps into the sale-event or month-end window.""",
        ["migration", "architecture", "risk", "decommissioning", "program"],
        difficulty="Hard",
        frequency="Very common at platform-heavy companies - and a reliable "
                  "probe of real technical depth for a TPM.",
        prep_minutes=45,
    ))

    out.append(E(
        "program",
        "Write the one-page status for the CEO on a program that is in "
        "trouble.",
        "Executive communication under bad news. They are testing whether you "
        "lead with the bottom line and the decision you need, whether your "
        "colour coding is honest, and whether you can translate engineering "
        "detail into business consequence. A CEO reads the first three lines "
        "and decides whether to read the rest - or whether to call you.",
        """THE STRUCTURE - the page, top to bottom

1. BOTTOM LINE (two lines, no more)
   Status, date confidence, and the ask. "Red. We will miss the 1 March date
   by 4-6 weeks unless we descope. I need a decision on option B by Friday."

2. DECISION NEEDED
   What, by when, and why it is yours to make (it crosses orgs, it costs
   money, or it changes a commitment to a customer or regulator). Two or
   three options with cost, date and risk each, and a recommendation.

3. WHAT CHANGED SINCE THE LAST UPDATE
   The CEO remembers the last page. Explain the delta - "two weeks ago this
   was amber because ..." - or you lose trust you will not get back.

4. WHY, IN ONE PARAGRAPH
   Cause, not blame, and not a timeline of events. One sentence on what is
   being done about the cause.

5. CONFIDENCE AND WHAT WOULD CHANGE IT
   "70% confident in mid-April. What would move it: the payments partner's
   certification on 20 March."

6. NEXT CHECKPOINT
   When they will hear from you next and what will be known by then.

THE RULES BEHIND THE PAGE
  * RAG honesty. Watermelon status - green outside, red inside - is the most
    common failure in program reporting. Define the colours: red means "will
    miss without a decision I cannot make myself"; amber means "at risk,
    recoverable within my authority, with an exit date"; green means on plan.
  * Never go green to red. If you skip amber, the problem was hidden or the
    reporting was broken; either way, say which.
  * No jargon. Translate every technical item into its business consequence:
    not "reconciliation service has P0 defects" but "sellers could be paid the
    wrong amount".
  * Write it to be forwarded. It will go to the board or the CFO without you.""",
        """A WORKED ANSWER - how you would talk the panel through it

"The first two lines carry the whole page, because that's often all a CEO
reads. So: 'Seller payouts re-platform: RED. We will miss the 1 March date by
four to six weeks at full scope. I need a decision by Friday between two
options; I recommend B.'

Then the decision section. Option A, hold full scope, ship mid-April, keep
paying the old vendor about two months longer. Option B, ship on 1 March for
the 80% of sellers on standard settlement and move the 20% with custom terms
in April - same total cost, much less risk. Option C, add a team, which I'd
show and argue against, because a new team joining a late program in its
final six weeks adds coordination load before it adds output.

Next, what changed. Two weeks ago I called this amber, so I'd say plainly:
'It was amber because we believed the reconciliation defects were contained.
Testing with real seller data found a second class of mismatch, and that
moved us to red.' If the last page was green, I'd own that too - the CEO
needs to know whether the reporting failed or the program did.

The cause in one paragraph, in business language. Not 'P0 defects in
reconciliation', but 'in testing, about one payout in two thousand came out
wrong, and we will not move sellers' money until that is zero'.

Then confidence: 'Seventy percent confident in 1 March for option B; the
thing that would change it is the bank's sign-off on 20 March.' And when
they'll hear from me next.

Two principles I'd say out loud. First, I define the colours on the page
itself - red means I need a decision I can't make - so nobody has to guess
what my red means versus another program's red. Second, I never let a
program go green to red. If it jumps, something in how we report is broken,
and I'd rather fix that than defend the jump." """,
        """STRONG sounds like: bottom line and ask in the first two lines;
options with a recommendation; an explicit "what changed since last time";
technical detail translated into business consequence; a confidence level
with the event that would move it; and colour definitions on the page.

WEAK sounds like: a page that opens with background and a list of
accomplishments and reaches the bad news in paragraph four. Also weak: an
amber that has been amber for eight weeks - that is red with a softer name.

THE DETAIL THAT IMPRESSES: arguing AGAINST one of your own options on the
page (adding a team late). It shows the CEO you have filtered the choices
rather than handing them a menu.""",
        ["The CEO calls you after reading it and says 'why am I only hearing "
         "this now?' What do you say?",
         "Your engineering VP wants it reported as amber. How do you handle "
         "that?",
         "How do you show confidence without it sounding like hedging?",
         "What goes on the page if you do not yet know the new date?",
         "How do you keep exec status from becoming a weekly theatre?",
         "What is the difference between this page and the one you send to "
         "the program team?"],
        """* Burying the bad news under context and accomplishments.
* Bringing a problem without options, or options without a recommendation.
* Watermelon reporting: green on the page, red in the teams.
* Jargon the CEO has to decode - service names, defect priorities, sprint
  numbers.
* Going green to red with no explanation of what the reporting missed.
* Writing for the room rather than for the forward to the board.""",
        ["communication", "executive", "status", "stakeholders", "program"],
        difficulty="Medium",
        frequency="Very common - often set as a live writing exercise or asked "
                  "as 'how do you communicate bad news upward'.",
        prep_minutes=35,
    ))

    out.append(E(
        "program",
        "Budget is cut by 30% mid-year. Re-plan the portfolio.",
        "Portfolio judgement under pressure. They are testing whether you "
        "clarify what the cut actually is before cutting, whether you can "
        "ignore sunk cost, whether you know that pausing is often killing "
        "slowly, and whether you protect the few things that must not break "
        "while communicating like a leader rather than a spreadsheet.",
        """THE STRUCTURE

1. CLARIFY THE CUT BEFORE TOUCHING THE PORTFOLIO
   30% of WHAT? Annual or run rate, headcount or opex, cloud or contractors,
   is hiring frozen, can it be reallocated across orgs? And do the arithmetic
   out loud: 30% of the annual budget with half the year already spent is 60%
   of what is left to spend. That number changes the whole conversation.

2. RING-FENCE THE CRITICAL FEW
   Keep-the-lights-on, security and compliance, regulatory commitments, and
   anything with a hard external date such as the annual sale event. Name
   them first, and say what they cost, so everyone sees how little is
   actually discretionary.

3. FIND MONEY THAT IS NOT IN THE PORTFOLIO
   Cloud waste (15-25% is routinely recoverable from idle environments,
   over-provisioning and orphaned storage), vendor and licence renegotiation,
   contractors before employees, open requisitions before filled roles. This
   can cover a third of the cut without stopping a single program.

4. SORT EVERYTHING ELSE INTO KEEP / DESCOPE / PAUSE / KILL
   Rank by REMAINING cost against REMAINING value. Sunk cost is irrelevant: a
   program 80% done whose last 20% is the hard part can be a kill; one 10%
   done with the best return is a keep.
   * Descope: ship the 60% that carries 90% of the value.
   * Pause: only with a restart date and a restart condition. A pause without
     both is a kill you have not admitted to, and it also loses the people
     and context.
   * Kill: decide once, cleanly, and harvest.

5. DECIDE FAST
   Two weeks, not two months. A long period of uncertainty costs more
   productivity than the cut itself, and your best people will start
   interviewing.

6. COMMUNICATE ONCE, TOGETHER, IN PERSON FIRST
   Teams whose work is killed hear it from their leader face to face before
   any wider announcement. Then one message to everyone on the same day:
   what is stopping, why, what happens to the people, and what is protected.

7. RE-BASELINE COMMITMENTS
   Every stakeholder who was promised something hears the new plan from you,
   not from the grapevine.""",
        """A WORKED ANSWER

"First I'd ask what the 30% is of, because the answer changes everything. If
it's 30% of the annual budget and we're in July, then I'm cutting 60% of what
is left to spend this year, and I'd want leadership to see that number before
we start, so nobody believes this is a light trim.

Then I'd ring-fence. Keep-the-lights-on, security and compliance, and
anything tied to the sale event in October, because the business cannot
absorb a failure there. I'd put a cost against that list immediately,
because it usually shows that half the budget is not discretionary at all,
and the real cut on the remaining portfolio is far deeper than 30%.

Before cutting any program I'd go after money outside the portfolio. In my
experience 15 to 25 percent of cloud spend is recoverable in a quarter - idle
test environments, over-provisioned clusters sized for last year's peak.
Contractors before employees, unfilled requisitions before filled roles,
licence renegotiations. That can be a third of the cut.

For the rest, I'd rank every program on remaining cost against remaining
value, and I'd say explicitly that sunk cost is not a criterion. Four
outcomes: keep, descope, pause, kill. I'm wary of pause. A pause with no
restart date and no restart condition is a kill that keeps a line on the
roadmap and loses the people anyway. So every pause gets both, or it becomes
a kill.

I'd decide in two weeks. Uncertainty is more expensive than the cut - the
teams stop working and the best engineers start taking recruiter calls.

Communication is where this is won or lost. Teams whose work is being killed
hear it from their own leader, in person, before anything is announced. Then
one message, same day, to everyone: what's stopping, why, what happens to the
people - and I'd aim to redeploy rather than release wherever the skills
transfer. And I'd personally re-baseline with every stakeholder who was
promised something, so the first they hear of it isn't a missed date." """,
        """STRONG sounds like: the "60% of what is left" arithmetic; a costed
ring-fence; money found outside the portfolio before programs are cut;
remaining-cost versus remaining-value ranking with sunk cost explicitly
excluded; the pause-is-a-slow-kill point; and a communication plan that puts
the affected teams first.

WEAK sounds like: "I'd cut 30% from every team." Peanut-butter cuts feel fair
and are almost always wrong - they leave every program under-resourced and
none of them finished.

THE DETAIL THAT IMPRESSES: refusing open-ended pauses. It shows you know what
actually happens to paused programs - the people leave, the context decays,
and the restart costs more than the original estimate.""",
        ["The CEO's pet project is the obvious kill. What do you do?",
         "A program is 85% done but has the lowest remaining value. Finish "
         "or kill?",
         "How do you decide between cutting contractors and cutting a "
         "program?",
         "Two months later the budget is restored. What do you restart?",
         "How do you keep morale up in the teams that survived?",
         "What would you do differently if the cut were 10%?"],
        """* Cutting before clarifying the base - you may be cutting the wrong
  thing by the wrong amount.
* Equal cuts everywhere. Fair, and fatal to the portfolio.
* Letting sunk cost decide - "we have already spent so much on it".
* Open-ended pauses that are really kills.
* A slow decision process. The uncertainty is its own budget cut.
* Teams learning that their program is dead from a broadcast email.""",
        ["portfolio", "prioritization", "budget", "communication", "program"],
        difficulty="Hard",
        frequency="Common at Director+ - especially in loops that care about "
                  "operating discipline and cost.",
        prep_minutes=40,
    ))

    out.append(E(
        "program",
        "Should we kill this program?",
        "Whether you can make a stop decision on its merits rather than on "
        "momentum, politics or sunk cost - and whether you know how to stop "
        "well. Organisations that cannot kill programs cannot fund new ones, "
        "and the panel wants to know you are the kind of leader who frees "
        "capacity rather than hoards it.",
        """THE STRUCTURE

1. REFRAME THE QUESTION
   "Knowing what we know today, would we START this program for its
   remaining cost?" If the answer is no, the burden of proof flips to
   continuing.

2. CHECK THE KILL CRITERIA SET AT THE START
   Good programs launch with a hypothesis, a leading metric, a threshold and
   a date: "if checkout conversion from the new flow is not +1.5 points by
   the end of Q2, we stop." If none were set, set them NOW, with a short
   horizon, and say you would never launch without them again.

3. REMAINING COST VERSUS REMAINING VALUE - AND OPTION VALUE
   Sunk cost does not count. What does count: the value still achievable, the
   probability of achieving it, and the OPTION value - does continuing buy us
   information, a capability, or a position we cannot get otherwise?

4. THE WARNING SIGNS THAT IT SHOULD ALREADY BE DEAD
   * The success metric has been redefined since launch.
   * "One more quarter" has been asked for more than once.
   * The original sponsor has left and nobody has picked it up.
   * The market or strategy that justified it has moved.
   * The team is working on it out of loyalty rather than belief.

5. THE OPTIONS ARE NOT BINARY
   Shrink to a two-person probe with a 6-week question to answer; pivot to
   the part that is working; fold it into another program; or stop.

6. HOW TO STOP WELL
   * Decide quickly and once - a slow death is worse for everyone.
   * Harvest: reusable components, data, learnings, and customer insight.
   * Decommission what shipped, or give it a real owner. Zombie features cost
     on-call forever.
   * Redeploy the people within two weeks, ideally to work they choose.
   * Write the "what we learned" and thank the team publicly. How you kill a
     program determines whether anyone takes a risk next year.""",
        """A WORKED ANSWER - a hyperlocal quick-delivery pilot

"I'd start by reframing it: if this program didn't exist, would we start it
today for what it will cost from here? Whatever we've already spent is gone
either way, so it shouldn't be in the room.

Then I'd look for the kill criteria we set at the beginning. Say this is a
30-minute delivery pilot in three cities, launched on the hypothesis that it
would lift repeat purchase among grocery customers by ten percent within two
quarters, at a contribution margin we could reach at scale. If those were
written down, the conversation is short: we compare against them. If they
weren't, I'd set them now, with a six-week horizon - and I'd note that
launching without them is the actual mistake.

Next, remaining value against remaining cost. Maybe repeat purchase is up
four percent, not ten, and unit economics only work at an order density we
have in one city out of three. That isn't a clean failure. So I'd ask about
option value - is it teaching us something about dark-store operations that
we can't learn otherwise?

I'd also look for the signs that it is already dead. Has the success metric
quietly changed from repeat purchase to 'customer delight'? Has the team
asked for one more quarter twice? Has the sponsor moved on? Any two of those
and I'd lean hard towards stopping.

My likely answer here isn't binary: shut two cities, keep the one where the
density works as a narrow probe with a single question to answer in a
quarter, and stop everything else.

And then stop well. Decide once. Harvest the routing work and the operations
data. Switch off what we shipped in the closed cities properly rather than
leaving a half-working feature on someone's on-call. Move the people within
two weeks. And thank the team publicly, with a written account of what we
learned - because the way an organisation kills its programs decides whether
anybody volunteers for the next risky one." """,
        """STRONG sounds like: the "would we start it today" reframe; kill
criteria that were (or should have been) set in advance; sunk cost explicitly
excluded but option value explicitly included; named warning signs; a
non-binary option; and a concrete plan to stop well.

WEAK sounds like: "I'd look at the business case and talk to the
stakeholders." Or the opposite failure - "yes, kill it, it's behind" -
treating lateness as the same thing as low value.

THE DETAIL THAT IMPRESSES: "the success metric has been quietly redefined" as
a warning sign. It shows you have watched programs survive by moving their
own goalposts.""",
        ["The team believes in it passionately. Does that change your view?",
         "The CEO sponsored it. How do you raise it?",
         "How do you set kill criteria without making teams risk-averse?",
         "Tell me about a program you stopped. What did it cost you?",
         "What does harvesting look like in practice?"],
        """* Letting sunk cost argue - "we're nearly there".
* Confusing late with worthless. A late program can still be the best use of
  the remaining money.
* Ignoring option value, which is what makes genuine bets worth continuing.
* Killing slowly - cutting the team by half and letting it limp.
* Leaving shipped pieces running with no owner.
* Punishing the team, which guarantees the next one hides its problems.""",
        ["portfolio", "decision-making", "sunk-cost", "program"],
        difficulty="Medium",
        frequency="Common - usually asked directly or as a probe on a "
                  "portfolio or budget case.",
        prep_minutes=35,
    ))

    out.append(E(
        "program",
        "Run the company's annual planning / OKR cycle across 40 teams.",
        "Whether you can design a planning SYSTEM - calendar, inputs, "
        "decision points - that produces real commitments rather than a "
        "spreadsheet nobody reads after February. At this level they want to "
        "hear that capacity and dependencies are resolved AT planning time, "
        "and that you know exactly what makes OKRs theatre.",
        """THE STRUCTURE - a ten-week calendar with a decision at each step

T-10 WEEKS: STRATEGY AND COMPANY BETS (top-down)
  Leadership sets three to five company objectives, each with two to four
  measurable key results. Fewer is the point - if everything is a company
  objective, nothing is.

T-8: THE CAPACITY ENVELOPE
  Each org gets its real capacity: headcount (including realistic hiring
  ramps and 60-90 day notice periods), minus keep-the-lights-on (commonly
  30-40%), on-call, sale-event preparation, and onboarding. Teams plan to
  70-80% of what remains.

T-6: BOTTOM-UP DRAFTS
  Teams draft their OKRs and roadmap against the envelope. Every team OKR
  ladders to a company KR or is explicitly labelled "run the business". No
  orphans.

T-4: THE DEPENDENCY MARKETPLACE
  Every cross-team ask is registered. A dependency is only real when the
  GIVING team has accepted it and put capacity against it. Unaccepted
  dependencies are escalated now, in planning - not discovered in month
  three.

T-2: RECONCILIATION
  Leadership resolves the conflicts: over-subscribed platform teams,
  unfunded dependencies, two orgs chasing the same KR. The output includes a
  published NOT-doing list.

T-0: COMMIT AND PUBLISH
  One page per org, visible to everyone.

WHAT MAKES OKRs THEATRE - say these out loud
  * Key results that are activities ("launch X") rather than outcomes.
  * 100% attainment every quarter - the targets are sandbagged.
  * Fifteen OKRs per team.
  * Nobody looks at them between planning cycles.
  * Tied directly to compensation, which guarantees sandbagging.

KEEPING IT ALIVE MID-CYCLE
  * Weekly confidence score (0-10) on each company KR, updated by its owner.
  * A monthly 30-minute company KR review that makes decisions.
  * A quarterly re-plan window - the only time scope formally moves.""",
        """A WORKED ANSWER

"I'd run it as a ten-week calendar where every step ends in a decision, not
a document.

It starts top-down. Leadership commits to three to five company objectives,
each with a few measurable key results. My job there is mostly to say no -
if we leave planning with twelve company priorities, we've planned nothing.

Then capacity, before anybody writes a roadmap. Each org gets an honest
envelope: real headcount with realistic hiring - a req opened in March in
India with a 90-day notice period is somebody productive in August - minus
keep-the-lights-on, which is usually 30 to 40 percent, minus sale-event prep
and on-call. Teams plan to about 75 percent of what's left. Skipping this
step is why most annual plans are fiction by April.

Teams then draft bottom-up, and every team OKR must ladder to a company KR or
be explicitly labelled run-the-business. That labelling is healthy - it
stops teams dressing up maintenance as strategy.

The step I'd care most about is the dependency marketplace, about four weeks
out. Every cross-team ask gets registered, and a dependency only counts when
the team being asked has accepted it and resourced it. With forty teams
there are always two or three platform teams that are wildly
over-subscribed, and this is where we find out - in planning, while
trade-offs are still cheap, rather than in month three when someone's launch
is blocked. Anything unaccepted goes to leadership to resolve before we
commit.

And the plan publishes with a not-doing list, because that's the part that
actually prevents re-litigation.

On OKR theatre, the signs are very consistent: key results that are really
activities, every team hitting a hundred percent, and nobody looking at them
between January and December. So I'd keep a light mid-cycle rhythm - a
weekly zero-to-ten confidence score on each company KR, a monthly thirty
minute review that changes something, and one formal quarterly re-plan
window. And I would keep OKR attainment out of individual compensation,
because the day you link them, every target gets sandbagged." """,
        """STRONG sounds like: a calendar with decisions at each step; capacity
before roadmap with KTLO subtracted; laddering with an explicit
"run the business" label; dependencies accepted by the giving team at
planning time; a not-doing list; and specific signs of OKR theatre with the
mechanism that prevents each.

WEAK sounds like: "I'd send out templates, collect OKRs from every team, and
roll them up." Collection is not planning - nothing in that answer forces a
trade-off.

THE DETAIL THAT IMPRESSES: "a dependency only counts when the giving team
has accepted and resourced it." It moves the most common mid-year failure
into the planning window, where it is cheap.""",
        ["Two orgs both claim the same key result. How do you resolve it?",
         "A platform team has requests for 3x its capacity. What happens?",
         "How do you handle a big strategic change in month four?",
         "How do you stop teams sandbagging their targets?",
         "Should OKRs be linked to performance reviews?",
         "How much of this would you do differently for 400 engineers versus "
         "4,000?"],
        """* Collecting and rolling up instead of forcing trade-offs.
* Planning against full headcount with no KTLO, on-call or hiring ramp.
* Dependencies listed but never accepted by the team that has to do the work.
* Too many company objectives.
* No mid-cycle rhythm, so the plan dies in February.
* Linking OKR attainment to compensation and then wondering why every target
  is 100% achieved.""",
        ["planning", "okrs", "capacity", "dependencies", "program"],
        difficulty="Medium",
        frequency="Very likely for a Head-of-TPM or VP TPM role, where the "
                  "planning cycle is usually owned by the function.",
        prep_minutes=40,
    ))

    out.append(E(
        "program",
        "Run a program to ship an AI/LLM-powered feature to production.",
        "Whether you know how AI programs differ from deterministic ones: "
        "requirements are fuzzy, quality is statistical, cost scales per "
        "call, and failure can be embarrassing as well as wrong. The panel "
        "wants to hear that an evaluation set is the definition of done, that "
        "risky actions stay outside the model, and that rollout is staged by "
        "risk rather than by percentage alone.",
        """THE STRUCTURE

1. MAKE THE EVALUATION SET THE SPEC (weeks 1-3)
   Before choosing a model, build 500-1,000 labelled REAL examples,
   stratified by intent, language (including mixed-language input such as
   Hinglish), and known edge cases. Write a rubric - correct, grounded in our
   data, safe, helpful - and agree target thresholds with product. "Done"
   means "passes the eval at these thresholds", not "the demo looked good".

2. OFFLINE EVALS AS A REGRESSION GATE
   Every prompt, model or retrieval change runs against the eval set in CI.
   If you use an LLM as the judge, calibrate it against human labels first
   (aim for 85%+ agreement) and re-check it monthly.

3. KEEP RISKY ACTIONS OUT OF THE MODEL
   The model reads and drafts; deterministic services act. Refunds,
   cancellations and address changes go through existing APIs with existing
   policy limits. Ground answers in tool calls to real order data. Add PII
   handling, prompt-injection tests, a red-team set, and a clean hand-off to
   a human.

4. COST AND LATENCY ARE REQUIREMENTS
   Cost per RESOLVED conversation, compared with the human cost it replaces,
   at sale-event volume, not average volume. A p95 latency budget. Route easy
   intents to a smaller model, cache what repeats, cap tokens.

5. HUMAN IN THE LOOP, THEN LESS OF IT
   Shadow mode (the model drafts, nobody sees it), then agent-assist (agents
   see and edit drafts - their edit rate is a free quality signal), then
   autonomous for low-risk intents only. Sample 2-5% of autonomous
   conversations for weekly human review.

6. STAGED ONLINE ROLLOUT WITH GUARDRAIL METRICS
   1% -> 5% -> 25% by intent. Success: resolution without escalation, CSAT.
   Guardrails: re-contact within 72 hours, complaint rate, cost per
   conversation. A kill switch that routes everything back to humans in
   seconds.

7. OPERATE IT LIKE A PRODUCT
   Pin model versions, monitor drift, add every production failure to the
   eval set, and plan for the vendor changing the model under you.

8. PROGRAM SHAPE
   You cannot Gantt-chart quality. Time-box exploration, then run two-week
   iterations whose goal is an eval score, and report progress as the
   score trend.""",
        """A WORKED ANSWER - an assistant for order and return questions in
customer support chat

"The first thing I'd change about how we usually run programs is the
definition of done. For an LLM feature, done is an evaluation set, so weeks
one to three are building it: about a thousand real support conversations,
stratified by intent and by language - we'd get a lot of Hinglish - and
labelled against a rubric of correct, grounded, safe and helpful. Product and
I agree the thresholds before anyone picks a model. Otherwise we end up
shipping whatever the best demo looked like.

That eval set becomes a regression gate. Every prompt or model change runs
against it automatically, and if we use a model as the judge, I want it
calibrated against human labels first.

Second, I'd keep anything risky out of the model entirely. The model reads
order data through tools and drafts replies; the actual refund or
cancellation goes through the same deterministic APIs and policy limits a
human agent uses. That single design choice removes most of the scary
failure modes, and it is far easier to get past legal and finance.

Third, cost is a requirement, not an afterthought. I'd track cost per
resolved conversation against the human cost it replaces, and model it at
sale-event volume, because a feature that's cheap on an average Tuesday can
be shockingly expensive at ten times the load. Easy intents like 'where is my
order' go to a smaller model.

Rollout is staged by risk. Shadow mode first. Then agent-assist, where human
agents see the draft - and their edit rate is the best free quality signal
you'll ever get. Then autonomous, starting with low-risk intents at one
percent. Success is resolution without escalation; the guardrail I'd watch
hardest is re-contact within 72 hours, because a confident wrong answer looks
like a resolution until the customer comes back angry. There's a kill switch
to send everything back to humans in seconds.

And I'd report progress as the eval score trend, not as percent complete." """,
        """STRONG sounds like: the eval set built first and treated as the spec;
LLM-judge calibration; actions kept in deterministic services; cost per
resolved conversation at peak volume; the shadow -> assist -> autonomous
ladder; re-contact as the guardrail; and progress reported as an eval trend.

WEAK sounds like: "I'd pick a model, build a prototype, get feedback from
users and iterate." That is a hackathon, not a production program, and it
has no definition of done.

THE DETAIL THAT IMPRESSES: agent edit rate as a free quality signal during
agent-assist. It shows you have thought about how to get labelled data out of
the rollout itself.""",
        ["The eval score plateaus at 82% and the target is 90%. What do you "
         "do?",
         "Legal is nervous about hallucinated refund promises. How do you "
         "address it?",
         "The model vendor ships a new version that changes behaviour. What "
         "happens?",
         "How do you estimate the cost at sale-event volume?",
         "How would you decide this feature should NOT use an LLM?",
         "How do you staff a program like this?"],
        """* No evaluation set, so "done" is whatever the last demo looked like.
* Letting the model take actions directly.
* Measuring cost per call instead of cost per resolved outcome, and at
  average volume instead of peak.
* Rolling out by traffic percentage across all intents at once instead of by
  risk.
* Using an uncalibrated LLM judge and trusting its scores.
* Treating launch as the end - drift and vendor model changes make this a
  feature you operate, not one you ship.""",
        ["ai", "llm", "evaluation", "rollout", "program"],
        difficulty="Hard",
        frequency="Very likely in current loops - most companies are asking "
                  "how you would ship AI safely.",
        prep_minutes=45,
    ))

    out.append(E(
        "program",
        "A critical third-party vendor will miss its date and you depend on it.",
        "Whether you can manage a dependency you do not control: getting to "
        "ground truth inside another company, using contractual and "
        "relationship levers without burning them, running a real plan B "
        "with a trigger date, and changing how you contract so it does not "
        "happen again.",
        """THE STRUCTURE

1. GET GROUND TRUTH INSIDE THE VENDOR
   The account manager's date is a sales artefact. Ask for a working session
   with their engineering lead, and ask to SEE the build - a demo in their
   staging environment is worth ten status calls. Establish how late, why,
   and how confident they are.

2. QUANTIFY THE IMPACT ON YOU
   What exactly depends on it, what is the cost per week of delay, and is
   your date hard (the sale event, a regulatory deadline) or soft?

3. LAY OUT THE OPTIONS
   (a) Descope: the minimum you need from them by the date.
   (b) Interim workaround: a manual operations process, the previous version,
       or a thin shim you build yourselves.
   (c) Parallel path: a second vendor or an in-house build, started now.
   (d) Move your own date.

4. PULL THE LEVERS - IN THE RIGHT ORDER
   * Help first: put two of your engineers in their war room; unblock their
     access to your sandbox; answer their questions same day.
   * Relationship: executive-to-executive escalation with a SPECIFIC ask
     ("your best two integration engineers on this until 15 September"),
     not a complaint. Your reference value matters to them.
   * Contract: milestone payments, SLAs, service credits and penalties.
     Mention them once, calmly; contracts are a floor, not a strategy.

5. SET A TRIGGER DATE FOR PLAN B - AND START THE NO-REGRET WORK NOW
   "If the vendor has not delivered X working in staging by date Y, we
   switch." Start whatever plan B needs that is cheap and useful either way
   - test accounts, a second integration's design - today.

6. COMMUNICATE INTERNALLY WITH THE SAME HONESTY
   Your stakeholders hear the vendor risk, the trigger date and the plan B
   from you, before it becomes a surprise.

7. FIX IT FOR NEXT TIME
   Milestone-based contracts with demonstrable intermediate deliverables;
   integration against their sandbox in week two, not week ten; the vendor's
   engineering lead in your weekly risk review; exit clauses; and no single
   vendor on the critical path of a hard date without a fallback.""",
        """A WORKED ANSWER - a payment partner's new instalment product,
promised for the sale event

"I'd start by getting past the account manager. Their date is a sales
commitment; I want a session with their engineering lead and a demo of what
actually works in their staging environment today. That tells me in an hour
whether we're two weeks late or two months late.

Then I'd size it from our side. Say marketing has already announced
no-cost instalments for the sale, and it's worth a meaningful share of
electronics revenue. The date is hard; the scope may not be.

So the options. Descope - do we need every bank and tenure on day one, or
would the top three issuing banks cover most of the volume? A workaround -
could we offer the instalment option through an existing partner on worse
terms for the sale period? A parallel path - is there a second provider we
could integrate in eight weeks? Or move our date, which here really means
changing the marketing promise.

On levers, I'd go in order. First, help: I'd offer to put two of our
engineers into their team, because vendors are often late for reasons we can
fix, like slow access to our sandbox or unanswered questions. Second, an
exec-to-exec call with a specific ask - their two best integration engineers
on this until the event. Being a large reference customer during the biggest
sale of the year matters to them. The contract - milestone payments,
penalties - I'd mention once and calmly. Penalties don't ship features.

The most important thing is a trigger date. 'If the end-to-end flow isn't
working in their staging by the 1st, we switch to the fallback partner.' And
we start the fallback's cheap groundwork today, so the trigger is real rather
than theoretical.

Internally, marketing and the business head hear about the risk and the
trigger date this week, not in the final fortnight.

Then I'd fix the contracting model: milestones tied to demonstrable builds,
integration against their sandbox in week two, their engineering lead in our
weekly risk review, and never a single vendor on the critical path of the
sale event without a fallback." """,
        """STRONG sounds like: ground truth from the vendor's engineers and a
demo; impact quantified; four distinct options; levers in order - help,
relationship, contract; a trigger date with no-regret work started now; and
contracting changes for next time.

WEAK sounds like: "I'd escalate and invoke the penalty clause." Penalties
compensate you after the fact; they do not get the feature built, and they
make the vendor's best people less willing to help.

THE DETAIL THAT IMPRESSES: offering your own engineers to the vendor before
escalating. It reframes the vendor's problem as a shared one, and it is very
often the fastest fix.""",
        ["The vendor's engineering lead tells you privately the date is "
         "impossible. What do you do with that?",
         "There is no alternative vendor. Now what?",
         "Procurement says the contract has no penalties. Does it matter?",
         "How do you decide the trigger date?",
         "Marketing refuses to change the public promise. How do you handle "
         "it?"],
        """* Trusting the account manager's date.
* Leading with the contract. It hardens positions and rarely accelerates
  anything.
* A plan B with no trigger date, which means it is never triggered.
* Not starting plan B's cheap groundwork, so switching takes too long.
* Telling internal stakeholders late.
* Treating it as bad luck rather than fixing how you contract and integrate.""",
        ["vendor-management", "dependencies", "risk", "escalation", "program"],
        difficulty="Medium",
        frequency="Common - a standard dependency-management variant, "
                  "especially where partners sit on the critical path.",
        prep_minutes=35,
    ))

    # ======================================================================
    #  ENGINEERING LEADERSHIP ROUND (Director of Engineering loop)
    # ======================================================================

    out.append(E(
        "engineering",
        "How do you balance technical debt against feature delivery?",
        "Whether you can turn technical debt from an engineering complaint "
        "into a business decision. They are testing whether you can measure "
        "it, classify it, fund it through a mechanism that survives deadline "
        "pressure, and get product to co-own the trade-off rather than "
        "treating debt as engineering's private hobby.",
        """THE STRUCTURE

1. REJECT THE FRAMING
   Debt is not the opposite of delivery; it is a tax ON delivery. The goal
   is to fund it in the same currency as features - time to market, risk,
   cost - so it competes on equal terms.

2. CLASSIFY BEFORE YOU FUND
   * Debt that SLOWS us: every change in this area takes three times as long.
   * Debt that RISKS us: reliability, security, scaling ceilings, an
     end-of-life dependency.
   * Debt that is merely UGLY: old patterns, inconsistent style. Leave it.
   Only the first two get funded. Saying the third out loud earns trust with
   product.

3. MEASURE THE INTEREST RATE
   Lead time for changes per module, change failure rate, incidents
   attributed to an area, on-call pages, onboarding time. "Every checkout
   feature takes 3 sprints instead of 1 because of the pricing module" is a
   sentence a business leader can act on.

4. A FUNDING MODEL THAT SURVIVES A DEADLINE
   * A standing 15-20% allocation per team for small debt, owned by the tech
     lead.
   * Large debt as named roadmap items with a business case, competing in
     planning on the same terms as features.
   * Risk debt ranked by severity and fixed on a timeline set by severity -
     not negotiated.
   * NOT a "tech-debt sprint", which signals that debt is optional and
     periodic.

5. MAKE PRODUCT A CO-OWNER
   The PM signs off on the allocation and sees the metrics. Debt is presented
   as a business case, never as "engineers want to refactor".

6. STOP CREATING IT CARELESSLY
   Deliberate shortcuts are fine - and are recorded at the time with an
   owner and a payback date. Architecture review for significant new
   systems.

7. HOLD THE LINE
   Track the allocation actually spent each quarter. The first time it is
   raided for a deadline without a recorded decision, it is gone for good.""",
        """A WORKED ANSWER

"I don't think of it as a balance between two opposites. Debt is a tax on
delivery, so my job is to price it in the same currency as features and let
it compete fairly.

The first step is classifying, because not all debt is worth paying. Some
debt slows us down - every change in an area takes three times longer than
it should. Some debt puts us at risk - a database at its scaling ceiling, a
library going end of life, a service that pages on-call every week. And some
is just ugly code that works. I'd fund the first two and openly leave the
third alone; product leaders relax noticeably when an engineering leader
says 'we're not going to rewrite things because they offend us'.

Then I'd measure it. Lead time per module, change failure rate, incidents
and pages by area. At my scale that typically produces a sentence like
'every pricing change takes three sprints instead of one, and pricing caused
four of last quarter's incidents'. That's a business case, not a complaint.

For funding I use two channels. Every team holds a standing allocation -
about fifteen to twenty percent - for small debt, controlled by the tech lead.
Big debt goes on the roadmap as a named item with a business case and
competes in planning alongside features. Risk debt is different: it's ranked
by severity and fixed on a timeline that isn't up for negotiation, the same
way a security finding is. What I don't do is tech-debt sprints; they tell
everyone debt is a holiday activity.

The PM co-signs the allocation and sees the same metrics, so the trade-off
is shared rather than argued.

To stop generating it carelessly, deliberate shortcuts are allowed, but they
are recorded at the time with an owner and a payback date - we know what we
borrowed and when it's due.

And I hold the line. I track the allocation actually spent every quarter,
because the first time it gets quietly raided for a deadline, it's gone.
If we need to borrow it, that's fine - but it's a recorded decision with a
date to pay it back, made by me and the product lead together." """,
        """STRONG sounds like: debt as a tax priced in business terms; a
three-way classification including debt you choose NOT to pay; specific
measures; a two-channel funding model plus non-negotiable risk debt; the PM
as co-owner; and tracking that the allocation is actually spent.

WEAK sounds like: "We allocate 20% to tech debt." A number with no
classification, measurement or protection is a hope, and every panel knows
that 20% is the first thing raided in a crunch.

THE DETAIL THAT IMPRESSES: explicitly choosing to leave "ugly but harmless"
debt alone. It shows judgement and earns product trust in one sentence.""",
        ["Product says this quarter is too important to spend 20% on debt. "
         "What do you say?",
         "How do you know your debt investment is actually paying off?",
         "An engineer wants a full rewrite. How do you evaluate it?",
         "How do you handle debt in a system no team owns?",
         "Give me an example where you chose NOT to pay down debt."],
        """* Treating all debt as equal and worth fixing.
* Talking about debt in engineering language to a business audience.
* A percentage allocation with nothing that protects it under pressure.
* Tech-debt sprints, which make debt periodic and optional.
* Proposing rewrites where incremental replacement would do.
* No measurement, so the investment cannot be defended next year.""",
        ["tech-debt", "prioritization", "product-partnership", "engineering"],
        difficulty="Medium",
        frequency="Very common - almost guaranteed in a Director of "
                  "Engineering loop.",
        prep_minutes=35,
    ))

    out.append(E(
        "engineering",
        "Reliability is getting worse - incidents are up quarter on quarter. "
        "What do you do as the engineering leader?",
        "Whether you can run reliability as a system with policy, ownership "
        "and investment - not as heroics and a new dashboard. The panel is "
        "listening for diagnosis before prescription, SLOs on user journeys, "
        "an error-budget policy with real consequences, and an incident "
        "review process that actually prevents repeats.",
        """THE STRUCTURE

1. DIAGNOSE BEFORE YOU PRESCRIBE
   * Is reliability worse, or is detection better? Normalise incident counts
     by traffic and deploy volume.
   * Count customer-impact MINUTES, not incidents.
   * Segment: by service, by owning team, by cause. In most organisations
     60-70% of incidents are change-induced - deploys and config.
   * Repeat rate: what share are the same failure again?

2. SLOs ON CRITICAL USER JOURNEYS
   Five to eight journeys (search, product page, cart, checkout, payment,
   order tracking) with availability and latency SLOs measured from the
   user's side, not the server's.

3. AN ERROR-BUDGET POLICY WITH TEETH - SIGNED IN ADVANCE
   Agreed by engineering AND product leadership before it is needed: when a
   service exhausts its budget, feature launches for that service stop and
   the team works on reliability until it is back inside budget. A policy
   nobody would enforce is worse than none.

4. INCIDENT REVIEWS THAT CHANGE THINGS
   Blameless but not toothless. Every action item has an owner and a date,
   and the closure rate is tracked. A weekly 30-minute reliability review,
   chaired by you, on the top incidents and overdue actions. Repeat-incident
   rate is the measure of whether reviews work.

5. CHANGE SAFETY - BECAUSE MOST INCIDENTS ARE CHANGES
   Canary deploys, automated rollback on SLO burn, progressive delivery,
   and config changes through the same pipeline as code.

6. OWNERSHIP
   Every service has an owning team and an on-call rotation. Find the
   orphans. Page only on user-facing symptoms; alert fatigue is a
   reliability bug.

7. FUND IT EXPLICITLY
   A named reliability roadmap for the worst two or three services, possibly
   a time-boxed reliability quarter for them. Do not hand ownership to a
   central SRE team - that removes the incentive from the people who change
   the code.

8. THE NUMBERS YOU REVIEW
   Customer-impact minutes, time to detect, time to mitigate, repeat rate,
   action closure rate, percent of deploys going through canary.""",
        """A WORKED ANSWER

"Before doing anything, I'd check the trend is real. If we launched better
alerting last quarter, incident counts go up while reliability gets better.
So I'd normalise by traffic and deploy volume, and I'd switch the headline
metric from incident count to customer-impact minutes - one forty-minute
checkout outage matters more than ten blips on an internal tool.

Then I'd segment. Which services, which teams, which causes? I'd expect,
like most organisations, that the majority are change-induced - deploys and
config pushes - and that two or three services account for half the impact.
I'd also look at the repeat rate. If a third of incidents are the same
failure happening again, our reviews aren't working, and that's a different
fix from the one for new failures.

Then the system. I'd define SLOs on the critical user journeys - search,
product page, cart, checkout, payment - measured from the user's side. And I'd
get an error-budget policy signed by me and my product counterpart before
we need it: if checkout burns its budget, feature launches on checkout stop
and that team works on reliability until it recovers. It has to be signed in
advance, because negotiated in the moment it never holds.

Incident reviews stay blameless, but every action has an owner and a date,
and I chair a thirty-minute weekly reliability review that looks at the top
incidents and the overdue actions. The overdue list is where the truth is.

Because most incidents come from change, I'd invest in change safety: canary
releases with automatic rollback on SLO burn, and config going through the
same pipeline as code - a lot of outages at our scale are a config push that
bypassed every check.

On ownership, I'd find services with no clear owner or no real on-call, and
fix that first. And I'd fund it openly - a named reliability roadmap for the
worst two or three services, sometimes a full quarter for one team. What I
would not do is create a central SRE team to own it, because then the people
writing the code stop feeling the pages.

I'd review impact minutes, time to detect, time to mitigate, and repeat rate
monthly with my leadership team." """,
        """STRONG sounds like: checking the trend is real; customer-impact
minutes; segmentation that finds the change-induced majority; SLOs on
journeys; an error-budget policy signed in advance by product; tracked
action closure; change safety; ownership; and refusing to centralise it
away.

WEAK sounds like: "I'd hold a reliability stand-down, set up a war room and
ask teams to be more careful." That is a campaign, and campaigns decay
within a quarter.

THE DETAIL THAT IMPRESSES: "the overdue action list is where the truth is."
Most reliability programs fail not in the review but in the follow-through,
and saying so shows you have watched it happen.""",
        ["Product refuses to freeze features when the budget is exhausted. "
         "What happens?",
         "How do you pick the right SLO target - 99.9 or 99.95?",
         "What does a good incident review look like, and a bad one?",
         "Should you have a central SRE team?",
         "How do you handle a team whose on-call is burning people out?",
         "What would you report to the CTO each month?"],
        """* Prescribing before diagnosing - and missing that detection, not
  reliability, changed.
* Counting incidents rather than customer impact.
* An error budget with no consequence, or one negotiated in the moment.
* Blameless reviews with no tracked actions - therapy, not engineering.
* Ignoring that most incidents are change-induced.
* Moving ownership to a central team, which removes the incentive from the
  people changing the code.""",
        ["reliability", "slos", "incidents", "operations", "engineering"],
        difficulty="Hard",
        frequency="Very likely for a Director of Engineering at consumer "
                  "scale - reliability is usually the core operational probe.",
        prep_minutes=45,
    ))

    out.append(E(
        "engineering",
        "One of your engineering managers is underperforming. Walk me through "
        "how you handle it.",
        "Whether you manage managers with evidence, directness and speed - "
        "and with fairness. They are testing whether you check your own part "
        "first, whether you diagnose before acting, whether you give a clear "
        "and time-bound path, whether you protect the team meanwhile, and "
        "whether you will actually make the call at the end.",
        """THE STRUCTURE

1. DEFINE THE GAP PRECISELY
   Delivery, people (attrition, engagement, hiring), quality, judgement, or
   cross-team behaviour? Gather evidence, not impressions: skip-levels,
   peer feedback, delivery and quality data, attrition. Triangulate from at
   least three sources.

2. CHECK YOURSELF FIRST
   Were expectations explicit? Is the team understaffed, inheriting a
   failing system, or carrying an impossible scope? Did you promote them
   without support? Is something going on in their life? A good share of
   "underperforming managers" are set up to fail.

3. DIAGNOSE: SKILL, WILL, FIT OR CONTEXT
   The most common pattern is a strong engineer, recently promoted, still
   DOING instead of leading - fixing the code and making the decisions
   themselves. That is a skill gap with a known fix.

4. HAVE THE DIRECT CONVERSATION EARLY
   Specific, not soft: "There are three things I need to see change: X, Y and
   Z. Here is what good looks like for each. I want to help you get there,
   and we will review it together every two weeks." Situation, behaviour,
   impact - and ask for their view before concluding.

5. A WRITTEN, TIME-BOUND PLAN (60-90 days)
   Measurable outcomes, coaching, a peer mentor among your stronger
   managers, and more of YOUR time - weekly one-to-ones instead of
   fortnightly. Bring HR in early so the process is fair and documented.

6. PROTECT THE TEAM MEANWHILE
   Monthly skip-levels, watch retention risk, make sure good engineers are
   not paying for the gap.

7. DECIDE ON THE DATE
   Three honest outcomes: they improve; they move back to a senior IC role
   - often the best result, and offered as a respected path, not a
   demotion; or they leave with dignity. Do not let it drift. The team
   noticed months before you acted.""",
        """A WORKED ANSWER

"I'd start by being precise about what underperforming means, because
'not great' isn't actionable. Is it delivery, is it the team - attrition,
engagement - is it quality, or is it how they work with other teams? I'd
look for evidence from at least three places: skip-level conversations, peer
managers, and the data - delivery against commitments, incidents, regretted
attrition.

Then I'd look at myself. Did I make the expectations explicit? Did I give
them a team that was already failing, or a scope that two managers couldn't
carry? A real share of the struggling managers I've seen were set up badly,
and it's only fair to rule that out first.

Then diagnosis. The pattern I see most is a very strong engineer promoted
into management who is still the best engineer on the team - reviewing every
pull request, making every design call, firefighting at night - and the
team can't grow around them. That's a skill gap, and it's coachable.

The conversation happens early and it's direct. Something like: 'I want to
talk about three things I need to see change - how decisions get made on
your team, how you're developing your seniors, and the delivery
predictability. Here's what good looks like for each. I want you to succeed
here, and I'll put real time into it.' Then I ask for their view, because
sometimes they tell me something that changes the picture.

Then a written plan, sixty to ninety days, with outcomes we can both
observe. I move our one-to-ones to weekly, pair them with one of my
strongest managers as a mentor, and bring HR in early so it's fair and
documented. Meanwhile I do monthly skip-levels with their team, because the
engineers shouldn't pay for this.

At the end there are three honest outcomes. They improve, which happens more
often than people expect when the feedback is clear. They move back to a
senior engineer role - which I'd offer genuinely as a respected path, and
which is often the happiest result. Or they leave, with dignity and support.
What I won't do is let it drift past the date. The team usually knows months
before the manager's manager acts." """,
        """STRONG sounds like: precise definition with triangulated evidence;
checking your own contribution first; a named diagnosis; the exact opening
sentence of the conversation; a time-bound written plan with more of your
time; team protection; and three real outcomes including a respected route
back to IC.

WEAK sounds like: "I'd put them on a PIP." That skips diagnosis, skips your
own part, and announces that the outcome has already been decided.

ALSO WEAK: endless coaching with no date. Kindness to one manager at the
expense of eight engineers is not kindness.

THE DETAIL THAT IMPRESSES: "the team usually knows months before the
manager's manager acts." It shows you understand the cost of delay falls on
the team, not on you.""",
        ["The manager is very popular with their team. Does that change "
         "anything?",
         "What if the problem is that they are too soft on their own low "
         "performers?",
         "How do you handle the conversation if they disagree with your "
         "assessment?",
         "Tell me about a time you moved a manager back to IC. How did it go?",
         "How quickly is too quickly?",
         "How would you prevent this next time you promote a manager?"],
        """* Acting on impressions rather than triangulated evidence.
* Skipping your own role in the problem.
* Vague feedback that the manager cannot act on.
* Going straight to a formal process without a real chance to improve.
* Letting it drift for a year while the team absorbs the cost.
* Treating a move back to IC as a failure rather than a legitimate outcome.""",
        ["people-management", "performance", "coaching", "engineering"],
        difficulty="Medium",
        frequency="Very common - the standard people-leadership case in a "
                  "Director of Engineering loop.",
        prep_minutes=35,
    ))

    out.append(E(
        "engineering",
        "How do you set and hold the hiring bar while growing the org fast?",
        "Whether you can scale hiring without diluting quality - and whether "
        "you see the bar as a system (definition, trained interviewers, "
        "structured loops, independent decision, feedback from outcomes) "
        "rather than as your personal judgement in every debrief. Under "
        "growth pressure, the bar fails quietly, and they want to know how "
        "you would notice.",
        """THE STRUCTURE

1. DEFINE THE BAR IN WRITING
   Per level: the competencies and the OBSERVABLE signals for each - not
   "strong problem solver" but "breaks an ambiguous problem into testable
   parts without prompting". Rubrics and question banks follow from this.

2. TRAIN AND MEASURE INTERVIEWERS
   Shadow two loops, reverse-shadow two, then calibrate. Track each
   interviewer's score distribution and how well their scores predict later
   performance. Remove interviewers who are consistently off.

3. STRUCTURED LOOPS
   Each interview owns one competency. Written feedback submitted
   independently BEFORE the debrief, so the loudest voice does not anchor
   the room.

4. AN INDEPENDENT DECISION
   A bar-raiser from outside the hiring team with a veto, or a hiring
   committee for senior roles. The hiring manager is the person under most
   pressure to lower the bar and should not be the only decider.

5. SEPARATE URGENCY FROM THE BAR
   When hiring is behind plan, increase pipeline - sourcing, referrals,
   campus, recruiter capacity - not acceptance. Say the cost: a wrong hire
   costs 12-18 months of team time to recognise and resolve.

6. PLAN FOR THE MARKET YOU ARE IN
   With 60-90 day notice periods and high offer-decline rates (often a
   quarter to a third of accepted offers do not join), pipeline targets must
   assume the drop-off. Keep a warm bench and stay in touch through the
   notice period.

7. CLOSE THE LOOP ON OUTCOMES
   Six-month performance of new hires against their interview scores,
   regretted early attrition, down-levelling rate, pass-through rate by
   stage. This is the only way to know whether the bar is holding.

8. SHAPE THE ORG WHILE YOU GROW IT
   Hire leaders and seniors first; a 60-person org that doubles with only
   juniors drowns its seniors in review and mentoring. Onboarding is part
   of the bar - a 30/60/90 plan for every hire.""",
        """A WORKED ANSWER - doubling an org from about 80 to 160 engineers in
a year

"The first thing I'd do is get the bar out of people's heads and onto paper.
For each level, the competencies and what they look like in an interview -
observable things like 'breaks an ambiguous problem into testable parts
without being prompted', not adjectives like 'smart'. Then everything else -
rubrics, question banks, training - hangs off that.

Second, interviewers are a trained role, not a favour. Shadow two loops,
reverse-shadow two, then calibrate. And I track each interviewer's score
distribution. When you double in a year, you double your interviewer pool,
and that's exactly where the bar drifts - a new interviewer who passes
everyone, or one who fails everyone.

Third, structure. Each interview owns one competency, and feedback is
written and submitted before the debrief, so nobody anchors on the most
senior voice in the room. And the final decision isn't the hiring manager's
alone - a bar-raiser from another team has a veto. The hiring manager is the
person with the most pressure to lower the bar, through no fault of their
own.

Fourth, I keep urgency and the bar separate. When we're behind plan, I add
pipeline - more recruiter capacity, referrals, campus - not acceptance. I'd
say to my managers plainly: a wrong hire costs us a year of a team's
attention, and an empty seat costs us a few weeks.

Our market adds its own twist. With ninety-day notice periods and a quarter
or more of accepted offers not joining, pipeline targets have to assume that
drop, and we keep in touch with candidates through their notice period.

Then I close the loop. Six months in, I compare new hires' performance with
their interview scores, look at early regretted attrition and down-levelling.
If the people we hired with marginal scores are struggling, the bar is
slipping, and I'll see it in data rather than in a feeling.

And I'd shape the growth: leaders and senior engineers first. If I double
with mostly juniors, my seniors spend their whole year reviewing code and
the org gets slower as it gets bigger." """,
        """STRONG sounds like: a written bar with observable signals; trained
and measured interviewers; independent written feedback before the debrief;
a bar-raiser with a veto; urgency met with pipeline rather than acceptance;
market-aware pipeline maths; and a loop that checks hires against their
interview scores.

WEAK sounds like: "I personally interview every candidate to make sure the
bar is high." It does not scale past a few dozen hires and it makes you the
bottleneck - which is precisely the failure the question is probing for.

THE DETAIL THAT IMPRESSES: comparing six-month performance with interview
scores. Very few leaders actually close that loop, and it is the only proof
that the bar means anything.""",
        ["A hiring manager is behind plan and wants to hire a 'maybe'. What "
         "do you say?",
         "How do you calibrate the bar across five different teams?",
         "How do you know your bar is too high rather than too low?",
         "What do you do about a senior hire who is clearly not working out "
         "after three months?",
         "How do you hire leaders when you are growing this fast?"],
        """* Treating the bar as your personal judgement - it does not scale.
* Untrained interviewers doubling in number with nobody watching their
  scores.
* Group debriefs before independent written feedback, so the room anchors.
* Lowering the bar to hit the hiring plan.
* Ignoring offer-decline and notice-period realities in pipeline planning.
* Growing with mostly juniors and burning out the seniors.
* Never checking whether interview scores predict anything.""",
        ["hiring", "talent", "scaling", "org-design", "engineering"],
        difficulty="Medium",
        frequency="Very common for a Director of Engineering role in a growing "
                  "org.",
        prep_minutes=35,
    ))

    return out

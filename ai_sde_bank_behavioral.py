"""Behavioural pack for the AI SDE bank (Section 6).

The bank already carries a full set of Amazon Leadership Principle prompts with
STAR skeletons. What was missing is the GOOGLE half - Googleyness, general
cognitive ability, collaboration - plus the student-specific questions a
final-year candidate actually gets: group projects, competing deadlines, a
professor you disagreed with, and the two-minute self-introduction that opens
every single loop.

Every entry follows the same shape: what the interviewer is REALLY testing,
how to structure the answer, a worked student-scale example, and the ways
candidates lose the point. Imported by ai_sde_bank.py, which supplies Q(...).
"""


def _c(s):
    return s.strip("\n")


def build(Q):
    entries = []

    entries += [
        Q("behavioral", "What 'Googleyness' actually means, and how to show it",
          "Google does not have Amazon's published list of principles, so candidates guess. The interview rubric has four axes and Googleyness is one of them; the other three are General Cognitive Ability (how you STRUCTURE an unfamiliar problem, which is scored in your coding and design rounds), Role-Related Knowledge, and Leadership - specifically EMERGENT leadership, meaning you step up when your skill is needed and step BACK when someone else's is. Googleyness itself decomposes into things you can actually demonstrate: comfort with ambiguity (you moved forward without complete requirements), bias to action balanced with humility (you tried something, and you changed course when the evidence said to), intellectual curiosity (you dug into WHY, not just what), collaboration (you made other people more effective), and doing the right thing when nobody is checking. HOW TO SHOW IT rather than claim it: in every story, include the moment you did not know something and say what you did about it; name the people you worked with and what THEY contributed; describe a decision you reversed and what changed your mind. THE CONTRAST WITH AMAZON is worth internalising because the same story needs different emphasis. Amazon wants ownership, data and a quantified result, told in the first person singular - 'I saw, I decided, I delivered, here is the number'. Google wants your reasoning process and your effect on the people around you - 'here is how I framed it, here is what I got wrong, here is how the team converged'. Same story, different spotlight. Saying 'we' too much loses points at Amazon; saying only 'I' can read as a poor collaborator at Google.",
          ["googleyness", "google", "behavioral", "star", "culture"],
          difficulty="Easy",
          frequency="Always asked - Googleyness is one of the four scored axes in every Google interview loop.",
          mnemonic="Google scores four things: cognitive ability (how you structure a problem), role knowledge, EMERGENT leadership (step up AND step back), and Googleyness (ambiguity, curiosity, humility, collaboration, doing the right thing). Amazon wants 'I' and a number; Google wants your reasoning and your effect on others.",
          example="Same project, two framings. AMAZON: 'Our model's inference was too slow for the demo, so I profiled it, found the bottleneck was per-request feature computation, added a cache, and cut p95 latency from 900ms to 120ms - which let us demo live.' GOOGLE: 'The obvious fix was a smaller model, but I wanted to know WHERE the time was going before trading accuracy away. Profiling showed it was feature computation, not inference - so caching fixed it without touching the model. I shared the profile with the two teammates who had been optimising the model, and we redirected that work.' Identical facts; the first spotlights ownership and a number, the second spotlights reasoning and the team.",
          examples=[
              r"""1. THE GOAL - what the word actually refers to.

Google does not publish a list of leadership principles the way Amazon does, so
candidates guess at what "Googleyness" means and usually guess wrong - assuming it is
about personality, enthusiasm, or cultural fit in a vague sense.

It is none of those. It is one of FOUR NAMED AXES on the actual hiring rubric, and
knowing all four is the first half of the answer:

    1. GENERAL COGNITIVE ABILITY (GCA)
       How you STRUCTURE an unfamiliar problem. Scored inside your coding and design
       rounds, not in a separate interview. This is why thinking out loud matters more
       than arriving at the answer.

    2. ROLE-RELATED KNOWLEDGE (RRK)
       Can you actually do the job. Data structures, systems, the domain.

    3. LEADERSHIP - and specifically EMERGENT leadership
       Not "did you have a title". Do you step up when your skill is what the situation
       needs, AND step BACK when it is someone else's. The stepping back is scored, and
       candidates almost never demonstrate it.

    4. GOOGLEYNESS
       Which decomposes into things you can actually show, listed in section 3.

Most candidates know about two of these. Knowing there are four, and that leadership
means emergent leadership rather than authority, is already unusual.

The practical goal of this page: turn a vague word into specific behaviours, and then
into specific SENTENCES you can say - because the whole difficulty of Googleyness is
that it must be SHOWN rather than CLAIMED, and most people claim it.""",
              r"""2. THE INTUITION - claiming versus showing.

Every trait on this rubric can be either asserted or evidenced, and the two land
completely differently:

    CLAIMING                          SHOWING
    ----------------------------      ------------------------------------------------
    "I'm a fast learner."             "I didn't know how HNSW indexes worked, so I
                                       spent a weekend reading the paper and built a
                                       toy version before touching our code."

    "I'm very collaborative."         "My teammate had done more graphics work than me,
                                       so I handed him the rendering piece and took the
                                       indexing instead."

    "I'm comfortable with             "The brief didn't say how fresh the results had
     ambiguity."                       to be, so I assumed one hour, wrote that
                                       assumption in the doc, and set a checkpoint to
                                       revisit it."

    "I have good judgement."          "I was wrong about the bottleneck for two days.
                                       What changed my mind was profiling it properly
                                       instead of guessing."

The left column costs three seconds and scores nothing - anyone can say it, so it
carries no information. The right column costs fifteen seconds and is evidence.

Now the second idea, which is what makes this topic genuinely worth studying: THE SAME
STORY SCORES DIFFERENTLY DEPENDING ON WHICH DETAILS YOU INCLUDE.

    the raw events            what you emphasise           what it scores
    ------------------        ------------------------     -------------------------
    you rescoped a            the deadline, the trade,     Amazon: Deliver Results,
    project to hit a          the number, "I decided"      Ownership
    demo date
                              what you got wrong, the      Google: Googleyness,
                              teammate who disagreed,      emergent leadership
                              what changed your mind

Not different stories. Different spotlights on one story. Section 9 does this in full,
and shows what happens when you point the wrong spotlight.""",
              r"""3. EVERY TERM, defined the first time you meet it.

GOOGLEYNESS. One of four scored rubric axes. Decomposes into: comfort with ambiguity,
bias to action balanced with humility, intellectual curiosity, collaboration, and doing
the right thing when nobody is checking.

GENERAL COGNITIVE ABILITY (GCA). How you structure an unfamiliar problem - clarifying,
decomposing, choosing an approach and explaining why. Scored during your technical
rounds from how you THINK, not from whether you finish.

ROLE-RELATED KNOWLEDGE (RRK). Technical competence for the specific role.

EMERGENT LEADERSHIP. Leadership without authority: stepping up when your skill fits the
problem, and stepping back when someone else's does. Both halves are scored. The
stepping-back half is what distinguishes this from ordinary "I led the team" answers.

INTELLECTUAL HUMILITY. Changing your mind when the evidence says to, and being able to
say what you were wrong about. Google treats this as a scored trait, not a soft skill -
which is why "tell me about a time you were wrong" is a real question with a real
rubric, not a trick.

COMFORT WITH AMBIGUITY. Moving forward without complete requirements - by making
assumptions EXPLICIT rather than by guessing silently. A stated assumption is
reversible; a silent one is a landmine.

BIAS TO ACTION. Starting before certainty. Only scores when paired with humility -
acting decisively AND changing course when the evidence turns.

HIRING COMMITTEE. At Google, the people who interviewed you write up feedback, and a
separate committee decides. This matters practically: your interviewer is WRITING
EVIDENCE FOR SOMEONE WHO WAS NOT IN THE ROOM. Vague impressions do not survive that
process; specific quotable moments do. Give them something quotable.

THE CONTRAST WITH AMAZON'S LEADERSHIP PRINCIPLES. Amazon publishes fourteen named
principles and asks explicitly against them. Google does not, and scores the four axes
above. Same stories work for both; the weighting differs.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - the fundamental one: CLAIMING TRAITS INSTEAD OF EVIDENCING THEM. "I'm
collaborative, I'm curious, I love learning new things." Every candidate says this, so
it distinguishes nobody, and it consumes the seconds you needed for the specific moment
that would have proved it.

TRAP 2 - the one that cuts both ways: THE "I" VERSUS "WE" CALIBRATION.

    At AMAZON, "we decided, we built, we shipped" reads as someone hiding inside a team.
    The interviewer cannot score an individual on a group narrative, so it scores low.

    At GOOGLE, relentless "I did, I decided, I fixed" with no mention of anyone else
    reads as someone who does not work well with others - and collaboration is scored
    explicitly.

The resolution is not to pick a pronoun. It is: BE SPECIFIC ABOUT YOUR OWN ACTIONS AND
EXPLICIT ABOUT OTHER PEOPLE'S CONTRIBUTIONS. "I owned the indexing pipeline; Arun had
done more graphics work so he took the rendering, and his suggestion about caching
thumbnails was what actually got us under the latency target." That sentence scores at
both companies - the "I" is unambiguous and the credit is real.

TRAP 3: TREATING "TELL ME ABOUT A TIME YOU WERE WRONG" AS A TRAP. It is not. Intellectual
humility is a scored trait, so this question is an OPPORTUNITY, and "I can't think of
one" or a fake humility answer ("I care too much about quality") scores zero on an axis
you could have scored well on. Have a real one, with what changed your mind.

TRAP 4: THINKING GOOGLEYNESS MEANS BEING FRIENDLY OR ENTHUSIASTIC. It is not a
personality assessment. Being warm is pleasant and unscored. Describing a decision you
reversed when the evidence turned IS scored.

TRAP 5: MISSING THE "STEP BACK" HALF OF EMERGENT LEADERSHIP. Everyone brings a story
about taking charge. Almost nobody brings the moment they recognised someone else was
better placed and handed it over. That second half is rarer and therefore more
distinguishing.

TRAP 6: THINKING YOU NEED A CORPORATE ETHICS STORY for "doing the right thing when
nobody is checking". At student scale it looks like: telling your group the benchmark you
ran was flawed after they had already celebrated the result; flagging that your test set
had leaked into training when nobody would have noticed; correcting a number in a report
that was in your favour. Small and real beats large and invented.

TRAP 7: FORGETTING THE FEEDBACK IS WRITTEN DOWN FOR STRANGERS. The hiring committee was
not in the room. Your interviewer must convert you into text. Specific moments survive
that conversion; general impressions do not. Say things that are quotable.""",
              r"""5. THE NAIVE MODEL FIRST, THEN THE REAL ONE.

THE NAIVE MODEL: "Googleyness is culture fit - they want to know if I'd be pleasant to
work with, so I should seem friendly, enthusiastic and easy-going."

Why it fails: it produces an interview performance rather than evidence. You arrive
warm, agreeable and complimentary, and the interviewer has nothing specific to write
down. Worse, "culture fit" invites you to try to seem like a certain kind of person,
which reads as performance, and reads worst of all to people who conduct interviews all
week.

THE REAL MODEL: it is a rubric with named components, each of which is a BEHAVIOUR YOU
EITHER DEMONSTRATED OR DID NOT.

Once you see it as a rubric, the preparation becomes concrete. For each component, you
need one specific moment:

    comfort with ambiguity      -> a time the requirements were incomplete and you
                                   named your assumption out loud
    bias to action + humility   -> a time you started before certainty AND a time you
                                   changed course when evidence arrived
    intellectual curiosity      -> a time you dug into WHY rather than just fixing it
    collaboration               -> a time you made someone else more effective
    doing the right thing       -> a time being honest cost you something
    emergent leadership         -> a time you stepped up, and a time you stepped back

Six components, six moments. And they come out of the same six stories from the story
bank - this is not additional material, it is a different index over the same
experiences.

WHY "SHOWING" ACTUALLY OUTSCORES "CLAIMING" - the argument, since this is the crux:

An interviewer must produce written evidence for a hiring committee that was not
present. A claim ("she said she's collaborative") is not evidence, because every
candidate makes it and it cannot be assessed. A specific incident ("she handed the
rendering work to a teammate with more graphics experience and took the harder indexing
piece instead") IS evidence, because it is a fact about something that happened, it is
quotable, and it can be weighed.

So "show, don't claim" is not a stylistic preference or an interview cliché. It is a
direct consequence of how the decision actually gets made - by people reading text
written by someone else. Anything not specific enough to survive being written down and
read by a stranger effectively did not happen.

THE UPGRADE ON TOP: prepare the SAME stories with two weightings, Amazon and Google, and
choose on the day. Section 9 shows both, and shows the cost of choosing wrong.""",
              r"""6. HOW TO PREPARE FOR IT - the procedure, step by step.

The one sentence that holds the whole idea: FOR EACH COMPONENT OF THE RUBRIC, HAVE ONE
SPECIFIC MOMENT YOU CAN DESCRIBE IN TWO SENTENCES - AND BUILD THE HABIT OF NAMING WHAT
YOU DID NOT KNOW, WHO CONTRIBUTED WHAT, AND WHAT CHANGED YOUR MIND.

THIS IS AN INDEXING LOOP over material you already have, and it has a clear stopping
rule:

  - Each pass takes one rubric component and finds a real moment from your existing
    stories that evidences it.
  - Failures look like: no moment exists, or the moment is a claim rather than an
    incident, or it cannot be told in two sentences.
  - WHAT MAKES IT STOP: every component has at least one specific incident attached, and
    you can state each one in two sentences without preamble.
  - You are NOT writing new stories. If you find yourself inventing experiences to fill
    a component, stop - a fabricated example collapses on the first follow-up, and the
    follow-up always comes.

THE STEPS:

  1. TAKE YOUR SIX EXISTING STORIES. This works from the story bank, not instead of it.

  2. GO THROUGH THE RUBRIC COMPONENT BY COMPONENT, and for each, find the MOMENT inside
     an existing story that evidences it. One story typically supplies three or four -
     the moment you did not know something, the moment you deferred to someone, the
     moment you changed your mind.

  3. WRITE EACH MOMENT AS TWO SENTENCES, in the "showing" form: what the situation was,
     and what you specifically did. No adjectives about yourself.

  4. FILL THE GAPS. Any component with no moment attached means either you have not
     looked hard enough at your material, or you genuinely lack an example - and knowing
     which, before the interview, is worth a great deal.

  5. BUILD THE THREE HABITS that make any story score on Googleyness:
       (a) INCLUDE THE MOMENT YOU DID NOT KNOW SOMETHING, and say what you did about it.
       (b) NAME THE PEOPLE and what THEY contributed. By name, with their actual
           contribution.
       (c) DESCRIBE A DECISION YOU REVERSED and what changed your mind.
     Any story containing all three scores on Googleyness regardless of its subject.

  6. PREPARE THE STEP-BACK MOMENT SPECIFICALLY. Everyone has a step-up story. Find the
     time you handed something to someone better placed. It is rarer and it distinguishes.

  7. PREPARE THE HONEST "I WAS WRONG" STORY. Real, with the specific evidence that
     changed your mind. Not a disguised strength.

  8. PRACTISE THE AMAZON AND GOOGLE WEIGHTINGS of your two strongest stories out loud.
     Same facts, different emphasis, as in section 9.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Imagine you are choosing between several people to join a small group that will work
together every day for years. You cannot watch them work first. You get forty-five
minutes each, and then you have to write down what you thought, for a committee that
never met them.

What is actually useful to write down?

Not "she seemed nice" or "he said he was collaborative" - everyone seems nice, everyone
says that, and none of it helps the committee choose. What is useful is a specific
thing that happened: "when I asked about the part she got wrong, she named it
immediately and told me exactly what evidence changed her mind." That is a fact. It can
be weighed against another candidate's facts.

So the question you are really being asked is not "are you a good person to work with".
It is "can you give me something specific enough that I can write it down and someone
who was not here can evaluate it".

Which means the preparation is not about being likeable. It is about having, ready to
hand, the small concrete moments: the time you did not know something and went and
learned it, the time you stepped aside because a teammate was better at the thing, the
time you were wrong for two days and what stopped you being wrong, the time being honest
cost you a bit of credit.

Those moments do not require an impressive career. They require having noticed them at
the time, and having them ready now.

And one more thing, which is where people trip. The same moment can be told to sound
like "I took charge and delivered" or like "here is how the group got there and what I
got wrong". Both are true. One of them is what this particular group is listening for -
and telling it the other way does not just miss the mark, it actively suggests the
opposite trait.""",
              r"""8. THE RUBRIC, WALKED THROUGH PIECE BY PIECE.

No code here, so what follows is each rubric component named, with what it holds, what
it decides, and the sentence pattern that evidences it.

--- THE FOUR AXES ---

    GENERAL COGNITIVE ABILITY
        HOLDS: how you structure an unfamiliar problem.
        DECIDES: most of your technical rounds, from how you think rather than whether
        you finish. Clarify the problem, state your approach and why, name the
        trade-off, then code.
        WHERE IT IS SCORED: inside coding and design rounds. There is no separate GCA
        interview, which is why silent problem-solving costs you even when you get the
        right answer.

    ROLE-RELATED KNOWLEDGE
        HOLDS: can you do the job.
        DECIDES: the technical bar. This is what all your DSA preparation is for.

    LEADERSHIP (EMERGENT)
        HOLDS: stepping up when your skill fits, AND stepping back when someone else's
        does.
        DECIDES: whether you can operate in a team without authority - which is every
        new-grad's actual situation.
        SENTENCE PATTERN: "I took X because I'd done the most work on it; I handed Y to
        [name] because she'd built something similar before."

    GOOGLEYNESS
        HOLDS: the five components below.
        DECIDES: whether you are someone this group can work with, evidenced rather than
        asserted.

--- GOOGLEYNESS, COMPONENT BY COMPONENT ---

    COMFORT WITH AMBIGUITY
        HOLDS: moving forward without complete requirements.
        DECIDES: whether you freeze without instructions.
        THE MOVE THAT SCORES: making the assumption EXPLICIT. Not guessing well -
        stating what you assumed, in writing, so it can be corrected.
        SENTENCE PATTERN: "The brief didn't specify X, so I assumed Y, wrote it in the
        doc, and set a checkpoint to revisit once we had data."

    BIAS TO ACTION, BALANCED WITH HUMILITY
        HOLDS: starting before certainty, and changing course when evidence arrives.
        DECIDES: whether you are decisive or merely stubborn. BOTH halves are needed -
        action alone reads as recklessness.
        SENTENCE PATTERN: "I started with X because waiting for Y would have cost a
        week; when Y came back different from what I expected, I switched to Z."

    INTELLECTUAL CURIOSITY
        HOLDS: digging into WHY, not just what.
        DECIDES: whether you understand your own work or merely operated it.
        SENTENCE PATTERN: "It worked and I didn't know why, which bothered me, so I..."

    COLLABORATION
        HOLDS: making other people more effective.
        DECIDES: whether the team is better with you in it.
        SENTENCE PATTERN: "[Name] was blocked on X, so I..." - and note the effect on
        them, not on you.

    DOING THE RIGHT THING WHEN NOBODY IS CHECKING
        HOLDS: honesty that costs you something.
        DECIDES: trust.
        AT STUDENT SCALE: telling the group your benchmark was flawed after they had
        already celebrated it; flagging leaked test data nobody would have found;
        correcting a number that favoured you.

--- THE THREE HABITS THAT MAKE ANY STORY SCORE ---

    1. Include the moment you did not know something, and what you did about it.
    2. Name the people and what they contributed - by name, with their real contribution.
    3. Describe a decision you reversed, and what changed your mind.

    A story containing all three evidences curiosity, collaboration and humility at once,
    whatever its subject. This is the cheapest way to make existing material score.""",
              r"""9. ONE STORY, TWO SPOTLIGHTS - AND WHAT HAPPENS WHEN YOU AIM THE WRONG ONE.

THE RAW EVENTS (the same capstone as the story-bank entry, deliberately - this is an
index over existing material, not new material):

    Four-person final-year project, six weeks, fixed demo date. Campus lost-and-found
    image search. She owned the indexing pipeline. At week four a full re-index took
    nine hours, allowing one experiment a day. She proposed cutting from twelve item
    categories to four, taking re-index to forty minutes and eight experiments a day.
    One teammate objected - twelve was what they had promised. She argued it on
    iteration speed rather than scope; he agreed and wrote the plan for adding the rest.
    Shipped on the demo date at 87% retrieval accuracy.

--- SPOTLIGHT A: WEIGHTED FOR AMAZON ---

    "Our model's indexing was too slow to iterate on, so I profiled it and found the
    full re-index took nine hours - which meant one experiment a day with two weeks
    left. I decided to cut scope from twelve categories to four. That took re-index to
    forty minutes and our experiment rate to eight a day. We shipped on the demo date at
    87% accuracy, where the alternative was twelve categories at an accuracy nobody
    would have had time to measure."

    WHAT IT SCORES: Ownership, Deliver Results, Bias for Action. First person singular
    throughout. The number is early and load-bearing. The decision is unambiguously
    hers.

--- SPOTLIGHT B: WEIGHTED FOR GOOGLE ---

    "The thing I got wrong was not measuring our iteration speed until week four - by
    then a full re-index took nine hours and we could only test once a day. Once I had
    the numbers the trade-off looked obvious to me, but Arun disagreed strongly, and he
    was right that we'd committed to twelve categories in the proposal. What changed the
    conversation was reframing it from what we'd promised to how fast we could learn -
    eighty experiments instead of ten. He ended up writing the plan for adding the other
    eight categories, and presenting it as a deliberate staging rather than a shortfall.
    We shipped at 87% on four categories.

    What I'd do differently is measure iteration speed in week one. The cut was right;
    needing it at week four was my planning failure."

    WHAT IT SCORES: Googleyness across four components at once - intellectual humility
    ("the thing I got wrong", "he was right"), collaboration (Arun named, with his real
    contribution), curiosity and reasoning (the reframing, explained), and emergent
    leadership (she drove it, then handed the extension plan to him).

--- NOW THE INVERSION: EACH VERSION AT THE WRONG COMPANY ---

    SPOTLIGHT A TOLD AT GOOGLE. Every sentence begins with "I". No other person appears
    at all - the interviewer does not learn that there were three other people on the
    project. Nothing went wrong; nothing was reconsidered. The written feedback reads:
    "strong ownership, no evidence of collaboration, no evidence of humility." Two of
    the four Googleyness components that this story could have evidenced score NOTHING,
    and the absence of any teammate reads as a mild negative rather than a neutral.

    SPOTLIGHT B TOLD AT AMAZON. The decision is buried under the reasoning and the
    credit-sharing. An Amazon interviewer, scoring an individual against Ownership and
    Deliver Results, has to hunt for what she actually did, and the write-up reads
    "seems collaborative, unclear what she personally drove." The number arrives last.

Same events. Same honesty. Opposite verdicts, purely from what was foregrounded.

THE POINT THIS MAKES: the weighting is not presentation polish sitting on top of the
answer. It IS the answer, because the interviewer can only score what you actually said,
and they are writing it down for someone who was not there.

AND THE VERSION THAT WORKS ANYWHERE, for when you are unsure which room you are in:
keep the "I" unambiguous on your own actions AND name other people's real contributions.
"I owned the indexing pipeline and made the call to cut scope; Arun pushed back hard and
was right about the commitment we'd made, and his framing of it as staged delivery is
what got the group behind it." One sentence, both signals, no cost to either.""",
              r"""10. WHAT IT COSTS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT THE PREPARATION COSTS: two to three hours, and only if you have already built the
six stories. This is an INDEX over existing material, not new material - you are walking
the rubric and attaching a moment to each component. If you find yourself writing new
stories, you are doing the story-bank work, not this.

WHERE EACH AXIS IS ACTUALLY SCORED, which surprises people:

  - GCA is scored in your CODING rounds, from how you structure the problem. So thinking
    out loud, stating your approach before writing, and naming the trade-off are not
    politeness - they are the only way this axis gets any evidence at all.
  - Googleyness and leadership are scored in EVERY round, including technical ones. How
    you take a hint, whether you say "I don't know" cleanly, whether you push back when
    you think the interviewer is wrong - all of it lands on these axes.
  - There is often no separate "behavioural round" at Google in the way there is at
    Amazon. The axes are assessed throughout.

THE FOLLOW-UPS TO BE READY FOR:

  - "Tell me about a time you were wrong." Not a trap - a scored opportunity. Real
    example, specific evidence that changed your mind, no disguised strengths.
  - "Tell me about a time you disagreed with someone." They want the other person's
    position stated fairly, and how it resolved - not a story where you were simply
    right.
  - "What would you do differently?" Have one per story.
  - "Tell me about a time you had to work with someone difficult." The trap is
    complaining. The signal is what you changed about your own approach.

THE AMAZON CONTRAST, condensed, since you are preparing for both:

    AMAZON wants: ownership, data, a quantified result, first person singular.
                  "I saw, I decided, I delivered, here is the number."
    GOOGLE wants: reasoning process, what you got wrong, effect on the people around
                  you. "Here is how I framed it, here is what I got wrong, here is how
                  the team got there."

    Same stories. Different foregrounding. Prepare both weightings for your two
    strongest stories and choose on the day.

THE #1 MISTAKE: claiming the traits instead of evidencing them. "I'm collaborative and I
love learning" is said by every candidate, distinguishes nobody, and burns the seconds
you needed for the specific incident that would have proved it. The interviewer must
write something a stranger can evaluate - and a claim is not evaluable.

RUNNER-UP: bringing only step-UP leadership stories and never a step-BACK one, which
leaves the rarer half of emergent leadership completely unevidenced.

TAKEAWAY: Googleyness is a rubric, not a personality - so attach one specific incident
to each component, build the habit of naming what you did not know, who contributed what,
and what changed your mind, and remember your interviewer has to write it down for
someone who was never in the room.""",
          ],
          pitfalls="Claiming traits instead of demonstrating them ('I'm very collaborative'); telling a story with no other humans in it; presenting yourself as never wrong, which reads as low self-awareness; assuming Googleyness means being nice - it means being effective WITH people.",
          followups="'Tell me about a time you were wrong' - have this ready, because at Google it is a Googleyness probe, not a trap. 'What would you do if you disagreed with your team's technical direction?' - argue with evidence, commit once decided, and say what would make you revisit."),

        Q("behavioral", "Tell me about yourself / walk me through your resume (the two-minute answer)",
          "It opens almost every interview and most candidates waste it by narrating their CV chronologically from school. THE INTERVIEWER IS TESTING three things: can you communicate concisely under no pressure at all (if not, the design round will be painful), what do you choose to emphasise (it tells them what you value), and is there a coherent story leading to THIS role. THE STRUCTURE that works is Present - Past - Why here, in about 90 to 120 seconds. PRESENT (20 seconds): who you are right now, in one sentence - 'I'm a final-year Computer Science student specialising in AI and data science.' PAST (60 seconds): two or three specific things that built toward this role, each with a concrete outcome, not a list of coursework. Pick the projects you WANT to be asked about, because you are steering the next twenty minutes. WHY HERE (20 seconds): a specific, researched reason - a team, a product, a paper, a technology - not 'Google is a great company'. THE RULES: no childhood, no chronological march through every semester, no reciting the resume they are holding, and land on something they will want to pull on. Practise it out loud until it is 90 seconds without notes, then stop practising - over-rehearsed sounds worse than slightly rough. And end with a small hook: 'the part I found most interesting was X' invites the natural follow-up.",
          ["behavioral", "introduction", "star", "communication", "interview-strategy"],
          difficulty="Easy",
          frequency="Always asked - it is the first question in essentially every interview at every company.",
          mnemonic="Present -> Past -> Why here, in 90-120 seconds. Choose the two projects you WANT to be asked about; you are steering the next twenty minutes. End on a hook, not on a full stop.",
          example="'I'm a final-year Computer Science student specialising in AI and data science. Two things shaped what I want to do next. The first was a course project where I built a document question-answering system with retrieval-augmented generation - the model part was straightforward, but making the retrieval reliable took most of the work, and that is where I learned the engineering matters more than the model. The second was a summer internship where I owned a data pipeline that had been failing weekly; I added validation and idempotent retries and it ran unattended for the rest of the summer. Both taught me I like the systems side of ML rather than pure modelling, which is why I'm interested in this team specifically - you're building the serving infrastructure, not just the models.'",
          examples=[
              r"""1. THE GOAL - what this question is really doing.

It opens almost every interview, and almost every candidate wastes it by narrating their
CV from school forwards.

Here is the thing to understand first: THE INTERVIEWER IS HOLDING YOUR RESUME. They can
read. Reciting it aloud tells them nothing they did not already have, and it burns the
two most valuable minutes of the whole conversation.

What they are actually testing, and all three matter:

  1. CAN YOU BE CONCISE UNDER NO PRESSURE AT ALL? This is the easiest question you will
     be asked. If you ramble here, they now expect the system-design round to be
     painful, and they are usually right.

  2. WHAT DO YOU CHOOSE TO EMPHASISE? Out of everything you have done, you picked three
     things. That choice tells them what you value and how you see yourself.

  3. IS THERE A COHERENT STORY THAT LEADS TO THIS ROLE? Not a straight line - nobody has
     one - but a reason you are sitting in this particular chair.

And there is a fourth thing, which is yours rather than theirs, and it is the reason
this question is worth real preparation:

    WHATEVER YOU NAME HERE IS WHAT GETS ASKED ABOUT NEXT.

You are not answering a question. You are choosing the topic of the next twenty
minutes. Name the project you can defend three levels deep, and the follow-ups land on
your strongest ground. Name whatever comes to mind first, and you have handed the
steering wheel away.

Target length: 90 to 120 seconds. Not five minutes, and not twenty seconds either.""",
              r"""2. THE INTUITION - three blocks, not a timeline.

The instinct is chronological: born, school, first year, second year, third year, now.
That structure buries the important part at the end and spends your best minute on your
weakest material.

Use three blocks instead, and notice how much of the time goes to the middle one:

    PRESENT       [==]                      ~20 seconds   one sentence: who you are now
    PAST          [==================]      ~60 seconds   two or three things that built
                                                          toward this role, each with an
                                                          outcome
    WHY HERE      [==]                      ~20 seconds   a specific, researched reason

    then a HOOK   [=]                       ~5 seconds    one unfinished thread they will
                                                          want to pull

Compare the two shapes on the same person:

    CHRONOLOGICAL                        PRESENT-PAST-WHY HERE
    "I was born in Chennai..."           "I'm a final-year CS student specialising
    "In school I liked maths..."          in AI and data science."
    "In first year we did C..."          "Two things got me here. First, a capstone
    "In second year, data structures"     where I owned the indexing pipeline and
    "Third year I did a project..."       cut re-index time from nine hours to
    "...and now I'm here."                forty minutes..."

The left version reaches the interesting material at second 100, by which point the
interviewer has stopped listening. The right version opens with it.

The structure is not a stylistic preference. It exists because attention is highest in
the first fifteen seconds, and because the PAST block is the only part that contains
evidence.""",
              r"""3. EVERY TERM, defined the first time you meet it.

TELL ME ABOUT YOURSELF. The opening question. Also arrives as "walk me through your
resume", "give me your background", or "so, tell me a bit about you". Same answer.

PRESENT - PAST - WHY HERE. The three-block structure. Where you are now, what built you
toward this, why this specific role.

THE HOOK. A deliberately slightly-unfinished final clause that invites the follow-up you
want. "The part I found most interesting was that the model barely mattered" is a hook;
"and that's my background" is not.

STEERING. Choosing what gets asked next by choosing what you name. The main strategic
purpose of this answer.

OUTCOME. What happened as a result, ideally with a number. "I built an image search
system" is a description; "I cut re-index time from nine hours to forty minutes, which
took us from one experiment a day to eight" is an outcome.

TAILORING. Adjusting the emphasis - not the facts - for the company. Section 9 shows the
same script weighted two ways.

OVER-REHEARSED. The failure mode at the other end from unprepared. A word-perfect
recitation sounds recited, and it goes flat. Practise until the SHAPE is automatic, then
stop.

RESUME-WALKING. Reading your CV aloud in order. The single most common wrong answer.

THE SIGNAL VERSUS THE CONTENT. The content is what you did; the signal is what your
choice of what to mention says about you. Both are being scored, and most candidates
only think about the first.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - the default failure: STARTING FROM CHILDHOOD. "I was born in Chennai and I've
been passionate about computers since I was young. In school I enjoyed maths, and then
in first year we learned C..." By the time anything relevant arrives, you have spent
sixty seconds on material that could describe several hundred thousand people.

TRAP 2: RECITING THE RESUME THEY ARE HOLDING. Listing every course, every project, every
technology. It signals that you cannot distinguish important from unimportant, which is
precisely the judgement the role requires.

TRAP 3: NAMING A PROJECT YOU CANNOT DEFEND. You mention four projects because they are
all on the CV, and the interviewer picks the one you did least of. Now you are twenty
minutes into your weakest material and you chose it yourself. Name two you know cold.

TRAP 4: A GENERIC "WHY HERE". "Google is a great company with brilliant people" is worse
than saying nothing, because it proves you did not look. Specific is not hard: a team,
a product, a paper, a technology, something you actually read.

TRAP 5 - the subtle one: NO NUMBERS IN THE PAST BLOCK. "I built a machine learning model
for image search" invites "okay, and?" A number does two things at once - it makes the
work concrete, and it demonstrates you measured something, which is itself a signal.

TRAP 6: OVER-REHEARSING INTO FLATNESS. There is a real point where more practice makes
it worse. A word-perfect delivery sounds like a recording, and the interviewer stops
hearing a person. Practise until you can hit the three blocks in 90 seconds without
notes, then stop and let the words vary.

TRAP 7: RUNNING LONG. Four minutes is common and it is a genuine negative mark. Time
yourself out loud - written text always takes longer to say than it looks. If you cannot
get under two minutes, the PAST block has three projects in it and should have two.

TRAP 8: ENDING ON A FULL STOP. "...and that's why I applied. So, yes." leaves the
interviewer to invent the next question, and they may not pick the one you wanted. End
on a hook.""",
              r"""5. THE NAIVE VERSION FIRST, THEN THE REAL ONE.

THE NAIVE VERSION: answer the question literally.

"Tell me about yourself" is, taken at face value, an invitation to describe yourself. So
people describe themselves - background, interests, personality, a chronological account
of how they got here.

It is not a wrong reading of the words. It is a wrong reading of the SITUATION. This is
a professional conversation with a fixed budget of about forty-five minutes, in which
the interviewer must gather enough evidence to write a recommendation. They are not
curious about you as a person yet. They are opening a technical conversation and giving
you the choice of where it starts.

THE REAL VERSION: it is a PITCH with a STEERING function.

Once you see that, every rule follows without needing to be memorised:

  - WHY 90 SECONDS? Because it is an opening, not the substance. The substance is the
    twenty minutes it sets up.
  - WHY NOT CHRONOLOGICAL? Because relevance decreases as you go back, and attention
    decreases as you go forward. The two curves point in opposite directions.
  - WHY ONLY TWO OR THREE THINGS? Because you are selecting the follow-up ground. More
    items means less control and a higher chance they pick your weakest.
  - WHY A NUMBER IN EACH? Because "I built X" invites "and?", while "I cut X from nine
    hours to forty minutes" invites "how?" - and "how?" is the question you want.
  - WHY A SPECIFIC "WHY HERE"? Because the generic version is evidence of not having
    looked, and evidence outranks assertion in every part of this process.
  - WHY A HOOK? Because the alternative is letting them choose the next question.

THE PROOF THAT STEERING IS REAL, and it is worth saying out loud because it converts
this from advice into mechanics: interviewers have limited time and no strong prior about
which of your projects is worth probing. Absent a reason to choose, they pick from what
you just said - it is fresh, it is what the conversation is about, and following it is
the path of least resistance. So the set of things you name IS, in practice, the set of
things you will be asked about. That makes the selection decision the highest-leverage
part of the whole answer, and it is the part almost nobody makes deliberately.""",
              r"""6. HOW TO BUILD IT - the procedure, step by step.

The one sentence that holds the whole idea: WRITE NINETY SECONDS IN THREE BLOCKS -
WHO YOU ARE NOW, TWO THINGS THAT BUILT YOU TOWARD THIS ROLE WITH A NUMBER IN EACH, AND
ONE RESEARCHED REASON FOR THIS COMPANY - THEN END ON SOMETHING THEY WILL WANT TO ASK
ABOUT.

THIS IS A REHEARSAL LOOP, and unusually, it has a stopping rule you must actually obey
- because over-practising makes this particular answer WORSE, which is not true of most
interview preparation:

  - Each pass: say it out loud, timed, without notes.
  - Failures look like: over 120 seconds, no number, a project you would not want probed,
    a generic "why here", or a flat ending.
  - WHAT MAKES IT STOP: you can hit all three blocks in 90 to 120 seconds without notes,
    twice in a row, and the wording comes out slightly different each time.
  - That last clause is the real stopping condition. If the wording is IDENTICAL each
    time, you have gone past prepared into memorised, and it will sound like it. Stop
    earlier than feels comfortable.

THE STEPS:

  1. WRITE THE PRESENT LINE. One sentence, who you are right now. "I'm a final-year
     Computer Science student specialising in AI and data science." That is the whole
     block. Resist adding to it.

  2. LIST EVERY CANDIDATE FOR THE PAST BLOCK. Projects, internships, competitions,
     significant coursework. Ten lines, unfiltered.

  3. SCORE EACH ON TWO AXES: how well can I defend this three questions deep, and how
     relevant is it to THIS role. Pick the two that score highest on both. Not the most
     impressive - the most defensible.

  4. WRITE EACH IN TWO SENTENCES: what it was, and what came out of it WITH A NUMBER.
     Two sentences each, not a paragraph. This whole block is sixty seconds.

  5. RESEARCH THE "WHY HERE" PROPERLY. Find one specific thing - a team, a product, a
     technical problem, a paper, a system you have actually used. Twenty seconds. If you
     cannot fill it specifically, you have not done the research, and that is the finding.

  6. WRITE THE HOOK. One clause at the end that leaves a thread showing. Ideally it
     points at whichever of your two projects you most want to discuss.

  7. TIME IT OUT LOUD. Not in your head - out loud takes far longer. Over 120 seconds
     means the PAST block has too much in it.

  8. CUT THE PRESENT BLOCK FIRST when trimming. It is always the one that has grown.

  9. PREPARE TWO WEIGHTINGS - one leaning toward ownership and numbers, one toward
     reasoning and collaboration. Section 9 shows both. Same facts, different emphasis.

 10. STOP PRACTISING once step-by-step rule above is met.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Imagine you have two minutes at the start of a meeting with someone who will spend the
next forty deciding what to think of you. They have a one-page summary of your history in
front of them, which they have skimmed.

The instinct is to read the page aloud. They have the page.

What actually helps them - and helps you - is to say: here is who I am, here are the two
things I have done that are worth your time, and here is why I am specifically in this
room rather than any other.

And here is the part that changes how you prepare. Whatever you mention, they will ask
about. Not because they are strategic, but because they have limited time and no
particular reason to pick anything else. The thing you just said is the obvious thing to
follow up on.

So you are not really answering. You are choosing the subject of the conversation that
follows - which means the choice should be made carefully, at home, in advance, and
should land on the two things you could talk about for an hour without running out.

Then you leave one thread hanging deliberately. Not a cliffhanger - just a clause that
sounds slightly unfinished. "The surprising part was that the model barely mattered."
Almost nobody can leave that alone, and now the conversation goes exactly where you
prepared for it to go, and it was their idea.""",
              r"""8. THE ARTEFACT, WALKED THROUGH PIECE BY PIECE.

No code here, so what follows is the answer taken apart block by block - what each holds,
what it decides, and how long it runs.

    PRESENT                                                        about 20 seconds
        HOLDS: one sentence stating who you are right now.
        DECIDES: whether the interviewer can place you immediately. That is all it does.
        RULE: one sentence. This block grows every time you rewrite and should be cut
        back every time you trim.
        EXAMPLE: "I'm a final-year Computer Science student specialising in AI and data
        science."

    PAST                                                           about 60 seconds
        HOLDS: two things - occasionally three - that built toward this role. Each in
        two sentences: what it was, and the outcome WITH A NUMBER.
        DECIDES: everything. This is the only block containing evidence, and it is the
        block that selects your follow-up ground.
        RULE: choose for DEFENSIBILITY, not impressiveness. The interviewer will probe
        whichever you name, so name what you know three levels deep.
        NOTE: this is 60% of the answer, exactly as ACTION is the bulk of a STAR story.
        The parallel is not a coincidence - both are the part carrying evidence.

    WHY HERE                                                       about 20 seconds
        HOLDS: one specific, researched reason for THIS company or team.
        DECIDES: whether you look like someone who applied here, or someone who applied
        everywhere. Specificity is the entire signal; enthusiasm is not.
        RULE: name something concrete - a team, a product, a technical problem, a paper.
        If you cannot, you have not researched enough, and that is worth knowing before
        the interview rather than during it.

    THE HOOK                                                       about 5 seconds
        HOLDS: one clause that leaves a thread showing.
        DECIDES: what gets asked next. This is your last chance to steer before control
        passes to them.
        RULE: point it at whichever project you most want to discuss. Make it sound
        slightly unfinished - a surprise, a thing that did not work as expected, a
        counterintuitive finding.
        EXAMPLE: "...though honestly the part I found most interesting was that the model
        barely mattered - the retrieval quality did."

    WHAT IS NOT IN IT
        No childhood. No school. No chronological march. No list of coursework. No
        technologies recited as a list. No personality claims ("I'm a fast learner",
        "I'm very collaborative") - those are asserted rather than shown, and asserting
        them costs you seconds you need for evidence.""",
              r"""9. THE WHOLE THING, WRITTEN OUT AND TIMED - THEN WEIGHTED TWO WAYS.

THE SCRIPT (about 105 seconds spoken, roughly 230 words):

    PRESENT (18s)
    "I'm a final-year Computer Science student specialising in AI and data science."

    PAST (62s)
    "Two things really shaped what I want to do next. The first was my capstone - four
    of us built a campus lost-and-found image search, and I owned the indexing pipeline.
    Four weeks in I realised a full re-index took nine hours, so we could only test one
    change a day. I cut our scope from twelve item categories to four, which brought
    that to forty minutes and let us run eight experiments a day instead of one. We
    shipped on the demo date at 87% retrieval accuracy.

    The second was a summer internship, where I automated a weekly report the team was
    assembling by hand. It took someone about three hours every Monday; I turned it into
    a scheduled job that has been running unattended since."

    WHY HERE (20s)
    "What draws me to this team specifically is the serving infrastructure side - the
    capstone taught me that the interesting problems were in retrieval and latency, not
    in the model, and that's exactly what this team works on."

    HOOK (5s)
    "Though honestly the part I found most interesting was that the model barely
    mattered - the retrieval quality decided everything."

CHECK IT AGAINST THE RULES:
    Present is one sentence.                                              yes
    Two past items, each with a number (9h -> 40min, 1 -> 8, 87%; 3 hours) yes
    Why here names a specific technical area, not the company's reputation yes
    Ends on an unfinished thread pointing at the capstone                  yes
    Under 120 seconds                                                      yes at ~105

NOW THE SAME FACTS, WEIGHTED TWO WAYS - and this is the part that demonstrates judgement.

    WEIGHTED FOR AMAZON (ownership, first person singular, the number up front):

    "...I owned the indexing pipeline. I measured our iteration speed, found the full
    re-index took nine hours, and decided to cut scope from twelve categories to four.
    That took re-index to forty minutes and our experiment rate from one a day to eight.
    We shipped on the demo date at 87%."

    Emphasis: I saw, I decided, I delivered, here is the number.

    WEIGHTED FOR GOOGLE (reasoning, what you got wrong, effect on others):

    "...I owned the indexing pipeline. What I got wrong was not measuring our iteration
    speed until week four - by then we could only test once a day. Once I saw the
    numbers, the trade-off was clear, but one teammate disagreed strongly and he was
    right that we'd committed to twelve categories. What changed his mind was reframing
    it around how fast we could learn rather than what we'd promised - and he ended up
    writing the plan for adding the rest."

    Emphasis: here is how I framed it, here is what I got wrong, here is how the team
    got there.

THE INVERSION WORTH NOTICING: these are not just two styles. Used at the wrong company,
each one actively hurts.

    The Amazon version at Google reads as someone who decided alone and does not mention
    anyone else - and Google scores collaboration and intellectual humility explicitly.

    The Google version at Amazon reads as someone hiding inside a team, with the
    decision and the number buried - and Amazon cannot score an individual on that.

Same events, same honesty, opposite outcome depending on the weighting. That is why you
prepare two and choose on the day, rather than preparing one and hoping.

AND FOR CONTRAST, THE WEAK VERSION, so the difference is audible:

    "I was born in Chennai and I've been passionate about computers since I was young.
    In school I enjoyed maths and physics. In first year we studied C and data
    structures, second year I did database systems and computer networks, and in third
    year I did a machine learning project. I'm proficient in Python, Java, SQL, and I've
    used TensorFlow and PyTorch. I'm a fast learner and I work well in teams. I'm looking
    for a role where I can grow."

    Ninety seconds. No number. No project the interviewer can follow up on. Two
    personality claims asserted rather than shown. Nothing specific to this company.
    Nothing to ask about next - so the interviewer now has to invent a question, and it
    will not be one you chose.""",
              r"""10. WHAT IT COSTS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT THE PREPARATION COSTS: about two hours total. One hour to select and write, one
hour spread across a few days saying it out loud and timing it. It is the highest
return-per-minute preparation available anywhere in the process, because this question
is guaranteed to be asked, is asked FIRST, and sets the agenda for everything after it.

WHEN TO STOP PRACTISING: once you can hit the three blocks in 90 to 120 seconds without
notes and the wording comes out slightly different each time. Past that point, more
practice makes it worse - a word-perfect delivery sounds recited and goes flat. This is
the one piece of interview prep with a genuine upper bound on useful rehearsal.

THE FOLLOW-UPS THIS ANSWER GENERATES, which is the whole point of the design:

  - "Tell me more about that capstone." Exactly what you wanted. This is the hook
    working.
  - "Why did you cut the scope rather than optimise the pipeline?" Prepare this - it is
    the obvious challenge to the decision you just described, and having a real answer
    is worth more than the story itself.
  - "What would you do differently?" Always asked. Have it ready.
  - "Why this team and not [adjacent team]?" Follows from a specific "why here", which
    is a good problem to have.

OTHER QUESTIONS THIS SETS UP, worth knowing:

  - "Why not further study?" if you are a final-year student. Have a straight answer;
    hedging reads as indecision.
  - "Walk me through your resume" is the same question with a slightly stronger pull
    toward chronology. Resist it - use the same three blocks, and mention dates only as
    scaffolding.

THE #1 MISTAKE: treating it as a request for autobiography rather than as the moment you
choose what the interview is about. Everything else - the childhood opening, the
technology list, the missing numbers - follows from that single misreading, and fixing
the misreading fixes all of them at once.

RUNNER-UP: naming four projects instead of two, which hands the interviewer the choice
of which one to probe, and they will not choose your best.

TAKEAWAY: the interviewer already has your resume, so do not read it to them - spend
ninety seconds on who you are now, two things you can defend three questions deep with a
number in each, and one researched reason for this room, then leave a thread hanging so
the next twenty minutes go where you prepared for them to go.""",
          ],
          pitfalls="Going four minutes; starting at 'I was born in...'; reading the resume aloud; being generic about why this company; mentioning a project you cannot defend in depth (they will ask); no structure, so it wanders.",
          followups="'Tell me more about that RAG project' - which is exactly what you wanted, so have the technical depth ready two levels down. 'Why this team rather than another?' - name something only true of them."),

        Q("behavioral", "Tell me about a time you worked with someone difficult (collaboration)",
          "WHAT THEY ARE REALLY TESTING: not whether you have met a difficult person, but whether you are the kind of person who makes conflict worse. They listen for how you describe the other person - contempt is disqualifying - and for whether you tried to understand their position before trying to change it. THE STRUCTURE: STAR, with the ACTION weighted toward the conversation you had, not the technical outcome. And there is a specific move that scores: describe the moment you found out WHY they were behaving that way. Almost every difficult teammate has a reason (they were overloaded, they had been burned by a previous rewrite, they did not understand the requirement, they were being measured on something you were not), and discovering it is the difference between a mature story and a complaint. THE ARC that works: I noticed friction -> I went to them directly and privately -> I asked before telling -> I found the underlying cause -> we agreed a concrete change -> here is what improved. ESCALATION IS ALLOWED, but only after a direct attempt, and framed as getting help rather than reporting someone. CHOOSING THE STORY: a group project where one member was not contributing is fine and normal for a student - do not feel you need a workplace story. What is NOT fine is picking a story where you were the difficult one and do not notice, or a story where the resolution was 'I just did their part myself' with no attempt to fix the cause.",
          ["behavioral", "collaboration", "conflict", "googleyness", "star", "teamwork"],
          difficulty="Medium",
          frequency="Always asked in some form at both Google and Amazon (at Amazon it maps to Earn Trust and Have Backbone).",
          mnemonic="They are testing whether YOU are the difficult one. Never show contempt. The scoring move is finding out WHY they behaved that way - then a private, direct conversation, a concrete agreement, and a real outcome.",
          example="SITUATION: In a four-person final-year project, one teammate kept rejecting pull requests with one-line comments and the review queue stalled for days. TASK: I owned the integration deadline and we were losing three days a week. ACTION: Rather than escalating to the supervisor, I asked him for fifteen minutes and started by asking what he was seeing in the code. It turned out he had spent the previous term on a project that failed a demo because of an untested edge case, and he did not trust our test coverage - which, honestly, was thin. So instead of arguing about review speed, we agreed a rule: any PR touching the model pipeline includes a test for the failure case, and in exchange reviews get a 24-hour turnaround. I wrote the first three tests myself to make the rule cheap to follow. RESULT: Review time dropped from three days to under one, coverage went from about 30% to 70%, and we shipped on time. What I took from it is that a process complaint is usually a trust problem wearing a costume.",
          examples=[
              "The scoring move is finding out WHY. A teammate kept rejecting pull requests with one-line comments and the review queue stalled for days. The easy story is 'he was obstructive and I escalated'. The real one: I asked for fifteen minutes and started by asking what he was seeing in the code — and he had spent the previous term on a project that failed a demo because of an untested edge case, so he did not trust our coverage, which was genuinely thin. Almost every difficult teammate has a reason. Discovering it is the difference between a mature story and a complaint.",
              "The resolution has to be a concrete agreement, not a truce. We traded: any PR touching the model pipeline includes a test for the failure case, and in exchange reviews get a 24-hour turnaround. I wrote the first three tests myself so the new rule was cheap for him to follow. Review time went from three days to under one and coverage went from about 30% to 70%. A story that ends with 'we talked and things got better' has no mechanism and no number, and reads as wishful.",
              "How you describe the other person is itself the test. Contempt is disqualifying — 'he was lazy', 'she was impossible', 'they didn't understand the code'. Interviewers are listening for whether YOU are the difficult one, and the surest signal is whether you can state the other person's position in a way they would recognise. If you cannot say what they thought they were protecting, you probably never asked.",
              "The two failure modes that bracket a good answer. AVOIDANCE: routing around them, doing their part yourself, or waiting for the project to end — solves nothing and tells the interviewer you will silently absorb an underperformer. ESCALATION FIRST: going to the supervisor before a direct private conversation, which reads as someone who creates political problems. The order that scores is private and direct, then escalate with facts and a proposal only if that fails.",
              "Student-scale material is completely acceptable, and often better. A group project where one member was not contributing, a lab partner who disagreed about the approach, a society committee where two people wanted different things, a part-time job with a difficult shift manager. You do not need a workplace story. What you DO need is genuine friction — a story where the disagreement was mild reads as having no conflict to report, which is its own kind of answer.",
              "The probes. 'What if the conversation had not worked?' — escalate with impact and options, not a complaint: 'here is what it is costing, here are the two paths I see'. 'What would you do differently?' — have a real answer; 'nothing' is the wrong one, and 'I would have asked sooner rather than assuming' is almost always true. 'How did they react?' — a story where the other person never changed at all is either incomplete or was resolved by you accommodating them, which is worth saying honestly if so.",
          ],
          pitfalls="Describing the person as lazy, stupid or toxic; a story where you avoided them entirely; escalating first; no resolution, or a resolution where you did their work; picking a conflict that was genuinely your fault without acknowledging it; a story so trivial it shows no real friction.",
          followups="'What if the conversation had not worked?' Escalate with facts and a proposal, not a complaint - 'here is the impact, here are the two options I see'. 'What would you do differently?' Have a real answer; 'nothing' is the wrong one."),

        Q("behavioral", "Tell me about a time you dealt with ambiguity or unclear requirements",
          "This is a top-scored Googleyness signal and it appears at Amazon too (Bias for Action, Are Right A Lot). WHAT THEY ARE TESTING: whether you freeze without instructions, or whether you can impose enough structure to start moving while staying ready to be wrong. Juniors often think the right answer is 'I asked for clarification', which is only the first half - anyone can ask questions; the signal is what you did when the answer was 'we do not know yet'. THE STRUCTURE THAT SCORES: (1) I identified WHAT specifically was ambiguous, and separated it from what was actually clear - most ambiguity is partial. (2) I asked the two or three questions whose answers would change my approach, not twenty. (3) For what remained unknown, I made an EXPLICIT ASSUMPTION, wrote it down, and told people - that is the whole move, because a stated assumption is reversible and a silent one is a landmine. (4) I built the smallest thing that would test the assumption. (5) I set a checkpoint to revisit. THE SENTENCE THAT LANDS: 'I decided X assuming Y; if Y turned out false the fix would cost about a day, so it was worth starting rather than waiting.' That shows you weighed the cost of being wrong, which is exactly what senior engineers do and what interviewers are checking for. Student-scale examples are completely acceptable: an open-ended capstone brief, a hackathon with a vague theme, an internship task where the person who knew the answer was on holiday.",
          ["behavioral", "ambiguity", "googleyness", "star", "decision-making", "bias-for-action"],
          difficulty="Medium",
          frequency="Very commonly asked at Google (a core Googleyness probe) and at Amazon under Bias for Action.",
          mnemonic="Asking for clarification is only half the answer. The scoring move: state an explicit ASSUMPTION, size the cost of being wrong, build the smallest thing that tests it, set a checkpoint. Ambiguity is a reason to start small, not a reason to wait.",
          example="SITUATION: My internship task was 'make the recommendations better' with no metric and no baseline, and the product owner was away for two weeks. TASK: I had six weeks total, so waiting was not viable. ACTION: I split what was ambiguous (what 'better' means) from what was not (the data, the current model, the serving path). I asked the two engineers on the team what users complained about, and the answer was repetitive recommendations rather than irrelevant ones. So I made an explicit assumption - 'better means more diverse, not more accurate' - wrote it at the top of my design doc, and messaged the product owner so it was on the record. Then I built the smallest test: added a diversity re-ranking step behind a flag and measured both diversity and click-through offline, so if my assumption was wrong I had lost three days, not six weeks. RESULT: When the product owner returned she confirmed diversity was the priority; the re-ranker raised category coverage by 40% with click-through flat, and it shipped behind the flag. The lesson I took is that writing the assumption down is what makes it cheap to be wrong.",
          pitfalls="Stopping at 'I asked my manager'; freezing until instructions arrived; making a big irreversible bet on an unstated assumption; a story with no checkpoint or reversal plan; claiming there was ambiguity when the requirements were actually clear and you just did not read them.",
          followups="'What if your assumption had been wrong?' Have the answer ready with a cost - that is the point of the story. 'How do you decide when to stop asking and start building?' When the next question's answer would not change what you build first."),

        Q("behavioral", "Tell me about a time you helped a teammate succeed",
          "A pure collaboration probe, and a surprisingly discriminating one. WHAT THEY ARE TESTING: whether you see other people's success as part of your job or as a distraction from your own, and whether you can help without taking over. THE ANTI-PATTERN, which is the most common failure: 'my teammate was stuck so I did it for them'. That is not helping, it is absorbing - the person learned nothing and you now own two jobs. The scoring version has you making them MORE capable, not less. THE STRUCTURE: notice the difficulty (often they did not ask - noticing is part of the signal), offer without condescension, teach the approach rather than the answer, then step back and let them finish and take the credit. THE DETAIL THAT LANDS: say what the OTHER PERSON went on to do afterwards. 'She then handled the next two of those herself' is the evidence that you taught rather than rescued, and it is the sentence most candidates leave out. AT AMAZON this maps to Hire and Develop the Best; AT GOOGLE it is emergent leadership plus Googleyness. Student-scale is fine: helping a classmate debug rather than sending your code, running a study session, onboarding a new member into a project's codebase, writing the README that stopped the same question being asked five times.",
          ["behavioral", "collaboration", "mentoring", "googleyness", "star", "teamwork"],
          difficulty="Easy",
          frequency="Commonly asked at Google (collaboration) and at Amazon (Hire and Develop the Best).",
          mnemonic="Helping means making them MORE capable, not doing it for them. Teach the approach, step back, let them finish and take the credit - then say what they went on to do alone. That last sentence is the proof.",
          example="SITUATION: A second-year student joined our robotics team and was assigned the sensor-calibration module. After a week he had not committed anything and had stopped coming to stand-ups. TASK: Nobody had asked me to help, but the module blocked my part of the pipeline. ACTION: I asked him to pair for an hour and quickly saw the problem was not the maths - it was that our repo had no setup instructions and he had spent five days fighting the build, too embarrassed to say so. So I did two things: I sat with him while HE fixed the build on his own machine, narrating what I was checking rather than typing, and then I wrote a ten-line SETUP.md so the next person would not lose a week. I deliberately did not touch his module. RESULT: He shipped calibration that week and went on to own the entire sensor stack for the rest of the year, including two modules nobody helped him with. The README also cut the onboarding time for the two students who joined after him from days to about an hour.",
          pitfalls="Doing the work for them and calling it help; a condescending framing ('I explained it very simply'); taking credit for their outcome; no evidence they became more independent; helping only because you were told to.",
          followups="'How did you know they needed help without them asking?' Describe the signal you noticed - it shows attentiveness. 'How do you help without undermining someone?' Ask before offering, teach the method, and let them own the commit and the credit."),

        Q("behavioral", "Tell me about a time you changed your mind because of evidence",
          "One of the highest-signal questions in the set, and candidates routinely fumble it because they think admitting a wrong belief is weakness. It is the opposite: at Google it demonstrates intellectual humility, at Amazon it hits Are Right A Lot (which is explicitly about SEEKING to disconfirm your own beliefs) and Disagree and Commit. WHAT THEY ARE TESTING: do you hold opinions loosely enough to update, and do you go looking for evidence or wait to be corrected? THE STRUCTURE, which has a specific requirement: you must state what you originally believed AND WHY it was reasonable - 'I thought the bottleneck was the model, because inference was the slowest single call in the trace' - because a belief that was never reasonable makes the story about carelessness, not about updating. Then the evidence that changed it, ideally evidence YOU went and got. Then the change, and what it cost. Then, if you can, the habit you built afterwards ('now I profile before I optimise anything'). THE STRONGEST VERSION has you changing your mind against your own interest - abandoning your own design, or conceding a teammate's approach was better after arguing for yours. That combination of backbone and humility is exactly what both companies are looking for, and it is rare enough that a good answer is memorable.",
          ["behavioral", "humility", "data-driven", "googleyness", "star", "are-right-a-lot"],
          difficulty="Medium",
          frequency="Commonly asked at Google as a Googleyness probe and at Amazon under Are Right A Lot / Disagree and Commit.",
          mnemonic="Say what you believed AND why it was reasonable, then the evidence YOU went and got, then the reversal, then the habit it created. Strongest version: you changed your mind against your own proposal.",
          example="SITUATION: In our final-year project I argued hard for a transformer-based classifier over the team's suggestion of gradient-boosted trees, on the grounds that our text features were rich. TASK: I had convinced two teammates, so I owned the decision. ACTION: Before committing three weeks to it, I insisted we spend two days on a fair comparison rather than assuming - a tuned LightGBM baseline against a fine-tuned small transformer, on the same time-based split. The trees came out one point of F1 ahead, trained in 40 seconds against 25 minutes, and ran on a laptop instead of needing a GPU we did not have reliable access to. I had been wrong about where the signal was: most of it came from four numeric columns, not the text. I said so in the next stand-up and we went with trees. RESULT: We shipped two weeks earlier than planned and used the saved time on evaluation, which is what the examiners actually asked about. What stuck with me is that I only found out because I built the baseline - if I had trusted my own argument we would have spent three weeks proving it the expensive way.",
          pitfalls="A story where changing your mind cost nothing; a belief that was never defensible, which makes it a carelessness story; being corrected by someone else rather than seeking evidence; refusing to name what you got wrong; 'I changed my mind because my manager told me to', which is compliance, not updating.",
          followups="'How do you decide when evidence is strong enough to act on?' Talk about sample size, whether the comparison was fair, and the cost of being wrong. 'Tell me about a time you did NOT change your mind and were right' - the mirror question, and worth preparing."),

        Q("behavioral", "Tell me about a time you led without authority",
          "Google calls this EMERGENT LEADERSHIP and scores it explicitly; Amazon reaches it through Ownership and Think Big. WHAT THEY ARE TESTING: as a new grad you will have no title and no direct reports, so the only leadership available to you is the kind people follow voluntarily. Can you create that? THE STRUCTURE: (1) a gap nobody owned - and note that the story is stronger when it was not assigned to you, (2) you stepped in, (3) crucially, HOW you got others to go along, which is the part candidates skip and the part being graded, and (4) you stepped BACK when the right person took over. That last beat is what distinguishes emergent leadership from someone who just likes being in charge, and Google's rubric names it directly. THE INFLUENCE MECHANISMS worth naming explicitly, because 'I convinced them' is not an answer: doing the unglamorous first slice yourself so the idea became concrete rather than a proposal; bringing data so the argument stopped being about opinions; making the change cheap for others to adopt; giving credit publicly. STUDENT-SCALE EXAMPLES that work perfectly: taking over coordination of a stalled group project, organising a study group, setting up CI for a class repo nobody had touched, running a retrospective after a bad hackathon. What does NOT work is a story where you were formally the team lead - that is authority, and the question specifically excluded it.",
          ["behavioral", "leadership", "influence", "googleyness", "star", "ownership"],
          difficulty="Medium",
          frequency="Very commonly asked at Google (emergent leadership is a scored axis) and at Amazon under Ownership.",
          mnemonic="No title, so influence is all you have: do the first slice yourself, bring data, make adoption cheap, give credit away - and STEP BACK when the right owner appears. The step-back beat is what they are listening for.",
          example="SITUATION: Our six-person capstone had no shared way of running experiments - everyone had a notebook, results were screenshots in a chat, and we twice argued about numbers nobody could reproduce. Nobody owned the problem and we had no team lead. TASK: I was not in charge of anything, but we were losing days to it. ACTION: Instead of proposing a process, I spent one evening building the smallest possible version - a script that took a config file, logged metrics to a shared CSV, and printed a comparison table - and I re-ran two people's existing experiments through it so they could see their own numbers come out identical. That made it concrete rather than a suggestion. Then I made adoption free: I converted the two most active notebooks myself so nobody had to do migration work to try it. When a teammate who was better at infrastructure than me offered to add proper experiment tracking, I handed it over and went back to my own module rather than defending my script. RESULT: All six of us were using it within a week, the reproducibility arguments stopped, and the final report had a comparison table we could actually defend to the examiners. She later extended it to log to a database, which was better than what I built.",
          pitfalls="A story where you actually had authority; 'I told everyone we should...' with no mechanism; taking over rather than enabling; never stepping back; a change nobody adopted, with no reflection on why.",
          followups="'What if people had ignored you?' Talk about finding one ally, shrinking the ask, or accepting that the problem was not painful enough yet - not about escalating. 'How did you handle someone who disagreed?' Ideally you incorporated their objection and it improved the thing."),

        Q("behavioral", "Tell me about your most challenging technical project (and how to go deep)",
          "This is the question your loop will spend the most time on, and it is really an ability probe wearing a behavioural costume. WHAT THEY ARE TESTING: technical depth (they will go two or three levels below whatever you say, so every claim must survive), your role specifically (they will separate 'the team built' from 'I built'), and whether you understand the TRADE-OFFS you made rather than just the choices. THE STRUCTURE: 30 seconds of context so they know what the system is, then the specific technical problem that made it hard, then what you tried that did NOT work, then what did and why, then the result with a number, then what you would change. THE 'WHAT DID NOT WORK' BEAT is the one candidates omit and interviewers value most - a project with no failed attempt reads as either trivial or rehearsed. HOW TO PREPARE, and this is the actual work: for your two best projects, write down the answers to 'why did you choose X over Y', 'what was the bottleneck and how did you find it', 'what would break at 100x the load', 'what is the part you are least happy with', and 'what did you measure'. Those five questions cover most follow-ups. CHOOSING THE PROJECT: pick the one where YOU made the hard decisions, not the one with the most impressive title, and never pick something you cannot explain at the level of 'and how does that library actually work?'. For an AI/ML candidate, be ready for the evaluation question - 'how did you know it was any good?' - because a project with no honest evaluation is the fastest way to lose this round.",
          ["behavioral", "technical-depth", "projects", "star", "google", "amazon"],
          difficulty="Medium",
          frequency="Always asked - typically the longest single segment of a new-grad loop.",
          mnemonic="Context (30s) -> what made it HARD -> what failed first -> what worked and why -> a number -> what you would change. Prepare five answers per project: why X over Y, where was the bottleneck, what breaks at 100x, what are you least happy with, what did you measure.",
          example="SITUATION: I built a question-answering system over my university's 400-page course handbook. TASK: The naive version - embed everything, retrieve the top 5, ask the model - was confidently wrong about a third of the time, which is worse than useless for something students would rely on. ACTION: I first assumed the model was the problem and tried a larger one, which barely moved the error rate - that was the wrong hypothesis and it cost me a week. So I built a small evaluation set instead: 60 real questions from the student forum with hand-checked answers, and I measured RETRIEVAL separately from GENERATION. Retrieval recall@5 was 61%, so in nearly 40% of cases the right passage was never in the prompt and no model could have answered. The fix was in the chunking, not the model: I had split on a fixed 1,000 characters, which cut tables in half and separated headings from their content. Chunking on section boundaries with a 15% overlap and prepending the section title to each chunk took recall@5 to 89%. RESULT: End-to-end accuracy went from 68% to 91% on the eval set, with no change of model and about a third of the token cost. What I would change: I built the evaluation set AFTER the first failed week, and it should have been the first thing.",
          examples=[
              "The five questions to prepare per project, which IS the preparation. (1) Why did you choose X over Y? (2) Where was the bottleneck and how did you FIND it - profiling, or guessing? (3) What breaks at 100x the load? (4) What is the part you are least happy with? (5) What did you measure, and against what baseline? Those five cover most follow-ups, and writing the answers down for your two best projects is maybe ninety minutes of work that pays across every loop you sit.",
              "The beat candidates omit: what failed first. A project narrative with no wrong turn reads as either trivial or rehearsed. 'I assumed the model was the problem and tried a larger one, which barely moved the error rate - that cost me a week' is the most credible sentence in the whole answer, because real work looks like that. It also sets up the recovery, which is where the actual skill shows.",
              "Going two levels down, which is what 'depth' means. Say 'I used a vector database' and the follow-up is 'which index, and why?'. Say 'HNSW' and the next is 'what does M control, and what happens if you set efSearch too low?'. There is always another level, and the honest move when you hit your limit is to say so and reason out loud: 'I don't know the internals of the graph construction, but I'd expect a higher M to mean better recall and more memory, because...'. Reasoning from what you do know beats bluffing, and interviewers are testing for exactly that boundary.",
              "For an AI/ML candidate, expect the evaluation question first. 'How did you know it was any good?' A project with no honest evaluation is the fastest way to lose this round, because it suggests you cannot tell whether your own work succeeded. Have the eval set, its size, how you built it, the baseline you beat, and the metric you chose WITH the reason. 'I built 60 hand-checked questions from the student forum and measured retrieval separately from generation' is worth more than any accuracy number.",
              "Separating 'the team built' from 'I built', without diminishing anyone. Interviewers will explicitly probe this, and the clean pattern is: name the scope, then your slice. 'The four of us built the pipeline; I owned retrieval and evaluation.' Then keep every subsequent claim inside your slice. Vague 'we' throughout makes your contribution unscoreable, and claiming the whole thing is worse - it tends to collapse when they ask a detailed question about the part you did not do.",
              "Choosing which project, using a test. Not the flashiest - the one where YOU made the hard decisions and can explain every dependency you name. If you cannot answer 'how does that library actually work?' about something in the story, either learn it before the interview or leave it out. A modest project you understand completely beats an impressive one you assembled from a tutorial, because the interview measures depth of understanding, not the size of the thing you touched.",
          ],
          pitfalls="Choosing the flashiest project rather than the one you understand; 'we' throughout so your contribution is invisible; no numbers; no failed attempt; a claim you cannot defend two levels down (never say 'I used a transformer' if you cannot explain attention); no honest evaluation.",
          followups="'What would break if this had a million users?' Have a real answer - retrieval latency, index size, cost per query. 'What is the weakest part of your design?' Naming it yourself scores far better than being shown it."),

        Q("behavioral", "How do you handle competing priorities and deadlines?",
          "For a student this is coursework versus project versus internship versus job hunting; for a new grad it becomes three teams wanting the same week. WHAT THEY ARE TESTING: do you have a SYSTEM, or do you just work harder until something breaks? And, critically, do you COMMUNICATE early when something is going to slip - because the failure mode that damages a team is not missing a deadline, it is missing it silently. THE STRUCTURE OF A GOOD ANSWER: (1) how you decide what matters - name a criterion, such as impact against effort, what blocks other people (unblocking someone else usually beats making progress alone), and what is genuinely irreversible versus merely late; (2) what you explicitly chose NOT to do, which is the beat that shows you prioritised rather than just worked more hours; (3) who you told, and WHEN - early, with options, not an apology on the deadline; (4) the outcome. THE SENTENCE THAT SCORES: 'I told my supervisor on the Tuesday that the analysis would not be ready by Friday, and offered either a partial result on Friday or the full one on Monday - she took the partial.' That is what a manager wants to hear, because it makes their problem solvable while there is still time. AVOID: 'I just work late', which signals no prioritisation and no sustainability; 'I do everything', which is either false or means everything was done badly; and any story where the person depending on you found out at the deadline.",
          ["behavioral", "prioritisation", "time-management", "communication", "star", "deliver-results"],
          difficulty="Easy",
          frequency="Commonly asked of students and new grads at both Google and Amazon (Deliver Results / Ownership).",
          mnemonic="Have a CRITERION (impact vs effort, who is blocked, what is irreversible), say what you dropped, and escalate EARLY with options rather than late with an apology. 'I worked late' is not prioritisation.",
          example="SITUATION: In one three-week stretch I had a database coursework deadline, the first working demo of our capstone, and an internship assignment my mentor was waiting on. TASK: All three had the same fortnight and honestly could not all be done well. ACTION: I ranked them by who was BLOCKED: my mentor could not start integration until my endpoint existed, so that came first even though it was the smallest piece; the capstone demo had three other people depending on it, so second; the coursework only affected me, and the marking scheme meant losing the top grade band on one assignment cost me very little overall. I messaged my mentor on day two with the date I would have the endpoint, and I told my project group early that I would deliver the model but not the UI, so someone else could pick that up while there was still time. Then I deliberately did the coursework to a good-not-perfect standard and stopped. RESULT: The endpoint landed two days early, the demo worked, and the coursework came in at about 78% rather than the 90% I would have wanted. That trade was the right one, and the important part was that both other parties knew my plan on day two rather than day fourteen.",
          pitfalls="'I work weekends' as the whole answer; claiming you delivered everything perfectly; no criterion, so it sounds like you did whatever was loudest; telling people late; no example of something you deliberately dropped.",
          followups="'What if your manager says all three are top priority?' Present the trade explicitly - 'here is what each costs and what slips; which do you want first?' - and make them choose, which is legitimate and expected. 'How do you estimate?' Break it down, add buffer for the unknown parts, and re-estimate out loud when reality disagrees."),

        Q("behavioral", "Tell me about a time you made a mistake that affected other people",
          "Distinct from 'your biggest failure' because it adds the element that actually tests character: someone else paid for it. WHAT THEY ARE TESTING: whether you disclose fast or hide, whether you fix the CAUSE or just the symptom, and whether you can talk about your own error without either minimising it or wallowing. THE ARC: what you did, how you found out (finding it yourself is better than being told), WHO YOU TOLD AND HOW QUICKLY - this is the beat that matters most, and 'within twenty minutes I told the two people affected' is worth more than any technical fix - what you did to contain the damage, then the fix, then the SYSTEMIC change so the same class of mistake cannot recur. That last part is the difference between an apology and an engineer: 'I added a confirmation step / a test / a check in CI so nobody can do that again' turns your mistake into a permanent improvement for everyone. TONE MATTERS: own it in the first person without a scapegoat, and without excessive self-flagellation, which reads as fragile rather than accountable. CHOOSING THE STORY: it must be a real mistake with real consequences - 'I once worked too hard' is transparent and insulting - but it should not be a catastrophic judgement or integrity failure. Deleting data, breaking a shared build, shipping a bug that cost a teammate a day, a wrong number in a report someone presented: all good. And practise saying the sentence 'that was my mistake' cleanly, because interviewers notice candidates who cannot.",
          ["behavioral", "failure", "ownership", "accountability", "star", "earn-trust"],
          difficulty="Medium",
          frequency="Always asked in some form - at Amazon under Earn Trust and Ownership, at Google as a humility probe.",
          mnemonic="Own it in the first person, disclose FAST, contain, fix, then make the class of mistake impossible (a test, a check, a guard). The systemic fix is what turns a confession into an engineering story.",
          example="SITUATION: During my internship I wrote a migration script to backfill a column and ran it against what I believed was the staging database. TASK: It was production, and it overwrote the column for about 12,000 rows with a default value. ACTION: I noticed within a couple of minutes because the row count in the output did not match staging's size. I did not try to quietly fix it - I told my mentor immediately and, because it was 4pm, I said it out loud in the team channel too so nobody built on the bad data. We restored the column from the previous night's backup within the hour, and I wrote the reconciliation query to confirm every affected row matched the backup. Then I did the part I actually care about: the root cause was that my shell prompt did not show which environment I was connected to, and the script took a connection string with no confirmation. I added an environment banner to the shared setup script and a required --confirm-production flag to the migration tool. RESULT: Total data-loss window was about 50 minutes with no downstream impact, and two other interns later told me the environment banner had stopped them making the same mistake. My mentor's feedback was that telling the channel immediately was the right call, and that is the habit I kept.",
          examples=[
              "The arc, with the beat that actually scores. Ran a backfill against what I believed was staging; it was production, and about 12,000 rows had a column overwritten. Noticed within two minutes because the output row count did not match staging's size. Told my mentor immediately AND said it in the team channel, because it was late afternoon and people were about to build on that data. Restored from the previous night's backup inside the hour and wrote the reconciliation query proving every row matched. The graded moment is not the restore — it is that the disclosure happened before the fix, in public, while it was still embarrassing.",
              "Why the systemic fix is what separates this from an apology. The root cause was that my shell prompt did not show the environment and the migration tool accepted a connection string with no confirmation. So: an environment banner in the shared setup script, and a required --confirm-production flag. Two other interns later said the banner had stopped them doing the same thing. 'I was more careful afterwards' is a resolution; 'I made it impossible for the next person' is engineering, and interviewers hear the difference immediately.",
              "How this differs from the biggest-failure question, since you will likely get both. FAILURE is about judgement: what you got wrong and how your process changed. THIS is about character: how fast you disclosed, whether you hid it, how you rebuilt trust. The same event can serve both, but the emphasis moves — there you spend your time on the wrong decision and the structural fix, here on who you told and when. Decide in advance which of your stories serves which, because reusing the identical telling in one loop is noticeable.",
              "The tone calibration, which is narrower than people think. Deflecting ('the configs were confusingly named') reads as blaming the environment even when true. Wallowing — two minutes of self-criticism — reads as fragile rather than accountable. The calibrated version states the error plainly in one sentence, spends the rest on containment and the fix, and mentions the contributing factor only as the thing you then fixed. Practise saying 'that was my mistake' cleanly; interviewers notice candidates who cannot get the words out.",
              "Choosing a story with real stakes but survivable ones. Good: data loss, a broken shared build, a bug that cost a teammate a day, a wrong number in a report someone presented, force-pushing over a colleague's branch. Bad in one direction: 'I once mislabelled a variable' — no stakes, nothing revealed. Bad in the other: anything involving dishonesty or a judgement failure severe enough to be a hiring risk. Student-scale is completely fine; what matters is that someone else paid for it.",
              "The probes, and what each is checking. 'Who did you tell, and when?' — the whole question in one, and a delay of hours is a different answer from a delay of minutes. 'What did your manager say?' — real feedback makes the story credible; a story where nobody reacted sounds invented. 'Has it happened again?' — should be no, BECAUSE of the systemic fix. 'Why the whole channel rather than just your mentor?' — because others were about to build on the bad data, which shows you thought about blast radius rather than about your own embarrassment.",
          ],
          pitfalls="A fake mistake; blaming the process, the documentation or a teammate; hiding it and fixing it quietly (disqualifying if it comes through in the story); no systemic fix; over-apologising for five minutes; a mistake with no actual consequence.",
          followups="'What did your manager say?' Real feedback makes the story credible. 'Has it happened again?' The answer should be no, because of the systemic fix - and if a related thing did happen, say what you learned the second time."),

        Q("behavioral", "How do you handle a group project where someone is not pulling their weight?",
          "A specifically student-shaped question, asked because it is the closest available proxy for a real team problem - and interviewers know the honest answer is uncomfortable. WHAT THEY ARE TESTING: whether your first instinct is to escalate, to absorb, or to address it; and whether you can distinguish 'will not' from 'cannot'. THE ORDER THAT SCORES: (1) find out WHY before deciding what it is - the most common causes are being stuck and embarrassed to say so, not understanding what was expected, or a genuine personal crisis, and only occasionally is it indifference; (2) talk to them directly and privately, asking rather than accusing; (3) make the work visible and smaller - a shared board with named, small tasks makes drift obvious early and gives a stuck person a rung to grab; (4) adjust the plan honestly if they genuinely cannot deliver, rather than pretending; (5) escalate to the supervisor only after a direct attempt, and framed as 'here is what we tried' rather than as a complaint. THE TRAP: the answer most students give is 'I just did their part so the project would not suffer'. Say that and you have told the interviewer you will silently absorb an underperforming teammate's work, hide the problem from your manager, and burn out - three things a hiring manager specifically does not want. Doing the work is sometimes the right short-term call for a deadline, but only alongside addressing the cause. THE STRONGEST STORIES include a moment where you found out the reason and it changed what you did.",
          ["behavioral", "teamwork", "conflict", "collaboration", "star", "student"],
          difficulty="Medium",
          frequency="Very commonly asked of students and new grads at both companies.",
          mnemonic="Find out WHY before deciding WHAT. Ask privately, make tasks small and visible, replan honestly, escalate only after a direct attempt - and never let 'I just did it myself' be the whole answer.",
          example="SITUATION: In a five-person systems project, one member missed two consecutive integration deadlines and stopped replying in the group chat, with the demo two weeks out. TASK: His component sat between mine and the front end, so nothing could be tested end to end. ACTION: Rather than assuming he had checked out, I messaged him directly and asked if he was okay. He was dealing with a family illness and had been too embarrassed to say anything to four people at once. So we changed the plan honestly instead of pretending: I took over the integration layer since it was on my critical path anyway, we cut one optional feature from his component to shrink it to something he could finish, and I told the supervisor that we were rescoping - not that someone had failed, because that framing would have been both unkind and inaccurate. We also moved to a shared board with small named tasks so nobody could silently drift for two weeks again. RESULT: We demoed on time with one fewer feature, he delivered the reduced scope, and the supervisor's feedback was specifically that the rescoping decision was made early enough to be useful. If I had assumed indifference and escalated, I would have been wrong and the outcome would have been worse.",
          pitfalls="'I did their work' as the entire answer; escalating to the supervisor first; assuming laziness; a public confrontation; no change to how the team worked afterwards, so the same drift could recur.",
          followups="'What if the reason had been that they simply did not care?' Then you address it directly, adjust the plan, and escalate with a factual record - the process is the same, the conclusion differs. 'How would you prevent it next time?' Small visible tasks and short check-ins surface drift in days rather than weeks."),

        Q("behavioral", "Why software engineering, and why AI/ML specifically?",
          "It sounds like small talk and it is not. WHAT THEY ARE TESTING: is your interest specific and durable, or did you pick the field because it is where the jobs are? Interviewers hear the generic version fifty times a week ('I've been passionate about technology since childhood'), and specificity is the entire differentiator. THE STRUCTURE: (1) a concrete ORIGIN - one specific moment or project, not a general love of computers; (2) what you did about it that nobody made you do, because unprompted effort is the strongest evidence of genuine interest; (3) why AI/ML rather than adjacent fields, with a real reason - and 'because it is the future' is not one; (4) what kind of AI/ML work, which is where you show you understand the field has parts. THAT LAST POINT MATTERS MORE THAN CANDIDATES REALISE: saying 'I want to do machine learning' to an SDE interviewer is vague, whereas 'I'm drawn to the engineering side - the serving, evaluation and data quality parts, because in my projects that is where the difficulty actually was' tells them exactly which team you fit and is far more credible from a new grad. IT ALSO PROTECTS YOU: a candidate who claims to want cutting-edge research will be measured against research depth they do not have, while a candidate who says they want to build reliable ML systems is being measured on exactly the skills a new-grad SDE role needs. HONESTY BEATS AMBITION here - a well-argued modest answer outperforms an over-claimed one every time.",
          ["behavioral", "motivation", "career", "ai", "ml", "interview-strategy"],
          difficulty="Easy",
          frequency="Very commonly asked - it opens or closes most new-grad loops.",
          mnemonic="Be SPECIFIC: one concrete origin, one thing you did unprompted, one real reason for AI/ML over adjacent fields, and which PART of AI/ML you want. 'It's the future' and 'passionate since childhood' are the two answers they hear all day.",
          example="'The honest origin is unglamorous. In second year I built a small model to predict which of my college's library study rooms would be free, because I kept walking across campus for nothing. It got 80% accuracy in an afternoon and I was pleased with myself - and then it was wrong every single week of exams, because the pattern it had learned did not exist any more. Nobody had set that as an assignment; I just wanted the rooms. Chasing why it failed is what got me into data drift, evaluation and eventually into the systems side of ML. That is also why I'm interested in ML engineering rather than research: in every project I've done, the modelling was the easy part and the difficulty was data quality, evaluation and keeping the thing working after the first week. I would rather be the person making models reliable in production than the person squeezing out the last point of accuracy, and this team's work on serving infrastructure is exactly that.'",
          examples=[
              "A full answer, with the origin deliberately unglamorous. 'In second year I built a small model to predict which library study rooms would be free, because I kept walking across campus for nothing. It got 80% accuracy in an afternoon and I was pleased with myself — and then it was wrong every week of exams, because the pattern it had learned no longer existed. Nobody set that as an assignment; I just wanted the rooms. Chasing why it failed is what got me into data drift and evaluation, and eventually into the systems side of ML.' A small real story beats a grand claimed one, because it is checkable.",
              "Why the answer must name WHICH PART of AI/ML you want. Saying 'I want to do machine learning' to an SDE interviewer is vague and, worse, invites them to measure you against research depth you do not have. 'I'm drawn to the engineering side — serving, evaluation, data quality — because in my projects that is where the difficulty actually was' tells them exactly which team you fit and is far more credible from a new grad. It also protects you: you are now being assessed on the skills the role needs.",
              "The unprompted-effort test. Interviewers weight what you did that NOBODY ASKED YOU TO DO far above coursework, because coursework is evidence of compliance and side projects are evidence of interest. A course you took is weak; a thing you built because it annoyed you is strong. If your only material is coursework, anchor it to something you then extended beyond the brief — and say that you did.",
              "The two answers they hear all day, and why each fails. 'I've been passionate about technology since childhood' — unfalsifiable, says nothing, and is true of every candidate in the queue. 'AI is the future' — a claim about the industry, not about you, and it is what someone says when they picked the field for the job market. Money and job availability are perfectly legitimate REASONS and terrible ANSWERS; nobody is offended by them, they simply do not distinguish you.",
              "Honesty beats ambition here, which surprises people. A well-argued modest answer outperforms an over-claimed one every time, because the over-claim gets tested. If you say you want to do research, expect 'what's the last paper you read and what did you disagree with?'. If you say you want to build reliable ML systems, expect questions about monitoring and evaluation — which you can actually answer. Claim the thing you can defend two levels down.",
              "The follow-ups to prepare. 'What's the last ML paper or article you read?' — have a real, recent one with an OPINION about it, not a summary. 'Where do you see yourself in five years?' — show a direction, admit uncertainty honestly, and connect it to what this role would teach you. 'Why not a PhD?' — if you are choosing industry over research, have a genuine reason (you like shipping, you want feedback from users) rather than a dismissive one.",
          ],
          pitfalls="'Passionate about technology since I was young'; 'AI is the future'; naming money or job availability as the reason (true, and not the answer); claiming research ambitions you cannot back with reading or projects; being unable to name a single specific thing you did unprompted.",
          followups="'What is the last ML paper or article you read?' Have a real, recent answer with an opinion about it. 'Where do you see yourself in five years?' Show a direction, admit uncertainty honestly, and connect it to what the role would teach you."),

        Q("behavioral", "Building a story bank: six stories that cover thirty questions",
          "The single highest-leverage piece of behavioural preparation, and almost nobody does it. THE INSIGHT: there are not thirty behavioural questions, there are about six story SHAPES, and one well-built story answers several prompts with a shift of emphasis. Preparing per-question means memorising thirty answers badly; preparing per-story means having six you know cold and can re-angle live. THE SIX TO BUILD: (1) a DELIVERY story - you shipped something hard under a real constraint (covers Deliver Results, Ownership, prioritisation, 'most challenging project'); (2) a FAILURE story - you got something wrong and fixed the cause (covers failure, mistake affecting others, Earn Trust, humility, feedback); (3) a CONFLICT story - you disagreed with someone and resolved it (covers difficult teammate, Have Backbone, disagreeing with a manager, collaboration); (4) an AMBIGUITY story - you moved without complete information (covers ambiguity, Bias for Action, Are Right A Lot, incomplete data); (5) a LEARNING story - you taught yourself something hard, fast, because you needed it (covers Learn and Be Curious, new technology, out of your depth); (6) a HELPING story - you made someone else more effective (covers collaboration, mentoring, Hire and Develop the Best, Googleyness). HOW TO BUILD EACH: write it in STAR, keep it under two minutes spoken, and make sure it contains a NUMBER, a DECISION you made, and something you would do differently. Then build the index: list the questions each story can answer and which detail to emphasise for each. THE DELIVERY SKILL that separates good from great: when a question arrives, take two seconds to pick the story and the ANGLE, then start with a one-sentence headline ('This is about a time I shipped a rescoped feature rather than a late complete one') so the interviewer knows where you are going.",
          ["behavioral", "star", "preparation", "interview-strategy", "story-bank"],
          difficulty="Easy",
          frequency="Applies to every behavioural round at every company - this is the preparation method, not a question.",
          mnemonic="Six stories, not thirty answers: DELIVERY, FAILURE, CONFLICT, AMBIGUITY, LEARNING, HELPING. Each in STAR, under two minutes, containing a number, a decision, and a 'what I'd change'. Then index which questions each one answers.",
          example="One story, three angles. A capstone where you rescoped a feature to hit a demo date. Asked about DELIVER RESULTS, emphasise the deadline, the trade you made and the number. Asked about DEALING WITH AMBIGUITY, emphasise that the requirement was unclear, the assumption you wrote down, and the checkpoint. Asked about CONFLICT, emphasise the teammate who wanted to ship it complete and late, how you argued it, and how you converged. Same facts, three different first sentences - and the interviewer never hears a recycled answer because you led with the part they asked about.",
          examples=[
              r"""1. THE GOAL - what this is and why it is the highest-leverage prep you can do.

Behavioural rounds ask what look like thirty different questions:

    Tell me about a time you failed.
    Tell me about a conflict with a teammate.
    Tell me about a time you had to decide without enough information.
    Tell me about your most challenging project.
    Tell me about a time you disagreed with your manager.
    ... and twenty-five more

Almost everybody prepares by trying to have thirty answers. That fails in two ways: you
cannot hold thirty rehearsed answers in your head under pressure, and the ones you do
hold come out sounding recited.

THE INSIGHT THAT CHANGES THE WORK:

    THERE ARE NOT THIRTY QUESTIONS. THERE ARE ABOUT SIX STORY SHAPES.
    ONE WELL-BUILT STORY ANSWERS SEVERAL PROMPTS WITH A SHIFT OF EMPHASIS.

Build six stories you know cold, learn to re-angle them live, and you have covered the
whole surface - with material you actually remember, because six real experiences are
easier to hold than thirty rehearsed paragraphs.

The goal of this page is therefore not "prepare answers". It is:

    (a) build six stories, each in a specific structure, each containing three specific
        things;
    (b) build the INDEX that maps questions to story-plus-angle, so that when a question
        lands you are choosing rather than composing.

That second part is what almost nobody does, and it is what makes the difference between
freezing for eight seconds and opening confidently.""",
              r"""2. THE INTUITION - six stories, thirty doors.

Draw it as a mapping, and the leverage becomes obvious:

    THE SIX STORIES              THE QUESTIONS THEY OPEN

    DELIVERY   -------------->   most challenging project
               \                 tell me about something you shipped
                \--------------> how do you prioritise
                 \-------------> a time you took ownership

    FAILURE    -------------->   tell me about a failure
               \---------------> a mistake that affected others
                \--------------> how do you take feedback
                 \-------------> something you would do differently

    CONFLICT   -------------->   a difficult teammate
               \---------------> disagreeing with a manager
                \--------------> convincing someone who disagreed

    AMBIGUITY  -------------->   deciding without enough data
               \---------------> a time you had to act fast
                \--------------> handling an unclear requirement

    LEARNING   -------------->   learning something hard, fast
               \---------------> out of your depth
                \-------------->  picking up a new technology

    HELPING    -------------->   collaboration
               \---------------> mentoring someone
                \--------------> making the team better

Six sources, roughly thirty destinations.

And there is a second multiplier, which is the actual skill: ONE STORY TOLD THREE
DIFFERENT WAYS. The same set of events, opened with a different sentence and weighted
toward a different part, answers genuinely different questions. Section 9 does this in
full with a single story - it is the part worth practising most, because it is what
turns six stories from "not quite enough" into "comfortably enough".

The shape of the work:

    six real experiences  ->  written in a fixed structure  ->  each re-angleable three
    ways  ->  indexed against the question list""",
              r"""3. EVERY TERM, defined the first time you meet it.

BEHAVIOURAL INTERVIEW. A round that asks about things you have actually done, on the
theory that past behaviour predicts future behaviour. Distinct from a technical round;
at Amazon and Google it carries real weight and can sink an otherwise strong candidate.

STAR. The standard structure for telling one of these stories:
    SITUATION - the context, in one or two sentences.
    TASK      - what you specifically were responsible for.
    ACTION    - what YOU did, step by step. The heart of it.
    RESULT    - what happened, with a number.
Some people add R for REFLECTION - what you would do differently. Treat it as required;
it is what turns a story into evidence of judgement.

STORY SHAPE. One of the six categories above. Not a specific anecdote - a TYPE of
experience.

ANGLE. Which aspect of a story you emphasise for a given question. Same events,
different opening sentence, different weighting.

HEADLINE SENTENCE. The one sentence you open with that states what the story is about.
It buys you thinking time and tells the interviewer immediately that you understood the
question.

LEADERSHIP PRINCIPLES (LPs). Amazon's fourteen stated values - Ownership, Bias for
Action, Have Backbone Disagree and Commit, Deliver Results, Earn Trust, Learn and Be
Curious, and others. Amazon interviewers ask explicitly against them and score against
them.

GOOGLEYNESS. Google's rough equivalent - comfort with ambiguity, collaboration,
intellectual humility, bias to action.

THE BAR RAISER. At Amazon, an interviewer from outside the hiring team whose job is to
hold the standard. Often the toughest behavioural round.

FOLLOW-UP QUESTIONS. The probing after your story - "what did your teammate think?",
"what would you do differently?", "how did you know that was the right call?". These
are where memorised answers fall apart, and they are the actual test.

THE "I" VERSUS "WE" PROBLEM. Interviewers listen for what YOU did. Candidates who say
"we" throughout leave the room having described a team, with no evidence about
themselves.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - the fatal one: MEMORISING WORD FOR WORD.

A recited answer sounds recited. Worse, it shatters on the first follow-up, because you
rehearsed a paragraph rather than remembering an experience. "What did your teammate
think about that?" is not in the paragraph, and the gap between the polished narrative
and the sudden groping is obvious from across the table.

Learn the STRUCTURE and the NUMBERS. Let the words come out fresh each time. You should
be able to tell the story in three minutes or in forty-five seconds depending on what
the room needs, which is impossible if you memorised one fixed version.

TRAP 2: no number in the result. "It went well and the team was happy" is an anecdote.
"We cut re-index time from nine hours to forty minutes, which took us from one
experiment a day to eight" is evidence. Every story needs at least one figure - latency,
percentage, days saved, people affected, size of the thing.

TRAP 3: saying "we" throughout. The interviewer is evaluating YOU. Describe the team's
situation, then be specific and unembarrassed about your own actions: "I proposed", "I
wrote", "I decided", "I was wrong about". This feels boastful and is not - it is the
information they are there to gather. Not providing it is the actual error.

TRAP 4: a failure story where you were not at fault. "My biggest failure was when a
teammate did not deliver" is not a failure story; it is a complaint. The story must have
a decision YOU made that was wrong, and what you changed as a result. Choosing a
safe-but-fake failure is the single most common way this question is wasted.

TRAP 5 - the practical constraint people miss: AMAZON INTERVIEWERS COMPARE NOTES
AFTERWARDS, and each round is assigned different principles. Telling the same story in
three rounds is visible to them and reads as a thin candidate. This is precisely why six
is the minimum, not a comfortable surplus - four rounds, no repeats, and one held in
reserve.

TRAP 6: front-loading the situation. Most people spend 80% of the time on background and
20% on what they did. Invert it. The interviewer needs two sentences of context; they
need two minutes of your actions and reasoning. If they are still hearing setup at the
ninety-second mark, you have lost the round.

TRAP 7: no reflection. "What would you do differently?" gets asked almost every time,
and "nothing, it worked out well" is a bad answer - it reads as either dishonest or
incurious. Have a real one prepared for each story, and make it specific.

TRAP 8: stories with no stakes. "I had a tight deadline so I worked hard and finished"
contains no decision. A usable story needs a moment where you could have gone two ways
and had to choose, because the choice is the thing being evaluated.""",
              r"""5. THE NAIVE APPROACH FIRST, THEN THE REAL ONE.

THE NAIVE APPROACH: prepare an answer per question.

Find a list of thirty common behavioural questions. Write an answer to each. Try to
remember them.

Why it fails, concretely:
  - THIRTY IS TOO MANY. Under pressure you will retrieve maybe five reliably.
  - IT PRODUCES RECITATION, which sounds like recitation and collapses on follow-ups.
  - THE LIST IS NEVER COMPLETE. The real question is phrased differently from your
    thirty, and now you are composing from scratch anyway, having practised the wrong
    skill entirely.
  - IT IS FRAGILE. You prepared "tell me about a failure"; they ask "tell me about a
    time you had to admit you were wrong to someone senior". Same story needed,
    different framing, and your rehearsed paragraph does not fit the frame.

THE REAL APPROACH: six stories, deeply built, indexed by question.

You prepare six EXPERIENCES rather than thirty ANSWERS. Each is written out once in
STAR, with its numbers fixed and its reflection thought through. Then you build an index
of which question maps to which story and which angle.

WHY SIX IS THE RIGHT NUMBER - the argument, since "six" needs justifying:

Look at what behavioural questions actually probe. Nearly all of them are asking about
one of six things: can you SHIP, can you own a MISTAKE, can you handle DISAGREEMENT, can
you act under UNCERTAINTY, can you LEARN, and do you make OTHERS better. Those are the
six shapes. They are not arbitrary - they map closely onto Amazon's principles and onto
what Google means by Googleyness, because both are attempts to describe the same set of
underlying behaviours.

Below six, you have a gap - some question arrives with nothing behind it. Above six,
you dilute; the seventh and eighth stories are never as well built as the first six, and
they are the ones that fall apart under probing.

Six also satisfies the practical constraint from trap 5: four or five rounds, no
repeats, one in reserve.

THE UPGRADE THAT MAKES SIX SUFFICIENT - re-angling.

This is the skill that separates prepared candidates from well-prepared ones. The same
story, told with a different opening sentence and a different weighting, answers
genuinely different questions. You are not being evasive - the events really do contain
all of those aspects, and choosing which to foreground is exactly what a good answer
does. Section 9 demonstrates it on one story, three ways.

Practise this out loud. It is the only part of the whole exercise that does not work on
paper.""",
              r"""6. HOW TO BUILD IT - the procedure, step by step.

The one sentence that holds the whole idea: WRITE SIX REAL EXPERIENCES IN STAR WITH A
NUMBER, A DECISION AND A REGRET IN EACH, THEN BUILD AN INDEX FROM QUESTIONS TO
STORY-PLUS-ANGLE SO THAT ANSWERING BECOMES CHOOSING RATHER THAN COMPOSING.

THIS IS A LOOP, and it needs a clear stopping rule or you will keep polishing forever:

  - Each pass takes one story, writes or refines it, then tests it by answering the
    questions it is supposed to cover - OUT LOUD, timed.
  - Failures show up as: running over two minutes, missing a number, having no answer to
    "what would you do differently", or realising the story does not actually fit a
    question you assigned it to.
  - WHAT MAKES IT STOP: every question on your list maps to at least one story and
    angle, AND you can tell each story in under two minutes without notes, AND you can
    answer three follow-ups on each without hesitating.
  - Without that stopping rule this becomes endless rewriting of stories that were
    already good enough, which is the most common failure mode of behavioural prep.

THE STEPS:

  1. LIST YOUR RAW MATERIAL. Every project, internship, group assignment, hackathon,
     club role, part-time job. Twenty lines, no filtering. Most people underestimate
     what they have, and academic projects count - they contain real constraints, real
     teammates and real decisions.

  2. SORT THE MATERIAL INTO THE SIX SHAPES. Delivery, failure, conflict, ambiguity,
     learning, helping. Some experiences fit two or three - note that, it is the
     re-angling opportunity.

  3. PICK ONE PER SHAPE. Choose the one with the clearest DECISION and the most
     available NUMBERS. Prefer recent, prefer ones where your role was central, prefer
     ones you can talk about honestly.

  4. WRITE EACH IN STAR. Two sentences of situation. One sentence of task. Then the
     bulk on action - what you did, in order, in first person singular. Then the result,
     with a figure.

  5. CHECK EACH AGAINST THE THREE-ITEM CHECKLIST:
       - A NUMBER in the result.
       - A DECISION you personally made, where the other choice was real.
       - A REFLECTION - something you would do differently, specific and honest.
     A story missing any of these is not finished.

  6. TIME IT SPOKEN. Under two minutes. Out loud, not in your head - written prose takes
     far longer to say than it looks. Cut the situation first; it is always too long.

  7. BUILD THE INDEX. Take a list of common behavioural questions and, for each one,
     write down which story and which angle. Where a question has no story, go back to
     step 3 and reconsider your picks.

  8. WRITE THE HEADLINE SENTENCE for each story-angle pair - the one sentence you open
     with. This is what you actually deploy in the room.

  9. REHEARSE THE FOLLOW-UPS. For each story, have someone ask: what did the others
     think, what would you do differently, how did you know that was right, what was the
     hardest part, what did you get wrong. If you cannot answer these fluently, you
     memorised rather than remembered.

 10. PRACTISE RE-ANGLING OUT LOUD. Take one story and tell it three times for three
     different questions. This is the highest-value rehearsal and the one people skip
     because it feels repetitive.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Think about a musician preparing for an audition where the panel will call out requests.

The nervous approach is to learn thirty pieces note for note. It does not work. Thirty is
more than anyone holds securely, the playing comes out stiff, and the moment the panel
asks for one in a different key everything falls apart.

What experienced musicians do instead is learn six pieces properly - properly enough to
play them slower, faster, in a different key, with a different emphasis. Then when the
panel asks for something in a style they have not literally prepared, they reach for the
piece that fits and bend it.

The preparation is not "have an answer ready". It is "know six things so well that you
can shape them to whatever is asked".

There is a second half, and it is the part people skip. The musician also knows, in
advance, which piece to reach for on each kind of request. That decision is made at home
with time to think, not on stage. On stage there are two seconds, and two seconds is
enough to CHOOSE but nowhere near enough to DECIDE.

That is the whole method. Six pieces you can bend, and a decided-in-advance map from
request to piece. When the question lands, you are not composing an answer - you are
picking one up, and everyone in the room can hear the difference.""",
              r"""8. THE ARTEFACT, WALKED THROUGH PIECE BY PIECE.

No code here, so what follows is the structure taken apart - each part named, with what
it holds and what it decides.

--- THE STAR STRUCTURE, part by part ---

    SITUATION
        Holds: the context. Who, where, what was going on.
        Length: TWO SENTENCES. This is the part everyone over-writes.
        Decides: whether the interviewer can follow the rest. Nothing more. It is
        scaffolding, not content.

    TASK
        Holds: what YOU specifically were responsible for - not the team's goal, yours.
        Length: one sentence.
        Decides: whether the actions that follow are creditable to you. Skip this and
        your achievements sound like the group's.

    ACTION
        Holds: what you did, in order, in first person singular, including the reasoning
        behind the key decision.
        Length: roughly 60% of the whole story. This is the answer.
        Decides: everything. This is the part being scored. If you are describing what
        the team did rather than what you did, you are not answering the question.

    RESULT
        Holds: what happened, WITH A NUMBER.
        Length: two or three sentences.
        Decides: whether this was consequential. Without a figure it is an anecdote.

    REFLECTION (the unofficial fifth part)
        Holds: what you would do differently, specifically.
        Length: one or two sentences.
        Decides: whether you look like someone who learns. Asked nearly every time, so
        prepare it rather than improvising it.

--- THE SIX SHAPES, and what each one covers ---

    DELIVERY - you shipped something hard under a real constraint.
        Covers: Deliver Results, Ownership, prioritisation, "most challenging project",
        "tell me about something you built".
        Must contain: the constraint, and the trade-off you chose.

    FAILURE - you got something wrong and fixed the cause.
        Covers: failure, a mistake affecting others, Earn Trust, humility, receiving
        feedback.
        Must contain: your own decision that was wrong. Not someone else's.

    CONFLICT - you disagreed with someone and resolved it.
        Covers: difficult teammate, Have Backbone, disagreeing with a manager,
        collaboration under tension.
        Must contain: the other person's position stated fairly, and how it ended.

    AMBIGUITY - you moved without complete information.
        Covers: ambiguity, Bias for Action, Are Right A Lot, incomplete data, unclear
        requirements.
        Must contain: what you did NOT know, and why waiting was worse than acting.

    LEARNING - you taught yourself something hard, fast, because you needed it.
        Covers: Learn and Be Curious, new technology, being out of your depth.
        Must contain: how you learned it, not just that you did.

    HELPING - you made someone else more effective.
        Covers: collaboration, mentoring, Hire and Develop the Best, Googleyness.
        Must contain: the effect on THEM, measured if possible.

--- THE INDEX ---

    Holds: for each likely question, which story and which angle, plus the headline
    sentence you open with.
    Decides: your response time in the room. This is the artefact that converts
    preparation into performance, and it is the one almost nobody builds.

--- THE HEADLINE SENTENCE ---

    Holds: one sentence naming what the story is about, framed for THIS question.
    Decides: the first impression, and it buys you the two seconds you need. Compare:
        weak:   "So, um, in my final year project, there were four of us, and we were
                 building..."
        strong: "The clearest example is when I cut our project's scope by two thirds
                 four weeks in, to protect a fixed demo date."
    The second one tells the interviewer immediately that you understood the question
    and have a real answer.""",
              r"""9. ONE STORY, TOLD IN FULL - THEN RE-ANGLED THREE WAYS.

THE RAW MATERIAL (final-year capstone, four people, six weeks, fixed demo date):

    The team built a campus lost-and-found image search - upload a photo of something
    you lost, get back matching found items. Twelve item categories planned.
    At week four, the image indexing pipeline took NINE HOURS for a full re-index, so
    the team could test at most ONE change per day. Two weeks left.
    She proposed cutting from twelve categories to four - bags, phones, keys, bottles -
    which brought re-index time to FORTY MINUTES and allowed EIGHT experiments a day.
    One teammate objected strongly: twelve categories was what they had promised in the
    proposal.
    She made the case on iteration speed rather than on scope, and they agreed to ship
    four categories with a written plan for adding the rest.
    Demo delivered on time, 87% retrieval accuracy on the four categories. The
    alternative was twelve categories at an accuracy nobody would have had time to
    measure.

NOW THE SAME EVENTS, OPENED THREE DIFFERENT WAYS.

--- ANGLE A: "Tell me about your most challenging project." (DELIVER RESULTS) ---

    HEADLINE: "The hardest call I made was cutting our capstone's scope by two thirds
    four weeks in, to protect a fixed demo date."

    SITUATION (2 sentences): four-person capstone, six weeks, hard demo date. Lost-and-
    found image search, twelve categories planned.
    TASK: I owned the indexing pipeline.
    ACTION (the bulk): at week four I measured our actual iteration speed and found the
    full re-index took nine hours - one experiment per day, ten working days left, so
    at most ten more experiments total. I worked out what was driving it, established
    that category count was the dominant factor, and calculated that four categories
    would bring it to forty minutes. I proposed cutting to four.
    RESULT: forty minutes instead of nine hours, eight experiments a day instead of
    one, demo delivered on time at 87% accuracy on four categories.
    REFLECTION: I should have measured iteration speed in week one. The cut was the
    right call; needing it at week four was my planning failure.

    Emphasis: the constraint, the measurement, the trade-off, the number.

--- ANGLE B: "Tell me about a time you disagreed with a teammate." (HAVE BACKBONE) ---

    HEADLINE: "I pushed hard against a teammate who wanted to keep our full scope, and
    what changed his mind was reframing it from what we'd promised to how fast we could
    learn."

    SITUATION: same two sentences, briefer.
    TASK: I had proposed cutting twelve categories to four; one teammate objected
    strongly, on the grounds that twelve was what we had committed to in the proposal.
    ACTION (the bulk): I took his objection seriously - it was a real commitment and he
    was right that we had made it. But I thought we were comparing the wrong things. I
    showed him the arithmetic: at one experiment a day we had ten experiments left, and
    we had no measurement of accuracy on ANY category. At eight a day we had eighty. I
    proposed that we ship four categories properly and write up exactly how the other
    eight would be added, so the commitment became deferred rather than dropped. He
    agreed to that, and he wrote the extension plan.
    RESULT: same numbers, and - the part that matters for this angle - he stayed
    invested. He wrote the plan, and we presented the cut as a deliberate decision
    rather than a shortfall.
    REFLECTION: I opened by arguing for my conclusion instead of asking what he was
    optimising for. It cost us most of a day.

    Emphasis: the other person's position stated fairly, the reframing, and disagree-
    and-commit landing on both sides.

--- ANGLE C: "Tell me about a decision you made without enough information." (AMBIGUITY) ---

    HEADLINE: "I cut two thirds of our project's scope without knowing whether what was
    left would be enough for a convincing demo."

    SITUATION: same.
    TASK: decide at week four whether to keep scope or protect iteration speed.
    ACTION (the bulk): what I did NOT know was whether four categories would be
    persuasive to the panel, or whether 87% - or whatever we reached - would be good
    enough. Nobody could tell me. What I DID know was measurable: our iteration rate,
    and how many experiments remained at each scope. So I decided on the thing I could
    measure rather than the thing I could only guess at, on the reasoning that a
    measured 87% on four categories was defensible in a way that an unmeasured twelve
    never would be. I also set a checkpoint - if we were not above 80% by day eight, we
    would cut to two categories.
    RESULT: 87% on four categories, demo on time, checkpoint never triggered.
    REFLECTION: the checkpoint was the best part of the decision and I nearly did not
    set it. I now try to make every irreversible-feeling decision reversible by putting
    a measurable trigger on it.

    Emphasis: what was unknown, why acting beat waiting, and the safeguard.

WHAT THIS DEMONSTRATES: three genuinely different answers, to three genuinely different
questions, from ONE experience. Not evasion - the events really do contain all three
aspects, and the skill is choosing which to foreground. Six stories times three angles
is eighteen distinct answers, which covers the thirty questions comfortably once you
account for overlap.

AND THE INVERSION WORTH NOTICING: the SAME story is a strong answer or a weak one
depending entirely on the angle. Told in Angle A's form when asked about conflict, it
answers the wrong question and reads as though you did not listen - the disagreement is
never even mentioned. Choosing the angle is not presentation polish; it is the answer.""",
              r"""10. WHAT IT COSTS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT THE PREPARATION ACTUALLY COSTS:

  - Listing raw material: an hour, once.
  - Writing six stories in STAR: about an hour each, so six hours.
  - Building the index and headline sentences: two hours.
  - Rehearsing out loud, including re-angling and follow-ups: three or four sessions of
    an hour.
  Roughly twelve to fifteen hours in total, and it is the best-returning twelve hours in
  the whole interview process - because unlike DSA practice, it has a definite end. You
  finish it, and it stays finished.

WHEN TO DO IT: early, not the night before. The stories need to settle so you remember
them as experiences rather than as text. Write them three weeks out, rehearse in the
last week.

THE FOLLOW-UPS TO PREPARE FOR, per story, because these are the actual test:
  - "What did the other people think?"
  - "What would you do differently?"
  - "How did you know that was the right call?"
  - "What was the hardest part?"
  - "What did you get wrong?"
If you can answer all five fluently on all six stories, you are prepared. If you cannot,
you have memorised rather than remembered, and the room will find that out.

TWO PRACTICAL CONSTRAINTS PEOPLE MISS:

  1. AMAZON INTERVIEWERS COMPARE NOTES afterwards, and each round is assigned different
     leadership principles. Repeating a story across rounds is visible and reads as a
     thin candidate. Six is the minimum for four or five rounds with one in reserve -
     not a comfortable surplus.

  2. GOOGLE WEIGHTS COLLABORATION AND AMBIGUITY more heavily; AMAZON asks explicitly
     against named principles and expects you to answer against them. Same stories, and
     you should know which principle each angle is serving so you can name it when the
     question does.

THE #1 MISTAKE: preparing answers instead of preparing stories. Thirty rehearsed
paragraphs cannot be held under pressure, come out sounding recited, and collapse on the
first follow-up - because you practised producing text rather than remembering an
experience. Six well-built stories with an index beat thirty memorised answers, and take
less work.

RUNNER-UP: no numbers. A story without a figure is an anecdote, and interviewers
discount anecdotes heavily.

TAKEAWAY: there are six story shapes, not thirty questions - so build six experiences
you know cold, practise telling each one three different ways, and decide the
question-to-story map at home so that in the room you are choosing rather than
composing.""",
          ],
          pitfalls="Memorising word-for-word, which sounds robotic and collapses under a follow-up; six stories from the same project (you will run out and it looks thin); stories with no number; forgetting that Amazon interviewers compare notes, so reusing the identical story in four rounds is visible - vary them; no 'what I'd do differently' prepared, which is the most common follow-up in the set.",
          followups="'Do you have another example?' - the reason you need more than one story per shape. 'What did your team think?' - prepare the other people's perspective for each story, since that is where thin stories fall apart."),

        Q("behavioral", "What questions should you ask the interviewer?",
          "Every interview ends here, it is scored, and 'I have no questions' is a genuinely bad answer - it reads as no curiosity, which at Google is a named rubric item. WHAT THEY ARE TESTING: whether you are evaluating them too, and what you actually care about. Note also that this is often your last few minutes with the person writing your feedback, so it is worth using well. THE FOUR CATEGORIES worth drawing from, one or two each: THE WORK - 'what does a typical week look like for a new grad on this team?', 'what is the project I'd most likely start on?', 'how much of the work is new development versus maintaining what exists?'. THE TEAM AND YOU - 'how does the team decide what to work on?', 'what does the onboarding look like?', 'how do new engineers get feedback in the first six months?'. THEIR EXPERIENCE - 'what surprised you most in your first year here?', 'what is the hardest problem the team is working on right now?' - people enjoy answering these and you learn a lot. THE HONEST ONE, which is the most useful and rarely asked: 'what is the most frustrating part of working on this team?' A candid answer tells you more than everything else combined, and a non-answer tells you something too. WHAT NOT TO ASK: anything answered on the careers page (it shows you did not look), compensation or holidays with an engineer rather than the recruiter, 'how did I do?', or a question so obviously engineered to impress that it is transparent. PREPARE ABOUT SIX, because two will be answered during the interview, and adapt at least one to something the interviewer actually said - that is the part that shows you were listening.",
          ["behavioral", "questions", "interview-strategy", "googleyness", "curiosity"],
          difficulty="Easy",
          frequency="Every interview ends with this, and it is part of the written feedback.",
          mnemonic="Prepare six, expect two to be answered already, and adapt one to something they SAID. Best single question: 'what's the most frustrating part of working here?' Never: nothing, salary-with-the-engineer, or anything on the careers page.",
          example="A strong close: 'You mentioned earlier that the team is moving the feature pipeline off the nightly batch job. What is driving that - latency, cost, or correctness? And what does that mean for someone joining in the next six months: would a new grad be working on the migration, or on what sits on top of it?' It proves you listened, it is technically specific, and the answer tells you exactly what your first year would look like. Contrast with 'What is the company culture like?', which they will answer generically because it is a generic question.",
          pitfalls="Having no questions; asking something the job description answers; asking about compensation, promotion timelines or holidays with the engineering interviewer rather than the recruiter; asking 'how did I do?', which puts them in an awkward position; asking a question you clearly do not care about.",
          followups="If they answer everything during the interview, say so honestly and pivot: 'you covered my main ones - can I ask instead what you'd want someone joining to be good at on day one?' That is a genuine question and it never fails."),
    ]

    return entries

-- ============================================================
--  DailyPlanner — AI SDE PREP TRACK for the student account
--
--  WHY THIS EXISTS. interview_prep seeds every new user with the OWNER's
--  executive TPM plan: role "Senior Director, Technical Program
--  Management", and topics like "Recovering a failing program",
--  "Building & scaling a team/org", "Managing up / disagreeing with an
--  exec". Stories to rehearse included "Delivered a company-scale
--  program".
--
--  For the final-year student account that content is not merely wrong,
--  it is discouraging: she has none of those experiences and cannot
--  acquire them before a new-grad loop. Her prep is the AI SDE bank at
--  /ai-sde, so her coach must be pointed at the same target.
--
--  NOTHING OF HERS IS LOST. Every one of her 28 topic confidences is 0
--  and none of her 8 stories is marked rehearsed — she had entered
--  nothing, because there was nothing here worth entering. Verified
--  before writing this.
--
--  THE TOPIC LIST IS DERIVED, NOT INVENTED. Each row is one subtopic
--  from ai_sde_tags.py that carries two or more MUST-KNOW entries, so
--  the study plan and the bank cannot drift apart. The count in each
--  title is how many must-know topics sit behind it.
--
--  Idempotent: keyed on the account's email, and re-running replaces the
--  seeded rows rather than duplicating them. Soft-deletes the old TPM
--  rows (never a hard delete) so they can be recovered if wanted.
-- ============================================================

do $$
declare
  uid uuid;
begin
  select id into uid from users where email = 'venghateshshreya@gmail.com';
  if uid is null then
    raise notice 'student account not found — nothing to do';
    return;
  end if;

  -- Point the plan at her actual target: 15 Nov 2026, 92 days out.
  --
  -- The daily goal is 240 minutes (4 hours), which is what she says she can
  -- actually give it. That is a stated capacity, not a derived number — but
  -- it is worth recording what it buys, because the earlier values did not
  -- buy enough. The bank's own prep_minutes put P0 at 92h35m and P0+P1 at
  -- 284h25m. Over the 92 days to 15 Nov:
  --      45 min/day =  69h  -> 75% of P0. Does not even finish the
  --                            must-know band before the interview.
  --      60 min/day =  92h  -> P0 almost exactly, nothing beyond it.
  --      90 min/day = 138h  -> all of P0 plus about a quarter of P1.
  --     185 min/day = 284h  -> P0+P1 complete, with nothing spare.
  --     240 min/day = 368h  -> P0+P1 complete by roughly 20 October, then
  --                            83h left over, about half of P2.
  -- So the goal stops being a stretch and becomes a schedule: the binding
  -- constraint is no longer hours available, it is whether the 4 hours
  -- actually happen. The budget line on /goal-planner reads feasible at this
  -- number, and it should start reading short again the moment she slips —
  -- that is the signal to watch, not the total.
  update interview_prep
     set role_title         = 'AI/ML SDE — New Grad (Amazon / Google)',
         target_date        = date '2026-11-15',
         daily_goal_minutes = 240,
         updated_at         = now()
   where user_id = uid;

  -- Already applied? Then stop, rather than churn.
  --
  -- The first version soft-deleted and re-inserted unconditionally, so every
  -- re-run left another 48 dead rows behind (a genuine double-apply during
  -- rollout took the soft-deleted count from 28 to 76). The live state was
  -- correct both times, but the clutter grows without bound. A marker row is
  -- enough to make the whole block a no-op the second time.
  if exists (select 1 from interview_topics
              where user_id = uid and deleted_at is null
                and title like 'DSA — %must-know)') then
    raise notice 'AI SDE prep track already applied for % — nothing to do', uid;
    return;
  end if;

  -- Retire the inherited TPM rows. Soft delete, per house rule.
  update interview_topics  set deleted_at = now()
   where user_id = uid and deleted_at is null;
  update interview_stories set deleted_at = now()
   where user_id = uid and deleted_at is null;

  -- ── Study areas, derived from the Must-Know tags ──
  insert into interview_topics (user_id, category, title, position)
  select uid, t.category, t.title, t.position
    from (values
      ('dsa', 'DSA — Arrays Hashing (12 must-know)', 0),
      ('dsa', 'DSA — Graphs (8 must-know)', 1),
      ('dsa', 'DSA — DP (8 must-know)', 2),
      ('dsa', 'DSA — Trees (7 must-know)', 3),
      ('dsa', 'DSA — Linked List (6 must-know)', 4),
      ('dsa', 'DSA — Heap (4 must-know)', 5),
      ('dsa', 'DSA — Stack (4 must-know)', 6),
      ('dsa', 'DSA — Two Pointers (3 must-know)', 7),
      ('dsa', 'DSA — Backtracking (3 must-know)', 8),
      ('dsa', 'DSA — Sliding Window (2 must-know)', 9),
      ('dsa', 'DSA — Binary Search (2 must-know)', 10),
      ('dsa', 'DSA — Greedy (2 must-know)', 11),
      ('dsa', 'DSA — Intervals (2 must-know)', 12),
      ('cs_fundamentals', 'Core-CS — OOP (12 must-know)', 13),
      ('cs_fundamentals', 'Core-CS — DBMS (9 must-know)', 14),
      ('cs_fundamentals', 'Core-CS — OS (8 must-know)', 15),
      ('cs_fundamentals', 'Core-CS — Networking (5 must-know)', 16),
      ('cs_fundamentals', 'Python — Language (2 must-know)', 17),
      ('ml', 'Classical-ML — Evaluation (25 must-know)', 18),
      ('ml', 'Classical-ML — Theory (16 must-know)', 19),
      ('ml', 'Classical-ML — Supervised (10 must-know)', 20),
      ('ml', 'Classical-ML — Trees Ensembles (7 must-know)', 21),
      ('ml', 'Classical-ML — Feature Engineering (6 must-know)', 22),
      ('ml', 'Classical-ML — Unsupervised (3 must-know)', 23),
      ('ml', 'Deep-Learning — Architectures (14 must-know)', 24),
      ('ml', 'Deep-Learning — Training (6 must-know)', 25),
      ('ml', 'Deep-Learning — Optimization (5 must-know)', 26),
      ('ml', 'Deep-Learning — Regularization (3 must-know)', 27),
      ('ml', 'Math-Stats — Linear Algebra (5 must-know)', 28),
      ('ml', 'Math-Stats — Calculus (2 must-know)', 29),
      ('ml', 'Math-Stats — Statistics (2 must-know)', 30),
      ('ml', 'Math-Stats — Probability (2 must-know)', 31),
      ('ai_llm', 'NLP-LLM — Transformers (16 must-know)', 32),
      ('ai_llm', 'NLP-LLM — RAG (6 must-know)', 33),
      ('ai_llm', 'NLP-LLM — Fine Tuning (5 must-know)', 34),
      ('ai_llm', 'NLP-LLM — Prompting (5 must-know)', 35),
      ('ai_llm', 'NLP-LLM — Inference (3 must-know)', 36),
      ('ai_llm', 'NLP-LLM — Evaluation (3 must-know)', 37),
      ('ai_llm', 'NLP-LLM — Embeddings (2 must-know)', 38),
      ('ai_llm', 'NLP-LLM — Agents (2 must-know)', 39),
      ('system_design', 'System-Design — ML System Design (4 must-know)', 40),
      ('system_design', 'System-Design — Fundamentals (2 must-know)', 41),
      ('system_design', 'System-Design — Scalability (2 must-know)', 42),
      ('system_design', 'MLOps — Monitoring (2 must-know)', 43),
      ('behavioral', 'Behavioral — Story Bank (9 must-know)', 44),
      ('behavioral', 'Behavioral — Amazon LP (5 must-know)', 45),
      ('behavioral', 'Behavioral — Process (3 must-know)', 46),
      ('behavioral', 'Behavioral — Googleyness (2 must-know)', 47)
    ) as t(category, title, position);

  -- ── Stories a final-year student can actually tell ──
  -- Drawn from the behavioural entries already written for her in the AI
  -- SDE bank, which were authored for a student rather than an executive.
  insert into interview_stories (user_id, title, competency, position)
  select uid, s.title, s.competency, s.position
    from (values
      ('Your most challenging technical project',        'Depth',        0),
      ('A group project where someone was not pulling their weight', 'Collaboration', 1),
      ('Learning something hard and unfamiliar, fast',   'Learn & Be Curious', 2),
      ('A bug or failure that was yours, and what you changed', 'Ownership', 3),
      ('Dealing with unclear or shifting requirements',  'Ambiguity',    4),
      ('Difficult feedback you received and acted on',   'Earn Trust',   5),
      ('Helping a teammate succeed',                     'Googleyness',  6),
      ('Choosing the right solution over the quick hack','Highest Standards', 7),
      ('Acting with incomplete information',             'Bias for Action', 8),
      ('Why software engineering, and why AI/ML',        'Motivation',   9)
    ) as s(title, competency, position);

  -- ── The same target as a goal, so it counts down ──
  -- Gives her the /goal-planner hero: days:hrs:mins to the interview, pace
  -- against the plan, and the budget verdict computed from the numbers
  -- above. effort_minutes is P0+P1 from the bank, so the page can say
  -- honestly whether the commitment covers the work.
  if not exists (select 1 from objectives
                  where user_id = uid and title = 'Crack the AI SDE interview'
                    and not is_deleted) then
    insert into objectives (user_id, title, description, time_horizon, status,
                            start_date, target_date, target_at,
                            daily_commit_minutes, effort_minutes,
                            is_primary, flash_enabled)
    values (uid, 'Crack the AI SDE interview',
            'Amazon / Google new-grad AI/ML SDE loop. Study bank at /ai-sde.',
            'quarterly', 'active',
            current_date, date '2026-11-15',
            (date '2026-11-15' + time '09:00:00') at time zone 'Asia/Kolkata',
            240, 17065, true, true);
  end if;

  raise notice 'AI SDE prep track seeded for %', uid;
end $$;

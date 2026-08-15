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

  -- Point the plan at her actual target. Adjust target_date once the
  -- interview season dates are known; 45 min/day is kept.
  update interview_prep
     set role_title = 'AI/ML SDE — New Grad (Amazon / Google)',
         updated_at = now()
   where user_id = uid;

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

  raise notice 'AI SDE prep track seeded for %', uid;
end $$;

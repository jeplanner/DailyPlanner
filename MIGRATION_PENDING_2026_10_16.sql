-- ================================================================
--  DailyPlanner — PENDING MIGRATIONS, consolidated 2026-10-16
--
--  Run this whole file once in the Supabase SQL editor.
--
--  It is three migrations concatenated in dependency-free order.
--  EVERY STATEMENT IS IDEMPOTENT — running it twice changes nothing,
--  so it is safe even if you have already run some of them.
--
--    1. MIGRATION_PREP_PROGRESS.sql      prep_progress.quiz_best_pct
--                                        (the table already exists; only
--                                        the last column is missing)
--    2. MIGRATION_TASK_COMPLETED_AT.sql  project_tasks.completed_at,
--                                        its trigger, backfill and index
--    3. MIGRATION_PREP_THOUGHTS.sql      Random thoughts: the spaced-
--                                        repetition review columns and
--                                        prep_thoughts.notes (your notes
--                                        on each question) - only the two
--                                        newest sections of that file
--
--  NOTE: Supabase's SQL editor runs a file as ONE transaction, so if
--  any statement fails NOTHING in the file takes effect. If you get an
--  error, fix that statement and re-run the whole file — you will not
--  have half-applied it.
-- ================================================================


-- ################################################################
-- ##  1 of 3  —  PREP PROGRESS (quiz scores on the deep dives)
-- ################################################################
-- ============================================================
--  PREP PROGRESS — "rehearsed" ticks and mock-interview scores for the
--  Interview Prep hub (case rounds, behavioural bank, system design).
--
--  Until now those ticks lived in each browser's localStorage, keyed by
--  the entry's POSITION in the bank. So ticks on the phone never reached
--  the laptop, and adding one case shifted every position after it.
--  Rows here are keyed by TITLE; the page migrates its old ticks across
--  automatically the first time it loads after this runs.
--
--  Safe to run more than once. Run in the Supabase SQL editor.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists prep_progress (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null,
  bank             text not null,          -- 'tpm' | 'behavioral' | 'sysdesign' | 'sddeep'
  entry_title      text not null,
  done             boolean not null default false,
  done_at          timestamptz,
  mock_attempts    int not null default 0,
  mock_last_score  smallint check (mock_last_score between 1 and 4),
  mock_best_score  smallint check (mock_best_score between 1 and 4),
  mock_last_at     timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- The upsert target: the app posts with ?on_conflict=user_id,bank,entry_title.
create unique index if not exists prep_progress_user_bank_title
  on prep_progress (user_id, bank, entry_title);

create index if not exists prep_progress_user_done
  on prep_progress (user_id, bank) where done;

-- NO ROW-LEVEL SECURITY HERE, ON PURPOSE (2026-10-17). The live server's
-- SUPABASE_KEY is the PUBLIC key, and RLS with no policies hides every row
-- from it and refuses every write: re-running this file emptied Random
-- thoughts that day. RLS is switched on in ONE place, MIGRATION_ENABLE_RLS.sql,
-- and only after SUPABASE_KEY on Render is the secret key.

-- Best quiz score (0-100) for the system design deep dives; 80%+ marks the
-- design as studied.
alter table prep_progress add column if not exists quiz_best_pct smallint
  check (quiz_best_pct between 0 and 100);


-- ################################################################
-- ##  2 of 3  —  WHEN WAS A TASK FINISHED (sprint burndown)
-- ################################################################
-- ============================================================
--  DailyPlanner — WHEN WAS A TASK FINISHED?
--
--  Added 2026-10-11 for the per-sprint burndown. project_tasks had no
--  completion time; the sprint chart used updated_at as a stand-in, which
--  moves whenever a finished task is edited (a note, a date), so a task
--  done on Monday could show up as done on Friday.
--
--  completed_at is maintained by a trigger rather than by the app, because
--  a task becomes "done" from at least six places (the task sheet, the
--  matrix, autosave, bulk update, the v2 complete button, status chips).
--  One trigger covers all of them, including any added later:
--    - status changes TO 'done'   → completed_at = now()
--    - status changes AWAY from it → completed_at = null
--    - anything else              → left alone
--
--  The app works before this runs: the burndown falls back to updated_at.
--
--  Safe to re-run.
-- ============================================================

alter table if exists project_tasks
    add column if not exists completed_at timestamptz;

create or replace function project_tasks_stamp_completed_at()
returns trigger
language plpgsql
as $$
begin
    if new.status = 'done' and (tg_op = 'INSERT' or old.status is distinct from 'done') then
        new.completed_at := coalesce(new.completed_at, now());
    elsif new.status is distinct from 'done' then
        new.completed_at := null;
    end if;
    return new;
end;
$$;

drop trigger if exists trg_project_tasks_completed_at on project_tasks;
create trigger trg_project_tasks_completed_at
    before insert or update of status on project_tasks
    for each row execute function project_tasks_stamp_completed_at();

-- Backfill: tasks already done get their last-updated time — the best
-- record there is of when they were finished. The live project_tasks has
-- no updated_at column (it is in MIGRATION_ALL_TABLES.sql but was never
-- applied), and naming a missing column fails the whole file, so use it
-- only where it exists and fall back to created_at.
do $$
begin
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'project_tasks'
                and column_name = 'updated_at') then
    execute 'update project_tasks set completed_at = coalesce(updated_at, created_at)
              where status = ''done'' and completed_at is null';
  else
    update project_tasks set completed_at = created_at
     where status = 'done' and completed_at is null;
  end if;
end $$;

create index if not exists ix_project_tasks_sprint_completed
    on project_tasks (sprint_id, completed_at)
    where sprint_id is not null;


-- ################################################################
-- ##  3 of 3  —  RANDOM THOUGHTS: REVIEW SCHEDULE + YOUR NOTES
-- ################################################################
-- ── Spaced repetition (added later; safe to re-run) ─────────────────
-- Marking a question "studied" schedules a review tomorrow; each review
-- (Forgot / Hard / Got it / Easy) moves it 1, 3, 7, 14, 30, 60 or 120 days out.
alter table prep_thoughts add column if not exists review_stage     integer not null default 0;
alter table prep_thoughts add column if not exists next_review_at   timestamptz;
alter table prep_thoughts add column if not exists last_reviewed_at timestamptz;
alter table prep_thoughts add column if not exists review_count     integer not null default 0;
create index if not exists prep_thoughts_due
  on prep_thoughts (user_id, next_review_at) where deleted_at is null and next_review_at is not null;
-- Questions you had already marked understood join the cycle: first review tomorrow.
update prep_thoughts set next_review_at = now() + interval '1 day'
  where understood and next_review_at is null and deleted_at is null and parent_id is null;

-- ── Your notes (added 2026-10-16; safe to re-run) ───────────────────
-- Your own notes against a question or follow-up, newest last:
--   [{id, text, created_at, updated_at, deleted_at}]
-- Deleting a note sets its deleted_at; the note itself is kept (soft
-- delete, like every other row in the app). A refreshed shipped answer
-- or a rewrite only touches `answer`, so notes survive both.
alter table prep_thoughts add column if not exists notes jsonb not null default '[]'::jsonb;

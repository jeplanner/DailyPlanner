-- ============================================================
--  DailyPlanner — AI SDE PROGRESS (server-side)
--
--  Until now every trace of AI SDE study lived in the browser's
--  localStorage: which topics were ticked, the Pomodoro minutes per
--  question, the Sadhana XP. Three consequences, all bad:
--
--    1. Progress did not follow the user between phone and laptop —
--       two devices meant two unrelated progress bars.
--    2. Clearing site data wiped months of work with no way back.
--    3. Nothing server-side could answer "is this being used at all",
--       so the effort readouts could never become real reporting.
--
--  KEYED BY TITLE, NOT BY THE ENTRY'S ID. The API hands out ids as
--  "ai0", "ai1", ... derived from the entry's INDEX in ai_sde_bank.py.
--  That index shifts every time an entry is added, removed or deduped —
--  and the bank has grown from ~500 to 1,120 entries and had 57
--  duplicates folded out along the way. Any progress stored against
--  those ids is therefore already pointing at the wrong topics. Titles
--  are the stable key: they are what the _EX_* example dicts and
--  ai_sde_tags.py already key on, and a title change is rare and
--  deliberate. The trade-off is that renaming a topic loses its
--  progress, which is the right way round.
--
--  minutes_focused holds the Pomodoro total for the topic so effort
--  survives a device change; studied_at is null until the topic is
--  ticked, so it doubles as "when did this land".
--
--  REVIEW SCHEDULE (added before this migration was ever run, so it
--  is one migration and not two). Ticking a topic "studied" says it
--  was read once; it says nothing about whether it can still be
--  recalled a fortnight later, which is the only thing an interview
--  measures. The recall quiz under each card grades itself, and these
--  columns hold the resulting Leitner ladder: review_streak counts
--  consecutive hits, review_due is when the topic comes back, and the
--  attempt counters are what would let a coach say "you have the
--  algorithm but keep missing the complexity".
--
--  review_due is nullable and null means "never drilled" — distinct
--  from a due date in the past, which means "overdue". The page reads
--  that difference, so do not default it to now().
--
--  Safe to re-run.
-- ============================================================

create table if not exists ai_sde_progress (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null,
  entry_title     text not null,
  studied         boolean not null default false,
  studied_at      timestamptz,
  minutes_focused int not null default 0,
  -- Recall schedule; see the header note.
  review_due      timestamptz,
  review_last     timestamptz,
  review_streak   int not null default 0,
  quiz_attempts   int not null default 0,
  quiz_correct    int not null default 0,
  updated_at      timestamptz not null default now(),
  created_at      timestamptz not null default now(),
  is_deleted      boolean not null default false,
  deleted_at      timestamptz
);

-- One row per topic per user. The upsert in the API relies on this.
create unique index if not exists ai_sde_progress_user_title
  on ai_sde_progress (user_id, entry_title);

-- The page loads every row for the user on open, so index the lookup.
create index if not exists ai_sde_progress_user_idx
  on ai_sde_progress (user_id)
  where not is_deleted;

-- Added after the table may already exist, so each is guarded.
alter table ai_sde_progress add column if not exists review_due    timestamptz;
alter table ai_sde_progress add column if not exists review_last   timestamptz;
alter table ai_sde_progress add column if not exists review_streak int not null default 0;
alter table ai_sde_progress add column if not exists quiz_attempts int not null default 0;
alter table ai_sde_progress add column if not exists quiz_correct  int not null default 0;

-- "What is due today" is the query the review queue runs on every page
-- load, so it gets its own index. Partial, because rows that have never
-- been drilled have a null review_due and are not part of the queue.
create index if not exists ai_sde_progress_due_idx
  on ai_sde_progress (user_id, review_due)
  where review_due is not null and not is_deleted;

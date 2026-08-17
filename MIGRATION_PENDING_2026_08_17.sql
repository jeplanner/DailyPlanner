-- ================================================================
--  DailyPlanner — PENDING MIGRATIONS, consolidated 2026-08-17
--
--  Run this whole file once in the Supabase SQL editor.
--
--  It is three migrations concatenated in dependency-free order.
--  EVERY STATEMENT IS IDEMPOTENT — running it twice changes nothing,
--  so it is safe even if you have already run some of them.
--
--    1. MIGRATION_AISDEPREP.sql       prep projects + project_tasks columns
--    2. MIGRATION_AI_SDE_PROGRESS.sql study progress + the recall schedule
--    3. MIGRATION_DAY_BOARD_PIN.sql   pinned day-board notification
--
--  NOTE: Supabase's SQL editor runs a file as ONE transaction, so if
--  any statement fails NOTHING in the file takes effect. If you get an
--  error, fix that statement and re-run the whole file — you will not
--  have half-applied it.
-- ================================================================


-- ################################################################
-- ##  1 of 3  —  PREP PROJECTS (AISDEPrep / JavaPrep / InterviewPrep)
-- ################################################################
--  DailyPlanner — prep projects (study topics onto the calendar)
--
--  Backs the "Plan" button on the three study-bank pages — /ai-sde,
--  /java and /interview-prep. Pick a topic, pick a day, and it lands in
--  three places at once —
--
--  Each page has its OWN project (AISDEPrep / JavaPrep / InterviewPrep)
--  so a Java topic never turns up in the AI/SDE syllabus. The file is
--  named for the first of them because it has already been run under
--  that name; re-running it adds the other two and nothing else.
--
--    * project_tasks  → the AISDEPrep project, so the whole syllabus
--                       has one home and one progress view;
--    * daily_events   → the calendar grid for that day;
--    * quick_bucket   → the one-liner list, so it is in front of her
--                       without opening the calendar at all.
--
--  No NEW schema is invented here — every column the feature writes is
--  one MIGRATION_ALL_TABLES.sql already declares. What this file does:
--
--    1. the starter row — an AISDEPrep project for each existing user,
--       so the project is there before the first click rather than
--       appearing out of nowhere on it;
--    2. the guard index — at most one active AISDEPrep per user, so a
--       double-tap on a slow connection cannot end up creating two
--       projects with the same name;
--    3. catches up any project_tasks column an older install missed.
--       This is not hypothetical: the first run of this file failed with
--         ERROR: 42703: column "is_deleted" does not exist
--       because that install predates the line in ALL_TABLES that adds
--       it. Every `add column if not exists` below is a no-op on an
--       install that already has the column.
--
--  The app also creates the project lazily (routes/interview_prep.py,
--  _ensure_ai_sde_project) so a new user, or an environment where this
--  file was never run, still works. Running it just means the project
--  is already sitting in /projects when she goes looking.
--
--  Safe to re-run.
-- ============================================================

-- ── 1. One active project per user per prep bank ────────────────────
-- Three study-bank pages schedule onto a day now — /ai-sde, /java and
-- /interview-prep — and each drops its topics into its own project so a
-- Java topic never lands in the AI/SDE syllabus. One index per name.
--
-- Wrapped rather than bare: if some environment already has two rows by
-- the same name, that index cannot be built, and that must not take the
-- rest of this file down with it. The lazy get-or-create in the app
-- tolerates any of them being absent — it selects before it inserts — so
-- a warning here is a warning, not a failure.
do $$
declare
  p text;
begin
  foreach p in array array['AISDEPrep', 'JavaPrep', 'InterviewPrep']
  loop
    begin
      execute format(
        'create unique index if not exists projects_one_%s_per_user '
        'on projects (user_id) where name = %L and is_archived = false',
        lower(p), p);
    exception when unique_violation then
      raise notice '% index not created: a user already has more than one active % project. De-duplicate them and re-run.', p, p;
    end;
  end loop;
end $$;

-- ── 2. Seed the projects for everyone who already has projects ──────
-- Idempotent: the existence check means a re-run inserts nothing, which
-- is what lets this file grow a bank without disturbing the ones already
-- seeded. Note that this deliberately does NOT set is_default — that
-- flag is the Inbox slot (MIGRATION_DEFAULT_PROJECT.sql), one per user,
-- and these are normal projects that happen to have known names.
do $$
declare
  u text;
  b record;
  seeded int := 0;
begin
  for b in
    select * from (values
      ('AISDEPrep',
       'AI/SDE interview prep. Topics scheduled from /ai-sde land here.'),
      ('JavaPrep',
       'Java core interview prep. Topics scheduled from /java land here.'),
      ('InterviewPrep',
       'Behavioural / TPM interview prep. Questions scheduled from /interview-prep land here.')
    ) as t(name, descr)
  loop
    for u in
      select distinct user_id from projects where user_id is not null
    loop
      if not exists (
        select 1 from projects
         where user_id = u and name = b.name and is_archived = false
      ) then
        insert into projects (user_id, name, description, is_archived)
        values (u, b.name, b.descr, false);
        seeded := seeded + 1;
      end if;
    end loop;
  end loop;
  raise notice 'prep projects seeded: % row(s)', seeded;
end $$;

-- ── 3. Columns an older install may be missing ──────────────────────
-- All four are declared in MIGRATION_ALL_TABLES.sql; an install older
-- than those lines never got them. is_deleted is the one that actually
-- bit (the index below and the scheduler's "is it already on this day?"
-- lookup both filter on it), and plan_date / start_time are what put the
-- task on a day at all — so they are caught here too rather than waiting
-- to fail on the first tap.
alter table project_tasks
  add column if not exists is_deleted boolean default false,
  add column if not exists deleted_at timestamptz,
  add column if not exists plan_date  date,
  add column if not exists start_time text;

-- Backfill, so the partial index below actually covers the existing rows
-- rather than silently skipping every one where the new column is NULL.
update project_tasks set is_deleted = false where is_deleted is null;

-- ── 4. Read paths this feature leans on ─────────────────────────────
-- The scheduler checks "is this topic already on this day?" before it
-- inserts, so the same tap twice is a no-op instead of a duplicate.
-- That check is (project_id, plan_date) on project_tasks.
create index if not exists project_tasks_project_plan_date_idx
  on project_tasks (project_id, plan_date)
  where is_deleted = false;


-- ################################################################
-- ##  2 of 3  —  AI SDE PROGRESS + RECALL SCHEDULE
-- ################################################################
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


-- ################################################################
-- ##  3 of 3  —  DAY BOARD PINNED NOTIFICATION
-- ################################################################
--  DailyPlanner — Day Board pinned notification
--
--  One row per user recording whether today's Day Board summary
--  should be kept pinned in the notification shade, and the state
--  the background scheduler needs to refresh it WITHOUT spamming.
--
--  WHY THERE IS A SIGNATURE COLUMN, AND WHY IT MATTERS.
--  The obvious design is "re-send every 15 minutes". That pushes an
--  identical notification most of the time — the day does not change
--  every quarter hour — and every one of those costs battery and push
--  quota for nothing. Instead the scheduler hashes the summary TEXT it
--  is about to send and compares it with the last one. It sends when
--  the CONTENT CHANGES (an event starts, a task is ticked) and
--  otherwise stays silent. `last_signature` is what makes that
--  comparison possible across processes and restarts.
--
--  `last_sent_at` is a THROTTLE FLOOR, not a timer: even when the
--  content changes it will not re-send more often than
--  min_interval_minutes, so a burst of edits cannot produce a burst of
--  notifications.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists day_board_pins (
    user_id              text primary key,

    -- The toggle. False rather than a deleted row, so turning it off
    -- and on again keeps the user's window and cadence.
    is_active            boolean     not null default false,

    -- Local hours (0-23) between which the pin refreshes. Outside this
    -- window the scheduler leaves it alone: a summary that updates at
    -- 3am is a notification that wakes you to say nothing.
    start_hour           smallint    not null default 7,
    end_hour             smallint    not null default 22,

    -- Throttle floor in minutes. Content-triggered sends still respect
    -- this, so ticking five checklist items in a row is one refresh.
    min_interval_minutes smallint    not null default 10,

    -- What the scheduler last actually sent, and when. The signature is
    -- a hash of the title+body, so "has anything the user would SEE
    -- changed?" is one string comparison.
    last_signature       text,
    last_sent_at         timestamptz,

    -- The date the current pin belongs to. The scheduler forces a send
    -- when this rolls over, so the first refresh of a new morning always
    -- lands even if the text happens to match yesterday's.
    pinned_date          date,

    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

-- The scheduler's hot path is "every active pin", once a minute. Without
-- this it is a full scan of the table on every tick.
create index if not exists day_board_pins_active_idx
    on day_board_pins (is_active)
    where is_active;

-- Guard rails on the window, so a bad client cannot store something the
-- scheduler would then have to defend against on every tick.
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'day_board_pins_hours_ck'
    ) then
        alter table day_board_pins
            add constraint day_board_pins_hours_ck
            check (start_hour between 0 and 23
                   and end_hour between 0 and 23
                   and min_interval_minutes between 1 and 240);
    end if;
end $$;

-- Keep updated_at honest without the application having to remember.
create or replace function day_board_pins_touch()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists day_board_pins_touch_trg on day_board_pins;
create trigger day_board_pins_touch_trg
    before update on day_board_pins
    for each row execute function day_board_pins_touch();


-- ================================================================
--  DONE. Quick verification queries — run these after the file above.
-- ================================================================
-- select name, count(*) from projects
--  where name in ('AISDEPrep','JavaPrep','InterviewPrep') group by name;
--
-- select column_name from information_schema.columns
--  where table_name = 'project_tasks'
--    and column_name in ('is_deleted','deleted_at','plan_date','start_time');
--
-- select column_name from information_schema.columns
--  where table_name = 'ai_sde_progress'
--    and column_name in ('review_due','review_last','review_streak',
--                        'quiz_attempts','quiz_correct');
--
-- select to_regclass('day_board_pins');

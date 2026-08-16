-- ============================================================
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

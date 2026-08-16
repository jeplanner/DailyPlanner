-- ============================================================
--  DailyPlanner — AISDEPrep project (AI/SDE topics onto the calendar)
--
--  Backs the "Schedule" button on /ai-sde: pick a topic, pick a day,
--  and it lands in three places at once —
--
--    * project_tasks  → the AISDEPrep project, so the whole syllabus
--                       has one home and one progress view;
--    * daily_events   → the calendar grid for that day;
--    * quick_bucket   → the one-liner list, so it is in front of her
--                       without opening the calendar at all.
--
--  NO SCHEMA CHANGE IS REQUIRED. Every column the feature writes
--  (project_tasks.plan_date / start_time / notes, daily_events.*,
--  quick_bucket.*) already exists. This file exists for two reasons:
--
--    1. the starter row — an AISDEPrep project for each existing user,
--       so the project is there before the first click rather than
--       appearing out of nowhere on it;
--    2. the guard index — at most one active AISDEPrep per user, so a
--       double-tap on a slow connection cannot end up creating two
--       projects with the same name.
--
--  The app also creates the project lazily (routes/interview_prep.py,
--  _ensure_ai_sde_project) so a new user, or an environment where this
--  file was never run, still works. Running it just means the project
--  is already sitting in /projects when she goes looking.
--
--  Safe to re-run.
-- ============================================================

-- ── 1. One active AISDEPrep per user ────────────────────────────────
-- Wrapped rather than bare: if some environment already has two rows by
-- the same name, the index cannot be built, and that must not take the
-- rest of this file down with it. The lazy get-or-create in the app
-- tolerates the index being absent — it selects before it inserts — so
-- a warning here is a warning, not a failure.
do $$
begin
  begin
    create unique index if not exists projects_one_aisdeprep_per_user
      on projects (user_id)
      where name = 'AISDEPrep' and is_archived = false;
  exception when unique_violation then
    raise notice 'projects_one_aisdeprep_per_user not created: a user already has more than one active AISDEPrep project. De-duplicate them and re-run.';
  end;
end $$;

-- ── 2. Seed the project for everyone who already has projects ───────
-- Idempotent: the existence check means a re-run inserts nothing. Note
-- that this deliberately does NOT set is_default — that flag is the
-- Inbox slot (MIGRATION_DEFAULT_PROJECT.sql), one per user, and
-- AISDEPrep is a normal project that happens to have a known name.
do $$
declare
  u text;
  seeded int := 0;
begin
  for u in
    select distinct user_id from projects where user_id is not null
  loop
    if not exists (
      select 1 from projects
       where user_id = u and name = 'AISDEPrep' and is_archived = false
    ) then
      insert into projects (user_id, name, description, is_archived)
      values (
        u,
        'AISDEPrep',
        'AI/SDE interview prep. Topics scheduled onto a day from the /ai-sde page land here.',
        false
      );
      seeded := seeded + 1;
    end if;
  end loop;
  raise notice 'AISDEPrep seeded for % user(s)', seeded;
end $$;

-- ── 3. Read paths this feature leans on ─────────────────────────────
-- The scheduler checks "is this topic already on this day?" before it
-- inserts, so the same tap twice is a no-op instead of a duplicate.
-- That check is (project_id, plan_date) on project_tasks.
create index if not exists project_tasks_project_plan_date_idx
  on project_tasks (project_id, plan_date)
  where is_deleted = false;

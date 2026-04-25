-- ============================================================
--  DailyPlanner — POMODORO + PAUSE for task time tracking
--
--  Extends task_time_logs (created in MIGRATION_PHASE3.sql) so the
--  same table can back both:
--    • free-running stopwatches (existing rows; mode='stopwatch')
--    • fixed-target Pomodoros that can be paused/resumed
--
--  Effective duration on stop:
--      duration_seconds = (ended_at - started_at)
--                       - paused_seconds
--                       - (ended_at - paused_at) IF currently paused
--
--  Safe to re-run.
-- ============================================================

alter table task_time_logs
  add column if not exists mode text default 'stopwatch';

alter table task_time_logs
  add column if not exists target_seconds int;

alter table task_time_logs
  add column if not exists paused_at timestamptz;

alter table task_time_logs
  add column if not exists paused_seconds int default 0;

-- Backfill: existing rows are stopwatches by definition.
update task_time_logs
   set mode = 'stopwatch'
 where mode is null;

-- Restrict to the two modes we use, but only if the constraint
-- doesn't already exist (Supabase / Postgres has no IF NOT EXISTS
-- on add constraint, so we guard with a do-block).
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conname = 'task_time_logs_mode_check'
  ) then
    alter table task_time_logs
      add constraint task_time_logs_mode_check
      check (mode in ('stopwatch', 'pomodoro'));
  end if;
end $$;

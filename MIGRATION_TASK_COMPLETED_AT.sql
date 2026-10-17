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

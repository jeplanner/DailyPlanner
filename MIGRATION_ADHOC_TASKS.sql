-- ============================================================
--  DailyPlanner — ADHOC_TASKS: time tracking repository
--
--  Quick Pomodoros are launched with a free-text label ("Reading
--  Atomic Habits chapter 4"). Until now those labels lived only as
--  duplicate strings on task_time_logs rows, which made it hard to
--  answer "how much time did I spend on reading this month?".
--
--  This migration introduces a small adhoc_tasks dimension table:
--    • One row per unique label per user.
--    • task_time_logs.adhoc_task_id points at it for source='adhoc'.
--    • Totals are computed on the fly (no denormalized counters), so
--      there's nothing to keep in sync — just sum duration_seconds
--      grouped by adhoc_task_id.
--
--  Backfill at the bottom: existing label-only adhoc rows get a row
--  in adhoc_tasks and a back-pointer set, so the Focus Log shows
--  history from day one.
--
--  Safe to re-run.
-- ============================================================

create table if not exists adhoc_tasks (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  label         text not null,
  category      text,                      -- free-text grouping ("Reading", "Admin")
  is_archived   boolean default false,
  created_at    timestamptz default now(),
  last_used_at  timestamptz default now()
);

-- Lookup by user — most queries scope by user_id + active.
create index if not exists adhoc_tasks_user_idx
  on adhoc_tasks (user_id, is_archived);

-- Case-insensitive uniqueness so "Reading" and "reading" don't fork into
-- two rows. Partial unique index ignores archived rows so users can
-- restart a label after archiving.
create unique index if not exists adhoc_tasks_user_label_uniq
  on adhoc_tasks (user_id, lower(label))
  where is_archived = false;

-- task_time_logs back-pointer
alter table task_time_logs
  add column if not exists adhoc_task_id uuid;

create index if not exists task_time_logs_adhoc_idx
  on task_time_logs (adhoc_task_id)
  where adhoc_task_id is not null;


-- ─────────────────────────────────────────────
-- Backfill — surface existing adhoc history immediately
-- ─────────────────────────────────────────────
do $$
declare r record;
declare new_id uuid;
begin
  for r in (
    select user_id,
           label,
           min(started_at) as first_at,
           max(started_at) as last_at
      from task_time_logs
     where source = 'adhoc'
       and label is not null
       and adhoc_task_id is null
     group by user_id, label
  ) loop
    -- Find an existing row for this (user, label) — partial unique index
    -- means we may have a non-archived match already; if so, just attach.
    select id into new_id
      from adhoc_tasks
     where user_id = r.user_id
       and lower(label) = lower(r.label)
       and is_archived = false
     limit 1;

    if new_id is null then
      insert into adhoc_tasks (user_id, label, created_at, last_used_at)
      values (r.user_id, r.label, r.first_at, r.last_at)
      returning id into new_id;
    end if;

    update task_time_logs
       set adhoc_task_id = new_id
     where user_id = r.user_id
       and source = 'adhoc'
       and label = r.label
       and adhoc_task_id is null;
  end loop;
end $$;

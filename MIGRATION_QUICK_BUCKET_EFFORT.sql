-- ============================================================
--  DailyPlanner — QUICK BUCKET: effort tracking
--
--  Adds planned vs actual effort (in minutes) plus an effort date to
--  each Quick Bucket task, so the page can show a daily "planned vs
--  actual productive time" summary.
--
--    planned_minutes  — minutes you expected the task to take
--    actual_minutes   — minutes you actually spent on it
--    effort_date      — the day this effort counts towards (defaults to
--                       the day the minutes were first logged)
--
--  All nullable — a task with no effort logged simply doesn't appear in
--  the daily summary. Non-negative amounts only.
--
--  Safe to re-run (idempotent).
-- ============================================================

alter table quick_bucket add column if not exists planned_minutes integer;
alter table quick_bucket add column if not exists actual_minutes  integer;
alter table quick_bucket add column if not exists effort_date     date;

-- Guard against negative minutes (drop-then-add so re-runs stay no-ops).
do $$ begin
  alter table quick_bucket drop constraint if exists quick_bucket_planned_minutes_chk;
  alter table quick_bucket add constraint quick_bucket_planned_minutes_chk
    check (planned_minutes is null or planned_minutes >= 0);
  alter table quick_bucket drop constraint if exists quick_bucket_actual_minutes_chk;
  alter table quick_bucket add constraint quick_bucket_actual_minutes_chk
    check (actual_minutes is null or actual_minutes >= 0);
end $$;

-- Hot query: "this user's tasks that count towards a given day's effort".
create index if not exists quick_bucket_user_effort_idx
  on quick_bucket (user_id, effort_date)
  where effort_date is not null and is_deleted = false;

-- ============================================================
--  Tasks Bucket — "Today's Top 5" panel
--
--  Two columns on tasks_bucket let a row appear in today's Top-5
--  panel: top5_date stamps which day the user pinned it for, and
--  top5_position is its slot within the panel (1..5).
--
--  Auto-roll: on each page load we bump any incomplete past-day
--  top-5 rows to today's date (handled in Python, not SQL).
--
--  Closed rows keep their top5_date so they stay crossed-out in
--  the panel for the rest of that day.
--
--  Idempotent — safe to re-run.
-- ============================================================

alter table tasks_bucket
  add column if not exists top5_date     date;
alter table tasks_bucket
  add column if not exists top5_position smallint;

create index if not exists tasks_bucket_user_top5_idx
  on tasks_bucket (user_id, top5_date)
  where top5_date is not null;

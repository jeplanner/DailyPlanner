-- ============================================================
--  DailyPlanner — start_date / target_date on Initiatives + Epics
--
--  OKRs (objectives) already carry start_date + target_date so users
--  can bound them. Initiatives and Epics inherited only created_at
--  from the original migration, which means the tree-tab create
--  dialog had nowhere to store dates for those two levels.
--
--  Mirrors the OKR convention (start_date + target_date, both date,
--  both nullable) so the same UI controls work across all three
--  levels and the same backfill semantics apply: no dates = open
--  bucket, dates = scheduled work.
--
--  Safe to re-run.
-- ============================================================

alter table if exists initiatives
  add column if not exists start_date  date,
  add column if not exists target_date date;

alter table if exists epics
  add column if not exists start_date  date,
  add column if not exists target_date date;

-- Helpful when filtering "what's due in the next 14 days" across a
-- project — keeps the planner queries snappy even with hundreds of
-- initiatives / epics.
create index if not exists ix_initiatives_target_date on initiatives (target_date) where is_deleted = false;
create index if not exists ix_epics_target_date       on epics       (target_date) where is_deleted = false;

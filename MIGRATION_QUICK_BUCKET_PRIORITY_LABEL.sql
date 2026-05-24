-- ============================================================
--  DailyPlanner — Quick Bucket: per-row priority label
--
--  Adds a numeric "priority_label" badge on each Quick Bucket row.
--  New rows default to (max existing label) + 1; clicking the badge
--  increments by 1 (no wrap). Conflicts (two rows at the same value)
--  are intentionally allowed — this is a fluid hint, not a rank.
--
--  Safe to re-run.
-- ============================================================

alter table quick_bucket
  add column if not exists priority_label int;

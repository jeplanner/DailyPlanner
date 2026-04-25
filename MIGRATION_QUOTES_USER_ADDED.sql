-- ============================================================
--  DailyPlanner — QUOTES: track who added each entry
--
--  The quotes corpus shipped via MIGRATION_QUOTES.sql is global, but
--  we want users to add their own without burying the seed entries
--  or letting them be wiped accidentally. This migration just adds
--  an optional `added_by` column.
--
--  Behaviour:
--    - Seed rows: added_by IS NULL (set in the original migration).
--    - User-added rows: added_by = session user_id of the creator.
--    - The Browse page shows a delete button only on rows the
--      logged-in user added (added_by = user_id), so seeds stay safe.
--
--  Safe to re-run.
-- ============================================================

alter table quotes
  add column if not exists added_by text;

create index if not exists quotes_added_by_idx
  on quotes (added_by) where added_by is not null;

-- ============================================================
--  DailyPlanner — CHAT MESSAGE EDITING
--
--  Lets a sender edit the body of their own message. We stamp
--  `edited_at` on each edit so the UI can show an "(edited)" marker.
--  NULL = never edited (every legacy row + every fresh send).
--
--  Delete is unchanged — soft-delete via the existing `deleted_at`
--  column, per the project's no-hard-delete convention.
--
--  Safe to re-run.
-- ============================================================

alter table messages
  add column if not exists edited_at timestamptz;

-- ============================================================
--  DailyPlanner — NOTES: folders + pinning
--
--  Adds a tiny bit of structure to the otherwise-flat scribble_notes
--  table so the new master-detail UI can group notes into folders
--  ("All Notes", "Work", "Ideas", …) and pin a handful to the top.
--
--  No new tables — folders are stored as a plain text label on each
--  note. Distinct values are surfaced as the folder list. This keeps
--  schema migrations cheap and lets users rename a folder by editing
--  any note in it (we'll bulk-rename via the API for ergonomics).
--
--  Safe to re-run.
-- ============================================================

alter table scribble_notes
  add column if not exists notebook text default 'All Notes';

alter table scribble_notes
  add column if not exists is_pinned boolean default false;

-- Backfill: existing rows with NULL notebook become "All Notes" so the
-- sidebar count is accurate from day one.
update scribble_notes
   set notebook = 'All Notes'
 where notebook is null;

create index if not exists scribble_notes_user_notebook_idx
  on scribble_notes (user_id, notebook)
  where is_deleted = false;

create index if not exists scribble_notes_user_pinned_idx
  on scribble_notes (user_id, is_pinned, updated_at desc)
  where is_deleted = false and is_pinned = true;

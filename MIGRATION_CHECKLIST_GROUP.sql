-- Add optional user-defined grouping tag to checklist items.
-- Stored in Title Case (normalised server-side) so "health" and
-- "Health" collapse to a single group.

alter table checklist_items
  add column if not exists group_name text;

create index if not exists checklist_items_group_idx
  on checklist_items (user_id, group_name) where is_deleted = false;

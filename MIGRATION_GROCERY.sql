-- ============================================================
--  DailyPlanner — GROCERY list
--
--  A simple per-user grocery list. Users add items to buy, optionally
--  with quantity, category, priority, and notes. Items can be marked
--  purchased (soft-marked, not deleted) so the user has a quick recap
--  of what's already in the basket. Removed items are soft-archived
--  (is_archived = true) — never hard-deleted, per project convention.
--
--  Schema:
--    groceries(id, user_id, item, quantity, category, notes,
--              priority, is_purchased, is_archived,
--              purchased_at, created_at, updated_at)
--
--  Categories used here (free-form text, but UI suggests these):
--    produce, dairy, staples, snacks, household, spices,
--    frozen, beverages, meat, bakery, other
--
--  Priorities: low | medium | high (default medium)
--
--  Safe to re-run.
-- ============================================================

create table if not exists groceries (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null,
  item          text not null,
  quantity      text,
  category      text default 'other',
  notes         text,
  priority      text default 'medium',
  is_purchased  boolean default false,
  is_archived   boolean default false,
  purchased_at  timestamptz,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- Hot path: list every active item for a given user, ordered by
-- category + priority. Partial index keeps it slim.
create index if not exists groceries_user_active_idx
  on groceries (user_id) where is_archived = false;

create index if not exists groceries_user_purchased_idx
  on groceries (user_id, is_purchased) where is_archived = false;

-- Touch updated_at on any row update.
create or replace function _grocery_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists groceries_touch_updated_at on groceries;
create trigger groceries_touch_updated_at
  before update on groceries
  for each row execute function _grocery_touch_updated_at();

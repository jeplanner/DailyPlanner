-- ============================================================
--  DailyPlanner — DAILY EXPENSES
--
--  A simple "money spent today" log: amount + category + optional
--  note, dated. The category field is free-text; the app suggests
--  previously-used categories (built from the user's own history) so
--  it starts empty and fills in as you go.
--
--  Soft-delete only (deleted_at), per the project convention.
--
--  Safe to re-run.
-- ============================================================

create table if not exists expenses (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  spent_on   date not null default current_date,
  amount     numeric(12,2) not null check (amount >= 0),
  category   text,
  note       text,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

-- The hot query is "this user's expenses for a day, newest first" and
-- "distinct categories for suggestions" — both covered here.
create index if not exists expenses_user_date_idx
  on expenses (user_id, spent_on desc) where deleted_at is null;

-- ============================================================
--  DailyPlanner — MONEY (expenses + income)
--
--  A simple ledger: each row is either money spent (expense) or money
--  received (income), with amount + category + optional note, dated.
--  The category field is free-text; the app suggests previously-used
--  categories (from the user's own history) so it starts empty and
--  fills in as you go. Reports sum by month / category / kind.
--
--  Soft-delete only (deleted_at), per the project convention.
--
--  Safe to re-run (idempotent).
-- ============================================================

create table if not exists expenses (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  kind       text not null default 'expense',
  spent_on   date not null default current_date,
  amount     numeric(12,2) not null check (amount >= 0),
  category   text,
  note       text,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

-- For tables created before income was added.
alter table expenses
  add column if not exists kind text not null default 'expense';

-- Constrain kind to the two known values (drop-then-add so re-runs and
-- future additions stay no-ops).
do $$ begin
  alter table expenses drop constraint if exists expenses_kind_chk;
  alter table expenses add constraint expenses_kind_chk
    check (kind in ('expense', 'income'));
end $$;

-- Hot queries: "this user's rows for a day" and "for a month" (reports),
-- newest first.
create index if not exists expenses_user_date_idx
  on expenses (user_id, spent_on desc) where deleted_at is null;

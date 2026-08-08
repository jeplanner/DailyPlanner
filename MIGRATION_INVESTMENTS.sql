-- ============================================================
--  DailyPlanner — INVESTMENTS (simple net-worth tracker)
--
--  Deliberately tiny: each row is one investment you hold, recorded
--  as just Name + Type + Date + Total Amount (INR). The page sums
--  every row into a grand total. No live prices or symbols — that's
--  the richer /portfolio feature. This is the "type the number in
--  yourself" version.
--
--  Name and Type are free-text but the app suggests values you've
--  used before (built from your own history) so each field grows into
--  a handy pick-list as you go.
--
--  Soft-delete only (deleted_at), per the project convention.
--
--  Safe to re-run (idempotent).
-- ============================================================

create table if not exists investments (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  name        text not null,
  type        text,
  invested_on date not null default current_date,
  amount      numeric(14,2) not null default 0 check (amount >= 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

-- For tables created by an earlier version of this migration.
alter table investments add column if not exists type text;
alter table investments add column if not exists invested_on date not null default current_date;

-- Hot query: "this user's live investments, newest first".
create index if not exists investments_user_idx
  on investments (user_id, invested_on desc) where deleted_at is null;

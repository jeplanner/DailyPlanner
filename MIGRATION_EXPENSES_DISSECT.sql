-- ============================================================
--  DailyPlanner — MONEY: dissect dimensions + recurrence
--
--  Adds structured fields so spend can be sliced beyond just
--  category, and so recurring commitments can be tagged (and
--  projected) instead of living in the free-text note:
--
--    recurrence  — single vs daily / monthly / quarterly / yearly
--    need_want   — budgeting class: need / want / saving
--    cost_type   — fixed (rent, EMI) vs variable (groceries, dining)
--    tag         — a second free-text label, like category
--
--  All optional and nullable except recurrence (defaults 'none').
--  Soft-delete only (deleted_at), per the project convention.
--
--  Safe to re-run (idempotent).
-- ============================================================

alter table expenses
  add column if not exists recurrence text not null default 'none',
  add column if not exists need_want  text,
  add column if not exists cost_type  text,
  add column if not exists tag        text;

-- Constrain the enumerated fields (drop-then-add so re-runs and
-- future value additions stay no-ops).
do $$ begin
  alter table expenses drop constraint if exists expenses_recurrence_chk;
  alter table expenses add constraint expenses_recurrence_chk
    check (recurrence in ('none', 'daily', 'monthly', 'quarterly', 'yearly'));

  alter table expenses drop constraint if exists expenses_need_want_chk;
  alter table expenses add constraint expenses_need_want_chk
    check (need_want is null or need_want in ('need', 'want', 'saving'));

  alter table expenses drop constraint if exists expenses_cost_type_chk;
  alter table expenses add constraint expenses_cost_type_chk
    check (cost_type is null or cost_type in ('fixed', 'variable'));
end $$;

-- "Recurring commitments for this user" — drives the projected
-- monthly / yearly totals.
create index if not exists expenses_user_recurrence_idx
  on expenses (user_id, recurrence) where deleted_at is null and recurrence <> 'none';

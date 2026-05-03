-- ─────────────────────────────────────────────────────────────────
-- PORTFOLIO_TRANSACTIONS → order_ref: store the broker's unique
-- trade ID per execution. ICICI's tradeBook export gives an
-- "Order Ref." column (e.g., 20260330N400010199) — using it as
-- the dedupe key prevents identical-looking trades (same date,
-- qty, price, fees) from being collapsed into one row.
--
-- Idempotent. No-op on re-run.
-- ─────────────────────────────────────────────────────────────────

alter table if exists portfolio_transactions
    add column if not exists order_ref text;

create index if not exists portfolio_txn_order_ref_idx
    on portfolio_transactions (order_ref) where order_ref is not null;

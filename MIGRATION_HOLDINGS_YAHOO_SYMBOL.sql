-- ─────────────────────────────────────────────────────────────────
-- HOLDINGS → yahoo_symbol: store the Yahoo Finance ticker
-- (e.g. "NTPC.NS", "RELIANCE.NS") separately from the broker's
-- internal short code. ICICI Direct uses opaque codes like
-- "OILIND" (not "OIL.NS") and "STEWIL" — naïvely appending ".NS"
-- to those returns 404 from Yahoo, which is why prices were
-- coming back blank.
--
-- Resolution flow: a Yahoo search per holding, with the result
-- cached here so we only pay the network cost once per symbol.
-- Refresh-prices reads yahoo_symbol first; falls back to symbol
-- with a ".NS" suffix when yahoo_symbol is NULL (preserves the
-- old behaviour for holdings the resolver hasn't touched yet).
--
-- Idempotent. No-op on re-run.
-- ─────────────────────────────────────────────────────────────────

alter table if exists portfolio_holdings
    add column if not exists yahoo_symbol text;

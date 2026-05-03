-- ─────────────────────────────────────────────────────────────────
-- PORTFOLIO_SNAPSHOTS: daily-cached values for the trend charts on
-- /portfolio. Without this table, /api/portfolio/trends returns 404
-- and the "Portfolio Value Over Time" / "XIRR Over Time" charts
-- can't render.
--
-- Idempotent — safe to re-run. Original table definition lives in
-- MIGRATION_ALL_TABLES.sql; this file exists so users on partial
-- DBs can pull just this table without re-running everything.
-- ─────────────────────────────────────────────────────────────────

create table if not exists portfolio_snapshots (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  snap_date     date not null,
  group_type    text not null,    -- 'overall' | 'asset_type' | 'sector'
  group_name    text not null,    -- e.g., 'all', 'stock', 'Banking'
  invested      numeric,
  current_value numeric,
  xirr          numeric,
  created_at    timestamptz default now()
);

create index if not exists portfolio_snap_user_idx
    on portfolio_snapshots (user_id, snap_date);

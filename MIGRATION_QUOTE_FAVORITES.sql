-- ============================================================
--  DailyPlanner — QUOTE FAVORITES
--
--  Per-user "starred quotes" so the Browse Quotes page can offer a
--  Favorites filter and the daily quote card can give weight to
--  favorites in future picks. Junction table keyed by (user_id,
--  quote_id) — one row per favorite, no duplicates.
--
--  Safe to re-run.
-- ============================================================

create table if not exists quote_favorites (
  user_id    text not null,
  quote_id   uuid not null references quotes(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, quote_id)
);

create index if not exists quote_favorites_user_idx
  on quote_favorites (user_id, created_at desc);

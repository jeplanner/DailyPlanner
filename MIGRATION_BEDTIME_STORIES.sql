-- ============================================================
--  DailyPlanner — BEDTIME STORIES
--
--  Schema only. Seed data lives in scripts/seed_bedtime_stories.py
--  (idempotent upsert by slug) so the corpus can grow without ever
--  touching another migration.
--
--  body = single TEXT field with paragraphs separated by '\n\n'.
--         The route splits on that delimiter when rendering.
--
--  Visibility is gated in the application by an env-var allowlist
--  (BEDTIME_STORIES_USER_EMAILS), not at the DB level — every active
--  row is potentially visible.
--
--  Safe to re-run.
-- ============================================================

create table if not exists bedtime_stories (
  id           uuid primary key default gen_random_uuid(),
  slug         text not null unique,
  source       text not null,                -- e.g. 'Panchatantra', 'Aesop'
  title        text not null,
  body         text not null,                -- paragraphs joined by '\n\n'
  moral        text not null,
  sort_order   integer not null default 0,   -- corpus display order
  is_active    boolean not null default true,
  created_at   timestamptz not null default now()
);

create index if not exists bedtime_stories_active_source_idx
  on bedtime_stories (is_active, source) where is_active = true;

create index if not exists bedtime_stories_sort_idx
  on bedtime_stories (sort_order);

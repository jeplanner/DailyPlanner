-- ============================================================
--  RANDOM THOUGHTS — questions that come up during interview prep,
--  answered in depth by the app (Interview Prep -> Random thoughts).
--
--  A question is saved as 'pending' and answered in the background; the
--  row becomes 'ready' (answer filled) or 'failed' (error filled).
--  Follow-ups ("explain simpler", "go deeper", your own) are rows with
--  parent_id set; root_id groups a whole thread.
--
--  Safe to run more than once. Run in the Supabase SQL editor.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists prep_thoughts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  parent_id   uuid references prep_thoughts(id) on delete cascade,
  root_id     uuid,
  question    text not null check (length(question) between 1 and 2000),
  context     text,
  answer      text,
  status      text not null default 'pending'
              check (status in ('pending', 'ready', 'failed')),
  model       text,
  error       text,
  understood  boolean not null default false,
  pinned      boolean not null default false,
  tags        text[] not null default '{}',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

create index if not exists prep_thoughts_user_recent
  on prep_thoughts (user_id, created_at desc) where deleted_at is null;
create index if not exists prep_thoughts_root
  on prep_thoughts (root_id) where deleted_at is null;

-- The app uses the service key (bypasses RLS); with RLS on and no
-- policies, the public anon key can read nothing here.
alter table prep_thoughts enable row level security;

-- ── Diagrams & images (added later; safe to re-run) ─────────────────
-- Images you attach to a question or follow-up: [{key, name, mime, size}].
alter table prep_thoughts add column if not exists images jsonb not null default '[]'::jsonb;

-- The image files themselves go in the EXISTING `user-photos` storage
-- bucket (the one the Photos page uses - see MIGRATION_USER_PHOTOS.sql),
-- under a "thoughts/<your user id>/" folder. No new bucket is needed.
-- The app reads them with the service key and serves each image only to
-- its owner. That bucket's limit is 5 MB per image.

-- ── Shelves (added later; safe to re-run) ───────────────────────────
-- Random thoughts live on two pages: Interview Prep ('tpm') and AI SDE
-- Prep ('aisde', answered for a new-grad AI/ML SDE loop). Every existing
-- row stays on Interview Prep.
alter table prep_thoughts add column if not exists shelf text not null default 'tpm';
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'prep_thoughts_shelf_check') then
    alter table prep_thoughts add constraint prep_thoughts_shelf_check
      check (shelf in ('tpm', 'aisde'));
  end if;
end $$;
create index if not exists prep_thoughts_user_shelf
  on prep_thoughts (user_id, shelf, created_at desc) where deleted_at is null;

-- ── Your notes (added 2026-10-16; safe to re-run) ───────────────────
-- Your own notes against a question or follow-up, newest last:
--   [{id, text, created_at, updated_at, deleted_at}]
-- Deleting a note sets its deleted_at; the note itself is kept (soft
-- delete, like every other row in the app). A refreshed shipped answer
-- or a rewrite only touches `answer`, so notes survive both.
alter table prep_thoughts add column if not exists notes jsonb not null default '[]'::jsonb;

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

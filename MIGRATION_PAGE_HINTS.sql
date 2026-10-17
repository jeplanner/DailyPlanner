-- ============================================================
--  HIGHLIGHTS WITH HINTS — on every page of the planner.
--
--  Select text anywhere, tap "Highlight & ask": the passage stays
--  highlighted and your question's short answer is saved on it as a hint.
--  A hint is a small conversation: keep asking follow-up questions.
--  A hint with no quote is a question about the page as a whole
--  ("Ask about this page").
--
--  thread: [{q, a, status: pending|ready|failed, error, model, at}]
--
--  Safe to run more than once. Run in the Supabase SQL editor.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists page_hints (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  page        text not null check (length(page) between 1 and 300),
  anchor      text not null default '',
  quote       text not null default '' check (length(quote) <= 600),
  prefix      text not null default '',
  thread      jsonb not null default '[]'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

create index if not exists page_hints_user_page
  on page_hints (user_id, page, created_at) where deleted_at is null;

-- The app uses the service key (bypasses RLS); with RLS on and no
-- policies, the public anon key can read nothing here.
alter table page_hints enable row level security;

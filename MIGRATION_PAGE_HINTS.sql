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

-- NO ROW-LEVEL SECURITY HERE, ON PURPOSE (2026-10-17). The live server's
-- SUPABASE_KEY is the PUBLIC key, and RLS with no policies hides every row
-- from it and refuses every write: re-running this file emptied Random
-- thoughts that day. RLS is switched on in ONE place, MIGRATION_ENABLE_RLS.sql,
-- and only after SUPABASE_KEY on Render is the secret key.

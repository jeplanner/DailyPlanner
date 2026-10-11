-- ============================================================
--  PREP PROGRESS — "rehearsed" ticks and mock-interview scores for the
--  Interview Prep hub (case rounds, behavioural bank, system design).
--
--  Until now those ticks lived in each browser's localStorage, keyed by
--  the entry's POSITION in the bank. So ticks on the phone never reached
--  the laptop, and adding one case shifted every position after it.
--  Rows here are keyed by TITLE; the page migrates its old ticks across
--  automatically the first time it loads after this runs.
--
--  Safe to run more than once. Run in the Supabase SQL editor.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists prep_progress (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null,
  bank             text not null,          -- 'tpm' | 'behavioral' | 'sysdesign' | 'sddeep'
  entry_title      text not null,
  done             boolean not null default false,
  done_at          timestamptz,
  mock_attempts    int not null default 0,
  mock_last_score  smallint check (mock_last_score between 1 and 4),
  mock_best_score  smallint check (mock_best_score between 1 and 4),
  mock_last_at     timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- The upsert target: the app posts with ?on_conflict=user_id,bank,entry_title.
create unique index if not exists prep_progress_user_bank_title
  on prep_progress (user_id, bank, entry_title);

create index if not exists prep_progress_user_done
  on prep_progress (user_id, bank) where done;

-- The app talks to Supabase with the service key, which bypasses RLS; with
-- RLS on and no policies, the public anon key can read nothing here.
alter table prep_progress enable row level security;

-- Best quiz score (0-100) for the system design deep dives; 80%+ marks the
-- design as studied.
alter table prep_progress add column if not exists quiz_best_pct smallint
  check (quiz_best_pct between 0 and 100);

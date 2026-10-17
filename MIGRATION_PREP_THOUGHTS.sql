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

-- ── Spaced repetition (added later; safe to re-run) ─────────────────
-- Marking a question "studied" schedules a review tomorrow; each review
-- (Forgot / Hard / Got it / Easy) moves it 1, 3, 7, 14, 30, 60 or 120 days out.
alter table prep_thoughts add column if not exists review_stage     integer not null default 0;
alter table prep_thoughts add column if not exists next_review_at   timestamptz;
alter table prep_thoughts add column if not exists last_reviewed_at timestamptz;
alter table prep_thoughts add column if not exists review_count     integer not null default 0;
create index if not exists prep_thoughts_due
  on prep_thoughts (user_id, next_review_at) where deleted_at is null and next_review_at is not null;
-- Questions you had already marked understood join the cycle: first review tomorrow.
update prep_thoughts set next_review_at = now() + interval '1 day'
  where understood and next_review_at is null and deleted_at is null and parent_id is null;

-- ── Your notes (added 2026-10-16; safe to re-run) ───────────────────
-- Your own notes against a question or follow-up, newest last:
--   [{id, text, created_at, updated_at, deleted_at}]
-- Deleting a note sets its deleted_at; the note itself is kept (soft
-- delete, like every other row in the app). A refreshed shipped answer
-- or a rewrite only touches `answer`, so notes survive both.
alter table prep_thoughts add column if not exists notes jsonb not null default '[]'::jsonb;

-- ── Highlights with hints (added 2026-10-17; safe to re-run) ─────────
-- Highlight a passage of an answer and ask about it: the question and its
-- short answer are saved as a HINT on that highlight. A hint is a follow-up
-- row (parent_id = the answer it highlights) with this column set:
--   {quote: the highlighted text, prefix: up to 80 chars before it}
-- Ordinary follow-ups leave it null.
alter table prep_thoughts add column if not exists highlight jsonb;

-- ── Audio summaries (added 2026-10-17; safe to re-run) ───────────────
-- A ~5 minute spoken summary of each question's answer, as an MP3:
-- the question, a 5-second pause to recall it, then the answer
-- (services/thoughts_audio.py). This column tracks it:
--   {status: pending|ready|failed, key, hash, seconds, words, error, at}
-- `hash` is of the question + answer, so an edited answer is re-spoken.
alter table prep_thoughts add column if not exists audio jsonb;

-- The files live in their own PRIVATE bucket: the user-photos bucket
-- only accepts images. Served through the app to their owner only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('thought-audio', 'thought-audio', false, 10485760, array['audio/mpeg'])
on conflict (id) do nothing;

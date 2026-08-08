-- ============================================================
--  DailyPlanner — INTERVIEW PREP: per-user question-bank overrides
--
--  The behavioral question bank (interview_question_bank.py) is static
--  reference content. This table lets a user EDIT any of those answers
--  in place and keep their edits — without the static file wiping them
--  on deploy. One row per (user, question_id) holds the user's full
--  edited copy; the bank endpoint merges it over the original.
--
--  "Reset" soft-deletes the override (deleted_at) so the original bank
--  answer shows again, per the project's soft-delete convention. Re-
--  editing revives the row via upsert (deleted_at back to null).
--
--  Safe to re-run (idempotent).
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists interview_question_overrides (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  question_id text not null,            -- matches bank id, e.g. 'q17'
  question    text,
  situation   text,
  task        text,
  action      text,
  result      text,
  tip         text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz,
  unique (user_id, question_id)
);

create index if not exists interview_qoverride_user_idx
  on interview_question_overrides (user_id) where deleted_at is null;

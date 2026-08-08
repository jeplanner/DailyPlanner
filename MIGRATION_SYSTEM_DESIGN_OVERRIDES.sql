-- ============================================================
--  DailyPlanner — SYSTEM DESIGN bank: per-user overrides
--
--  The system-design bank (system_design_bank.py) is static reference
--  content. This table lets a user EDIT any entry in place and keep the
--  edit across deploys. One row per (user, entry_id) holds the user's
--  full edited copy; the bank endpoint merges it over the original.
--
--  "Reset" soft-deletes the override (deleted_at) so the original shows
--  again; re-editing revives the row via upsert. Mirrors
--  interview_question_overrides.
--
--  Safe to re-run (idempotent).
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists system_design_overrides (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users(id) on delete cascade,
  entry_id      text not null,               -- matches bank id, e.g. 'sd23'
  title         text,
  problem       text,
  answer        text,
  example       text,
  use_cases     text,
  arch          text,
  disadvantages text,
  competing     text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  deleted_at    timestamptz,
  unique (user_id, entry_id)
);

create index if not exists system_design_override_user_idx
  on system_design_overrides (user_id) where deleted_at is null;

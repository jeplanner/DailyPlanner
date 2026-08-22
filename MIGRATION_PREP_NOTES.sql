-- ============================================================
--  DailyPlanner — her own notes on a prep question
--
--  A bank entry is written material: an answer, a walkthrough, worked
--  examples. What it has never had is a place for the reader's OWN
--  thinking — the thing she got wrong the first time, the sentence
--  that finally made it click, the follow-up an interviewer actually
--  asked her. That is the note most worth keeping and it currently
--  has nowhere to live.
--
--  KEYED BY TITLE, NOT BY ENTRY ID, and this is not a preference.
--  Every bank numbers its entries by POSITION — ai42, j7, sq3 — and
--  a position shifts the moment an entry is added or deduped. The AI
--  SDE bank went from ~500 to 1,120 entries with 57 duplicates folded
--  out, so anything stored against those ids has been pointing at the
--  wrong topic for a long time. Progress, recall and the tag tables
--  all key on title for the same reason.
--
--  ONE NOTE PER (user, bank, title). Not a thread — a note you revise
--  is more useful than a list you scroll, and revision history on a
--  personal scratchpad is a feature nobody has asked for.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists prep_notes (
    id          uuid primary key default gen_random_uuid(),
    user_id     text        not null,
    -- 'ai_sde' | 'java' | 'sql' | 'behavioral' — the same keys
    -- PREP_BANKS uses, so a new bank needs no schema change.
    bank        text        not null,
    entry_title text        not null,
    note        text        not null default '',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- The upsert target. Writing a note is an UPSERT on this triple, so it
-- must be unique or a second save creates a second row and the first
-- one silently becomes unreachable.
create unique index if not exists prep_notes_user_bank_title_idx
    on prep_notes (user_id, bank, entry_title);

-- The read is always "every note this user has for this bank", so the
-- page can paint them all without a query per card.
create index if not exists prep_notes_user_bank_idx
    on prep_notes (user_id, bank);

alter table prep_notes add column if not exists note       text not null default '';
alter table prep_notes add column if not exists created_at timestamptz not null default now();
alter table prep_notes add column if not exists updated_at timestamptz not null default now();

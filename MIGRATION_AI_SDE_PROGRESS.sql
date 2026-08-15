-- ============================================================
--  DailyPlanner — AI SDE PROGRESS (server-side)
--
--  Until now every trace of AI SDE study lived in the browser's
--  localStorage: which topics were ticked, the Pomodoro minutes per
--  question, the Sadhana XP. Three consequences, all bad:
--
--    1. Progress did not follow the user between phone and laptop —
--       two devices meant two unrelated progress bars.
--    2. Clearing site data wiped months of work with no way back.
--    3. Nothing server-side could answer "is this being used at all",
--       so the effort readouts could never become real reporting.
--
--  KEYED BY TITLE, NOT BY THE ENTRY'S ID. The API hands out ids as
--  "ai0", "ai1", ... derived from the entry's INDEX in ai_sde_bank.py.
--  That index shifts every time an entry is added, removed or deduped —
--  and the bank has grown from ~500 to 1,120 entries and had 57
--  duplicates folded out along the way. Any progress stored against
--  those ids is therefore already pointing at the wrong topics. Titles
--  are the stable key: they are what the _EX_* example dicts and
--  ai_sde_tags.py already key on, and a title change is rare and
--  deliberate. The trade-off is that renaming a topic loses its
--  progress, which is the right way round.
--
--  minutes_focused holds the Pomodoro total for the topic so effort
--  survives a device change; studied_at is null until the topic is
--  ticked, so it doubles as "when did this land".
--
--  Safe to re-run.
-- ============================================================

create table if not exists ai_sde_progress (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null,
  entry_title     text not null,
  studied         boolean not null default false,
  studied_at      timestamptz,
  minutes_focused int not null default 0,
  updated_at      timestamptz not null default now(),
  created_at      timestamptz not null default now(),
  is_deleted      boolean not null default false,
  deleted_at      timestamptz
);

-- One row per topic per user. The upsert in the API relies on this.
create unique index if not exists ai_sde_progress_user_title
  on ai_sde_progress (user_id, entry_title);

-- The page loads every row for the user on open, so index the lookup.
create index if not exists ai_sde_progress_user_idx
  on ai_sde_progress (user_id)
  where not is_deleted;

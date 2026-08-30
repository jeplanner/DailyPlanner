-- ============================================================
--  DailyPlanner — SHARE AN ITEM WITH SOMEONE, FOR A DAY AND TIME
--
--  Asked 2026-08-30, in two goes:
--    "make specific inbox items to be shared with multiple users.
--     when they log in it should appear there also"
--    "also interview prep sections i can mark few items to be
--     shared with others. It should appear in chat space under a
--     section called calendar where they know which item has been
--     tagged them to read at what day and time. They should be
--     able to mark it as completed ... It should tell me who has
--     completed it and the date in which it was completed."
--
--  ONE TABLE FOR BOTH, because they are the same sentence: this
--  thing, to these people, for that day, and did they do it. A
--  second table for prep would be the same columns with a different
--  name and its own bugs.
--
--  WHY THE TITLE AND URL ARE COPIED IN.
--  An inbox share could join back to inbox_links. A prep share
--  cannot: the banks are PYTHON MODULES, not tables, and their
--  entry ids are positional — they shift whenever the bank is
--  edited, which is why progress and notes are already keyed by
--  TITLE (see memory: project_ai_sde_progress_sync). So the share
--  carries the title it was made with. That also makes the chat
--  calendar one query with no lookups, and keeps a shared item
--  readable after the bank moves on.
--
--  COMPLETION IS PER ROW, AND THE ROW IS PER PERSON.
--  There is one row per (item, recipient), so completed_at is
--  naturally per recipient: two people can be given the same
--  article and finish it on different days, which is what "tell me
--  who has completed it and the date" needs.
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists shared_items (
  id            uuid primary key default gen_random_uuid(),

  -- 'inbox' | 'prep'. Kept as text rather than an enum so adding a
  -- third kind is a code change, not a migration.
  kind          text not null,

  -- inbox_links.id for an inbox item; the TITLE for a prep topic.
  item_ref      text not null,

  -- Which bank a prep item came from ('ai-sde' | 'java' | 'sql' |
  -- 'interview'). Null for inbox items.
  bank          text,

  -- What it is called and where it points, copied at share time —
  -- see the note above.
  item_title    text,
  item_url      text,

  -- Text, not uuid: users.id is compared against inbox_links.user_id
  -- which is text, and one cast per read is one cast too many.
  owner_id      text not null,
  shared_with   text not null,

  -- "to read at what day and time". Both optional: sharing without a
  -- date is still sharing, and the calendar lists undated items last.
  due_date      date,
  due_time      time,

  completed_at  timestamptz,

  created_at    timestamptz default now()
);

-- One grant per (item, person) so re-sharing is a no-op rather than a
-- second row — the share endpoint sends the whole set and upserts.
create unique index if not exists shared_items_unique_grant_idx
  on shared_items (kind, item_ref, shared_with);

-- Hot path: "what has been given to me", the chat calendar, every load.
create index if not exists shared_items_recipient_idx
  on shared_items (shared_with, due_date);

-- Cold path: "who did I give this to, and did they do it".
create index if not exists shared_items_owner_idx
  on shared_items (owner_id, kind, item_ref);

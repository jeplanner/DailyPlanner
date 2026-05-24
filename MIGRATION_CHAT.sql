-- ============================================================
--  DailyPlanner — FAMILY CHAT (one shared room)
--
--  Single shared channel. Every signed-in user is implicitly a
--  member — being logged in *is* membership. No rooms table, no
--  members table, no DMs in v1.
--
--  `author_name` is denormalized so historical messages still
--  render correctly even after a user's display_name changes or
--  the user row is removed (cascade keeps history intact when
--  the user is purged, but the name on the bubble stays the one
--  in use at send time).
--
--  Soft-delete only (`deleted_at`) per the project convention —
--  the column ships now even though the UI doesn't expose a
--  delete action yet, so we don't need a follow-up migration.
--
--  Safe to re-run.
-- ============================================================

create table if not exists messages (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  author_name text not null,
  body        text not null check (char_length(body) between 1 and 2000),
  created_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

-- Polling fetches "messages with created_at > :since" ordered ASC, and
-- initial page-load fetches "last 100 ordered DESC". Both want an index
-- on created_at — one DESC index serves both since Postgres can scan it
-- either direction.
create index if not exists messages_created_at_idx
  on messages (created_at desc);

-- Per-user "last read" cursor for the unread badge. Stored directly on
-- the users row (rather than a chat_read_state side table) because
-- there's exactly one chat room — no need for a per-room cursor.
-- NULL means "never opened chat" — the unread query treats that as
-- "every non-own message is unread" so the badge does the right thing
-- on first ever load.
alter table users
  add column if not exists chat_last_read_at timestamptz;

-- Message "kind" tag — lets the chat UI filter shares away from
-- regular conversation. Default 'text' covers every legacy row and
-- every normal compose. The share endpoint sets 'kb-share' or
-- 'inbox-share' depending on origin.
alter table messages
  add column if not exists kind text not null default 'text';

-- Belt-and-braces: clamp the column to the values the app knows
-- how to render. Drop-then-add so re-running the migration after
-- adding a new kind value later is a no-op.
do $$ begin
  alter table messages drop constraint if exists messages_kind_chk;
  alter table messages add constraint messages_kind_chk
    check (kind in ('text', 'kb-share', 'inbox-share'));
end $$;

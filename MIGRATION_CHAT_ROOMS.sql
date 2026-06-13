-- ============================================================
--  DailyPlanner — CHAT ROOMS (private membership)
--
--  Turns the single hard-coded family room into multiple rooms, each
--  with its own member list. A room is visible only to its members;
--  the CHAT_USER_EMAILS allowlist still gates who can use chat at all,
--  and members are picked from that allowlist.
--
--  Schema:
--    chat_rooms          — one row per room. is_default marks the
--                          permanent "Family" room everyone auto-joins.
--    chat_room_members   — (room_id, user_id) membership. Carries the
--                          per-room read cursor (last_read_at), so the
--                          old single users.chat_last_read_at is now
--                          per-room. Soft-delete via deleted_at = "left".
--    messages.room_id    — which room a message belongs to.
--
--  Backfill: every existing message goes into a default "Family" room,
--  everyone who has ever posted becomes a member, and each member's
--  read cursor is seeded from the old users.chat_last_read_at so the
--  unread badge doesn't light up for the whole history on first load.
--
--  Safe to re-run (idempotent).
-- ============================================================

create table if not exists chat_rooms (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (char_length(name) between 1 and 80),
  -- NULL created_by = system-created (the default room) → no owner, so
  -- it can't be renamed or deleted by anyone. User rooms are owned by
  -- their creator.
  created_by  uuid references users(id) on delete set null,
  is_default  boolean not null default false,
  created_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

create table if not exists chat_room_members (
  id           uuid primary key default gen_random_uuid(),
  room_id      uuid not null references chat_rooms(id) on delete cascade,
  user_id      uuid not null references users(id) on delete cascade,
  added_by     uuid,
  added_at     timestamptz not null default now(),
  -- Per-room "last read" cursor — replaces users.chat_last_read_at.
  last_read_at timestamptz,
  -- Soft-leave: a member who leaves keeps their row (history/audit) but
  -- with deleted_at set, so re-joining is an UPDATE not a fresh row.
  deleted_at   timestamptz
);

-- One membership row per (room, user) — also the conflict target for
-- the auto-join upsert in the app.
create unique index if not exists chat_room_members_uniq
  on chat_room_members (room_id, user_id);

-- "Which rooms am I in" — the hottest lookup (every chat load).
create index if not exists chat_room_members_user_idx
  on chat_room_members (user_id) where deleted_at is null;

alter table messages
  add column if not exists room_id uuid references chat_rooms(id);

-- Message list / unread queries always filter by room then order by time.
create index if not exists messages_room_created_idx
  on messages (room_id, created_at desc);

-- ── Backfill the default room ──────────────────────────────────
do $$
declare d uuid;
begin
  select id into d from chat_rooms
   where is_default = true and deleted_at is null
   limit 1;
  if d is null then
    insert into chat_rooms (name, is_default) values ('Family', true)
      returning id into d;
  end if;

  -- Park every orphan message in the default room.
  update messages set room_id = d where room_id is null;

  -- Everyone who has ever posted is a member of the default room.
  insert into chat_room_members (room_id, user_id)
    select d, t.user_id
      from (select distinct user_id from messages where user_id is not null) t
  on conflict (room_id, user_id) do nothing;

  -- Seed the per-room read cursor from the old global one.
  update chat_room_members crm
     set last_read_at = u.chat_last_read_at
    from users u
   where crm.user_id = u.id
     and crm.room_id = d
     and crm.last_read_at is null;
end $$;

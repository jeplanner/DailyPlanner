-- ============================================================
--  DailyPlanner — spoken announcements, moved to the server
--
--  Until now these lived in localStorage under "dp-time-announcer",
--  so they existed on exactly one device. That is backwards from
--  where they matter most: the phone is the thing in your pocket
--  with the screen off, and it was the device you had to set up
--  separately. Clearing site data wiped them.
--
--  WHAT SYNCS AND WHAT DOES NOT, decided deliberately:
--
--    SYNCED — the announcements themselves, the repeating interval,
--    and the shared "say this first" label. These are CONTENT: what
--    gets announced. They belong to you, not to a browser.
--
--    LOCAL — mode (start/pause/stop), the keep-alive checkbox, and
--    the "already said this slot" marks. These are per-device
--    RUNTIME state. Pausing on your phone must not silence the
--    laptop you are sitting at, holding audio open is a battery
--    decision that belongs to the device making it, and if `said`
--    synced then one device announcing would silence every other.
--
--  ONE ROW PER ANNOUNCEMENT, not one JSON blob per user. With a blob,
--  a phone that had the list open before you added something on the
--  laptop overwrites it on its next save. Per-row means adds and
--  deletes from two devices merge instead of clobbering.
--
--  client_id is the id the browser already generates. Keying on it
--  makes every write an idempotent upsert, so a retry after a flaky
--  connection cannot create a duplicate.
--
--  Column names avoid `at`, `until`, `repeat`, `start`, `end` and
--  `text` — all either reserved or shadowing a builtin in Postgres.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists announcer_items (
    id          uuid        primary key default gen_random_uuid(),
    user_id     text        not null,
    -- The id generated client-side. The upsert target, see above.
    client_id   text        not null,

    at_time     text        not null,             -- 'HH:MM', when it starts
    until_time  text,                             -- 'HH:MM' or null
    every_mins  integer     not null default 0,   -- 0 = speaks once

    -- 'once' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'custom'
    repeat_rule text        not null default 'daily',
    days        integer[]   not null default '{}',-- 0=Sun..6=Sat, for 'custom'
    start_date  date,
    end_date    date,                             -- null = runs for good

    say_text    text        not null default '',
    is_on       boolean     not null default true,

    -- SOFT DELETE, like everything else in this app. A deleted
    -- announcement stops speaking and stays recoverable.
    is_deleted  boolean     not null default false,

    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- The upsert target. Without this unique index a retried save creates a
-- second row and the first silently becomes unreachable.
create unique index if not exists announcer_items_user_client_idx
    on announcer_items (user_id, client_id);

-- The read is always "every live announcement for this user".
create index if not exists announcer_items_user_live_idx
    on announcer_items (user_id)
    where is_deleted = false;

-- The two settings that are content rather than runtime state.
create table if not exists announcer_settings (
    user_id     text        primary key,
    every_mins  integer     not null default 15,  -- the repeating clock
    label       text        not null default '',  -- "say this first"
    updated_at  timestamptz not null default now()
);

-- Re-runnable column adds, for a database created by an earlier version.
alter table announcer_items add column if not exists until_time  text;
alter table announcer_items add column if not exists every_mins  integer not null default 0;
alter table announcer_items add column if not exists repeat_rule text not null default 'daily';
alter table announcer_items add column if not exists days        integer[] not null default '{}';
alter table announcer_items add column if not exists start_date  date;
alter table announcer_items add column if not exists end_date    date;
alter table announcer_items add column if not exists say_text    text not null default '';
alter table announcer_items add column if not exists is_on       boolean not null default true;
alter table announcer_items add column if not exists is_deleted  boolean not null default false;
alter table announcer_items add column if not exists created_at  timestamptz not null default now();
alter table announcer_items add column if not exists updated_at  timestamptz not null default now();

alter table announcer_settings add column if not exists every_mins integer not null default 15;
alter table announcer_settings add column if not exists label      text not null default '';
alter table announcer_settings add column if not exists updated_at timestamptz not null default now();

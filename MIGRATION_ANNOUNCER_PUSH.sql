-- ============================================================
--  DailyPlanner — announcements as push notifications
--
--  WHY. Spoken announcements need the page alive and VISIBLE. The
--  keep-alive audio keeps the page running with the screen off, but
--  Web Speech is suspended on a locked phone on every platform that
--  matters, so nothing is heard. That is a browser limitation and no
--  amount of work on our side changes it.
--
--  A NOTIFICATION does work with the screen locked, and works with the
--  app fully closed, which speech never can. So each announcement now
--  ALSO fires as a push at its scheduled time. Speech remains the
--  experience when you are looking at the app; the notification is what
--  reaches you when you are not.
--
--  This became possible only because announcements moved server-side in
--  MIGRATION_ANNOUNCER_SYNC.sql — the scheduler cannot read a schedule
--  that lives in one browser's localStorage.
--
--  THE DEDUP LOG mirrors checklist_reminder_log: the unique index is
--  what makes this safe across several gunicorn workers, since only the
--  first insert wins and only that worker sends.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists announcer_fire_log (
    id         uuid        primary key default gen_random_uuid(),
    user_id    text        not null,
    -- The announcement's client_id, matching announcer_items.
    client_id  text        not null,
    fire_date  date        not null,
    -- 'HH:MM' — a windowed announcement has many slots a day and each
    -- must fire independently, so the time is part of the key.
    fire_time  text        not null,
    created_at timestamptz not null default now()
);

-- THE CLAIM. Without this being unique, two workers both insert and the
-- user gets the same announcement twice.
create unique index if not exists announcer_fire_log_claim_idx
    on announcer_fire_log (user_id, client_id, fire_date, fire_time);

-- For the cleanup job; nothing needs yesterday's log.
create index if not exists announcer_fire_log_date_idx
    on announcer_fire_log (fire_date);

-- Opt out per announcement. Some are worth a notification and some are
-- only worth saying out loud while you are at the desk.
alter table announcer_items
    add column if not exists notify boolean not null default true;

comment on column announcer_items.notify is
    'True = also send a push notification at each scheduled time, which '
    'is the only thing that reaches a locked phone. False = speak it only '
    'when the app is open and visible.';

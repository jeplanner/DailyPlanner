-- ============================================================
--  DailyPlanner — Day Board pinned notification
--
--  One row per user recording whether today's Day Board summary
--  should be kept pinned in the notification shade, and the state
--  the background scheduler needs to refresh it WITHOUT spamming.
--
--  WHY THERE IS A SIGNATURE COLUMN, AND WHY IT MATTERS.
--  The obvious design is "re-send every 15 minutes". That pushes an
--  identical notification most of the time — the day does not change
--  every quarter hour — and every one of those costs battery and push
--  quota for nothing. Instead the scheduler hashes the summary TEXT it
--  is about to send and compares it with the last one. It sends when
--  the CONTENT CHANGES (an event starts, a task is ticked) and
--  otherwise stays silent. `last_signature` is what makes that
--  comparison possible across processes and restarts.
--
--  `last_sent_at` is a THROTTLE FLOOR, not a timer: even when the
--  content changes it will not re-send more often than
--  min_interval_minutes, so a burst of edits cannot produce a burst of
--  notifications.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists day_board_pins (
    user_id              text primary key,

    -- The toggle. False rather than a deleted row, so turning it off
    -- and on again keeps the user's window and cadence.
    is_active            boolean     not null default false,

    -- Local hours (0-23) between which the pin refreshes. Outside this
    -- window the scheduler leaves it alone: a summary that updates at
    -- 3am is a notification that wakes you to say nothing.
    start_hour           smallint    not null default 7,
    end_hour             smallint    not null default 22,

    -- Throttle floor in minutes. Content-triggered sends still respect
    -- this, so ticking five checklist items in a row is one refresh.
    min_interval_minutes smallint    not null default 10,

    -- What the scheduler last actually sent, and when. The signature is
    -- a hash of the title+body, so "has anything the user would SEE
    -- changed?" is one string comparison.
    last_signature       text,
    last_sent_at         timestamptz,

    -- The date the current pin belongs to. The scheduler forces a send
    -- when this rolls over, so the first refresh of a new morning always
    -- lands even if the text happens to match yesterday's.
    pinned_date          date,

    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

-- The scheduler's hot path is "every active pin", once a minute. Without
-- this it is a full scan of the table on every tick.
create index if not exists day_board_pins_active_idx
    on day_board_pins (is_active)
    where is_active;

-- Guard rails on the window, so a bad client cannot store something the
-- scheduler would then have to defend against on every tick.
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'day_board_pins_hours_ck'
    ) then
        alter table day_board_pins
            add constraint day_board_pins_hours_ck
            check (start_hour between 0 and 23
                   and end_hour between 0 and 23
                   and min_interval_minutes between 1 and 240);
    end if;
end $$;

-- Keep updated_at honest without the application having to remember.
create or replace function day_board_pins_touch()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists day_board_pins_touch_trg on day_board_pins;
create trigger day_board_pins_touch_trg
    before update on day_board_pins
    for each row execute function day_board_pins_touch();

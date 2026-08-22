-- ============================================================
--  DailyPlanner — login history, with where the sign-in came from
--
--  Until now the only trace of a sign-in was `users.last_login_at`,
--  a single timestamp that each login overwrote. That answers "when
--  was the last time" and nothing else — it cannot answer "was that
--  me?", which is the only question a login history exists to answer.
--
--  WHY LOCATION IS STORED, NOT DERIVED AT READ TIME.
--  An IP's geography changes: addresses are reassigned, and a lookup
--  run months later can return a different city than the one the
--  sign-in actually came from. Resolving once, at the moment of the
--  login, and keeping the answer is the only version that stays true.
--  It also means the history page renders without calling anyone.
--
--  WHY THE LOOKUP IS ALLOWED TO FAIL.
--  Geolocation is a best-effort external call. `location_status`
--  records WHY a row has no city — private network, lookup failed,
--  never attempted — so the page can say "on this network" or "could
--  not determine" instead of showing a blank cell that looks like a
--  bug.
--
--  Times are stored in UTC (`at`). Rendering is the reader's problem:
--  the page converts to the user's own timezone, which for this
--  household is Asia/Kolkata (IST).
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists login_events (
    id               uuid primary key default gen_random_uuid(),
    user_id          text        not null,
    at               timestamptz not null default now(),

    -- Network. `ip` is kept because it is the only durable identifier
    -- of a session's origin; everything else here is derived from it.
    ip               text,
    user_agent       text,

    -- Derived once, at login. All nullable: a lookup that fails must
    -- not stop the login from being recorded.
    city             text,
    region           text,
    country          text,
    country_code     text,
    timezone         text,
    location_status  text not null default 'pending',

    -- What happened. Failed attempts are recorded too — a history that
    -- only shows successes cannot show someone trying to get in.
    outcome          text not null default 'success',

    created_at       timestamptz not null default now()
);

-- The page reads "this user's logins, newest first" and nothing else.
create index if not exists login_events_user_at_idx
    on login_events (user_id, at desc);

-- Adding the columns separately as well, so a table created by an
-- earlier partial run of this file gains anything it is missing. Every
-- statement is guarded, which is what makes re-running safe.
alter table login_events add column if not exists ip              text;
alter table login_events add column if not exists user_agent      text;
alter table login_events add column if not exists city            text;
alter table login_events add column if not exists region          text;
alter table login_events add column if not exists country         text;
alter table login_events add column if not exists country_code    text;
alter table login_events add column if not exists timezone        text;
alter table login_events add column if not exists location_status text not null default 'pending';
alter table login_events add column if not exists outcome         text not null default 'success';

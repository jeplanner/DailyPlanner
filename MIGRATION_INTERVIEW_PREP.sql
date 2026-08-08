-- ============================================================
--  DailyPlanner — INTERVIEW PREP COACH
--
--  A motivating, on-track prep tracker for a senior interview (built
--  for a Senior Director / Head of Technical Program Management run).
--
--  Four tables:
--    interview_prep      one row per user — the plan (role, target date,
--                        daily goal). Streak/readiness are computed on
--                        the fly from sessions/topics, not stored.
--    interview_topics    syllabus items with a 0–4 confidence level,
--                        grouped by category (behavioral / system_design
--                        / tpm / executive / domain). Seeded per-user in
--                        the app on first visit, then fully editable.
--    interview_stories   STAR behavioral story bank (Situation / Task /
--                        Action / Result) tagged to a competency, with a
--                        "rehearsed" flag.
--    interview_sessions  daily practice log (minutes + focus + reflection)
--                        — drives the streak and today's goal.
--
--  Soft-delete only (deleted_at), per the project convention.
--
--  Safe to re-run (idempotent).
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists interview_prep (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null unique references users(id) on delete cascade,
  role_title         text not null default 'Senior Director, Technical Program Management',
  target_date        date,
  daily_goal_minutes int  not null default 45 check (daily_goal_minutes >= 0),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  deleted_at         timestamptz
);

create table if not exists interview_topics (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  category    text not null default 'domain',
  title       text not null,
  confidence  smallint not null default 0 check (confidence between 0 and 4),
  notes       text,
  position    int not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);
create index if not exists interview_topics_user_idx
  on interview_topics (user_id, category, position) where deleted_at is null;

create table if not exists interview_stories (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  title       text not null,
  competency  text,
  situation   text,
  task        text,
  action      text,
  result      text,
  rehearsed   boolean not null default false,
  position    int not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);
create index if not exists interview_stories_user_idx
  on interview_stories (user_id, position, created_at) where deleted_at is null;

create table if not exists interview_sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references users(id) on delete cascade,
  practiced_on date not null default current_date,
  minutes      int  not null default 0 check (minutes >= 0),
  focus        text,
  reflection   text,
  created_at   timestamptz not null default now(),
  deleted_at   timestamptz
);
create index if not exists interview_sessions_user_idx
  on interview_sessions (user_id, practiced_on desc) where deleted_at is null;

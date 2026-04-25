-- ============================================================
--  DailyPlanner — WEEKLY REVIEW (3 structured prompts)
--
--  Replaces the single free-form weekly reflection with three
--  scaffolded prompts that drive better retros:
--
--    went_well   — what worked well this week
--    didnt_go    — what didn't, what got dropped
--    one_change  — one specific change for next week
--
--  Stored per-week (one row per user × week_start) so the data
--  is easy to query and chart over time.
--
--  Safe to re-run.
-- ============================================================

create table if not exists weekly_reviews (
  user_id     text not null,
  week_start  date not null,
  went_well   text,
  didnt_go    text,
  one_change  text,
  updated_at  timestamptz default now(),
  created_at  timestamptz default now(),
  unique (user_id, week_start)
);

create index if not exists weekly_reviews_user_idx
  on weekly_reviews (user_id, week_start desc);

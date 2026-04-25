-- ============================================================
--  DailyPlanner — DAILY INTENT ("One Big Thing")
--
--  Adds two columns to daily_meta so the user can capture a single
--  high-level focus per day, separate from the task list:
--
--    daily_intent       — free text (e.g. "Ship the auth fix",
--                         "Be present with the kids"). Not always
--                         a task — sometimes an aspiration or theme.
--    daily_intent_done  — boolean toggle so the user can mark the
--                         intent achieved (visual celebration cue).
--
--  Safe to re-run: both columns guarded with `if not exists`.
--
--  Code degrades gracefully when these columns are missing — the
--  daily summary just doesn't render the "Today's Focus" card.
-- ============================================================

alter table daily_meta
  add column if not exists daily_intent      text,
  add column if not exists daily_intent_done boolean default false;

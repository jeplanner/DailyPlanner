-- ============================================================
--  DailyPlanner — GOAL COUNTDOWN / GOAL PLANNER
--
--  Adds a deadline-countdown layer on top of the EXISTING OKR schema
--  (objectives → key_results → initiatives) rather than introducing a
--  second, parallel goals table. The /goal-planner page, the /goals OKR
--  page and the interview-prep dashboard all read the same rows, so a
--  goal entered in one place counts down in all of them.
--
--    objectives.target_at            — the deadline as a MOMENT, not a
--                                      date. `target_date` only resolves
--                                      to a day, so "3h 12m pending" is
--                                      meaningless without this. Kept
--                                      alongside target_date (not
--                                      replacing it) so existing OKR
--                                      rows and code keep working; the
--                                      app falls back to end-of-day in
--                                      the user's timezone when target_at
--                                      is null.
--    objectives.daily_commit_minutes — how many minutes/day the user has
--                                      promised this goal. Turns "44 days
--                                      left" into a real time BUDGET:
--                                      44 × 120 min = 88h available.
--    objectives.effort_minutes       — how much work the goal is believed
--                                      to need. Budget minus effort is
--                                      the shortfall that tells you a
--                                      goal is infeasible while there is
--                                      still time to re-scope.
--    objectives.is_primary           — the one pinned goal that gets the
--                                      big flashing countdown. Several
--                                      live countdowns is a wall of
--                                      clocks and no focus.
--    objectives.flash_enabled        — per-goal opt-out of the urgency
--                                      pulse, for goals that are simply
--                                      dated and not urgent.
--
--    key_results.due_at              — an interim checkpoint. Without
--                                      these a six-month goal shows a
--                                      countdown that is useless for
--                                      five of them; the page surfaces
--                                      the NEXT checkpoint, not just the
--                                      finish line.
--
--  Safe to re-run: every column guarded with `if not exists`, and the
--  partial index is `if not exists` too.
--
--  Code degrades gracefully when these columns are missing — the goal
--  planner falls back to target_date and simply hides the budget line.
-- ============================================================

alter table objectives
  add column if not exists target_at            timestamptz,
  add column if not exists daily_commit_minutes int,
  add column if not exists effort_minutes       int,
  add column if not exists is_primary           boolean default false,
  add column if not exists flash_enabled        boolean default true;

alter table key_results
  add column if not exists due_at timestamptz;

-- At most one pinned goal per user. A partial unique index is the
-- cheapest way to enforce it: rows with is_primary false are not indexed,
-- so unpinned goals never collide.
create unique index if not exists objectives_one_primary_per_user
  on objectives (user_id)
  where is_primary and not is_deleted;

-- The planner lists by deadline, so index the column it sorts on.
create index if not exists objectives_target_at_idx
  on objectives (user_id, target_at)
  where not is_deleted;

-- Backfill: give existing dated objectives a moment to count down to, so
-- the new page is useful immediately instead of looking empty. End of day
-- is the honest reading of a bare date ("due on the 14th" means "by the
-- end of the 14th"). Only touches rows that have a date and no moment.
do $$
begin
  if exists (
    select 1 from information_schema.columns
     where table_name = 'objectives' and column_name = 'target_at'
  ) then
    update objectives
       set target_at = (target_date + time '23:59:59') at time zone 'Asia/Kolkata'
     where target_date is not null
       and target_at is null;
  end if;
end $$;

-- ────────────────────────────────────────────────────────────
--  ADDENDUM — typed percent complete
--
--  Progress rolls up from an objective's key results, which is the right
--  default: a KR is a measurable claim and an average of them is honest.
--  But a goal entered on the planner has NO key results, so it scored 0
--  forever and the coach scolded it permanently with no way to answer back.
--
--    objectives.manual_progress — 0-100, nullable. When set it WINS over the
--                                 key-result roll-up and the UI labels the
--                                 number "typed" so the two can never be
--                                 silently confused. Clearing it (null)
--                                 returns the goal to the automatic roll-up,
--                                 so the override is always reversible.
--
--  Safe to re-run: guarded with `if not exists`, and the constraint is added
--  only when it is absent.
-- ────────────────────────────────────────────────────────────

alter table objectives
  add column if not exists manual_progress int;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'objectives_manual_progress_range'
  ) then
    alter table objectives
      add constraint objectives_manual_progress_range
      check (manual_progress is null or (manual_progress >= 0 and manual_progress <= 100));
  end if;
end $$;

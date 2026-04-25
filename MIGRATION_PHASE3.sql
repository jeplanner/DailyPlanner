-- ============================================================
--  DailyPlanner — PHASE 3 features (PM audit response)
--
--  Bundles four small additions:
--    1. task_time_logs    — actual time spent on tasks (timer)
--    2. relationships     — life-OS contact tracker
--    3. daily_meta        — gratitude column (split from reflection)
--    4. key_results       — auto_progress flag (opt-in to roll-up)
--
--  Safe to re-run: every CREATE / ALTER guarded.
-- ============================================================

-- ─────────────────────────────────────────────
-- 1. TIME TRACKING — actual minutes per task
--
--  One row per timer session. Aggregating by task_id gives total
--  actual minutes; aggregating by source+date gives daily focus
--  time per source ("Eisenhower vs project work" comparison).
--
--  Both task IDs are nullable so a future "track ad-hoc time"
--  feature (no linked task) doesn't need another table.
-- ─────────────────────────────────────────────
create table if not exists task_time_logs (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null,
  source          text not null,           -- 'matrix' | 'project' | 'event' | 'adhoc'
  matrix_task_id  uuid,                    -- todo_matrix.id when source='matrix'
  project_task_id uuid,                    -- project_tasks.task_id when source='project'
  event_id        uuid,                    -- daily_events.id when source='event'
  label           text,                    -- ad-hoc label when no task linked
  started_at      timestamptz not null,
  ended_at        timestamptz,             -- null = currently running
  duration_seconds int,                    -- denormalized for fast sums
  notes           text,
  created_at      timestamptz default now()
);
create index if not exists task_time_logs_user_date_idx
  on task_time_logs (user_id, started_at desc);
create index if not exists task_time_logs_matrix_idx
  on task_time_logs (matrix_task_id) where matrix_task_id is not null;
create index if not exists task_time_logs_project_idx
  on task_time_logs (project_task_id) where project_task_id is not null;


-- ─────────────────────────────────────────────
-- 2. RELATIONSHIPS — "when did I last call mom?"
--
--  One row per person the user wants to stay in touch with.
--  cadence_days is the desired frequency; the daily summary
--  surfaces overdue contacts based on (now - last_contact_date).
-- ─────────────────────────────────────────────
create table if not exists relationships (
  id                  uuid primary key default gen_random_uuid(),
  user_id             text not null,
  name                text not null,
  relation            text,                -- 'family' | 'friend' | 'mentor' | etc.
  cadence_days        int default 14,      -- how often to reach out
  last_contact_date   date,
  notes               text,
  is_archived         boolean default false,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);
create index if not exists relationships_user_idx
  on relationships (user_id, is_archived);


-- ─────────────────────────────────────────────
-- 3. GRATITUDE — separate from open-ended reflection
--
--  Reflection is "how did the day go?" (analytical).
--  Gratitude is "what am I thankful for?" (appreciative).
--  Mixing them dilutes both, per how Daily Stoic / Five Minute
--  Journal split them.
-- ─────────────────────────────────────────────
alter table daily_meta
  add column if not exists gratitude text;


-- ─────────────────────────────────────────────
-- 4. OKR AUTO-PROGRESS — opt-in per KR
--
--  When auto_progress=true, the KR's current_value is recomputed
--  from the share of completed initiatives → tasks. When false,
--  the existing manual flow keeps working.
-- ─────────────────────────────────────────────
alter table key_results
  add column if not exists auto_progress boolean default false;

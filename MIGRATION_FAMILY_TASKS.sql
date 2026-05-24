-- ============================================================
--  DailyPlanner — FAMILY TASKS (cross-user assignment)
--
--  Lets allowlisted users (same CHAT_USER_EMAILS list that gates
--  the family chat) create tasks for each other. When the
--  assignee logs in, the task shows up under their "For me"
--  filter on the /family-tasks page.
--
--  Both creator and assignee names are denormalized so historical
--  tasks render correctly even after a user renames, and so the
--  list view doesn't need a join.
--
--  Soft-delete only (`deleted_at`) per the project convention.
--
--  Safe to re-run.
-- ============================================================

create table if not exists family_tasks (
  id               uuid primary key default gen_random_uuid(),

  title            text not null
                   check (char_length(title) between 1 and 300),
  notes            text,

  -- Creator. ON DELETE SET NULL so a removed user doesn't take
  -- their tasks with them — the row stays, just orphaned with
  -- created_by = null. created_by_name preserves the display label.
  created_by       uuid references users(id) on delete set null,
  created_by_name  text not null,

  -- Assignee. ON DELETE CASCADE: if the assignee is removed, their
  -- inbox of tasks goes with them (nobody else can act on them
  -- meaningfully). Reassignment is the path for "keep this task".
  assigned_to      uuid not null references users(id) on delete cascade,
  assigned_to_name text not null,

  due_date         date,
  done_at          timestamptz,
  deleted_at       timestamptz,
  created_at       timestamptz not null default now()
);

-- Primary access path: "give me all tasks assigned to me". The "By me"
-- view (created_by = viewer) hits the table less often, so we skip a
-- dedicated index on it for now — a seq scan on a small family-sized
-- table is cheap.
create index if not exists family_tasks_assigned_to_idx
  on family_tasks (assigned_to, done_at);

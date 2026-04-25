-- ============================================================
--  DailyPlanner — PARKING: revised_due_date
--
--  Tasks with elapsed due dates were piling up in the Eisenhower
--  quadrants and burying today's actual priorities. This migration
--  adds a `revised_due_date` column to the two tables that feed the
--  matrix:
--    • todo_matrix     (standalone Eisenhower tasks)
--    • project_tasks   (project initiative tasks)
--
--  Semantics:
--    - `due_date` (existing) — original deadline. Never overwritten
--      by the reschedule UI. Keeps the audit trail intact.
--    - `revised_due_date` (new) — current intent. Defaults to due_date
--      on insert; mutated by /todo/revise-date or /projects/tasks/
--      update-date going forward.
--    - "Parked" = open task whose effective date (coalesce of
--      revised_due_date, due_date, task_date) is before today. Such
--      rows are excluded from quadrant queries; the /todo page
--      surfaces them in a separate Parked section.
--
--  Safe to re-run.
-- ============================================================

alter table todo_matrix
  add column if not exists revised_due_date date;

alter table project_tasks
  add column if not exists revised_due_date date;

-- Backfill — point the new column at the existing schedule field so
-- the parked-vs-active filter behaves identically to today before the
-- user makes any explicit revision.
update todo_matrix
   set revised_due_date = coalesce(task_date, plan_date)
 where revised_due_date is null;

update project_tasks
   set revised_due_date = due_date
 where revised_due_date is null
   and due_date is not null;

create index if not exists todo_matrix_revised_idx
  on todo_matrix (user_id, revised_due_date)
  where is_deleted = false;

-- project_tasks uses `is_eliminated` for soft-delete (not is_deleted).
create index if not exists project_tasks_revised_idx
  on project_tasks (user_id, revised_due_date)
  where is_eliminated = false;

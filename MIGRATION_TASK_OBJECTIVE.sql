-- ============================================================
--  DailyPlanner — ATTACH A TASK STRAIGHT TO A GOAL
--
--  Asked 2026-08-30: "make the projects simpler. I want to attach
--  just goals to tasks. dont want all this intiative,epic
--  hierarchy. disable for the timebeing."
--
--  WHAT "GOAL" MEANS HERE.
--  routes/goals.py says it in its own header: "what earlier
--  iterations called a Goal is now an Objective across the whole
--  codebase". So a goal is an OBJECTIVE, and this column lets a
--  task point at one without walking Objective → Key Result →
--  Initiative to get there.
--
--  WHY THE MIDDLE OF THAT LADDER IS BEING SKIPPED.
--  Measured the day this was asked for, on the live data:
--      key results whose current_value has EVER moved:  0 of 28
--      tasks linked to a key result:                    3 of 120
--      objectives with no key results at all:           several
--  The measurement layer that justifies Key Results and
--  Initiatives is not being used. The structure was being complied
--  with, not used.
--
--  NOTHING IS REMOVED. initiative_id, key_result_id and epic_id
--  keep their values and keep working; the app simply stops making
--  you go through them to file a task. The layers are hidden behind
--  a flag (config.SIMPLE_GOALS) because "for the timebeing" means
--  reversible, and turning it off restores the old pickers exactly.
--
--  Safe to re-run.
-- ============================================================

alter table project_tasks
  add column if not exists objective_id uuid;

-- "Everything under this goal", which is what the task list and the
-- goal filter both ask.
create index if not exists project_tasks_objective_idx
  on project_tasks (objective_id)
  where objective_id is not null;

-- Backfill: a task that already ladders up to an objective through an
-- initiative gets that objective stamped on it directly, so switching
-- to the simple view does not make existing work look unassigned.
-- Left join through initiatives → key_results → objectives.
do $$
begin
  if exists (select 1 from information_schema.tables
             where table_name = 'initiatives')
     and exists (select 1 from information_schema.tables
                 where table_name = 'key_results') then
    update project_tasks t
       set objective_id = kr.objective_id
      from initiatives i
      join key_results kr on kr.id = i.key_result_id
     where t.initiative_id = i.id
       and t.objective_id is null
       and kr.objective_id is not null;

    -- Legacy rows that were linked straight to a key result.
    update project_tasks t
       set objective_id = kr.objective_id
      from key_results kr
     where t.key_result_id = kr.id
       and t.objective_id is null
       and kr.objective_id is not null;
  end if;
end $$;

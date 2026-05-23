-- ============================================================
--  DailyPlanner — SPRINTS (per-project time-boxes)
--
--  A sprint is a named bucket of work for a project, usually 1-2
--  weeks. Tasks can be optionally tagged to a sprint regardless of
--  which epic they live in, so the same "Demo for Acme" task in the
--  Sales > Outreach epic can be planned for Sprint 4.
--
--  Scope: per-project. Each project owns its own sprint list (Sprint 1,
--  Sprint 2, ... by default; user can rename). Tasks reference a
--  sprint via nullable project_tasks.sprint_id — null means
--  "unassigned / backlog".
--
--  Dates (starts_on / ends_on) are optional so you can use sprints
--  as ad-hoc buckets without committing to a calendar.
--
--  is_active is a small UX flag that drives ordering in pickers
--  (active sprints float to the top). The UI treats it as a hint, not
--  a constraint — a task can still be tagged to an inactive sprint.
--
--  Soft-delete via is_deleted; tasks keep their sprint_id pointer so a
--  restore re-links them.
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists sprints (
    id           uuid primary key default gen_random_uuid(),
    user_id      text not null,
    project_id   uuid not null references projects(project_id) on delete cascade,
    name         text not null,
    starts_on    date,
    ends_on      date,
    is_active    boolean default false,
    order_index  int default 0,
    is_deleted   boolean default false,
    deleted_at   timestamptz,
    created_at   timestamptz default now()
);

create index if not exists ix_sprints_user_project
    on sprints (user_id, project_id)
    where is_deleted = false;

create index if not exists ix_sprints_active
    on sprints (project_id, is_active)
    where is_deleted = false and is_active = true;

alter table if exists project_tasks
    add column if not exists sprint_id uuid references sprints(id) on delete set null;

create index if not exists ix_project_tasks_user_sprint
    on project_tasks (user_id, sprint_id)
    where is_eliminated = false and sprint_id is not null;

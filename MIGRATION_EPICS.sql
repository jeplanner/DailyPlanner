-- ============================================================
--  DailyPlanner — EPICS layer between Initiative and Task
--
--  Adds the missing "Epic" tier the projects page asked for. Tree
--  becomes:
--    Project ─▸ Objective (OKR) ─▸ Key Result ─▸ Initiative ─▸ Epic ─▸ Task
--
--  An Epic is a chunk of work under an Initiative that bundles a set
--  of tasks. Same lifecycle pattern as initiatives:
--    - soft-delete only (is_deleted + deleted_at)
--    - order_index for manual sort
--    - status active|paused|done|cancelled (free-text for now, same as initiatives)
--
--  project_tasks.epic_id is nullable so existing tasks survive
--  unchanged and can be tied to an epic later from the UI. When an
--  epic is soft-deleted we DO keep task pointers intact so a restore
--  brings the linkage back, matching how delete_initiative behaves.
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists epics (
    id             uuid primary key default gen_random_uuid(),
    user_id        text not null,
    initiative_id  uuid not null references initiatives(id) on delete cascade,
    title          text not null,
    description    text,
    status         text default 'active',
    order_index    int default 0,
    is_deleted     boolean default false,
    deleted_at     timestamptz,
    created_at     timestamptz default now()
);

create index if not exists ix_epics_user_initiative
    on epics (user_id, initiative_id)
    where is_deleted = false;

alter table if exists project_tasks
    add column if not exists epic_id uuid references epics(id) on delete set null;

-- NOTE: project_tasks uses `is_eliminated` for soft-delete, not the
-- `is_deleted` convention used elsewhere on the OKR tree. Match the
-- actual column name in the partial-index predicate.
create index if not exists ix_project_tasks_user_epic
    on project_tasks (user_id, epic_id)
    where is_eliminated = false and epic_id is not null;

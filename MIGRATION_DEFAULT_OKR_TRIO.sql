-- ============================================================
--  DailyPlanner — DEFAULT OKR / INITIATIVE / EPIC per project
--
--  Every project now owns a default trio:
--
--      Inbox (objective, is_default=true)
--        └── Catch-all (key_result, is_default=true)
--              └── Inbox (initiative, is_default=true)
--                    └── Inbox (epic, is_default=true)
--
--  Tasks created without an explicit epic land in the project's
--  default epic. The defaults are visible in the OKR tree (so the
--  user knows where unclassified work lives) but the UI prevents:
--    - creating a new Initiative under the default OKR
--    - creating a new Epic under the default Initiative
--  Real organisation forces a real OKR/Initiative to be created
--  first, which keeps the tree meaningful.
--
--  is_default is a boolean on each of the four tables. Partial
--  unique indexes guarantee at most one default per scope.
--
--  Backfill: a do-block scans every active project and inserts a
--  trio if one doesn't already exist. Idempotent — re-running is a
--  no-op for projects already provisioned. Skips archived projects
--  (is_archived = true).
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

alter table if exists objectives  add column if not exists is_default boolean default false;
alter table if exists key_results add column if not exists is_default boolean default false;
alter table if exists initiatives add column if not exists is_default boolean default false;
alter table if exists epics       add column if not exists is_default boolean default false;

-- At most one default of each kind per scope. WHERE clauses skip
-- non-default rows so we don't pay the constraint cost on most rows.
create unique index if not exists ux_objectives_default_per_project
    on objectives (project_id)
    where is_default = true and is_deleted = false;

create unique index if not exists ux_key_results_default_per_objective
    on key_results (objective_id)
    where is_default = true and is_deleted = false;

create unique index if not exists ux_initiatives_default_per_kr
    on initiatives (key_result_id)
    where is_default = true and is_deleted = false;

create unique index if not exists ux_epics_default_per_initiative
    on epics (initiative_id)
    where is_default = true and is_deleted = false;

-- Backfill: ensure every active project has the trio.
-- NOTE on the casts: in some installs `projects.user_id` is text while
-- `objectives.user_id` (and siblings) are uuid. In raw SQL Postgres
-- won't auto-cast text → uuid, so we cast explicitly. The cast is a
-- no-op when the source is already uuid, so it's safe either way.
do $$
declare
    p           record;
    uid_uuid    uuid;
    obj_id      uuid;
    kr_id       uuid;
    init_id     uuid;
    epic_id     uuid;
begin
    for p in
        select project_id, user_id
        from projects
        where coalesce(is_archived, false) = false
    loop
        -- One conversion per project; reused for all four inserts.
        begin
            uid_uuid := p.user_id::uuid;
        exception when invalid_text_representation then
            -- user_id isn't a uuid string — skip this project rather
            -- than blow up the whole backfill.
            continue;
        end;

        -- Skip if a default objective is already present for this project.
        select id into obj_id
          from objectives
          where project_id = p.project_id
            and is_default = true
            and coalesce(is_deleted, false) = false
          limit 1;

        if obj_id is null then
            insert into objectives (user_id, project_id, title, is_default, status, time_horizon)
                values (uid_uuid, p.project_id, 'Inbox', true, 'active', 'ongoing')
                returning id into obj_id;
        end if;

        select id into kr_id
          from key_results
          where objective_id = obj_id
            and is_default = true
            and coalesce(is_deleted, false) = false
          limit 1;

        if kr_id is null then
            insert into key_results (user_id, objective_id, title, target_value, unit, is_default)
                values (uid_uuid, obj_id, 'Catch-all', 100, '%', true)
                returning id into kr_id;
        end if;

        select id into init_id
          from initiatives
          where key_result_id = kr_id
            and is_default = true
            and coalesce(is_deleted, false) = false
          limit 1;

        if init_id is null then
            insert into initiatives (user_id, key_result_id, title, is_default, status)
                values (uid_uuid, kr_id, 'Inbox', true, 'active')
                returning id into init_id;
        end if;

        select id into epic_id
          from epics
          where initiative_id = init_id
            and is_default = true
            and coalesce(is_deleted, false) = false
          limit 1;

        if epic_id is null then
            insert into epics (user_id, initiative_id, title, is_default, status)
                values (uid_uuid, init_id, 'Inbox', true, 'active');
        end if;
    end loop;
end $$;

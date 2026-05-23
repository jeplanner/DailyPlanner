-- ============================================================
--  DailyPlanner — combined migration for everything shipped on
--  2026-05-23. One file, idempotent, can be run end-to-end in the
--  Supabase SQL editor.
--
--  What this does (in order):
--
--    1. EPICS LAYER
--         Adds an `epics` table between Initiative and Task.
--         project_tasks.epic_id (nullable FK).
--
--    2. OFFLINE WRITE IDEMPOTENCY
--         client_id text + partial unique index on
--         (user_id, client_id) for quick_bucket and inbox_links
--         so the SW's offline-write replay doesn't dupe rows.
--
--    3. DEFAULT OKR/INITIATIVE/EPIC TRIO PER PROJECT
--         is_default boolean on objectives / key_results /
--         initiatives / epics. Partial unique indexes guarantee
--         at most one default of each kind per parent. Backfill
--         do-block provisions a default chain for every project.
--         Casts text → uuid where projects.user_id is text and
--         the OKR-tree user_id columns are uuid.
--
--    4. LABEL RENAME
--         Renames the default rows from Inbox/Catch-all/Inbox/Inbox
--         to Uncategorized / — / General / Misc. Skips rows where
--         the user has already customised the title.
--
--    5. SPRINTS
--         Per-project `sprints` table. Tasks may opt into a
--         sprint via nullable project_tasks.sprint_id.
--
--  Every block uses CREATE / ALTER / INSERT … IF NOT EXISTS or
--  guarded UPDATEs, so re-running this script is a no-op once
--  applied.
-- ============================================================

create extension if not exists pgcrypto;


-- ────────────────────────────────────────────────────────────
-- 1. EPICS
-- ────────────────────────────────────────────────────────────

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

-- project_tasks uses `is_eliminated` for soft-delete (legacy convention),
-- not the `is_deleted` used on the OKR-tree tables.
create index if not exists ix_project_tasks_user_epic
    on project_tasks (user_id, epic_id)
    where is_eliminated = false and epic_id is not null;


-- ────────────────────────────────────────────────────────────
-- 2. OFFLINE WRITE IDEMPOTENCY
--    client_id stamped by sync-queue.js on every queued mutating
--    request; partial unique index gates the upsert path so
--    replays return the existing row rather than create dupes.
-- ────────────────────────────────────────────────────────────

alter table if exists quick_bucket
    add column if not exists client_id text;

alter table if exists inbox_links
    add column if not exists client_id text;

create unique index if not exists ux_quick_bucket_user_client
    on quick_bucket (user_id, client_id)
    where client_id is not null;

create unique index if not exists ux_inbox_links_user_client
    on inbox_links (user_id, client_id)
    where client_id is not null;


-- ────────────────────────────────────────────────────────────
-- 3. DEFAULT OKR / KR / INITIATIVE / EPIC PER PROJECT
-- ────────────────────────────────────────────────────────────

alter table if exists objectives  add column if not exists is_default boolean default false;
alter table if exists key_results add column if not exists is_default boolean default false;
alter table if exists initiatives add column if not exists is_default boolean default false;
alter table if exists epics       add column if not exists is_default boolean default false;

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

-- Backfill the default trio for every active project. Inserts run only
-- when a default doesn't already exist for that scope, so this is safe
-- to re-run. user_id is cast to uuid because some installs have
-- projects.user_id as text while objectives.user_id (and siblings) are
-- uuid; raw SQL won't auto-cast.
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
        begin
            uid_uuid := p.user_id::uuid;
        exception when invalid_text_representation then
            continue;        -- skip projects with non-uuid user_id
        end;

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


-- ────────────────────────────────────────────────────────────
-- 4. RENAME default rows to the friendlier labels.
--    Match only on the original auto-titles so user-customised
--    rows are left alone.
-- ────────────────────────────────────────────────────────────

update objectives
   set title = 'Uncategorized'
 where is_default = true
   and coalesce(is_deleted, false) = false
   and title = 'Inbox';

update key_results
   set title = '—'
 where is_default = true
   and coalesce(is_deleted, false) = false
   and title = 'Catch-all';

update initiatives
   set title = 'General'
 where is_default = true
   and coalesce(is_deleted, false) = false
   and title = 'Inbox';

update epics
   set title = 'Misc'
 where is_default = true
   and coalesce(is_deleted, false) = false
   and title = 'Inbox';


-- ────────────────────────────────────────────────────────────
-- 5. SPRINTS
--    Per-project time-boxes. Tasks may opt into a sprint
--    independently of the OKR tree.
-- ────────────────────────────────────────────────────────────

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

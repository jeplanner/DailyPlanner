-- ============================================================
--  DailyPlanner — DEFAULT PROJECT marker
--
--  Backs the "@-tag checklist → tasks" feature: any task that doesn't
--  carry an explicit @ProjectName tag (or carries an unknown one)
--  lands in the user's default project — an "Inbox" project that the
--  app creates lazily on first conversion.
--
--  Schema change:
--    projects.is_default boolean default false
--    + partial unique index so a user has at most one default at a
--      time (only counts unarchived rows).
--
--  Safe to re-run.
-- ============================================================

alter table projects
  add column if not exists is_default boolean default false;

-- One active default per user. Archived projects don't count, so a
-- user can rotate which project is the default by archiving the old
-- one before flagging a new one.
create unique index if not exists projects_one_default_per_user
  on projects (user_id)
  where is_default = true and is_archived = false;

create index if not exists projects_user_default_idx
  on projects (user_id) where is_default = true;

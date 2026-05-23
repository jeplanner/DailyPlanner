-- ============================================================
--  DailyPlanner — rename the default OKR/Initiative/Epic labels.
--
--  The first version of the default-trio migration named every row
--  "Inbox" (and the KR "Catch-all"), which collided visually with
--  the top-nav Inbox feature. New labels:
--
--      Objective    : "Uncategorized"
--      Key Result   : "—"
--      Initiative   : "General"
--      Epic         : "Misc"
--
--  WHERE clauses match only rows still using the original auto-
--  created titles, so any project where the user has manually
--  renamed a default row keeps that custom name. Safe to re-run.
--
--  PREREQ: MIGRATION_DEFAULT_OKR_TRIO.sql adds the is_default
--  column and backfills the rows being renamed below. The
--  add-column statements here are belt-and-braces so this file
--  can run in any order without erroring — they're no-ops once
--  the trio migration has run. The UPDATEs do real work only
--  after the trio migration has actually inserted matching rows.
-- ============================================================

alter table if exists objectives  add column if not exists is_default boolean default false;
alter table if exists key_results add column if not exists is_default boolean default false;
alter table if exists initiatives add column if not exists is_default boolean default false;
alter table if exists epics       add column if not exists is_default boolean default false;

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

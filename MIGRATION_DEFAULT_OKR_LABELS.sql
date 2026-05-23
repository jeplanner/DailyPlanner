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
-- ============================================================

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

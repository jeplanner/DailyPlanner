-- ============================================================
--  Quick Bucket — "Today's Top 5" panel
--
--  Two columns on quick_bucket let a row appear in today's Top-5
--  panel: top5_date stamps which day the user pinned it for, and
--  top5_position is its slot within the panel (1..5).
--
--  Auto-roll (handled in Python): on each page load, any incomplete
--  past-day pins get bumped to today so they "carry over". Closed
--  (is_done=true) rows keep their old top5_date so they stay
--  crossed-out in the panel for the rest of that day, then fall off.
--
--  Idempotent — safe to re-run.
-- ============================================================

alter table quick_bucket
  add column if not exists top5_date     date;
alter table quick_bucket
  add column if not exists top5_position smallint;

create index if not exists quick_bucket_user_top5_idx
  on quick_bucket (user_id, top5_date)
  where top5_date is not null;

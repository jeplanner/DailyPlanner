-- ============================================================
--  DailyPlanner — Quick Bucket items scheduled into a calendar slot
--
--  Bulk-selecting bucket items and dropping them into one calendar
--  slot needs somewhere to record WHERE they went. Without it the only
--  options are to delete the items (losing them) or to mark them done
--  (which is a lie — they are scheduled, not finished).
--
--  `scheduled_event_id` points at the daily_events row that now
--  carries them; `scheduled_for` is that slot's date, denormalised so
--  the bucket list can show "on the calendar Fri" without a join.
--  Both null for an item that has never been scheduled.
--
--  The feature degrades without this: the calendar slot is still
--  created and only the back-link is skipped, so running it is about
--  the bucket being able to show where a row went.
--
--  Idempotent: safe to run repeatedly.
-- ============================================================

alter table quick_bucket add column if not exists scheduled_event_id text;
alter table quick_bucket add column if not exists scheduled_for      date;

create index if not exists quick_bucket_scheduled_idx
    on quick_bucket (user_id, scheduled_for);

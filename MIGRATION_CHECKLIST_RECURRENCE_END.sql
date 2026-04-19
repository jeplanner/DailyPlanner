-- ============================================================
--  Add optional recurrence end-date to checklist items.
--
--  When set, the scheduler stops firing reminders after this date
--  (inclusive through to the end of that day in the user's tz)
--  and the mirrored Google Calendar event gets an UNTIL clause on
--  its RRULE so the calendar stops showing it too.
-- ============================================================

alter table checklist_items
  add column if not exists recurrence_end date;

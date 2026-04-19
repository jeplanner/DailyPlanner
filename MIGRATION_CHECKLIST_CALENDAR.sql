-- ============================================================
--  Add Google Calendar sync column to checklist_items.
--
--  When a checklist item has a reminder_time, we mirror it into the
--  user's Google Calendar as a recurring event with a popup reminder.
--  Android's native Calendar notifications bypass the OEM-level
--  demotion that eats generic Web Push heads-up banners, so the
--  reminder actually pops prominently.
-- ============================================================

alter table checklist_items
  add column if not exists google_event_id text;

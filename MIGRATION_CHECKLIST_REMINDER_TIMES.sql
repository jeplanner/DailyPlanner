-- ============================================================
--  Multiple reminder times per checklist item.
--
--  Before: checklist_items.reminder_time was a single TIME column,
--  and checklist_ticks deduped on (item_id, tick_date) — i.e. one
--  reminder and one tick per item per day.
--
--  After: checklist_reminder_times is a child table; each row is one
--  scheduled fire (e.g. drink water at 09:00, 13:00, 17:00). Ticks and
--  the dedup-send log are widened with a reminder_time column so each
--  fire is independently ticked and pushed.
--
--  checklist_items.reminder_time is kept as a legacy "first time"
--  mirror so any code reading it still sees something sensible until
--  it's migrated. New code should read from checklist_reminder_times.
--
--  Idempotent — safe to re-run.
-- ============================================================


-- ─────────────────────────────────────────────
--  CHILD TABLE: per-item reminder times
-- ─────────────────────────────────────────────
create table if not exists checklist_reminder_times (
  id              uuid primary key default gen_random_uuid(),
  item_id         uuid not null references checklist_items(id) on delete cascade,
  user_id         text not null,
  reminder_time   time not null,
  google_event_id text,
  position        int  not null default 0,
  created_at      timestamptz default now(),
  unique (item_id, reminder_time)
);

create index if not exists checklist_reminder_times_item_idx
  on checklist_reminder_times (item_id);
create index if not exists checklist_reminder_times_user_time_idx
  on checklist_reminder_times (user_id, reminder_time);


-- ─────────────────────────────────────────────
--  TICKS: per-fire completion
-- ─────────────────────────────────────────────
alter table checklist_ticks
  add column if not exists reminder_time time;

-- Drop the old (item_id, tick_date) uniqueness and replace it with one
-- that also keys on reminder_time. coalesce() handles legacy rows where
-- reminder_time is null — two NULL ticks on the same day still collide.
alter table checklist_ticks
  drop constraint if exists checklist_ticks_item_id_tick_date_key;

create unique index if not exists checklist_ticks_item_date_time_uidx
  on checklist_ticks (item_id, tick_date, coalesce(reminder_time, '00:00:00'::time));


-- ─────────────────────────────────────────────
--  REMINDER SEND LOG: per-fire dedup
-- ─────────────────────────────────────────────
alter table checklist_reminder_log
  add column if not exists reminder_time time;

alter table checklist_reminder_log
  drop constraint if exists checklist_reminder_log_item_id_sent_date_key;

create unique index if not exists checklist_reminder_log_item_date_time_uidx
  on checklist_reminder_log (item_id, sent_date, coalesce(reminder_time, '00:00:00'::time));


-- ─────────────────────────────────────────────
--  BACKFILL: each existing items.reminder_time → one child row
--  After backfill, null out parent google_event_id since the child
--  row now owns the Calendar event.
-- ─────────────────────────────────────────────
do $$
begin
  insert into checklist_reminder_times (item_id, user_id, reminder_time, google_event_id, position)
    select ci.id, ci.user_id, ci.reminder_time, ci.google_event_id, 0
      from checklist_items ci
     where ci.reminder_time is not null
       and not exists (
         select 1 from checklist_reminder_times rt
          where rt.item_id = ci.id and rt.reminder_time = ci.reminder_time
       );

  update checklist_items ci
     set google_event_id = null
   where ci.google_event_id is not null
     and exists (
       select 1 from checklist_reminder_times rt
        where rt.item_id = ci.id
          and rt.google_event_id = ci.google_event_id
     );
end $$;

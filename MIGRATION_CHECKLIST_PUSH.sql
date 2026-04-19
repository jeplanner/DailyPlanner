-- ============================================================
--  DailyPlanner — Daily Checklist + Web Push schema.
--
--  Run once in the Supabase SQL editor after adding the
--  checklist feature. Idempotent: safe to re-run.
--
--  Tables:
--    checklist_items           master list of recurring items
--    checklist_ticks           per-day completion rows
--    checklist_reminder_log    dedup log for scheduled push sends
--    push_subscriptions        browser push subscriptions
-- ============================================================


-- ─────────────────────────────────────────────
--  CHECKLIST ITEMS
-- ─────────────────────────────────────────────
create table if not exists checklist_items (
  id             uuid primary key default gen_random_uuid(),
  user_id        text not null,
  name           text not null,
  notes          text,
  -- 'daily' (every day), 'weekdays' (Mon–Fri), 'weekends' (Sat–Sun),
  -- 'custom' (use schedule_days CSV of 0=Sun..6=Sat).
  schedule       text not null default 'daily',
  schedule_days  text,
  -- Time-of-day bucket used for grouping in the UI.
  -- 'morning' | 'afternoon' | 'evening' | 'anytime'
  time_of_day    text default 'anytime',
  -- Optional local HH:MM:SS for the reminder. null = no push.
  reminder_time  time,
  position       int default 9999,
  is_deleted     boolean default false,
  created_at     timestamptz default now()
);
create index if not exists checklist_items_user_idx on checklist_items (user_id);


-- ─────────────────────────────────────────────
--  CHECKLIST TICKS (per-day completion)
-- ─────────────────────────────────────────────
create table if not exists checklist_ticks (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  item_id    uuid not null references checklist_items(id) on delete cascade,
  tick_date  date not null,
  ticked_at  timestamptz default now(),
  unique (item_id, tick_date)
);
create index if not exists checklist_ticks_user_date_idx on checklist_ticks (user_id, tick_date);


-- ─────────────────────────────────────────────
--  REMINDER SEND LOG (dedup across workers)
--
--  The push scheduler inserts one row per (item_id, sent_date).
--  The UNIQUE constraint guarantees that if multiple gunicorn
--  workers wake up in the same minute, only one successfully
--  inserts and therefore sends the notification.
-- ─────────────────────────────────────────────
create table if not exists checklist_reminder_log (
  id         uuid primary key default gen_random_uuid(),
  item_id    uuid not null,
  user_id    text not null,
  sent_date  date not null,
  sent_at    timestamptz default now(),
  unique (item_id, sent_date)
);
create index if not exists checklist_reminder_log_user_date_idx on checklist_reminder_log (user_id, sent_date);


-- ─────────────────────────────────────────────
--  PUSH SUBSCRIPTIONS
-- ─────────────────────────────────────────────
create table if not exists push_subscriptions (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  endpoint    text not null unique,
  p256dh      text not null,
  auth        text not null,
  user_agent  text,
  is_active   boolean default true,
  created_at  timestamptz default now(),
  last_used   timestamptz
);
create index if not exists push_subscriptions_user_idx on push_subscriptions (user_id);

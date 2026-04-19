-- ============================================================
--  DailyPlanner — COMPLETE schema for a fresh Supabase project.
--
--  This file is a consolidation of MIGRATION_FRESH_INSTALL.sql
--  and MIGRATION_CHECKLIST_PUSH.sql. It creates every table the
--  live application reads or writes. It is safe to re-run any
--  number of times: every `create table` uses `if not exists`,
--  every `alter table … add column` is guarded with
--  `if not exists`, and every `create index` is guarded too.
--
--  Order matters: parent tables precede children, base tables
--  precede the FKs that depend on them. Run this in the Supabase
--  SQL editor after the project is created.
--
--  Covers 34 tables across 13 feature areas:
--    users, projects, OKRs (objectives/key_results/initiatives),
--    project tasks + subtasks, Eisenhower matrix, recurring/
--    overrides, travel checklists, planner slots+meta+events,
--    health/habits, inbox/notes/references, Google Calendar
--    tokens, vault (refcards + bills + activity), portfolio
--    (holdings/txns/snapshots), daily checklist + web push.
-- ============================================================


-- ─────────────────────────────────────────────
-- 1. USERS
-- ─────────────────────────────────────────────
create table if not exists users (
  id            uuid primary key default gen_random_uuid(),
  email         text unique not null,
  display_name  text not null,
  password_hash text not null,
  is_active     boolean default true,
  created_at    timestamptz default now()
);
create index if not exists users_email_idx on users (email);

alter table users
  add column if not exists timezone text default 'Asia/Kolkata';

update users set timezone = 'Asia/Kolkata' where timezone is null;


-- ─────────────────────────────────────────────
-- 2. PROJECTS
-- ─────────────────────────────────────────────
create table if not exists projects (
  project_id   uuid primary key default gen_random_uuid(),
  user_id      text not null,
  name         text not null,
  description  text,
  is_archived  boolean default false,
  default_sort text default 'smart',
  created_at   timestamptz default now()
);
create index if not exists projects_user_idx on projects (user_id);


-- ─────────────────────────────────────────────
-- 3. OKRs (objectives → key_results → initiatives)
-- ─────────────────────────────────────────────
create table if not exists objectives (
  id           uuid primary key default gen_random_uuid(),
  user_id      text not null,
  project_id   uuid references projects(project_id) on delete cascade,
  title        text not null,
  description  text,
  category     text,
  time_horizon text,
  start_date   date,
  target_date  date,
  status       text default 'active',
  color        text,
  order_index  int default 0,
  is_deleted   boolean default false,
  deleted_at   timestamptz,
  created_at   timestamptz default now()
);
alter table objectives
  add column if not exists is_deleted    boolean default false,
  add column if not exists deleted_at    timestamptz,
  add column if not exists order_index   int default 0,
  add column if not exists category      text,
  add column if not exists time_horizon  text,
  add column if not exists start_date    date,
  add column if not exists target_date   date,
  add column if not exists status        text default 'active',
  add column if not exists color         text,
  add column if not exists description   text;
create index if not exists objectives_user_idx    on objectives (user_id, status);
create index if not exists objectives_project_idx on objectives (project_id);


create table if not exists key_results (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null,
  objective_id    uuid not null references objectives(id) on delete cascade,
  title           text not null,
  metric_type     text,
  unit            text,
  start_value     numeric default 0,
  current_value   numeric default 0,
  target_value    numeric not null,
  direction       text default 'up',
  progress_source text default 'manual',
  order_index     int default 0,
  is_deleted      boolean default false,
  deleted_at      timestamptz,
  created_at      timestamptz default now()
);
alter table key_results
  add column if not exists is_deleted      boolean default false,
  add column if not exists deleted_at      timestamptz,
  add column if not exists order_index     int default 0,
  add column if not exists progress_source text default 'manual',
  add column if not exists direction       text default 'up',
  add column if not exists start_value     numeric default 0,
  add column if not exists current_value   numeric default 0,
  add column if not exists metric_type     text,
  add column if not exists unit            text;
create index if not exists kr_objective_idx on key_results (objective_id);


create table if not exists initiatives (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  key_result_id uuid not null references key_results(id) on delete cascade,
  title         text not null,
  description   text,
  status        text default 'active',
  order_index   int default 0,
  is_deleted    boolean default false,
  deleted_at    timestamptz,
  created_at    timestamptz default now()
);
alter table initiatives
  add column if not exists is_deleted   boolean default false,
  add column if not exists deleted_at   timestamptz,
  add column if not exists order_index  int default 0,
  add column if not exists status       text default 'active',
  add column if not exists description  text;
create index if not exists initiatives_kr_idx on initiatives (key_result_id);


-- ─────────────────────────────────────────────
-- 4. PROJECT TASKS + SUBTASKS
-- ─────────────────────────────────────────────
create table if not exists project_tasks (
  task_id             uuid primary key default gen_random_uuid(),
  project_id          uuid references projects(project_id) on delete cascade,
  user_id             text not null,
  task_text           text not null,
  status              text default 'open',
  priority            text default 'medium',
  priority_rank       int default 2,
  start_date          date,
  due_date            date,
  due_time            text,
  duration_days       int default 0,
  notes               text,
  planned_hours       numeric,
  actual_hours        numeric,
  order_index         int default 0,
  is_pinned           boolean default false,
  delegated_to        text,
  is_eliminated       boolean default false,
  is_deleted          boolean default false,
  is_recurring        boolean default false,
  recurrence_type     text,
  recurrence_days     jsonb,
  recurrence_interval int,
  recurrence_end      date,
  auto_advance        boolean default true,
  quadrant            text,
  key_result_id       uuid,
  initiative_id       uuid references initiatives(id) on delete set null,
  plan_date           date,
  start_time          text,
  is_completed        boolean default false,
  elimination_reason  text,
  deleted_at          timestamptz,
  updated_at          timestamptz default now(),
  created_at          timestamptz default now()
);
alter table project_tasks
  add column if not exists priority_rank       int default 2,
  add column if not exists order_index         int default 0,
  add column if not exists is_pinned           boolean default false,
  add column if not exists delegated_to        text,
  add column if not exists is_eliminated       boolean default false,
  add column if not exists is_deleted          boolean default false,
  add column if not exists is_recurring        boolean default false,
  add column if not exists recurrence_type     text,
  add column if not exists recurrence_days     jsonb,
  add column if not exists recurrence_interval int,
  add column if not exists recurrence_end      date,
  add column if not exists auto_advance        boolean default true,
  add column if not exists quadrant            text,
  add column if not exists key_result_id       uuid,
  add column if not exists initiative_id       uuid,
  add column if not exists plan_date           date,
  add column if not exists start_time          text,
  add column if not exists is_completed        boolean default false,
  add column if not exists elimination_reason  text,
  add column if not exists deleted_at          timestamptz,
  add column if not exists updated_at          timestamptz default now();
create index if not exists project_tasks_project_idx    on project_tasks (project_id);
create index if not exists project_tasks_user_idx       on project_tasks (user_id);
create index if not exists project_tasks_initiative_idx on project_tasks (initiative_id);
create index if not exists project_tasks_quadrant_idx   on project_tasks (user_id) where quadrant is not null;


create table if not exists project_subtasks (
  id             uuid primary key default gen_random_uuid(),
  project_id     uuid references projects(project_id) on delete cascade,
  parent_task_id uuid references project_tasks(task_id) on delete cascade,
  title          text not null,
  is_done        boolean default false,
  position       int default 0,
  created_at     timestamptz default now()
);


-- ─────────────────────────────────────────────
-- 5. EISENHOWER MATRIX (todo_matrix + recurring + overrides)
-- ─────────────────────────────────────────────
create table if not exists todo_matrix (
  id             uuid primary key default gen_random_uuid(),
  user_id        text not null,
  plan_date      date not null,
  quadrant       text not null,
  task_text      text not null,
  is_done        boolean default false,
  is_deleted     boolean default false,
  position       int default 0,
  task_date      date,
  task_time      text,
  category       text,
  subcategory    text,
  project_id     uuid,
  source_task_id uuid,
  recurring_id   uuid,
  delegated_to   text,
  status         text default 'open',
  priority       text default 'medium',
  priority_rank  int default 2,
  is_pinned      boolean default false,
  deleted_at     timestamptz,
  updated_at     timestamptz default now(),
  created_at     timestamptz default now()
);
alter table todo_matrix
  add column if not exists status        text default 'open',
  add column if not exists priority      text default 'medium',
  add column if not exists priority_rank int default 2,
  add column if not exists task_date     date,
  add column if not exists task_time     text,
  add column if not exists is_pinned     boolean default false,
  add column if not exists deleted_at    timestamptz,
  add column if not exists updated_at    timestamptz default now();
create index if not exists todo_user_date_idx on todo_matrix (user_id, plan_date);


create table if not exists recurring_tasks (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  quadrant      text,
  task_text     text,
  recurrence    text,
  start_date    date,
  end_date      date,
  is_active     boolean default true,
  category      text,
  subcategory   text,
  day_of_month  int,
  days_of_week  jsonb
);

create table if not exists task_overrides (
  user_id        text not null,
  task_id        uuid,
  task_date      date,
  status         text,
  completed_date date
);


-- ─────────────────────────────────────────────
-- 6. TRAVEL MODE — pre-built checklists
-- ─────────────────────────────────────────────
create table if not exists travel_tasks (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  category    text default 'Default',
  quadrant    text default 'do',
  task_text   text not null,
  subcategory text,
  order_index int default 0,
  is_deleted  boolean default false,
  deleted_at  timestamptz,
  created_at  timestamptz default now()
);
alter table travel_tasks
  add column if not exists order_index int default 0,
  add column if not exists category    text default 'Default',
  add column if not exists quadrant    text default 'do',
  add column if not exists subcategory text,
  add column if not exists is_deleted  boolean default false,
  add column if not exists deleted_at  timestamptz;
create index if not exists travel_tasks_user_idx on travel_tasks (user_id);


-- ─────────────────────────────────────────────
-- 7. PLANNER (legacy V1 slot grid + meta + events)
-- ─────────────────────────────────────────────
create table if not exists daily_slots (
  user_id       text not null,
  plan_date     date not null,
  slot          int  not null,
  plan          text,
  status        text,
  start_time    text,
  end_time      text,
  priority      text,
  category      text,
  tags          jsonb,
  priority_rank int,
  unique (user_id, plan_date, slot)
);
create index if not exists daily_slots_user_idx on daily_slots (user_id, plan_date);

create table if not exists daily_meta (
  user_id       text not null,
  plan_date     date not null,
  habits        jsonb,
  reflection    text,
  untimed_tasks jsonb,
  unique (user_id, plan_date)
);

create table if not exists daily_events (
  id               uuid primary key default gen_random_uuid(),
  user_id          text not null,
  plan_date        date not null,
  start_time       text,
  end_time         text,
  title            text,
  description      text,
  status           text default 'Nothing Planned',
  priority         text default 'medium',
  is_deleted       boolean default false,
  google_event_id  text,
  quadrant         text,
  reminder_minutes int default 10,
  created_at       timestamptz default now()
);
create index if not exists events_user_date_idx on daily_events (user_id, plan_date);


-- ─────────────────────────────────────────────
-- 8. HEALTH + HABITS
-- ─────────────────────────────────────────────
create table if not exists habit_master (
  id          serial primary key,
  user_id     text not null,
  name        text not null,
  unit        text,
  goal        numeric,
  habit_type  text default 'number',
  position    int default 9999,
  is_deleted  boolean default false,
  start_date  date,
  created_at  timestamptz default now()
);

create table if not exists habit_entries (
  id        serial primary key,
  user_id   text not null,
  habit_id  int references habit_master(id),
  plan_date date not null,
  value     numeric,
  unique (user_id, habit_id, plan_date)
);

create table if not exists habit_goal_history (
  id              serial primary key,
  habit_id        int references habit_master(id),
  goal            numeric,
  effective_from  date,
  created_at      timestamptz default now()
);

create table if not exists daily_health (
  user_id      text not null,
  plan_date    date not null,
  weight       numeric,
  height       numeric,
  mood         text,
  energy_level int,
  notes        text,
  goal         text,
  unique (user_id, plan_date)
);


-- ─────────────────────────────────────────────
-- 9. INBOX + NOTES + REFERENCES
-- ─────────────────────────────────────────────
create table if not exists inbox_links (
  id           uuid primary key,
  user_id      text not null,
  url          text,
  title        text,
  description  text,
  content_type text,
  category     text,
  status       text default 'Unread',
  is_favorite  boolean default false,
  reminder_at  timestamptz,
  created_at   timestamptz default now()
);

create table if not exists scribble_notes (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  title      text,
  content    text,
  updated_at timestamptz default now(),
  is_deleted boolean default false
);

create table if not exists reference_links (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  title       text,
  description text,
  url         text,
  tags        jsonb,
  category    text,
  created_at  timestamptz default now()
);

create table if not exists tags (
  id      serial primary key,
  user_id text not null,
  name    text not null
);


-- ─────────────────────────────────────────────
-- 10. GOOGLE CALENDAR TOKENS
-- ─────────────────────────────────────────────
create table if not exists user_google_tokens (
  user_id        text primary key,
  access_token   text,
  refresh_token  text,
  token_uri      text,
  client_id      text,
  client_secret  text,
  scopes         text,
  updated_at     timestamptz default now()
);


-- ─────────────────────────────────────────────
-- 11. VAULT (refcards + bills + activity)
-- ─────────────────────────────────────────────
create table if not exists vault_settings (
  user_id           text primary key,
  password_hash     text,
  auto_lock_minutes int default 15,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

create table if not exists ref_contexts (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  name       text not null,
  address    text,
  position   int default 0,
  created_at timestamptz default now()
);
create index if not exists ref_contexts_user_idx on ref_contexts (user_id);

create table if not exists ref_cards (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null,
  property_id     uuid references ref_contexts(id) on delete cascade,
  category        text not null,
  provider        text not null,
  account_number  text,
  amount          numeric,
  currency        text default 'INR',
  billing_cycle   text,
  due_day         int,
  auto_pay        boolean default false,
  payment_method  text,
  portal_url      text,
  customer_id     text,
  notes           text,
  status          text default 'active',
  instrument_type text,
  country         text,
  details         text,
  created_at      timestamptz default now()
);
alter table ref_cards
  add column if not exists instrument_type text,
  add column if not exists country         text,
  add column if not exists details         text;
create index if not exists ref_cards_user_idx on ref_cards (user_id);

create table if not exists ref_activity_log (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  bill_id    uuid references ref_cards(id) on delete cascade,
  paid_date  date,
  amount     numeric,
  method     text,
  reference  text,
  notes      text,
  created_at timestamptz default now()
);


-- ─────────────────────────────────────────────
-- 12. PORTFOLIO
-- ─────────────────────────────────────────────
create table if not exists portfolio_holdings (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  name          text not null,
  symbol        text,
  asset_type    text default 'stock',
  exchange      text,
  quantity      numeric default 0,
  avg_price     numeric default 0,
  current_price numeric,
  currency      text default 'INR',
  folio_number  text,
  broker        text,
  sector        text,
  notes         text,
  held_by       text,
  buy_date      date,
  sell_date     date,
  institution   text,
  interest_rate numeric,
  payout_type   text,
  compounding   text,
  maturity_date date,
  start_date    date,
  account_ref   text,
  is_deleted    boolean default false,
  deleted_at    timestamptz,
  created_at    timestamptz default now()
);
alter table portfolio_holdings
  add column if not exists is_deleted boolean default false,
  add column if not exists deleted_at timestamptz;
create index if not exists portfolio_holdings_user_idx on portfolio_holdings (user_id);
create index if not exists portfolio_holdings_live_idx
  on portfolio_holdings (user_id) where is_deleted = false;

create table if not exists portfolio_transactions (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  holding_id uuid references portfolio_holdings(id) on delete cascade,
  txn_type   text default 'buy',
  txn_date   date not null,
  quantity   numeric,
  price      numeric,
  amount     numeric,
  notes      text,
  is_deleted boolean default false,
  deleted_at timestamptz,
  created_at timestamptz default now()
);
alter table portfolio_transactions
  add column if not exists is_deleted boolean default false,
  add column if not exists deleted_at timestamptz;
create index if not exists portfolio_txn_holding_idx on portfolio_transactions (holding_id);

create table if not exists portfolio_snapshots (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  snap_date     date not null,
  group_type    text not null,
  group_name    text not null,
  invested      numeric,
  current_value numeric,
  xirr          numeric,
  created_at    timestamptz default now()
);
create index if not exists portfolio_snap_user_idx on portfolio_snapshots (user_id, snap_date);


-- ─────────────────────────────────────────────
-- 13. DAILY CHECKLIST + WEB PUSH
-- ─────────────────────────────────────────────
create table if not exists checklist_items (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  name          text not null,
  notes         text,
  -- 'daily' | 'weekdays' | 'weekends' | 'custom'
  schedule      text not null default 'daily',
  -- CSV of weekday numbers (Sun=0 … Sat=6) when schedule='custom'
  schedule_days text,
  -- 'morning' | 'afternoon' | 'evening' | 'anytime'
  time_of_day   text default 'anytime',
  -- Optional local HH:MM:SS reminder time. null = no push.
  reminder_time time,
  position      int default 9999,
  is_deleted    boolean default false,
  created_at    timestamptz default now()
);
create index if not exists checklist_items_user_idx on checklist_items (user_id);


create table if not exists checklist_ticks (
  id        uuid primary key default gen_random_uuid(),
  user_id   text not null,
  item_id   uuid not null references checklist_items(id) on delete cascade,
  tick_date date not null,
  ticked_at timestamptz default now(),
  unique (item_id, tick_date)
);
create index if not exists checklist_ticks_user_date_idx on checklist_ticks (user_id, tick_date);


-- Dedup log for push reminders. The UNIQUE(item_id, sent_date) lets us
-- insert-or-fail atomically, so if multiple gunicorn workers wake up in
-- the same minute only one "wins" and sends the push.
create table if not exists checklist_reminder_log (
  id        uuid primary key default gen_random_uuid(),
  item_id   uuid not null,
  user_id   text not null,
  sent_date date not null,
  sent_at   timestamptz default now(),
  unique (item_id, sent_date)
);
create index if not exists checklist_reminder_log_user_date_idx
  on checklist_reminder_log (user_id, sent_date);


create table if not exists push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  endpoint   text not null unique,
  p256dh     text not null,
  auth       text not null,
  user_agent text,
  is_active  boolean default true,
  created_at timestamptz default now(),
  last_used  timestamptz
);
create index if not exists push_subscriptions_user_idx on push_subscriptions (user_id);


-- ============================================================
-- DONE.
--
--  Verify with:
--    select count(*) from information_schema.tables
--     where table_schema = 'public';
--  Expected: ~34 tables.
--
--  Tables created (alphabetical):
--    checklist_items, checklist_reminder_log, checklist_ticks,
--    daily_events, daily_health, daily_meta, daily_slots,
--    habit_entries, habit_goal_history, habit_master,
--    inbox_links, initiatives, key_results, objectives,
--    portfolio_holdings, portfolio_snapshots,
--    portfolio_transactions, project_subtasks, project_tasks,
--    projects, push_subscriptions, recurring_tasks,
--    ref_activity_log, ref_cards, ref_contexts,
--    reference_links, scribble_notes, tags, task_overrides,
--    todo_matrix, travel_tasks, user_google_tokens, users,
--    vault_settings.
--
--  If a 500 hits later with a "column X.Y does not exist" error
--  after a code change, add an
--    alter table X add column if not exists Y <type>;
--  block below and re-run.
-- ============================================================

-- ============================================================
--  DailyPlanner — QUICK BUCKET (a.k.a. Tasks Bucket)
--
--  A frictionless inbox for quick task capture, classified only by
--  *when* the user wants to act on it: Now, within 4h, within 8h, or
--  Future. The classification is a single inline toggle that cycles
--  through the four values.
--
--  Replaces the earlier category-flavoured tasks_bucket (Health /
--  Grocery / Portfolio / …) — that table and routes still exist so
--  no data is lost, but the nav link now points here.
--
--  Soft-delete only — see project convention (memory: no-hard-delete).
--  Done items set is_done = true; removed items set is_deleted = true.
--  No hard delete, no "delete permanently" UI.
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists quick_bucket (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null,
  text          text not null,
  time_bucket   text not null default 'now',  -- now | 4h | 8h | future
  is_done       boolean default false,
  is_deleted    boolean default false,
  position      int default 0,
  done_at       timestamptz,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- Hot path: list every active row for one user, ordered for the UI.
create index if not exists quick_bucket_user_active_idx
  on quick_bucket (user_id, time_bucket, position, created_at desc)
  where is_deleted = false and is_done = false;

create or replace function _quick_bucket_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists quick_bucket_touch_updated_at on quick_bucket;
create trigger quick_bucket_touch_updated_at
  before update on quick_bucket
  for each row execute function _quick_bucket_touch_updated_at();

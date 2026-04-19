-- ============================================================
--  Add Google-Calendar-style recurrence to calendar events.
--
--  Model:
--    daily_events gains a recurrence_rule + bounds + series_id.
--    The "master" row of a series has series_id = its own id and
--    carries the rule. Single (non-recurring) events leave it null.
--
--    "This occurrence only" edits create a per-occurrence override
--    row with is_exception=true, series_id pointing at the master,
--    and original_date = the date being overridden.
--
--    Deletes/skips of one occurrence insert into event_exceptions so
--    the occurrence expander knows to skip that date for that series.
--
--    "This and following" edits split the series:
--      - cap the original master's recurrence_end = day before the split
--      - create a new master starting from the split date with the
--        new data.
--
--    "All occurrences" edits simply update the master row.
-- ============================================================


alter table daily_events
  add column if not exists series_id        uuid,
  add column if not exists recurrence_rule  text,
  add column if not exists recurrence_days  text,
  add column if not exists recurrence_end   date,
  add column if not exists recurrence_count int,
  add column if not exists is_exception     boolean default false,
  add column if not exists original_date    date;

create index if not exists daily_events_series_idx
  on daily_events (series_id) where is_deleted = false;
create index if not exists daily_events_series_original_idx
  on daily_events (series_id, original_date)
  where is_exception = true and is_deleted = false;


create table if not exists event_exceptions (
  id             uuid primary key default gen_random_uuid(),
  series_id      uuid not null,
  user_id        text not null,
  exception_date date not null,
  reason         text default 'deleted',   -- 'deleted' | 'modified'
  created_at     timestamptz default now(),
  unique (series_id, exception_date)
);
create index if not exists event_exceptions_series_idx
  on event_exceptions (series_id);
create index if not exists event_exceptions_user_idx
  on event_exceptions (user_id, exception_date);

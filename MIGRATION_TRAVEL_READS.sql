-- ============================================================
--  DailyPlanner — TRAVEL READS queue
--
--  A focused "stuff to read / listen to while travelling" list.
--  Different from the Knowledge Base (references) which is
--  permanent — TravelReads is a queue: you add things, work
--  through them, and items naturally graduate to "Done" or get
--  archived once consumed.
--
--  Schema:
--    travel_reads(id, user_id, url, title, description,
--                 thumbnail_url, source, kind,
--                 duration_minutes, priority, status,
--                 notes, transcript_note_id,
--                 added_at, started_at, finished_at,
--                 archived_at, created_at, updated_at)
--
--  Status lifecycle:
--    queued       → default for new items
--    in_progress  → user tapped "Start"
--    done         → finished consuming it
--    archived     → soft-delete (no hard delete per project rule)
--
--  Kind (free-form, but UI suggests these):
--    article | video | podcast | audio | other
--
--  Priorities: high | medium | low (default medium)
--
--  Safe to re-run.
-- ============================================================

create table if not exists travel_reads (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null,
  url                 text not null,
  title               text,
  description         text,
  thumbnail_url       text,
  source              text,                  -- domain / publisher (e.g. "youtube.com")
  kind                text default 'article',
  duration_minutes    int,
  priority            text default 'medium',
  status              text default 'queued',
  notes               text,
  transcript_note_id  uuid,                  -- → scribble_notes.id when transcribed
  added_at            timestamptz default now(),
  started_at          timestamptz,
  finished_at         timestamptz,
  archived_at         timestamptz,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

-- Hot path: list every active item for a user, ordered for the queue.
create index if not exists travel_reads_user_status_idx
  on travel_reads (user_id, status) where status != 'archived';

create index if not exists travel_reads_user_added_idx
  on travel_reads (user_id, added_at desc);

-- Touch updated_at on any update.
create or replace function _travel_reads_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists travel_reads_touch_updated_at on travel_reads;
create trigger travel_reads_touch_updated_at
  before update on travel_reads
  for each row execute function _travel_reads_touch_updated_at();

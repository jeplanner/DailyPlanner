-- ============================================================
--  DailyPlanner — STUDY NOTES (Cornell + Feynman)
--
--  Two structured note-taking methods for serious reading and
--  retention work. Both share the same table; the `method` column
--  is a discriminator and only the matching column-set is used:
--
--    method = 'cornell'  → cornell_cues, cornell_notes, cornell_summary
--    method = 'feynman'  → feynman_concept, feynman_simple,
--                          feynman_gaps, feynman_refined,
--                          feynman_parent_id (chains iterations)
--
--  Source attachment (optional):
--    source_url       — the article/video URL
--    source_text      — free-form citation ("Make It Stick, ch. 3")
--    travel_read_id   — auto-set when source_url matches a row in
--                       travel_reads (so a study note knows which
--                       queued item it came from)
--
--  Spaced review (Leitner-style):
--    review_stage     — 0=new, 1=1d, 2=3d, 3=7d, 4=21d, 5=mastered
--    next_review_at   — when the note becomes due in /study/review
--    last_reviewed_at — last time the user advanced or reset stage
--
--  Soft-delete only (no hard DELETE per project rule).
--  Safe to re-run.
-- ============================================================

create table if not exists study_notes (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null,

  method             text not null check (method in ('cornell', 'feynman')),
  title              text not null default '',

  -- Source linkage
  source_url         text,
  source_text        text,
  travel_read_id     uuid,

  -- Cornell-specific
  cornell_cues       text,
  cornell_notes      text,
  cornell_summary    text,

  -- Feynman-specific
  feynman_concept    text,
  feynman_simple     text,
  feynman_gaps       text,
  feynman_refined    text,
  feynman_parent_id  uuid,                                  -- prior pass in the chain

  tags               text[] default '{}',

  -- Spaced review
  review_stage       int not null default 0,
  next_review_at     timestamptz default (now() + interval '1 day'),
  last_reviewed_at   timestamptz,

  is_deleted         boolean not null default false,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

-- Hot path: list a user's notes, newest first.
create index if not exists study_notes_user_method_idx
  on study_notes (user_id, method, updated_at desc)
  where is_deleted = false;

-- Review queue: due-today notes, oldest-due first.
create index if not exists study_notes_user_due_idx
  on study_notes (user_id, next_review_at)
  where is_deleted = false and review_stage < 5;

-- Source linkage lookup (when navigating from a travel_reads row).
create index if not exists study_notes_travel_read_idx
  on study_notes (travel_read_id)
  where is_deleted = false;

-- Iteration chain (find children of a Feynman pass).
create index if not exists study_notes_feynman_parent_idx
  on study_notes (feynman_parent_id)
  where is_deleted = false;

-- Touch updated_at on any update.
create or replace function _study_notes_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists study_notes_touch_updated_at on study_notes;
create trigger study_notes_touch_updated_at
  before update on study_notes
  for each row execute function _study_notes_touch_updated_at();

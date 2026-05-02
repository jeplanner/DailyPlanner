-- ============================================================
--  DailyPlanner — MEETING PREPS
--
--  Structured prep sheets for executive meetings where you have to
--  present and walk out with a decision. The schema mirrors the
--  prep frameworks we recommend in the UI:
--
--    BLUF (Bottom Line Up Front)
--      ask_recommendation, ask_decision_needed, ask_by_when, ask_from_whom
--
--    SCQA opener
--      scqa_situation, scqa_complication, scqa_question, scqa_answer
--
--    Body
--      supporting_points       — 3 supporting points with evidence
--      anticipated_questions   — Q: ... / A: ... / Backup: slide N
--      pre_brief_plan          — who to brief 1:1 before the room
--
--    Post-meeting
--      outcome                 — what was actually decided
--      follow_ups              — action items, owners, dates
--      retro                   — what to do differently next time
--
--  Status:
--    upcoming   — default for new preps
--    done       — meeting happened
--    cancelled  — meeting got cancelled (kept as record)
--
--  Soft-delete only (no hard DELETE per project rule).
--  Safe to re-run.
-- ============================================================

create table if not exists meeting_preps (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null,

  title                  text not null default '',
  meeting_date           timestamptz,
  attendees              text,
  status                 text not null default 'upcoming'
                         check (status in ('upcoming', 'done', 'cancelled')),

  -- BLUF — the ask
  ask_recommendation     text,
  ask_decision_needed    text,
  ask_by_when            text,
  ask_from_whom          text,

  -- SCQA opener
  scqa_situation         text,
  scqa_complication      text,
  scqa_question          text,
  scqa_answer            text,

  -- Body
  supporting_points      text,
  anticipated_questions  text,
  pre_brief_plan         text,

  -- Post-meeting capture
  outcome                text,
  follow_ups             text,
  retro                  text,

  is_deleted             boolean not null default false,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

-- Hot path: list a user's preps, upcoming first then most-recent.
create index if not exists meeting_preps_user_status_date_idx
  on meeting_preps (user_id, status, meeting_date desc nulls last)
  where is_deleted = false;

-- Touch updated_at on any update.
create or replace function _meeting_preps_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists meeting_preps_touch_updated_at on meeting_preps;
create trigger meeting_preps_touch_updated_at
  before update on meeting_preps
  for each row execute function _meeting_preps_touch_updated_at();

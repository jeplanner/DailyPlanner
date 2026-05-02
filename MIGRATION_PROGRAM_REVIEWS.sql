-- ============================================================
--  DailyPlanner — PROGRAM REVIEWS (IT program steering decks)
--
--  Each row is one review (monthly / quarterly / board) of one named
--  program. `program_name` is the grouping key — multiple reviews of
--  the same program share the name and form a history.
--
--  Layout matches the recommended exec format:
--
--    SCORECARD   — overall_rag, exec_summary, headline counts
--    OBJECTIVES  — recap (often copied from previous review)
--    WORKSTREAMS — JSONB array, each with name/owner/RAG/update
--    MILESTONES  — JSONB array, each with label/due_date/status
--    FINANCIALS  — budget_total, budget_spent, currency, variance
--    RISKS       — JSONB array, each with risk/likelihood/impact/mitigation
--    BUSINESS_IMPACT — translate technical → revenue/customer/risk
--    DECISIONS   — JSONB array, each with title/context/options/recommendation
--    ASKS        — what you need from the room
--
--  previous_review_id chains reviews so the editor can show history
--  and the "clone next-month review" feature can populate new rows.
--
--  Soft-delete only (no hard DELETE per project rule).
--  Safe to re-run.
-- ============================================================

create table if not exists program_reviews (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null,

  program_name         text not null default '',
  review_date          date,
  cadence              text not null default 'monthly'
                       check (cadence in ('weekly', 'monthly', 'quarterly', 'board', 'adhoc')),

  -- Scorecard (single-page summary that goes out 24h before the meeting)
  overall_rag          text not null default 'green'
                       check (overall_rag in ('green', 'amber', 'red')),
  overall_status       text,                                  -- one-line headline
  exec_summary         text,                                  -- 5 bullets max
  timeline_status      text,                                  -- short — "2 weeks behind on workstream B"
  top_risk_headline    text,                                  -- one-line — "Senior infra hire still open (60 days)"

  -- Financials
  budget_total         numeric(14, 2),
  budget_spent         numeric(14, 2),
  budget_currency      text not null default 'USD',
  budget_variance_note text,                                  -- "on plan" / "over by $80k due to vendor X"

  -- Recap
  objectives           text,

  -- Structured arrays (JSONB so PostgREST returns them as native JSON)
  --
  -- workstreams: [{ name, owner, rag, update }]
  -- milestones:  [{ label, due_date, status }]      status: hit | slipped | missed | upcoming
  -- risks:       [{ risk, likelihood, impact, mitigation, owner, target_date }]
  -- decisions:   [{ title, context, options, recommendation }]
  workstreams          jsonb not null default '[]'::jsonb,
  milestones           jsonb not null default '[]'::jsonb,
  risks                jsonb not null default '[]'::jsonb,
  decisions            jsonb not null default '[]'::jsonb,

  -- Narrative
  business_impact      text,
  asks                 text,

  -- Lineage
  previous_review_id   uuid,

  is_deleted           boolean not null default false,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

-- Hot path: list a user's programs, with most-recent review per program.
create index if not exists program_reviews_user_program_idx
  on program_reviews (user_id, program_name, review_date desc nulls last)
  where is_deleted = false;

-- Lineage walks (find previous / next reviews).
create index if not exists program_reviews_prev_idx
  on program_reviews (previous_review_id)
  where is_deleted = false;

-- Touch updated_at on any update.
create or replace function _program_reviews_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists program_reviews_touch_updated_at on program_reviews;
create trigger program_reviews_touch_updated_at
  before update on program_reviews
  for each row execute function _program_reviews_touch_updated_at();

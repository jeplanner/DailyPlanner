-- ============================================================
--  DailyPlanner — KNOWLEDGE BASE BACKLOG
--
--  Per-user list of items the owner intends to add to their KB
--  (books to scan, papers to find, handwritten notes to convert).
--  Lives next to the file grid on /knowledge-base so the "what
--  I want to add" sits beside "what I have."
--
--  Per-user (not per-family) — backlog tasks are intentions, not
--  shared work. Family Tasks already exists for cross-user assignment.
--
--  Soft-delete only (`deleted_at`) per the project convention. The
--  done-vs-open distinction uses `done_at` so we can show "completed
--  on Tue" rather than a flat boolean.
--
--  Safe to re-run.
-- ============================================================

create table if not exists kb_backlog (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  title       text not null
              check (char_length(title) between 1 and 300),
  notes       text,
  done_at     timestamptz,
  deleted_at  timestamptz,
  created_at  timestamptz not null default now()
);

-- Always fetched as "all backlog for me, ordered by recency". A single
-- composite index on (user_id, created_at desc) covers both — Postgres
-- can read in either direction.
create index if not exists kb_backlog_user_idx
  on kb_backlog (user_id, created_at desc);

-- ── Family sharing (Option 2 hybrid) ───────────────────────────
-- `is_shared = true` means the row is visible to every CHAT_USER_EMAILS
-- allowlisted user, not just the creator. Default false keeps every
-- existing row private (no surprise leaks). `created_by_name` is the
-- denormalized display name so the family view can render "added by
-- X" without joining users on every fetch — and so the label survives
-- a rename later, same convention as messages.author_name.
alter table kb_backlog
  add column if not exists is_shared boolean not null default false;
alter table kb_backlog
  add column if not exists created_by_name text;

-- Index for the family-list query path. Small table today, but
-- worth having so the panel stays snappy as it grows.
create index if not exists kb_backlog_shared_idx
  on kb_backlog (is_shared, created_at desc)
  where is_shared = true and deleted_at is null;

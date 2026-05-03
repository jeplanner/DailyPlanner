-- ─────────────────────────────────────────────────────────────────
-- INBOX → published_at: store the source content's publish date
-- (YouTube videos, articles where we can sniff one) so each card
-- can show "published X ago" alongside the existing "added X ago".
-- Lets the user spot stale links before opening them.
--
-- Stored as timestamptz so it round-trips cleanly with YouTube's
-- RFC 3339 publishedAt field.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS so re-running on an already
-- patched database is a no-op.
-- ─────────────────────────────────────────────────────────────────

alter table if exists inbox_links
    add column if not exists published_at timestamptz;

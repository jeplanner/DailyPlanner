-- ============================================================
--  DailyPlanner — OFFLINE WRITE IDEMPOTENCY
--
--  The PWA's offline write queue (static/js/sync-queue.js) stamps
--  every queued mutating request with an X-Client-Id header (UUID
--  generated client-side). When the service worker replays the
--  queue after reconnect, there's a small window where the same
--  request could be replayed twice — e.g. the server processed it
--  but the response was lost in transit, so the client thinks it
--  failed and replays.
--
--  Adding (user_id, client_id) as a unique constraint lets us do a
--  PostgREST upsert (Prefer: resolution=merge-duplicates) instead
--  of a blind insert. Re-sending the same payload returns the
--  existing row rather than creating a duplicate.
--
--  Applied to the two write surfaces wired through dpFetch today:
--    - quick_bucket (Quick Bucket / Tasks Bucket inbox)
--    - inbox_links  (Inbox — both /api/inbox and /inbox/share)
--
--  client_id is nullable so existing rows (and any future call
--  sites that don't yet pass one) continue to work — the partial
--  unique index only covers rows where client_id IS NOT NULL.
--
--  Safe to re-run.
-- ============================================================

alter table if exists quick_bucket
    add column if not exists client_id text;

alter table if exists inbox_links
    add column if not exists client_id text;

create unique index if not exists ux_quick_bucket_user_client
    on quick_bucket (user_id, client_id)
    where client_id is not null;

create unique index if not exists ux_inbox_links_user_client
    on inbox_links (user_id, client_id)
    where client_id is not null;

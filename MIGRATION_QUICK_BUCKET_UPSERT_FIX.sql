-- ============================================================
--  DailyPlanner — quick_bucket / inbox_links upsert fix
--
--  The original MIGRATION_OFFLINE_IDEMPOTENCY.sql created PARTIAL
--  unique indexes (... WHERE client_id IS NOT NULL) so existing rows
--  with NULL client_id wouldn't conflict.
--
--  Problem: PostgREST's ON CONFLICT inference only matches non-partial
--  unique constraints / indexes. PostgREST POSTs with
--  ?on_conflict=user_id,client_id, and the server returns
--    42P10 "there is no unique or exclusion constraint matching the
--    ON CONFLICT specification"
--  even though our partial index exists.
--
--  Fix: drop the partial index and replace it with a full unique
--  index on (user_id, client_id). Two NULL client_id rows are still
--  allowed because NULL is never equal to NULL in a unique constraint,
--  so legacy rows continue to work — but every new row carries a
--  client_id and the upsert can now bind to the index.
--
--  Safe to re-run.
-- ============================================================

drop index if exists ux_quick_bucket_user_client;
drop index if exists ux_inbox_links_user_client;

create unique index if not exists uq_quick_bucket_user_client
    on quick_bucket (user_id, client_id);

create unique index if not exists uq_inbox_links_user_client
    on inbox_links (user_id, client_id);

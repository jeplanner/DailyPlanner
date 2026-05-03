-- ─────────────────────────────────────────────────────────────────
-- LABELS + DRIVE QUEUE: lightweight tags on inbox/travel items so
-- the user can filter "what fits a 90-min drive". Stored as a
-- text[] (Postgres array) — small fixed vocabulary today, but the
-- column accepts anything so user-defined tags work later without
-- another migration.
--
-- Vocabulary (UI-suggested, free-form in storage):
--   drivable   🎧   audio-only safe (talks, podcasts, lectures)
--   visual     👀   needs the screen (code, demos, diagrams)
--   quick      ⚡   ≤10 min — fits a coffee break
--   long       🕐   ≥30 min — needs a real slot
--   priority   ⭐   user-flagged, never auto-set
--
-- Also adds inbox_links.duration_seconds so saved YouTube cards
-- carry their length without a re-fetch (and so the drive-queue
-- packer can sum it). travel_reads already has duration_minutes.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS, no-op on re-run.
-- ─────────────────────────────────────────────────────────────────

alter table if exists inbox_links
    add column if not exists labels text[] not null default '{}',
    add column if not exists duration_seconds int;

alter table if exists travel_reads
    add column if not exists labels text[] not null default '{}';

-- GIN index makes the "items containing label X" filter fast even
-- once the table grows. Cheap on inserts because the array is tiny.
create index if not exists inbox_links_labels_idx
    on inbox_links using gin (labels);

create index if not exists travel_reads_labels_idx
    on travel_reads using gin (labels);

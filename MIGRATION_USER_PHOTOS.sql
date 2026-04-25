-- ============================================================
--  DailyPlanner — USER PHOTOS (General Photos page)
--
--  A general-purpose photo album, separate from /prayer's curated
--  devotional grid. Mirrors the prayer_photos pattern — files in
--  Supabase Storage, metadata in this table — but on its own bucket
--  so the two stay logically distinct.
--
--  TWO-STEP SETUP — both required before /photos/upload will work:
--
--    1. STORAGE BUCKET — in the Supabase dashboard:
--         Storage → New bucket → name: user-photos
--         Public: ON   (so <img src> works without signed URLs)
--         File size limit: 5 MB
--         Allowed MIME types: image/jpeg, image/png, image/webp, image/gif
--
--    2. THIS MIGRATION — creates the metadata table.
--
--  Safe to re-run.
-- ============================================================

create table if not exists user_photos (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  storage_key   text not null,
  display_name  text,
  mime_type     text,
  size_bytes    int,
  is_deleted    boolean default false,
  created_at    timestamptz default now()
);

create index if not exists user_photos_user_idx
  on user_photos (user_id, is_deleted, created_at desc)
  where is_deleted = false;

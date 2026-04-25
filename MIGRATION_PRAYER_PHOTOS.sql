-- ============================================================
--  DailyPlanner — PRAYER PHOTOS
--
--  Lets users upload their own devotional photos that surface in the
--  Prayer page alongside the curated deity images bundled with the
--  repo. Files live in Supabase Storage (Render's filesystem is
--  ephemeral, so the bundled-asset approach can't carry user uploads).
--
--  TWO-STEP SETUP — both required before /prayer/upload will work:
--
--    1. STORAGE BUCKET — in the Supabase dashboard:
--         Storage → New bucket → name: prayer-photos
--         Public: ON   (so <img src> works without signed URLs)
--         File size limit: 5 MB
--         Allowed MIME types: image/jpeg, image/png, image/webp, image/gif
--
--    2. THIS MIGRATION — creates the metadata table that records who
--       uploaded what so we can list and soft-delete user photos.
--
--  Safe to re-run.
-- ============================================================

create table if not exists prayer_photos (
  id            uuid primary key default gen_random_uuid(),
  user_id       text not null,
  storage_key   text not null,        -- path inside the bucket: <user_id>/<uuid>.<ext>
  display_name  text,                 -- user-supplied caption
  mime_type     text,
  size_bytes    int,
  is_deleted    boolean default false,
  created_at    timestamptz default now()
);

create index if not exists prayer_photos_user_idx
  on prayer_photos (user_id, is_deleted, created_at desc)
  where is_deleted = false;

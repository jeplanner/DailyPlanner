-- ============================================================
--  DailyPlanner — CHAT FILE ATTACHMENTS (Google Drive)
--
--  Lets people attach images / PDFs / documents to a chat message.
--  The bytes live in the sender's Google Drive folder
--  "DailyPlannerChat" (created on first upload, id cached on the
--  existing user_google_tokens row). Drive is the source of truth —
--  we only persist enough metadata on the message row to render the
--  bubble (name, mime, kind, web link, size) and a file id so the
--  app can stream the bytes back for inline preview.
--
--  Sharing reuses the Knowledge-Base pattern: on upload we grant
--  every other family-allowlist email read access to the file, so
--  the link opens for everyone in the room.
--
--  Piggybacks on the same drive.file OAuth scope the Knowledge Base
--  already uses (see routes/events.py SCOPES). No new scope, so no
--  Google verification needed.
--
--  Safe to re-run.
-- ============================================================

-- Per-user cache of the chat upload folder's Drive id. Sits next to
-- kb_folder_id on the same row events.py manages for Calendar/Drive.
alter table user_google_tokens
  add column if not exists chat_folder_id text;

-- Attachment metadata carried directly on the message. All nullable —
-- a normal text message leaves every column NULL and renders exactly
-- as before. attachment_kind is a coarse render hint
-- ('image' | 'pdf' | 'file') so the frontend doesn't have to sniff
-- the mime type itself.
alter table messages
  add column if not exists attachment_file_id text,
  add column if not exists attachment_name    text,
  add column if not exists attachment_mime    text,
  add column if not exists attachment_kind    text,
  add column if not exists attachment_url      text,
  add column if not exists attachment_size     bigint;

-- Extend the kind whitelist with 'file-share'. Drop-then-add so a
-- re-run after a future kind is added stays a no-op (mirrors the
-- pattern in MIGRATION_CHAT.sql).
do $$ begin
  alter table messages drop constraint if exists messages_kind_chk;
  alter table messages add constraint messages_kind_chk
    check (kind in ('text', 'kb-share', 'inbox-share', 'file-share'));
end $$;

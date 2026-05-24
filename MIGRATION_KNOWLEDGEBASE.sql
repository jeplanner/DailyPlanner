-- ============================================================
--  DailyPlanner — KNOWLEDGE BASE (Google Drive PDFs)
--
--  The Knowledge Base page lists / uploads PDFs from the user's
--  Google Drive folder "knowledgebase2026". Drive is the source of
--  truth — we don't mirror a row per file. The only thing we cache
--  locally is the Drive folder id, so we don't re-search Drive for
--  it on every page load.
--
--  Piggybacks on the existing user_google_tokens row that
--  routes/events.py already manages for Calendar sync. Adding the
--  drive.file scope to SCOPES in events.py + re-consenting through
--  /google-login gives this page the token it needs.
--
--  Safe to re-run.
-- ============================================================

alter table user_google_tokens
  add column if not exists kb_folder_id text;

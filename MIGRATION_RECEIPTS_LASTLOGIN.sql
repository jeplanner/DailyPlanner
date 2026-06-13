-- ============================================================
--  DailyPlanner — EXPENSE RECEIPTS + LAST-LOGIN
--
--  1) Receipts: an expense can carry a receipt file stored in Google
--     Drive under  dailyplanner / receipts . We persist the Drive file
--     id + link + name on the expense row, and cache the receipts
--     folder id on the user's token row.
--  2) Last login: stamp users.last_login_at on each successful login so
--     the chat member list can show "last seen".
--
--  Safe to re-run (idempotent).
-- ============================================================

alter table expenses
  add column if not exists receipt_file_id text,
  add column if not exists receipt_url     text,
  add column if not exists receipt_name    text;

alter table user_google_tokens
  add column if not exists receipts_folder_id text;

alter table users
  add column if not exists last_login_at timestamptz;

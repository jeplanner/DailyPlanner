-- ─────────────────────────────────────────────────────────────────
-- INBOX → SCRIBBLE NOTES: link saved YouTube videos to their
-- transcripts so each card can show "View transcript" once captured.
--
-- Mirrors the pattern travel_reads.transcript_note_id already uses;
-- the actual transcript text lives in scribble_notes (notebook =
-- 'Transcripts'), this column is just the back-reference so the
-- inbox card can link to it.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS so re-running the migration
-- on an already-patched database is a no-op.
-- ─────────────────────────────────────────────────────────────────

alter table if exists inbox_links
    add column if not exists transcript_note_id uuid;

-- No FK to scribble_notes intentionally — when a user deletes a
-- transcript note we just want the card to fall back to "Transcribe"
-- (mic icon), not block the delete with a constraint violation.

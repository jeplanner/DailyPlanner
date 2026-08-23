-- ─────────────────────────────────────────────────────────────────────
-- Per-item notification mute for checklist reminders.
--
-- Asked for 2026-08-23: "per item notification mutes on announcements page
-- is needed." Until now there was ONE switch for all push notifications, in
-- Settings. Silencing a single item meant deleting its reminder times, which
-- loses the times themselves — so it was a delete dressed up as a mute.
--
-- A muted item keeps its schedule, keeps showing on the checklist and the
-- Day Board, and simply does not push. Unmuting restores it exactly, which
-- is the whole point and the reason this is a flag rather than a deletion.
--
-- Safe to run more than once.
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE checklist_items
    ADD COLUMN IF NOT EXISTS notify_muted boolean NOT NULL DEFAULT false;

-- The scheduler filters on (user_id, is_deleted) and now also reads this
-- column; the partial index keeps the common "not muted" case cheap.
CREATE INDEX IF NOT EXISTS checklist_items_notify_live_idx
    ON checklist_items (user_id)
    WHERE is_deleted = false AND notify_muted = false;

COMMENT ON COLUMN checklist_items.notify_muted IS
    'True = this item never sends a push reminder. Its reminder_times are '
    'kept intact so unmuting restores the exact schedule. Read in Python '
    'rather than filtered in the query, so the app keeps working against a '
    'database where this migration has not been run yet.';

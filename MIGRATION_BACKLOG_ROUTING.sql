-- ─────────────────────────────────────────────────────────────────────
-- BACKLOG AS THE CAPTURE INBOX
--
-- The Backlog used to be a read-only view over two lists. It becomes the
-- one place a laundry-list item is captured, and the place it is routed
-- out of — to the Quick Bucket, a project, a note, references or inbox.
--
-- WHY A COLUMN AND NOT JUST A COPY
-- --------------------------------
-- Pushing a PROJECT task into the Quick Bucket is the one route that can
-- lie. The task already counts toward its project's progress, so writing
-- a second row for the same piece of work makes the planner report more
-- outstanding work than exists, and ticking one leaves the other open
-- forever. This column ties the bucket row back to the task it came from
-- so completing the bucket item closes the project task with it.
--
-- Idempotent: safe to run more than once.
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'quick_bucket' AND column_name = 'source_task_id'
    ) THEN
        ALTER TABLE quick_bucket ADD COLUMN source_task_id UUID;
        RAISE NOTICE 'quick_bucket.source_task_id added';
    ELSE
        RAISE NOTICE 'quick_bucket.source_task_id already present';
    END IF;
END $$;

-- Only the promoted rows carry one, so the index stays small.
CREATE INDEX IF NOT EXISTS idx_quick_bucket_source_task
    ON quick_bucket (source_task_id)
    WHERE source_task_id IS NOT NULL;


-- ─────────────────────────────────────────────────────────────────────
-- A DEADLINE THAT SURVIVES BEING PRIORITISED
--
-- "it should also capture, has to do by X days (take the current date as
-- the baseline). Highlight things which have missed the date."
--
-- WHY NOT due_at, AND WHY NOT scheduled_for
-- -----------------------------------------
-- Both already mean something else, and reusing either would destroy the
-- deadline exactly when it starts to matter:
--
--   * due_at is the Quick Bucket's countdown ("in 2 hours") and is
--     RECOMPUTED from the bucket every time the bucket changes — so
--     promoting a backlog item to "Now" would wipe the date it was
--     supposed to be done by.
--   * scheduled_for records the day an item was moved onto the calendar,
--     and is paired with scheduled_event_id.
--
-- A DATE, not a timestamp: "by Friday" is the granularity anyone actually
-- means when capturing a laundry list.
--
-- Idempotent: safe to run again even if the first half of this file has
-- already been applied.
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'quick_bucket' AND column_name = 'backlog_due'
    ) THEN
        ALTER TABLE quick_bucket ADD COLUMN backlog_due DATE;
        RAISE NOTICE 'quick_bucket.backlog_due added';
    ELSE
        RAISE NOTICE 'quick_bucket.backlog_due already present';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_quick_bucket_backlog_due
    ON quick_bucket (user_id, backlog_due)
    WHERE backlog_due IS NOT NULL;

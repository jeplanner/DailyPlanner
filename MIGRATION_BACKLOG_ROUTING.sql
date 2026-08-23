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

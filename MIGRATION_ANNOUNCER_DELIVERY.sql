-- ─────────────────────────────────────────────────────────────────────
-- ANNOUNCEMENTS: DELIVERY LOGGING, AND A GOOGLE CALENDAR MIRROR
--
-- Part 1: record whether an announcement actually reached anything.
--
-- The fire log proves the SCHEDULER ran. It proves nothing about
-- delivery, and treating the two as the same has now cost several nights
-- of testing: a claim row exists for every slot, including the ones where
-- no device made a sound and no notification appeared.
--
-- The send outcome was recorded only through services/loud.py, which is
-- IN MEMORY and lost on every restart — so by the time anyone looked, the
-- one fact that mattered was gone.
--
-- Two integers. `sent` and `failed` are what push_service.send_to_user()
-- already returns and currently throws away.
--
-- Idempotent: safe to run more than once.
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'announcer_fire_log' AND column_name = 'sent'
    ) THEN
        ALTER TABLE announcer_fire_log ADD COLUMN sent INTEGER;
        RAISE NOTICE 'announcer_fire_log.sent added';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'announcer_fire_log' AND column_name = 'failed'
    ) THEN
        ALTER TABLE announcer_fire_log ADD COLUMN failed INTEGER;
        RAISE NOTICE 'announcer_fire_log.failed added';
    END IF;
END $$;


-- ─────────────────────────────────────────────────────────────────────
-- MIRROR ANNOUNCEMENTS INTO GOOGLE CALENDAR
--
-- "can you not make it as system notification since calendar notification
-- in android did not work. i had to create it in samsung calender or
-- google calendar to make it work."
--
-- Exactly right, and this codebase already knows it — see the docstring of
-- services/checklist_calendar_service.py: Samsung and most Android OEMs
-- suppress heads-up banners from generic Web Push, while Google Calendar
-- popup reminders are treated as first-class by the OS. A calendar popup
-- uses the OS's exact-alarm path and is not deferred by Doze, which is
-- what "it only arrived when I unlocked the phone" means.
--
-- So each announcement also becomes a recurring Calendar event with a
-- popup at T-0. This column holds the event it owns, so the mirror can be
-- updated and removed rather than duplicated.
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'announcer_items' AND column_name = 'google_event_id'
    ) THEN
        ALTER TABLE announcer_items ADD COLUMN google_event_id TEXT;
        RAISE NOTICE 'announcer_items.google_event_id added';
    END IF;
END $$;

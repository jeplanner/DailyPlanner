"""Revision reminders for Random thoughts: a push when spaced reviews are due.

Marking a question studied puts it on the review ladder (1, 3, 7, 14, 30,
60, 120 days - thoughts_service.REVIEW_DAYS). The page already pops the
review up when you open it, but a review you never open the page for is a
review missed, and missing one is what lets the memory fade. So the push
scheduler calls fire() every minute, and at SLOTS (your local time) a
notification says how many are due and opens the review directly.

* Morning slot: everything due by the end of today.
* Evening slot: only if some of those are still waiting - the nudge for the
  day you didn't get to it. Nothing due means nothing sent, ever.
* One notification per shelf (Interview Prep, AI SDE), each linking to its
  own page with ?review=1.

Dedupe rides on checklist_reminder_log, so no migration: item_id is a uuid5
of (user, shelf, slot) - the table has no foreign key on it - and its unique
index on (item_id, sent_date, coalesce(reminder_time)) lets exactly one
gunicorn worker win each fire.
"""
import logging
import uuid
from datetime import datetime, time, timedelta, timezone

from requests.exceptions import HTTPError

from services import push_service
from services import thoughts_service as ts
from supabase_client import get, post

logger = logging.getLogger(__name__)

SLOTS = ("08:00", "20:00")
SHELVES = {
    "tpm": ("Interview Prep", "/interview-prep/thoughts?review=1"),
    "aisde": ("AI SDE Prep", "/ai-sde/thoughts?review=1"),
}
_NS = uuid.UUID("6f1c2b8e-4d0a-4f7e-9a51-2c3d4e5f6a7b")


def end_of_day_utc(now_local):
    """The end of the reader's local day, as a UTC ISO string. A review
    falls due on a DAY, not at the minute it was rated: one due at 15:00
    is already counted in the 08:00 reminder."""
    end = datetime.combine(now_local.date() + timedelta(days=1), time(0), tzinfo=now_local.tzinfo)
    return end.astimezone(timezone.utc).isoformat()


def due_counts(user_id, now_local):
    """{shelf: number of studied questions due for review by tonight}."""
    rows = get(ts.TABLE, params={
        "user_id": f"eq.{user_id}", "understood": "is.true", "parent_id": "is.null",
        "deleted_at": "is.null", "next_review_at": f"lte.{end_of_day_utc(now_local)}",
        "select": "shelf", "limit": "1000"}) or []
    out = {}
    for r in rows:
        shelf = r.get("shelf") or "tpm"
        out[shelf] = out.get(shelf, 0) + 1
    return out


def message(n, slot):
    q = "question" if n == 1 else "questions"
    if slot == SLOTS[0]:
        return f"{n} {q} due for review today. Two minutes of recall now and they stay with you."
    return f"Still {n} {q} waiting for review today. Recall them before the day ends, or the gap grows."


def _claim(user_id, shelf, slot, today):
    item = uuid.uuid5(_NS, f"{user_id}|{shelf}|{slot}")
    try:
        post("checklist_reminder_log", {"item_id": str(item), "user_id": str(user_id),
                                        "sent_date": today}, prefer="return=minimal")
        return True
    except HTTPError as e:
        if e.response is None or e.response.status_code != 409:
            logger.exception("review reminder: claim failed for %s", user_id)
        return False


def fire(user_id, now_local):
    """Send this minute's revision reminders, if it is a slot and any are due.
    Returns [(shelf, count)] actually sent."""
    slot = now_local.strftime("%H:%M")
    if slot not in SLOTS:
        return []
    sent = []
    today = now_local.date().isoformat()
    for shelf, n in sorted(due_counts(user_id, now_local).items()):
        if not n or shelf not in SHELVES or not _claim(user_id, shelf, slot, today):
            continue
        name, url = SHELVES[shelf]
        push_service.send_to_user(user_id, title=f"🧠 {name}: time to revise",
                                  body=message(n, slot), url=url,
                                  tag=f"review-{shelf}-{slot.replace(':', '')}")
        sent.append((shelf, n))
    return sent

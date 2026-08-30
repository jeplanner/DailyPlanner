"""What the paragraph reader must get right.

These are not "the regex fired" tests. Each one is a sentence somebody
would actually type into the Quick Bucket, and the assertion is what
should end up in the bucket afterwards — because the only thing that
matters here is whether the thing you meant survives the trip.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from utils.brain_dump import (
    clean_title,
    read_dump,
    segment,
)

IST = ZoneInfo("Asia/Kolkata")

# A Monday, mid-morning, so "tomorrow" and "friday" are both unambiguous
# and no test result depends on the day it is run.
NOW = datetime(2026, 8, 31, 10, 0, tzinfo=IST)


def by_title(items, needle):
    for it in items:
        if needle.lower() in it["text"].lower():
            return it
    raise AssertionError(
        f"no item matching {needle!r}; got {[i['text'] for i in items]}"
    )


# ── splitting prose into tasks ──────────────────────────────────────

def test_a_paragraph_becomes_several_tasks_not_one():
    """The failure this whole feature exists to fix: a dictated
    paragraph used to land as ONE bucket row with a paragraph in it."""
    items = read_dump(
        "I need to call the plumber tomorrow morning, pay the electricity "
        "bill before Friday and book the flight, that one is urgent.",
        now=NOW,
    )
    titles = [i["text"] for i in items]
    assert len(titles) >= 3, titles
    by_title(items, "plumber")
    by_title(items, "electricity bill")
    by_title(items, "flight")


def test_and_only_splits_when_a_new_instruction_follows():
    """"call the plumber and the electrician" is ONE task. Splitting on
    every "and" is the obvious implementation and it shreds half of all
    real sentences."""
    items = read_dump("Call the plumber and the electrician", now=NOW)
    assert len(items) == 1
    assert "electrician" in items[0]["text"].lower()


def test_a_pasted_list_still_works_line_by_line():
    """Lines win over sentences — someone who pressed Enter has already
    said where the boundaries are, and list lines rarely end in a stop."""
    items = read_dump("milk\nbread\n- pay rent\n1. call mum", now=NOW)
    assert [i["text"] for i in items] == ["Milk", "Bread", "Pay rent", "Call mum"]


def test_a_decimal_time_does_not_end_a_sentence():
    assert segment("Meet Ravi at 3.30 pm today") == ["Meet Ravi at 3.30 pm today"]


def test_pm_with_dots_does_not_end_a_sentence():
    assert segment("Call at 5 p.m. sharp") == ["Call at 5 p.m. sharp"]


def test_duplicate_lines_collapse():
    items = read_dump("pay rent\npay rent", now=NOW)
    assert len(items) == 1


def test_a_real_work_dump_comes_out_as_the_list_it_is():
    """The dump that exposed all of this, pasted verbatim on 2026-08-30.

    It came back as SEVEN items, four of them several tasks glued
    together, and the two timed personal items had no time on them. The
    verb test alone cannot read a work list: "traffic prioritisation" and
    "theme review calendar" contain no verb and are obviously tasks.
    """
    items = read_dump(
        "Today - Reflect feedback before 12pm. review deployment exceptions , "
        "traffic prioritisation, mail regarding capacity requests,theme review "
        "calendar, upload the JAS initiatives to JIRA , Action item updates to "
        "JIRA, Bug bash budget email, NPS in portal, complete the flipkart "
        "training, 2 pager BBD Prep document for team. walk 10am today. "
        "pray 10.30 today",
        now=NOW,
    )
    titles = [i["text"] for i in items]
    assert titles == [
        "Reflect feedback",
        "Review deployment exceptions",
        "Traffic prioritisation",
        "Mail regarding capacity requests",
        "Theme review calendar",
        "Upload the JAS initiatives to JIRA",
        "Action item updates to JIRA",
        "Bug bash budget email",
        "NPS in portal",
        "Complete the flipkart training",
        "2 pager BBD Prep document for team",
        "Walk",
        "Pray",
    ], titles
    # "Today - " is a heading, not the first task.
    assert not any(t.lower() == "today" for t in titles)
    assert by_title(items, "Reflect")["due_at"].startswith("2026-08-31T06:30")
    assert by_title(items, "Walk")["due_at"].startswith("2026-08-31T04:30")
    assert by_title(items, "Pray")["due_at"].startswith("2026-08-31T05:00")


def test_a_comma_list_of_noun_phrases_is_a_list_of_tasks():
    items = read_dump(
        "review deployment exceptions, traffic prioritisation, theme review "
        "calendar", now=NOW)
    assert len(items) == 3, [i["text"] for i in items]


def test_a_one_word_comma_run_is_one_task_with_things_in_it():
    """"pick up groceries — milk, eggs, bread" is a shopping trip, not
    three tasks that each mean nothing on their own."""
    items = read_dump("Pick up groceries — milk, eggs, bread", now=NOW)
    assert len(items) == 1, [i["text"] for i in items]


def test_a_comma_before_a_clause_still_does_not_split():
    """The list rule must not eat the case it was carved out of."""
    for line in ("Book the flight, that one is urgent",
                 "Call Ravi, he wants the numbers",
                 "Finish the deck, it needs the latest figures"):
        assert len(read_dump(line, now=NOW)) == 1, line


def test_a_time_written_without_a_preposition_is_still_a_time():
    """Nobody writes "walk at 10am today" in their own notes."""
    assert by_title(read_dump("walk 10am today", now=NOW), "Walk")["due_at"] \
        .startswith("2026-08-31T04:30")
    # 10.30 with a dot is how half of India writes half past ten.
    assert by_title(read_dump("pray 10.30 today", now=NOW), "Pray")["due_at"] \
        .startswith("2026-08-31T05:00")


def test_a_quantity_is_not_a_time():
    """"2 pager BBD Prep document" must not become an alarm at 2pm, and
    that is exactly what a preposition-free time reader does if it is
    allowed to guess at a bare number."""
    it = by_title(read_dump("2 pager BBD Prep document for team", now=NOW),
                  "pager")
    assert it["due_at"] is None
    assert it["time_bucket"] == "now"


# ── titles ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("i need to call the plumber", "Call the plumber"),
    ("also, remember to pay rent", "Pay rent"),
    ("I have to submit the report", "Submit the report"),
    ("don't forget to book the flight", "Book the flight"),
    ("todo: renew the passport", "Renew the passport"),
    ("and then send the invoice", "Send the invoice"),
])
def test_the_title_is_the_task_not_the_preamble(raw, expected):
    assert clean_title(raw) == expected


# ── when ────────────────────────────────────────────────────────────

def test_a_clock_time_pins_an_alarm():
    items = read_dump("Call the bank at 3:30pm today", now=NOW)
    it = by_title(items, "bank")
    assert it["time_bucket"] == "at"
    assert it["due_at"], "no due_at — nothing would ring"
    assert it["due_at"].startswith("2026-08-31T10:00")  # 15:30 IST = 10:00 UTC


def test_tomorrow_morning_lands_tomorrow():
    items = read_dump("Call the plumber tomorrow at 9am", now=NOW)
    it = by_title(items, "plumber")
    assert it["due_at"].startswith("2026-09-01T03:30")  # 09:00 IST
    assert "plumber" in it["text"].lower()
    # The day word is consumed, not left dangling in the title.
    assert "tomorrow" not in it["text"].lower()


def test_a_bare_hour_is_guessed_and_the_guess_is_declared():
    """"at 9" is 9am or 9pm and English does not say which. Guessing is
    right — silently guessing is not."""
    items = read_dump("Call Ravi at 9", now=NOW)
    it = by_title(items, "Ravi")
    assert it["time_bucket"] == "at"
    assert any("check it" in w for w in it["why"]), it["why"]


def test_in_two_hours_is_a_deadline_bucket_not_an_alarm():
    items = read_dump("Send the invoice in 2 hours", now=NOW)
    it = by_title(items, "invoice")
    assert it["time_bucket"] == "2h"
    assert it["due_at"] is None


def test_in_twenty_minutes_snaps_to_the_nearest_bucket_not_upward():
    """Rounding 20 minutes up to the 30m bucket hands the task ten
    minutes it does not have."""
    it = by_title(read_dump("Reply to Anita in 20 minutes", now=NOW), "Anita")
    assert it["time_bucket"] == "15m"


def test_urgent_means_now_and_keeps_saying_so():
    it = by_title(read_dump("Book the flight, urgent", now=NOW), "flight")
    assert it["time_bucket"] == "now"
    assert "urgent" in it["text"].lower(), "the reason vanished from the title"


def test_next_week_defers_and_dates_it():
    it = by_title(read_dump("Review the deck next week", now=NOW), "deck")
    assert it["time_bucket"] == "future"
    assert it["backlog_due"] == "2026-09-07"     # the Monday after


def test_by_friday_sets_a_date_and_not_a_midnight_alarm():
    it = by_title(read_dump("Pay the electricity bill before Friday", now=NOW),
                  "electricity")
    assert it["backlog_due"] == "2026-09-04"
    assert it["due_at"] is None, "a date is not an alarm"
    assert it["time_bucket"] == "future"


def test_in_three_days_counts_from_today():
    it = by_title(read_dump("Renew the passport in 3 days", now=NOW), "passport")
    assert it["backlog_due"] == "2026-09-03"


def test_nothing_at_all_defaults_to_now_and_says_why():
    it = by_title(read_dump("Water the plants", now=NOW), "plants")
    assert it["time_bucket"] == "now"
    assert any("defaulted to Now" in w for w in it["why"])


# ── how long ────────────────────────────────────────────────────────

def test_effort_is_read_separately_from_the_deadline():
    """"spend 30 mins on the deck tomorrow at 4pm" carries both, and
    they are different columns."""
    it = by_title(
        read_dump("Spend 30 mins on the deck tomorrow at 4pm", now=NOW),
        "deck")
    assert it["planned_minutes"] == 30
    assert it["time_bucket"] == "at"
    assert it["due_at"].startswith("2026-09-01T10:30")   # 16:00 IST


def test_takes_an_hour_is_effort_not_a_deadline():
    it = by_title(read_dump("Clean the garage, takes an hour", now=NOW),
                  "garage")
    assert it["planned_minutes"] == 60
    assert it["time_bucket"] == "now"


def test_a_thirty_minute_call_keeps_its_own_words():
    it = by_title(read_dump("Book a 30 minute call with Ravi", now=NOW), "Ravi")
    assert it["planned_minutes"] == 30
    assert "30" in it["text"], "the phrase describes the task; keep it"


def test_an_effort_clause_stays_with_the_task_it_measures():
    """"start the java prep, spend 45 mins a day on it" splits at the
    comma on the strength of the verb "spend" and produces a second task
    called "Spend 45 mins a day on it" — which is not a task, it is the
    first one's estimate."""
    items = read_dump(
        "Next week sometime start the java prep, spend 45 mins a day on it",
        now=NOW)
    assert len(items) == 1, [i["text"] for i in items]
    assert items[0]["text"] == "Start the java prep"
    assert items[0]["planned_minutes"] == 45
    assert items[0]["time_bucket"] == "future"


def test_a_consumed_part_of_the_day_leaves_the_title():
    """The clock reader eats the day word it used, which left "Tomorrow
    morning I must drop Shreya at school by 8" as a task called "Morning
    I must drop Shreya at school"."""
    it = read_dump(
        "Tomorrow morning I must drop Shreya at school by 8", now=NOW)[0]
    assert it["text"] == "Drop Shreya at school"
    assert it["due_at"].startswith("2026-09-01T02:30")   # 08:00 IST


# ── what is not a task ──────────────────────────────────────────────

def test_thinking_out_loud_is_kept_but_not_ticked():
    """Never DELETE a line on a guess. An unticked row costs a click; a
    dropped task costs the thing itself."""
    items = read_dump(
        "I am completely exhausted today. Book a doctor's appointment.",
        now=NOW)
    note = by_title(items, "exhausted")
    assert note["use"] is False
    assert by_title(items, "doctor")["use"] is True


def test_a_feeling_with_a_deadline_is_a_task_after_all():
    items = read_dump("I should sleep by 10pm", now=NOW)
    it = items[0]
    assert it["use"] is True
    assert it["time_bucket"] == "at"


def test_every_item_explains_itself():
    for it in read_dump(
        "Pay rent tomorrow at 9am, review the deck next week, "
        "and call the plumber asap", now=NOW,
    ):
        assert it["why"], f"{it['text']} arrived with no explanation"
        assert it["source"], "no original text to check the guess against"


def test_nothing_in_nothing_out():
    assert read_dump("", now=NOW) == []
    assert read_dump("   \n  \n", now=NOW) == []


def test_a_huge_dump_is_capped():
    items = read_dump("\n".join(f"task number {i}" for i in range(200)),
                      now=NOW)
    assert len(items) <= 60


def test_the_buckets_it_can_emit_all_exist_on_the_page():
    """A bucket this module invents would render as a blank pill and
    could never be cycled back to anything sensible."""
    from routes.quick_bucket import BUCKET_SET
    allowed = BUCKET_SET | {"at"}
    dump = (
        "call now\nsend in 5 minutes\nreply in 20 minutes\n"
        "fix in 40 minutes\ndraft in 2 hours\nship in 7 hours\n"
        "review next week\nmeet at 4pm tomorrow\nclean the garage"
    )
    for it in read_dump(dump, now=NOW):
        assert it["time_bucket"] in allowed, it


def test_a_priority_word_never_becomes_a_task_of_its_own():
    """"urgent - reply to the recruiter email" is one item. Split at the
    dash it becomes a task called "Urgent", and the real task loses the
    urgency it was carrying."""
    items = read_dump(
        "book cab for airport at 4:30am tomorrow, urgent - reply to the "
        "recruiter email", now=NOW)
    assert not any(i["text"].strip().lower() == "urgent" for i in items), \
        [i["text"] for i in items]
    it = by_title(items, "recruiter")
    assert it["time_bucket"] == "now"


# ── the optional model pass ─────────────────────────────────────────
#
# The model is only ever allowed to SPLIT. Everything below is about
# what happens when it misbehaves, which is the only interesting part:
# on a good day the two readings agree and there is nothing to test.

from services import brain_dump_service as bds       # noqa: E402


def test_without_the_flag_no_model_is_called():
    called = []
    items, used_ai, note = bds.interpret(
        "pay rent tomorrow at 9am", use_ai=False,
        ai_call=lambda p: called.append(p) or "x", now=NOW)
    assert called == [], "the model ran for a request that did not ask for it"
    assert used_ai is False and items


def test_the_model_splits_but_never_decides_the_time():
    """It hands back phrases; the rules read them. A model that could set
    a bucket could set a different one for the same words tomorrow."""
    items, used_ai, _ = bds.interpret(
        "pay rent tomorrow at 9am and call the plumber asap",
        use_ai=True, now=NOW,
        ai_call=lambda p: "pay rent tomorrow at 9am\ncall the plumber asap")
    assert used_ai is True
    assert by_title(items, "rent")["due_at"].startswith("2026-09-01T03:30")
    assert by_title(items, "plumber")["time_bucket"] == "now"


def test_an_invented_task_is_dropped():
    """A list that grows work nobody wrote is worse than one that misses
    a split — you cannot tell by looking which line is which."""
    items, _, _ = bds.interpret(
        "pay rent", use_ai=True, now=NOW,
        ai_call=lambda p: "pay rent\nbook a holiday in Barcelona")
    assert not any("barcelona" in i["text"].lower() for i in items)


def test_a_model_that_drops_half_the_dump_cannot_lose_it():
    items, _, note = bds.interpret(
        "pay rent\ncall the plumber\nrenew the passport",
        use_ai=True, now=NOW, ai_call=lambda p: "pay rent")
    titles = " ".join(i["text"].lower() for i in items)
    assert "plumber" in titles and "passport" in titles
    assert note and "built-in rules" in note


def test_a_dead_model_falls_back_and_says_so():
    """Silent fallback is how you end up believing the AI is working
    months after the key expired."""
    items, used_ai, note = bds.interpret(
        "pay rent", use_ai=True, now=NOW,
        ai_call=lambda p: "AI service is busy. Please try again in a few seconds.")
    assert used_ai is False
    assert items and "could not be reached" in note

    boom, used, note2 = bds.interpret(
        "pay rent", use_ai=True, now=NOW,
        ai_call=lambda p: (_ for _ in ()).throw(RuntimeError("no network")))
    assert used is False and boom, "an exception must not lose the rule parse"


def test_model_chatter_is_not_a_task():
    items, _, _ = bds.interpret(
        "pay rent", use_ai=True, now=NOW,
        ai_call=lambda p: "Here are the tasks:\n- pay rent\n```")
    assert [i["text"] for i in items] == ["Pay rent"]

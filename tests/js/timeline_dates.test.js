/* static/js/dates.js — the plain-language date layer.
 *
 * Shared by the Roadmap ("3 days late"), Sprints ("day 6 of 14") and the
 * goal countdowns, so a wrong answer here is wrong on three pages at
 * once. Everything below is a case that was either already wrong or is
 * one off-by-one away from being wrong:
 *
 *  - Month ends, year ends and a leap day, because the helpers do their
 *    arithmetic at UTC midnight specifically to stop a daylight-saving
 *    shift from moving a date by a day.
 *  - "Next Monday" on all seven weekdays. The natural (8 - dow) % 7
 *    returns 0 on a Monday, which would schedule work to the day it is
 *    already on and read as "nothing happened".
 *  - progressThrough with one date missing, which used to be how
 *    "day NaN of NaN" reached the screen.
 */
const H = require("../../static/js/dates.js");

let pass = 0, fail = 0;
const eq = (name, got, want) => {
  if (got === want) { pass++; console.log("PASS " + name); }
  else { fail++; console.log(`FAIL ${name}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); }
};

/* ── addDays: the boundaries ─────────────────────────────────────────── */
eq("addDays month end", H.addDays("2026-01-31", 1), "2026-02-01");
eq("addDays year end",  H.addDays("2026-12-31", 1), "2027-01-01");
eq("addDays leap day",  H.addDays("2028-02-28", 1), "2028-02-29");
eq("addDays non-leap",  H.addDays("2026-02-28", 1), "2026-03-01");
eq("addDays backwards", H.addDays("2026-03-01", -1), "2026-02-28");
eq("addDays a week",    H.addDays("2026-10-04", 7), "2026-10-11");
eq("addDays zero",      H.addDays("2026-10-04", 0), "2026-10-04");

/* ── daysBetween ─────────────────────────────────────────────────────── */
eq("between same day", H.daysBetween("2026-10-04", "2026-10-04"), 0);
eq("between forward",  H.daysBetween("2026-10-04", "2026-10-11"), 7);
eq("between backward", H.daysBetween("2026-10-04", "2026-09-20"), -14);
eq("between a year",   H.daysBetween("2026-01-01", "2027-01-01"), 365);

/* ── relativeDay: the words the pages actually print ─────────────────── */
const T = "2026-10-04";
eq("today",        H.relativeDay("2026-10-04", T), "Today");
eq("tomorrow",     H.relativeDay("2026-10-05", T), "Tomorrow");
eq("yesterday",    H.relativeDay("2026-10-03", T), "Yesterday");
eq("3 days late",  H.relativeDay("2026-10-01", T), "3 days late");
eq("2 weeks late", H.relativeDay("2026-09-20", T), "2 weeks late");
eq("months late",  H.relativeDay("2026-06-04", T), "4 months late");
eq("in 5 days",    H.relativeDay("2026-10-09", T), "in 5 days");
eq("in 2 weeks",   H.relativeDay("2026-10-18", T), "in 2 weeks");
eq("in 3 months",  H.relativeDay("2027-01-04", T), "in 3 months");

/* ── nextMonday must always be strictly ahead, on every weekday ──────── */
for (let i = 0; i < 7; i++) {
  const today = H.addDays("2026-10-04", i);          // 2026-10-04 is a Sunday
  const monday = H.nextMonday(today);
  const dow = new Date(monday + "T00:00:00Z").getUTCDay();
  const ahead = H.daysBetween(today, monday);
  const ok = dow === 1 && ahead >= 1 && ahead <= 7;
  if (ok) { pass++; console.log(`PASS nextMonday ${today} -> ${monday} (+${ahead})`); }
  else { fail++; console.log(`FAIL nextMonday ${today} -> ${monday} dow ${dow} +${ahead}`); }
}

/* ── progressThrough: a sprint's "day N of M" ────────────────────────── */
// A two-week sprint, 2026-10-05 .. 2026-10-18 inclusive = 14 days.
const S = ["2026-10-05", "2026-10-18"];
eq("sprint total is inclusive", H.progressThrough(...S, "2026-10-05").total, 14);
eq("first day is day 1",        H.progressThrough(...S, "2026-10-05").day, 1);
eq("mid sprint",                H.progressThrough(...S, "2026-10-10").day, 6);
eq("last day is day 14",        H.progressThrough(...S, "2026-10-18").day, 14);
eq("last day is 100%",          H.progressThrough(...S, "2026-10-18").pct, 100);
eq("remaining mid sprint",      H.progressThrough(...S, "2026-10-10").remaining, 8);

// Past its end: clamps rather than reporting day 19 of 14.
const over = H.progressThrough(...S, "2026-10-23");
eq("overrun clamps to total", over.day, 14);
eq("overrun flagged",         over.elapsed, true);
eq("overrun has none left",   over.remaining, 0);

// Before it starts.
const early = H.progressThrough(...S, "2026-10-01");
eq("not started flagged", early.notStarted, true);
eq("not started is day 0", early.day, 0);

// Missing dates must give null, not NaN.
eq("no start -> null", H.progressThrough(null, "2026-10-18", T), null);
eq("no end -> null",   H.progressThrough("2026-10-05", null, T), null);
eq("neither -> null",  H.progressThrough(null, null, T), null);
// A single-day sprint is still day 1 of 1, not a divide-by-zero.
eq("one-day sprint total", H.progressThrough("2026-10-05", "2026-10-05", "2026-10-05").total, 1);
eq("one-day sprint pct",   H.progressThrough("2026-10-05", "2026-10-05", "2026-10-05").pct, 100);
// Backwards dates are nonsense, not a negative bar.
eq("end before start -> null", H.progressThrough("2026-10-18", "2026-10-05", T), null);

/* ── todayISO shape ──────────────────────────────────────────────────── */
eq("todayISO shape", /^\d{4}-\d{2}-\d{2}$/.test(H.todayISO()), true);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

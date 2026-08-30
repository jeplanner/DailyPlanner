/* Chat timestamps carry a date, not just a clock time.
 *
 * "Also chats tag it with dates and time. not only time." (2026-08-30)
 *
 * The formatter's own comment promised "Mon h:mm AM within the week,
 * MMM D otherwise" and the body returned toLocaleTimeString and nothing
 * else. Which day a message belonged to came only from the separator
 * chips — and those are hidden under any filter, so a filtered room was
 * a list of bare clock times.
 *
 * The formatter is pulled out of the template and run directly: the rule
 * is date arithmetic (midnights, week edges, year boundaries) and that is
 * where it goes wrong, not in the rendering around it.
 */
const fs = require("fs");

const html = fs.readFileSync(__dirname + "/../../templates/chat.html", "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

// Lift `const fmtTime = (iso) => { ... };` straight out of the page.
const m = html.match(/const fmtTime = \(iso\) => \{[\s\S]*?\n  \};/);
if (!m) {
  console.log("FAIL could not find fmtTime in chat.html");
  process.exit(1);
}
const fmtTime = eval("(" + m[0].replace(/^const fmtTime = /, "").replace(/;$/, "") + ")");

// A fixed "now" so the test does not drift with the calendar. Everything
// below is relative to Sunday 30 August 2026, 18:00 local.
const NOW = new Date(2026, 7, 30, 18, 0);
const RealDate = Date;
global.Date = class extends RealDate {
  constructor(...a) { return a.length ? new RealDate(...a) : new RealDate(NOW); }
  static now() { return NOW.getTime(); }
};

const at = (y, mo, d, h, mi) => new RealDate(y, mo, d, h, mi).toISOString();

{
  const today = fmtTime(at(2026, 7, 30, 15, 45));
  ok("today shows the time alone — no date means today", /^\d{1,2}:45/.test(today));
  ok("...and no day name crept in", !/aug|sun|yesterday/i.test(today));
}

ok("yesterday is named, not dated",
   /^Yesterday /.test(fmtTime(at(2026, 7, 29, 15, 45))));

{
  const midweek = fmtTime(at(2026, 7, 26, 9, 5));   // 4 days back
  ok("within the week it is the weekday", /^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)/.test(midweek));
  ok("...with the time still on it", /9:05/.test(midweek));
}

{
  // 8 days back — past the weekday window, same year.
  const older = fmtTime(at(2026, 7, 22, 11, 30));
  ok("older than a week gets a real date", /22/.test(older) && /Aug/i.test(older));
  ok("...and no year, because it is this year", !/2026/.test(older));
  ok("...and keeps the time", /11:30/.test(older));
}

{
  const lastYear = fmtTime(at(2025, 11, 24, 20, 15));
  ok("a different year says which", /2025/.test(lastYear));
  ok("...with the date and time", /24/.test(lastYear) && /8:15|20:15/.test(lastYear));
}

// Boundaries: the two places date maths usually breaks.
ok("6 days back is still a weekday, not a date",
   /^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)/.test(fmtTime(at(2026, 7, 24, 12, 0))));
ok("7 days back has crossed into dates",
   !/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s/.test(fmtTime(at(2026, 7, 23, 12, 0))));

// Robustness: the stream renders whatever the server sent.
ok("a missing timestamp renders nothing", fmtTime(null) === "" && fmtTime("") === "");
ok("an unparseable timestamp renders nothing", fmtTime("not a date") === "");

global.Date = RealDate;
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

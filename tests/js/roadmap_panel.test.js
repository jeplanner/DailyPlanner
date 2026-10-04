/* The Roadmap, in a real DOM.
 *
 * Asked 2026-10-04: make the Work pages usable on a phone. Two things on
 * this page were not, and neither is visible in the template source:
 *
 *  1. Rescheduling was HTML5 drag-and-drop ONLY. Touch screens fire no
 *     dragstart and no drop, so on a phone the roadmap was read-only —
 *     you could see the plan and not change it. There is now a sheet on
 *     every card, and what has to be checked is that it opens against
 *     the card you tapped and POSTs that card's id with the date chosen.
 *  2. The page never said what was late. Every block rendered the same,
 *     so three weeks overdue looked like due next month. The blocks are
 *     classed from their own data-date against the user's today.
 *
 * The page is rendered by Flask (tests/test_smoke.py writes it to the
 * path given as argv[2]) and the real static JS is run against it, so
 * the TEMPLATE and the SCRIPTS are checked together.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const DATES = fs.readFileSync(__dirname + "/../../static/js/dates.js", "utf8");
const UI = fs.readFileSync(__dirname + "/../../static/timeline_ui.js", "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

/** Boot the page with a fixed "today" so the assertions are not calendar-dependent. */
function boot(today) {
  const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://example.test/projects/timeline",
  });
  const { window } = dom;
  const doc = window.document;

  // Pin the clock. The page asks DPDates for today, which asks Intl in
  // the user's timezone — so freezing Date is the honest way to fix it.
  const FIXED = new Date(today + "T09:00:00Z").getTime();
  const RealDate = window.Date;
  class FrozenDate extends RealDate {
    constructor(...a) { return a.length ? new RealDate(...a) : new RealDate(FIXED); }
    static now() { return FIXED; }
  }
  window.Date = FrozenDate;
  window.USER_TZ = "UTC";

  // Record what the page sends rather than letting it reach the network.
  const posted = [];
  window.fetch = (url, opts) => {
    posted.push({ url, body: JSON.parse(opts.body), headers: opts.headers });
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ status: "ok" }) });
  };
  window.showToast = () => {};
  // The page reloads after a successful move; swallow it.
  let reloaded = 0;
  delete window.location;
  window.location = { href: "https://example.test/projects/timeline", hash: "",
                      reload: () => { reloaded++; }, searchParams: null };
  window.requestAnimationFrame = fn => fn();

  window.eval(DATES);
  window.eval(UI);
  doc.dispatchEvent(new window.Event("DOMContentLoaded"));

  return { window, doc, posted, reloaded: () => reloaded };
}

/* The fixture the pytest side renders carries three blocks:
   2026-09-20 (late), 2026-10-04 (today), 2026-10-18 (ahead). */
const TODAY = "2026-10-04";
const { window, doc, posted } = boot(TODAY);
const q = s => doc.querySelector(s);
const all = s => Array.from(doc.querySelectorAll(s));

/* The page wires Reschedule with an inline onclick="openReschedule(this)".
 * jsdom with runScripts:"outside-only" does not compile content attributes
 * into handlers, so .click() on the button does nothing here — the same
 * limitation nav_groups.test.js works around for highlightActiveNav. Call
 * the function the attribute names, which is what the attribute does in a
 * browser; the attribute itself is asserted separately below. */
const tapMove = card => {
  const btn = card.querySelector(".card-move");
  if (!btn) throw new Error("no reschedule button on that card");
  window.openReschedule(btn);
  return btn;
};

/* ── 1. Late / today / ahead are marked ───────────────────────────────── */
const late  = q('.time-block[data-date="2026-09-20"]');
const today = q('.time-block[data-date="2026-10-04"]');
const ahead = q('.time-block[data-date="2026-10-18"]');

ok("the past block is marked late",   late  && late.classList.contains("is-late"));
ok("today's block is marked today",   today && today.classList.contains("is-today"));
ok("the future block is marked ahead",ahead && ahead.classList.contains("is-ahead"));
ok("late is not also marked ahead",   late && !late.classList.contains("is-ahead"));

/* ── 2. Each block says how late it is, in words ──────────────────────── */
ok("the late block says it is late",
   /late/i.test(late.querySelector(".time-when").textContent));
ok("today says Today",
   /^Today$/.test(today.querySelector(".time-when").textContent.trim()));
ok("the future block says 'in'",
   /^in /.test(ahead.querySelector(".time-when").textContent.trim()));

/* ── 3. The summary counts tasks, not blocks ──────────────────────────── */
const summary = q("#tl-summary");
ok("the summary is shown", summary.hidden === false);
ok("the summary counts the late task", /1 late/.test(summary.textContent));
ok("the summary counts today's",       /1 due today/.test(summary.textContent));
ok("the summary counts the ahead one", /1 ahead/.test(summary.textContent));

/* ── 4. Every card has a reschedule control — the whole point on touch ── */
const cards = all(".timeline-card");
ok("there are three cards", cards.length === 3);
ok("every card has a reschedule button",
   cards.every(c => !!c.querySelector(".card-move")));
ok("the button is wired to openReschedule",
   cards.every(c => c.querySelector(".card-move").getAttribute("onclick") === "openReschedule(this)"));
ok("openReschedule is a global the attribute can reach",
   typeof window.openReschedule === "function");

/* ── 5. The sheet opens against the card you tapped ───────────────────── */
const sheet = q("#tl-sheet");
ok("the sheet starts hidden", sheet.hidden === true);

const lateCard = late.querySelector(".timeline-card");
tapMove(lateCard);

ok("the sheet opens", sheet.hidden === false);
ok("the scrim opens", q("#tl-scrim").hidden === false);
ok("the page behind is locked", doc.body.classList.contains("tl-sheet-open"));
ok("the sheet names that task",
   q("#tl-sheet-title").textContent === lateCard.dataset.title);
ok("the sheet says where it is now",
   /late/i.test(q("#tl-sheet-current").textContent));
ok("the date field starts on the card's own date",
   q("#tl-date").value === "2026-09-20");

/* ── 6. Quick choices are offered and are real dates ─────────────────── */
const chips = all("#tl-quick .tl-chip");
ok("four quick choices", chips.length === 4);
ok("Today is offered",       /Today/.test(chips[0].textContent));
ok("Next Monday is offered", chips.some(c => /Next Monday/.test(c.textContent)));

/* ── 7. Escape closes it ─────────────────────────────────────────────── */
doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape" }));
ok("Escape closes the sheet", sheet.hidden === true);
ok("Escape unlocks the page", !doc.body.classList.contains("tl-sheet-open"));

/* ── 8. Choosing a date POSTs that card and that date ────────────────── */
tapMove(lateCard);
q("#tl-date").value = "2026-10-06";
window.saveReschedule();

ok("exactly one request went out", posted.length === 1);
ok("it went to the existing endpoint",
   posted[0] && posted[0].url === "/api/timeline/reschedule");
ok("it carries the tapped card's task id",
   posted[0] && posted[0].body.task_id === lateCard.dataset.task);
ok("it carries the date chosen",
   posted[0] && posted[0].body.new_date === "2026-10-06");

/* ── 9. Moving a card to the date it already has is not a write ──────── */
const beforeNoop = posted.length;
const todayCard = today.querySelector(".timeline-card");
tapMove(todayCard);
window.saveReschedule();
ok("re-saving the same date sends nothing", posted.length === beforeNoop);
ok("...and closes the sheet", sheet.hidden === true);

/* ── 10. The summary pills are buttons that jump, not decoration ─────── */
const pills = all("#tl-summary .tl-pill");
ok("the pills are buttons", pills.length === 3 && pills.every(p => p.tagName === "BUTTON"));
ok("each pill names what it jumps to",
   pills.every(p => ["is-late", "is-today", "is-ahead"].includes(p.dataset.jump)));
// Clicking must not throw where scrollIntoView does not exist — that is
// exactly the environment an embedded webview presents.
let jumpThrew = null;
try { pills[0].click(); } catch (e) { jumpThrew = e.message; }
ok("jumping does not throw without scrollIntoView", jumpThrew === null);
ok("the jumped-to block is marked", !!q(".time-block.just-jumped"));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

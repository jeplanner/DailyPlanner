/* The announcer PANEL, in a real DOM.
 *
 * Reported 2026-08-23: "if i delete something it goes to home page. it should
 * stay in the announcement page." The panel was closing itself on delete.
 *
 * The cause needs a real DOM to reproduce, which is why the plain-stub
 * harness in tests/js/time_announcer.test.js could never have caught it:
 * deleting rebuilds the list with innerHTML, DETACHING the clicked button,
 * and the outside-click listener then ran `ev.target.closest(".ta-pop")` on a
 * node no longer in the document, got null, and concluded the click was
 * outside the panel.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const SRC = __dirname + "/../../static/js/time-announcer.js";

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const dom = new JSDOM(
  `<!doctype html><html><head></head><body>
     <div class="top-context"><button class="help-btn">?</button></div>
   </body></html>`,
  { runScripts: "outside-only", pretendToBeVisual: true, url: "https://example.test/quick-bucket" }
);
const { window } = dom;

// speechSynthesis does not exist in jsdom; the panel must still mount.
window.speechSynthesis = {
  speak() {}, cancel() {}, resume() {}, getVoices() { return []; },
  addEventListener() {}, speaking: false, pending: false, paused: false,
};
window.SpeechSynthesisUtterance = function () {};

// ── fetch stub ───────────────────────────────────────────────────────
// jsdom has no fetch, and the announcer now syncs to the server. Recording
// the calls turns a missing global into an actual test of the sync.
const calls = [];
window.fetch = function (url, opts) {
  opts = opts || {};
  calls.push({ url: String(url), method: opts.method || "GET",
               headers: opts.headers || {},
               body: opts.body ? JSON.parse(opts.body) : null });
  const json = String(url).indexOf("/api/announcer/state") === 0
    ? { ok: true, every: 15, label: "", items: [] }      // empty server
    : { ok: true };
  return Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve(json),
  });
};
const sent = (method, part) =>
  calls.filter(c => c.method === method && c.url.indexOf(part) !== -1);

window.eval(fs.readFileSync(SRC, "utf8"));

// jsdom with runScripts:"outside-only" leaves readyState === "loading"
// forever, so the module parks on DOMContentLoaded and never mounts. Fire it
// by hand — this is the SAME order the real page uses (script parsed, then
// the event), which is the part that matters: a harness that mounts in a
// different order from production tests something production never does.
window.document.dispatchEvent(new window.Event("DOMContentLoaded", { bubbles: true }));

const doc = window.document;
const q = (s) => doc.querySelector(s);
const click = (el) => el.dispatchEvent(
  new window.MouseEvent("click", { bubbles: true, cancelable: true }));

// ── server sync (2026-08-23) ─────────────────────────────────────────
// Announcements moved off localStorage so they follow you between devices.
ok("pulls the stored schedule on load", sent("GET", "/api/announcer/state").length === 1);

// ── it mounts ────────────────────────────────────────────────────────
ok("button mounted in the top bar", !!q(".ta-btn"));
ok("panel exists", !!q(".ta-pop"));
ok("panel starts hidden", q(".ta-pop").hidden === true);

// ── it opens ─────────────────────────────────────────────────────────
click(q(".ta-btn"));
ok("opens on the button", q(".ta-pop").hidden === false);

// ── the close control that was missing ───────────────────────────────
ok("has a close control", !!q("[data-ta-close]"));
click(q("[data-ta-close]"));
ok("close button closes it", q(".ta-pop").hidden === true);
click(q(".ta-btn"));
ok("reopens", q(".ta-pop").hidden === false);

// ── adding an announcement ───────────────────────────────────────────
q("[data-ta-new-at]").value = "5.00";
q("[data-ta-new-text]").value = "Wake up";
click(q("[data-ta-add]"));
ok("add creates a row", doc.querySelectorAll(".ta-item").length === 1);
ok("...parsed 5.00 as 5:00 AM", /5:00 AM/.test(q(".ta-when b").textContent));
ok("...kept the text", /Wake up/.test(q(".ta-what").textContent));
ok("panel STAYS OPEN after add", q(".ta-pop").hidden === false);

q("[data-ta-new-at]").value = "6.45pm";
q("[data-ta-new-text]").value = "Leave office";
click(q("[data-ta-add]"));
ok("second row added", doc.querySelectorAll(".ta-item").length === 2);

// ── the reported bug ─────────────────────────────────────────────────
click(doc.querySelector("[data-ta-toggle]"));
ok("toggle stops just that one", doc.querySelectorAll(".ta-item.off").length === 1);
ok("toggling syncs the row", sent("POST", "/api/announcer/items").length >= 1);
ok("panel STAYS OPEN after toggle", q(".ta-pop").hidden === false);

click(doc.querySelector("[data-ta-del]"));
ok("delete removes one row", doc.querySelectorAll(".ta-item").length === 1);
ok("PANEL STAYS OPEN AFTER DELETE", q(".ta-pop").hidden === false);
ok("did not navigate away",
   window.location.pathname === "/quick-bucket");

click(doc.querySelector("[data-ta-del]"));
ok("deleting the last row is fine", doc.querySelectorAll(".ta-item").length === 0);
ok("panel still open with an empty list", q(".ta-pop").hidden === false);
ok("empty state is shown", !!q(".ta-empty"));

// ── IT IS A MODAL (2026-08-23) ───────────────────────────────────────
// Reported: "currently it closes if i drag or click something." It was a
// popover that shut on any click outside itself, so a drag inside it that
// finished outside registered as an outside click and closed it mid-edit.
ok("dialog role", q(".ta-pop").getAttribute("role") === "dialog");
ok("marked modal", q(".ta-pop").getAttribute("aria-modal") === "true");
ok("backdrop shown while open", q(".ta-backdrop").hidden === false);
ok("page scroll locked",
   doc.documentElement.classList.contains("ta-locked"));

click(doc.body);
ok("clicking the page does NOT close it", q(".ta-pop").hidden === false);

// A drag that starts on a field and ends on the page fires a click whose
// target is the page. That must not close the dialog either.
q("[data-ta-new-text]").dispatchEvent(
  new window.MouseEvent("mousedown", { bubbles: true }));
doc.body.dispatchEvent(new window.MouseEvent("mouseup", { bubbles: true }));
click(doc.body);
ok("a drag ending outside does NOT close it", q(".ta-pop").hidden === false);

// A deliberate press on the backdrop is still a way out.
q(".ta-backdrop").dispatchEvent(
  new window.MouseEvent("mousedown", { bubbles: true }));
ok("pressing the backdrop closes it", q(".ta-pop").hidden === true);
ok("backdrop hidden with it", q(".ta-backdrop").hidden === true);
ok("scroll lock released",
   !doc.documentElement.classList.contains("ta-locked"));

// ── escape ───────────────────────────────────────────────────────────
click(q(".ta-btn"));
doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
ok("Escape closes it", q(".ta-pop").hidden === true);

// ── the AM/PM chooser ────────────────────────────────────────────────
click(q(".ta-btn"));
ok("AM/PM buttons exist", doc.querySelectorAll('[data-ta-mer="at"]').length === 2);

// SELECTED MUST LOOK DIFFERENT FROM UNSELECTED — asserted on the COMPUTED
// background, not on the class. The classes were correct the whole time a
// stray `.ta-add button` rule was painting every button in the add form
// indigo: same specificity, later in the sheet, so it won and both AM and
// PM rendered as selected. A class-only assertion cannot see that.
{
  const bg = (el) => window.getComputedStyle(el).backgroundColor;
  const am = doc.querySelector('[data-ta-mer="at"][data-v="am"]');
  const pm = doc.querySelector('[data-ta-mer="at"][data-v="pm"]');
  ok("selected and unselected AM/PM differ visually", bg(am) !== bg(pm));
  const chip = doc.querySelector('[data-ta-day="1"]');
  const addb = q("[data-ta-add]");
  ok("a weekday chip is not painted like the Add button", bg(chip) !== bg(addb));
}
ok("AM selected by default",
   doc.querySelector('[data-ta-mer="at"][data-v="am"]').classList.contains("on"));

q("[data-ta-new-at]").value = "5";
q("[data-ta-new-at]").dispatchEvent(new window.Event("input", {bubbles:true}));
ok("preview shows the AM reading", /5:00 AM/.test(q("[data-ta-preview]").textContent));

click(doc.querySelector('[data-ta-mer="at"][data-v="pm"]'));
ok("PM becomes selected",
   doc.querySelector('[data-ta-mer="at"][data-v="pm"]').classList.contains("on"));
ok("preview follows to PM", /5:00 PM/.test(q("[data-ta-preview]").textContent));

q("[data-ta-new-text]").value = "Evening walk";
click(q("[data-ta-add]"));
ok("added at the chosen meridiem",
   /5:00 PM/.test(doc.querySelector(".ta-when b").textContent));
{
  const posts = sent("POST", "/api/announcer/items");
  ok("adding pushes it to the server", posts.length >= 1);
  const last = posts[posts.length - 1];
  ok("...as a list of items", Array.isArray(last.body.items));
  ok("...carrying the resolved 24h time", last.body.items[0].at === "17:00");
  ok("...and its text", last.body.items[0].text === "Evening walk");
  // A real check, not a placeholder: without this header every write is
  // rejected and the schedule silently stops syncing.
  ok("...with a CSRF header", "X-CSRFToken" in last.headers);
}
ok("chooser resets to AM after adding",
   doc.querySelector('[data-ta-mer="at"][data-v="am"]').classList.contains("on"));

// Typing the meridiem must beat the buttons, and say so by dimming them.
q("[data-ta-new-at]").value = "9am";
q("[data-ta-new-at]").dispatchEvent(new window.Event("input", {bubbles:true}));
ok("buttons dim when the text settles it",
   doc.querySelector('[data-ta-mer="at"][data-v="am"]').classList.contains("moot"));
click(doc.querySelector('[data-ta-mer="at"][data-v="pm"]'));
q("[data-ta-new-text]").value = "Morning";
click(q("[data-ta-add]"));
ok("typed 9am wins over the PM button",
   /9:00 AM/.test(doc.querySelectorAll(".ta-when b")[0].textContent) ||
   /9:00 AM/.test(doc.querySelectorAll(".ta-when b")[1].textContent));

// Clear the list so the recurrence block starts from nothing.
const delsBefore = sent("DELETE", "/api/announcer/items/").length;
while (doc.querySelector("[data-ta-del]")) click(doc.querySelector("[data-ta-del]"));
ok("list cleared for the next block", doc.querySelectorAll(".ta-item").length === 0);
ok("deleting tells the server too",
   sent("DELETE", "/api/announcer/items/").length > delsBefore);
click(q("[data-ta-close]"));

// ── the recurrence controls ──────────────────────────────────────────
click(q(".ta-btn"));
ok("repeat selector present", !!q("[data-ta-new-repeat]"));
ok("start defaults to today",
   /^\d{4}-\d{2}-\d{2}$/.test(q("[data-ta-new-start]").value));
ok("day chips hidden unless custom", q("[data-ta-days]").hidden === true);

q("[data-ta-new-repeat]").value = "custom";
q("[data-ta-new-repeat]").dispatchEvent(new window.Event("change", {bubbles:true}));
ok("choosing 'custom' reveals the days", q("[data-ta-days]").hidden === false);

// Adding with no day chosen must be refused, not silently created dead.
q("[data-ta-new-at]").value = "8am";
click(q("[data-ta-add]"));
ok("refuses custom with no days", doc.querySelectorAll(".ta-item").length === 0);

click(doc.querySelector('[data-ta-day="1"]'));
click(doc.querySelector('[data-ta-day="3"]'));
ok("day chips toggle on", doc.querySelectorAll(".ta-days .on").length === 2);
click(q("[data-ta-add]"));
ok("adds once days are chosen", doc.querySelectorAll(".ta-item").length === 1);
ok("row states the rule", /Mon Wed/.test(q(".ta-when i").textContent));
ok("panel stays open", q(".ta-pop").hidden === false);

// An end before the start would never fire, so it must be refused.
q("[data-ta-new-repeat]").value = "daily";
q("[data-ta-new-repeat]").dispatchEvent(new window.Event("change", {bubbles:true}));
q("[data-ta-new-at]").value = "9am";
q("[data-ta-new-start]").value = "2026-09-10";
q("[data-ta-new-end]").value = "2026-09-01";
click(q("[data-ta-add]"));
ok("refuses an end before the start", doc.querySelectorAll(".ta-item").length === 1);
q("[data-ta-new-end]").value = "2026-09-30";
click(q("[data-ta-add]"));
ok("accepts a valid window", doc.querySelectorAll(".ta-item").length === 2);
ok("row states the window",
   /until 30 Sep 2026/.test(doc.querySelectorAll(".ta-when i")[1].textContent) ||
   /until 30 Sep 2026/.test(doc.querySelectorAll(".ta-when i")[0].textContent));

// Leave the panel as this block found it — closed — so the next block's
// toggle opens rather than closes. A test that depends on the previous
// block's leftover state fails for a reason that has nothing to do with
// the thing it is testing.
click(q("[data-ta-close]"));

// ── the interval buttons highlight ───────────────────────────────────
click(q(".ta-btn"));
click(doc.querySelector('[data-ta-every="45"]'));
ok("choosing an interval pushes settings",
   sent("POST", "/api/announcer/settings").length >= 1);
ok("45m becomes the selected interval",
   doc.querySelector('[data-ta-every="45"]').classList.contains("on"));
ok("...and 15m is no longer selected",
   !doc.querySelector('[data-ta-every="15"]').classList.contains("on"));
ok("panel stays open after choosing an interval", q(".ta-pop").hidden === false);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

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

// ── a genuine outside click must still close it ──────────────────────
click(doc.body);
ok("clicking the page closes it", q(".ta-pop").hidden === true);

// ── escape ───────────────────────────────────────────────────────────
click(q(".ta-btn"));
doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
ok("Escape closes it", q(".ta-pop").hidden === true);

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
ok("45m becomes the selected interval",
   doc.querySelector('[data-ta-every="45"]').classList.contains("on"));
ok("...and 15m is no longer selected",
   !doc.querySelector('[data-ta-every="15"]').classList.contains("on"));
ok("panel stays open after choosing an interval", q(".ta-pop").hidden === false);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

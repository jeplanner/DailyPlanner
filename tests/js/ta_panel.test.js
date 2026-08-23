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
  let json = { ok: true };
  if (String(url).indexOf("/api/announcer/state") === 0) {
    json = { ok: true, every: 15, label: "", items: [] };   // empty server
  } else if (String(url).indexOf("/api/checklist/mutes") === 0) {
    json = { items: [
      { id: "c1", name: "Take Vitamin Tablet", times: ["21:30"], muted: false },
      { id: "c2", name: "Drink water", times: ["08:00", "11:00"], muted: true },
    ] };
  }
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

// Flush pending promises. The mute list is fetched, so a synchronous
// assertion after opening the panel races the microtask queue and sees an
// empty list — which looks exactly like a broken feature.
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
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

// ── TABS (2026-08-23) ────────────────────────────────────────────────
// The panel had grown into one scroll of eleven unrelated controls, which
// is what "the UX is not friendly" meant. Four tabs, grouped by how often
// each is touched.
click(q(".ta-btn"));
ok("four tabs", doc.querySelectorAll("[data-ta-tab]").length === 4);
ok("opens on Announcements",
   doc.querySelector('[data-ta-pane="items"]').hidden === false);
ok("other panes hidden",
   doc.querySelector('[data-ta-pane="clock"]').hidden === true);

// Start/Pause/Stop and the status line stay OUTSIDE the tabs, because they
// are what you open the panel to check.
ok("mode buttons are not in a pane",
   !q('[data-ta-mode="on"]').closest("[data-ta-pane]"));
ok("status line is not in a pane", !q("[data-ta-now]").closest("[data-ta-pane]"));

click(doc.querySelector('[data-ta-tab="clock"]'));
ok("clock tab shows", doc.querySelector('[data-ta-pane="clock"]').hidden === false);
ok("...and items hides", doc.querySelector('[data-ta-pane="items"]').hidden === true);
ok("...and the tab is marked selected",
   doc.querySelector('[data-ta-tab="clock"]').getAttribute("aria-selected") === "true");
click(doc.querySelector('[data-ta-tab="items"]'));
ok("back to announcements",
   doc.querySelector('[data-ta-pane="items"]').hidden === false);

// The four advanced fields are folded away by default — showing all seven
// inputs at once is most of why this looked forbidding.
ok("advanced fields start hidden", q("[data-ta-advanced]").hidden === true);
click(q("[data-ta-more]"));
ok("...and open on request", q("[data-ta-advanced]").hidden === false);
click(q("[data-ta-more]"));
ok("...and fold again", q("[data-ta-advanced]").hidden === true);

// Editing something that USES an advanced field must reveal it, or the
// form shows values the row displays and the inputs do not.
q("[data-ta-new-at]").value = "8";
click(q("[data-ta-more]"));
q("[data-ta-new-until]").value = "8pm";
q("[data-ta-new-mins]").value = "60";
q("[data-ta-new-text]").value = "Windowed";
click(q("[data-ta-add]"));
click(q("[data-ta-more]"));            // fold it back down
ok("folded before editing", q("[data-ta-advanced]").hidden === true);
click(q("[data-ta-edit]"));
ok("editing a windowed announcement opens the advanced block",
   q("[data-ta-advanced]").hidden === false);
click(q("[data-ta-cancel]"));
while (doc.querySelector("[data-ta-del]")) click(doc.querySelector("[data-ta-del]"));
click(q("[data-ta-close]"));

// ── THE CHIME (2026-08-23) ───────────────────────────────────────────
// Reported: "audio notifications are not working". Speech is suspended
// with the screen off and a push notification's sound belongs to the OS,
// so a real audio file is the only sound this app can make when locked.
click(q(".ta-btn"));
click(doc.querySelector('[data-ta-tab="device"]'));
// Permission state must be STATED. The self-heal never prompts, so on a
// device where permission was never granted it does nothing — correctly,
// and silently. That silence is why a phone received nothing for a day
// while everything else looked configured.
ok("permission state is shown", !!q("[data-ta-perm]"));
ok("...and names the state", /granted|default|denied|unsupported/
   .test(q("[data-ta-perm]").className));

ok("chime control exists", !!q("[data-ta-chime]"));
ok("chime is ON by default", q("[data-ta-chime]").checked === true);
{
  // It must use a real <audio> element. Web Audio is not treated as
  // playback and is exactly what a locked phone declines to run.
  const before = doc.querySelectorAll("audio").length;
  window.TimeAnnouncer._playChime();
  const el = doc.getElementById("ta-chime");
  ok("plays through a real audio element", !!el);
  ok("...pointing at a real file",
     (el.getAttribute("src") || "").indexOf("audio-chime") !== -1);
}
// A click on a checkbox ALREADY toggles it, in jsdom and in a browser.
// Pre-setting .checked as well flips it twice and tests nothing.
click(q("[data-ta-chime]"));
ok("chime can be switched off", q("[data-ta-chime]").checked === false);
click(q("[data-ta-chime]"));
ok("...and back on", q("[data-ta-chime]").checked === true);
click(doc.querySelector('[data-ta-tab="items"]'));
click(q("[data-ta-close]"));

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

// ── EDITING (2026-08-23) ─────────────────────────────────────────────
// Previously an announcement could only be added, switched off or deleted.
// Changing one meant deleting it and retyping every field.
click(q(".ta-btn"));
// Start from empty: the recurrence block above leaves rows behind, and a
// count assertion that depends on a previous block fails for a reason
// unrelated to what it is testing.
while (doc.querySelector("[data-ta-del]")) click(doc.querySelector("[data-ta-del]"));
q("[data-ta-new-at]").value = "7";
q("[data-ta-new-text]").value = "Original";
click(q("[data-ta-add]"));
ok("one announcement to edit", doc.querySelectorAll(".ta-item").length === 1);
ok("rows carry an edit control", !!q("[data-ta-edit]"));

click(q("[data-ta-edit]"));
ok("the form fills with the existing values",
   q("[data-ta-new-at]").value === "07:00" &&
   q("[data-ta-new-text]").value === "Original");
ok("the button becomes Save", q("[data-ta-add]").textContent === "Save");
ok("Cancel appears", q("[data-ta-cancel]").hidden === false);
ok("the row shows it is being edited", !!q(".ta-item.editing"));

// Cancel must not change anything.
click(q("[data-ta-cancel]"));
ok("cancel restores Add", q("[data-ta-add]").textContent === "Add");
ok("cancel changes nothing", /7:00 AM/.test(q(".ta-when b").textContent));
ok("still one row", doc.querySelectorAll(".ta-item").length === 1);

// Saving replaces IN PLACE — one row, not two, and the id survives.
click(q("[data-ta-edit]"));
q("[data-ta-new-at]").value = "9.30";
q("[data-ta-new-text]").value = "Edited";
const idBefore = q(".ta-item").getAttribute("data-id");
click(q("[data-ta-add]"));
ok("still ONE row after saving", doc.querySelectorAll(".ta-item").length === 1);
ok("the new time took", /9:30 AM/.test(q(".ta-when b").textContent));
ok("the new text took", /Edited/.test(q(".ta-what").textContent));
ok("the id is unchanged", q(".ta-item").getAttribute("data-id") === idBefore);
ok("the edit was pushed to the server", (() => {
  const p = sent("POST", "/api/announcer/items");
  return p[p.length - 1].body.items[0].id === idBefore;
})());
ok("back to Add mode", q("[data-ta-add]").textContent === "Add");

while (doc.querySelector("[data-ta-del]")) click(doc.querySelector("[data-ta-del]"));
click(q("[data-ta-close]"));

// ── editing the reminder NOTIFICATIONS ───────────────────────────────
click(q(".ta-btn"));
await tick();
ok("reminder rows are listed", doc.querySelectorAll("[data-mute-id]").length === 2);
ok("a muted one reads as muted",
   /muted/.test(doc.querySelector('[data-mute-id="c2"]').textContent));
ok("reminder rows carry an edit control", !!q("[data-ta-mute-edit]"));

click(doc.querySelector('[data-mute-id="c1"] [data-ta-mute-edit]'));
ok("the times become editable", q("[data-ta-mute-times]").value === "21:30");
q("[data-ta-mute-times]").value = "6.30am, 9pm";
click(q("[data-ta-mute-save]"));
await tick();
ok("the new times are shown",
   /6:30 AM/.test(doc.querySelector('[data-mute-id="c1"]').textContent));
ok("...through the existing checklist API",
   sent("PATCH", "/api/checklist/items/c1").length === 1);
ok("...as parsed 24-hour times", (() => {
  const p = sent("PATCH", "/api/checklist/items/c1")[0];
  return JSON.stringify(p.body.reminder_times) === '["06:30","21:00"]';
})());
ok("panel stays open throughout", q(".ta-pop").hidden === false);
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
})();

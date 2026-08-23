/* The Backlog page's capture box and Send → router, in a real DOM.
 *
 * The page is rendered by Flask (tests/test_smoke.py writes it to the path
 * given as argv[2]) and the real static/js/backlog.js is run against it, so
 * this exercises the TEMPLATE and the SCRIPT together. A selector that only
 * one of them knows about is exactly the kind of break that source-reading
 * assertions cannot see.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const SRC = __dirname + "/../../static/js/backlog.js";

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"),
                      { runScripts: "outside-only", pretendToBeVisual: true,
                        url: "https://example.test/backlog" });
const { window } = dom;
const doc = window.document;

const calls = [];
window.fetch = function (url, opts) {
  opts = opts || {};
  calls.push({ url: String(url), method: opts.method || "GET",
               body: opts.body ? JSON.parse(opts.body) : null });
  return Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve({ status: "ok", created: [] }),
  });
};
const sent = (url) => calls.filter((c) => c.url === url);

window.eval(fs.readFileSync(SRC, "utf8"));

const q = (s) => doc.querySelector(s);
const click = (el) => el.dispatchEvent(
  new window.MouseEvent("click", { bubbles: true, cancelable: true }));
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {

// ── the capture box ──────────────────────────────────────────────────
ok("there is a capture box", !!q("[data-bk-text]"));
ok("...and an add button", !!q("[data-bk-add]"));
ok("...and a list for captured items to land in", !!q("[data-bk-list-future]"));

q("[data-bk-text]").value = "Renew passport\nBook dentist";
q("[data-bk-capture]").dispatchEvent(
  new window.Event("submit", { bubbles: true, cancelable: true }));
await tick();
ok("capturing posts to the backlog", sent("/api/backlog/capture").length === 1);
ok("...sending the whole pasted block, split server-side",
   sent("/api/backlog/capture")[0].body.text.indexOf("Book dentist") !== -1);

// ── the router opens a DIALOG, not an immediate move ─────────────────
const row = doc.querySelector('.bk-item[data-kind="bucket"]');
ok("a captured row is rendered", !!row);
click(row.querySelector("[data-bk-send]"));
ok("Send opens the menu", q("[data-bk-menu]").hidden === false);

const dest = Array.prototype.filter.call(
  q("[data-bk-menu]").querySelectorAll("button"),
  (b) => b.textContent === "Quick Bucket")[0];
ok("Quick Bucket is offered", !!dest);
click(dest);
ok("the menu closes", q("[data-bk-menu]").hidden === true);
ok("a dialog opens instead of moving straight away",
   q("[data-bk-modal]").hidden === false);
ok("...over a backdrop", q("[data-bk-back]").hidden === false);

// THE POINT OF THE DIALOG: it asks WHEN. Sending everything to "now" moves
// the pile rather than prioritising it.
const when = q("[data-bk-modal] select[name=bucket]");
ok("it asks when the task is due", !!when);
ok("...offering more than just Now", when.options.length > 1);
const textFld = q("[data-bk-modal] input[name=text]");
ok("...and lets the wording be fixed first", !!textFld);

const before = calls.length;
when.value = "1h";
q("[data-bk-modal] form").dispatchEvent(
  new window.Event("submit", { bubbles: true, cancelable: true }));
await tick();
const moved = sent("/api/backlog/send");
ok("submitting moves it", moved.length === 1);
ok("...carrying the chosen bucket", moved[0].body.bucket === "1h");
ok("...and the destination", moved[0].body.to === "quick");
ok("the dialog closes", q("[data-bk-modal]").hidden === true);
ok("...and the backdrop with it", q("[data-bk-back]").hidden === true);

// ── a project task is offered only the one safe route ────────────────
const task = doc.querySelector('.bk-item[data-kind="task"]');
if (task) {
  click(task.querySelector("[data-bk-send]"));
  const labels = Array.prototype.map.call(
    q("[data-bk-menu]").querySelectorAll("button"), (b) => b.textContent);
  ok("a project task can be promoted", labels.indexOf("Quick Bucket") !== -1);
  ok("...but not re-filed under another project",
     labels.indexOf("A project") === -1);
  ok("...and not turned into a note", labels.indexOf("Note") === -1);
  click(doc.body);
}

// ── Escape closes the dialog, not just the menu ──────────────────────
click(doc.querySelector('.bk-item[data-kind="bucket"] [data-bk-send]'));
click(Array.prototype.filter.call(
  q("[data-bk-menu]").querySelectorAll("button"),
  (b) => b.textContent === "Quick Bucket")[0]);
ok("dialog is open again", q("[data-bk-modal]").hidden === false);
doc.dispatchEvent(new window.KeyboardEvent("keydown",
                                           { key: "Escape", bubbles: true }));
ok("Escape closes it", q("[data-bk-modal]").hidden === true);

// ── A BACKLOG ITEM THAT SPEAKS (2026-08-23) ──────────────────────────
// "some backlog items, i want to make it as announcement."
//
// Every other destination is a place the work GOES, and the row leaves the
// backlog behind. An announcement is not a place — it is something the item
// now does — so the row must stay. Sending it away would leave you being
// reminded, out loud, about a task no longer on any list.
{
  const row = doc.querySelector('.bk-item[data-kind="bucket"]');
  click(row.querySelector("[data-bk-send]"));
  const entry = Array.prototype.filter.call(
    q("[data-bk-menu]").querySelectorAll("button"),
    (b) => /Announce/.test(b.textContent))[0];
  ok("announcing is offered", !!entry);
  click(entry);
  ok("the dialog opens", q("[data-bk-modal]").hidden === false);

  const at = q("[data-bk-modal] input[name=at]");
  ok("it asks for a time", !!at && at.type === "time");
  ok("...and how often", !!q("[data-bk-modal] select[name=repeat]"));
  ok("...and what to say", !!q("[data-bk-modal] input[name=text]"));

  // A time is required: an announcement with no time can never fire, and a
  // silently-guessed one is worse than being asked.
  const before = calls.length;
  q("[data-bk-modal] form").dispatchEvent(
    new window.Event("submit", { bubbles: true, cancelable: true }));
  ok("refuses to save without a time", calls.length === before);
  ok("...and stays open to say so", q("[data-bk-modal]").hidden === false);

  at.value = "19:45";
  q("[data-bk-modal] select[name=repeat]").value = "daily";
  q("[data-bk-modal] form").dispatchEvent(
    new window.Event("submit", { bubbles: true, cancelable: true }));
  await tick();

  const posted = sent("/api/announcer/items");
  ok("it posts to the announcer's own endpoint", posted.length === 1);
  ok("...as a list, which is what that endpoint takes",
     Array.isArray(posted[0].body.items));
  const made = posted[0].body.items[0];
  ok("...at the time given", made.at === "19:45");
  ok("...with the repeat given", made.repeat === "daily");
  ok("...switched on", made.on === true);
  ok("...carrying the words", !!made.text);

  // THE ROW MUST NOT BE MOVED OR DROPPED.
  ok("the item is not sent anywhere", sent("/api/backlog/send").length === 1);
  ok("...and not dropped from the backlog",
     sent("/api/backlog/drop").length === 0);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
})();

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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
})();

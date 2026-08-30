/* The paragraph reader's confirm-before-save dialog, in a real DOM.
 *
 * "hope once i press the add, it pops up and i am able to correct it if
 * needed before saving to quick bucket" (2026-08-30).
 *
 * That is a behaviour, not a string: press Add on a paragraph and a dialog
 * has to appear; correct a row and the CORRECTION has to be what is saved;
 * close it and what you typed has to still be in the box. The page is
 * rendered by Flask (tests/test_smoke.py passes the path as argv[2]) and
 * the real static/js/quick_bucket.js is run against it.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const SRC = __dirname + "/../../static/js/quick_bucket.js";
const src = fs.readFileSync(SRC, "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const CANDIDATES = [
  {
    text: "Reflect feedback", time_bucket: "at",
    due_at: "2026-08-31T06:30:00+00:00", backlog_due: null,
    planned_minutes: null, use: true, confidence: "medium",
    why: ["scheduled from “before 12pm”"], source: "Reflect feedback before 12pm",
  },
  {
    text: "Review deployment exceptions", time_bucket: "now", due_at: null,
    backlog_due: null, planned_minutes: null, use: true, confidence: "high",
    why: ["no timing found — defaulted to Now"],
    source: "review deployment exceptions",
  },
  {
    text: "I am exhausted", time_bucket: "now", due_at: null,
    backlog_due: null, planned_minutes: null, use: false, confidence: "low",
    why: ["no timing found — defaulted to Now"], source: "I am exhausted",
  },
];

function boot() {
  const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://example.test/quick-bucket",
  });
  const { window } = dom;
  const doc = window.document;

  const calls = [];
  window.fetch = function (url, opts = {}) {
    let body = null;
    try { body = opts.body ? JSON.parse(opts.body) : null; } catch (_) {}
    calls.push({ url: String(url), method: opts.method || "GET", body });

    const reply = (obj) => Promise.resolve({
      ok: true, status: 200, json: () => Promise.resolve(obj),
    });
    if (String(url).includes("/interpret")) {
      // One candidate for a short line, the full set for a paragraph.
      const words = String((body && body.text) || "").split(/\s+/).length;
      return reply({
        items: words > 6 ? CANDIDATES : [CANDIDATES[1]],
        used_ai: false, note: null, count: words > 6 ? CANDIDATES.length : 1,
      });
    }
    if (String(url).startsWith("/api/quick-bucket") && (opts.method === "POST")) {
      return reply({ ok: true, item: { id: "x" + calls.length, ...(body || {}) } });
    }
    return reply({ items: [] });
  };

  // jsdom has no matchMedia and the page uses it to pick a default for
  // the Top-5 panel. Stubbing it as "wide" keeps the boot on the desktop
  // path, which is the one this dialog is being tested on.
  window.matchMedia = window.matchMedia || ((q) => ({
    matches: false, media: q, addEventListener() {}, removeEventListener() {},
    addListener() {}, removeListener() {}, onchange: null,
  }));

  window.eval(src);
  doc.dispatchEvent(new window.Event("DOMContentLoaded"));
  return { window, doc, calls };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

const submit = async (doc, window, text) => {
  const input = doc.querySelector("#qb-add-input");
  input.value = text;
  doc.querySelector("#qb-add-form")
     .dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 6; i++) await flush();
};

(async () => {
  // ── pressing Add on a paragraph opens the dialog ──────────────────
  {
    const { window, doc, calls } = boot();
    const panel = doc.querySelector("#qb-read");
    ok("the dialog starts hidden", panel.hidden === true);

    await submit(doc, window,
      "Reflect feedback before 12pm, review deployment exceptions. I am exhausted");

    ok("Add asked the server to read it",
       calls.some((c) => c.url.includes("/interpret")));
    ok("the dialog is up", panel.hidden === false);
    ok("nothing was saved yet",
       !calls.some((c) => c.url === "/api/quick-bucket" && c.method === "POST"));
    ok("what you typed is still in the box",
       doc.querySelector("#qb-add-input").value.startsWith("Reflect feedback"));

    const rows = doc.querySelectorAll("#qb-read-list .qb-read-row");
    ok("one row per candidate", rows.length === CANDIDATES.length);
    ok("the remark is present but unticked",
       rows[2].querySelector("[data-read-use]").checked === false);
    ok("the timed one shows when it will fire",
       /\d/.test(rows[0].querySelector(".qb-read-when").textContent));
    ok("every row explains itself",
       [...rows].every((r) => r.querySelector(".qb-read-why").textContent.trim()));
    ok("the button counts only what is ticked",
       doc.querySelector("#qb-read-add").textContent === "Add 2 tasks");
  }

  // ── correcting a row changes what is saved ────────────────────────
  {
    const { window, doc, calls } = boot();
    await submit(doc, window,
      "Reflect feedback before 12pm, review deployment exceptions. I am exhausted");

    const rows = doc.querySelectorAll("#qb-read-list .qb-read-row");

    // Rename the first, give it an estimate, and drop the second.
    const title = rows[0].querySelector("[data-read-text]");
    title.value = "Reflect on the feedback";
    title.dispatchEvent(new window.Event("input", { bubbles: true }));

    const mins = rows[0].querySelector("[data-read-mins]");
    mins.value = "20";
    mins.dispatchEvent(new window.Event("input", { bubbles: true }));

    const drop = rows[1].querySelector("[data-read-use]");
    drop.checked = false;
    drop.dispatchEvent(new window.Event("input", { bubbles: true }));
    ok("unticking updates the count",
       doc.querySelector("#qb-read-add").textContent === "Add 1 task");

    doc.querySelector("#qb-read-add").click();
    for (let i = 0; i < 8; i++) await flush();

    const saved = calls.filter((c) => c.url === "/api/quick-bucket" && c.method === "POST");
    ok("only the ticked row was saved", saved.length === 1);
    ok("...with the corrected title",
       saved[0].body.text === "Reflect on the feedback");
    ok("...the estimate you typed", saved[0].body.planned_minutes === 20);
    ok("...and the time it was shown with",
       saved[0].body.due_at === "2026-08-31T06:30:00+00:00" &&
       saved[0].body.time_bucket === "at");
    ok("the dialog closed itself", doc.querySelector("#qb-read").hidden === true);
    ok("the box was emptied, because those are real rows now",
       doc.querySelector("#qb-add-input").value === "");
  }

  // ── changing the bucket by hand drops the alarm ───────────────────
  {
    const { window, doc, calls } = boot();
    await submit(doc, window,
      "Reflect feedback before 12pm, review deployment exceptions. I am exhausted");

    const row = doc.querySelector("#qb-read-list .qb-read-row");
    const sel = row.querySelector("[data-read-bucket]");
    sel.value = "2h";
    sel.dispatchEvent(new window.Event("input", { bubbles: true }));

    row.querySelector("[data-read-use]").checked = true;
    doc.querySelectorAll("#qb-read-list [data-read-use]").forEach((c, i) => {
      if (i > 0) { c.checked = false; c.dispatchEvent(new window.Event("input", { bubbles: true })); }
    });
    doc.querySelector("#qb-read-add").click();
    for (let i = 0; i < 8; i++) await flush();

    const saved = calls.filter((c) => c.url === "/api/quick-bucket" && c.method === "POST");
    ok("picking a countdown bucket saves that bucket",
       saved.length === 1 && saved[0].body.time_bucket === "2h");
    ok("...and cancels the pinned time, which would have rung anyway",
       !saved[0].body.due_at);
  }

  // ── closing keeps your text ───────────────────────────────────────
  {
    const { window, doc, calls } = boot();
    await submit(doc, window,
      "Reflect feedback before 12pm, review deployment exceptions. I am exhausted");

    doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    ok("Escape closes the dialog", doc.querySelector("#qb-read").hidden === true);
    ok("...and nothing was saved",
       !calls.some((c) => c.url === "/api/quick-bucket" && c.method === "POST"));
    ok("...and the paragraph is still in the box, to fix by hand",
       doc.querySelector("#qb-add-input").value.startsWith("Reflect feedback"));
  }

  // ── a plain one-liner is not worth a dialog ───────────────────────
  {
    const { window, doc, calls } = boot();
    await submit(doc, window, "call mum");
    ok("a short plain line is added without asking",
       !calls.some((c) => c.url.includes("/interpret")));
    ok("...and it really was added",
       calls.some((c) => c.url === "/api/quick-bucket" && c.method === "POST" &&
                         c.body.text === "call mum"));
    ok("...with no dialog in the way", doc.querySelector("#qb-read").hidden === true);
  }

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();

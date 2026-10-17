/* Random thoughts with REAL row shapes: audio null / pending / ready,
 * studied and due. The notes test feeds rows with no `audio` key at all,
 * which skips every audio code path - a crash there blanked the list.
 * Run by tests/test_prep_hub.py with the Flask-rendered page as argv[2].
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const SRC = __dirname + "/../../static/js/prep_thoughts.js";
let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const dom = new JSDOM(fs.readFileSync(process.argv[2], "utf8"),
                      { runScripts: "outside-only", pretendToBeVisual: true,
                        url: "https://example.test/ai-sde/thoughts" });
const { window } = dom;
const doc = window.document;
const errors = [];
window.addEventListener("error", (e) => errors.push(String(e.error || e.message)));
window.PrepHub = { esc: (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
                   say: () => {} };
window.scrollTo = () => {};

const T = "2026-10-16T09:00:00Z", PAST = "2026-01-01T00:00:00Z";
const base = { parent_id: null, answer: "An answer.", status: "ready", tags: [], images: [], notes: [], created_at: T };
const items = [
  Object.assign({}, base, { id: "a1", root_id: "a1", question: "Studied, due, no audio yet?", understood: true, next_review_at: PAST, review_stage: 0, audio: null }),
  Object.assign({}, base, { id: "a2", root_id: "a2", question: "Has audio?", understood: true, next_review_at: PAST, audio: { status: "ready", hash: "h2", seconds: 301, key: "u/a2-h2.mp3" } }),
  Object.assign({}, base, { id: "a3", root_id: "a3", question: "Being made?", audio: { status: "pending", at: new Date().toISOString() } }),
  Object.assign({}, base, { id: "a4", root_id: "a4", question: "Not studied, no audio?", understood: false, audio: null }),
  Object.assign({}, base, { id: "a5", root_id: "a5", question: "Still answering?", status: "pending", answer: "", audio: null }),
];
const calls = [];
window.fetch = function (url, opts) {
  opts = opts || {}; url = String(url);
  calls.push({ url, method: opts.method || "GET" });
  const json = (b) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(b) });
  if (url.indexOf("/api/prep/thoughts?") === 0)
    return json({ available: true, provider: true, notes_available: true, items: JSON.parse(JSON.stringify(items)) });
  if (/\/audio$/.test(url)) return json({ audio: { status: "pending", at: new Date().toISOString() } });
  return json({});
};

window.eval(fs.readFileSync(SRC, "utf8"));
const tick = () => new Promise((r) => setTimeout(r, 0));
const card = (id) => doc.querySelector('.th-card[data-id="' + id + '"]');

(async () => {
  await window.PrepThoughts.load(); await tick(); await tick();
  ok("no script errors", errors.length === 0);
  if (errors.length) console.log(errors.join("\n"));
  ok("every question is listed", ["a1", "a2", "a3", "a4", "a5"].every((id) => !!card(id)));
  ok("Listen to due is offered", !doc.getElementById("th-listen-due").hidden);
  ok("a studied question without audio is queued on load",
     calls.some((c) => c.method === "POST" && /\/a1\/audio$/.test(c.url)));
  ok("...an unstudied one is not", !calls.some((c) => /\/a4\/audio$/.test(c.url)));

  // Open each kind of card: none of them may break the list.
  for (const id of ["a2", "a3", "a4", "a5"]) {
    card(id).querySelector('[data-th="toggle"]').dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    await tick();
  }
  ok("still no script errors after opening cards", errors.length === 0);
  ok("ready audio shows Listen with its length", /Listen \(5:01\)/.test(card("a2").textContent));
  ok("pending audio says it is being made", /Making the 5-minute audio/.test(card("a3").textContent));
  ok("no audio offers the button", !!card("a4").querySelector('[data-th="audio-make"]'));
  ok("an unanswered question has no audio controls", !card("a5").querySelector(".th-audio"));

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log("CRASH " + (e && e.stack || e)); process.exit(1); });

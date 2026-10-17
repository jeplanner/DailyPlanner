/* Your notes on a Random thoughts question, in a real DOM.
 *
 * The page is rendered by Flask (tests/test_prep_hub.py writes
 * /ai-sde/thoughts to the path given as argv[2]) and the real
 * static/js/prep_thoughts.js runs against it, with fetch stubbed.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const SRC = __dirname + "/../../static/js/prep_thoughts.js";

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"),
                      { runScripts: "outside-only", pretendToBeVisual: true,
                        url: "https://example.test/ai-sde/thoughts" });
const { window } = dom;
const doc = window.document;

const said = [];
window.PrepHub = {
  esc: (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
  say: (m, k) => said.push([m, k]),
};
window.confirm = () => true;
window.scrollTo = () => {};

const T = "2026-10-16T09:00:00Z";
let notesAvailable = true;
const notes = { q1: [{ id: "n1", text: "Asked in round 2", created_at: T, updated_at: T }], f1: [] };
const items = () => [
  { id: "q1", root_id: "q1", parent_id: null, question: "How does a chat app catch up?",
    answer: "## The short answer\nA cursor.", status: "ready", tags: [], images: [],
    notes: notes.q1, created_at: T },
  { id: "f1", root_id: "q1", parent_id: "q1", question: "Simpler?", answer: "Like a bookmark.",
    status: "ready", tags: [], images: [], notes: notes.f1, created_at: "2026-10-16T09:05:00Z" },
];
const calls = [];
const json = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
window.fetch = function (url, opts) {
  opts = opts || {};
  url = String(url);
  const body = opts.body ? JSON.parse(opts.body) : null;
  calls.push({ url, method: opts.method || "GET", body });
  if (url.indexOf("/api/prep/thoughts?") === 0)
    return json({ available: true, provider: true, notes_available: notesAvailable, items: items() });
  let m = url.match(/^\/api\/prep\/thoughts\/(\w+)\/notes$/);
  if (m) {
    notes[m[1]] = notes[m[1]].concat([{ id: "n" + calls.length, text: body.text, created_at: T, updated_at: T }]);
    return json({ notes: notes[m[1]] });
  }
  m = url.match(/^\/api\/prep\/thoughts\/(\w+)\/notes\/(\w+)$/);
  if (m) {
    notes[m[1]] = notes[m[1]].map((n) => n.id === m[2] ? Object.assign({}, n, { text: body.text, updated_at: "2026-10-17T09:00:00Z" }) : n);
    return json({ notes: notes[m[1]] });
  }
  m = url.match(/^\/api\/prep\/thoughts\/(\w+)\/notes\/(\w+)\/delete$/);
  if (m) {
    notes[m[1]] = notes[m[1]].filter((n) => n.id !== m[2]);
    return json({ notes: notes[m[1]] });
  }
  return json({});
};
const posted = (re) => calls.filter((c) => c.method === "POST" && re.test(c.url));

window.eval(fs.readFileSync(SRC, "utf8"));

const q = (s) => doc.querySelector(s);
const qa = (s) => Array.prototype.slice.call(doc.querySelectorAll(s));
const click = (el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
const type = (el, v) => { el.value = v; el.dispatchEvent(new window.Event("input", { bubbles: true })); };
const tick = () => new Promise((r) => setTimeout(r, 0));
const root = () => q('.th-card[data-id="q1"]');
const follow = () => q('.th-follow[data-id="f1"]');

(async () => {
  await window.PrepThoughts.load(); await tick();

  ok("the newest thread opens by itself", !!root().querySelector(".th-body"));
  ok("the card head counts your notes", /1 note(?!s)/.test(root().querySelector(".q-head").textContent));
  ok("an existing note is shown under the question", root().querySelector(".th-note-text").textContent === "Asked in round 2");
  ok("every question has an Add a note button (question and follow-up)",
     qa('[data-th="note-add"]').length === 2 && !!follow().querySelector('[data-th="note-add"]'));

  // ── add a note to the follow-up ──────────────────────────────────────
  click(follow().querySelector('[data-th="note-add"]'));
  const box = follow().querySelector("[data-th-note]");
  ok("Add a note opens a box on that follow-up only", !!box && qa("[data-th-note]").length === 1);
  ok("...and puts the cursor in it", doc.activeElement === box);
  type(box, "Bookmark = last seen message id");

  // A poll re-renders the list while you type; the draft must survive.
  await window.PrepThoughts.load(); await tick();
  ok("a re-render keeps what you were typing",
     follow().querySelector("[data-th-note]").value === "Bookmark = last seen message id");

  click(follow().querySelector('[data-th="note-save"]')); await tick(); await tick();
  ok("saving posts to the follow-up's own notes", posted(/\/f1\/notes$/).length === 1 &&
     posted(/\/f1\/notes$/)[0].body.text === "Bookmark = last seen message id");
  ok("...the box closes and the note shows", !q("[data-th-note]") &&
     follow().querySelector(".th-note-text").textContent === "Bookmark = last seen message id");
  ok("...and the head now counts both notes", /2 notes/.test(root().querySelector(".q-head").textContent));

  // ── an empty note is not sent ────────────────────────────────────────
  click(root().querySelector('.th-body > .th-notes [data-th="note-add"]'));
  click(q('[data-th="note-save"]')); await tick();
  ok("an empty note is not posted", posted(/\/q1\/notes$/).length === 0);
  click(q('[data-th="note-cancel"]'));

  // ── edit ─────────────────────────────────────────────────────────────
  click(root().querySelector('[data-th="note-edit"]'));
  const ed = q("[data-th-note]");
  ok("Edit opens the note's text for editing", ed && ed.value === "Asked in round 2");
  type(ed, "Asked in rounds 2 and 4");
  ed.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true }));
  await tick(); await tick();
  ok("Ctrl+Enter saves the edit to that note", posted(/\/q1\/notes\/n1$/).length === 1);
  ok("...and shows the new text, marked edited",
     root().querySelector(".th-note-text").textContent === "Asked in rounds 2 and 4" &&
     /edited/.test(root().querySelector(".th-note-meta").textContent));

  // ── search finds notes ───────────────────────────────────────────────
  type(q("#th-search"), "bookmark = last");
  ok("search matches a note's text", !!root());
  type(q("#th-search"), "nothing-like-this");
  ok("...and still filters out non-matches", !root());
  type(q("#th-search"), "");

  // ── delete ───────────────────────────────────────────────────────────
  click(root().querySelector('[data-th="note-del"]')); await tick(); await tick();
  ok("Delete posts the note's delete", posted(/\/q1\/notes\/n1\/delete$/).length === 1);
  ok("...and the note leaves the page", !root().querySelector(".th-body > .th-notes .th-note"));

  // ── before the migration ─────────────────────────────────────────────
  notesAvailable = false;
  await window.PrepThoughts.load(); await tick();
  ok("without the notes column, no note controls are offered", qa('[data-th="note-add"]').length === 0);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

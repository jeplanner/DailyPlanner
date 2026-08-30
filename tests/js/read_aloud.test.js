/* Read aloud, driven against a stubbed speech engine.
 *
 * "implement read-aloud feature for the entire planner. Please put in
 * areas where there is textual content." (2026-08-30)
 *
 * Speech synthesis fails SILENTLY — that is what cost five days on the
 * time announcer — so the rules borrowed from it are asserted here
 * rather than trusted: never cancel-then-speak in the same task, resume
 * after speak, prefer a local voice, and chunk long text so the browser
 * cannot cut it off part-way.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const SRC = __dirname + "/../../static/js/read-aloud.js";
const src = fs.readFileSync(SRC, "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const PAGE = `<!doctype html><html lang="en"><body>
  <nav><a href="/x">Sidebar link nobody wants read</a></nav>
  <main>
    <h1>Today's plan</h1>
    <p>Reflect on the feedback before twelve.</p>
    <p hidden>This paragraph is hidden and must stay unread.</p>
    <script>var noise = "scripts are not content";</script>
    <button>Save</button>
  </main>
</body></html>`;

function boot() {
  const dom = new JSDOM(PAGE, { runScripts: "outside-only", pretendToBeVisual: true,
                                url: "https://example.test/summary" });
  const { window } = dom;
  const spoken = [];
  const calls = [];
  let utterances = [];

  window.SpeechSynthesisUtterance = function (text) {
    this.text = text;
    utterances.push(this);
  };
  window.speechSynthesis = {
    speaking: false, pending: false, paused: false,
    speak(u) { calls.push("speak"); spoken.push(u.text); this._last = u; },
    cancel() { calls.push("cancel"); },
    pause() { calls.push("pause"); this.paused = true; },
    resume() { calls.push("resume"); this.paused = false; },
    getVoices() {
      return [
        { name: "Cloud", lang: "en-US", localService: false, default: true },
        { name: "Local", lang: "en-US", localService: true, default: false },
      ];
    },
    addEventListener() {},
  };
  // jsdom reports offsetParent as undefined; the walker treats null as
  // hidden, so make visible elements look visible.
  Object.defineProperty(window.HTMLElement.prototype, "offsetParent", {
    get() { return this.hasAttribute("hidden") ? null : window.document.body; },
    configurable: true,
  });

  window.eval(src);
  return { window, doc: window.document, spoken, calls, utterances,
           finishOne: () => { const u = window.speechSynthesis._last; if (u && u.onend) u.onend(); } };
}

/* speak() is deliberately deferred by a tick — cancel-then-speak in the
   same task is the Chrome bug that swallowed the announcer's utterances —
   so every assertion after a read() has to let the timer run. */
const tick = () => new Promise((r) => setTimeout(r, 5));

(async () => {

// ── it speaks at all ────────────────────────────────────────────────
{
  const { window, spoken, calls } = boot();
  ok("the module exposes a reader", typeof window.dpReadAloud?.read === "function");
  ok("empty text is refused", window.dpReadAloud.read("   ") === false);

  window.dpReadAloud.read("Pay the electricity bill before Friday.");
  await tick();
  ok("it speaks", spoken.length === 1);
  ok("...what it was given", /electricity/.test(spoken[0]));
  ok("resume() follows speak(), or a paused queue swallows everything",
     calls.indexOf("resume") > calls.indexOf("speak"));
}

// ── the voice choice that broke the announcer in a pocket ───────────
{
  const { window, utterances } = boot();
  window.dpReadAloud.read("A local voice works with no network.");
  await tick();
  ok("a LOCAL voice is chosen over the cloud default",
     utterances[0].voice && utterances[0].voice.localService === true);
}

// ── long text is chunked, not sent as one doomed utterance ──────────
{
  const { window, spoken, finishOne } = boot();
  const long = "This is a sentence that goes on. ".repeat(40);
  window.dpReadAloud.read(long);
  await tick();
  ok("only the first piece is spoken to begin with", spoken.length === 1);
  ok("...and it is within a speakable length", spoken[0].length <= 220);
  finishOne();
  ok("finishing one piece starts the next", spoken.length === 2);
  ok("the player says where it is",
     /Reading 2 of \d+/.test(window.document.querySelector(".ra-progress").textContent));
}

// ── pause, resume, stop ─────────────────────────────────────────────
{
  const { window, doc, calls } = boot();
  window.dpReadAloud.read("Something long enough to pause. And more of it.");
  await tick();
  doc.querySelector('[data-ra="toggle"]').click();
  ok("pause pauses", calls.includes("pause"));
  ok("...and the button offers to resume",
     doc.querySelector('[data-ra="toggle"]').textContent === "▶");
  doc.querySelector('[data-ra="toggle"]').click();
  ok("resume resumes", calls.lastIndexOf("resume") > calls.indexOf("pause"));

  doc.querySelector('[data-ra="stop"]').click();
  ok("stop stops", window.dpReadAloud.isPlaying() === false);
  ok("...and the player goes away", doc.querySelector(".ra-bar").hidden === true);
}

// ── reading the page skips the furniture ────────────────────────────
{
  const { window, spoken, finishOne } = boot();
  window.dpReadAloud.readPage();
  await tick();
  // Drain the queue: the page is spoken in pieces, so what has been
  // "read" is everything that gets through, not just the first chunk.
  for (let i = 0; i < 20 && window.dpReadAloud.isPlaying(); i++) finishOne();
  const all = spoken.join(" ");
  ok("the page's own words are read", /Reflect on the feedback/.test(all));
  ok("the heading is read", /Today's plan/.test(all));
  ok("the sidebar is NOT read", !/Sidebar link/.test(all));
  ok("hidden text is NOT read", !/must stay unread/.test(all));
  ok("script contents are NOT read", !/scripts are not content/.test(all));
}

// ── an external cancel does not leave it wedged ─────────────────────
{
  const { window } = boot();
  window.dpReadAloud.read("The announcer is about to interrupt this.");
  await tick();
  const u = window.speechSynthesis._last;
  u.onerror({ error: "interrupted" });
  ok("an interruption stops it cleanly rather than hanging",
     window.dpReadAloud.isPlaying() === false);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
})();

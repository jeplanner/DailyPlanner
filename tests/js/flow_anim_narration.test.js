/* Animated diagrams: narration and word-by-word captions, in a real DOM.
 *
 * Runs the real static/js/flow_anim.js against a fake speechSynthesis whose
 * word-boundary and end events the test fires by hand, so "the caption
 * follows the voice" and "Play waits for the voice" are checked as behaviour.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");
const SRC = __dirname + "/../../static/js/flow_anim.js";

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

const spec = {
  title: "Ordering", w: 400, h: 120,
  nodes: [{ id: "a", label: "App", x: 10, y: 10, w: 100, h: 40 }, { id: "b", label: "Log", x: 200, y: 10, w: 180, h: 40, kind: "log" }],
  steps: [
    { say: "Order 101 is created. It goes to partition zero.", append: [{ node: "b", label: "101" }] },
    { say: "Order 102 follows it.", append: [{ node: "b", label: "102" }] },
    { say: "Both stay in order.", highlight: ["b"] },
  ],
};
const html = '<!doctype html><html lang="en"><body><div class="fa-anim" data-spec=\'' +
  JSON.stringify(spec).replace(/'/g, "&#39;") + '\'></div></body></html>';
const dom = new JSDOM(html, { runScripts: "outside-only", pretendToBeVisual: true, url: "https://example.test/x" });
const { window } = dom;
const doc = window.document;

// ── a fake voice ──────────────────────────────────────────────────────
const said = [];          // every utterance handed to speak()
let queue = [];           // spoken, not yet ended
const synth = {
  speaking: false, pending: false, cancels: 0, resumes: 0,
  getVoices: () => [{ lang: "en-US", localService: true, name: "Local" }],
  addEventListener() {},
  speak(u) { said.push(u); queue.push(u); this.speaking = true; },
  resume() { this.resumes++; },
  cancel() {
    this.cancels++;
    const q = queue; queue = []; this.speaking = false;
    q.forEach((u) => u.onerror && u.onerror({ error: "interrupted" }));   // what Chrome does
  },
};
function finishOne() {      // the current utterance ends
  const u = queue.shift(); if (!queue.length) synth.speaking = false;
  if (u && u.onend) u.onend({});
}
window.speechSynthesis = synth;
window.SpeechSynthesisUtterance = function (t) { this.text = t; };

window.eval(fs.readFileSync(SRC, "utf8"));
window.FlowAnim.init(doc);

const q = (s) => doc.querySelector(s);
const click = (el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const words = () => Array.prototype.slice.call(doc.querySelectorAll(".fa-cap .fa-w"));
const shown = () => words().filter((w) => w.classList.contains("on")).length;
const now = () => words().findIndex((w) => w.classList.contains("now"));
const count = () => q(".fa-count").textContent;

(async () => {
  const vb = q('[data-fa="voice"]');
  ok("there is a Voice button, on by default", vb && vb.getAttribute("aria-pressed") === "true" && /on/.test(vb.textContent));

  // ── Next: speaks, and the caption builds with the voice ───────────────
  click(q('[data-fa="next"]'));
  ok("the caption is laid out word by word", words().length === 9);
  ok("...but only the first word shows before the voice starts", shown() === 1);
  await wait(5);
  ok("the step is spoken a sentence at a time", said.length === 1 && said[0].text === "Order 101 is created.");
  ok("...at the chosen speed, with resume() after speak()", said[0].rate === 1 && synth.resumes >= 1);

  said[0].onboundary({ name: "word", charIndex: "Order 101 is ".length });   // now saying "created."
  ok("a word boundary reveals the words up to it", shown() === 4);
  ok("...and highlights the word being said", now() === 3);

  finishOne(); await wait(5);
  ok("the second sentence follows", said.length === 2 && said[1].text === "It goes to partition zero.");
  said[1].onboundary({ name: "word", charIndex: "It goes ".length });   // "to", offset into the whole step
  ok("its boundaries map into the whole caption", now() === 6 && shown() === 7);
  finishOne(); await wait(5);
  ok("when the voice ends, every word shows and nothing is highlighted", shown() === 9 && now() === -1);

  // ── Play waits for the narration ──────────────────────────────────────
  click(q('[data-fa="restart"]'));
  click(q('[data-fa="play"]'));
  await wait(20);
  ok("Play starts on step 1", count() === "1 / 3");
  await wait(1200);
  ok("...and stays there while the voice is still talking", count() === "1 / 3");
  ok("a voice that sends no word boundaries still moves the words along", shown() >= 3 && shown() < 9);
  finishOne(); await wait(5); finishOne();          // both sentences end
  await wait(900);                                  // the 700 ms breath
  ok("only after the voice ends does step 2 begin", count() === "2 / 3");
  ok("...and step 2 is spoken", said[said.length - 1].text === "Order 102 follows it.");

  // ── Pause mid-sentence ────────────────────────────────────────────────
  const c0 = synth.cancels;
  click(q('[data-fa="play"]'));                     // Pause
  ok("Pause silences the voice", synth.cancels > c0 && !synth.speaking);
  ok("...and shows the rest of the sentence", shown() === words().length && now() === -1);

  // ── Voice off: no speech, the words still build at reading pace ───────
  click(vb);
  ok("Voice can be turned off", vb.getAttribute("aria-pressed") === "false" && window.localStorage.getItem("faVoice") === "off");
  const n0 = said.length;
  click(q('[data-fa="next"]'));                     // step 3: "Both stay in order."
  await wait(20);
  ok("with Voice off nothing is spoken", said.length === n0);
  ok("...but the caption still starts word by word", shown() >= 1 && shown() < 4);
  await wait(1600);                                 // 4 words at ~300 ms
  ok("...and finishes on its own", shown() === 4 && now() === -1);

  // ── Back shows the whole caption at once, in silence ──────────────────
  click(vb);                                        // voice back on
  click(q('[data-fa="back"]'));
  ok("Back shows the previous caption whole", q(".fa-cap").textContent === "Order 102 follows it." && !synth.speaking);

  ok("the Voice choice is remembered for next time", window.localStorage.getItem("faVoice") === "on");

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

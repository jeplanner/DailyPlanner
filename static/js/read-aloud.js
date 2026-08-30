/* Read aloud — anywhere in the planner there is text.

   "implement read-aloud feature for the entire planner. Please put in
   areas where there is textual content." (2026-08-30)

   TWO WAYS IN, because "textual content" is most of the app and a Listen
   button on every card would be worse than no feature at all:

     1. SELECT ANY TEXT and a small Listen chip appears by the selection.
        Works on every page, every card, every paragraph, with nothing
        added to the markup.
     2. READ THIS PAGE, from the toolbar — walks the page's main content
        in document order and reads it.

   ── THE FOUR RULES BORROWED FROM time-announcer.js ──────────────────
   That file cost five days of wrong diagnoses (see its own comments and
   tests/js/time_announcer.test.js). Speech synthesis fails silently, so
   every one of these is here on purpose:

     1. NEVER cancel() and speak() in the same task. A long-standing
        Chrome bug swallows the utterance. Cancel, then speak on a later
        tick.
     2. PRIME THE VOICES. getVoices() is empty right after load —
        especially on Android — and speaking into that gap is dropped
        with no error.
     3. resume() AFTER speak(). Chrome leaves the queue paused after some
        lifecycle transitions, and a paused queue accepts utterances
        forever while saying nothing.
     4. PREFER A LOCAL VOICE. A network voice needs a live request at the
        moment of speaking, which a backgrounded page does not get. It
        works at the desk and stops in a pocket.

   ── AND ONE THAT IS ITS OWN ─────────────────────────────────────────
   LONG TEXT MUST BE CHUNKED. Browsers cut a single long utterance off
   part-way — Chrome around fifteen seconds — so a page is spoken as a
   queue of sentence-sized pieces. That is also what makes pause, resume
   and a progress count possible at all. */
(function () {
  "use strict";

  var synth = window.speechSynthesis;
  if (!synth || typeof window.SpeechSynthesisUtterance !== "function") return;

  var MAX_CHUNK = 220;          // characters; roughly one long sentence
  var state = {
    chunks: [], at: 0, playing: false, paused: false, bar: null,
  };

  /* ── voices ──────────────────────────────────────────────────────
     Primed once, and re-read on voiceschanged because the list arrives
     asynchronously on most platforms. */
  var voices = [];
  function loadVoices() {
    try { voices = synth.getVoices() || []; } catch (_) { voices = []; }
  }
  loadVoices();
  try { synth.addEventListener("voiceschanged", loadVoices); } catch (_) {}

  function pickVoice(lang) {
    var want = (lang || "en").slice(0, 2).toLowerCase();
    var local = voices.filter(function (v) { return v.localService; });
    return local.filter(function (v) {
      return (v.lang || "").slice(0, 2).toLowerCase() === want;
    })[0] || local.filter(function (v) { return v.default; })[0] || null;
  }

  /* ── splitting ───────────────────────────────────────────────────
     Sentence-ish, then hard-wrapped so one runaway paragraph without
     punctuation cannot become a single unspeakable utterance. */
  function chunk(text) {
    var clean = String(text || "").replace(/\s+/g, " ").trim();
    if (!clean) return [];
    var out = [];
    clean.split(/(?<=[.!?;:])\s+/).forEach(function (piece) {
      while (piece.length > MAX_CHUNK) {
        var cut = piece.lastIndexOf(" ", MAX_CHUNK);
        if (cut < 40) cut = MAX_CHUNK;
        out.push(piece.slice(0, cut).trim());
        piece = piece.slice(cut).trim();
      }
      if (piece) out.push(piece);
    });
    return out;
  }

  /* ── the player ──────────────────────────────────────────────────
     A strip rather than a dialog: reading is something you do WHILE
     looking at the page, so it must not cover it. */
  function bar() {
    if (state.bar) return state.bar;
    var el = document.createElement("div");
    el.className = "ra-bar";
    el.setAttribute("role", "status");
    el.innerHTML =
      '<button type="button" class="ra-btn" data-ra="toggle" aria-label="Pause">⏸</button>' +
      '<span class="ra-progress"></span>' +
      '<button type="button" class="ra-btn" data-ra="stop" aria-label="Stop reading">✕</button>';
    el.addEventListener("click", function (e) {
      var b = e.target.closest("[data-ra]");
      if (!b) return;
      if (b.getAttribute("data-ra") === "stop") stop();
      else togglePause();
    });
    document.body.appendChild(el);
    state.bar = el;
    return el;
  }

  function paintBar() {
    var el = bar();
    el.hidden = !state.playing;
    if (!state.playing) return;
    el.querySelector(".ra-progress").textContent =
      "Reading " + Math.min(state.at + 1, state.chunks.length) +
      " of " + state.chunks.length;
    var t = el.querySelector('[data-ra="toggle"]');
    t.textContent = state.paused ? "▶" : "⏸";
    t.setAttribute("aria-label", state.paused ? "Resume" : "Pause");
  }

  function next() {
    if (!state.playing) return;
    if (state.at >= state.chunks.length) { stop(); return; }
    var text = state.chunks[state.at];
    var u = new window.SpeechSynthesisUtterance(text);
    u.rate = 1;
    u.lang = document.documentElement.lang || navigator.language || "en-US";
    var v = pickVoice(u.lang);
    if (v) u.voice = v;
    u.onend = function () {
      if (!state.playing) return;
      state.at += 1;
      paintBar();
      next();
    };
    u.onerror = function () {
      // "interrupted" is what a cancel() from elsewhere looks like — the
      // time announcer firing mid-read, for instance. Stop cleanly
      // rather than fighting it for the queue.
      stop();
    };
    try {
      synth.speak(u);
      // Rule 3: a queue left paused accepts everything and says nothing.
      try { synth.resume(); } catch (_) {}
    } catch (_) {
      stop();
    }
    paintBar();
  }

  function read(text) {
    var chunks = chunk(text);
    if (!chunks.length) return false;
    var wasSpeaking = synth.speaking || synth.pending;
    try { synth.cancel(); } catch (_) {}
    state.chunks = chunks;
    state.at = 0;
    state.playing = true;
    state.paused = false;
    paintBar();
    // Rule 1: never cancel and speak in the same task.
    setTimeout(next, wasSpeaking ? 180 : 0);
    return true;
  }

  function stop() {
    state.playing = false;
    state.paused = false;
    state.chunks = [];
    state.at = 0;
    try { synth.cancel(); } catch (_) {}
    paintBar();
  }

  function togglePause() {
    if (!state.playing) return;
    try {
      if (state.paused) { synth.resume(); state.paused = false; }
      else { synth.pause(); state.paused = true; }
    } catch (_) {}
    paintBar();
  }

  /* ── 1. read the selection ───────────────────────────────────────
     The chip follows the selection instead of living in the markup, so
     every page gains this without a single template change. */
  var chip = null;
  function hideChip() { if (chip) chip.hidden = true; }

  function showChip(rect, text) {
    if (!chip) {
      chip = document.createElement("button");
      chip.type = "button";
      chip.className = "ra-chip";
      chip.textContent = "🔊 Listen";
      // mousedown, not click: by the time click fires the selection is
      // already gone on some browsers.
      chip.addEventListener("mousedown", function (e) {
        e.preventDefault();
        read(chip.dataset.text || "");
        hideChip();
      });
      document.body.appendChild(chip);
    }
    chip.dataset.text = text;
    chip.style.top = (window.scrollY + rect.top - 40) + "px";
    chip.style.left = (window.scrollX + rect.left) + "px";
    chip.hidden = false;
  }

  document.addEventListener("selectionchange", function () {
    var sel = document.getSelection();
    var text = sel ? String(sel).trim() : "";
    if (!text || text.length < 12) { hideChip(); return; }
    try {
      var rect = sel.getRangeAt(0).getBoundingClientRect();
      if (!rect || (!rect.width && !rect.height)) { hideChip(); return; }
      showChip(rect, text);
    } catch (_) { hideChip(); }
  });

  /* ── 2. read the page ────────────────────────────────────────────
     Walks visible text in document order and skips the furniture:
     navigation, controls, scripts, and anything hidden. Reading the
     sidebar's forty links before the content would make the feature
     useless on every page at once. */
  var SKIP = "nav, script, style, noscript, select, textarea, input, " +
             ".sidebar, .top-nav, .top-context, .ra-bar, .ra-chip, " +
             "[aria-hidden='true'], [hidden]";

  function pageText(root) {
    var scope = root || document.querySelector("main, .container, .content") ||
                document.body;
    var out = [];
    var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var el = node.parentElement;
        if (!el || el.closest(SKIP)) return NodeFilter.FILTER_REJECT;
        // offsetParent is null for display:none — cheap visibility test
        // that does not force a full style resolve per node.
        if (el.offsetParent === null && el.tagName !== "BODY") {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    var n;
    while ((n = walker.nextNode())) out.push(n.nodeValue.trim());
    return out.join(". ");
  }

  function readPage() {
    var text = pageText();
    if (!read(text) && window.showToast) {
      window.showToast("Nothing to read on this page", "info");
    }
  }

  /* Exposed so a page can offer its own control over its own region —
     e.g. one story, one prep answer — rather than the whole document. */
  window.dpReadAloud = {
    read: read,
    readElement: function (el) { return read(pageText(el)); },
    readPage: readPage,
    stop: stop,
    isPlaying: function () { return state.playing; },
  };

  /* Keyboard: the same shape the rest of the app uses — ignored while
     typing so it never eats a keystroke. */
  document.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
              t.isContentEditable)) return;
    if (e.key === "Escape" && state.playing) { stop(); return; }
    // Shift+R: read the page. Shift, because a bare letter is already
    // spoken for on several pages.
    if (e.shiftKey && (e.key === "R" || e.key === "r")) {
      e.preventDefault();
      state.playing ? stop() : readPage();
    }
  });

  // Speech does not survive a navigation, and a voice left talking over
  // the next page is alarming.
  window.addEventListener("pagehide", stop);
})();

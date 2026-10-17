/* flow_anim.js — step-by-step animated diagrams for Random thoughts.
 *
 * An answer embeds a spec as a fenced block:
 *
 *   ```anim
 *   {"title": "...", "w": 640, "h": 340,
 *    "nodes": [{"id": "app", "label": "Checkout", "x": 20, "y": 40, "w": 130, "h": 46, "kind": "service"},
 *              {"id": "p0", "label": "Partition 0", "x": 240, "y": 30, "w": 360, "h": 44, "kind": "log"}],
 *    "steps": [{"say": "Order 101 is created.",
 *               "send": [{"from": "app", "to": "p0", "label": "101 created", "color": "a"}],
 *               "append": [{"node": "p0", "label": "101 created", "color": "a"}],
 *               "highlight": ["p0"], "mark": [{"node": "p0", "index": 0}]}]}
 *   ```
 *
 * kinds: user, service, broker, db, queue, cache, log (cells appended left to
 * right), note. Colours a-f are theme-aware. Steps run with Play / Next / Back;
 * Back rebuilds the picture up to the previous step, so it is always exact.
 * With prefers-reduced-motion, messages jump instead of travelling.
 *
 * NARRATION. With Voice on (the default where the browser can speak), each
 * step's "say" is read aloud and its caption appears word by word as it is
 * spoken, the current word highlighted. Play waits for the narration to end
 * before the next step, so a long sentence is never cut off; Speed sets the
 * speaking rate too. With Voice off the caption still builds up, at reading
 * pace. Words follow the speech's own word-boundary events where the voice
 * sends them, and an estimate where it does not (many Android voices).
 */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var COLORS = ["a", "b", "c", "d", "e", "f"];
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SPEEDS = [0.5, 0.75, 1, 1.5, 2];
  function savedSpeed() {
    try { var v = parseFloat(localStorage.getItem("faSpeed")); if (SPEEDS.indexOf(v) >= 0) return v; } catch (e) {}
    return 1;
  }

  function savedVoice() {
    try { return localStorage.getItem("faVoice") !== "off"; } catch (e) { return true; }
  }

  /* ── Narrator: one voice for every player on the page ─────────────────
     The rules static/js/read-aloud.js and time-announcer.js learned the
     hard way, because speech synthesis fails silently:
       1. never cancel() and speak() in the same task (Chrome drops it);
       2. prime the voices (getVoices() is empty right after load);
       3. resume() after speak() (a paused queue swallows utterances);
       4. prefer a local voice (a network one dies in a background tab).
     A step is spoken a sentence at a time: browsers cut one long
     utterance off at ~15 s, which a 180-character line at 0.5x passes. */
  var Narrator = (function () {
    var synth = window.speechSynthesis;
    var ok = !!(synth && typeof window.SpeechSynthesisUtterance === "function");
    var voices = [], job = null;
    function loadVoices() { try { voices = synth.getVoices() || []; } catch (e) { voices = []; } }
    if (ok) { loadVoices(); try { synth.addEventListener("voiceschanged", loadVoices); } catch (e) {} }
    function pickVoice(lang) {
      var want = (lang || "en").slice(0, 2).toLowerCase();
      var local = voices.filter(function (v) { return v.localService; });
      return local.filter(function (v) { return (v.lang || "").slice(0, 2).toLowerCase() === want; })[0] ||
        voices.filter(function (v) { return (v.lang || "").slice(0, 2).toLowerCase() === want; })[0] || null;
    }
    function sentences(text) {
      var out = [], re = /[^.!?]+[.!?]*\s*/g, m;
      while ((m = re.exec(text))) if (m[0].trim()) out.push({ text: m[0].trim(), off: m.index });
      return out.length ? out : [{ text: text, off: 0 }];
    }
    function stop() {
      if (job) job.dead = true;
      job = null;
      if (!ok) return;
      try { if (synth.speaking || synth.pending) synth.cancel(); } catch (e) {}
    }
    // speak(text, rate, onWord(charIndex), onEnd()) -> false when it can't.
    function speak(text, rate, onWord, onEnd) {
      if (!ok) return false;
      var busy = false;
      try { busy = synth.speaking || synth.pending; } catch (e) {}
      stop();
      var me = job = { dead: false }, parts = sentences(text), lang = document.documentElement.lang || navigator.language || "en-US";
      function say(k) {
        if (me.dead) return;
        if (k >= parts.length) { job = null; onEnd(); return; }
        var u = new window.SpeechSynthesisUtterance(parts[k].text);
        u.rate = Math.max(0.5, Math.min(2, rate || 1)); u.lang = lang;
        var v = pickVoice(lang); if (v) u.voice = v;
        u.onboundary = function (e) { if (!me.dead && (!e.name || e.name === "word")) onWord(parts[k].off + (e.charIndex || 0)); };
        u.onend = function () { say(k + 1); };
        // An error must not stall Play; a cancel() of ours is already dead.
        u.onerror = function () { if (!me.dead) { job = null; onEnd(); } };
        try { synth.speak(u); synth.resume(); } catch (e) { if (!me.dead) { job = null; onEnd(); } }
      }
      setTimeout(function () { say(0); }, busy ? 150 : 0);   // rule 1
      return true;
    }
    return { ok: ok, speak: speak, stop: stop };
  })();
  var activePlayer = null;    // the player that owns the voice right now
  window.addEventListener("pagehide", function () { if (activePlayer) activePlayer.stop(); });

  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function txt(parent, x, y, s, cls, anchor) {
    var t = el("text", { x: x, y: y, "class": cls || "fa-t", "text-anchor": anchor || "middle" }, parent);
    t.textContent = s;
    return t;
  }
  function center(n) { return { x: n.x + n.w / 2, y: n.y + n.h / 2 }; }
  function col(c) { return "fa-c-" + (COLORS.indexOf(c) >= 0 ? c : "a"); }
  function clip(s, max) { s = String(s || ""); return s.length > max ? s.slice(0, max - 1) + "…" : s; }

  function Player(host, spec) {
    this.host = host; this.spec = spec; this.i = 0; this.playing = false; this.busy = false;
    this.speed = savedSpeed();
    this.voice = Narrator.ok && savedVoice();
    this.tok = 0;             // bumps on every caption, so a stale callback is ignored
    this.byId = {};
    for (var k = 0; k < spec.nodes.length; k++) this.byId[spec.nodes[k].id] = spec.nodes[k];
    this.build();
    this.reset();
  }

  Player.prototype.build = function () {
    var s = this.spec, self = this;
    this.host.innerHTML = "";
    this.host.classList.add("fa-ready");
    if (s.title) { var h = document.createElement("div"); h.className = "fa-title"; h.textContent = s.title; this.host.appendChild(h); }
    var wrap = document.createElement("div"); wrap.className = "fa-stage"; this.host.appendChild(wrap);
    this.svg = el("svg", { viewBox: "0 0 " + (s.w || 640) + " " + (s.h || 340), role: "img", "aria-label": s.title || "Animated diagram" });
    this.svg.style.minWidth = Math.min(s.w || 640, 460) + "px";
    wrap.appendChild(this.svg);
    var tip = document.createElement("div"); tip.className = "fa-turn"; tip.textContent = "Tip: turn your phone sideways for a bigger diagram."; this.host.appendChild(tip);
    var hint = document.createElement("div"); hint.className = "fa-swipe"; hint.hidden = true;
    hint.textContent = "Swipe the diagram sideways to see all of it."; this.host.appendChild(hint);
    function fit() { hint.hidden = !(wrap.scrollWidth > wrap.clientWidth + 4); }
    requestAnimationFrame(fit); window.addEventListener("resize", fit);
    this.gEdges = el("g", {}, this.svg); this.gNodes = el("g", {}, this.svg); this.gFly = el("g", {}, this.svg);
    (s.edges || []).forEach(function (e) {
      var a = self.byId[e.from], b = self.byId[e.to]; if (!a || !b) return;
      var p = center(a), q = center(b);
      el("line", { x1: p.x, y1: p.y, x2: q.x, y2: q.y, "class": "fa-edge" }, self.gEdges);
    });
    this.nodeEls = {};
    s.nodes.forEach(function (n) {
      var g = el("g", { "class": "fa-node fa-k-" + (n.kind || "service") }, self.gNodes);
      el("rect", { x: n.x, y: n.y, width: n.w, height: n.h, rx: n.kind === "user" ? n.h / 2 : 8, "class": "fa-box" }, g);
      if (n.kind === "log") {
        txt(g, n.x + 8, n.y - 6, n.label, "fa-lbl", "start");
        g.cells = el("g", {}, g);
      } else {
        txt(g, n.x + n.w / 2, n.y + n.h / 2 + (n.sub ? -2 : 5), clip(n.label, Math.floor(n.w / 7.2)), "fa-t");
        if (n.sub) txt(g, n.x + n.w / 2, n.y + n.h / 2 + 13, clip(n.sub, Math.floor(n.w / 6.4)), "fa-s");
      }
      self.nodeEls[n.id] = g;
    });
    var cap = document.createElement("div"); cap.className = "fa-cap"; cap.setAttribute("aria-live", "polite"); this.host.appendChild(cap); this.cap = cap;
    var bar = document.createElement("div"); bar.className = "fa-bar";
    bar.innerHTML = '<button type="button" class="fa-btn" data-fa="back" aria-label="Previous step">◀ Back</button>' +
      '<button type="button" class="fa-btn fa-main" data-fa="play">▶ Play</button>' +
      '<button type="button" class="fa-btn" data-fa="next" aria-label="Next step">Next ▶</button>' +
      '<button type="button" class="fa-btn" data-fa="restart">↺ Restart</button>' +
      '<label class="fa-speed">Speed <select aria-label="Play speed">' +
      SPEEDS.map(function (v) { return '<option value="' + v + '">' + v + '×</option>'; }).join("") + '</select></label>' +
      (Narrator.ok ? '<button type="button" class="fa-btn" data-fa="voice"></button>' : "") +
      '<button type="button" class="fa-btn" data-fa="full" aria-label="Full screen">⛶ Full screen</button>' +
      '<span class="fa-count"></span>';
    this.host.appendChild(bar);
    this.count = bar.querySelector(".fa-count"); this.playBtn = bar.querySelector('[data-fa="play"]');
    this.fullBtn = bar.querySelector('[data-fa="full"]');
    this.voiceBtn = bar.querySelector('[data-fa="voice"]');
    this.paintVoice();
    var sel = bar.querySelector(".fa-speed select"); sel.value = String(this.speed);
    sel.addEventListener("change", function () {
      self.speed = parseFloat(sel.value) || 1;
      try { localStorage.setItem("faSpeed", String(self.speed)); } catch (e) {}
    });
    this.host.addEventListener("keydown", function (e) {
      if (e.target.tagName === "SELECT") return;
      if (e.key === "Escape" && self.host.classList.contains("fa-full")) { self.full(false); }
      else if (e.key === "ArrowRight") { self.stop(); self.next(); e.preventDefault(); }
      else if (e.key === "ArrowLeft") { self.stop(); self.goto(self.i - 1); e.preventDefault(); }
      else if (e.key === " " && e.target === self.host) { self.toggle(); e.preventDefault(); }
    });
    if (!this.host.hasAttribute("tabindex")) this.host.setAttribute("tabindex", "-1");
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("[data-fa]"); if (!b) return;
      var a = b.dataset.fa;
      if (a === "play") self.toggle();
      else if (a === "next") { self.stop(); self.next(); }
      else if (a === "back") { self.stop(); self.goto(self.i - 1); }
      else if (a === "restart") { self.stop(); self.reset(); }
      else if (a === "full") { self.full(!self.host.classList.contains("fa-full")); }
      else if (a === "voice") { self.setVoice(!self.voice); }
    });
  };

  Player.prototype.paintVoice = function () {
    if (!this.voiceBtn) return;
    this.voiceBtn.textContent = this.voice ? "🔊 Voice on" : "🔇 Voice off";
    this.voiceBtn.setAttribute("aria-pressed", this.voice ? "true" : "false");
    this.voiceBtn.setAttribute("aria-label", this.voice ? "Turn narration off" : "Turn narration on");
  };
  Player.prototype.setVoice = function (on) {
    this.voice = !!on && Narrator.ok;
    try { localStorage.setItem("faVoice", this.voice ? "on" : "off"); } catch (e) {}
    this.paintVoice();
    // Turning it off mid-sentence: go quiet and let the words finish at
    // reading pace. Turning it on takes effect from the next step.
    if (!this.voice && this.speaking) {
      this.speaking = false;
      Narrator.stop();
      if (this.saying) this.paceWords(this.saying.from, false);
    }
  };

  Player.prototype.clearState = function () {
    var self = this;
    this.logs = {};
    this.spec.nodes.forEach(function (n) {
      var g = self.nodeEls[n.id]; g.classList.remove("fa-hi");
      if (g.cells) g.cells.innerHTML = "";
      self.logs[n.id] = [];
    });
    this.gFly.innerHTML = "";
  };
  Player.prototype.reset = function () { this.clearState(); this.i = 0; this.caption(this.spec.intro || "Press Play, or step through with Next."); };
  // The whole caption at once (Back, Restart, Pause, the intro).
  Player.prototype.caption = function (s) {
    this.hush();
    this.cap.textContent = s || "";
    this.count.textContent = this.i + " / " + this.spec.steps.length;
  };
  // Stop talking and drop any half-built caption's timers.
  Player.prototype.hush = function () {
    this.tok++;
    clearTimeout(this.wordTimer); clearTimeout(this.watchdog);
    if (this.speaking) { this.speaking = false; Narrator.stop(); }
    if (activePlayer === this) activePlayer = null;
    this.saying = null;
  };

  /* A step's caption, built up word by word while it is spoken (or, with
     Voice off, at reading pace). done() runs once, when the words are all
     out and the voice has finished, so Play can move on. */
  Player.prototype.narrate = function (s, done) {
    var self = this;
    this.hush();
    var tok = this.tok;
    s = String(s || "");
    this.count.textContent = this.i + " / " + this.spec.steps.length;
    var words = [], re = /\S+/g, m;
    while ((m = re.exec(s))) words.push({ w: m[0], at: m.index });
    this.cap.innerHTML = "";
    words.forEach(function (x, k) {
      var sp = document.createElement("span"); sp.className = "fa-w"; sp.textContent = x.w;
      self.cap.appendChild(sp);
      if (k < words.length - 1) self.cap.appendChild(document.createTextNode(" "));
    });
    this.wordEls = this.cap.querySelectorAll(".fa-w");
    var finished = false;
    var saying = this.saying = { words: words, from: 0, voiceDone: false, wordsDone: false,
      done: function () {
        if (finished || tok !== self.tok) return;
        if (!(saying.wordsDone && saying.voiceDone)) return;
        finished = true; clearTimeout(self.watchdog);
        if (activePlayer === self) activePlayer = null;
        self.showWord(-1);
        if (done) done();
      } };
    // Nothing to build up: finish on the next tick, never synchronously
    // (next() is still setting up when this returns).
    if (!words.length || reduce && !this.voice) { this.showWord(-1); saying.wordsDone = saying.voiceDone = true; setTimeout(saying.done, 0); return; }
    var spoken = false;
    if (this.voice) {
      if (activePlayer && activePlayer !== this) activePlayer.stop();
      activePlayer = this;
      var heard = false;   // true once the voice sends word boundaries
      spoken = Narrator.speak(s, this.speed, function (ci) {
        if (tok !== self.tok) return;
        if (!heard) { heard = true; clearTimeout(self.wordTimer); }
        var k = 0; while (k + 1 < words.length && words[k + 1].at <= ci) k++;
        saying.from = k; self.showWord(k);
      }, function () {
        if (tok !== self.tok) return;
        self.speaking = false;
        saying.wordsDone = saying.voiceDone = true;   // the last word has been said
        saying.done();
      });
      this.speaking = spoken;
      if (spoken) {
        // If the voice never reports an end (it happens), don't hang Play.
        var est = this.msPerWord(true) * words.length;
        this.watchdog = setTimeout(function () {
          if (tok !== self.tok) return;
          self.speaking = false; Narrator.stop();
          saying.wordsDone = saying.voiceDone = true; saying.done();
        }, est * 2 + 4000);
      }
    }
    if (!spoken) saying.voiceDone = true;
    this.paceWords(0, spoken);
  };
  // Words per minute: a speaking voice runs ~165 at rate 1, a reader ~200.
  Player.prototype.msPerWord = function (voiced) { return 60000 / ((voiced ? 165 : 200) * (this.speed || 1)); };
  // Reveal words on a timer from `from`. With the voice on this is only the
  // fallback for voices that send no word boundaries, so it never ends the
  // step itself (the voice's end does); with it off it does.
  Player.prototype.paceWords = function (from, voiced) {
    var self = this, tok = this.tok, saying = this.saying;
    if (!saying) return;
    clearTimeout(this.wordTimer);
    var k = from, n = saying.words.length, step = this.msPerWord(voiced);
    (function tick() {
      if (tok !== self.tok) return;
      self.showWord(k); saying.from = k;
      if (k >= n - 1) {
        if (voiced) return;
        self.wordTimer = setTimeout(function () {
          if (tok !== self.tok) return;
          saying.wordsDone = saying.voiceDone = true; saying.done();
        }, step);
        return;
      }
      k++; self.wordTimer = setTimeout(tick, step);
    })();
  };
  // Words up to k shown, k highlighted; -1 = the whole caption, no highlight.
  Player.prototype.showWord = function (k) {
    var els = this.wordEls || [];
    for (var j = 0; j < els.length; j++) {
      els[j].classList.toggle("on", k < 0 || j <= k);
      els[j].classList.toggle("now", j === k);
    }
  };

  Player.prototype.drawCell = function (nodeId, idx, label, color) {
    var n = this.byId[nodeId], g = this.nodeEls[nodeId]; if (!n || !g || !g.cells) return;
    var cw = n.cw || 72, gap = 4, x = n.x + 6 + idx * (cw + gap);
    if (x + cw > n.x + n.w - 4) return;          // log is full: keep the picture clean
    var c = el("g", { "class": "fa-cell " + col(color), "data-i": idx }, g.cells);
    el("rect", { x: x, y: n.y + 6, width: cw, height: n.h - 12, rx: 5 }, c);
    txt(c, x + cw / 2, n.y + n.h / 2 + 4, clip(label, Math.floor(cw / 6)), "fa-ct");
    txt(c, x + cw / 2, n.y + n.h + 12, String(idx), "fa-off");
  };

  // Apply a step's lasting effects (no animation): appends, highlights, marks.
  Player.prototype.apply = function (st) {
    var self = this;
    this.spec.nodes.forEach(function (n) { self.nodeEls[n.id].classList.remove("fa-hi"); });
    (st.highlight || []).forEach(function (id) { if (self.nodeEls[id]) self.nodeEls[id].classList.add("fa-hi"); });
    (st.append || []).forEach(function (a) {
      var arr = self.logs[a.node]; if (!arr) return;
      arr.push(a); self.drawCell(a.node, arr.length - 1, a.label, a.color);
    });
    (st.remove || []).forEach(function (r) {
      var g = self.nodeEls[r.node]; if (!g || !g.cells) return;
      var c = g.cells.querySelector('[data-i="' + r.index + '"]'); if (c) c.classList.add("fa-gone");
    });
    this.nodeEls && Object.keys(this.nodeEls).forEach(function (id) {
      var g = self.nodeEls[id]; if (g.cells) g.cells.querySelectorAll(".fa-mark").forEach(function (m) { m.classList.remove("fa-mark"); });
    });
    (st.mark || []).forEach(function (m) {
      var g = self.nodeEls[m.node]; if (!g || !g.cells) return;
      var c = g.cells.querySelector('[data-i="' + m.index + '"]'); if (c) c.classList.add("fa-mark");
    });
  };

  // Animate the travelling messages of a step, then apply its effects.
  Player.prototype.run = function (st, done) {
    var self = this, sends = st.send || [];
    if (!sends.length || reduce) { this.apply(st); done(); return; }
    var left = sends.length, dur = 900 / (this.speed || 1);
    sends.forEach(function (m, k) {
      var a = self.byId[m.from], b = self.byId[m.to];
      if (!a || !b) { if (--left === 0) { self.apply(st); done(); } return; }
      var p = center(a), q = center(b);
      if (b.kind === "log") { var arr = self.logs[b.id] || []; q = { x: b.x + 6 + arr.length * ((b.cw || 72) + 4) + (b.cw || 72) / 2, y: q.y }; }
      var g = el("g", { "class": "fa-msg " + col(m.color) }, self.gFly);
      var lw = Math.max(46, Math.min(150, String(m.label || "").length * 6.4 + 16));
      el("rect", { x: -lw / 2, y: -11, width: lw, height: 22, rx: 11 }, g);
      txt(g, 0, 4, clip(m.label, 24), "fa-mt");
      var t0 = null, delay = k * 220 / (self.speed || 1);
      function frame(ts) {
        if (t0 === null) t0 = ts;
        var t = Math.min(1, Math.max(0, (ts - t0 - delay) / dur));
        var e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        g.setAttribute("transform", "translate(" + (p.x + (q.x - p.x) * e) + "," + (p.y + (q.y - p.y) * e) + ")");
        if (t < 1) requestAnimationFrame(frame);
        else { g.remove(); if (--left === 0) { self.apply(st); done(); } }
      }
      requestAnimationFrame(frame);
    });
  };

  Player.prototype.next = function (after) {
    var self = this;
    if (this.busy || this.i >= this.spec.steps.length) { if (after) after(false); return; }
    this.busy = true;
    var st = this.spec.steps[this.i];
    this.i++;
    // The picture and the words run together; Play moves on when both are done.
    var left = 2, tok;
    function both() { if (--left === 0 && after && tok === self.tok) after(true); }
    this.narrate(st.say, both);
    tok = this.tok;
    this.run(st, function () { self.busy = false; both(); });
  };
  Player.prototype.goto = function (k) {
    k = Math.max(0, Math.min(k, this.spec.steps.length));
    this.clearState();
    for (var j = 0; j < k; j++) this.apply(this.spec.steps[j]);
    this.i = k;
    this.caption(k ? this.spec.steps[k - 1].say : (this.spec.intro || "Press Play, or step through with Next."));
  };
  Player.prototype.toggle = function () { if (this.playing) this.stop(); else this.play(); };
  Player.prototype.play = function () {
    var self = this;
    if (this.i >= this.spec.steps.length) this.reset();
    this.playing = true; this.playBtn.textContent = "❚❚ Pause";
    (function loop() {
      if (!self.playing) return;
      // The page re-drew the answer (a poll): this player is gone.
      if (!self.host.isConnected) { self.stop(); return; }
      self.next(function (moved) {
        if (!moved || !self.playing) { self.stop(); return; }
        // A short breath between steps; the narration already set the pace.
        self.timer = setTimeout(loop, 700 / (self.speed || 1));
      });
    })();
  };
  Player.prototype.stop = function () {
    var wasPlaying = this.playing;
    this.playing = false; clearTimeout(this.timer);
    // Pausing mid-sentence: go quiet and show the rest of the words.
    if (this.saying || this.speaking) { this.hush(); this.showWord(-1); }
    if (this.playBtn) this.playBtn.textContent = this.i >= this.spec.steps.length ? "▶ Replay" : "▶ Play";
    return wasPlaying;
  };

  // Full screen: the real Fullscreen API where the browser allows it on an
  // element (desktop, Android); otherwise (iPhone Safari) the player fills the
  // window with fixed positioning. Either way the diagram is scaled to fit.
  Player.prototype.full = function (on) {
    var h = this.host, self = this;
    var req = h.requestFullscreen || h.webkitRequestFullscreen;
    var fsEl = function () { return document.fullscreenElement || document.webkitFullscreenElement; };
    if (on) {
      h.classList.add("fa-full"); document.documentElement.classList.add("fa-noscroll");
      this.fullBtn.textContent = "✕ Exit full screen"; this.fullBtn.setAttribute("aria-label", "Exit full screen");
      var lockLand = function () {
        // Android Chrome can turn the screen sideways once in full screen.
        try { if (screen.orientation && screen.orientation.lock && window.innerWidth < 700) screen.orientation.lock("landscape").catch(function () {}); } catch (e) {}
      };
      if (req) { try { var r = req.call(h); if (r && r.then) r.then(lockLand, function () {}); else lockLand(); } catch (e) {} }
      if (!this._fsWatch) {
        this._fsWatch = function () { if (!fsEl() && self.host.classList.contains("fa-full") && self._wasNative) self.full(false); self._wasNative = !!fsEl(); };
        document.addEventListener("fullscreenchange", this._fsWatch); document.addEventListener("webkitfullscreenchange", this._fsWatch);
      }
      h.focus({ preventScroll: true });
    } else {
      h.classList.remove("fa-full"); document.documentElement.classList.remove("fa-noscroll");
      this.fullBtn.textContent = "⛶ Full screen"; this.fullBtn.setAttribute("aria-label", "Full screen");
      try { if (screen.orientation && screen.orientation.unlock) screen.orientation.unlock(); } catch (e) {}
      if (fsEl() === h) { var x = document.exitFullscreen || document.webkitExitFullscreen; if (x) { try { var p = x.call(document); if (p && p.catch) p.catch(function () {}); } catch (e) {} } }
      this._wasNative = false;
    }
    window.dispatchEvent(new Event("resize"));
  };

  function init(root) {
    (root || document).querySelectorAll(".fa-anim:not(.fa-ready)").forEach(function (host) {
      var raw = host.getAttribute("data-spec") || (host.querySelector("script[type='application/json']") || {}).textContent;
      try {
        var spec = JSON.parse(raw);
        if (!spec.nodes || !spec.steps) throw new Error("bad spec");
        host._fa = new Player(host, spec);
      } catch (e) {
        host.classList.add("fa-ready", "fa-bad");
        host.textContent = "This animation could not be drawn.";
      }
    });
  }
  window.FlowAnim = { init: init };
})();

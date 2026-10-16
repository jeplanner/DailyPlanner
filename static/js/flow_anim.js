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
      '<button type="button" class="fa-btn" data-fa="full" aria-label="Full screen">⛶ Full screen</button>' +
      '<span class="fa-count"></span>';
    this.host.appendChild(bar);
    this.count = bar.querySelector(".fa-count"); this.playBtn = bar.querySelector('[data-fa="play"]');
    this.fullBtn = bar.querySelector('[data-fa="full"]');
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
    });
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
  Player.prototype.caption = function (s) {
    this.cap.textContent = s || "";
    this.count.textContent = this.i + " / " + this.spec.steps.length;
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
    this.caption(st.say);
    this.run(st, function () { self.busy = false; if (after) after(true); });
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
      self.next(function (moved) {
        if (!moved || !self.playing) { self.stop(); return; }
        self.timer = setTimeout(loop, 1700 / (self.speed || 1));
      });
    })();
  };
  Player.prototype.stop = function () { this.playing = false; clearTimeout(this.timer); if (this.playBtn) this.playBtn.textContent = this.i >= this.spec.steps.length ? "▶ Replay" : "▶ Play"; };

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

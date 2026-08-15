/* ════════════════════════════════════════════════════════════════
   DAILYPLANNER — PER-QUESTION POMODORO TIMER & ACTUAL-EFFORT LOG

   Attaches a Pomodoro timer to every question card on the prep pages
   (AI SDE, Interview Prep, TPM rounds) and records how long you
   ACTUALLY spent on each one, so the estimate (prep_minutes) can be
   compared against reality.

   Usage from a page, after its cards are in the DOM:

       Pomodoro.init({ ns: "ai_sde", container: document.getElementById("list") });

   Contract with the page:
     - cards are `.q-card[data-id]`, with a `.q-head` and a `.q-body`
     - optional `data-est="25"` on the card = the estimate, in minutes
     - the page may re-render the container wholesale; a MutationObserver
       re-decorates and restores a running timer.
     - `document` receives a `pomodoro:change` event whenever logged
       effort changes, so the page can refresh its own summary line.

   Storage (localStorage, per namespace):
     dp-pom-<ns>        {"<card id>": seconds_logged}
     dp-pom-paused-<ns> {"<card id>": ms_left_on_a_paused_session}
     dp-pom-active      {ns, id, startedAt, mode, endsAt}   (one globally)
     dp-pom-len         focus length in minutes (default 25)

   Only ONE timer runs at a time across the whole app: starting a second
   one banks the first one's elapsed seconds and stops it. Elapsed time
   is derived from wall-clock timestamps, not from tick counting, so a
   backgrounded tab, a locked phone or a page reload all keep counting
   correctly.
   ════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  if (window.Pomodoro) return;

  var ACTIVE_KEY = "dp-pom-active";
  var LEN_KEY = "dp-pom-len";
  var BREAK_MIN = 5;
  var DEFAULT_FOCUS = 25;

  /* ── storage helpers ─────────────────────────────────────────── */
  function readJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; }
    catch (_) { return fallback; }
  }
  function writeJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
  }
  function effortKey(ns) { return "dp-pom-" + ns; }
  function loadEffort(ns) { return readJSON(effortKey(ns), {}); }
  function saveEffort(ns, obj) { writeJSON(effortKey(ns), obj); }

  /* Milliseconds left on a session that was PAUSED, per card. The button
     says Pause, so resuming must pick the session up where it stopped
     rather than handing out a fresh full-length one. */
  function pausedKey(ns) { return "dp-pom-paused-" + ns; }

  function focusMinutes() {
    var n = parseInt(localStorage.getItem(LEN_KEY) || "", 10);
    return (n >= 1 && n <= 180) ? n : DEFAULT_FOCUS;
  }
  function setFocusMinutes(n) {
    try { localStorage.setItem(LEN_KEY, String(n)); } catch (_) {}
  }

  /* Active-timer record, shared across pages so navigating away and
     back does not silently drop a running session. */
  function getActive() { return readJSON(ACTIVE_KEY, null); }
  function setActive(a) {
    if (a) writeJSON(ACTIVE_KEY, a);
    else { try { localStorage.removeItem(ACTIVE_KEY); } catch (_) {} }
  }

  /* Card ids come from the banks (slugs like "dsa-two-pointers"), but
     escape them anyway before building a selector. */
  function cssId(id) {
    var s = String(id);
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return s.replace(/["\\\]]/g, "\\$&");
  }

  /* ── formatting ──────────────────────────────────────────────── */
  function mmss(sec) {
    sec = Math.max(0, Math.round(sec));
    var m = Math.floor(sec / 60), s = sec % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function humanMin(sec) {
    var m = Math.round(sec / 60);
    if (m < 60) return m + "m";
    var h = Math.floor(m / 60), r = m % 60;
    return r ? h + "h " + r + "m" : h + "h";
  }

  /* ── one-off chime so a finished pomodoro is noticeable even if
     the tab is not focused. Silently no-ops where WebAudio is
     unavailable or blocked before a user gesture. ─────────────── */
  function chime() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      [880, 1175].forEach(function (freq, i) {
        var osc = ctx.createOscillator(), gain = ctx.createGain();
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.0001, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.22, ctx.currentTime + 0.02 + i * 0.28);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.26 + i * 0.28);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.28);
        osc.stop(ctx.currentTime + 0.3 + i * 0.28);
      });
      setTimeout(function () { try { ctx.close(); } catch (_) {} }, 1500);
    } catch (_) {}
  }

  function say(msg, kind) {
    if (window.toast) { try { window.toast(msg, kind || "success"); return; } catch (_) {} }
  }

  /* ── styles, injected once so every page picks them up ────────── */
  function injectStyles() {
    if (document.getElementById("pom-styles")) return;
    var css = [
      ".pom { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:0 0 10px 0;",
      "  padding:8px 10px; border-radius:10px; background:#f5f3ff; border:1px solid #ddd6fe; }",
      ".pom .clock { font-variant-numeric:tabular-nums; font-weight:800; font-size:16px; color:#5b21b6;",
      "  min-width:56px; text-align:center; letter-spacing:.02em; }",
      ".pom.running .clock { color:#4338ca; }",
      ".pom.break .clock { color:#047857; }",
      ".pom.held .clock { color:#b45309; }",
      ".pom button { font-size:12px; font-weight:700; padding:4px 10px; border-radius:8px; cursor:pointer;",
      "  border:1px solid #c4b5fd; background:#fff; color:#5b21b6; }",
      ".pom button:hover { background:#ede9fe; }",
      ".pom button[disabled] { opacity:.45; cursor:default; }",
      ".pom .spent { font-size:11.5px; font-weight:700; color:#6d28d9; margin-left:auto; text-align:right; }",
      ".pom .spent .over { color:#b45309; }",
      ".pom .spent .under { color:#047857; }",
      ".pom select { font-size:11.5px; padding:3px 6px; border-radius:8px; border:1px solid #c4b5fd;",
      "  background:#fff; color:#5b21b6; font-weight:700; }",
      ".q-spent { font-size:10.5px; font-weight:800; color:#5b21b6; background:#f5f3ff; border-radius:999px;",
      "  padding:2px 8px; white-space:nowrap; flex:none; }",
      ".q-spent.live { color:#fff; background:#6d28d9; }",
      "@media (max-width: 640px) { .pom { gap:6px; padding:7px 8px; } .pom .spent { margin-left:0; width:100%; text-align:left; } }",
      /* Dark: explicit class, and OS-dark when no explicit light choice. */
      "html.dark .pom { background:#1e1b33; border-color:#4c1d95; }",
      "html.dark .pom .clock { color:#c4b5fd; }",
      "html.dark .pom.running .clock { color:#a5b4fc; }",
      "html.dark .pom.break .clock { color:#6ee7b7; }",
      "html.dark .pom.held .clock { color:#fbbf24; }",
      "html.dark .pom button, html.dark .pom select { background:#2e1065; border-color:#6d28d9; color:#ddd6fe; }",
      "html.dark .pom button:hover { background:#4c1d95; }",
      "html.dark .pom .spent { color:#c4b5fd; }",
      "html.dark .q-spent { color:#ddd6fe; background:#2e1065; }",
      "html.dark .q-spent.live { background:#7c3aed; color:#fff; }",
      "@media (prefers-color-scheme: dark) {",
      "  :root:not(.light) .pom { background:#1e1b33; border-color:#4c1d95; }",
      "  :root:not(.light) .pom .clock { color:#c4b5fd; }",
      "  :root:not(.light) .pom.running .clock { color:#a5b4fc; }",
      "  :root:not(.light) .pom.break .clock { color:#6ee7b7; }",
      "  :root:not(.light) .pom.held .clock { color:#fbbf24; }",
      "  :root:not(.light) .pom button, :root:not(.light) .pom select { background:#2e1065; border-color:#6d28d9; color:#ddd6fe; }",
      "  :root:not(.light) .pom button:hover { background:#4c1d95; }",
      "  :root:not(.light) .pom .spent { color:#c4b5fd; }",
      "  :root:not(.light) .q-spent { color:#ddd6fe; background:#2e1065; }",
      "  :root:not(.light) .q-spent.live { background:#7c3aed; color:#fff; }",
      "}"
    ].join("\n");
    var el = document.createElement("style");
    el.id = "pom-styles";
    el.textContent = css;
    document.head.appendChild(el);
  }

  /* ════════════════════════════════════════════════════════════════
     The controller. One per page; handles every card in `container`.
     ════════════════════════════════════════════════════════════════ */
  function Controller(opts) {
    this.ns = opts.ns;
    this.container = opts.container;
    this.effort = loadEffort(this.ns);
    this.paused = readJSON(pausedKey(this.ns), {});
    this.tickHandle = null;
    var self = this;

    injectStyles();
    this.decorateAll();

    /* The prep pages rebuild their list with innerHTML on every filter
       change, which wipes the injected controls - so re-decorate
       whenever the container's children change.
       childList only, NOT subtree: our own inserts and the per-second
       clock updates happen inside the cards, and observing those would
       re-enter this callback forever. */
    if (window.MutationObserver) {
      this.observer = new MutationObserver(function () { self.decorateAll(); });
      this.observer.observe(this.container, { childList: true });
    }

    /* Bank the elapsed seconds whenever the page might go away, so a
       closed tab or a backgrounded phone never loses a session. */
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) self.bank();
    });
    window.addEventListener("pagehide", function () { self.bank(); });
    window.addEventListener("beforeunload", function () { self.bank(); });

    /* Another tab changed the log or started its own timer. */
    window.addEventListener("storage", function (ev) {
      if (ev.key === effortKey(self.ns)) {
        self.effort = loadEffort(self.ns);
        self.paint();
        self.emit();
      } else if (ev.key === pausedKey(self.ns)) {
        self.paused = readJSON(pausedKey(self.ns), {});
        self.paint();
      } else if (ev.key === ACTIVE_KEY) {
        self.paint();
      }
    });

    this.startTicking();
  }

  /* Seconds already banked for a card. */
  Controller.prototype.logged = function (id) {
    return this.effort[id] || 0;
  };

  /* Seconds banked PLUS whatever the running timer has accrued but not
     yet written - what the UI should show right now. */
  Controller.prototype.liveLogged = function (id) {
    var a = getActive();
    var base = this.logged(id);
    if (a && a.ns === this.ns && a.id === id && a.mode === "focus") {
      base += Math.max(0, (Date.now() - a.startedAt) / 1000);
    }
    return base;
  };

  Controller.prototype.emit = function () {
    try {
      document.dispatchEvent(new CustomEvent("pomodoro:change", { detail: { ns: this.ns } }));
    } catch (_) {}
  };

  /* Write the running timer's elapsed seconds into the log and reset
     its clock origin. Safe to call at any time, including when nothing
     is running. */
  Controller.prototype.bank = function () {
    var a = getActive();
    if (!a || a.ns !== this.ns) return;
    var now = Date.now();
    if (a.mode === "focus") {
      var secs = Math.max(0, (now - a.startedAt) / 1000);
      if (secs >= 1) {
        this.effort[a.id] = this.logged(a.id) + secs;
        saveEffort(this.ns, this.effort);
        this.emit();
      }
    }
    a.startedAt = now;             // elapsed is now accounted for
    setActive(a);
  };

  Controller.prototype.savePaused = function () {
    writeJSON(pausedKey(this.ns), this.paused);
  };

  /* ── control actions ─────────────────────────────────────────── */
  Controller.prototype.start = function (id, mode) {
    var a = getActive();
    if (a) this.bank();            // bank whatever was running first
    var ms = (mode === "break" ? BREAK_MIN : focusMinutes()) * 60000;
    /* Resuming a paused session continues its remaining time; only a
       fresh session gets the full length. */
    if (mode !== "break" && this.paused[id] > 1000) {
      ms = this.paused[id];
      delete this.paused[id];
      this.savePaused();
    }
    setActive({
      ns: this.ns, id: id, mode: mode || "focus",
      startedAt: Date.now(),
      endsAt: Date.now() + ms
    });
    this.paint();
  };

  Controller.prototype.pause = function () {
    var a = getActive();
    if (a && a.ns === this.ns && a.mode === "focus") {
      var left = a.endsAt - Date.now();
      if (left > 1000) this.paused[a.id] = left;   // remember where we stopped
      else delete this.paused[a.id];
      this.savePaused();
    }
    this.bank();                   // keep the seconds...
    setActive(null);               // ...then stop the clock
    this.paint();
    this.emit();
  };

  /* Clear the recorded effort for one card (the timer's reset button).
     Also discards a half-finished session, so Start means a full one. */
  Controller.prototype.reset = function (id) {
    var a = getActive();
    if (a && a.ns === this.ns && a.id === id) setActive(null);
    delete this.effort[id];
    delete this.paused[id];
    this.savePaused();
    saveEffort(this.ns, this.effort);
    this.paint();
    this.emit();
  };

  /* Log a session by hand - for work done away from the screen. */
  Controller.prototype.addManual = function (id, minutes) {
    this.effort[id] = this.logged(id) + minutes * 60;
    saveEffort(this.ns, this.effort);
    this.paint();
    this.emit();
  };

  /* ── rendering ───────────────────────────────────────────────── */
  Controller.prototype.decorateAll = function () {
    var cards = this.container.querySelectorAll(".q-card[data-id]");
    for (var i = 0; i < cards.length; i++) this.decorate(cards[i]);
    this.paint();
  };

  Controller.prototype.decorate = function (card) {
    var body = card.querySelector(".q-body");
    var head = card.querySelector(".q-head");
    if (!body) return;
    /* The flag alone is not enough: a page that fills a card body lazily
       replaces its innerHTML, which throws away a bar we inserted earlier.
       Check the bar is still there, not just that we once added it. */
    if (card.getAttribute("data-pom") === "1" && card.querySelector(".pom")) return;
    card.setAttribute("data-pom", "1");

    var bar = document.createElement("div");
    bar.className = "pom";
    bar.innerHTML =
      '<span class="clock">' + mmss(focusMinutes() * 60) + '</span>' +
      '<button type="button" data-pom-act="start" title="Start a focus session on this topic">▶ Start</button>' +
      '<button type="button" data-pom-act="pause" title="Pause and bank the time so far">⏸ Pause</button>' +
      '<button type="button" data-pom-act="log15" title="Log 15 minutes you already spent offline">+15m</button>' +
      '<button type="button" data-pom-act="reset" title="Clear the effort logged for this topic">⟲ Reset</button>' +
      '<select data-pom-act="len" title="Focus session length">' +
        '<option value="15">15 min</option><option value="25">25 min</option>' +
        '<option value="45">45 min</option><option value="50">50 min</option>' +
      '</select>' +
      '<span class="spent"></span>';
    bar.querySelector('select[data-pom-act="len"]').value = String(focusMinutes());
    body.insertBefore(bar, body.firstChild);

    /* A compact "actual" chip in the header, so effort is visible
       without expanding the card. */
    if (head && !head.querySelector(".q-spent")) {
      var chip = document.createElement("span");
      chip.className = "q-spent";
      chip.style.display = "none";
      /* Insert next to the badge WHEREVER it lives — on a phone the header
         chips sit inside a wrapper, so the badge is a grandchild of the head
         and head.insertBefore(chip, badge) would throw NotFoundError. */
      var badge = head.querySelector(".q-badge");
      if (badge && badge.parentNode) badge.parentNode.insertBefore(chip, badge);
      else head.appendChild(chip);
    }
  };

  /* Repaint one card's clock, buttons, chip and spent-vs-estimate line. */
  Controller.prototype.paintCard = function (card, a) {
    var id = card.dataset.id;
    var bar = card.querySelector(".pom");
    if (!bar) return;
    var isActive = !!(a && a.ns === this.ns && a.id === id);
    var clock = bar.querySelector(".clock");
    var spent = bar.querySelector(".spent");
    var chip = card.querySelector(".q-spent");

    var held = this.paused[id] > 1000 ? this.paused[id] : 0;
    bar.classList.toggle("running", isActive && a.mode === "focus");
    bar.classList.toggle("break", isActive && a.mode === "break");
    bar.classList.toggle("held", !isActive && !!held);
    clock.textContent = isActive
      ? mmss((a.endsAt - Date.now()) / 1000)
      : (held ? mmss(held / 1000) : mmss(focusMinutes() * 60));

    var startBtn = bar.querySelector('[data-pom-act="start"]');
    var pauseBtn = bar.querySelector('[data-pom-act="pause"]');
    startBtn.textContent = isActive ? "▶ Running" : (held ? "▶ Resume" : "▶ Start");
    startBtn.title = held
      ? "Resume this paused session where it stopped"
      : "Start a focus session on this topic";
    startBtn.disabled = isActive;
    pauseBtn.disabled = !isActive;

    var secs = this.liveLogged(id);
    var est = parseInt(card.getAttribute("data-est") || "", 10);
    if (secs >= 30) {
      var txt = "⏳ actual <b>" + humanMin(secs) + "</b>";
      if (est > 0) {
        var ratio = (secs / 60) / est;
        var cls = ratio > 1.15 ? "over" : (ratio < 0.85 ? "under" : "");
        txt += ' vs <b>' + est + 'm</b> est <span class="' + cls + '">('
             + Math.round(ratio * 100) + '%)</span>';
      }
      spent.innerHTML = txt;
      if (chip) {
        chip.style.display = "";
        chip.textContent = "⏳ " + humanMin(secs);
        chip.classList.toggle("live", isActive && a.mode === "focus");
        chip.title = "Actual time you have logged on this topic";
      }
    } else {
      spent.innerHTML = est > 0 ? "no time logged yet · <b>" + est + "m</b> estimated" : "no time logged yet";
      if (chip) { chip.style.display = "none"; chip.classList.remove("live"); }
    }
  };

  /* Full repaint - on decorate and on any state change. The lists can
     hold a thousand cards, so this is NOT what the per-second tick
     calls; see startTicking. */
  Controller.prototype.paint = function () {
    var a = getActive();
    var cards = this.container.querySelectorAll(".q-card[data-id]");
    for (var i = 0; i < cards.length; i++) this.paintCard(cards[i], a);
  };

  /* One interval for the whole page. It only touches the ONE card whose
     timer is running, so a 1000-card list costs nothing per second. */
  Controller.prototype.startTicking = function () {
    var self = this;
    if (this.tickHandle) return;
    this.tickHandle = setInterval(function () {
      var a = getActive();
      if (!a || a.ns !== self.ns) return;
      if (Date.now() >= a.endsAt) { self.complete(a); return; }
      var card = self.container.querySelector('.q-card[data-id="' + cssId(a.id) + '"]');
      if (card) self.paintCard(card, a);
      /* Flush to storage periodically so a crash loses at most 15s. */
      if ((Date.now() - a.startedAt) / 1000 > 15) self.bank();
    }, 1000);
  };

  Controller.prototype.complete = function (a) {
    this.bank();                   // credit the final seconds
    setActive(null);
    delete this.paused[a.id];      // the session finished, nothing held over
    this.savePaused();
    this.paint();
    this.emit();
    chime();
    if (a.mode === "focus") {
      say("Pomodoro done — " + humanMin(this.logged(a.id)) + " logged. Take a " + BREAK_MIN + "-minute break.", "success");
      /* Offer the break rather than forcing it: one click, no nagging. */
      var card = this.container.querySelector('.q-card[data-id="' + cssId(a.id) + '"]');
      if (card) {
        var bar = card.querySelector(".pom");
        if (bar && !bar.querySelector('[data-pom-act="break"]')) {
          var b = document.createElement("button");
          b.type = "button";
          b.setAttribute("data-pom-act", "break");
          b.textContent = "☕ Break " + BREAK_MIN + "m";
          bar.insertBefore(b, bar.querySelector(".spent"));
          setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 120000);
        }
      }
    } else {
      say("Break over — back to it.", "info");
    }
  };

  /* ── click / change delegation ───────────────────────────────── */
  Controller.prototype.bindEvents = function () {
    var self = this;
    this.container.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-pom-act]");
      if (!btn) return;
      var card = btn.closest(".q-card[data-id]");
      if (!card) return;
      ev.stopPropagation();        // never toggle the card open/closed
      ev.preventDefault();
      var id = card.dataset.id;
      var act = btn.getAttribute("data-pom-act");
      if (act === "start") self.start(id, "focus");
      else if (act === "pause") self.pause();
      else if (act === "break") { self.start(id, "break"); btn.remove(); }
      else if (act === "log15") { self.addManual(id, 15); say("Logged 15 minutes", "success"); }
      else if (act === "reset") self.reset(id);
    }, true);

    this.container.addEventListener("change", function (ev) {
      var sel = ev.target.closest('select[data-pom-act="len"]');
      if (!sel) return;
      ev.stopPropagation();
      setFocusMinutes(parseInt(sel.value, 10));
      /* Choosing a new length means the old half-finished sessions no
         longer make sense - drop them so Start gives the new length. */
      self.paused = {};
      self.savePaused();
      /* Keep every card's dropdown in step - the length is a global
         preference, not a per-question one. */
      var all = self.container.querySelectorAll('select[data-pom-act="len"]');
      for (var i = 0; i < all.length; i++) all[i].value = sel.value;
      self.paint();
    }, true);
  };

  /* ── public API ──────────────────────────────────────────────── */
  var registry = {};

  window.Pomodoro = {
    /* Attach timers to every card in `container`. Returns the
       controller so a page can query totals for its summary line. */
    init: function (opts) {
      if (!opts || !opts.ns || !opts.container) return null;
      if (registry[opts.ns]) return registry[opts.ns];
      var c = new Controller(opts);
      c.bindEvents();
      registry[opts.ns] = c;
      return c;
    },
    /* Seconds logged against one card. */
    logged: function (ns, id) {
      var c = registry[ns];
      return c ? c.liveLogged(id) : (loadEffort(ns)[id] || 0);
    },
    /* Seconds logged across a list of ids (or everything, if omitted). */
    total: function (ns, ids) {
      var e = registry[ns] ? registry[ns].effort : loadEffort(ns);
      var sum = 0, k;
      if (ids) {
        for (var i = 0; i < ids.length; i++) sum += e[ids[i]] || 0;
      } else {
        for (k in e) if (Object.prototype.hasOwnProperty.call(e, k)) sum += e[k];
      }
      var a = getActive();
      if (a && a.ns === ns && a.mode === "focus" && (!ids || ids.indexOf(a.id) !== -1)) {
        sum += Math.max(0, (Date.now() - a.startedAt) / 1000);
      }
      return sum;
    },
    /* How many cards have any recorded effort. */
    count: function (ns) {
      var e = registry[ns] ? registry[ns].effort : loadEffort(ns);
      var n = 0, k;
      for (k in e) if (Object.prototype.hasOwnProperty.call(e, k) && e[k] >= 30) n++;
      return n;
    },
    /* Re-attach any bar a lazy body render wiped out. The MutationObserver
       only watches the container's direct children, so filling one card's
       body is invisible to it — the page calls this instead. */
    refresh: function (ns) {
      var c = registry[ns];
      if (c) c.decorateAll();
    },
    humanMin: humanMin
  };
})();

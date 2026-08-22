/* time-announcer.js — say the time out loud on the quarter hour.
 *
 * Asked for: "announce time every 15 mins (should be able to pause or
 * stop)".
 *
 * ALIGNED TO THE CLOCK, NOT TO WHEN YOU STARTED. "Every 15 minutes" for a
 * TIME announcement means :00, :15, :30, :45 — an announcement at 3:07 and
 * again at 3:22 would be technically every fifteen minutes and useless for
 * telling you where you are in the hour.
 *
 * IT NEVER ANNOUNCES A TIME THAT HAS PASSED. A laptop that slept through
 * 14:15 and woke at 14:41 must not then say "quarter past two" — that is
 * worse than silence, because you would believe it. Anything more than
 * GRACE_MS past a boundary is skipped, not queued.
 *
 * STATE SURVIVES NAVIGATION. This app is many separate pages, so the
 * setting lives in localStorage and every page picks it up. The caveat is
 * the browser's, not ours: speech synthesis needs a user gesture on each
 * new document, so after a navigation the first announcement may be
 * refused until you touch the page. The control says so rather than
 * pretending, and re-arms itself on the first interaction.
 */
(function () {
  "use strict";
  if (window.TimeAnnouncer) return;

  var KEY = "dp-time-announcer";
  var GRACE_MS = 90 * 1000;      // how late an announcement may still be true
  var TICK_MS = 15 * 1000;       // cheap: the work is one Date comparison
  var INTERVALS = [15, 30, 60];

  var state = load();
  var timer = null;
  var armed = false;             // has this document had a user gesture?

  function load() {
    var d = { mode: "off", every: 15, lastSlot: null };
    try {
      var raw = JSON.parse(localStorage.getItem(KEY));
      if (raw && typeof raw === "object") {
        if (raw.mode === "on" || raw.mode === "paused") d.mode = raw.mode;
        if (INTERVALS.indexOf(raw.every) !== -1) d.every = raw.every;
        if (typeof raw.lastSlot === "string") d.lastSlot = raw.lastSlot;
      }
    } catch (_) {}
    return d;
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {}
  }

  function supported() {
    return typeof window.speechSynthesis !== "undefined" &&
           typeof window.SpeechSynthesisUtterance !== "undefined";
  }

  /* The boundary this moment belongs to, as a stable key. Shared through
     localStorage so two open tabs do not both announce — whichever gets
     there first writes the slot and the other sees it already done. */
  function slotFor(d) {
    var mins = d.getHours() * 60 + d.getMinutes();
    var slot = Math.floor(mins / state.every) * state.every;
    return d.toDateString() + "|" + slot;
  }

  function phrase(d) {
    var h = d.getHours();
    var m = d.getMinutes();
    var suffix = h < 12 ? "A M" : "P M";
    var h12 = h % 12 === 0 ? 12 : h % 12;
    // "3 o'clock" reads better than "3:00", and the engines say the rest
    // correctly from digits.
    var body = m === 0 ? h12 + " o'clock" : h12 + ":" + (m < 10 ? "0" + m : m);
    return "It's " + body + " " + suffix;
  }

  function speak(text) {
    if (!supported()) return false;
    try {
      // Cancel anything still queued: a backlog of announcements read out
      // in sequence is the failure mode people remember.
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.rate = 0.95;
      u.volume = 1;
      window.speechSynthesis.speak(u);
      return true;
    } catch (_) {
      return false;
    }
  }

  function check(now) {
    if (state.mode !== "on") return;
    now = now || new Date();
    var mins = now.getHours() * 60 + now.getMinutes();
    if (mins % state.every !== 0 && (mins % state.every) * 60000 + now.getSeconds() * 1000 > GRACE_MS) {
      return;                                   // not near a boundary
    }
    var lateBy = (mins % state.every) * 60000 + now.getSeconds() * 1000;
    if (lateBy > GRACE_MS) return;              // slept through it — stay quiet

    var slot = slotFor(now);
    // Re-read from storage so a sibling tab that already announced wins.
    var fresh = load();
    if (fresh.lastSlot === slot) { state.lastSlot = slot; return; }

    state.lastSlot = slot;
    save();
    speak(phrase(now));
  }

  function start() {
    stopTimer();
    timer = setInterval(function () { check(); }, TICK_MS);
    check();
  }

  function stopTimer() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function applyMode() {
    if (state.mode === "on") start();
    else {
      stopTimer();
      if (supported()) { try { window.speechSynthesis.cancel(); } catch (_) {} }
    }
    save();
    paint();
  }

  /* ── the control ────────────────────────────────────────────────── */

  function inject() {
    if (document.getElementById("ta-style")) return;
    var css = [
      ".ta-btn{position:relative}",
      ".ta-btn.is-on{color:#4338ca}",
      ".ta-btn.is-paused{color:#b45309}",
      ".ta-dot{position:absolute;top:2px;right:2px;width:7px;height:7px;border-radius:50%;",
      "background:#4338ca}",
      ".ta-btn.is-paused .ta-dot{background:#f59e0b}",
      ".ta-pop{position:fixed;z-index:10060;min-width:216px;padding:12px;",
      "border-radius:12px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-surface,#fff);color:var(--color-text,#111827);",
      "box-shadow:0 16px 40px rgba(0,0,0,.18);font-size:13px}",
      ".ta-pop[hidden]{display:none}",
      ".ta-pop h4{margin:0 0 3px;font-size:13.5px;font-weight:800}",
      ".ta-pop p{margin:0 0 10px;font-size:11.5px;line-height:1.45;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-row{display:flex;gap:6px;margin-bottom:8px}",
      ".ta-row button{flex:1;font:inherit;font-size:12.5px;font-weight:700;padding:6px 8px;",
      "border-radius:9px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827);cursor:pointer}",
      ".ta-row button.on{background:#4338ca;border-color:#4338ca;color:#fff}",
      ".ta-int{display:flex;gap:6px;align-items:center;font-size:11.5px;font-weight:700;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-int button{padding:4px 9px;border-radius:999px;font-size:11.5px}",
      ".ta-warn{margin-top:9px;font-size:11px;line-height:1.45;color:#b45309}",
    ].join("");
    var el = document.createElement("style");
    el.id = "ta-style";
    el.textContent = css;
    document.head.appendChild(el);
  }

  var btn = null, pop = null;

  function paint() {
    if (!btn) return;
    btn.classList.toggle("is-on", state.mode === "on");
    btn.classList.toggle("is-paused", state.mode === "paused");
    btn.title = state.mode === "on"
      ? "Announcing the time every " + state.every + " minutes"
      : state.mode === "paused" ? "Time announcements paused"
      : "Announce the time out loud";
    var dot = btn.querySelector(".ta-dot");
    if (state.mode === "off") { if (dot) dot.remove(); }
    else if (!dot) {
      var d = document.createElement("span");
      d.className = "ta-dot";
      btn.appendChild(d);
    }
    if (!pop) return;
    pop.querySelectorAll("[data-ta-mode]").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-ta-mode") === state.mode);
    });
    pop.querySelectorAll("[data-ta-every]").forEach(function (b) {
      b.classList.toggle("on", parseInt(b.getAttribute("data-ta-every"), 10) === state.every);
    });
    var warn = pop.querySelector(".ta-warn");
    if (warn) warn.hidden = !(state.mode === "on" && !armed);
  }

  function buildPop() {
    pop = document.createElement("div");
    pop.className = "ta-pop";
    pop.hidden = true;
    pop.innerHTML =
      '<h4>Announce the time</h4>' +
      '<p>Spoken on the clock — :00, :15, :30, :45. A missed one is skipped, ' +
      'never read out late.</p>' +
      '<div class="ta-row">' +
        '<button type="button" data-ta-mode="on">Start</button>' +
        '<button type="button" data-ta-mode="paused">Pause</button>' +
        '<button type="button" data-ta-mode="off">Stop</button>' +
      '</div>' +
      '<div class="ta-int"><span>Every</span>' +
        INTERVALS.map(function (n) {
          return '<button type="button" data-ta-every="' + n + '">' + n + 'm</button>';
        }).join("") +
      '</div>' +
      '<p class="ta-warn" hidden>Your browser needs a tap on this page before it ' +
      'will speak. Interact anywhere and the next announcement will play.</p>';
    document.body.appendChild(pop);

    pop.addEventListener("click", function (ev) {
      var m = ev.target.closest("[data-ta-mode]");
      if (m) {
        state.mode = m.getAttribute("data-ta-mode");
        // Starting IS the gesture, so speak a confirmation — it also proves
        // to the user that sound works before they walk away from the desk.
        if (state.mode === "on") { armed = true; speak(phrase(new Date())); }
        applyMode();
        return;
      }
      var e = ev.target.closest("[data-ta-every]");
      if (e) {
        state.every = parseInt(e.getAttribute("data-ta-every"), 10) || 15;
        state.lastSlot = null;
        applyMode();
      }
    });
  }

  function place() {
    var r = btn.getBoundingClientRect();
    pop.hidden = false;
    var w = pop.offsetWidth;
    pop.style.top = (r.bottom + 8) + "px";
    pop.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left)) + "px";
  }

  function mount() {
    var host = document.querySelector(".top-context");
    if (!host || document.querySelector(".ta-btn")) return;
    inject();

    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "help-btn ta-btn";
    btn.setAttribute("aria-label", "Announce the time");
    btn.innerHTML = '<i data-feather="volume-2"></i>';
    // Next to the other utility buttons, not in the page body: this is an
    // ambient setting and belongs where it is reachable from anywhere.
    var anchor = host.querySelector(".help-btn");
    if (anchor) host.insertBefore(btn, anchor);
    else host.appendChild(btn);

    buildPop();
    btn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (pop.hidden) { place(); paint(); } else { pop.hidden = true; }
    });
    document.addEventListener("click", function (ev) {
      if (pop.hidden) return;
      if (ev.target.closest(".ta-pop") || ev.target.closest(".ta-btn")) return;
      pop.hidden = true;
    });

    if (window.feather) { try { window.feather.replace(); } catch (_) {} }
    paint();
  }

  /* The first real interaction on this document unblocks speech. Recorded
     so the control can stop warning about it. */
  ["pointerdown", "keydown"].forEach(function (evt) {
    document.addEventListener(evt, function () {
      if (armed) return;
      armed = true;
      paint();
    }, { once: true, capture: true });
  });

  // Another tab changed the setting — follow it rather than disagreeing.
  window.addEventListener("storage", function (ev) {
    if (ev.key !== KEY) return;
    state = load();
    applyMode();
  });

  window.TimeAnnouncer = {
    start: function () { state.mode = "on"; applyMode(); },
    pause: function () { state.mode = "paused"; applyMode(); },
    stop:  function () { state.mode = "off"; state.lastSlot = null; applyMode(); },
    state: function () { return JSON.parse(JSON.stringify(state)); },
    _phrase: phrase,
    _slotFor: slotFor,
    _check: check,
    _supported: supported,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { mount(); applyMode(); });
  } else {
    mount();
    applyMode();
  }
})();

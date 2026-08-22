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
 *
 * DOES IT RUN WHEN THE WINDOW IS MINIMISED? Partly, and the honest answer
 * has three parts.
 *
 *   1. THROTTLING — survivable, and measured. A hidden tab has its timers
 *      clamped, in Chrome to once per MINUTE after about five minutes.
 *      Simulated against this logic: a 60s tick still catches all 96
 *      quarter-hours in a day, because GRACE_MS is 90s. At a 120s clamp it
 *      would start missing half, which is why the grace window is not
 *      tightened.
 *   2. FREEZING — fatal, and the reason KEEPALIVE exists below. Chrome may
 *      FREEZE an eligible background tab, at which point timers do not run
 *      at all. Tabs that are playing audio are exempt, so the opt-in
 *      keep-alive holds a near-silent Web Audio node open. It costs a
 *      little battery and makes the tab show an "playing audio" indicator,
 *      which is why it is opt-in rather than always on.
 *   3. A CLOSED PAGE, OR A BACKGROUNDED PHONE BROWSER — nothing works, and
 *      nothing here can make it. Script only runs while the document is
 *      alive, and mobile browsers suspend background pages almost at once.
 *      That is a limit of the platform, not a setting.
 *
 * Whatever happens, a missed announcement is SKIPPED rather than replayed,
 * so waking up never produces a burst of stale times.
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
  var keepCtx = null;            // Web Audio node held open, see KEEPALIVE

  function load() {
    var d = { mode: "off", every: 15, lastSlot: null, keepalive: false };
    try {
      var raw = JSON.parse(localStorage.getItem(KEY));
      if (raw && typeof raw === "object") {
        if (raw.mode === "on" || raw.mode === "paused") d.mode = raw.mode;
        if (INTERVALS.indexOf(raw.every) !== -1) d.every = raw.every;
        if (typeof raw.lastSlot === "string") d.lastSlot = raw.lastSlot;
        d.keepalive = !!raw.keepalive;
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

  /* ── KEEPALIVE ──────────────────────────────────────────────────────
     Chrome may FREEZE a background tab, and a frozen page runs no timers
     at all — which is the difference between "announcements are late" and
     "announcements stop". Tabs that are playing audio are exempt from
     freezing, so this holds a Web Audio node open at a level far below
     hearing.

     It is OPT-IN because it is not free: the tab shows the browser's
     "playing audio" indicator, and keeping an audio context alive costs a
     little battery. Someone who only uses this at a desk with the window
     visible should not pay for either.

     The gain is very small but NOT zero. A muted graph is the thing a
     browser is entitled to optimise away, and an optimised-away graph
     stops counting as playback — which would silently undo the whole
     point. Verified only by reasoning about the spec; if freezing still
     happens with this on, that is the first thing to re-check. */
  /* Running as an INSTALLED PWA rather than a tab. It changes nothing about
     what the platform allows — an installed app is still a document, and a
     minimised window is still hidden — but it does change the ADVICE: someone
     who installed the app is far more likely to leave it minimised and expect
     it to keep working, which is exactly the case the keep-alive exists for.
     So the recommendation is surfaced instead of buried. */
  function isInstalled() {
    try {
      return (window.matchMedia &&
              (window.matchMedia("(display-mode: standalone)").matches ||
               window.matchMedia("(display-mode: window-controls-overlay)").matches ||
               window.matchMedia("(display-mode: minimal-ui)").matches)) ||
             window.navigator.standalone === true;
    } catch (_) {
      return false;
    }
  }

  function keepaliveOn() {
    if (keepCtx) return true;
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return false;
      var ctx = new Ctx();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      gain.gain.value = 0.0001;            // inaudible, not silent
      osc.frequency.value = 30;            // below most speakers anyway
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      keepCtx = { ctx: ctx, osc: osc };
      return true;
    } catch (_) {
      return false;
    }
  }

  function keepaliveOff() {
    if (!keepCtx) return;
    try { keepCtx.osc.stop(); } catch (_) {}
    try { keepCtx.ctx.close(); } catch (_) {}
    keepCtx = null;
  }

  function applyKeepalive() {
    // Only worth holding while announcements are actually due to happen.
    if (state.mode === "on" && state.keepalive) keepaliveOn();
    else keepaliveOff();
  }

  function applyMode() {
    if (state.mode === "on") start();
    else {
      stopTimer();
      if (supported()) { try { window.speechSynthesis.cancel(); } catch (_) {} }
    }
    applyKeepalive();
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
      ".ta-keep{display:flex;align-items:center;gap:7px;margin-top:11px;",
      "font-size:12px;font-weight:700;cursor:pointer}",
      ".ta-keep input{width:15px;height:15px;accent-color:#4338ca;cursor:pointer}",
      ".ta-note{margin-top:7px !important;font-size:10.5px !important;line-height:1.45}",
      ".ta-tip{margin-top:6px !important;font-size:11px !important;line-height:1.45;",
      "color:#4338ca;font-weight:700}",
      ".ta-tip[hidden]{display:none}",
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
    var keep = pop.querySelector("[data-ta-keep]");
    if (keep) keep.checked = !!state.keepalive;
    var tip = pop.querySelector(".ta-tip");
    if (tip) tip.hidden = !(isInstalled() && !state.keepalive);
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
      '<label class="ta-keep"><input type="checkbox" data-ta-keep> ' +
        'Keep going when minimised</label>' +
      '<p class="ta-tip" hidden>You are running the installed app &mdash; turn this ' +
      'on, or the system can freeze the window while it is minimised and the ' +
      'announcements stop.</p>' +
      '<p class="ta-note">Announcements survive another window being on top. They ' +
      'stop if the browser freezes this tab &mdash; the option above prevents that ' +
      'by holding a silent sound open, at the cost of a little battery and an ' +
      '&ldquo;audio playing&rdquo; mark on the tab. Nothing works once the page ' +
      'is closed, or on a phone with the browser in the background.</p>' +
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
      var k = ev.target.closest("[data-ta-keep]");
      if (k) {
        state.keepalive = !!k.checked;
        applyKeepalive();
        save();
        paint();
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
    keepalive: function (on) { state.keepalive = !!on; applyKeepalive(); save(); paint(); },
    _keptAlive: function () { return !!keepCtx; },
    _phrase: phrase,
    _slotFor: slotFor,
    _check: check,
    _supported: supported,
    _isInstalled: isInstalled,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { mount(); applyMode(); });
  } else {
    mount();
    applyMode();
  }
})();

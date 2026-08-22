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
  var INTERVALS = [15, 30, 45, 60];   // 45 was simply missing before
  var MAX_EVERY = 720;                // 12h; beyond that use exact times
  var SILENT_MS = 1500;               // no onstart by now => it did not speak

  var state = load();
  var timer = null;
  var armed = false;             // has this document had a user gesture?
  var keepCtx = null;            // Web Audio node held open, see KEEPALIVE
  var voicesReady = false;
  var health = { at: null, ok: null, why: "", said: "" };   // see NOISY FAILURE

  function load() {
    var d = { mode: "off", every: 15, at: [], label: "",
              lastSlot: null, keepalive: false };
    try {
      var raw = JSON.parse(localStorage.getItem(KEY));
      if (raw && typeof raw === "object") {
        if (raw.mode === "on" || raw.mode === "paused") d.mode = raw.mode;
        // ANY whole number of minutes, not just the presets. The old code
        // tested `INTERVALS.indexOf(raw.every)` and SILENTLY reset anything
        // else to 15 — so a custom value could never have stuck even if the
        // UI had offered one.
        var e = parseInt(raw.every, 10);
        if (e >= 0 && e <= MAX_EVERY) d.every = e;
        if (Array.isArray(raw.at)) d.at = raw.at.filter(isHHMM);
        if (typeof raw.label === "string") d.label = raw.label.slice(0, 60);
        if (typeof raw.lastSlot === "string") d.lastSlot = raw.lastSlot;
        d.keepalive = !!raw.keepalive;
      }
    } catch (_) {}
    return d;
  }

  function isHHMM(v) {
    return typeof v === "string" && /^([01]?\d|2[0-3]):[0-5]\d$/.test(v);
  }

  /* "9, 9:30, 13:45 18:00" -> ["09:00","09:30","13:45","18:00"].
     Deliberately forgiving about separators and about a bare hour, because
     this is a text field someone types into once and should not have to
     get exactly right. Anything unparseable is dropped, and the caller
     shows what survived so nothing is silently ignored. */
  function parseTimes(text) {
    var out = [];
    String(text || "").split(/[^0-9:]+/).forEach(function (tok) {
      if (!tok) return;
      var m = /^(\d{1,2})(?::(\d{1,2}))?$/.exec(tok);
      if (!m) return;
      var h = parseInt(m[1], 10), mi = parseInt(m[2] || "0", 10);
      if (h > 23 || mi > 59) return;
      var v = (h < 10 ? "0" + h : h) + ":" + (mi < 10 ? "0" + mi : mi);
      if (out.indexOf(v) === -1) out.push(v);
    });
    return out.sort();
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
  function slotFor(d, slotMins) {
    return d.toDateString() + "|" + slotMins;
  }

  /* WHICH BOUNDARY, IF ANY, THIS MOMENT BELONGS TO.
     Returns the boundary in minutes-since-midnight, or null.

     Two sources, either of which can fire: the repeating interval, and the
     list of exact times. An exact time WINS when both land together, so
     that "09:00" is announced once rather than twice.

     A 45-minute interval does not divide the hour, and that is fine — it
     steps from midnight (00:00, 00:45, 01:30, ...) rather than resetting
     each hour, which is the only definition of "every 45 minutes" that is
     actually every 45 minutes. */
  function dueSlot(now) {
    var mins = now.getHours() * 60 + now.getMinutes();
    var lateBy = function (boundary) {
      return (mins - boundary) * 60000 + now.getSeconds() * 1000;
    };

    for (var i = 0; i < state.at.length; i++) {
      var p = state.at[i].split(":");
      var b = parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
      var late = lateBy(b);
      if (late >= 0 && late <= GRACE_MS) return b;
    }

    if (state.every > 0) {
      var boundary = Math.floor(mins / state.every) * state.every;
      if (lateBy(boundary) <= GRACE_MS) return boundary;
    }
    return null;
  }

  function phrase(d) {
    var h = d.getHours();
    var m = d.getMinutes();
    var suffix = h < 12 ? "A M" : "P M";
    var h12 = h % 12 === 0 ? 12 : h % 12;
    // "3 o'clock" reads better than "3:00", and the engines say the rest
    // correctly from digits.
    var body = m === 0 ? h12 + " o'clock" : h12 + ":" + (m < 10 ? "0" + m : m);
    var said = "It's " + body + " " + suffix;
    // THE HEADING, read before the time. The point of an announcement is
    // rarely the time itself — it is what the time is FOR. "Stand up and
    // stretch. It's 3 o'clock PM" does a job that "It's 3 o'clock PM"
    // does not.
    if (state.label) said = state.label.replace(/[.!?]*$/, "") + ". " + said;
    return said;
  }

  /* ── NOISY FAILURE ──────────────────────────────────────────────────
     The old speak() returned true if speechSynthesis.speak() did not
     THROW. It almost never throws. It just does nothing, and there was no
     onerror handler, no watchdog and nothing on screen — so "the
     announcements are not working" had no evidence anywhere, which is
     precisely the report that arrived.

     Every attempt now lands in `health`, and the panel shows it. */
  function note(ok, why, said) {
    if (ok === null) { health = { at: null, ok: null, why: "", said: "" }; paint(); return; }
    health = { at: new Date(), ok: ok, why: why || "", said: said || "" };
    try {
      if (window.dpInert && !ok) window.dpInert("time announcer", why);
    } catch (_) {}
    paint();
  }

  /* Voices arrive ASYNCHRONOUSLY. On Android especially, getVoices() is
     empty for the first moments after load and speaking into that gap is
     dropped without a sound or an error. */
  function primeVoices() {
    if (!supported()) return;
    try {
      voicesReady = (window.speechSynthesis.getVoices() || []).length > 0;
      if (voicesReady) return;
      window.speechSynthesis.addEventListener("voiceschanged", function () {
        voicesReady = (window.speechSynthesis.getVoices() || []).length > 0;
      });
    } catch (_) {}
  }

  function speak(text) {
    if (!supported()) {
      note(false, "this browser has no speech synthesis");
      return false;
    }
    var synth = window.speechSynthesis;

    function fire() {
      try {
        var u = new SpeechSynthesisUtterance(text);
        u.rate = 0.95;
        u.volume = 1;
        u.lang = (document.documentElement.lang || navigator.language ||
                  "en-US");

        // Naming a voice explicitly. Left unset, some Android builds pick
        // nothing at all and stay silent.
        try {
          var vs = synth.getVoices() || [];
          var want = u.lang.slice(0, 2).toLowerCase();
          var v = vs.filter(function (x) {
            return (x.lang || "").slice(0, 2).toLowerCase() === want;
          })[0] || vs.filter(function (x) { return x.default; })[0] || vs[0];
          if (v) u.voice = v;
        } catch (_) {}

        var started = false, errored = false;
        u.onstart = function () { started = true; note(true, "", text); };
        u.onerror = function (ev) {
          errored = true;
          note(false, (ev && ev.error) || "the browser refused to speak");
        };
        synth.speak(u);

        // CHROME LEAVES THE QUEUE PAUSED after some page lifecycle events,
        // and a paused queue accepts utterances forever without saying one.
        try { if (synth.paused) synth.resume(); } catch (_) {}

        // WATCHDOG. If onstart has not fired, nothing was said — and with
        // no error either, this is the silent case that had no evidence.
        setTimeout(function () {
          if (!started && !errored) {
            note(false, armed
              ? "the browser accepted it but said nothing"
              : "blocked until you tap the page once");
          }
        }, SILENT_MS);
        return true;
      } catch (e) {
        note(false, "speak() threw: " + (e && e.message));
        return false;
      }
    }

    // CANCEL-THEN-SPEAK IN THE SAME TASK IS A CHROME BUG: the new utterance
    // is swallowed. The old code did exactly that on every announcement, on
    // desktop and Android alike. Only cancel when something is actually in
    // flight, and let the cancel settle first.
    if (synth.speaking || synth.pending) {
      try { synth.cancel(); } catch (_) {}
      setTimeout(fire, 150);
      return true;
    }
    return fire();
  }

  function check(now) {
    if (state.mode !== "on") return;
    now = now || new Date();

    var boundary = dueSlot(now);
    if (boundary === null) return;   // not near one, or slept through it

    var slot = slotFor(now, boundary);
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
     Two different problems, one mechanism.

     ON A DESKTOP the risk is FREEZING: Chrome may freeze an eligible
     background window, and a frozen page runs no timers at all — the
     difference between "announcements are late" and "announcements stop".

     ON A LOCKED PHONE the page is suspended outright and nothing in an
     ordinary web page survives it. The one exception is MEDIA: a page with
     an active media session keeps running with the screen off, which is
     exactly how a music PWA keeps playing in your pocket. So the keep-alive
     is a real <audio> element on loop, registered with the Media Session
     API — NOT a Web Audio oscillator, which the OS does not treat as
     playback, and which is what the first version of this used.

     The track is one second of 8 kHz PCM at an amplitude of ONE least
     significant bit: genuinely audio, inaudible in practice. Not digital
     silence, on purpose — silence is what a platform may optimise away, and
     an optimised-away stream stops counting as playback, quietly undoing
     the whole point.

     THE LOCK SCREEN WILL SHOW A MEDIA NOTIFICATION for it, and that is a
     feature rather than a leak. It is honest about what is running, and its
     pause button really does stop the announcements — a control that looks
     like it stops something must stop it.

     BEST-EFFORT, AND SAID SO. Whether a locked Android keeps the page
     scheduled well enough to speak is a device-and-version question that
     cannot be settled from here. iOS is stricter and is not expected to
     work at all. */
  /* Running as an INSTALLED PWA rather than a tab. It changes nothing about
     what the platform allows — an installed app is still a document, and a
     minimised window is still hidden — but it does change the ADVICE: someone
     who installed the app is far more likely to leave it minimised or pocket
     the phone and expect it to keep working, which is exactly the case the
     keep-alive exists for. So the recommendation is surfaced, not buried. */
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
      var el = document.getElementById("ta-keepalive");
      if (!el) {
        el = document.createElement("audio");
        el.id = "ta-keepalive";
        el.src = "/static/audio-keepalive.wav";
        el.loop = true;
        el.preload = "auto";
        // NOT muted: a muted element does not hold audio focus, and without
        // audio focus the OS will not keep the page alive for it.
        el.volume = 0.02;
        el.setAttribute("playsinline", "");
        document.body.appendChild(el);
      }
      var p = el.play();
      if (p && p.catch) {
        // Blocked until a gesture. Start IS a gesture so the normal path
        // works; a page restored without one picks it up on first touch.
        p.catch(function () {});
      }
      setMediaSession();
      keepCtx = { el: el };
      return true;
    } catch (_) {
      return false;
    }
  }

  /* Naming the session is what makes the lock-screen entry legible, and
     wiring its buttons is what makes it honest. */
  function setMediaSession() {
    if (!("mediaSession" in navigator)) return;
    try {
      if (window.MediaMetadata) {
        navigator.mediaSession.metadata = new window.MediaMetadata({
          title: "Announcing the time",
          artist: "Every " + state.every + " minutes",
          album: "DailyPlanner",
        });
      }
      navigator.mediaSession.playbackState = "playing";
      navigator.mediaSession.setActionHandler("pause", function () {
        state.mode = "paused";
        applyMode();
      });
      navigator.mediaSession.setActionHandler("play", function () {
        state.mode = "on";
        applyMode();
      });
      navigator.mediaSession.setActionHandler("stop", function () {
        state.mode = "off";
        state.lastSlot = null;
        applyMode();
      });
    } catch (_) {}
  }

  function keepaliveOff() {
    if (!keepCtx) return;
    try { keepCtx.el.pause(); } catch (_) {}
    try {
      if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "none";
    } catch (_) {}
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
      ".ta-fld{margin-top:9px}",
      ".ta-fld[hidden]{display:none}",
      ".ta-fld label{display:block;font-size:11.5px;font-weight:700;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-fld input{width:100%;box-sizing:border-box;margin-top:4px;font:inherit;",
      "font-size:13px;padding:6px 8px;border-radius:8px;",
      "border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827)}",
      ".ta-fld small{display:block;margin-top:3px;font-size:10.5px;line-height:1.4;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-health{margin:9px 0 0 !important;font-size:11px !important;",
      "line-height:1.45;font-weight:700}",
      ".ta-health.good{color:#047857}",
      ".ta-health.bad{color:#b91c1c}",
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

    var custom = INTERVALS.indexOf(state.every) === -1;
    var cbtn = pop.querySelector("[data-ta-custom]");
    if (cbtn) {
      cbtn.classList.toggle("on", custom);
      cbtn.textContent = custom ? state.every + "m" : "Custom";
    }
    var crow = pop.querySelector("[data-ta-customrow]");
    if (crow && custom) crow.hidden = false;
    var cin = pop.querySelector("[data-ta-every-in]");
    if (cin && document.activeElement !== cin) cin.value = state.every;
    var atin = pop.querySelector("[data-ta-at]");
    if (atin && document.activeElement !== atin) atin.value = state.at.join(", ");
    var lbl = pop.querySelector("[data-ta-label]");
    if (lbl && document.activeElement !== lbl) lbl.value = state.label;
    paintAtEcho();

    /* THE HEALTH LINE. The whole reason this feature could fail unnoticed
       was that nothing on screen ever said whether it had worked. */
    var h = pop.querySelector("[data-ta-health]");
    if (h) {
      if (!health.at) {
        h.textContent = state.mode === "on"
          ? "Nothing announced yet this session."
          : "";
        h.className = "ta-health";
      } else {
        var t = health.at.toTimeString().slice(0, 5);
        h.className = "ta-health " + (health.ok ? "good" : "bad");
        h.textContent = health.ok
          ? "\u2713 Spoke at " + t + " \u2014 \u201c" + health.said + "\u201d"
          : "\u26a0 " + t + " \u2014 " + health.why;
      }
    }
  }

  function paintAtEcho() {
    if (!pop) return;
    var e = pop.querySelector("[data-ta-at-echo]");
    if (!e) return;
    e.textContent = state.at.length
      ? "Understood: " + state.at.join(", ")
      : "Optional. Blank = only the interval above.";
  }

  function buildPop() {
    pop = document.createElement("div");
    pop.className = "ta-pop";
    pop.hidden = true;
    pop.innerHTML =
      '<h4>Announce the time</h4>' +
      '<p>Spoken on the clock, not from when you pressed start. A missed one ' +
      'is skipped rather than read out late.</p>' +
      '<div class="ta-row">' +
        '<button type="button" data-ta-mode="on">Start</button>' +
        '<button type="button" data-ta-mode="paused">Pause</button>' +
        '<button type="button" data-ta-mode="off">Stop</button>' +
      '</div>' +
      '<div class="ta-int"><span>Every</span>' +
        INTERVALS.map(function (n) {
          return '<button type="button" data-ta-every="' + n + '">' + n + 'm</button>';
        }).join("") +
        '<button type="button" data-ta-custom>Custom</button>' +
      '</div>' +
      '<div class="ta-fld" data-ta-customrow hidden>' +
        '<label>Minutes between announcements' +
        '<input type="number" min="0" max="' + MAX_EVERY + '" step="1" ' +
        'data-ta-every-in placeholder="e.g. 20"></label>' +
        '<small>0 = only the exact times below.</small>' +
      '</div>' +
      '<div class="ta-fld">' +
        '<label>Also announce at exactly' +
        '<input type="text" data-ta-at placeholder="9:00, 13:30, 18:45"></label>' +
        '<small data-ta-at-echo></small>' +
      '</div>' +
      '<div class="ta-fld">' +
        '<label>Say this first' +
        '<input type="text" maxlength="60" data-ta-label ' +
        'placeholder="e.g. Stand up and stretch"></label>' +
        '<small>Read out before the time, every time.</small>' +
      '</div>' +
      '<div class="ta-row"><button type="button" data-ta-test>Test the voice now</button></div>' +
      '<p class="ta-health" data-ta-health></p>' +
      '<label class="ta-keep"><input type="checkbox" data-ta-keep> ' +
        'Keep going when minimised or locked</label>' +
      '<p class="ta-tip" hidden>You are running the installed app &mdash; turn this ' +
      'on, or the system will freeze it once the window is minimised and the ' +
      'announcements stop.</p>' +
      '<p class="ta-note">This holds an inaudible sound playing, which is what stops ' +
      'the system suspending the app. A media entry appears on the lock screen while ' +
      'it runs &mdash; its pause button really does stop the announcements. ' +
      '<b>Battery:</b> the announcements themselves cost nothing measurable ' +
      '(one date comparison every 15s, and a second of speech an hour). This ' +
      'checkbox is the part that costs &mdash; holding audio open keeps the ' +
      'screen-off CPU awake, roughly like leaving a podcast paused-but-loaded: ' +
      'expect a few percent over a night, not a flat battery. Leave it OFF if ' +
      'you only want announcements while you are looking at the app. ' +
      '<b>On a locked phone this is best-effort:</b> it is the only ' +
      'mechanism that can work, and whether it does depends on your device. Nothing ' +
      'works once the app is fully closed &mdash; the web cannot speak from a closed ' +
      'app.</p>' +
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
        return;
      }
      if (ev.target.closest("[data-ta-custom]")) {
        var row = pop.querySelector("[data-ta-customrow]");
        if (row) row.hidden = false;
        var inp = pop.querySelector("[data-ta-every-in]");
        if (inp) { inp.value = state.every; inp.focus(); inp.select(); }
        return;
      }
      if (ev.target.closest("[data-ta-test]")) {
        // Pressing it IS the gesture, so this is also the way to re-arm a
        // page that has not been touched yet.
        armed = true;
        note(null, "");
        speak(phrase(new Date()));
        return;
      }
    });

    /* The three text fields. Committed on input rather than on a Save
       button — there is nothing here worth a round trip to confirm, and a
       setting that needs saving is a setting people forget to save. */
    pop.addEventListener("input", function (ev) {
      var n = ev.target;
      if (n.matches("[data-ta-every-in]")) {
        var v = parseInt(n.value, 10);
        if (!(v >= 0)) return;
        state.every = Math.min(MAX_EVERY, v);
        state.lastSlot = null;
        save();
        paint();
        return;
      }
      if (n.matches("[data-ta-at]")) {
        state.at = parseTimes(n.value);
        state.lastSlot = null;
        save();
        paintAtEcho();
        return;
      }
      if (n.matches("[data-ta-label]")) {
        state.label = n.value.slice(0, 60);
        save();
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
    _dueSlot: dueSlot,
    _parseTimes: parseTimes,
    _health: function () { return health; },
    _set: function (patch) { Object.keys(patch).forEach(function (k) {
      state[k] = patch[k]; }); },
    _check: check,
    _supported: supported,
    _isInstalled: isInstalled,
  };

  primeVoices();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { mount(); applyMode(); });
  } else {
    mount();
    applyMode();
  }
})();

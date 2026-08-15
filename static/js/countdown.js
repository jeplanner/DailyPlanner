/* ==========================================================================
   countdown.js — the live deadline ticker.

   Mountable the same way as gamify.js / pomodoro.js, so the goal planner,
   the OKR page and the interview-prep dashboard all show the same clock
   without three copies of this arithmetic.

       Countdown.mount(el, {targetIso, flash, onZero})
       Countdown.mountAll(root)     // every [data-countdown] under root
       Countdown.text(targetIso)    // one-off string, no ticking

   Three things this does that a naive setInterval(1000) does not:

     1. TICKS AT THE RIGHT RATE. Per second under an hour, per minute under
        a day, per hour beyond that. Animating a digit nobody is reading is
        just battery drain, and this page is meant to sit open all day.

     2. STOPS WHEN HIDDEN. A backgrounded tab keeps its timers running; we
        pause on visibilitychange and re-sync on return, so a phone left in
        a pocket does not burn cycles.

     3. RENDERS TWO WAYS from one instance. Hosts that want the full
        DAYS / HOURS / MINUTES readout provide [data-cd-d] [data-cd-h]
        [data-cd-m] (and optionally [data-cd-s]); dense lists that only have
        room for one line use [data-cd-compact] ("44d 06h 12m"); the older
        single-dominant-unit hooks [data-cd-big]/[data-cd-unit] still work.
        Because all three units are visible at once the UNIT no longer
        escalates, so urgency is carried entirely by the tone attribute and
        the pulse — which still starts only in the last day, since a
        permanently pulsing page is one you stop seeing.

   The server computes the same breakdown in utils/countdown.py and both
   must agree; the client re-derives it only so the display can tick between
   fetches.
   ========================================================================== */
(function (global) {
  "use strict";

  var SEC = 1000, MIN = 60 * SEC, HOUR = 60 * MIN, DAY = 24 * HOUR, WEEK = 7 * DAY;
  var instances = [];
  var timer = null;

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  /* The complementary split — the parts sum to the whole, so 16 days reads
     "2w 2d", never "2w 16d". Mirrors breakdown() on the server. */
  function split(ms) {
    var abs = Math.abs(ms);
    var weeks = Math.floor(abs / WEEK); abs -= weeks * WEEK;
    var days = Math.floor(abs / DAY); abs -= days * DAY;
    var hours = Math.floor(abs / HOUR); abs -= hours * HOUR;
    var minutes = Math.floor(abs / MIN); abs -= minutes * MIN;
    return {
      overdue: ms < 0, total: ms, weeks: weeks, days: days,
      hours: hours, minutes: minutes, seconds: Math.floor(abs / SEC),
      totalDays: Math.floor(Math.abs(ms) / DAY)
    };
  }

  /* Which unit is the headline, and how often it needs redrawing. */
  function display(b) {
    if (b.overdue) {
      return { value: b.totalDays, unit: b.totalDays === 1 ? "day overdue" : "days overdue",
               tick: MIN, tone: "overdue" };
    }
    var t = b.total;
    if (t >= 3 * WEEK) {
      var w = Math.floor(t / WEEK);
      return { value: w, unit: w === 1 ? "week" : "weeks", tick: HOUR, tone: "calm" };
    }
    if (t >= WEEK) return { value: Math.floor(t / DAY), unit: "days", tick: HOUR, tone: "calm" };
    if (t >= DAY) {
      var d = Math.floor(t / DAY);
      return { value: d, unit: d === 1 ? "day" : "days", tick: MIN, tone: "soon" };
    }
    if (t >= HOUR) return { value: Math.floor(t / HOUR), unit: "hours left", tick: SEC, tone: "urgent" };
    if (t > 0) return { value: Math.floor(t / MIN), unit: "minutes left", tick: SEC, tone: "urgent" };
    return { value: 0, unit: "time is up", tick: MIN, tone: "done" };
  }

  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function when(ts) {
    var dt = new Date(ts);
    return DAYS[dt.getDay()] + " " + dt.getDate() + " " + MONTHS[dt.getMonth()] +
           ", " + pad(dt.getHours()) + ":" + pad(dt.getMinutes());
  }

  /* The supporting line under the headline.

     It deliberately changes KIND, not just precision, as the deadline nears.
     Far out, the remainder after the headline ("2d 08h" under "6 weeks") is
     actively misleading — it reads as the total. What you actually want to
     know that far ahead is the DATE. Close in, the date is obvious and the
     running clock is what matters. */
  function detail(b, d, target) {
    if (b.overdue) {
      var late = [];
      if (b.weeks) late.push(b.weeks + "w");
      if (b.days) late.push(b.days + "d");
      if (!late.length && b.hours) late.push(b.hours + "h");
      return (late.length ? "overdue by " + late.join(" ") : "just passed") +
             " · was " + when(target);
    }
    if (d.tone === "calm") return "due " + when(target);
    if (d.tone === "soon") {
      /* Inside a week both halves are useful: what is left, and when. */
      return pad(b.hours) + "h " + pad(b.minutes) + "m more · " + when(target);
    }
    /* Under a day the seconds matter, so show a real clock. */
    return pad(b.hours) + ":" + pad(b.minutes) + ":" + pad(b.seconds);
  }

  /* DAYS : HOURS : MINUTES, the requested format.

     Note these are NOT the complementary split above: with no weeks segment
     on show, `days` has to be the TOTAL days (44), never the remainder after
     whole weeks (2), or a six-week deadline would read "2d 06h 12m" and be
     wildly wrong. Hours and minutes are the ordinary remainders. */
  function segments(b) {
    var abs = Math.abs(b.total);
    return {
      d: Math.floor(abs / DAY),
      h: Math.floor((abs % DAY) / HOUR),
      m: Math.floor((abs % HOUR) / MIN),
      s: Math.floor((abs % MIN) / SEC)
    };
  }

  /* The compact one-line form of the same thing, for dense lists where three
     separate boxes would be noise: "44d 06h 12m". */
  function compact(b) {
    var g = segments(b);
    var text = g.d + "d " + pad(g.h) + "h " + pad(g.m) + "m";
    /* Inside the last hour the minutes alone stop conveying the pressure,
       so the seconds join in. */
    if (!b.overdue && b.total < HOUR) text = pad(g.m) + "m " + pad(g.s) + "s";
    return b.overdue ? text + " over" : text;
  }

  function render(inst) {
    var target = inst.target;
    if (isNaN(target)) return;
    var b = split(target - Date.now());
    var d = display(b);
    var g = segments(b);

    /* Segmented D/H/M display. Any of the hooks may be absent — a host that
       only wants days writes one of them. */
    if (inst.dEl) inst.dEl.textContent = String(g.d);
    if (inst.hEl) inst.hEl.textContent = pad(g.h);
    if (inst.mEl) inst.mEl.textContent = pad(g.m);
    if (inst.sEl) inst.sEl.textContent = pad(g.s);
    if (inst.compactEl) inst.compactEl.textContent = compact(b);

    /* Legacy single-unit hooks, still used where one number is enough. */
    if (inst.bigEl) inst.bigEl.textContent = String(d.value);
    if (inst.unitEl) inst.unitEl.textContent = d.unit;
    if (inst.detailEl) inst.detailEl.textContent = detail(b, d, target);

    inst.el.dataset.tone = d.tone;
    inst.el.dataset.overdue = b.overdue ? "true" : "false";
    /* Flash is opt-in per goal AND only in the last day — an always-on
       pulse is noise, and noise gets ignored precisely when it matters.
       Now that every unit is on screen at once the unit no longer escalates,
       so this colour/pulse change carries the urgency by itself. */
    var shouldFlash = !!inst.flash && (d.tone === "urgent" || d.tone === "overdue");
    if (shouldFlash !== inst.flashing) {
      inst.flashing = shouldFlash;
      /* Crossing into (or out of) the last day while the page sits open has
         to start (or stop) the blink — that transition is the entire point. */
      scheduleFlash();
    }
    inst.el.classList.toggle("flash", shouldFlash);
    if (b.total <= 0 && !inst.firedZero) {
      inst.firedZero = true;
      if (typeof inst.onZero === "function") { try { inst.onZero(inst); } catch (e) {} }
    }
    /* THE REDRAW RATE MUST MATCH THE FINEST UNIT ON SCREEN, not the distance
       to the deadline.

       display() picks a rate suited to a single dominant unit — hourly when
       something is weeks away, which is right if the only thing showing is
       "19 weeks". But the D/H/M readout and the compact form both show
       MINUTES at every distance, so an hourly redraw left the minutes stale
       for up to an hour and the whole clock looked frozen. Seconds are worse
       again. So: ask what is actually rendered. */
    var finest = d.tick;
    if (inst.mEl || inst.compactEl) finest = Math.min(finest, MIN);
    if (inst.sEl) finest = SEC;
    /* Inside the last hour the compact form switches to showing seconds. */
    if (inst.compactEl && b.total < HOUR && b.total > 0) finest = SEC;
    inst.tick = finest;
  }

  /* ── The flash ─────────────────────────────────────────────────────────
     Driven from JS, not from a CSS animation, because on phones a CSS-only
     pulse frequently does nothing at all:

       · iOS Low Power Mode PAUSES CSS animations outright;
       · "Reduce Motion" (common on phones, and implied by Low Power Mode)
         suppresses them, and the old rule then fell back to `animation:none`
         — i.e. no indication whatsoever, on exactly the devices where the
         deadline matters most.

     Toggling a class instead is a discrete state change, which nothing
     throttles. At ~0.7s it is well under the 3 Hz accessibility ceiling for
     flashing content.

     Under Reduce Motion we deliberately do NOT blink — the class is pinned
     ON so the element sits in its high-contrast alert state permanently.
     That respects the setting while still being impossible to miss, which
     the old `animation: none` was not. */
  var FLASH_MS = 700;
  var flashTimer = null;
  var flashOn = false;

  function reduceMotion() {
    try {
      return !!(global.matchMedia &&
                global.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (e) { return false; }
  }

  function paintFlash() {
    for (var i = 0; i < instances.length; i++) {
      var inst = instances[i];
      if (!inst.flashing) { inst.el.classList.remove("flash-on"); continue; }
      inst.el.classList.toggle("flash-on", reduceMotion() ? true : flashOn);
    }
  }

  function scheduleFlash() {
    var any = false;
    for (var i = 0; i < instances.length; i++) {
      if (instances[i].flashing) { any = true; break; }
    }
    if (flashTimer) { clearInterval(flashTimer); flashTimer = null; }
    /* Only run a timer while something is actually flashing, and never while
       the tab is hidden. */
    if (!any || (global.document && global.document.hidden)) { paintFlash(); return; }
    flashOn = true;
    paintFlash();
    flashTimer = global.setInterval(function () {
      flashOn = !flashOn;
      paintFlash();
    }, FLASH_MS);
  }

  /* One shared timer for every instance on the page, re-armed to the
     shortest interval anyone currently needs. */
  function schedule() {
    if (timer) { clearTimeout(timer); timer = null; }
    if (!instances.length || global.document.hidden) return;
    var soonest = instances.reduce(function (m, i) {
      return Math.min(m, i.tick || HOUR);
    }, HOUR);
    timer = global.setTimeout(function () {
      instances.forEach(render);
      schedule();
    }, Math.max(250, soonest));
  }

  var Countdown = {
    /* el needs [data-cd-big], [data-cd-unit], [data-cd-detail] children;
       any of them may be absent. */
    mount: function (el, opts) {
      if (!el) return null;
      opts = opts || {};
      var iso = opts.targetIso || el.dataset.countdown;
      if (!iso) return null;
      var inst = {
        el: el,
        target: Date.parse(iso),
        flash: opts.flash !== undefined ? opts.flash : el.dataset.flash !== "false",
        onZero: opts.onZero,
        bigEl: el.querySelector("[data-cd-big]"),
        unitEl: el.querySelector("[data-cd-unit]"),
        detailEl: el.querySelector("[data-cd-detail]"),
        dEl: el.querySelector("[data-cd-d]"),
        hEl: el.querySelector("[data-cd-h]"),
        mEl: el.querySelector("[data-cd-m]"),
        sEl: el.querySelector("[data-cd-s]"),
        compactEl: el.querySelector("[data-cd-compact]"),
        tick: HOUR,
        flashing: false,
        firedZero: false
      };
      if (isNaN(inst.target)) return null;
      instances.push(inst);
      render(inst);
      schedule();
      return inst;
    },

    mountAll: function (root) {
      var scope = root || global.document;
      var found = scope.querySelectorAll("[data-countdown]");
      for (var i = 0; i < found.length; i++) Countdown.mount(found[i]);
      return instances.length;
    },

    /* Drop every instance — call before re-rendering a list, or the old
       nodes keep ticking against detached DOM. */
    clear: function () {
      instances.length = 0;
      if (timer) { clearTimeout(timer); timer = null; }
      if (flashTimer) { clearInterval(flashTimer); flashTimer = null; }
    },

    /* A one-off string for places that do not need to tick. */
    text: function (iso) {
      var t = Date.parse(iso);
      if (isNaN(t)) return "";
      var b = split(t - Date.now()), d = display(b);
      return d.value + " " + d.unit;
    },

    _split: split,
    _display: display,
    _segments: segments,
    _compact: compact,
    _flashing: function () {
      return instances.filter(function (i) { return i.flashing; }).length;
    }
  };

  if (global.document) {
    global.document.addEventListener("visibilitychange", function () {
      if (global.document.hidden) {
        if (timer) { clearTimeout(timer); timer = null; }
        if (flashTimer) { clearInterval(flashTimer); flashTimer = null; }
      } else {
        /* Re-render immediately on return: while hidden the clock kept
           moving even though we stopped drawing it. */
        instances.forEach(render);
        schedule();
        scheduleFlash();
      }
    });
  }

  global.Countdown = Countdown;
})(typeof window !== "undefined" ? window : this);

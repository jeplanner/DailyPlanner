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

     3. SHOWS ONE DOMINANT UNIT. The escalation from weeks to days to a live
        clock IS the urgency signal, which is why nothing flashes until the
        last day. A permanently pulsing page is one you stop seeing.

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

  function render(inst) {
    var target = inst.target;
    if (isNaN(target)) return;
    var b = split(target - Date.now());
    var d = display(b);
    if (inst.bigEl) inst.bigEl.textContent = String(d.value);
    if (inst.unitEl) inst.unitEl.textContent = d.unit;
    if (inst.detailEl) inst.detailEl.textContent = detail(b, d, target);
    inst.el.dataset.tone = d.tone;
    /* Flash is opt-in per goal AND only in the last day — an always-on
       pulse is noise, and noise gets ignored precisely when it matters. */
    inst.el.classList.toggle("flash", !!inst.flash && (d.tone === "urgent" || d.tone === "overdue"));
    if (b.total <= 0 && !inst.firedZero) {
      inst.firedZero = true;
      if (typeof inst.onZero === "function") { try { inst.onZero(inst); } catch (e) {} }
    }
    inst.tick = d.tick;
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
        tick: HOUR,
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
    },

    /* A one-off string for places that do not need to tick. */
    text: function (iso) {
      var t = Date.parse(iso);
      if (isNaN(t)) return "";
      var b = split(t - Date.now()), d = display(b);
      return d.value + " " + d.unit;
    },

    _split: split,
    _display: display
  };

  if (global.document) {
    global.document.addEventListener("visibilitychange", function () {
      if (global.document.hidden) {
        if (timer) { clearTimeout(timer); timer = null; }
      } else {
        /* Re-render immediately on return: while hidden the clock kept
           moving even though we stopped drawing it. */
        instances.forEach(render);
        schedule();
      }
    });
  }

  global.Countdown = Countdown;
})(typeof window !== "undefined" ? window : this);

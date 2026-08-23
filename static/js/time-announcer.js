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
              items: [], said: {}, lastSlot: null, keepalive: false };
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
        if (raw.said && typeof raw.said === "object") d.said = raw.said;
        if (Array.isArray(raw.items)) {
          d.items = raw.items.filter(function (it) {
            return it && isHHMM(it.at);
          }).map(function (it) {
            var rep = REPEATS.indexOf(it.repeat) === -1 ? null : it.repeat;
            var start = isYMD(it.start) ? it.start : null;
            // MIGRATION from the date-only shape: a fixed date became a
            // one-off, and no date became a daily repeat.
            if (!rep) {
              rep = isYMD(it.date) ? "once" : "daily";
              start = isYMD(it.date) ? it.date : todayYMD();
            }
            return {
              id: String(it.id || ""),
              at: it.at,
              until: isHHMM(it.until) ? it.until : null,
              mins: parseInt(it.mins, 10) > 0
                ? Math.min(720, parseInt(it.mins, 10)) : 0,
              repeat: rep,
              days: Array.isArray(it.days)
                ? it.days.filter(function (d) { return d >= 0 && d <= 6; })
                : [],
              start: start || todayYMD(),
              end: isYMD(it.end) ? it.end : null,
              text: String(it.text || "").slice(0, 120),
              on: it.on !== false,
            };
          });
        }
        d.keepalive = !!raw.keepalive;
      }
    } catch (_) {}

    // MIGRATION. The previous shape was one shared label plus a bare list of
    // times. Each of those becomes an announcement carrying that label, so
    // nobody loses a setting by upgrading.
    if (!d.items.length && d.at.length) {
      d.items = d.at.map(function (t, i) {
        return { id: "m" + i + t, at: t, until: null, mins: 0,
                 repeat: "daily", days: [], start: todayYMD(), end: null,
                 text: d.label, on: true };
      });
      d.at = [];
    }
    return d;
  }

  function isYMD(v) {
    return typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
  }

  function todayYMD(d) {
    d = d || new Date();
    var m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + "-" + (m < 10 ? "0" + m : m) + "-" +
           (day < 10 ? "0" + day : day);
  }

  function newId() {
    // No Math.random needed and no collision risk in practice: an id only has
    // to be unique within one person's list.
    idSeq += 1;
    return "i" + idSeq + "-" + (new Date()).getTime();
  }
  var idSeq = 0;

  /* ── RECURRENCE ─────────────────────────────────────────────────────
     Each announcement repeats on a rule, inside an optional window.

     `start` is the first day it may fire (defaults to the day it was
     created) and `end` is the last (null means forever). The rule then
     decides which days inside that window count.

     THE TWO AWKWARD CASES, both decided in favour of firing rather than
     silently skipping. A monthly reminder on the 31st CLAMPS to the last day
     of a short month, so February gets it on the 28th rather than not at
     all; a yearly one on 29 February clamps to the 28th in common years.
     Skipping would be defensible and it is not what a person setting a
     reminder wants. */
  var REPEATS = ["once", "daily", "weekly", "monthly", "yearly", "custom"];
  var DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  function ymdToParts(v) {
    var p = String(v).split("-");
    return { y: +p[0], m: +p[1], d: +p[2] };
  }

  function daysInMonth(y, m) {           // m is 1-based
    return new Date(y, m, 0).getDate();
  }

  function weekdayOf(ymd) {
    var p = ymdToParts(ymd);
    return new Date(p.y, p.m - 1, p.d).getDay();
  }

  function matchesOn(it, ymd) {
    var start = isYMD(it.start) ? it.start : null;
    if (start && ymd < start) return false;
    if (isYMD(it.end) && ymd > it.end) return false;

    var rep = REPEATS.indexOf(it.repeat) === -1 ? "daily" : it.repeat;
    if (rep === "daily") return true;
    if (rep === "once") return !!start && ymd === start;
    if (rep === "custom") {
      var days = Array.isArray(it.days) ? it.days : [];
      return days.indexOf(weekdayOf(ymd)) !== -1;
    }
    if (!start) return true;             // no anchor to repeat from
    var s = ymdToParts(start), t = ymdToParts(ymd);
    if (rep === "weekly") return weekdayOf(ymd) === weekdayOf(start);
    if (rep === "monthly") {
      var dm = Math.min(s.d, daysInMonth(t.y, t.m));   // clamp, see above
      return t.d === dm;
    }
    if (rep === "yearly") {
      var dy = Math.min(s.d, daysInMonth(t.y, s.m));
      return t.m === s.m && t.d === dy;
    }
    return false;
  }

  /* The rule in words, for the row and for the read-back. */
  function repeatWords(it) {
    var rep = REPEATS.indexOf(it.repeat) === -1 ? "daily" : it.repeat;
    var base;
    if (rep === "once") base = it.start || "once";
    else if (rep === "daily") base = "every day";
    else if (rep === "weekly") base = "every " +
      (it.start ? DAY_NAMES[weekdayOf(it.start)] : "week");
    else if (rep === "monthly") base = "monthly on the " +
      (it.start ? ordinal(ymdToParts(it.start).d) : "same day");
    else if (rep === "yearly") base = "yearly on " +
      (it.start ? shortDate(it.start) : "the same date");
    else base = (it.days || []).length
      ? (it.days.slice().sort().map(function (d) { return DAY_NAMES[d]; }).join(" "))
      : "no days chosen";
    if (rep !== "once" && isYMD(it.end)) base += ", until " + shortDate(it.end);
    return base;
  }

  /* "5:00 AM", or "8:00 AM–8:00 PM every 60m" when it repeats in a window. */
  function timeWords(it) {
    if (!(it.mins > 0) || !isHHMM(it.until)) return friendly(it.at);
    return friendly(it.at) + "\u2013" + friendly(it.until) +
           " \u00b7 " + it.mins + "m";
  }

  function ordinal(n) {
    var s = ["th", "st", "nd", "rd"], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  function shortDate(ymd) {
    var p = ymdToParts(ymd);
    return p.d + " " + ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                        "Aug", "Sep", "Oct", "Nov", "Dec"][p.m - 1] +
           " " + p.y;
  }

  /* Has this announcement finished for good? A `once` in the past, or any
     rule whose end date has gone. Shown as expired rather than kept looking
     armed. */
  function isExpired(it, today) {
    if (isYMD(it.end) && it.end < today) return true;
    if (it.repeat === "once" && isYMD(it.start) && it.start < today) return true;
    return false;
  }

  function isHHMM(v) {
    return typeof v === "string" && /^([01]?\d|2[0-3]):[0-5]\d$/.test(v);
  }

  /* "9, 9:30, 13:45 18:00" -> ["09:00","09:30","13:45","18:00"].
     Deliberately forgiving about separators and about a bare hour, because
     this is a text field someone types into once and should not have to
     get exactly right. Anything unparseable is dropped, and the caller
     shows what survived so nothing is silently ignored. */
  /* `defaultMer` is the AM/PM chosen with the buttons. It applies ONLY when
     the typed text does not settle the question itself:

       "5"      + PM  ->  17:00     (the chooser decides)
       "5pm"    + AM  ->  17:00     (what you typed wins)
       "17:00"  + AM  ->  17:00     (already unambiguous, chooser ignored)
       "0:30"   + PM  ->  00:30     (hour 0 is 24-hour by construction)

     Typing beats clicking, because someone who wrote "pm" meant it. */
  function parseTimes(text, defaultMer) {
    var out = [];
    // A FULL STOP IS A TIME SEPARATOR. "5.00" is how most of the world writes
    // five o'clock, and the previous version split on any non-digit — so it
    // read that as TWO times, 05:00 and 00:00, and quietly announced midnight
    // every night. Dots and dashes between the hour and minute are joined
    // back up before anything is split.
    var t = String(text || "")
      .toLowerCase()
      .replace(/(\d)\s*[.\-]\s*(\d)/g, "$1:$2");

    // Split on commas, semicolons, "and", or runs of spaces — but NOT on
    // letters, because am/pm has to survive to the next step.
    t.split(/\s*(?:,|;|\band\b|\s{2,})\s*|\s+(?=\d)/).forEach(function (tok) {
      tok = (tok || "").trim();
      if (!tok) return;
      var m = /^(\d{1,2})(?::(\d{1,2}))?\s*(am|pm|a\.m\.|p\.m\.)?$/.exec(tok);
      if (!m) return;
      var h = parseInt(m[1], 10), mi = parseInt(m[2] || "0", 10);
      var mer = (m[3] || "").replace(/\./g, "");
      if (mi > 59) return;
      // Only a bare 1-12 is ambiguous. 0 and 13-23 can only be 24-hour.
      if (!mer && (defaultMer === "am" || defaultMer === "pm") &&
          h >= 1 && h <= 12) {
        mer = defaultMer;
      }
      // 12-HOUR INPUT, because "5pm" is what people type. Without a meridiem
      // the number is taken as-is, so 17:00 still works and 5 means 05:00.
      if (mer === "pm" && h < 12) h += 12;
      else if (mer === "am" && h === 12) h = 0;
      if (h > 23) return;
      var v = (h < 10 ? "0" + h : h) + ":" + (mi < 10 ? "0" + mi : mi);
      if (out.indexOf(v) === -1) out.push(v);
    });
    return out.sort();
  }

  /* 24h -> "5:00 AM", so the echo is unambiguous about what was understood.
     "Is 5.00 five in the morning?" is only a question because nothing ever
     read the answer back. */
  function friendly(hhmm) {
    var p = hhmm.split(":");
    var h = parseInt(p[0], 10);
    var suffix = h < 12 ? "AM" : "PM";
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + ":" + p[1] + " " + suffix;
  }

  /* The schedule in words. Used by the lock-screen metadata and the panel. */
  function scheduleWords() {
    var bits = [];
    if (state.every > 0) bits.push("every " + state.every + " min");
    var live = state.items.filter(function (it) {
      return it.on && !isExpired(it, todayYMD());
    });
    if (live.length) {
      bits.push(live.length + (live.length === 1 ? " announcement"
                                                 : " announcements"));
    }
    return bits.length ? bits.join(", plus ") : "nothing scheduled";
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
  /* THE TIMES ONE ANNOUNCEMENT SPEAKS ON A DAY IT IS ACTIVE.
     Returns minutes-since-midnight, ascending.

     `at` is when it starts. `until` is when it stops, and `mins` is how often
     it repeats in between — so "drink water, every day, 08:00 to 20:00, every
     60 minutes" is one announcement rather than thirteen.

     Leave `until` and `mins` empty and it speaks ONCE at `at`, which is what
     every existing announcement does and why nothing had to be migrated. */
  function slotsFor(it) {
    var from = hhmmToMins(it.at);
    if (from === null) return [];
    var step = parseInt(it.mins, 10);
    var to = isHHMM(it.until) ? hhmmToMins(it.until) : null;
    if (!(step > 0) || to === null || to < from) return [from];

    var out = [];
    // A guard rather than a while(true): a step of 1 across a full day is
    // 1440 slots, and anything past that is a bug, not a schedule.
    for (var m = from; m <= to && out.length < 1441; m += step) out.push(m);
    return out;
  }

  function hhmmToMins(v) {
    if (!isHHMM(v)) return null;
    var p = v.split(":");
    return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
  }

  function minsToHHMM(m) {
    var h = Math.floor(m / 60), mm = m % 60;
    return (h < 10 ? "0" + h : h) + ":" + (mm < 10 ? "0" + mm : mm);
  }

  /* WHICH NAMED ANNOUNCEMENTS ARE DUE RIGHT NOW.
     Returns the items, not just a flag, because several can land on the same
     minute and all of them must be said.

     THE DATE RULE, as asked for: no date means EVERY day from now on; a date
     means that day only. A date in the past never fires again, and the panel
     shows it as expired rather than silently ignoring it. */
  function dueItems(now) {
    var mins = now.getHours() * 60 + now.getMinutes();
    var today = todayYMD(now);
    var out = [];
    for (var i = 0; i < state.items.length; i++) {
      var it = state.items[i];
      if (!it.on) continue;                       // stopped individually
      if (!matchesOn(it, today)) continue;        // not a day this rule fires

      // A windowed announcement has many slots in a day, and each settles on
      // its own — so the key carries the SLOT, not the item's start time.
      var slots = slotsFor(it);
      for (var k = 0; k < slots.length; k++) {
        var late = (mins - slots[k]) * 60000 + now.getSeconds() * 1000;
        if (late < 0 || late > GRACE_MS) continue;   // not yet, or slept past
        var key = today + "|" + minsToHHMM(slots[k]);
        if (state.said[it.id] === key) continue;     // already said this slot
        out.push({ item: it, slot: slots[k], key: key,
                   id: it.id, text: it.text, at: it.at, on: it.on });
        break;                                       // one slot per tick
      }
    }
    return out;
  }

  function dueSlot(now) {
    var mins = now.getHours() * 60 + now.getMinutes();
    var lateBy = function (boundary) {
      return (mins - boundary) * 60000 + now.getSeconds() * 1000;
    };

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
    // THE SHARED HEADING still applies to the repeating interval. Named
    // announcements carry their own text and are prepended by check().
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
    var today = todayYMD(now);

    // Re-read from storage so a sibling tab that already announced wins.
    var fresh = load();

    // ── the named announcements ──────────────────────────────────────
    var items = dueItems(now).filter(function (d) {
      return fresh.said[d.id] !== d.key;
    });

    // ── the repeating interval ───────────────────────────────────────
    var boundary = dueSlot(now);
    var intervalDue = boundary !== null &&
                      fresh.lastSlot !== slotFor(now, boundary);

    if (!items.length && !intervalDue) return;

    // ONE UTTERANCE, not several. Two announcements landing on the same
    // minute must not talk over each other, and queueing them would let a
    // backlog build up — which is the failure people remember.
    var parts = items.map(function (it) {
      return (it.text || "").replace(/[.!?]*$/, "") || "Reminder";
    });
    parts.push(phrase(now));

    items.forEach(function (d) {
      state.said[d.id] = d.key;
    });
    if (intervalDue) state.lastSlot = slotFor(now, boundary);

    // Keep `said` from growing forever: yesterday's marks cannot matter.
    Object.keys(state.said).forEach(function (k) {
      if (String(state.said[k]).slice(0, 10) !== today) delete state.said[k];
    });

    save();
    speak(parts.join(". "));
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
      // METADATA MUST BE SET ONCE PLAYBACK HAS ACTUALLY STARTED, not before.
      // play() is asynchronous; a session described while the element is
      // still loading is routinely discarded, and then there is no lock
      // screen entry even though the audio is running.
      el.addEventListener("playing", setMediaSession);

      var p = el.play();
      if (p && p.catch) {
        // Blocked until a gesture. Start IS a gesture so the normal path
        // works; a page restored without one picks it up on first touch.
        // SAID OUT LOUD, though: silently swallowing this is how "keep going
        // when minimised" ends up ticked and doing nothing.
        p.catch(function (err) {
          note(false, "keep-alive audio was blocked (" +
                      ((err && err.name) || "autoplay policy") +
                      ") — tap the page once");
        });
      }
      setMediaSession();
      keepCtx = { el: el };
      return true;
    } catch (_) {
      return false;
    }
  }

  /* Naming the session is what makes the lock-screen entry legible, and
     wiring its buttons is what makes it honest.

     WHY THE LOCK SCREEN SHOWED NOTHING. The keep-alive track was ONE SECOND
     long. Chrome does not create a media notification for media shorter than
     about five seconds — it classifies short clips as sound effects, not
     playback. Audio focus was held either way, so the page stayed awake and
     the announcements worked, but there were no controls anywhere. The track
     is now 40 seconds, still one least-significant-bit of amplitude. */
  function setMediaSession() {
    if (!("mediaSession" in navigator)) return;
    try {
      if (window.MediaMetadata) {
        navigator.mediaSession.metadata = new window.MediaMetadata({
          title: "Announcing the time",
          artist: scheduleWords(),
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
      ".ta-backdrop{position:fixed;inset:0;z-index:10059;",
      "background:rgba(15,18,28,.45);backdrop-filter:blur(1.5px)}",
      ".ta-backdrop[hidden]{display:none}",
      "html.ta-locked, html.ta-locked body{overflow:hidden}",
      /* CENTRED, not anchored to the button. It is a dialog with several
         fields, a day picker and a list — dragging inside it must not be
         able to land outside it. */
      ".ta-pop{position:fixed;z-index:10060;top:50%;left:50%;",
      "transform:translate(-50%,-50%);width:min(420px,calc(100vw - 24px));",
      "max-height:min(86vh,720px);overflow-y:auto;overscroll-behavior:contain;",
      "padding:14px 16px 16px;",
      "border-radius:14px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-surface,#fff);color:var(--color-text,#111827);",
      "box-shadow:0 24px 64px rgba(0,0,0,.28);font-size:13px}",
      ".ta-pop[hidden]{display:none}",
      "@media (max-width:520px){.ta-pop{width:calc(100vw - 16px);",
      "max-height:92vh}}",
      ".ta-pop h4{margin:0 0 3px;font-size:13.5px;font-weight:800;padding-right:22px}",
      ".ta-x{position:absolute;top:6px;right:7px;border:0;background:none;",
      "cursor:pointer;font-size:19px;line-height:1;padding:2px 5px;border-radius:6px;",
      "color:var(--color-text-secondary,#9ca3af)}",
      ".ta-x:hover{background:var(--color-bg,#f3f4f6);color:var(--color-text,#111827)}",
      ".ta-pop p{margin:0 0 10px;font-size:11.5px;line-height:1.45;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-row{display:flex;gap:6px;margin-bottom:8px}",
      // .ta-int is listed everywhere .ta-row is. The interval buttons live in
      // .ta-int and these rules were scoped to .ta-row only, so 15/30/45/60
      // never highlighted the selected one — and never even got a border or a
      // background. paint() was setting .on correctly the whole time; there
      // was simply nothing for the class to do.
      ".ta-row button,.ta-int button{font:inherit;font-size:12.5px;font-weight:700;",
      "padding:6px 8px;border-radius:9px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827);cursor:pointer}",
      ".ta-row button{flex:1}",
      ".ta-row button.on,.ta-int button.on{background:#4338ca;border-color:#4338ca;",
      "color:#fff;box-shadow:0 0 0 2px color-mix(in srgb,#4338ca 30%,transparent)}",
      ".ta-int{display:flex;gap:6px;align-items:center;font-size:11.5px;font-weight:700;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-int{flex-wrap:wrap}",
      ".ta-int button{flex:0 0 auto;padding:5px 10px;border-radius:999px;font-size:11.5px}",
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
      ".ta-sec{margin:12px 0 5px;font-size:11px;font-weight:800;",
      "letter-spacing:.05em;text-transform:uppercase;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-list{list-style:none;margin:0;padding:0;max-height:260px;",
      "overflow:auto;border:1px solid var(--color-border,#e5e7eb);",
      "border-radius:9px}",
      ".ta-list:empty{display:none}",
      ".ta-empty{padding:9px 10px;font-size:11px;line-height:1.45;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-item{display:flex;align-items:center;gap:7px;padding:6px 8px;",
      "border-bottom:1px solid var(--color-border,#e5e7eb);font-size:12px}",
      ".ta-item:last-child{border-bottom:0}",
      ".ta-item.off{opacity:.5}",
      ".ta-item.expired .ta-when i{color:#b91c1c}",
      ".ta-tog{flex:0 0 auto;border:0;background:none;cursor:pointer;",
      "font-size:13px;line-height:1;padding:2px;color:#4338ca}",
      ".ta-item.off .ta-tog{color:var(--color-text-secondary,#9ca3af)}",
      ".ta-when{flex:0 0 auto;display:flex;flex-direction:column;",
      "min-width:70px;line-height:1.25}",
      ".ta-when b{font-size:12px;font-variant-numeric:tabular-nums}",
      ".ta-when i{font-style:normal;font-size:9.5px;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-what{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;",
      "white-space:nowrap}",
      ".ta-del{flex:0 0 auto;border:0;background:none;cursor:pointer;",
      "font-size:15px;line-height:1;padding:2px 4px;",
      "color:var(--color-text-secondary,#9ca3af)}",
      ".ta-del:hover{color:#b91c1c}",
      ".ta-add{display:flex;flex-direction:column;gap:5px;margin-top:7px}",
      ".ta-add-row{display:flex;flex-wrap:wrap;gap:5px;align-items:flex-end}",
      ".ta-add select{font:inherit;font-size:12px;padding:5px 7px;",
      "border-radius:8px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827);",
      "flex:1 1 120px;min-width:0}",
      ".ta-dt{flex:1 1 120px;display:flex;flex-direction:column;gap:2px;",
      "font-size:10px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;",
      "color:var(--color-text-secondary,#6b7280);min-width:0}",
      ".ta-dt i{font-style:normal;font-weight:500;text-transform:none;",
      "letter-spacing:0}",
      ".ta-dt input{width:100%}",
      ".ta-dt .ta-timefld{width:100%}",
      ".ta-dt .ta-timefld input{flex:1 1 auto;min-width:0}",
      ".ta-days{display:flex;flex-wrap:wrap;gap:4px}",
      ".ta-days[hidden]{display:none}",
      ".ta-days button{font:inherit;font-size:11px;font-weight:700;",
      "padding:4px 8px;border-radius:999px;cursor:pointer;",
      "border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827)}",
      ".ta-days button.on{background:#4338ca;border-color:#4338ca;color:#fff}",
      "[data-ta-new-end][aria-invalid],[data-ta-new-until][aria-invalid]",
      "{border-color:#b91c1c}",
      ".ta-add input{font:inherit;font-size:12px;padding:5px 7px;",
      "border-radius:8px;border:1px solid var(--color-border,#e5e7eb);",
      "background:var(--color-bg,#f9fafb);color:var(--color-text,#111827);",
      "min-width:0}",
      ".ta-timefld{display:flex;align-items:stretch;gap:4px;flex:0 0 auto;min-width:0}",
      ".ta-ampm{display:flex;border:1px solid var(--color-border,#e5e7eb);",
      "border-radius:8px;overflow:hidden;flex:0 0 auto}",
      ".ta-ampm button{font:inherit;font-size:10.5px;font-weight:800;",
      "letter-spacing:.03em;padding:0 8px;border:0;cursor:pointer;",
      "background:var(--color-bg,#f9fafb);color:var(--color-text-secondary,#6b7280)}",
      ".ta-ampm button + button{border-left:1px solid var(--color-border,#e5e7eb)}",
      ".ta-ampm button.on{background:#4338ca;color:#fff}",
      /* Dimmed when the typed text already settles it — clicking would do
         nothing, and a control that does nothing should look like it. */
      ".ta-ampm button.moot{opacity:.4}",
      ".ta-preview{display:block;margin-top:4px;font-size:11px;font-weight:700;",
      "color:#4338ca;min-height:14px;font-variant-numeric:tabular-nums}",
      "[data-ta-new-at]{flex:0 0 78px}",
      "[data-ta-new-text]{flex:1 1 140px}",
      "[data-ta-new-at][aria-invalid]{border-color:#b91c1c}",
      ".ta-add button{flex:0 0 auto;font:inherit;font-size:12px;",
      "font-weight:700;padding:5px 12px;border-radius:8px;border:0;",
      "background:#4338ca;color:#fff;cursor:pointer}",
      ".ta-hint{display:block;margin-top:5px;font-size:10.5px;line-height:1.45;",
      "color:var(--color-text-secondary,#6b7280)}",
      ".ta-hint code{font-size:10px;padding:1px 3px;border-radius:3px;",
      "background:var(--color-bg,#f3f4f6)}",
      ".ta-saved{float:right;font-size:11px;font-weight:800;color:#047857;",
      "background:color-mix(in srgb,#047857 14%,transparent);",
      "border:1px solid color-mix(in srgb,#047857 35%,transparent);",
      "border-radius:999px;padding:2px 8px;line-height:1.5;",
      "opacity:0;transform:translateY(-2px);transition:opacity .12s,transform .12s}",
      ".ta-saved.show{opacity:1;transform:none}",
      ".ta-auto{margin:10px 0 0 !important;font-size:10.5px !important;",
      "line-height:1.45;font-style:italic}",
      ".ta-now{margin:6px 0 0 !important;font-size:11px !important;",
      "line-height:1.45;font-weight:700;",
      "color:var(--color-text,#111827) !important}",
    ].join("");
    var el = document.createElement("style");
    el.id = "ta-style";
    el.textContent = css;
    document.head.appendChild(el);
  }

  var btn = null, pop = null, backdrop = null;

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
    var lbl = pop.querySelector("[data-ta-label]");
    if (lbl && document.activeElement !== lbl) lbl.value = state.label;
    var sEl = pop.querySelector("[data-ta-new-start]");
    if (sEl && !sEl.value) sEl.value = todayYMD();
    paintDayChips();
    paintMer();
    paintAtEcho();

    /* WHAT IS CURRENTLY SAVED, in words. Read back from the same state the
       announcer schedules from, so if this line is wrong the feature is
       wrong — it cannot drift into reassuring you about a setting that is
       not the one in effect. */
    var nowEl = pop.querySelector("[data-ta-now]");
    if (nowEl) {
      var what = scheduleWords();
      if (state.label) what += " \u2014 saying \u201c" + state.label + "\u201d first";
      nowEl.textContent = (state.mode === "on" ? "Saved & running: "
                           : state.mode === "paused" ? "Saved, paused: "
                           : "Saved, stopped: ") + what;
    }

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

  /* AUTOSAVE, SAID OUT LOUD.
     There is no Save button and there should not be — this writes to
     localStorage, and a setting that needs saving is a setting people forget
     to save. But silent persistence is indistinguishable from no persistence,
     which is exactly the doubt it caused. So it now says "Saved" for a beat
     after every keystroke settles. */
  var savedTimer = null;
  function savedFlash() {
    var el = pop && pop.querySelector("[data-ta-saved]");
    if (!el) return;
    el.textContent = "\u2713 Saved";
    el.classList.add("show");
    if (savedTimer) clearTimeout(savedTimer);
    // Long enough to notice and read. The first version held it 1.4s at
    // 10.5px, which is the same as not showing it.
    savedTimer = setTimeout(function () { el.classList.remove("show"); }, 2600);
  }

  function paintAtEcho() {
    if (!pop) return;
    var ul = pop.querySelector("[data-ta-list]");
    if (!ul) return;
    if (!state.items.length) {
      ul.innerHTML = '<li class="ta-empty">Nothing scheduled yet. Add one ' +
                     'below &mdash; 5.00, 5:00 and 5am all mean five in the ' +
                     'morning; use 5pm or 17:00 for the evening.</li>';
      return;
    }
    var today = todayYMD();
    var rows = state.items.slice().sort(function (a, b) {
      return (a.date || "") === (b.date || "")
        ? a.at.localeCompare(b.at)
        : (a.date || "0").localeCompare(b.date || "0");
    });
    ul.innerHTML = rows.map(function (it) {
      // EXPIRED IS SHOWN, NOT HIDDEN. A one-off whose day has passed will
      // never speak again, and silently keeping it in the list looks like a
      // setting that is still armed.
      var expired = isExpired(it, today);
      var when = expired ? "finished \u00b7 " + repeatWords(it)
                         : repeatWords(it);
      return '<li class="ta-item' + (it.on ? "" : " off") +
             (expired ? " expired" : "") + '" data-id="' + esc(it.id) + '">' +
             '<button type="button" class="ta-tog" data-ta-toggle ' +
               'aria-pressed="' + (it.on ? "true" : "false") + '" ' +
               'title="' + (it.on ? "Stop this one" : "Start this one") + '">' +
               (it.on ? "\u25CF" : "\u25CB") + '</button>' +
             '<span class="ta-when"><b>' + esc(timeWords(it)) + '</b>' +
               '<i>' + esc(when) + '</i></span>' +
             '<span class="ta-what">' + esc(it.text || "(just the time)") +
             '</span>' +
             '<button type="button" class="ta-del" data-ta-del ' +
               'title="Delete">&times;</button>' +
             '</li>';
    }).join("");
  }

  //: Days selected in the ADD form, before the announcement exists.
  var newDays = [];
  //: AM/PM chosen for each time field in the ADD form. Defaults to morning,
  //: which is what a bare "5" nearly always means when someone is setting a
  //: wake-up or a start-of-day reminder.
  var newMer = { at: "am", until: "am" };

  /* Is the chooser actually deciding anything for this text? It is not, when
     the text already carries am/pm or is unambiguously 24-hour. Shown by
     dimming the buttons, so nobody wonders why clicking them does nothing. */
  function merApplies(text) {
    var t = String(text || "").trim().toLowerCase();
    if (!t) return true;
    if (/(am|pm)/.test(t)) return false;
    var m = /^(\d{1,2})/.exec(t.replace(/[.\-]/, ":"));
    if (!m) return true;
    var h = parseInt(m[1], 10);
    return h >= 1 && h <= 12;
  }

  function paintMer() {
    if (!pop) return;
    ["at", "until"].forEach(function (which) {
      var input = pop.querySelector(which === "at"
        ? "[data-ta-new-at]" : "[data-ta-new-until]");
      var live = merApplies(input && input.value);
      pop.querySelectorAll('[data-ta-mer="' + which + '"]').forEach(function (b) {
        var on = b.getAttribute("data-v") === newMer[which];
        b.classList.toggle("on", on && live);
        b.classList.toggle("moot", !live);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
    paintPreview();
  }

  /* The whole point of the chooser is that nothing is left to guess, so the
     resolved time is shown as it is typed rather than after adding. */
  function paintPreview() {
    var el = pop && pop.querySelector("[data-ta-preview]");
    if (!el) return;
    var atEl = pop.querySelector("[data-ta-new-at]");
    var uEl = pop.querySelector("[data-ta-new-until]");
    var mEl = pop.querySelector("[data-ta-new-mins]");
    var a = parseTimes(atEl && atEl.value, newMer.at);
    if (!a.length) { el.textContent = ""; return; }
    var txt = "\u2192 " + a.map(friendly).join(", ");
    var u = parseTimes(uEl && uEl.value, newMer.until);
    var step = parseInt(mEl && mEl.value, 10);
    if (u.length) {
      txt += " until " + friendly(u[0]);
      if (step > 0) {
        var n = TA_countSlots(a[0], u[0], step);
        txt += ", every " + step + " min" +
               (n ? " \u00b7 " + n + " time" + (n === 1 ? "" : "s") + " a day" : "");
      }
    }
    el.textContent = txt;
  }

  function TA_countSlots(from, to, step) {
    var f = hhmmToMins(from), t = hhmmToMins(to);
    if (f === null || t === null || t < f || !(step > 0)) return 0;
    return Math.floor((t - f) / step) + 1;
  }

  function paintDayChips() {
    if (!pop) return;
    var wrap = pop.querySelector("[data-ta-days]");
    var sel = pop.querySelector("[data-ta-new-repeat]");
    if (!wrap || !sel) return;
    wrap.hidden = sel.value !== "custom";
    wrap.querySelectorAll("[data-ta-day]").forEach(function (b) {
      var d = parseInt(b.getAttribute("data-ta-day"), 10);
      b.classList.toggle("on", newDays.indexOf(d) !== -1);
      b.setAttribute("aria-pressed", newDays.indexOf(d) !== -1 ? "true" : "false");
    });
  }

  function byId(id) {
    for (var i = 0; i < state.items.length; i++) {
      if (state.items[i].id === id) return state.items[i];
    }
    return null;
  }

  function addItem() {
    var atEl = pop.querySelector("[data-ta-new-at]");
    var uEl = pop.querySelector("[data-ta-new-until]");
    var mEl = pop.querySelector("[data-ta-new-mins]");
    var rEl = pop.querySelector("[data-ta-new-repeat]");
    var sEl = pop.querySelector("[data-ta-new-start]");
    var eEl = pop.querySelector("[data-ta-new-end]");
    var tEl = pop.querySelector("[data-ta-new-text]");
    // Reuse the forgiving parser, so "5.00" and "6.45pm" work here too.
    var times = parseTimes(atEl.value, newMer.at);
    if (!times.length) {
      atEl.setAttribute("aria-invalid", "true");
      atEl.focus();
      note(false, "I could not read \u201c" + atEl.value + "\u201d as a time");
      return;
    }
    atEl.removeAttribute("aria-invalid");

    // The daily window. Same forgiving parser, so "8pm" works here too.
    var until = null;
    if ((uEl.value || "").trim()) {
      var u = parseTimes(uEl.value, newMer.until);
      if (!u.length) {
        uEl.setAttribute("aria-invalid", "true");
        note(false, "I could not read \u201c" + uEl.value + "\u201d as a time");
        return;
      }
      until = u[0];
      if (hhmmToMins(until) < hhmmToMins(times[0])) {
        uEl.setAttribute("aria-invalid", "true");
        note(false, "the end time is before the start time");
        return;
      }
    }
    uEl.removeAttribute("aria-invalid");

    var stepMins = parseInt(mEl.value, 10);
    stepMins = stepMins > 0 ? Math.min(720, stepMins) : 0;
    // A window with no interval would speak once and ignore the window, and
    // an interval with no window would run to midnight. Neither is what
    // anyone means, so ask rather than guess.
    if (until && !stepMins) {
      note(false, "add how often to repeat between those times");
      return;
    }
    if (stepMins && !until) {
      note(false, "add a time to repeat until");
      return;
    }

    var repeat = REPEATS.indexOf(rEl.value) === -1 ? "daily" : rEl.value;
    var start = isYMD(sEl.value) ? sEl.value : todayYMD();
    var end = isYMD(eEl.value) ? eEl.value : null;
    // AN END BEFORE THE START would never fire, so refuse it rather than
    // creating a row that looks armed and is not.
    if (end && end < start) {
      eEl.setAttribute("aria-invalid", "true");
      note(false, "the end date is before the start date");
      return;
    }
    eEl.removeAttribute("aria-invalid");
    // "Chosen days" with nothing chosen is the same trap.
    if (repeat === "custom" && !newDays.length) {
      note(false, "pick at least one day");
      return;
    }
    var text = (tEl.value || "").slice(0, 120);
    // A field accepting several times adds several announcements rather than
    // quietly keeping the first — the parser already returns a list.
    times.forEach(function (t) {
      state.items.push({
        id: newId(), at: t, until: until, mins: stepMins,
        repeat: repeat, days: newDays.slice(),
        start: start, end: end, text: text, on: true,
      });
    });
    atEl.value = ""; uEl.value = ""; mEl.value = ""; tEl.value = "";
    newMer = { at: "am", until: "am" };
    state.lastSlot = null;
    save(); paint(); savedFlash();
    atEl.focus();
  }

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;",
               '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function buildPop() {
    backdrop = document.createElement("div");
    backdrop.className = "ta-backdrop";
    backdrop.hidden = true;
    document.body.appendChild(backdrop);

    pop = document.createElement("div");
    pop.className = "ta-pop";
    pop.hidden = true;
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-modal", "true");
    pop.setAttribute("aria-label", "Announce the time");
    pop.innerHTML =
      '<button type="button" class="ta-x" data-ta-close ' +
        'aria-label="Close">&times;</button>' +
      '<h4>Announce the time <span class="ta-saved" data-ta-saved></span></h4>' +
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
        '<label>Say this first (with every interval announcement)' +
        '<input type="text" maxlength="60" data-ta-label ' +
        'placeholder="e.g. Stand up and stretch"></label>' +
      '</div>' +
      '<div class="ta-sec">Your announcements</div>' +
      '<ul class="ta-list" data-ta-list></ul>' +
      '<div class="ta-add">' +
        '<div class="ta-add-row">' +
          '<span class="ta-timefld">' +
            '<input type="text" data-ta-new-at placeholder="5.00" ' +
              'aria-label="Start time">' +
            '<span class="ta-ampm" role="group" aria-label="Morning or afternoon">' +
              '<button type="button" data-ta-mer="at" data-v="am">AM</button>' +
              '<button type="button" data-ta-mer="at" data-v="pm">PM</button>' +
            '</span>' +
          '</span>' +
          '<select data-ta-new-repeat aria-label="How often">' +
            '<option value="daily">Every day</option>' +
            '<option value="once">Once</option>' +
            '<option value="weekly">Every week</option>' +
            '<option value="monthly">Every month</option>' +
            '<option value="yearly">Every year</option>' +
            '<option value="custom">Chosen days</option>' +
          '</select>' +
        '</div>' +
        '<small class="ta-preview" data-ta-preview></small>' +
        '<div class="ta-days" data-ta-days hidden>' +
          [0, 1, 2, 3, 4, 5, 6].map(function (d) {
            return '<button type="button" data-ta-day="' + d + '">' +
                   DAY_NAMES[d] + '</button>';
          }).join("") +
        '</div>' +
        '<div class="ta-add-row">' +
          '<label class="ta-dt">Until <i>optional</i>' +
            '<span class="ta-timefld">' +
              '<input type="text" data-ta-new-until placeholder="8.00">' +
              '<span class="ta-ampm" role="group" aria-label="Morning or afternoon">' +
                '<button type="button" data-ta-mer="until" data-v="am">AM</button>' +
                '<button type="button" data-ta-mer="until" data-v="pm">PM</button>' +
              '</span>' +
            '</span></label>' +
          '<label class="ta-dt">Repeat every <i>optional</i>' +
            '<input type="number" min="0" max="720" step="5" ' +
            'data-ta-new-mins placeholder="60 min"></label>' +
        '</div>' +
        '<div class="ta-add-row">' +
          '<label class="ta-dt">Starts' +
            '<input type="date" data-ta-new-start></label>' +
          '<label class="ta-dt">Ends <i>optional</i>' +
            '<input type="date" data-ta-new-end></label>' +
        '</div>' +
        '<div class="ta-add-row">' +
          '<input type="text" data-ta-new-text maxlength="120" ' +
            'placeholder="What to say" aria-label="What to say">' +
          '<button type="button" data-ta-add>Add</button>' +
        '</div>' +
      '</div>' +
      '<small class="ta-hint">Type the time and pick <b>AM</b> or <b>PM</b>. ' +
      'If you write it in full &mdash; <code>5pm</code> or <code>17:00</code> ' +
      '&mdash; what you typed wins and the buttons grey out. ' +
      '<b>Until</b> and <b>repeat every</b> make one ' +
      'announcement speak through the day &mdash; 8am to 8pm every 60 minutes ' +
      'is one row, not thirteen. Leave them blank and it speaks once. ' +
      '<b>Starts</b> defaults to today; leave <b>Ends</b> blank and it runs ' +
      'for good. A monthly reminder on the 31st still fires on the last day ' +
      'of a short month rather than skipping it.</small>' +
      '<p class="ta-auto">Everything here saves as you type &mdash; there is no ' +
      'Save button, and closing this panel keeps your settings.</p>' +
      '<p class="ta-now" data-ta-now></p>' +
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
      // Anything handled in here is by definition an inside click. Saying so
      // explicitly means the outside-click handler above never has to reason
      // about a node this function may be about to remove.
      if (ev.target.closest("button, input, label")) ev.stopPropagation();

      if (ev.target.closest("[data-ta-close]")) { closePanel(); return; }
      var m = ev.target.closest("[data-ta-mode]");
      if (m) {
        state.mode = m.getAttribute("data-ta-mode");
        // Starting IS the gesture, so speak a confirmation — it also proves
        // to the user that sound works before they walk away from the desk.
        if (state.mode === "on") { armed = true; speak(phrase(new Date())); }
        applyMode();
        savedFlash();
        return;
      }
      var k = ev.target.closest("[data-ta-keep]");
      if (k) {
        state.keepalive = !!k.checked;
        applyKeepalive();
        save();
        paint();
        savedFlash();
        return;
      }
      var e = ev.target.closest("[data-ta-every]");
      if (e) {
        state.every = parseInt(e.getAttribute("data-ta-every"), 10) || 15;
        state.lastSlot = null;
        applyMode();
        savedFlash();
        return;
      }
      if (ev.target.closest("[data-ta-custom]")) {
        var row = pop.querySelector("[data-ta-customrow]");
        if (row) row.hidden = false;
        var inp = pop.querySelector("[data-ta-every-in]");
        if (inp) { inp.value = state.every; inp.focus(); inp.select(); }
        return;
      }
      var tog = ev.target.closest("[data-ta-toggle]");
      if (tog) {
        var li = tog.closest("[data-id]");
        var it = byId(li && li.getAttribute("data-id"));
        if (it) { it.on = !it.on; save(); paint(); savedFlash(); }
        return;
      }
      var del = ev.target.closest("[data-ta-del]");
      if (del) {
        var li2 = del.closest("[data-id]");
        var id = li2 && li2.getAttribute("data-id");
        state.items = state.items.filter(function (x) { return x.id !== id; });
        delete state.said[id];
        save(); paint(); savedFlash();
        return;
      }
      var mer = ev.target.closest("[data-ta-mer]");
      if (mer) {
        newMer[mer.getAttribute("data-ta-mer")] = mer.getAttribute("data-v");
        paintMer();
        return;
      }
      var day = ev.target.closest("[data-ta-day]");
      if (day) {
        var d = parseInt(day.getAttribute("data-ta-day"), 10);
        var at = newDays.indexOf(d);
        if (at === -1) newDays.push(d); else newDays.splice(at, 1);
        paintDayChips();
        return;
      }
      if (ev.target.closest("[data-ta-add]")) { addItem(); return; }
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
    pop.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter") return;
      if (ev.target.closest("[data-ta-new-at],[data-ta-new-date],[data-ta-new-text]")) {
        ev.preventDefault();
        addItem();
      }
    });

    pop.addEventListener("change", function (ev) {
      if (ev.target.matches("[data-ta-new-repeat]")) paintDayChips();
    });

    pop.addEventListener("input", function (ev) {
      var n = ev.target;
      if (n.matches("[data-ta-new-at],[data-ta-new-until],[data-ta-new-mins]")) {
        paintMer();
        return;
      }
      if (n.matches("[data-ta-every-in],[data-ta-label]")) savedFlash();
      if (n.matches("[data-ta-every-in]")) {
        var v = parseInt(n.value, 10);
        if (!(v >= 0)) return;
        state.every = Math.min(MAX_EVERY, v);
        state.lastSlot = null;
        save();
        paint();
        return;
      }
      if (n.matches("[data-ta-label]")) {
        state.label = n.value.slice(0, 60);
        save();
      }
    });
  }

  /* A modal is CENTRED, so there is no anchoring arithmetic left — the old
     place() positioned it under the button, which is a popover's job. */
  function openPanel() {
    backdrop.hidden = false;
    pop.hidden = false;
    document.documentElement.classList.add("ta-locked");
    paint();
    // Focus goes into the dialog, not left on the button behind it.
    var first = pop.querySelector("[data-ta-new-at]");
    if (first) { try { first.focus(); } catch (e) {} }
  }

  function closePanel() {
    pop.hidden = true;
    backdrop.hidden = true;
    document.documentElement.classList.remove("ta-locked");
    if (btn) { try { btn.focus(); } catch (e) {} }
  }

  /* Tab must not escape into the page underneath. Small enough to do by
     hand: wrap from the last focusable element back to the first. */
  function trapTab(ev) {
    if (ev.key !== "Tab" || pop.hidden) return;
    var f = pop.querySelectorAll(
      'button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
    f = Array.prototype.filter.call(f, function (el) {
      return !el.disabled && el.offsetParent !== null;
    });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (ev.shiftKey && document.activeElement === first) {
      ev.preventDefault(); last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault(); first.focus();
    }
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
      if (pop.hidden) openPanel(); else closePanel();
    });
    /* IT IS A MODAL, so nothing outside it closes it.
       The previous popover shut on any click that was not inside it, which
       meant a DRAG — selecting a time, dragging a number field — ended
       outside and registered as a click, closing the panel mid-edit. There
       is real editing in here now: several fields, a day picker and a list.
       That is a dialog, not a popover.

       (The detached-node guard that used to be needed here is gone with the
       listener itself; deleting a row can no longer reach anything that
       would close the panel.) */
    backdrop.addEventListener("mousedown", function (ev) {
      // Only a deliberate press ON the backdrop, not a drag that happens to
      // finish there. Kept as a convenience; the × and Escape are the real
      // ways out.
      if (ev.target === backdrop) closePanel();
    });

    // Escape closes it, which is what every panel should do and what people
    // try first.
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !pop.hidden) closePanel();
      trapTab(ev);
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
    _dueItems: dueItems,
    _matchesOn: matchesOn,
    _slotsFor: slotsFor,
    _timeWords: timeWords,
    _repeatWords: repeatWords,
    _isExpired: isExpired,
    _todayYMD: todayYMD,
    _parseTimes: parseTimes,
    _merApplies: merApplies,
    _load: load,
    _friendly: friendly,
    _scheduleWords: scheduleWords,
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

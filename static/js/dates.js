/* ═══════════════════════════════════════════════════════════════════════
   DATES — the plain-language layer

   Several pages hold an ISO date and need to say something human about
   it: the Roadmap ("3 days late"), Sprints ("day 6 of 14", "ends
   Friday"), the goal countdowns. They were each doing their own version,
   or more often printing the raw 2026-10-04 and leaving the reader to
   work out whether that was behind them or ahead.

   Two rules this module exists to keep:

   1. TODAY IS THE USER'S TODAY. The app stores a timezone per user and
      _top_nav.html publishes it as window.USER_TZ. A planner that calls
      yesterday "today" is worse than one that says nothing at all.
   2. ARITHMETIC HAPPENS IN UTC. Adding a day to a local Date lands on
      the same clock time, which across a daylight-saving boundary is the
      previous or next calendar day. Every helper below converts to a UTC
      midnight first, so "+7 days" is always seven calendar days.

   Everything takes and returns YYYY-MM-DD strings, which is also what
   the APIs want, so nothing has to be reformatted on the way out.
   ═══════════════════════════════════════════════════════════════════════ */

(function (global) {
  "use strict";

  function timezone() {
    if (global.USER_TZ) return global.USER_TZ;
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; }
    catch { return "UTC"; }
  }

  /** Today in the user's timezone, as YYYY-MM-DD. */
  function todayISO() {
    try {
      // en-CA is the one common locale that formats as YYYY-MM-DD.
      return new Intl.DateTimeFormat("en-CA", {
        timeZone: timezone(),
        year: "numeric", month: "2-digit", day: "2-digit",
      }).format(new Date());
    } catch {
      return new Date().toISOString().slice(0, 10);
    }
  }

  /** UTC-midnight epoch for a YYYY-MM-DD, so arithmetic cannot drift. */
  function stamp(iso) {
    const [y, m, d] = String(iso).split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  }

  function addDays(iso, n) {
    const dt = new Date(stamp(iso));
    dt.setUTCDate(dt.getUTCDate() + n);
    return dt.toISOString().slice(0, 10);
  }

  /** Whole days from `a` to `b`. Negative means `b` is in the past. */
  function daysBetween(a, b) {
    return Math.round((stamp(b) - stamp(a)) / 86400000);
  }

  /** "Mon, 4 Oct" */
  function humanDay(iso) {
    return new Date(stamp(iso)).toLocaleDateString(undefined, {
      weekday: "short", day: "numeric", month: "short", timeZone: "UTC",
    });
  }

  /** "4 Oct" — for a pair of dates where the weekday is noise. */
  function shortDay(iso) {
    return new Date(stamp(iso)).toLocaleDateString(undefined, {
      day: "numeric", month: "short", timeZone: "UTC",
    });
  }

  /**
   * The relative phrase a person would use.
   * Coarsens with distance on purpose: "in 97 days" is a number you have
   * to convert, "in 3 months" is one you can act on.
   */
  function relativeDay(iso, today) {
    today = today || todayISO();
    const n = daysBetween(today, iso);
    if (n === 0) return "Today";
    if (n === 1) return "Tomorrow";
    if (n === -1) return "Yesterday";
    if (n < 0) {
      const k = -n;
      if (k < 14) return k + " days late";
      if (k < 60) return Math.round(k / 7) + " weeks late";
      return Math.round(k / 30) + " months late";
    }
    if (n < 14) return "in " + n + " days";
    if (n < 60) return "in " + Math.round(n / 7) + " weeks";
    return "in " + Math.round(n / 30) + " months";
  }

  /** The next Monday, always strictly in the future (7 days on a Monday). */
  function nextMonday(today) {
    today = today || todayISO();
    const dow = new Date(stamp(today)).getUTCDay();   // Sun 0 … Sat 6
    return addDays(today, ((8 - dow) % 7) || 7);
  }

  /**
   * Where today sits inside a dated span, for a sprint or a goal.
   *
   * Returns null when there are not two dates to measure between —
   * callers must handle that rather than render "day NaN of NaN", which
   * is what a half-dated sprint used to produce.
   *
   * `day` is 1-based and inclusive, so a sprint that starts today is
   * "day 1 of N", and it clamps to the span: a sprint whose end has
   * passed reads "day N of N" rather than day 19 of 14.
   */
  function progressThrough(startISO, endISO, today) {
    if (!startISO || !endISO) return null;
    today = today || todayISO();
    const total = daysBetween(startISO, endISO) + 1;   // inclusive of both ends
    if (total <= 0) return null;
    const raw = daysBetween(startISO, today) + 1;
    const day = Math.min(Math.max(raw, 0), total);
    return {
      total: total,
      day: day,
      /** 0–100, for a bar. */
      pct: Math.round((day / total) * 100),
      elapsed: raw > total,
      notStarted: raw < 1,
      remaining: Math.max(total - day, 0),
    };
  }

  global.DPDates = {
    timezone: timezone,
    todayISO: todayISO,
    addDays: addDays,
    daysBetween: daysBetween,
    humanDay: humanDay,
    shortDay: shortDay,
    relativeDay: relativeDay,
    nextMonday: nextMonday,
    progressThrough: progressThrough,
  };

  // So the test harness can require() it under node as well as the browser.
  if (typeof module !== "undefined" && module.exports) module.exports = global.DPDates;
})(typeof window !== "undefined" ? window : globalThis);

/* ════════════════════════════════════════════════════════════════
   DAILYPLANNER — "SADHANA": GAMIFIED INTERVIEW PREP

   A singing-themed progression layer over the prep banks. You earn
   NOTES (the XP) by studying topics, clocking Pomodoro focus time and
   answering quiz questions, and you climb the scale:

       Sa Re Ga Ma Pa Dha Ni   x 3 octaves (saptak) = 21 levels
       Mandra saptak  (low)    - Warming up
       Madhya saptak  (middle) - Finding your voice
       Taar saptak    (high)   - Centre stage
       then: Maestro

   Every level-up PLAYS the swara you just reached, so the progression
   is audible, not just a number going up.

   Usage from a page:
       Gamify.mount(document.getElementById("gamebar"));
       Gamify.studied(id, minutes, {difficulty, priority});   // once per id
       Gamify.studiedBulk([{id, minutes}, ...]);              // silent backfill
       Gamify.syncMinutes("ai_sde", minutesClockedSoFar);     // awards the delta
       Gamify.quiz({correct: 21, total: 25, mode: "mixed"});

   All state is localStorage (key dp-sadhana-v1), matching how the prep
   pages already store progress.
   ════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  if (window.Gamify) return;

  var KEY = "dp-sadhana-v1";
  var OLD_KEY = "dp-riyaaz-v1";        // pre-rename; migrated on first load

  /* ── the scale ───────────────────────────────────────────────────
     Seven swaras, three octaves. The frequencies are the equal-tempered
     C major scale so the level-up chime is an actual musical note:
     Sa=C, Re=D, Ga=E, Ma=F, Pa=G, Dha=A, Ni=B. */
  var SWARAS = [
    { s: "Sa",  full: "Shadja",  hz: 261.63 },
    { s: "Re",  full: "Rishabh", hz: 293.66 },
    { s: "Ga",  full: "Gandhar", hz: 329.63 },
    { s: "Ma",  full: "Madhyam", hz: 349.23 },
    { s: "Pa",  full: "Pancham", hz: 392.00 },
    { s: "Dha", full: "Dhaivat", hz: 440.00 },
    { s: "Ni",  full: "Nishad",  hz: 493.88 }
  ];
  var OCTAVES = [
    { key: "mandra", label: "Mandra saptak", title: "Warming up",          mult: 0.5 },
    { key: "madhya", label: "Madhya saptak", title: "Finding your voice",  mult: 1.0 },
    { key: "taar",   label: "Taar saptak",   title: "Centre stage",        mult: 2.0 }
  ];
  var MAX_LEVEL = 22;                       // 21 swaras + Maestro

  /* Notes needed to REACH a level. Level 1 is free; the top lands near
     24,000 - about the whole bank studied once, so finishing the prep
     and finishing the game are the same journey. */
  function xpForLevel(level) {
    if (level <= 1) return 0;
    var n = level - 1;
    return 50 * n * n + 50 * n;             // L2=100, L10=4950, L22=23100
  }

  function levelInfo(level) {
    if (level >= MAX_LEVEL) {
      return { level: MAX_LEVEL, swara: "Sa", full: "Maestro", octave: OCTAVES[2],
               title: "Maestro", hz: 523.25 * 2, isMax: true };
    }
    var i = level - 1;                      // 0-based across all 21 swaras
    var oct = OCTAVES[Math.floor(i / 7)];
    var sw = SWARAS[i % 7];
    return { level: level, swara: sw.s, full: sw.full, octave: oct,
             title: oct.title, hz: sw.hz * oct.mult, isMax: false };
  }

  function levelFromXp(xp) {
    var lvl = 1;
    while (lvl < MAX_LEVEL && xp >= xpForLevel(lvl + 1)) lvl++;
    return lvl;
  }

  /* ── badges ──────────────────────────────────────────────────────
     Each has a test(state) run after every award. Once earned, they
     stay earned - nothing here can be taken away. */
  var BADGES = [
    { id: "first-note",  icon: "🎵", name: "First Note",
      hint: "Earn your first notes",
      test: function (s) { return s.xp > 0; } },
    { id: "warm-up",     icon: "🎧", name: "Warm-Up",
      hint: "Study 10 topics",
      test: function (s) { return s.stats.topics >= 10; } },
    { id: "scales",      icon: "🎼", name: "Practising Scales",
      hint: "Study 50 topics",
      test: function (s) { return s.stats.topics >= 50; } },
    { id: "chart",       icon: "📈", name: "Chart Topper",
      hint: "Study 100 topics",
      test: function (s) { return s.stats.topics >= 100; } },
    { id: "headliner",   icon: "🌟", name: "Headliner",
      hint: "Study 500 topics",
      test: function (s) { return s.stats.topics >= 500; } },
    { id: "sadhana-3",   icon: "🔥", name: "Three Days of Sadhana",
      hint: "Practise 3 days running",
      test: function (s) { return s.streak.n >= 3; } },
    { id: "sadhana-7",   icon: "🪔", name: "In Tune",
      hint: "A 7-day sadhana streak",
      test: function (s) { return s.streak.n >= 7; } },
    { id: "sadhana-30",  icon: "👑", name: "Disciplined Voice",
      hint: "A 30-day sadhana streak",
      test: function (s) { return s.streak.n >= 30; } },
    { id: "perfect",     icon: "🎯", name: "Perfect Pitch",
      hint: "Score 100% on a quiz",
      test: function (s) { return s.stats.best >= 100; } },
    { id: "encore",      icon: "🎤", name: "Encore",
      hint: "Three focus sessions in one day",
      test: function (s) { return (s.day.sessions || 0) >= 3; } },
    { id: "marathon",    icon: "⏳", name: "Marathon Sadhana",
      hint: "Three hours clocked in one day",
      test: function (s) { return s.day.minutes >= 180; } },
    { id: "octave-up",   icon: "⬆️", name: "Octave Up",
      hint: "Reach the middle octave",
      test: function (s) { return levelFromXp(s.xp) >= 8; } },
    { id: "centre",      icon: "🎙️", name: "Centre Stage",
      hint: "Reach the high octave",
      test: function (s) { return levelFromXp(s.xp) >= 15; } },
    { id: "hard-notes",  icon: "💎", name: "Hard Notes",
      hint: "Study 25 Hard topics",
      test: function (s) { return (s.stats.hard || 0) >= 25; } },
    { id: "setlist",     icon: "📜", name: "The Setlist",
      hint: "Study 50 P0 topics",
      test: function (s) { return (s.stats.p0 || 0) >= 50; } },
    { id: "maestro",     icon: "🏆", name: "Maestro",
      hint: "Reach the top of the scale",
      test: function (s) { return levelFromXp(s.xp) >= MAX_LEVEL; } }
  ];

  /* Today's sadhana: three small targets. Hitting all three pays a bonus
     and is what the ring in the widget fills up. */
  var GOAL = { minutes: 25, topics: 3, quizzes: 1 };
  var GOAL_BONUS = 50;

  /* ── state ───────────────────────────────────────────────────────── */
  function today() { return new Date().toISOString().slice(0, 10); }
  function yesterday() { return new Date(Date.now() - 86400000).toISOString().slice(0, 10); }

  function blank() {
    return {
      v: 1, xp: 0,
      badges: {},                       // id -> ISO date earned
      streak: { n: 0, last: "" },
      day: { d: today(), xp: 0, minutes: 0, topics: 0, quizzes: 0, sessions: 0, bonus: false },
      topics: {},                       // awarded topic ids (never re-award)
      mins: {},                         // pomodoro namespace -> minutes already counted
      stats: { topics: 0, minutes: 0, quizzes: 0, correct: 0, answered: 0, best: 0, hard: 0, p0: 0 }
    };
  }

  var state = load();

  function load() {
    var s;
    try { s = JSON.parse(localStorage.getItem(KEY)); } catch (_) { s = null; }
    /* This was called "riyaaz" when it shipped. Carry that progress over
       rather than resetting anyone who had already started climbing. */
    if (!s) {
      try {
        var old = JSON.parse(localStorage.getItem(OLD_KEY));
        if (old && old.v === 1) {
          s = old;
          if (s.badges) {                       // the streak badge ids moved too
            ["3", "7", "30"].forEach(function (n) {
              if (s.badges["riyaaz-" + n] && !s.badges["sadhana-" + n]) {
                s.badges["sadhana-" + n] = s.badges["riyaaz-" + n];
                delete s.badges["riyaaz-" + n];
              }
            });
          }
          localStorage.setItem(KEY, JSON.stringify(s));
          localStorage.removeItem(OLD_KEY);
        }
      } catch (_) {}
    }
    if (!s || s.v !== 1) s = blank();
    var b = blank();
    /* Defensive merge: a half-written or older record must not throw. */
    s.badges = s.badges || {};
    s.streak = s.streak || b.streak;
    s.day = s.day || b.day;
    s.topics = s.topics || {};
    s.mins = s.mins || {};
    s.stats = Object.assign(b.stats, s.stats || {});
    if (s.day.d !== today()) s.day = b.day;    // a new day resets the goal
    return s;
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {}
  }

  /* ── sound ───────────────────────────────────────────────────────
     A short plucked note. Used for level-ups (the swara you reached)
     and, quietly, for badges. No-ops where WebAudio is blocked. */
  function playNote(hz, when, dur, vol) {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      if (!playNote._ctx) playNote._ctx = new Ctx();
      var ctx = playNote._ctx;
      if (ctx.state === "suspended" && ctx.resume) ctx.resume();
      var t = ctx.currentTime + (when || 0);
      var osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.value = hz;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(vol || 0.25, t + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.6));
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(t); osc.stop(t + (dur || 0.6) + 0.05);
    } catch (_) {}
  }

  /* The run up the scale you hear when you level up: the three swaras
     ending on the one you just reached. */
  function playLevelUp(level) {
    var info = levelInfo(level);
    var idx = (level - 1) % 7;
    var oct = OCTAVES[Math.min(2, Math.floor((level - 1) / 7))];
    for (var back = 2; back >= 1; back--) {
      var j = idx - back;
      if (j >= 0) playNote(SWARAS[j].hz * oct.mult, (2 - back) * 0.12, 0.25, 0.13);
    }
    playNote(info.hz, 0.26, 0.9, 0.28);
  }

  function say(msg, kind) {
    if (window.toast) { try { window.toast(msg, kind || "success"); } catch (_) {} }
  }

  /* ── awarding ────────────────────────────────────────────────────── */
  function rollDay() {
    if (state.day.d !== today()) {
      state.day = { d: today(), xp: 0, minutes: 0, topics: 0, quizzes: 0, sessions: 0, bonus: false };
    }
  }

  function bumpStreak() {
    var t = today();
    if (state.streak.last === t) return;
    state.streak.n = (state.streak.last === yesterday()) ? state.streak.n + 1 : 1;
    state.streak.last = t;
  }

  /* The single path every gain goes through: add notes, roll the day,
     keep the streak alive, check badges, check the level, repaint. */
  function award(amount, reason, opts) {
    opts = opts || {};
    amount = Math.max(0, Math.round(amount));
    rollDay();
    var before = levelFromXp(state.xp);
    if (amount > 0) {
      state.xp += amount;
      state.day.xp += amount;
      if (!opts.silent) bumpStreak();
    }
    checkGoal(opts);
    var after = levelFromXp(state.xp);
    var newBadges = checkBadges();
    save();
    render();

    if (!opts.silent) {
      if (amount > 0) pop("+" + amount + " 🎵" + (reason ? " " + reason : ""));
      if (after > before) celebrate(after);
      newBadges.forEach(function (b, i) {
        setTimeout(function () {
          say(b.icon + "  Badge unlocked - " + b.name, "success");
          playNote(659.25, 0, 0.5, 0.18);
        }, 900 + i * 1200);
      });
    }
    emit();
    return amount;
  }

  function checkGoal(opts) {
    if (state.day.bonus) return;
    if (state.day.minutes >= GOAL.minutes && state.day.topics >= GOAL.topics
        && state.day.quizzes >= GOAL.quizzes) {
      state.day.bonus = true;
      state.xp += GOAL_BONUS;
      state.day.xp += GOAL_BONUS;
      if (!(opts && opts.silent)) {
        setTimeout(function () {
          say("🪔  Today's sadhana complete - bonus " + GOAL_BONUS + " notes", "success");
        }, 600);
      }
    }
  }

  function checkBadges() {
    var earned = [];
    BADGES.forEach(function (b) {
      if (!state.badges[b.id] && b.test(state)) {
        state.badges[b.id] = today();
        earned.push(b);
      }
    });
    return earned;
  }

  function celebrate(level) {
    var info = levelInfo(level);
    playLevelUp(level);
    say((info.isMax ? "🏆" : "🎶") + "  Level " + level + " - " + info.swara
        + (info.isMax ? "" : " (" + info.octave.label + ")") + " - " + info.title, "success");
    var host = document.querySelector(".gm");
    if (host) {
      host.classList.remove("gm-levelup");
      void host.offsetWidth;                 // restart the animation
      host.classList.add("gm-levelup");
    }
  }

  /* Small floating "+45 🎵" over the widget. */
  function pop(text) {
    var host = document.querySelector(".gm");
    if (!host) return;
    var el = document.createElement("span");
    el.className = "gm-pop";
    el.textContent = text;
    host.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 1600);
  }

  function emit() {
    try { document.dispatchEvent(new CustomEvent("gamify:change")); } catch (_) {}
  }

  /* ── styles ──────────────────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById("gm-styles")) return;
    var css = [
      ".gm { position:relative; display:flex; align-items:center; gap:10px; flex-wrap:wrap;",
      "  margin:0 0 12px; padding:9px 12px; border-radius:14px;",
      "  background:linear-gradient(135deg,#fdf4ff,#eef2ff); border:1px solid #e9d5ff; }",
      ".gm-main { display:flex; align-items:center; gap:11px; flex:1; min-width:210px;",
      "  background:none; border:0; padding:0; cursor:pointer; font:inherit; text-align:left; color:inherit; }",
      ".gm-swara { flex:none; width:44px; height:44px; border-radius:50%; display:flex; align-items:center;",
      "  justify-content:center; font-size:15px; font-weight:900; color:#fff;",
      "  background:linear-gradient(135deg,#8b5cf6,#6366f1); box-shadow:0 2px 8px rgba(99,102,241,.35); }",
      ".gm-meta { flex:1; min-width:0; }",
      ".gm-lvl { display:block; font-size:12px; font-weight:800; color:#5b21b6; letter-spacing:.01em; }",
      ".gm-sub { display:block; font-size:10.5px; font-weight:700; color:#7c3aed; opacity:.8; }",
      ".gm-bar { display:block; height:7px; margin-top:4px; border-radius:999px; background:#ede9fe; overflow:hidden; }",
      ".gm-bar > i { display:block; height:100%; border-radius:999px;",
      "  background:linear-gradient(90deg,#a78bfa,#6366f1); transition:width .5s ease; }",
      ".gm-chip { font-size:11.5px; font-weight:800; color:#5b21b6; background:#fff; border:1px solid #e9d5ff;",
      "  border-radius:999px; padding:4px 10px; white-space:nowrap; cursor:pointer; }",
      ".gm-chip.on { background:#6d28d9; color:#fff; border-color:#6d28d9; }",
      ".gm-pop { position:absolute; right:14px; top:4px; font-size:12.5px; font-weight:900; color:#6d28d9;",
      "  pointer-events:none; animation:gmPop 1.6s ease-out forwards; }",
      "@keyframes gmPop { 0%{opacity:0;transform:translateY(6px)} 15%{opacity:1}",
      "  100%{opacity:0;transform:translateY(-26px)} }",
      ".gm-levelup .gm-swara { animation:gmRing 1.1s ease-out 2; }",
      "@keyframes gmRing { 0%{box-shadow:0 0 0 0 rgba(139,92,246,.6)}",
      "  100%{box-shadow:0 0 0 16px rgba(139,92,246,0)} }",

      /* the panel */
      ".gm-ov { position:fixed; inset:0; background:rgba(15,10,35,.55); z-index:9998;",
      "  display:flex; align-items:flex-start; justify-content:center; padding:22px 12px; overflow-y:auto; }",
      ".gm-panel { width:100%; max-width:560px; background:var(--color-surface,#fff); color:var(--color-text,#111);",
      "  border-radius:16px; padding:16px 16px 20px; box-shadow:0 18px 50px rgba(0,0,0,.3); }",
      ".gm-panel h3 { margin:0 0 2px; font-size:17px; font-weight:900; }",
      ".gm-panel .muted { color:var(--color-text-secondary,#666); font-size:12.5px; margin:0 0 12px; }",
      ".gm-x { float:right; background:none; border:0; font-size:20px; cursor:pointer; color:var(--color-text-secondary,#666); line-height:1; }",
      ".gm-stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(88px,1fr)); gap:8px; margin:0 0 14px; }",
      ".gm-stat { background:var(--color-bg,#f8f8fb); border:1px solid var(--color-border,#e5e7eb); border-radius:10px; padding:8px 10px; }",
      ".gm-stat b { display:block; font-size:16px; font-weight:900; }",
      ".gm-stat span { font-size:10.5px; font-weight:700; color:var(--color-text-secondary,#666); }",
      ".gm-h4 { font-size:10.5px; font-weight:900; text-transform:uppercase; letter-spacing:.05em;",
      "  color:var(--color-text-secondary,#666); margin:14px 0 7px; }",
      ".gm-scale { display:flex; flex-wrap:wrap; gap:5px; }",
      ".gm-step { flex:none; width:38px; height:38px; border-radius:10px; display:flex; flex-direction:column;",
      "  align-items:center; justify-content:center; font-size:11.5px; font-weight:800;",
      "  background:var(--color-bg,#f4f4f7); color:var(--color-text-secondary,#888); border:1px solid var(--color-border,#e5e7eb); }",
      ".gm-step.done { background:#ede9fe; color:#5b21b6; border-color:#ddd6fe; }",
      ".gm-step.now { background:linear-gradient(135deg,#8b5cf6,#6366f1); color:#fff; border-color:#6d28d9;",
      "  transform:scale(1.1); box-shadow:0 3px 10px rgba(99,102,241,.4); }",
      ".gm-step i { font-style:normal; font-size:8.5px; opacity:.75; font-weight:700; }",
      ".gm-oct { font-size:10px; font-weight:800; color:var(--color-text-secondary,#888); margin:9px 0 4px; }",
      ".gm-badges { display:grid; grid-template-columns:repeat(auto-fill,minmax(102px,1fr)); gap:7px; }",
      ".gm-badge { border:1px solid var(--color-border,#e5e7eb); border-radius:10px; padding:8px; text-align:center;",
      "  background:var(--color-bg,#f8f8fb); opacity:.42; filter:grayscale(1); }",
      ".gm-badge.got { opacity:1; filter:none; background:#faf5ff; border-color:#e9d5ff; }",
      ".gm-badge .ic { font-size:19px; display:block; }",
      ".gm-badge .nm { font-size:10.5px; font-weight:800; display:block; margin-top:2px; }",
      ".gm-badge .ht { font-size:9.5px; color:var(--color-text-secondary,#777); display:block; }",
      ".gm-goal { display:flex; gap:7px; flex-wrap:wrap; }",
      ".gm-goal .g { flex:1; min-width:96px; background:var(--color-bg,#f8f8fb); border:1px solid var(--color-border,#e5e7eb);",
      "  border-radius:10px; padding:7px 9px; font-size:11px; font-weight:700; }",
      ".gm-goal .g.hit { background:#ecfdf5; border-color:#a7f3d0; color:#047857; }",
      ".gm-goal .g b { display:block; font-size:13.5px; }",
      "@media (max-width:640px){ .gm { padding:8px 10px; gap:7px; } .gm-swara { width:38px; height:38px; font-size:13px; } }",

      /* dark: explicit class and OS-dark without an explicit light choice */
      "html.dark .gm { background:linear-gradient(135deg,#241a33,#161a33); border-color:#4c1d95; }",
      "html.dark .gm-lvl { color:#ddd6fe; } html.dark .gm-sub { color:#c4b5fd; }",
      "html.dark .gm-bar { background:#2e1065; }",
      "html.dark .gm-chip { background:#2e1065; color:#ddd6fe; border-color:#6d28d9; }",
      "html.dark .gm-pop { color:#c4b5fd; }",
      "html.dark .gm-step.done { background:#2e1065; color:#ddd6fe; border-color:#6d28d9; }",
      "html.dark .gm-badge.got { background:#2a1a3d; border-color:#6d28d9; }",
      "html.dark .gm-goal .g.hit { background:#0e2119; border-color:#10b981; color:#6ee7b7; }",
      "@media (prefers-color-scheme: dark) {",
      "  :root:not(.light) .gm { background:linear-gradient(135deg,#241a33,#161a33); border-color:#4c1d95; }",
      "  :root:not(.light) .gm-lvl { color:#ddd6fe; }",
      "  :root:not(.light) .gm-sub { color:#c4b5fd; }",
      "  :root:not(.light) .gm-bar { background:#2e1065; }",
      "  :root:not(.light) .gm-chip { background:#2e1065; color:#ddd6fe; border-color:#6d28d9; }",
      "  :root:not(.light) .gm-pop { color:#c4b5fd; }",
      "  :root:not(.light) .gm-step.done { background:#2e1065; color:#ddd6fe; border-color:#6d28d9; }",
      "  :root:not(.light) .gm-badge.got { background:#2a1a3d; border-color:#6d28d9; }",
      "  :root:not(.light) .gm-goal .g.hit { background:#0e2119; border-color:#10b981; color:#6ee7b7; }",
      "}"
    ].join("\n");
    var el = document.createElement("style");
    el.id = "gm-styles";
    el.textContent = css;
    document.head.appendChild(el);
  }

  /* ── the widget ──────────────────────────────────────────────────── */
  var host = null;

  function num(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }

  function render() {
    if (!host) return;
    var lvl = levelFromXp(state.xp);
    var info = levelInfo(lvl);
    var floor = xpForLevel(lvl), ceil = xpForLevel(lvl + 1);
    var pct = info.isMax ? 100 : Math.round((state.xp - floor) / (ceil - floor) * 100);
    var badgeCount = Object.keys(state.badges).length;
    var goalsHit = (state.day.minutes >= GOAL.minutes ? 1 : 0)
                 + (state.day.topics >= GOAL.topics ? 1 : 0)
                 + (state.day.quizzes >= GOAL.quizzes ? 1 : 0);

    host.className = "gm";
    host.innerHTML =
      '<button class="gm-main" type="button" data-gm="panel" title="Open your sadhana progress">' +
        '<span class="gm-swara">' + info.swara + '</span>' +
        '<span class="gm-meta">' +
          '<span class="gm-lvl">Level ' + lvl + ' · ' + (info.isMax ? "Maestro" : info.full + " · " + info.octave.label) + '</span>' +
          '<span class="gm-sub">' + (info.isMax
              ? num(state.xp) + " notes · top of the scale"
              : num(state.xp) + " notes · " + num(ceil - state.xp) + " to " + levelInfo(lvl + 1).swara) + '</span>' +
          '<span class="gm-bar"><i style="width:' + pct + '%"></i></span>' +
        '</span>' +
      '</button>' +
      '<span class="gm-chip' + (state.streak.n > 0 ? " on" : "") + '" data-gm="panel" ' +
        'title="Days of sadhana in a row">🔥 ' + state.streak.n + '</span>' +
      '<span class="gm-chip" data-gm="panel" title="Badges earned">🏅 ' + badgeCount + '/' + BADGES.length + '</span>' +
      '<span class="gm-chip' + (goalsHit === 3 ? " on" : "") + '" data-gm="panel" ' +
        'title="Today: ' + GOAL.minutes + ' min focus, ' + GOAL.topics + ' topics, ' + GOAL.quizzes + ' quiz">' +
        '🪔 today ' + goalsHit + '/3</span>';
  }

  function openPanel() {
    var lvl = levelFromXp(state.xp);
    var ov = document.createElement("div");
    ov.className = "gm-ov";

    var scale = "";
    OCTAVES.forEach(function (oct, oi) {
      scale += '<div class="gm-oct">' + oct.label + ' — ' + oct.title + '</div><div class="gm-scale">';
      for (var i = 0; i < 7; i++) {
        var n = oi * 7 + i + 1;
        var cls = n < lvl ? "done" : (n === lvl ? "now" : "");
        scale += '<span class="gm-step ' + cls + '" title="Level ' + n + ' · ' + num(xpForLevel(n)) + ' notes">'
              + SWARAS[i].s + '<i>' + n + '</i></span>';
      }
      scale += '</div>';
    });
    scale += '<div class="gm-oct">Beyond the scale</div><div class="gm-scale">'
          + '<span class="gm-step ' + (lvl >= MAX_LEVEL ? "now" : "") + '" title="Level 22 · '
          + num(xpForLevel(MAX_LEVEL)) + ' notes">🏆<i>22</i></span></div>';

    var badges = BADGES.map(function (b) {
      var got = !!state.badges[b.id];
      return '<div class="gm-badge' + (got ? " got" : "") + '">' +
        '<span class="ic">' + b.icon + '</span>' +
        '<span class="nm">' + b.name + '</span>' +
        '<span class="ht">' + (got ? "earned " + state.badges[b.id] : b.hint) + '</span></div>';
    }).join("");

    var acc = state.stats.answered
      ? Math.round(state.stats.correct / state.stats.answered * 100) + "%" : "—";

    ov.innerHTML =
      '<div class="gm-panel" role="dialog" aria-label="Sadhana progress">' +
        '<button class="gm-x" type="button" data-gm="close" aria-label="Close">×</button>' +
        '<h3>🎤 Your sadhana</h3>' +
        '<p class="muted">Study, clock focus time and take quizzes to earn notes and climb the scale. ' +
        'Practise every day to keep the streak alive.</p>' +
        '<div class="gm-stats">' +
          '<div class="gm-stat"><b>' + num(state.xp) + '</b><span>notes earned</span></div>' +
          '<div class="gm-stat"><b>' + state.stats.topics + '</b><span>topics studied</span></div>' +
          '<div class="gm-stat"><b>' + Math.round(state.stats.minutes / 60) + 'h</b><span>focus clocked</span></div>' +
          '<div class="gm-stat"><b>' + state.streak.n + '</b><span>day streak</span></div>' +
          '<div class="gm-stat"><b>' + acc + '</b><span>quiz accuracy</span></div>' +
          '<div class="gm-stat"><b>' + state.stats.best + '%</b><span>best quiz</span></div>' +
        '</div>' +
        '<div class="gm-h4">Today\'s sadhana</div>' +
        '<div class="gm-goal">' +
          goalBox("Focus", state.day.minutes, GOAL.minutes, "min") +
          goalBox("Topics", state.day.topics, GOAL.topics, "") +
          goalBox("Quiz", state.day.quizzes, GOAL.quizzes, "set") +
        '</div>' +
        '<div class="gm-h4">The scale</div>' + scale +
        '<div class="gm-h4">Badges</div><div class="gm-badges">' + badges + '</div>' +
      '</div>';

    ov.addEventListener("click", function (ev) {
      if (ev.target === ov || ev.target.closest('[data-gm="close"]')) ov.remove();
    });
    document.body.appendChild(ov);
  }

  function goalBox(label, have, need, unit) {
    var hit = have >= need;
    return '<div class="g' + (hit ? " hit" : "") + '"><b>' + Math.min(have, need) + ' / ' + need +
           (unit ? " " + unit : "") + '</b>' + (hit ? "✓ " : "") + label + '</div>';
  }

  /* ── public API ──────────────────────────────────────────────────── */
  window.Gamify = {
    /* Render the widget into `el` (a div you place on the page). */
    mount: function (el) {
      if (!el) return;
      injectStyles();
      host = el;
      render();
      if (!window.Gamify._bound) {
        window.Gamify._bound = true;
        document.addEventListener("click", function (ev) {
          if (ev.target.closest('[data-gm="panel"]')) { ev.preventDefault(); openPanel(); }
        });
        window.addEventListener("storage", function (ev) {
          if (ev.key === KEY) { state = load(); render(); }
        });
      }
      return this;
    },

    /* One topic marked studied. Notes = its prep_minutes (a 45-minute
       topic is worth more than a 5-minute one). Idempotent per id. */
    studied: function (id, minutes, meta) {
      if (!id || state.topics[id]) return 0;
      state.topics[id] = 1;
      state.stats.topics += 1;
      rollDay();
      state.day.topics += 1;
      meta = meta || {};
      if (meta.difficulty === "Hard") state.stats.hard += 1;
      if (meta.priority === "P0") state.stats.p0 += 1;
      return award(Math.max(5, minutes || 10), "studied", meta);
    },

    /* Silent catch-up for topics ticked before the game existed, or on
       another page. No toasts, no chain of level-up chimes. */
    studiedBulk: function (list) {
      var gained = 0;
      (list || []).forEach(function (t) {
        if (!t || !t.id || state.topics[t.id]) return;
        state.topics[t.id] = 1;
        state.stats.topics += 1;
        if (t.difficulty === "Hard") state.stats.hard += 1;
        if (t.priority === "P0") state.stats.p0 += 1;
        gained += Math.max(5, t.minutes || 10);
      });
      if (gained > 0) award(gained, "", { silent: true });
      return gained;
    },

    /* Pomodoro effort. Pass the TOTAL minutes clocked for a namespace;
       only the increase since last time is awarded, so this is safe to
       call on every pomodoro:change event. */
    syncMinutes: function (ns, totalMinutes) {
      totalMinutes = Math.floor(totalMinutes || 0);
      var seen = state.mins[ns] || 0;
      if (totalMinutes <= seen) return 0;
      var delta = totalMinutes - seen;
      state.mins[ns] = totalMinutes;
      state.stats.minutes += delta;
      rollDay();
      state.day.minutes += delta;
      /* First sight of an existing log is a backfill, not a session. */
      var silent = seen === 0 && delta > 5;
      if (!silent) state.day.sessions = (state.day.sessions || 0) + (delta >= 5 ? 1 : 0);
      return award(delta, "focus", { silent: silent });
    },

    /* A finished quiz: 10 notes per correct answer, plus completion and
       perfect-score bonuses. */
    quiz: function (r) {
      r = r || {};
      var total = r.total || 0, correct = r.correct || 0;
      if (!total) return 0;
      var pct = Math.round(correct / total * 100);
      state.stats.quizzes += 1;
      state.stats.correct += correct;
      state.stats.answered += total;
      state.stats.best = Math.max(state.stats.best, pct);
      rollDay();
      state.day.quizzes += 1;
      var notes = correct * 10 + 25 + (pct === 100 ? 150 : 0);
      return award(notes, pct === 100 ? "perfect set!" : "quiz", {});
    },

    open: function () { injectStyles(); openPanel(); },
    level: function () { return levelFromXp(state.xp); },
    levelName: function () { var i = levelInfo(levelFromXp(state.xp)); return i.isMax ? "Maestro" : i.swara; },
    xp: function () { return state.xp; },
    streak: function () { return state.streak.n; },
    state: function () { return JSON.parse(JSON.stringify(state)); },
    /* Wipe everything - only used by a deliberate "start over". */
    reset: function () { state = blank(); save(); render(); emit(); }
  };
})();

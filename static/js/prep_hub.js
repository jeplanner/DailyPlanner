/* prep_hub.js — the Interview Prep hub: tabs, the overview dashboard, and the
 * behavioural and system-design banks.
 *
 * ONE PAGE, FOUR TABS. Interview Prep and TPM Case Rounds used to be two
 * menu items, and this page alone drew 3,000+ buttons in one 29,000px scroll
 * because both banks rendered in full on load. Each tab now has its own
 * path (/interview-prep, /cases, /behavioral, /design) so links land on the
 * right one, and a bank is only fetched and drawn the first time its tab is
 * opened — then 40 cards at a time.
 *
 * REHEARSED TICKS LIVE ON THE SERVER (prep_progress), keyed by title. They
 * used to sit in localStorage keyed by position, so they never left the
 * device and drifted whenever a bank changed. The first load after the
 * migration copies the old local ticks up once.
 *
 * The case-rounds tab is prep_cases.js; it uses PrepHub from here.
 */
(function () {
  "use strict";

  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var say = function (msg, kind) { if (window.toast) window.toast(msg, kind || "info"); };

  async function api(path, opts) {
    opts = opts || {};
    var r = await fetch(path, Object.assign({
      credentials: "same-origin",
      headers: opts.body ? { "Content-Type": "application/json", "X-CSRFToken": CSRF }
                         : { "X-CSRFToken": CSRF },
    }, opts));
    var j = {};
    try { j = await r.json(); } catch (_) {}
    if (!r.ok) { var e = new Error(j.error || "Something went wrong"); e.status = r.status; throw e; }
    return j;
  }

  var hrs = function (m) {
    m = Math.round(m || 0);
    return m < 60 ? m + "m" : (m % 60 ? Math.floor(m / 60) + "h " + (m % 60) + "m" : Math.floor(m / 60) + "h");
  };

  /* The banks' long text is hard-wrapped at ~78 columns in the source, which
     reads as ragged lines in a narrow, proportional-font card. Re-flow it:
     keep paragraph breaks, bullets, numbered steps and CAPS headings on
     their own lines, and join everything else to the line before. */
  var NEW_LINE = /^(\*|-|•|\d+[.)]\s|[A-Z][A-Z0-9 /&'(),+-]{2,}(:|$)|[A-Z]+ (sounds like|THAT)\b)/;
  function reflow(text) {
    var out = [];
    String(text || "").split("\n").forEach(function (raw) {
      var line = raw.trim();
      if (!line) { out.push(""); return; }
      var prev = out.length ? out[out.length - 1] : "";
      var prevIsHead = prev && prev === prev.toUpperCase() && /[A-Z]/.test(prev) && !/[a-z]/.test(prev);
      if (!out.length || prev === "" || NEW_LINE.test(line) || prevIsHead) {
        out.push(line);
      } else {
        out[out.length - 1] = prev + " " + line;
      }
    });
    return out.join("\n").replace(/\n{3,}/g, "\n\n");
  }

  /* ── Rehearsed / practised ticks ─────────────────────────────────── */
  function makeProgress(bank, legacyKey, syncNoteEl) {
    var p = { bank: bank, done: new Set(), mock: {}, available: null };
    var readLocal = function () {
      try { return JSON.parse(localStorage.getItem(legacyKey) || "[]") || []; } catch (_) { return []; }
    };
    var writeLocal = function () {
      try { localStorage.setItem(legacyKey, JSON.stringify(Array.from(p.done))); } catch (_) {}
    };
    var note = function (msg) {
      if (!syncNoteEl) return;
      syncNoteEl.hidden = !msg;
      syncNoteEl.textContent = msg || "";
    };

    p.load = async function () {
      var local = readLocal();
      try {
        var j = await api("/api/prep/progress?bank=" + encodeURIComponent(bank));
        p.available = j.available !== false;
        if (!p.available) {
          local.forEach(function (x) { p.done.add(x); });
          note("Ticks are saved on this device only. Run " + (j.migration || "the migration") +
               " in Supabase to sync them across devices.");
          return p;
        }
        p.done = new Set(j.done || []);
        p.mock = j.mock || {};
        var flag = legacyKey + "__synced";
        var synced = false;
        try { synced = localStorage.getItem(flag) === "1"; } catch (_) {}
        var missing = local.filter(function (x) { return !p.done.has(x); });
        if (!synced && missing.length) {
          // One-off: carry the old device-only ticks up to the server.
          try {
            await api("/api/prep/progress", { method: "POST", body: JSON.stringify({ bank: bank, ids: missing }) });
            missing.forEach(function (x) { p.done.add(x); });
          } catch (_) { /* try again next load */ }
        }
        try { localStorage.setItem(flag, "1"); } catch (_) {}
        writeLocal();
        note("");
      } catch (e) {
        p.available = false;
        local.forEach(function (x) { p.done.add(x); });
      }
      return p;
    };

    /* A mock-interview score (1-4). The server counts the attempt, keeps
       the best, and marks the entry rehearsed on a 3 or 4. */
    p.mockScore = async function (id, score) {
      var r = await api("/api/prep/progress", { method: "POST",
        body: JSON.stringify({ bank: bank, id: id, mock_score: score }) });
      p.mock[id] = { attempts: r.attempts, best: r.best, last: score };
      if (r.done) p.done.add(id);
      writeLocal();
      return r;
    };

    p.set = async function (id, isDone) {
      if (isDone) p.done.add(id); else p.done.delete(id);
      writeLocal();
      if (!p.available) return true;
      try {
        await api("/api/prep/progress", { method: "POST", body: JSON.stringify({ bank: bank, id: id, done: !!isDone }) });
        return true;
      } catch (e) {
        say("Couldn't save that tick — " + e.message, "error");
        return false;
      }
    };
    return p;
  }

  /* ── Tabs ────────────────────────────────────────────────────────── */
  var PATHS = { overview: "/interview-prep", cases: "/interview-prep/cases",
                behavioral: "/interview-prep/behavioral", design: "/interview-prep/design" };
  var loaders = {};          // tab -> function, run once on first open
  var loaded = {};
  var current = null;

  function activate(tab, push) {
    if (!PATHS[tab]) tab = "overview";
    current = tab;
    document.querySelectorAll(".ip-tab").forEach(function (a) {
      a.setAttribute("aria-selected", a.dataset.tab === tab ? "true" : "false");
    });
    document.querySelectorAll(".ip-panel").forEach(function (s) {
      s.hidden = s.dataset.panel !== tab;
    });
    if (push) {
      try { history.pushState({ tab: tab }, "", PATHS[tab]); } catch (_) {}
    }
    if (!loaded[tab] && loaders[tab]) { loaded[tab] = true; loaders[tab](); }
    if (window.feather) window.feather.replace();
  }

  document.querySelector(".ip-tabs").addEventListener("click", function (e) {
    var a = e.target.closest(".ip-tab");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    if (a.dataset.tab !== current) {
      activate(a.dataset.tab, true);
      window.scrollTo({ top: 0 });
    }
  });
  window.addEventListener("popstate", function () {
    var tab = Object.keys(PATHS).find(function (k) { return PATHS[k] === location.pathname; });
    activate(tab || "overview", false);
  });

  /* ── Overview ────────────────────────────────────────────────────── */
  var RING_C = 326.7;
  var data = null;
  var fmtDate = function (iso) {
    if (!iso) return "";
    var d = new Date(iso + "T00:00:00");
    return isNaN(d) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  };

  function mountDaysCountdown(targetDate, daysLeft) {
    var chip = $("days-chip");
    if (!chip) return;
    if (typeof Countdown === "undefined" || !targetDate) {
      $("days-left").textContent = daysLeft == null ? "–" : daysLeft;
      $("days-unit").textContent = "days left";
      return;
    }
    Countdown.clear();
    // A bare date: the interview is at the END of that day for the clock.
    chip.dataset.countdown = String(targetDate).slice(0, 10) + "T23:59:59";
    chip.dataset.flash = "true";
    Countdown.mount(chip);
  }

  function pctOrDash(v) { return v == null ? "–" : v + "%"; }

  function renderOverview() {
    var p = data.plan || {}, s = data.stats || {};
    $("role").value = p.role_title || "";
    $("target-date").value = p.target_date || "";
    $("goal").value = p.daily_goal_minutes != null ? p.daily_goal_minutes : 45;

    var rd = s.readiness || 0;
    $("readiness").textContent = rd + "%";
    $("ring-fill").style.strokeDashoffset = (RING_C * (1 - rd / 100)).toFixed(1);
    $("ring").dataset.tone = rd >= 70 ? "high" : rd >= 40 ? "mid" : "low";
    $("hs-ready").textContent = rd + "%";
    $("hs-days").textContent = s.days_left == null ? "–" : s.days_left;
    $("hs-days-wrap").hidden = s.days_left == null;
    $("hs-streak").textContent = s.streak || 0;
    mountDaysCountdown(p.target_date, s.days_left);
    $("mastered").textContent = (s.topics_mastered || 0) + "/" + (s.topics_total || 0);

    if (data.migration_pending) {
      $("coach").className = "coach scold";
      $("coach-msg").textContent = "Run MIGRATION_INTERVIEW_PREP.sql in Supabase to switch on the prep coach.";
      $("coach-quote").textContent = "";
    } else {
      $("coach").className = "coach " + (s.tone || "cheer");
      $("coach-msg").textContent = s.coach || "";
      $("coach-quote").textContent = s.quote ? "“" + s.quote + "” — " + s.quote_by : "";
    }

    var goal = p.daily_goal_minutes || 0, mt = s.minutes_today || 0;
    $("today-min").textContent = mt;
    $("today-goal").textContent = goal;
    $("today-prog").style.width = (goal > 0 ? Math.min(100, Math.round(mt / goal * 100)) : 0) + "%";
    $("today-prog-wrap").classList.toggle("met", !!s.goal_met);
    $("bd-topics").textContent = (s.topic_score || 0) + "%";
    $("bd-stories").textContent = (s.story_score || 0) + "%";
    $("bd-cases").textContent = pctOrDash(s.case_score);
    $("bd-banks").textContent = pctOrDash(s.bank_score);
    $("bd-cases-wrap").classList.toggle("off", s.case_score == null);
    $("bd-banks-wrap").classList.toggle("off", s.bank_score == null);
    $("bd-consistency").textContent = (s.consistency || 0) + "%";

    var items = [];
    (s.next_cases || []).forEach(function (c) {
      items.push('<a class="focus-item case" href="/interview-prep/cases?topic=' + encodeURIComponent(c.title) +
        '" data-case="' + esc(c.title) + '"><span class="k">' + esc(c.priority) + '</span><span class="t">' +
        esc(c.title) + '</span></a>');
    });
    (s.weakest || []).forEach(function (t) {
      items.push('<div class="focus-item weak"><span class="k">' + t.confidence + '/4</span><span class="t">' +
        esc(t.title) + '</span><span class="cat">' + esc(t.category) + '</span></div>');
    });
    (s.to_rehearse || []).forEach(function (x) {
      items.push('<div class="focus-item"><span class="k">Story</span><span class="t">' + esc(x.title) +
        '</span><span class="cat">' + esc(x.competency) + '</span></div>');
    });
    $("focus-list").innerHTML = items.join("") ||
      '<div class="empty">All caught up — add topics or stories to keep sharpening.</div>';

    var sel = $("add-topic-cat");
    if (sel && !sel.children.length) {
      sel.innerHTML = (data.categories || []).map(function (c) {
        return '<option value="' + c.key + '">' + esc(c.label) + "</option>";
      }).join("");
    }
    renderTopics();
    renderStories();
    renderSessions();
    if (window.feather) window.feather.replace();
  }

  function renderTopics() {
    var cats = data.categories || [], byCat = {};
    (data.topics || []).forEach(function (t) { (byCat[t.category] = byCat[t.category] || []).push(t); });
    var all = data.topics || [];
    var avg = all.length ? Math.round(all.reduce(function (a, t) { return a + (t.confidence || 0); }, 0) / all.length / 4 * 100) : 0;
    $("sum-topics").textContent = all.length ? all.length + " topics · " + avg + "% confident" : "empty";
    $("topics").innerHTML = cats.filter(function (c) { return (byCat[c.key] || []).length; }).map(function (c) {
      var list = byCat[c.key];
      var a = Math.round(list.reduce(function (x, t) { return x + (t.confidence || 0); }, 0) / list.length / 4 * 100);
      return '<div class="cat-block"><div class="cat-head">' + esc(c.label) + ' <span class="n">· ' + a + '%</span></div>' +
        list.map(function (t) {
          return '<div class="topic" data-id="' + t.id + '"><div class="t">' + esc(t.title) + '</div><div class="pips">' +
            [1, 2, 3, 4].map(function (i) {
              return '<button class="pip ' + (t.confidence >= i ? "on" : "") + '" data-conf="' + i +
                '" type="button" aria-label="Confidence ' + i + ' of 4"></button>';
            }).join("") +
            '</div><button class="icon-del" data-del type="button" aria-label="Remove topic"><i data-feather="x"></i></button></div>';
        }).join("") + "</div>";
    }).join("") || '<div class="empty">No topics yet — add your syllabus below.</div>';
  }

  function renderStories() {
    var st = data.stories || [];
    var reh = st.filter(function (s) { return s.rehearsed; }).length;
    $("sum-stories").textContent = st.length ? reh + " of " + st.length + " rehearsed" : "empty";
    $("stories").innerHTML = st.map(function (s) {
      return '<div class="story ' + (s.rehearsed ? "done" : "") + '" data-id="' + s.id + '">' +
        '<div class="story-head"><input class="title" value="' + esc(s.title) + '" placeholder="Story title" maxlength="140" aria-label="Story title">' +
        '<input class="comp" value="' + esc(s.competency || "") + '" placeholder="Competency" maxlength="140" aria-label="Competency"></div>' +
        '<div class="star-grid">' +
        ["situation", "task", "action", "result"].map(function (f) {
          return '<label>' + f + '<textarea data-f="' + f + '">' + esc(s[f] || "") + "</textarea></label>";
        }).join("") +
        '</div><div class="story-foot"><label class="reh"><input type="checkbox" data-reh ' + (s.rehearsed ? "checked" : "") +
        '> Rehearsed</label><span class="spacer"></span><button class="btn sm" data-save type="button">Save</button>' +
        '<button class="del" data-del type="button">Delete</button></div></div>';
    }).join("") || '<div class="empty">No stories yet.</div>';
  }

  function renderSessions() {
    var ss = data.sessions || [];
    $("sum-sessions").textContent = ss.length ? ss.length + " recent" : "nothing yet";
    $("sessions").innerHTML = ss.map(function (s) {
      return '<div class="sess" data-id="' + s.id + '"><span class="m">' + s.minutes + 'm</span><span class="d">' +
        fmtDate(s.practiced_on) + '</span><span class="f">' + esc(s.focus || "—") +
        '</span><button class="icon-del" data-del type="button" aria-label="Delete session"><i data-feather="trash-2"></i></button></div>';
    }).join("") || '<div class="empty">No practice logged yet.</div>';
  }

  async function reload() {
    try { data = await api("/api/interview-prep"); renderOverview(); }
    catch (e) { say(e.message || "Couldn't load", "error"); }
  }

  var savePlan = async function (patch) {
    try { await api("/api/interview-prep/plan", { method: "POST", body: JSON.stringify(patch) }); reload(); }
    catch (e) { say(e.message, "error"); }
  };
  $("role").addEventListener("change", function (e) { savePlan({ role_title: e.target.value }); });
  $("target-date").addEventListener("change", function (e) { savePlan({ target_date: e.target.value }); });
  $("goal").addEventListener("change", function (e) { savePlan({ daily_goal_minutes: e.target.value }); });

  $("log-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var minutes = $("log-min").value;
    if (!minutes) return;
    try {
      await api("/api/interview-prep/sessions", { method: "POST", body: JSON.stringify({
        minutes: minutes, focus: $("log-focus").value, reflection: $("log-reflect").value }) });
      $("log-form").reset();
      say("Logged — nice work", "success");
      reload();
    } catch (err) { say(err.message, "error"); }
  });

  $("focus-list").addEventListener("click", function (e) {
    var a = e.target.closest("[data-case]");
    if (!a) return;
    e.preventDefault();
    activate("cases", true);
    if (window.PrepCases) window.PrepCases.focus(a.dataset.case);
  });

  $("topics").addEventListener("click", async function (e) {
    var row = e.target.closest(".topic"); if (!row) return;
    var id = row.dataset.id;
    var pip = e.target.closest(".pip");
    if (pip) {
      var t = (data.topics || []).find(function (x) { return x.id === id; }); if (!t) return;
      var conf = parseInt(pip.dataset.conf, 10);
      if (t.confidence === conf) conf = conf - 1;   // tap the current level to step down
      t.confidence = conf; renderTopics(); if (window.feather) window.feather.replace();
      try { await api("/api/interview-prep/topics/" + id, { method: "POST", body: JSON.stringify({ confidence: conf }) }); reload(); }
      catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest("[data-del]")) {
      if (!confirm("Remove this topic?")) return;
      try { await api("/api/interview-prep/topics/" + id + "/delete", { method: "POST" }); reload(); }
      catch (err) { say(err.message, "error"); }
    }
  });
  var addTopic = async function () {
    var title = $("add-topic-title").value.trim();
    if (!title) { $("add-topic-title").focus(); return; }
    try {
      await api("/api/interview-prep/topics", { method: "POST", body: JSON.stringify({ title: title, category: $("add-topic-cat").value }) });
      $("add-topic-title").value = ""; reload();
    } catch (err) { say(err.message, "error"); }
  };
  $("add-topic-btn").addEventListener("click", addTopic);
  $("add-topic-title").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); addTopic(); } });

  $("stories").addEventListener("click", async function (e) {
    var card = e.target.closest(".story"); if (!card) return;
    var id = card.dataset.id;
    if (e.target.closest("[data-save]")) {
      var body = { title: card.querySelector(".title").value, competency: card.querySelector(".comp").value };
      card.querySelectorAll("textarea[data-f]").forEach(function (t) { body[t.dataset.f] = t.value; });
      try { await api("/api/interview-prep/stories/" + id, { method: "POST", body: JSON.stringify(body) }); say("Saved", "success"); reload(); }
      catch (err) { say(err.message, "error"); }
    } else if (e.target.closest("[data-del]")) {
      if (!confirm("Delete this story?")) return;
      try { await api("/api/interview-prep/stories/" + id + "/delete", { method: "POST" }); reload(); }
      catch (err) { say(err.message, "error"); }
    }
  });
  $("stories").addEventListener("change", async function (e) {
    var reh = e.target.closest("[data-reh]"); if (!reh) return;
    var id = e.target.closest(".story").dataset.id;
    try {
      await api("/api/interview-prep/stories/" + id, { method: "POST", body: JSON.stringify({ rehearsed: reh.checked }) });
      if (reh.checked) say("Story locked in", "success");
      reload();
    } catch (err) { say(err.message, "error"); }
  });
  $("add-story-btn").addEventListener("click", async function () {
    try { await api("/api/interview-prep/stories", { method: "POST", body: JSON.stringify({ title: "New story" }) }); reload(); }
    catch (err) { say(err.message, "error"); }
  });
  $("sessions").addEventListener("click", async function (e) {
    if (!e.target.closest("[data-del]")) return;
    var id = e.target.closest(".sess").dataset.id;
    try { await api("/api/interview-prep/sessions/" + id + "/delete", { method: "POST" }); reload(); }
    catch (err) { say(err.message, "error"); }
  });

  /* ── A paged list, shared by the two big banks ───────────────────── */
  var PAGE = 40;
  function pager(moreEl, onMore) {
    var shown = PAGE;
    moreEl.addEventListener("click", function (e) {
      if (!e.target.closest("button")) return;
      shown += PAGE * 2; onMore();
    });
    return {
      reset: function () { shown = PAGE; },
      slice: function (list) {
        var rest = list.length - shown;
        moreEl.innerHTML = rest > 0
          ? '<button class="btn" type="button">Show ' + Math.min(rest, PAGE * 2) + " more of " + rest + "</button>" : "";
        return list.slice(0, shown);
      },
    };
  }

  function progressLine(el, done, total, noun) {
    var pct = total ? Math.round(done / total * 100) : 0;
    el.innerHTML = "<span><b>" + done + "</b> of " + total + " " + noun + "</span><span><b>" + pct +
      '%</b></span><span class="bar"><i style="width:' + pct + '%"></i></span>';
  }

  /* Whole sentences under a cap, the rule ai_sde_summary.py uses, so no
     card summary is cut mid-clause. */
  function summary(tip, s) {
    var flat = [tip || "", s || ""].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
    if (!flat) return "";
    var out = "";
    flat.split(/(?<=[.!?])\s+/).some(function (part) {
      var cand = out ? out + " " + part : part;
      if (cand.length > 260) return true;
      out = cand; return false;
    });
    return out || flat.slice(0, 260).replace(/\s\S*$/, "") + " …";
  }

  function gamify(nsList, prefix, ids, minutes) {
    if (!window.Gamify) return;
    window.Gamify.studiedBulk(ids.map(function (x) { return { id: prefix + x, minutes: minutes }; }));
    if (window.Pomodoro) window.Gamify.syncMinutes(nsList, window.Pomodoro.total(nsList) / 60);
  }

  /* ── Behavioural bank ────────────────────────────────────────────── */
  var QBANK = null, editingQ = null;
  var qCatLabel = {};
  var qProg = makeProgress("behavioral", "ip_practiced", $("qbank-sync"));
  var qPager = pager($("qbank-more"), renderBank);

  function renderBank() {
    if (!QBANK) return;
    var cat = $("qbank-cat").value;
    var term = ($("qbank-search").value || "").trim().toLowerCase();
    var onlyUn = $("qbank-unpracticed").checked;
    var list = QBANK.questions.filter(function (q) {
      return (!cat || q.cat === cat) && (!onlyUn || !qProg.done.has(q.id)) &&
        (!term || q.q.toLowerCase().indexOf(term) >= 0 || (qCatLabel[q.cat] || "").toLowerCase().indexOf(term) >= 0 ||
          (q.tags || []).some(function (t) { return t.indexOf(term) >= 0; }));
    });
    progressLine($("qbank-prog"), qProg.done.size, QBANK.total, "practised");
    $("tn-beh").textContent = qProg.done.size + "/" + QBANK.total;
    var ta = function (label, cls, val) {
      return "<label>" + label + '<textarea class="' + cls + '" data-e="' + cls + '">' + esc(val) + "</textarea></label>";
    };
    $("qbank-list").innerHTML = qPager.slice(list).map(function (q) {
      var isEd = editingQ === q.id;
      var done = qProg.done.has(q.id);
      var body = isEd
        ? '<div class="q-edit">' + ta("Question", "q", q.q) + ta("Situation", "situation", q.s) + ta("Task", "task", q.t) +
          ta("Action", "action", q.a) + ta("Result", "result", q.r) + ta("Tip", "tip", q.tip) +
          '<div class="q-actions"><button class="btn sm primary" data-savq type="button">Save</button>' +
          '<button class="btn sm" data-cancelq type="button">Cancel</button></div></div>'
        : '<div class="star s"><b>S</b><span>' + esc(q.s) + '</span></div><div class="star"><b>T</b><span>' + esc(q.t) +
          '</span></div><div class="star"><b>A</b><span>' + esc(q.a) + '</span></div><div class="star"><b>R</b><span>' + esc(q.r) +
          '</span></div>' + (q.tip ? '<div class="q-tip">' + esc(q.tip) + "</div>" : "") +
          (q.strong_weak ? '<details class="c-sec sw"><summary>Strong vs weak</summary><div class="txt">' + esc(reflow(q.strong_weak)) + "</div></details>" : "") +
          (q.probes && q.probes.length ? '<details class="c-sec probes"><summary>They will push back (' + q.probes.length +
            ")</summary><ol>" + q.probes.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
          (q.tags && q.tags.length ? '<div class="tags">' + q.tags.map(function (t) {
            return '<button class="tag" data-qtag="' + esc(t) + '" type="button">#' + esc(t) + "</button>"; }).join("") + "</div>" : "") +
          '<div class="q-actions"><button class="btn sm" data-use type="button">Use as my story</button>' +
          '<button class="btn sm" data-edit type="button">Edit</button>' +
          (q.edited ? '<button class="btn sm" data-reset type="button">Reset</button>' : "") +
          '<a class="btn sm" href="/interview-prep/behavioral/pdf?id=' + q.id + '" target="_blank" rel="noopener">PDF</a></div>';
      var sum = summary(q.tip, q.s);
      return '<div class="q-card ' + (done ? "done " : "") + (isEd ? "open" : "") + '" data-id="' + q.id + '">' +
        '<div class="q-head"><input type="checkbox" class="q-prac" ' + (done ? "checked" : "") + ' aria-label="Practised">' +
        '<span class="q-text">' + esc(q.q) + '</span><span class="q-meta">' +
        (q.edited ? '<span class="badge edited">edited</span>' : "") +
        '<span class="badge">' + esc(qCatLabel[q.cat] || q.cat) + "</span>" +
        PrepScheduler.button("behavioral", q.q, q.id) + "</span>" +
        (sum ? '<p class="q-sum">' + esc(sum) + "</p>" : "") + "</div>" +
        '<div class="q-body">' + body + "</div></div>";
    }).join("") || '<div class="card"><div class="empty">No questions match.</div></div>';
  }

  async function loadBank() {
    try {
      var r = await Promise.all([api("/api/interview-prep/questions"), qProg.load()]);
      QBANK = r[0];
      (QBANK.categories || []).forEach(function (c) { qCatLabel[c.key] = c.label; });
      var sel = $("qbank-cat");
      if (sel.children.length <= 1) {
        sel.innerHTML = '<option value="">All competencies</option>' + (QBANK.categories || []).map(function (c) {
          return '<option value="' + c.key + '">' + esc(c.label) + "</option>"; }).join("");
      }
      openTopicFromUrl(QBANK.questions.map(function (q) { return q.q; }), $("qbank-search"));
      renderBank();
      PrepScheduler.attach($("qbank-list"));
      if (window.Pomodoro) window.Pomodoro.init({ ns: "ip_behavioral", container: $("qbank-list") });
      gamify("ip_behavioral", "ipb:", Array.from(qProg.done), 12);
    } catch (e) { $("qbank-list").innerHTML = '<div class="card"><div class="empty">Couldn\'t load the question bank.</div></div>'; }
  }

  function resetAndRender(pg, fn) { return function () { pg.reset(); fn(); }; }
  $("qbank-cat").addEventListener("change", resetAndRender(qPager, renderBank));
  $("qbank-search").addEventListener("input", resetAndRender(qPager, renderBank));
  $("qbank-unpracticed").addEventListener("change", resetAndRender(qPager, renderBank));
  $("qbank-pdf").addEventListener("click", function () {
    var p = new URLSearchParams();
    if ($("qbank-cat").value) p.set("cat", $("qbank-cat").value);
    var term = ($("qbank-search").value || "").trim();
    if (term) p.set("q", term);
    window.open("/interview-prep/behavioral/pdf" + (p.toString() ? "?" + p : ""), "_blank", "noopener");
  });

  $("qbank-list").addEventListener("click", async function (e) {
    var card = e.target.closest(".q-card"); if (!card) return;
    var id = card.dataset.id;
    var q = QBANK && QBANK.questions.find(function (x) { return x.id === id; }); if (!q) return;
    if (e.target.classList.contains("q-prac")) {
      var on = e.target.checked;
      card.classList.toggle("done", on);
      if (!(await qProg.set(id, on))) { e.target.checked = !on; card.classList.toggle("done", !on); }
      if (on && window.Gamify) window.Gamify.studied("ipb:" + id, 12, {});
      progressLine($("qbank-prog"), qProg.done.size, QBANK.total, "practised");
      $("tn-beh").textContent = qProg.done.size + "/" + QBANK.total;
      return;
    }
    if (e.target.closest("[data-use]")) {
      try {
        await api("/api/interview-prep/stories", { method: "POST", body: JSON.stringify({
          title: q.q, competency: qCatLabel[q.cat] || q.cat, situation: q.s, task: q.t, action: q.a, result: q.r }) });
        say("Added to your story bank — now make it yours", "success");
        reload();
      } catch (err) { say(err.message, "error"); }
      return;
    }
    var qtag = e.target.closest("[data-qtag]");
    if (qtag) {
      $("qbank-search").value = qtag.dataset.qtag; $("qbank-cat").value = "";
      qPager.reset(); renderBank(); window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (e.target.closest("[data-edit]")) { editingQ = id; renderBank(); return; }
    if (e.target.closest("[data-cancelq]")) { editingQ = null; renderBank(); return; }
    if (e.target.closest("[data-savq]")) {
      var vals = {};
      card.querySelectorAll("textarea[data-e]").forEach(function (t) { vals[t.dataset.e] = t.value; });
      if (!(vals.q || "").trim()) { say("The question can't be empty", "error"); return; }
      try {
        await api("/api/interview-prep/questions/" + id, { method: "POST", body: JSON.stringify({
          question: vals.q, situation: vals.situation, task: vals.task, action: vals.action, result: vals.result, tip: vals.tip }) });
        q.q = vals.q; q.s = vals.situation; q.t = vals.task; q.a = vals.action; q.r = vals.result; q.tip = vals.tip; q.edited = true;
        editingQ = null; renderBank();
        say("Saved your version", "success");
      } catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest("[data-reset]")) {
      if (!confirm("Reset to the original answer? Your edits will be discarded.")) return;
      try {
        await api("/api/interview-prep/questions/" + id + "/reset", { method: "POST" });
        editingQ = null; say("Reverted to the original", "info"); loadBank();
      } catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest(".q-head") && !e.target.closest("a,button")) card.classList.toggle("open");
  });

  /* ── System design bank ──────────────────────────────────────────── */
  var SDBANK = null, editingSD = null;
  var sdCatLabel = {};
  var sdProg = makeProgress("sysdesign", "sd_practiced", $("sdbank-sync"));
  var sdPager = pager($("sdbank-more"), renderSDBank);
  var SD_LABELS = { problem: "Problem it solves", answer: "Approach", example: "Example", use_cases: "Use cases",
                    arch: "Architecture", disadvantages: "Disadvantages", competing: "Competing tech" };
  // Mirrors DETAIL_ORDER in system_design_bank.py. [key, label, isMono]
  var SD_DETAIL_ORDER = [
    ["scope", "1 · Understand the problem & scope", false], ["functional", "2 · Functional requirements", false],
    ["nonfunctional", "3 · Non-functional requirements", false], ["estimation", "4 · Back-of-the-envelope estimation", false],
    ["api", "5 · API design", false], ["data_model", "6 · Data model", false], ["hld", "7 · High-level design", false],
    ["hld_diagram", "High-level diagram", true], ["algorithms", "8 · Algorithms used", false],
    ["deep_dive", "9 · Design deep dive", false], ["follow_ups", "10 · Follow-up questions", false],
    ["final_diagram", "11 · Final design diagram", true], ["wrap_up", "12 · Wrap up", false],
  ];

  function sdDetailHtml(e) {
    if (!e.detail) return "";
    var secs = SD_DETAIL_ORDER.map(function (d) {
      var v = e.detail[d[0]]; if (!v) return "";
      return '<div class="sd-sec"><span class="h">' + esc(d[1]) + "</span>" +
        (d[2] ? '<div class="sd-arch">' + esc(v) + "</div>" : '<div class="b">' + esc(v) + "</div>") + "</div>";
    }).join("");
    return '<details class="c-sec frame"><summary>Full design walkthrough</summary><div style="padding:0 12px 10px">' + secs + "</div></details>";
  }

  function renderSDBank() {
    if (!SDBANK) return;
    var cat = $("sdbank-cat").value;
    var term = ($("sdbank-search").value || "").trim().toLowerCase();
    var onlyUn = $("sdbank-unpracticed").checked;
    var list = SDBANK.entries.filter(function (e) {
      return (!cat || e.cat === cat) && (!onlyUn || !sdProg.done.has(e.id)) &&
        (!term || e.title.toLowerCase().indexOf(term) >= 0 || (e.answer || "").toLowerCase().indexOf(term) >= 0 ||
          (e.competing || "").toLowerCase().indexOf(term) >= 0 || (sdCatLabel[e.cat] || "").toLowerCase().indexOf(term) >= 0 ||
          (e.tags || []).some(function (t) { return t.indexOf(term) >= 0; }));
    });
    progressLine($("sdbank-prog"), sdProg.done.size, SDBANK.total, "studied");
    $("tn-sd").textContent = sdProg.done.size + "/" + SDBANK.total;
    var fields = ["problem", "answer", "example", "use_cases", "arch", "disadvantages", "competing"];
    var clsFor = { problem: "problem", answer: "answer", disadvantages: "disadv", competing: "compete" };
    $("sdbank-list").innerHTML = sdPager.slice(list).map(function (e) {
      var isEd = editingSD === e.id, done = sdProg.done.has(e.id);
      var body;
      if (isEd) {
        body = '<div class="q-edit"><label>Title<textarea class="q" data-e="title">' + esc(e.title) + "</textarea></label>" +
          fields.map(function (f) {
            return "<label>" + SD_LABELS[f] + '<textarea class="' + (f === "arch" ? "arch" : "") + '" data-e="' + f + '">' + esc(e[f]) + "</textarea></label>";
          }).join("") +
          '<div class="q-actions"><button class="btn sm primary" data-savsd type="button">Save</button>' +
          '<button class="btn sm" data-cancelsd type="button">Cancel</button></div></div>';
      } else {
        body = fields.map(function (f) {
          if (!e[f]) return "";
          if (f === "arch") return '<div class="sd-field"><span class="lbl">Architecture</span></div><div class="sd-arch">' + esc(e.arch) + "</div>";
          return '<div class="sd-field ' + (clsFor[f] || "") + '"><span class="lbl">' + SD_LABELS[f] + "</span>" + esc(e[f]) + "</div>";
        }).join("") + sdDetailHtml(e) +
          (e.tags && e.tags.length ? '<div class="tags">' + e.tags.map(function (t) {
            return '<button class="tag" data-tag="' + esc(t) + '" type="button">#' + esc(t) + "</button>"; }).join("") + "</div>" : "") +
          '<div class="sd-related" data-related="pending"></div>' +
          '<div class="q-actions"><button class="btn sm" data-editsd type="button">Edit</button>' +
          (e.edited ? '<button class="btn sm" data-resetsd type="button">Reset</button>' : "") +
          '<a class="btn sm" href="/interview-prep/system-design/pdf?id=' + e.id + '" target="_blank" rel="noopener">PDF</a>' +
          '<button class="btn sm" data-saveref type="button">Save to References</button></div>';
      }
      return '<div class="q-card ' + (done ? "done " : "") + (isEd ? "open" : "") + '" data-id="' + e.id + '">' +
        '<div class="q-head"><input type="checkbox" class="q-prac" ' + (done ? "checked" : "") + ' aria-label="Studied">' +
        '<span class="q-text">' + esc(e.title) + '</span><span class="q-meta">' +
        (e.edited ? '<span class="badge edited">edited</span>' : "") +
        '<span class="badge">' + esc(sdCatLabel[e.cat] || e.cat) + "</span></span></div>" +
        '<div class="q-body">' + body + "</div></div>";
    }).join("") || '<div class="card"><div class="empty">No entries match.</div></div>';
  }

  async function loadSDBank() {
    try {
      var r = await Promise.all([api("/api/interview-prep/system-design"), sdProg.load()]);
      SDBANK = r[0];
      (SDBANK.categories || []).forEach(function (c) { sdCatLabel[c.key] = c.label; });
      var sel = $("sdbank-cat");
      if (sel.children.length <= 1) {
        sel.innerHTML = '<option value="">All categories</option>' + (SDBANK.categories || []).map(function (c) {
          return '<option value="' + c.key + '">' + esc(c.label) + "</option>"; }).join("");
      }
      renderSDBank();
      if (window.Pomodoro) window.Pomodoro.init({ ns: "ip_sysdesign", container: $("sdbank-list") });
      gamify("ip_sysdesign", "ipsd:", Array.from(sdProg.done), 30);
    } catch (e) { $("sdbank-list").innerHTML = '<div class="card"><div class="empty">Couldn\'t load the design bank.</div></div>'; }
  }

  async function loadSDRelated(card, id) {
    var box = card.querySelector(".sd-related");
    if (!box || box.dataset.related !== "pending") return;
    box.dataset.related = "loading";
    try {
      var d = await api("/api/interview-prep/system-design/" + id + "/related");
      var groups = [["From your References", d.references || [], "category"], ["From your Travel Reads", d.travel_reads || [], "source"],
                    ["From your Knowledge Base", d.knowledge_base || [], null]];
      box.innerHTML = groups.filter(function (g) { return g[1].length; }).map(function (g) {
        return "<h5>" + g[0] + "</h5>" + g[1].map(function (x) {
          return '<div class="sd-rel-item"><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.title) + "</a>" +
            (g[2] && x[g[2]] ? '<span class="src">' + esc(x[g[2]]) + "</span>" : "") + "</div>";
        }).join("");
      }).join("");
      box.dataset.related = "done";
    } catch (err) { box.dataset.related = "pending"; }
  }

  $("sdbank-cat").addEventListener("change", resetAndRender(sdPager, renderSDBank));
  $("sdbank-search").addEventListener("input", resetAndRender(sdPager, renderSDBank));
  $("sdbank-unpracticed").addEventListener("change", resetAndRender(sdPager, renderSDBank));
  $("sdbank-pdf").addEventListener("click", function () {
    var p = new URLSearchParams();
    if ($("sdbank-cat").value) p.set("cat", $("sdbank-cat").value);
    var term = ($("sdbank-search").value || "").trim();
    if (term) p.set("q", term);
    window.open("/interview-prep/system-design/pdf" + (p.toString() ? "?" + p : ""), "_blank", "noopener");
  });

  $("sdbank-list").addEventListener("click", async function (e) {
    var card = e.target.closest(".q-card"); if (!card) return;
    var id = card.dataset.id;
    var it = SDBANK && SDBANK.entries.find(function (x) { return x.id === id; }); if (!it) return;
    if (e.target.classList.contains("q-prac")) {
      var on = e.target.checked;
      card.classList.toggle("done", on);
      if (!(await sdProg.set(id, on))) { e.target.checked = !on; card.classList.toggle("done", !on); }
      if (on && window.Gamify) window.Gamify.studied("ipsd:" + id, 30, {});
      progressLine($("sdbank-prog"), sdProg.done.size, SDBANK.total, "studied");
      $("tn-sd").textContent = sdProg.done.size + "/" + SDBANK.total;
      return;
    }
    var tagBtn = e.target.closest("[data-tag]");
    if (tagBtn) {
      $("sdbank-search").value = tagBtn.dataset.tag; $("sdbank-cat").value = "";
      sdPager.reset(); renderSDBank(); window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (e.target.closest("[data-saveref]")) {
      try { await api("/api/interview-prep/system-design/" + id + "/save-reference", { method: "POST" }); say("Saved to your References", "success"); }
      catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest("[data-editsd]")) { editingSD = id; renderSDBank(); return; }
    if (e.target.closest("[data-cancelsd]")) { editingSD = null; renderSDBank(); return; }
    if (e.target.closest("[data-savsd]")) {
      var vals = {};
      card.querySelectorAll("textarea[data-e]").forEach(function (t) { vals[t.dataset.e] = t.value; });
      if (!(vals.title || "").trim()) { say("The title can't be empty", "error"); return; }
      try {
        await api("/api/interview-prep/system-design/" + id, { method: "POST", body: JSON.stringify(vals) });
        Object.assign(it, vals); it.edited = true;
        editingSD = null; renderSDBank();
        say("Saved your version", "success");
      } catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest("[data-resetsd]")) {
      if (!confirm("Reset to the original entry? Your edits will be discarded.")) return;
      try {
        await api("/api/interview-prep/system-design/" + id + "/reset", { method: "POST" });
        editingSD = null; say("Reverted to the original", "info"); loadSDBank();
      } catch (err) { say(err.message, "error"); }
      return;
    }
    if (e.target.closest(".q-head") && !e.target.closest("a,button")) {
      card.classList.toggle("open");
      if (card.classList.contains("open")) loadSDRelated(card, id);
    }
  });

  /* ?topic= from the Day Board: put the topic in the search box so its card
     is on the first page; prep-scheduler.js then opens and scrolls to it. */
  function topicFromUrl() {
    try { return new URLSearchParams(location.search).get("topic") || ""; } catch (_) { return ""; }
  }
  function openTopicFromUrl(titles, searchEl) {
    var t = topicFromUrl();
    if (t && titles.indexOf(t) >= 0 && searchEl) searchEl.value = t;
  }

  /* ── Boot ────────────────────────────────────────────────────────── */
  loaders.overview = function () { if (window.Gamify) window.Gamify.mount($("gamebar")); };
  loaders.behavioral = loadBank;
  loaders.design = loadSDBank;
  loaders.cases = function () { if (window.PrepCases) window.PrepCases.load(); };

  window.PrepHub = { api: api, esc: esc, reflow: reflow, say: say, hrs: hrs, makeProgress: makeProgress,
                     activate: activate, topicFromUrl: topicFromUrl, reloadOverview: reload,
                     progressLine: progressLine };

  var initial = document.getElementById("ip").dataset.initialTab || "overview";
  // An old Day Board link for a behavioural question lands on /interview-prep?topic=.
  if (initial === "overview" && topicFromUrl()) initial = "behavioral";
  try { history.replaceState({ tab: initial }, "", location.href); } catch (_) {}
  document.addEventListener("DOMContentLoaded", function () {
    reload();
    activate(initial, false);
  });
})();

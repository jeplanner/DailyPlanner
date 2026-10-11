/* prep_cases.js — the Case rounds tab of the Interview Prep hub, and the
 * mock-interview mode.
 *
 * Formerly its own page (/tpm-rounds) with its own menu item; now a tab, so
 * the whole loop — product, program, engineering leadership, the questions
 * you ask them, plus the behavioural and design banks — is one place.
 *
 * Each case card: the framework is open, the long parts (worked answer,
 * strong vs weak, probes, pitfalls) fold, so the list scans as a list. The
 * Plan / Share buttons and the per-case notes box come from
 * prep-scheduler.js under bank "tpm"; rehearsed ticks and mock scores are
 * saved server-side through PrepHub.makeProgress.
 *
 * MOCK INTERVIEW: draw a case (unrehearsed P0 first), answer it out loud
 * against a timer, face one of the panel's follow-up probes, then score
 * yourself against the strong-vs-weak contrast. A run scored 3 or 4 counts
 * as rehearsed.
 */
(function () {
  "use strict";
  var H = function () { return window.PrepHub; };
  var $ = function (id) { return document.getElementById(id); };

  var BANK = null, prog = null, round = "", started = false, landed = "";
  var roundLabel = {};

  function esc(s) { return H().esc(s); }

  function load() {
    if (started) return;
    started = true;
    prog = H().makeProgress("tpm", "tpm_rounds_done", $("c-sync"));
    Promise.all([H().api("/api/tpm-rounds"), prog.load()]).then(function (r) {
      BANK = r[0];
      (BANK.rounds || []).forEach(function (x) { roundLabel[x.key] = x.label; });
      var t = H().topicFromUrl();
      if (t && BANK.entries.some(function (e) { return e.title === t; })) { $("c-search").value = t; landed = t; }
      chips(); render();
      PrepScheduler.attach($("c-list"));
      if (window.Pomodoro) {
        window.Pomodoro.init({ ns: "tpm_rounds", container: $("c-list") });
        document.addEventListener("pomodoro:change", function () {
          if (window.Gamify) window.Gamify.syncMinutes("tpm_rounds", window.Pomodoro.total("tpm_rounds") / 60);
        });
      }
      if (window.Gamify) {
        window.Gamify.studiedBulk(BANK.entries.filter(function (x) { return prog.done.has(x.id); }).map(function (x) {
          return { id: "tpm:" + x.id, minutes: x.prep_minutes, difficulty: x.difficulty, priority: x.priority };
        }));
      }
      if (window.feather) window.feather.replace();
    }).catch(function () {
      $("c-list").innerHTML = '<div class="card"><div class="empty">Couldn\'t load the case rounds.</div></div>';
    });
  }

  /* Round chips. The loop has four rounds plus design and behavioural; the
     last two are other tabs, so their chips switch tab rather than filter. */
  function chips() {
    var counts = {};
    BANK.entries.forEach(function (e) { counts[e.round] = (counts[e.round] || 0) + 1; });
    var html = '<button class="rchip" type="button" data-round="" aria-pressed="' + (round === "" ? "true" : "false") +
      '">All <span class="n">' + BANK.entries.length + "</span></button>";
    (BANK.rounds || []).forEach(function (r) {
      html += '<button class="rchip" type="button" data-round="' + r.key + '" aria-pressed="' + (round === r.key ? "true" : "false") +
        '">' + esc(shortRound(r.key, r.label)) + ' <span class="n">' + (counts[r.key] || 0) + "</span></button>";
    });
    html += '<a class="rchip link" href="/interview-prep/design" data-goto="design">System design →</a>' +
            '<a class="rchip link" href="/interview-prep/behavioral" data-goto="behavioral">Behavioral →</a>';
    $("c-rounds").innerHTML = html;
  }
  function shortRound(key, label) {
    return { product: "Product", program: "Program", engineering: "Engineering leadership", close: "Your questions" }[key] || label;
  }

  $("c-rounds").addEventListener("click", function (e) {
    var go = e.target.closest("[data-goto]");
    if (go) { e.preventDefault(); H().activate(go.dataset.goto, true); window.scrollTo({ top: 0 }); return; }
    var b = e.target.closest("[data-round]");
    if (!b) return;
    round = b.dataset.round;
    // Arriving on one case (?topic= or "Do these next") fills the search
    // box; picking a round means "show me the round", so let it go.
    if (landed && $("c-search").value === landed) { $("c-search").value = ""; landed = ""; }
    chips(); render();
  });

  function filtered() {
    var pri = $("c-pri").value;
    var term = ($("c-search").value || "").trim().toLowerCase();
    var todo = $("c-todo").checked;
    return BANK.entries.filter(function (e) {
      return (!round || e.round === round) && (!pri || e.priority === pri) && (!todo || !prog.done.has(e.id)) &&
        (!term || e.title.toLowerCase().indexOf(term) >= 0 || (e.framework || "").toLowerCase().indexOf(term) >= 0 ||
          (e.tags || []).some(function (t) { return t.indexOf(term) >= 0; }));
    }).sort(function (a, b) { return (a.rank || 0) - (b.rank || 0); });
  }

  function progress(list) {
    var tot = 0, left = 0, n = 0;
    list.forEach(function (e) {
      tot += e.prep_minutes || 0;
      if (prog.done.has(e.id)) n++; else left += e.prep_minutes || 0;
    });
    var pct = list.length ? Math.round(n / list.length * 100) : 0;
    $("c-progress").innerHTML = "<span><b>" + n + "</b> of " + list.length + " rehearsed</span><span><b>" +
      H().hrs(left) + "</b> of rehearsal left</span><span>" + H().hrs(tot) + ' in total</span><span class="bar"><i style="width:' + pct + '%"></i></span>';
    var all = BANK.entries.filter(function (e) { return prog.done.has(e.id); }).length;
    $("tn-cases").textContent = all + "/" + BANK.entries.length;
  }

  function sec(cls, label, text, open) {
    if (!text) return "";
    return '<details class="c-sec ' + cls + '"' + (open ? " open" : "") + "><summary>" + label + '</summary><div class="txt">' +
      esc(H().reflow(text)) + "</div></details>";
  }

  function render() {
    if (!BANK) return;
    var list = filtered();
    progress(list);
    $("c-brief").innerHTML = round && BANK.briefs && BANK.briefs[round]
      ? '<div class="brief"><b>What this round is really testing.</b> ' + esc(BANK.briefs[round]) + "</div>" : "";
    $("c-list").innerHTML = list.map(function (e) {
      var done = prog.done.has(e.id);
      var m = prog.mock[e.id];
      return '<div class="q-card ' + (done ? "done" : "") + '" data-id="' + e.id + '" data-est="' + (e.prep_minutes || "") + '">' +
        '<div class="q-head"><input type="checkbox" class="q-prac" ' + (done ? "checked" : "") + ' aria-label="Rehearsed">' +
        '<span class="q-text">' + esc(e.title) + '</span><span class="q-meta">' +
        '<span class="badge ' + esc(e.priority) + '" title="' + esc(e.priority_note || "") + '">' + esc(e.priority) + "</span>" +
        '<span class="badge">' + esc(e.prep_label) + "</span>" +
        (round ? "" : '<span class="badge">' + esc(shortRound(e.round, roundLabel[e.round] || e.round)) + "</span>") +
        (m ? '<span class="badge mock" title="Best mock score">mock ' + m.best + "/4</span>" : "") +
        PrepScheduler.button("tpm", e.title, e.id, e.prep_minutes) + "</span></div>" +
        '<div class="q-body">' +
        '<p class="c-test">' + esc(e.what_they_test) + "</p>" +
        '<p class="c-freq">' + esc(e.difficulty) + " · " + esc(e.frequency) + "</p>" +
        sec("frame", "The framework — impose this structure", e.framework, true) +
        sec("worked", "Worked answer", e.worked) +
        sec("sw", "Strong vs weak", e.strong_weak) +
        (e.probes && e.probes.length ? '<details class="c-sec probes"><summary>Their follow-up probes (' + e.probes.length +
          ")</summary><ol>" + e.probes.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
        sec("pit", "Pitfalls", e.pitfalls) +
        '<div class="q-actions"><button class="btn sm primary" data-mock type="button">Mock this case</button>' +
        '<a class="btn sm" href="/interview-prep/cases/pdf?id=' + e.id + '" target="_blank" rel="noopener">PDF</a></div>' +
        "</div></div>";
    }).join("") || '<div class="card"><div class="empty">No cases match.</div></div>';
  }

  ["c-pri", "c-todo"].forEach(function (id) { $(id).addEventListener("change", render); });
  $("c-search").addEventListener("input", render);
  $("c-pdf").addEventListener("click", function () {
    var p = new URLSearchParams();
    if (round) p.set("round", round);
    if ($("c-pri").value) p.set("priority", $("c-pri").value);
    var term = ($("c-search").value || "").trim();
    if (term) p.set("q", term);
    window.open("/interview-prep/cases/pdf" + (p.toString() ? "?" + p : ""), "_blank", "noopener");
  });

  $("c-list").addEventListener("click", async function (e) {
    var card = e.target.closest(".q-card"); if (!card) return;
    var id = card.dataset.id;
    var ent = BANK.entries.find(function (x) { return x.id === id; }) || {};
    if (e.target.classList.contains("q-prac")) {
      var on = e.target.checked;
      card.classList.toggle("done", on);
      if (!(await prog.set(id, on))) { e.target.checked = !on; card.classList.toggle("done", !on); }
      if (on && window.Gamify) window.Gamify.studied("tpm:" + id, ent.prep_minutes, { difficulty: ent.difficulty, priority: ent.priority });
      progress(filtered());
      return;
    }
    if (e.target.closest("[data-mock]")) { Mock.start(ent); return; }
    if (e.target.closest("a,button,summary,.prep-panel")) return;
    if (e.target.closest(".q-head")) card.classList.toggle("open");
  });

  /* Jump to one case: from the overview's "Do these next", or ?topic=. */
  function focus(title) {
    var go = function () {
      $("c-search").value = title; landed = title; round = ""; $("c-pri").value = ""; $("c-todo").checked = false;
      chips(); render();
      var card = $("c-list").querySelector(".q-card");
      if (card) { card.classList.add("open"); card.scrollIntoView({ block: "start" }); }
    };
    if (BANK) go(); else { load(); var t = setInterval(function () { if (BANK) { clearInterval(t); go(); } }, 80); }
  }

  /* ══════════════════ Mock interview ══════════════════ */
  var Mock = (function () {
    var back = $("mock"), box = $("mock-card");
    var cur = null, timer = null, endAt = 0, score = 0, setup = { round: "", minutes: 5 };

    function close() {
      stop(); back.hidden = true; cur = null;
      document.removeEventListener("keydown", onKey);
    }
    function onKey(e) { if (e.key === "Escape") close(); }
    function open() { back.hidden = false; document.addEventListener("keydown", onKey); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function tick(el, sub) {
      var left = Math.round((endAt - Date.now()) / 1000);
      var a = Math.abs(left);
      el.textContent = (left < 0 ? "+" : "") + Math.floor(a / 60) + ":" + String(a % 60).padStart(2, "0");
      el.classList.toggle("over", left < 0);
      if (sub) sub.textContent = left < 0 ? "Over time — land it in one sentence." : "Think out loud. Structure first.";
    }
    function countdown(seconds) {
      stop(); endAt = Date.now() + seconds * 1000;
      var el = box.querySelector(".timer"), sub = box.querySelector(".timer-sub");
      tick(el, sub);
      timer = setInterval(function () { tick(el, sub); }, 500);
    }

    function pick() {
      var pool = BANK.entries.filter(function (e) { return !setup.round || e.round === setup.round; });
      var fresh = pool.filter(function (e) { return !prog.done.has(e.id); });
      var src = fresh.length ? fresh : pool;
      // Weighted toward P0, then P1: the cases most likely to decide the loop.
      var w = { P0: 4, P1: 2, P2: 1 }, total = 0;
      src.forEach(function (e) { total += w[e.priority] || 1; });
      var r = Math.random() * total;
      for (var i = 0; i < src.length; i++) { r -= w[src[i].priority] || 1; if (r <= 0) return src[i]; }
      return src[0];
    }

    function head(step) {
      return '<div class="mock-top"><span class="step">' + step + '</span><button class="btn sm ghost" data-x type="button" aria-label="Close">Close</button></div>';
    }

    function showSetup() {
      var opts = '<option value="">Any round</option>' + (BANK.rounds || []).map(function (r) {
        return '<option value="' + r.key + '"' + (setup.round === r.key ? " selected" : "") + ">" + esc(r.label) + "</option>";
      }).join("");
      box.innerHTML = head("Mock interview") +
        '<h2 id="mock-title">Answer a case out loud, against the clock</h2>' +
        '<p class="lead">You get one case, drawn from what you have not rehearsed yet (P0 first). Answer it out loud as if the panel is listening, ' +
        "then take one of their follow-up probes, then score yourself against what separates a hire.</p>" +
        '<div class="mock-setup"><label>Round<select id="m-round">' + opts + "</select></label>" +
        '<label>Time to answer<select id="m-min">' + [3, 5, 8, 10].map(function (m) {
          return '<option value="' + m + '"' + (setup.minutes === m ? " selected" : "") + ">" + m + " minutes</option>"; }).join("") +
        "</select></label></div>" +
        '<div class="mock-actions"><button class="btn primary" data-go type="button">Draw a case</button></div>';
    }

    function showQuestion() {
      score = 0;
      box.innerHTML = head("1 of 3 · Your answer · " + esc(roundLabel[cur.round] || cur.round)) +
        '<h2 id="mock-title">' + esc(cur.title) + "</h2>" +
        '<div class="timer">0:00</div><div class="timer-sub"></div>' +
        '<div id="m-hint"></div>' +
        '<div class="mock-actions"><button class="btn left" data-hint type="button">Hint: the structure</button>' +
        '<button class="btn" data-skip type="button">Different case</button>' +
        '<button class="btn primary" data-next type="button">Done — next</button></div>';
      countdown(setup.minutes * 60);
    }

    function hint() {
      // Just the headings of the framework: enough to recover, not the answer.
      var lines = (cur.framework || "").split("\n").filter(function (l) {
        var t = l.trim();
        return t && t === t.toUpperCase() && /[A-Z]/.test(t);
      });
      $("m-hint").innerHTML = '<div class="hint">' + esc(lines.join("\n") || "Name your structure first, then go phase by phase.") + "</div>";
    }

    function showProbe() {
      var p = (cur.probes || [])[Math.floor(Math.random() * (cur.probes || [1]).length)] || "Why that order, and not another?";
      box.innerHTML = head("2 of 3 · Their follow-up") +
        '<p class="lead">They push back. Answer without restarting your whole answer.</p>' +
        '<div class="probe-box">' + esc(p) + "</div>" +
        '<div class="timer">0:00</div><div class="timer-sub"></div>' +
        '<div class="mock-actions"><button class="btn primary" data-next type="button">Done — score it</button></div>';
      countdown(120);
    }

    function showScore() {
      stop();
      box.innerHTML = head("3 of 3 · Score yourself") +
        '<h2 id="mock-title">' + esc(cur.title) + "</h2>" +
        '<div class="rubric">' + [
          "I named a structure out loud before going into detail",
          "I described mechanisms and the behaviour they change, not artefacts",
          "I put numbers on it — dates, ratios, thresholds, confidence",
          "I said what I would NOT do, or the trade-off, at least once",
          "I handled the probe without restarting my answer",
        ].map(function (t) { return '<label><input type="checkbox"> ' + esc(t) + "</label>"; }).join("") + "</div>" +
        sec("sw", "Strong vs weak — compare honestly", cur.strong_weak, true) +
        sec("frame", "The framework", cur.framework) +
        '<p class="lead" style="margin-top:12px">Overall, how would the panel score it?</p>' +
        '<div class="scores">' + [[1, "No hire"], [2, "Lean no"], [3, "Lean hire"], [4, "Strong hire"]].map(function (s) {
          return '<button type="button" data-score="' + s[0] + '" aria-pressed="false"><b>' + s[0] + "</b>" + s[1] + "</button>"; }).join("") + "</div>" +
        '<div class="mock-actions"><button class="btn left" data-again type="button">Retry this case</button>' +
        '<button class="btn" data-save-next type="button" disabled>Save &amp; next case</button>' +
        '<button class="btn primary" data-save type="button" disabled>Save</button></div>';
    }

    async function save(thenNext) {
      if (!score || !cur) return;
      var id = cur.id;
      try {
        var was = prog.done.has(id);
        var r = await prog.mockScore(id, score);
        if (r.done && !was) {
          if (window.Gamify) window.Gamify.studied("tpm:" + id, cur.prep_minutes, { difficulty: cur.difficulty, priority: cur.priority });
        }
        H().say(score >= 3 ? "Saved — counted as rehearsed" : "Saved. Run it again tomorrow.", "success");
      } catch (e) {
        if (e.status === 503) H().say("Scores need MIGRATION_PREP_PROGRESS.sql run in Supabase.", "error");
        else H().say(e.message, "error");
      }
      render();
      if (thenNext) { cur = pick(); showQuestion(); } else close();
    }

    box.addEventListener("click", function (e) {
      var t = e.target.closest("button"); if (!t) return;
      if (t.hasAttribute("data-x")) { close(); return; }
      if (t.hasAttribute("data-go")) {
        setup.round = $("m-round").value; setup.minutes = parseInt($("m-min").value, 10) || 5;
        cur = pick(); if (!cur) { H().say("No cases in that round", "error"); return; }
        showQuestion(); return;
      }
      if (t.hasAttribute("data-hint")) { hint(); return; }
      if (t.hasAttribute("data-skip")) { cur = pick(); showQuestion(); return; }
      if (t.hasAttribute("data-next")) {
        if (box.querySelector(".probe-box")) showScore(); else showProbe();
        return;
      }
      if (t.hasAttribute("data-score")) {
        score = parseInt(t.dataset.score, 10);
        box.querySelectorAll("[data-score]").forEach(function (b) { b.setAttribute("aria-pressed", b === t ? "true" : "false"); });
        box.querySelectorAll("[data-save],[data-save-next]").forEach(function (b) { b.disabled = false; });
        return;
      }
      if (t.hasAttribute("data-again")) { showQuestion(); return; }
      if (t.hasAttribute("data-save")) { save(false); return; }
      if (t.hasAttribute("data-save-next")) { save(true); return; }
    });
    back.addEventListener("click", function (e) { if (e.target === back) close(); });

    return {
      start: function (entry) {
        if (!BANK) return;
        open();
        if (entry && entry.id) { cur = entry; showQuestion(); } else showSetup();
      },
    };
  })();

  $("c-mock").addEventListener("click", function () { Mock.start(null); });

  window.PrepCases = { load: load, focus: focus };
})();

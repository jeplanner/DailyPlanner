/* DailyPlanner — project tasks page v2 shell.

   Responsibilities (only the new bits — row-level interactions like
   open-detail, toggle done, edit etc. all stay in project_tasks.js):

     1. Tab switching: Focus / All / Tree / Done.
        - URL hash mirror so `#tree` etc. deep-links and survives reload.
        - Body data-active-tab attribute so CSS can hide the standalone
          table/board on the wrong tab without JS toggling each one.
     2. Focus tab: read every <tr.task-row> in the table, group into
        Overdue / Today / Upcoming (7 days), render lightweight cards
        that delegate to the existing openTaskDetail / toggleTaskDone.
     3. Done tab: same idea, filter for rows with data-status="done".
     4. Tree tab: render OKR > Init > Epic columns inline (instead of
        as a modal). Reuses the /api/projects/<id>/hierarchy endpoint
        already wired by okr_cascade.js. Selecting a node filters the
        Tree-tasks list below.
     5. Sticky add bar expander: tap chevron toggles the detail row.
     6. ⋯ menu open/close + density cycling.
     7. Stat bar (header progress) from the same source as Focus.

   This file is purely a presentation layer over the existing data —
   it never mutates state directly; everything goes through the
   pre-existing handlers in project_tasks.js. */

(function () {
  "use strict";

  if (!document.querySelector(".ptv2-tabs")) return;
  document.body.dataset.ptv2 = "1";

  /* ───── PROJECT_ID + endpoints ──────────────────────────────── */

  const PROJECT_ID = (document.getElementById("add-task-input") || {}).dataset?.projectId
                  || (location.pathname.match(/\/projects\/([^/]+)\/tasks/) || [])[1];

  const _fetch = window.dpFetch || ((u, o) => fetch(u, o));

  /* ───── tab switching ───────────────────────────────────────── */

  const TABS = ["focus", "all", "tree", "done"];
  function activeTab() {
    const h = (location.hash || "").replace("#", "").split("?")[0];
    return TABS.includes(h) ? h : "focus";
  }
  function setTab(tab, opts = {}) {
    if (!TABS.includes(tab)) tab = "focus";
    document.body.dataset.activeTab = tab;
    document.querySelectorAll(".ptv2-tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    document.querySelectorAll(".ptv2-panel").forEach((p) => {
      p.hidden = p.dataset.tab !== tab;
    });
    if (!opts.skipHash && activeTab() !== tab) {
      history.replaceState(null, "", `#${tab}`);
    }
    // Render tab-specific content on entry.
    if (tab === "focus")   renderFocus();
    if (tab === "tree")    renderTreeIfNeeded();
    if (tab === "done")    renderDone();
    if (tab === "sprints") renderSprintsTab();
  }
  function jumpTab(tab) { setTab(tab); }

  document.addEventListener("click", (e) => {
    const tabBtn = e.target.closest(".ptv2-tab[data-tab]");
    if (tabBtn) { setTab(tabBtn.dataset.tab); return; }
    const jumpLink = e.target.closest("[data-jump-tab]");
    if (jumpLink) { e.preventDefault(); setTab(jumpLink.dataset.jumpTab); }
  });
  window.addEventListener("hashchange", () => setTab(activeTab(), { skipHash: true }));
  window.ptv2GoTab = jumpTab;

  /* ───── grab the source task data from the existing table ──── */

  function readTasks() {
    const rows = Array.from(document.querySelectorAll("#task-tbody tr.task-row"));
    return rows.map((row) => ({
      el:           row,
      id:           row.dataset.id,
      status:       row.dataset.status,
      priority:     row.dataset.priority,
      objectiveId:  row.dataset.objectiveId,
      keyResultId:  row.dataset.krId || row.dataset.keyResultId,
      initiativeId: row.dataset.initiativeId,
      epicId:       row.dataset.epicId,
      sprintId:     row.dataset.sprintId,
      group:        row.dataset.group,
      isDone:       row.dataset.status === "done" || row.classList.contains("done"),
      title:        (row.querySelector(".task-text")?.textContent || "").trim(),
      dueLabel:     (row.querySelector(".due-chip")?.textContent || "").trim(),
      dueOverdue:   !!row.querySelector(".due-chip.overdue-label"),
    }));
  }

  /* ───── render a "ptv2-row" card for a task ─────────────────── */

  function rowCard(t, opts = {}) {
    const prio = ["high", "medium", "low"].includes(t.priority) ? t.priority : "medium";
    const div = document.createElement("div");
    div.className = `ptv2-row prio-${prio}${t.isDone ? " is-done" : ""}`;
    div.dataset.id = t.id;
    div.innerHTML = `
      <span class="ptv2-row-prio"></span>
      <button type="button" class="ptv2-row-check${t.isDone ? " is-checked" : ""}"
              aria-label="Toggle done">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
             stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </button>
      <div class="ptv2-row-main">
        <span class="ptv2-row-title" title="${esc(t.title)}">${esc(t.title) || "(untitled)"}</span>
        <div class="ptv2-row-meta">
          ${t.dueLabel ? `<span class="ptv2-row-due${t.dueOverdue ? " is-overdue" : ""}">${esc(t.dueLabel)}</span>` : ""}
          ${opts.crumb ? `<span class="ptv2-row-crumb">${esc(opts.crumb)}</span>` : ""}
        </div>
      </div>`;
    // Open detail when the card body is tapped — delegate to the
    // existing handler.
    div.addEventListener("click", (e) => {
      if (e.target.closest(".ptv2-row-check")) return;
      if (typeof openTaskDetail === "function") openTaskDetail(t.id);
    });
    // Toggle done — also delegate to the existing chain so server +
    // optimistic UI + recurrence all behave the same as the table.
    div.querySelector(".ptv2-row-check").addEventListener("click", (e) => {
      e.stopPropagation();
      const cb = t.el.querySelector("input.task-check");
      if (cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event("change", { bubbles: true })); }
      // Optimistic local class flip; the existing handler will sync the DOM.
      const becomes = !div.classList.contains("is-done");
      div.classList.toggle("is-done", becomes);
      div.querySelector(".ptv2-row-check").classList.toggle("is-checked", becomes);
      // Re-render the focus/done lists on the next tick so counts stay right.
      setTimeout(() => {
        if (document.body.dataset.activeTab === "focus") renderFocus();
        if (document.body.dataset.activeTab === "done")  renderDone();
      }, 250);
    });
    return div;
  }

  /* ───── crumb resolver: task -> "OKR ▸ Initiative" ──────────── */

  let _hierIndex = null;          // { objectivesById, initiativesById, epicsById }
  function indexHierarchy(tree) {
    const objectivesById  = new Map();
    const krsById         = new Map();
    const initiativesById = new Map();
    const epicsById       = new Map();
    for (const o of tree) {
      objectivesById.set(o.id, o);
      for (const kr of o.key_results || []) {
        krsById.set(kr.id, { ...kr, _okr: o });
        for (const it of kr.initiatives || []) {
          initiativesById.set(it.id, { ...it, _kr: kr, _okr: o });
          for (const ep of it.epics || []) {
            epicsById.set(ep.id, { ...ep, _init: it, _kr: kr, _okr: o });
          }
        }
      }
    }
    _hierIndex = { objectivesById, krsById, initiativesById, epicsById };
  }
  function crumbFor(t) {
    if (!_hierIndex) return "";
    const init = t.initiativeId && _hierIndex.initiativesById.get(t.initiativeId);
    if (init) return `${init._okr.title} ▸ ${init.title}`;
    const ep   = t.epicId && _hierIndex.epicsById.get(t.epicId);
    if (ep) return `${ep._okr.title} ▸ ${ep._init.title}`;
    const obj  = t.objectiveId && _hierIndex.objectivesById.get(t.objectiveId);
    if (obj) return obj.title;
    return "";
  }

  /* ───── FOCUS tab ───────────────────────────────────────────── */

  function renderFocus() {
    const tasks = readTasks().filter((t) => !t.isDone);
    const buckets = { overdue: [], today: [], upcoming: [] };
    for (const t of tasks) {
      // Tasks the server already classified into a group — we honor it,
      // but only the three Focus buckets we care about here.
      const g = (t.group || "").toLowerCase();
      const lbl = (t.dueLabel || "").toLowerCase();
      if (t.dueOverdue || g.includes("overdue") || lbl.includes("overdue")) {
        buckets.overdue.push(t);
      } else if (g.includes("today") || lbl === "today") {
        buckets.today.push(t);
      } else if (
        g.includes("this week") || g.includes("upcoming") ||
        ["tomorrow", "mon", "tue", "wed", "thu", "fri", "sat", "sun"].some((d) => lbl.startsWith(d))
      ) {
        buckets.upcoming.push(t);
      }
    }
    const lists = { overdue: "#list-overdue", today: "#list-today", upcoming: "#list-upcoming" };
    const counts = { overdue: "#ct-overdue", today: "#ct-today", upcoming: "#ct-upcoming" };
    for (const k of Object.keys(buckets)) {
      const el = document.querySelector(lists[k]);
      const cnt = document.querySelector(counts[k]);
      if (!el || !cnt) continue;
      el.innerHTML = "";
      buckets[k].forEach((t) => el.appendChild(rowCard(t, { crumb: crumbFor(t) })));
      cnt.textContent = String(buckets[k].length);
    }
    // Show / hide whole sections based on emptiness — keeps the page
    // tidy when one bucket is zero.
    ["overdue", "today", "upcoming"].forEach((k) => {
      const sec = document.getElementById(`ptv2-${k}`);
      if (sec) sec.hidden = buckets[k].length === 0;
    });
    const totalFocus = buckets.overdue.length + buckets.today.length + buckets.upcoming.length;
    const emptyEl = document.getElementById("ptv2-focus-empty");
    if (emptyEl) emptyEl.hidden = totalFocus > 0;

    // Header badges + project header counts.
    setBadge("focus", totalFocus);
  }

  /* ───── DONE tab ────────────────────────────────────────────── */

  function renderDone() {
    const tasks = readTasks().filter((t) => t.isDone);
    const list = document.getElementById("list-done");
    const cnt = document.getElementById("ct-done");
    const empty = document.getElementById("ptv2-done-empty");
    if (!list) return;
    list.innerHTML = "";
    tasks.forEach((t) => list.appendChild(rowCard(t, { crumb: crumbFor(t) })));
    if (cnt) cnt.textContent = String(tasks.length);
    if (empty) empty.hidden = tasks.length > 0;
    setBadge("done", tasks.length);
  }

  /* ───── TREE tab ────────────────────────────────────────────── */

  let _treeSel = { okrs: new Set(), inits: new Set(), epics: new Set() };
  let _treeData = [];
  let _sprints = [];                 // [{id,name,starts_on,ends_on,is_active,...}]
  let _sprintSel = new Set();        // checked sprint ids (multi-select filter)

  async function renderTreeIfNeeded() {
    if (_treeData.length === 0) await fetchTree();
    renderTree();
  }
  async function fetchTree() {
    if (!PROJECT_ID) return;
    try {
      const r = await fetch(`/api/projects/${PROJECT_ID}/hierarchy`, { credentials: "same-origin" });
      const j = await r.json();
      _treeData = j.tree || [];
      _sprints  = j.sprints || [];
      indexHierarchy(_treeData);
      renderSprintsBar();
      populateSprintPickers();
    } catch (e) { console.warn("[ptv2] tree fetch failed", e); }
  }

  /* ───── SPRINTS bar ─────────────────────────────────────────── */

  function renderSprintsBar() {
    const bar = document.getElementById("ptv2-sprints-bar");
    const list = document.getElementById("ptv2-sprints-list");
    if (!bar || !list) return;
    // Always show the bar so the user can create the first sprint.
    bar.hidden = false;
    list.innerHTML = "";
    if (!_sprints.length) {
      const hint = document.createElement("span");
      hint.style.cssText = "font-size:12px;color:var(--ptv2-text-soft);padding:0 4px";
      hint.textContent = "No sprints yet. Create one →";
      list.appendChild(hint);
    }
    // Count tasks per sprint from the current DOM (cheap, accurate).
    const counts = new Map();
    document.querySelectorAll("#task-tbody tr.task-row").forEach((row) => {
      const sid = row.dataset.sprintId;
      if (sid) counts.set(sid, (counts.get(sid) || 0) + 1);
    });
    for (const s of _sprints) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "ptv2-sprint-chip" + (_sprintSel.has(s.id) ? " is-active" : "") + (s.is_active ? " is-running" : "");
      const n = counts.get(s.id) || 0;
      chip.innerHTML = `<span class="dot"></span>${esc(s.name)}<span class="count">${n}</span>`;
      chip.addEventListener("click", () => {
        if (_sprintSel.has(s.id)) _sprintSel.delete(s.id);
        else _sprintSel.add(s.id);
        renderSprintsBar();
        applySprintFilter();
      });
      list.appendChild(chip);
    }
    if (window.feather) window.feather.replace();
  }

  // Hide / show task rows by sprint_id. Returns visible count.
  function applySprintFilter() {
    const rows = document.querySelectorAll("#task-tbody tr.task-row");
    rows.forEach((row) => {
      if (!_sprintSel.size) { row.style.removeProperty("display"); return; }
      row.style.display = _sprintSel.has(row.dataset.sprintId) ? "" : "none";
    });
    // Re-render focus/done/tree-tasks since they read from the table.
    if (document.body.dataset.activeTab === "focus") renderFocus();
    if (document.body.dataset.activeTab === "done")  renderDone();
    if (document.body.dataset.activeTab === "tree")  renderTreeTasks();
    updateHeaderCounts();
  }

  function populateSprintPickers() {
    // The add-task picker AND the detail-panel picker.
    const opts = ['<option value="">No sprint</option>']
      .concat(_sprints.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}${s.is_active ? " (active)" : ""}</option>`));
    for (const id of ["add-task-sprint", "sheet-sprint"]) {
      const sel = document.getElementById(id);
      if (!sel) continue;
      const cur = sel.value;
      sel.innerHTML = opts.join("");
      if (cur && sel.querySelector(`option[value="${cur}"]`)) sel.value = cur;
    }
  }

  /* ───── SPRINT TAB ──────────────────────────────────────────── */

  async function renderSprintsTab() {
    const board = document.getElementById("ptv2-sprints-board");
    const empty = document.getElementById("ptv2-sprints-empty");
    if (!board) return;
    if (!_sprints.length) {
      empty.hidden = false;
      board.innerHTML = "";
      setBadge("sprints", 0);
      return;
    }
    empty.hidden = true;
    board.innerHTML = "";
    // Group tasks by sprint_id from the existing DOM.
    const tasksBySprint = new Map();
    for (const s of _sprints) tasksBySprint.set(s.id, []);
    const unassigned = [];
    for (const t of readTasks()) {
      if (t.isDone) continue;
      if (t.sprintId && tasksBySprint.has(t.sprintId)) {
        tasksBySprint.get(t.sprintId).push(t);
      } else {
        unassigned.push(t);
      }
    }
    setBadge("sprints", _sprints.length);

    for (const s of _sprints) {
      board.appendChild(sprintCard(s, tasksBySprint.get(s.id) || []));
    }
    // Drop-zone for "unassigned" so users can drag tasks out of all sprints.
    board.appendChild(sprintCard({ id: null, name: "Unassigned", _virtual: true },
      unassigned, { virtual: true }));
    if (window.feather) window.feather.replace();
    // Stats are async — kick off per-sprint fetches.
    _sprints.forEach((s) => fetchAndRenderSprintStats(s.id));
  }

  function sprintCard(s, tasks, opts = {}) {
    const card = document.createElement("article");
    card.className = "ptv2-sprint-card" + (s.is_active ? " is-active" : "");
    card.dataset.sprintId = s.id || "";
    const dates = s._virtual ? "" : sprintDateLabel(s);
    const activeBadge = s.is_active ? `<span class="badge">Active</span>` : "";
    card.innerHTML = `
      <header>
        <h3>${esc(s.name)}${activeBadge}</h3>
        <span class="dates">${esc(dates)}</span>
        ${s._virtual ? "" : `<button type="button" class="rollover" data-action="rollover">Roll over →</button>`}
      </header>
      ${s._virtual ? "" : `
        <div class="ptv2-sprint-progress">
          <span class="nums" data-stats>0 / 0 · 0%</span>
          <div class="bar"><span class="fill" style="width:0%"></span></div>
          <svg class="spark" width="100" height="20" viewBox="0 0 100 20" aria-hidden="true"
               style="opacity:0.6"></svg>
        </div>`}
      <div class="ptv2-sprint-tasks" data-tasks></div>`;

    // Render tasks
    const taskWrap = card.querySelector("[data-tasks]");
    tasks.forEach((t) => {
      const tile = rowCard(t, { crumb: crumbFor(t) });
      tile.draggable = true;
      tile.addEventListener("dragstart", (e) => {
        try { e.dataTransfer.setData("text/plain", t.id); } catch (_) {}
        e.dataTransfer.effectAllowed = "move";
        card.classList.add("is-source");
      });
      tile.addEventListener("dragend", () => card.classList.remove("is-source"));
      taskWrap.appendChild(tile);
    });

    // Make whole card a drop target.
    card.addEventListener("dragover", (e) => {
      if (!e.dataTransfer.types.includes("text/plain")) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      card.classList.add("is-drop-target");
    });
    card.addEventListener("dragleave", (e) => {
      // Only clear when leaving the card itself, not children.
      if (e.target === card) card.classList.remove("is-drop-target");
    });
    card.addEventListener("drop", async (e) => {
      e.preventDefault();
      card.classList.remove("is-drop-target");
      const taskId = (e.dataTransfer.getData("text/plain") || "").trim();
      if (!taskId) return;
      const targetSprint = s.id || null;
      try {
        const r = await _fetch(`/projects/tasks/${taskId}/update`, {
          method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
          credentials: "same-origin",
          body: JSON.stringify({ sprint_id: targetSprint || "" }),
        });
        if (!r.ok) throw new Error("update failed");
        // Patch the DOM data-attr so re-render picks up the change.
        const row = document.querySelector(`#task-tbody tr.task-row[data-id="${taskId}"]`);
        if (row) row.dataset.sprintId = targetSprint || "";
        renderSprintsTab();
        renderSprintsBar();
      } catch (err) { console.error("[ptv2] sprint move failed", err); }
    });

    // Rollover handler
    card.querySelector('[data-action="rollover"]')?.addEventListener("click", () => promptRollover(s));

    return card;
  }

  function sprintDateLabel(s) {
    if (s.starts_on && s.ends_on) return `${s.starts_on} → ${s.ends_on}`;
    if (s.starts_on) return `from ${s.starts_on}`;
    if (s.ends_on)   return `due ${s.ends_on}`;
    return "no dates";
  }

  function csrf() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  async function fetchAndRenderSprintStats(sprintId) {
    try {
      const r = await fetch(`/api/sprints/${sprintId}/stats`, { credentials: "same-origin" });
      if (!r.ok) return;
      const j = await r.json();
      const card = document.querySelector(`.ptv2-sprint-card[data-sprint-id="${sprintId}"]`);
      if (!card) return;
      const nums = card.querySelector("[data-stats]");
      const fill = card.querySelector(".ptv2-sprint-progress .fill");
      const spark = card.querySelector("svg.spark");
      const pct = Math.round((j.pct || 0) * 100);
      if (nums) nums.textContent = `${j.done} / ${j.total} · ${pct}%`;
      if (fill) fill.style.width = `${pct}%`;
      if (spark && j.by_day) renderSparkline(spark, j.by_day);
    } catch (_) {}
  }

  function renderSparkline(svg, points) {
    // 100x20 viewBox, 14 buckets -> bar width ~6, gap 1
    svg.innerHTML = "";
    const max = Math.max(1, ...points.map((p) => p.done));
    const barW = 100 / points.length - 1;
    points.forEach((p, i) => {
      const h = (p.done / max) * 18;
      const x = i * (barW + 1);
      const y = 20 - h;
      const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      r.setAttribute("x", x.toFixed(2));
      r.setAttribute("y", y.toFixed(2));
      r.setAttribute("width", barW.toFixed(2));
      r.setAttribute("height", Math.max(1, h).toFixed(2));
      r.setAttribute("fill", "var(--ptv2-primary)");
      r.setAttribute("rx", "1");
      r.append(document.createElementNS("http://www.w3.org/2000/svg", "title"));
      r.lastChild.textContent = `${p.date}: ${p.done} done`;
      svg.appendChild(r);
    });
  }

  async function promptRollover(s) {
    const others = _sprints.filter((x) => x.id !== s.id);
    if (!others.length) {
      if (confirm(`No other sprint to move to. Unassign all unfinished tasks from "${s.name}"?`)) {
        await rolloverSprint(s.id, null);
      }
      return;
    }
    // Build a quick picker via prompt — keeps the implementation small.
    const labels = others.map((x, i) => `${i + 1}. ${x.name}${x.is_active ? " (active)" : ""}`).join("\n");
    const choice = prompt(`Roll over unfinished tasks from "${s.name}" to:\n\n${labels}\n0. Unassign\n\nEnter the number:`);
    if (choice == null) return;
    const idx = parseInt(choice, 10);
    if (isNaN(idx) || idx < 0 || idx > others.length) return;
    const targetId = idx === 0 ? null : others[idx - 1].id;
    await rolloverSprint(s.id, targetId);
  }
  async function rolloverSprint(srcId, targetId) {
    const r = await _fetch(`/api/sprints/${srcId}/rollover`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ target_sprint_id: targetId }),
    });
    if (!r.ok) {
      alert("Rollover failed");
      return;
    }
    // Update all matching rows' data-sprint-id so the UI reflects without a reload.
    document.querySelectorAll(`#task-tbody tr.task-row[data-sprint-id="${srcId}"]`).forEach((row) => {
      if (row.dataset.status !== "done") row.dataset.sprintId = targetId || "";
    });
    renderSprintsTab();
    renderSprintsBar();
  }

  /* ───── inline sprint manager ───────────────────────────────── */

  function openSprintManager() {
    const sheet = document.getElementById("ptv2-spm");
    if (!sheet) return;
    sheet.hidden = false;
    renderSprintManager();
  }
  function closeSprintManager() {
    const sheet = document.getElementById("ptv2-spm");
    if (sheet) sheet.hidden = true;
  }
  function renderSprintManager() {
    const body = document.getElementById("ptv2-spm-body");
    if (!body) return;
    body.innerHTML = "";
    for (const s of _sprints) {
      const row = document.createElement("div");
      row.className = "ptv2-spm-row";
      row.dataset.sprintId = s.id;
      row.innerHTML = `
        <input type="text" value="${esc(s.name)}" data-field="name" maxlength="80">
        <input type="date" value="${esc(s.starts_on || "")}" data-field="starts_on">
        <input type="date" value="${esc(s.ends_on || "")}" data-field="ends_on">
        <button type="button" class="spm-act is-active-toggle ${s.is_active ? "is-on" : ""}"
                title="Active sprint (drives default picker order)">${s.is_active ? "●" : "○"}</button>
        <button type="button" class="spm-act danger" title="Delete">×</button>`;
      row.querySelectorAll("input").forEach((inp) => {
        const commit = () => updateSprint(s.id, { [inp.dataset.field]: inp.value });
        inp.addEventListener("change", commit);
        inp.addEventListener("blur", commit);
      });
      row.querySelector(".is-active-toggle").addEventListener("click", () => updateSprint(s.id, { is_active: !s.is_active }));
      row.querySelector(".danger").addEventListener("click", () => {
        if (confirm(`Delete sprint "${s.name}"? Tasks keep their pointer.`)) deleteSprint(s.id);
      });
      body.appendChild(row);
    }
    const add = document.createElement("button");
    add.type = "button";
    add.className = "ptv2-spm-add";
    add.textContent = "+ Add sprint";
    add.addEventListener("click", () => createSprint());
    body.appendChild(add);
  }

  async function createSprint(name) {
    const r = await _fetch("/api/sprints", {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ project_id: PROJECT_ID, name: name || "" }),
    });
    if (r.ok) await refreshSprints();
  }
  async function updateSprint(id, patch) {
    const r = await _fetch(`/api/sprints/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(patch),
    });
    if (r.ok) await refreshSprints();
  }
  async function deleteSprint(id) {
    const r = await _fetch(`/api/sprints/${id}`, {
      method: "DELETE", credentials: "same-origin",
    });
    if (r.ok) {
      _sprintSel.delete(id);
      await refreshSprints();
    }
  }
  async function refreshSprints() {
    try {
      const r = await fetch(`/api/projects/${PROJECT_ID}/sprints`, { credentials: "same-origin" });
      const j = await r.json();
      _sprints = j.sprints || [];
      renderSprintsBar();
      renderSprintManager();
      populateSprintPickers();
    } catch (_) {}
  }
  function renderTree() {
    const colOkr  = document.querySelector('.ptv2-tree-col[data-col="okr"]');
    const colInit = document.querySelector('.ptv2-tree-col[data-col="init"]');
    const colEpic = document.querySelector('.ptv2-tree-col[data-col="epic"]');
    if (!colOkr) return;

    // ── OKR column ──
    colOkr.innerHTML = `<h3>OKR</h3>`;
    colOkr.appendChild(createInline("+ New OKR", () => promptCreateOkr()));
    if (!_treeData.length) {
      colOkr.appendChild(empty("No OKRs yet."));
    } else {
      for (const o of _treeData) {
        const krCt = (o.key_results || []).length;
        const itCt = (o.key_results || []).reduce((n, kr) => n + (kr.initiatives || []).length, 0);
        colOkr.appendChild(treeRow({
          label: o.title, sub: `${krCt} KR · ${itCt} init`,
          isDefault: !!o.is_default,
          checked: _treeSel.okrs.has(o.id),
          onToggle: (v) => {
            v ? _treeSel.okrs.add(o.id) : _treeSel.okrs.delete(o.id);
            if (!v) {
              for (const kr of o.key_results || [])
                for (const it of kr.initiatives || []) {
                  _treeSel.inits.delete(it.id);
                  for (const ep of it.epics || []) _treeSel.epics.delete(ep.id);
                }
            }
            renderTree(); renderTreeTasks();
          },
        }));
      }
    }

    // ── Initiative column ──
    colInit.innerHTML = `<h3>Initiative</h3>`;
    const initsByOkr = new Map();
    for (const o of _treeData) {
      if (_treeSel.okrs.size && !_treeSel.okrs.has(o.id)) continue;
      const inits = [];
      for (const kr of o.key_results || [])
        for (const it of kr.initiatives || []) inits.push({ it, kr });
      if (inits.length) initsByOkr.set(o, inits);
    }
    if (!initsByOkr.size) {
      colInit.appendChild(empty(_treeSel.okrs.size ? "No initiatives under selected OKRs." : "Select an OKR to see initiatives."));
    } else {
      for (const [o, inits] of initsByOkr) {
        colInit.insertAdjacentHTML("beforeend", `<div class="ptv2-section-h" style="margin-top:8px"><span class="ptv2-section-dot ptv2-dot--primary"></span>${esc(o.title)}</div>`);
        for (const { it, kr } of inits) {
          const epCt = (it.epics || []).length;
          colInit.appendChild(treeRow({
            label: it.title, sub: `KR: ${kr.title} · ${epCt} epic`,
            isDefault: !!it.is_default,
            checked: _treeSel.inits.has(it.id),
            onToggle: (v) => {
              v ? _treeSel.inits.add(it.id) : _treeSel.inits.delete(it.id);
              if (!v) for (const ep of it.epics || []) _treeSel.epics.delete(ep.id);
              renderTree(); renderTreeTasks();
            },
          }));
        }
      }
    }
    appendInitiativeCreator(colInit);

    // ── Epic column ──
    colEpic.innerHTML = `<h3>Epic</h3>`;
    const activeInits = [];
    for (const o of _treeData)
      for (const kr of o.key_results || [])
        for (const it of kr.initiatives || []) {
          if (_treeSel.okrs.size && !_treeSel.okrs.has(o.id)) continue;
          if (_treeSel.inits.size && !_treeSel.inits.has(it.id)) continue;
          activeInits.push(it);
        }
    if (!activeInits.length) {
      colEpic.appendChild(empty("Select an initiative to see epics."));
    } else {
      let any = false;
      for (const it of activeInits) {
        if (!(it.epics || []).length) continue;
        any = true;
        colEpic.insertAdjacentHTML("beforeend", `<div class="ptv2-section-h" style="margin-top:8px"><span class="ptv2-section-dot ptv2-dot--muted"></span>${esc(it.title)}</div>`);
        for (const ep of it.epics) {
          colEpic.appendChild(treeRow({
            label: ep.title, sub: ep.description ? ep.description.slice(0, 80) : null,
            isDefault: !!ep.is_default,
            checked: _treeSel.epics.has(ep.id),
            onToggle: (v) => {
              v ? _treeSel.epics.add(ep.id) : _treeSel.epics.delete(ep.id);
              renderTreeTasks();
            },
          }));
        }
      }
      if (!any) colEpic.appendChild(empty("No epics yet under these initiatives."));
    }
    appendEpicCreator(colEpic, activeInits);

    renderTreeTasks();
    if (window.feather) window.feather.replace();
  }
  function renderTreeTasks() {
    const list = document.getElementById("list-tree-tasks");
    const cnt = document.getElementById("ct-tree-tasks");
    const hint = document.getElementById("tree-tasks-hint");
    if (!list) return;

    const tasks = readTasks().filter((t) => !t.isDone);
    const anyFilter = _treeSel.okrs.size || _treeSel.inits.size || _treeSel.epics.size;
    let visible = tasks;
    if (anyFilter) {
      // Resolve which init/epic ids are valid under selected OKRs.
      const okrInits = new Set(), okrEpics = new Set();
      if (_treeSel.okrs.size) {
        for (const o of _treeData) {
          if (!_treeSel.okrs.has(o.id)) continue;
          for (const kr of o.key_results || [])
            for (const it of kr.initiatives || []) {
              okrInits.add(it.id);
              for (const ep of it.epics || []) okrEpics.add(ep.id);
            }
        }
      }
      visible = tasks.filter((t) => {
        if (_treeSel.epics.size && _treeSel.epics.has(t.epicId)) return true;
        if (_treeSel.epics.size) return false;
        if (_treeSel.inits.size && _treeSel.inits.has(t.initiativeId)) return true;
        if (_treeSel.inits.size) return false;
        if (_treeSel.okrs.size) {
          return _treeSel.okrs.has(t.objectiveId)
              || okrInits.has(t.initiativeId)
              || okrEpics.has(t.epicId);
        }
        return true;
      });
    }
    list.innerHTML = "";
    visible.forEach((t) => list.appendChild(rowCard(t, { crumb: crumbFor(t) })));
    if (cnt) cnt.textContent = String(visible.length);
    if (hint) {
      const bits = [];
      if (_treeSel.okrs.size)  bits.push(`${_treeSel.okrs.size} OKR`);
      if (_treeSel.inits.size) bits.push(`${_treeSel.inits.size} init`);
      if (_treeSel.epics.size) bits.push(`${_treeSel.epics.size} epic`);
      hint.textContent = bits.length ? `Filtered: ${bits.join(" · ")}` : "All tasks in project";
    }
  }

  function treeRow({ label, sub, checked, onToggle, isDefault }) {
    const d = document.createElement("div");
    d.className = "okrc-row" + (isDefault ? " is-default" : "");
    d.style.cssText = "display:flex;align-items:center;gap:8px;padding:8px 6px;border-radius:8px";
    const badge = isDefault
      ? `<span title="Default catch-all — receives tasks created without an Epic"
            style="display:inline-block;background:var(--ptv2-primary-soft);color:var(--ptv2-primary);
                   font-size:10px;font-weight:700;padding:1px 7px;border-radius:999px;margin-left:6px;
                   text-transform:uppercase;letter-spacing:0.04em">Default</span>` : "";
    d.innerHTML = `
      <label style="display:flex;align-items:center;gap:10px;flex:1;cursor:pointer">
        <input type="checkbox" ${checked ? "checked" : ""} style="width:16px;height:16px;accent-color:var(--ptv2-primary)">
        <span><span style="font-size:14px;font-weight:600;color:var(--ptv2-text);display:block">${esc(label)}${badge}</span>
        ${sub ? `<span style="font-size:11px;color:var(--ptv2-text-mute)">${esc(sub)}</span>` : ""}</span>
      </label>`;
    d.querySelector("input").addEventListener("change", (e) => onToggle(e.target.checked));
    return d;
  }
  function empty(msg) {
    const d = document.createElement("div");
    d.textContent = msg;
    d.style.cssText = "padding:18px 8px;text-align:center;color:var(--ptv2-text-soft);font-size:13px";
    return d;
  }
  function createInline(label, onClick) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.style.cssText = "width:100%;padding:9px 12px;background:var(--ptv2-primary-soft);color:var(--ptv2-primary);border:1px dashed var(--ptv2-primary);border-radius:10px;font-weight:600;cursor:pointer;margin-bottom:10px";
    b.addEventListener("click", onClick);
    return b;
  }
  function appendInitiativeCreator(col) {
    // Exclude KRs that belong to the default OKR — server rejects
    // those anyway. If nothing is left, surface a hint instead so the
    // user knows they need to create an OKR first.
    const krs = [];
    for (const o of _treeData) {
      if (o.is_default) continue;
      if (_treeSel.okrs.size && !_treeSel.okrs.has(o.id)) continue;
      for (const kr of o.key_results || []) {
        if (kr.is_default) continue;
        krs.push({ kr, o });
      }
    }
    if (!krs.length) {
      col.appendChild(creatorHint(
        "To add an Initiative, create a new OKR (above) first — defaults can't have children."
      ));
      return;
    }
    const wrap = inlineCreator({
      placeholder: "New initiative…",
      options: krs.map(({ kr, o }) => ({ id: kr.id, label: `${o.title} ▸ ${kr.title}` })),
      submit: async (title, parentId) => {
        const r = await _fetch("/api/initiatives", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, key_result_id: parentId }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          alert(body.error || "Couldn't create initiative");
          return;
        }
        await fetchTree(); renderTree();
      },
    });
    col.appendChild(wrap);
  }
  function appendEpicCreator(col, inits) {
    // Drop default initiatives from the picker (server-side enforced).
    const userInits = inits.filter((it) => !it.is_default);
    if (!userInits.length) {
      col.appendChild(creatorHint(
        "To add an Epic, create a new Initiative (above) first — defaults can't have children."
      ));
      return;
    }
    const wrap = inlineCreator({
      placeholder: "New epic…",
      options: userInits.map((it) => ({ id: it.id, label: it.title })),
      submit: async (title, parentId) => {
        const r = await _fetch("/api/epics", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, initiative_id: parentId }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          alert(body.error || "Couldn't create epic");
          return;
        }
        await fetchTree(); renderTree();
      },
    });
    col.appendChild(wrap);
  }
  function creatorHint(msg) {
    const d = document.createElement("div");
    d.textContent = msg;
    d.style.cssText = "margin-top:12px;padding:10px 12px;background:var(--ptv2-primary-soft);"
                    + "color:var(--ptv2-text-mute);font-size:12px;border-radius:10px;line-height:1.4";
    return d;
  }
  function inlineCreator({ placeholder, options, submit }) {
    const wrap = document.createElement("div");
    wrap.style.cssText = "display:flex;gap:6px;margin-top:12px;padding-top:12px;border-top:1px dashed var(--ptv2-border)";
    wrap.innerHTML = `
      <input type="text" placeholder="${esc(placeholder)}" style="flex:1;padding:7px 10px;border:1px solid var(--ptv2-border);border-radius:8px;font-size:13px;background:var(--ptv2-surface);color:var(--ptv2-text)">
      <select style="padding:7px 8px;border:1px solid var(--ptv2-border);border-radius:8px;font-size:12px;max-width:46%;background:var(--ptv2-surface);color:var(--ptv2-text)">
        ${options.map((o) => `<option value="${esc(o.id)}">${esc(o.label)}</option>`).join("")}
      </select>
      <button type="button" style="background:var(--ptv2-success);color:#fff;border:0;border-radius:8px;padding:0 12px;font-weight:700;font-size:16px;cursor:pointer">+</button>`;
    const input = wrap.querySelector("input");
    const select = wrap.querySelector("select");
    const button = wrap.querySelector("button");
    const fire = async () => {
      const t = input.value.trim(); if (!t) return;
      button.disabled = true;
      try { await submit(t, select.value); input.value = ""; }
      finally { button.disabled = false; }
    };
    button.addEventListener("click", fire);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") fire(); });
    return wrap;
  }
  async function promptCreateOkr() {
    const title = prompt("New OKR title:");
    if (!title || !title.trim()) return;
    const krTitle = prompt("First Key Result (leave blank to skip):");
    try {
      const r = await _fetch("/api/goals", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(), project_id: PROJECT_ID, status: "active",
          time_horizon: "quarterly",
        }),
      });
      const data = await r.json();
      const obj = data.objective || data;
      if (krTitle && krTitle.trim() && obj && obj.id) {
        await _fetch("/api/key-results", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: krTitle.trim(), objective_id: obj.id,
            target_value: 100, unit: "%",
          }),
        });
      }
      await fetchTree(); renderTree();
    } catch (e) { alert("Couldn't create OKR — check connection."); }
  }

  /* ───── ⋯ menu, density, add-bar expand, header counts ──────── */

  function ptv2CloseMenu() {
    const pop = document.getElementById("ptv2-menu-pop");
    if (pop) pop.hidden = true;
  }
  window.ptv2CloseMenu = ptv2CloseMenu;
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("#ptv2-menu");
    const pop = document.getElementById("ptv2-menu-pop");
    if (btn && pop) { pop.hidden = !pop.hidden; e.stopPropagation(); return; }
    if (pop && !pop.hidden && !e.target.closest("#ptv2-menu-pop")) pop.hidden = true;
  });

  const DENSITIES = ["comfortable", "cozy", "compact"];
  function getDensity() { return localStorage.getItem("ptv2-density") || "cozy"; }
  function applyDensity(d) {
    document.documentElement.setAttribute("data-density", d);
    const lbl = document.getElementById("ptv2-density-label");
    if (lbl) lbl.textContent = d;
  }
  window.ptv2CycleDensity = function () {
    const cur = getDensity();
    const next = DENSITIES[(DENSITIES.indexOf(cur) + 1) % DENSITIES.length];
    localStorage.setItem("ptv2-density", next);
    applyDensity(next);
  };

  const addToggle = document.getElementById("ptv2-add-toggle");
  const addMore   = document.getElementById("ptv2-add-more");
  if (addToggle && addMore) {
    addToggle.addEventListener("click", () => {
      const open = addMore.hidden;
      addMore.hidden = !open;
      addToggle.setAttribute("aria-expanded", String(open));
    });
  }

  function setBadge(name, n) {
    const el = document.getElementById(`badge-${name}`);
    if (!el) return;
    if (n > 0) { el.textContent = String(n); }
    else el.textContent = "";
  }
  function updateHeaderCounts() {
    const all = readTasks();
    const done = all.filter((t) => t.isDone).length;
    const overdue = all.filter((t) => !t.isDone && t.dueOverdue).length;
    const total = all.length;
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
    setText("stat-done", done);
    setText("stat-total", total);
    setText("stat-overdue", overdue);
    const fill = document.getElementById("proj-progress-fill");
    if (fill) fill.style.width = total ? `${Math.round((done / total) * 100)}%` : "0%";
    setBadge("all", total - done);
  }

  /* ───── helpers ─────────────────────────────────────────────── */

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* ───── boot ─────────────────────────────────────────────────── */

  document.addEventListener("DOMContentLoaded", async () => {
    applyDensity(getDensity());
    updateHeaderCounts();
    await fetchTree();        // hierarchy + sprints in one round trip
    setTab(activeTab(), { skipHash: true });

    document.getElementById("ptv2-sprints-add")?.addEventListener("click", () => createSprint());
    document.getElementById("ptv2-sprints-mgr")?.addEventListener("click", openSprintManager);
    document.getElementById("ptv2-spm-close")?.addEventListener("click", closeSprintManager);

    if (window.feather) window.feather.replace();
  });

  // Re-render after server-driven re-renders that the existing code
  // might trigger (e.g., status changes, bulk updates).
  const obs = new MutationObserver(() => {
    updateHeaderCounts();
    if (document.body.dataset.activeTab === "focus") renderFocus();
    if (document.body.dataset.activeTab === "done")  renderDone();
    if (document.body.dataset.activeTab === "tree")  renderTreeTasks();
  });
  const tbody = document.getElementById("task-tbody");
  if (tbody) obs.observe(tbody, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "data-status"] });
})();

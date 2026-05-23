/* DailyPlanner — OKR cascading filter + manager for project tasks.

   Replaces the old pt-shared filter sheet + OKR manager with a single
   mobile-first cascading drawer. Tree:

     Project ─▸ OKR (objective) ─▸ KR ─▸ Initiative ─▸ Epic ─▸ Task

   "OKR" here = one objective. Selecting an OKR rolls in initiatives
   under all its KRs (we keep KRs as internal grouping headers inside
   the Initiative column).

   UX
     - Desktop (>= 900 px):  three columns side by side (OKR / Init / Epic)
                             with checkboxes + inline "+" add button.
     - Mobile  (<  900 px):  a single-column drawer that drills:
                                Stage 0: OKR list
                                Stage 1: Initiatives under selected OKRs
                                Stage 2: Epics under selected initiatives
                             Back arrow returns; "Done" closes drawer.
     - Filter cascades:
         0 OKR selected            → no filtering (show all tasks)
         OKR(s) selected, no inits → all initiatives under those OKRs
         + inits selected          → only those initiatives
         + epics selected          → only those epics
       Orphan tasks (no init/epic/kr/objective) are hidden when ANY
       filter is active; toggle below shows them on demand.

   Selection is persisted per project in localStorage AND mirrored to
   the URL hash so a shared link reopens the same view.

   Server contracts (already in routes/goals.py + projects.py):
     GET  /api/projects/<id>/hierarchy          tree of {okrs[KRs[Inits[Epics]]]}
     POST /api/goals                            create objective
     POST /api/key-results                      create KR
     POST /api/initiatives                      create initiative
     POST /api/epics                            create epic                       */

(function () {
  "use strict";

  if (!document.getElementById("pt-okr-btn")) return;     // only on /projects/<id>/tasks

  /* ───── state ───────────────────────────────────────────────── */

  const PROJECT_ID = (document.getElementById("add-task-input") || {}).dataset?.projectId
                  || (location.pathname.match(/\/projects\/([^/]+)\/tasks/) || [])[1];
  if (!PROJECT_ID) return;

  const LS_KEY = `dp-okr-cascade:${PROJECT_ID}`;
  const _fetch = window.dpFetch || ((u, o) => fetch(u, o));

  const sel = {
    okrs:  new Set(),
    inits: new Set(),
    epics: new Set(),
    showOrphans: true,
  };
  let tree = [];          // raw hierarchy from API
  let stage = 0;          // mobile drawer stage 0|1|2

  /* ───── persistence ─────────────────────────────────────────── */

  function loadState() {
    // URL hash wins (links carry view); fall back to localStorage.
    const fromUrl = parseHash(location.hash);
    if (fromUrl) return applyState(fromUrl);
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) applyState(JSON.parse(raw));
    } catch (_) {}
  }
  function saveState() {
    const s = {
      o: [...sel.okrs], i: [...sel.inits], e: [...sel.epics],
      orph: sel.showOrphans,
    };
    try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch (_) {}
    // Hash mirror — short keys so the URL stays readable.
    const params = new URLSearchParams();
    if (s.o.length) params.set("o", s.o.join(","));
    if (s.i.length) params.set("i", s.i.join(","));
    if (s.e.length) params.set("e", s.e.join(","));
    if (!s.orph)    params.set("orph", "0");
    const hash = params.toString();
    history.replaceState(null, "", hash ? `#${hash}` : location.pathname + location.search);
  }
  function applyState(s) {
    if (!s) return;
    sel.okrs  = new Set(s.o || s.okrs  || []);
    sel.inits = new Set(s.i || s.inits || []);
    sel.epics = new Set(s.e || s.epics || []);
    sel.showOrphans = s.orph === undefined ? true : !!parseInt(s.orph, 10);
  }
  function parseHash(h) {
    if (!h || h.length < 2) return null;
    const p = new URLSearchParams(h.slice(1));
    if (!p.has("o") && !p.has("i") && !p.has("e") && !p.has("orph")) return null;
    return {
      o: p.get("o") ? p.get("o").split(",") : [],
      i: p.get("i") ? p.get("i").split(",") : [],
      e: p.get("e") ? p.get("e").split(",") : [],
      orph: p.get("orph") === null ? 1 : p.get("orph"),
    };
  }

  /* ───── fetch ───────────────────────────────────────────────── */

  async function refreshHierarchy() {
    try {
      const r = await fetch(`/api/projects/${PROJECT_ID}/hierarchy`, { credentials: "same-origin" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      tree = j.tree || [];
      pruneInvalidSelections();
      populateAddTaskDropdowns();
      applyFilter();
      updateSummary();
    } catch (e) {
      console.warn("[okr_cascade] hierarchy fetch failed", e);
    }
  }
  function pruneInvalidSelections() {
    // Drop selections whose ids no longer exist (after deletion / restore).
    const okrIds  = new Set();
    const initIds = new Set();
    const epicIds = new Set();
    for (const o of tree) {
      okrIds.add(o.id);
      for (const kr of o.key_results || []) {
        for (const it of kr.initiatives || []) {
          initIds.add(it.id);
          for (const ep of it.epics || []) epicIds.add(ep.id);
        }
      }
    }
    for (const id of sel.okrs)  if (!okrIds.has(id))  sel.okrs.delete(id);
    for (const id of sel.inits) if (!initIds.has(id)) sel.inits.delete(id);
    for (const id of sel.epics) if (!epicIds.has(id)) sel.epics.delete(id);
  }

  /* ───── derive what's visible at each level ─────────────────── */

  function visibleInitiatives() {
    // If no OKR selected, show initiatives of every OKR (no filter active).
    const out = [];
    for (const o of tree) {
      if (sel.okrs.size && !sel.okrs.has(o.id)) continue;
      for (const kr of o.key_results || []) {
        for (const it of kr.initiatives || []) {
          out.push(Object.assign({}, it, { _kr: kr, _okr: o }));
        }
      }
    }
    return out;
  }
  function visibleEpics() {
    const inits = visibleInitiatives();
    const activeInits = sel.inits.size
      ? new Set([...sel.inits].filter((id) => inits.some((it) => it.id === id)))
      : new Set(inits.map((it) => it.id));
    const out = [];
    for (const it of inits) {
      if (!activeInits.has(it.id)) continue;
      for (const ep of it.epics || []) out.push(Object.assign({}, ep, { _init: it }));
    }
    return out;
  }

  /* ───── filter visible tasks (DOM-level) ────────────────────── */

  function applyFilter() {
    const rows = document.querySelectorAll(".task, .task-row, .pt-card");
    if (!rows.length) return;

    const okrActive  = sel.okrs.size > 0;
    const initActive = sel.inits.size > 0;
    const epicActive = sel.epics.size > 0;
    const anyFilter  = okrActive || initActive || epicActive;

    // Pre-resolve which initiative_ids belong to selected OKRs (so a row
    // with only initiative_id can still be matched).
    const okrInitiativeIds = new Set();
    if (okrActive) {
      for (const o of tree) {
        if (!sel.okrs.has(o.id)) continue;
        for (const kr of o.key_results || [])
          for (const it of kr.initiatives || []) okrInitiativeIds.add(it.id);
      }
    }
    // Same for OKR → epics
    const okrEpicIds = new Set();
    if (okrActive) {
      for (const o of tree) {
        if (!sel.okrs.has(o.id)) continue;
        for (const kr of o.key_results || [])
          for (const it of kr.initiatives || [])
            for (const ep of it.epics || []) okrEpicIds.add(ep.id);
      }
    }
    // initiative -> epics for the case "init selected but task has only epic_id"
    const initEpicIds = new Set();
    if (initActive) {
      for (const o of tree)
        for (const kr of o.key_results || [])
          for (const it of kr.initiatives || []) {
            if (!sel.inits.has(it.id)) continue;
            for (const ep of it.epics || []) initEpicIds.add(ep.id);
          }
    }

    let shown = 0, hidden = 0;
    rows.forEach((row) => {
      const ds = row.dataset || {};
      const taskOkr  = ds.objectiveId || ds.objective || "";
      const taskInit = ds.initiativeId || ds.initiative || "";
      const taskEpic = ds.epicId || "";
      const isOrphan = !taskOkr && !taskInit && !taskEpic;

      let visible = true;
      if (anyFilter) {
        if (isOrphan) {
          visible = sel.showOrphans;
        } else {
          // OKR gate
          if (okrActive) {
            visible = sel.okrs.has(taskOkr)
                   || okrInitiativeIds.has(taskInit)
                   || okrEpicIds.has(taskEpic);
          }
          // Initiative gate (narrower)
          if (visible && initActive) {
            visible = sel.inits.has(taskInit) || initEpicIds.has(taskEpic);
          }
          // Epic gate (narrowest)
          if (visible && epicActive) {
            visible = sel.epics.has(taskEpic);
          }
        }
      }
      row.style.display = visible ? "" : "none";
      visible ? shown++ : hidden++;
    });

    // Update any group header counts if present (best-effort, no-op
    // when the page uses a flat list).
    document.querySelectorAll("[data-task-group]").forEach((grp) => {
      const visibleKids = grp.querySelectorAll(".task-row:not([style*='display: none']), .pt-card:not([style*='display: none'])").length;
      grp.style.display = visibleKids === 0 && anyFilter ? "none" : "";
    });
  }

  function updateSummary() {
    const el = document.getElementById("pt-okr-summary");
    if (!el) return;
    const total = sel.okrs.size + sel.inits.size + sel.epics.size;
    if (total === 0) { el.style.display = "none"; return; }
    el.style.display = "";
    el.textContent = `${sel.okrs.size}/${sel.inits.size}/${sel.epics.size}`;
    el.title = `${sel.okrs.size} OKR · ${sel.inits.size} Init · ${sel.epics.size} Epic selected`;
  }

  function populateAddTaskDropdowns() {
    // Initiative dropdown — only initiatives under selected OKRs (or all).
    const initSel = document.getElementById("add-task-initiative");
    if (initSel) {
      const current = initSel.value;
      const opts = ['<option value="">— Not linked —</option>'];
      for (const it of visibleInitiatives()) {
        opts.push(`<option value="${esc(it.id)}">${esc(it._okr.title)} ▸ ${esc(it.title)}</option>`);
      }
      initSel.innerHTML = opts.join("");
      if (current && initSel.querySelector(`option[value="${current}"]`)) initSel.value = current;
      initSel.dataset.current = initSel.value || "";
    }
    // Epic dropdown — under whichever initiative is currently picked, or
    // under any visible initiative if none is.
    const epicSel = document.getElementById("add-task-epic");
    if (epicSel) {
      const current = epicSel.value;
      const opts = ['<option value="">— No epic —</option>'];
      for (const ep of visibleEpics()) {
        opts.push(`<option value="${esc(ep.id)}">${esc(ep._init.title)} ▸ ${esc(ep.title)}</option>`);
      }
      epicSel.innerHTML = opts.join("");
      if (current && epicSel.querySelector(`option[value="${current}"]`)) epicSel.value = current;
      epicSel.dataset.current = epicSel.value || "";
    }
  }

  /* ───── drawer / columns UI ─────────────────────────────────── */

  function openOkrCascade() {
    let modal = document.getElementById("okr-cascade-modal");
    if (modal) { modal.style.display = ""; renderCascade(); return; }
    modal = document.createElement("div");
    modal.id = "okr-cascade-modal";
    modal.innerHTML = `
      <div class="okrc-backdrop" data-close></div>
      <div class="okrc-sheet" role="dialog" aria-label="OKR filter">
        <header class="okrc-head">
          <button class="okrc-back" id="okrc-back" title="Back">←</button>
          <div class="okrc-title" id="okrc-title">OKRs</div>
          <button class="okrc-done" data-close>Done</button>
        </header>
        <div class="okrc-body" id="okrc-body"></div>
        <footer class="okrc-foot">
          <label class="okrc-orph">
            <input type="checkbox" id="okrc-orph"> Show unassigned
          </label>
          <button class="okrc-clear" id="okrc-clear">Clear all</button>
        </footer>
      </div>`;
    document.body.appendChild(modal);
    injectStyles();
    // Wire close + back + clear
    modal.addEventListener("click", (e) => { if (e.target.dataset.close !== undefined) closeModal(); });
    modal.querySelector("#okrc-back").addEventListener("click", () => { stage = Math.max(0, stage - 1); renderCascade(); });
    modal.querySelector("#okrc-clear").addEventListener("click", () => {
      sel.okrs.clear(); sel.inits.clear(); sel.epics.clear();
      saveState(); renderCascade(); applyFilter(); updateSummary(); populateAddTaskDropdowns();
    });
    modal.querySelector("#okrc-orph").addEventListener("change", (e) => {
      sel.showOrphans = e.target.checked;
      saveState(); applyFilter();
    });
    renderCascade();
  }
  function closeModal() {
    const m = document.getElementById("okr-cascade-modal");
    if (m) m.style.display = "none";
  }
  function isDesktop() { return window.matchMedia("(min-width: 900px)").matches; }

  function renderCascade() {
    const body = document.getElementById("okrc-body");
    const title = document.getElementById("okrc-title");
    const back  = document.getElementById("okrc-back");
    const orph  = document.getElementById("okrc-orph");
    if (!body) return;
    orph.checked = sel.showOrphans;

    if (isDesktop()) {
      // All three columns side by side.
      body.className = "okrc-body okrc-cols";
      back.style.visibility = "hidden";
      title.textContent = "OKR · Initiative · Epic";
      body.innerHTML = `
        <section class="okrc-col" id="col-okr"></section>
        <section class="okrc-col" id="col-init"></section>
        <section class="okrc-col" id="col-epic"></section>
      `;
      renderOkrColumn(body.querySelector("#col-okr"));
      renderInitColumn(body.querySelector("#col-init"));
      renderEpicColumn(body.querySelector("#col-epic"));
    } else {
      body.className = "okrc-body okrc-drawer";
      back.style.visibility = stage === 0 ? "hidden" : "visible";
      title.textContent = ["OKRs", "Initiatives", "Epics"][stage];
      body.innerHTML = `<section class="okrc-col okrc-col-mobile"></section>`;
      const col = body.querySelector(".okrc-col");
      if (stage === 0) renderOkrColumn(col);
      if (stage === 1) renderInitColumn(col);
      if (stage === 2) renderEpicColumn(col);
    }
  }

  function makeRow({ id, label, sub, checked, disabled, onToggle, onDrill }) {
    const div = document.createElement("div");
    div.className = "okrc-row" + (disabled ? " is-disabled" : "");
    div.innerHTML = `
      <label class="okrc-check">
        <input type="checkbox" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}>
        <span class="okrc-label">
          <span class="okrc-l1">${esc(label)}</span>
          ${sub ? `<span class="okrc-l2">${esc(sub)}</span>` : ""}
        </span>
      </label>
      ${onDrill ? `<button class="okrc-drill" title="Drill in">›</button>` : ""}`;
    div.querySelector("input").addEventListener("change", (e) => onToggle(e.target.checked));
    if (onDrill) div.querySelector(".okrc-drill").addEventListener("click", onDrill);
    return div;
  }

  function renderOkrColumn(col) {
    col.innerHTML = `<h3 class="okrc-h">OKRs</h3>`;
    col.appendChild(addButton("+ New OKR", () => promptCreateOkr()));
    if (!tree.length) {
      col.appendChild(emptyState("No OKRs yet for this project. Tap “New OKR” to add one."));
      return;
    }
    for (const o of tree) {
      const krCount = (o.key_results || []).length;
      const initCount = (o.key_results || []).reduce((n, kr) => n + (kr.initiatives || []).length, 0);
      col.appendChild(makeRow({
        id: o.id,
        label: o.title,
        sub: `${krCount} KR · ${initCount} init`,
        checked: sel.okrs.has(o.id),
        onToggle: (v) => {
          v ? sel.okrs.add(o.id) : sel.okrs.delete(o.id);
          if (!v) {
            // Drop downstream selections under this OKR so the cascade narrows.
            for (const kr of o.key_results || [])
              for (const it of kr.initiatives || []) {
                sel.inits.delete(it.id);
                for (const ep of it.epics || []) sel.epics.delete(ep.id);
              }
          }
          saveState(); renderCascade(); applyFilter(); updateSummary(); populateAddTaskDropdowns();
        },
        onDrill: isDesktop() ? null : () => { stage = 1; renderCascade(); },
      }));
    }
  }

  function renderInitColumn(col) {
    col.innerHTML = `<h3 class="okrc-h">Initiatives</h3>`;
    // Group by parent OKR (and KR as sub-label).
    const initsByOkr = new Map();
    for (const o of tree) {
      if (sel.okrs.size && !sel.okrs.has(o.id)) continue;
      const arr = [];
      for (const kr of o.key_results || [])
        for (const it of kr.initiatives || []) arr.push({ it, kr });
      if (arr.length) initsByOkr.set(o, arr);
    }
    if (!initsByOkr.size) {
      col.appendChild(emptyState(
        sel.okrs.size
          ? "No initiatives under the selected OKR(s). Pick an OKR’s KR below and tap “New Initiative”."
          : "Select at least one OKR to see its initiatives, or just create one."));
      // Inline create still works if there's at least one KR somewhere.
      addInitiativeCreator(col);
      return;
    }
    for (const [o, arr] of initsByOkr) {
      col.insertAdjacentHTML("beforeend", `<div class="okrc-section">${esc(o.title)}</div>`);
      for (const { it, kr } of arr) {
        const epicCount = (it.epics || []).length;
        col.appendChild(makeRow({
          id: it.id,
          label: it.title,
          sub: `KR: ${kr.title} · ${epicCount} epic`,
          checked: sel.inits.has(it.id),
          onToggle: (v) => {
            v ? sel.inits.add(it.id) : sel.inits.delete(it.id);
            if (!v) for (const ep of it.epics || []) sel.epics.delete(ep.id);
            saveState(); renderCascade(); applyFilter(); updateSummary(); populateAddTaskDropdowns();
          },
          onDrill: isDesktop() ? null : () => { stage = 2; renderCascade(); },
        }));
      }
    }
    addInitiativeCreator(col);
  }

  function addInitiativeCreator(col) {
    // Build a KR picker so the user can pick where to add the initiative.
    // Exclude defaults — Initiatives can't live under the default OKR.
    const krs = [];
    for (const o of tree) {
      if (o.is_default) continue;
      if (sel.okrs.size && !sel.okrs.has(o.id)) continue;
      for (const kr of o.key_results || []) {
        if (kr.is_default) continue;
        krs.push({ kr, o });
      }
    }
    if (!krs.length) {
      const hint = document.createElement("div");
      hint.className = "okrc-empty";
      hint.textContent = "Create a new OKR first — Initiatives can't go under the default.";
      col.appendChild(hint);
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "okrc-create";
    wrap.innerHTML = `
      <input type="text" placeholder="New initiative…" class="okrc-input">
      <select class="okrc-select">
        ${krs.map(({ kr, o }) => `<option value="${esc(kr.id)}">${esc(o.title)} ▸ ${esc(kr.title)}</option>`).join("")}
      </select>
      <button class="okrc-add">+</button>`;
    const input  = wrap.querySelector("input");
    const select = wrap.querySelector("select");
    const button = wrap.querySelector("button");
    const submit = async () => {
      const title = input.value.trim();
      if (!title) return;
      button.disabled = true;
      try {
        const r = await _fetch("/api/initiatives", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ title, key_result_id: select.value }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          alert(body.error || "Couldn't create initiative");
          return;
        }
        input.value = "";
        await refreshHierarchy();
        renderCascade();
      } finally { button.disabled = false; }
    };
    button.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    col.appendChild(wrap);
  }

  function renderEpicColumn(col) {
    col.innerHTML = `<h3 class="okrc-h">Epics</h3>`;
    const inits = visibleInitiatives();
    const activeInits = sel.inits.size
      ? inits.filter((it) => sel.inits.has(it.id))
      : inits;
    if (!activeInits.length) {
      col.appendChild(emptyState("Select at least one initiative to see its epics."));
      return;
    }
    let any = false;
    for (const it of activeInits) {
      if (!(it.epics || []).length) continue;
      any = true;
      col.insertAdjacentHTML("beforeend", `<div class="okrc-section">${esc(it.title)}</div>`);
      for (const ep of it.epics) {
        col.appendChild(makeRow({
          id: ep.id,
          label: ep.title,
          sub: ep.description ? ep.description.slice(0, 90) : null,
          checked: sel.epics.has(ep.id),
          onToggle: (v) => {
            v ? sel.epics.add(ep.id) : sel.epics.delete(ep.id);
            saveState(); applyFilter(); updateSummary(); populateAddTaskDropdowns();
          },
        }));
      }
    }
    if (!any) col.appendChild(emptyState("No epics under the selected initiatives yet."));
    // Inline create — exclude default initiatives, can't have children.
    const userInits = activeInits.filter((it) => !it.is_default);
    if (!userInits.length) {
      const hint = document.createElement("div");
      hint.className = "okrc-empty";
      hint.textContent = "Create a new Initiative first — Epics can't go under the default.";
      col.appendChild(hint);
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "okrc-create";
    wrap.innerHTML = `
      <input type="text" placeholder="New epic…" class="okrc-input">
      <select class="okrc-select">
        ${userInits.map((it) => `<option value="${esc(it.id)}">${esc(it.title)}</option>`).join("")}
      </select>
      <button class="okrc-add">+</button>`;
    const input  = wrap.querySelector("input");
    const select = wrap.querySelector("select");
    const button = wrap.querySelector("button");
    const submit = async () => {
      const title = input.value.trim();
      if (!title) return;
      button.disabled = true;
      try {
        const r = await _fetch("/api/epics", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ title, initiative_id: select.value }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          alert(body.error || "Couldn't create epic");
          return;
        }
        input.value = "";
        await refreshHierarchy();
        renderCascade();
      } finally { button.disabled = false; }
    };
    button.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    col.appendChild(wrap);
  }

  function addButton(label, onClick) {
    const b = document.createElement("button");
    b.className = "okrc-bigbtn";
    b.textContent = label;
    b.addEventListener("click", onClick);
    return b;
  }
  function emptyState(msg) {
    const d = document.createElement("div");
    d.className = "okrc-empty";
    d.textContent = msg;
    return d;
  }

  /* ───── create OKR (objective + first KR in one flow) ────────── */

  async function promptCreateOkr() {
    const title = prompt("New OKR title:");
    if (!title || !title.trim()) return;
    const krTitle = prompt("First Key Result for this OKR (leave blank to skip):");
    try {
      const r = await _fetch("/api/goals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          title: title.trim(),
          project_id: PROJECT_ID,
          status: "active",
          time_horizon: "quarterly",
        }),
      });
      const data = await r.json();
      const objective = data.objective || data;
      if (krTitle && krTitle.trim() && objective && objective.id) {
        await _fetch("/api/key-results", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            title: krTitle.trim(),
            objective_id: objective.id,
            target_value: 100,
            unit: "%",
          }),
        });
      }
      await refreshHierarchy();
      renderCascade();
    } catch (e) {
      console.error("create OKR failed", e);
      alert("Couldn't create OKR — check your connection.");
    }
  }

  /* ───── styles (injected, no extra css file) ─────────────────── */

  function injectStyles() {
    if (document.getElementById("okrc-styles")) return;
    const s = document.createElement("style");
    s.id = "okrc-styles";
    s.textContent = `
      #okr-cascade-modal { position:fixed; inset:0; z-index:9050; }
      .okrc-backdrop { position:absolute; inset:0; background:rgba(15,17,21,0.45); }
      .okrc-sheet {
        position:absolute; left:0; right:0; bottom:0; top:auto;
        background:#fff; border-top-left-radius:18px; border-top-right-radius:18px;
        max-height:88vh; display:flex; flex-direction:column;
        box-shadow:0 -10px 40px rgba(0,0,0,0.2);
      }
      @media (min-width: 900px) {
        .okrc-sheet { left:50%; right:auto; top:6vh; bottom:6vh; transform:translateX(-50%);
          width:min(1100px, 92vw); border-radius:18px; max-height:none; }
      }
      .okrc-head { display:flex; align-items:center; gap:10px; padding:14px 16px; border-bottom:1px solid #eef0f4; }
      .okrc-back { width:36px; height:36px; border:0; background:transparent; font-size:22px; cursor:pointer; }
      .okrc-title { flex:1; font-weight:700; font-size:16px; }
      .okrc-done { padding:8px 14px; background:#6366f1; color:#fff; border:0; border-radius:8px; font-weight:600; cursor:pointer; }
      .okrc-body { flex:1; overflow:auto; }
      .okrc-cols { display:grid; grid-template-columns:1fr 1fr 1fr; gap:0; }
      .okrc-col { padding:14px 16px; border-right:1px solid #eef0f4; }
      .okrc-col:last-child { border-right:0; }
      .okrc-col-mobile { padding:14px 16px; }
      .okrc-h { font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; margin:0 0 10px; }
      .okrc-section { font-size:11px; font-weight:700; color:#374151; margin:12px 0 4px; text-transform:uppercase; letter-spacing:0.04em; }
      .okrc-row { display:flex; align-items:center; gap:8px; padding:8px 6px; border-radius:8px; }
      .okrc-row:hover { background:#f3f4f7; }
      .okrc-check { display:flex; align-items:center; gap:10px; flex:1; cursor:pointer; }
      .okrc-check input { width:18px; height:18px; accent-color:#6366f1; }
      .okrc-label { display:flex; flex-direction:column; }
      .okrc-l1 { font-size:14px; font-weight:600; color:#1f2330; }
      .okrc-l2 { font-size:11px; color:#6b7280; }
      .okrc-drill { background:transparent; border:0; font-size:22px; color:#9ca3af; cursor:pointer; padding:0 8px; }
      .okrc-empty { padding:24px 10px; color:#9ca3af; font-size:13px; text-align:center; }
      .okrc-bigbtn { width:100%; padding:10px 12px; background:#eef2ff; color:#4338ca; border:1px dashed #6366f1; border-radius:10px; font-weight:600; cursor:pointer; margin:6px 0 12px; }
      .okrc-create { display:flex; gap:6px; margin-top:14px; padding-top:12px; border-top:1px dashed #e5e7eb; }
      .okrc-input { flex:1; padding:8px 10px; border:1px solid #e5e7eb; border-radius:8px; font-size:13px; }
      .okrc-select { padding:8px 10px; border:1px solid #e5e7eb; border-radius:8px; font-size:12px; max-width:40%; }
      .okrc-add { background:#22c55e; color:#fff; border:0; border-radius:8px; padding:0 14px; font-weight:700; font-size:18px; cursor:pointer; }
      .okrc-foot { display:flex; align-items:center; gap:14px; padding:10px 16px; border-top:1px solid #eef0f4; font-size:13px; }
      .okrc-orph { display:flex; align-items:center; gap:6px; flex:1; }
      .okrc-clear { background:transparent; color:#ef4444; border:1px solid #ef4444; border-radius:8px; padding:6px 12px; font-weight:600; cursor:pointer; font-size:12px; }
      @media (prefers-color-scheme: dark) {
        .okrc-sheet { background:#181b22; color:#e8eaf0; }
        .okrc-head, .okrc-foot { border-color:#232733; }
        .okrc-col { border-color:#232733; }
        .okrc-row:hover { background:#1f2330; }
        .okrc-l1 { color:#e8eaf0; }
        .okrc-l2, .okrc-h, .okrc-section { color:#9ca3af; }
        .okrc-bigbtn { background:#1e2030; border-color:#6366f1; color:#a5b4fc; }
        .okrc-input, .okrc-select { background:#0f1115; border-color:#232733; color:#e8eaf0; }
      }
    `;
    document.head.appendChild(s);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* ───── boot ─────────────────────────────────────────────────── */

  window.openOkrCascade = openOkrCascade;

  document.addEventListener("DOMContentLoaded", () => {
    loadState();
    refreshHierarchy();
    // Re-apply when window resizes across the desktop breakpoint.
    let lastDesktop = isDesktop();
    window.addEventListener("resize", () => {
      const now = isDesktop();
      if (now !== lastDesktop) { lastDesktop = now; if (document.getElementById("okrc-body")) renderCascade(); }
    });
  });
})();

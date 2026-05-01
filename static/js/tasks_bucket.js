/* Tasks Bucket — front-end */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.querySelector('meta[name="csrf-token"]')?.content) || "";

  const CATEGORIES = window.TB_CATEGORIES || ["Health", "Grocery", "Portfolio", "Checklist", "TravelReads", "ProjectTask"];
  const DEBOUNCE_MS = 60_000;            // 60s idle window before auto-classify
  const PENDING_POLL_MS = 1_000;         // countdown tick rate
  const MILESTONES = [10, 25, 50, 100, 250, 500];
  const DEST_PAGE = { groceries: "/grocery", checklist_items: "/checklist", travel_reads: "/travel-reads" };

  // Effort cycle: clicking the effort button steps through these values.
  // null → 5 → 15 → 30 → 60 → 120 → 180 → 240 → null …
  const EFFORTS = [null, 5, 15, 30, 60, 120, 180, 240];
  const effortLabel = (m) => {
    if (m == null) return "—";
    if (m < 60) return `${m}m`;
    return `${m / 60}h`;
  };
  const nextEffort = (cur) => {
    const i = EFFORTS.indexOf(cur == null ? null : Number(cur));
    return EFFORTS[(i < 0 ? 0 : (i + 1) % EFFORTS.length)];
  };

  // Per-category form defs for the "Save & move" modal. fromRaw=true
  // means prefill this field with the bucket row's raw_text.
  const FIELD_DEFS = {
    Grocery: [
      { name: "item",     label: "Item",     type: "text",     fromRaw: true, required: true, max: 120 },
      { name: "quantity", label: "Quantity", type: "text",     placeholder: "e.g. 2 lb",      max: 40  },
      { name: "category", label: "Aisle",    type: "select",   default: "other",
        options: ["produce","dairy","staples","snacks","household","spices","frozen","beverages","meat","bakery","other"] },
      { name: "priority", label: "Priority", type: "select",   default: "medium",
        options: ["high","medium","low"] },
      { name: "notes",    label: "Notes",    type: "textarea", wide: true,    max: 400  },
    ],
    Checklist: [
      { name: "name",          label: "Name",         type: "text",     fromRaw: true, required: true, max: 200 },
      { name: "schedule",      label: "Schedule",     type: "select",   default: "daily",
        options: ["daily","weekdays","weekends","custom"] },
      { name: "time_of_day",   label: "When",         type: "select",   default: "anytime",
        options: ["morning","afternoon","evening","anytime"] },
      { name: "reminder_time", label: "Reminder",     type: "time",     placeholder: "HH:MM" },
      { name: "group_name",    label: "Group",        type: "text",     placeholder: "Optional" },
      { name: "notes",         label: "Notes",        type: "textarea", wide: true, max: 400 },
    ],
    TravelReads: [
      { name: "title",    label: "Title",    type: "text",     fromRaw: true, required: true, max: 200 },
      { name: "url",      label: "URL",      type: "url",      placeholder: "https://…", wide: true },
      { name: "kind",     label: "Kind",     type: "select",   default: "article",
        options: ["article","video","book","podcast","newsletter","documentary","other"] },
      { name: "priority", label: "Priority", type: "select",   default: "medium",
        options: ["high","medium","low"] },
      { name: "notes",    label: "Notes",    type: "textarea", wide: true },
    ],
    ProjectTask: [
      { name: "name",          label: "Title",      type: "text",   fromRaw: true, required: true, max: 200 },
      { name: "group_name",    label: "Group",      type: "text",   default: "Project Tasks" },
      { name: "time_of_day",   label: "When",       type: "select", default: "anytime",
        options: ["morning","afternoon","evening","anytime"] },
      { name: "reminder_time", label: "Reminder",   type: "time" },
    ],
    // Health & Portfolio: not routable from the bucket.
    Health: null,
    Portfolio: null,
  };
  const NON_ROUTABLE_NOTE = {
    Health: "Health items stay in this bucket — log the actual habit/measurement directly in the Health module when you're ready.",
    Portfolio: "Portfolio items stay in this bucket — open the Investments module to add the holding with full details (broker, ticker, quantity, …).",
  };

  let items = [];
  let stats = { today: { captured: 0, classified: 0, closed: 0 }, streak: 0 };
  let pendingIds = new Set();
  let lastInputAt = 0;
  let countdownTimer = null;
  let recognizing = false;
  let recognition = null;

  // ─────────── helpers ───────────────────────────────────────

  const apiFetch = async (path, opts = {}) => {
    const headers = Object.assign({ "Content-Type": "application/json", "X-CSRFToken": csrf() }, opts.headers || {});
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts, { headers }));
    let body = {};
    try { body = await res.json(); } catch (_) { body = {}; }
    if (!res.ok) {
      throw new Error(body.error || `Request failed (${res.status})`);
    }
    return body;
  };

  const toast = (msg, kind = "info") => {
    if (window.toast && typeof window.toast.show === "function") return window.toast.show(msg, kind);
    if (window.showToast) return window.showToast(msg, kind);
    console.log(`[${kind}]`, msg);
  };

  const refreshFeather = () => { if (window.feather && window.feather.replace) window.feather.replace(); };

  // ─────────── data load ─────────────────────────────────────

  const loadItems = async () => {
    const r = await apiFetch("/api/tasks-bucket");
    items = r.items || [];
    pendingIds = new Set(items.filter(i => i.status === "pending").map(i => i.id));
    render();
    tickCountdown();
  };

  const loadStats = async () => {
    try {
      const r = await apiFetch("/api/tasks-bucket/stats");
      stats = r;
      renderStats();
    } catch (e) { /* non-fatal */ }
  };

  const sweepClosed = async () => {
    try { await apiFetch("/api/tasks-bucket/sweep-closed", { method: "POST", body: "{}" }); }
    catch (e) { /* non-fatal */ }
  };

  // ─────────── render: stats & XP ────────────────────────────

  const renderStats = () => {
    const t = stats.today || { captured: 0, classified: 0, closed: 0 };
    $("#tb-stat-captured").textContent = t.captured;
    $("#tb-stat-classified").textContent = t.classified;
    $("#tb-stat-closed").textContent = t.closed;
    $("#tb-stat-streak").textContent = stats.streak || 0;

    // XP = captured + 2 * classified + 5 * closed (closing is the goal)
    const xp = (t.captured || 0) + 2 * (t.classified || 0) + 5 * (t.closed || 0);
    const target = Math.max(50, Math.ceil((xp + 1) / 50) * 50);
    const pct = Math.min(100, Math.round((xp / target) * 100));
    $("#tb-xp-fill").style.width = pct + "%";
    $("#tb-xp-label").textContent = `${xp} / ${target} XP`;
  };

  // ─────────── render: groups ────────────────────────────────

  const groupItems = () => {
    const groups = { Unclassified: [] };
    CATEGORIES.forEach(c => groups[c] = []);
    // Stable sort: priority first, then position, then most-recent first.
    const sorted = items.slice().sort((a, b) => {
      const pa = a.is_priority ? 1 : 0;
      const pb = b.is_priority ? 1 : 0;
      if (pa !== pb) return pb - pa;
      const xa = a.position == null ? 9999 : a.position;
      const xb = b.position == null ? 9999 : b.position;
      if (xa !== xb) return xa - xb;
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
    sorted.forEach(it => {
      const key = it.category && CATEGORIES.includes(it.category) ? it.category : "Unclassified";
      groups[key].push(it);
    });
    return groups;
  };

  const escapeHTML = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const renderRow = (it) => {
    const tag = it.category
      ? `<span class="tb-tag tb-tag--${it.category}">${it.category}</span>`
      : (it.status === "pending" ? `<span class="tb-tag">Pending</span>` : `<span class="tb-tag">Unclassified</span>`);
    const dest = it.destination_table && DEST_PAGE[it.destination_table]
      ? `<span class="tb-tag" title="Synced to ${it.destination_table}">↗ ${it.destination_table.replace('_', ' ')}</span>`
      : "";
    const isPrio = !!it.is_priority;
    const eff = it.effort_minutes;
    const cls = [
      "tb-row",
      it.status === "pending" ? "is-pending" : "",
      isPrio ? "is-priority" : "",
    ].filter(Boolean).join(" ");
    return `
      <div class="${cls}" data-id="${it.id}" draggable="true">
        <span class="tb-handle" aria-hidden="true"><i data-feather="menu"></i></span>
        <input type="checkbox" class="tb-check" data-action="close" aria-label="Mark done">
        <div class="tb-row-body">
          <div class="tb-row-text">${escapeHTML(it.raw_text)}</div>
          <div class="tb-row-meta">${tag} ${dest}</div>
        </div>
        <button class="tb-prio-btn ${isPrio ? 'is-on' : ''}" data-action="priority"
                title="${isPrio ? 'Priority — click to clear' : 'Mark as immediate priority'}">
          <i data-feather="flag"></i>${isPrio ? '<span>HIGH</span>' : ''}
        </button>
        <button class="tb-effort-btn ${eff ? 'is-set' : ''}" data-action="effort"
                title="Effort estimate (click to cycle)">
          <i data-feather="clock"></i><span>${effortLabel(eff)}</span>
        </button>
        <div class="tb-row-actions">
          <button class="tb-icon-btn" data-action="classify" title="Classify now"><i data-feather="zap"></i></button>
          <button class="tb-icon-btn" data-action="open" title="Details"><i data-feather="more-horizontal"></i></button>
        </div>
      </div>`;
  };

  const renderGroups = () => {
    const groups = groupItems();
    const order = ["Unclassified", ...CATEGORIES];
    const html = order.map(cat => {
      const list = groups[cat];
      const count = list.length;
      const cls = cat === "Unclassified" ? "tb-group tb-group--unclassified" : "tb-group";
      const rows = list.map(renderRow).join("");
      return `
        <section class="${cls}" data-category="${cat}">
          <div class="tb-group-head">
            ${cat === "Unclassified" ? "Unclassified" : cat}
            <span class="tb-group-count">${count}</span>
          </div>
          <div class="tb-list">${rows}</div>
        </section>`;
    }).join("");
    $("#tb-groups").innerHTML = html;
    refreshFeather();
    wireRows();
    wireDnD();
  };

  const render = () => {
    renderGroups();
    renderStats();
  };

  // ─────────── row interactions ──────────────────────────────

  const wireRows = () => {
    $$("#tb-groups .tb-row").forEach(row => {
      const id = row.dataset.id;
      const it = items.find(x => x.id === id);
      if (!it) return;

      // Click anywhere outside interactive controls → open detail.
      row.addEventListener("click", (e) => {
        const t = e.target;
        if (t.closest("input.tb-check") ||
            t.closest("button.tb-icon-btn") ||
            t.closest("button.tb-prio-btn") ||
            t.closest("button.tb-effort-btn")) return;
        openDetail(it);
      });

      $("input.tb-check", row)?.addEventListener("change", (e) => {
        if (e.target.checked) closeItem(it.id, row);
      });

      $$('button.tb-icon-btn', row).forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          if (action === "open") openDetail(it);
          else if (action === "classify") classifyOne(it.id, true);
        });
      });

      $('button.tb-prio-btn', row)?.addEventListener("click", (e) => {
        e.stopPropagation();
        togglePriority(it);
      });
      $('button.tb-effort-btn', row)?.addEventListener("click", (e) => {
        e.stopPropagation();
        cycleEffort(it);
      });
    });
  };

  const togglePriority = async (it) => {
    const want = !it.is_priority;
    try {
      await apiFetch(`/api/tasks-bucket/${it.id}/update`, {
        method: "POST", body: JSON.stringify({ is_priority: want }),
      });
      it.is_priority = want;
      render();
    } catch (err) {
      toast(err.message || "Couldn't update priority", "error");
    }
  };

  const cycleEffort = async (it) => {
    const next = nextEffort(it.effort_minutes);
    try {
      await apiFetch(`/api/tasks-bucket/${it.id}/update`, {
        method: "POST", body: JSON.stringify({ effort_minutes: next }),
      });
      it.effort_minutes = next;
      render();
    } catch (err) {
      toast(err.message || "Couldn't update effort", "error");
    }
  };

  // ─────────── drag & drop between categories ────────────────

  const wireDnD = () => {
    let draggingId = null;

    $$("#tb-groups .tb-row").forEach(row => {
      row.addEventListener("dragstart", (e) => {
        draggingId = row.dataset.id;
        row.classList.add("is-dragging");
        e.dataTransfer.effectAllowed = "move";
        try { e.dataTransfer.setData("text/plain", draggingId); } catch (_) { /* IE */ }
      });
      row.addEventListener("dragend", () => {
        draggingId = null;
        row.classList.remove("is-dragging");
        $$("#tb-groups .tb-group").forEach(g => g.classList.remove("is-drop-target"));
      });
    });

    $$("#tb-groups .tb-group").forEach(group => {
      group.addEventListener("dragover", (e) => { e.preventDefault(); group.classList.add("is-drop-target"); });
      group.addEventListener("dragleave", () => group.classList.remove("is-drop-target"));
      group.addEventListener("drop", async (e) => {
        e.preventDefault();
        group.classList.remove("is-drop-target");
        const id = draggingId || (e.dataTransfer && e.dataTransfer.getData("text/plain"));
        if (!id) return;
        const newCat = group.dataset.category;
        const it = items.find(x => x.id === id);
        if (!it) return;
        // Dropping into "Unclassified" is a no-op (no learning signal there).
        if (newCat === "Unclassified") return;
        if (it.category === newCat) return;

        try {
          const r = await apiFetch(`/api/tasks-bucket/${id}/reclassify`, {
            method: "POST", body: JSON.stringify({ category: newCat }),
          });
          it.category = newCat;
          it.manual_override = true;
          it.status = "classified";
          if (r.destination_table) {
            it.destination_table = r.destination_table;
            it.destination_id = r.destination_id;
          }
          render();
          loadStats();
          toast(`Moved to ${newCat}`, "success");
        } catch (err) {
          toast(err.message || "Couldn't move", "error");
        }
      });
    });
  };

  // ─────────── capture: typing + dictation ───────────────────

  const sendItem = async (text) => {
    text = (text || "").trim();
    if (!text) return;
    try {
      const r = await apiFetch("/api/tasks-bucket", {
        method: "POST", body: JSON.stringify({ raw_text: text }),
      });
      if (r.item) {
        items.unshift(r.item);
        pendingIds.add(r.item.id);
      }
      lastInputAt = Date.now();
      render();
      loadStats();
      tickCountdown();
    } catch (err) {
      toast(err.message || "Couldn't add", "error");
    }
  };

  const splitAndSend = async (raw) => {
    const lines = String(raw || "").split(/\n+/).map(s => s.trim()).filter(Boolean);
    for (const line of lines) await sendItem(line);
  };

  const inputEl = () => $("#tb-input");

  const wireCapture = () => {
    const ta = inputEl();
    const send = $("#tb-send");
    const mic = $("#tb-mic");

    const submit = async () => {
      const v = ta.value;
      ta.value = "";
      ta.style.height = "auto";
      await splitAndSend(v);
    };

    ta.addEventListener("input", () => { lastInputAt = Date.now(); });
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    send.addEventListener("click", submit);

    // Web Speech API — graceful fallback if unsupported.
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      mic.disabled = true;
      mic.title = "Dictation not supported in this browser";
    } else {
      recognition = new SR();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = navigator.language || "en-US";

      let interimBuf = "";
      recognition.onresult = (e) => {
        let finalText = "";
        interimBuf = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) finalText += t + "\n";
          else interimBuf += t;
        }
        if (finalText) {
          ta.value = (ta.value ? ta.value + (ta.value.endsWith("\n") ? "" : " ") : "") + finalText.trim();
          lastInputAt = Date.now();
        }
      };
      recognition.onend = () => {
        recognizing = false;
        mic.classList.remove("is-on");
        // After dictation ends, surface what's typed for review — user
        // taps Send to add (so they can clean up before classify runs).
      };
      recognition.onerror = () => {
        recognizing = false;
        mic.classList.remove("is-on");
        toast("Dictation stopped", "info");
      };
      mic.addEventListener("click", () => {
        if (recognizing) {
          recognition.stop();
        } else {
          try {
            recognition.start();
            recognizing = true;
            mic.classList.add("is-on");
          } catch (e) { /* ignore */ }
        }
      });
    }
  };

  // ─────────── countdown → auto-classify ─────────────────────

  const tickCountdown = () => {
    if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
    const cd = $("#tb-countdown");
    const lbl = $("#tb-countdown-label");
    if (pendingIds.size === 0) { cd.classList.add("tb-countdown--idle"); return; }

    cd.classList.remove("tb-countdown--idle");
    countdownTimer = setInterval(async () => {
      const elapsed = Date.now() - lastInputAt;
      const remaining = Math.max(0, DEBOUNCE_MS - elapsed);
      lbl.textContent = `Classifying in ${Math.ceil(remaining / 1000)}s`;
      if (remaining <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
        cd.classList.add("tb-countdown--idle");
        await classifyAllPending();
      }
    }, PENDING_POLL_MS);
  };

  const classifyOne = async (id, forceShowResult = false) => {
    try {
      const r = await apiFetch(`/api/tasks-bucket/${id}/classify`, { method: "POST", body: "{}" });
      pendingIds.delete(id);
      const it = items.find(x => x.id === id);
      if (it) {
        it.category = r.category;
        it.confidence = r.confidence;
        it.matched_keywords = r.matched;
        it.status = r.category ? "classified" : "unclassified";
        if (r.destination_table) {
          it.destination_table = r.destination_table;
          it.destination_id = r.destination_id;
        }
      }
      if (forceShowResult) {
        if (r.category) toast(`Classified as ${r.category}`, "success");
        else toast("Couldn't classify confidently — pick a category", "info");
      }
      render();
      loadStats();
    } catch (err) {
      toast(err.message || "Couldn't classify", "error");
    }
  };

  const classifyAllPending = async () => {
    const ids = Array.from(pendingIds);
    for (const id of ids) await classifyOne(id, false);
  };

  // ─────────── close / archive (with milestone confetti) ────

  const closeItem = async (id, rowEl) => {
    try {
      await apiFetch(`/api/tasks-bucket/${id}/close`, { method: "POST", body: "{}" });
      // Remove locally with a small fade
      if (rowEl) rowEl.style.transition = "opacity .25s";
      if (rowEl) rowEl.style.opacity = "0";
      const prevClosed = stats.today?.closed || 0;
      await loadStats();
      const nowClosed = stats.today?.closed || 0;
      if (MILESTONES.includes(nowClosed) && nowClosed > prevClosed) {
        confettiBurst();
        toast(`🎉 ${nowClosed} closed today — keep going!`, "success");
      }
      items = items.filter(x => x.id !== id);
      render();
    } catch (err) {
      toast(err.message || "Couldn't close", "error");
      if (rowEl) {
        const cb = $("input.tb-check", rowEl);
        if (cb) cb.checked = false;
        rowEl.style.opacity = "";
      }
    }
  };

  const archiveItem = async (id) => {
    try {
      await apiFetch(`/api/tasks-bucket/${id}/archive`, { method: "POST", body: "{}" });
      items = items.filter(x => x.id !== id);
      render();
    } catch (err) {
      toast(err.message || "Couldn't archive", "error");
    }
  };

  // ─────────── detail / reclassify modal ─────────────────────

  let modalItemId = null;

  const renderFormFields = (defs, raw) => {
    return defs.map(d => {
      const wide = d.wide ? "tb-form-field--wide" : "";
      const placeholder = d.placeholder ? ` placeholder="${escapeHTML(d.placeholder)}"` : "";
      const max = d.max ? ` maxlength="${d.max}"` : "";
      const req = d.required ? " required" : "";
      const initial = d.fromRaw ? (raw || "") : (d.default ?? "");
      let control = "";
      if (d.type === "select") {
        const opts = (d.options || []).map(o =>
          `<option value="${escapeHTML(o)}" ${String(initial) === String(o) ? "selected" : ""}>${escapeHTML(o)}</option>`
        ).join("");
        control = `<select name="${d.name}"${req}>${opts}</select>`;
      } else if (d.type === "textarea") {
        control = `<textarea name="${d.name}" rows="3"${placeholder}${max}${req}>${escapeHTML(initial)}</textarea>`;
      } else {
        const t = (d.type === "url" || d.type === "time") ? d.type : "text";
        control = `<input type="${t}" name="${d.name}" value="${escapeHTML(initial)}"${placeholder}${max}${req}>`;
      }
      return `
        <div class="tb-form-field ${wide}">
          <label for="${d.name}">${escapeHTML(d.label)}</label>
          ${control}
        </div>`;
    }).join("");
  };

  const refreshModalForm = (it) => {
    const formWrap = $("#tb-modal-form-wrap");
    const form = $("#tb-modal-form");
    const note = $("#tb-modal-form-note");
    const formTitle = $("#tb-modal-form-title");
    const routeBtn = $("#tb-modal-route");

    // Already routed → no form, just a "linked in" line + disabled save.
    if (it.destination_table && it.destination_id) {
      formWrap.setAttribute("hidden", "");
      routeBtn.disabled = true;
      routeBtn.style.display = "none";
      return;
    }

    // No category yet → user must pick one first.
    if (!it.category) {
      formWrap.removeAttribute("hidden");
      formTitle.textContent = "Move to module";
      form.innerHTML = "";
      note.textContent = "Pick a category above to see the move form.";
      note.removeAttribute("hidden");
      routeBtn.disabled = true;
      routeBtn.style.display = "";
      return;
    }

    const defs = FIELD_DEFS[it.category];
    formWrap.removeAttribute("hidden");
    formTitle.textContent = `Move to ${it.category}`;
    routeBtn.style.display = "";

    if (!defs) {
      // Health / Portfolio: show informational note, hide save button.
      form.innerHTML = "";
      note.textContent = NON_ROUTABLE_NOTE[it.category] || "This category stays in the bucket.";
      note.removeAttribute("hidden");
      routeBtn.disabled = true;
      return;
    }

    form.innerHTML = renderFormFields(defs, it.raw_text || "");
    note.setAttribute("hidden", "");
    routeBtn.disabled = false;
  };

  const openDetail = (it) => {
    modalItemId = it.id;
    $("#tb-modal-title").textContent = it.category || (it.status === "pending" ? "Pending" : "Unclassified");
    $("#tb-modal-text").textContent = it.raw_text || "";

    // Category buttons
    const grid = $("#tb-modal-cats");
    grid.innerHTML = CATEGORIES.map(c =>
      `<button class="tb-cat-btn ${it.category === c ? 'is-current' : ''}" data-cat="${c}" type="button">${c}</button>`
    ).join("");
    $$("#tb-modal-cats .tb-cat-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cat = btn.dataset.cat;
        if (cat === it.category) return;
        try {
          await apiFetch(`/api/tasks-bucket/${it.id}/reclassify`, {
            method: "POST", body: JSON.stringify({ category: cat }),
          });
          it.category = cat;
          it.manual_override = true;
          it.status = "classified";
          openDetail(it);  // re-render modal with new state
          render();
          loadStats();
          toast(`Saved as ${cat}`, "success");
        } catch (err) {
          toast(err.message || "Couldn't save", "error");
        }
      });
    });

    // Category-specific form (or non-routable note)
    refreshModalForm(it);

    // Evidence (matched tokens)
    const ev = $("#tb-modal-evidence");
    const wrap = $("#tb-modal-evidence-wrap");
    const matched = Array.isArray(it.matched_keywords) ? it.matched_keywords : [];
    if (matched.length) {
      ev.innerHTML = matched.map(m => `<span class="tb-tag" title="weight ${m.weight}">${escapeHTML(m.keyword)}</span>`).join("");
      wrap.removeAttribute("hidden");
    } else {
      wrap.setAttribute("hidden", "");
    }

    // Destination link (if already routed)
    const destWrap = $("#tb-modal-dest-wrap");
    const destLink = $("#tb-modal-dest-link");
    if (it.destination_table && DEST_PAGE[it.destination_table]) {
      destWrap.removeAttribute("hidden");
      destLink.textContent = `Open in ${it.destination_table.replace('_', ' ')}`;
      destLink.href = DEST_PAGE[it.destination_table];
    } else {
      destWrap.setAttribute("hidden", "");
    }

    $("#tb-modal").classList.add("is-open");
    $("#tb-modal").setAttribute("aria-hidden", "false");
    refreshFeather();
  };

  const submitRoute = async () => {
    if (!modalItemId) return;
    const it = items.find(x => x.id === modalItemId);
    if (!it) return;
    if (!it.category || !FIELD_DEFS[it.category]) return;
    if (it.destination_id) return;

    const form = $("#tb-modal-form");
    const fd = new FormData(form);
    const fields = {};
    for (const [k, v] of fd.entries()) fields[k] = v;

    // Client-side guard: required fields
    for (const d of FIELD_DEFS[it.category]) {
      if (d.required && !(fields[d.name] || "").trim()) {
        toast(`${d.label} is required`, "error");
        return;
      }
    }

    const btn = $("#tb-modal-route");
    btn.disabled = true;
    try {
      const r = await apiFetch(`/api/tasks-bucket/${it.id}/route`, {
        method: "POST", body: JSON.stringify({ fields }),
      });
      it.destination_table = r.destination_table;
      it.destination_id = r.destination_id;
      it.status = "classified";
      const where = (r.destination_table || "").replace("_", " ");
      toast(`Moved to ${where}`, "success");
      closeModal();
      render();
      loadStats();
    } catch (err) {
      toast(err.message || "Couldn't move", "error");
    } finally {
      btn.disabled = false;
    }
  };

  const closeModal = () => {
    $("#tb-modal").classList.remove("is-open");
    $("#tb-modal").setAttribute("aria-hidden", "true");
    modalItemId = null;
  };

  const wireModal = () => {
    $("#tb-modal-close").addEventListener("click", closeModal);
    $("#tb-modal").addEventListener("click", (e) => { if (e.target.id === "tb-modal") closeModal(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
    $("#tb-modal-archive").addEventListener("click", async () => {
      if (!modalItemId) return;
      const id = modalItemId;
      closeModal();
      await archiveItem(id);
      loadStats();
    });
    $("#tb-modal-close-item").addEventListener("click", async () => {
      if (!modalItemId) return;
      const id = modalItemId;
      closeModal();
      const row = $(`#tb-groups .tb-row[data-id="${id}"]`);
      await closeItem(id, row);
    });
    $("#tb-modal-route").addEventListener("click", submitRoute);
  };

  // ─────────── confetti (no library, simple particles) ───────

  const confettiBurst = () => {
    const cv = $("#tb-confetti");
    cv.hidden = false;
    cv.width = window.innerWidth;
    cv.height = window.innerHeight;
    const ctx = cv.getContext("2d");
    const colors = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"];
    const N = 80;
    const parts = [];
    for (let i = 0; i < N; i++) {
      parts.push({
        x: cv.width / 2, y: cv.height / 3,
        vx: (Math.random() - 0.5) * 14,
        vy: (Math.random() * -10) - 4,
        g: 0.35 + Math.random() * 0.2,
        s: 4 + Math.random() * 6,
        c: colors[i % colors.length],
        r: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 0.3,
      });
    }
    let frames = 0;
    const draw = () => {
      ctx.clearRect(0, 0, cv.width, cv.height);
      parts.forEach(p => {
        p.vy += p.g; p.x += p.vx; p.y += p.vy; p.r += p.vr;
        ctx.save();
        ctx.translate(p.x, p.y); ctx.rotate(p.r);
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s);
        ctx.restore();
      });
      frames++;
      if (frames < 110) requestAnimationFrame(draw);
      else { ctx.clearRect(0, 0, cv.width, cv.height); cv.hidden = true; }
    };
    requestAnimationFrame(draw);
  };

  // ─────────── boot ──────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", async () => {
    refreshFeather();
    wireCapture();
    wireModal();
    await sweepClosed();
    await loadItems();
    await loadStats();
  });
})();

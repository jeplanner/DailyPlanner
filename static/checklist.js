/* Checklist page — renders grouped items, handles tick/edit, talks to
   /api/checklist/* endpoints. Web Push UI is driven by push.js (loaded
   before this file) which exposes window.ClPush. */

(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const TIME_BUCKETS = [
    { key: "morning",   label: "Morning"   },
    { key: "afternoon", label: "Afternoon" },
    { key: "evening",   label: "Evening"   },
    { key: "anytime",   label: "Anytime"   },
  ];

  const state = { items: [], knownGroups: [] };

  // ── API helpers ───────────────────────────────────
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  // ── Render ────────────────────────────────────────
  function render() {
    const container = $("#cl-groups");
    container.innerHTML = "";

    if (!state.items.length) {
      container.innerHTML = `<div class="cl-empty">No items yet. Tap + to add one.</div>`;
      return;
    }

    // If ANY item has a user-defined group, primary-group by that.
    // Otherwise fall back to time-of-day buckets (the old layout).
    const anyGroup = state.items.some((it) => (it.group_name || "").trim());

    if (anyGroup) {
      renderByGroup(container);
    } else {
      renderByTimeOfDay(container);
    }
  }

  function renderByGroup(container) {
    const buckets = new Map();  // preserve insertion order
    for (const it of state.items) {
      const key = (it.group_name || "").trim() || "__ungrouped";
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(it);
    }
    // Sort keys alphabetically, with Ungrouped last.
    const keys = [...buckets.keys()].sort((a, b) => {
      if (a === "__ungrouped") return 1;
      if (b === "__ungrouped") return -1;
      return a.localeCompare(b);
    });

    for (const key of keys) {
      const label = key === "__ungrouped" ? "Ungrouped" : key;
      const section = document.createElement("div");
      section.innerHTML = `<div class="cl-group-title">${label}</div>
                           <div class="cl-list" data-group="${label}"></div>`;
      const list = section.querySelector(".cl-list");
      for (const it of buckets.get(key)) list.appendChild(itemEl(it));
      container.appendChild(section);
    }
  }

  function renderByTimeOfDay(container) {
    const byTime = {};
    for (const b of TIME_BUCKETS) byTime[b.key] = [];
    for (const it of state.items) {
      const k = byTime[it.time_of_day] ? it.time_of_day : "anytime";
      byTime[k].push(it);
    }
    for (const b of TIME_BUCKETS) {
      const items = byTime[b.key];
      if (!items.length) continue;
      const section = document.createElement("div");
      section.innerHTML = `<div class="cl-group-title">${b.label}</div>
                           <div class="cl-list" data-group="${b.key}"></div>`;
      const list = section.querySelector(".cl-list");
      for (const it of items) list.appendChild(itemEl(it));
      container.appendChild(section);
    }
  }

  function itemEl(it) {
    const row = document.createElement("div");
    row.className = "cl-item" + (it.ticked ? " is-ticked" : "");
    row.dataset.id = it.id;

    const meta = [];
    if (it.reminder_time) meta.push(`<span class="cl-meta-badge">⏰ ${it.reminder_time}</span>`);
    if (it.time_of_day && it.time_of_day !== "anytime") {
      const tod = it.time_of_day.charAt(0).toUpperCase() + it.time_of_day.slice(1);
      meta.push(`<span class="cl-meta-badge">${tod}</span>`);
    }
    if (it.schedule && it.schedule !== "daily") {
      meta.push(`<span class="cl-meta-badge">${scheduleLabel(it)}</span>`);
    }
    if (it.recurrence_end) {
      meta.push(`<span class="cl-meta-badge">until ${it.recurrence_end}</span>`);
    }

    row.innerHTML = `
      <button type="button" class="cl-check" aria-label="Toggle">✓</button>
      <div class="cl-main">
        <div class="cl-name"></div>
        ${meta.length ? `<div class="cl-meta">${meta.join("")}</div>` : ""}
      </div>
      <button type="button" class="cl-edit" aria-label="Edit">✎</button>
    `;
    row.querySelector(".cl-name").textContent = it.name;
    row.querySelector(".cl-check").addEventListener("click", (e) => {
      e.stopPropagation();
      toggleTick(it);
    });
    row.querySelector(".cl-edit").addEventListener("click", (e) => {
      e.stopPropagation();
      openModal(it);
    });
    row.addEventListener("click", () => toggleTick(it));
    return row;
  }

  function scheduleLabel(it) {
    if (it.schedule === "weekdays") return "Weekdays";
    if (it.schedule === "weekends") return "Weekends";
    if (it.schedule === "custom") {
      const names = ["S", "M", "T", "W", "T", "F", "S"];
      const days = (it.schedule_days || "").split(",").filter(Boolean).map(Number);
      return days.map((d) => names[d]).join(" ");
    }
    return "Daily";
  }

  // ── Tick / untick ─────────────────────────────────
  async function toggleTick(it) {
    const wasTicked = it.ticked;
    it.ticked = !it.ticked;
    render();
    try {
      const endpoint = wasTicked ? "untick" : "tick";
      await api(`/api/checklist/items/${it.id}/${endpoint}`, { method: "POST" });
    } catch (err) {
      it.ticked = wasTicked;
      render();
      alert("Couldn't update: " + err.message);
    }
  }

  // ── Modal ─────────────────────────────────────────
  function openModal(item) {
    const editing = Boolean(item);
    $("#cl-modal-title").textContent = editing ? "Edit item" : "New checklist item";
    $("#cl-item-id").value = item?.id || "";
    $("#cl-name").value = item?.name || "";
    $("#cl-notes").value = item?.notes || "";
    $("#cl-time-of-day").value = item?.time_of_day || "anytime";
    $("#cl-schedule").value = item?.schedule || "daily";
    $("#cl-reminder-time").value = item?.reminder_time || "";
    $("#cl-recurrence-end").value = item?.recurrence_end || "";
    $("#cl-group").value = item?.group_name || "";
    refreshGroupList();

    const customDays = (item?.schedule_days || "").split(",").filter(Boolean);
    $$("#cl-weekdays input[type=checkbox]").forEach((cb) => {
      cb.checked = customDays.includes(cb.value);
    });
    toggleWeekdayPicker();

    $("#cl-delete-btn").hidden = !editing;
    $("#cl-modal").hidden = false;
    setTimeout(() => $("#cl-name").focus(), 50);
  }
  function closeModal() { $("#cl-modal").hidden = true; }

  function toggleWeekdayPicker() {
    $("#cl-weekdays").hidden = $("#cl-schedule").value !== "custom";
  }

  let saving = false;
  async function saveItem(e) {
    e.preventDefault();
    if (saving) return;               // guard against double-tap
    const id = $("#cl-item-id").value;
    const payload = {
      name: $("#cl-name").value.trim(),
      notes: $("#cl-notes").value.trim(),
      time_of_day: $("#cl-time-of-day").value,
      schedule: $("#cl-schedule").value,
      reminder_time: $("#cl-reminder-time").value || null,
      recurrence_end: $("#cl-recurrence-end").value || null,
      group_name: $("#cl-group").value.trim() || null,
      schedule_days: $$("#cl-weekdays input:checked").map((cb) => cb.value).join(","),
    };
    if (!payload.name) return;

    saving = true;
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const prevLabel = submitBtn?.textContent;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Saving…";
    }

    try {
      if (id) {
        await api(`/api/checklist/items/${id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await api(`/api/checklist/items`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      closeModal();
      await load();
    } catch (err) {
      alert("Couldn't save: " + err.message);
    } finally {
      saving = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = prevLabel;
      }
    }
  }

  async function deleteItem(e) {
    const id = $("#cl-item-id").value;
    if (!id) return;
    if (!confirm("Delete this item?")) return;
    const btn = e?.currentTarget;
    if (btn) { btn.disabled = true; btn.textContent = "Deleting…"; }
    try {
      await api(`/api/checklist/items/${id}`, { method: "DELETE" });
      closeModal();
      await load();
    } catch (err) {
      alert("Couldn't delete: " + err.message);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Delete"; }
    }
  }

  // ── Load ──────────────────────────────────────────
  async function load() {
    try {
      const data = await api("/api/checklist/items");
      state.items = data.items || [];
      // Derive known groups from the loaded items — avoids a second
      // round-trip to /api/checklist/groups on every page load.
      state.knownGroups = [
        ...new Set(state.items.map((it) => (it.group_name || "").trim()).filter(Boolean)),
      ].sort();
      refreshGroupList();
      render();
    } catch (err) {
      $("#cl-groups").innerHTML =
        `<div class="cl-empty">Failed to load: ${err.message}</div>`;
    }
  }

  function refreshGroupList() {
    const dl = $("#cl-groups-list");
    if (!dl) return;
    dl.innerHTML = state.knownGroups
      .map((g) => `<option value="${g.replace(/"/g, "&quot;")}"></option>`)
      .join("");
  }

  // ── Wire up ───────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    $("#cl-add-btn").addEventListener("click", () => openModal(null));
    $("#cl-modal-close").addEventListener("click", closeModal);
    $("#cl-cancel-btn").addEventListener("click", closeModal);
    $("#cl-delete-btn").addEventListener("click", deleteItem);
    $("#cl-form").addEventListener("submit", saveItem);
    $("#cl-schedule").addEventListener("change", toggleWeekdayPicker);
    $("#cl-modal").addEventListener("click", (e) => {
      if (e.target.id === "cl-modal") closeModal();
    });

    $("#cl-sync-calendar")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      const label = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Syncing…";
      try {
        const r = await api("/api/checklist/sync-calendar", { method: "POST" });
        const parts = [];
        if (r.synced)  parts.push(`${r.synced} synced`);
        if (r.skipped) parts.push(`${r.skipped} skipped (no Google link?)`);
        if (r.failed)  parts.push(`${r.failed} failed`);
        alert(parts.length ? parts.join(", ") : "Nothing to sync.");
      } catch (err) {
        alert("Sync failed: " + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = label;
      }
    });

    // Push UI wiring (push.js is loaded first)
    if (window.ClPush) {
      window.ClPush.init({
        statusEl:    $("#cl-push-status"),
        statusOkEl:  $("#cl-push-status-ok"),
        enableBtn:   $("#cl-push-enable"),
        disableBtn:  $("#cl-push-disable"),
        testBtn:     $("#cl-push-test"),
      });
    }

    load();
  });
})();

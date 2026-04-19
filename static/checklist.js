/* Checklist page — renders grouped items, handles tick/edit, talks to
   /api/checklist/* endpoints. Web Push UI is driven by push.js (loaded
   before this file) which exposes window.ClPush. */

(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const GROUPS = [
    { key: "morning",   label: "Morning"   },
    { key: "afternoon", label: "Afternoon" },
    { key: "evening",   label: "Evening"   },
    { key: "anytime",   label: "Anytime"   },
  ];

  const state = { items: [] };

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

    const byGroup = {};
    for (const g of GROUPS) byGroup[g.key] = [];
    for (const it of state.items) {
      const k = byGroup[it.time_of_day] ? it.time_of_day : "anytime";
      byGroup[k].push(it);
    }

    for (const g of GROUPS) {
      const items = byGroup[g.key];
      if (!items.length) continue;

      const section = document.createElement("div");
      section.innerHTML = `<div class="cl-group-title">${g.label}</div>
                           <div class="cl-list" data-group="${g.key}"></div>`;
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
    if (it.schedule && it.schedule !== "daily") {
      meta.push(`<span class="cl-meta-badge">${scheduleLabel(it)}</span>`);
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

  async function saveItem(e) {
    e.preventDefault();
    const id = $("#cl-item-id").value;
    const payload = {
      name: $("#cl-name").value.trim(),
      notes: $("#cl-notes").value.trim(),
      time_of_day: $("#cl-time-of-day").value,
      schedule: $("#cl-schedule").value,
      reminder_time: $("#cl-reminder-time").value || null,
      schedule_days: $$("#cl-weekdays input:checked").map((cb) => cb.value).join(","),
    };
    if (!payload.name) return;

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
    }
  }

  async function deleteItem() {
    const id = $("#cl-item-id").value;
    if (!id) return;
    if (!confirm("Delete this item?")) return;
    try {
      await api(`/api/checklist/items/${id}`, { method: "DELETE" });
      closeModal();
      await load();
    } catch (err) {
      alert("Couldn't delete: " + err.message);
    }
  }

  // ── Load ──────────────────────────────────────────
  async function load() {
    try {
      const data = await api("/api/checklist/items");
      state.items = data.items || [];
      render();
    } catch (err) {
      $("#cl-groups").innerHTML =
        `<div class="cl-empty">Failed to load: ${err.message}</div>`;
    }
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

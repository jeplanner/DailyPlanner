/* ═══════════════════════════════════════════════════════════════
   OKRs PAGE  (Project → Objective → Key Result → Initiative → Task)
   ═══════════════════════════════════════════════════════════════ */

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));

const state = {
  objectives: [],
  projects: [],                 // [[id, name], ...]
  editingObjectiveId: null,     // null = creating new
  editingKrId: null,
  editingInitiativeId: null,
  pendingKrObjectiveId: null,
  pendingInitiativeKrId: null,
  selectedColor: "#2563eb",
};

function csrfHeader() {
  return { "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "" };
}

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...csrfHeader() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw new Error(data.error || "Request failed");
  return data;
}

// ═══════════════════════════════════════════════════════════════
// LOAD + RENDER
// ═══════════════════════════════════════════════════════════════

async function loadGoals() {
  const includeArchived = $("include-archived")?.checked ? "1" : "0";
  const projectId = $("project-filter")?.value || "";
  const qs = new URLSearchParams({ include_archived: includeArchived });
  if (projectId) {
    qs.set("project_id", projectId);
    qs.set("include_unassigned", "0");
  }
  try {
    const data = await api("GET", `/api/goals?${qs.toString()}`);
    state.objectives = data.objectives || [];
    state.projects = data.projects || [];
    populateProjectSelectors();
    renderObjectives();
    populateCategorySuggest();
  } catch (err) {
    console.error(err);
    showToast("Failed to load OKRs", "error");
  }
}

function populateProjectSelectors() {
  const filter = $("project-filter");
  const omProject = $("om-project");

  const currentFilter = filter?.value || "";
  if (filter) {
    filter.innerHTML =
      `<option value="">All projects</option>` +
      state.projects.map(([id, name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join("");
    filter.value = currentFilter;
  }

  if (omProject) {
    const current = omProject.value;
    omProject.innerHTML =
      `<option value="">— Unassigned —</option>` +
      state.projects.map(([id, name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join("");
    omProject.value = current;
  }
}

function renderObjectives() {
  const container = $("goals-list");
  const empty = $("goals-empty");
  if (!state.objectives.length) {
    container.innerHTML = "";
    empty.style.display = "block";
    if (window.feather) feather.replace();
    return;
  }
  empty.style.display = "none";

  // Group by project
  const byProject = new Map();
  for (const o of state.objectives) {
    const key = o.project_id || "__unassigned__";
    if (!byProject.has(key)) byProject.set(key, []);
    byProject.get(key).push(o);
  }

  const projectNameMap = new Map(state.projects);
  const keys = [...byProject.keys()].sort((a, b) => {
    if (a === "__unassigned__") return 1;
    if (b === "__unassigned__") return -1;
    const na = (projectNameMap.get(a) || "").toLowerCase();
    const nb = (projectNameMap.get(b) || "").toLowerCase();
    return na.localeCompare(nb);
  });

  const singleProjectView = keys.length === 1;
  const sections = [];
  for (const key of keys) {
    const objs = byProject.get(key);
    const label =
      key === "__unassigned__"
        ? "Unassigned · personal objectives"
        : (projectNameMap.get(key) || "Unknown project");
    if (!singleProjectView) {
      sections.push(`<div class="project-group-header">${esc(label)}</div>`);
    }
    sections.push(objs.map(renderObjectiveCard).join(""));
  }

  container.innerHTML = sections.join("");
  if (window.feather) feather.replace();
}

function renderObjectiveCard(o) {
  const color = o.color || "#2563eb";
  const progress = Math.round(o._progress || 0);
  const dueLabel = formatDueLabel(o.target_date);
  const statusClass = o.status && o.status !== "active" ? o.status : "";
  const projectBadge = o.project_name
    ? `<span class="goal-category" style="background:#eef2ff;color:#4338ca;">📁 ${esc(o.project_name)}</span>`
    : "";

  return `
    <div class="goal-card ${statusClass}" data-objective-id="${o.id}">
      <div class="goal-card-header">
        <div class="goal-color-bar" style="background:${esc(color)}"></div>
        <div class="goal-card-body-wrap">
          <div class="goal-title-row">
            <div class="goal-title">${esc(o.title)}</div>
            ${projectBadge}
            ${o.category ? `<span class="goal-category">${esc(o.category)}</span>` : ""}
            ${o.time_horizon ? `<span class="goal-horizon">${esc(o.time_horizon)}</span>` : ""}
          </div>
          ${o.description ? `<div class="goal-description">${esc(o.description)}</div>` : ""}
          ${dueLabel ? `<div class="goal-due ${dueLabel.cls}">${dueLabel.text}</div>` : ""}
          <div class="goal-progress-wrap">
            <div class="progress-bar"><div class="progress-bar-fill" style="width:${progress}%;background:${esc(color)}"></div></div>
            <div class="progress-label">${progress}%</div>
          </div>
        </div>
        <div class="goal-actions">
          <button class="icon-btn" title="Edit" onclick="openEditObjectiveModal('${o.id}')"><i data-feather="edit-2"></i></button>
          <button class="icon-btn" title="Archive / unarchive" onclick="toggleObjectiveArchived('${o.id}')"><i data-feather="${o.status === 'active' ? 'archive' : 'rotate-ccw'}"></i></button>
          <button class="icon-btn danger" title="Delete" onclick="deleteObjective('${o.id}')"><i data-feather="trash-2"></i></button>
        </div>
      </div>
      <div class="objective-list">
        ${(o.key_results || []).map(kr => renderKr(o, kr)).join("")}
        <button class="add-inline" onclick="openNewKrModal('${o.id}')"><i data-feather="plus"></i> Add key result</button>
      </div>
    </div>
  `;
}

function renderKr(o, kr) {
  const progress = Math.round(kr._progress || 0);
  const unit = kr.unit || "";
  const color = o.color || "#10b981";
  const initiatives = kr.initiatives || [];

  return `
    <div class="kr-block" data-kr-id="${kr.id}">
      <div class="kr-row">
        <div>
          <div class="kr-title">${esc(kr.title)}</div>
          <div class="kr-meta">
            Start ${fmtNum(kr.start_value)}${esc(unit)} · Target ${fmtNum(kr.target_value)}${esc(unit)}
          </div>
        </div>
        <div class="kr-progress-group">
          <input type="number" step="any" class="kr-current-edit"
                 value="${kr.current_value ?? 0}"
                 title="Update current value"
                 onchange="updateKrCurrent('${kr.id}', this.value)">
          <div class="kr-progress-bar"><div class="kr-progress-bar-fill" style="width:${progress}%;background:${esc(color)}"></div></div>
          <div class="progress-label">${progress}%</div>
        </div>
        <div class="objective-actions">
          <button class="icon-btn" title="Edit" onclick="openEditKrModal('${kr.id}')"><i data-feather="edit-2"></i></button>
          <button class="icon-btn danger" title="Delete" onclick="deleteKr('${kr.id}')"><i data-feather="trash-2"></i></button>
        </div>
      </div>
      <div class="initiative-list">
        ${initiatives.map(i => renderInitiative(i)).join("")}
        <button class="add-inline add-inline-sub" onclick="openNewInitiativeModal('${kr.id}')"><i data-feather="plus"></i> Add initiative</button>
      </div>
    </div>
  `;
}

function renderInitiative(i) {
  return `
    <div class="initiative-row" data-initiative-id="${i.id}">
      <div class="initiative-icon">⚙</div>
      <div class="initiative-body">
        <div class="initiative-title">${esc(i.title)}</div>
        ${i.description ? `<div class="initiative-desc">${esc(i.description)}</div>` : ""}
      </div>
      <div class="objective-actions">
        <button class="icon-btn" title="Edit" onclick="openEditInitiativeModal('${i.id}')"><i data-feather="edit-2"></i></button>
        <button class="icon-btn danger" title="Delete" onclick="deleteInitiative('${i.id}')"><i data-feather="trash-2"></i></button>
      </div>
    </div>
  `;
}

function fmtNum(n) {
  if (n === null || n === undefined || n === "") return "0";
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  if (Math.abs(num) >= 10000) return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return (num % 1 === 0) ? num.toString() : num.toFixed(2).replace(/\.?0+$/, "");
}

function formatDueLabel(dateStr) {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  const now = new Date();
  const days = Math.round((target - now) / (1000 * 60 * 60 * 24));
  if (days < 0) return { text: `Overdue by ${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"}`, cls: "overdue" };
  if (days === 0) return { text: "Due today", cls: "soon" };
  if (days <= 14) return { text: `Due in ${days} day${days === 1 ? "" : "s"}`, cls: "soon" };
  return { text: `Due ${target.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`, cls: "" };
}

function populateCategorySuggest() {
  const datalist = $("cat-suggest");
  if (!datalist) return;
  const cats = new Set(state.objectives.map(o => o.category).filter(Boolean));
  datalist.innerHTML = [...cats].map(c => `<option value="${esc(c)}">`).join("");
}

// ═══════════════════════════════════════════════════════════════
// OBJECTIVE MODAL
// ═══════════════════════════════════════════════════════════════

function openNewObjectiveModal() {
  state.editingObjectiveId = null;
  state.selectedColor = "#2563eb";
  $("objective-modal-title").textContent = "New Objective";
  $("om-project").value = $("project-filter")?.value || "";
  $("om-title").value = "";
  $("om-description").value = "";
  $("om-category").value = "";
  $("om-horizon").value = "quarterly";
  $("om-start").value = "";
  $("om-target").value = "";
  highlightColor(state.selectedColor);
  $("objective-modal").classList.remove("hidden");
  setTimeout(() => $("om-title").focus(), 50);
}

function openEditObjectiveModal(objectiveId) {
  const o = state.objectives.find(x => x.id === objectiveId);
  if (!o) return;
  state.editingObjectiveId = objectiveId;
  state.selectedColor = o.color || "#2563eb";
  $("objective-modal-title").textContent = "Edit Objective";
  $("om-project").value = o.project_id || "";
  $("om-title").value = o.title || "";
  $("om-description").value = o.description || "";
  $("om-category").value = o.category || "";
  $("om-horizon").value = o.time_horizon || "quarterly";
  $("om-start").value = o.start_date || "";
  $("om-target").value = o.target_date || "";
  highlightColor(state.selectedColor);
  $("objective-modal").classList.remove("hidden");
}

function closeObjectiveModal() {
  $("objective-modal").classList.add("hidden");
  state.editingObjectiveId = null;
}

function highlightColor(color) {
  document.querySelectorAll("#om-color button").forEach(btn => {
    btn.classList.toggle("selected", btn.dataset.color === color);
  });
}

async function saveObjectiveModal() {
  const payload = {
    project_id: $("om-project").value || null,
    title: $("om-title").value.trim(),
    description: $("om-description").value.trim(),
    category: $("om-category").value.trim(),
    time_horizon: $("om-horizon").value,
    start_date: $("om-start").value || null,
    target_date: $("om-target").value || null,
    color: state.selectedColor,
  };
  if (!payload.title) { showToast("Title is required", "error"); return; }

  try {
    if (state.editingObjectiveId) {
      await api("PATCH", `/api/goals/${state.editingObjectiveId}`, payload);
      showToast("Objective updated", "success");
    } else {
      await api("POST", "/api/goals", payload);
      showToast("Objective created", "success");
    }
    closeObjectiveModal();
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Save failed", "error");
  }
}

async function deleteObjective(objectiveId) {
  const o = state.objectives.find(x => x.id === objectiveId);
  if (!o) return;
  if (!confirm(`Delete "${o.title}" and ALL its key results and initiatives? This cannot be undone.`)) return;
  try {
    await api("DELETE", `/api/goals/${objectiveId}`);
    showToast("Objective deleted", "success");
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Delete failed", "error");
  }
}

async function toggleObjectiveArchived(objectiveId) {
  const o = state.objectives.find(x => x.id === objectiveId);
  if (!o) return;
  const newStatus = o.status === "active" ? "paused" : "active";
  try {
    await api("PATCH", `/api/goals/${objectiveId}`, { status: newStatus });
    showToast(newStatus === "paused" ? "Objective archived" : "Objective reactivated", "success");
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Update failed", "error");
  }
}

// ═══════════════════════════════════════════════════════════════
// KEY RESULT MODAL
// ═══════════════════════════════════════════════════════════════

function openNewKrModal(objectiveId) {
  state.editingKrId = null;
  state.pendingKrObjectiveId = objectiveId;
  $("kr-modal-title").textContent = "New Key Result";
  $("km-title").value = "";
  $("km-start").value = 0;
  $("km-current").value = 0;
  $("km-target").value = "";
  $("km-unit").value = "";
  $("km-direction").value = "up";
  const auto = $("km-auto-progress");
  if (auto) auto.checked = false;
  $("kr-modal").classList.remove("hidden");
  setTimeout(() => $("km-title").focus(), 50);
}

function openEditKrModal(krId) {
  let kr = null, parentObj = null;
  for (const o of state.objectives) {
    const k = (o.key_results || []).find(x => x.id === krId);
    if (k) { kr = k; parentObj = o; break; }
  }
  if (!kr) return;
  state.editingKrId = krId;
  state.pendingKrObjectiveId = parentObj.id;
  $("kr-modal-title").textContent = "Edit Key Result";
  $("km-title").value = kr.title || "";
  $("km-start").value = kr.start_value ?? 0;
  $("km-current").value = kr.current_value ?? 0;
  $("km-target").value = kr.target_value ?? "";
  $("km-unit").value = kr.unit || "";
  $("km-direction").value = kr.direction || "up";
  const auto = $("km-auto-progress");
  if (auto) auto.checked = !!kr.auto_progress;
  $("kr-modal").classList.remove("hidden");
}

function closeKrModal() {
  $("kr-modal").classList.add("hidden");
  state.editingKrId = null;
  state.pendingKrObjectiveId = null;
}

async function saveKrModal() {
  const target = parseFloat($("km-target").value);
  if (Number.isNaN(target)) { showToast("Target is required", "error"); return; }

  const payload = {
    title: $("km-title").value.trim(),
    start_value: parseFloat($("km-start").value) || 0,
    current_value: parseFloat($("km-current").value) || 0,
    target_value: target,
    unit: $("km-unit").value.trim() || null,
    direction: $("km-direction").value,
    auto_progress: !!($("km-auto-progress") && $("km-auto-progress").checked),
  };
  if (!payload.title) { showToast("Title is required", "error"); return; }

  try {
    if (state.editingKrId) {
      await api("PATCH", `/api/key-results/${state.editingKrId}`, payload);
      showToast("Key result updated", "success");
    } else {
      payload.objective_id = state.pendingKrObjectiveId;
      await api("POST", "/api/key-results", payload);
      showToast("Key result created", "success");
    }
    closeKrModal();
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Save failed", "error");
  }
}

async function deleteKr(krId) {
  if (!confirm("Delete this key result and all its initiatives?")) return;
  try {
    await api("DELETE", `/api/key-results/${krId}`);
    showToast("Key result deleted", "success");
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Delete failed", "error");
  }
}

async function updateKrCurrent(krId, value) {
  const num = parseFloat(value);
  if (Number.isNaN(num)) return;
  try {
    await api("PATCH", `/api/key-results/${krId}`, { current_value: num });
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Update failed", "error");
  }
}

// ═══════════════════════════════════════════════════════════════
// INITIATIVE MODAL
// ═══════════════════════════════════════════════════════════════

function openNewInitiativeModal(krId) {
  state.editingInitiativeId = null;
  state.pendingInitiativeKrId = krId;
  $("initiative-modal-title").textContent = "New Initiative";
  $("im-title").value = "";
  $("im-description").value = "";
  $("initiative-modal").classList.remove("hidden");
  setTimeout(() => $("im-title").focus(), 50);
}

function openEditInitiativeModal(initiativeId) {
  let init = null, parentKr = null;
  for (const o of state.objectives) {
    for (const k of (o.key_results || [])) {
      const i = (k.initiatives || []).find(x => x.id === initiativeId);
      if (i) { init = i; parentKr = k; break; }
    }
    if (init) break;
  }
  if (!init) return;
  state.editingInitiativeId = initiativeId;
  state.pendingInitiativeKrId = parentKr.id;
  $("initiative-modal-title").textContent = "Edit Initiative";
  $("im-title").value = init.title || "";
  $("im-description").value = init.description || "";
  $("initiative-modal").classList.remove("hidden");
}

function closeInitiativeModal() {
  $("initiative-modal").classList.add("hidden");
  state.editingInitiativeId = null;
  state.pendingInitiativeKrId = null;
}

async function saveInitiativeModal() {
  const payload = {
    title: $("im-title").value.trim(),
    description: $("im-description").value.trim(),
  };
  if (!payload.title) { showToast("Title is required", "error"); return; }

  try {
    if (state.editingInitiativeId) {
      await api("PATCH", `/api/initiatives/${state.editingInitiativeId}`, payload);
      showToast("Initiative updated", "success");
    } else {
      payload.key_result_id = state.pendingInitiativeKrId;
      await api("POST", "/api/initiatives", payload);
      showToast("Initiative created", "success");
    }
    closeInitiativeModal();
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Save failed", "error");
  }
}

async function deleteInitiative(initiativeId) {
  if (!confirm("Delete this initiative? Tasks linked to it will lose their initiative link but remain in the project.")) return;
  try {
    await api("DELETE", `/api/initiatives/${initiativeId}`);
    showToast("Initiative deleted", "success");
    await loadGoals();
  } catch (err) {
    showToast(err.message || "Delete failed", "error");
  }
}

// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#om-color button").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedColor = btn.dataset.color;
      highlightColor(state.selectedColor);
    });
  });

  $("include-archived")?.addEventListener("change", loadGoals);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeObjectiveModal();
      closeKrModal();
      closeInitiativeModal();
    }
  });

  loadGoals();
});

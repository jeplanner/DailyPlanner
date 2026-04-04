/* =========================================================
   PROJECT TASKS — SINGLE ENTRY FILE
   ========================================================= */

/* -------------------------
   Utilities
------------------------- */
function $(id) { return document.getElementById(id); }

function showProjectToast(message, type = "info", duration = 2500) {
  const container = $("project-toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `proj-toast proj-toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* -------------------------
   Sorting
------------------------- */
function initSort() {
  const sortSelect = $("sortSelect");
  if (!sortSelect) return;

  sortSelect.addEventListener("change", async e => {
    await fetch(`/projects/${sortSelect.dataset.projectId}/set-sort`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sort: e.target.value })
    });
    location.reload();
  });
}

/* -------------------------
   Drag & Drop Reorder
------------------------- */
let draggedId = null;

window.dragStart = e => {
  draggedId = e.target.closest(".task")?.dataset.id || null;
};

window.dragOver = e => e.preventDefault();

window.dropTask = e => {
  e.preventDefault();
  const target = e.target.closest(".task");
  if (!draggedId || !target) return;

  const targetId = target.dataset.id;
  if (draggedId === targetId) return;

  fetch("/projects/tasks/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dragged_id: draggedId, target_id: targetId })
  })
    .then(r => {
      if (r.ok) location.reload();
      else showProjectToast("Reorder failed", "error");
    })
    .catch(console.error);
};

/* -------------------------
   Task Expand / Collapse
------------------------- */
window.toggleTask = taskId => {
  const el = $(`task-${taskId}`);
  if (el) el.classList.toggle("open");
};

/* -------------------------
   Pin Task
------------------------- */
window.togglePin = btn => {
  const task = btn.closest(".task");
  if (!task) return;

  const isPinned = task.dataset.pinned === "1";

  fetch("/projects/tasks/pin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: task.dataset.id, is_pinned: !isPinned })
  }).then(() => {
    task.dataset.pinned = isPinned ? "0" : "1";
    btn.classList.toggle("pinned", !isPinned);
  }).catch(console.error);
};

/* -------------------------
   Status Update
------------------------- */
window.updateStatus = (taskId, status, date = null) => {
  const task = $(`task-${taskId}`);
  if (!task) return;

  const prev = task.dataset.status;
  task.dataset.status = status;

  fetch("/projects/tasks/status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, status, date })
  })
    .then(r => {
      if (!r.ok) throw new Error();
      location.reload();
    })
    .catch(() => {
      task.dataset.status = prev;
      showProjectToast("Failed to update status", "error");
    });
};

/* -------------------------
   Priority Cycle
------------------------- */
window.cyclePriority = async (e, taskId) => {
  const task = document.querySelector(`.task[data-id="${taskId}"]`);
  if (!task) return;
  const icon = task.querySelector(".priority-icon");
  const order = ["low", "medium", "high"];
  const current = icon?.dataset.priority || "medium";
  const next = order[(order.indexOf(current) + 1) % order.length];
  if (icon) icon.dataset.priority = next;

  try {
    await fetch("/projects/tasks/update-priority", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, priority: next })
    });
    showProjectToast(`Priority → ${next}`, "success", 1500);
  } catch (err) {
    console.error(err);
  }
};

/* -------------------------
   Planned / Actual / Due Time
------------------------- */
window.updatePlanned = function (taskId, value) {
  fetch("/projects/tasks/update-planned", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, planned_hours: parseFloat(value) || 0 })
  }).catch(console.error);
};

window.updateActual = function (taskId, value) {
  fetch("/projects/tasks/update-actual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, actual_hours: parseFloat(value) || 0 })
  }).catch(console.error);
};

window.updateDueTime = function (taskId, value) {
  fetch("/projects/tasks/update-time", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: taskId, due_time: value || null })
  }).catch(console.error);
};

/* -------------------------
   Eisenhower
------------------------- */
window.openEisenhower = function (taskId) {
  const today = new Date().toLocaleDateString("en-CA");
  // Simple quadrant picker — replace with modal if needed
  const options = ["do", "decide", "delegate", "eliminate"];
  const choice = window.prompt(
    `Send to Eisenhower quadrant:\n${options.join(" / ")}`,
    "do"
  );
  if (!choice) return;
  const quadrant = choice.trim().toLowerCase();
  if (!options.includes(quadrant)) {
    showProjectToast("Invalid quadrant", "error");
    return;
  }

  fetch("/projects/tasks/send-to-eisenhower", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, plan_date: today, quadrant })
  })
    .then(r => r.json())
    .then(data => {
      if (data.status === "ok") {
        showProjectToast("Sent to Eisenhower ✓", "success");
        const btn = $(`send-${taskId}`);
        if (btn) btn.classList.add("sent");
      } else if (data.status === "already-sent") {
        showProjectToast("Already in Eisenhower", "info");
      }
    })
    .catch(console.error);
};

/* -------------------------
   Filters
------------------------- */
function toggleHideCompleted(checked) {
  const url = new URL(window.location.href);
  url.searchParams.set("hide_completed", checked ? "1" : "0");
  window.location.href = url.toString();
}

function toggleFilter(key, checked) {
  const url = new URL(window.location.href);
  url.searchParams.set(key, checked ? "1" : "0");
  window.location.href = url.toString();
}

/* -------------------------
   Due Badge Formatting
------------------------- */
function formatDueBadges() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  document.querySelectorAll(".due-badge").forEach(badge => {
    const dueStr = badge.dataset.due;
    if (!dueStr) return;

    // Parse without timezone shift
    const [y, m, d] = dueStr.split("-").map(Number);
    const due = new Date(y, m - 1, d);
    const diff = Math.round((due - today) / 86400000);
    badge.classList.remove("today", "soon", "overdue");

    if (diff === 0) {
      badge.textContent = "⏰ Today";
      badge.classList.add("today");
    } else if (diff === 1) {
      badge.textContent = "⏰ Tomorrow";
      badge.classList.add("soon");
    } else if (diff > 1) {
      badge.textContent = `⏰ In ${diff} days`;
      badge.classList.add("soon");
    } else {
      badge.textContent = `⚠ ${Math.abs(diff)} days overdue`;
      badge.classList.add("overdue");
    }
  });
}

/* -------------------------
   Project Health
------------------------- */
function calculateProjectHealth() {
  const tasks = document.querySelectorAll(".task");
  if (!tasks.length) return;

  let total = 0, done = 0, progress = 0, overdue = 0;
  let planned = 0, actual = 0;
  const today = new Date().toISOString().slice(0, 10);

  tasks.forEach(t => {
    total++;
    if (t.dataset.status === "done") done++;
    if (t.dataset.status === "in_progress") progress++;

    const due = t.querySelector(".due-date")?.textContent;
    if (due && due < today && t.dataset.status !== "done") overdue++;

    planned += parseFloat(t.querySelector('[onchange*="updatePlanned"]')?.value || 0);
    actual  += parseFloat(t.querySelector('[onchange*="updateActual"]')?.value || 0);
  });

  const completion = total ? (done / total) * 100 : 0;
  const accuracy   = planned
    ? Math.max(0, 100 - Math.abs(actual - planned) / planned * 100)
    : 100;

  const score =
    completion * 0.35 +
    accuracy   * 0.25 +
    (100 - (overdue / total) * 100) * 0.25 +
    Math.min(100, (progress / total) * 100) * 0.15;

  if ($("health-score"))      $("health-score").textContent      = Math.round(score);
  if ($("metric-complete"))   $("metric-complete").textContent   = Math.round(completion) + "%";
  if ($("metric-overdue"))    $("metric-overdue").textContent    = overdue;
  if ($("metric-accuracy"))   $("metric-accuracy").textContent   = Math.round(accuracy) + "%";
  if ($("metric-progress"))   $("metric-progress").textContent   = progress;
}

/* -------------------------
   Notes → Bulk Tasks
------------------------- */
function extractTasksFromNotes(text) {
  return text
    .split("\n")
    .map(l => l.trim())
    .filter(Boolean)
    .map(l => l.replace(/^[-•]\s*/, ""));
}

/* -------------------------
   Inline Edit (title)
------------------------- */
window.enableEdit = function (el, taskId) {
  if (!el || !taskId) return;

  el.contentEditable = "true";
  el.focus();
  document.execCommand("selectAll", false, null);
  document.getSelection()?.collapseToEnd();

  el.onblur   = () => saveEdit(el, taskId);
  el.onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); el.blur(); } };
};

function saveEdit(el, taskId) {
  el.contentEditable = "false";
  const text = el.textContent.trim();
  if (!text) return;

  fetch(`/projects/tasks/${taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_text: text })
  })
    .then(r => { if (r.ok) showProjectToast("Saved ✓", "success", 1500); })
    .catch(console.error);
}

/* -------------------------
   Delegation
------------------------- */
window.updateDelegation = function (taskId, value) {
  if (!taskId) return;
  fetch("/projects/tasks/update-delegation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: taskId, delegated_to: value || null })
  }).catch(console.error);
};

/* -------------------------
   Planning (start date + duration)
------------------------- */
window.updatePlanning = function (taskId) {
  if (!taskId) return;

  const taskEl = $(`task-${taskId}`);
  if (!taskEl) return;

  const startInput    = taskEl.querySelector(".start-date");
  const durationInput = taskEl.querySelector(".duration-days");
  if (!startInput || !durationInput) return;

  fetch("/projects/tasks/update-planning", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: taskId,
      start_date: startInput.value,
      duration_days: durationInput.value
    })
  })
    .then(r => r.json())
    .then(res => {
      if (res?.due_date) {
        const dueBadge = taskEl.querySelector(".due-badge");
        if (dueBadge) dueBadge.dataset.due = res.due_date;
        formatDueBadges();
      }
      calculateProjectHealth();
    })
    .catch(console.error);
};

/* -------------------------
   Eliminate Task
------------------------- */
window.eliminateTask = function (taskId) {
  if (!taskId) return;
  if (!window.confirm("Delete this task? This cannot be undone.")) return;

  fetch("/projects/tasks/eliminate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: taskId, reason: null })
  })
    .then(r => {
      if (!r.ok) throw new Error("Eliminate failed");
      location.reload();
    })
    .catch(() => showProjectToast("Failed to delete task", "error"));
};

/* -------------------------
   Save Task (full card)
------------------------- */
function serializeTask(taskEl) {
  return {
    task_text:     taskEl.querySelector(".task-title")?.textContent.trim() || null,
    priority:      taskEl.querySelector(".priority-icon")?.dataset.priority || null,
    status:        taskEl.dataset.status || null,
    start_date:    taskEl.querySelector(".start-date")?.value || null,
    duration_days: taskEl.querySelector(".duration-days")?.value || 0,
    planned_hours: taskEl.querySelector('[onchange*="updatePlanned"]')?.value || 0,
    actual_hours:  taskEl.querySelector('[onchange*="updateActual"]')?.value || 0,
    due_time:      taskEl.querySelector('select[onchange*="updateDueTime"]')?.value || null,
    delegated_to:  taskEl.querySelector('input[maxlength="25"]')?.value || null
  };
}

document.addEventListener("click", async e => {
  const btn = e.target.closest(".save-task-btn");
  if (!btn) return;

  const taskEl = btn.closest(".task");
  if (!taskEl) return;

  const taskId = taskEl.dataset.id;
  if (!taskId) return;

  const payload = serializeTask(taskEl);
  if (!payload.task_text) {
    showProjectToast("Task text cannot be empty", "error");
    return;
  }

  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = "Saving…";

  try {
    const res = await fetch(`/projects/tasks/${taskId}/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Save failed");
    showProjectToast("Saved ✓", "success", 1500);
    location.reload();
  } catch (err) {
    console.error(err);
    showProjectToast("Save failed. Try again.", "error");
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

/* -------------------------
   Recurrence
------------------------- */
async function updateRecurrence(taskId, type) {
  const taskEl = $(`task-${taskId}`);
  if (!taskEl) return;

  await fetch(`/projects/tasks/${taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_recurring: type !== "none", recurrence_type: type })
  });

  const weeklyBox = taskEl.querySelector(".recurrence-days");
  if (weeklyBox) weeklyBox.style.display = type === "weekly" ? "flex" : "none";

  const badge = taskEl.querySelector(".repeat-badge");
  if (type === "none") {
    if (badge) badge.remove();
  } else {
    if (!badge) {
      const newBadge = document.createElement("span");
      newBadge.className = "repeat-badge";
      taskEl.querySelector(".task-header")?.appendChild(newBadge);
    }
    const finalBadge = taskEl.querySelector(".repeat-badge");
    if (finalBadge) finalBadge.textContent = `🔁 ${type}`;
  }
}

function updateRecurrenceDays(taskId) {
  const box = $(`task-${taskId}`);
  if (!box) return;
  const days = [...box.querySelectorAll(".recurrence-days input:checked")]
    .map(cb => parseInt(cb.value));

  fetch(`/projects/tasks/${taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recurrence_days: days })
  }).catch(console.error);
}

function toggleAutoAdvance(taskId, enabled) {
  fetch(`/projects/tasks/${taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ auto_advance: enabled })
  }).catch(console.error);
}

/* -------------------------
   Task Action Sheet (long-press)
------------------------- */
let currentSheetTask = {};

function openTaskSheet(task) {
  currentSheetTask = task;
  const titleEl = $("sheet-title");
  const toggleEl = $("autoAdvanceToggle");
  if (titleEl) titleEl.textContent = task.text;
  if (toggleEl) toggleEl.checked = !!task.autoAdvance;
  $("task-action-sheet")?.classList.remove("hidden");
}

function closeTaskSheet() {
  $("task-action-sheet")?.classList.add("hidden");
  currentSheetTask = {};
}

function sheetCompleteToday() {
  fetch("/projects/tasks/status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: currentSheetTask.taskId,
      status: "done",
      date: currentSheetTask.date
    })
  })
    .then(() => { closeTaskSheet(); location.reload(); })
    .catch(() => showProjectToast("Failed to complete task", "error"));
}

function sheetEditAll() {
  closeTaskSheet();
  const taskEl = $(`task-${currentSheetTask.taskId}`);
  if (!taskEl) return;
  const titleEl = taskEl.querySelector(".task-title");
  if (titleEl) window.enableEdit(titleEl, currentSheetTask.taskId);
}

function sheetToggleAutoAdvance(enabled) {
  fetch(`/projects/tasks/${currentSheetTask.taskId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ auto_advance: enabled })
  }).catch(console.error);
}

function attachLongPress(el, onLongPress) {
  let timer = null;
  let moved = false;

  el.addEventListener("mousedown", e => {
    if (e.button !== 0) return;
    moved = false;
    timer = setTimeout(() => { if (!moved) onLongPress(e); }, 500);
  });
  el.addEventListener("mousemove",  () => { moved = true; clearTimeout(timer); });
  el.addEventListener("mouseup",    () => clearTimeout(timer));
  el.addEventListener("mouseleave", () => clearTimeout(timer));

  el.addEventListener("touchstart", () => { timer = setTimeout(onLongPress, 500); },
    { passive: true });
  el.addEventListener("touchend", () => clearTimeout(timer));

  el.addEventListener("contextmenu", e => { e.preventDefault(); onLongPress(e); });
}

/* -------------------------
   Number controls
------------------------- */
function attachScrollNumbers() {
  document.querySelectorAll(".scroll-number").forEach(el => {
    el.addEventListener("wheel", function (e) {
      e.preventDefault();
      let value = parseInt(this.value || 0);
      value += e.deltaY < 0 ? 1 : -1;
      value = Math.min(100, Math.max(0, value));
      this.value = value;
      this.dispatchEvent(new Event("change"));
    }, { passive: false });
  });
}

window.adjustInlineNumber = function (btn, direction, type, taskId, date = null) {
  const wrapper = btn.closest(".number-control");
  const input   = wrapper.querySelector("input");
  const step    = parseFloat(wrapper.dataset.step || 1);
  let value     = parseFloat(input.value || 0) + direction * step;
  value = Math.min(100, Math.max(0, value));
  input.value = value;

  if (type === "planned") updatePlanned(taskId, value);
  if (type === "actual")  updateActual(taskId, value);
  if (type === "duration") updatePlanning(taskId, date);
};

window.validateInlineNumber = function (input) {
  let value = parseFloat(input.value);
  if (isNaN(value)) value = 0;
  input.value = Math.min(100, Math.max(0, value));
};

document.addEventListener("wheel", e => {
  const wrapper = e.target.closest(".inline-number");
  if (!wrapper) return;
  e.preventDefault();
  const input = wrapper.querySelector("input");
  const step  = parseFloat(wrapper.dataset.step || 1);
  let value   = parseFloat(input.value || 0);
  value += e.deltaY < 0 ? step : -step;
  input.value = Math.min(100, Math.max(0, value));
}, { passive: false });

/* -------------------------
   Single DOMContentLoaded init
------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  initSort();
  formatDueBadges();
  calculateProjectHealth();
  attachScrollNumbers();

  // Bulk add from notes
  $("addTasksFromNotes")?.addEventListener("click", async () => {
    const notes = $("projectNotes");
    const tasks = extractTasksFromNotes(notes.value);
    if (!tasks.length) { showProjectToast("No tasks found in notes", "error"); return; }

    const res = await fetch("/projects/tasks/bulk-add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: notes.dataset.projectId, tasks })
    });
    if (res.ok) location.reload();
    else showProjectToast("Bulk add failed", "error");
  });

  // Long-press on task rows → action sheet
  document.querySelectorAll(".task").forEach(el => {
    attachLongPress(el, () => {
      openTaskSheet({
        taskId: el.dataset.id,
        date: el.dataset.date,
        text: el.querySelector(".task-title")?.innerText || "",
        autoAdvance: el.dataset.autoAdvance === "true"
      });
    });
  });
});

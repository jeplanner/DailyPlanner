/* =========================================================
   PROJECT TASKS  --  Microsoft Project-style task planner
   ========================================================= */

/* ---------------------------------------------------------
   Helpers
   --------------------------------------------------------- */
const _q  = (sel, ctx = document) => ctx.querySelector(sel);
const _qa = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const _id = id => document.getElementById(id);

function _post(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function _put(url, body) {
  return fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/* Currently open task id in the bottom sheet */
let _sheetTaskId = null;

/* Scheduled reminder timeouts (keyed by taskId) */
const _reminders = {};

/* Selected priority in the add-task picker */
let _addPriority = "medium";

/* ---------------------------------------------------------
   Priority Picker
   --------------------------------------------------------- */
function initPrioPicker() {
  const picker = _id("prio-picker");
  if (!picker) return;

  _qa(".pp-btn", picker).forEach(btn => {
    btn.addEventListener("click", () => {
      _qa(".pp-btn", picker).forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _addPriority = btn.dataset.p;
    });
  });
}

/* ---------------------------------------------------------
   Add Task
   --------------------------------------------------------- */
function initAddTask() {
  const input = _id("add-task-input");
  const btn   = _id("add-task-btn");
  if (!input) return;

  input.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); addTask(); }
  });
  if (btn) btn.addEventListener("click", addTask);
}

async function addTask() {
  const input = _id("add-task-input");
  const dateInput = _id("add-task-date");
  const text = (input?.value || "").trim();
  if (!text) return;

  try {
    const res = await _post(`/projects/${PROJECT_ID}/tasks/add-ajax`, {
      task_text: text,
      priority: _addPriority,
      start_date: dateInput?.value || "",
    });

    if (!res.ok) throw new Error("Add failed");

    input.value = "";
    showToast("Task added", "success");
    location.reload();
  } catch (err) {
    console.error(err);
    showToast("Failed to add task", "error");
  }
}

/* ---------------------------------------------------------
   Toggle Task Done (checkbox)
   --------------------------------------------------------- */
function toggleTaskDone(checkbox, taskId, date) {
  const status = checkbox.checked ? "done" : "open";
  const row = checkbox.closest(".task-row");

  _post("/projects/tasks/status", { task_id: taskId, status, date })
    .then(r => {
      if (!r.ok) throw new Error();

      if (row) {
        row.classList.toggle("done", status === "done");
        row.dataset.status = status;
        // update the status select in the same row
        const sel = _q(".status-select", row);
        if (sel) sel.value = status;
      }

      // If hide-done filter is active, fade out
      const hiding = new URL(location.href).searchParams.get("hide_completed") === "1";
      if (hiding && status === "done" && row) {
        row.style.transition = "opacity .4s, transform .4s";
        row.style.opacity = "0";
        row.style.transform = "translateX(20px)";
        setTimeout(() => row.remove(), 420);
      }

      updateProjectStats();
      showToast(status === "done" ? "Marked complete" : "Reopened", "success");
    })
    .catch(() => {
      checkbox.checked = !checkbox.checked;
      showToast("Failed to update status", "error");
    });
}

/* ---------------------------------------------------------
   Status Select
   --------------------------------------------------------- */
function updateStatus(taskId, value, date) {
  const row = document.querySelector(`.task-row[data-id="${taskId}"]`);

  _post("/projects/tasks/status", { task_id: taskId, status: value, date })
    .then(r => {
      if (!r.ok) throw new Error();
      if (row) {
        const isDone = value === "done";
        row.classList.toggle("done", isDone);
        row.dataset.status = value;
        const cb = _q(".task-check", row);
        if (cb) cb.checked = isDone;
        // Update select styling
        const sel = _q(".status-select", row);
        if (sel) {
          sel.className = "status-select status-" + value;
        }
      }
      updateProjectStats();
      showToast("Status updated", "success");
    })
    .catch(() => showToast("Status update failed", "error"));
}

/* ---------------------------------------------------------
   Generic Field Update (inline editing in table)
   --------------------------------------------------------- */
function updateField(taskId, field, value) {
  // Planning fields (start_date, duration_days) need the planning endpoint
  if (field === "start_date" || field === "duration_days") {
    const row = document.querySelector(`.task-row[data-id="${taskId}"]`);
    const startInput = _q('input[type="date"].cell-date', _q(".col-start", row));
    const durInput   = _q('input[type="number"].cell-num', _q(".col-dur", row));

    _post("/projects/tasks/update-planning", {
      task_id: taskId,
      start_date: startInput?.value || "",
      duration_days: durInput?.value || 1,
    })
      .then(r => r.json())
      .then(data => {
        if (data.due_date && row) {
          const dueInput = _q(".col-due input.cell-date", row);
          if (dueInput) dueInput.value = data.due_date;
          updateDueLabel(row, data.due_date);
        }
        updateProjectStats();
      })
      .catch(console.error);
    return;
  }

  // Due date has its own endpoint
  if (field === "due_date") {
    _post("/projects/tasks/update-date", { task_id: taskId, due_date: value })
      .then(() => {
        const row = document.querySelector(`.task-row[data-id="${taskId}"]`);
        if (row) updateDueLabel(row, value);
        updateProjectStats();
      })
      .catch(console.error);
    return;
  }

  // All other fields
  _post(`/projects/tasks/${taskId}/update`, { [field]: value })
    .catch(console.error);
}

/* Helper: refresh the due-label text in a row */
function updateDueLabel(row, dueDateStr) {
  const label = _q(".due-label", row);
  if (!dueDateStr) {
    if (label) label.textContent = "";
    row.classList.remove("overdue");
    return;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [y, m, d] = dueDateStr.split("-").map(Number);
  const due = new Date(y, m - 1, d);
  const diff = Math.round((due - today) / 86400000);

  if (!label) return;
  label.classList.remove("overdue-label");
  row.classList.remove("overdue");

  if (diff < 0) {
    label.textContent = `${Math.abs(diff)}d overdue`;
    label.classList.add("overdue-label");
    row.classList.add("overdue");
  } else if (diff === 0) {
    label.textContent = "Today";
  } else if (diff === 1) {
    label.textContent = "Tomorrow";
  } else {
    label.textContent = `In ${diff}d`;
  }
}

/* ---------------------------------------------------------
   Priority Cycling  (dot click in table)
   --------------------------------------------------------- */
const PRIO_ORDER = ["high", "medium", "low"];

function cyclePriority(taskId, el) {
  const current = el.className.replace("prio-dot prio-", "").trim();
  const idx = PRIO_ORDER.indexOf(current);
  const next = PRIO_ORDER[(idx + 1) % PRIO_ORDER.length];

  el.className = `prio-dot prio-${next}`;
  el.title = next;

  const row = el.closest(".task-row");
  if (row) row.dataset.priority = next;

  _post("/projects/tasks/update-priority", { task_id: taskId, priority: next })
    .then(() => showToast(`Priority: ${next}`, "success"))
    .catch(() => showToast("Priority update failed", "error"));
}

/* ---------------------------------------------------------
   Group Toggle  (collapse/expand)
   --------------------------------------------------------- */
function toggleGroup(el) {
  el.classList.toggle("collapsed");
  const row = el.closest(".group-row");
  if (!row) return;

  const groupName = row.dataset.group;
  const collapsed = el.classList.contains("collapsed");

  _qa(`.task-row[data-group="${groupName}"]`).forEach(tr => {
    tr.classList.toggle("hidden-group", collapsed);
  });

  // Rotate chevron
  const chevron = _q(".group-chevron", el);
  if (chevron) {
    chevron.style.transform = collapsed ? "rotate(-90deg)" : "";
  }
}

/* ---------------------------------------------------------
   View Switching  (table / board)
   --------------------------------------------------------- */
function setTaskView(view) {
  const tableView = _id("table-view");
  const boardView = _id("board-view");
  if (!tableView || !boardView) return;

  tableView.classList.toggle("hidden", view !== "table");
  boardView.classList.toggle("hidden", view !== "board");

  _qa(".vt-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });

  if (view === "board") populateBoard();
}

/* ---------------------------------------------------------
   Board View (Kanban)
   --------------------------------------------------------- */
function populateBoard() {
  // Clear columns
  ["backlog", "open", "in_progress", "done"].forEach(status => {
    const col = _id(`board-${status}`);
    if (col) col.innerHTML = "";
  });

  _qa(".task-row").forEach(row => {
    const status = row.dataset.status || "open";
    const col = _id(`board-${status}`);
    if (!col) return;

    const id   = row.dataset.id;
    const text = _q(".task-text", row)?.textContent.trim() || "";
    const prio = row.dataset.priority || "medium";
    const dueInput = _q(".col-due input.cell-date", row);
    const due  = dueInput?.value || "";

    const card = document.createElement("div");
    card.className = `board-card prio-border-${prio}`;
    card.dataset.id = id;
    card.onclick = () => openTaskDetail(id);

    card.innerHTML = `
      <div class="board-card-title">${_escHtml(text)}</div>
      ${due ? `<div class="board-card-due">${due}</div>` : ""}
    `;
    col.appendChild(card);
  });
}

function _escHtml(str) {
  const el = document.createElement("span");
  el.textContent = str;
  return el.innerHTML;
}

/* ---------------------------------------------------------
   Filters
   --------------------------------------------------------- */
function initFilters() {
  const hideDone = _id("filter-hide-done");
  const overdue  = _id("filter-overdue");

  if (hideDone) {
    hideDone.addEventListener("change", () => {
      const url = new URL(location.href);
      url.searchParams.set("hide_completed", hideDone.checked ? "1" : "0");
      location.href = url.toString();
    });
  }

  if (overdue) {
    overdue.addEventListener("change", () => {
      const url = new URL(location.href);
      url.searchParams.set("overdue_only", overdue.checked ? "1" : "0");
      location.href = url.toString();
    });
  }
}

/* ---------------------------------------------------------
   Sort
   --------------------------------------------------------- */
function initSort() {
  const sel = _id("sort-select");
  if (!sel) return;

  sel.addEventListener("change", async () => {
    await _post(`/projects/${PROJECT_ID}/set-sort`, { sort: sel.value });
    const url = new URL(location.href);
    url.searchParams.set("sort", sel.value);
    location.href = url.toString();
  });
}

/* ---------------------------------------------------------
   Project Stats
   --------------------------------------------------------- */
function updateProjectStats() {
  const rows    = _qa(".task-row");
  const total   = rows.length;
  const done    = rows.filter(r => r.classList.contains("done")).length;
  const overdue = rows.filter(r => r.classList.contains("overdue")).length;

  const elTotal   = _id("stat-total");
  const elDone    = _id("stat-done");
  const elOverdue = _id("stat-overdue");
  const elFill    = _id("proj-progress-fill");

  if (elTotal)   elTotal.textContent   = `${total} task${total !== 1 ? "s" : ""}`;
  if (elDone)    elDone.textContent    = `${done} done`;
  if (elOverdue) elOverdue.textContent = `${overdue} overdue`;

  if (elFill) {
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    elFill.style.width = pct + "%";
  }
}

/* ---------------------------------------------------------
   Task Detail Bottom Sheet
   --------------------------------------------------------- */
async function openTaskDetail(taskId) {
  _sheetTaskId = taskId;

  try {
    const res = await fetch(`/api/v2/project-tasks/${taskId}`);
    if (!res.ok) throw new Error();
    const t = await res.json();

    // Populate fields
    _val("sheet-name",      t.task_text || "");
    _val("sheet-status",    t.status || "open");
    _val("sheet-priority",  t.priority || "medium");
    _val("sheet-start",     t.start_date || "");
    _val("sheet-due",       t.due_date || "");
    _val("sheet-duration",  t.duration_days || "");
    _val("sheet-due-time",  t.due_time || "");
    _val("sheet-planned",   t.planned_hours || "");
    _val("sheet-actual",    t.actual_hours || "");
    _val("sheet-delegate",  t.delegated_to || "");
    _val("sheet-notes",     t.notes || "");
    _val("sheet-reminder",  "");

    // Recurrence
    const recType = t.is_recurring ? (t.recurrence_type || "daily") : "none";
    _val("sheet-recurrence", recType);
    onRecurrenceChange();

    // Populate day chips for weekly
    if (recType === "weekly" && Array.isArray(t.recurrence_days)) {
      _qa("#recurrence-days .day-chip").forEach(chip => {
        chip.classList.toggle("active", t.recurrence_days.includes(parseInt(chip.dataset.day)));
      });
    }

    // Load subtasks
    loadSubtasks(taskId);

    // Store task id on sheet
    const sheet = _id("task-sheet");
    if (sheet) {
      sheet.dataset.taskId = taskId;
      sheet.classList.remove("hidden");
    }

    feather.replace();
  } catch (err) {
    console.error(err);
    showToast("Failed to load task details", "error");
  }
}

function _val(id, value) {
  const el = _id(id);
  if (el) el.value = value;
}

function closeTaskSheet() {
  const sheet = _id("task-sheet");
  if (sheet) sheet.classList.add("hidden");
  _sheetTaskId = null;
}

async function saveTaskSheet() {
  if (!_sheetTaskId) return;

  const name     = _id("sheet-name")?.value.trim();
  const status   = _id("sheet-status")?.value;
  const priority = _id("sheet-priority")?.value;
  const start    = _id("sheet-start")?.value || null;
  const due      = _id("sheet-due")?.value || null;
  const duration = _id("sheet-duration")?.value || null;
  const planned  = _id("sheet-planned")?.value || null;
  const actual   = _id("sheet-actual")?.value || null;
  const delegate = _id("sheet-delegate")?.value || null;
  const notes    = _id("sheet-notes")?.value || null;
  const dueTime  = _id("sheet-due-time")?.value || null;

  if (!name) {
    showToast("Task name cannot be empty", "error");
    return;
  }

  try {
    // Main fields via PUT
    const putRes = await _put(`/api/v2/project-tasks/${_sheetTaskId}`, {
      task_text: name,
      status,
      priority,
      due_date: due,
      duration_days: duration,
      planned_hours: planned,
      actual_hours: actual,
      notes,
    });
    if (!putRes.ok) throw new Error();

    // Additional fields via PATCH endpoint
    const recurrence = _id("sheet-recurrence")?.value || "none";
    const isRecurring = recurrence !== "none";
    const recurrenceDays = isRecurring && recurrence === "weekly"
      ? _qa("#recurrence-days .day-chip.active").map(c => parseInt(c.dataset.day))
      : [];

    await _post(`/projects/tasks/${_sheetTaskId}/update`, {
      start_date: start,
      due_time: dueTime,
      delegated_to: delegate,
      is_recurring: isRecurring,
      recurrence_type: isRecurring ? recurrence : null,
      recurrence_days: recurrenceDays.length ? recurrenceDays : null,
    });

    // Schedule reminder if set
    const reminderMin = _id("sheet-reminder")?.value;
    if (reminderMin !== "" && due && dueTime) {
      scheduleReminder(_sheetTaskId, name, due, dueTime, parseInt(reminderMin));
    }

    closeTaskSheet();
    showToast("Task saved", "success");
    location.reload();
  } catch (err) {
    console.error(err);
    showToast("Failed to save task", "error");
  }
}

/* ---------------------------------------------------------
   Google Calendar Integration
   --------------------------------------------------------- */
function addTaskToGCal(taskId) {
  const row = document.querySelector(`.task-row[data-id="${taskId}"]`);
  if (!row) return;

  const title   = _q(".task-text", row)?.textContent.trim() || "Task";
  const dueInput = _q(".col-due input.cell-date", row);
  const dueDate = dueInput?.value || "";

  _openGCalUrl(title, dueDate, "", "");
}

function addSheetTaskToGCal() {
  const title   = _id("sheet-name")?.value.trim() || "Task";
  const dueDate = _id("sheet-due")?.value || "";
  const dueTime = _id("sheet-due-time")?.value || "";
  const notes   = _id("sheet-notes")?.value || "";

  _openGCalUrl(title, dueDate, dueTime, notes);
}

function _openGCalUrl(title, dueDate, dueTime, notes) {
  if (!dueDate) {
    showToast("Set a due date first", "error");
    return;
  }

  const dateClean = dueDate.replace(/-/g, "");
  let startStr, endStr;

  if (dueTime) {
    const timeClean = dueTime.replace(/:/g, "") + "00";
    startStr = `${dateClean}T${timeClean}`;
    // Default 1-hour event
    const startDt = new Date(`${dueDate}T${dueTime}`);
    const endDt   = new Date(startDt.getTime() + 3600000);
    const pad2 = n => String(n).padStart(2, "0");
    endStr = `${endDt.getFullYear()}${pad2(endDt.getMonth()+1)}${pad2(endDt.getDate())}` +
             `T${pad2(endDt.getHours())}${pad2(endDt.getMinutes())}00`;
  } else {
    // All-day event
    startStr = dateClean;
    const next = new Date(`${dueDate}T00:00:00`);
    next.setDate(next.getDate() + 1);
    const pad2 = n => String(n).padStart(2, "0");
    endStr = `${next.getFullYear()}${pad2(next.getMonth()+1)}${pad2(next.getDate())}`;
  }

  const url = `https://calendar.google.com/calendar/r/eventedit?` +
    `text=${encodeURIComponent(title)}` +
    `&dates=${startStr}/${endStr}` +
    (notes ? `&details=${encodeURIComponent(notes)}` : "");

  window.open(url, "_blank");
}

/* ---------------------------------------------------------
   Browser Notification Reminders
   --------------------------------------------------------- */
function scheduleReminder(taskId, title, dueDate, dueTime, reminderMinutes) {
  if (!dueDate || !dueTime) return;

  // Clear existing reminder for this task
  if (_reminders[taskId]) {
    clearTimeout(_reminders[taskId]);
    delete _reminders[taskId];
  }

  const dueMs = new Date(`${dueDate}T${dueTime}`).getTime();
  const reminderMs = dueMs - (reminderMinutes * 60 * 1000);
  const now = Date.now();

  if (reminderMs <= now) return; // already passed

  // Request permission
  if (Notification.permission === "default") {
    Notification.requestPermission();
  }

  _reminders[taskId] = setTimeout(() => {
    if (Notification.permission === "granted") {
      new Notification("Task Reminder", {
        body: title,
        icon: "/static/favicon.png",
      });
    }
    delete _reminders[taskId];
  }, reminderMs - now);
}

function schedulePageReminders() {
  if (!("Notification" in window)) return;

  _qa(".task-row").forEach(row => {
    const id = row.dataset.id;
    const dueInput = _q(".col-due input.cell-date", row);
    const dueDate = dueInput?.value || "";
    if (dueDate !== TODAY) return;

    const title = _q(".task-text", row)?.textContent.trim() || "";
    // Default: remind 15 min before noon if no due time
    scheduleReminder(id, title, dueDate, "12:00", 15);
  });
}

/* ---------------------------------------------------------
   Subtasks
   --------------------------------------------------------- */
async function loadSubtasks(taskId) {
  const list = _id("subtask-list");
  if (!list) return;
  list.innerHTML = "";

  try {
    // Fetch subtasks -- they may be embedded in task data or need separate call
    // The GET endpoint returns the task row; subtasks need a separate fetch
    const res = await fetch(`/api/v2/project-tasks/${taskId}`);
    if (!res.ok) return;
    const task = await res.json();

    // If subtasks are embedded in the task response
    const subtasks = task.subtasks || [];
    subtasks.forEach(st => _renderSubtask(list, st));
  } catch (e) {
    // Subtasks may not be available -- show empty list
    console.debug("No subtasks loaded", e);
  }
}

function _renderSubtask(container, st) {
  const item = document.createElement("label");
  item.className = "subtask-item";
  item.innerHTML = `
    <input type="checkbox" ${st.is_done ? "checked" : ""}
           onchange="toggleSubtask('${st.id}', this.checked)">
    <span class="${st.is_done ? "st-done" : ""}">${_escHtml(st.title)}</span>
  `;
  container.appendChild(item);
}

async function addSubtask() {
  const input = _id("subtask-input");
  const title = (input?.value || "").trim();
  if (!title || !_sheetTaskId) return;

  try {
    await _post("/subtask/add", {
      project_id: PROJECT_ID,
      task_id: _sheetTaskId,
      title,
    });

    // Append optimistically
    const list = _id("subtask-list");
    if (list) {
      _renderSubtask(list, { id: "temp-" + Date.now(), title, is_done: false });
    }
    input.value = "";
  } catch {
    showToast("Failed to add subtask", "error");
  }
}

function toggleSubtask(id, isDone) {
  _post("/subtask/toggle", { id, is_done: isDone }).catch(console.error);
}

/* ---------------------------------------------------------
   Recurrence Change
   --------------------------------------------------------- */
function onRecurrenceChange() {
  const sel = _id("sheet-recurrence");
  const daysEl = _id("recurrence-days");
  if (!sel || !daysEl) return;

  daysEl.classList.toggle("hidden", sel.value !== "weekly");

  // Bind day chip toggles
  _qa(".day-chip", daysEl).forEach(chip => {
    chip.onclick = () => chip.classList.toggle("active");
  });
}

/* ---------------------------------------------------------
   Pin Task (from sheet)
   --------------------------------------------------------- */
function pinTask() {
  if (!_sheetTaskId) return;

  const row = document.querySelector(`.task-row[data-id="${_sheetTaskId}"]`);
  const isPinned = row?.dataset.pinned === "1";

  _post("/projects/tasks/pin", { task_id: _sheetTaskId, is_pinned: !isPinned })
    .then(r => {
      if (!r.ok) throw new Error();
      if (row) row.dataset.pinned = isPinned ? "0" : "1";
      showToast(isPinned ? "Unpinned" : "Pinned", "success");
    })
    .catch(() => showToast("Failed to update pin", "error"));
}

/* ---------------------------------------------------------
   Eliminate Task (from sheet)
   --------------------------------------------------------- */
function eliminateTask() {
  if (!_sheetTaskId) return;
  if (!confirm("Delete this task? This cannot be undone.")) return;

  _post("/projects/tasks/eliminate", { id: _sheetTaskId })
    .then(r => {
      if (!r.ok) throw new Error();
      closeTaskSheet();
      showToast("Task deleted", "success");
      location.reload();
    })
    .catch(() => showToast("Failed to delete task", "error"));
}

/* ---------------------------------------------------------
   Click-outside to close sheet
   --------------------------------------------------------- */
function onSheetOverlayClick(e) {
  if (e.target.id === "task-sheet") {
    closeTaskSheet();
  }
}

/* ---------------------------------------------------------
   DOMContentLoaded
   --------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  initPrioPicker();
  initAddTask();
  initFilters();
  initSort();
  updateProjectStats();
  schedulePageReminders();

  // Close sheet on overlay click
  const sheet = _id("task-sheet");
  if (sheet) sheet.addEventListener("click", onSheetOverlayClick);

  feather.replace();
});

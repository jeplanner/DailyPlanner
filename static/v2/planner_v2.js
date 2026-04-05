"use strict";

/* ═══════════════════════════════════════════════════════════════════
   PLANNER V2 — Google Calendar-style Day / 3-Day / Week planner
   ═══════════════════════════════════════════════════════════════════ */

/* ──────────────────────────
   CONSTANTS
   ────────────────────────── */
const HOUR_HEIGHT = 60;   // px per hour
const SNAP = 5;           // 5-minute snap grid
const TOTAL_HOURS = 24;
const GRID_HEIGHT = HOUR_HEIGHT * TOTAL_HOURS;

/* ──────────────────────────
   STATE
   ────────────────────────── */
let currentDate = getISTDate();          // YYYY-MM-DD anchor
let currentView = "day";                 // "day" | "3day" | "week"
let eventsMap = new Map();               // date-string -> array of events
let floatingTasks = [];
let selected = null;                     // event being edited
let popoverEvent = null;                 // event shown in popover
let draggedTask = null;
let snapLine = null;

// Drag-to-create state
let creatingEvent = false;
let pendingCreate = false;
let createStartY = 0;
let createStartX = 0;
let createColDate = null;
let ghostEvent = null;

// Mini-cal state
let miniCalMonth = null;   // Date object for displayed month
let miniCalYear = null;

// Current-time timer
let timeLineInterval = null;

/* ══════════════════════════════════════════════════════════════
   1. TIME / DATE HELPERS
   ══════════════════════════════════════════════════════════════ */

function getISTNow() {
  return new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
  );
}

function getISTDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

function formatTime(t) {
  if (!t) return "";
  return t.slice(0, 5);
}

function minutes(t) {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function toTime(mins) {
  mins = Math.max(0, Math.min(1439, mins));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function calculateEndTime(start, duration) {
  return toTime(minutes(start) + parseInt(duration));
}

function normalizeDuration(mins) {
  const allowed = [15, 30, 45, 60, 90, 120];
  for (const d of allowed) {
    if (mins <= d) return d;
  }
  return 120;
}

function formatHour(hour) {
  if (hour === 0) return "12 AM";
  if (hour < 12) return `${hour} AM`;
  if (hour === 12) return "12 PM";
  return `${hour - 12} PM`;
}

function formatTimeRange(start, end) {
  return `${formatTime12(start)} - ${formatTime12(end)}`;
}

function formatTime12(t) {
  if (!t) return "";
  const [h, m] = t.split(":").map(Number);
  const ampm = h < 12 ? "AM" : "PM";
  const h12 = h % 12 || 12;
  return m === 0 ? `${h12} ${ampm}` : `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
}

/** Parse "YYYY-MM-DD" into a local Date (no timezone shift). */
function parseLocalDate(str) {
  const [y, m, d] = str.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Format a Date to "YYYY-MM-DD". */
function dateToStr(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Add days to a YYYY-MM-DD string, return new YYYY-MM-DD. */
function addDays(dateStr, n) {
  const d = parseLocalDate(dateStr);
  d.setDate(d.getDate() + n);
  return dateToStr(d);
}

/** Get Monday of the week containing dateStr. */
function getMonday(dateStr) {
  const d = parseLocalDate(dateStr);
  const day = d.getDay(); // 0=Sun
  const diff = (day === 0 ? -6 : 1 - day);
  d.setDate(d.getDate() + diff);
  return dateToStr(d);
}

/* ══════════════════════════════════════════════════════════════
   2. VISIBLE DATES CALCULATION
   ══════════════════════════════════════════════════════════════ */

function getVisibleDates() {
  if (currentView === "day") {
    return [currentDate];
  }
  if (currentView === "3day") {
    return [currentDate, addDays(currentDate, 1), addDays(currentDate, 2)];
  }
  // week: Mon-Sun
  const monday = getMonday(currentDate);
  const dates = [];
  for (let i = 0; i < 7; i++) {
    dates.push(addDays(monday, i));
  }
  return dates;
}

/* ══════════════════════════════════════════════════════════════
   3. VIEW SWITCHING / NAVIGATION
   ══════════════════════════════════════════════════════════════ */

function setView(view) {
  currentView = view;

  // Update button active state
  document.querySelectorAll(".view-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });

  // Set body data attribute for CSS
  document.body.dataset.view = view;

  buildGrid();
  loadAllEvents();
}

function changeDate(delta) {
  if (currentView === "day") {
    currentDate = addDays(currentDate, delta);
  } else if (currentView === "3day") {
    currentDate = addDays(currentDate, delta * 3);
  } else {
    currentDate = addDays(currentDate, delta * 7);
  }
  buildGrid();
  loadAllEvents();
}

function goToday() {
  currentDate = getISTDate();
  buildGrid();
  loadAllEvents();
  setTimeout(scrollToNow, 300);
}

/* ══════════════════════════════════════════════════════════════
   4. HEADER TITLE
   ══════════════════════════════════════════════════════════════ */

function updateHeaderTitle() {
  const el = document.getElementById("header-title");
  if (!el) return;

  const d = parseLocalDate(currentDate);
  const months = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"];
  const monthsShort = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"];

  if (currentView === "day") {
    el.textContent = `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
  } else if (currentView === "3day") {
    const end = parseLocalDate(addDays(currentDate, 2));
    if (d.getMonth() === end.getMonth()) {
      el.textContent = `${monthsShort[d.getMonth()]} ${d.getDate()} - ${end.getDate()}, ${d.getFullYear()}`;
    } else {
      el.textContent = `${monthsShort[d.getMonth()]} ${d.getDate()} - ${monthsShort[end.getMonth()]} ${end.getDate()}, ${d.getFullYear()}`;
    }
  } else {
    el.textContent = `${monthsShort[d.getMonth()]} ${d.getFullYear()}`;
  }
}

/* ══════════════════════════════════════════════════════════════
   5. GRID BUILDING (columns, headers, time gutter)
   ══════════════════════════════════════════════════════════════ */

function buildGrid() {
  const dates = getVisibleDates();
  const today = getISTDate();

  updateHeaderTitle();
  buildDayHeaders(dates, today);
  buildTimeGutter();
  buildColumns(dates, today);
  renderMiniCal();
}

function buildDayHeaders(dates, today) {
  const container = document.getElementById("day-headers");
  if (!container) return;

  const dayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

  container.innerHTML = dates.map(ds => {
    const d = parseLocalDate(ds);
    const isToday = ds === today;
    return `<div class="gcal-day-header ${isToday ? "today" : ""}" data-date="${ds}">
      <span class="day-name">${dayNames[d.getDay()]}</span>
      <span class="day-number ${isToday ? "today-number" : ""}">${d.getDate()}</span>
    </div>`;
  }).join("");
}

function buildTimeGutter() {
  const gutter = document.getElementById("time-gutter");
  if (!gutter) return;

  gutter.innerHTML = "";
  gutter.style.height = GRID_HEIGHT + "px";

  for (let hour = 0; hour < TOTAL_HOURS; hour++) {
    const label = document.createElement("div");
    label.className = "hour-label";
    label.style.top = (hour * HOUR_HEIGHT) + "px";
    label.textContent = hour === 0 ? "" : formatHour(hour);
    gutter.appendChild(label);
  }
}

function buildColumns(dates, today) {
  const container = document.getElementById("gcal-columns");
  if (!container) return;

  container.innerHTML = "";

  dates.forEach(ds => {
    const col = document.createElement("div");
    col.className = "gcal-day-col";
    col.dataset.date = ds;
    if (ds === today) col.classList.add("today");

    col.style.height = GRID_HEIGHT + "px";

    // Hour lines
    for (let hour = 0; hour < TOTAL_HOURS; hour++) {
      const line = document.createElement("div");
      line.className = "hour-line";
      line.style.top = (hour * HOUR_HEIGHT) + "px";
      col.appendChild(line);
    }

    // Drag-and-drop listeners (desktop)
    col.addEventListener("dragover", onColumnDragOver);
    col.addEventListener("dragleave", onColumnDragLeave);
    col.addEventListener("drop", onColumnDrop);

    // Drag-to-create (pointer)
    col.addEventListener("pointerdown", onColumnPointerDown);

    container.appendChild(col);
  });

  // Render the current-time line
  renderCurrentTimeLine();
}

/* ══════════════════════════════════════════════════════════════
   6. DATA LOADING
   ══════════════════════════════════════════════════════════════ */

async function loadAllEvents() {
  const dates = getVisibleDates();
  eventsMap.clear();

  // Fetch all dates in parallel — each date fetches independently
  const fetches = dates.map(async (ds) => {
    let eventData = [];
    let taskData = [];

    try {
      const evRes = await fetch(`/api/v2/events?date=${ds}`);
      if (evRes.ok) eventData = await evRes.json();
    } catch (e) { console.warn("Events fetch failed for", ds, e); }

    try {
      const taskRes = await fetch(`/api/v2/project-tasks?date=${ds}`);
      if (taskRes.ok) {
        const raw = await taskRes.json();
        taskData = Array.isArray(raw) ? raw : [];
      }
    } catch (e) { console.warn("Tasks fetch failed for", ds, e); }

    const timedTasks = taskData.filter(t => t.start_time);

    const combined = [
      ...eventData.map(e => ({ ...e, type: "event" })),
      ...timedTasks.map(t => ({
        ...t,
        task_id: t.task_id,
        title: t.task_text,
        end_time: calculateEndTime(t.start_time, 30),
        type: "project",
        priority: t.priority || "medium"
      }))
    ];

    eventsMap.set(ds, combined);

    if (ds === currentDate) {
      floatingTasks = taskData;
    }
  });

  await Promise.all(fetches);
  renderAllColumns();
  renderFloatingTasks(floatingTasks);
  renderMiniCal();
}

/* ══════════════════════════════════════════════════════════════
   7. EVENT RENDERING
   ══════════════════════════════════════════════════════════════ */

function renderAllColumns() {
  const dates = getVisibleDates();

  dates.forEach(ds => {
    const col = document.querySelector(`.gcal-day-col[data-date="${ds}"]`);
    if (!col) return;

    // Remove old event chips
    col.querySelectorAll(".event-chip").forEach(c => c.remove());

    const dayEvents = eventsMap.get(ds) || [];
    if (!dayEvents.length) return;

    const positioned = computeLayout(dayEvents);

    positioned.forEach(ev => {
      const chip = document.createElement("div");
      chip.className = "event-chip";
      chip.dataset.id = ev.id || ev.task_id;
      chip.dataset.type = ev.type;

      // Priority class
      if (ev.type === "project") {
        chip.classList.add("p-project");
      } else {
        chip.classList.add(`p-${ev.priority || "medium"}`);
      }

      // Position
      chip.style.top = ev.top + "px";
      chip.style.height = Math.max(ev.height, 18) + "px";
      chip.style.left = `calc(${ev.left}% + 2px)`;
      chip.style.width = `calc(${ev.width}% - 4px)`;

      // Content
      const timeStr = formatTime(ev.start_time);
      const title = ev.task_text || ev.title || "";
      const isSmall = ev.height < 36;
      const qBadge = ev.quadrant ? `<span class="chip-quadrant cq-${ev.quadrant}">${ev.quadrant}</span>` : "";

      if (isSmall) {
        chip.innerHTML = `<span class="chip-title">${qBadge} ${timeStr} ${title}</span>`;
      } else {
        chip.innerHTML = `
          <div class="chip-time">${timeStr} ${qBadge}</div>
          <div class="chip-title">${title}</div>
        `;
      }

      // Click -> popover
      chip.addEventListener("click", (e) => {
        e.stopPropagation();
        showPopover(ev, chip, ds);
      });

      // Drag to move (desktop)
      chip.draggable = true;
      chip.addEventListener("dragstart", (e) => {
        draggedTask = { ...ev, _sourceDate: ds };
        e.dataTransfer.effectAllowed = "move";
        // Make chip semi-transparent during drag
        setTimeout(() => chip.style.opacity = "0.4", 0);
      });
      chip.addEventListener("dragend", () => {
        chip.style.opacity = "";
      });

      // Touch drag for mobile
      attachChipTouchDrag(chip, ev, ds);

      col.appendChild(chip);
    });
  });

  // Re-render current time line
  renderCurrentTimeLine();
}

/* ──────────────────────────
   Layout Engine (overlap columns)
   ────────────────────────── */
function computeLayout(events) {
  if (!events.length) return [];

  const enriched = events
    .filter(ev => ev.start_time)
    .map(ev => {
      const start = minutes(ev.start_time);
      const end = minutes(ev.end_time);
      return {
        ...ev,
        _start: start,
        _end: end,
        top: (start / 60) * HOUR_HEIGHT,
        height: ((end - start) / 60) * HOUR_HEIGHT
      };
    });

  enriched.sort((a, b) => a._start - b._start || a._end - b._end);

  // Build overlap clusters
  // Adjacent events (end === start) are NOT overlapping — use strict < / >
  const clusters = [];
  enriched.forEach(ev => {
    let placed = false;
    for (const cluster of clusters) {
      if (cluster.some(e => ev._start < e._end && ev._end > e._start)) {
        cluster.push(ev);
        placed = true;
        break;
      }
    }
    if (!placed) clusters.push([ev]);
  });

  // Assign columns within each cluster
  clusters.forEach(cluster => {
    const columns = [];
    cluster.forEach(ev => {
      let placed = false;
      for (let i = 0; i < columns.length; i++) {
        const last = columns[i][columns[i].length - 1];
        if (ev._start >= last._end) { // adjacent (start === end) fits in same column
          columns[i].push(ev);
          ev._col = i;
          placed = true;
          break;
        }
      }
      if (!placed) {
        columns.push([ev]);
        ev._col = columns.length - 1;
      }
    });

    const totalCols = columns.length;
    cluster.forEach(ev => {
      if (totalCols === 1) {
        ev.width = 100;
        ev.left = 0;
      } else {
        ev.width = 100 / totalCols;
        ev.left = ev._col * ev.width;
      }
    });
  });

  return enriched;
}

/* ══════════════════════════════════════════════════════════════
   8. CURRENT TIME LINE
   ══════════════════════════════════════════════════════════════ */

function renderCurrentTimeLine() {
  // Remove existing
  document.querySelectorAll(".current-time-line").forEach(el => el.remove());

  const today = getISTDate();
  const col = document.querySelector(`.gcal-day-col[data-date="${today}"]`);
  if (!col) return;

  const now = getISTNow();
  const minutesNow = now.getHours() * 60 + now.getMinutes();
  const top = (minutesNow / 60) * HOUR_HEIGHT;

  const line = document.createElement("div");
  line.className = "current-time-line";
  line.style.top = top + "px";

  // Red dot
  const dot = document.createElement("div");
  dot.className = "current-time-dot";
  line.appendChild(dot);

  col.appendChild(line);
}

function startTimeLineUpdater() {
  if (timeLineInterval) clearInterval(timeLineInterval);
  timeLineInterval = setInterval(renderCurrentTimeLine, 60000);
}

/* ══════════════════════════════════════════════════════════════
   9. AUTO-SCROLL
   ══════════════════════════════════════════════════════════════ */

function scrollToNow() {
  const scroll = document.getElementById("gcal-scroll");
  if (!scroll) return;
  const now = getISTNow();
  const top = (now.getHours() * 60 + now.getMinutes()) / 60 * HOUR_HEIGHT;
  scroll.scrollTo({ top: Math.max(0, top - 200), behavior: "smooth" });
}

function scrollTo7AM() {
  const scroll = document.getElementById("gcal-scroll");
  if (!scroll) return;
  scroll.scrollTop = 7 * HOUR_HEIGHT - 20;
}

/* ══════════════════════════════════════════════════════════════
   10. MINI CALENDAR
   ══════════════════════════════════════════════════════════════ */

function renderMiniCal() {
  const container = document.getElementById("mini-cal");
  if (!container) return;

  const anchor = parseLocalDate(currentDate);
  if (miniCalMonth === null) {
    miniCalMonth = anchor.getMonth();
    miniCalYear = anchor.getFullYear();
  }

  const today = getISTDate();
  const dayNames = ["Mo","Tu","We","Th","Fr","Sa","Su"];

  // First day of month
  const first = new Date(miniCalYear, miniCalMonth, 1);
  let startDay = first.getDay(); // 0=Sun
  startDay = startDay === 0 ? 6 : startDay - 1; // Convert to Mon=0

  const daysInMonth = new Date(miniCalYear, miniCalMonth + 1, 0).getDate();

  const monthNames = ["January","February","March","April","May","June",
                      "July","August","September","October","November","December"];

  let html = `<div class="mini-cal-header">
    <button class="mini-cal-nav" onclick="miniCalNav(-1)"><i data-feather="chevron-left"></i></button>
    <span class="mini-cal-title">${monthNames[miniCalMonth]} ${miniCalYear}</span>
    <button class="mini-cal-nav" onclick="miniCalNav(1)"><i data-feather="chevron-right"></i></button>
  </div>`;

  html += `<div class="mini-cal-grid">`;
  dayNames.forEach(dn => {
    html += `<div class="mini-cal-dayname">${dn}</div>`;
  });

  // Empty cells before first day
  for (let i = 0; i < startDay; i++) {
    html += `<div class="mini-cal-day empty"></div>`;
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${miniCalYear}-${String(miniCalMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const isToday = ds === today;
    const isSelected = ds === currentDate;
    const classes = ["mini-cal-day"];
    if (isToday) classes.push("today");
    if (isSelected) classes.push("selected");

    html += `<div class="${classes.join(" ")}" onclick="miniCalSelect('${ds}')">${d}</div>`;
  }

  html += `</div>`;

  container.innerHTML = html;

  if (window.feather) feather.replace();
}

function miniCalNav(delta) {
  miniCalMonth += delta;
  if (miniCalMonth < 0) { miniCalMonth = 11; miniCalYear--; }
  if (miniCalMonth > 11) { miniCalMonth = 0; miniCalYear++; }
  renderMiniCal();
}

function miniCalSelect(dateStr) {
  currentDate = dateStr;
  const d = parseLocalDate(dateStr);
  miniCalMonth = d.getMonth();
  miniCalYear = d.getFullYear();
  buildGrid();
  loadAllEvents();
}

/* ══════════════════════════════════════════════════════════════
   11. EVENT POPOVER
   ══════════════════════════════════════════════════════════════ */

function showPopover(ev, chipEl, dateStr) {
  closePopover();
  popoverEvent = { ...ev, _date: dateStr };

  const popover = document.getElementById("event-popover");
  if (!popover) return;

  // Fill content
  const dot = document.getElementById("popover-dot");
  const pClass = ev.type === "project" ? "project" : (ev.priority || "medium");
  dot.className = `popover-color-dot p-${pClass}`;

  document.getElementById("popover-title").textContent = ev.task_text || ev.title || "";
  document.getElementById("popover-time").textContent = formatTimeRange(ev.start_time, ev.end_time);
  document.getElementById("popover-desc").textContent = ev.description || ev.notes || "";

  // On mobile, let CSS render the popover as a bottom-sheet (see planner_v2.css @media).
  // Clear any inline positioning from a previous desktop-view invocation.
  const isMobile = window.matchMedia("(max-width: 768px)").matches;
  if (isMobile) {
    popover.style.top = "";
    popover.style.left = "";
    popover.classList.remove("hidden");
  } else {
    // Position near chip (desktop)
    const rect = chipEl.getBoundingClientRect();
    popover.style.top = (rect.top + window.scrollY) + "px";
    popover.style.left = (rect.right + 8) + "px";
    popover.classList.remove("hidden");

    // Adjust if offscreen right
    requestAnimationFrame(() => {
      const pr = popover.getBoundingClientRect();
      if (pr.right > window.innerWidth - 10) {
        popover.style.left = (rect.left - pr.width - 8) + "px";
      }
      if (pr.bottom > window.innerHeight - 10) {
        popover.style.top = (window.innerHeight - pr.height - 10 + window.scrollY) + "px";
      }
    });
  }

  if (window.feather) feather.replace();
}

function closePopover() {
  const popover = document.getElementById("event-popover");
  if (popover) popover.classList.add("hidden");
  popoverEvent = null;
}

function editFromPopover() {
  if (!popoverEvent) return;
  const ev = popoverEvent;
  closePopover();
  if (ev.type === "project") {
    openTaskCard(ev.task_id);
  } else {
    openModal(ev);
  }
}

function deleteFromPopover() {
  if (!popoverEvent) return;
  const ev = popoverEvent;
  closePopover();

  if (ev.type === "project") {
    // Cannot delete project tasks from here; open task card instead
    openTaskCard(ev.task_id);
    return;
  }

  deleteEventById(ev.id);
}

/* ══════════════════════════════════════════════════════════════
   12. EVENT MODAL (create / edit)
   ══════════════════════════════════════════════════════════════ */

function openCreateModal(prefillDate, prefillStart, prefillEnd) {
  hideConflict();
  selected = null;

  document.getElementById("modal-title").textContent = "New Event";
  document.getElementById("start-time").value = prefillStart || "";
  document.getElementById("end-time").value = prefillEnd || (prefillStart ? toTime(minutes(prefillStart) + 30) : "");
  document.getElementById("event-priority").value = "medium";
  document.getElementById("event-title").value = "";
  document.getElementById("event-desc").value = "";

  // Reset reminder
  const select = document.getElementById("reminder-select");
  const custom = document.getElementById("custom-reminder");
  select.value = "10";
  custom.value = "";
  custom.style.display = "none";

  // Reset quadrant
  document.querySelectorAll(".quad-btn").forEach(b => b.classList.remove("active"));
  document.querySelector('.quad-btn[data-q=""]')?.classList.add("active");

  // Hide delete button for new events
  const delBtn = document.getElementById("delete-btn");
  if (delBtn) delBtn.style.display = "none";

  document.getElementById("modal").classList.remove("hidden");
  updateDurationLabel();

  setTimeout(() => {
    const focus = prefillStart ? document.getElementById("event-title") : document.getElementById("start-time");
    focus?.focus();
  }, 50);
}

function openModal(ev) {
  hideConflict();
  selected = ev;

  document.getElementById("modal-title").textContent = "Edit Event";
  document.getElementById("start-time").value = formatTime(ev.start_time) || "";
  document.getElementById("end-time").value = formatTime(ev.end_time) || "";
  document.getElementById("event-priority").value = ev.priority || "medium";
  document.getElementById("event-title").value = ev.task_text || ev.title || "";
  document.getElementById("event-desc").value = ev.description || "";

  // Reminder
  const select = document.getElementById("reminder-select");
  const custom = document.getElementById("custom-reminder");
  select.value = "10";
  custom.value = "";
  custom.style.display = "none";

  if (ev.reminder_minutes !== undefined && ev.reminder_minutes !== null) {
    const reminder = parseInt(ev.reminder_minutes);
    if ([0, 5, 10, 15, 30, 60].includes(reminder)) {
      select.value = String(reminder);
    } else {
      select.value = "custom";
      custom.value = reminder;
      custom.style.display = "block";
    }
  }

  // Set quadrant
  document.querySelectorAll(".quad-btn").forEach(b => b.classList.remove("active"));
  const qVal = ev.quadrant || "";
  const qBtn = document.querySelector(`.quad-btn[data-q="${qVal}"]`);
  if (qBtn) qBtn.classList.add("active");

  // Show delete button for existing events
  const delBtn = document.getElementById("delete-btn");
  if (delBtn) delBtn.style.display = "";

  document.getElementById("modal").classList.remove("hidden");
  updateDurationLabel();

  if (window.feather) feather.replace();
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
  selected = null;
}

function updateEndFromStart() {
  // When start changes, move end to keep same duration
  const start = document.getElementById("start-time").value;
  const end = document.getElementById("end-time").value;
  if (!start) return;

  const startMin = minutes(start);
  const endMin = end ? minutes(end) : startMin + 30;
  let dur = endMin - startMin;
  if (dur <= 0) dur = 30; // If end is before start, default 30min

  document.getElementById("end-time").value = toTime(startMin + dur);
  updateDurationLabel();
}

function updateDurationFromEnd() {
  // When end changes, update duration label
  updateDurationLabel();
}

function updateDurationLabel() {
  const start = document.getElementById("start-time").value;
  const end = document.getElementById("end-time").value;
  const label = document.getElementById("duration-label");
  if (!start || !end || !label) return;

  const dur = minutes(end) - minutes(start);
  if (dur <= 0) { label.textContent = "Invalid"; return; }

  // Format nicely
  if (dur < 60) {
    label.textContent = dur + " min";
  } else {
    const h = Math.floor(dur / 60);
    const m = dur % 60;
    label.textContent = m ? `${h}h ${m}m` : `${h} hour${h > 1 ? "s" : ""}`;
  }

  // Update hidden duration select for backward compat
  document.getElementById("duration").value = dur;

  // Highlight matching preset button
  document.querySelectorAll(".dur-btn").forEach(btn => {
    const val = parseInt(btn.getAttribute("onclick").match(/\d+/)?.[0] || 0);
    btn.classList.toggle("active", val === dur);
  });
}

function setDuration(mins) {
  const start = document.getElementById("start-time").value;
  if (!start) {
    showToast("Set a start time first", "error");
    return;
  }
  document.getElementById("end-time").value = toTime(minutes(start) + mins);
  updateDurationLabel();
}

// Legacy compat
function updateEndPreview() { updateDurationLabel(); }

function pickQuadrant(btn) {
  document.querySelectorAll(".quad-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

function getSelectedQuadrant() {
  const active = document.querySelector(".quad-btn.active");
  return active ? active.dataset.q || null : null;
}

function handleReminderSelect() {
  const select = document.getElementById("reminder-select");
  const custom = document.getElementById("custom-reminder");
  custom.style.display = select.value === "custom" ? "block" : "none";
}

function getReminderMinutes() {
  const select = document.getElementById("reminder-select");
  const custom = document.getElementById("custom-reminder");
  if (select.value === "custom") {
    return parseInt(custom.value || 0);
  }
  return parseInt(select.value);
}

async function saveEvent() {
  const start = document.getElementById("start-time").value;
  const end = document.getElementById("end-time").value;

  if (!start) {
    showToast("Please enter a start time", "error");
    return;
  }
  if (!end || minutes(end) <= minutes(start)) {
    showToast("End time must be after start time", "error");
    return;
  }

  const payload = {
    plan_date: (selected && (selected.plan_date || selected._date)) || currentDate,
    start_time: start,
    end_time: end,
    title: document.getElementById("event-title").value,
    description: document.getElementById("event-desc").value,
    priority: document.getElementById("event-priority").value,
    quadrant: getSelectedQuadrant(),
    reminder_minutes: getReminderMinutes()
  };

  let url, method;

  if (selected) {
    if (selected.type === "project") {
      url = `/api/v2/project-tasks/${selected.task_id}`;
      method = "PUT";
    } else {
      url = `/api/v2/events/${selected.id}`;
      method = "PUT";
    }
  } else {
    url = "/api/v2/events";
    method = "POST";
  }

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      let data = {};
      try { data = await res.json(); } catch {}

      if (data.conflict) {
        showConflictDialog(data.conflicting_events, payload);
        return;
      }

      showToast("Save failed", "error");
      return;
    }

    closeModal();
    showToast("Event saved", "success");
    loadAllEvents();

  } catch (err) {
    console.error("Save error:", err);
    showToast("Save failed", "error");
  }
}

async function deleteEvent() {
  if (!selected || !selected.id) return;
  await deleteEventById(selected.id);
  closeModal();
}

async function deleteEventById(id) {
  try {
    await fetch(`/api/v2/events/${id}`, { method: "DELETE" });
    showToast("Event deleted", "success");
    loadAllEvents();
  } catch (err) {
    showToast("Delete failed", "error");
  }
}

function hideConflict() {
  const section = document.getElementById("conflict-section");
  if (section) section.style.display = "none";
}

function showConflictDialog(conflicts, payload) {
  const list = document.getElementById("conflict-list");
  const section = document.getElementById("conflict-section");

  list.innerHTML = conflicts.map(c =>
    `<div style="margin:6px 0;">
       ${formatTime(c.start_time)} - ${formatTime(c.end_time)}: ${c.title}
     </div>`
  ).join("");

  section.style.display = "block";

  document.getElementById("accept-conflict").onclick = async () => {
    payload.force = true;

    await fetch("/api/v2/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    hideConflict();
    closeModal();
    showToast("Event saved (conflict accepted)", "success");
    loadAllEvents();
  };

  if (window.feather) feather.replace();
}

/* ══════════════════════════════════════════════════════════════
   13. PROJECT TASK MODAL
   ══════════════════════════════════════════════════════════════ */

async function openTaskCard(taskId) {
  selected = { task_id: taskId };

  try {
    const res = await fetch(`/api/v2/project-tasks/${taskId}`);
    if (!res.ok) throw new Error("Failed to load task");
    const task = await res.json();

    document.getElementById("task-title").value = task.task_text || "";
    document.getElementById("task-description").value = task.notes || "";
    document.getElementById("task-planned-hours").value = task.planned_hours || 0;
    document.getElementById("task-actual-hours").value = task.actual_hours || 0;
    document.getElementById("task-status").value = task.status || "open";
    document.getElementById("task-priority").value = task.priority || "medium";
    document.getElementById("task-duration").value = task.duration_days || 0;
    document.getElementById("task-due-date").value = task.due_date || "";
    document.getElementById("task-start-time").value = task.start_time || "";

    document.getElementById("task-card-modal").classList.add("show");
    document.getElementById("task-card-modal").classList.remove("hidden");
  } catch (err) {
    showToast("Failed to load task", "error");
  }
}

async function saveTaskCard() {
  const taskId = selected?.task_id;
  if (!taskId) return;

  const payload = {
    task_text: document.getElementById("task-title").value,
    notes: document.getElementById("task-description").value,
    status: document.getElementById("task-status").value,
    priority: document.getElementById("task-priority").value,
    planned_hours: parseFloat(document.getElementById("task-planned-hours").value) || 0,
    actual_hours: parseFloat(document.getElementById("task-actual-hours").value) || 0,
    duration_days: parseInt(document.getElementById("task-duration").value) || 0,
    due_date: document.getElementById("task-due-date").value,
    start_time: document.getElementById("task-start-time").value
  };

  try {
    const res = await fetch(`/api/v2/project-tasks/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Save failed");
    closeTaskCard();
    showToast("Task saved", "success");
    loadAllEvents();
  } catch (err) {
    showToast("Save failed", "error");
  }
}

function closeTaskCard() {
  const modal = document.getElementById("task-card-modal");
  modal.classList.remove("show");
  modal.classList.add("hidden");
  selected = null;
}

function adjustTaskNumber(btn, direction) {
  const wrapper = btn.closest(".number-control");
  const input = wrapper.querySelector("input");
  const step = parseFloat(input.step || 1);
  let value = parseFloat(input.value || 0);
  value += direction * step;
  if (value < 0) value = 0;
  if (value > 999) value = 999;
  input.value = parseFloat(value.toFixed(2));
}

/* ══════════════════════════════════════════════════════════════
   14. FLOATING TASKS (sidebar)
   ══════════════════════════════════════════════════════════════ */

function renderFloatingTasks(tasks) {
  const container = document.getElementById("floating-tasks");
  if (!container) return;
  container.innerHTML = "";

  // Only unscheduled tasks (no start_time)
  const unscheduled = (tasks || []).filter(t => !t.start_time);

  if (!unscheduled.length) {
    container.innerHTML = `<div class="empty-state">No unscheduled tasks</div>`;
    return;
  }

  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const todayStr = getISTDate();

  // Sort: priority high->low, then by due date
  unscheduled.sort((a, b) => {
    const pa = priorityOrder[a.priority || "medium"] ?? 1;
    const pb = priorityOrder[b.priority || "medium"] ?? 1;
    if (pa !== pb) return pa - pb;
    if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
    if (a.due_date) return -1;
    if (b.due_date) return 1;
    return 0;
  });

  unscheduled.forEach(task => {
    const div = document.createElement("div");
    div.className = "floating-task";
    div.draggable = true;

    const priority = task.priority || "medium";
    const projectName = task.projects?.name || "";
    const isOverdue = task.due_date && task.due_date < todayStr;

    if (isOverdue) div.classList.add("overdue-floating");

    div.innerHTML = `
      <div class="floating-title">${task.task_text || ""}</div>
      ${projectName ? `<div class="floating-project">${projectName}</div>` : ""}
      <div class="floating-meta">
        <span class="floating-priority p-${priority}">${priority.toUpperCase()}</span>
        ${task.due_date ? `<span class="floating-due">${task.due_date}</span>` : ""}
      </div>
    `;

    // Click -> open task card
    div.addEventListener("click", (e) => {
      e.stopPropagation();
      openTaskCard(task.task_id);
    });

    // Desktop drag
    div.addEventListener("dragstart", () => {
      draggedTask = { ...task, type: "project" };
    });

    // Touch drag for mobile
    attachFloatingTouchDrag(div, task);

    container.appendChild(div);
  });
}

/* ══════════════════════════════════════════════════════════════
   15. DRAG & DROP — Desktop (column handlers)
   ══════════════════════════════════════════════════════════════ */

function onColumnDragOver(e) {
  e.preventDefault();
  if (!draggedTask) return;

  const col = e.currentTarget;
  const rect = col.getBoundingClientRect();
  const y = e.clientY - rect.top + col.closest("#gcal-scroll").scrollTop;
  const minutesFromTop = (y / HOUR_HEIGHT) * 60;
  const snapped = Math.round(minutesFromTop / SNAP) * SNAP;
  const top = (snapped / 60) * HOUR_HEIGHT;

  // Show snap line
  let line = col.querySelector(".snap-line");
  if (!line) {
    line = document.createElement("div");
    line.className = "snap-line";
    col.appendChild(line);
  }
  line.style.top = top + "px";
}

function onColumnDragLeave(e) {
  const col = e.currentTarget;
  const line = col.querySelector(".snap-line");
  if (line) line.remove();
}

async function onColumnDrop(e) {
  e.preventDefault();
  if (!draggedTask) return;

  const col = e.currentTarget;
  const targetDate = col.dataset.date;

  // Clean snap line
  const line = col.querySelector(".snap-line");
  if (line) line.remove();

  const rect = col.getBoundingClientRect();
  const scrollTop = col.closest("#gcal-scroll").scrollTop;
  const y = e.clientY - rect.top + scrollTop;
  const minutesFromTop = (y / HOUR_HEIGHT) * 60;
  const snapped = Math.round(minutesFromTop / SNAP) * SNAP;

  const newStart = toTime(snapped);

  if (draggedTask.type === "project") {
    const end = calculateEndTime(newStart, 30);
    await fetch(`/api/v2/project-tasks/${draggedTask.task_id}/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_date: targetDate, start_time: newStart, end_time: end })
    });
  } else {
    const duration = (draggedTask._end || minutes(draggedTask.end_time)) - (draggedTask._start || minutes(draggedTask.start_time));
    const newEnd = toTime(snapped + duration);

    await fetch(`/api/v2/events/${draggedTask.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_date: targetDate,
        start_time: newStart,
        end_time: newEnd,
        title: draggedTask.title
      })
    });
  }

  draggedTask = null;
  showToast("Event moved", "success");
  loadAllEvents();
}

/* ══════════════════════════════════════════════════════════════
   16. DRAG-TO-CREATE (pointer events on columns)
   ══════════════════════════════════════════════════════════════ */

function onColumnPointerDown(e) {
  // Ignore if on an event chip or button
  if (e.target.closest(".event-chip")) return;
  if (e.target.closest("button")) return;

  const col = e.currentTarget;
  createColDate = col.dataset.date;
  pendingCreate = true;
  creatingEvent = false;
  createStartY = e.clientY;
  createStartX = e.clientX;

  document.addEventListener("pointermove", onCreatePointerMove);
  document.addEventListener("pointerup", onCreatePointerUp);
}

function onCreatePointerMove(e) {
  if (!pendingCreate && !creatingEvent) return;

  const dY = e.clientY - createStartY;
  const dX = Math.abs(e.clientX - createStartX);

  if (!creatingEvent) {
    // Cancel if horizontal movement dominates (scroll)
    if (dX > Math.abs(dY) && dX > 8) {
      cancelCreate();
      return;
    }

    const threshold = e.pointerType === "touch" ? 20 : 8;
    if (Math.abs(dY) < threshold) return;

    if (e.pointerType === "touch" && dX >= Math.abs(dY)) {
      cancelCreate();
      return;
    }

    // Commit to creating
    creatingEvent = true;
    pendingCreate = false;

    const col = document.querySelector(`.gcal-day-col[data-date="${createColDate}"]`);
    if (!col) return;

    const rect = col.getBoundingClientRect();
    const scrollTop = col.closest("#gcal-scroll").scrollTop;
    const y = createStartY - rect.top + scrollTop;
    const minutesFromTop = (y / HOUR_HEIGHT) * 60;
    const snapped = Math.round(minutesFromTop / SNAP) * SNAP;
    const top = (snapped / 60) * HOUR_HEIGHT;

    ghostEvent = document.createElement("div");
    ghostEvent.className = "event-chip ghost-event";
    ghostEvent.style.top = top + "px";
    ghostEvent.style.height = "5px";
    ghostEvent.style.left = "2px";
    ghostEvent.style.width = "calc(100% - 4px)";
    col.appendChild(ghostEvent);
  }

  if (!ghostEvent) return;

  const col = document.querySelector(`.gcal-day-col[data-date="${createColDate}"]`);
  if (!col) return;

  const rect = col.getBoundingClientRect();
  const scrollTop = col.closest("#gcal-scroll").scrollTop;
  const startY = createStartY - rect.top + scrollTop;
  const currentY = e.clientY - rect.top + scrollTop;
  const delta = currentY - startY;

  if (delta < 0) return;

  const mins = (delta / HOUR_HEIGHT) * 60;
  const snapped = Math.round(mins / SNAP) * SNAP;
  const height = (snapped / 60) * HOUR_HEIGHT;
  ghostEvent.style.height = Math.max(height, 5) + "px";
}

function onCreatePointerUp(e) {
  if (!pendingCreate && !creatingEvent) return;

  const wasCreating = creatingEvent;

  if (ghostEvent) { ghostEvent.remove(); ghostEvent = null; }
  pendingCreate = false;
  creatingEvent = false;

  document.removeEventListener("pointermove", onCreatePointerMove);
  document.removeEventListener("pointerup", onCreatePointerUp);

  if (!wasCreating) return;

  const col = document.querySelector(`.gcal-day-col[data-date="${createColDate}"]`);
  if (!col) return;

  const rect = col.getBoundingClientRect();
  const scrollTop = col.closest("#gcal-scroll").scrollTop;
  const startY = createStartY - rect.top + scrollTop;
  const endY = e.clientY - rect.top + scrollTop;

  const startMinutes = Math.round(((startY / HOUR_HEIGHT) * 60) / SNAP) * SNAP;
  const endMinutes = Math.round(((endY / HOUR_HEIGHT) * 60) / SNAP) * SNAP;

  if (endMinutes <= startMinutes) return;

  const startTime = toTime(startMinutes);
  const endTime = toTime(endMinutes);

  // Set currentDate to the column's date for new event creation
  currentDate = createColDate;

  openCreateModal(createColDate, startTime, endTime);
}

function cancelCreate() {
  if (ghostEvent) { ghostEvent.remove(); ghostEvent = null; }
  pendingCreate = false;
  creatingEvent = false;
  document.removeEventListener("pointermove", onCreatePointerMove);
  document.removeEventListener("pointerup", onCreatePointerUp);
}

/* ══════════════════════════════════════════════════════════════
   17. TOUCH DRAG — Event chips (mobile)
   ══════════════════════════════════════════════════════════════ */

function attachChipTouchDrag(chipEl, ev, dateStr) {
  let clone = null;
  let dragging = false;
  let startX, startY;
  const DRAG_THRESHOLD = 10;

  chipEl.addEventListener("touchstart", (e) => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    dragging = false;
  }, { passive: true });

  chipEl.addEventListener("touchmove", (e) => {
    const dx = Math.abs(e.touches[0].clientX - startX);
    const dy = Math.abs(e.touches[0].clientY - startY);

    if (!dragging && (dx > DRAG_THRESHOLD || dy > DRAG_THRESHOLD)) {
      dragging = true;
      draggedTask = { ...ev, _sourceDate: dateStr };

      clone = chipEl.cloneNode(true);
      clone.style.cssText = `
        position: fixed;
        opacity: 0.75;
        pointer-events: none;
        z-index: 9999;
        width: ${chipEl.offsetWidth}px;
        height: ${chipEl.offsetHeight}px;
        transform: scale(1.04);
        box-shadow: 0 8px 24px rgba(0,0,0,.3);
      `;
      document.body.appendChild(clone);
    }

    if (!dragging) return;
    e.preventDefault();
    e.stopPropagation();

    const x = e.touches[0].clientX;
    const y = e.touches[0].clientY;

    clone.style.left = (x - chipEl.offsetWidth / 2) + "px";
    clone.style.top = (y - chipEl.offsetHeight / 2) + "px";

    // Show snap line on the column under the touch point
    showTouchSnapLine(x, y);
  }, { passive: false });

  chipEl.addEventListener("touchend", async (e) => {
    if (clone) { clone.remove(); clone = null; }
    clearTouchSnapLines();

    if (!dragging || !draggedTask) {
      dragging = false;
      return;
    }

    const x = e.changedTouches[0].clientX;
    const y = e.changedTouches[0].clientY;

    await handleTouchDrop(x, y, ev);
    draggedTask = null;
    dragging = false;
  });
}

/* ══════════════════════════════════════════════════════════════
   18. TOUCH DRAG — Floating tasks (mobile)
   ══════════════════════════════════════════════════════════════ */

function attachFloatingTouchDrag(div, task) {
  let clone = null;
  let dragging = false;
  let startX, startY;

  div.addEventListener("touchstart", (e) => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    dragging = false;
  }, { passive: true });

  div.addEventListener("touchmove", (e) => {
    const dx = Math.abs(e.touches[0].clientX - startX);
    const dy = Math.abs(e.touches[0].clientY - startY);

    if (!dragging && (dx > 8 || dy > 8)) {
      dragging = true;
      draggedTask = { ...task, type: "project" };

      clone = div.cloneNode(true);
      clone.style.cssText = `
        position: fixed;
        opacity: 0.8;
        pointer-events: none;
        z-index: 9999;
        width: ${div.offsetWidth}px;
        transform: scale(1.05);
        box-shadow: 0 8px 24px rgba(0,0,0,.3);
      `;
      document.body.appendChild(clone);
    }

    if (!dragging) return;
    e.preventDefault();

    const x = e.touches[0].clientX;
    const y = e.touches[0].clientY;

    clone.style.left = (x - div.offsetWidth / 2) + "px";
    clone.style.top = (y - 30) + "px";

    showTouchSnapLine(x, y);
  }, { passive: false });

  div.addEventListener("touchend", async (e) => {
    if (clone) { clone.remove(); clone = null; }
    clearTouchSnapLines();

    if (!dragging || !draggedTask) {
      dragging = false;
      return;
    }

    const x = e.changedTouches[0].clientX;
    const y = e.changedTouches[0].clientY;

    // Find column under touch
    const col = getColumnUnderPoint(x, y);
    if (col) {
      const rect = col.getBoundingClientRect();
      const scrollTop = col.closest("#gcal-scroll").scrollTop;
      const relY = y - rect.top + scrollTop;
      const minutesFromTop = (relY / HOUR_HEIGHT) * 60;
      const snapped = Math.round(minutesFromTop / SNAP) * SNAP;
      const start = toTime(snapped);
      const end = calculateEndTime(start, 30);
      const targetDate = col.dataset.date;

      await fetch(`/api/v2/project-tasks/${draggedTask.task_id}/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_date: targetDate, start_time: start, end_time: end })
      });

      showToast("Task scheduled", "success");
      loadAllEvents();
    }

    draggedTask = null;
    dragging = false;
  });
}

/* ── Shared touch helpers ── */

function getColumnUnderPoint(x, y) {
  const cols = document.querySelectorAll(".gcal-day-col");
  for (const col of cols) {
    const rect = col.getBoundingClientRect();
    if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
      return col;
    }
  }
  return null;
}

function showTouchSnapLine(x, y) {
  clearTouchSnapLines();
  const col = getColumnUnderPoint(x, y);
  if (!col) return;

  const rect = col.getBoundingClientRect();
  const scrollTop = col.closest("#gcal-scroll").scrollTop;
  const relY = y - rect.top + scrollTop;
  const minutesFromTop = (relY / HOUR_HEIGHT) * 60;
  const snapped = Math.round(minutesFromTop / SNAP) * SNAP;
  const top = (snapped / 60) * HOUR_HEIGHT;

  const line = document.createElement("div");
  line.className = "snap-line";
  line.style.top = top + "px";
  col.appendChild(line);
}

function clearTouchSnapLines() {
  document.querySelectorAll(".snap-line").forEach(l => l.remove());
}

async function handleTouchDrop(x, y, ev) {
  const col = getColumnUnderPoint(x, y);
  if (!col) return;

  const targetDate = col.dataset.date;
  const rect = col.getBoundingClientRect();
  const scrollTop = col.closest("#gcal-scroll").scrollTop;
  const relY = y - rect.top + scrollTop;
  const minutesFromTop = (relY / HOUR_HEIGHT) * 60;
  const snapped = Math.round(minutesFromTop / SNAP) * SNAP;

  const duration = minutes(ev.end_time) - minutes(ev.start_time);
  const newStart = toTime(snapped);
  const newEnd = toTime(snapped + duration);

  if (ev.type === "project") {
    await fetch(`/api/v2/project-tasks/${ev.task_id}/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_date: targetDate, start_time: newStart, end_time: newEnd })
    });
  } else {
    await fetch(`/api/v2/events/${ev.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_date: targetDate,
        start_time: newStart,
        end_time: newEnd,
        title: ev.title
      })
    });
  }

  showToast("Event moved", "success");
  loadAllEvents();
}

/* ══════════════════════════════════════════════════════════════
   19. SMART PLANNER
   ══════════════════════════════════════════════════════════════ */

async function runSmartPlanner() {
  const input = document.getElementById("smart-input");
  const text = input.value.trim();
  if (!text) return;

  try {
    const res = await fetch("/api/v2/smart-create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: currentDate, text })
    });

    if (!res.ok) {
      showToast("Smart planner failed", "error");
      return;
    }

    input.value = "";
    showToast("Events created", "success");
    loadAllEvents();
  } catch (err) {
    showToast("Smart planner failed", "error");
  }
}

async function runAISmartPlanner() {
  const input = document.getElementById("smart-input");
  const text = input.value.trim();
  if (!text) return;

  showToast("AI is parsing your input…", "info");

  try {
    const res = await fetch("/api/v2/ai-parse-events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: currentDate, text })
    });

    if (!res.ok) {
      showToast("AI parsing failed", "error");
      return;
    }

    const data = await res.json();
    if (data.created_count > 0) {
      input.value = "";
      showToast(`Created ${data.created_count} event${data.created_count > 1 ? "s" : ""}`, "success");
      loadAllEvents();
    } else {
      showToast("AI couldn't parse any events. Try being more specific.", "error");
    }
  } catch {
    showToast("AI parsing failed", "error");
  }
}

/* ══════════════════════════════════════════════════════════════
   20. NUMBER CONTROL (scroll wheel on task fields)
   ══════════════════════════════════════════════════════════════ */

document.addEventListener("wheel", function (e) {
  const wrapper = e.target.closest(".number-control");
  if (!wrapper) return;

  e.preventDefault();
  const input = wrapper.querySelector("input");
  const step = parseFloat(input.step || 1);
  let value = parseFloat(input.value || 0);

  if (e.deltaY < 0) value += step;
  else value -= step;

  if (value < 0) value = 0;
  if (value > 999) value = 999;

  input.value = parseFloat(value.toFixed(2));
}, { passive: false });

/* ══════════════════════════════════════════════════════════════
   21. CLOSE POPOVER ON OUTSIDE CLICK
   ══════════════════════════════════════════════════════════════ */

document.addEventListener("click", (e) => {
  const popover = document.getElementById("event-popover");
  if (!popover || popover.classList.contains("hidden")) return;
  if (popover.contains(e.target)) return;
  if (e.target.closest(".event-chip")) return;
  closePopover();
});

/* ══════════════════════════════════════════════════════════════
   22. KEYBOARD SHORTCUTS
   ══════════════════════════════════════════════════════════════ */

document.addEventListener("keydown", (e) => {
  // Escape closes modals / popovers
  if (e.key === "Escape") {
    closePopover();
    if (!document.getElementById("modal").classList.contains("hidden")) {
      closeModal();
    }
    if (document.getElementById("task-card-modal").classList.contains("show")) {
      closeTaskCard();
    }
  }

  // T = go to today
  if (e.key === "t" && !e.ctrlKey && !e.metaKey && !isInputFocused()) {
    goToday();
  }

  // D / 3 / W = switch view
  if (!isInputFocused()) {
    if (e.key === "d") setView("day");
    if (e.key === "3") setView("3day");
    if (e.key === "w") setView("week");
  }
});

function isInputFocused() {
  const tag = document.activeElement?.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

/* ══════════════════════════════════════════════════════════════
   23. INITIALIZATION
   ══════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  // Set initial view
  document.body.dataset.view = currentView;

  // Build the grid and load data
  buildGrid();
  loadAllEvents();

  // Bind modal form listeners — start/end time sync
  document.getElementById("start-time")?.addEventListener("change", updateEndFromStart);
  document.getElementById("end-time")?.addEventListener("change", updateDurationFromEnd);
  document.getElementById("reminder-select")?.addEventListener("change", handleReminderSelect);

  // Auto-scroll to current time (or 7 AM if not today)
  setTimeout(() => {
    const today = getISTDate();
    const dates = getVisibleDates();
    if (dates.includes(today)) {
      scrollToNow();
    } else {
      scrollTo7AM();
    }
  }, 400);

  // Start current-time-line updater
  startTimeLineUpdater();

  // Render feather icons
  if (window.feather) feather.replace();
});


const USE_TIMELINE_VIEW = false; // Set to true to enable timeline view
const summaryModal = document.getElementById("summary-modal");
const summaryContent = document.getElementById("summary-content");
let dragGhost = null;
let PLAN_DATE =
  document.body.dataset.planDate ||
  new Date().toISOString().slice(0,10);

function initDragSystem() {

  document.querySelectorAll(".event-block").forEach(block => {

    block.addEventListener("mousedown", e => {

      if (e.target.classList.contains("resize-handle")) return;

      draggingEvent = block;

      const rect = block.getBoundingClientRect();
      dragOffsetY = e.clientY - rect.top;

      dragGhost = block.cloneNode(true);
      dragGhost.classList.add("event-ghost");

      dragGhost.style.width = rect.width + "px";
      dragGhost.style.height = rect.height + "px";

      block.parentElement.appendChild(dragGhost);

      block.style.opacity = "0.3";

      document.body.style.userSelect = "none";

    });

  });

}

function initSlotDrag() {

  document.querySelectorAll(".time-row").forEach(row => {

    row.addEventListener("mousedown", () => {

      dragStartSlot = Number(row.dataset.slot);
      dragEndSlot = dragStartSlot;
      isDragging = true;

      highlightSlots();

    });

    row.addEventListener("mouseenter", () => {

      if (!isDragging) return;

      dragEndSlot = Number(row.dataset.slot);
      highlightSlots();

    });

    row.addEventListener("click", e => {

      if (isDragging) return;

      const slot = Number(row.dataset.slot);
      openCreateEvent(slot, slot);

    });

  });

}

/* =========================================================
   CLOCK (IST)
========================================================= */
function updateClock() {
  const el = document.getElementById("clock");
  if (!el) return;

  const ist = new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
  );
  el.textContent = ist.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

/* =========================================================
   MOBILE PULL-DOWN TO CLOSE SUMMARY
========================================================= */
let touchStartY = null;
let isAtTop = false;

if (summaryModal && summaryContent) {
  summaryModal.addEventListener("touchstart", e => {
    if (e.touches.length !== 1) return;
    touchStartY = e.touches[0].clientY;
    isAtTop = summaryContent.scrollTop === 0;
  });

  summaryModal.addEventListener("touchmove", e => {
    if (!touchStartY || !isAtTop) return;
    const deltaY = e.touches[0].clientY - touchStartY;
    if (deltaY > 80) {
      closeSummary();
      touchStartY = null;
    }
  });

  summaryModal.addEventListener("touchend", () => {
    touchStartY = null;
  });
}



/* =========================================================
   ESC KEY
========================================================= */
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    const modal = document.getElementById("summary-modal");
    if (modal && modal.style.display === "flex") {
      closeSummary();
    }
  }
});

/* =========================================================
   HABITS / REFLECTION SYNC
========================================================= */
function syncHabit(cb) {
  const main = document.querySelector(
    `input[name="habits"][value="${cb.dataset.habit}"]`
  );
  if (main) main.checked = cb.checked;
}

function syncReflection(el) {
  const main = document.querySelector('textarea[name="reflection"]');
  if (main) main.value = el.value;
}
function getISTDate() {
  return new Date().toLocaleDateString("en-CA", {
    timeZone: "Asia/Kolkata"
  });
}

/* =========================================================
   EVENT EDITING
========================================================= */

function saveEvent(startSlot, endSlot) {

  const text = document.getElementById("editText")?.value || "";

  fetch("/slot/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      start_slot: startSlot,
      end_slot: endSlot,
      text: text
    })
  }).then(() => location.reload());

}

/* =========================================================
   DAY STRIP AUTO-SCROLL
========================================================= */


document.addEventListener("DOMContentLoaded", () => {
  prefetchAdjacentDays();
  initDragSystem();   // 🔴 ADD THIS
  initSlotDrag();
  if (USE_TIMELINE_VIEW) {
    document.body.classList.add("timeline-mode");

    const root = document.getElementById("timeline-root");
    if (root) {
      renderTimeline(window.TIMELINE_TASKS || [], root);
      renderTimeGutter();
    }
  }
});


function toggleCheckin() {
  const modal = document.getElementById("summary-modal");
  if (!modal) return;

  modal.style.display =
    modal.style.display === "flex" ? "none" : "flex";
}

/* =========================================================
   SUBTASK TOGGLE
========================================================= */
function toggleSubtask(id, isDone) {
  fetch("/subtask/toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, is_done: isDone })
  });
}

window.addEventListener("focusin", () =>
  document.body.classList.add("keyboard-open")
);

window.addEventListener("focusout", () =>
  document.body.classList.remove("keyboard-open")
);

function handleSmartSave(e) {
  e?.preventDefault?.();

  const form = document.getElementById("planner-form");
  let text = document
  .querySelector('textarea[name="smart_plan"]')
  .value
  .trim();

  text = normalizeSmartTime(text);

  if (!text) {
    form.submit();
    return;
  }

  const timeRange = parseTimeRange(text);

  // No time detected → safe submit
  if (!timeRange) {
    smartAdd(text);
    return;
  }

  // Ask backend to preview slot conflicts
  fetch("/smart/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      text
    })
  })
    .then(r => r.json())
    .then(result => {
      if (!result.conflicts || !result.conflicts.length) {
        smartAdd(text);
        return;
      }

      openSmartPreview(result);
    });
}
function smartAdd(text) {
  return fetch("/smart/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      text: text
    })
  }).then(() => {
    window.location.reload();
  });
}

function openSmartPreview(result) {
  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  const html = result.conflicts.map(c => `
    <div style="margin-bottom:10px">
      <strong>${c.time}</strong>
      <pre>${c.existing}</pre>
      <hr>
      <pre>${c.incoming}</pre>
    </div>
  `).join("");

  content.innerHTML = `
    <h3>⚠️ Slot conflicts</h3>
    ${html}
    <button onclick="modal.style.display='none'">Cancel</button>
    <button onclick="smartAdd(document.querySelector('textarea[name=smart_plan]').value)">
        Overwrite & Save
    </button>

  `;

  modal.style.display = "flex";
}
function normalizeSmartTime(line) {
  // Only normalize whitespace, do NOT infer time
  return line.trim().replace(/\s+/g, " ");
}

function parseTimeRange(text) {
  // Matches: 9-10 | 9.30-10.30 | 9:30-10:30
  const m = text.match(
    /(\d{1,2})(?:[.:](\d{2}))?\s*-\s*(\d{1,2})(?:[.:](\d{2}))?/
  );

  if (!m) return null;

  const sh = parseInt(m[1], 10);
  const sm = parseInt(m[2] || "0", 10);
  const eh = parseInt(m[3], 10);
  const em = parseInt(m[4] || "0", 10);

  if (
    sh > 23 || eh > 23 ||
    sm > 59 || em > 59
  ) return null;

  return {
    startMinutes: sh * 60 + sm,
    endMinutes: eh * 60 + em
  };
}
function parseTimeToMinutes(timeStr) {
  // supports: 2.15, 2:15, 14.15, 14:15
  const [h, m = "00"] = timeStr.replace(".", ":").split(":");
  return parseInt(h, 10) * 60 + parseInt(m, 10);
}

function minutesToTime(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}:${m.toString().padStart(2, "0")}`;
}
function snapDown(mins) {
  return Math.floor(mins / 30) * 30;
}

function snapUp(mins) {
  return Math.ceil(mins / 30) * 30;
}
document.addEventListener("change", async (e) => {
  if (!e.target.classList.contains("slot-checkbox")) return;

  const slot = e.target.dataset.slot;
  const checked = e.target.checked;

  try {
    await fetch("/slot/toggle-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_date: document.body.dataset.planDate,
        slot: slot,
        status: checked ? "done" : "open"
      })
    });
  } catch (err) {
    console.error(err);
    e.target.checked = !checked;
  }
});
function getHourLabel(timeStr) {
  const [h, m] = timeStr.split(":").map(Number);
  const hour12 = h % 12 || 12;
  const ampm = h >= 12 ? "PM" : "AM";
  return `${hour12} ${ampm}`;
}

function calculateDuration(start, end) {
  if (!end) return "";
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const mins = (eh * 60 + em) - (sh * 60 + sm);
  const hrs = mins / 60;
  return hrs % 1 === 0 ? `${hrs} hr` : `${hrs.toFixed(1)} hrs`;
}
function renderTimeline(tasks, root) {
  if (!root) return;

  root.innerHTML = "";
  root.id = "timeline"; // optional, for CSS

  if (!Array.isArray(tasks) || tasks.length === 0) {
    root.innerHTML = "<div style='opacity:.6'>No scheduled tasks</div>";
    return;
  }

  // Normalize + filter
  const normalized = tasks
    .filter(t => t.start_time) // timeline needs time
    .map(t => ({
      ...t,
      text: t.text || t.plan || ""
    }))
    .sort((a, b) => a.start_time.localeCompare(b.start_time));

  let lastHour = null;

  normalized.forEach(task => {
    const hour = task.start_time.split(":")[0];
    root.appendChild(renderTaskCard(task));
  });
}



function renderTaskCard(task) {
  const div = document.createElement("div");
  div.className = "task-card";

  const duration = calculateDuration(task.start_time, task.end_time);

  div.innerHTML = `
    <div class="task-main">
      <input type="checkbox" class="task-check" />
      <div class="task-content">
        <div class="task-title">${task.text}</div>
        ${duration ? `<div class="task-meta">${duration}</div>` : ""}
      </div>
    </div>
  `;

  return div;
}
/* =========================================================
   EVENT EDITING
========================================================= */

function editEvent(startSlot, endSlot) {

  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  fetch(`/slot/get?date=${PLAN_DATE}&slot=${startSlot}`)
    .then(r => r.json())
    .then(data => {

      const text = (data.text || "")
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;");

      content.innerHTML = `
        <h3>✏️ Edit Event</h3>

        <textarea id="editText" style="width:100%;min-height:140px;">${text}</textarea>

        <br><br>

        <button onclick="closeModal()">Cancel</button>
        <button onclick="saveEvent(${startSlot}, ${endSlot})">Save</button>
      `;

      if (modal) modal.style.display = "flex";
    })
    .catch(err => {
      console.error("Edit fetch failed:", err);
    });
}

function closeModal() {
  const modal = document.getElementById("modal");
  if (modal) modal.style.display = "none";
}



function renderDailySummaryTable() {
  const rows = [];

  document.querySelectorAll(".time-row").forEach(row => {
    const label = row.querySelector(".time-column")?.innerText?.trim();
    const checkbox = row.querySelector(".slot-checkbox");
    if (!label || !checkbox) return;

    rows.push({
      time: label,
      done: checkbox.checked
    });
  });

  return `
    <table style="width:100%; border-collapse:collapse">
      <tr>
        <th align="left">Time</th>
        <th align="left">Status</th>
      </tr>
      ${rows.map(r => `
        <tr>
          <td>${r.time}</td>
          <td>${r.done ? "✅ Done" : "⬜ Open"}</td>
        </tr>
      `).join("")}
    </table>
  `;
}

function promoteUntimed(btn) {
  const id = btn.dataset.id;

  fetch("/task/promote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id,
      plan_date: document.body.dataset.planDate
    })
  }).then(() => window.location.reload());
}
function scheduleUntimed(taskId) {
  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  content.innerHTML = `
    <h3>🕒 Schedule task</h3>
    <p>Select a start slot:</p>
    <input type="number" id="schedule-slot" min="1" max="48" value="1">
    <br><br>
    <button onclick="modal.style.display='none'">Cancel</button>
    <button onclick="confirmSchedule('${taskId}')">Schedule</button>
  `;

  modal.style.display = "flex";
}

function confirmSchedule(taskId) {
  const slot = document.getElementById("schedule-slot").value;

  fetch("/task/schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: taskId,
      plan_date: document.body.dataset.planDate,
      slot: Number(slot)
    })
  }).then(() => window.location.reload());
}
document.addEventListener("click", async (e) => {

  const btn = e.target.closest("#generatePlanBtn");
  if (!btn) return;

  const selectedDate = btn.dataset.date;
  const output = document.getElementById("aiPlanOutput");

  output.innerHTML = "⏳ Generating AI plan...";

  btn.disabled = true;

  const res = await fetch("/ai/generate-day-plan", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      date: selectedDate
    })
  });

  const data = await res.json();

 streamText(output, data.result);

  btn.disabled = false;
});
function streamText(el, text, speed = 20) {

  el.innerText = "";
  el.classList.add("streaming");

  const words = text.split(" ");
  let i = 0;

  function next() {

    if (i >= words.length) {
      el.classList.remove("streaming");
      return;
    }

    el.innerText += (i === 0 ? "" : " ") + words[i];
    i++;

    setTimeout(next, speed);
  }

  next();
}
function loadPlannerForDate(date) {
  PLAN_DATE = date;
  loadTasks();
  loadHealth();
  renderPlanner();
}
function jumpToDate() {

  const monthInput = document.getElementById("jump-month");
  const dayInput = document.getElementById("jump-day");

  if (!monthInput.value || !dayInput.value) {
    alert("Please select a date");
    return;
  }

  const [year, month] = monthInput.value.split("-");
  const day = dayInput.value.padStart(2,"0");

  const newDate = `${year}-${month}-${day}`;

  window.location.replace(
  `/?year=${year}&month=${month}&day=${day}`
  );
}


document.addEventListener("mouseup", () => {

  if (!isDragging) return;

  isDragging = false;

  const start = Math.min(dragStartSlot, dragEndSlot);
  const end = Math.max(dragStartSlot, dragEndSlot);

  clearSlotHighlight();

  openCreateEvent(start, end);

});


function highlightSlots() {

  clearSlotHighlight();

  const start = Math.min(dragStartSlot, dragEndSlot);
  const end = Math.max(dragStartSlot, dragEndSlot);

  document.querySelectorAll(".time-row").forEach(row => {

    const slot = Number(row.dataset.slot);

    if (slot >= start && slot <= end) {
      row.classList.add("slot-preview");
    }

  });

}

function clearSlotHighlight() {

  document
    .querySelectorAll(".slot-preview")
    .forEach(el => el.classList.remove("slot-preview"));

}

function openCreateEvent(startSlot, endSlot) {

  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  content.innerHTML = `
    <h3>Create Event</h3>

    <textarea id="editText"
      placeholder="Event description"
      style="width:100%;min-height:120px"></textarea>

    <br><br>

    <button onclick="closeModal()">Cancel</button>
    <button onclick="saveEvent(${startSlot}, ${endSlot})">Save</button>
  `;

  modal.style.display = "flex";

}

/* =========================================================
   DRAG EVENT TO MOVE
========================================================= */


/* =========================================================
   DRAG EVENT TO MOVE
========================================================= */
/* =========================================================
   DRAG EVENT TO MOVE
========================================================= */

let draggingEvent = null;
let dragOffsetY = 0;


document.addEventListener("mousemove", e => {

  if (!draggingEvent) return;

  const container = document.querySelector(".day-grid");
  const rect = container.getBoundingClientRect();

  const y = e.clientY - rect.top - dragOffsetY;

  const slotHeight = parseFloat(
  getComputedStyle(document.documentElement)
    .getPropertyValue("--slot-height")
);

const snappedSlot = Math.round(y / slotHeight);

if (dragGhost) {
  dragGhost.style.top = `${snappedSlot * slotHeight}px`;
}

});

document.addEventListener("mouseup", e => {

  if (!draggingEvent) return;

  const slotHeight = parseFloat(
    getComputedStyle(document.documentElement)
      .getPropertyValue("--slot-height")
  );

  const top = dragGhost ? dragGhost.offsetTop : draggingEvent.offsetTop;

  const newStart = Math.round(top / slotHeight) + 1;

  const start = Number(draggingEvent.dataset.start);
  const end = Number(draggingEvent.dataset.end);

  const duration = end - start;

  const newEnd = newStart + duration;

  draggingEvent.style.opacity = "";
  document.body.style.userSelect = "";

    saveEvent(newStart, newEnd);
    if (dragGhost) {
    dragGhost.remove();
    dragGhost = null;
  }

draggingEvent.style.opacity = "";
  draggingEvent = null;

});
/* =========================================================
   RESIZE EVENT
========================================================= */

let resizingEvent = null;

document.querySelectorAll(".resize-handle").forEach(handle => {

  handle.addEventListener("mousedown", e => {

    e.stopPropagation();

    resizingEvent = handle.parentElement;

    document.body.style.userSelect = "none";

  });

});

document.addEventListener("mousemove", e => {

  if (!resizingEvent || draggingEvent) return;

  const container = document.querySelector(".day-grid");
  const rect = container.getBoundingClientRect();

  const slotHeight = parseFloat(
    getComputedStyle(document.documentElement)
      .getPropertyValue("--slot-height")
  );

  const y = e.clientY - rect.top;

  const start = Number(resizingEvent.dataset.start);

  let newEnd = Math.round(y / slotHeight) + 1;

  if (newEnd <= start) newEnd = start + 1;

  const newHeight = (newEnd - start + 1) * slotHeight;

  resizingEvent.style.height = `${newHeight}px`;

});

document.addEventListener("mouseup", () => {

  if (!resizingEvent) return;

  const slotHeight = parseFloat(
    getComputedStyle(document.documentElement)
      .getPropertyValue("--slot-height")
  );

  const start = Number(resizingEvent.dataset.start);

  const height = resizingEvent.offsetHeight;

  const slots = Math.round(height / slotHeight);

  const newEnd = start + slots - 1;

  saveEvent(start, newEnd);

  resizingEvent = null;

  document.body.style.userSelect = "";

});


function prefetchAdjacentDays() {
  const d = new Date(PLAN_DATE);

  const prev = new Date(d);
  prev.setDate(d.getDate() - 1);

  const next = new Date(d);
  next.setDate(d.getDate() + 1);

  [prev, next].forEach(date => {
    const y = date.getFullYear();
    const m = date.getMonth() + 1;
    const day = date.getDate();

    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = `/?year=${y}&month=${m}&day=${day}`;

    document.head.appendChild(link);
  });
}
document.addEventListener("click", async e => {

  const link = e.target.closest(".day-link");
  if (!link) return;

  e.preventDefault();

  const res = await fetch(link.href);
  const html = await res.text();

  const doc = new DOMParser().parseFromString(html,"text/html");

  document.querySelector("#planner-root").innerHTML =
  doc.querySelector("#planner-root").innerHTML;

  initDragSystem();   // 🔴 REATTACH DRAG EVENTS
  initSlotDrag();

  history.pushState({}, "", link.href);

});
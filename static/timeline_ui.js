/* ═══════════════════════════════════════════════════════════════════════
   ROADMAP

   Two ways to move a task, because one of them does not exist on a phone:

   - DRAG, for a mouse. Kept exactly as it was.
   - THE RESCHEDULE SHEET, for everything. HTML5 drag-and-drop fires no
     events on a touch screen — no dragstart, no drop — so until this
     existed the roadmap was read-only on the device it is most often
     opened on. The sheet also reaches dates that drag cannot: a block
     only appears on this page if a task already sits on that date, so
     dragging could never move work to a free day.

   Both paths POST the same {task_id, new_date} to the same endpoint.
   Nothing here needs anything new from the server.
   ═══════════════════════════════════════════════════════════════════════ */

const RESCHEDULE_URL = "/api/timeline/reschedule";

/* ─────────────────────────────────────────────────────────────────────
   DATES — shared with Sprints and the goal countdowns, so "3 days late"
   means the same thing and is computed the same way everywhere.
   See static/js/dates.js for why the arithmetic is done in UTC.
   ───────────────────────────────────────────────────────────────────── */

const D = window.DPDates;
const todayISO    = () => D.todayISO();
const addDays     = (iso, n) => D.addDays(iso, n);
const daysBetween = (a, b) => D.daysBetween(a, b);
const humanDay    = iso => D.humanDay(iso);
const relativeDay = (iso, today) => D.relativeDay(iso, today);

/* ─────────────────────────────────────────────────────────────────────
   MARK UP WHAT IS LATE
   Every block gets late / today / ahead from its own data-date, and the
   header gets the three counts. Previously a task three weeks overdue
   looked exactly like one due next month.
   ───────────────────────────────────────────────────────────────────── */

function markTimeline() {
  const today = todayISO();
  const blocks = document.querySelectorAll(".time-block[data-date]");
  let late = 0, due = 0, ahead = 0;

  blocks.forEach(block => {
    const iso = block.dataset.date;
    if (!iso) return;
    const n = daysBetween(today, iso);
    const count = block.querySelectorAll(".timeline-card").length;

    block.classList.remove("is-late", "is-today", "is-ahead");
    if (n < 0)      { block.classList.add("is-late");  late  += count; }
    else if (n === 0) { block.classList.add("is-today"); due  += count; }
    else            { block.classList.add("is-ahead"); ahead += count; }

    const when = block.querySelector(".time-when");
    if (when) when.textContent = relativeDay(iso, today);
  });

  const summary = document.getElementById("tl-summary");
  if (!summary) return;
  if (!blocks.length) { summary.hidden = true; return; }

  // The pills are BUTTONS that jump to the first block of their kind.
  // The roadmap lists every scheduled task from the earliest, so on a
  // phone you open on months-old work and scroll. An earlier version of
  // this scrolled you to today automatically, which is worse: it fights
  // the browser's own scroll restoration when you come back via Back,
  // and it moves the page under someone who did not ask it to. A pill you
  // can tap puts the same shortcut in your hands instead.
  const parts = [];
  if (late)  parts.push(`<button type="button" class="tl-pill is-late" data-jump="is-late">${late} late</button>`);
  if (due)   parts.push(`<button type="button" class="tl-pill is-today" data-jump="is-today">${due} due today</button>`);
  if (ahead) parts.push(`<button type="button" class="tl-pill is-ahead" data-jump="is-ahead">${ahead} ahead</button>`);
  summary.innerHTML = parts.join("");
  summary.hidden = parts.length === 0;

  summary.querySelectorAll("[data-jump]").forEach(pill => {
    pill.addEventListener("click", () => jumpTo(pill.dataset.jump));
  });
}

/** Scroll to the first block of a given kind. */
function jumpTo(cls) {
  const target = document.querySelector(".time-block." + cls);
  if (!target) return;
  // Guarded: jsdom has no scrollIntoView, and neither do some embedded
  // webviews. A shortcut that cannot scroll should do nothing, not throw
  // and take the rest of the handler with it.
  if (typeof target.scrollIntoView === "function") {
    target.scrollIntoView({ block: "start", behavior: "smooth" });
  }
  target.classList.remove("just-jumped");
  // Reflow so the animation restarts when the same pill is tapped twice.
  void target.offsetWidth;
  target.classList.add("just-jumped");
}

/* ─────────────────────────────────────────────────────────────────────
   THE SHEET
   ───────────────────────────────────────────────────────────────────── */

let sheetCard = null;        // the card being moved
let lastFocus = null;        // where focus came from, to put it back

function openReschedule(btn) {
  const card = btn.closest(".timeline-card");
  if (!card) return;
  sheetCard = card;
  lastFocus = btn;

  const today = todayISO();
  const current = card.dataset.date || today;

  document.getElementById("tl-sheet-title").textContent =
    card.dataset.title || "This task";
  document.getElementById("tl-sheet-current").textContent =
    `Currently ${humanDay(current)} · ${relativeDay(current, today)}`;

  // Quick choices, each one tap. "Next Monday" is the one people actually
  // reach for when pushing work out of this week.
  const quick = [
    ["Today", today],
    ["Tomorrow", addDays(today, 1)],
    ["Next Monday", D.nextMonday(today)],
    ["In a week", addDays(today, 7)],
  ];
  const wrap = document.getElementById("tl-quick");
  wrap.innerHTML = "";
  quick.forEach(([label, iso]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tl-chip" + (iso === current ? " is-current" : "");
    b.innerHTML = `${label}<small>${humanDay(iso)}</small>`;
    b.onclick = () => commitReschedule(iso);
    wrap.appendChild(b);
  });

  const dateInput = document.getElementById("tl-date");
  dateInput.value = current;

  document.getElementById("tl-scrim").hidden = false;
  const sheet = document.getElementById("tl-sheet");
  sheet.hidden = false;
  document.body.classList.add("tl-sheet-open");
  if (window.feather) feather.replace();
  requestAnimationFrame(() => sheet.classList.add("is-open"));

  document.addEventListener("keydown", sheetKeydown);
}

function closeReschedule() {
  const sheet = document.getElementById("tl-sheet");
  sheet.classList.remove("is-open");
  sheet.hidden = true;
  document.getElementById("tl-scrim").hidden = true;
  document.body.classList.remove("tl-sheet-open");
  document.removeEventListener("keydown", sheetKeydown);
  if (lastFocus) { try { lastFocus.focus(); } catch {} }
  sheetCard = null;
  lastFocus = null;
}

function sheetKeydown(e) {
  if (e.key === "Escape") { e.preventDefault(); closeReschedule(); }
}

function saveReschedule() {
  const iso = document.getElementById("tl-date").value;
  if (!iso) {
    if (window.showToast) showToast("Pick a date first", "error");
    return;
  }
  commitReschedule(iso);
}

function commitReschedule(iso) {
  if (!sheetCard) return;
  const taskId = sheetCard.dataset.task;
  const from = sheetCard.dataset.date;
  if (!taskId) { closeReschedule(); return; }
  if (iso === from) { closeReschedule(); return; }

  const save = document.getElementById("tl-save");
  if (save) { save.disabled = true; save.textContent = "Moving…"; }

  reschedule(taskId, iso)
    .then(() => {
      if (window.showToast) showToast(`Moved to ${humanDay(iso)}`, "success");
      // The server groups the blocks, so it re-renders them correctly;
      // regrouping here would mean reimplementing that grouping in a
      // second place and keeping the two in step.
      window.location.reload();
    })
    .catch(err => {
      console.error("Reschedule failed", err);
      if (window.showToast) showToast("Could not move that task. It is still on its old date.", "error");
      if (save) { save.disabled = false; save.textContent = "Move"; }
    });
}

/** The one place that talks to the API. */
function reschedule(taskId, newDate) {
  return fetch(RESCHEDULE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, new_date: newDate }),
  })
    .then(r => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(resp => {
      if (resp.status !== "ok") throw new Error(resp.message || "rejected");
      return resp;
    });
}

/* ─────────────────────────────────────────────────────────────────────
   DRAG — mouse only, unchanged in behaviour
   ───────────────────────────────────────────────────────────────────── */

let draggedTask = null;

function dragStart(e) {
  draggedTask = e.currentTarget;
  e.dataTransfer.effectAllowed = "move";
}

function dragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add("drag-over");
}

function dragLeave(e) {
  const rect = e.currentTarget.getBoundingClientRect();
  const { clientX: x, clientY: y } = e;
  // Still inside the block — a child element just took the pointer.
  if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) return;
  e.currentTarget.classList.remove("drag-over");
}

function dropTask(e) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");
  if (!draggedTask) return;

  const card = draggedTask;
  draggedTask = null;

  const taskId = card.dataset.task;
  const newDate = e.currentTarget.dataset.date;
  if (!taskId || !newDate) {
    console.warn("Missing taskId or newDate for reschedule");
    return;
  }
  if (newDate === card.dataset.date) return;

  // Move it visually first so the drop feels immediate, then confirm.
  const container = e.currentTarget.querySelector(".time-content");
  const previousParent = card.parentElement;
  if (container) container.appendChild(card);

  reschedule(taskId, newDate)
    .then(() => {
      card.dataset.date = newDate;
      markTimeline();
      if (window.showToast) showToast(`Moved to ${humanDay(newDate)}`, "success");
    })
    .catch(err => {
      console.error("Reschedule error", err);
      // Put it back. A card that stays where you dropped it while the
      // server still has the old date is the worst of both.
      if (previousParent) previousParent.appendChild(card);
      markTimeline();
      if (window.showToast) showToast("Could not move that task. It is still on its old date.", "error");
    });
}

/* ─────────────────────────────────────────────────────────────────────
   ZOOM + FILTER
   ───────────────────────────────────────────────────────────────────── */

function setZoom(mode) {
  const url = new URL(window.location);
  url.searchParams.set("zoom", mode);
  window.location = url;
}

function filterProject(pid) {
  const url = new URL(window.location);
  if (pid) url.searchParams.set("project", pid);
  else url.searchParams.delete("project");
  window.location = url;
}

document.addEventListener("DOMContentLoaded", markTimeline);

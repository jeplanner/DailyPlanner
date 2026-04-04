/* ============================================================
   Health Dashboard — Modern SaaS Habit Tracker
   ============================================================ */

// --------------- State ---------------
let currentDate = "";
let saveHealthTimer = null;
let habitSaveTimers = {};

// --------------- IST Timezone ---------------
function getISTDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

function getISTDateObj() {
  const str = new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" });
  return new Date(str);
}

// --------------- Initialization ---------------
document.addEventListener("DOMContentLoaded", () => {
  currentDate = getISTDate();
  renderDateStrip();
  loadHealth(currentDate);
  loadWeeklyStats();
  loadHeatmap();
  if (typeof feather !== "undefined") feather.replace();

  // Close habit sheet on overlay click
  const sheet = document.getElementById("habit-sheet");
  if (sheet) {
    sheet.addEventListener("click", (e) => {
      if (e.target === sheet) closeHabitSheet();
    });
  }
});

// ============================================================
//  DATE STRIP
// ============================================================
function renderDateStrip() {
  const strip = document.getElementById("date-strip");
  if (!strip) return;
  strip.innerHTML = "";

  const today = getISTDateObj();
  const todayStr = getISTDate();
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toLocaleDateString("en-CA");
    const dayName = dayNames[d.getDay()];
    const dayNum = d.getDate();

    const pill = document.createElement("button");
    pill.className = "date-pill";
    if (dateStr === todayStr) pill.classList.add("today");
    if (dateStr === currentDate) pill.classList.add("active");
    pill.dataset.date = dateStr;

    pill.innerHTML = `
      <span class="date-pill-day">${dayName}</span>
      <span class="date-pill-num">${dayNum}</span>
      <span class="date-pill-dot"></span>
    `;

    pill.addEventListener("click", () => {
      currentDate = dateStr;
      document.querySelectorAll(".date-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      loadHealth(currentDate);
      loadHeatmap();
    });

    strip.appendChild(pill);
  }
}

// Mark dots for dates that have data (called after heatmap loads)
function markDateStripDots(heatmapData) {
  document.querySelectorAll(".date-pill").forEach(pill => {
    const d = pill.dataset.date;
    const dot = pill.querySelector(".date-pill-dot");
    if (dot && heatmapData[d] && heatmapData[d] > 0) {
      dot.classList.add("has-data");
    }
  });
}

// ============================================================
//  MAIN DATA LOADER
// ============================================================
async function loadHealth(date) {
  try {
    const res = await fetch(`/api/v2/daily-health?date=${date}`);
    if (!res.ok) throw new Error("Failed to load health data");
    const data = await res.json();

    // --- Health metric fields ---
    const weightEl = document.getElementById("health-weight");
    const heightEl = document.getElementById("health-height");
    const moodEl = document.getElementById("health-mood");
    const energyEl = document.getElementById("health-energy");
    const notesEl = document.getElementById("health-notes");

    if (weightEl) weightEl.value = data.weight || "";
    if (heightEl) heightEl.value = data.height || "";
    if (moodEl) moodEl.value = data.mood || "neutral";
    if (energyEl) energyEl.value = data.energy_level || 5;
    if (notesEl) notesEl.value = data.notes || "";

    updateEnergyLabel();
    calculateBMI();

    // --- Habits ---
    if (data.habits) {
      renderHabits(data.habits);
    }

    // --- Overview cards ---
    updateRing(data.habit_percent || 0);
    updateHealthScore(data);

    const streakEl = document.getElementById("streak-value");
    if (streakEl) streakEl.textContent = data.streak || 0;

    if (typeof feather !== "undefined") feather.replace();
  } catch (err) {
    console.error("loadHealth error:", err);
    if (typeof showToast === "function") showToast("Failed to load health data", "error");
  }
}

// ============================================================
//  COMPLETION RING
// ============================================================
const RING_CIRCUMFERENCE = 2 * Math.PI * 52; // ~326.73

function updateRing(percent) {
  const fill = document.getElementById("ring-fill");
  const pctEl = document.getElementById("ring-percent");
  if (!fill) return;

  const offset = RING_CIRCUMFERENCE * (1 - percent / 100);
  fill.style.transition = "stroke-dashoffset 0.8s ease";
  fill.setAttribute("stroke-dasharray", RING_CIRCUMFERENCE);
  fill.setAttribute("stroke-dashoffset", offset);

  if (pctEl) pctEl.textContent = `${Math.round(percent)}%`;
}

// ============================================================
//  HEALTH SCORE
// ============================================================
function updateHealthScore(data) {
  const el = document.getElementById("health-score");
  if (!el) return;

  const habitPercent = data.habit_percent || 0;
  const energy = data.energy_level || 0;
  const mood = data.mood || "neutral";
  const streak = data.streak || 0;

  // habitScore: 0-50
  const habitScore = habitPercent * 0.5;

  // energyScore: 0-15
  const energyScore = (energy / 10) * 15;

  // moodScore: 0-10
  const moodMap = { great: 10, good: 8, neutral: 6, low: 3, bad: 1 };
  const moodScore = moodMap[mood] || 6;

  // streakScore: 0-15
  const streakScore = Math.min(streak * 1.5, 15);

  // weightScore: constant 10
  const weightScore = 10;

  const total = Math.round(habitScore + energyScore + moodScore + streakScore + weightScore);
  el.textContent = total;
}

// ============================================================
//  WEEKLY STATS
// ============================================================
async function loadWeeklyStats() {
  try {
    const res = await fetch("/api/v2/weekly-health");
    if (!res.ok) return;
    const data = await res.json();

    const avgEl = document.getElementById("weekly-avg");
    if (avgEl) avgEl.textContent = `${Math.round(data.weekly_avg || 0)}%`;
  } catch (err) {
    console.error("loadWeeklyStats error:", err);
  }
}

// ============================================================
//  HEATMAP
// ============================================================
async function loadHeatmap() {
  try {
    const res = await fetch("/api/v2/heatmap");
    if (!res.ok) return;
    const data = await res.json();
    renderHeatmap(data);
    markDateStripDots(data);
  } catch (err) {
    console.error("loadHeatmap error:", err);
  }
}

function renderHeatmap(data) {
  const container = document.getElementById("heatmap");
  if (!container) return;
  container.innerHTML = "";

  const today = getISTDateObj();

  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toLocaleDateString("en-CA");
    const pct = data[dateStr] || 0;

    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    cell.title = `${dateStr}: ${Math.round(pct)}%`;

    if (pct === 0) {
      cell.classList.add("level-0");
    } else if (pct <= 25) {
      cell.classList.add("level-1");
    } else if (pct <= 50) {
      cell.classList.add("level-2");
    } else if (pct <= 75) {
      cell.classList.add("level-3");
    } else {
      cell.classList.add("level-4");
    }

    container.appendChild(cell);
  }
}

// ============================================================
//  HABIT GRID
// ============================================================
function renderHabits(habits) {
  const grid = document.getElementById("habit-grid");
  if (!grid) return;
  grid.innerHTML = "";

  habits.forEach(habit => {
    const card = createHabitCard(habit);
    grid.appendChild(card);
  });

  if (typeof feather !== "undefined") feather.replace();
}

function createHabitCard(habit) {
  const card = document.createElement("div");
  card.className = "habit-card";
  card.dataset.habitId = habit.id;

  const value = habit.value || 0;
  const goal = habit.goal || 1;
  const pct = Math.min(Math.round((value / goal) * 100), 100);
  const isBoolean = habit.habit_type === "boolean";
  const isComplete = value >= goal;

  if (isComplete) card.classList.add("completed");

  // Determine step based on unit
  const step = getStepForUnit(habit.unit);

  // Goal text
  const goalText = isBoolean ? "Yes / No" : `${goal} ${habit.unit || ""}`;

  card.innerHTML = `
    <div class="habit-card-header">
      <div class="habit-card-info">
        <span class="habit-card-name">${escapeHtml(habit.name)}</span>
        <span class="habit-card-goal">${escapeHtml(goalText)}</span>
      </div>
      <div class="habit-card-actions">
        <button class="habit-action-btn" onclick="editHabit(${habit.id})" title="Edit">
          <i data-feather="edit-2" style="width:14px;height:14px"></i>
        </button>
        <button class="habit-action-btn habit-delete-btn" onclick="deleteHabit(${habit.id})" title="Delete">
          <i data-feather="trash-2" style="width:14px;height:14px"></i>
        </button>
      </div>
    </div>

    ${isBoolean ? buildBooleanInput(habit) : buildNumericInput(habit, step)}

    <div class="habit-progress-row">
      <div class="habit-progress-bar">
        <div class="habit-progress-fill" style="width:${pct}%"></div>
      </div>
      <span class="habit-progress-pct">${pct}%</span>
    </div>

    <div class="habit-weekly-dots" data-habit-id="${habit.id}"></div>
  `;

  // Load weekly dots
  loadWeeklyDots(habit.id);

  return card;
}

function buildNumericInput(habit, step) {
  const value = habit.value || 0;
  return `
    <div class="habit-input-row">
      <button class="habit-step-btn habit-minus" onclick="stepHabit(${habit.id}, -${step})">
        <i data-feather="minus" style="width:16px;height:16px"></i>
      </button>
      <input type="number" class="habit-value-input" id="habit-val-${habit.id}"
             value="${value}" min="0" step="${step}"
             data-habit-id="${habit.id}"
             onchange="onHabitValueChange(${habit.id})">
      <button class="habit-step-btn habit-plus" onclick="stepHabit(${habit.id}, ${step})">
        <i data-feather="plus" style="width:16px;height:16px"></i>
      </button>
    </div>
  `;
}

function buildBooleanInput(habit) {
  const value = habit.value || 0;
  const isOn = value >= 1;
  return `
    <div class="habit-input-row habit-input-row-bool">
      <button class="habit-toggle ${isOn ? "active" : ""}"
              id="habit-val-${habit.id}"
              data-habit-id="${habit.id}"
              onclick="toggleBooleanHabit(${habit.id})">
        ${isOn ? "Done" : "Not done"}
      </button>
    </div>
  `;
}

function getStepForUnit(unit) {
  if (!unit) return 1;
  const u = unit.toLowerCase();
  if (u === "steps") return 100;
  if (u === "ml") return 100;
  if (u === "mins" || u === "minutes") return 5;
  return 1;
}

// ============================================================
//  HABIT VALUE CHANGES
// ============================================================
function onHabitValueChange(habitId) {
  const input = document.getElementById(`habit-val-${habitId}`);
  if (!input) return;

  let val = parseFloat(input.value) || 0;
  if (val < 0) val = 0;
  input.value = val;

  updateHabitCardProgress(habitId, val);
  debouncedSaveHabit(habitId, val);
}

function stepHabit(habitId, delta) {
  const input = document.getElementById(`habit-val-${habitId}`);
  if (!input) return;

  let val = parseFloat(input.value) || 0;
  val = Math.max(0, val + delta);
  input.value = val;

  updateHabitCardProgress(habitId, val);
  debouncedSaveHabit(habitId, val);
}

function toggleBooleanHabit(habitId) {
  const btn = document.getElementById(`habit-val-${habitId}`);
  if (!btn) return;

  const isActive = btn.classList.toggle("active");
  const val = isActive ? 1 : 0;
  btn.textContent = isActive ? "Done" : "Not done";

  updateHabitCardProgress(habitId, val);
  debouncedSaveHabit(habitId, val);
}

function updateHabitCardProgress(habitId, value) {
  const card = document.querySelector(`.habit-card[data-habit-id="${habitId}"]`);
  if (!card) return;

  const fill = card.querySelector(".habit-progress-fill");
  const pctEl = card.querySelector(".habit-progress-pct");

  // Get goal from the card's goal text or fallback
  const goalText = card.querySelector(".habit-card-goal");
  let goal = 1;
  if (goalText) {
    const match = goalText.textContent.match(/^(\d+)/);
    if (match) goal = parseFloat(match[1]);
  }

  const pct = Math.min(Math.round((value / goal) * 100), 100);
  if (fill) fill.style.width = `${pct}%`;
  if (pctEl) pctEl.textContent = `${pct}%`;

  if (value >= goal) {
    card.classList.add("completed");
  } else {
    card.classList.remove("completed");
  }
}

// ============================================================
//  DEBOUNCED HABIT SAVE
// ============================================================
function debouncedSaveHabit(habitId, value) {
  if (habitSaveTimers[habitId]) clearTimeout(habitSaveTimers[habitId]);

  habitSaveTimers[habitId] = setTimeout(async () => {
    try {
      const res = await fetch("/api/save-habit-value", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          habit_id: habitId,
          plan_date: currentDate,
          value: value
        })
      });

      if (!res.ok) throw new Error("Save failed");
      if (typeof showToast === "function") showToast("Habit saved", "success");

      // Refresh completion ring
      const healthRes = await fetch(`/api/v2/daily-health?date=${currentDate}`);
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        updateRing(healthData.habit_percent || 0);
        updateHealthScore(healthData);
      }
    } catch (err) {
      console.error("saveHabitValue error:", err);
      if (typeof showToast === "function") showToast("Failed to save habit", "error");
    }
  }, 500);
}

// ============================================================
//  WEEKLY DOTS
// ============================================================
async function loadWeeklyDots(habitId) {
  try {
    const res = await fetch(`/api/v2/habit-weekly/${habitId}`);
    if (!res.ok) return;
    const values = await res.json();

    const container = document.querySelector(`.habit-weekly-dots[data-habit-id="${habitId}"]`);
    if (!container) return;
    container.innerHTML = "";

    const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];
    values.forEach((val, i) => {
      const dot = document.createElement("span");
      dot.className = "weekly-dot";
      dot.title = dayLabels[i] || "";

      if (val >= 100) {
        dot.classList.add("dot-full");
      } else if (val > 0) {
        dot.classList.add("dot-partial");
      } else {
        dot.classList.add("dot-empty");
      }

      container.appendChild(dot);
    });
  } catch (err) {
    console.error("loadWeeklyDots error:", err);
  }
}

// ============================================================
//  HEALTH METRICS SAVE
// ============================================================
function autoSaveHealth() {
  if (saveHealthTimer) clearTimeout(saveHealthTimer);
  saveHealthTimer = setTimeout(() => saveHealth(), 1500);
}

async function saveHealth() {
  const weightEl = document.getElementById("health-weight");
  const heightEl = document.getElementById("health-height");
  const moodEl = document.getElementById("health-mood");
  const energyEl = document.getElementById("health-energy");
  const notesEl = document.getElementById("health-notes");

  const payload = {
    plan_date: currentDate,
    weight: weightEl ? parseFloat(weightEl.value) || null : null,
    height: heightEl ? parseFloat(heightEl.value) || null : null,
    mood: moodEl ? moodEl.value : "neutral",
    energy_level: energyEl ? parseInt(energyEl.value) || 5 : 5,
    notes: notesEl ? notesEl.value : ""
  };

  try {
    const res = await fetch("/api/v2/daily-health", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Save failed");
    if (typeof showToast === "function") showToast("Health data saved", "success");

    calculateBMI();

    // Refresh score
    const healthRes = await fetch(`/api/v2/daily-health?date=${currentDate}`);
    if (healthRes.ok) {
      const data = await healthRes.json();
      updateHealthScore(data);
    }
  } catch (err) {
    console.error("saveHealth error:", err);
    if (typeof showToast === "function") showToast("Failed to save health data", "error");
  }
}

// ============================================================
//  BMI CALCULATION
// ============================================================
function calculateBMI() {
  const weightEl = document.getElementById("health-weight");
  const heightEl = document.getElementById("health-height");
  const bmiEl = document.getElementById("bmi-display");
  if (!bmiEl) return;

  const weight = weightEl ? parseFloat(weightEl.value) : 0;
  const height = heightEl ? parseFloat(heightEl.value) : 0;

  if (!weight || !height || height === 0) {
    bmiEl.textContent = "--";
    bmiEl.className = "bmi-display";
    return;
  }

  const heightM = height / 100;
  const bmi = weight / (heightM * heightM);
  const rounded = bmi.toFixed(1);

  bmiEl.textContent = rounded;
  bmiEl.className = "bmi-display";

  if (bmi < 18.5) {
    bmiEl.classList.add("bmi-under");
  } else if (bmi < 25) {
    bmiEl.classList.add("bmi-normal");
  } else if (bmi < 30) {
    bmiEl.classList.add("bmi-over");
  } else {
    bmiEl.classList.add("bmi-obese");
  }
}

// ============================================================
//  ENERGY LABEL
// ============================================================
function updateEnergyLabel() {
  const energyEl = document.getElementById("health-energy");
  const labelEl = document.getElementById("energy-label");
  if (!energyEl || !labelEl) return;

  const val = parseInt(energyEl.value) || 5;
  const labels = {
    1: "Exhausted", 2: "Very Low", 3: "Low", 4: "Below Avg",
    5: "Average", 6: "Above Avg", 7: "Good", 8: "High",
    9: "Very High", 10: "Peak"
  };
  labelEl.textContent = labels[val] || `${val}/10`;
}

// ============================================================
//  HABIT SHEET (ADD / EDIT MODAL)
// ============================================================
function openHabitSheet() {
  const sheet = document.getElementById("habit-sheet");
  if (!sheet) return;

  sheet.classList.remove("hidden");
  sheet.dataset.editId = "";

  // Clear fields
  const nameEl = document.getElementById("sheet-name");
  const unitEl = document.getElementById("sheet-unit");
  const goalEl = document.getElementById("sheet-goal");
  const startEl = document.getElementById("sheet-start");
  const titleEl = document.getElementById("sheet-title");

  if (nameEl) nameEl.value = "";
  if (unitEl) unitEl.value = "";
  if (goalEl) goalEl.value = "";
  if (startEl) startEl.value = getISTDate();
  if (titleEl) titleEl.textContent = "Add Habit";

  setHabitType("number");
}

function closeHabitSheet() {
  const sheet = document.getElementById("habit-sheet");
  if (sheet) sheet.classList.add("hidden");
}

function setHabitType(type) {
  const sheet = document.getElementById("habit-sheet");
  if (!sheet) return;

  sheet.dataset.habitType = type;

  // Toggle active state on type buttons
  document.querySelectorAll(".type-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.type === type);
  });

  // Show/hide unit+goal row for boolean habits
  const unitGoalRow = document.getElementById("sheet-unit")?.closest(".sheet-row");

  if (type === "boolean") {
    if (unitGoalRow) unitGoalRow.style.display = "none";
  } else {
    if (unitGoalRow) unitGoalRow.style.display = "";
  }
}

async function submitHabitSheet() {
  const sheet = document.getElementById("habit-sheet");
  if (!sheet) return;

  const editId = sheet.dataset.editId;
  const habitType = sheet.dataset.habitType || "number";

  const name = document.getElementById("sheet-name")?.value?.trim();
  const unit = document.getElementById("sheet-unit")?.value?.trim() || "";
  const goal = parseFloat(document.getElementById("sheet-goal")?.value) || (habitType === "boolean" ? 1 : 0);
  const startDate = document.getElementById("sheet-start")?.value || getISTDate();

  if (!name) {
    if (typeof showToast === "function") showToast("Habit name is required", "error");
    return;
  }

  try {
    let res;
    if (editId) {
      // Edit existing habit
      res = await fetch(`/api/habits/${editId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, unit, goal })
      });
    } else {
      // Add new habit
      res = await fetch("/api/habits/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          unit: habitType === "boolean" ? "boolean" : unit,
          goal: habitType === "boolean" ? 1 : goal,
          start_date: startDate,
          habit_type: habitType
        })
      });
    }

    if (!res.ok) throw new Error("Save failed");

    closeHabitSheet();
    if (typeof showToast === "function") showToast(editId ? "Habit updated" : "Habit added", "success");
    loadHealth(currentDate);
  } catch (err) {
    console.error("submitHabitSheet error:", err);
    if (typeof showToast === "function") showToast("Failed to save habit", "error");
  }
}

async function editHabit(id) {
  try {
    const res = await fetch(`/api/habits/${id}`);
    if (!res.ok) throw new Error("Failed to fetch habit");
    const habit = await res.json();

    const sheet = document.getElementById("habit-sheet");
    if (!sheet) return;

    sheet.classList.remove("hidden");
    sheet.dataset.editId = id;

    const titleEl = document.getElementById("sheet-title");
    const nameEl = document.getElementById("sheet-name");
    const unitEl = document.getElementById("sheet-unit");
    const goalEl = document.getElementById("sheet-goal");
    const startEl = document.getElementById("sheet-start");

    if (titleEl) titleEl.textContent = "Edit Habit";
    if (nameEl) nameEl.value = habit.name || "";
    if (unitEl) unitEl.value = habit.unit || "";
    if (goalEl) goalEl.value = habit.goal || "";
    if (startEl) startEl.value = habit.start_date || getISTDate();

    setHabitType(habit.habit_type === "boolean" ? "boolean" : "number");
  } catch (err) {
    console.error("editHabit error:", err);
    if (typeof showToast === "function") showToast("Failed to load habit", "error");
  }
}

function deleteHabit(id) {
  // Remove card from DOM immediately (optimistic)
  const card = document.querySelector(`.habit-card[data-habit-id="${id}"]`);
  if (card) card.remove();

  // Show undo toast
  let undone = false;
  if (typeof showToast === "function") {
    showToast("Habit deleted. Undo?", "success");
  }

  // Create an undo container
  const undoToast = document.createElement("div");
  undoToast.className = "undo-toast";
  undoToast.innerHTML = `
    <span>Habit deleted</span>
    <button class="undo-btn" id="undo-delete-${id}">Undo</button>
  `;
  document.body.appendChild(undoToast);
  requestAnimationFrame(() => undoToast.classList.add("show"));

  const undoBtn = document.getElementById(`undo-delete-${id}`);
  if (undoBtn) {
    undoBtn.addEventListener("click", async () => {
      undone = true;
      undoToast.classList.remove("show");
      setTimeout(() => undoToast.remove(), 300);

      try {
        await fetch("/api/habits/restore", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ habit_id: id })
        });
        loadHealth(currentDate);
        if (typeof showToast === "function") showToast("Habit restored", "success");
      } catch (err) {
        console.error("restoreHabit error:", err);
      }
    });
  }

  // Perform delete after 4 seconds if not undone
  setTimeout(async () => {
    undoToast.classList.remove("show");
    setTimeout(() => undoToast.remove(), 300);

    if (undone) return;

    try {
      await fetch("/api/habits/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habit_id: id })
      });
    } catch (err) {
      console.error("deleteHabit error:", err);
      if (typeof showToast === "function") showToast("Failed to delete habit", "error");
      loadHealth(currentDate);
    }
  }, 4000);
}

// ============================================================
//  UTILITY
// ============================================================
function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

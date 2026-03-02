let lastHealthPayload = "";
async function loadHealth(date) {

  const res = await fetch(`/api/v2/daily-health?date=${date}`);
  const data = await res.json();

  // ------------------------
  // Basic health fields
  // ------------------------
  const weightEl = document.getElementById("weight");
  const heightEl = document.getElementById("height");
  const energyEl = document.getElementById("energy");
  const moodEl = document.getElementById("mood");
  const notesEl = document.getElementById("health-notes");

  if (weightEl) weightEl.value = data.weight || "";
  if (heightEl) heightEl.value = data.height || "";
  if (energyEl) energyEl.value = data.energy_level || 5;
  if (moodEl) moodEl.value = data.mood || "😊 Happy";
  if (notesEl) notesEl.value = data.notes || "";

  // ------------------------
  // Habits
  // ------------------------
  if (data.habits) {
    renderHabits(data.habits);
  }

  updateHabitCircle(data.habit_percent || 0);
  updateHealthScore(data);
  calculateBMI();

  // ------------------------
  // Streak
  // ------------------------
  const badge = document.getElementById("streak-badge");
  if (badge) {
    badge.innerText = `🔥 ${data.streak || 0} day streak`;
  }
  // ------------------------
  // Weight Trend Graph
  // ------------------------
  if (data.weight_trend) {
    renderWeightTrend(data.weight_trend);
    renderWeightSparkline(data.weight_trend);
  }
  if (data.weight_delta !== undefined) {
    const deltaEl = document.getElementById("weightDelta");

    if (!deltaEl) {
      console.warn("weightDelta element missing");
    } else {

      if (data.weight_delta > 0) {
        deltaEl.className = "weight-delta up";
        deltaEl.innerText = `↑ ${data.weight_delta.toFixed(1)} kg`;
      } else if (data.weight_delta < 0) {
        deltaEl.className = "weight-delta down";
        deltaEl.innerText = `↓ ${Math.abs(data.weight_delta)} kg from yesterday`;
      } else {
        deltaEl.className = "weight-delta";
        deltaEl.innerText = `No change from yesterday`;
      }
    }
  }
  // ------------------------
  // Chart update
  // ------------------------
  if (
    window.healthChart &&
    window.healthChart.data &&
    window.healthChart.data.datasets &&
    window.healthChart.data.datasets.length > 2
  ) {
    window.healthChart.data.datasets[2].data = [data.habit_percent || 0];
    window.healthChart.update();
  }

  // ------------------------
  // Weekly + Monthly analytics (parallel)
  // ------------------------


}
function renderHabits(habits) {

  const container = document.getElementById("habitContainer");
  if (!container) return;

  container.innerHTML = "";

  habits.forEach(h => {

    const value = h.value ?? "";
    const goal = h.goal ?? 0;
    const percent = goal > 0
      ? Math.min(100, Math.round((value / goal) * 100))
      : 0;

    container.innerHTML += `
      <div class="habit-item" data-id="${h.id}" data-goal="${goal}">

        <div class="habit-header habit-tap" data-id="${h.id}">
          <div>
            <div class="habit-title">${h.name}</div>
          </div>

          <div class="habit-actions">
            <button onclick="event.stopPropagation(); editHabit('${h.id}')">✏️</button>
            <button onclick="event.stopPropagation(); showHabitChart('${h.id}')">📈</button>
            <button onclick="event.stopPropagation(); deleteHabit('${h.id}')">🗑</button>
          </div>
        </div>

        <div class="habit-entry-block">
          <div class="entry-label">Today</div>

          ${h.habit_type === "boolean"
        ? `
              <label class="switch">
                <input type="checkbox"
                       data-id="${h.id}"
                       class="habit-boolean"
                       ${value == 1 ? "checked" : ""}>
                <span class="slider"></span>
              </label>
            `
        : `
              <input type="number"
                     step="1"
                     value="${value}"
                     data-id="${h.id}"
                     class="habit-input"
                     placeholder="Enter value">
            `
      }
        </div>

        <div class="habit-progress">
          <div class="habit-progress-fill"
               style="width: ${percent}%"></div>
        </div>

        <div class="habit-goal-display">
          <span class="goal-text">Goal: ${goal} ${h.unit}</span>
          <span class="goal-percent">${percent}%</span>
        </div>

      </div>
    `;
  });

  wireHabitInputs();
  wireBooleanHabits();
}
function updateHabitCircle(percent) {

  const bar = document.getElementById("habitPercentBar");
  const text = document.getElementById("habitPercentText");

  if (bar) bar.style.width = percent + "%";
  if (text) text.innerText = percent + "%";
}
function openHabitModal() {
  const modal = document.getElementById("habitModal");
  modal.classList.add("active");

  setTimeout(() => {
    document.getElementById("modalHabitName").focus();
  }, 100);
}

function closeHabitModal() {
  document.getElementById("habitModal").classList.remove("active");
}

async function submitHabitModal() {

  const name = document.getElementById("modalHabitName").value.trim();
  const unit = document.getElementById("modalHabitUnit").value.trim();
  const goal = parseFloat(document.getElementById("modalHabitGoal").value);

  if (!name || !unit || !goal) {
    showToast("All fields are required", "error");
    return;
  }

  const res = await fetch("/api/habits/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, unit, goal })
  });
  if (res.status === 409) {
    showToast("Habit already exists", "error");
    return;
  }
  if (!res.ok) {
    showToast("Failed to add habit", "error");
    return;
  }

  const newHabit = await res.json();

  appendHabitToDOM(newHabit);

  showToast("Habit added", "success");

  // Clear inputs
  document.getElementById("modalHabitName").value = "";
  document.getElementById("modalHabitUnit").value = "";
  document.getElementById("modalHabitGoal").value = "";

  closeHabitModal();
}

function appendHabitToDOM(h) {

  const container = document.getElementById("habitContainer");
  if (!container) return;

  const goal = h.goal ?? 0;
  const value = h.value ?? "";
  const percent = goal > 0
    ? Math.min(100, Math.round((value / goal) * 100))
    : 0;

  const div = document.createElement("div");
  div.className = "habit-item";
  div.dataset.id = h.id;
  div.dataset.goal = goal; // ✅ MUST BE HERE

  div.innerHTML = `
    <div class="habit-header habit-tap" data-id="${h.id}">
      <div>
        <div class="habit-title">${h.name}</div>
      </div>

      <div class="habit-actions">
        <button onclick="event.stopPropagation(); showHabitChart('${h.id}')">📈</button>
        <button onclick="event.stopPropagation(); deleteHabit('${h.id}')">🗑</button>
      </div>
    </div>

    <div class="habit-entry-block">
      <div class="entry-label">Today</div>

      <input type="number"
             step="1"
             value="${value}"
             data-id="${h.id}"
             class="habit-input"
             placeholder="Enter value">
    </div>

    <div class="habit-progress">
      <div class="habit-progress-fill"
           style="width: ${percent}%"></div>
    </div>

    <div class="habit-goal-display">
      <span class="goal-text">Goal: ${goal} ${h.unit}</span>
      <span class="goal-percent">${percent}%</span>
    </div>
   
  `;

  container.appendChild(div);

  wireHabitInputs();

}
async function saveHealth() {

  const payload = {
    plan_date: document.getElementById("health-date").value,
    weight: document.getElementById("weight").value,
    height: document.getElementById("height").value,
    mood: document.getElementById("mood").value,
    energy_level: document.getElementById("energy").value,
    notes: document.getElementById("health-notes").value
  };

  const payloadString = JSON.stringify(payload);

  // 🚀 Prevent duplicate saves
  if (payloadString === lastHealthPayload) return;

  lastHealthPayload = payloadString;

  const res = await fetch("/api/v2/daily-health", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payloadString
  });

  if (!res.ok) {
    showToast("Save failed", "error");
    return;
  }

  updateHealthScore({
    habit_percent: parseInt(document.querySelector(".circle-text")?.innerText) || 0,
    energy_level: document.getElementById("energy").value,
    mood: document.getElementById("mood").value,
    streak: 0 // keep current, or store globally if you want
  });

  calculateBMI();
  showSaveToast();
}
function wireHabitInputs() {

  document.querySelectorAll(".habit-input").forEach(input => {

    if (input.dataset.bound) return;
    input.dataset.bound = "1";

    let timeout;

    input.addEventListener("input", () => {

      clearTimeout(timeout);

      timeout = setTimeout(async () => {

        const date = document.getElementById("health-date").value;
        const value = parseFloat(input.value) || 0;

        await fetch("/api/save-habit-value", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            habit_id: input.dataset.id,
            plan_date: date,
            value: value
          })
        });

        showSaveToast();
        recalcHabitPercent();

        // 🔥 Update progress visually
        const item = input.closest(".habit-item");
        if (!item) return;

        const goal = parseFloat(item.dataset.goal) || 0;
        const percentEl = item.querySelector(".goal-percent");
        const bar = item.querySelector(".habit-progress-fill");

        const percent = goal > 0
          ? Math.min(100, Math.round((value / goal) * 100))
          : 0;

        if (percentEl) {
          percentEl.innerText = percent + "%";
        }

        if (bar) {
          bar.style.width = percent + "%";
          bar.classList.toggle("completed", percent >= 100);
        }

        // 🔥 Subtle card glow
        item.classList.toggle("completed", percent >= 100);

      }, 500);

    });

  });

}
function wireBooleanHabits() {

  document.querySelectorAll(".habit-boolean").forEach(input => {

    if (input.dataset.bound) return;
    input.dataset.bound = "1";

    input.addEventListener("change", async () => {

      const date = document.getElementById("health-date").value;
      const value = input.checked ? 1 : 0;

      await fetch("/api/save-habit-value", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          habit_id: input.dataset.id,
          plan_date: date,
          value: value
        })
      });

      showSaveToast();
      recalcHabitPercent();

      // 🔥 Update progress visually
      const item = input.closest(".habit-item");
      if (!item) return;

      const bar = item.querySelector(".habit-progress-fill");
      const percentEl = item.querySelector(".goal-percent");
      const percent = input.checked ? 100 : 0;

      if (percentEl) percentEl.innerText = percent + "%";

      if (bar) {
        bar.style.width = percent + "%";
        bar.classList.toggle("completed", percent >= 100);
      }

      item.classList.toggle("completed", percent >= 100);

    });

  });

}

function recalcHabitPercent() {

  const items = document.querySelectorAll(".habit-item");

  let total = items.length;
  let completed = 0;

  items.forEach(item => {

    const checkbox = item.querySelector(".habit-boolean");
    const input = item.querySelector(".habit-input");
    const goalText = item.querySelector(".habit-goal-display");

    if (checkbox) {
      if (checkbox.checked) completed++;
      return;
    }

    if (input && goalText) {
      const value = parseFloat(input.value || 0);
      const goal = parseFloat(item.dataset.goal) || 0;

      if (goal > 0 && value >= goal) completed++;
    }

  });

  const percent = total
    ? Math.round((completed / total) * 100)
    : 0;

  updateHabitCircle(percent);
}
function showSavedFeedback() {
  const btn = document.getElementById("saveBtn");
  if (!btn) return;

  btn.innerText = "✓ Saved";
  btn.style.background = "#16a34a";

  setTimeout(() => {
    btn.innerText = "Save";
    btn.style.background = "#2563eb";
  }, 1500);
}

document.addEventListener("DOMContentLoaded", async () => {

  const dateInput = document.getElementById("health-date");
  if (!dateInput) return;

  ["weight", "height", "mood", "energy", "health-notes"].forEach(id => {

    const el = document.getElementById(id);
    if (!el || el.dataset.bound) return;

    el.dataset.bound = "1";

    el.addEventListener("input", autoSaveHealth);
    el.addEventListener("blur", autoSaveHealth);

  });
  ["weight", "height"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", calculateBMI);
  });
  const today = new Date().toLocaleDateString("en-CA", {
    timeZone: "Asia/Kolkata"
  });

  dateInput.value = today;

  await loadHealth(today);
  loadAnalytics(); // 🔥 call once only

  dateInput.addEventListener("change", async () => {
    await loadHealth(dateInput.value);
  });

  // 🔥 Load heatmap once
  fetch("/api/v2/heatmap")
    .then(res => res.json())
    .then(data => {

      const container = document.getElementById("heatmap");
      if (!container) return;

      container.innerHTML = "";

      Object.keys(data).forEach(day => {

        const div = document.createElement("div");
        div.className = "heat-cell";

        div.style.background =
          data[day] > 75 ? "#16a34a" :
            data[day] > 40 ? "#4ade80" :
              data[day] > 10 ? "#86efac" :
                "#e5e7eb";

        container.appendChild(div);
      });
    });
  // 🔥 Enable Drag Reorder
  const container = document.getElementById("habitContainer");

  if (container && typeof Sortable !== "undefined") {
    new Sortable(container, {
      animation: 150,
      handle: ".habit-drag",
      onEnd: async function () {

        const items = document.querySelectorAll(".habit-item");

        await Promise.all(
          Array.from(items).map((item, i) =>
            fetch("/api/habits/reorder", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                habit_id: item.dataset.id,
                position: i
              })
            })
          )
        );

      }
    });
  }
  document.querySelectorAll(".emoji-picker .emoji").forEach(el => {
    el.addEventListener("click", () => {

      selectedEmoji = el.textContent;

      document.getElementById("sheetHabitName").value =
        selectedEmoji + " ";

    });
  });
  const addBtn = document.getElementById("addHabitBtn");
  if (addBtn) {
    addBtn.addEventListener("click", openHabitSheet);
  }
}); // ✅ THIS WAS MISSING
async function deleteHabit(id) {

  // Optimistically remove from UI immediately
  const item = document.querySelector(`.habit-item[data-id="${id}"]`);
  if (item) item.remove();

  showUndoDeleteToast(id);

  // Soft delete in backend
  await fetch("/api/habits/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ habit_id: id })
  });
}
function showUndoDeleteToast(id) {

  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `
    Habit deleted
    <button class="undo-btn">Undo</button>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  const timer = setTimeout(() => {
    toast.remove();
  }, 4000);

  toast.querySelector(".undo-btn").onclick = async () => {
    clearTimeout(timer);

    await fetch("/api/habits/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habit_id: id })
    });

    toast.remove();
    loadHealth(document.getElementById("health-date").value);
  };
}
async function showHabitChart(id) {

  const res = await fetch(`/api/v2/habit-weekly/${id}`);
  const data = await res.json();

  const ctx = document.getElementById("healthChart");
  if (!ctx) return;

  if (window.habitChartInstance) {
    window.habitChartInstance.destroy();
  }

  window.habitChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
      datasets: [{
        label: "Weekly Progress",
        data: data,
        tension: 0.3
      }]
    }
  });
}
function toggleEdit(id) {
  const panel = document.getElementById("edit-" + id);
  panel.style.display =
    panel.style.display === "flex" ? "none" : "flex";
}

document.addEventListener("focus", function (e) {
  if (
    e.target.classList.contains("habit-input") ||
    e.target.classList.contains("habit-name-edit") ||
    e.target.classList.contains("habit-unit-edit") ||
    e.target.classList.contains("habit-goal-edit")
  ) {
    e.target.select();
  }
}, true);

let weightChart = null;

function renderWeightTrend(data) {

  if (!data || data.length === 0) return;

  const ctx = document.getElementById("weightChart");

  if (!ctx) return;

  // destroy previous chart
  if (weightChart) {
    weightChart.destroy();
  }

  weightChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map(d => d.date.slice(5)),
      datasets: [{
        data: data.map(d => d.weight ?? null),
        tension: 0.4,
        borderColor: "#2563eb",
        borderWidth: 2,
        pointRadius: 3,
        fill: false
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { display: false },
        x: { display: false }
      }
    }
  });

}
let sparklineChart = null;

function renderWeightSparkline(data) {

  if (!data || data.length === 0) return;

  const ctx = document.getElementById("weightSparkline");
  if (!ctx) return;

  if (sparklineChart) sparklineChart.destroy();

  sparklineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map(d => ""),
      datasets: [{
        data: data.map(d => d.weight ?? null),
        borderColor: "#16a34a",
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 0,
        fill: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { display: false }
      },
      animation: {
        duration: 800
      }
    }
  });
}
document.addEventListener("keydown", function (e) {

  if (e.target.classList.contains("habit-goal-edit") && e.key === "Enter") {

    const item = e.target.closest(".habit-item");
    const entry = item.querySelector(".habit-input");

    if (entry) {
      entry.focus();
      entry.select();
    }

  }

});

async function quickAdd(id) {

  const item = document.querySelector(`.habit-item[data-id="${id}"]`);
  if (!item) return;

  const input = item.querySelector(".habit-input");

  let current = parseFloat(input.value || 0);
  const goalText = item.querySelector(".habit-goal-display")?.innerText || "";
  const unitMatch = goalText.match(/Goal:\s*[\d.]+\s*(.*)/);
  const unit = unitMatch ? unitMatch[1] : "";

  const step = getStepFromUnit(unit);

  current = Math.round((current + step) * 100) / 100;

  input.value = current;

  // trigger autosave
  input.dispatchEvent(new Event("input"));

  // visual feedback
  item.classList.add("tap-flash");
  setTimeout(() => item.classList.remove("tap-flash"), 300);

}
function getStepFromUnit(unit) {

  if (!unit) return 1;

  unit = unit.toLowerCase();

  if (unit.includes("min")) return 5;
  if (unit.includes("hr")) return 0.5;
  if (unit.includes("step")) return 50;
  if (unit.includes("ml")) return 50;
  if (unit.includes("rs")) return 50;

  return 1;
}
function quickAdjust(id, direction) {

  const item = document.querySelector(`.habit-item[data-id="${id}"]`);
  if (!item) return;

  const input = item.querySelector(".habit-input");
  const goalText = item.querySelector(".habit-goal-display")?.innerText || "";
  const unitMatch = goalText.match(/Goal:\s*[\d.]+\s*(.*)/);
  const unit = unitMatch ? unitMatch[1] : "";

  let current = parseFloat(input.value || 0);

  const step = getStepFromUnit(unit);

  current = Math.round((current + step * direction) * 100) / 100;

  if (current < 0) current = 0;

  input.value = current;

  // trigger autosave
  input.dispatchEvent(new Event("input"));

  // visual feedback
  item.classList.add("tap-flash");
  setTimeout(() => item.classList.remove("tap-flash"), 250);
}
let healthSaveTimer;

function autoSaveHealth() {

  clearTimeout(healthSaveTimer);

  healthSaveTimer = setTimeout(() => {
    saveHealth();
  }, 1500); // save after user pauses 1.5s

}
function showToast(message, type = "info") {

  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type} `;
  toast.textContent = message;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  setTimeout(() => {
    toast.classList.remove("show");

    setTimeout(() => {
      toast.remove();
    }, 300);

  }, 2200);
}
function showSaveToast() {

  const toast = document.getElementById("saveToast");
  if (!toast) return;

  toast.classList.add("show");

  clearTimeout(toast.timer);

  toast.timer = setTimeout(() => {
    toast.classList.remove("show");
  }, 1200);

}

function updateHealthScore(data) {

  const habits = data.habit_percent || 0;
  const energy = data.energy_level || 5;
  const mood = data.mood || "Neutral";
  const streak = data.streak || 0;

  const habitScore = habits * 0.5;

  const energyScore = (energy / 10) * 15;

  const moodScore =
    mood.includes("Happy") ? 10 :
      mood.includes("Neutral") ? 6 :
        3;

  const streakScore = Math.min(streak * 1.5, 15);

  const weightScore = 10; // optional stability logic later

  const total =
    habitScore +
    energyScore +
    moodScore +
    streakScore +
    weightScore;

  const score = Math.round(total);

  renderHealthScore(score);

}
function renderHealthScore(score) {

  const number = document.getElementById("healthScoreNumber");
  const bar = document.getElementById("healthScoreBar");

  if (number) number.innerText = score;
  if (bar) bar.style.width = score + "%";
}
async function loadAnalytics() {
  try {

    const [weekly, month] = await Promise.all([
      fetch("/api/v2/weekly-health").then(r => r.json()),
      fetch("/api/v2/monthly-summary").then(r => r.json())
    ]);

    const avgEl = document.getElementById("weeklyAvg");
    if (avgEl) {
      avgEl.innerText = `7-day avg: ${weekly.weekly_avg}%`;
    }

    const bestEl = document.getElementById("bestHabit");
    if (bestEl) {
      bestEl.innerText =
        weekly.best_habit ? `🏆 Best: ${weekly.best_habit}` : "";
    }

    const monthlyEl = document.getElementById("monthlySummary");
    if (monthlyEl) {
      monthlyEl.innerHTML = `
        <p>Days tracked: ${month.days_tracked}</p>
        <p>Avg completion: ${month.avg_percent}%</p>
        <p>Weight change: ${month.weight_change} kg</p>
        <p>Avg energy: ${month.avg_energy}/10</p>
      `;
    }

  } catch (err) {
    console.warn("Analytics load failed", err);
  }
}
let selectedEmoji = "";
let selectedColor = "#2563eb";

function openHabitSheet() {
  document.getElementById("habitSheet").classList.add("active");
}

function closeHabitSheet() {

  const sheet = document.getElementById("habitSheet");

  sheet.classList.remove("active");

  document.getElementById("sheetHabitName").value = "";
  document.getElementById("sheetHabitUnit").value = "";
  document.getElementById("sheetHabitGoal").value = "";

  sheet.querySelector(".sheet-header h3").innerText = "New Habit";
  sheet.querySelector(".sheet-submit").innerText = "Add Habit";

  delete sheet.dataset.editId;
}

document.querySelectorAll(".color-dot").forEach(dot => {
  dot.style.background = dot.dataset.color;

  dot.addEventListener("click", () => {
    document.querySelectorAll(".color-dot").forEach(d => d.classList.remove("active"));
    dot.classList.add("active");
    selectedColor = dot.dataset.color;
  });
});
const unitInput = document.getElementById("sheetHabitUnit");

if (unitInput) {
  unitInput.addEventListener("input", function () {

    const unit = this.value.toLowerCase();
    const suggestions = document.getElementById("goalSuggestions");
    if (!suggestions) return;

    suggestions.innerHTML = "";

    let values = [];

    if (unit.includes("step")) values = [5000, 8000, 10000];
    if (unit.includes("min")) values = [15, 30, 45];
    if (unit.includes("ml")) values = [1500, 2000, 3000];
    if (unit.includes("hr")) values = [1, 2, 3];

    values.forEach(val => {
      const btn = document.createElement("button");
      btn.innerText = val;
      btn.onclick = () => {
        const goalInput = document.getElementById("sheetHabitGoal");
        if (goalInput) goalInput.value = val;
      };
      suggestions.appendChild(btn);
    });
  });
}


function calculateBMI() {
  const weight = parseFloat(document.getElementById("weight")?.value);
  const heightCm = parseFloat(document.getElementById("height")?.value);
  const bmiEl = document.getElementById("bmiValue");

  if (!bmiEl) return;

  if (!weight || !heightCm) {
    bmiEl.innerText = "BMI: --";
    bmiEl.style.color = "#6b7280";
    return;
  }

  const heightM = heightCm / 100;
  const bmi = weight / (heightM * heightM);
  const rounded = bmi.toFixed(1);

  let status = "";

  if (bmi < 18.5) {
    status = "Underweight";
    bmiEl.style.color = "#f59e0b";
  } else if (bmi < 25) {
    status = "Normal";
    bmiEl.style.color = "#16a34a";
  } else if (bmi < 30) {
    status = "Overweight";
    bmiEl.style.color = "#f97316";
  } else {
    status = "Obese";
    bmiEl.style.color = "#ef4444";
  }

  bmiEl.innerText = `BMI: ${rounded} (${status})`;
}
async function editHabit(id) {

  const res = await fetch(`/api/habits/${id}`);
  if (!res.ok) {
    showToast("Failed to load habit", "error");
    return;
  }

  const habit = await res.json();

  const sheet = document.getElementById("habitSheet");

  document.getElementById("sheetHabitName").value = habit.name;
  document.getElementById("sheetHabitUnit").value = habit.unit;
  document.getElementById("sheetHabitGoal").value = habit.goal;

  sheet.dataset.editId = id;

  sheet.querySelector(".sheet-header h3").innerText = "Edit Habit";
  sheet.querySelector(".sheet-submit").innerText = "Save Changes";

  sheet.classList.add("active");
}
async function submitHabitSheet() {

  const sheet = document.getElementById("habitSheet");
  const editId = sheet.dataset.editId;

  const name = document.getElementById("sheetHabitName").value.trim();
  const unit = document.getElementById("sheetHabitUnit").value.trim();
  const goal = parseFloat(document.getElementById("sheetHabitGoal").value);

  if (!name || !unit || !goal) {
    showToast("All fields required", "error");
    return;
  }

  const payload = {
    name,
    unit,
    goal,
    emoji: selectedEmoji,
    color: selectedColor
  };

  let res;

  if (editId) {
    res = await fetch(`/api/habits/${editId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    delete sheet.dataset.editId;
    showToast("Habit updated", "success");

  } else {
    res = await fetch(`/api/habits/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    showToast("Habit added", "success");
  }

  if (!res.ok) {
    showToast("Save failed", "error");
    return;
  }

  closeHabitSheet();
  await loadHealth(document.getElementById("health-date").value);
}

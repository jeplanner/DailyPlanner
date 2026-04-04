/* ============================================================
   Summary Dashboard — Charts + AI Recaps
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  if (typeof feather !== "undefined") feather.replace();

  if (VIEW === "weekly" && typeof WEEKLY_DATA !== "undefined") {
    renderActivityChart();
    renderCompletionChart();
  }
});

/* ══════════════════════════════════════
   WEEKLY CHARTS (Chart.js)
   ══════════════════════════════════════ */

function renderActivityChart() {
  const ctx = document.getElementById("activityChart");
  if (!ctx) return;

  const days = WEEKLY_DATA.days;
  const labels = [];
  const taskCounts = [];
  const doneCounts = [];
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Sort dates
  const sortedDates = Object.keys(days).sort();

  sortedDates.forEach(ds => {
    const d = new Date(ds + "T00:00:00");
    labels.push(dayNames[d.getDay()] + " " + d.getDate());
    const tasks = days[ds] || [];
    taskCounts.push(tasks.length);
    doneCounts.push(tasks.filter(t => t.done).length);
  });

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Total",
          data: taskCounts,
          backgroundColor: "rgba(37, 99, 235, 0.2)",
          borderColor: "rgba(37, 99, 235, 0.8)",
          borderWidth: 1.5,
          borderRadius: 4
        },
        {
          label: "Completed",
          data: doneCounts,
          backgroundColor: "rgba(16, 185, 129, 0.3)",
          borderColor: "rgba(16, 185, 129, 0.8)",
          borderWidth: 1.5,
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, padding: 16, font: { size: 11 } } }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 11 } }, grid: { color: "rgba(0,0,0,0.05)" } },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } }
      }
    }
  });
}

function renderCompletionChart() {
  const ctx = document.getElementById("completionChart");
  if (!ctx) return;

  const rate = WEEKLY_DATA.completion_rate;
  const remaining = Math.max(0, 100 - rate);

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Completed", "Remaining"],
      datasets: [{
        data: [rate, remaining],
        backgroundColor: ["#10b981", "#e5e7eb"],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "70%",
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    },
    plugins: [{
      id: "centerText",
      beforeDraw: function(chart) {
        const { width, height, ctx: c } = chart;
        c.save();
        c.font = "700 24px Inter, system-ui";
        c.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--sm-text") || "#1a1a2e";
        c.textAlign = "center";
        c.textBaseline = "middle";
        c.fillText(Math.round(rate) + "%", width / 2, height / 2);
        c.restore();
      }
    }]
  });
}

/* ══════════════════════════════════════
   AI RECAP GENERATION
   ══════════════════════════════════════ */

async function generateDailyRecap(dateStr) {
  const container = document.getElementById("ai-recap");
  if (!container) return;

  container.innerHTML = '<div class="ai-loading">Generating recap...</div>';

  try {
    // Build context from tasks
    const tasks = typeof DAILY_TASKS !== "undefined" ? DAILY_TASKS : [];
    const taskSummary = tasks.map(t =>
      `${t.time_label}: ${t.text}${t.done ? " (done)" : ""}`
    ).join("\n");

    const message = `Summarize this day (${dateStr}) in 3-4 short bullet points. What went well, what could improve, and one actionable tip for tomorrow.\n\nSchedule:\n${taskSummary || "No tasks scheduled."}`;

    const res = await fetch("/ai/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message })
    });

    if (!res.ok) throw new Error("AI unavailable");

    const data = await res.json();
    const text = data.response || data.summary || "No recap generated.";
    container.innerHTML = `<div class="ai-text">${escapeHtml(text)}</div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-msg">AI recap unavailable. Try again later.</div>`;
    console.warn("AI recap error:", e);
  }
}

async function generateWeeklyRecap() {
  const container = document.getElementById("ai-recap");
  if (!container) return;

  container.innerHTML = '<div class="ai-loading">Generating weekly recap...</div>';

  try {
    const data = typeof WEEKLY_DATA !== "undefined" ? WEEKLY_DATA : {};

    // Count tasks across the week
    let totalTasks = 0, doneTasks = 0;
    Object.values(data.days || {}).forEach(tasks => {
      totalTasks += tasks.length;
      doneTasks += tasks.filter(t => t.done).length;
    });

    const message = `Give a brief weekly productivity review (4-5 bullet points) with actionable advice for next week.

Stats:
- Focus hours: ${data.focused_hours || 0}h
- Completion: ${data.completion_rate || 0}%
- Habit consistency: ${data.habit_days || 0}/7 days
- Total tasks: ${totalTasks}, completed: ${doneTasks}
- Active days: ${Object.keys(data.days || {}).length}/7`;

    const res = await fetch("/ai/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message })
    });

    if (!res.ok) throw new Error("AI unavailable");

    const result = await res.json();
    const text = result.response || result.summary || "No recap generated.";
    container.innerHTML = `<div class="ai-text">${escapeHtml(text)}</div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-msg">AI recap unavailable. Try again later.</div>`;
    console.warn("AI recap error:", e);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/\n/g, "<br>");
}

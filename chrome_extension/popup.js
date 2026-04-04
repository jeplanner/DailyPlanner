const API_BASE = "https://dailyplanner-zus3.onrender.com";

let currentUrl = "";
let currentTitle = "";

// ── Load current tab info ──────────────────────────────────────────────────

chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  currentUrl   = tab.url   || "";
  currentTitle = tab.title || "";

  document.getElementById("page-title").textContent = currentTitle || currentUrl;
  document.getElementById("page-url").textContent   = currentUrl;
});

// ── Save ───────────────────────────────────────────────────────────────────

async function save() {
  const btn      = document.getElementById("btn-save");
  const statusEl = document.getElementById("status");
  const desc     = document.getElementById("desc").value.trim();

  btn.disabled    = true;
  statusEl.className = "status";
  statusEl.textContent = "Saving…";

  const result = await chrome.runtime.sendMessage({
    type: "SAVE",
    url: currentUrl,
    title: currentTitle,
    description: desc,
  });

  if (result.ok) {
    statusEl.textContent = `✓ Saved${result.category ? ` as "${result.category}"` : ""}`;
    statusEl.className = "status success";
    document.getElementById("btn-view").classList.add("show");
    document.getElementById("desc").value = "";
  } else if (result.error === "not_logged_in") {
    statusEl.textContent = "⚠ Not logged in — open your planner first.";
    statusEl.className = "status error";
    btn.disabled = false;
  } else {
    statusEl.textContent = "Error saving. Try again.";
    statusEl.className = "status error";
    btn.disabled = false;
  }
}

// ── Open inbox tab ─────────────────────────────────────────────────────────

function openInbox() {
  chrome.tabs.create({ url: `${API_BASE}/inbox` });
}

// ── Press Enter in textarea to save ───────────────────────────────────────

document.getElementById("desc").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    save();
  }
});

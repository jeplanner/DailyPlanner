const API_BASE = "https://dailyplanner-zus3.onrender.com";

// ── Context menu: right-click on page or link ──────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "Save page to Inbox",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "save-link",
    title: "Save link to Inbox",
    contexts: ["link"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const url = info.menuItemId === "save-link" ? info.linkUrl : tab.url;
  const title = info.menuItemId === "save-link" ? "" : (tab.title || "");
  saveToInbox(url, title, "");
});

// ── Message from popup ─────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "SAVE") {
    saveToInbox(msg.url, msg.title, msg.description)
      .then(result => sendResponse(result))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true; // keep channel open for async response
  }
});

// ── Core save function ─────────────────────────────────────────────────────

async function saveToInbox(url, title, description) {
  try {
    const res = await fetch(`${API_BASE}/api/inbox`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // sends session cookie
      body: JSON.stringify({ url, description }),
    });

    if (res.status === 302 || res.redirected) {
      return { ok: false, error: "not_logged_in" };
    }

    const data = await res.json();
    return { ok: data.success === true, category: data.category, error: data.error };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

/* DailyPlanner — PWA UX glue.
   Two responsibilities, both small:
     1. Capture beforeinstallprompt and expose a custom "Install app"
        button instead of relying on the browser's hidden menu item.
     2. Detect when a new service worker has installed and is waiting,
        and surface a "Reload to update" toast so users don't see stale
        UI for days.

   push.js is the file that actually registers the SW; we only attach
   listeners to the existing registration. */

(function () {
  "use strict";

  /* ───── install prompt ──────────────────────────────────────── */

  let deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    hideInstallButton();
    if (window.showToast) showToast("Installed — find DailyPlanner on your home screen", "success", 4000);
  });

  function showInstallButton() {
    if (document.getElementById("pwa-install-btn")) return;
    // Hide on iOS Safari (no install prompt event, install is via Share
    // sheet) and inside an already-installed PWA.
    if (window.matchMedia("(display-mode: standalone)").matches) return;
    if (navigator.standalone) return;

    const btn = document.createElement("button");
    btn.id = "pwa-install-btn";
    btn.type = "button";
    btn.textContent = "Install app";
    Object.assign(btn.style, {
      position: "fixed",
      right: "16px",
      bottom: "calc(16px + env(safe-area-inset-bottom))",
      zIndex: "9000",
      background: "#6366f1",
      color: "#fff",
      border: "0",
      borderRadius: "999px",
      padding: "10px 18px",
      fontSize: "14px",
      fontWeight: "600",
      fontFamily: "'Inter', system-ui, sans-serif",
      boxShadow: "0 8px 24px rgba(99,102,241,0.35)",
      cursor: "pointer",
    });
    btn.addEventListener("click", async () => {
      if (!deferredPrompt) return;
      btn.disabled = true;
      deferredPrompt.prompt();
      try { await deferredPrompt.userChoice; } catch (_) {}
      deferredPrompt = null;
      hideInstallButton();
    });
    document.body.appendChild(btn);
  }

  function hideInstallButton() {
    const btn = document.getElementById("pwa-install-btn");
    if (btn) btn.remove();
  }

  /* ───── SW update toast ─────────────────────────────────────── */

  if (!("serviceWorker" in navigator)) return;

  // push.js already calls register() on the load event. We just wait
  // for whatever registration exists and watch its update lifecycle.
  navigator.serviceWorker.ready.then((reg) => {
    if (!reg) return;

    // A waiting worker was present before this page loaded — prompt now.
    if (reg.waiting && navigator.serviceWorker.controller) {
      promptReload(reg.waiting);
    }

    reg.addEventListener("updatefound", () => {
      const sw = reg.installing;
      if (!sw) return;
      sw.addEventListener("statechange", () => {
        if (sw.state === "installed" && navigator.serviceWorker.controller) {
          promptReload(sw);
        }
      });
    });
  }).catch(() => { /* SW unsupported or registration failed — silent */ });

  // Once the new SW takes control, reload exactly once.
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (reloading) return;
    reloading = true;
    location.reload();
  });

  function promptReload(sw) {
    if (!window.showToast) {
      // Toast not loaded yet (race) — try again shortly.
      setTimeout(() => promptReload(sw), 500);
      return;
    }
    showToast("New version available", "info", 8000, {
      label: "Reload",
      onClick: () => sw.postMessage({ type: "SKIP_WAITING" }),
    });
  }

  /* ───── offline-queue status pill ───────────────────────────── */

  // Tiny indicator that appears in the bottom-left whenever there are
  // queued writes. Clicking it pokes the SW to retry. Hidden when the
  // queue is empty. Uses a fixed-position element so it doesn't require
  // any page-specific markup — works on every screen.
  function ensurePill() {
    let pill = document.getElementById("dp-queue-pill");
    if (pill) return pill;
    pill = document.createElement("button");
    pill.id = "dp-queue-pill";
    pill.type = "button";
    pill.title = "Click to retry now";
    Object.assign(pill.style, {
      position: "fixed",
      left: "16px",
      bottom: "calc(16px + env(safe-area-inset-bottom))",
      zIndex: "9000",
      background: "#f59e0b",
      color: "#fff",
      border: "0",
      borderRadius: "999px",
      padding: "8px 14px",
      fontSize: "13px",
      fontWeight: "600",
      fontFamily: "'Inter', system-ui, sans-serif",
      boxShadow: "0 6px 18px rgba(245,158,11,0.35)",
      cursor: "pointer",
      display: "none",
    });
    pill.addEventListener("click", () => {
      if (window.dpSync) window.dpSync.replay();
      if (window.showToast) showToast("Retrying queued writes…", "info", 2000);
    });
    document.body.appendChild(pill);
    return pill;
  }

  async function refreshPill() {
    if (!window.dpSync) return;
    const n = await window.dpSync.pendingCount();
    const pill = ensurePill();
    if (n > 0) {
      pill.textContent = n === 1
        ? "1 change pending"
        : `${n} changes pending`;
      pill.style.display = "";
      // Green-ish once we're back online — visual hint that a retry
      // is imminent (Background Sync) or possible (click the pill).
      pill.style.background = navigator.onLine ? "#22c55e" : "#f59e0b";
      pill.style.boxShadow  = navigator.onLine
        ? "0 6px 18px rgba(34,197,94,0.35)"
        : "0 6px 18px rgba(245,158,11,0.35)";
    } else {
      pill.style.display = "none";
    }
  }

  if (window.dpSync) {
    window.dpSync.onQueued(refreshPill);
    window.dpSync.onResult((r) => {
      refreshPill();
      if (!window.showToast) return;
      if (r.ok) showToast("Synced", "success", 1800);
      else      showToast(`Sync failed (${r.status})`, "error", 3500);
    });
  }
  window.addEventListener("online",  refreshPill);
  window.addEventListener("offline", refreshPill);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshPill();
  });
  refreshPill();
})();

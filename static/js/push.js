/* DailyPlanner — Web Push client helpers (exported as window.ClPush).
   Handles service-worker registration, subscribe / unsubscribe, and
   syncing the subscription to the server. */
(function () {
  const SW_PATH = "/service-worker.js";

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
    return out;
  }

  async function getRegistration() {
    if (!("serviceWorker" in navigator)) return null;
    const reg = await navigator.serviceWorker.getRegistration();
    if (reg) return reg;
    return navigator.serviceWorker.register(SW_PATH, { scope: "/" });
  }

  async function currentSubscription() {
    const reg = await getRegistration();
    if (!reg) return null;
    return reg.pushManager.getSubscription();
  }

  async function fetchVapidKey() {
    const res = await fetch("/api/push/vapid-public-key", { credentials: "same-origin" });
    if (!res.ok) throw new Error("Could not fetch VAPID key");
    const { key } = await res.json();
    return key;
  }

  async function subscribe() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      throw new Error("This browser does not support Web Push.");
    }
    const perm = await Notification.requestPermission();
    if (perm !== "granted") throw new Error("Notifications permission denied.");

    const reg = await getRegistration();
    const vapid = await fetchVapidKey();

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid),
      });
    }

    await fetch("/api/push/subscribe", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: sub.toJSON(), user_agent: navigator.userAgent }),
    });
    return sub;
  }

  async function unsubscribe() {
    const sub = await currentSubscription();
    if (!sub) return;
    await fetch("/api/push/unsubscribe", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: sub.endpoint }),
    });
    await sub.unsubscribe();
  }

  async function sendTest() {
    const res = await fetch("/api/push/test", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Test failed: HTTP " + res.status);
    return res.json();
  }

  // ── UI wiring used by the checklist page ─────────
  async function init({ statusEl, statusOkEl, enableBtn, disableBtn, testBtn }) {
    const supported = "serviceWorker" in navigator && "PushManager" in window;

    async function refresh() {
      if (!supported) {
        statusEl.hidden = false;
        statusEl.querySelector(".cl-push-text strong").textContent =
          "This browser does not support Web Push.";
        enableBtn.hidden = true;
        return;
      }
      const sub = await currentSubscription();
      const on = Boolean(sub) && Notification.permission === "granted";
      statusEl.hidden = on;
      statusOkEl.hidden = !on;

      /* SELF-HEAL THE SERVER'S COPY.
         This used to check only whether the BROWSER holds a subscription,
         and reported "notifications are on" whenever it did. But the server
         marks a row is_active=false the moment a send comes back 404/410,
         and the browser is not told — so the two drift apart and the UI
         confidently says on while nothing will ever be delivered.

         Found in live data: six subscriptions for the same Android phone,
         every one inactive, the newest already a month old. Checklist
         reminders had not been arriving at all, which is the likeliest
         reason nothing on that checklist had been ticked in four months.

         Re-registering is idempotent — /api/push/subscribe upserts on the
         endpoint and sets is_active=true — so doing it on every load is
         cheap and repairs the drift without the user knowing there was any. */
      if (on) {
        try {
          await fetch("/api/push/subscribe", {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": document.querySelector('meta[name=csrf-token]')?.content || "",
            },
            // Same shape subscribe() sends — the server reads
            // data["subscription"], so a flat body is a 400.
            body: JSON.stringify({
              subscription: sub.toJSON(),
              user_agent: navigator.userAgent,
            }),
          });
        } catch (_) {
          /* Offline, or the endpoint is unhappy. The next load tries again;
             there is nothing useful to tell the user here. */
        }
      }
    }

    enableBtn?.addEventListener("click", async () => {
      enableBtn.disabled = true;
      try {
        await subscribe();
        await refresh();
      } catch (err) {
        alert(err.message || "Could not enable notifications.");
      } finally {
        enableBtn.disabled = false;
      }
    });

    disableBtn?.addEventListener("click", async () => {
      try { await unsubscribe(); } catch (_) { /* noop */ }
      await refresh();
    });

    testBtn?.addEventListener("click", async () => {
      testBtn.disabled = true;
      try {
        const r = await sendTest();
        if (!r.sent) alert("No active device subscriptions were reachable.");
      } catch (err) {
        alert(err.message);
      } finally {
        testBtn.disabled = false;
      }
    });

    await refresh();
  }

  // Registers the SW on every page load (so offline/push infra is warm).
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register(SW_PATH, { scope: "/" }).catch(() => {});
    });
  }

  window.ClPush = { init, subscribe, unsubscribe, currentSubscription, sendTest };
})();

/* DailyPlanner — service worker.
   Responsibilities:
     1. Receive Web Push events and display a notification.
     2. On notification click, focus an existing window or open a new
        one at the payload URL. */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_) {
    payload = { title: "DailyPlanner", body: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "DailyPlanner";
  const options = {
    body: payload.body || "",
    icon: payload.icon || "/static/icons/icon.svg",
    badge: payload.badge || "/static/icons/icon.svg",
    tag: payload.tag || "dailyplanner",
    renotify: true,
    // Keep on screen until the user taps/dismisses — otherwise Android
    // auto-hides after a few seconds.
    requireInteraction: true,
    // Explicit vibration pattern so phones on the default channel
    // importance still rumble.
    vibrate: [200, 100, 200],
    // Force non-silent so OS playback of the channel's sound triggers.
    silent: false,
    data: { url: payload.url || "/checklist" },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/checklist";

  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });

    // Prefer an existing window on the same origin. If its URL already
    // matches the notification target, just focus it; otherwise navigate
    // it to the target so we don't stack up duplicate tabs.
    const sameOrigin = all.filter((c) => {
      try { return new URL(c.url).origin === self.location.origin; }
      catch (_) { return false; }
    });

    if (sameOrigin.length) {
      const exact = sameOrigin.find((c) => c.url.includes(url));
      const target = exact || sameOrigin[0];
      if ("focus" in target) {
        try {
          if (!exact && "navigate" in target) await target.navigate(url);
        } catch (_) { /* cross-origin or unsupported — focus anyway */ }
        return target.focus();
      }
    }

    if (self.clients.openWindow) return self.clients.openWindow(url);
  })());
});

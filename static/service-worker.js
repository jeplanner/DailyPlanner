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
    data: { url: payload.url || "/checklist" },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/checklist";

  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes(url) && "focus" in c) return c.focus();
    }
    if (self.clients.openWindow) return self.clients.openWindow(url);
  })());
});

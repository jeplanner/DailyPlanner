/* DailyPlanner — service worker.
   Responsibilities:
     1. Receive Web Push events and display a notification.
     2. On notification click, focus an existing window or open a new
        one at the payload URL.
     3. Offline caching: serve a usable shell when the network is down.

   Cache strategy:
     - /static/* and /manifest.json + /service-worker.js  → SWR
       (return cache instantly, refresh in background).
     - Same-origin HTML navigations → network-first with cache fallback,
       and /offline as the last resort.
     - Cross-origin, non-GET, /api/*, /admin/* → pass through, no cache.

   Bump CACHE_VERSION on every deploy so stale chunks get evicted. The
   route at /service-worker.js is served with no-cache (app.py), so a
   new version is picked up on the next page load. */

const CACHE_VERSION = "v75-2026-08-16-java-deep-16"
const STATIC_CACHE = `dp-static-${CACHE_VERSION}`;
const PAGES_CACHE  = `dp-pages-${CACHE_VERSION}`;
const OFFLINE_URL  = "/offline";

// LRU caps per cache so the SW doesn't grow unbounded for users who
// hop around 50+ pages. We trim oldest entries (insertion order) when
// the cache exceeds the cap. Static assets get more headroom because
// they're small and cache hits are valuable.
const CACHE_LIMITS = {
  [STATIC_CACHE]: 120,
  [PAGES_CACHE]:  50,
};

// Files we want available immediately on first install so the very
// first offline open works. Keep this list short — anything missed
// is still cached lazily on first fetch.
const PRECACHE_URLS = [
  OFFLINE_URL,
  "/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC_CACHE);
    // Use addAll so a single 404 doesn't fail the whole install —
    // wrap each so missing files don't block activation.
    await Promise.all(PRECACHE_URLS.map(async (url) => {
      try { await cache.add(new Request(url, { cache: "reload" })); }
      catch (_) { /* tolerate — lazy cache will pick it up later */ }
    }));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    // Evict caches from prior versions.
    const names = await caches.keys();
    await Promise.all(
      names
        .filter((n) => n.startsWith("dp-") && n !== STATIC_CACHE && n !== PAGES_CACHE)
        .map((n) => caches.delete(n))
    );
    await self.clients.claim();
  })());
});

// Page → SW messages:
//   SKIP_WAITING  — activate the freshly installed SW right now
//   DP_REPLAY     — drain the offline write queue immediately
//                   (used by browsers without Background Sync)
self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type === "SKIP_WAITING") self.skipWaiting();
  if (data.type === "DP_REPLAY")    event.waitUntil(replayQueue());
});

// Background Sync — Chrome/Edge fire this when connectivity returns,
// even when no tab is open. Tag must match sync-queue.js SYNC_TAG.
self.addEventListener("sync", (event) => {
  if (event.tag === "dp-replay") event.waitUntil(replayQueue());
});

// Periodic Background Sync — Chrome/Edge only, requires the site to
// be installed AND the user to have granted the 'periodic-background-
// sync' permission. We register from pwa.js with a 12h interval; the
// browser fires this no more often than its own heuristics allow,
// which is usually closer to once per day. Best-effort prefetch of
// today's checklist + inbox so opening the app feels instant.
self.addEventListener("periodicsync", (event) => {
  if (event.tag === "dp-prefetch") event.waitUntil(prefetchToday());
});

async function prefetchToday() {
  const cache = await caches.open(PAGES_CACHE);
  const urls = ["/checklist", "/inbox", "/quick-bucket"];
  await Promise.all(urls.map(async (url) => {
    try {
      const res = await fetch(url, { credentials: "include" });
      if (res && res.ok && res.type === "basic") await cache.put(url, res.clone());
    } catch (_) { /* offline at sync time — skip */ }
  }));
}

/* ───── offline write queue (replay side) ─────────────────────────
   The page (sync-queue.js) writes records into IndexedDB when a
   mutating request fails for network reasons. We replay them oldest-
   first as soon as we get a chance, post the result back to every
   open client, and delete the record on a definitive outcome.
   "Definitive" = any HTTP response (2xx, or 4xx/5xx — re-sending a
   400 won't suddenly succeed); network-level failures keep the record
   for the next sync event. */

const QUEUE_DB    = "dp-queue";
const QUEUE_STORE = "writes";

function openQueueDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

function queueAll(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readonly");
    const req = tx.objectStore(QUEUE_STORE).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror   = () => reject(req.error);
  });
}

function queueDelete(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readwrite");
    const req = tx.objectStore(QUEUE_STORE).delete(id);
    req.onsuccess = () => resolve();
    req.onerror   = () => reject(req.error);
  });
}

function queueUpdate(db, record) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readwrite");
    const req = tx.objectStore(QUEUE_STORE).put(record);
    req.onsuccess = () => resolve();
    req.onerror   = () => reject(req.error);
  });
}

function rehydrateBody(body) {
  if (!body || body.kind === "none") return undefined;
  if (body.kind === "text")          return body.value;
  if (body.kind === "urlencoded")    return body.value;
  if (body.kind === "buffer")        return body.value;
  if (body.kind === "blob")          return new Blob([body.value], { type: body.type });
  return undefined;
}

async function notifyClients(payload) {
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  for (const c of clients) {
    try { c.postMessage(Object.assign({ type: "DP_SYNC_RESULT" }, payload)); }
    catch (_) { /* client gone */ }
  }
}

let replayInFlight = null;

function replayQueue() {
  // Coalesce concurrent triggers (sync event + page message racing).
  if (replayInFlight) return replayInFlight;
  replayInFlight = (async () => {
    try {
      const db = await openQueueDB();
      const records = await queueAll(db);
      // Oldest first so causally-related writes (create then update)
      // replay in the order the user made them.
      records.sort((a, b) => a.queuedAt - b.queuedAt);

      for (const rec of records) {
        const headers = Object.assign({}, rec.headers || {});
        // For Content-Type, leave whatever the page sent (usually JSON).
        let res;
        try {
          res = await fetch(rec.url, {
            method:  rec.method,
            headers,
            body:    rehydrateBody(rec.body),
            credentials: "include",
          });
        } catch (netErr) {
          // Still offline — bump attempt counter and stop. Next sync
          // event (or 'online' postMessage) will pick up where we left.
          rec.attempts = (rec.attempts || 0) + 1;
          rec.lastError = String(netErr);
          await queueUpdate(db, rec);
          // Abort the whole drain: if this one failed, the next likely
          // will too. Re-throwing would also cancel the sync retry; we
          // want it to come back, so resolve cleanly.
          return;
        }

        // Read body for the page to consume. Tolerate non-JSON responses.
        let bodyText = "";
        try { bodyText = await res.text(); } catch (_) {}
        let bodyJson = null;
        if ((res.headers.get("content-type") || "").includes("application/json")) {
          try { bodyJson = JSON.parse(bodyText); } catch (_) {}
        }

        await queueDelete(db, rec.id);
        await notifyClients({
          clientId: rec.clientId,
          ok:       res.ok,
          status:   res.status,
          // 409 from a queued write is a real conflict: the same row
          // was changed on another device while this one was offline.
          // The page can distinguish via .conflict and show a chooser
          // instead of treating it as a generic failure.
          conflict: res.status === 409,
          url:      rec.url,
          method:   rec.method,
          body:     bodyJson != null ? bodyJson : bodyText,
        });
      }
    } finally {
      replayInFlight = null;
    }
  })();
  return replayInFlight;
}

/* ───── fetch routing ─────────────────────────────────────────── */

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Bail out fast for things we never want to handle.
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Range requests (audio/video) are not cache-friendly.
  if (req.headers.has("range")) return;

  // API endpoints, push subscription, auth callbacks — always live.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/admin/") ||
    url.pathname.startsWith("/auth/") ||
    url.pathname.startsWith("/oauth/") ||
    url.pathname.startsWith("/push/")
  ) {
    return;
  }

  // Static assets — stale-while-revalidate.
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.json") {
    event.respondWith(staleWhileRevalidate(req, STATIC_CACHE));
    return;
  }

  // HTML navigations — network-first, cache fallback, /offline last.
  const isHTML =
    req.mode === "navigate" ||
    (req.headers.get("accept") || "").includes("text/html");
  if (isHTML) {
    event.respondWith(networkFirst(req, PAGES_CACHE));
    return;
  }
});

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const network = fetch(req)
    .then(async (res) => {
      if (res && res.ok) {
        await cache.put(req, res.clone()).catch(() => {});
        trimCache(cacheName);
      }
      return res;
    })
    .catch(() => null);
  return cached || (await network) || Response.error();
}

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res && res.ok && res.type === "basic") {
      cache.put(req, res.clone()).catch(() => {});
      trimCache(cacheName);
    }
    return res;
  } catch (_) {
    const cached = await cache.match(req);
    if (cached) return cached;
    const offline = await caches.match(OFFLINE_URL);
    if (offline) return offline;
    return new Response("Offline", { status: 503, statusText: "Offline" });
  }
}

// Cache.keys() returns entries in insertion order, which we treat as
// LRU since each successful fetch re-puts the request (deleting the
// old entry and appending). Fire-and-forget — no await needed in the
// response path.
function trimCache(cacheName) {
  const max = CACHE_LIMITS[cacheName];
  if (!max) return;
  caches.open(cacheName).then(async (cache) => {
    const keys = await cache.keys();
    if (keys.length <= max) return;
    const excess = keys.length - max;
    for (let i = 0; i < excess; i++) await cache.delete(keys[i]);
  }).catch(() => {});
}

/* ───── push notifications (unchanged behavior) ───────────────── */

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_) {
    payload = { title: "DailyPlanner", body: event.data ? event.data.text() : "" };
  }

  // Defaults are ALERT behaviour, because a reminder that does not interrupt
  // has failed. But every one of them is overridable by the payload, because
  // an AMBIENT notification — the pinned day summary — needs the exact
  // opposite: it refreshes itself and must never buzz the phone to say the
  // same thing again. Hardcoding these meant there was only one kind of
  // notification this app could ever send.
  const pick = (key, fallback) =>
    Object.prototype.hasOwnProperty.call(payload, key) ? payload[key] : fallback;

  const title = payload.title || "DailyPlanner";
  const options = {
    body: payload.body || "",
    icon: payload.icon || "/static/icons/icon-192.png",
    badge: payload.badge || "/static/icons/icon-192.png",
    tag: payload.tag || "dailyplanner",
    // renotify only means anything alongside a tag: it decides whether
    // REPLACING an existing notification alerts again. False = update in place,
    // silently, which is what a status display wants.
    renotify: pick("renotify", true),
    // Keep on screen until the user taps/dismisses — otherwise Android
    // auto-hides after a few seconds.
    requireInteraction: pick("requireInteraction", true),
    // Explicit vibration pattern so phones on the default channel
    // importance still rumble.
    vibrate: pick("vibrate", [200, 100, 200]),
    // Force non-silent so OS playback of the channel's sound triggers.
    silent: pick("silent", false),
    data: { url: payload.url || "/checklist" },
  };
  if (Array.isArray(payload.actions) && payload.actions.length) {
    options.actions = payload.actions.slice(0, 2);   // Android shows at most 2
  }

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

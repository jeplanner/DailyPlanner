/* DailyPlanner — offline write queue.

   Public API
     window.dpFetch(url, opts)          → Promise<Response>
        Behaves like fetch(). For GETs, just delegates. For mutating
        verbs (POST/PUT/PATCH/DELETE) that fail with a *network* error,
        stashes the request in IndexedDB, asks the SW to retry it when
        connectivity returns, and resolves with a synthetic Response:
            { ok: true, status: 202, _queued: true, clientId, queuedAt }
        json() on that response returns { queued: true, clientId }.
        Server validation errors (4xx/5xx with a response) propagate
        normally — they're not network issues and would just keep failing.

     window.dpSync.pendingCount()       → Promise<number>
     window.dpSync.replay()             → Promise<void>   force a replay
     window.dpSync.onResult(cb)         → unsubscribe fn
        cb receives { clientId, ok, status, body, url, method, error? }
        for each queued request that replays.

   Design notes
     - The IDB schema is shared with service-worker.js (DB_NAME, STORE).
       Bump DB_VERSION if you change the schema.
     - Same-origin only — we don't queue cross-origin (CORS preflight
       state on a replay an hour later is a minefield).
     - Background Sync (chrome.com/en/docs/web/api/Background_Sync_API)
       handles replay when the tab is closed. Where unsupported (Safari,
       Firefox) we fall back to listening for the 'online' event and
       message-driving the SW to replay.
     - We include a clientId on every request via the X-Client-Id
       header. The server can use it for idempotency dedup if it wants;
       if it ignores it, replays may double-create on the rare case
       where the network died after the server processed the write.
*/

(function () {
  "use strict";

  // Capture the live fetch via window.* so we always reach the global,
  // even if a consumer script later declares `const fetch = ...` at its
  // top level. Classic <script> blocks share one Script Lexical
  // Environment, so a bare `fetch` reference inside this IIFE would
  // otherwise resolve to that shadowing const — and if that const
  // points back at dpFetch, you get infinite recursion (a stack
  // overflow we hit on the Eisenhower page).
  const _nativeFetch = (url, opts) => window.fetch(url, opts);

  const DB_NAME      = "dp-queue";
  const STORE        = "writes";
  const DB_VERSION   = 1;
  const SYNC_TAG     = "dp-replay";

  /* ───── IndexedDB ───────────────────────────────────────────── */

  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });
  }

  async function idbAdd(record) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const req = tx.objectStore(STORE).add(record);
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });
  }

  async function idbCount() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).count();
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });
  }

  async function idbAll() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror   = () => reject(req.error);
    });
  }

  async function idbDelete(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const req = tx.objectStore(STORE).delete(id);
      req.onsuccess = () => resolve();
      req.onerror   = () => reject(req.error);
    });
  }

  /* ───── helpers ─────────────────────────────────────────────── */

  // RFC 4122 v4-ish — good enough for an idempotency key.
  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, (c) =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c/4).toString(16)
    );
  }

  function isMutating(method) {
    const m = (method || "GET").toUpperCase();
    return m === "POST" || m === "PUT" || m === "PATCH" || m === "DELETE";
  }

  function isSameOrigin(url) {
    try { return new URL(url, location.href).origin === location.origin; }
    catch { return false; }
  }

  // We serialize fetch's RequestInit into something IDB can hold and
  // an SW can rehydrate. Bodies are kept as strings (everything in
  // this app posts JSON), or as ArrayBuffer for the rare binary case.
  async function serializeBody(body) {
    if (body == null) return { kind: "none", value: null };
    if (typeof body === "string") return { kind: "text", value: body };
    if (body instanceof Blob) {
      return { kind: "blob", value: await body.arrayBuffer(), type: body.type };
    }
    if (body instanceof ArrayBuffer) return { kind: "buffer", value: body };
    if (body instanceof FormData) {
      // Multipart is awkward to replay (boundary regenerated). For now,
      // convert simple form fields to URL-encoded; bail on file fields.
      const entries = [];
      for (const [k, v] of body.entries()) {
        if (typeof v !== "string") throw new Error("FormData with files cannot be queued offline");
        entries.push([k, v]);
      }
      return { kind: "urlencoded", value: new URLSearchParams(entries).toString() };
    }
    // URLSearchParams, etc — stringify
    return { kind: "text", value: String(body) };
  }

  function headersToObject(h) {
    if (!h) return {};
    if (h instanceof Headers) {
      const o = {};
      h.forEach((v, k) => { o[k] = v; });
      return o;
    }
    if (Array.isArray(h)) return Object.fromEntries(h);
    return Object.assign({}, h);
  }

  /* ───── SW bridge ───────────────────────────────────────────── */

  async function requestReplay() {
    if (!("serviceWorker" in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      // Preferred path: Background Sync API. Fires the 'sync' event in
      // the SW when the browser thinks we're back online — works even
      // when no tab is open.
      if (reg && reg.sync) {
        try { await reg.sync.register(SYNC_TAG); return; } catch (_) { /* fall through */ }
      }
      // Fallback: just message the SW to replay now. Useful for Safari
      // and Firefox (no Background Sync support).
      if (reg && reg.active) reg.active.postMessage({ type: "DP_REPLAY" });
    } catch (_) { /* SW not ready — try again on next online event */ }
  }

  /* ───── public: dpFetch ─────────────────────────────────────── */

  async function dpFetch(url, opts) {
    opts = opts || {};
    const method = (opts.method || "GET").toUpperCase();

    // GETs and cross-origin requests pass straight through.
    if (!isMutating(method) || !isSameOrigin(url)) {
      return _nativeFetch(url, opts);
    }

    // Stamp every mutating request with a client id so the server can
    // dedup if it wants. Read it back from the headers on the queued
    // copy when we replay.
    const headers = headersToObject(opts.headers);
    const clientId = headers["X-Client-Id"] || uuid();
    headers["X-Client-Id"] = clientId;

    try {
      const res = await _nativeFetch(url, Object.assign({}, opts, { headers }));
      // We got *a* response — even 500. Don't queue, don't retry.
      // The page handles HTTP errors itself.
      return res;
    } catch (networkErr) {
      // True network failure (fetch threw, not an HTTP error).
      const body = await serializeBody(opts.body);
      const record = {
        clientId,
        url: new URL(url, location.href).toString(),
        method,
        headers,
        body,
        queuedAt: Date.now(),
        attempts: 0,
      };
      try {
        await idbAdd(record);
      } catch (idbErr) {
        // Couldn't queue — surface the original network error so the
        // page can show "save failed" honestly.
        throw networkErr;
      }
      requestReplay();
      notifyQueued(clientId);
      return synthQueuedResponse(clientId, record.queuedAt);
    }
  }

  function synthQueuedResponse(clientId, queuedAt) {
    const body = JSON.stringify({ queued: true, clientId, queuedAt });
    const res = new Response(body, {
      status: 202,
      statusText: "Queued",
      headers: { "Content-Type": "application/json", "X-Client-Id": clientId },
    });
    // Mark it so callers (and apiFetch wrappers) can detect.
    Object.defineProperty(res, "_queued",  { value: true });
    Object.defineProperty(res, "clientId", { value: clientId });
    return res;
  }

  /* ───── observers ───────────────────────────────────────────── */

  const resultListeners = new Set();
  const queueListeners  = new Set();

  function notifyResult(payload) {
    resultListeners.forEach((cb) => { try { cb(payload); } catch (_) {} });
  }
  function notifyQueued(clientId) {
    queueListeners.forEach((cb) => { try { cb({ clientId }); } catch (_) {} });
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.addEventListener("message", (e) => {
      const d = e.data;
      if (!d || d.type !== "DP_SYNC_RESULT") return;
      notifyResult(d);
    });
  }

  // When the browser flips back online, ping the SW to replay even if
  // Background Sync isn't supported.
  window.addEventListener("online", () => { requestReplay(); });

  /* ───── public surface ──────────────────────────────────────── */

  window.dpFetch = dpFetch;
  window.dpSync = {
    pendingCount: () => idbCount().catch(() => 0),
    list:         () => idbAll().catch(() => []),
    drop:         (id) => idbDelete(id),
    replay: () => requestReplay(),
    onResult: (cb) => {
      resultListeners.add(cb);
      return () => resultListeners.delete(cb);
    },
    onQueued: (cb) => {
      queueListeners.add(cb);
      return () => queueListeners.delete(cb);
    },
  };
})();

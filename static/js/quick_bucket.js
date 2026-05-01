/* Quick Bucket — minimal Tasks Bucket front-end */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.querySelector('meta[name="csrf-token"]')?.content) || "";

  const BUCKETS = window.QB_BUCKETS || ["now","1h","2h","3h","4h","5h","6h","7h","8h","future"];
  const BUCKET_LABEL = {
    now: "Now",
    "1h": "1H", "2h": "2H", "3h": "3H", "4h": "4H",
    "5h": "5H", "6h": "6H", "7h": "7H", "8h": "8H",
    future: "Future",
  };
  // Hour buckets all live in one display group so the page doesn't
  // sprout 10 headers; the pill on each row still shows the precise
  // bucket and a live countdown.
  const VISIBLE_GROUPS = ["now", "today", "future"];
  const VISIBLE_GROUP_LABEL = { now: "Now", today: "Today", future: "Future" };
  const HOUR_BUCKETS = new Set(["1h","2h","3h","4h","5h","6h","7h","8h"]);
  const TICK_MS = 30_000;  // recompute countdowns twice a minute

  let items = [];
  // Tracks rows we've already alerted on so the toast / row pulse only
  // fires once when a deadline trips, not every 30s after.
  const alerted = new Set();
  let tickTimer = null;

  // ─────────── helpers ───────────────────────────────────────

  const apiFetch = async (path, opts = {}) => {
    const headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      opts.headers || {}
    );
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts, { headers }));
    let body = {};
    try { body = await res.json(); } catch (_) { body = {}; }
    if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
    return body;
  };

  const toast = (msg, kind = "info") => {
    if (window.toast?.show) return window.toast.show(msg, kind);
    if (window.showToast) return window.showToast(msg, kind);
    console.log(`[${kind}]`, msg);
  };

  const refreshFeather = () => { if (window.feather?.replace) window.feather.replace(); };

  const escapeHTML = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  // Returns minutes remaining (negative when overdue), or null if the
  // item has no deadline (now / future buckets).
  const minutesUntil = (dueAtISO) => {
    if (!dueAtISO) return null;
    const due = new Date(dueAtISO);
    if (Number.isNaN(due.getTime())) return null;
    return Math.round((due - new Date()) / 60000);
  };

  const isCountedDown = (it) => HOUR_BUCKETS.has(it.time_bucket);

  // Toggle pill text — static for now/future, live countdown for 4h/8h.
  const toggleLabel = (it) => {
    if (it.time_bucket === "now")    return BUCKET_LABEL.now;
    if (it.time_bucket === "future") return BUCKET_LABEL.future;
    const mins = minutesUntil(it.due_at);
    if (mins == null) return BUCKET_LABEL[it.time_bucket] || "?";
    if (mins <= 0) return "OVERDUE";
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m === 0 ? `${h}h` : `${h}h ${m}m`;
  };

  const isOverdue = (it) => isCountedDown(it) && minutesUntil(it.due_at) <= 0;

  // ─────────── data load ─────────────────────────────────────

  const loadItems = async () => {
    try {
      const r = await apiFetch("/api/quick-bucket");
      items = r.items || [];
      render();
    } catch (err) {
      toast(err.message || "Could not load", "error");
    }
  };

  // ─────────── render ───────────────────────────────────────

  const groupItems = () => {
    const groups = { now: [], today: [], future: [] };
    items.forEach(it => {
      if (it.time_bucket === "now") groups.now.push(it);
      else if (it.time_bucket === "future") groups.future.push(it);
      else groups.today.push(it);  // 1h..8h
    });
    // Within "today" sort by deadline ascending (closest-first), so the
    // tightest item is on top no matter which hour bucket it picked.
    groups.today.sort((a, b) => {
      const da = a.due_at ? new Date(a.due_at).getTime() : Number.POSITIVE_INFINITY;
      const db = b.due_at ? new Date(b.due_at).getTime() : Number.POSITIVE_INFINITY;
      return da - db;
    });
    return groups;
  };

  const renderRow = (it) => {
    const tb = BUCKETS.includes(it.time_bucket) ? it.time_bucket : "now";
    const overdue = isOverdue(it);
    const rowCls = overdue ? "qb-row is-overdue" : "qb-row";
    const togCls = overdue ? `qb-toggle qb-toggle--overdue` : `qb-toggle qb-toggle--${tb}`;
    return `
      <div class="${rowCls}" data-id="${it.id}">
        <input type="checkbox" class="qb-check" data-action="done" aria-label="Mark done">
        <div class="qb-text" title="${escapeHTML(it.text)}">${escapeHTML(it.text)}</div>
        <button class="${togCls}" data-action="pick" type="button"
                title="Click to choose when: Now / 1H–8H / Future">
          ${escapeHTML(toggleLabel(it))}
        </button>
        <button class="qb-icon-btn" data-action="archive" title="Remove">
          <i data-feather="x"></i>
        </button>
      </div>`;
  };

  const render = () => {
    const wrap = $("#qb-groups");
    const empty = $("#qb-empty");
    if (!items.length) {
      wrap.innerHTML = "";
      empty.removeAttribute("hidden");
      refreshFeather();
      return;
    }
    empty.setAttribute("hidden", "");
    const groups = groupItems();
    wrap.innerHTML = VISIBLE_GROUPS.map(g => {
      const list = groups[g];
      if (!list.length) return "";
      return `
        <section class="qb-group qb-group--${g}">
          <div class="qb-group-head">${VISIBLE_GROUP_LABEL[g]} <span class="qb-count">${list.length}</span></div>
          <div class="qb-list">${list.map(renderRow).join("")}</div>
        </section>`;
    }).join("");
    refreshFeather();
    wireRows();
  };

  // ─────────── interactions ─────────────────────────────────

  const wireRows = () => {
    $$("#qb-groups .qb-row").forEach(row => {
      const id = row.dataset.id;
      const it = items.find(x => x.id === id);
      if (!it) return;

      $("input.qb-check", row)?.addEventListener("change", (e) => {
        if (e.target.checked) markDone(it);
      });
      $("button.qb-toggle", row)?.addEventListener("click", (e) => {
        e.stopPropagation();
        openPicker(e.currentTarget, it);
      });
      $("button.qb-icon-btn[data-action='archive']", row)?.addEventListener("click", () => archive(it));
    });
  };

  // ─────────── bucket picker popover ────────────────────────

  const closePicker = () => {
    const picker = $("#qb-picker");
    if (!picker || picker.hidden) return;
    picker.hidden = true;
    picker.innerHTML = "";
  };

  const openPicker = (anchor, it) => {
    const picker = $("#qb-picker");
    if (!picker) return;

    picker.innerHTML = BUCKETS.map(b => {
      const cur = it.time_bucket === b ? "is-current" : "";
      return `<button class="qb-pick ${cur}" data-b="${b}" type="button">${BUCKET_LABEL[b] || b}</button>`;
    }).join("");

    // Position below the toggle pill, flush-left with it. If that
    // would overflow the viewport on the right edge, slide left.
    const r = anchor.getBoundingClientRect();
    picker.hidden = false;
    const pw = picker.offsetWidth;
    const top = r.bottom + window.scrollY + 4;
    let left = r.left + window.scrollX;
    if (left + pw > window.innerWidth + window.scrollX - 8) {
      left = Math.max(8, window.innerWidth + window.scrollX - pw - 8);
    }
    picker.style.top = `${top}px`;
    picker.style.left = `${left}px`;

    $$(".qb-pick", picker).forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const newBucket = btn.dataset.b;
        closePicker();
        if (newBucket === it.time_bucket) return;
        setBucket(it, newBucket);
      });
    });
  };

  const setBucket = async (it, newBucket) => {
    try {
      const r = await apiFetch(`/api/quick-bucket/${it.id}/update`, {
        method: "POST", body: JSON.stringify({ time_bucket: newBucket }),
      });
      it.time_bucket = newBucket;
      // The /update endpoint echoes the patch back; it includes the
      // freshly-stamped due_at (or null for now/future).
      if (r && r.patch && "due_at" in r.patch) it.due_at = r.patch.due_at;
      else it.due_at = null;
      // Re-arm overdue alerts for this row — the deadline is new.
      alerted.delete(it.id);
      render();
    } catch (err) {
      toast(err.message || "Couldn't change", "error");
    }
  };

  const markDone = async (it) => {
    try {
      await apiFetch(`/api/quick-bucket/${it.id}/done`, { method: "POST", body: "{}" });
      items = items.filter(x => x.id !== it.id);
      render();
    } catch (err) {
      toast(err.message || "Couldn't mark done", "error");
    }
  };

  const archive = async (it) => {
    try {
      await apiFetch(`/api/quick-bucket/${it.id}/archive`, { method: "POST", body: "{}" });
      items = items.filter(x => x.id !== it.id);
      render();
    } catch (err) {
      toast(err.message || "Couldn't remove", "error");
    }
  };

  const addItem = async (text) => {
    text = (text || "").trim();
    if (!text) return;
    try {
      const r = await apiFetch("/api/quick-bucket", {
        method: "POST", body: JSON.stringify({ text, time_bucket: "now" }),
      });
      if (r.item) items.unshift(r.item);
      render();
    } catch (err) {
      toast(err.message || "Couldn't add", "error");
    }
  };

  // ─────────── countdown ticker + overdue alerts ────────────

  const fireOverdueAlert = (it) => {
    toast(`⏰ Overdue: ${it.text}`, "error");
    // Use the browser Notification API too if the user has granted
    // permission elsewhere — handy when the tab is in the background.
    if ("Notification" in window && Notification.permission === "granted") {
      try { new Notification("Tasks Bucket — overdue", { body: it.text }); } catch (_) {}
    }
  };

  const tick = () => {
    let anyOverdueChanged = false;
    items.forEach(it => {
      if (!isCountedDown(it)) return;
      const overdue = isOverdue(it);
      if (overdue && !alerted.has(it.id)) {
        alerted.add(it.id);
        fireOverdueAlert(it);
        anyOverdueChanged = true;
      }
    });
    // Re-render unconditionally — countdown labels need updating each
    // tick, and re-render is cheap (no API call).
    render();
  };

  const startTicker = () => {
    if (tickTimer) clearInterval(tickTimer);
    tickTimer = setInterval(tick, TICK_MS);
    // Also re-tick when the tab regains focus, since setInterval is
    // throttled in background tabs.
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) tick();
    });
  };

  // ─────────── boot ─────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", async () => {
    refreshFeather();
    const form = $("#qb-add-form");
    const input = $("#qb-add-input");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const v = input.value;
      input.value = "";
      await addItem(v);
      input.focus();
    });
    await loadItems();
    // After the first render, prime the alerted set with currently-
    // overdue items so we don't fire a wall of toasts for tasks the
    // user has been ignoring across sessions.
    items.forEach(it => { if (isOverdue(it)) alerted.add(it.id); });
    startTicker();

    // Close the bucket picker when the user clicks anywhere outside it.
    document.addEventListener("click", (e) => {
      const picker = $("#qb-picker");
      if (!picker || picker.hidden) return;
      if (e.target.closest("#qb-picker")) return;
      if (e.target.closest("button.qb-toggle")) return;
      closePicker();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePicker();
    });
  });
})();

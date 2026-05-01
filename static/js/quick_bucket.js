/* Quick Bucket — minimal Tasks Bucket front-end */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.querySelector('meta[name="csrf-token"]')?.content) || "";

  const BUCKETS = window.QB_BUCKETS || ["now", "4h", "8h", "future"];
  const BUCKET_LABEL = { now: "Now", "4h": "4h", "8h": "8h", future: "Future" };
  const GROUP_LABEL = { now: "Now", "4h": "Within 4h", "8h": "Within 8h", future: "Future" };

  let items = [];

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
    const groups = {};
    BUCKETS.forEach(b => groups[b] = []);
    items.forEach(it => {
      const key = BUCKETS.includes(it.time_bucket) ? it.time_bucket : "now";
      groups[key].push(it);
    });
    return groups;
  };

  const renderRow = (it) => {
    const tb = BUCKETS.includes(it.time_bucket) ? it.time_bucket : "now";
    return `
      <div class="qb-row" data-id="${it.id}">
        <input type="checkbox" class="qb-check" data-action="done" aria-label="Mark done">
        <div class="qb-text" title="${escapeHTML(it.text)}">${escapeHTML(it.text)}</div>
        <button class="qb-toggle qb-toggle--${tb}" data-action="cycle" type="button"
                title="Click to cycle: Now → 4h → 8h → Future">
          ${BUCKET_LABEL[tb] || tb}
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
    wrap.innerHTML = BUCKETS.map(b => {
      const list = groups[b];
      if (!list.length) return "";
      return `
        <section class="qb-group qb-group--${b}">
          <div class="qb-group-head">${GROUP_LABEL[b]} <span class="qb-count">${list.length}</span></div>
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
      $("button.qb-toggle", row)?.addEventListener("click", () => cycle(it));
      $("button.qb-icon-btn[data-action='archive']", row)?.addEventListener("click", () => archive(it));
    });
  };

  const cycle = async (it) => {
    try {
      const r = await apiFetch(`/api/quick-bucket/${it.id}/cycle`, { method: "POST", body: "{}" });
      it.time_bucket = r.time_bucket;
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
  });
})();

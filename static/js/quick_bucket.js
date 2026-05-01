/* Quick Bucket — minimal Tasks Bucket front-end */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.querySelector('meta[name="csrf-token"]')?.content) || "";

  const BUCKETS = window.QB_BUCKETS || [
    "now",
    "5m","15m","30m","45m",
    "1h","2h","3h","4h","5h","6h","7h","8h",
    "future",
  ];
  const BUCKET_LABEL = {
    now: "Now",
    "5m": "5M", "15m": "15M", "30m": "30M", "45m": "45M",
    "1h": "1H", "2h": "2H", "3h": "3H", "4h": "4H",
    "5h": "5H", "6h": "6H", "7h": "7H", "8h": "8H",
    future: "Future",
  };
  // Minute + hour buckets all live in one display group so the page
  // doesn't sprout 12+ headers; the pill on each row still shows the
  // precise bucket and a live countdown. Done items get their own
  // group at the bottom so closed work stays visible without polluting
  // the active list.
  const VISIBLE_GROUPS = ["now", "today", "future", "done"];
  const VISIBLE_GROUP_LABEL = { now: "Now", today: "Today", future: "Future", done: "Done" };
  const COUNTED_DOWN = new Set([
    "5m","15m","30m","45m",
    "1h","2h","3h","4h","5h","6h","7h","8h",
  ]);
  // Tighter cadence — with 5/15/30/45m options, a 30s tick is too slow
  // to feel "live". 10s keeps the label moving without burning power.
  const TICK_MS = 10_000;

  let items = [];
  // Tracks rows we've already alerted on so the toast / row pulse only
  // fires once when a deadline trips, not every 30s after.
  const alerted = new Set();
  let tickTimer = null;

  // Motivational quotes for the stats bar — one per day, deterministic
  // so a refresh doesn't shuffle. Date-of-year picks the index.
  const QUOTES = [
    "Small steps every day beat big leaps once in a while.",
    "Done is better than perfect.",
    "Focus is saying no to a thousand good things.",
    "Discipline equals freedom.",
    "Action expresses priorities.",
    "Slow is smooth, smooth is fast.",
    "The best way to get started is to quit talking and begin doing.",
    "Energy and persistence conquer all things.",
    "Inch by inch life's a cinch; yard by yard it's hard.",
    "What gets scheduled gets done.",
    "Make it work, make it right, make it fast — in that order.",
    "You don't have to be great to start, but you have to start to be great.",
    "Compound interest is the eighth wonder — even on habits.",
    "The chains of habit are too light to be felt until they are too heavy to be broken.",
    "Motivation gets you going; habit keeps you going.",
    "If it's not on the list, it didn't happen.",
    "Done lists tell better stories than to-do lists.",
    "Progress, not perfection.",
    "One task at a time, and that one task fully.",
    "The successful warrior is the average person, with laser-like focus.",
    "Consistency is more important than intensity.",
    "Tomorrow becomes never. Do it now.",
    "Direction is more important than speed.",
    "You'll never find time for anything. If you want time, you must make it.",
    "When in doubt, take the smallest possible next step.",
    "First do what's necessary, then what's possible — soon you're doing the impossible.",
    "Plans are nothing; planning is everything.",
    "Focus on being productive instead of busy.",
    "The way to get started is to quit talking and begin doing.",
    "Success is the sum of small efforts, repeated.",
  ];
  const quoteOfTheDay = () => {
    const d = new Date();
    const dayIdx = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 86_400_000);
    return QUOTES[dayIdx % QUOTES.length];
  };
  const isSameLocalDay = (iso) => {
    if (!iso) return false;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return false;
    const now = new Date();
    return d.getFullYear() === now.getFullYear()
        && d.getMonth() === now.getMonth()
        && d.getDate() === now.getDate();
  };
  const renderStatBar = () => {
    const open = items.filter(it => !it.is_done).length;
    const doneToday = items.filter(it => it.is_done && isSameLocalDay(it.done_at)).length;
    const openEl = document.getElementById("qb-stat-open");
    const doneEl = document.getElementById("qb-stat-done");
    const quoteEl = document.getElementById("qb-quote");
    if (openEl) openEl.textContent = open;
    if (doneEl) doneEl.textContent = doneToday;
    if (quoteEl) quoteEl.textContent = `"${quoteOfTheDay()}"`;
  };

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

  const isCountedDown = (it) => COUNTED_DOWN.has(it.time_bucket);

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
    const groups = { now: [], today: [], future: [], done: [] };
    items.forEach(it => {
      if (it.is_done)              groups.done.push(it);
      else if (it.time_bucket === "now")    groups.now.push(it);
      else if (it.time_bucket === "future") groups.future.push(it);
      else                                  groups.today.push(it);  // 1h..8h
    });
    // Within "today" sort by deadline ascending (closest-first), so the
    // tightest item is on top no matter which hour bucket it picked.
    groups.today.sort((a, b) => {
      const da = a.due_at ? new Date(a.due_at).getTime() : Number.POSITIVE_INFINITY;
      const db = b.due_at ? new Date(b.due_at).getTime() : Number.POSITIVE_INFINITY;
      return da - db;
    });
    // Done sorted by most-recently-closed first.
    groups.done.sort((a, b) => (b.done_at || "").localeCompare(a.done_at || ""));
    return groups;
  };

  const renderRow = (it) => {
    const tb = BUCKETS.includes(it.time_bucket) ? it.time_bucket : "now";
    const overdue = !it.is_done && isOverdue(it);
    const cls = ["qb-row"];
    if (overdue) cls.push("is-overdue");
    if (it.is_done) cls.push("is-done");
    const togCls = overdue ? "qb-toggle qb-toggle--overdue" : `qb-toggle qb-toggle--${tb}`;

    // Done rows still get a Reopen icon. Active rows have no side
    // action — clicking the task text itself opens the edit popup.
    const sideAction = it.is_done
      ? `<button class="qb-row-icon-action" data-action="reopen" title="Reopen">
           <i data-feather="rotate-ccw"></i>
         </button>`
      : `<span class="qb-row-spacer" aria-hidden="true"></span>`;

    return `
      <div class="${cls.join(' ')}" data-id="${it.id}">
        <input type="checkbox" class="qb-check" data-action="done"
               aria-label="Mark done" ${it.is_done ? 'checked' : ''}>
        <div class="qb-text" data-action="edit" title="Click to edit"
             tabindex="0" role="button">${escapeHTML(it.text)}</div>
        <button class="${togCls}" data-action="pick" type="button"
                title="Click to choose when: Now / 1H–8H / Future">
          ${escapeHTML(toggleLabel(it))}
        </button>
        ${sideAction}
        <button class="qb-icon-btn" data-action="archive" title="Remove">
          <i data-feather="x"></i>
        </button>
      </div>`;
  };

  const render = () => {
    renderStatBar();
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
        else reopen(it);
      });
      $("button.qb-toggle", row)?.addEventListener("click", (e) => {
        e.stopPropagation();
        openPicker(e.currentTarget, it);
      });
      $("button.qb-icon-btn[data-action='archive']", row)?.addEventListener("click", () => archive(it));
      $("button.qb-row-icon-action[data-action='reopen']", row)?.addEventListener("click", () => reopen(it));
      // Tapping the task text opens the edit-and-move popup. Done rows
      // also get the popup so the user can fix typos in past entries.
      const textEl = $(".qb-text", row);
      textEl?.addEventListener("click", () => openEditModal(it));
      textEl?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openEditModal(it);
        }
      });
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
      it.is_done = true;
      it.done_at = new Date().toISOString();
      // Closed items stay in `items` so the Done group can render them.
      render();
    } catch (err) {
      toast(err.message || "Couldn't mark done", "error");
    }
  };

  const reopen = async (it) => {
    try {
      await apiFetch(`/api/quick-bucket/${it.id}/reopen`, { method: "POST", body: "{}" });
      it.is_done = false;
      it.done_at = null;
      render();
    } catch (err) {
      toast(err.message || "Couldn't reopen", "error");
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

  // ─────────── Move-to-category modal ───────────────────────
  //
  // The user clicks the → icon on a row, picks a category, fills the
  // category-specific form, and hits Save & move. The bucket row is
  // archived; a real row is created in the destination module.

  const MOVE_CATEGORIES = [
    { key: "ProjectTask", label: "Project Task" },
    { key: "Checklist",   label: "Checklist" },
    { key: "TravelReads", label: "Travel & Reads" },
    { key: "Grocery",     label: "Grocery" },
  ];
  const MOVE_FIELDS = {
    Grocery: [
      { name: "item",     label: "Item",     type: "text",     fromText: true, required: true, max: 120 },
      { name: "quantity", label: "Quantity", type: "text",     placeholder: "e.g. 2 lb", max: 40 },
      { name: "category", label: "Aisle",    type: "select",   default: "other",
        options: ["produce","dairy","staples","snacks","household","spices","frozen","beverages","meat","bakery","other"] },
      { name: "priority", label: "Priority", type: "select",   default: "medium",
        options: ["high","medium","low"] },
      { name: "notes",    label: "Notes",    type: "textarea", wide: true, max: 400 },
    ],
    Checklist: [
      { name: "name",          label: "Name",         type: "text",     fromText: true, required: true, max: 200 },
      { name: "schedule",      label: "Schedule",     type: "select",   default: "daily",
        options: ["daily","weekdays","weekends","custom"] },
      { name: "time_of_day",   label: "When",         type: "select",   default: "anytime",
        options: ["morning","afternoon","evening","anytime"] },
      { name: "reminder_time", label: "Reminder",     type: "time" },
      { name: "group_name",    label: "Group",        type: "text",     placeholder: "Optional" },
      { name: "notes",         label: "Notes",        type: "textarea", wide: true, max: 400 },
    ],
    TravelReads: [
      { name: "title",    label: "Title",    type: "text",     fromText: true, required: true, max: 200 },
      { name: "url",      label: "URL",      type: "url",      placeholder: "https://…", wide: true },
      { name: "kind",     label: "Kind",     type: "select",   default: "article",
        options: ["article","video","book","podcast","newsletter","documentary","other"] },
      { name: "priority", label: "Priority", type: "select",   default: "medium",
        options: ["high","medium","low"] },
      { name: "notes",    label: "Notes",    type: "textarea", wide: true },
    ],
    ProjectTask: [
      { name: "name",          label: "Title",    type: "text",   fromText: true, required: true, max: 200 },
      { name: "group_name",    label: "Group",    type: "text",   default: "Project Tasks" },
      { name: "time_of_day",   label: "When",     type: "select", default: "anytime",
        options: ["morning","afternoon","evening","anytime"] },
      { name: "reminder_time", label: "Reminder", type: "time" },
    ],
  };

  let moveItem = null;
  let moveCategory = null;

  const renderMoveCategoryButtons = () => {
    const grid = $("#qb-move-cats");
    grid.innerHTML = MOVE_CATEGORIES.map(c =>
      `<button class="qb-cat-btn ${moveCategory === c.key ? 'is-current' : ''}" data-cat="${c.key}" type="button">${c.label}</button>`
    ).join("");
    $$(".qb-cat-btn", grid).forEach(btn => {
      btn.addEventListener("click", () => {
        // Clicking the same category twice clears it (text-edit only).
        moveCategory = (moveCategory === btn.dataset.cat) ? null : btn.dataset.cat;
        renderMoveCategoryButtons();
        renderMoveForm();
        updateSaveLabel();
      });
    });
  };

  const updateSaveLabel = () => {
    const lbl = $("#qb-move-save-label");
    if (!lbl) return;
    if (moveCategory && MOVE_FIELDS[moveCategory]) {
      const cat = MOVE_CATEGORIES.find(c => c.key === moveCategory);
      lbl.textContent = `Save & move to ${cat ? cat.label : moveCategory}`;
    } else {
      lbl.textContent = "Save";
    }
  };

  const renderMoveForm = () => {
    const wrap  = $("#qb-move-form-wrap");
    const form  = $("#qb-move-form");
    const note  = $("#qb-move-form-note");
    const title = $("#qb-move-form-title");
    const save  = $("#qb-move-save");

    if (!moveCategory) {
      wrap.setAttribute("hidden", "");
      save.disabled = true;
      return;
    }
    const defs = MOVE_FIELDS[moveCategory];
    if (!defs) {
      wrap.removeAttribute("hidden");
      title.textContent = "Details";
      form.innerHTML = "";
      note.textContent = "This category isn't routable yet.";
      note.removeAttribute("hidden");
      save.disabled = true;
      return;
    }
    wrap.removeAttribute("hidden");
    title.textContent = `Move to ${MOVE_CATEGORIES.find(c => c.key === moveCategory)?.label || moveCategory}`;
    note.setAttribute("hidden", "");
    form.innerHTML = defs.map(d => {
      const wide = d.wide ? "qb-form-field--wide" : "";
      const placeholder = d.placeholder ? ` placeholder="${escapeHTML(d.placeholder)}"` : "";
      const max = d.max ? ` maxlength="${d.max}"` : "";
      const req = d.required ? " required" : "";
      const initial = d.fromText ? (moveItem?.text || "") : (d.default ?? "");
      let control;
      if (d.type === "select") {
        const opts = (d.options || []).map(o =>
          `<option value="${escapeHTML(o)}" ${String(initial) === String(o) ? "selected" : ""}>${escapeHTML(o)}</option>`
        ).join("");
        control = `<select name="${d.name}"${req}>${opts}</select>`;
      } else if (d.type === "textarea") {
        control = `<textarea name="${d.name}" rows="3"${placeholder}${max}${req}>${escapeHTML(initial)}</textarea>`;
      } else {
        const t = (d.type === "url" || d.type === "time") ? d.type : "text";
        control = `<input type="${t}" name="${d.name}" value="${escapeHTML(initial)}"${placeholder}${max}${req}>`;
      }
      return `
        <div class="qb-form-field ${wide}">
          <label>${escapeHTML(d.label)}</label>
          ${control}
        </div>`;
    }).join("");
    save.disabled = false;
  };

  const openEditModal = (it) => {
    moveItem = it;
    moveCategory = null;
    const textInput = $("#qb-edit-text-input");
    if (textInput) textInput.value = it.text || "";
    renderMoveCategoryButtons();
    renderMoveForm();
    updateSaveLabel();
    $("#qb-move-modal").classList.add("is-open");
    $("#qb-move-modal").setAttribute("aria-hidden", "false");
    refreshFeather();
    // Focus the textarea so the user can immediately start editing.
    setTimeout(() => textInput?.focus(), 30);
  };

  const closeEditModal = () => {
    $("#qb-move-modal").classList.remove("is-open");
    $("#qb-move-modal").setAttribute("aria-hidden", "true");
    moveItem = null;
    moveCategory = null;
  };

  const submitEdit = async () => {
    if (!moveItem) return;
    const newText = ($("#qb-edit-text-input")?.value || "").trim();
    if (!newText) {
      toast("Task text can't be empty", "error");
      return;
    }
    const save = $("#qb-move-save");
    save.disabled = true;
    try {
      // Always persist text edits first — even if we're also routing,
      // this keeps the bucket row coherent if the route call fails.
      if (newText !== moveItem.text) {
        await apiFetch(`/api/quick-bucket/${moveItem.id}/update`, {
          method: "POST", body: JSON.stringify({ text: newText }),
        });
        moveItem.text = newText;
      }

      // No category picked → text-only edit, we're done.
      if (!moveCategory || !MOVE_FIELDS[moveCategory]) {
        toast("Saved", "success");
        closeEditModal();
        render();
        return;
      }

      // Category picked → also route into the destination module.
      const defs = MOVE_FIELDS[moveCategory];
      const form = $("#qb-move-form");
      const fd = new FormData(form);
      const fields = {};
      for (const [k, v] of fd.entries()) fields[k] = v;
      // Title-ish field is overridden with the latest textarea value
      // so editing the text in the textarea wins over the original
      // pre-fill in the form.
      for (const d of defs) {
        if (d.fromText) { fields[d.name] = newText; break; }
      }
      for (const d of defs) {
        if (d.required && !(fields[d.name] || "").trim()) {
          toast(`${d.label} is required`, "error");
          save.disabled = false;
          return;
        }
      }
      const r = await apiFetch(`/api/quick-bucket/${moveItem.id}/route`, {
        method: "POST",
        body: JSON.stringify({ category: moveCategory, fields }),
      });
      const where = (r.destination_table || "").replace("_", " ");
      toast(`Moved to ${where}`, "success");
      items = items.filter(x => x.id !== moveItem.id);
      closeEditModal();
      render();
    } catch (err) {
      toast(err.message || "Couldn't save", "error");
    } finally {
      save.disabled = false;
    }
  };

  const wireMoveModal = () => {
    $("#qb-move-close").addEventListener("click", closeEditModal);
    $("#qb-move-cancel").addEventListener("click", closeEditModal);
    $("#qb-move-save").addEventListener("click", submitEdit);
    $("#qb-move-modal").addEventListener("click", (e) => {
      if (e.target.id === "qb-move-modal") closeEditModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeEditModal();
    });
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

  // ─────────── Pomodoro timer ───────────────────────────────
  //
  // State machine: idle → running → (paused | ended). Reset goes back
  // to idle. Persisted to localStorage so a refresh mid-session keeps
  // ticking. We store the absolute end timestamp while running, so
  // closing the tab and re-opening it resyncs to wall-clock time.

  const POMO_KEY = "qb-pomo-v1";
  const POMO_TICK_MS = 500;
  const POMO_PRESETS = [15, 25, 50, 90];
  const POMO_DEFAULT_MIN = 25;
  const PAGE_TITLE = "Tasks Bucket — DailyPlanner";

  let pomo = {
    durationMins: POMO_DEFAULT_MIN,
    state: "idle",                                    // idle | running | paused | ended
    endsAt: null,                                     // ms timestamp; only set when running
    remaining: POMO_DEFAULT_MIN * 60 * 1000,          // ms; valid when paused/idle
    label: null,                                      // what the user is focusing on
    serverLogId: null,                                // task_time_logs row id (server-side mirror)
  };
  let pomoTimer = null;

  const loadPomo = () => {
    try {
      const raw = localStorage.getItem(POMO_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved && typeof saved === "object") Object.assign(pomo, saved);
    } catch (_) { /* corrupt → keep defaults */ }
  };
  const savePomo = () => {
    try { localStorage.setItem(POMO_KEY, JSON.stringify(pomo)); } catch (_) {}
  };

  const pomoMsRemaining = () => {
    if (pomo.state === "running" && pomo.endsAt) {
      return Math.max(0, pomo.endsAt - Date.now());
    }
    return Math.max(0, pomo.remaining || 0);
  };

  const fmtClock = (ms) => {
    const totalSec = Math.ceil(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  const renderPomo = () => {
    const root = $("#qb-pomo");
    if (!root) return;
    const ms = pomoMsRemaining();
    $("#qb-pomo-time").textContent = fmtClock(ms);

    const playBtn = $("#qb-pomo-play");
    const playing = pomo.state === "running";
    playBtn.innerHTML = `<i data-feather="${playing ? "pause" : "play"}"></i>`;
    playBtn.title = playing ? "Pause" : (pomo.state === "paused" ? "Resume" : "Start");

    root.classList.toggle("is-running", playing);
    root.classList.toggle("is-ended", pomo.state === "ended");

    // Label area: shows "Focus" when no title is set, or the activity
    // title once the user has picked one. The title is collected via
    // a popup, not an inline field, so the widget stays compact.
    const lbl = $("#qb-pomo-label");
    if (lbl) {
      lbl.textContent = pomo.label || "Focus";
      lbl.title = pomo.label || "Focus session";
    }

    $$(".qb-pomo-dur").forEach(b => {
      b.classList.toggle("is-current", Number(b.dataset.min) === pomo.durationMins);
    });

    // Tab title: keep the countdown visible when the page is in the
    // background. Restore on idle/paused/ended.
    if (playing) {
      const tail = pomo.label ? ` — ${pomo.label}` : " • Pomodoro";
      document.title = `${fmtClock(ms)}${tail}`;
    } else {
      document.title = PAGE_TITLE;
    }

    refreshFeather();

    // Phase ended while running → fire once.
    if (playing && ms <= 0) pomoEnd();
  };

  const startPomoTicker = () => {
    if (pomoTimer) clearInterval(pomoTimer);
    pomoTimer = setInterval(renderPomo, POMO_TICK_MS);
  };
  const stopPomoTicker = () => {
    if (pomoTimer) { clearInterval(pomoTimer); pomoTimer = null; }
  };

  // Opens the in-page focus-title popup and resolves with the typed
  // title (trimmed) or null if the user dismissed it.
  const askPomoTitle = () => new Promise((resolve) => {
    const modal = $("#qb-pomo-modal");
    const input = $("#qb-pomo-modal-input");
    const startBtn = $("#qb-pomo-modal-start");
    const cancelBtn = $("#qb-pomo-modal-cancel");
    const closeBtn = $("#qb-pomo-modal-close");
    if (!modal || !input || !startBtn) { resolve(null); return; }

    input.value = "";
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    setTimeout(() => input.focus(), 30);

    const finish = (val) => {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
      startBtn.removeEventListener("click", onStart);
      cancelBtn.removeEventListener("click", onCancel);
      closeBtn.removeEventListener("click", onCancel);
      input.removeEventListener("keydown", onKey);
      modal.removeEventListener("click", onBackdrop);
      resolve(val);
    };
    const onStart = () => {
      const v = (input.value || "").trim();
      if (!v) { input.focus(); return; }
      finish(v);
    };
    const onCancel = () => finish(null);
    const onKey = (e) => {
      // Shift+Enter inserts a newline (the field is now a textarea so
      // long titles wrap), plain Enter submits.
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onStart(); }
      else if (e.key === "Escape") { e.preventDefault(); onCancel(); }
    };
    const onBackdrop = (e) => { if (e.target === modal) onCancel(); };

    startBtn.addEventListener("click", onStart);
    cancelBtn.addEventListener("click", onCancel);
    closeBtn.addEventListener("click", onCancel);
    input.addEventListener("keydown", onKey);
    modal.addEventListener("click", onBackdrop);
  });

  const pomoStart = async () => {
    if (pomo.state === "running") return;

    // First-time start → custom popup asks for the focus title. Resuming
    // a paused session (label already set) skips this so the play/pause
    // toggle stays one-tap.
    const isResume = pomo.state === "paused" && !!pomo.label;
    if (!isResume) {
      const title = await askPomoTitle();
      if (!title) return;  // user cancelled
      pomo.label = title.slice(0, 200);
    }

    const ms = pomo.state === "paused"
      ? Math.max(0, pomo.remaining)
      : pomo.durationMins * 60 * 1000;
    if (ms <= 0) {
      // Resuming a finished timer → restart fresh.
      pomo.remaining = pomo.durationMins * 60 * 1000;
    }
    pomo.state = "running";
    pomo.endsAt = Date.now() + (pomo.remaining > 0 ? pomo.remaining : pomo.durationMins * 60 * 1000);
    pomo.remaining = pomo.endsAt - Date.now();

    // Open a server-side log so this session lands in the Focus Log.
    // Skipped on resume (we already have a log id from the original
    // start). Best-effort — local timer keeps working if the API fails.
    if (!pomo.serverLogId) {
      try {
        const r = await apiFetch("/api/v2/timer/start", {
          method: "POST",
          body: JSON.stringify({
            source: "adhoc",
            label: pomo.label,
            mode: "pomodoro",
            target_seconds: pomo.durationMins * 60,
          }),
        });
        pomo.serverLogId = (r && r.id) || null;
      } catch (err) {
        console.warn("pomodoro: server log start failed", err);
      }
    }

    savePomo();
    startPomoTicker();
    renderPomo();
  };

  const closeServerLog = async () => {
    if (!pomo.serverLogId) return;
    const id = pomo.serverLogId;
    pomo.serverLogId = null;
    try {
      await apiFetch("/api/v2/timer/stop", {
        method: "POST", body: JSON.stringify({ id }),
      });
    } catch (err) {
      console.warn("pomodoro: server log stop failed", err);
    }
  };

  // Compute how many ms have elapsed in the current Pomodoro session,
  // taking into account whether the timer is running (use endsAt) or
  // paused (use remaining).
  const pomoElapsedMs = () => {
    const dur = pomo.durationMins * 60 * 1000;
    if (pomo.state === "running" && pomo.endsAt) {
      return Math.max(0, dur - Math.max(0, pomo.endsAt - Date.now()));
    }
    if (pomo.state === "paused") {
      return Math.max(0, dur - Math.max(0, pomo.remaining || 0));
    }
    if (pomo.state === "ended") return dur;
    return 0;
  };

  // Drop a Done-marked entry into the Tasks Bucket so today's focus
  // sessions are visible inline. Best-effort — failures don't block
  // the rest of the Pomodoro lifecycle.
  const recordFocusInDone = async (label, elapsedMs) => {
    if (!label || elapsedMs < 30_000) return;  // ignore <30s blips
    const minutes = Math.round(elapsedMs / 60_000);
    const elapsedText = minutes >= 60
      ? `${Math.floor(minutes / 60)}h ${minutes % 60}m`
      : `${minutes}m`;
    const text = `🎯 ${label} — ${elapsedText} focus`;
    try {
      const r = await apiFetch("/api/quick-bucket", {
        method: "POST",
        body: JSON.stringify({ text, time_bucket: "future", is_done: true }),
      });
      if (r && r.item) {
        items.unshift(r.item);
        render();
      }
    } catch (err) {
      console.warn("pomodoro: focus-done insert failed", err);
    }
  };

  const pomoPause = () => {
    if (pomo.state !== "running") return;
    pomo.remaining = Math.max(0, pomo.endsAt - Date.now());
    pomo.state = "paused";
    pomo.endsAt = null;
    savePomo();
    stopPomoTicker();
    renderPomo();
  };

  const pomoToggle = () => {
    if (pomo.state === "running") pomoPause();
    else pomoStart();
  };

  const pomoReset = async () => {
    // Capture state BEFORE closing the log, so a partial session can
    // also land in the Done section with the right minutes count.
    const elapsedBefore = pomoElapsedMs();
    const labelBefore = pomo.label;

    await closeServerLog();
    if (labelBefore && elapsedBefore > 30_000) {
      recordFocusInDone(labelBefore, elapsedBefore);
    }

    pomo.state = "idle";
    pomo.endsAt = null;
    pomo.remaining = pomo.durationMins * 60 * 1000;
    pomo.label = null;
    savePomo();
    stopPomoTicker();
    renderPomo();
  };

  const pomoSetDuration = (mins) => {
    pomo.durationMins = mins;
    // If we're idle/ended, snap the visible clock to the new length.
    // Don't reach into a running session — it'll keep its current end.
    if (pomo.state !== "running") {
      pomo.remaining = mins * 60 * 1000;
      pomo.state = "idle";
      pomo.endsAt = null;
    }
    savePomo();
    renderPomo();
  };

  const pomoEnd = async () => {
    const finishedLabel = pomo.label;
    const fullDurationMs = pomo.durationMins * 60 * 1000;
    // Close the server log first so the focus session lands in the Focus
    // Log with the right duration. Errors here are non-fatal.
    await closeServerLog();
    if (finishedLabel) {
      recordFocusInDone(finishedLabel, fullDurationMs);
    }
    pomo.state = "ended";
    pomo.remaining = 0;
    pomo.endsAt = null;
    // Clear label so the next Start prompts for a fresh activity.
    pomo.label = null;
    savePomo();
    stopPomoTicker();
    pomoBeep();
    const what = finishedLabel ? ` — ${finishedLabel}` : "";
    toast(`✅ ${pomo.durationMins}-minute focus complete${what}`, "success");
    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification("Pomodoro done", {
          body: `${pomo.durationMins}-minute focus complete${what}`,
        });
      } catch (_) {}
    }
    renderPomo();
  };

  // Short tone via Web Audio — no audio file dependency.
  const pomoBeep = () => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const beepAt = (freq, t0, dur = 0.18) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, ctx.currentTime + t0);
        gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + t0 + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t0 + dur);
        osc.start(ctx.currentTime + t0);
        osc.stop(ctx.currentTime + t0 + dur + 0.02);
      };
      // Two-note chime so the end is distinct from the deadline alert.
      beepAt(880, 0);
      beepAt(1320, 0.22);
      setTimeout(() => ctx.close(), 800);
    } catch (_) {}
  };

  const wirePomo = () => {
    $("#qb-pomo-play").addEventListener("click", () => {
      pomoToggle();
      // First user gesture is a good moment to ask for Notification
      // permission so the end-of-Pomodoro notification can fire.
      if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
    });
    $("#qb-pomo-reset").addEventListener("click", pomoReset);
    $$(".qb-pomo-dur").forEach(b => {
      b.addEventListener("click", () => pomoSetDuration(Number(b.dataset.min)));
    });
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

    // Pomodoro: hydrate from localStorage. If the timer was running
    // when the user closed the tab, the absolute end timestamp picks
    // up where they left off (or fires the end immediately if the
    // session has already elapsed).
    loadPomo();
    wirePomo();
    wireMoveModal();
    if (pomo.state === "running") {
      if (pomo.endsAt && pomo.endsAt > Date.now()) {
        startPomoTicker();
      } else {
        pomoEnd();
      }
    }
    renderPomo();

    const form = $("#qb-add-form");
    const input = $("#qb-add-input");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const v = input.value;
      input.value = "";
      await addItem(v);
      input.focus();
    });

    // ── Mic: dictate one task at a time (Web Speech API) ──
    // Single-shot mode (continuous=false, interimResults=false) — same
    // pattern the AI Assist page uses (static/js/ai_assist.js). One
    // press, one phrase, the engine ends on its own when you stop
    // talking, the task is added. To dictate another, press again.
    //
    // Hands-free toggle below adds a wake-word listener so saying
    // "start" triggers a dictation without tapping the button, and
    // "stop" cancels an in-flight dictation early.
    const VOICE_COMMIT_TRIGGERS = new Set(["add", "save", "done", "stop", "submit"]);
    const HANDSFREE_KEY = "qb-handsfree-v1";
    const WAKE_DEBOUNCE_MS = 2_000;
    // Wake phrases — plain English words the engine transcribes
    // reliably. "hello" begins a dictation, "bye" turns hands-free
    // off. The console.log("[qb wake] heard:", t) line in onresult
    // prints the live transcript so it's easy to verify the engine
    // is hearing what you say.
    const WAKE_START_RE = /\b(?:hello|helo|hallo)\b/i;
    const WAKE_STOP_RE  = /\b(?:bye|goodbye|bye-bye|bye bye)\b/i;
    const micBtn = $("#qb-mic-btn");
    const handsfreeBtn = $("#qb-handsfree-btn");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

    // Diagnostic logs so the user can see in the browser console
    // exactly what state the mic boot ended up in. If the listening
    // toggle "does nothing", look here first.
    console.log("[qb mic] boot",
      { hasMic: !!micBtn, hasHandsfree: !!handsfreeBtn, hasSR: !!SR });

    if (!SR) {
      micBtn.disabled = true;
      micBtn.title = "Dictation not supported in this browser";
      if (handsfreeBtn) {
        handsfreeBtn.disabled = true;
        handsfreeBtn.title = "Not supported in this browser";
      }
      // Tap-feedback even when disabled — surface why nothing happens.
      handsfreeBtn?.addEventListener("click", () => {
        toast("Speech Recognition isn't available in this browser", "error");
      });
    } else {
      let recognition = null;          // single-shot dictation recognizer
      let recognizing = false;
      let wakeRec = null;              // continuous wake-word recognizer
      let wakeRunning = false;
      let wakePending = false;         // "start" detected, awaiting onend
      let handsfreeOn = false;
      let lastWakeAt = 0;

      const stripTrigger = (text) => {
        const tokens = text.split(/\s+/).filter(Boolean);
        if (!tokens.length) return text;
        const last = tokens[tokens.length - 1].toLowerCase().replace(/[^a-z]/g, "");
        if (VOICE_COMMIT_TRIGGERS.has(last)) tokens.pop();
        return tokens.join(" ").trim();
      };

      // ── Single-shot dictation ───────────────────────────
      const startDictation = () => {
        if (recognizing) return;
        recognition = new SR();
        recognition.lang = navigator.language || "en-US";
        recognition.onresult = (e) => {
          const r = e.results && e.results[0];
          const transcript = ((r && r[0] && r[0].transcript) || "").trim();
          if (!transcript) return;
          const text = stripTrigger(transcript);
          if (!text) return;
          input.value = text;
          addItem(text);
          toast(`Added: ${text}`, "success");
          setTimeout(() => { if (input.value === text) input.value = ""; }, 800);
        };
        recognition.onend = () => {
          recognizing = false;
          micBtn.classList.remove("is-on");
          updateHandsfreeStatus();
          // Resume wake listening so the next "start" works.
          if (handsfreeOn) startWake();
        };
        recognition.onerror = (e) => {
          recognizing = false;
          micBtn.classList.remove("is-on");
          updateHandsfreeStatus();
          if (e.error && e.error !== "no-speech" && e.error !== "aborted") {
            toast(`Mic: ${e.error}`, "error");
          }
          if (handsfreeOn) startWake();
        };
        try {
          recognition.start();
          recognizing = true;
          micBtn.classList.add("is-on");
          updateHandsfreeStatus();
        } catch (_) { /* ignore double-start */ }
      };

      micBtn.addEventListener("click", () => {
        if (recognizing) {
          try { recognition?.stop(); } catch (_) {}
          return;
        }
        // Tapping the mic manually pauses hands-free for this dictation
        // — wake will resume from the dictation onend.
        stopWake();
        startDictation();
      });

      // ── Wake-word listener (continuous; opt-in) ─────────
      // Watches transcripts for "start" → triggers dictation.
      // For "stop": single-shot dictation ends on natural silence
      // anyway, but if the wake listener hears "stop" while a dictation
      // is in flight, abort the dictation early.
      const updateHandsfreeStatus = () => {
        const el = $("#qb-handsfree-status");
        const txt = $("#qb-handsfree-status-text");
        if (!el) return;
        if (handsfreeOn && wakeRunning) {
          el.removeAttribute("hidden");
          if (txt) txt.textContent = 'Listening — say "Hello" to dictate';
        } else if (handsfreeOn && recognizing) {
          el.removeAttribute("hidden");
          if (txt) txt.textContent = "Dictating…";
        } else {
          el.setAttribute("hidden", "");
        }
      };

      const startWake = () => {
        if (!handsfreeOn || wakeRunning || recognizing) return;
        wakeRunning = true;
        updateHandsfreeStatus();
        wakeRec = new SR();
        wakeRec.continuous = true;
        wakeRec.interimResults = true;
        wakeRec.lang = navigator.language || "en-US";

        wakeRec.onresult = (e) => {
          // Look at the latest result only — interim is enough since we
          // just need to spot the wake phrase. We don't accumulate text
          // here at all; the dictation recognizer captures the actual
          // task once "Hey Renga" has triggered it.
          for (let i = e.resultIndex; i < e.results.length; i++) {
            const t = (e.results[i][0].transcript || "").toLowerCase();
            // Log the heard text so the user can see what the engine
            // is producing — useful for tuning the wake-phrase regex.
            console.log("[qb wake] heard:", t);
            // "Bye" → turn off hands-free entirely.
            if (WAKE_STOP_RE.test(t)) {
              console.log("[qb wake] WAKE_STOP matched on:", t);
              setHandsfree(false);
              toast("Hands-free off", "info");
              return;
            }
            // "Hello" → kick off a single dictation.
            if (WAKE_START_RE.test(t)) {
              console.log("[qb wake] WAKE_START matched on:", t);
              const now = Date.now();
              if (now - lastWakeAt < WAKE_DEBOUNCE_MS) return;
              lastWakeAt = now;
              wakePending = true;
              try { wakeRec.stop(); } catch (_) {}
              return;
            }
          }
        };
        wakeRec.onend = () => {
          wakeRunning = false;
          wakeRec = null;
          updateHandsfreeStatus();
          if (wakePending) {
            wakePending = false;
            startDictation();
            return;
          }
          // Engine timed out on its own — restart so the listener
          // stays effectively always-on while the toggle is enabled.
          if (handsfreeOn && !recognizing) {
            setTimeout(startWake, 250);
          }
        };
        wakeRec.onerror = (e) => {
          wakeRunning = false;
          wakeRec = null;
          updateHandsfreeStatus();
          if (e.error === "not-allowed") {
            // User denied mic permission — auto-disable hands-free.
            setHandsfree(false);
            toast("Mic permission denied", "error");
            return;
          }
          if (handsfreeOn && !recognizing && e.error !== "aborted") {
            setTimeout(startWake, 500);
          }
        };
        try {
          wakeRec.start();
          console.log("[qb wake] started");
        } catch (e) {
          wakeRunning = false;
          updateHandsfreeStatus();
          console.error("[qb wake] start failed:", e);
          // Common cause: SpeechRecognition.start() called outside a
          // user gesture, which Chrome rejects. Surface the failure
          // so the toggle isn't a green-but-dead button.
          toast("Couldn't start mic — tap the toggle again", "error");
          handsfreeOn = false;
          if (handsfreeBtn) handsfreeBtn.classList.remove("is-on");
        }
      };
      const stopWake = () => {
        wakePending = false;
        if (wakeRec) {
          try { wakeRec.stop(); } catch (_) {}
        }
        updateHandsfreeStatus();
      };

      const setHandsfree = (on) => {
        handsfreeOn = on;
        try { localStorage.setItem(HANDSFREE_KEY, on ? "1" : "0"); } catch (_) {}
        if (handsfreeBtn) {
          handsfreeBtn.classList.toggle("is-on", on);
          handsfreeBtn.title = on
            ? 'Hands-free on — say "Hello" to dictate, "Bye" to stop'
            : 'Hands-free — say "Hello" to dictate';
        }
        if (on) {
          startWake();
          toast('Listening — say "Hello" to dictate', "info");
        } else {
          stopWake();
        }
      };

      if (handsfreeBtn) {
        handsfreeBtn.addEventListener("click", () => {
          console.log("[qb mic] handsfree toggle click; was on?", handsfreeOn);
          setHandsfree(!handsfreeOn);
        });
      } else {
        console.warn("[qb mic] handsfree button not found in DOM");
      }

      // We deliberately do NOT auto-restore from localStorage. Browsers
      // require a user gesture for the first SpeechRecognition.start();
      // a setTimeout-driven auto-start fires outside that gesture and
      // Chrome silently rejects it, leaving the toggle green-but-dead.
      // Instead, mark the toggle pre-armed if it was previously on, but
      // wait for the user's tap to actually wire up the mic.
      try {
        if (localStorage.getItem(HANDSFREE_KEY) === "1" && handsfreeBtn) {
          handsfreeBtn.title = 'Hands-free was on — tap to re-enable';
        }
      } catch (_) {}
    }

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

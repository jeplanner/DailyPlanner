/* prep-scheduler.js — put a prep topic on a day, from any bank page.
 *
 * Three pages carry a bank of study topics (/ai-sde, /java,
 * /interview-prep) and all three want the same thing: pick a topic, pick
 * a day, and have it land in that bank's project, on the calendar, and in
 * the Quick Bucket. This is that, once, rather than three copies that
 * drift the first time one of them is fixed.
 *
 * The pages do NOT share a card structure — the title lives in .q-text on
 * one and .t on another — so nothing here reads the DOM to find out what
 * it is scheduling. The button carries its own bank and title in data
 * attributes, and the panel is injected next to it. All a host page has
 * to do is put PrepScheduler.button(bank, title) in its card header and
 * call PrepScheduler.attach(listEl) once.
 *
 * CAPTURE PHASE, deliberately. Every host page has its own click handler
 * on the same container that opens and closes cards, and this button sits
 * inside the header that toggles them. Listening in the capture phase and
 * stopping propagation there means a press on Plan cannot also fold the
 * card shut, whichever listener was registered first.
 */
(function () {
  "use strict";

  var STYLE_ID = "prep-scheduler-css";

  var CSS = [
    /* The button. Drawn as a filled pill, not a bare glyph: it sits on a
       row that already carries several coloured chips, and a transparent
       icon among them reads as decoration rather than a control. */
    ".prep-plan-btn{flex:none;display:inline-flex;align-items:center;gap:5px;",
    "font:inherit;font-size:11.5px;font-weight:800;line-height:1;color:#fff;",
    "background:var(--color-primary,#2563eb);border:1px solid var(--color-primary,#2563eb);",
    "border-radius:999px;padding:7px 11px;cursor:pointer;white-space:nowrap;",
    "box-shadow:0 1px 2px rgba(0,0,0,.12)}",
    ".prep-plan-btn:hover{background:var(--color-primary-hover,#1d4ed8);",
    "border-color:var(--color-primary-hover,#1d4ed8)}",
    ".prep-plan-btn:active{transform:translateY(1px)}",
    ".prep-plan-btn:focus-visible{outline:3px solid var(--color-primary-ring,rgba(37,99,235,.18));outline-offset:1px}",
    ".prep-plan-btn.on{background:var(--color-surface,#fff);color:var(--color-primary,#2563eb);",
    "border-color:var(--color-border,#e5e7eb);box-shadow:none}",

    /* The panel, injected under the card header on first press. */
    ".prep-panel{display:flex;flex-wrap:wrap;gap:8px;align-items:center;",
    "margin:0 13px 11px;padding:10px;border:1px dashed var(--color-border,#e5e7eb);",
    "border-radius:10px;background:var(--color-bg,#f9fafb)}",
    ".prep-panel[hidden]{display:none}",
    ".prep-panel label{display:flex;align-items:center;gap:6px;font-size:12px;",
    "font-weight:700;color:var(--color-text-secondary,#6b7280)}",
    ".prep-panel input{font:inherit;font-size:13px;padding:6px 8px;min-width:0;",
    "border:1px solid var(--color-border,#e5e7eb);border-radius:8px;",
    "background:var(--color-surface,#fff);color:var(--color-text,#111827)}",
    ".prep-panel .prep-go{font:inherit;font-size:12.5px;font-weight:800;color:#fff;",
    "background:var(--color-primary,#2563eb);border:1px solid var(--color-primary,#2563eb);",
    "border-radius:10px;padding:7px 12px;cursor:pointer}",
    ".prep-panel .prep-go[disabled]{opacity:.6;cursor:default}",
    ".prep-msg{flex-basis:100%;font-size:11.5px;color:var(--color-text-secondary,#6b7280)}",
    ".prep-msg.ok{color:#047857;font-weight:700}",
    ".prep-msg.err{color:#b91c1c;font-weight:700}",
    "html.dark .prep-msg.ok{color:#6ee7b7}html.dark .prep-msg.err{color:#fca5a5}",

    /* Each field on its own line on a phone — a date picker squeezed
       beside a time picker at 360px leaves neither one tappable. */
    "@media (max-width:640px){.prep-panel label{flex-basis:100%}",
    ".prep-panel label input{flex:1}.prep-panel .prep-go{width:100%}}",
  ].join("");

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var el = document.createElement("style");
    el.id = STYLE_ID;
    el.textContent = CSS;
    document.head.appendChild(el);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* LOCAL date, not toISOString(). toISOString() converts to UTC first, so
     anywhere west of Greenwich it returns yesterday for most of the
     evening and the picker opens on the wrong day. */
  function todayISO() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function csrf() {
    var m = document.querySelector('meta[name=csrf-token]');
    return (m && m.content) || "";
  }

  function panelHTML() {
    return '<div class="prep-panel" hidden>' +
      '<label>Day <input type="date" class="prep-date" value="' + todayISO() + '"></label>' +
      '<label>Time <input type="time" class="prep-time"></label>' +
      '<button class="prep-go" type="button" data-prep-go>Put it on the calendar</button>' +
      '<span class="prep-msg">Leave the time blank and it sits at 12:00 AM, the top of that day. ' +
      'It lands in the prep project, the calendar and the Quick Bucket.</span>' +
      '</div>';
  }

  /* The panel goes directly after the card header, so it is the first
     thing under the title rather than below however much body the card
     turns out to have — on /ai-sde that body is a ten-section deep dive
     and a dozen worked examples, which is several screens of scrolling. */
  function panelFor(btn) {
    var card = btn.closest(".q-card") || btn.parentElement;
    if (!card) return null;
    var existing = card.querySelector(":scope > .prep-panel");
    if (existing) return existing;
    var head = card.querySelector(":scope > .q-head");
    var tmp = document.createElement("div");
    tmp.innerHTML = panelHTML();
    var panel = tmp.firstChild;
    if (head && head.nextSibling) card.insertBefore(panel, head.nextSibling);
    else card.appendChild(panel);
    return panel;
  }

  async function submit(btn, panel) {
    var msg = panel.querySelector(".prep-msg");
    var go = panel.querySelector("[data-prep-go]");
    var day = panel.querySelector(".prep-date").value;
    var time = panel.querySelector(".prep-time").value;
    if (!day) { msg.className = "prep-msg err"; msg.textContent = "Pick a day first."; return; }

    go.disabled = true;
    msg.className = "prep-msg";
    msg.textContent = "Adding…";
    try {
      var r = await fetch("/api/prep/schedule", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        // The title is what identifies the topic. Ids in every one of
        // these banks are POSITIONS (ai42, j7, q19) and shift the moment
        // an entry is added or deduped, so a tab left open across an edit
        // would otherwise schedule whatever moved into that slot. The id
        // rides along as a hint; the server lets the title decide.
        body: JSON.stringify({
          bank: btn.dataset.bank,
          id: btn.dataset.entryId || null,
          title: btn.dataset.title,
          plan_date: day,
          start_time: time,
        }),
      });
      var out = {};
      try { out = await r.json(); } catch (_) { }
      if (!r.ok) throw new Error(out.error || ("HTTP " + r.status));
      msg.className = "prep-msg ok";
      // "sending", not "sent": the Google mirror runs on a background
      // thread that outlives this response, so claiming it has arrived
      // would be a claim the server never made.
      msg.textContent = (out.status === "already-scheduled" ? "Already there — " : "Added — ") +
        (out.message || day) +
        (out.project ? " In " + out.project + "." : "") +
        (out.gcal_syncing ? " Sending it to Google Calendar too." : "");
      if (window.showToast) showToast(out.message || "Scheduled", "success");
    } catch (e) {
      msg.className = "prep-msg err";
      msg.textContent = "Could not schedule it: " + e.message;
    } finally {
      go.disabled = false;
    }
  }

  function show(btn, panel, open) {
    if (open) panel.removeAttribute("hidden"); else panel.setAttribute("hidden", "");
    btn.classList.toggle("on", open);
    if (open) {
      panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
      var d = panel.querySelector(".prep-date");
      if (d) d.focus();
    }
  }

  var PrepScheduler = {
    /* HTML for the header button. `title` is the topic text and is what
       actually identifies it to the server; `entryId` is optional and is
       only ever a hint. */
    button: function (bank, title, entryId) {
      return '<button class="prep-plan-btn" type="button" data-prep-plan' +
        ' data-bank="' + esc(bank) + '"' +
        ' data-title="' + esc(title) + '"' +
        (entryId ? ' data-entry-id="' + esc(entryId) + '"' : "") +
        ' title="Put this topic on a day" aria-label="Schedule this topic">' +
        '📅<span>Plan</span></button>';
    },

    /* Wire one list container. Safe to call more than once — a second
       call on the same element is ignored rather than doubling every
       click, which would fire two inserts per press. */
    attach: function (root) {
      if (!root || root.dataset.prepSchedulerBound) return;
      root.dataset.prepSchedulerBound = "1";
      injectStyles();

      root.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-prep-plan]");
        if (btn && root.contains(btn)) {
          ev.stopPropagation();
          ev.preventDefault();
          var panel = panelFor(btn);
          if (panel) show(btn, panel, panel.hasAttribute("hidden"));
          return;
        }
        var go = ev.target.closest("[data-prep-go]");
        if (go && root.contains(go)) {
          ev.stopPropagation();
          ev.preventDefault();
          var p = go.closest(".prep-panel");
          var owner = p.parentElement.querySelector("[data-prep-plan]");
          submit(owner, p);
          return;
        }
        // Typing in the date or time field must not reach the host page's
        // card toggle, which would fold the card shut mid-edit.
        if (ev.target.closest(".prep-panel") && root.contains(ev.target)) {
          ev.stopPropagation();
        }
      }, true);   // capture — see the header comment
    },
  };

  window.PrepScheduler = PrepScheduler;
})();

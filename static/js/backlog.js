/* Backlog — capture, then route.
 *
 * The page is the one place a task is allowed to land undecided, so the
 * two things it has to do well are: take a line with no ceremony, and get
 * that line out again to wherever it actually belongs.
 *
 * ONE POPOVER, NOT ONE PER ROW. A backlog is long by nature — sixty rows
 * each carrying a hidden menu is sixty menus' worth of layout for a
 * control that is used once and dismissed.
 *
 * INBOX AND REFERENCES ARE POSTED TO THEIR OWN ENDPOINTS. Both are URL
 * pipelines with metadata fetching and auto-categorising behind them.
 * Re-implementing a thinner version server-side would have produced rows
 * that looked like the real thing and were not, so the browser calls the
 * real route and then drops the backlog copy.
 */
(function () {
  "use strict";

  var msgEl   = document.querySelector("[data-bk-msg]");
  var menu    = document.querySelector("[data-bk-menu]");
  var capForm = document.querySelector("[data-bk-capture]");
  var capText = document.querySelector("[data-bk-text]");
  var addBtn  = document.querySelector("[data-bk-add]");

  var projects = [];
  try {
    var raw = document.querySelector("[data-bk-projects]");
    if (raw) projects = JSON.parse(raw.textContent) || [];
  } catch (e) { projects = []; }

  var URL_RE = /https?:\/\/\S+/i;

  function say(text, bad) {
    if (!msgEl) return;
    msgEl.textContent = text;
    msgEl.className = "bk-msg show " + (bad ? "err" : "ok");
    clearTimeout(say._t);
    say._t = setTimeout(function () { msgEl.className = "bk-msg"; }, 4000);
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw new Error(j.error || ("Server said " + r.status));
        return j;
      });
    });
  }

  /* ── counts ──────────────────────────────────────────────────────
     A number that does not move when the list does is worse than no
     number, because it is read as fact. */
  function bumpCounts(li, delta) {
    var sec = li.closest(".bk-sec");
    var group = li.closest(".bk-proj");
    [group, sec].forEach(function (scope) {
      if (!scope) return;
      var n = scope.querySelector(".bk-n");
      if (!n) return;
      var v = parseInt(n.textContent, 10);
      if (!isNaN(v)) n.textContent = Math.max(0, v + delta);
    });
    var total = document.querySelector(".bk-total");
    if (total) {
      var t = parseInt(total.textContent, 10);
      if (!isNaN(t)) {
        t = Math.max(0, t + delta);
        total.textContent = t + " item" + (t === 1 ? "" : "s");
      }
    }
  }

  function removeRow(li) {
    li.classList.add("going");
    bumpCounts(li, -1);
    setTimeout(function () {
      var list = li.parentNode;
      li.remove();
      // An empty list left behind reads as "nothing here" for the whole
      // section, which is not what happened.
      // ...except the capture list, which is where the next captured
      // item has to land. Removing it would make every later capture
      // fall back to a full page reload.
      if (list && !list.querySelector(".bk-item") &&
          !list.hasAttribute("data-bk-list-future")) {
        var holder = list.closest(".bk-proj") || list.closest(".bk-sec");
        if (holder) holder.remove();
      }
    }, 160);
  }

  /* ── the router popover ──────────────────────────────────────────── */
  var openFor = null;

  function closeMenu() {
    if (!menu) return;
    menu.hidden = true;
    menu.innerHTML = "";
    openFor = null;
  }

  function opt(label, fn) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", fn);
    return b;
  }

  function buildMenu(li) {
    menu.innerHTML = "";
    var kind = li.getAttribute("data-kind");
    var id   = li.getAttribute("data-id");
    var text = li.getAttribute("data-text") || "";

    var h = document.createElement("h4");
    h.textContent = "Send to";
    menu.appendChild(h);

    menu.appendChild(opt("Quick Bucket", function () {
      run(li, postJSON("/api/backlog/send",
                       { kind: kind, id: id, to: "quick" }),
          kind === "task"
            ? "Promoted, and dated for today so the project keeps it."
            : "Moved to the Quick Bucket.");
    }));

    // A project task is already IN a project and already counted there.
    // Offering to file it again, or to turn it into a note, would only
    // create a second version of work that already exists.
    if (kind !== "task") {
      if (projects.length) {
        var sel = document.createElement("select");
        var ph = document.createElement("option");
        ph.value = ""; ph.textContent = "Move to project…";
        sel.appendChild(ph);
        projects.forEach(function (p) {
          var o = document.createElement("option");
          o.value = p.project_id;
          o.textContent = p.name || "Untitled project";
          sel.appendChild(o);
        });
        sel.addEventListener("change", function () {
          if (!sel.value) return;
          run(li, postJSON("/api/backlog/send", {
            kind: kind, id: id, to: "project", project_id: sel.value,
          }), "Filed under " + sel.options[sel.selectedIndex].textContent + ".");
        });
        menu.appendChild(sel);
      }

      menu.appendChild(opt("Note", function () {
        run(li, postJSON("/api/backlog/send", { kind: kind, id: id, to: "note" }),
            "Saved as a note.");
      }));

      // Only when there is actually a link. Both destinations store a URL
      // and enrich it; handing them "call the plumber" would write a row
      // that can never be opened.
      var m = text.match(URL_RE);
      if (m) {
        var url = m[0];
        menu.appendChild(document.createElement("div")).className = "sep";
        menu.appendChild(opt("Inbox", function () {
          run(li, postJSON("/api/inbox", { url: url })
                    .then(function () {
                      return postJSON("/api/backlog/drop", { id: id });
                    }), "Saved to the Inbox.");
        }));
        menu.appendChild(opt("References", function () {
          run(li, postJSON("/references/add", { url: url, tags: [] })
                    .then(function () {
                      return postJSON("/api/backlog/drop", { id: id });
                    }), "Saved to References.");
        }));
      }
    }
  }

  function run(li, promise, okText) {
    closeMenu();
    li.classList.add("going");
    promise.then(function () {
      say(okText, false);
      removeRow(li);
    }).catch(function (err) {
      li.classList.remove("going");
      say(err.message || "That did not save.", true);
    });
  }

  function place(btn) {
    menu.hidden = false;
    var r = btn.getBoundingClientRect();
    var w = menu.offsetWidth;
    var left = Math.min(r.right - w, window.innerWidth - w - 10);
    menu.style.left = Math.max(10, left) + window.scrollX + "px";
    var top = r.bottom + 6;
    // Flip above when there is no room below, rather than running off the
    // bottom of a phone where nothing can reach it.
    if (top + menu.offsetHeight > window.innerHeight - 8 &&
        r.top - menu.offsetHeight - 6 > 8) {
      top = r.top - menu.offsetHeight - 6;
    }
    menu.style.top = top + window.scrollY + "px";
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest("[data-bk-send]") : null;
    if (btn) {
      ev.preventDefault();
      var li = btn.closest(".bk-item");
      if (openFor === li) { closeMenu(); return; }
      buildMenu(li);
      openFor = li;
      place(btn);
      return;
    }
    if (menu && !menu.hidden && !ev.target.closest("[data-bk-menu]")) closeMenu();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeMenu();
  });
  window.addEventListener("resize", closeMenu);

  /* ── capture ─────────────────────────────────────────────────────── */
  function capture() {
    var text = (capText && capText.value || "").trim();
    if (!text) { capText && capText.focus(); return; }
    addBtn.disabled = true;
    postJSON("/api/backlog/capture", { text: text })
      .then(function (res) {
        var made = (res && res.created) || [];
        capText.value = "";
        say(made.length === 1 ? "Added to the backlog."
                              : "Added " + made.length + " items.", false);
        // Reload only when there is no Future list to insert into — the
        // section is rendered server-side and does not exist on a page
        // that had nothing in it.
        var list = document.querySelector('.bk-sec [data-bk-list-future]');
        if (!list) { window.location.reload(); return; }
        made.forEach(function (row) { list.insertBefore(rowEl(row), list.firstChild); });
        bumpCounts(list, made.length);
      })
      .catch(function (err) { say(err.message || "Could not save.", true); })
      .then(function () { addBtn.disabled = false; capText && capText.focus(); });
  }

  function rowEl(row) {
    var li = document.createElement("li");
    li.className = "bk-item";
    li.setAttribute("data-kind", "bucket");
    li.setAttribute("data-id", row.id);
    li.setAttribute("data-text", row.text || "");
    var t = document.createElement("span");
    t.className = "t";
    t.textContent = row.text || "";
    li.appendChild(t);
    var b = document.createElement("button");
    b.type = "button";
    b.className = "bk-send";
    b.setAttribute("data-bk-send", "");
    b.textContent = "Send →";
    li.appendChild(b);
    return li;
  }

  if (capForm) {
    capForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      capture();
    });
  }
  // Ctrl/Cmd+Enter submits, because the textarea has to keep plain Enter
  // for pasting and typing multi-line lists.
  if (capText) {
    capText.addEventListener("keydown", function (ev) {
      if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
        ev.preventDefault();
        capture();
      }
    });
  }
})();

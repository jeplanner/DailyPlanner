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
  var capMins = document.querySelector("[data-bk-mins]");
  var capDays = document.querySelector("[data-bk-days]");

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

  /* WHAT EACH DESTINATION NEEDS TO BE TOLD.

     A one-tap move looked tidy and produced untriaged rows somewhere else:
     a bucket item with no "when", a project task with no due date, a link
     with no tags. Every destination asks for the few things it actually
     uses, pre-filled from the captured line, and nothing more. */
  var BUCKETS = [
    ["now", "Now"], ["5m", "In 5 minutes"], ["15m", "In 15 minutes"],
    ["30m", "In 30 minutes"], ["45m", "In 45 minutes"], ["1h", "In an hour"],
    ["2h", "In 2 hours"], ["3h", "In 3 hours"], ["4h", "In 4 hours"],
    ["6h", "In 6 hours"], ["8h", "In 8 hours"],
  ];

  function fld(label, node) {
    var l = document.createElement("label");
    l.className = "bk-fld";
    var s = document.createElement("span");
    s.textContent = label;
    l.appendChild(s);
    l.appendChild(node);
    return l;
  }

  function input(name, value, type) {
    var i = document.createElement("input");
    i.type = type || "text";
    i.name = name;
    i.value = value || "";
    return i;
  }

  function select(name, pairs, value) {
    var sel = document.createElement("select");
    sel.name = name;
    pairs.forEach(function (p) {
      var o = document.createElement("option");
      o.value = p[0];
      o.textContent = p[1];
      if (p[0] === value) o.selected = true;
      sel.appendChild(o);
    });
    return sel;
  }

  function area(name, value) {
    var t = document.createElement("textarea");
    t.name = name;
    t.value = value || "";
    return t;
  }

  function two(a, b) {
    var d = document.createElement("div");
    d.className = "bk-two";
    d.appendChild(a); d.appendChild(b);
    return d;
  }

  function firstUrl(text) {
    var m = (text || "").match(URL_RE);
    return m ? m[0] : "";
  }

  /* Each builder returns {title, why, fields(form), submit(values)}. */
  var DESTS = {
    quick: function (li, text, kind) {
      return {
        title: "Move to the Quick Bucket",
        why: "The Quick Bucket is what you have prioritised to do. When it " +
             "is due is the decision being made here — everything landing " +
             "on \u201cNow\u201d just moves the pile.",
        build: function (form) {
          form.appendChild(fld("Task", input("text", text)));
          form.appendChild(fld("When", select("bucket", BUCKETS, "now")));
        },
        submit: function (v) {
          return postJSON("/api/backlog/send", {
            kind: kind, id: li.getAttribute("data-id"), to: "quick",
            text: v.text, bucket: v.bucket,
          });
        },
        ok: function (v) {
          var lab = BUCKETS.filter(function (b) { return b[0] === v.bucket; })[0];
          return "In the Quick Bucket \u2014 " +
                 (lab ? lab[1].toLowerCase() : v.bucket) + ".";
        },
      };
    },

    project: function (li, text) {
      return {
        title: "File under a project",
        why: "It lands with the project's own backlog status, so it is work " +
             "to be planned rather than work already underway.",
        build: function (form) {
          form.appendChild(fld("Project", select("project_id",
            projects.map(function (p) {
              return [String(p.project_id), p.name || "Untitled project"];
            }), "")));
          form.appendChild(fld("Task", input("text", text)));
          form.appendChild(two(
            fld("Due date (optional)", input("due_date", "", "date")),
            fld("Priority", select("priority",
              [["medium", "Medium"], ["high", "High"], ["low", "Low"]],
              "medium"))));
        },
        submit: function (v) {
          if (!v.project_id) throw new Error("Pick a project");
          return postJSON("/api/backlog/send", {
            kind: "bucket", id: li.getAttribute("data-id"), to: "project",
            project_id: v.project_id, text: v.text,
            due_date: v.due_date, priority: v.priority,
          });
        },
        ok: function () { return "Filed under the project."; },
      };
    },

    note: function (li, text) {
      return {
        title: "Save as a note",
        why: "For something that is not a task at all \u2014 a thought, a " +
             "reference, a paragraph you want to keep.",
        build: function (form) {
          form.appendChild(fld("Title", input("title", text.slice(0, 120))));
          form.appendChild(fld("Note", area("content", text)));
          form.appendChild(fld("Notebook", input("notebook", "Backlog")));
        },
        submit: function (v) {
          return postJSON("/api/backlog/send", {
            kind: "bucket", id: li.getAttribute("data-id"), to: "note",
            title: v.title, content: v.content, notebook: v.notebook,
          });
        },
        ok: function () { return "Saved as a note."; },
      };
    },

    inbox: function (li, text) {
      return {
        title: "Save to the Inbox",
        why: "The Inbox fetches the page title and works out its type and " +
             "category itself. A description here only overrides what it " +
             "would have written.",
        build: function (form) {
          form.appendChild(fld("Link", input("url", firstUrl(text), "url")));
          form.appendChild(fld("Description (optional)", area("description", "")));
        },
        submit: function (v) {
          if (!v.url) throw new Error("A link is required");
          var id = li.getAttribute("data-id");
          return postJSON("/api/inbox", { url: v.url, description: v.description })
            .then(function () { return postJSON("/api/backlog/drop", { id: id }); });
        },
        ok: function () { return "Saved to the Inbox."; },
      };
    },

    reference: function (li, text) {
      return {
        title: "Save to References",
        why: "Tags are how references are found again, and the category is " +
             "guessed from them when you leave it blank.",
        build: function (form) {
          form.appendChild(fld("Link", input("url", firstUrl(text), "url")));
          form.appendChild(fld("Tags (comma separated)", input("tags", "")));
          form.appendChild(fld("Category (optional)", input("category", "")));
        },
        submit: function (v) {
          if (!v.url) throw new Error("A link is required");
          var id = li.getAttribute("data-id");
          var tags = (v.tags || "").split(",").map(function (t) {
            return t.trim();
          }).filter(Boolean);
          return postJSON("/references/add", {
            url: v.url, tags: tags, category: v.category || null,
          }).then(function () { return postJSON("/api/backlog/drop", { id: id }); });
        },
        ok: function () { return "Saved to References."; },
      };
    },
  };

  /* ── the dialog ──────────────────────────────────────────────────── */
  var modal = document.querySelector("[data-bk-modal]");
  var backdrop = document.querySelector("[data-bk-back]");
  var lastFocus = null;

  function closeDialog() {
    if (!modal) return;
    modal.hidden = true;
    backdrop.hidden = true;
    modal.innerHTML = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
    lastFocus = null;
  }

  function openDialog(li, destKey) {
    var kind = li.getAttribute("data-kind");
    var text = li.getAttribute("data-text") || "";
    var spec = DESTS[destKey](li, text, kind);

    lastFocus = document.activeElement;
    modal.innerHTML = "";

    var h = document.createElement("h3");
    h.id = "bk-modal-title";
    h.textContent = spec.title;
    modal.appendChild(h);

    var why = document.createElement("p");
    why.className = "why";
    why.textContent = spec.why;
    modal.appendChild(why);

    var err = document.createElement("p");
    err.className = "bk-err";
    modal.appendChild(err);

    var form = document.createElement("form");
    spec.build(form);

    var acts = document.createElement("div");
    acts.className = "bk-acts";
    var cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "bk-btn ghost";
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", closeDialog);
    var go = document.createElement("button");
    go.type = "submit";
    go.className = "bk-btn";
    go.textContent = spec.title.split(" ")[0] === "Move" ? "Move" : "Save";
    acts.appendChild(cancel);
    acts.appendChild(go);
    form.appendChild(acts);

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var v = {};
      Array.prototype.forEach.call(form.elements, function (el) {
        if (el.name) v[el.name] = el.value;
      });
      var p;
      try {
        p = spec.submit(v);
      } catch (e) {
        err.textContent = e.message;
        err.className = "bk-err show";
        return;
      }
      go.disabled = true;
      closeDialog();
      run(li, p, spec.ok(v));
    });

    modal.appendChild(form);
    backdrop.hidden = false;
    modal.hidden = false;
    var first = form.querySelector("input, select, textarea");
    if (first) first.focus();
  }

  function buildMenu(li) {
    menu.innerHTML = "";
    var kind = li.getAttribute("data-kind");
    var text = li.getAttribute("data-text") || "";

    var h = document.createElement("h4");
    h.textContent = "Send to";
    menu.appendChild(h);

    menu.appendChild(opt("Quick Bucket", function () {
      closeMenu(); openDialog(li, "quick");
    }));

    // A project task is already IN a project and already counted there.
    // Offering to file it again, or to turn it into a note, would only
    // create a second version of work that already exists.
    if (kind !== "task") {
      if (projects.length) {
        menu.appendChild(opt("A project", function () {
          closeMenu(); openDialog(li, "project");
        }));
      }
      menu.appendChild(opt("Note", function () {
        closeMenu(); openDialog(li, "note");
      }));

      // Only when there is actually a link. Both destinations store a URL
      // and enrich it; handing them "call the plumber" would write a row
      // that can never be opened.
      if (URL_RE.test(text)) {
        var sep = document.createElement("div");
        sep.className = "sep";
        menu.appendChild(sep);
        menu.appendChild(opt("Inbox", function () {
          closeMenu(); openDialog(li, "inbox");
        }));
        menu.appendChild(opt("References", function () {
          closeMenu(); openDialog(li, "reference");
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
    if (modal && !modal.hidden) return;
    if (menu && !menu.hidden && !ev.target.closest("[data-bk-menu]")) closeMenu();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    if (modal && !modal.hidden) { closeDialog(); return; }
    closeMenu();
  });
  // mousedown, not click: a drag that starts inside the dialog and ends on
  // the backdrop fires a click whose target is the backdrop, and would shut
  // a form mid-edit.
  if (backdrop) backdrop.addEventListener("mousedown", closeDialog);
  window.addEventListener("resize", closeMenu);

  /* ── capture ─────────────────────────────────────────────────────── */
  function capture() {
    var text = (capText && capText.value || "").trim();
    if (!text) { capText && capText.focus(); return; }
    var dated = !!(capDays && capDays.value) || !!(capMins && capMins.value);
    addBtn.disabled = true;
    postJSON("/api/backlog/capture", {
      text: text,
      minutes: capMins && capMins.value ? parseInt(capMins.value, 10) : 0,
      days: capDays && capDays.value ? parseInt(capDays.value, 10) : 0,
    })
      .then(function (res) {
        var made = (res && res.created) || [];
        capText.value = "";
        if (capMins) capMins.value = "";
        if (capDays) capDays.value = "";
        say(made.length === 1 ? "Added to the backlog."
                              : "Added " + made.length + " items.", false);
        // A DEADLINE CHANGES WHERE THE ROW BELONGS. The list is sorted
        // late-first, then by time remaining, so a dated capture inserted
        // at the top would be sitting in the wrong place until the next
        // load — and the whole point of the date is the ordering it buys.
        // Undated captures still go straight in, which is the fast path
        // that matters when emptying your head one line at a time.
        if (dated) { window.location.reload(); return; }
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

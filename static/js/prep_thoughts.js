/* prep_thoughts.js — the "Random thoughts" tab of the Interview Prep hub.
 *
 * A place for the questions that come to mind while preparing ("why is
 * Kafka ordered only per partition?", "what does a Director actually own
 * that an EM doesn't?"). Each is answered in depth by the server — short
 * answer, intuition, how it works, a worked example, misconceptions, how to
 * say it in an interview, takeaways, and self-check questions — and kept.
 *
 * Answers are written in the background (they take up to a minute), so a
 * new question shows as "Writing…" and the list polls until it is ready.
 * Follow-ups ("Explain simpler", "Go deeper", or your own) stay threaded
 * under the original question. Your own notes can sit under any question
 * or follow-up — what you'd say differently, where it came up, a link.
 */
(function () {
  "use strict";
  var H = function () { return window.PrepHub; };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return H().esc(s); };
  // Two shelves share this code: Interview Prep ("tpm") and AI SDE Prep
  // ("aisde"). The page says which one via data-shelf on #th-view.
  var SHELF = (function () { var v = document.getElementById("th-view"); return (v && v.dataset.shelf) || "tpm"; })();
  var STUDENT = SHELF === "aisde";
  var Q = "?shelf=" + SHELF;
  var CATS = [];           // [[slug, name], ...] in study order, from the server
  // interview_prep_bp is not CSRF-exempt: every write carries the token.
  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  function api(path, opts) {
    opts = opts || {};
    return fetch(path, Object.assign({ credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF } }, opts))
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.error || "Something went wrong");
          return j;
        });
      });
  }

  var ITEMS = [], available = true, provider = true, started = false;
  var view = { q: "", filter: "all", order: "study" };
  var open = {};            // root id -> expanded
  var editing = null;       // id whose answer is being edited
  var asking = null;        // root id with the follow-up box open
  var askQuote = null;      // {text, parentId} when the follow-up is about a selected sentence
  var pollTimer = null;
  var notesOk = true;       // false until the notes column exists
  var noteDraft = null;     // {tid, nid}: the note box that is open (nid null = new note)
  var noteText = "";        // its text, kept so a poll's re-render doesn't lose it
  var quizCache = {};      // step -> [mcq]
  var quizOpen = {};       // root id -> quiz shown
  var REVIEW_DAYS = [1, 3, 7, 14, 30, 60, 120];   // mirrors thoughts_service.REVIEW_DAYS

  /* ── A small, safe Markdown renderer ─────────────────────────────────
     Escapes everything first, then recognises: ## headings, ``` code
     blocks, - / * / 1. lists, | tables |, **bold**, *italic*, `code`, and
     "Answer:" lines (turned into tap-to-reveal, for the self-check). */
  function inline(t) {
    return t.replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
            .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>");
  }
  function md(src) {
    var lines = esc(src || "").split("\n"), out = [], i = 0;
    function para(buf) { if (buf.length) out.push("<p>" + inline(buf.join(" ")) + "</p>"); }
    var buf = [];
    while (i < lines.length) {
      var l = lines[i];
      if (/^\s*```/.test(l)) {
        para(buf); buf = [];
        var isMermaid = /^\s*```\s*mermaid\b/i.test(l);
        var isAnim = /^\s*```\s*anim\b/i.test(l);
        var code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
        // A ```mermaid block is drawn as a diagram after render (drawDiagrams);
        // the source stays inside as the fallback if it can't be drawn.
        // A ```anim block (JSON, already escaped) becomes a step-by-step
        // animated diagram via flow_anim.js.
        out.push(isAnim
          ? '<div class="fa-anim" data-spec="' + code.join("\n") + '"><p class="mini-lbl">Loading animation…</p></div>'
          : isMermaid
          ? '<div class="th-mermaid"><pre class="th-code">' + code.join("\n") + "</pre></div>"
          : '<pre class="th-code">' + code.join("\n") + "</pre>");
        i++; continue;
      }
      var h = l.match(/^\s*(#{1,6})\s+(.*)$/);
      if (h) { para(buf); buf = []; var lv = Math.min(5, h[1].length + 2); out.push("<h" + lv + ">" + inline(h[2]) + "</h" + lv + ">"); i++; continue; }
      if (/^\s*\|.*\|\s*$/.test(l)) {
        para(buf); buf = [];
        var rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(lines[i]); i++; }
        var cells = function (r) { return r.trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return inline(c.trim()); }); };
        var body = rows.filter(function (r) { return !/^\s*\|[\s:|-]+\|\s*$/.test(r); });
        out.push('<div class="th-tablewrap"><table class="th-table"><thead><tr>' + cells(body[0]).map(function (c) { return "<th>" + c + "</th>"; }).join("") +
          "</tr></thead><tbody>" + body.slice(1).map(function (r) { return "<tr>" + cells(r).map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>"; }).join("") +
          "</tbody></table></div>");
        continue;
      }
      var ans = l.match(/^\s*(?:\*\*)?Answer:(?:\*\*)?\s*(.*)$/i);
      if (ans) { para(buf); buf = []; out.push('<details class="th-reveal"><summary>Show answer</summary><div>' + inline(ans[1]) + "</div></details>"); i++; continue; }
      if (/^\s*([-*•]|\d+[.)])\s+/.test(l)) {
        para(buf); buf = [];
        var ordered = /^\s*\d+[.)]\s+/.test(l), items = [];
        while (i < lines.length && /^\s*([-*•]|\d+[.)])\s+/.test(lines[i])) {
          var item = lines[i].replace(/^\s*([-*•]|\d+[.)])\s+/, ""); i++;
          var reveal = "";
          // Continuation lines of the same item; an indented "Answer:" line
          // under a self-check question becomes its tap-to-reveal answer.
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*•]|\d+[.)])\s+/.test(lines[i])) {
            var cont = lines[i].trim(), ca = cont.match(/^(?:\*\*)?Answer:(?:\*\*)?\s*(.*)$/i);
            if (ca) reveal += '<details class="th-reveal"><summary>Show answer</summary><div>' + inline(ca[1]) + "</div></details>";
            else if (reveal) reveal = reveal.replace(/<\/div><\/details>$/, " " + inline(cont) + "</div></details>");
            else item += " " + cont;
            i++;
          }
          var a2 = item.match(/^(?:\*\*)?Answer:(?:\*\*)?\s*(.*)$/i);
          items.push((a2 ? '<details class="th-reveal"><summary>Show answer</summary><div>' + inline(a2[1]) + "</div></details>" : inline(item)) + reveal);
        }
        out.push((ordered ? "<ol>" : "<ul>") + items.map(function (x) { return "<li>" + x + "</li>"; }).join("") + (ordered ? "</ol>" : "</ul>"));
        continue;
      }
      if (!l.trim()) { para(buf); buf = []; i++; continue; }
      buf.push(l.trim()); i++;
    }
    para(buf);
    return out.join("");
  }

  /* ── Diagrams (Mermaid, self-hosted, loaded only when needed) ──────── */
  var MERMAID_SRC = "/static/js/vendor/mermaid-10.9.1.min.js";
  var mermaidReady = null, mmCount = 0;
  function isDark() {
    var h = document.documentElement;
    if (h.classList.contains("dark")) return true;
    if (h.classList.contains("light")) return false;
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function loadMermaid() {
    if (mermaidReady) return mermaidReady;
    mermaidReady = new Promise(function (res, rej) {
      if (window.mermaid) return res(window.mermaid);
      var sc = document.createElement("script");
      sc.src = MERMAID_SRC; sc.async = true;
      sc.onload = function () { res(window.mermaid); };
      sc.onerror = function () { mermaidReady = null; rej(new Error("diagram library failed to load")); };
      document.head.appendChild(sc);
    }).then(function (m) {
      // "strict" escapes labels and disables click handlers: answers are
      // AI-written text, so nothing in a diagram may run script.
      // Label backgrounds match the diagram panel, so arrow labels don't sit
      // in grey boxes on either theme.
      // The token is a light-dark() pair, so resolve it to a real colour by
      // painting it on a throwaway element.
      var panelBg = "";
      try {
        var probe = document.createElement("div");
        probe.style.background = "var(--color-surface-secondary)";
        document.body.appendChild(probe);
        panelBg = getComputedStyle(probe).backgroundColor;
        probe.remove();
      } catch (_) {}
      m.initialize({ startOnLoad: false, securityLevel: "strict",
                     theme: isDark() ? "dark" : "neutral", fontFamily: "inherit",
                     themeVariables: /^rgb/.test(panelBg) ? { edgeLabelBackground: panelBg } : {} });
      return m;
    });
    return mermaidReady;
  }
  function drawDiagrams(root) {
    var blocks = (root || document).querySelectorAll(".th-mermaid:not([data-drawn])");
    if (!blocks.length) return;
    loadMermaid().then(function (m) {
      Array.prototype.forEach.call(blocks, function (b) {
        if (b.getAttribute("data-drawn")) return;
        b.setAttribute("data-drawn", "1");
        var src = (b.querySelector("pre") || b).textContent;
        m.render("thmm" + (++mmCount), src).then(function (out) {
          b.innerHTML = '<div class="th-svg">' + out.svg + "</div>" +
            '<div class="th-mm-bar"><button type="button" class="th-mm-full">Open full size</button>' +
            '<details class="th-src"><summary>Diagram source</summary><pre class="th-code"></pre></details></div>';
          b.querySelector(".th-src pre").textContent = src;
        }).catch(function () {
          b.classList.add("bad");
          var note = document.createElement("div");
          note.className = "th-mm-note";
          note.textContent = "This diagram couldn't be drawn, so its text is shown. Use Edit to fix it.";
          b.appendChild(note);
          // Mermaid leaves an error element in the page on failure.
          var junk = document.getElementById("dthmm" + mmCount); if (junk) junk.remove();
        });
      });
    }).catch(function () { /* offline: the source stays readable */ });
  }

  // "Open full size": the diagram as its own page, for pinch-zoom on a phone.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".th-mm-full");
    if (!btn) return;
    var svg = btn.closest(".th-mermaid").querySelector(".th-svg svg");
    if (!svg) return;
    var bg = getComputedStyle(document.body).backgroundColor;
    var html = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<body style="margin:0;padding:16px;background:' + bg + '">' + svg.outerHTML + "</body>";
    var url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    window.open(url, "_blank", "noopener");
    setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
  });

  /* ── Images ──────────────────────────────────────────────────────── */
  var MAX_IMAGES = 6, MAX_BYTES = 5 * 1024 * 1024;
  var pendingFiles = [];          // attached in the ask box, not yet sent
  function imgUrl(im) { return "/interview-prep/thoughts/img/" + im.key; }
  function imagesBlock(t) {
    var ims = t.images || [];
    if (!ims.length) return "";
    return '<div class="th-imgs">' + ims.map(function (im) {
      return '<figure class="th-img"><a href="' + imgUrl(im) + '" target="_blank" rel="noopener">' +
        '<img loading="lazy" src="' + imgUrl(im) + '" alt="' + esc(im.name || "attached image") + '"></a>' +
        '<button class="th-img-x" type="button" data-th="img-del" data-key="' + esc(im.key) + '" aria-label="Remove image">×</button></figure>';
    }).join("") + "</div>";
  }
  function goodFiles(list) {
    var out = [];
    Array.prototype.forEach.call(list || [], function (f) {
      if (!/^image\/(png|jpe?g|webp|gif)$/i.test(f.type)) { H().say(f.name + ": only PNG, JPG, WebP or GIF", "error"); return; }
      if (f.size > MAX_BYTES) { H().say(f.name + " is over 5 MB", "error"); return; }
      out.push(f);
    });
    return out;
  }
  function paintPending() {
    var box = $("th-files");
    if (!box) return;
    box.hidden = !pendingFiles.length;
    box.innerHTML = pendingFiles.map(function (f, i) {
      return '<span class="th-chip"><img alt="" src="' + URL.createObjectURL(f) + '">' + esc(f.name || "pasted image") +
        '<button type="button" data-th="unattach" data-i="' + i + '" aria-label="Remove">×</button></span>';
    }).join("");
  }
  function upload(path, fields, files) {
    var fd = new FormData();
    Object.keys(fields || {}).forEach(function (k) { if (fields[k] != null) fd.append(k, fields[k]); });
    files.forEach(function (f, i) { fd.append("images", f, f.name || ("image-" + (i + 1) + ".png")); });
    return fetch(path, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": CSRF }, body: fd })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.error || "Upload failed");
          return j;
        });
      });
  }

  /* ── Data ────────────────────────────────────────────────────────── */
  function load() {
    if (!started) { started = true; shell(); }
    return api("/api/prep/thoughts" + Q).then(function (j) {
      available = j.available !== false;
      provider = j.provider !== false;
      notesOk = available && j.notes_available !== false;
      ITEMS = j.items || [];
      CATS = j.categories || CATS;
      if (!Object.keys(open).length) {
        var newest = roots()[0];
        if (newest) open[newest.id] = true;
      }
      render();
      schedulePoll();
      maybeReview();
    }).catch(function () {
      $("th-list").innerHTML = '<div class="card"><div class="empty">Couldn\'t load your thoughts.</div></div>';
    });
  }

  function schedulePoll() {
    clearTimeout(pollTimer);
    var pending = ITEMS.some(function (t) { return t.status === "pending"; });
    if (!pending) return;
    pollTimer = setTimeout(function () {
      var panel = document.querySelector("[data-panel=thoughts]");
      if (panel && !panel.hidden && !document.hidden) load(); else schedulePoll();
    }, 4000);
  }

  function roots() {
    return ITEMS.filter(function (t) { return !t.parent_id; });
  }
  function children(root) {
    // Hints (follow-ups saved on a highlight) are shown on their highlight,
    // not in the follow-up thread.
    return ITEMS.filter(function (t) { return t.parent_id && !t.highlight && (t.root_id === root.id); })
      .sort(function (a, b) { return (a.created_at || "").localeCompare(b.created_at || ""); });
  }

  /* ── Rendering ───────────────────────────────────────────────────── */
  function shell() {
    $("th-view").innerHTML =
      '<div class="card th-ask">' +
      '<label for="th-q" class="th-ask-lbl">What\'s on your mind?</label>' +
      '<textarea id="th-q" rows="3" maxlength="2000" placeholder="' + (STUDENT ? "e.g. How does attention work in a transformer? · When would I use a heap over a sorted array? · How does a chat app catch up after going offline?" : "e.g. What does a Director own that an EM doesn\'t? · When would I pick Cassandra over Postgres? · How does a CDN decide what to cache?") + '"></textarea>' +
      '<div class="th-more" id="th-more" hidden>' +
      '<textarea id="th-ctx" rows="2" maxlength="4000" placeholder="What prompted it? (optional) — where you saw it, what confused you"></textarea>' +
      '<input id="th-tags" maxlength="120" placeholder="Tags, comma-separated (optional) — ' + (STUDENT ? "dsa, ml" : "kafka, leadership") + '"></div>' +
      '<div class="th-files" id="th-files" hidden></div>' +
      '<input type="file" id="th-file" accept="image/png,image/jpeg,image/webp,image/gif" multiple hidden>' +
      '<div class="th-ask-row"><button class="btn sm ghost" id="th-more-btn" type="button">+ Context &amp; tags</button>' +
      '<button class="btn sm ghost" id="th-attach" type="button">+ Image</button>' +
      '<span class="mini-lbl th-hint">Ctrl/⌘ + Enter to ask</span>' +
      '<button class="btn primary" id="th-go" type="button">Ask</button></div>' +
      '<p class="mini-lbl th-how">Every answer comes back the same way: the short answer, the intuition, how it actually works, a worked example, common misconceptions, how to say it in an interview, key takeaways, and three questions to check yourself — with a diagram. Attach or paste a screenshot or whiteboard photo and it will be explained too.</p>' +
      "</div>" +
      '<div class="sync-note" id="th-note" hidden></div>' +
      '<div class="toolbar" style="margin-top:14px"><input type="search" id="th-search" placeholder="Search your questions and answers…" aria-label="Search thoughts">' +
      '<div class="round-chips th-filter" role="group" aria-label="Filter">' +
      '<button class="rchip" type="button" data-thf="all" aria-pressed="true">All <span class="n" id="thn-all"></span></button>' +
      '<button class="rchip" type="button" data-thf="todo" aria-pressed="false">Still unclear <span class="n" id="thn-todo"></span></button>' +
      '<button class="rchip" type="button" data-thf="pinned" aria-pressed="false">Pinned <span class="n" id="thn-pin"></span></button>' +
      '<button class="rchip" type="button" data-thf="campus" aria-pressed="false">Campus interview <span class="n" id="thn-campus"></span></button>' +
      '<button class="rchip" type="button" data-thf="studied" aria-pressed="false">Studied <span class="n" id="thn-studied"></span></button>' +
      '<button class="rchip" type="button" data-thf="due" aria-pressed="false">Due for review <span class="n" id="thn-due"></span></button></div>' +
      '<button class="btn sm" type="button" id="th-review-now" hidden>Review now</button>' +
      '<label class="th-order mini-lbl">Order <select id="th-order" aria-label="Order of questions"><option value="study">Study order, by topic</option><option value="new">Newest first</option></select></label></div>' +
      '<details class="card th-guide" id="th-guide"><summary>Suggested study order</summary><div id="th-guide-body"></div></details>' +
      '<div id="th-list"><div class="card"><div class="empty">Loading…</div></div></div>';
  }

  function render() {
    var ae = document.activeElement;
    var hadNoteFocus = wantNoteFocus || !!(ae && ae.matches && ae.matches("[data-th-note]"));
    wantNoteFocus = false;
    var note = $("th-note");
    if (!available) { note.hidden = false; note.textContent = "Random thoughts need MIGRATION_PREP_THOUGHTS.sql run in Supabase before questions can be saved" + (STUDENT ? " (re-run it if it was run before — it now adds the AI SDE shelf)." : "."); }
    else if (!provider) { note.hidden = false; note.textContent = "No AI provider is configured on the server, so questions will be saved but not answered. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY or GROQ_API_KEY."; }
    else note.hidden = true;

    var rs = roots();
    var q = view.q.toLowerCase();
    var unclear = rs.filter(function (r) { return !r.understood; }).length;
    var pinned = rs.filter(function (r) { return r.pinned; }).length;
    $("thn-all").textContent = rs.length; $("thn-todo").textContent = unclear; $("thn-pin").textContent = pinned;
    if ($("thn-campus")) $("thn-campus").textContent = rs.filter(function (r) { return r.campus; }).length;
    var dueN = dueList().length;
    if ($("thn-studied")) $("thn-studied").textContent = rs.filter(function (r) { return r.understood; }).length;
    if ($("thn-due")) $("thn-due").textContent = dueN || "";
    if ($("th-review-now")) { $("th-review-now").hidden = !dueN; $("th-review-now").textContent = "Review now (" + dueN + ")"; }
    paintGuide(rs);
    if ($("tn-th")) $("tn-th").textContent = rs.length || "";
    var list = rs.filter(function (r) {
      if (view.filter === "todo" && r.understood) return false;
      if (view.filter === "pinned" && !r.pinned) return false;
      if (view.filter === "campus" && !r.campus) return false;
      if (view.filter === "studied" && !r.understood) return false;
      if (view.filter === "due" && !isDue(r)) return false;
      if (!q) return true;
      return [r].concat(children(r)).some(function (t) {
        return ((t.question || "") + " " + (t.answer || "") + " " + (t.tags || []).join(" ") + " " +
          notesOf(t).map(function (n) { return n.text; }).join(" ")).toLowerCase().indexOf(q) >= 0;
      });
    }).sort(function (a, b) {
      if (view.order === "study") {
        // Your own questions first (newest first), then the shipped ones in study order.
        var sa = a.step || 0, sb = b.step || 0;
        if (!sa || !sb) return (!sa && sb) ? -1 : (sa && !sb) ? 1 : (b.created_at || "").localeCompare(a.created_at || "");
        return sa - sb;
      }
      return (b.pinned - a.pinned) || (b.created_at || "").localeCompare(a.created_at || "");
    });

    var names = {}; CATS.forEach(function (c) { names[c[0]] = c[1]; });
    var lastCat = null, html = list.map(function (r) {
      var head = "";
      if (view.order === "study") {
        var cat = r.category || "_mine";
        if (cat !== lastCat) {
          lastCat = cat;
          head = '<h3 class="th-group" id="th-cat-' + esc(cat) + '">' + esc(cat === "_mine" ? "Your questions" : (names[cat] || cat)) + "</h3>";
        }
      }
      return head + thread(r);
    }).join("");
    $("th-list").innerHTML = html ||
      '<div class="card"><div class="empty">' + (rs.length ? "Nothing matches." :
        (STUDENT ? "No questions yet. The next time something doesn't quite make sense — a concept, an algorithm, a design choice — write it above." : "No questions yet. The next time something doesn't quite make sense — a concept, a design choice, a leadership situation — write it above.")) + "</div></div>";
    drawDiagrams($("th-list"));
    paintHighlights($("th-list"));
    if (window.FlowAnim) window.FlowAnim.init($("th-list"));
    if (window.feather) window.feather.replace();
    // A re-render (the poll, another click) rebuilt the open note box: put
    // the cursor back where it was so typing just carries on.
    var nb = document.querySelector("[data-th-note]");
    if (nb && hadNoteFocus && noteFocus) {
      nb.focus();
      try { nb.setSelectionRange(noteFocus[0], noteFocus[1]); } catch (_) {}
      nb.style.height = "auto"; nb.style.height = Math.min(nb.scrollHeight + 2, 520) + "px";
    }
  }
  var noteFocus = null;     // [start, end] of the cursor in the open note box
  var wantNoteFocus = false; // the box was just opened: focus it on this render

  function when(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  }

  function answerBlock(t) {
    if (editing === t.id) {
      return '<div class="th-edit"><textarea data-th-edit rows="16">' + esc(t.answer || "") + "</textarea>" +
        '<p class="mini-lbl">Markdown works: ## headings, **bold**, lists, tables. A ```mermaid block becomes a diagram.</p>' +
        '<div class="q-actions"><button class="btn sm primary" data-th="save-edit" type="button">Save answer</button>' +
        '<button class="btn sm" data-th="insert-flow" type="button">+ Flow diagram</button>' +
        '<button class="btn sm" data-th="insert-seq" type="button">+ Sequence diagram</button>' +
        '<button class="btn sm" data-th="cancel-edit" type="button">Cancel</button></div></div>';
    }
    if (t.status === "pending") {
      return '<div class="th-writing"><span class="th-spin" aria-hidden="true"></span>Writing a detailed answer — this takes up to a minute. You can keep studying; it will appear here.</div>';
    }
    if (t.status === "failed") {
      return '<div class="th-failed">' + esc(t.error || "The answer could not be written.") + "</div>" +
        '<div class="q-actions"><button class="btn sm primary" data-th="retry" type="button">Try again</button>' +
        '<button class="btn sm" data-th="edit" type="button">Write it myself</button></div>';
    }
    return '<div class="th-answer" data-tid="' + esc(t.id) + '">' + md(t.answer) + "</div>" + hintList(t);
  }

  /* ── Your notes ──────────────────────────────────────────────────── */
  function notesOf(t) { return (t && t.notes) || []; }
  function noteBox(t, nid, text) {
    return '<div class="th-nbox"><textarea data-th-note rows="3" maxlength="5000" placeholder="Your note — what you\'d say differently, where this came up, what to revisit…">' +
      esc(text) + "</textarea>" +
      '<div class="q-actions"><button class="btn sm primary" data-th="note-save" type="button">' + (nid ? "Save note" : "Add note") + "</button>" +
      '<button class="btn sm" data-th="note-cancel" type="button">Cancel</button>' +
      '<span class="mini-lbl th-hint">Ctrl/⌘ + Enter to save</span></div></div>';
  }
  function notesBlock(t) {
    if (!notesOk || t.seed) return "";
    var ns = notesOf(t);
    var draft = noteDraft && noteDraft.tid === t.id ? noteDraft : null;
    var list = ns.map(function (n) {
      if (draft && draft.nid === n.id) return noteBox(t, n.id, noteText);
      var edited = n.updated_at && n.updated_at !== n.created_at;
      return '<div class="th-note" data-nid="' + esc(n.id) + '"><div class="th-note-text">' + esc(n.text) + "</div>" +
        '<div class="th-note-meta"><span>' + when(n.created_at) + (edited ? " · edited " + when(n.updated_at) : "") + "</span>" +
        '<button class="th-note-btn" data-th="note-edit" data-nid="' + esc(n.id) + '" type="button">Edit</button>' +
        '<button class="th-note-btn" data-th="note-del" data-nid="' + esc(n.id) + '" type="button">Delete</button></div></div>';
    }).join("");
    var adding = draft && !draft.nid;
    return '<div class="th-notes">' +
      (ns.length ? '<div class="th-notes-k">Your notes</div>' + list : "") +
      (adding ? noteBox(t, null, noteText)
              : '<button class="btn sm ghost th-note-add" data-th="note-add" type="button">+ Add a note</button>') +
      "</div>";
  }

  function relatedBlock(r) {
    if (!r.related || !r.related.length) return "";
    return '<div class="th-related"><b>Related questions</b>' + r.related.map(function (x) {
      return '<button type="button" class="rchip" data-th="goto" data-q="' + esc(x.question) + '">' + esc(x.title) + "</button>";
    }).join("") + "</div>";
  }

  function paintGuide(rs) {
    var body = $("th-guide-body");
    if (!body || !CATS.length) return;
    var counts = {}, campus = {};
    rs.forEach(function (r) { if (!r.category) return; counts[r.category] = (counts[r.category] || 0) + 1; if (r.campus) campus[r.category] = (campus[r.category] || 0) + 1; });
    body.innerHTML = '<p class="mini-lbl">Work through the topics top to bottom; the numbers on each question are the order to read them in. ' +
      '<b>Campus interviews:</b> turn on the "Campus interview" filter and skip the Experienced-level ones. ' +
      '<b>Experienced roles:</b> do everything, and spend most time on system design, reliability and AI engineering.</p><ol class="th-guide-list">' +
      CATS.filter(function (c) { return counts[c[0]]; }).map(function (c) {
        return '<li><a href="#th-cat-' + esc(c[0]) + '" data-th-cat="' + esc(c[0]) + '">' + esc(c[1]) + "</a> <span class=\"mini-lbl\">" +
          counts[c[0]] + " questions, " + (campus[c[0]] || 0) + " for campus</span></li>";
      }).join("") + "</ol>";
  }

  function thread(r) {
    var kids = children(r);
    var isOpen = !!open[r.id];
    var pending = [r].concat(kids).some(function (t) { return t.status === "pending"; });
    var head = '<div class="q-head th-head" data-th="toggle">' +
      '<span class="q-text">' + (r.step ? '<span class="th-step">' + r.step + "</span>" : "") + esc(r.question) + "</span>" +
      '<span class="q-meta">' + (r.status === "ready" ? '<button type="button" class="th-studied' + (r.understood ? " on" : "") + '" data-th="understood" aria-pressed="' + (r.understood ? "true" : "false") + '" title="' + (r.understood ? "Studied - tap to unmark" : "Mark as studied") + '">' + (r.understood ? "✓ Studied" : "Mark studied") + "</button>" : "") +
      reviewBadge(r) +
      (r.step ? (r.campus ? '<span class="badge th-campus">Campus interview</span>' : '<span class="badge th-exp">Experienced-level</span>') : "") + (r.pinned ? '<span class="badge P1">pinned</span>' : "") +
      (pending ? '<span class="badge P2">writing…</span>' : r.status === "failed" ? '<span class="badge P0">failed</span>' :
        "") +
      (kids.length ? '<span class="badge">' + kids.length + " follow-up" + (kids.length === 1 ? "" : "s") + "</span>" : "") +
      (function () {
        var n = [r].concat(kids).reduce(function (c, t) { return c + notesOf(t).length; }, 0);
        return n ? '<span class="badge th-nbadge">' + n + " note" + (n === 1 ? "" : "s") + "</span>" : "";
      })() +
      (r.tags || []).map(function (g) { return '<span class="badge">#' + esc(g) + "</span>"; }).join("") +
      '<span class="badge">' + when(r.created_at) + "</span></span></div>";
    if (!isOpen) return '<div class="q-card th-card' + (r.understood ? " done" : "") + '" data-id="' + r.id + '">' + head + "</div>";

    var body = (r.context ? '<div class="th-ctx"><b>What prompted it</b>' + esc(r.context) + "</div>" : "") +
      imagesBlock(r) +
      answerBlock(r) +
      notesBlock(r) +
      quizBlock(r) +
      relatedBlock(r) +
      kids.map(function (k) {
        return '<div class="th-follow" data-id="' + k.id + '">' + followHead(k.question) +
          imagesBlock(k) +
          answerBlock(k) +
          notesBlock(k) +
          (k.status !== "pending" && editing !== k.id ? '<div class="q-actions th-small"><button class="btn sm ghost" data-th="retry" type="button">Rewrite</button>' +
            '<button class="btn sm ghost" data-th="edit" type="button">Edit</button><button class="btn sm ghost" data-th="delete" type="button">Delete</button></div>' : "") +
          "</div>";
      }).join("") +
      (asking === r.id
        ? '<div class="th-fbox">' + (askQuote ? '<blockquote class="th-quote"><span>About this part</span>' + esc(askQuote.text) + "</blockquote>" : "") +
          '<textarea data-th-follow rows="2" maxlength="2000" placeholder="' + (askQuote ? "What is unclear about it? (or just press Ask to have it explained)" : "Ask a follow-up — what is still unclear?") + '"></textarea>' +
          '<div class="q-actions"><button class="btn sm primary" data-th="send-follow" type="button">Ask</button><button class="btn sm" data-th="cancel-follow" type="button">Cancel</button></div></div>'
        : "") +
      (r.status === "ready" && editing !== r.id
        ? '<div class="q-actions th-actions">' +
          '<button class="btn sm ' + (r.understood ? "" : "primary") + '" data-th="understood" type="button">' + (r.understood ? "✓ Studied" : "Mark as studied") + "</button>" +
          '<button class="btn sm" data-th="simpler" type="button">Explain simpler</button>' +
          '<button class="btn sm" data-th="deeper" type="button">Go deeper</button>' +
          '<button class="btn sm" data-th="interview" type="button">Interview version</button>' +
          '<button class="btn sm" data-th="follow" type="button">Ask a follow-up</button>' +
          '<span class="th-sep"></span>' +
          '<button class="btn sm ghost" data-th="pin" type="button">' + (r.pinned ? "Unpin" : "Pin") + "</button>" +
          '<button class="btn sm ghost" data-th="add-img" type="button">Add image</button>' +
          '<button class="btn sm ghost" data-th="retry" type="button">Rewrite</button>' +
          '<button class="btn sm ghost" data-th="edit" type="button">Edit</button>' +
          '<a class="btn sm ghost" href="/interview-prep/thoughts/' + r.id + '/pdf" target="_blank" rel="noopener">PDF</a>' +
          '<button class="btn sm ghost" data-th="delete" type="button">Delete</button></div>'
        : r.status !== "pending" && editing !== r.id ? '<div class="q-actions th-actions"><button class="btn sm ghost" data-th="delete" type="button">Delete</button></div>' : "");
    return '<div class="q-card open th-card' + (r.understood ? " done" : "") + '" data-id="' + r.id + '">' + head +
      '<div class="q-body th-body">' + body + "</div></div>";
  }

  /* ── Actions ─────────────────────────────────────────────────────── */
  async function ask(question, extra, files) {
    var body = Object.assign({ question: question }, extra || {});
    var r;
    if (files && files.length) {
      r = await upload("/api/prep/thoughts" + Q, {
        question: question, context: body.context || "", parent_id: body.parent_id || null, shelf: SHELF,
        tags: (body.tags || []).join(","),
      }, files);
      if (r && r.item && r.item.image_error) H().say(r.item.image_error, "error");
    } else {
      r = await api("/api/prep/thoughts" + Q, { method: "POST", body: JSON.stringify(Object.assign({ shelf: SHELF }, body)) });
    }
    if (r && r.item) {
      ITEMS.unshift(r.item);
      open[r.item.root_id || r.item.id] = true;
      render(); schedulePoll();
    }
    return r;
  }

  function submitMain() {
    var q = $("th-q").value.trim();
    if (!q) { $("th-q").focus(); return; }
    var btn = $("th-go"); btn.disabled = true;
    var tags = ($("th-tags").value || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean);
    open = {};
    ask(q, { context: $("th-ctx").value.trim(), tags: tags }, pendingFiles.slice()).then(function () {
      $("th-q").value = ""; $("th-ctx").value = ""; $("th-tags").value = "";
      pendingFiles = []; paintPending();
      $("th-more").hidden = true;
      H().say("Saved — the answer is being written", "success");
      window.scrollTo({ top: $("th-list").getBoundingClientRect().top + window.scrollY - 120, behavior: "smooth" });
    }).catch(function (e) { H().say(e.message, "error"); })
      .then(function () { btn.disabled = false; });
  }

  function find(id) { return ITEMS.find(function (t) { return t.id === id; }); }

  async function patch(id, body) {
    await api("/api/prep/thoughts/" + id, { method: "POST", body: JSON.stringify(body) });
    Object.assign(find(id) || {}, body);
  }

  document.addEventListener("click", async function (e) {
    if (e.target.id === "th-review-now") { openReview(dueList(), true); return; }
    if (e.target.closest("#th-rev")) { reviewClick(e); return; }
    var panel = e.target.closest("[data-panel=thoughts]");
    if (!panel) return;
    if (e.target.id === "th-go") { submitMain(); return; }
    if (e.target.id === "th-more-btn") { $("th-more").hidden = !$("th-more").hidden; return; }
    if (e.target.id === "th-attach") { $("th-file").click(); return; }
    var f = e.target.closest("[data-thf]");
    if (f) {
      view.filter = f.dataset.thf;
      document.querySelectorAll("[data-thf]").forEach(function (b) { b.setAttribute("aria-pressed", b === f ? "true" : "false"); });
      render(); return;
    }
    var a = e.target.closest("[data-th]");
    if (!a) return;
    var card = a.closest(".th-card"), rootId = card && card.dataset.id;
    var sub = a.closest(".th-follow");
    var id = sub ? sub.dataset.id : rootId;
    var root = find(rootId), t = find(id);
    try {
      switch (a.dataset.th) {
        case "toggle": open[rootId] = !open[rootId]; render(); break;
        case "goto": {
          var target = roots().filter(function (x) { return x.question === a.dataset.q; })[0];
          if (!target) { H().say("That question isn't in this list", "info"); break; }
          if (view.filter !== "all" || view.q) {
            view.filter = "all"; view.q = ""; if ($("th-search")) $("th-search").value = "";
            document.querySelectorAll("[data-thf]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.thf === "all" ? "true" : "false"); });
          }
          open[target.id] = true; render();
          var el = document.querySelector('.th-card[data-id="' + target.id + '"]');
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
          break;
        }
        case "understood": {
          var res = await api("/api/prep/thoughts/" + rootId, { method: "POST", body: JSON.stringify({ understood: !root.understood }) });
          root.understood = !root.understood;
          if ("next_review_at" in res) { root.next_review_at = res.next_review_at; root.review_stage = res.review_stage; }
          if (root.understood) H().say(res.review_unavailable ? "Marked as studied" : "Marked as studied — first review tomorrow", "success");
          render(); break;
        }
        case "quiz": {
          quizOpen[rootId] = !quizOpen[rootId];
          if (quizOpen[rootId] && root.step && !quizCache[root.step]) {
            a.disabled = true;
            var qj = await api("/api/prep/thoughts/quiz/" + root.step);
            quizCache[root.step] = qj.items || [];
          }
          var box = card.querySelector(".th-quiz");
          if (box) box.outerHTML = quizBlock(root); else render();
          break;
        }
        case "qopt": {
          var qbox = a.closest(".th-mcq");
          if (!qbox || qbox.dataset.done) break;
          qbox.dataset.done = "1";
          var right = +a.dataset.o === +qbox.dataset.answer;
          qbox.classList.add(right ? "got" : "miss");
          qbox.querySelectorAll("[data-th=qopt]").forEach(function (o) {
            o.disabled = true;
            if (+o.dataset.o === +qbox.dataset.answer) o.classList.add("right");
            else if (o === a) o.classList.add("wrong");
          });
          qbox.querySelector(".th-why").hidden = false;
          var wrap = a.closest(".th-quiz"); if (wrap) quizScore(wrap);
          break;
        }
        case "pin": await patch(rootId, { pinned: !root.pinned }); render(); break;
        case "simpler": await ask("Explain this again more simply, as if to someone new to the topic, with a different analogy: " + root.question, { parent_id: lastOf(root).id }); break;
        case "deeper": await ask((STUDENT ? "Go one level deeper on this - the internals, edge cases and trade-offs a strong new-grad SDE interviewer would probe: " : "Go one level deeper on this - the internals, edge cases, numbers and trade-offs a Director-level interviewer would probe: ") + root.question, { parent_id: lastOf(root).id }); break;
        case "hint-open": toggleHint(a.dataset.hid, true); break;
        case "hint-close": toggleHint(openHint); break;
        case "hint-rewrite": {
          var hr = find(a.dataset.hid); if (!hr) break;
          await api("/api/prep/thoughts/" + hr.id + "/retry" + Q, { method: "POST" });
          hr.status = "pending"; hr.error = null; render(); schedulePoll(); break;
        }
        case "hint-del": {
          var hd = find(a.dataset.hid); if (!hd) break;
          if (armedDel !== hd.id) { armedDel = hd.id; a.textContent = "Tap again to delete"; setTimeout(function () { if (armedDel === hd.id) { armedDel = null; if (a.isConnected) a.textContent = "Delete"; } }, 4000); break; }
          await api("/api/prep/thoughts/" + hd.id + "/delete", { method: "POST" });
          ITEMS = ITEMS.filter(function (x) { return x.id !== hd.id; });
          armedDel = null; openHint = null; render(); H().say("Highlight removed", "success"); break;
        }
        case "interview": await ask((STUDENT
            ? "Interview version: how should I explain this in a campus interview in about 60 seconds? Use simple words and one small example, in the order I would say it out loud. Then give 2 follow-up questions the interviewer is likely to ask next, each with a short answer. Topic: "
            : "Interview version: how should I answer this in a Director-level interview in about 60-90 seconds? Lead with the decision, then scale and numbers, the key trade-offs, and how I would lead the team through it, in the order I would say it out loud. Then give 2 follow-up questions the interviewer is likely to ask next, each with a short answer. Topic: ") + root.question, { parent_id: lastOf(root).id }); break;
        case "follow": askQuote = null; asking = rootId; render(); setTimeout(function () { var x = document.querySelector("[data-th-follow]"); if (x) x.focus(); }, 30); break;
        case "cancel-follow": asking = null; askQuote = null; render(); break;
        case "send-follow": {
          var box = document.querySelector("[data-th-follow]"), v = box && box.value.trim();
          var quote = askQuote;
          if (!v && !quote) { box && box.focus(); break; }
          a.disabled = true; asking = null; askQuote = null;
          if (quote) {
            await ask('About this part: \u201c' + quote.text + '\u201d ' + (v.slice(0, 1300) || "Explain this part in simple words, with a small example."),
                      { parent_id: quote.parentId }); break;
          }
          await ask(v, { parent_id: lastOf(root).id }); break;
        }
        case "retry":
          if (t.status === "ready" && !confirm("Write a fresh answer? The current one will be replaced.")) break;
          await api("/api/prep/thoughts/" + id + "/retry" + Q, { method: "POST" });
          t.status = "pending"; t.error = null; render(); schedulePoll(); break;
        case "edit": editing = id; render(); break;
        case "insert-flow": case "insert-seq": {
          var ed = document.querySelector("[data-th-edit]");
          var tpl = a.dataset.th === "insert-flow"
            ? "\n```mermaid\nflowchart LR\n  A[Client] --> B[Service]\n  B --> C[(Database)]\n```\n"
            : "\n```mermaid\nsequenceDiagram\n  participant U as User\n  participant S as Service\n  U->>S: request\n  S-->>U: response\n```\n";
          var at = ed.selectionStart || ed.value.length;
          ed.value = ed.value.slice(0, at) + tpl + ed.value.slice(at);
          ed.focus(); break;
        }
        case "unattach": pendingFiles.splice(+a.dataset.i, 1); paintPending(); break;
        case "add-img": {
          var picker = document.createElement("input");
          picker.type = "file"; picker.accept = "image/png,image/jpeg,image/webp,image/gif"; picker.multiple = true;
          picker.onchange = function () {
            var fs = goodFiles(picker.files);
            if (!fs.length) return;
            H().say("Uploading…", "info");
            upload("/api/prep/thoughts/" + rootId + "/images", {}, fs).then(function (j) {
              root.images = j.images; render(); H().say("Image added", "success");
            }).catch(function (err) { H().say(err.message, "error"); });
          };
          picker.click(); break;
        }
        case "img-del": {
          var owner = a.closest(".th-follow") ? find(a.closest(".th-follow").dataset.id) : root;
          if (!confirm("Remove this image?")) break;
          var j = await api("/api/prep/thoughts/" + owner.id + "/images/delete", { method: "POST", body: JSON.stringify({ key: a.dataset.key }) });
          owner.images = j.images; render(); break;
        }
        case "note-add": noteDraft = { tid: id, nid: null }; noteText = ""; noteFocus = [0, 0]; wantNoteFocus = true; render(); break;
        case "note-edit": {
          var en = notesOf(t).find(function (n) { return n.id === a.dataset.nid; });
          if (!en) break;
          noteDraft = { tid: id, nid: en.id }; noteText = en.text;
          noteFocus = [en.text.length, en.text.length]; wantNoteFocus = true; render(); break;
        }
        case "note-cancel": noteDraft = null; noteText = ""; noteFocus = null; render(); break;
        case "note-save": {
          var nv = noteText.trim();
          if (!nv) { var nb = document.querySelector("[data-th-note]"); if (nb) nb.focus(); break; }
          var d = noteDraft;
          a.disabled = true;
          var nr = await api("/api/prep/thoughts/" + d.tid + "/notes" + (d.nid ? "/" + d.nid : ""),
                             { method: "POST", body: JSON.stringify({ text: nv }) });
          find(d.tid).notes = nr.notes;
          noteDraft = null; noteText = ""; noteFocus = null;
          H().say(d.nid ? "Note saved" : "Note added", "success"); render(); break;
        }
        case "note-del": {
          if (!confirm("Delete this note?")) break;
          var dr = await api("/api/prep/thoughts/" + id + "/notes/" + a.dataset.nid + "/delete", { method: "POST" });
          t.notes = dr.notes; render(); break;
        }
        case "cancel-edit": editing = null; render(); break;
        case "save-edit": {
          var ta = document.querySelector("[data-th-edit]");
          await patch(editing, { answer: ta.value }); find(editing).status = "ready"; editing = null; render(); break;
        }
        case "delete":
          if (!confirm(sub ? "Delete this follow-up?" : "Delete this question and its follow-ups?")) break;
          await api("/api/prep/thoughts/" + id + "/delete", { method: "POST" });
          ITEMS = ITEMS.filter(function (x) { return x.id !== id && (sub || x.root_id !== id); });
          render(); break;
      }
    } catch (err) {
      H().say(err.message, "error");
      if (a.dataset.th === "note-save") a.disabled = false;
    }
  });

  // A follow-up asked about a selected sentence is stored as
  // 'About this part: “…” <doubt>' and shown with the sentence quoted.
  function followHead(q) {
    var m = /^About this part: \u201c([\s\S]*?)\u201d\s*([\s\S]*)$/.exec(q || "");
    if (!m) return '<div class="th-fq"><span class="th-fq-k">Follow-up</span>' + esc(q) + "</div>";
    return '<div class="th-fq"><span class="th-fq-k">Follow-up</span>' + esc(m[2]) + "</div>" +
      '<blockquote class="th-quote"><span>About this part</span>' + esc(m[1]) + "</blockquote>";
  }

  // "Ask about this": select a sentence in any answer (long-press on a
  // phone) and a chip offers to ask a follow-up about exactly that part.
  // The follow-up chains from the answer the sentence came from.
  var selChip = null, selInfo = null;
  function hideChip() { if (selChip) selChip.hidden = true; selInfo = null; }
  function checkSelection() {
    var sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) { hideChip(); return; }
    var text = String(sel).replace(/\s+/g, " ").trim();
    var node = sel.anchorNode && (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement);
    var ans = node && node.closest && node.closest(".th-answer");
    var card = ans && ans.closest(".th-card");
    if (!ans || !card || text.length < 3 || !ans.contains(sel.focusNode)) { hideChip(); return; }
    if (ans.querySelector(".th-hlcard") && sel.anchorNode && ans.querySelector(".th-hlcard").contains(sel.anchorNode)) { hideChip(); return; }
    var sub = ans.closest(".th-follow");
    var range = sel.getRangeAt(0);
    selInfo = { rootId: card.dataset.id, parentId: ans.dataset.tid || (sub ? sub.dataset.id : card.dataset.id),
                text: text.slice(0, 500), highlight: !!ans.dataset.tid,
                prefix: prefixBefore(ans, range), rect: range.getBoundingClientRect() };
    if (!selChip) {
      selChip = document.createElement("button");
      selChip.type = "button"; selChip.className = "th-selchip"; selChip.textContent = "💡 Highlight & ask";
      selChip.addEventListener("mousedown", function (e) { e.preventDefault(); });
      selChip.addEventListener("click", function () {
        if (!selInfo) return;
        if (selInfo.highlight) { openHighlightBox(selInfo); return; }
        askQuote = { text: selInfo.text, parentId: selInfo.parentId };
        asking = selInfo.rootId; open[selInfo.rootId] = true;
        var sel2 = window.getSelection && window.getSelection(); if (sel2) sel2.removeAllRanges();
        hideChip(); render();
        setTimeout(function () {
          var x = document.querySelector("[data-th-follow]");
          if (x) { x.scrollIntoView({ behavior: "smooth", block: "center" }); x.focus({ preventScroll: true }); }
        }, 30);
      });
      document.body.appendChild(selChip);
    }
    var rect = sel.getRangeAt(0).getBoundingClientRect();
    selChip.hidden = false;
    var w = selChip.offsetWidth || 120;
    var x = Math.min(Math.max(8, rect.left + rect.width / 2 - w / 2), window.innerWidth - w - 8);
    // Below the selection: phones put their own copy/select menu above it.
    var y = rect.bottom + 10;
    if (y + 44 > window.innerHeight) y = Math.max(8, rect.top - 52);
    selChip.style.left = (x + window.scrollX) + "px";
    selChip.style.top = (y + window.scrollY) + "px";
  }
  var selTimer = null;
  document.addEventListener("selectionchange", function () { clearTimeout(selTimer); selTimer = setTimeout(checkSelection, 250); });
  window.addEventListener("scroll", function () { if (selInfo) checkSelection(); }, { passive: true });

  /* ── Highlights with hints ────────────────────────────────────────
     Select text in an answer -> "Highlight & ask" -> the passage stays
     highlighted and your question's short answer is saved on it as a hint
     (a follow-up row with `highlight` = {quote, prefix}). Tap a highlight
     to read its hint. The passage is found again on every render by its
     text (whitespace-insensitive) and the words just before it. */
  var openHint = null;        // id of the hint whose card is open
  var armedDel = null;        // hint id waiting for a second tap to delete
  function hintsOf(t) {
    return ITEMS.filter(function (h) { return h.highlight && h.parent_id === t.id; })
      .sort(function (a, b) { return (a.created_at || "").localeCompare(b.created_at || ""); });
  }
  function hintList(t) {
    var hs = hintsOf(t);
    if (!hs.length) return "";
    return '<div class="th-hints"><b>💡 Your highlights (' + hs.length + ")</b>" + hs.map(function (h) {
      var q = (h.highlight && h.highlight.quote) || "";
      return '<button type="button" class="th-hint-row' + (openHint === h.id ? " on" : "") + '" data-th="hint-open" data-hid="' + esc(h.id) + '">' +
        '<span class="th-hint-q">\u201c' + esc(q.length > 70 ? q.slice(0, 68) + "…" : q) + '\u201d</span>' +
        '<span class="th-hint-ask">' + esc(h.question || "") + (h.status === "pending" ? " · writing…" : h.status === "failed" ? " · failed" : "") + "</span></button>";
    }).join("") + "</div>";
  }
  function skipNode(n) {
    return n.closest && n.closest(".th-hlcard, .th-hlpin, svg, .fa-anim, .mermaid, .th-hints");
  }
  // The answer's text with runs of whitespace collapsed, plus where each
  // character came from, so a match can be turned back into DOM ranges.
  function textMap(root) {
    var text = "", map = [], w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { return skipNode(n.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } });
    var n;
    while ((n = w.nextNode())) {
      var v = n.nodeValue;
      for (var i = 0; i < v.length; i++) {
        var c = v[i];
        if (/\s/.test(c)) { if (!text.length || text[text.length - 1] === " ") continue; c = " "; }
        text += c; map.push({ node: n, off: i });
      }
    }
    return { text: text, map: map };
  }
  function norm(s) { return String(s || "").replace(/\s+/g, " ").trim(); }
  function prefixBefore(ans, range) {
    try {
      var r = document.createRange(); r.setStart(ans, 0); r.setEnd(range.startContainer, range.startOffset);
      var frag = r.cloneContents(); frag.querySelectorAll(".th-hlcard, .th-hlpin, svg, .fa-anim, .mermaid, .th-hints").forEach(function (x) { x.remove(); });
      return norm(frag.textContent).slice(-80);
    } catch (_) { return ""; }
  }
  function findQuote(tm, quote, prefix) {
    var q = norm(quote); if (!q) return -1;
    var best = -1, bestScore = -1, i = tm.text.indexOf(q);
    while (i >= 0) {
      var before = tm.text.slice(Math.max(0, i - 80), i).trim(), k = 0, p = norm(prefix);
      while (k < before.length && k < p.length && before[before.length - 1 - k] === p[p.length - 1 - k]) k++;
      if (k > bestScore) { bestScore = k; best = i; }
      i = tm.text.indexOf(q, i + 1);
    }
    return best;
  }
  function wrap(tm, start, len, h) {
    var a = tm.map[start], b = tm.map[start + len - 1];
    if (!a || !b) return false;
    var nodes = [], seen = new Set();
    for (var i = start; i < start + len; i++) { var nd = tm.map[i].node; if (!seen.has(nd)) { seen.add(nd); nodes.push(nd); } }
    var last = null;
    nodes.forEach(function (nd) {
      var from = nd === a.node ? a.off : 0, to = nd === b.node ? b.off + 1 : nd.nodeValue.length;
      if (to <= from || !nd.nodeValue.slice(from, to).trim()) return;
      var r = document.createRange(); r.setStart(nd, from); r.setEnd(nd, to);
      var m = document.createElement("mark");
      m.className = "th-hl" + (h.status === "pending" ? " pending" : "") + (openHint === h.id ? " on" : "");
      m.dataset.hid = h.id; m.title = "Tap to read your hint";
      try { r.surroundContents(m); last = m; } catch (_) {}
    });
    if (last) {
      var pin = document.createElement("span"); pin.className = "th-hlpin"; pin.dataset.hid = h.id;
      pin.setAttribute("role", "button"); pin.tabIndex = 0;
      pin.setAttribute("aria-label", "Read hint: " + (h.question || "")); pin.textContent = "💡";
      last.after(pin);
    }
    return !!last;
  }
  function paintHighlights(scope) {
    (scope || document).querySelectorAll(".th-answer[data-tid]").forEach(function (ans) {
      var t = find(ans.dataset.tid); if (!t) return;
      hintsOf(t).forEach(function (h) {
        var tm = textMap(ans), q = h.highlight || {};
        var at = findQuote(tm, q.quote, q.prefix);
        h._anchored = at >= 0 && wrap(tm, at, norm(q.quote).length, h);
      });
      if (openHint) {
        var h0 = find(openHint);
        if (h0 && h0.parent_id === t.id) showHintCard(ans, h0);
      }
    });
  }
  function hintCardHtml(h) {
    var body = h.status === "pending" ? '<p class="th-hl-wait"><span class="th-spin" aria-hidden="true"></span>Writing your hint…</p>'
      : h.status === "failed" ? '<p class="th-failed">' + esc(h.error || "The hint could not be written.") + "</p>"
      : '<div class="th-hl-ans">' + md(h.answer || "") + "</div>";
    return '<div class="th-hlcard" data-hid="' + esc(h.id) + '">' +
      '<div class="th-hl-head"><span class="th-hl-k">💡 Hint</span><span class="th-hl-when">' + when(h.created_at) + "</span></div>" +
      (h._anchored === false ? '<blockquote class="th-quote"><span>Highlighted (the answer changed since)</span>' + esc((h.highlight || {}).quote || "") + "</blockquote>" : "") +
      '<p class="th-hl-qq">' + esc(h.question || "") + "</p>" + body +
      '<div class="q-actions th-small">' +
      (h.status !== "pending" ? '<button class="btn sm ghost" data-th="hint-rewrite" data-hid="' + esc(h.id) + '" type="button">Rewrite</button>' : "") +
      '<button class="btn sm ghost" data-th="hint-del" data-hid="' + esc(h.id) + '" type="button">' + (armedDel === h.id ? "Tap again to delete" : "Delete") + "</button>" +
      '<button class="btn sm ghost" data-th="hint-close" type="button">Close</button></div></div>';
  }
  function showHintCard(ans, h) {
    document.querySelectorAll(".th-hlcard").forEach(function (c) { c.remove(); });
    var holder = document.createElement("div"); holder.innerHTML = hintCardHtml(h);
    var card = holder.firstChild;
    var mark = ans.querySelector('mark.th-hl[data-hid="' + h.id + '"]');
    if (mark) {
      var block = mark.closest("li, p, pre, blockquote, h1, h2, h3, h4, h5, table") || mark;
      if (block.tagName === "LI") block.appendChild(card);
      else { var top = block; while (top.parentElement && top.parentElement !== ans && !top.parentElement.classList.contains("th-answer")) top = top.parentElement; top.after(card); }
    } else {
      var list = ans.nextElementSibling && ans.nextElementSibling.classList.contains("th-hints") ? ans.nextElementSibling : null;
      (list || ans).after(card);
    }
    ans.querySelectorAll("mark.th-hl").forEach(function (m) { m.classList.toggle("on", m.dataset.hid === h.id); });
  }
  function toggleHint(hid, scroll) {
    var h = find(hid); if (!h) return;
    armedDel = null;
    if (openHint === hid) { openHint = null; document.querySelectorAll(".th-hlcard").forEach(function (c) { c.remove(); });
      document.querySelectorAll("mark.th-hl.on").forEach(function (m) { m.classList.remove("on"); });
      document.querySelectorAll(".th-hint-row.on").forEach(function (m) { m.classList.remove("on"); }); return; }
    openHint = hid;
    var ans = document.querySelector('.th-answer[data-tid="' + h.parent_id + '"]');
    if (!ans) { open[h.root_id] = true; render(); ans = document.querySelector('.th-answer[data-tid="' + h.parent_id + '"]'); if (!ans) return; }
    showHintCard(ans, h);
    document.querySelectorAll(".th-hint-row").forEach(function (b) { b.classList.toggle("on", b.dataset.hid === hid); });
    if (scroll) { var c = document.querySelector(".th-hlcard"); if (c) c.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }

  // The little box that opens from "Highlight & ask".
  var hlBox = null, hlInfo = null;
  function closeHighlightBox() { if (hlBox) hlBox.hidden = true; hlInfo = null; }
  function openHighlightBox(info) {
    hlInfo = info;
    var sel = window.getSelection && window.getSelection(); if (sel) sel.removeAllRanges();
    hideChip();
    if (!hlBox) {
      hlBox = document.createElement("div"); hlBox.className = "th-hlpop"; hlBox.setAttribute("role", "dialog"); hlBox.setAttribute("aria-label", "Highlight and ask");
      hlBox.innerHTML = '<div class="th-hlpop-q"></div>' +
        '<textarea rows="2" maxlength="1500" placeholder="Your question about this (optional)"></textarea>' +
        '<div class="q-actions"><button class="btn sm primary" type="button" data-hl="save">Save hint</button>' +
        '<button class="btn sm" type="button" data-hl="cancel">Cancel</button></div>' +
        '<p class="th-hlpop-tip">Leave the question empty to have this part explained simply. The answer is saved on the highlight.</p>';
      hlBox.addEventListener("click", function (e) {
        var b = e.target.closest("[data-hl]"); if (!b) return;
        if (b.dataset.hl === "cancel") closeHighlightBox(); else saveHighlight(b);
      });
      hlBox.querySelector("textarea").addEventListener("keydown", function (e) {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveHighlight(hlBox.querySelector('[data-hl="save"]')); }
        if (e.key === "Escape") closeHighlightBox();
      });
      document.body.appendChild(hlBox);
    }
    hlBox.querySelector(".th-hlpop-q").textContent = "\u201c" + info.text + "\u201d";
    var ta = hlBox.querySelector("textarea"); ta.value = "";
    hlBox.hidden = false;
    var w = Math.min(420, window.innerWidth - 16), r = info.rect || { left: 8, bottom: 80, width: 0 };
    hlBox.style.width = w + "px";
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.bottom + 10;
    if (y + 230 > window.innerHeight) y = Math.max(8, window.innerHeight - 240);
    hlBox.style.left = (x + window.scrollX) + "px"; hlBox.style.top = (y + window.scrollY) + "px";
    setTimeout(function () { ta.focus({ preventScroll: true }); }, 20);
  }
  async function saveHighlight(btn) {
    if (!hlInfo) return;
    var info = hlInfo, q = hlBox.querySelector("textarea").value.trim();
    btn.disabled = true;
    try {
      var r = await api("/api/prep/thoughts" + Q, { method: "POST", body: JSON.stringify({
        shelf: SHELF, question: q, parent_id: info.parentId, highlight: { quote: info.text, prefix: info.prefix } }) });
      if (r && r.item) {
        ITEMS.unshift(r.item); open[info.rootId] = true; openHint = r.item.id;
        closeHighlightBox(); render(); schedulePoll();
        H().say("Highlighted — your hint is being written", "success");
      }
    } catch (e) { H().say(e.message, "error"); }
    btn.disabled = false;
  }
  document.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") && e.target.classList && e.target.classList.contains("th-hlpin")) { e.preventDefault(); toggleHint(e.target.dataset.hid); }
  });
  document.addEventListener("click", function (e) {
    if (hlBox && !hlBox.hidden && !e.target.closest(".th-hlpop, .th-selchip")) closeHighlightBox();
    var m = e.target.closest("mark.th-hl, .th-hlpin");
    if (m && !(window.getSelection && String(window.getSelection()).trim())) { e.preventDefault(); toggleHint(m.dataset.hid); }
  });

  // Follow-ups chain from the latest answer in the thread, so "go deeper"
  // after "explain simpler" builds on what was just said.
  function lastOf(root) {
    var kids = children(root).filter(function (k) { return k.status === "ready"; });
    return kids.length ? kids[kids.length - 1] : root;
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      if (e.target.id === "th-q" || e.target.id === "th-ctx") { e.preventDefault(); submitMain(); }
      else if (e.target.matches && e.target.matches("[data-th-follow]")) {
        e.preventDefault(); var b = document.querySelector('[data-th="send-follow"]'); if (b) b.click();
      }
      else if (e.target.matches && e.target.matches("[data-th-note]")) {
        e.preventDefault(); var nb = document.querySelector('[data-th="note-save"]'); if (nb) nb.click();
      }
    }
  });
  document.addEventListener("change", function (e) {
    if (e.target.id !== "th-file") return;
    pendingFiles = pendingFiles.concat(goodFiles(e.target.files)).slice(0, MAX_IMAGES);
    e.target.value = "";
    paintPending();
  });
  // Paste a screenshot straight into the question box.
  document.addEventListener("paste", function (e) {
    if (e.target.id !== "th-q" && e.target.id !== "th-ctx") return;
    var items = (e.clipboardData && e.clipboardData.files) || [];
    var fs = goodFiles(items);
    if (!fs.length) return;
    e.preventDefault();
    pendingFiles = pendingFiles.concat(fs).slice(0, MAX_IMAGES);
    paintPending();
    H().say("Image attached", "success");
  });

  document.addEventListener("change", function (e) {
    if (e.target.id === "th-order") { view.order = e.target.value; render(); }
  });
  document.addEventListener("input", function (e) {
    if (e.target.id === "th-search") { view.q = e.target.value; render(); }
    if (e.target.matches && e.target.matches("[data-th-note]")) {
      noteText = e.target.value; noteFocus = [e.target.selectionStart, e.target.selectionEnd];
    }
    if (e.target.id === "th-q" || (e.target.matches && e.target.matches("[data-th-follow],[data-th-edit],[data-th-note]"))) {
      e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight + 2, 520) + "px";
    }
  });

  /* ── "Choose the best answer" quiz ───────────────────────────────── */
  function mcqHtml(m, i, prefix) {
    return '<div class="th-mcq" data-answer="' + m.answer + '"><div class="th-mq"><span class="th-mn">' + (prefix || "") + (i + 1) + "</span>" +
      esc(m.q) + ' <span class="badge">' + esc(m.level || "") + "</span></div>" +
      m.options.map(function (o, k) {
        return '<button type="button" class="th-opt" data-th="qopt" data-o="' + k + '"><b>' + "ABCD"[k] + "</b> " + esc(o) + "</button>";
      }).join("") + '<div class="th-why" hidden>' + esc(m.why) + "</div></div>";
  }
  function quizBlock(r) {
    if (!r.step || !r.quiz_count) return "";
    var shown = !!quizOpen[r.id], items = quizCache[r.step];
    return '<div class="th-quiz"><div class="th-quiz-head"><b>Choose the best answer</b> <span class="mini-lbl">' + r.quiz_count +
      " scenario questions to lock this in</span> <span class=\"th-score mini-lbl\"></span>" +
      '<button type="button" class="btn sm' + (shown ? "" : " primary") + '" data-th="quiz">' + (shown ? "Hide quiz" : "Quiz me") + "</button></div>" +
      (shown && items ? '<div class="th-mcqs">' + items.map(function (m, i) { return mcqHtml(m, i); }).join("") + "</div>" : "") + "</div>";
  }
  function quizScore(wrap) {
    var done = wrap.querySelectorAll(".th-mcq[data-done]").length, got = wrap.querySelectorAll(".th-mcq.got").length;
    var el = wrap.querySelector(".th-score"); if (el) el.textContent = got + " / " + done + " right";
  }

  /* ── Spaced repetition: reviews pop up when they are due ─────────── */
  function isDue(r) {
    return !!(r.understood && r.next_review_at && new Date(r.next_review_at) <= new Date());
  }
  function dueList() {
    return roots().filter(isDue).sort(function (a, b) { return (a.next_review_at || "").localeCompare(b.next_review_at || ""); });
  }
  function reviewBadge(r) {
    if (!r.understood || !r.next_review_at) return "";
    var days = Math.ceil((new Date(r.next_review_at) - new Date()) / 864e5);
    return days <= 0 ? '<span class="badge P1">review due</span>' : '<span class="badge th-next">review in ' + days + "d</span>";
  }
  function nextDays(stage, rating) {
    stage = stage || 0;
    if (rating === "again") stage = 0; else if (rating === "good") stage += 1; else if (rating === "easy") stage += 2;
    return REVIEW_DAYS[Math.min(stage, REVIEW_DAYS.length - 1)];
  }
  function inDays(d) { return d === 1 ? "tomorrow" : "in " + d + " days"; }
  var REV = null;   // {list, i, picks, answered, got}
  function todayKey() { var d = new Date(); return "thReviewSeen-" + SHELF + "-" + d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }
  function maybeReview() {
    var due = dueList();
    if (!due.length) return;
    var seen = false; try { seen = localStorage.getItem(todayKey()) === "1"; } catch (e) {}
    if (!seen) openReview(due, false);
  }
  function openReview(list, manual) {
    if (!list.length) return;
    try { localStorage.setItem(todayKey(), "1"); } catch (e) {}
    REV = { list: list.slice(0, 20), i: 0 };
    var back = $("th-rev");
    if (!back) {
      back = document.createElement("div"); back.id = "th-rev"; back.className = "th-rev-back";
      back.setAttribute("role", "dialog"); back.setAttribute("aria-modal", "true"); back.setAttribute("aria-label", "Spaced review");
      document.body.appendChild(back);
    }
    back.hidden = false;
    reviewStep();
  }
  function closeReview() { var b = $("th-rev"); if (b) b.hidden = true; REV = null; render(); }
  async function reviewStep() {
    var back = $("th-rev"); if (!back || !REV) return;
    if (REV.i >= REV.list.length) {
      back.innerHTML = '<div class="th-rev"><h3>All caught up</h3><p>You reviewed ' + REV.list.length + " question" + (REV.list.length === 1 ? "" : "s") +
        ". Each one will come back just before you are likely to forget it.</p>" +
        '<div class="q-actions"><button class="btn primary" type="button" data-rv="close">Done</button></div></div>';
      return;
    }
    var r = REV.list[REV.i];
    REV.picks = null; REV.answered = 0; REV.got = 0;
    if (r.step && r.quiz_count) {
      if (!quizCache[r.step]) {
        back.innerHTML = '<div class="th-rev"><p class="mini-lbl">Loading…</p></div>';
        try { quizCache[r.step] = (await api("/api/prep/thoughts/quiz/" + r.step)).items || []; } catch (e) { quizCache[r.step] = []; }
      }
      var pool = quizCache[r.step].slice();
      for (var k = pool.length - 1; k > 0; k--) { var j = Math.floor(Math.random() * (k + 1)); var t = pool[k]; pool[k] = pool[j]; pool[j] = t; }
      REV.picks = pool.slice(0, 3);
    }
    var st = r.review_stage || 0;
    back.innerHTML = '<div class="th-rev"><div class="th-rev-top"><span class="mini-lbl">Spaced review · ' + (REV.i + 1) + " of " + REV.list.length + "</span>" +
      '<button type="button" class="btn sm ghost" data-rv="later">Later</button></div>' +
      "<h3>" + (r.step ? '<span class="th-step">' + r.step + "</span>" : "") + esc(r.title || r.question) + "</h3>" +
      (REV.picks && REV.picks.length
        ? '<p class="mini-lbl">Answer these from memory, then rate how well you remembered.</p><div class="th-quiz">' +
          REV.picks.map(function (m, i) { return mcqHtml(m, i, "Q"); }).join("") + "</div>"
        : '<p class="th-rev-q">' + esc(r.question) + '</p><p class="mini-lbl">Say the answer out loud first, then rate yourself.</p>') +
      '<div class="th-rev-rate"><span class="mini-lbl" id="th-rev-hint">How well did you remember it?</span><div class="q-actions">' +
      '<button class="btn sm" type="button" data-rv="again">Forgot <small>' + inDays(nextDays(st, "again")) + "</small></button>" +
      '<button class="btn sm" type="button" data-rv="hard">Hard <small>' + inDays(nextDays(st, "hard")) + "</small></button>" +
      '<button class="btn sm primary" type="button" data-rv="good">Got it <small>' + inDays(nextDays(st, "good")) + "</small></button>" +
      '<button class="btn sm" type="button" data-rv="easy">Easy <small>' + inDays(nextDays(st, "easy")) + "</small></button></div>" +
      '<button type="button" class="btn sm ghost" data-rv="open">Open the full answer</button></div></div>';
  }
  async function reviewClick(e) {
    var back = $("th-rev");
    if (e.target === back) { closeReview(); return; }
    var opt = e.target.closest("[data-th=qopt]");
    if (opt) {
      var qbox = opt.closest(".th-mcq");
      if (qbox.dataset.done) return;
      qbox.dataset.done = "1";
      var right = +opt.dataset.o === +qbox.dataset.answer;
      qbox.classList.add(right ? "got" : "miss");
      qbox.querySelectorAll("[data-th=qopt]").forEach(function (o) { o.disabled = true; if (+o.dataset.o === +qbox.dataset.answer) o.classList.add("right"); else if (o === opt) o.classList.add("wrong"); });
      qbox.querySelector(".th-why").hidden = false;
      REV.answered++; if (right) REV.got++;
      if (REV.picks && REV.answered === REV.picks.length) {
        var sug = REV.got === REV.answered ? "good" : REV.got === 0 ? "again" : "hard";
        var hint = $("th-rev-hint");
        if (hint) hint.textContent = REV.got + " of " + REV.answered + " right. Suggested: " + ({ good: "Got it", hard: "Hard", again: "Forgot" })[sug] + ".";
        back.querySelectorAll("[data-rv]").forEach(function (b) { b.classList.toggle("primary", b.dataset.rv === sug); });
      }
      return;
    }
    var b = e.target.closest("[data-rv]");
    if (!b || !REV) { if (b && b.dataset.rv === "close") closeReview(); return; }
    var act = b.dataset.rv, r = REV.list[REV.i];
    if (act === "close" || act === "later") { closeReview(); return; }
    if (act === "open") { open[r.id] = true; view.filter = "all"; closeReview();
      var el = document.querySelector('.th-card[data-id="' + r.id + '"]'); if (el) el.scrollIntoView({ behavior: "smooth", block: "start" }); return; }
    b.disabled = true;
    try {
      var res = await api("/api/prep/thoughts/" + r.id + "/review" + Q, { method: "POST", body: JSON.stringify({ rating: act }) });
      Object.assign(r, { review_stage: res.review_stage, next_review_at: res.next_review_at, last_reviewed_at: res.last_reviewed_at, review_count: res.review_count, understood: true });
    } catch (err) { H().say(err.message, "error"); b.disabled = false; return; }
    REV.i++; reviewStep();
  }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && REV) closeReview(); });

  window.PrepThoughts = { load: load, _md: md, _draw: drawDiagrams };
})();

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
 * under the original question.
 */
(function () {
  "use strict";
  var H = function () { return window.PrepHub; };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return H().esc(s); };
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
  var view = { q: "", filter: "all" };
  var open = {};            // root id -> expanded
  var editing = null;       // id whose answer is being edited
  var asking = null;        // root id with the follow-up box open
  var pollTimer = null;

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
        var code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
        // A ```mermaid block is drawn as a diagram after render (drawDiagrams);
        // the source stays inside as the fallback if it can't be drawn.
        out.push(isMermaid
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
    return api("/api/prep/thoughts").then(function (j) {
      available = j.available !== false;
      provider = j.provider !== false;
      ITEMS = j.items || [];
      if (!Object.keys(open).length) {
        var newest = roots()[0];
        if (newest) open[newest.id] = true;
      }
      render();
      schedulePoll();
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
    return ITEMS.filter(function (t) { return t.parent_id && (t.root_id === root.id); })
      .sort(function (a, b) { return (a.created_at || "").localeCompare(b.created_at || ""); });
  }

  /* ── Rendering ───────────────────────────────────────────────────── */
  function shell() {
    $("th-view").innerHTML =
      '<div class="card th-ask">' +
      '<label for="th-q" class="th-ask-lbl">What\'s on your mind?</label>' +
      '<textarea id="th-q" rows="3" maxlength="2000" placeholder="e.g. What does a Director own that an EM doesn\'t? · When would I pick Cassandra over Postgres? · How does a CDN decide what to cache?"></textarea>' +
      '<div class="th-more" id="th-more" hidden>' +
      '<textarea id="th-ctx" rows="2" maxlength="4000" placeholder="What prompted it? (optional) — where you saw it, what confused you"></textarea>' +
      '<input id="th-tags" maxlength="120" placeholder="Tags, comma-separated (optional) — kafka, leadership"></div>' +
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
      '<button class="rchip" type="button" data-thf="pinned" aria-pressed="false">Pinned <span class="n" id="thn-pin"></span></button></div></div>' +
      '<div id="th-list"><div class="card"><div class="empty">Loading…</div></div></div>';
  }

  function render() {
    var note = $("th-note");
    if (!available) { note.hidden = false; note.textContent = "Random thoughts need MIGRATION_PREP_THOUGHTS.sql run in Supabase before questions can be saved."; }
    else if (!provider) { note.hidden = false; note.textContent = "No AI provider is configured on the server, so questions will be saved but not answered. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY or GROQ_API_KEY."; }
    else note.hidden = true;

    var rs = roots();
    var q = view.q.toLowerCase();
    var unclear = rs.filter(function (r) { return !r.understood; }).length;
    var pinned = rs.filter(function (r) { return r.pinned; }).length;
    $("thn-all").textContent = rs.length; $("thn-todo").textContent = unclear; $("thn-pin").textContent = pinned;
    $("tn-th").textContent = rs.length || "";
    var list = rs.filter(function (r) {
      if (view.filter === "todo" && r.understood) return false;
      if (view.filter === "pinned" && !r.pinned) return false;
      if (!q) return true;
      return [r].concat(children(r)).some(function (t) {
        return ((t.question || "") + " " + (t.answer || "") + " " + (t.tags || []).join(" ")).toLowerCase().indexOf(q) >= 0;
      });
    }).sort(function (a, b) { return (b.pinned - a.pinned) || (b.created_at || "").localeCompare(a.created_at || ""); });

    $("th-list").innerHTML = list.map(thread).join("") ||
      '<div class="card"><div class="empty">' + (rs.length ? "Nothing matches." :
        "No questions yet. The next time something doesn't quite make sense — a concept, a design choice, a leadership situation — write it above.") + "</div></div>";
    drawDiagrams($("th-list"));
    if (window.feather) window.feather.replace();
  }

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
    return '<div class="th-answer">' + md(t.answer) + "</div>";
  }

  function thread(r) {
    var kids = children(r);
    var isOpen = !!open[r.id];
    var pending = [r].concat(kids).some(function (t) { return t.status === "pending"; });
    var head = '<div class="q-head th-head" data-th="toggle">' +
      '<span class="q-text">' + esc(r.question) + "</span>" +
      '<span class="q-meta">' + (r.pinned ? '<span class="badge P1">pinned</span>' : "") +
      (pending ? '<span class="badge P2">writing…</span>' : r.status === "failed" ? '<span class="badge P0">failed</span>' :
        r.understood ? '<span class="badge mock">understood</span>' : "") +
      (kids.length ? '<span class="badge">' + kids.length + " follow-up" + (kids.length === 1 ? "" : "s") + "</span>" : "") +
      (r.tags || []).map(function (g) { return '<span class="badge">#' + esc(g) + "</span>"; }).join("") +
      '<span class="badge">' + when(r.created_at) + "</span></span></div>";
    if (!isOpen) return '<div class="q-card th-card' + (r.understood ? " done" : "") + '" data-id="' + r.id + '">' + head + "</div>";

    var body = (r.context ? '<div class="th-ctx"><b>What prompted it</b>' + esc(r.context) + "</div>" : "") +
      imagesBlock(r) +
      answerBlock(r) +
      kids.map(function (k) {
        return '<div class="th-follow" data-id="' + k.id + '"><div class="th-fq"><span class="th-fq-k">Follow-up</span>' + esc(k.question) + "</div>" +
          imagesBlock(k) +
          answerBlock(k) +
          (k.status !== "pending" && editing !== k.id ? '<div class="q-actions th-small"><button class="btn sm ghost" data-th="retry" type="button">Rewrite</button>' +
            '<button class="btn sm ghost" data-th="edit" type="button">Edit</button><button class="btn sm ghost" data-th="delete" type="button">Delete</button></div>' : "") +
          "</div>";
      }).join("") +
      (asking === r.id
        ? '<div class="th-fbox"><textarea data-th-follow rows="2" maxlength="2000" placeholder="Ask a follow-up — what is still unclear?"></textarea>' +
          '<div class="q-actions"><button class="btn sm primary" data-th="send-follow" type="button">Ask</button><button class="btn sm" data-th="cancel-follow" type="button">Cancel</button></div></div>'
        : "") +
      (r.status === "ready" && editing !== r.id
        ? '<div class="q-actions th-actions">' +
          '<button class="btn sm ' + (r.understood ? "" : "primary") + '" data-th="understood" type="button">' + (r.understood ? "✓ Understood" : "I understand this now") + "</button>" +
          '<button class="btn sm" data-th="simpler" type="button">Explain simpler</button>' +
          '<button class="btn sm" data-th="deeper" type="button">Go deeper</button>' +
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
      r = await upload("/api/prep/thoughts", {
        question: question, context: body.context || "", parent_id: body.parent_id || null,
        tags: (body.tags || []).join(","),
      }, files);
      if (r && r.item && r.item.image_error) H().say(r.item.image_error, "error");
    } else {
      r = await api("/api/prep/thoughts", { method: "POST", body: JSON.stringify(body) });
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
        case "understood": await patch(rootId, { understood: !root.understood });
          if (root.understood) H().say("Nice — marked as understood", "success"); render(); break;
        case "pin": await patch(rootId, { pinned: !root.pinned }); render(); break;
        case "simpler": await ask("Explain this again more simply, as if to someone new to the topic, with a different analogy: " + root.question, { parent_id: lastOf(root).id }); break;
        case "deeper": await ask("Go one level deeper on this - the internals, edge cases, numbers and trade-offs a Director-level interviewer would probe: " + root.question, { parent_id: lastOf(root).id }); break;
        case "follow": asking = rootId; render(); setTimeout(function () { var x = document.querySelector("[data-th-follow]"); if (x) x.focus(); }, 30); break;
        case "cancel-follow": asking = null; render(); break;
        case "send-follow": {
          var box = document.querySelector("[data-th-follow]"), v = box && box.value.trim();
          if (!v) { box && box.focus(); break; }
          a.disabled = true; asking = null;
          await ask(v, { parent_id: lastOf(root).id }); break;
        }
        case "retry":
          if (t.status === "ready" && !confirm("Write a fresh answer? The current one will be replaced.")) break;
          await api("/api/prep/thoughts/" + id + "/retry", { method: "POST" });
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
    } catch (err) { H().say(err.message, "error"); }
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

  document.addEventListener("input", function (e) {
    if (e.target.id === "th-search") { view.q = e.target.value; render(); }
    if (e.target.id === "th-q" || (e.target.matches && e.target.matches("[data-th-follow],[data-th-edit]"))) {
      e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight + 2, 520) + "px";
    }
  });

  window.PrepThoughts = { load: load, _md: md, _draw: drawDiagrams };
})();

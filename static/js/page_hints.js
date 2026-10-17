/* page_hints.js — highlight text anywhere and ask about it.
 *
 * Select words on any page and tap "💡 Highlight & ask". The words stay
 * highlighted and the answer is saved on them as a HINT. A hint is a small
 * conversation: open it and keep asking follow-up questions. The 💡 button
 * at the bottom-left lists this page's hints and lets you ask about the
 * page as a whole ("Ask about this page").
 *
 * Saved per person in page_hints (MIGRATION_PAGE_HINTS.sql) through
 * /api/hints; answered on the server by the same AI keys Random thoughts
 * uses. A highlight is found again by its text (whitespace-insensitive)
 * and the words just before it, inside the card it was made in when that
 * card can still be found, so it survives re-renders and reloads.
 */
(function () {
  "use strict";
  if (window.__pageHints) return;
  window.__pageHints = true;

  var PAGE = location.pathname.replace(/\/+$/, "") || "/";
  var SKIP = "nav, .top-nav, .sidebar, script, style, noscript, textarea, input, select, svg, " +
             "[contenteditable], .ph-ui, .ra-chip, .ra-bar, .fa-anim, .toast, [aria-hidden='true']";
  var hints = [], available = true, loaded = false, openId = null, view = "list", armed = null, pollT = null;

  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }
  async function api(url, body) {
    var r = await fetch(url, body === undefined ? { credentials: "same-origin" } : {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify(body) });
    var j = {}; try { j = await r.json(); } catch (_) {}
    if (!r.ok) { var e = new Error(j.error || ("Request failed (" + r.status + ")")); e.status = r.status; throw e; }
    return j;
  }
  function say(msg, kind) { if (window.showToast) window.showToast(msg, kind || "info"); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function norm(s) { return String(s || "").replace(/\s+/g, " ").trim(); }
  function inline(t) { return t.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>"); }
  function md(src) { // small, safe Markdown: everything is escaped first
    var out = [], lines = esc(src || "").split("\n"), i = 0, list = null, para = [];
    function flush() { if (para.length) { out.push("<p>" + inline(para.join("<br>")) + "</p>"); para = []; } if (list) { out.push("</" + list + ">"); list = null; } }
    while (i < lines.length) {
      var l = lines[i];
      if (/^```/.test(l)) { flush(); var code = []; i++; while (i < lines.length && !/^```/.test(lines[i])) { code.push(lines[i]); i++; } out.push("<pre><code>" + code.join("\n") + "</code></pre>"); i++; continue; }
      var h = l.match(/^#{1,4}\s+(.*)/); if (h) { flush(); out.push("<p><b>" + inline(h[1]) + "</b></p>"); i++; continue; }
      var ul = l.match(/^\s*[-*]\s+(.*)/), ol = l.match(/^\s*\d+[.)]\s+(.*)/);
      if (ul || ol) { if (para.length) { out.push("<p>" + inline(para.join("<br>")) + "</p>"); para = []; } var want = ul ? "ul" : "ol"; if (list !== want) { if (list) out.push("</" + list + ">"); out.push("<" + want + ">"); list = want; } out.push("<li>" + inline((ul || ol)[1]) + "</li>"); i++; continue; }
      if (!l.trim()) { flush(); i++; continue; }
      if (list) { out.push("</" + list + ">"); list = null; } para.push(l); i++;
    }
    flush(); return out.join("");
  }
  function when(iso) { try { var d = new Date(iso); return isNaN(d) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "short" }); } catch (_) { return ""; } }
  function mainRoot() { return document.querySelector("main") || document.querySelector(".container, .content, #content") || document.body; }
  function skipEl(el) { return !el || (el.closest && el.closest(SKIP)); }
  function last(h) { var t = h.thread || []; return t[t.length - 1] || {}; }
  function pending(h) { return last(h).status === "pending"; }

  /* ── finding a passage again ───────────────────────────────────── */
  function textMap(root) {
    var text = "", map = [], w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { return skipEl(n.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
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
  function findQuote(tm, quote, prefix) {
    var q = norm(quote); if (!q) return -1;
    var best = -1, score = -1, p = norm(prefix), i = tm.text.indexOf(q);
    while (i >= 0) {
      var before = tm.text.slice(Math.max(0, i - 80), i).trim(), k = 0;
      while (k < before.length && k < p.length && before[before.length - 1 - k] === p[p.length - 1 - k]) k++;
      if (k > score) { score = k; best = i; }
      i = tm.text.indexOf(q, i + 1);
    }
    return best;
  }
  var ANCHOR_SEL = "[data-id], [data-key], [data-qid], [data-topic-id], details[id], section[id], article[id], li[id], .card[id], [id^='q-'], [id^='t-']";
  var BIG_IDS = { app: 1, main: 1, content: 1, ip: 1 };
  function anchorOf(el) {
    var a = el && el.closest && el.closest(ANCHOR_SEL);
    while (a && a.id && BIG_IDS[a.id]) a = a.parentElement && a.parentElement.closest(ANCHOR_SEL);
    if (!a) return "";
    if (a.dataset.id) return "data-id=" + a.dataset.id;
    if (a.dataset.key) return "data-key=" + a.dataset.key;
    if (a.dataset.qid) return "data-qid=" + a.dataset.qid;
    if (a.dataset.topicId) return "data-topic-id=" + a.dataset.topicId;
    return a.id ? "#" + a.id : "";
  }
  function anchorEl(anchor) {
    if (!anchor) return null;
    try {
      if (anchor[0] === "#") return document.getElementById(anchor.slice(1));
      var k = anchor.indexOf("="); return document.querySelector("[" + anchor.slice(0, k) + '="' + CSS.escape(anchor.slice(k + 1)) + '"]');
    } catch (_) { return null; }
  }
  function marksOf(id) { return document.querySelectorAll('mark.ph-hl[data-hid="' + id + '"]'); }
  function wrap(tm, start, len, h) {
    var a = tm.map[start], b = tm.map[start + len - 1]; if (!a || !b) return false;
    var nodes = [], seen = new Set();
    for (var i = start; i < start + len; i++) { var nd = tm.map[i].node; if (!seen.has(nd)) { seen.add(nd); nodes.push(nd); } }
    var made = [];
    nodes.forEach(function (nd) {
      var from = nd === a.node ? a.off : 0, to = nd === b.node ? b.off + 1 : nd.nodeValue.length;
      if (to <= from || !nd.nodeValue.slice(from, to).trim()) return;
      var r = document.createRange(); r.setStart(nd, from); r.setEnd(nd, to);
      var m = document.createElement("mark");
      m.className = "ph-hl"; m.dataset.hid = h.id; m.title = "Tap to open your hint";
      try { r.surroundContents(m); made.push(m); } catch (_) {}
    });
    if (made.length) made[made.length - 1].classList.add("ph-last");
    return made.length > 0;
  }
  function styleMarks(h) {
    marksOf(h.id).forEach(function (m) { m.classList.toggle("pending", pending(h)); m.classList.toggle("on", openId === h.id); });
  }
  function unwrapMarks(id) {
    marksOf(id).forEach(function (m) { var p = m.parentNode; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); if (p.normalize) p.normalize(); });
  }
  var painting = false;
  function paint() {
    if (!hints.length) return;
    painting = true;
    try {
      hints.forEach(function (h) {
        if (!h.quote) return;
        if (marksOf(h.id).length) { styleMarks(h); h._found = true; return; }
        var roots = [anchorEl(h.anchor), mainRoot()].filter(Boolean), done = false;
        for (var i = 0; i < roots.length && !done; i++) {
          var tm = textMap(roots[i]), at = findQuote(tm, h.quote, h.prefix);
          if (at >= 0) done = wrap(tm, at, norm(h.quote).length, h);
        }
        h._found = done; if (done) styleMarks(h);
      });
    } finally { setTimeout(function () { painting = false; }, 0); }
  }
  var paintT = null;
  var mo = new MutationObserver(function (recs) {
    if (painting || !hints.length) return;
    for (var i = 0; i < recs.length; i++) {
      var t = recs[i].target, el = t.nodeType === 1 ? t : t.parentElement;
      if (el && !(el.closest && el.closest(".ph-ui"))) { clearTimeout(paintT); paintT = setTimeout(paint, 300); return; }
    }
  });

  /* ── context sent with a question ──────────────────────────────── */
  function visibleText(el) {
    var tm = textMap(el); return tm.text;
  }
  function contextFor(el, quote) {
    var node = el;
    while (node && node !== document.body && visibleText(node).length < 700) node = node.parentElement;
    var t = visibleText(node || mainRoot());
    if (t.length > 6000) {
      var i = quote ? t.indexOf(norm(quote)) : -1;
      t = i >= 0 ? t.slice(Math.max(0, i - 3000), i + 3000) : t.slice(0, 6000);
    }
    return ((document.title ? "Page: " + document.title + "\n" : "") + t).slice(0, 8000);
  }
  function hintContext(h) {
    var m = marksOf(h.id)[0];
    if (m) return contextFor(m, h.quote);
    var a = anchorEl(h.anchor); if (a) return contextFor(a, h.quote);
    return pageContext();
  }
  function pageContext() {
    var el = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
    if (!el || skipEl(el)) el = mainRoot();
    return contextFor(el, "");
  }


  /* Styles live here so the feature works on every page without touching templates. */
  var CSS = [
    "mark.ph-hl{background:rgba(250,204,21,.38);color:inherit;border-radius:3px;padding:1px 0;cursor:pointer;border-bottom:2px solid #d9b53c;-webkit-box-decoration-break:clone;box-decoration-break:clone;font:inherit}",
    "mark.ph-hl.pending{background:rgba(250,204,21,.18);border-bottom-style:dashed}",
    "mark.ph-hl.on{background:rgba(250,204,21,.6)}",
    "mark.ph-hl.ph-last::after{content:'💡';font-size:.72em;vertical-align:super;margin-left:1px}",
    ".ph-chip{position:absolute;z-index:2147480000;font:600 13px system-ui,sans-serif;padding:8px 14px;border-radius:999px;border:none;cursor:pointer;background:var(--color-primary,#15161a);color:var(--color-on-primary,#fff);box-shadow:0 4px 14px rgba(0,0,0,.25)}",
    ".ph-chip[hidden],.ph-box[hidden],.ph-panel[hidden]{display:none!important}",
    ".ph-box{position:absolute;z-index:2147480001;box-sizing:border-box;padding:12px;border-radius:14px;background:var(--color-surface,#fff);color:var(--color-text,#15161a);border:1px solid var(--color-border-strong,#c9cac4);box-shadow:0 10px 30px rgba(0,0,0,.25);display:flex;flex-direction:column;gap:8px;font:15px system-ui,sans-serif}",
    ".ph-box-q{font-size:13.5px;font-style:italic;background:rgba(250,204,21,.3);border-radius:6px;padding:6px 8px;max-height:4.6em;overflow:auto}",
    ".ph-ui textarea{width:100%;box-sizing:border-box;padding:8px 10px;font:inherit;font-size:15px;line-height:1.45;border-radius:10px;border:1px solid var(--color-border-strong,#c9cac4);background:var(--color-surface,#fff);color:inherit;resize:vertical}",
    ".ph-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}",
    ".ph-btn{font:600 13px system-ui,sans-serif;padding:7px 14px;border-radius:999px;cursor:pointer;border:1px solid var(--color-border-strong,#c9cac4);background:var(--color-surface,#fff);color:var(--color-text,#15161a)}",
    ".ph-btn:disabled{opacity:.5;cursor:default}.ph-btn.ph-sm{padding:4px 10px;font-size:12px}",
    ".ph-primary{background:var(--color-primary,#15161a);color:var(--color-on-primary,#fff);border-color:transparent}",
    ".ph-danger{color:#c0392b;margin-left:auto}",
    ".ph-tip{margin:0;font-size:12px;color:var(--color-text-secondary,#6b6f76)}",
    ".ph-pill{position:fixed;left:14px;bottom:calc(14px + env(safe-area-inset-bottom));z-index:2147479000;height:40px;min-width:40px;padding:0 10px;border-radius:999px;border:1px solid var(--color-border-strong,#c9cac4);background:var(--color-surface,#fff);color:var(--color-text,#15161a);box-shadow:0 4px 14px rgba(0,0,0,.18);font:600 15px system-ui,sans-serif;cursor:pointer;display:flex;align-items:center;gap:4px}",
    ".ph-pill{transition:transform .25s ease,opacity .25s ease}.ph-pill.ph-away{transform:translateY(80px);opacity:0;pointer-events:none}",
    ".ph-n{font-size:12px;background:#facc15;color:#15161a;border-radius:999px;padding:1px 7px}",
    ".ph-panel{position:fixed;z-index:2147479500;top:12px;right:12px;bottom:12px;width:min(400px,calc(100vw - 24px));display:flex;flex-direction:column;background:var(--color-surface,#fff);color:var(--color-text,#15161a);border:1px solid var(--color-border-strong,#c9cac4);border-radius:16px;box-shadow:0 16px 48px rgba(0,0,0,.28);font:15px/1.5 system-ui,sans-serif;overflow:hidden}",
    "@media (max-width:640px){.ph-panel{top:auto;left:0;right:0;bottom:0;width:auto;max-height:78vh;border-radius:16px 16px 0 0;padding-bottom:env(safe-area-inset-bottom)}}",
    ".ph-head{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--color-border,#e4e4df)}",
    ".ph-head b{font-size:14px}.ph-when{font-size:12px;color:var(--color-text-secondary,#6b6f76)}",
    ".ph-x{margin-left:auto;border:none;background:none;font-size:24px;line-height:1;cursor:pointer;color:inherit;padding:0 4px}",
    ".ph-body{flex:1 1 auto;overflow:auto;padding:12px 14px;display:flex;flex-direction:column;gap:12px}",
    ".ph-quote{display:block;text-align:left;font:italic 14px/1.5 system-ui,sans-serif;background:rgba(250,204,21,.25);border:none;border-left:4px solid #d9b53c;border-radius:0 10px 10px 0;padding:8px 10px;cursor:pointer;color:inherit}",
    ".ph-moved{display:block;font-style:normal;font-size:12px;color:var(--color-text-secondary,#6b6f76);margin-top:4px}",
    ".ph-pageq{margin:0;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--color-text-secondary,#6b6f76)}",
    ".ph-turn{display:flex;flex-direction:column;gap:4px}.ph-q{margin:0;font-weight:700}",
    ".ph-ans p,.ph-ans li{margin:4px 0}.ph-ans ul,.ph-ans ol{margin:4px 0;padding-left:20px}.ph-ans pre{overflow:auto;font-size:13px}",
    ".ph-wait{margin:0;color:var(--color-text-secondary,#6b6f76);display:flex;align-items:center;gap:8px}",
    ".ph-spin{width:14px;height:14px;border-radius:50%;border:2px solid currentColor;border-right-color:transparent;animation:phspin .8s linear infinite}",
    "@keyframes phspin{to{transform:rotate(360deg)}}",
    ".ph-err{margin:0;color:#c0392b;font-size:13.5px}",
    ".ph-foot{border-top:1px solid var(--color-border,#e4e4df);padding:10px 14px;display:flex;flex-direction:column;gap:8px}",
    ".ph-item{display:flex;flex-direction:column;gap:2px;text-align:left;font:inherit;font-size:14px;padding:10px 12px;border-radius:12px;cursor:pointer;border:1px solid var(--color-border,#e4e4df);background:var(--color-surface,#fff);color:inherit}",
    ".ph-item-q{font-style:italic}.ph-item-a{font-size:13px;color:var(--color-text-secondary,#6b6f76)}",
    ".ph-empty{margin:0;color:var(--color-text-secondary,#6b6f76)}"
  ].join("\n");
  function injectCss() { if (document.getElementById("ph-css")) return; var st = document.createElement("style"); st.id = "ph-css"; st.textContent = CSS; document.head.appendChild(st); }
  /* ── UI: chip, new-highlight box, panel, page button ───────────── */
  var chip, box, panel, pill, sel = null, boxInfo = null;
  function ui() {
    if (chip) return;
    injectCss();
    chip = document.createElement("button"); chip.type = "button"; chip.className = "ph-ui ph-chip"; chip.hidden = true;
    chip.textContent = "💡 Highlight & ask";
    chip.addEventListener("mousedown", function (e) { e.preventDefault(); });
    chip.addEventListener("click", function () { if (sel) openBox(sel); });
    box = document.createElement("div"); box.className = "ph-ui ph-box"; box.hidden = true; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", "Highlight and ask");
    box.innerHTML = '<div class="ph-box-q"></div><textarea rows="2" maxlength="1500" placeholder="Your question about this (optional)"></textarea>' +
      '<div class="ph-row"><button type="button" class="ph-btn ph-primary" data-ph="save">Save hint</button><button type="button" class="ph-btn" data-ph="cancel">Cancel</button></div>' +
      '<p class="ph-tip">Leave it empty to have this part explained simply. The answer is saved on the highlight; open it later to ask more.</p>';
    panel = document.createElement("aside"); panel.className = "ph-ui ph-panel"; panel.hidden = true; panel.setAttribute("aria-label", "Hints");
    pill = document.createElement("button"); pill.type = "button"; pill.className = "ph-ui ph-pill"; pill.setAttribute("aria-label", "Hints on this page"); pill.dataset.ph = "pill";
    document.body.appendChild(chip); document.body.appendChild(box); document.body.appendChild(panel); document.body.appendChild(pill);
    box.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveBox(); }
      if (e.key === "Escape") closeBox();
    });
    panel.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && e.target.tagName === "TEXTAREA") { e.preventDefault(); var b = panel.querySelector('[data-ph="ask"],[data-ph="ask-page"]'); if (b) b.click(); }
      if (e.key === "Escape") closePanel();
    });
    paintPill();
  }
  function paintPill() {
    if (!pill) return;
    var n = hints.length;
    pill.innerHTML = "💡" + (n ? '<span class="ph-n">' + n + "</span>" : "");
    pill.title = n ? n + " hint" + (n === 1 ? "" : "s") + " on this page" : "Ask about this page";
  }
  function hideChip() { if (chip) chip.hidden = true; sel = null; }
  function checkSel() {
    var s = window.getSelection && window.getSelection();
    if (!s || s.isCollapsed || !s.rangeCount) { hideChip(); return; }
    var text = norm(String(s));
    var node = s.anchorNode && (s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement);
    if (!node || text.length < 2 || skipEl(node) || (s.focusNode && skipEl(s.focusNode.nodeType === 1 ? s.focusNode : s.focusNode.parentElement))) { hideChip(); return; }
    var range = s.getRangeAt(0), rect = range.getBoundingClientRect();
    if (!rect || (!rect.width && !rect.height)) { hideChip(); return; }
    var anchor = anchorOf(node), root = anchorEl(anchor) || mainRoot();
    sel = { text: text.slice(0, 500), anchor: anchor, prefix: prefixBefore(root, range), rect: rect, node: node };
    ui(); chip.hidden = false;
    var w = chip.offsetWidth || 150, x = Math.min(Math.max(8, rect.left + rect.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = rect.bottom + 10; if (y + 44 > window.innerHeight) y = Math.max(8, rect.top - 92);
    chip.style.left = (x + window.scrollX) + "px"; chip.style.top = (y + window.scrollY) + "px";
  }
  function prefixBefore(root, range) {
    try {
      if (!root.contains(range.startContainer)) root = mainRoot();
      var r = document.createRange(); r.setStart(root, 0); r.setEnd(range.startContainer, range.startOffset);
      var f = r.cloneContents(); f.querySelectorAll(SKIP).forEach(function (x) { x.remove(); });
      return norm(f.textContent).slice(-80);
    } catch (_) { return ""; }
  }
  function closeBox() { if (box) box.hidden = true; boxInfo = null; }
  function openBox(info) {
    boxInfo = info; info.context = contextFor(info.node, info.text);
    var s = window.getSelection && window.getSelection(); if (s) s.removeAllRanges();
    hideChip(); ui();
    box.querySelector(".ph-box-q").textContent = "“" + info.text + "”";
    var ta = box.querySelector("textarea"); ta.value = ""; box.hidden = false;
    var w = Math.min(420, window.innerWidth - 16), r = info.rect; box.style.width = w + "px";
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8), y = r.bottom + 10;
    if (y + 230 > window.innerHeight) y = Math.max(8, window.innerHeight - 240);
    box.style.left = (x + window.scrollX) + "px"; box.style.top = (y + window.scrollY) + "px";
    setTimeout(function () { ta.focus({ preventScroll: true }); }, 20);
  }
  async function saveBox() {
    if (!boxInfo) return;
    var info = boxInfo, btn = box.querySelector('[data-ph="save"]'), q = box.querySelector("textarea").value.trim();
    btn.disabled = true;
    try {
      var j = await api("/api/hints", { page: PAGE, anchor: info.anchor, quote: info.text, prefix: info.prefix, question: q, context: info.context });
      closeBox(); hints.push(j.item); paint(); openHint(j.item.id); schedulePoll();
    } catch (e) { say(e.message, "error"); }
    btn.disabled = false;
  }

  function turnHtml(t, k, h, isLast) {
    var a = t.status === "pending" ? '<p class="ph-wait"><span class="ph-spin"></span>Writing the answer…</p>'
      : t.status === "failed" ? '<p class="ph-err">' + esc(t.error || "Not answered.") + "</p>" +
        (isLast ? '<button type="button" class="ph-btn ph-sm" data-ph="retry">Try again</button>' : "")
      : '<div class="ph-ans">' + md(t.a) + "</div>";
    return '<div class="ph-turn"><p class="ph-q">' + esc(t.q) + "</p>" + a + "</div>";
  }
  function renderPanel() {
    ui(); var h = openId && hints.find(function (x) { return x.id === openId; });
    if (view === "hint" && h) {
      var t = h.thread || [], busy = pending(h);
      panel.innerHTML = '<div class="ph-head"><button type="button" class="ph-btn ph-sm" data-ph="back">← All hints</button><b>💡 Hint</b>' +
        '<span class="ph-when">' + when(h.created_at) + '</span><button type="button" class="ph-x" data-ph="close" aria-label="Close">×</button></div>' +
        '<div class="ph-body">' +
        (h.quote ? '<button type="button" class="ph-quote" data-ph="goto" title="Show it on the page">“' + esc(h.quote) + "”" +
          (h._found === false ? '<span class="ph-moved">not found on the page right now</span>' : "") + "</button>"
          : '<p class="ph-pageq">About this page</p>') +
        t.map(function (x, k) { return turnHtml(x, k, h, k === t.length - 1); }).join("") +
        '</div><div class="ph-foot"><textarea rows="2" maxlength="1500" placeholder="' + (busy ? "Wait for the answer, then ask more…" : "Ask a follow-up…") + '"' + (busy ? " disabled" : "") + "></textarea>" +
        '<div class="ph-row"><button type="button" class="ph-btn ph-primary" data-ph="ask"' + (busy ? " disabled" : "") + ">Ask</button>" +
        '<button type="button" class="ph-btn ph-danger" data-ph="del">' + (armed === h.id ? "Tap again to delete" : "Delete hint") + "</button></div></div>";
      var body = panel.querySelector(".ph-body"); body.scrollTop = body.scrollHeight;
    } else {
      view = "list";
      panel.innerHTML = '<div class="ph-head"><b>💡 Hints on this page</b><button type="button" class="ph-x" data-ph="close" aria-label="Close">×</button></div>' +
        '<div class="ph-body">' +
        (!available ? '<p class="ph-err">Highlights need MIGRATION_PAGE_HINTS.sql run in Supabase (safe to re-run).</p>' : "") +
        (hints.length ? hints.map(function (x) {
          var lt = last(x), first = (x.thread || [])[0] || {};
          return '<button type="button" class="ph-item" data-ph="open" data-hid="' + esc(x.id) + '">' +
            '<span class="ph-item-q">' + (x.quote ? "“" + esc(x.quote.length > 80 ? x.quote.slice(0, 78) + "…" : x.quote) + "”" : "About this page") + "</span>" +
            '<span class="ph-item-a">' + esc(first.q || "") + ((x.thread || []).length > 1 ? " · " + x.thread.length + " questions" : "") +
            (lt.status === "pending" ? " · writing…" : lt.status === "failed" ? " · not answered" : "") + "</span></button>";
        }).join("") : '<p class="ph-empty">No hints here yet. Select any words on the page and tap <b>💡 Highlight &amp; ask</b>.</p>') +
        "</div>" +
        '<div class="ph-foot"><textarea rows="2" maxlength="1500" placeholder="Ask about what you are reading on this page…"></textarea>' +
        '<div class="ph-row"><button type="button" class="ph-btn ph-primary" data-ph="ask-page">Ask about this page</button></div></div>';
    }
  }
  function openPanel() { ui(); closeBox(); panel.hidden = false; document.documentElement.classList.add("ph-open"); renderPanel(); }
  function closePanel() {
    if (panel) panel.hidden = true; document.documentElement.classList.remove("ph-open");
    var was = openId; openId = null; armed = null;
    if (was) { var h = hints.find(function (x) { return x.id === was; }); if (h) styleMarks(h); }
  }
  function openHint(id) {
    var prev = openId; openId = id; view = "hint"; armed = null;
    [prev, id].forEach(function (x) { var h = x && hints.find(function (y) { return y.id === x; }); if (h) styleMarks(h); });
    openPanel();
  }

  async function act(a, el) {
    var h = openId && hints.find(function (x) { return x.id === openId; });
    try {
      if (a === "pill") { if (!panel || panel.hidden) { view = "list"; openPanel(); } else closePanel(); }
      else if (a === "close") closePanel();
      else if (a === "back") { var was = openId; openId = null; view = "list"; if (was) { var hh = hints.find(function (x) { return x.id === was; }); if (hh) styleMarks(hh); } renderPanel(); }
      else if (a === "open") openHint(el.dataset.hid);
      else if (a === "save") saveBox();
      else if (a === "cancel") closeBox();
      else if (a === "goto" && h) { var m = marksOf(h.id)[0]; if (m) m.scrollIntoView({ behavior: "smooth", block: "center" }); else say("That passage isn't on the page right now — open the card it was in.", "info"); }
      else if (a === "ask" && h) {
        var ta = panel.querySelector(".ph-foot textarea"), q = ta.value.trim(); if (!q) { ta.focus(); return; }
        el.disabled = true;
        var j = await api("/api/hints/" + h.id + "/ask", { question: q, context: hintContext(h) });
        Object.assign(h, j.item); renderPanel(); styleMarks(h); schedulePoll(); paintPill();
      }
      else if (a === "retry" && h) { var r = await api("/api/hints/" + h.id + "/retry", { context: hintContext(h) }); Object.assign(h, r.item); renderPanel(); styleMarks(h); schedulePoll(); }
      else if (a === "del" && h) {
        if (armed !== h.id) { armed = h.id; renderPanel(); setTimeout(function () { if (armed === h.id) { armed = null; if (!panel.hidden) renderPanel(); } }, 4000); return; }
        await api("/api/hints/" + h.id + "/delete", {});
        unwrapMarks(h.id); hints = hints.filter(function (x) { return x.id !== h.id; });
        armed = null; openId = null; view = "list"; renderPanel(); paintPill(); say("Hint deleted", "success");
      }
      else if (a === "ask-page") {
        var t2 = panel.querySelector(".ph-foot textarea"), q2 = t2.value.trim(); if (!q2) { t2.focus(); return; }
        el.disabled = true;
        var c = await api("/api/hints", { page: PAGE, question: q2, context: pageContext() });
        hints.push(c.item); paintPill(); openHint(c.item.id); schedulePoll();
      }
    } catch (e) { say(e.message, "error"); if (el) el.disabled = false; }
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-ph]");
    if (b && b.closest(".ph-ui")) { e.preventDefault(); act(b.dataset.ph, b); return; }
    if (box && !box.hidden && !e.target.closest(".ph-box, .ph-chip")) closeBox();
    var m = e.target.closest && e.target.closest("mark.ph-hl");
    if (m && !norm(String(window.getSelection ? window.getSelection() : "")) && !m.closest("a, button, summary, label")) {
      e.preventDefault(); e.stopPropagation();
      if (openId === m.dataset.hid && panel && !panel.hidden) closePanel(); else openHint(m.dataset.hid);
    }
  }, true);
  var selT = null;
  document.addEventListener("selectionchange", function () { clearTimeout(selT); selT = setTimeout(checkSel, 250); });

  function schedulePoll() {
    clearTimeout(pollT);
    if (!hints.some(pending)) return;
    pollT = setTimeout(async function () {
      if (document.hidden) { schedulePoll(); return; }
      try { await load(true); } catch (_) {}
      schedulePoll();
    }, 3000);
  }
  async function load(quiet) {
    var j = await api("/api/hints?page=" + encodeURIComponent(PAGE));
    available = j.available !== false;
    var fresh = j.items || [];
    fresh.forEach(function (n) { var o = hints.find(function (x) { return x.id === n.id; }); if (o) n._found = o._found; });
    hints = fresh; loaded = true;
    paint(); paintPill();
    if (panel && !panel.hidden) {
      // Don't wipe a half-typed follow-up.
      var ta = panel.querySelector(".ph-foot textarea"), typed = ta && ta.value;
      renderPanel(); var ta2 = panel.querySelector(".ph-foot textarea"); if (ta2 && typed && !ta2.disabled) ta2.value = typed;
    }
    if (!quiet) schedulePoll();
  }
  // The page button slides away while you scroll down (so it never sits on
  // top of what you are reading) and comes back when you scroll up.
  var lastY = window.scrollY;
  window.addEventListener("scroll", function () {
    if (!pill) return;
    var y = window.scrollY, d = y - lastY;
    if (Math.abs(d) < 8) return;
    pill.classList.toggle("ph-away", d > 0 && y > 120);
    lastY = y;
  }, { passive: true });
  function start() {
    ui();
    load().catch(function () { available = false; });
    mo.observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

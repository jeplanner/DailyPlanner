// ==========================================================
// REFERENCE APP MODULE
// ==========================================================

(function () {

  // ==========================================================
  // GLOBALS
  // ==========================================================

  window.tagifyInstance = null;

  const state = {
    currentPage: 1,
    selectedTags: [],
    selectedCategory: null,
    searchQuery: "",
    sortOption: "created_at_desc",
    isLoading: false,
    hasMore: true,
    totalRendered: 0,
  };

  const referenceCache = {};
  let searchTimeout = null;
  let scrollTimeout = null;

  // ==========================================================
  // UTILITIES
  // ==========================================================

  function $(id) { return document.getElementById(id); }

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = String(str || "");
    return d.innerHTML;
  }

  const CATEGORY_COLORS = {
    "AI / ML":       "#7c3aed",
    "Programming":   "#2563eb",
    "Technology":    "#0891b2",
    "Finance":       "#16a34a",
    "Health":        "#dc2626",
    "Learning":      "#d97706",
    "Tech News":     "#0284c7",
    "Design":        "#db2777",
    "Productivity":  "#7c3aed",
    "Entertainment": "#ea580c",
    "Science":       "#059669",
    "Business":      "#4338ca",
    "Shopping":      "#be185d",
    "Other":         "#6b7280",
  };

  function categoryColor(cat, alpha) {
    const hex = CATEGORY_COLORS[cat] || "#6b7280";
    if (!alpha) return hex;
    // convert hex to rgba
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function safeHref(url) {
    try {
      const u = new URL(url);
      if (u.protocol === "http:" || u.protocol === "https:") return url;
    } catch (_) {}
    return "#";
  }

  function showToast(message, type = "info", duration = 2500) {
    const container = $("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<div class="toast-message">${esc(message)}</div><div class="toast-progress"></div>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add("show"), 10);
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  function clearCache() {
    Object.keys(referenceCache).forEach(k => delete referenceCache[k]);
  }

  function normalizedTagKey() {
    return [...state.selectedTags].sort().join(",");
  }

  // ==========================================================
  // SAVE REFERENCE
  // ==========================================================

  async function saveReference() {
    const rawDesc = ($("ref-description")?.value || "").trim();
    const payload = {
      title:       $("ref-title")?.value.trim() || null,
      description: rawDesc ? rawDesc.replace(/\n/g, "<br>") : null,
      url:         $("ref-url")?.value.trim(),
      tags:        window.tagifyInstance ? window.tagifyInstance.value.map(t => t.value) : [],
      category:    $("new-category")?.value.trim() || $("ref-category")?.value || null,
    };

    if (!payload.url) { showToast("URL is required", "error"); return; }

    const container = $("referenceList");
    if (!container) return;

    showToast("Saving reference...", "info", 1500);

    // Optimistic card — use safe DOM methods to avoid XSS
    const tempItem = document.createElement("div");
    tempItem.className = "ref-item saving";
    const titleLink = document.createElement("h4");
    const a = document.createElement("a");
    a.href = safeHref(payload.url);
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = payload.title || payload.url;
    titleLink.appendChild(a);
    tempItem.appendChild(titleLink);
    container.prepend(tempItem);

    try {
      const res = await fetch("/references/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Save failed");

      showToast("Saved successfully ✓", "success");

      // Reset form
      if (window.tagifyInstance) window.tagifyInstance.removeAllTags();
      if ($("ref-title"))       $("ref-title").value       = "";
      if ($("ref-url"))         $("ref-url").value         = "";
      if ($("ref-description")) $("ref-description").value = "";
      if ($("ref-category"))    $("ref-category").value    = "";
      if ($("new-category"))    $("new-category").value    = "";
      setFetchStatus(null);
      resetAIAssist();

      // Close modal after short delay so user sees the toast
      setTimeout(() => {
        if (typeof closeAddModal === "function") closeAddModal();
      }, 800);

      clearCache();
      resetAndReload();
      loadTagCloud();
      tempItem.classList.remove("saving");

    } catch (err) {
      tempItem.remove();
      showToast("Save failed. Please try again.", "error");
    }
  }

  // ==========================================================
  // AI RESET
  // ==========================================================

  function resetAIAssist() {
    const aiInput = $("ai-query");
    if (aiInput) aiInput.value = "";
  }

  // ==========================================================
  // SKELETON
  // ==========================================================

  function showSkeletonLoader() {
    const container = $("referenceList");
    if (!container || container.querySelector(".ref-skeleton")) return;
    for (let i = 0; i < 5; i++) {
      const s = document.createElement("div");
      s.className = "ref-skeleton";
      container.appendChild(s);
    }
  }

  function removeSkeletonLoader() {
    document.querySelectorAll(".ref-skeleton").forEach(el => el.remove());
  }

  // ==========================================================
  // LOAD REFERENCES
  // ==========================================================

  async function loadReferences() {
    if (state.isLoading || !state.hasMore) return;
    state.isLoading = true;

    const container = $("referenceList");
    if (!container) return;

    const cacheKey = `${state.currentPage}-${normalizedTagKey()}-${state.searchQuery}-${state.sortOption}-${state.selectedCategory}`;
    if (referenceCache[cacheKey]) {
      renderReferences(referenceCache[cacheKey]);
      state.isLoading = false;
      return;
    }

    let url = `/references/list?page=${state.currentPage}&sort=${state.sortOption}`;
    if (state.selectedTags.length > 0)  url += `&tags=${normalizedTagKey()}`;
    if (state.selectedCategory)          url += `&category=${encodeURIComponent(state.selectedCategory)}`;
    if (state.searchQuery)               url += `&search=${encodeURIComponent(state.searchQuery)}`;

    showSkeletonLoader();
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Server error");
      const data = await res.json();
      removeSkeletonLoader();
      referenceCache[cacheKey] = data;
      renderReferences(data);
    } catch (err) {
      removeSkeletonLoader();
      console.error("Load failed:", err);
    }
    state.isLoading = false;
  }

  // ==========================================================
  // RENDER — XSS safe
  // ==========================================================

  function renderReferences(data) {
    const container = $("referenceList");
    if (!container) return;

    if (!data.items || data.items.length === 0) {
      state.hasMore = false;
      if (state.currentPage === 1)
        container.innerHTML = "<div class='empty-state'>No references found. Add one below ↓</div>";
      return;
    }

    data.items.forEach(ref => {
      const item = document.createElement("div");
      item.className = "ref-item";
      item.dataset.id = ref.id;

      // Set category accent color via CSS custom property
      if (ref.category) {
        item.style.setProperty("--cat-color", categoryColor(ref.category));
      }

      // ── Top row: favicon + title + delete ──
      const header = document.createElement("div");
      header.className = "ref-item-header";

      // Favicon
      const favicon = document.createElement("img");
      favicon.className = "ref-favicon";
      try {
        const domain = new URL(ref.url).hostname;
        favicon.src   = `https://www.google.com/s2/favicons?sz=32&domain=${domain}`;
      } catch (_) {
        favicon.src = "";
      }
      favicon.onerror = () => { favicon.style.display = "none"; };
      favicon.width  = 16;
      favicon.height = 16;

      const titleBlock = document.createElement("div");
      titleBlock.className = "ref-title-block";

      const a = document.createElement("a");
      a.href        = safeHref(ref.url);
      a.target      = "_blank";
      a.rel         = "noopener noreferrer";
      a.className   = "ref-title-link";
      a.textContent = ref.title || ref.url;

      const domainSpan = document.createElement("span");
      domainSpan.className = "ref-domain";
      try { domainSpan.textContent = new URL(ref.url).hostname.replace("www.", ""); }
      catch (_) { domainSpan.textContent = ""; }

      titleBlock.appendChild(a);
      titleBlock.appendChild(domainSpan);

      const studyBtn = document.createElement("button");
      studyBtn.className   = "btn-study";
      studyBtn.title       = "Generate study notes";
      studyBtn.textContent = "📚";
      studyBtn.addEventListener("click", () => openStudyModal(ref.id, ref.title));

      const delBtn = document.createElement("button");
      delBtn.className   = "btn-delete";
      delBtn.title       = "Delete";
      delBtn.textContent = "🗑";
      delBtn.addEventListener("click", () => deleteReference(ref.id, item));

      header.appendChild(favicon);
      header.appendChild(titleBlock);
      header.appendChild(studyBtn);
      header.appendChild(delBtn);
      item.appendChild(header);

      // ── Description ──
      if (ref.description) {
        const descDiv = document.createElement("div");
        descDiv.className = "ref-content";
        descDiv.innerHTML = ref.description;
        item.appendChild(descDiv);
      }

      // ── Footer: tags + category ──
      const footer = document.createElement("div");
      footer.className = "ref-footer";

      const tagsWrap = document.createElement("div");
      tagsWrap.className = "ref-tags";
      (ref.tags || []).forEach(tag => {
        const span = document.createElement("span");
        span.className   = "tag";
        span.textContent = "#" + tag;
        span.title       = `Filter by "${tag}"`;
        span.addEventListener("click", () => {
          if (!state.selectedTags.includes(tag)) state.selectedTags.push(tag);
          resetAndReload();
        });
        tagsWrap.appendChild(span);
      });

      footer.appendChild(tagsWrap);

      if (ref.category) {
        const cat = document.createElement("span");
        cat.className = "category-pill";
        cat.textContent = ref.category;
        cat.style.background = categoryColor(ref.category, 0.12);
        cat.style.color      = categoryColor(ref.category);
        footer.appendChild(cat);
      }

      item.appendChild(footer);
      container.appendChild(item);
      state.totalRendered++;
    });

    state.hasMore = data.has_more;

    const resultCount = $("resultCount");
    if (resultCount)
      resultCount.textContent = `Showing ${state.totalRendered} result${state.totalRendered !== 1 ? "s" : ""}`;
  }

  // ==========================================================
  // DELETE
  // ==========================================================

  async function deleteReference(id, el) {
    // Inline confirm: swap the card into a red "Delete?" banner instead
    // of using the native browser confirm() dialog.
    if (el && !el.classList.contains("confirming-delete")) {
      const prevHTML = el.innerHTML;
      el.classList.add("confirming-delete");
      el.style.border = "1.5px solid #fecaca";
      el.style.background = "#fef2f2";
      el.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <strong style="font-size:13px;color:#991b1b;flex:1;min-width:160px;">Delete this entry? This can't be undone.</strong>
          <div style="display:flex;gap:6px;flex-shrink:0;">
            <button type="button" class="kb-btn kb-btn-ghost" id="kb-del-cancel-${id}" style="padding:6px 12px;font-size:12px;">Cancel</button>
            <button type="button" class="kb-btn" id="kb-del-yes-${id}"
                    style="padding:6px 12px;font-size:12px;background:#dc2626;color:#fff;border-color:#dc2626;">
              Delete
            </button>
          </div>
        </div>`;
      document.getElementById(`kb-del-cancel-${id}`)?.addEventListener("click", () => {
        el.classList.remove("confirming-delete");
        el.style.border = "";
        el.style.background = "";
        el.innerHTML = prevHTML;
        // Re-attach handlers on the restored content
        const newStudy = el.querySelector(".btn-study");
        const newDel = el.querySelector(".btn-delete");
        if (newStudy) newStudy.addEventListener("click", () => openStudyModal(id, el.querySelector(".ref-title-link")?.textContent));
        if (newDel) newDel.addEventListener("click", () => deleteReference(id, el));
      });
      document.getElementById(`kb-del-yes-${id}`)?.addEventListener("click", () => _kbConfirmDelete(id, el));
      return;
    }
    // Fallback path — continue to server call
    _kbConfirmDelete(id, el);
    return;
  }

  async function _kbConfirmDelete(id, el) {
    try {
      const res = await fetch(`/references/${id}`, { method: "DELETE" });
      if (res.ok) {
        el.remove();
        state.totalRendered = Math.max(0, state.totalRendered - 1);
        clearCache();
        loadTagCloud();
        const resultCount = $("resultCount");
        if (resultCount)
          resultCount.textContent = `Showing ${state.totalRendered} result${state.totalRendered !== 1 ? "s" : ""}`;
      }
    } catch (err) {
      showToast("Delete failed", "error");
    }
  }

  // ==========================================================
  // RESET
  // ==========================================================

  function resetAndReload() {
    state.currentPage   = 1;
    state.hasMore       = true;
    state.totalRendered = 0;
    const container = $("referenceList");
    if (container) container.innerHTML = "";
    loadReferences();
  }

  // ==========================================================
  // TAG CLOUD
  // ==========================================================

  async function loadTagCloud() {
    const container = $("tagCloud");
    if (!container) return;

    try {
      const res = await fetch("/references/tags");
      const groupedTags = await res.json();
      container.innerHTML = "";

      // Flatten all tags into a single sorted list showing only the top
      // most-used tags — the new sidebar is compact so group headers are
      // more clutter than help.
      const flat = [];
      Object.keys(groupedTags).forEach(group => {
        Object.entries(groupedTags[group]).forEach(([tag, count]) => {
          flat.push({ tag, count });
        });
      });
      flat.sort((a, b) => b.count - a.count);

      if (!flat.length) {
        container.innerHTML = `<div class="kb-facet-empty">No tags yet</div>`;
        return;
      }

      flat.slice(0, 40).forEach(({ tag, count }) => {
        const span = document.createElement("span");
        span.className = "tag" + (state.selectedTags.includes(tag) ? " active" : "");
        span.textContent = `#${tag}${count > 1 ? ' · ' + count : ''}`;
        span.title = `Filter by #${tag}`;
        span.addEventListener("click", () => {
          if (state.selectedTags.includes(tag)) {
            state.selectedTags = state.selectedTags.filter(t => t !== tag);
          } else {
            state.selectedTags.push(tag);
          }
          resetAndReload();
          loadTagCloud();
        });
        container.appendChild(span);
      });
    } catch (err) {
      console.error("loadTagCloud:", err);
      container.innerHTML = `<div class="kb-facet-empty">Failed to load tags</div>`;
    }
  }

  // ==========================================================
  // METADATA
  // ==========================================================

  function setFetchStatus(msg) {
    const bar  = $("fetch-status");
    const text = $("fetch-status-text");
    if (!bar) return;
    if (msg) {
      bar.style.display   = "flex";
      if (text) text.textContent = msg;
    } else {
      bar.style.display = "none";
    }
  }

  async function autoFetchMetadata() {
    const urlInput = $("ref-url");
    if (!urlInput || !urlInput.value.trim()) return;

    const useAI = $("enable-ai")?.checked !== false;

    setFetchStatus(useAI ? "Fetching title, description and tags…" : "Fetching title…");
    if ($("ref-description")) $("ref-description").value = "";

    try {
      const res = await fetch("/references/metadata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlInput.value.trim(), use_ai: useAI }),
      });
      if (!res.ok) return;
      const data = await res.json();

      // Title
      if ($("ref-title") && data.title) {
        $("ref-title").value = data.title;
        $("ref-title").placeholder = "Title (auto-filled from URL)";
      }

      // Description — plain textarea, always works
      if ($("ref-description")) {
        $("ref-description").value = data.description || "";
      }

      // Tags
      if (window.tagifyInstance && Array.isArray(data.tags) && data.tags.length) {
        window.tagifyInstance.removeAllTags();
        window.tagifyInstance.addTags(data.tags);
      }

      // Category
      if (data.category) {
        const catSelect = $("ref-category");
        if (catSelect) {
          // Try to match existing option
          const opt = [...catSelect.options].find(
            o => o.value.toLowerCase() === data.category.toLowerCase()
          );
          if (opt) catSelect.value = opt.value;
          else if ($("new-category")) $("new-category").value = data.category;
        }
      }

      setFetchStatus(null);
      showToast("Details fetched ✓", "success", 2000);

    } catch (err) {
      console.error("Metadata fetch failed:", err);
      setFetchStatus(null);
    }
  }

  // ==========================================================
  // STUDY MODAL
  // ==========================================================

  async function openStudyModal(refId, title) {
    const overlay  = document.getElementById("study-modal-overlay");
    const titleRow = document.getElementById("study-title-row");
    const notesEl  = document.getElementById("study-notes");
    const loading  = document.getElementById("study-loading");

    // Reset
    notesEl.innerHTML  = "";
    titleRow.innerHTML = "";
    loading.style.display = "flex";

    // Show title
    const h = document.createElement("h3");
    h.className   = "study-ref-title";
    h.textContent = title || "Study Notes";
    titleRow.appendChild(h);

    overlay.classList.add("open");
    document.body.style.overflow = "hidden";

    try {
      const res  = await fetch("/references/study", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ref_id: refId }),
      });
      const data = await res.json();

      loading.style.display = "none";

      if (data.error) {
        notesEl.textContent = "Could not generate study notes. Try again.";
        return;
      }

      notesEl.innerHTML = renderStudyMarkdown(data.notes);

    } catch (err) {
      loading.style.display = "none";
      notesEl.textContent = "Failed to load study notes.";
    }
  }

  function renderStudyMarkdown(md) {
    if (!md) return "";
    const lines  = md.split("\n");
    let html     = "";
    let inList   = false;

    for (const raw of lines) {
      const line = raw.trim();

      if (line.startsWith("## ")) {
        if (inList) { html += "</ul>"; inList = false; }
        const label = esc(line.slice(3));
        html += `<div class="study-section-header">${label}</div>`;

      } else if (line.startsWith("- ")) {
        if (!inList) { html += "<ul class='study-list'>"; inList = true; }
        html += `<li>${formatInline(line.slice(2))}</li>`;

      } else if (/^\d+\.\s/.test(line)) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<div class="study-quiz-item">${formatInline(line)}</div>`;

      } else if (line === "") {
        if (inList) { html += "</ul>"; inList = false; }

      } else {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<p class="study-para">${formatInline(line)}</p>`;
      }
    }

    if (inList) html += "</ul>";
    return html;
  }

  function formatInline(text) {
    return esc(text)
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>");
  }

  // ==========================================================
  // Q&A — Ask my references
  // ==========================================================

  function renderAskAnswer(text) {
    if (!text) return "";
    // Split on section headers like **Answer**, **Key Takeaway**, **Example or Analogy**
    const sectionIcons = {
      "Answer": "💬",
      "Key Takeaway": "🔑",
      "Example or Analogy": "💡",
      "Example": "💡",
      "Analogy": "💡",
    };

    let html = "";
    const lines = text.split("\n");
    let inSection = false;

    for (const raw of lines) {
      const line = raw.trim();

      // Detect **Section Header**
      const headerMatch = line.match(/^\*\*(.+?)\*\*\s*$/);
      if (headerMatch) {
        const label = headerMatch[1];
        const icon  = sectionIcons[label] || "•";
        if (inSection) html += "</div>";
        html += `<div class="ask-section">`;
        html += `<div class="ask-section-label">${icon} ${esc(label)}</div>`;
        html += `<div class="ask-section-body">`;
        inSection = true;
        continue;
      }

      if (line === "") continue;

      const formatted = esc(line)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\[(\d+)\]/g, "<strong class='cite'>[$1]</strong>");

      if (inSection) {
        html += `<p>${formatted}</p>`;
      } else {
        html += `<p>${formatted}</p>`;
      }
    }

    if (inSection) html += "</div></div>";
    return html;
  }

  async function askReferences() {
    const input     = $("ask-input");
    const answerEl  = $("ask-answer");
    const sourcesEl = $("ask-sources");
    const btn       = $("ask-btn");

    const question = input?.value.trim();
    if (!question) return;

    btn.disabled      = true;
    btn.textContent   = "Thinking…";
    answerEl.innerHTML = "";
    sourcesEl.innerHTML = "";
    $("ask-result").style.display = "none";

    try {
      const res  = await fetch("/references/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();

      if (data.error) {
        answerEl.textContent = "Error: " + data.error;
      } else {
        answerEl.innerHTML = renderAskAnswer(data.answer);

        if (data.sources && data.sources.length > 0) {
          const label = document.createElement("div");
          label.className   = "ask-sources-label";
          label.textContent = "Sources used:";
          sourcesEl.appendChild(label);

          data.sources.forEach((s, i) => {
            const row = document.createElement("div");
            const num = document.createElement("span");
            num.textContent = `[${i + 1}] `;
            num.style.color = "#6b7280";
            num.style.fontWeight = "600";
            const a = document.createElement("a");
            a.href        = safeHref(s.url);
            a.target      = "_blank";
            a.rel         = "noopener noreferrer";
            a.className   = "ask-source-link";
            a.textContent = s.title || s.url;
            row.appendChild(num);
            row.appendChild(a);
            sourcesEl.appendChild(row);
          });
        }
      }

      $("ask-result").style.display = "block";

    } catch (err) {
      answerEl.textContent = "Failed to get answer. Please try again.";
      $("ask-result").style.display = "block";
    }

    btn.disabled    = false;
    btn.textContent = "Ask";
  }

  // ==========================================================
  // INIT
  // ==========================================================

  document.addEventListener("DOMContentLoaded", function () {
    const params = new URLSearchParams(window.location.search);
    const initialTag      = params.get("tag");
    const initialCategory = params.get("category");
    if (initialTag)      state.selectedTags    = [initialTag.toLowerCase()];
    if (initialCategory) state.selectedCategory = initialCategory;

    // Tagify
    const tagInput = $("ref-tags");
    if (tagInput) {
      window.tagifyInstance = new Tagify(tagInput, {
        delimiters: ",",
        dropdown: { enabled: 0 },
      });
    }

    $("saveRefBtn")?.addEventListener("click", saveReference);
    // Trigger on blur (tab away) AND on paste
    $("ref-url")?.addEventListener("blur",  autoFetchMetadata);
    $("ref-url")?.addEventListener("paste", () => setTimeout(autoFetchMetadata, 100));

    // Search
    const searchInput = $("searchInput");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          state.searchQuery = this.value.trim();
          resetAndReload();
        }, 400);
      });
    }

    $("sortSelect")?.addEventListener("change", function () {
      state.sortOption = this.value;
      resetAndReload();
    });

    $("categoryFilter")?.addEventListener("change", function () {
      state.selectedCategory = this.value || null;
      resetAndReload();
    });

    $("resetFilterBtn")?.addEventListener("click", function () {
      state.selectedTags     = [];
      state.searchQuery      = "";
      state.sortOption       = "created_at_desc";
      state.selectedCategory = null;
      if ($("searchInput"))    $("searchInput").value    = "";
      if ($("sortSelect"))     $("sortSelect").value     = "created_at_desc";
      if ($("categoryFilter")) $("categoryFilter").value = "";
      document.querySelectorAll(".tag-cloud-item").forEach(el => el.classList.remove("active"));
      resetAndReload();
    });

    // Tag cloud toggle
    $("tagCloudToggle")?.addEventListener("click", function () {
      const cloud = $("tagCloud");
      const hidden = cloud.classList.toggle("tag-cloud-hidden");
      this.style.background = hidden ? "" : "#e0e7ff";
      this.style.color      = hidden ? "" : "#3730a3";
    });

    // Q&A
    $("ask-btn")?.addEventListener("click", askReferences);
    $("ask-input")?.addEventListener("keydown", e => {
      if (e.key === "Enter") askReferences();
    });

    loadTagCloud();
    loadReferences();
  });

  // ==========================================================
  // INFINITE SCROLL
  // ==========================================================

  window.addEventListener("scroll", function () {
    if (scrollTimeout) clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      if (state.isLoading || !state.hasMore) return;
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 250) {
        state.currentPage++;
        loadReferences();
      }
    }, 120);
  });

})();

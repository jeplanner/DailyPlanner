// ==========================================================
// REFERENCE APP MODULE
// ==========================================================

(function () {

  // ==========================================================
  // GLOBALS
  // ==========================================================

  window.tagifyInstance = null;
  let quillInstance = null;

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
    const payload = {
      title: $("ref-title")?.value.trim() || null,
      description: quillInstance ? quillInstance.root.innerHTML : null,
      url: $("ref-url")?.value.trim(),
      tags: window.tagifyInstance ? window.tagifyInstance.value.map(t => t.value) : [],
      category: $("new-category")?.value.trim() || $("ref-category")?.value || null,
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
      if (quillInstance) quillInstance.setContents([]);
      if (window.tagifyInstance) window.tagifyInstance.removeAllTags();
      if ($("ref-title"))    $("ref-title").value    = "";
      if ($("ref-url"))      $("ref-url").value      = "";
      if ($("ref-category")) $("ref-category").value = "";
      if ($("new-category")) $("new-category").value = "";
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
    const aiInput   = $("ai-query");
    const aiPreview = $("ai-preview");
    if (aiInput)   { aiInput.value = ""; aiInput.focus(); }
    if (aiPreview) aiPreview.innerHTML = "";
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

      const delBtn = document.createElement("button");
      delBtn.className   = "btn-delete";
      delBtn.title       = "Delete";
      delBtn.textContent = "🗑";
      delBtn.addEventListener("click", () => deleteReference(ref.id, item));

      header.appendChild(favicon);
      header.appendChild(titleBlock);
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
    if (!confirm("Delete this reference?")) return;
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

    const res = await fetch("/references/tags");
    const groupedTags = await res.json();
    container.innerHTML = "";

    Object.keys(groupedTags).sort().forEach(groupName => {
      const groupWrapper = document.createElement("div");
      groupWrapper.className = "tag-group";

      const header = document.createElement("div");
      header.className = "tag-group-header";
      header.textContent = `📁 ${groupName}`;

      const content = document.createElement("div");
      content.className = "tag-group-content";

      const groupTags = Object.keys(groupedTags[groupName]);
      if (groupTags.some(tag => state.selectedTags.includes(tag)))
        content.classList.add("open");

      header.addEventListener("click", () => content.classList.toggle("open"));

      groupTags.sort().forEach(tag => {
        const span = document.createElement("span");
        span.className = "tag-cloud-item" + (state.selectedTags.includes(tag) ? " active" : "");
        span.textContent = `# ${tag} (${groupedTags[groupName][tag]})`;
        span.onclick = function (e) {
          e.stopPropagation();
          span.classList.toggle("active");
          if (state.selectedTags.includes(tag))
            state.selectedTags = state.selectedTags.filter(t => t !== tag);
          else
            state.selectedTags.push(tag);
          resetAndReload();
        };
        content.appendChild(span);
      });

      groupWrapper.appendChild(header);
      groupWrapper.appendChild(content);
      container.appendChild(groupWrapper);
    });
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
    if (quillInstance) quillInstance.setText("");

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

      // Description — use dangerouslyPasteHTML so Quill formats it correctly
      if (quillInstance) {
        if (data.description) {
          quillInstance.setContents([]);
          quillInstance.clipboard.dangerouslyPasteHTML(
            `<p>${data.description.replace(/\n/g, "</p><p>")}</p>`
          );
        } else {
          quillInstance.setText("");
        }
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
      if (quillInstance) quillInstance.setText("");
    }
  }

  // ==========================================================
  // Q&A — Ask my references
  // ==========================================================

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
        // Render answer preserving line breaks and bold citations like [1]
        answerEl.innerHTML = data.answer
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
          .replace(/\[(\d+)\]/g, "<strong>[$1]</strong>")
          .replace(/\n/g, "<br>");

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

    // Quill
    const editor = $("ref-editor");
    if (editor) {
      quillInstance = new Quill("#ref-editor", {
        theme: "snow",
        modules: {
          toolbar: [
            [{ header: [1, 2, false] }],
            ["bold", "italic"],
            [{ list: "ordered" }, { list: "bullet" }],
            ["link"],
          ],
        },
      });
    }

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

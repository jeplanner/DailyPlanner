const AIAssist = (() => {
  let quill = null;
  let quillReady = false;

  const $ = (id) => document.getElementById(id);

  /* ---------------- Quill lazy init ---------------- */

  function ensureQuill() {
    if (quillReady) return true;
    const container = $("ai-preview");
    if (!container) return false;

    quill = new Quill("#ai-preview", {
      theme: "snow",
      modules: {
        toolbar: [
          ["bold", "italic", "underline"],
          [{ header: [1, 2, 3, false] }],
          [{ list: "ordered" }, { list: "bullet" }],
          ["link"]
        ]
      }
    });

    quill.on("text-change", () => {
      const editor = quill.root;
      editor.style.height = "auto";
      editor.style.height = editor.scrollHeight + "px";
    });

    quillReady = true;
    return true;
  }

  /* ---------------- Toast ---------------- */

  function showToast(message, type = "info", duration = 2500) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<div class="toast-message">${message}</div><div class="toast-progress"></div>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add("show"), 10);
    const progress = toast.querySelector(".toast-progress");
    if (progress) progress.style.animation = `toastProgress ${duration}ms linear forwards`;
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /* ---------------- Manual Mode ---------------- */

  function openManualMode(query) {
    navigator.clipboard.writeText(query);
    window.open("https://chat.openai.com", "_blank");
    showToast("Query copied. Paste in ChatGPT.");
  }

  /* ---------------- API Generate ---------------- */

  async function generateViaAPI(query, mode) {
    const endpoint = mode === "gemini"
      ? "/references/ai-generate"
      : "/references/ai-generate-groq";

    if (!ensureQuill()) return;

    quill.setText(`Generating with ${mode === "groq" ? "Groq" : "Gemini"}…`);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });

      if (!res.ok) { quill.setText("AI request failed."); return; }

      const data = await res.json();

      // Show in preview Quill
      quill.setContents([]);
      quill.clipboard.dangerouslyPasteHTML(`
        <h3>${data.title || ""}</h3>
        <p>${data.description || ""}</p>
        ${data.url ? `<p><a href="${data.url}" target="_blank">${data.url}</a></p>` : ""}
      `);
      setTimeout(() => {
        if (quill) {
          quill.root.style.height = "auto";
          quill.root.style.height = quill.root.scrollHeight + "px";
        }
      }, 50);

      // Autofill form fields
      if ($("ref-title"))       $("ref-title").value       = data.title    || "";
      if ($("ref-url"))         $("ref-url").value         = data.url      || "";
      if ($("ref-description")) $("ref-description").value = data.description || "";
      if ($("ref-category"))    $("ref-category").value    = data.category  || "";

      if (window.tagifyInstance && Array.isArray(data.tags)) {
        window.tagifyInstance.removeAllTags();
        window.tagifyInstance.addTags(data.tags);
      }

      showToast(`${mode === "groq" ? "Groq" : "Gemini"} content generated. Review and save.`, "success");

    } catch (err) {
      console.error(err);
      quill.setText("AI generation failed.");
      showToast("Error generating AI content.", "error");
    }
  }

  /* ---------------- Voice ---------------- */

  function initVoice() {
    const btn   = $("voiceBtn");
    const input = $("ai-query");
    if (!btn || !input) return;
    if (!("webkitSpeechRecognition" in window)) { btn.style.display = "none"; return; }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";

    btn.addEventListener("click", () => { recognition.start(); btn.innerText = "🎧"; });
    recognition.onresult = (e) => {
      input.value = e.results[0][0].transcript;
    };
    recognition.onend = () => { btn.innerText = "🎙"; };
  }

  /* ---------------- Generate Button ---------------- */

  function initGenerate() {
    const btn = $("ai-primary-btn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const query = $("ai-query")?.value.trim();
      const mode  = $("ai-mode")?.value;

      if (!query) {
        if (ensureQuill()) quill.setText("Please enter a topic.");
        return;
      }

      btn.disabled  = true;
      btn.innerText = "Generating…";

      try {
        if (mode === "manual") openManualMode(query);
        else await generateViaAPI(query, mode);
      } finally {
        btn.disabled  = false;
        btn.innerText = "Generate";
      }
    });
  }

  /* ---------------- Init ---------------- */

  function init() {
    const modeSelect = $("ai-mode");
    if (!modeSelect) return;

    const savedMode = localStorage.getItem("ai_mode");
    if (savedMode) modeSelect.value = savedMode;

    modeSelect.addEventListener("change", function () {
      localStorage.setItem("ai_mode", this.value);
    });

    // Do NOT init Quill here — it's inside a hidden modal
    initGenerate();
    initVoice();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", AIAssist.init);

/* ================================================
   GLOBAL JS — CSRF + Fetch Wrapper + Helpers
   Include in every page via _top_nav.html
   ================================================ */

(function () {
    "use strict";

    // ── CSRF Token ────────────────────────────────
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.content : "";

    // Patch fetch to auto-include CSRF token on non-GET requests
    const _fetch = window.fetch;
    window.fetch = function (url, options) {
        options = options || {};
        const method = (options.method || "GET").toUpperCase();

        if (csrfToken && method !== "GET" && method !== "HEAD") {
            options.headers = options.headers || {};
            // Support both Headers object and plain object
            if (options.headers instanceof Headers) {
                if (!options.headers.has("X-CSRFToken")) {
                    options.headers.set("X-CSRFToken", csrfToken);
                }
            } else {
                if (!options.headers["X-CSRFToken"]) {
                    options.headers["X-CSRFToken"] = csrfToken;
                }
            }
        }

        return _fetch.call(window, url, options);
    };

    // ── Dark Mode ─────────────────────────────────
    function applyTheme() {
        const stored = localStorage.getItem("dp-theme");
        if (stored === "dark") {
            document.documentElement.classList.add("dark");
        } else if (stored === "light") {
            document.documentElement.classList.remove("dark");
        }
        // If no preference stored, let CSS @media handle it
    }

    window.toggleDarkMode = function () {
        const isDark = document.documentElement.classList.toggle("dark");
        localStorage.setItem("dp-theme", isDark ? "dark" : "light");
        // Update toggle icon if exists
        const icon = document.getElementById("dark-mode-icon");
        if (icon) icon.textContent = isDark ? "sun" : "moon";
        if (window.feather) feather.replace();
    };

    applyTheme();

    // ── Loading Overlay Helpers ──────────��────────
    window.showLoading = function (containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.style.position = "relative";
        const overlay = document.createElement("div");
        overlay.className = "loading-overlay";
        overlay.id = containerId + "-loading";
        overlay.innerHTML = '<div class="loading-spinner"></div>';
        container.appendChild(overlay);
    };

    window.hideLoading = function (containerId) {
        const el = document.getElementById(containerId + "-loading");
        if (el) el.remove();
    };
})();

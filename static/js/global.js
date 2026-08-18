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
    // Tri-state: "dark" forces html.dark, "light" forces html.light, no
    // value lets the OS prefers-color-scheme @media query decide.
    // The .light class is essential — design-system.css scopes its dark
    // @media block to :root:not(.light) so a user who explicitly picks
    // light on a system-dark phone actually gets light tokens. Without
    // .light, html.dark would be cleared but the OS-pref dark block
    // would still inject dark tokens, producing white text on a white
    // surface.
    //
    // WHY THE NO-PREFERENCE BRANCH ALSO SETS .dark:
    // design-system.css defines the dark TOKENS twice, identically - once
    // under `html.dark` and once under
    //   @media (prefers-color-scheme: dark) { :root:not(.light) { ... } }
    // so on a system-dark phone with no stored preference the tokens
    // switched (--color-text became #f1f5f9) while html.dark was NEVER SET.
    // Individual pages hardcode light panels - #f6fefa, #fdf2f8, #eef2ff -
    // and revert them only under `html.dark`. The result was near-white
    // text on a near-white panel: the text was simply invisible. It hit
    // ~35 templates (/sql's Result block, its trap and portability notes,
    // its tags, and the same pattern on /todo, /inbox, /portfolio, ...).
    // Setting the class when the OS says dark makes every one of those
    // per-page rules fire. It is idempotent - html.dark carries the same
    // token values the media query already applied.
    function osPrefersDark() {
        return !!(window.matchMedia &&
                  window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    function applyTheme() {
        const root = document.documentElement;
        const stored = localStorage.getItem("dp-theme");
        if (stored === "dark") {
            root.classList.add("dark");
            root.classList.remove("light");
        } else if (stored === "light") {
            root.classList.add("light");
            root.classList.remove("dark");
        } else {
            root.classList.remove("light");
            root.classList.toggle("dark", osPrefersDark());
        }
    }

    // Follow the OS if the user has expressed no preference, so switching
    // the phone to dark at sunset does not leave half the page unreadable
    // until the next reload.
    if (window.matchMedia) {
        const mq = window.matchMedia("(prefers-color-scheme: dark)");
        const onChange = function () {
            if (!localStorage.getItem("dp-theme")) applyTheme();
        };
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        else if (mq.addListener) mq.addListener(onChange);
    }

    window.toggleDarkMode = function () {
        const root = document.documentElement;
        // Resolve current effective theme — class beats stored, stored
        // beats OS preference. We need this so the toggle flips between
        // explicit dark and explicit light, not "explicit dark → no
        // pref" which would re-engage the OS preference.
        const stored = localStorage.getItem("dp-theme");
        let effectiveDark;
        if (stored === "dark") effectiveDark = true;
        else if (stored === "light") effectiveDark = false;
        else effectiveDark = window.matchMedia &&
                              window.matchMedia("(prefers-color-scheme: dark)").matches;
        const next = effectiveDark ? "light" : "dark";
        localStorage.setItem("dp-theme", next);
        applyTheme();
        const icon = document.getElementById("dark-mode-icon");
        if (icon) icon.textContent = next === "dark" ? "sun" : "moon";
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

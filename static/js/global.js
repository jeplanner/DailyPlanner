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

/* ══════════════════════════════════════════════════════════════════════
   ARRIVING FROM THE DAY BOARD

   The board links into whichever section owns a row (?focus=<id>), and the
   shared nav renders a "← Board" chip on the way back (?from=board&bd=...).
   This is the third piece: making the arrival land ON the thing you tapped
   rather than at the top of a page you now have to search.

   Two problems it has to survive:

   1. MOST OF THESE PAGES RENDER THEIR LISTS IN JAVASCRIPT, after their own
      fetch. An element queried at DOMContentLoaded is usually not there yet,
      so this retries on a MutationObserver until the row appears, and gives
      up after a few seconds rather than observing forever.
   2. THE ID MAY SIMPLY NOT BE ON THE PAGE — the task was completed and
      filtered out, the date moved on, the item was deleted. That is a normal
      outcome, not an error: the page is still the right page, so it stays
      silent rather than showing a failure for something the user can see.
   ══════════════════════════════════════════════════════════════════════ */
(function () {
    "use strict";

    var params = new URLSearchParams(window.location.search);
    var focusId = params.get("focus");
    var fromBoard = params.get("from") === "board";

    /* Esc goes back to the board, matching the board's own Esc-to-menu.
       Skipped while typing, so it cannot eat an editor's escape. */
    if (fromBoard) {
        document.addEventListener("keydown", function (ev) {
            if (ev.key !== "Escape") return;
            var t = ev.target;
            if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
                      t.isContentEditable)) return;
            var chip = document.querySelector(".back-board");
            if (chip) window.location.href = chip.getAttribute("href");
        });
    }

    if (!focusId) return;

    var DEADLINE = 6000;
    var started = Date.now();
    var observer = null;
    var done = false;

    function find() {
        /* data-focus-id is the explicit hook; data-id is what the existing
           task and list markup already carries, so both are accepted. The
           id is escaped because it comes from the URL. */
        var safe = (window.CSS && CSS.escape) ? CSS.escape(focusId)
                                              : focusId.replace(/["\\\]]/g, "\\$&");
        return document.querySelector('[data-focus-id="' + safe + '"]') ||
               document.querySelector('[data-id="' + safe + '"]');
    }

    function land(el) {
        if (done) return;
        done = true;
        if (observer) observer.disconnect();
        try {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (_) {
            el.scrollIntoView();
        }
        el.classList.add("board-focus");
        /* Remove the class rather than leaving it: a permanent highlight
           reads as a state the item is in, not as "here is what you tapped". */
        setTimeout(function () { el.classList.remove("board-focus"); }, 2600);
    }

    function attempt() {
        var el = find();
        if (el) { land(el); return true; }
        if (Date.now() - started > DEADLINE && observer) {
            observer.disconnect();
            observer = null;
        }
        return false;
    }

    function start() {
        if (attempt()) return;
        if (!window.MutationObserver) return;
        observer = new MutationObserver(attempt);
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(function () {
            if (observer) { observer.disconnect(); observer = null; }
        }, DEADLINE);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }

    /* Injected rather than added to every stylesheet, so a page that never
       receives a ?focus= never pays for it. */
    var style = document.createElement("style");
    style.textContent =
        ".board-focus{animation:board-focus-flash 2.4s ease-out 1;" +
        "outline:2px solid #6366f1 !important;outline-offset:2px;" +
        "border-radius:8px;scroll-margin:80px}" +
        "@keyframes board-focus-flash{" +
        "0%,25%{background:rgba(99,102,241,.28)}" +
        "100%{background:transparent}}" +
        "@media (prefers-reduced-motion:reduce){" +
        ".board-focus{animation:none;background:rgba(99,102,241,.18)}}";
    document.head.appendChild(style);
})();

/* font_scale.js — small controller for A-/A+ text-size buttons.
 *
 * Sets a CSS custom property (default `--story-font-scale`) on a target
 * element so any rule using `calc(<base>px * var(--story-font-scale))`
 * scales together. Choice is persisted in localStorage under a shared
 * key so it carries across story pages without requiring login.
 *
 * Usage:
 *   <div id="fs">
 *     <button data-fs-action="dec" aria-label="Smaller">A−</button>
 *     <span data-fs-readout>100%</span>
 *     <button data-fs-action="inc" aria-label="Larger">A+</button>
 *     <button data-fs-action="reset" aria-label="Reset">↺</button>
 *   </div>
 *   <script>FontScale.attach({ container: "#fs" });</script>
 *
 * Keyboard: + / - / 0  (when focus is not in an input/textarea).
 */
(function (global) {
  const STORAGE_KEY = "font-scale.stories";
  const MIN = 0.85, MAX = 1.6, STEP = 0.1, DEFAULT = 1.0;

  function _clamp(v) { return Math.max(MIN, Math.min(MAX, v)); }
  function _round(v) { return Math.round(v * 100) / 100; }

  function _read() {
    try {
      const raw = parseFloat(localStorage.getItem(STORAGE_KEY));
      if (!isFinite(raw)) return DEFAULT;
      return _clamp(raw);
    } catch (_) { return DEFAULT; }
  }
  function _write(v) {
    try { localStorage.setItem(STORAGE_KEY, String(v)); } catch (_) {}
  }

  function _apply(scale, ctx) {
    ctx.target.style.setProperty(ctx.cssVar, scale);
    if (ctx.readout) ctx.readout.textContent = Math.round(scale * 100) + "%";
  }

  function attach(opts) {
    opts = opts || {};
    const container = (typeof opts.container === "string")
      ? document.querySelector(opts.container) : opts.container;
    if (!container) return;
    const target = (typeof opts.target === "string")
      ? document.querySelector(opts.target) : (opts.target || document.documentElement);
    const ctx = {
      target,
      cssVar: opts.cssVar || "--story-font-scale",
      readout: container.querySelector("[data-fs-readout]"),
    };

    let scale = _read();
    _apply(scale, ctx);

    container.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-fs-action]");
      if (!btn) return;
      const action = btn.dataset.fsAction;
      if (action === "inc") scale = _clamp(_round(scale + STEP));
      else if (action === "dec") scale = _clamp(_round(scale - STEP));
      else if (action === "reset") scale = DEFAULT;
      else return;
      _write(scale);
      _apply(scale, ctx);
    });

    document.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "+" || e.key === "=") scale = _clamp(_round(scale + STEP));
      else if (e.key === "-" || e.key === "_") scale = _clamp(_round(scale - STEP));
      else if (e.key === "0") scale = DEFAULT;
      else return;
      e.preventDefault();
      _write(scale);
      _apply(scale, ctx);
    });
  }

  global.FontScale = { attach };
})(window);

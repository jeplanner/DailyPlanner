/* A clap for something finished.
 *
 * Asked for as "clap on items which are finished on the inteview prep pages
 * and also on dayboard".
 *
 * WHY ONE FILE. The prep banks, the board and the checklist all mark things
 * done in their own way, and three hand-rolled confetti routines would drift
 * into three different celebrations for the same act. This is the whole
 * vocabulary: window.dpClap(el) claps at an element.
 *
 * IT MUST NEVER COST ANYTHING. The burst is a handful of absolutely
 * positioned spans on a layer that ignores the pointer, removed when the
 * animation ends. It never blocks a click, never holds a timer open, and it
 * does nothing at all under prefers-reduced-motion — a celebration is the
 * first thing that should go quiet for someone who asked for less movement.
 */
(function () {
  "use strict";
  if (window.dpClap) return;

  var HANDS = ["👏", "👏", "✨", "🎉"];
  var layer = null;
  var styled = false;

  function reduced() {
    try {
      return window.matchMedia &&
             window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) { return false; }
  }

  function ensureStyle() {
    if (styled) return;
    styled = true;
    var css =
      "#dp-clap{position:fixed;inset:0;pointer-events:none;z-index:99999;" +
        "overflow:hidden}" +
      "#dp-clap span{position:absolute;will-change:transform,opacity;" +
        "font-size:20px;line-height:1;animation:dp-clap-fly .9s ease-out forwards}" +
      "@keyframes dp-clap-fly{" +
        "0%{opacity:0;transform:translate(-50%,-50%) scale(.5)}" +
        "18%{opacity:1}" +
        "100%{opacity:0;transform:translate(calc(-50% + var(--dx)),"+
             "calc(-50% + var(--dy))) scale(1.15) rotate(var(--rot))}}" +
      /* The badge that says WHY it clapped. Silent applause with no reason
         attached reads as a glitch. */
      "#dp-clap b{position:absolute;transform:translate(-50%,-50%);" +
        "font-size:12px;font-weight:800;white-space:nowrap;padding:5px 11px;" +
        "border-radius:999px;background:#0f172a;color:#fff;" +
        "box-shadow:0 6px 18px rgba(0,0,0,.3);" +
        "animation:dp-clap-say 1.5s ease-out forwards}" +
      "@keyframes dp-clap-say{0%{opacity:0;transform:translate(-50%,-30%) scale(.9)}" +
        "14%{opacity:1;transform:translate(-50%,-50%) scale(1)}" +
        "70%{opacity:1}100%{opacity:0;transform:translate(-50%,-90%) scale(1)}}";
    var el = document.createElement("style");
    el.id = "dp-clap-style";
    el.textContent = css;
    document.head.appendChild(el);
  }

  function ensureLayer() {
    if (layer && layer.isConnected) return layer;
    layer = document.createElement("div");
    layer.id = "dp-clap";
    layer.setAttribute("aria-hidden", "true");   // decorative, never announced
    document.body.appendChild(layer);
    return layer;
  }

  /* Where to clap. An element that has scrolled out of view, or was removed
     by the very update that finished it, has no useful box — fall back to
     the middle of the screen rather than clapping at 0,0. */
  function pointFor(el) {
    try {
      if (el && el.getBoundingClientRect) {
        var r = el.getBoundingClientRect();
        if (r.width || r.height) {
          return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        }
      }
    } catch (e) { /* detached */ }
    return { x: window.innerWidth / 2, y: window.innerHeight / 3 };
  }

  /* ── THE PREP BANKS, WITHOUT TOUCHING FIVE TEMPLATES ────────────────
     "clap on items which are finished on the inteview prep pages".

     Every bank marks a topic studied with a checkbox inside a .q-card —
     .q-prac on /ai-sde, /interview-prep and the TPM rounds, and a bare box
     carrying data-title on /java and /sql. Matching the SHAPE here rather
     than editing each page means a new bank gets the clap for free, and
     there is one celebration instead of five that drift apart.

     Delegated and passive: these pages rebuild their lists constantly, so a
     listener bound per checkbox would be lost with the first repaint. */
  document.addEventListener("change", function (ev) {
    var box = ev.target;
    if (!box || box.type !== "checkbox" || !box.checked) return;
    if (!box.closest || !box.closest(".q-card")) return;
    if (!box.classList.contains("q-prac") && !box.hasAttribute("data-title")) return;
    // Unticking is a correction, not an achievement — only the tick claps.
    window.dpClap(box, "Studied");
  });

  window.dpClap = function (el, message) {
    if (reduced()) return;
    try {
      ensureStyle();
      var host = ensureLayer();
      var p = pointFor(el);
      var n = 10;
      for (var i = 0; i < n; i++) {
        var s = document.createElement("span");
        s.textContent = HANDS[i % HANDS.length];
        s.style.left = p.x + "px";
        s.style.top = p.y + "px";
        // Fanned upward and outward: a burst that also falls downward reads
        // as something breaking rather than something achieved.
        var ang = (Math.PI * (0.15 + 0.7 * (i / (n - 1)))) + Math.PI;
        var dist = 46 + (i % 4) * 22;
        s.style.setProperty("--dx", Math.cos(ang) * dist + "px");
        s.style.setProperty("--dy", Math.sin(ang) * dist + "px");
        s.style.setProperty("--rot", ((i % 2 ? 1 : -1) * (20 + i * 7)) + "deg");
        s.style.animationDelay = (i * 18) + "ms";
        s.addEventListener("animationend", function () { this.remove(); });
        host.appendChild(s);
      }
      if (message) {
        var b = document.createElement("b");
        b.textContent = message;
        b.style.left = p.x + "px";
        b.style.top = (p.y - 26) + "px";
        b.addEventListener("animationend", function () { this.remove(); });
        host.appendChild(b);
      }
    } catch (e) { /* a celebration must never break the thing it celebrates */ }
  };
})();

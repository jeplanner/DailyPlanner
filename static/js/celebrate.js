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
    window.dpParty(box, "Studied \u2014 nicely done");
  });

  /* ── THE LONG CELEBRATION ────────────────────────────────────────
     "claps should be for atleast 20 seconds... Along with clap dancing and
     singing girl should be shown."

     IT RESTARTS, IT DOES NOT STACK. Twenty seconds is a long time on a
     prep page where ten topics get ticked in a row — ten overlapping
     parties would be unusable and would drown the page in DOM. A new
     celebration resets the clock on the running one instead.

     It sits in a corner, ignores the pointer, and can be dismissed by
     clicking it. Nothing about it blocks the work being celebrated. */
  var HOLD_MS = 20000;
  var party = null, partyEnds = 0, partyTimer = null;

  function endParty() {
    if (partyTimer) { clearInterval(partyTimer); partyTimer = null; }
    if (party) { party.remove(); party = null; }
  }

  function ensureParty(message) {
    if (party && party.isConnected) {
      if (message) {
        var m = party.querySelector(".dp-party-say");
        if (m) m.textContent = message;
      }
      return party;
    }
    party = document.createElement("div");
    party.className = "dp-party";
    party.setAttribute("aria-hidden", "true");
    party.innerHTML =
      '<div class="dp-party-cast">' +
        '<span class="dp-dancer dp-d1">\uD83D\uDC83</span>' +
        '<span class="dp-dancer dp-d2">\uD83D\uDD7A</span>' +
        '<span class="dp-note dp-n1">\uD83C\uDFB5</span>' +
        '<span class="dp-note dp-n2">\uD83C\uDFB6</span>' +
        '<span class="dp-note dp-n3">\u2728</span>' +
      '</div>' +
      '<b class="dp-party-say"></b>';
    party.querySelector(".dp-party-say").textContent = message || "Nicely done";
    // Clicking it out is the only control it needs — it leaves on its own.
    party.addEventListener("click", endParty);
    document.body.appendChild(party);
    return party;
  }

  function partyStyle() {
    if (document.getElementById("dp-party-style")) return;
    var css =
      ".dp-party{position:fixed;right:16px;bottom:16px;z-index:99998;" +
        "display:flex;flex-direction:column;align-items:center;gap:6px;" +
        "padding:12px 16px 10px;border-radius:16px;cursor:pointer;" +
        "background:rgba(15,23,42,.92);color:#fff;" +
        "box-shadow:0 14px 40px rgba(0,0,0,.35);" +
        "animation:dp-party-in .4s cubic-bezier(.2,.9,.25,1)}" +
      ".dp-party-cast{position:relative;display:flex;gap:4px;font-size:34px;" +
        "line-height:1}" +
      ".dp-dancer{display:inline-block;transform-origin:50% 90%}" +
      ".dp-d1{animation:dp-dance .62s ease-in-out infinite alternate}" +
      ".dp-d2{animation:dp-dance .62s ease-in-out infinite alternate-reverse}" +
      ".dp-note{position:absolute;top:-2px;font-size:15px;opacity:0;" +
        "animation:dp-note-up 2.1s ease-out infinite}" +
      ".dp-n1{left:-6px;animation-delay:0s}" +
      ".dp-n2{left:26px;animation-delay:.7s}" +
      ".dp-n3{left:56px;animation-delay:1.4s}" +
      ".dp-party-say{font-size:12.5px;font-weight:800;letter-spacing:.01em;" +
        "white-space:nowrap;max-width:46vw;overflow:hidden;" +
        "text-overflow:ellipsis}" +
      "@keyframes dp-party-in{from{opacity:0;transform:translateY(18px) scale(.9)}" +
        "to{opacity:1;transform:none}}" +
      "@keyframes dp-dance{from{transform:rotate(-13deg) translateY(0)}" +
        "to{transform:rotate(13deg) translateY(-7px)}}" +
      "@keyframes dp-note-up{0%{opacity:0;transform:translateY(0) scale(.7)}" +
        "20%{opacity:1}100%{opacity:0;transform:translateY(-40px) scale(1.1)}}" +
      "@media (max-width:520px){.dp-party{right:10px;bottom:10px;" +
        "padding:9px 12px 8px}.dp-party-cast{font-size:28px}}";
    var el = document.createElement("style");
    el.id = "dp-party-style";
    el.textContent = css;
    document.head.appendChild(el);
  }

  function burst(el) {
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
  }

  function badge(el, message) {
    var host = ensureLayer();
    var p = pointFor(el);
    var b = document.createElement("b");
    b.textContent = message;
    b.style.left = p.x + "px";
    b.style.top = (p.y - 26) + "px";
    b.addEventListener("animationend", function () { this.remove(); });
    host.appendChild(b);
  }

  window.dpClap = function (el, message, opts) {
    if (reduced()) return;
    try {
      ensureStyle();
      burst(el);

      // A short burst is enough for one checkbox. The full twenty seconds
      // is for finishing something — passed explicitly so ordinary ticks
      // do not each start a party.
      if (!(opts && opts.long)) {
        if (message) badge(el, message);
        return;
      }

      partyStyle();
      ensureParty(message);
      partyEnds = Date.now() + HOLD_MS;
      if (!partyTimer) {
        partyTimer = setInterval(function () {
          if (Date.now() >= partyEnds) { endParty(); return; }
          burst(party);           // keep clapping for the whole twenty
        }, 1400);
      }
    } catch (e) { /* a celebration must never break the thing it celebrates */ }
  };

  window.dpParty = function (el, message) {
    window.dpClap(el, message, { long: true });
  };
})();

/* The collapsible sidebar, in a real DOM.
 *
 * "the left side bar menu collapsable. it is too much scrolling, group it
 * by categories and i could expand or collapse" (2026-08-30).
 *
 * The page is rendered by Flask (tests/test_smoke.py writes it to the path
 * given as argv[2]) and the real static/js/nav-groups.js is run against it,
 * so the TEMPLATE and the SCRIPT are checked together. This script does
 * nothing but move real nodes around — it replaces the heading, re-parents
 * every link — and there is no string in either file that can tell you
 * whether that worked.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const SRC = __dirname + "/../../static/js/nav-groups.js";
const src = fs.readFileSync(SRC, "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

function boot({ activeHref = "/quick-bucket", storage = null } = {}) {
  const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://example.test" + activeHref,
  });
  const { window } = dom;
  const doc = window.document;

  // The inline highlightActiveNav() in _top_nav.html does not run under
  // runScripts:"outside-only", so mark the current link the same way it
  // would — that mark is what decides which group opens.
  const link = doc.querySelector(`.sidebar-nav a[href="${activeHref}"]`);
  if (link) link.classList.add("active");

  if (storage) {
    window.localStorage.setItem("dp-nav-groups-v1", JSON.stringify(storage));
  }
  window.eval(src);
  return { window, doc };
}

const groupsOf = (doc) =>
  [...doc.querySelectorAll(".sidebar-nav .nav-group")]
    .filter((g) => !g.classList.contains("nav-footer"));

const byName = (doc, name) =>
  groupsOf(doc).find((g) => g.dataset.navName === name);

// ── it actually rewires the markup ──────────────────────────────────
{
  const { doc } = boot();
  const groups = groupsOf(doc);
  ok("the sidebar still has its category groups", groups.length >= 4);

  ok("every group heading became a button",
     groups.every((g) => g.querySelector("button.nav-group-title")));
  ok("no plain-div heading is left behind",
     !doc.querySelector("div.nav-group-title"));

  ok("every group's links moved into the collapsible part",
     groups.every((g) => {
       const items = g.querySelector(".nav-group-items");
       return items && items.querySelectorAll("a").length > 0 &&
              g.querySelectorAll(":scope > a").length === 0;
     }));

  ok("nothing was lost in the move",
     doc.querySelectorAll(".sidebar-nav a[href]").length ===
     doc.querySelectorAll(".sidebar-nav .nav-group-items a[href], " +
                          ".sidebar-nav .nav-footer a[href]").length);

  ok("the heading says how many links it hides",
     groups.every((g) => {
       const n = g.querySelector(".nav-group-count");
       return n && Number(n.textContent) ===
                   g.querySelectorAll(".nav-group-items a").length;
     }));

  ok("the button reports its state to a screen reader",
     groups.every((g) => {
       const b = g.querySelector(".nav-group-title");
       return b.getAttribute("aria-expanded") === (g.dataset.open === "1" ? "true" : "false") &&
              b.getAttribute("aria-controls") === g.querySelector(".nav-group-items").id;
     }));

  // THE POINT OF THE WHOLE THING: most of it is put away.
  const open = groups.filter((g) => g.dataset.open === "1");
  ok("only one group is open on a fresh device", open.length === 1);
  ok("...and it is the one holding the page you are on",
     open[0].querySelector('a[href="/quick-bucket"]') !== null);
}

// ── the group you are in is never hidden ────────────────────────────
{
  // Saved state says Today is shut. You are on a Today page.
  const { doc } = boot({ activeHref: "/quick-bucket",
                         storage: { Today: false, Work: true } });
  const today = byName(doc, "Today");
  ok("a saved 'collapsed' cannot hide the page you are on",
     today.dataset.open === "1");
  ok("...and it is flagged as the one you are in", today.dataset.here === "1");
  ok("an unrelated group keeps what you saved",
     byName(doc, "Work").dataset.open === "1");
}

// ── clicking, and remembering ───────────────────────────────────────
{
  const { window, doc } = boot({ activeHref: "/quick-bucket" });
  const work = byName(doc, "Work");
  ok("a group you are not in starts collapsed", work.dataset.open === "0");

  work.querySelector(".nav-group-title").click();
  ok("clicking the heading opens it", work.dataset.open === "1");
  ok("...and the arrow state follows",
     work.querySelector(".nav-group-title").getAttribute("aria-expanded") === "true");

  work.querySelector(".nav-group-title").click();
  ok("clicking again puts it away", work.dataset.open === "0");

  const saved = JSON.parse(window.localStorage.getItem("dp-nav-groups-v1"));
  ok("the choice is remembered", saved.Work === false);
}

// ── expand all / collapse all ───────────────────────────────────────
{
  const { doc } = boot({ activeHref: "/quick-bucket" });
  const all = doc.querySelector(".nav-allbtn");
  ok("there is one control for the whole menu", !!all);
  ok("it offers to open everything when most is shut",
     all.textContent === "Collapse all" || all.textContent === "Expand all");

  const groups = groupsOf(doc);
  // Collapse everything...
  if (all.textContent === "Collapse all") all.click();
  ok("collapse all leaves only the group you are in",
     groups.filter((g) => g.dataset.open === "1").length === 1);
  ok("...which is that group", byName(doc, "Today").dataset.open === "1");
  // A control that cannot undo itself is a broken control: after putting
  // everything away, the next press must bring it back.
  ok("...and the button now offers to bring it all back",
     all.textContent === "Expand all");

  all.click();
  ok("expand all opens every group",
     groups.every((g) => g.dataset.open === "1"));
  ok("...and the button now offers the opposite",
     all.textContent === "Collapse all");
}

// ── a page the menu does not know about ─────────────────────────────
{
  const { doc } = boot({ activeHref: "/nowhere-in-the-menu" });
  const open = groupsOf(doc).filter((g) => g.dataset.open === "1");
  ok("a page that matches nothing still leaves a way in", open.length >= 1);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

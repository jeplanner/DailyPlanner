/* The Projects list — find, order, and what the card actually says.
 *
 * "can you review the projects menu item ... make it more user friendly.
 * UX also clean." (2026-08-30)
 *
 * The page is rendered by Flask (tests/test_smoke.py passes the path as
 * argv[2]) with real-shaped project rows, and the page's own inline script
 * is run against it. Sorting and filtering are DOM reordering — there is no
 * string in the template that can tell you the late project came first.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

function boot() {
  const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
    runScripts: "dangerously",          // the page's logic is inline
    pretendToBeVisual: true,
    url: "https://example.test/projects",
    // The nav calls feather.replace() unguarded and the CDN never loads
    // here. Stub it before parsing so the console stays readable — the
    // icons are not what this test is about.
    beforeParse(w) { w.feather = { replace() {} }; },
  });
  const { window } = dom;
  return { window, doc: window.document };
}

const names = (doc) =>
  [...doc.querySelectorAll(".project-card-wrap")]
    .filter((c) => !c.hidden)
    .map((c) => c.dataset.name);

const cardFor = (doc, name) =>
  [...doc.querySelectorAll(".project-card-wrap")].find((c) => c.dataset.name === name);

const { window, doc } = boot();

// ── the card says what is wrong, not just how far along ─────────────
{
  const late = cardFor(doc, "cloudera architect certification");
  ok("the late project renders", !!late);
  ok("its chip counts the overdue work",
     /29 overdue/.test(late.querySelector(".chip").textContent));
  ok("its chip is styled as late",
     late.querySelector(".chip").classList.contains("chip-late"));
  ok("its progress bar is red, not the same yellow as a new project",
     late.querySelector(".progress-fill").classList.contains("red"));

  const empty = cardFor(doc, "brand new idea");
  ok("a project with no tasks says so rather than showing 0%",
     /No tasks/.test(empty.querySelector(".chip").textContent));
  ok("...and shows no progress bar at all",
     empty.querySelector(".progress-fill") === null);

  const done = cardFor(doc, "shipped thing");
  ok("a finished project reads as finished",
     /Finished/.test(done.querySelector(".chip").textContent));
  ok("...in green", done.querySelector(".progress-fill").classList.contains("green"));

  const live = cardFor(doc, "office");
  ok("an ordinary project counts what is open",
     /8 open/.test(live.querySelector(".chip").textContent));
}

// ── the headline numbers ────────────────────────────────────────────
{
  const bar = doc.querySelector(".stats-bar").textContent.replace(/\s+/g, " ");
  ok("the bar totals the overdue work across every project", /29 overdue/.test(bar));
  ok("...and the open work", /37 tasks open/.test(bar));
  ok("...and it is marked as late", !!doc.querySelector(".stats-bar .is-late"));
}

// ── default order: what needs attention ─────────────────────────────
{
  const order = names(doc);
  ok("the late project is first, not the oldest one",
     order[0] === "cloudera architect certification");
  ok("live work outranks a project with no tasks",
     order.indexOf("office") < order.indexOf("brand new idea"));
  ok("finished work sinks to the bottom",
     order[order.length - 1] === "shipped thing");
}

// ── search ──────────────────────────────────────────────────────────
{
  const search = doc.getElementById("project-search");
  search.value = "off";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  ok("typing filters to the match", names(doc).join() === "office");
  ok("...and the rest are hidden, not removed",
     doc.querySelectorAll(".project-card-wrap").length > 1);

  search.value = "zzzz";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  ok("a search with no hits says so",
     doc.getElementById("no-match").style.display === "block");

  search.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  ok("Escape clears the filter", names(doc).length > 1);
  ok("...and hides the no-match line",
     doc.getElementById("no-match").style.display === "none");
}

// ── sort, and it is remembered ──────────────────────────────────────
{
  const sort = doc.getElementById("project-sort");
  sort.value = "name";
  sort.dispatchEvent(new window.Event("change", { bubbles: true }));
  const byName = names(doc);
  ok("sorting by name is alphabetical",
     byName.join() === [...byName].sort().join());

  sort.value = "progress";
  sort.dispatchEvent(new window.Event("change", { bubbles: true }));
  ok("sorting by progress puts the finished one first",
     names(doc)[0] === "shipped thing");

  ok("the choice is remembered for next time",
     JSON.parse(window.localStorage.getItem("projects-view-v1")).sort === "progress");
}

// ── the menu tells the truth about what it does ─────────────────────
{
  const btn = doc.querySelector(".card-menu-btn");
  ok("the action button starts closed", btn.getAttribute("aria-expanded") === "false");
  btn.click();
  ok("...and reports itself open", btn.getAttribute("aria-expanded") === "true");
  doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  ok("Escape closes it", btn.getAttribute("aria-expanded") === "false");

  const labels = [...doc.querySelectorAll(".card-menu button")].map((b) => b.textContent.trim());
  ok("nothing is labelled Delete, because nothing deletes",
     !labels.some((l) => /delete/i.test(l)));
  ok("it is called Archive", labels.some((l) => /archive/i.test(l)));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

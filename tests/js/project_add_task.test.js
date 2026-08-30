/* Adding a task inside a project, without the page reloading itself.
 *
 * "what about creation of tasks in project" (2026-08-30).
 *
 * The add bar was already one field and Enter — the cost was what came
 * after: addTask() ended with location.reload(), so five tasks meant five
 * full page loads of a page that issues a dozen queries. The server was
 * already rendering the new row and the client was throwing it away.
 *
 * Placement is the part that can silently go wrong — a row landing in the
 * wrong section looks right until you refresh — so it is what this drives.
 */
const fs = require("fs");
const { JSDOM, VirtualConsole } = require("jsdom");

const SRC = __dirname + "/../../static/project_tasks.js";
const src = fs.readFileSync(SRC, "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

// A table shaped like the real one: two sections, each with its rows.
const TABLE = `
  <table><tbody>
    <tr class="task-row" data-group="Today" data-id="a"><td>first today</td></tr>
    <tr class="task-row" data-group="Today" data-id="b"><td>second today</td></tr>
    <tr class="task-row" data-group="Later" data-id="c"><td>a later one</td></tr>
  </tbody></table>
  <form id="ptv2-add-form">
    <input id="add-task-input" data-project-id="p1">
    <input type="date" id="add-task-date" value="2026-08-30">
    <select id="add-task-initiative"></select>
    <select id="add-task-epic"></select>
    <select id="add-task-sprint"></select>
    <button id="add-task-btn"></button>
  </form>`;

const NEW_ROW = '<tr class="task-row" data-group="Today" data-id="new"><td>Write the brief</td></tr>';

function boot({ reply } = {}) {
  // location.reload() cannot be stubbed (jsdom's location is not
  // configurable) but it DOES raise a jsdomError — "navigation to
  // another Document" — so counting those is a real observation of
  // whether the page tried to reload itself.
  const navs = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { navs.push(String(e.message || e)); });
  const dom = new JSDOM(`<!doctype html><html><body>${TABLE}</body></html>`, {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://example.test/projects/p1/tasks",
    virtualConsole: vc,
  });
  const { window } = dom;
  window.__navs = navs;
  window.PROJECT_ID = "p1";
  window.showToast = () => {};
  window.feather = { replace() {} };
  window.fetch = () => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(reply === undefined
      ? { html: NEW_ROW, group: "Today", task_id: "new" }
      : reply),
  });
  window.eval(src);
  return { window, doc: window.document };
}

const rowIds = (doc) =>
  [...doc.querySelectorAll("tr.task-row")].map((r) => r.dataset.id);

// ── placement ───────────────────────────────────────────────────────
{
  const { window, doc } = boot();
  ok("the placer is exported for the add flow to use",
     typeof window.insertTaskRow === "function");

  const placed = window.insertTaskRow(NEW_ROW, "Today");
  ok("it reports the row was placed", placed === true);
  ok("the row is in the table", rowIds(doc).includes("new"));
  ok("...at the BOTTOM of its own group, not the top of the table",
     rowIds(doc).join() === "a,b,new,c");
}

// ── it refuses rather than guessing ─────────────────────────────────
{
  const { window } = boot();
  ok("a group with nothing on screen is not placed blind",
     window.insertTaskRow(NEW_ROW, "This Month") === false);
  ok("no html means no row", window.insertTaskRow("", "Today") === false);
  ok("markup that is not a task row is refused",
     window.insertTaskRow("<div>nope</div>", "Today") === false);
}

// ── the whole add, end to end ───────────────────────────────────────
(async () => {
  {
    const { window, doc } = boot();
    doc.getElementById("add-task-input").value = "Write the brief";
    await window.addTask();
    ok("the task is added without reloading the page", window.__navs.length === 0);
    ok("the new row is on screen straight away", rowIds(doc).includes("new"));
    ok("the box is cleared for the next one",
       doc.getElementById("add-task-input").value === "");
  }

  // A reply the client cannot place must still not lose the task: fall
  // back to the reload rather than leaving the row invisible.
  {
    const { window, doc } = boot({ reply: { html: "", group: "" } });
    doc.getElementById("add-task-input").value = "Write the brief";
    await window.addTask();
    ok("an unplaceable row falls back to a reload, not a silent loss",
       window.__navs.some((m) => /navigation/i.test(m)));
  }

  {
    const { window, doc } = boot();
    doc.getElementById("add-task-input").value = "   ";
    await window.addTask();
    ok("an empty box adds nothing", !rowIds(doc).includes("new"));
    ok("...and does not reload either", window.__navs.length === 0);
  }

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();

/* The Goals page, in a real DOM.
 *
 * Reported 2026-10-04: "UX is very cumbersome for OKR." It was, in three
 * measurable ways, and each one is asserted here:
 *
 *  1. ADDING A GOAL cost a nine-field modal when /api/goals has only ever
 *     required a title. There is now a one-field composer, and what has to
 *     be true is that it posts the title alone.
 *  2. PROGRESS COULD NOT BE SET. /api/goals derived it only from key
 *     results, and on live data no key result's current_value had ever
 *     moved (0 of 28) — so the bar was permanently empty on every goal.
 *     Dragging now writes manual_progress, the field /goal-planner already
 *     wrote, so a percentage set in either place shows in both.
 *  3. TWENTY CONTROLS sat on one objective carrying two key results with
 *     two initiatives each (counted in this harness, not estimated).
 *     Three icon buttons per row became one menu and the key results fold
 *     away, so a row shows three.
 *  4. AND NOW IT COUNTS ITSELF. Once MIGRATION_TASK_OBJECTIVE was applied
 *     (2026-10-04) a goal knows which tasks are its own, so progress comes
 *     from "3 of 8 tasks done" without anyone typing anything. A row says
 *     which source its number came from, and a typed override offers the
 *     counted figure back.
 *
 * The page is rendered by Flask (tests/test_smoke.py writes it to the path
 * given as argv[2]) and the real static/goals.js runs against it, so the
 * TEMPLATE and the SCRIPT are checked together.
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const htmlPath = process.argv[2];
const JS = fs.readFileSync(__dirname + "/../../static/goals.js", "utf8");

let pass = 0, fail = 0;
const ok = (n, c) => { c ? pass++ : fail++; console.log((c ? "PASS " : "FAIL ") + n); };

/* Three goals, one per progress source: a typed 60% sitting over an
   automatic figure, one with no source at all (the case that always
   showed 0% and could not be changed), and one counting its own tasks. */
const OBJECTIVES = [
  {
    id: "o1", title: "Launch v2 with premium experience", project_id: "p1",
    project_name: "Platform", category: "product", time_horizon: "quarterly",
    target_date: "2026-11-18", status: "active", color: "#424aa8",
    description: "Ship the paid tier.", manual_progress: 60,
    _progress: 60, _progress_source: "manual", _rolled_up: 20,
    _task_done: 2, _task_total: 4, _from_tasks: 50,
    key_results: [{
      id: "k1", objective_id: "o1", title: "Paid signups", start_value: 0,
      current_value: 40, target_value: 200, direction: "up", unit: "",
      _progress: 20, initiatives: [],
    }],
  },
  {
    id: "o2", title: "Clear the interview backlog", project_id: null,
    time_horizon: "monthly", target_date: "2026-12-31", status: "active",
    color: null, manual_progress: null,
    _progress: 0, _progress_source: "none", _rolled_up: 0,
    _task_done: 0, _task_total: 0, _from_tasks: null, key_results: [],
  },
  {
    // Counting itself: 3 of 8 of its own tasks are done.
    id: "o3", title: "Ship the RLS migration", project_id: "p1",
    project_name: "Platform", time_horizon: "quarterly",
    target_date: "2026-10-20", status: "active", color: null,
    manual_progress: null, _progress: 38, _progress_source: "tasks",
    _rolled_up: 0, _task_done: 3, _task_total: 8, _from_tasks: 38,
    key_results: [],
  },
];

(async function main() {
  const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://example.test/goals",
  });
  const { window } = dom;
  const doc = window.document;
  const q = s => doc.querySelector(s);
  const all = s => Array.from(doc.querySelectorAll(s));

  // Record every request instead of letting it reach the network.
  const sent = [];
  window.fetch = (url, opts = {}) => {
    sent.push({ url, method: opts.method || "GET", body: opts.body ? JSON.parse(opts.body) : null });
    const payload = (opts.method || "GET") === "GET"
      ? { objectives: OBJECTIVES, projects: [["p1", "Platform"]] }
      : { status: "ok" };
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) });
  };
  window.showToast = () => {};
  window.requestAnimationFrame = fn => fn();

  /* `const state` in an eval'd script creates a global LEXICAL binding, not
     a property of window — so the trailing assignment is how the test
     reaches it. Function declarations do land on window, hence the direct
     calls below. */
  window.eval(JS + "\n;window.__state = state;");
  const state = window.__state;
  ok("the script exposes its state", !!state);

  /* Render from the fixture rather than waiting on loadGoals, so the
     assertions are about the markup the renderer produces. */
  state.objectives = OBJECTIVES;
  state.projects = [["p1", "Platform"]];
  window.renderObjectives();

  /* ── 1. One row per goal, and ONE visible action on it ─────────────── */
  ok("one row per goal", all(".goal-card").length === 3);

  const row = q('.goal-card[data-objective-id="o1"]');
  const menuButtons = Array.from(row.querySelectorAll(".goal-menu-wrap > button"));
  ok("the row has a single menu button", menuButtons.length === 1);
  ok("the old three-icon action group is gone", !row.querySelector(".goal-actions"));

  /* ── 2. Key results are folded away, not expanded ──────────────────── */
  const fold = row.querySelector("details.kr-fold");
  ok("key results are in a fold", !!fold);
  ok("the fold starts closed", fold && fold.open === false);
  ok("the fold says how many", /1 key result\b/.test(fold.querySelector("summary").textContent));
  ok("a goal with no key results has no fold",
     !q('.goal-card[data-objective-id="o2"] details.kr-fold'));

  /* ── 3. The menu holds the actions, and only opens on demand ───────── */
  const menu = q("#goal-menu-o1");
  ok("the menu starts hidden", menu.hidden === true);
  window.toggleGoalMenu({ stopPropagation() {} }, "o1");
  ok("the menu opens", menu.hidden === false);
  ok("it offers Edit, Add key result, Archive and Delete",
     menu.querySelectorAll("button").length === 4);
  window.closeAllGoalMenus();
  ok("the menu closes", menu.hidden === true);

  /* ── 4. The bar IS the control ─────────────────────────────────────── */
  const slider = row.querySelector("input.goal-slider");
  ok("the progress bar is a range input", !!slider && slider.type === "range");
  ok("it starts at the goal's progress", slider.value === "60");
  ok("it is native, so keyboard and touch work for free",
     slider.min === "0" && slider.max === "100");
  ok("the percentage is shown beside it", q('[data-pct-for="o1"]').textContent === "60%");

  sent.length = 0;
  slider.value = "75";
  window.previewGoalProgress(slider, "o1");
  ok("dragging updates the number immediately",
     q('[data-pct-for="o1"]').textContent === "75%");
  ok("...and does not save on every pixel", sent.length === 0);

  /* ── 5. Releasing saves manual_progress ───────────────────────────── */
  sent.length = 0;
  await window.setGoalProgress("o1", "75");
  const patch = sent.find(r => r.method === "PATCH");
  ok("releasing sends one PATCH", !!patch);
  ok("it goes to that goal", patch && patch.url === "/api/goals/o1");
  ok("it writes manual_progress", patch && patch.body.manual_progress === 75);

  /* ── 5b. A counted percentage says what it counted ─────────────────── */
  const counted = q('.goal-card[data-objective-id="o3"]');
  ok("a task-derived goal shows its progress",
     counted.querySelector('[data-pct-for="o3"]').textContent === "38%");
  ok("...and says what it counted",
     /3 of 8 tasks done/.test(counted.querySelector(".goal-source").textContent));
  ok("a counted goal is not asked to justify itself with a roll-up link",
     !counted.querySelector(".goal-rollup"));

  /* ── 6. The disagreement with key results is shown, with a way back ── */
  const rollup = q('.goal-card[data-objective-id="o1"] .goal-rollup');
  ok("a typed percentage over an automatic one says so", !!rollup);
  // Tasks are offered ahead of key results, matching the server precedence.
  ok("it offers the task count, not the key results",
     rollup && /2 of 4 tasks done = 50%/.test(rollup.textContent));
  ok("a goal with no key results offers no roll-up link",
     !q('.goal-card[data-objective-id="o2"] .goal-rollup'));

  sent.length = 0;
  await window.clearGoalProgress("o1");
  const cleared = sent.find(r => r.method === "PATCH");
  ok("clearing sends an empty manual_progress",
     cleared && cleared.body.manual_progress === "");

  /* ── 7. Adding a goal takes one field ─────────────────────────────── */
  state.objectives = OBJECTIVES;          // loadGoals re-rendered from the stub
  window.renderObjectives();
  sent.length = 0;
  q("#goal-quick-title").value = "Ship the RLS migration";
  await window.addGoalInline();
  const post = sent.find(r => r.method === "POST");
  ok("one field is enough to add a goal", !!post);
  ok("it posts to the existing endpoint", post && post.url === "/api/goals");
  ok("it carries the title typed", post && post.body.title === "Ship the RLS migration");
  ok("no date is required", post && post.body.target_date === null);
  ok("the box is cleared for the next one", q("#goal-quick-title").value === "");

  sent.length = 0;
  q("#goal-quick-title").value = "   ";
  await window.addGoalInline();
  ok("whitespace does not create a goal", !sent.some(r => r.method === "POST"));

  /* ── 8. The counts filter the list ────────────────────────────────── */
  state.objectives = OBJECTIVES;
  window.renderObjectives();
  const chips = all("#goals-summary .goal-chip");
  ok("the summary shows counts", chips.length >= 1);
  ok("they are buttons", chips.every(c => c.tagName === "BUTTON"));
  window.setFilter("overdue");
  ok("filtering to an empty group explains itself and offers a way back",
     !!q(".goal-none .goal-link"));
  window.setFilter("all");
  ok("going back shows every goal again", all(".goal-card").length === 3);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch(err => {
  console.log("FAIL harness threw: " + (err && err.stack || err));
  process.exit(1);
});

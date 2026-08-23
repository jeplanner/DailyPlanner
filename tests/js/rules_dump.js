/* Dump the CLIENT's recurrence decisions as JSON, so the Python side can be
 * compared against them case for case.
 *
 * The rules exist in two languages. This is what stops that being a latent
 * bug: any disagreement fails a test rather than being discovered by
 * someone whose 7am reminder spoke but never buzzed.
 */
const fs = require("fs");
const store = {};
global.localStorage = { getItem: k => k in store ? store[k] : null,
                        setItem: (k, v) => { store[k] = String(v); },
                        removeItem: k => { delete store[k]; } };
const noop = () => {};
const el = () => ({ style: {}, classList: { toggle: noop, add: noop, remove: noop,
  contains: () => false }, querySelector: () => null, querySelectorAll: () => [],
  addEventListener: noop, appendChild: noop, setAttribute: noop,
  getAttribute: () => null, remove: noop, matches: () => false, hidden: false,
  getBoundingClientRect: () => ({ top:0, left:0, bottom:0, right:0, width:0, height:0 }) });
global.document = { readyState: "complete", documentElement: { lang: "en-US" },
  head: el(), body: el(), getElementById: () => null, createElement: el,
  querySelector: () => null, querySelectorAll: () => [], addEventListener: noop,
  activeElement: null };
global.navigator = { language: "en-US" };
global.window = { addEventListener: noop, matchMedia: () => ({ matches: false }),
  document: global.document, localStorage: global.localStorage,
  navigator: global.navigator };
global.setInterval = () => 0; global.clearInterval = noop; global.setTimeout = noop;

new Function("window","document","navigator","localStorage","setInterval",
             "clearInterval","setTimeout",
  fs.readFileSync(__dirname + "/../../static/js/time-announcer.js", "utf8")
)(global.window, global.document, global.navigator, global.localStorage,
  global.setInterval, global.clearInterval, global.setTimeout);

const TA = global.window.TimeAnnouncer;
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map(c => ({
  matches: c.dates.map(d => TA._matchesOn(c.item, d)),
  slots: TA._slotsFor(c.item),
}));
process.stdout.write(JSON.stringify(out));

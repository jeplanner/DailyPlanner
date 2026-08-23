/* Behavioural tests for the time announcer's SCHEDULING.
 *
 * The repo has no JS test runner, so its JS guards have historically been
 * pytest reading the source for a string. That is not proof: the announcer
 * shipped with a `speechSynthesis.cancel()` immediately followed by
 * `speak()` — a known Chrome bug that swallows the utterance — and every
 * source assertion passed the whole time it was mute.
 *
 * So this RUNS the module, against stub DOM and storage. Node is present;
 * tests/test_smoke.py shells out to it and skips if it ever is not.
 */
const fs=require('fs');
// Minimal DOM + speech stubs: we are testing the SCHEDULING logic, which is
// where the reported bug lives, not the rendering.
const store={};
global.localStorage={getItem:k=>k in store?store[k]:null,setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}};
const noop=()=>{};
const el=()=>({style:{},classList:{toggle:noop,add:noop,remove:noop,contains:()=>false},
  querySelector:()=>null,querySelectorAll:()=>[],addEventListener:noop,appendChild:noop,
  setAttribute:noop,getAttribute:()=>null,remove:noop,matches:()=>false,hidden:false,
  getBoundingClientRect:()=>({top:0,left:0,bottom:0,right:0,width:0,height:0})});
global.document={readyState:"complete",documentElement:{lang:"en-US"},head:el(),body:el(),
  getElementById:()=>null,createElement:el,querySelector:()=>null,querySelectorAll:()=>[],
  addEventListener:noop,activeElement:null};
global.navigator={language:"en-US"};
global.window={addEventListener:noop,matchMedia:()=>({matches:false}),document:global.document,
  localStorage:global.localStorage,navigator:global.navigator};
global.setInterval=()=>0; global.clearInterval=noop; global.setTimeout=noop;
new Function('window','document','navigator','localStorage','setInterval','clearInterval','setTimeout',
  fs.readFileSync(__dirname + '/../../static/js/time-announcer.js', 'utf8')
)(global.window,global.document,global.navigator,global.localStorage,global.setInterval,global.clearInterval,global.setTimeout);
const TA=global.window.TimeAnnouncer;
let pass=0,fail=0;
const ok=(n,c)=>{ (c?pass++:fail++); console.log((c?"PASS ":"FAIL ")+n); };
const at=(h,m,s=0)=>new Date(2026,7,22,h,m,s);

// parseTimes
ok("parses forgiving list", JSON.stringify(TA._parseTimes("9, 13:30 18:45"))==='["09:00","13:30","18:45"]');
// "5.00" is how most of the world writes five o'clock. Splitting on any
// non-digit read it as TWO times — 05:00 and 00:00 — and announced midnight.
ok("5.00 is five o'clock, not 5:00 + 0:00", JSON.stringify(TA._parseTimes("5.00"))==='["05:00"]');
ok("5.30 keeps its minutes",   JSON.stringify(TA._parseTimes("5.30"))==='["05:30"]');
ok("dotted list",              JSON.stringify(TA._parseTimes("5.00, 9.30, 18.45"))==='["05:00","09:30","18:45"]');
ok("pm shifts by 12",          JSON.stringify(TA._parseTimes("5pm"))==='["17:00"]');
ok("am leaves alone",          JSON.stringify(TA._parseTimes("5am"))==='["05:00"]');
ok("12am is midnight",         JSON.stringify(TA._parseTimes("12am"))==='["00:00"]');
ok("12pm is noon",             JSON.stringify(TA._parseTimes("12pm"))==='["12:00"]');
ok("6.45pm",                   JSON.stringify(TA._parseTimes("6.45pm"))==='["18:45"]');
ok("mixed notations together", JSON.stringify(TA._parseTimes("5.00, 9am, 13:30, 6.45pm"))==='["05:00","09:00","13:30","18:45"]');
ok("many times allowed",       TA._parseTimes("1,2,3,4,5,6,7,8").length===8);
ok("24h still works",          JSON.stringify(TA._parseTimes("17:00"))==='["17:00"]');
ok("friendly reads back 12h",  TA._friendly("17:30")==="5:30 PM" && TA._friendly("05:00")==="5:00 AM");
ok("friendly noon/midnight",   TA._friendly("12:00")==="12:00 PM" && TA._friendly("00:00")==="12:00 AM");
ok("drops nonsense",        JSON.stringify(TA._parseTimes("25:00, abc, 9:70"))==='[]');
ok("dedupes + sorts",       JSON.stringify(TA._parseTimes("18:00, 9:00, 18:00"))==='["09:00","18:00"]');

// EVERY 15/30/45/60 — the intervals reported as not working.
for (const every of [15,30,45,60]) {
  TA._set({mode:"on", every, at:[], label:""});
  // DISTINCT SLOTS, not minutes: the 90s grace window makes a boundary live
  // at both :00 and :01, and check() dedupes those through lastSlot.
  const slots=new Set(); const dedup=[];
  for (let h=0;h<24;h++) for (let m=0;m<60;m++) {
    const b=TA._dueSlot(at(h,m,0));
    if (b!==null && !slots.has(b)) { slots.add(b); dedup.push(b); }
  }
  const want = Math.ceil(1440/every);
  ok(`every ${every}m fires ${want}x/day (got ${slots.size})`, slots.size===want);
  ok(`every ${every}m steps 0,${every},${2*every}`,
     dedup[0]===0 && dedup[1]===every && dedup[2]===2*every);
  ok(`every ${every}m never repeats a slot`, dedup.length===slots.size);
}
// Grace window
TA._set({mode:"on",every:15,at:[]});
ok("60s late still counts",  TA._dueSlot(at(14,16,0))!==null);
ok("2m late is skipped",     TA._dueSlot(at(14,17,0))===null);
ok("mid-interval is silent", TA._dueSlot(at(14,7,0))===null);
// ── NAMED ANNOUNCEMENTS (2026-08-23) ────────────────────────────────
// Exact times moved out of the interval logic into their own list, where
// each carries its own text, an optional date, and its own on/off switch.
const TODAY = TA._todayYMD(at(12,0,0));
// The harness clock is 2026-08-22, so these must straddle THAT date.
const YESTERDAY = "2026-08-21", TOMORROW = "2026-08-23";
// The stored shape. `_set` writes straight to state, bypassing load()'s
// migration, so these must already be in the CURRENT shape.
const item = (o) => Object.assign(
  {id:"x", at:"09:00", repeat:"daily", days:[], start:"2026-08-01",
   end:null, text:"", on:true}, o);

TA._set({mode:"on", every:0, at:[], items:[], said:{}});
ok("every=0 => interval silent", TA._dueSlot(at(14,0,0))===null);

TA._set({items:[item({id:"a", at:"13:30", text:"Lunch"})], said:{}});
ok("undated item fires today",   TA._dueItems(at(13,30,0)).length===1);
ok("...and says its own text",   TA._dueItems(at(13,30,0))[0].text==="Lunch");
ok("not at another time",        TA._dueItems(at(11,0,0)).length===0);

TA._set({items:[item({id:"b", repeat:"once", start:TODAY})], said:{}});
ok("one-off fires on its day",   TA._dueItems(at(9,0,0)).length===1);
TA._set({items:[item({id:"c", repeat:"once", start:TOMORROW})], said:{}});
ok("not before its day",         TA._dueItems(at(9,0,0)).length===0);
TA._set({items:[item({id:"d", repeat:"once", start:YESTERDAY})], said:{}});
ok("never after its day",        TA._dueItems(at(9,0,0)).length===0);

TA._set({items:[item({id:"e", at:"09:00", on:false})], said:{}});
ok("stopped item stays silent",   TA._dueItems(at(9,0,0)).length===0);

// Several on the same minute must ALL be returned — they are combined into
// one utterance rather than talking over each other.
TA._set({items:[item({id:"f", at:"09:00", text:"One"}),
                item({id:"g", at:"09:00", text:"Two"})], said:{}});
ok("two at once both fire",       TA._dueItems(at(9,0,0)).length===2);

// Already said today is not repeated, and the grace window still applies.
TA._set({items:[item({id:"h", at:"09:00"})], said:{h: TODAY+"|09:00"}});
ok("not repeated once said",      TA._dueItems(at(9,0,0)).length===0);
TA._set({items:[item({id:"i", at:"09:00"})], said:{}});
ok("60s late still fires",        TA._dueItems(at(9,1,0)).length===1);
ok("2m late is skipped",          TA._dueItems(at(9,2,0)).length===0);
ok("never fires early",           TA._dueItems(at(8,59,0)).length===0);

// The interval is independent of the items and still works alongside them.
TA._set({mode:"on", every:60, items:[item({id:"j", at:"09:00"})], said:{}});
ok("interval unaffected by items", TA._dueSlot(at(9,0,0))===540);
TA._set({mode:"on", every:15, items:[], said:{}, at:[], label:""});
// Heading
TA._set({label:"", every:15, at:[]});
ok("no heading",  TA._phrase(at(15,0))==="It's 3 o'clock P M");
TA._set({label:"Stand up and stretch."});
ok("heading read first", TA._phrase(at(15,0))==="Stand up and stretch. It's 3 o'clock P M");
TA._set({label:""});
ok("15:30 phrasing", TA._phrase(at(15,30))==="It's 3:30 P M");
// ── RECURRENCE (2026-08-23) ─────────────────────────────────────────
// Each announcement repeats on a rule inside an optional start/end window.
const R = (o) => Object.assign(
  {id:"r", at:"09:00", repeat:"daily", days:[], start:"2026-08-23",
   end:null, text:"", on:true}, o);
const M = (o, d) => TA._matchesOn(R(o), d);

// once
ok("once fires on its day",      M({repeat:"once", start:"2026-08-25"}, "2026-08-25"));
ok("once not the day before",    !M({repeat:"once", start:"2026-08-25"}, "2026-08-24"));
ok("once not the day after",     !M({repeat:"once", start:"2026-08-25"}, "2026-08-26"));

// daily
ok("daily fires every day",      M({repeat:"daily"}, "2026-09-14"));
ok("daily respects start",       !M({repeat:"daily", start:"2026-09-01"}, "2026-08-31"));
ok("daily respects end",         !M({repeat:"daily", end:"2026-08-31"}, "2026-09-01"));
ok("daily fires on the end day", M({repeat:"daily", end:"2026-08-31"}, "2026-08-31"));

// weekly — 2026-08-23 is a Sunday
ok("weekly same weekday",        M({repeat:"weekly", start:"2026-08-23"}, "2026-08-30"));
ok("weekly not other weekdays",  !M({repeat:"weekly", start:"2026-08-23"}, "2026-08-31"));

// monthly, including the short-month clamp
ok("monthly same day of month",  M({repeat:"monthly", start:"2026-01-15"}, "2026-06-15"));
ok("monthly not other days",     !M({repeat:"monthly", start:"2026-01-15"}, "2026-06-16"));
ok("31st CLAMPS to 28 Feb",      M({repeat:"monthly", start:"2026-01-31"}, "2026-02-28"));
ok("...and not 27 Feb",          !M({repeat:"monthly", start:"2026-01-31"}, "2026-02-27"));
ok("31st still fires on 31 Mar", M({repeat:"monthly", start:"2026-01-31"}, "2026-03-31"));
ok("30th clamps in Feb too",     M({repeat:"monthly", start:"2026-01-30"}, "2026-02-28"));

// yearly, including the leap-day clamp
ok("yearly same date",           M({repeat:"yearly", start:"2026-03-05"}, "2027-03-05"));
ok("yearly not other dates",     !M({repeat:"yearly", start:"2026-03-05"}, "2027-03-06"));
ok("29 Feb clamps in 2027",      M({repeat:"yearly", start:"2024-02-29"}, "2027-02-28"));
ok("29 Feb exact in 2028",       M({repeat:"yearly", start:"2024-02-29"}, "2028-02-29"));

// custom days — 2026-08-24 is a Monday, 26th a Wednesday
ok("custom fires on a chosen day",  M({repeat:"custom", days:[1,3]}, "2026-08-24"));
ok("custom fires on the other one", M({repeat:"custom", days:[1,3]}, "2026-08-26"));
ok("custom silent otherwise",       !M({repeat:"custom", days:[1,3]}, "2026-08-25"));
ok("custom with no days never fires", !M({repeat:"custom", days:[]}, "2026-08-24"));

// the window bounds every rule, not just daily
ok("weekly stops at its end",    !M({repeat:"weekly", start:"2026-08-23", end:"2026-08-29"}, "2026-08-30"));
ok("monthly waits for its start", !M({repeat:"monthly", start:"2026-09-15"}, "2026-08-15"));

// expiry
ok("past one-off is expired",    TA._isExpired(R({repeat:"once", start:"2026-08-01"}), "2026-08-23"));
ok("today's one-off is not",     !TA._isExpired(R({repeat:"once", start:"2026-08-23"}), "2026-08-23"));
ok("ended repeat is expired",    TA._isExpired(R({repeat:"daily", end:"2026-08-22"}), "2026-08-23"));
ok("open-ended never expires",   !TA._isExpired(R({repeat:"daily"}), "2030-01-01"));

// words
ok("words: daily",   TA._repeatWords(R({repeat:"daily"}))==="every day");
ok("words: weekly",  TA._repeatWords(R({repeat:"weekly", start:"2026-08-23"}))==="every Sun");
ok("words: monthly", TA._repeatWords(R({repeat:"monthly", start:"2026-01-31"}))==="monthly on the 31st");
ok("words: custom",  TA._repeatWords(R({repeat:"custom", days:[1,3]}))==="Mon Wed");
ok("words: until",   /until 31 Aug 2026/.test(TA._repeatWords(R({repeat:"daily", end:"2026-08-31"}))));

// dueItems must obey the rule, not just the clock
TA._set({mode:"on", every:0, items:[R({id:"z", at:"09:00", repeat:"custom", days:[1]})], said:{}});
ok("dueItems skips a non-matching day", TA._dueItems(at(9,0,0)).length===0);  // 22nd is a Saturday
TA._set({items:[R({id:"z2", at:"09:00", repeat:"weekly", start:"2026-08-22"})], said:{}});
ok("dueItems fires on the anchor day",  TA._dueItems(at(9,0,0)).length===1);

// ── THE AM/PM CHOOSER (2026-08-23) ──────────────────────────────────
// "i will manually enter time but provide facility to choose am or pm."
// The chooser supplies the meridiem ONLY when the typed text does not.
const P = (txt, mer) => JSON.stringify(TA._parseTimes(txt, mer));

ok("bare 5 + PM  => 17:00", P("5", "pm")==='["17:00"]');
ok("bare 5 + AM  => 05:00", P("5", "am")==='["05:00"]');
ok("5.30 + PM    => 17:30", P("5.30", "pm")==='["17:30"]');
ok("5:30 + PM    => 17:30", P("5:30", "pm")==='["17:30"]');
ok("12 + PM is noon",       P("12", "pm")==='["12:00"]');
ok("12 + AM is midnight",   P("12", "am")==='["00:00"]');

// Typing beats clicking.
ok("5pm + AM stays 17:00",  P("5pm", "am")==='["17:00"]');
ok("5am + PM stays 05:00",  P("5am", "pm")==='["05:00"]');
ok("17:00 + AM stays 17:00",P("17:00", "am")==='["17:00"]');
ok("0:30 + PM stays 00:30", P("0:30", "pm")==='["00:30"]');
ok("23:15 + AM unchanged",  P("23:15", "am")==='["23:15"]');

// No chooser at all behaves exactly as before, so nothing else changed.
ok("no chooser => as typed", P("5")==='["05:00"]');
ok("no chooser, pm typed",   P("5pm")==='["17:00"]');

// A list still works, with the chooser applied to each ambiguous entry.
ok("list + PM", P("5, 6, 7", "pm")==='["17:00","18:00","19:00"]');
ok("list, mixed explicit + PM", P("5, 9am, 23:00", "pm")==='["09:00","17:00","23:00"]');

// merApplies drives the dimming, so it must agree with the parser.
ok("chooser applies to a bare hour",  TA._merApplies("5")===true);
ok("...and to 5.30",                  TA._merApplies("5.30")===true);
ok("...not when am/pm is typed",      TA._merApplies("5pm")===false);
ok("...not for 24-hour hours",        TA._merApplies("17:00")===false);
ok("...not for hour zero",            TA._merApplies("0:30")===false);
ok("...applies to an empty field",    TA._merApplies("")===true);

// ── THE DAILY WINDOW (2026-08-23) ───────────────────────────────────
// "start at and ends at timing" meant a TIME window: one announcement that
// speaks repeatedly through the day between two times.
const W = (o) => Object.assign(
  {id:"w", at:"08:00", until:null, mins:0, repeat:"daily", days:[],
   start:"2026-08-01", end:null, text:"", on:true}, o);
const slots = (o) => TA._slotsFor(W(o));

ok("no window => one slot",       JSON.stringify(slots({}))==="[480]");
ok("window without an interval => one slot",
   JSON.stringify(slots({until:"20:00"}))==="[480]");
ok("interval without a window => one slot",
   JSON.stringify(slots({mins:60}))==="[480]");

const s8to12 = slots({until:"12:00", mins:60});
ok("8am-12pm every 60m is 5 slots", s8to12.length===5);
ok("...starting at 08:00",          s8to12[0]===480);
ok("...ending at 12:00",            s8to12[4]===720);
ok("...and stepping by an hour",    s8to12[1]-s8to12[0]===60);

ok("a 90m step lands correctly",
   JSON.stringify(slots({until:"12:00", mins:90}))==="[480,570,660]");
ok("the end is included when it lands exactly",
   slots({until:"12:00", mins:120}).indexOf(720)!==-1);
ok("the end is not overshot",
   slots({until:"12:00", mins:100}).every(m => m<=720));
ok("until BEFORE at is ignored rather than looping",
   JSON.stringify(slots({until:"06:00", mins:30}))==="[480]");
ok("a 1-minute step is capped, not infinite",
   slots({at:"00:00", until:"23:59", mins:1}).length<=1441);

// Each slot settles on its own, so the whole window is not silenced by one.
TA._set({mode:"on", every:0, said:{},
         items:[W({id:"win", at:"09:00", until:"11:00", mins:60})]});
ok("window fires at its start",  TA._dueItems(at(9,0,0)).length===1);
ok("...and at the middle slot",  TA._dueItems(at(10,0,0)).length===1);
ok("...and at the last slot",    TA._dueItems(at(11,0,0)).length===1);
ok("...but not between slots",   TA._dueItems(at(9,30,0)).length===0);
ok("...and not after the end",   TA._dueItems(at(12,0,0)).length===0);
ok("the slot key names the SLOT, not the start",
   TA._dueItems(at(10,0,0))[0].key.slice(-5)==="10:00");
TA._set({said:{win:"2026-08-22|10:00"}});
ok("a said slot is skipped",     TA._dueItems(at(10,0,0)).length===0);
ok("...without silencing the others", TA._dueItems(at(11,0,0)).length===1);

// The recurrence still gates the whole window.
TA._set({said:{}, items:[W({id:"w2", at:"09:00", until:"11:00", mins:60,
                            repeat:"custom", days:[1]})]});
ok("a window on a non-matching day is silent", TA._dueItems(at(10,0,0)).length===0);

ok("words: plain time",  TA._timeWords(W({}))==="8:00 AM");
ok("words: window",      TA._timeWords(W({until:"20:00", mins:60}))
                          ==="8:00 AM\u20138:00 PM \u00b7 60m");

// ── MIGRATION from the shapes already in people's browsers ──────────
// _set bypasses load(), so the migration needs its own exercise. Anyone
// upgrading has data in one of the two older shapes and must lose nothing.
const KEY = "dp-time-announcer";
store[KEY] = JSON.stringify({
  mode:"on", every:30, at:["05:00","18:45"], label:"Stand up", keepalive:true});
let mig = TA._load();
ok("v1: each time becomes an announcement", mig.items.length===2);
ok("v1: they repeat daily",  mig.items.every(i => i.repeat==="daily"));
ok("v1: the shared label is kept", mig.items.every(i => i.text==="Stand up"));
ok("v1: interval survives", mig.every===30);
ok("v1: keepalive survives", mig.keepalive===true);
ok("v1: the old list is cleared", mig.at.length===0);
ok("v1: no window by default",   mig.items.every(i => i.until===null && i.mins===0));

store[KEY] = JSON.stringify({mode:"on", items:[
  {id:"a", at:"09:00", date:null, text:"Daily one", on:true},
  {id:"b", at:"10:00", date:"2026-12-25", text:"Christmas", on:false}]});
mig = TA._load();
ok("v2: undated becomes daily", mig.items[0].repeat==="daily");
ok("v2: dated becomes a one-off", mig.items[1].repeat==="once");
ok("v2: the date becomes the start", mig.items[1].start==="2026-12-25");
ok("v2: off stays off", mig.items[1].on===false);
ok("v2: text preserved", mig.items[1].text==="Christmas");
delete store[KEY];

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);

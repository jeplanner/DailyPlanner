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
const item = (o) => Object.assign(
  {id:"x", at:"09:00", date:null, text:"", on:true}, o);

TA._set({mode:"on", every:0, at:[], items:[], said:{}});
ok("every=0 => interval silent", TA._dueSlot(at(14,0,0))===null);

TA._set({items:[item({id:"a", at:"13:30", text:"Lunch"})], said:{}});
ok("undated item fires today",   TA._dueItems(at(13,30,0)).length===1);
ok("...and says its own text",   TA._dueItems(at(13,30,0))[0].text==="Lunch");
ok("not at another time",        TA._dueItems(at(11,0,0)).length===0);

TA._set({items:[item({id:"b", at:"09:00", date:TODAY})], said:{}});
ok("dated item fires on its day", TA._dueItems(at(9,0,0)).length===1);
TA._set({items:[item({id:"c", at:"09:00", date:TOMORROW})], said:{}});
ok("not before its day",          TA._dueItems(at(9,0,0)).length===0);
TA._set({items:[item({id:"d", at:"09:00", date:YESTERDAY})], said:{}});
ok("never after its day",         TA._dueItems(at(9,0,0)).length===0);

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
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);

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
// Exact times
TA._set({mode:"on",every:0,at:["09:00","13:30"],label:""});
ok("every=0 => interval off", TA._dueSlot(at(14,0,0))===null);
ok("exact time fires",        TA._dueSlot(at(13,30,0))===13*60+30);
ok("exact-only ignores :00",  TA._dueSlot(at(11,0,0))===null);
TA._set({mode:"on",every:60,at:["09:00"]});
ok("exact wins over interval",TA._dueSlot(at(9,0,0))===540);
// Heading
TA._set({label:"", every:15, at:[]});
ok("no heading",  TA._phrase(at(15,0))==="It's 3 o'clock P M");
TA._set({label:"Stand up and stretch."});
ok("heading read first", TA._phrase(at(15,0))==="Stand up and stretch. It's 3 o'clock P M");
TA._set({label:""});
ok("15:30 phrasing", TA._phrase(at(15,30))==="It's 3:30 P M");
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);

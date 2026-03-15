/* =========================================================
   GLOBAL STATE
========================================================= */

const USE_TIMELINE_VIEW = false;

const summaryModal = document.getElementById("summary-modal");
const summaryContent = document.getElementById("summary-content");

let PLAN_DATE =
  document.body.dataset.planDate ||
  new Date().toISOString().slice(0, 10);

/* =========================================================
   CLOCK (IST)
========================================================= */

function updateClock() {
  const el = document.getElementById("clock");
  if (!el) return;

  const ist = new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
  );

  el.textContent = ist.toLocaleTimeString();
}

setInterval(updateClock, 1000);
updateClock();

/* =========================================================
   CLEAN DRAG + RESIZE SYSTEM
========================================================= */

function initDragResize() {

  const slotHeight = parseFloat(
    getComputedStyle(document.documentElement)
      .getPropertyValue("--slot-height")
  );

  document.querySelectorAll(".event-block").forEach(block => {

    const resizeHandle = block.querySelector(".resize-handle");

    /* ---------- DRAG ---------- */

    block.addEventListener("pointerdown", e => {
      
      if (e.target === resizeHandle) return;

      block.setPointerCapture(e.pointerId);
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", up);

      const startY = e.clientY;
      const startTop = block.offsetTop;

      const startSlot = Number(block.dataset.start);
      const endSlot = Number(block.dataset.end);

      const duration = endSlot - startSlot;
      let isLongPress = false;

      let longPressTimer = setTimeout(() => {

      isLongPress = true;

      // stop drag listeners
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);

      block.releasePointerCapture(e.pointerId);

      editEvent(startSlot, endSlot);

    }, 500);

     function move(ev) {

        if (isLongPress) return;

        const delta = ev.clientY - startY;

        if (Math.abs(delta) > 5) {
          clearTimeout(longPressTimer);
        }

        let newTop = startTop + delta;

        if (newTop < 0) newTop = 0;

        const snappedSlot = Math.floor(newTop / slotHeight) + 1;

        block.style.top = `${(snappedSlot - 1) * slotHeight}px`;

      }
    function up(ev) {

      clearTimeout(longPressTimer);

      if (isLongPress) return;

      block.releasePointerCapture(ev.pointerId);

      const newStart =
        Math.floor(block.offsetTop / slotHeight) + 1;

      const newEnd = newStart + duration;

      saveEvent(startSlot, endSlot, newStart, newEnd, block);

      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);

    }
});  // ← CLOSE pointerdown
    /* ---------- RESIZE ---------- */

    if (resizeHandle) {

      resizeHandle.addEventListener("pointerdown", e => {

        e.stopPropagation();

        block.setPointerCapture(e.pointerId);

        const startY = e.clientY;

        const startSlot = Number(block.dataset.start);
        const endSlot = Number(block.dataset.end);

        function move(ev) {

          const delta = ev.clientY - startY;

          const slotsMoved = Math.floor(delta / slotHeight);

          let newEnd = endSlot + slotsMoved;

          if (newEnd < startSlot)
            newEnd = startSlot ;

          const newHeight =
            (newEnd - startSlot + 1) * slotHeight;

          block.style.height = `${newHeight}px`;

        }

        function up(ev) {

          block.releasePointerCapture(ev.pointerId);

          const height = block.offsetHeight;

          const slots = Math.floor(height / slotHeight);

          const newEnd = startSlot + slots - 1;

          saveEvent(startSlot, endSlot, startSlot, newEnd,block);

          document.removeEventListener("pointermove", move);
          document.removeEventListener("pointerup", up);

        }

        document.addEventListener("pointermove", move);
        document.addEventListener("pointerup", up);

      });

    }

  });

}

/* =========================================================
   SLOT DRAG CREATE
========================================================= */

let dragStartSlot = null;
let dragEndSlot = null;
let isDragging = false;

function initSlotDrag() {

  document.querySelectorAll(".time-row").forEach(row => {

    row.addEventListener("mousedown", () => {

      dragStartSlot = Number(row.dataset.slot);
      dragEndSlot = dragStartSlot;
      isDragging = true;

      highlightSlots();

    });

    row.addEventListener("mouseenter", () => {

      if (!isDragging) return;

      dragEndSlot = Number(row.dataset.slot);

      highlightSlots();

    });

    row.addEventListener("click", () => {

      if (isDragging) return;

      const slot = Number(row.dataset.slot);

      openCreateEvent(slot, slot);

    });

  });

}

document.addEventListener("mouseup", () => {

  if (!isDragging) return;

  isDragging = false;

  const start = Math.min(dragStartSlot, dragEndSlot);
  const end = Math.max(dragStartSlot, dragEndSlot);

  clearSlotHighlight();

  openCreateEvent(start, end);

});

function highlightSlots() {

  clearSlotHighlight();

  const start = Math.min(dragStartSlot, dragEndSlot);
  const end = Math.max(dragStartSlot, dragEndSlot);

  document.querySelectorAll(".time-row").forEach(row => {

    const slot = Number(row.dataset.slot);

    if (slot >= start && slot <= end)
      row.classList.add("slot-preview");

  });

}

function clearSlotHighlight() {

  document
    .querySelectorAll(".slot-preview")
    .forEach(el => el.classList.remove("slot-preview"));

}

/* =========================================================
   EVENT CREATION
========================================================= */

function openCreateEvent(startSlot, endSlot) {

  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  content.innerHTML = `
    <h3>Create Event</h3>

    <textarea id="editText"
      placeholder="Event description"
      style="width:100%;min-height:120px"></textarea>

    <br><br>

    <button onclick="closeModal()">Cancel</button>
    <button onclick="saveEvent(${startSlot}, ${endSlot}, ${startSlot}, ${endSlot})">
      Save
    </button>
  `;

  modal.style.display = "flex";

}

/* =========================================================
   EDIT EVENT
========================================================= */
function editEvent(startSlot, endSlot) {

  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  fetch(`/slot/get?date=${PLAN_DATE}&slot=${startSlot}`)
    .then(r => r.json())
    .then(data => {

      content.innerHTML = `
        <h3>Edit Event</h3>

        <label>Event</label>
        <textarea id="editText" style="width:100%;min-height:80px;">${data.text || ""}</textarea>

        <br><br>

        <label>Start</label>
        <input type="time" id="editStart" value="${data.start_time || ""}">

        <label>End</label>
        <input type="time" id="editEnd" value="${data.end_time || ""}">

        <br><br>

        <label>Priority</label>
        <select id="editPriority">
          <option ${data.priority=="Low"?"selected":""}>Low</option>
          <option ${data.priority=="Medium"?"selected":""}>Medium</option>
          <option ${data.priority=="High"?"selected":""}>High</option>
        </select>

        <br><br>

        <label>Category</label>
        <input type="text" id="editCategory" value="${data.category || "Office"}">

        <br><br>

        <button onclick="closeModal()">Cancel</button>
        <button onclick="saveFromModal(${startSlot},${endSlot})">Save</button>
      `;

      modal.style.display = "flex";

    });

}

function closeModal() {

  const modal = document.getElementById("modal");

  modal.style.display = "none";

}

/* =========================================================
   SAVE EVENT
========================================================= */
function saveEvent(oldStart, oldEnd, newStart, newEnd, block=null) {

  const text =
    document.getElementById("editText")?.value ||
    block?.dataset.text ||
    block?.textContent.trim() ||
    "";

  fetch("/slot/update", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      old_start: oldStart,
      old_end: oldEnd,
      start_slot: newStart,
      end_slot: newEnd,
      text: text
    })
  })
  .then(r => {
    if(!r.ok) throw new Error("Save failed");

    if(block){

      block.dataset.start = newStart;
      block.dataset.end = newEnd;

      const slotHeight = parseFloat(
        getComputedStyle(document.documentElement)
        .getPropertyValue("--slot-height")
      );

      block.style.top = `${(newStart - 1) * slotHeight}px`;
      block.style.height = `${(newEnd - newStart + 1) * slotHeight}px`;

    }
  })
  .catch(err=>{
    console.error(err);
    alert("Failed to update event");
  });
}
/* =========================================================
   SMART PLANNER
========================================================= */

function handleSmartSave(e) {

  e?.preventDefault?.();

  const form = document.getElementById("planner-form");

  let text = document
    .querySelector('textarea[name="smart_plan"]')
    .value
    .trim();

  text = normalizeSmartTime(text);

  if (!text) {
    form.submit();
    return;
  }

  const timeRange = parseTimeRange(text);

  if (!timeRange) {
    smartAdd(text);
    return;
  }

  fetch("/smart/preview", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      text
    })
  })
  .then(r => r.json())
  .then(result => {

    if (!result.conflicts || !result.conflicts.length) {
      smartAdd(text);
      return;
    }

    openSmartPreview(result);

  });

}

function smartAdd(text){

  return fetch("/smart/add",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      text
    })
  }).then(()=>{

    window.location.reload();

  });

}

function openSmartPreview(result){

  const modal = document.getElementById("modal");
  const content = document.getElementById("modal-content");

  const html = result.conflicts.map(c=>`
    <div style="margin-bottom:10px">
      <strong>${c.time}</strong>
      <pre>${c.existing}</pre>
      <hr>
      <pre>${c.incoming}</pre>
    </div>
  `).join("");

  content.innerHTML = `
    <h3>⚠ Slot conflicts</h3>
    ${html}
    <button onclick="modal.style.display='none'">Cancel</button>
    <button onclick="smartAdd(document.querySelector('textarea[name=smart_plan]').value)">
      Overwrite & Save
    </button>
  `;

  modal.style.display = "flex";

}

function normalizeSmartTime(text){
  return text
    .split("\n")
    .map(l => l.trim().replace(/[ \t]+/g," "))
    .join("\n");
}

function parseTimeRange(text){

  const m = text.match(
    /(\\d{1,2})(?:[.:](\\d{2}))?\\s*-\\s*(\\d{1,2})(?:[.:](\\d{2}))?/
  );

  if (!m) return null;

  const sh = parseInt(m[1],10);
  const sm = parseInt(m[2] || "0",10);
  const eh = parseInt(m[3],10);
  const em = parseInt(m[4] || "0",10);

  if (sh > 23 || eh > 23 || sm > 59 || em > 59)
    return null;

  return {
    startMinutes: sh*60 + sm,
    endMinutes: eh*60 + em
  };

}
function timeToSlot(time){

  const [h,m] = time.split(":").map(Number);

  return h*2 + (m>=30 ? 2 : 1);

}
/* =========================================================
   SAVE FROM MODAL
========================================================= */
function saveFromModal(oldStart, oldEnd){

  const text = document.getElementById("editText").value;
  const startTime = document.getElementById("editStart").value;
  const endTime = document.getElementById("editEnd").value;
  const priority = document.getElementById("editPriority").value;
  const category = document.getElementById("editCategory").value;

  const newStart = timeToSlot(startTime);
  const newEnd = timeToSlot(endTime) - 1;

  fetch("/slot/update", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      old_start: oldStart,
      old_end: oldEnd,
      start_slot: newStart,
      end_slot: newEnd,
      text,
      priority,
      category
    })
  })
  .then(()=>location.reload());

}
/* =========================================================
   SLOT CHECKBOX STATUS
========================================================= */

document.addEventListener("change", async (e) => {

  if (!e.target.classList.contains("slot-checkbox"))
    return;

  const slot = e.target.dataset.slot;
  const checked = e.target.checked;

  await fetch("/slot/toggle-status",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      plan_date: PLAN_DATE,
      slot,
      status: checked ? "done":"open"
    })
  });

});

/* =========================================================
   CHECKIN MODAL
========================================================= */

function toggleCheckin(){

  const modal = document.getElementById("summary-modal");

  modal.style.display =
    modal.style.display === "flex"
      ? "none"
      : "flex";

}

/* =========================================================
   DATE NAVIGATION
========================================================= */

function jumpToDate(){

  const monthInput = document.getElementById("jump-month");
  const dayInput = document.getElementById("jump-day");

  if(!monthInput.value || !dayInput.value)
    return alert("Select date");

  const [year,month] = monthInput.value.split("-");
  const day = dayInput.value.padStart(2,"0");

  window.location.replace(
    `/?year=${year}&month=${month}&day=${day}`
  );

}

/* =========================================================
   PREFETCH ADJACENT DAYS
========================================================= */

function prefetchAdjacentDays(){

  const d = new Date(PLAN_DATE);

  [-1,1].forEach(offset=>{

    const date = new Date(d);
    date.setDate(d.getDate()+offset);

    const link = document.createElement("link");

    link.rel="prefetch";

    link.href =
      `/?year=${date.getFullYear()}&month=${date.getMonth()+1}&day=${date.getDate()}`;

    document.head.appendChild(link);

  });

}

/* =========================================================
   INIT
========================================================= */

document.addEventListener("DOMContentLoaded",()=>{

  prefetchAdjacentDays();

  initDragResize();
  initSlotDrag();

});
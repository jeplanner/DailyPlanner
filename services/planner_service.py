import json
import re
from datetime import datetime,date

from flask import session
from config import MONTHLY_RE,STARTING_RE,EVERY_DAY_RE,EVERY_WEEKDAY_RE,INTERVAL_RE,WEEKDAYS
from config import (
    TOTAL_SLOTS,
    DEFAULT_STATUS,
    HEALTH_HABITS,
    MIN_HEALTH_HABITS,
)

from utils.slots import generate_half_hour_slots
import logging
from supabase_client import get, post, update
from utils.planner_parser import parse_planner_input
from utils.slots import slot_label

logger = logging.getLogger(__name__)

def fetch_daily_slots(plan_date):

    user_id = session["user_id"]

    if hasattr(plan_date, "strftime"):
        plan_date = plan_date.strftime("%Y-%m-%d")

    rows = get(
        "daily_slots",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "select": "plan,start_time,status,end_time,slot,priority,category",
            "order": "slot.asc",
        },
    )

    if not rows:
        return []

    result = []

    for r in rows:

        # handle list rows
        if isinstance(r, list):
            plan, start_time, status, end_time, slot, *rest = r
            priority = rest[0] if len(rest) > 0 else None
            category = rest[1] if len(rest) > 1 else None

        # handle dict rows
        else:
            plan = r.get("plan")
            start_time = r.get("start_time")
            status = r.get("status")
            end_time = r.get("end_time")
            slot = r.get("slot")
            priority = r.get("priority")
            category = r.get("category")

        if plan and slot is not None:
            result.append({
                "plan": plan,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "slot": slot,
                "priority": priority,
                "category": category
            })
    logger.debug("FETCH RAW ROW SAMPLE → %s", rows[:2])
    return result

# ==========================================================
# DATA ACCESS – DAILY PLANNER
# ==========================================================
def load_slots_cached(plan_date):
    slots = get(
        "daily_slots",
        params={
            "user_id": f"eq.{session['user_id']}",
            "plan_date": f"eq.{plan_date.isoformat()}",
            "select": "slot,plan,status,start_time,end_time,priority,category",
            "order": "slot.asc"
        }
    ) or []

    slot_map = {r["slot"]: r for r in slots}

    return slots, slot_map
def load_day(plan_date, tag=None):
    plans = {
        i: {"plan": "", "status": DEFAULT_STATUS} for i in range(1, TOTAL_SLOTS + 1)
    }
    #  habits = set()
    #  reflection = ""
    # untimed_tasks = []  
    user_id =session["user_id"]
    #meta = get(
     #   "daily_meta",
      #  params={
       #     "user_id": f"eq.{user_id}",
        #    "plan_date": f"eq.{plan_date}",
         #   "select": "habits,reflection,untimed_tasks",
        #},
    #)

    #if meta:
     #   row = meta[0]
      #  habits = set(row.get("habits") or [])
       # reflection = row.get("reflection") or ""
        #untimed_tasks = row.get("untimed_tasks") or []

    rows = (
        get(
            "daily_slots",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date}",
                "select": "slot,plan,status,priority,category,tags",
            },
        )
        or []
    )

    for r in rows:
        slot = r.get("slot")

        if not isinstance(slot, int) or not (1 <= slot <= TOTAL_SLOTS):
            logger.error("Invalid slot dropped %s", r)
            continue

        row_tags = []
        if r.get("tags"):
          if isinstance(r["tags"], list):
              row_tags = r["tags"]
          elif isinstance(r["tags"], str):
              try:
                  row_tags = json.loads(r["tags"])
              except Exception:
                  row_tags = []


        if tag and tag not in row_tags:
            continue

        plans[r["slot"]] = {
            "plan": r.get("plan") or "",
            "status": r.get("status") or DEFAULT_STATUS,
            "priority": r.get("priority"),
            "category": r.get("category"),
            "tags": row_tags,
        }


    return plans




def clean_plan_text(text: str) -> str:

    if not text:
        return ""

    text = text.strip()

    # Remove "from X to Y"
    text = re.sub(
        r"\s*from\s+\d{1,2}(:\d{2})?\s*(am|pm)?\s+to\s+\d{1,2}(:\d{2})?\s*(am|pm)?",
        "",
        text,
        flags=re.I,
    )

    # Remove "@9", "@9:30"
    text = re.sub(
        r"\s*@\s*\d{1,2}(:\d{2})?\s*(am|pm)?",
        "",
        text,
        flags=re.I,
    )

    # Remove trailing spaces
    return text.strip()

def save_day(plan_date, form):
    user_id=session["user_id"]
    payload = []
    print("Hey i am getting called...")
    #auto_untimed = []
   # existing_meta = {}
   # meta_rows = get(
   #     "daily_meta",
     #   params={
      #      "user_id": f"eq.{user_id}",
       #     "plan_date": f"eq.{plan_date}",
     #       "select": "habits,reflection,untimed_tasks",
      #  },
  #  )

   # if meta_rows:   
   #     existing_meta = meta_rows[0]

    # Track slots already filled by smart parsing
    smart_block = form.get("smart_plan", "").strip()
    recurrence = parse_recurrence_block(smart_block, plan_date)

    # -------------------------------------------------
    # SMART MULTI-LINE INPUT (GLOBAL)
    # -------------------------------------------------
    if smart_block:
        for line in smart_block.splitlines():
            
            # -------------------------------------------------
            # Normalize leading time formats
            # -------------------------------------------------
            m = re.match(r"^(\d{1,2})(?:[.:](\d{2}))?\s*-\s*(\d{1,2})(?:[.:](\d{2}))?\s+(.+)$", line)
            if m:
                sh = m.group(1)
                sm = m.group(2) or "00"
                eh = m.group(3)
                em = m.group(4) or "00"
                task = m.group(5)

                line = f"{task} from {sh}:{sm} to {eh}:{em}"
            # Case 1: "9 task" → "task @9"
            m = re.match(r"^(\d{1,2})(?:\s+)(.+)$", line)
            if m:
                line = f"{m.group(2)} @{m.group(1)}"
            m = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\.(\d{2})\s+(.+)$", line)
            #Case 1a: "9-9.30 task" -> task from 9:00 to 9:30"
            if m:
                start = f"{m.group(1)}:00"
                end = f"{m.group(2)}:{m.group(3)}"
                line = f"{m.group(4)} from {start} to {end}"
            # Case 2: "9-10 task" → "task from 9 to 10"
            m = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+(.+)$", line)
            if m:
                line = f"{m.group(3)} from {m.group(1)} to {m.group(2)}"

            # Case 3: "9.30-10.30 task" → "task from 9:30 to 10:30"
            m = re.match(r"^(\d{1,2})\.(\d{2})\s*-\s*(\d{1,2})\.(\d{2})\s+(.+)$", line)
            if m:
                start = f"{m.group(1)}:{m.group(2)}"
                end = f"{m.group(3)}:{m.group(4)}"
                line = f"{m.group(5)} from {start} to {end}"

            line = line.strip()
          
            if not line:
                continue
            has_time = re.search(
                r"""
                (
                    @\s*\d{1,2}(:\d{2})?\s*(am|pm)? |
                    \bfrom\s+\d{1,2} |
                    ^\d{1,2}(\.\d{2})?(\s*(am|pm))? |
                    ^\d{1,2}(\.\d{2})?\s*-\s*\d{1,2}(\.\d{2})?
                )
                """,
                line,
                re.I | re.X
                )

            quadrant_match = re.search(r"\b(Q[1-4])\b", line, re.I)

            # -------------------------------------------------
            # CASE 1: No time BUT Q1–Q4 → Eisenhower-only
            # -------------------------------------------------
            if not has_time and quadrant_match:
                try:
                    # Reuse parser by injecting a dummy time
                    parsed = parse_planner_input(
                        line + " @12am",
                        plan_date
                    )

                    quadrant = parsed["quadrant"]

                    existing = get(
                        "todo_matrix",
                        params={
                            "plan_date": f"eq.{plan_date}",
                            "quadrant": f"eq.{quadrant}",
                            "task_text": f"eq.{parsed['title']}",
                            "is_deleted": "eq.false",
                        },
                    )

                    if not existing:
                        max_pos = get(
                        "todo_matrix",
                        params={
                            "plan_date": f"eq.{plan_date}",
                            "quadrant": f"eq.{quadrant}",
                            "is_deleted": "eq.false",
                            "select": "position",
                            "order": "position.desc",
                            "limit": 1,
                         },
                        )

                        next_pos = max_pos[0]["position"] + 1 if max_pos else 0
                        cleanedtext=clean_plan_text(line)
                        post(
                            "todo_matrix",
                            {
                                "plan_date": str(plan_date),
                                "quadrant": quadrant,
                                "task_text": cleanedtext,
                                "is_done": False,
                                "is_deleted": False,
                                "position": next_pos,
                                "category": parsed["category"],
                                "subcategory": "General",
                            },
                        )

                    logger.info(f"Eisenhower-only task added: {line}")
                    continue

                except Exception as e:
                    logger.error(f"Eisenhower-only parse failed: {line} → {e}")
                    continue

            # -------------------------------------------------
            # CASE 2: No time and no quadrant → skip
            # -------------------------------------------------
            # CASE 2: No time and no quadrant → append to untimed tasks
          #  if not has_time and not quadrant_match:
           #   auto_untimed.append({
           #         "id": f"u_{int(datetime.now().timestamp() * 1000)}_{len(auto_untimed)}",
           #         "text": line
           #     })
           #   continue
            
            try:
                parsed = parse_planner_input(line, plan_date)
                task_date = parsed["date"]
                # --------------------------------------------
                # AUTO-INSERT INTO EISENHOWER MATRIX (Q1–Q4)
                # --------------------------------------------
                if parsed.get("quadrant"):
                    quadrant = parsed["quadrant"]

                    task_time = parsed["start"].strftime("%H:%M")
                   
                    existing = get(
                        "todo_matrix",
                        params={
                            "plan_date": f"eq.{task_date}",
                            "quadrant": f"eq.{quadrant}",
                            "task_text": f"eq.{parsed['title']}",
                            "task_time": f"eq.{task_time}",  # 👈 prevent duplicates
                            "is_deleted": "eq.false",
                        },
                    )

                    if not existing:
                      max_pos = get(
                            "todo_matrix",
                            params={
                                "plan_date": f"eq.{task_date}",
                                "quadrant": f"eq.{quadrant}",
                                "is_deleted": "eq.false",
                                "select": "position",
                                "order": "position.desc",
                                "limit": 1,
                            },
                        )

                      next_pos = max_pos[0]["position"] + 1 if max_pos else 0
                      cleanedtext=clean_plan_text(line)
                      post(
                            "todo_matrix",
                            {
                                "plan_date": str(task_date),
                                "quadrant": quadrant,
                                "task_text": cleanedtext,
                                "task_date": str(task_date),   # ✅ retain date
                                "task_time": task_time,        # ✅ retain time
                                "is_done": False,
                                "is_deleted": False,
                                "position": next_pos,
                                "category": parsed["category"],
                                "subcategory": "General",
                            },
                        )
              

                slots = generate_half_hour_slots(parsed)
               
                affected_slots = set()

                affected_slots = {
                    s["slot"]
                    for s in slots
                    if 1 <= s["slot"] <= TOTAL_SLOTS
                }

                # -------------------------------
                # Slot metadata for recurrence
                # -------------------------------
                if affected_slots:
                    first_slot = min(affected_slots)
                    slot_count = len(affected_slots)
                else:
                    first_slot = None
                    slot_count = 0
                if recurrence["type"] and affected_slots:
                    existing = get(
                        "recurring_slots",
                        params={
                            "title": f"eq.{parsed['title']}",
                            "start_slot": f"eq.{first_slot}",
                            "slot_count": f"eq.{slot_count}",
                            "start_date": f"eq.{recurrence['start_date']}",
                            "is_active": "eq.true",
                        },
                    )

                    if not existing:
                        post(
                            "recurring_slots",
                            {
                                "user_id": user_id,
                                "title": clean_plan_text(parsed["title"]),
                                "start_slot": first_slot,
                                "slot_count": slot_count,
                                "recurrence_type": recurrence["type"],
                                "interval_value": recurrence["interval"],
                                "days_of_week": recurrence["days_of_week"],
                                "start_date": str(recurrence["start_date"]),
                                "is_active": True,
                            },
                        )

              

                # Re-insert smart slots
                for s in slots:
                    if 1 <= s["slot"] <= TOTAL_SLOTS:
                        payload.append(
                        {
                            "plan_date": str(task_date),
                            "slot": s["slot"],
                            "plan": clean_plan_text(parsed["title"]),

                            # 🔥 ADD THESE TWO LINES
                            "start_time": s["start"].strftime("%H:%M"),
                            "end_time": s["end"].strftime("%H:%M"),

                            "status": DEFAULT_STATUS,
                            "priority": s["priority"],
                            "category": s["category"],
                            "tags": s["tags"],
                            "user_id":user_id
                        }
                    )


            except Exception as e:
                logger.error(
                    f"Smart planner parse failed for line '{line}': {e}"
                )

    # -------------------------------------------------
    # MANUAL ENTRY (only if smart planner not used)
    # -------------------------------------------------
    if not smart_block:
        for slot in range(1, TOTAL_SLOTS + 1):
            plan = form.get(f"plan_{slot}", "").strip()
            status = form.get(f"status_{slot}", DEFAULT_STATUS)

            if not plan:
                continue

            payload.append(
                {
                    "user_id":user_id,
                    "plan_date": str(plan_date),
                    "slot": slot,
                    "plan": plan,
                    "status": status,
                }
            )

  

   # untimed_raw = form.get("untimed_tasks", "")

   # # 🔒 normalize untimed_raw to string
   # if isinstance(untimed_raw, list):
   #     untimed_raw = "\n".join(untimed_raw)
  #  elif untimed_raw is None:
   #     untimed_raw = ""

   # untimed_raw = untimed_raw.strip()

    #new_untimed = []

   # if untimed_raw:
    #    new_untimed = [
         #   {
          #      "id": f"u_{int(datetime.now().timestamp() * 1000)}_{i}",
           #     "text": line.strip()
          #  }
         #   for i, line in enumerate(untimed_raw.splitlines())
         #   if line.strip()
       # ]

   # merged = {}

    # Existing untimed tasks from DB
   # existing_untimed = existing_meta.get("untimed_tasks", [])
   # if isinstance(existing_untimed, list):
   #     for t in existing_untimed:
    ##  for t in auto_untimed:
   #     merged[t["id"]] = t

    # Manually entered untimed
   # for t in new_untimed:
      #  merged[t["id"]] = t

    # 🔒 Support both request.form and dict inputs
   # if hasattr(form, "getlist"):
   #     habits = form.getlist("habits")
   # else:
    #    habits = form.get("habits", []) or []

  #  if habits is None:
   #     habits = existing_meta.get("habits", [])
   
  #  update(
   # "daily_meta",
   # params={
  #      "user_id": f"eq.{user_id}",
   #     "plan_date": f"eq.{plan_date}",
   # },
  #  json={
  #      "habits": habits,
   #     "reflection": form.get("reflection", "").strip(),
   #     "untimed_tasks": list(merged.values()),
   # },
#)





    # -------------------------------------------------
    # FINAL WRITE (REQUIRED)
    # -------------------------------------------------
    ALLOWED_DAILY_COLUMNS = {
        "plan_date",
        "slot",
        "plan",
        "status",
        "priority",
        "category",
        "tags",
         # 🔥 ADD THESE
        "start_time",
        "end_time",
        "user_id",
    }

    clean_payload = [
        {k: v for k, v in row.items() if k in ALLOWED_DAILY_COLUMNS}
        for row in payload
    ]

    if clean_payload:
        post(
            "daily_slots?on_conflict=user_id,plan_date,slot",
            clean_payload,
            prefer="resolution=merge-duplicates",
        )



SLOT_LABELS = {i: slot_label(i) for i in range(1, TOTAL_SLOTS + 1)}
def load_tasks_from_slots(user_id, plan_date):
    rows = get(
        "daily_slots",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "select": "slot,plan",
            "order": "slot.asc",
        },
    ) or []

    tasks = []
    current = None

    for r in rows:
        slot = r.get("slot")
        text = (r.get("plan") or "").strip()

        if not text or slot not in SLOT_LABELS:
            current = None
            continue

        if (
            current is None
            or current["text"] != text
            or slot != current["end_slot"] + 1
        ):
            current = {
                "start_slot": slot,
                "end_slot": slot,
                "text": text,
            }
            tasks.append(current)
        else:
            current["end_slot"] = slot

    # add labels
    for t in tasks:
        start = SLOT_LABELS[t["start_slot"]].split("–")[0].strip()
        end = SLOT_LABELS[t["end_slot"]].split("–")[-1].strip()

        t["time_label"] = f"{start} – {end}"

    return tasks
def load_tasks_from_events(user_id, plan_date):
    rows = get(
    "daily_events",
    params={
        "user_id": f"eq.{user_id}",
        "plan_date": f"eq.{plan_date}",
        "is_deleted": "eq.false",
        "select": "start_time,end_time,title,description,status",
        "order": "start_time.asc",
    },
    ) or []

    tasks = []

    for r in rows:
        start = r.get("start_time")
        end = r.get("end_time")
        title = (r.get("title") or "").strip()
        desc = (r.get("description") or "").strip()
        text = f"{title} — {desc}" if desc else title
        if not start or not end or not text:
            continue

        tasks.append({
            "time_label": f"{start} – {end}",
            "text": text,
            "done": r.get("status") == "done"
        })

    return tasks
def get_daily_summary(plan_date, planner_mode="slots"):
    user_id = session["user_id"]

    meta_rows = get(
        "daily_meta",
        params={
            "user_id": f"eq.{user_id}",  # ✅ FIX
            "plan_date": f"eq.{plan_date}",
            "select": "habits,reflection",
        },
    ) or []

    habits = []
    reflection = ""

    if meta_rows:
        habits = meta_rows[0].get("habits") or []
        reflection = meta_rows[0].get("reflection") or ""

    # 🔁 SWITCH
    if planner_mode == "v2":
        tasks = load_tasks_from_events(user_id, plan_date)

        # ✅ fallback safety
        if not tasks:
            tasks = load_tasks_from_slots(user_id, plan_date)
    else:
        tasks = load_tasks_from_slots(user_id, plan_date)

    return {
        "tasks": tasks,
        "habits": habits,
        "reflection": reflection,
    }


def get_morning_dashboard(plan_date, user_id):
    """Build the unified morning-dashboard payload for /summary?view=daily.

    Returns a single chronologically-ordered agenda merging calendar
    meetings, Eisenhower/Matrix tasks scheduled for today, project
    tasks due today, plus today's habits; and a separate overdue list
    of tasks the user should pay off first.

    Shape:
        {
          "today_items":   [  # chronological, timed first, untimed last
              {
                "type": "meeting"|"task"|"habit",
                "time": "HH:MM"|None,
                "end_time": "HH:MM"|None,
                "title": str,
                "context": str|None,    # project name / quadrant label
                "done": bool,
                "priority": "high"|"medium"|"low"|None,
                "id": str|int|None,
                "link": str|None,       # deep link back to editing surface
              }, …
          ],
          "overdue":       [ {title, context, due_date, days_overdue, priority, source, id}, … ],
          "habits":        [ {id, name, unit, goal, value, habit_type, done, progress_pct}, … ],
          "counts":        {"meetings", "tasks", "habits", "habits_done", "overdue"},
        }
    """
    plan_date_iso = plan_date.isoformat() if hasattr(plan_date, "isoformat") else str(plan_date)

    today_items = []
    overdue = []

    # ── 1. Calendar meetings (daily_events) ───────────────────────
    try:
        events = get(
            "daily_events",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date_iso}",
                "is_deleted": "eq.false",
                "select": "id,title,description,start_time,end_time,status,priority,quadrant",
                "order": "start_time.asc",
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: events fetch failed: %s", e)
        events = []

    meeting_count = 0
    for e in events:
        title = (e.get("title") or "").strip()
        if not title:
            continue
        start = (e.get("start_time") or "")[:5] or None
        end = (e.get("end_time") or "")[:5] or None
        today_items.append({
            "type": "meeting",
            "time": start,
            "end_time": end,
            "title": title,
            "context": (e.get("description") or "").strip() or None,
            "done": (e.get("status") == "done"),
            "priority": e.get("priority") or None,
            "id": e.get("id"),
            "link": "/planner",
        })
        meeting_count += 1

    # ── 2. Matrix tasks for today ─────────────────────────────────
    try:
        matrix_rows = get(
            "todo_matrix",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date_iso}",
                "is_deleted": "eq.false",
                "select": "id,task_text,is_done,status,priority,quadrant,task_time,category,project_id",
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: matrix fetch failed: %s", e)
        matrix_rows = []

    # We want project names for the context column — batch one lookup.
    project_ids = {r.get("project_id") for r in matrix_rows if r.get("project_id")}
    project_name_map = {}
    if project_ids:
        try:
            prows = get(
                "projects",
                params={
                    "user_id": f"eq.{user_id}",
                    "project_id": f"in.({','.join(str(p) for p in project_ids)})",
                    "select": "project_id,name",
                },
            ) or []
            project_name_map = {p["project_id"]: p["name"] for p in prows}
        except Exception as e:
            logger.warning("morning dashboard: project lookup failed: %s", e)

    quadrant_labels = {
        "do": "Do Now", "schedule": "Schedule",
        "delegate": "Delegate", "eliminate": "Eliminate",
    }

    matrix_count = 0
    for r in matrix_rows:
        # Skip Travel-archived and hidden categories.
        cat = (r.get("category") or "")
        if cat == "Travel-archived":
            continue
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        tt = (r.get("task_time") or "")[:5] or None
        ctx = project_name_map.get(r.get("project_id")) or quadrant_labels.get(r.get("quadrant"))
        today_items.append({
            "type": "task",
            "time": tt,
            "end_time": None,
            "title": title,
            "context": ctx,
            "done": bool(r.get("is_done")),
            "priority": r.get("priority"),
            "id": r.get("id"),
            "link": "/todo",
        })
        matrix_count += 1

    # ── 3. Project tasks due today ────────────────────────────────
    try:
        proj_rows = get(
            "project_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "is_eliminated": "eq.false",
                "due_date": f"eq.{plan_date_iso}",
                "select": "task_id,task_text,status,priority,due_time,project_id",
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: project tasks due fetch failed: %s", e)
        proj_rows = []

    # Project-name lookup for project-tasks rows (may need more ids)
    more_proj_ids = {r.get("project_id") for r in proj_rows if r.get("project_id")} - set(project_name_map.keys())
    if more_proj_ids:
        try:
            prows = get(
                "projects",
                params={
                    "user_id": f"eq.{user_id}",
                    "project_id": f"in.({','.join(str(p) for p in more_proj_ids)})",
                    "select": "project_id,name",
                },
            ) or []
            for p in prows:
                project_name_map[p["project_id"]] = p["name"]
        except Exception as e:
            logger.warning("morning dashboard: project lookup 2 failed: %s", e)

    for r in proj_rows:
        if r.get("status") == "done":
            continue
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        today_items.append({
            "type": "task",
            "time": (r.get("due_time") or "")[:5] or None,
            "end_time": None,
            "title": title,
            "context": project_name_map.get(r.get("project_id")),
            "done": False,
            "priority": r.get("priority"),
            "id": f"pt-{r.get('task_id')}",
            "link": f"/projects/{r.get('project_id')}/tasks" if r.get("project_id") else None,
        })
        matrix_count += 1

    # ── 4. Habits (daily, from habit_master + today's entries) ────
    try:
        habit_rows = get(
            "habit_master",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "select": "id,name,unit,goal,habit_type,position",
                "order": "position.asc",
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: habits fetch failed: %s", e)
        habit_rows = []

    habit_value_map = {}
    if habit_rows:
        try:
            entry_rows = get(
                "habit_entries",
                params={
                    "user_id": f"eq.{user_id}",
                    "plan_date": f"eq.{plan_date_iso}",
                    "select": "habit_id,value",
                },
            ) or []
            habit_value_map = {r["habit_id"]: float(r.get("value") or 0) for r in entry_rows}
        except Exception as e:
            logger.warning("morning dashboard: habit entries failed: %s", e)

    habits = []
    habits_done = 0
    for h in habit_rows:
        goal = float(h.get("goal") or 0)
        value = habit_value_map.get(h["id"], 0.0)
        is_boolean = (h.get("habit_type") == "boolean")
        done = (value >= 1) if is_boolean else (goal > 0 and value >= goal)
        pct = 100 if done else (int(round(value / goal * 100)) if goal > 0 else 0)
        pct = max(0, min(100, pct))
        habits.append({
            "id": h["id"],
            "name": h.get("name"),
            "unit": h.get("unit"),
            "goal": goal,
            "value": value,
            "habit_type": h.get("habit_type"),
            "done": done,
            "progress_pct": pct,
        })
        if done:
            habits_done += 1

    # ── 5. Overdue tasks (project tasks + matrix tasks with past due) ─
    try:
        overdue_proj = get(
            "project_tasks",
            params={
                "user_id": f"eq.{user_id}",
                "is_eliminated": "eq.false",
                "status": "neq.done",
                "due_date": f"lt.{plan_date_iso}",
                "select": "task_id,task_text,priority,due_date,project_id",
                "order": "due_date.asc",
                "limit": 200,
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: overdue project fetch failed: %s", e)
        overdue_proj = []

    # Resolve any extra project names for overdue rows
    more_ids = {r.get("project_id") for r in overdue_proj if r.get("project_id")} - set(project_name_map.keys())
    if more_ids:
        try:
            prows = get(
                "projects",
                params={
                    "user_id": f"eq.{user_id}",
                    "project_id": f"in.({','.join(str(p) for p in more_ids)})",
                    "select": "project_id,name",
                },
            ) or []
            for p in prows:
                project_name_map[p["project_id"]] = p["name"]
        except Exception as e:
            logger.warning("morning dashboard: project lookup overdue failed: %s", e)

    def _days_overdue(d_iso):
        try:
            d = date.fromisoformat(d_iso)
            return (plan_date - d).days if hasattr(plan_date, "__sub__") else 0
        except Exception:
            return 0

    for r in overdue_proj:
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        d_iso = r.get("due_date")
        overdue.append({
            "title": title,
            "context": project_name_map.get(r.get("project_id")),
            "due_date": d_iso,
            "days_overdue": _days_overdue(d_iso),
            "priority": r.get("priority"),
            "source": "project",
            "id": f"pt-{r.get('task_id')}",
            "link": f"/projects/{r.get('project_id')}/tasks" if r.get("project_id") else None,
        })

    # Matrix tasks with task_date in the past and still not done
    try:
        overdue_matrix = get(
            "todo_matrix",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "is_done": "eq.false",
                "task_date": f"lt.{plan_date_iso}",
                "select": "id,task_text,priority,task_date,quadrant,category,project_id",
                "order": "task_date.asc",
                "limit": 200,
            },
        ) or []
    except Exception as e:
        logger.warning("morning dashboard: overdue matrix fetch failed: %s", e)
        overdue_matrix = []

    for r in overdue_matrix:
        if (r.get("category") or "") == "Travel-archived":
            continue
        title = (r.get("task_text") or "").strip()
        if not title:
            continue
        d_iso = r.get("task_date")
        overdue.append({
            "title": title,
            "context": project_name_map.get(r.get("project_id")) or quadrant_labels.get(r.get("quadrant")),
            "due_date": d_iso,
            "days_overdue": _days_overdue(d_iso),
            "priority": r.get("priority"),
            "source": "matrix",
            "id": r.get("id"),
            "link": "/todo",
        })

    overdue.sort(key=lambda x: (-(x.get("days_overdue") or 0), x.get("title") or ""))

    # ── 6. Sort today_items chronologically; untimed to the bottom ─
    prio_weight = {"high": 1, "medium": 2, "low": 3}
    today_items.sort(key=lambda it: (
        it.get("time") is None,
        it.get("time") or "",
        prio_weight.get(it.get("priority") or "", 4),
        it.get("title") or "",
    ))

    return {
        "today_items": today_items,
        "overdue": overdue,
        "habits": habits,
        "counts": {
            "meetings": meeting_count,
            "tasks": matrix_count,
            "habits": len(habits),
            "habits_done": habits_done,
            "overdue": len(overdue),
        },
    }


def get_weekly_summary(start_date, end_date, planner_mode="slots"):
    user_id = session["user_id"]

    # ----------------------------
    # LOAD DATA
    # ----------------------------
    if planner_mode == "v2":
        rows =rows = get(
            "daily_events",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "and": f"(plan_date.gte.{start_date},plan_date.lte.{end_date})",
                "select": "plan_date,start_time,end_time,title,status",
                "order": "plan_date.asc,start_time.asc",
            },
        ) or []
    else:
        rows = get(
            "daily_slots",
            params={
                "user_id": f"eq.{user_id}",
                "plan_date": f"gte.{start_date}",
                "and": f"(plan_date.lte.{end_date})",
                "select": "plan_date,slot,plan,status",
                "order": "plan_date.asc,slot.asc",
            },
        ) or []

    # ----------------------------
    # META (FIX: add user_id)
    # ----------------------------
    meta = get(
        "daily_meta",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"gte.{start_date}",
            "and": f"(plan_date.lte.{end_date})",
            "select": "plan_date,habits,reflection",
        },
    ) or []

    # ----------------------------
    # PROCESS
    # ----------------------------
    days = {}
    total_minutes = 0
    completed_minutes = 0

    for r in rows:

        date = r.get("plan_date")

        # =========================
        # V2 (EVENT-BASED)
        # =========================
        if planner_mode == "v2":
            title = (r.get("title") or "").strip()
            desc = (r.get("description") or "").strip()
            text = f"{title} — {desc}" if desc else title
            start = r.get("start_time")
            end = r.get("end_time")

            if not text or not start or not end:
                continue

            label = f"{start} – {end}"

            # ⏱️ duration calc
            try:
                sh, sm = map(int, start.split(":"))
                eh, em = map(int, end.split(":"))
                duration = (eh * 60 + em) - (sh * 60 + sm)
            except:
                duration = 0

            days.setdefault(date, []).append({
                "label": label,
                "text": text,
                "done": r.get("status") == "done",
            })

            total_minutes += duration
            if r.get("status") == "done":
                completed_minutes += duration

        # =========================
        # V1 (SLOT-BASED)
        # =========================
        else:
            text = (r.get("plan") or "").strip()
            slot = r.get("slot")

            if not text or slot not in SLOT_LABELS:
                continue

            days.setdefault(date, []).append({
                "slot": slot,
                "label": SLOT_LABELS[slot],
                "text": text,
                "done": r.get("status") == "done",
            })

            total_minutes += 30
            if r.get("status") == "done":
                completed_minutes += 30

    # ----------------------------
    # META PROCESSING
    # ----------------------------
    habit_days = 0
    reflections = []

    for m in meta:
        if m.get("habits"):
            habit_days += 1
        if m.get("reflection"):
            reflections.append(m["reflection"])

    # ----------------------------
    # FINAL METRICS
    # ----------------------------
    focused_hours = round(total_minutes / 60, 1)

    completion_rate = (
        round((completed_minutes / total_minutes) * 100, 1)
        if total_minutes else 0
    )

    return {
        "days": days,
        "focused_hours": focused_hours,
        "completion_rate": completion_rate,
        "habit_days": habit_days,
        "reflections": reflections,
    }
def generate_weekly_insight(data):
    insights = []

    if data["completion_rate"] >= 80:
        insights.append("🔥 Excellent execution this week.")
    elif data["completion_rate"] >= 50:
        insights.append("👍 Decent follow-through, room to tighten focus.")
    else:
        insights.append("⚠️ Planning exceeded execution — simplify next week.")

    if data["habit_days"] >= 5:
        insights.append("💪 Strong habit consistency.")
    elif data["habit_days"] >= 3:
        insights.append("🙂 Habits are forming — keep them visible.")
    else:
        insights.append("🧠 Habits slipped — reduce friction next week.")

    if data["focused_hours"] >= 25:
        insights.append("⏱ High focus output — watch for burnout.")
    elif data["focused_hours"] >= 15:
        insights.append("⏳ Solid focus foundation.")
    else:
        insights.append("⚡ Increase protected focus blocks.")

    return insights


def ensure_daily_habits_row(user_id, plan_date):
    existing = get(
        "daily_meta",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
        },
    )

    if existing:
        return

    post(
        "daily_meta",
        {
            "user_id": user_id,
            "plan_date": str(plan_date),
            "habits": [],
            "reflection": "",
            "untimed_tasks": [],
        },
    )



def is_health_day(habits):
    return len(HEALTH_HABITS.intersection(habits)) >= MIN_HEALTH_HABITS
def compute_health_streak(user_id, plan_date):

    try:
        # Get active habits
        habit_defs = get(
            "habit_master",
            {
                "user_id": f"eq.{user_id}",
                "is_deleted": "is.false"
            }
        )

        total = len(habit_defs)
        if total == 0:
            return 0

        habit_map = {h["id"]: h for h in habit_defs}

        # Get entries for that day
        entries = get(
            "habit_entries",
            {
                "user_id": f"eq.{user_id}",
                "plan_date": f"eq.{plan_date}"
            }
        )

        completed = 0

        for e in entries:
            habit = habit_map.get(e["habit_id"])
            if not habit:
                continue

            goal = float(habit.get("goal") or 0)
            value = float(e.get("value") or 0)

            if goal > 0 and value >= goal:
                completed += 1

        return completed

    except Exception as e:
        logger.warning(f"Health streak query failed: {e}")
        return 0

def parse_recurrence_block(text, default_date):
    text = text.lower()

    recurrence = {
        "type": None,
        "interval": None,
        "days_of_week": None,
        "start_date": default_date,
    }

    if m := re.search(STARTING_RE, text, re.I):
        try:
            recurrence["start_date"] = date.fromisoformat(m.group(1))
        except Exception:
            recurrence["start_date"] = default_date


    if re.search(EVERY_DAY_RE, text, re.I):
        recurrence["type"] = "daily"

    elif m := re.search(EVERY_WEEKDAY_RE, text, re.I):
        recurrence["type"] = "weekly"
        recurrence["days_of_week"] = [WEEKDAYS[m.group(1)]]

    elif m := re.search(INTERVAL_RE, text, re.I):
        recurrence["type"] = "interval"
        recurrence["interval"] = int(m.group(1))

    elif re.search(MONTHLY_RE, text, re.I):
        recurrence["type"] = "monthly"

    return recurrence
def group_slots_into_blocks(plans):
    blocks = []
    current = None

    logger.debug("PLANS SAMPLE: %s", list(plans.items())[:10])

    for slot in sorted(plans.keys()):
        plan = (plans[slot].get("plan") or "").strip()

        if not plan:
            current = None
            continue

        if (
            current
            and current["text"] == plan
            and slot == current["end_slot"] + 1
        ):
            current["end_slot"] = slot

        else:
            current = {
                "text": plan,
                "start_slot": slot,
                "end_slot": slot,
                "status": plans[slot].get("status"),
                "recurring_id": plans[slot].get("recurring_id"),
                "category": plans[slot].get("category"),
                "priority": plans[slot].get("priority"),
            }

            blocks.append(current)

    return blocks
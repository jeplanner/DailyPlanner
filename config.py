from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
TOTAL_SLOTS = 48
DEFAULT_STATUS = "Nothing Planned"
MIN_HEALTH_HABITS = 2
HEALTH_HABITS = {"Workout", "Walking", "Meditation", "Yoga", "Water"}

STATUSES = ["Nothing Planned", "Yet to Start", "In Progress", "Closed", "Deferred"]

HABIT_LIST = [
    "Walking",
    "Water",
    "No Shopping",
    "No TimeWastage",
    "8 hrs sleep",
    "Daily prayers",
]

HABIT_ICONS = {
    "Walking": "🚶",
    "Water": "💧",
    "No Shopping": "🛑🛍️",
    "No TimeWastage": "⏳",
    "8 hrs sleep": "😴",
    "Daily prayers": "🙏",
}
MOTIVATIONAL_QUOTES = [
    {"icon": "🎯", "text": "Focus on what matters, not what screams loudest."},
    {"icon": "⏳", "text": "Urgent is not always important."},
    {"icon": "🧠", "text": "Clarity comes from prioritization."},
    {"icon": "📌", "text": "Do the right thing, not everything."},
    {"icon": "📅", "text": "What you schedule gets done."},
    {"icon": "🌱", "text": "Small progress each day adds up."},
    {"icon": "✂️", "text": "Decide what not to do."},
    {"icon": "🧭", "text": "Your priorities shape your future."},
    {"icon": "⚡", "text": "Action beats intention."},
    {"icon": "☀️", "text": "Important tasks deserve calm attention."},
]

### Travel mode Code Changes ###
TASK_CATEGORIES = {
    "Office": "🏢",
    "Personal": "👤",
    "Family": "👨‍👩‍👧",
    "Travel": "✈️",
    "Health": "🩺",
    "Finance": "💰",
    "General": "📁",
}


STATIC_TRAVEL_SUBGROUPS = {
    "Utilities": "⚙️",
    "Security": "🔐",
    "Vehicle": "🚗",
    "Documents": "📄",
    "Gadgets": "🔌",
    "Personal": "🧳",
}

### Travel mode Code Changes ###
### Category, Sub Category Changes start here ###

TRAVEL_MODE_TASKS = [
    # =========================
    # Utilities (Home shutdown)
    # =========================
    ("do", "Geyser switched off", "Utilities"),
    ("do", "Toilet valves closed", "Utilities"),
    ("do", "Fridge switched off", "Utilities"),
    ("do", "No food left inside fridge", "Utilities"),
    ("do", "Fridge door kept open", "Utilities"),
    ("do", "Washing machine switched off", "Utilities"),
    ("do", "Dishwasher switched off", "Utilities"),
    ("do", "Iron box switched off", "Utilities"),
    ("do", "AquaGuard valve closed & switched off", "Utilities"),
    ("do", "Router switched off", "Utilities"),
    ("do", "Inverter switched off", "Utilities"),
    ("do", "Main power switched off (Bengaluru)", "Utilities"),
    ("do", "All lights switched off", "Utilities"),
    ("do", "All vessels washed", "Utilities"),
    # =========================
    # Security & Housekeeping
    # =========================
    ("do", "Blankets and pillows kept inside", "Security"),
    ("do", "All doors closed", "Security"),
    ("do", "Door locked", "Security"),
    ("do", "Pooja room check", "Security"),
    ("do", "Bengaluru and Chennai house keys taken", "Security"),
    # =========================
    # Vehicle
    # =========================
    ("do", "Petrol and tyre air pressure checked", "Vehicle"),
    ("do", "Car wiper checked", "Vehicle"),
    # =========================
    # Gadgets & Electronics
    # =========================
    ("do", "Mobile phones (2)", "Gadgets"),
    ("do", "Watches (2)", "Gadgets"),
    ("do", "Power bank", "Gadgets"),
    ("do", "AirPods (2)", "Gadgets"),
    ("do", "Galaxy tablet", "Gadgets"),
    ("do", "iPad", "Gadgets"),
    ("do", "HP laptop", "Gadgets"),
    ("do", "Office laptop", "Gadgets"),
    ("do", "Laptop charger", "Gadgets"),
    ("do", "Floor robo cleaner packed", "Gadgets"),
    # =========================
    # Documents & Essentials
    # =========================
    ("do", "Purse", "Documents"),
    ("do", "Travel pouch", "Documents"),
    ("do", "Tickets (if applicable)", "Documents"),
    ("do", "ID card", "Documents"),
    # =========================
    # Personal & Misc
    # =========================
    ("do", "Clothes packed", "Personal"),
    ("do", "Homeopathy tablets", "Personal"),
    ("do", "Any vessels, groceries, or vegetables to be taken", "Personal"),
]

# ============================
# PLANNER PARSING CONFIG
# ============================

PRIORITY_RANK = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
}

DEFAULT_PRIORITY = "Medium"

# ── SIMPLE GOALS ────────────────────────────────────────────────────
# Asked 2026-08-30: "make the projects simpler. I want to attach just
# goals to tasks. dont want all this intiative,epic hierarchy. disable
# for the timebeing."
#
# True  → a task is filed against a GOAL (an objective) and the Epic and
#         Initiative pickers are hidden.
# False → the full Objective → Key Result → Initiative → Epic ladder,
#         exactly as before.
#
# A FLAG AND NOT A DELETION, because "for the timebeing" is the whole
# instruction: nothing is removed, no column is dropped, and every
# existing initiative_id / epic_id keeps working and keeps being written
# behind the scenes — project progress is computed from that tree, so
# tearing it out would silently change every project's completion
# figure. Flip this to False and the old pickers come back.
#
# Why the middle of the ladder is the part hidden, measured on the live
# data the day it was asked for:
#     key results whose current_value had EVER moved:  0 of 28
#     tasks linked to a key result:                    3 of 120
SIMPLE_GOALS = True
DEFAULT_CATEGORY = "Office"
QUADRANT_MAP = {
    "Q1": "do",
    "Q2": "schedule",
    "Q3": "delegate",
    "Q4": "eliminate",
}
WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
### Category, Subcategory code ends here ###
SLOT_MINUTES = 30

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
STARTING_RE = r"starting\s+([\w\- ]+)"
EVERY_DAY_RE = r"\bevery\s+day\b"
EVERY_WEEKDAY_RE = r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
INTERVAL_RE = r"\bonce\s+in\s+(\d+)\s+days?\b"
MONTHLY_RE = r"\b(once\s+in\s+a\s+month|every\s+month)\b"
QUADRANT_ALIASES = {
    "do_now": "do",
    "schedule": "schedule",
    "delegate": "delegate",
    "eliminate": "eliminate",
    }
#SLOT_HEIGHT_PX = 36      # must match CSS --slot-height
#MINUTES_PER_SLOT = 30
#FIRST_VISIBLE_SLOT = 15  # 07:00–07:30
#GRID_START_MINUTES = (FIRST_VISIBLE_SLOT - 1) * MINUTES_PER_SLOT
#PX_PER_MIN = SLOT_HEIGHT_PX / MINUTES_PER_SLOT
PRIORITY_MAP = {
    "high": 1,
    "medium": 2,
    "low": 3
}
SORT_PRESETS = {
    "smart": (
        "is_pinned.desc,"
        "due_date.asc,"
        "priority_rank.asc,"
        "order_index.asc"
    ),
    "due": (
        "is_pinned.desc,"
        "due_date.asc,"
        "order_index.asc"
    ),
    "priority": (
        "is_pinned.desc,"
        "priority_rank.asc,"
        "order_index.asc"
    ),
    "created": (
        "is_pinned.desc,"
        "order_index.asc,"
        "created_at.asc"
    ),
}

from flask import Flask
import os
from logger import setup_logger

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")

    logger = setup_logger()

    # --------------------------------
    # Register Blueprints
    # --------------------------------
    from routes.planner import planner_bp
    from routes.todo import todo_bp
    from routes.projects import projects_bp
    from routes.health import health_bp
    from routes.habits import habits_bp
    from routes.references import references_bp
    from routes.ai import ai_bp
    from routes.events import events_bp
    from routes.timeline import timeline_bp
    from routes.notes import notes_bp

    app.register_blueprint(planner_bp)
    app.register_blueprint(todo_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(references_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(notes_bp)

    return app


app = create_app()





## Eisenhower Matrix + Daily Planner integrated. Calender control working
print("STEP 1: app.py import started")
from re import search
from warnings import filters
from flask import (
    Flask, request, redirect, url_for,
    render_template, render_template_string,
    session, jsonify, abort
)
import os
from datetime import date, datetime, timedelta
import calendar
from calendar import monthrange
import json
from google.auth.transport.requests import Request   
from werkzeug.wrappers import response
from supabase_client import get, post, update
from logger import setup_logger
from utils.dates import safe_date 
from config import TOTAL_SLOTS,QUADRANT_MAP
from utils.calender_links import google_calendar_link
from services.planner_service import generate_weekly_insight, load_day, save_day, get_daily_summary, get_weekly_summary,compute_health_streak,is_health_day,ensure_daily_habits_row,group_slots_into_blocks
from services.planner_service import fetch_daily_slots
from services.login_service import login_required
from services.eisenhower_service import autosave_task
from config import MIN_HEALTH_HABITS
from services.recurring_service import materialize_recurring_slots
from services.gantt_service import build_gantt_tasks
from services.eisenhower_service import (
    copy_open_tasks_from_previous_day,  
    enable_travel_mode,
)
from services.task_service import (
    complete_task_occurrence,
    skip_task_occurrence,
    update_task_occurrence,
    compute_next_occurrence
)
from collections import OrderedDict
from services.untimed_service import remove_untimed_task  
from services.timeline_service import load_timeline_tasks
from templates.planner import PLANNER_TEMPLATE
from templates.todo import TODO_TEMPLATE
from templates.summary import SUMMARY_TEMPLATE
from templates.login import LOGIN_TEMPLATE
from utils.smartplanner import parse_smart_sentence
from config import (
    IST,
    STATUSES,
    DEFAULT_STATUS, 
    HABIT_ICONS,
    HABIT_LIST,
    PRIORITY_MAP,
    SORT_PRESETS,
)
from utils.planner_parser import parse_planner_input
from utils.slots import current_slot,slot_label
import traceback
from services.ai_service  import call_gemini
import requests
from bs4 import BeautifulSoup
from utils.dates import safe_date_from_string
import bleach
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime

from requests.exceptions import HTTPError
print("STEP 2: imports completed")

app = Flask(__name__)
print("STEP 3: flask created")
logger = setup_logger()
@app.errorhandler(Exception)
def catch_all_errors(e):
    print("🔥 GLOBAL EXCEPTION CAUGHT 🔥")
    traceback.print_exc()   # <-- ALWAYS prints
    logger.exception("UNHANDLED EXCEPTION")
    return "Internal Server Error", 500

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
# ==========================================================
# Log in codestarts here
# ==========================================================
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # REMOVE in production









































# ENTR
# Y POINT
# ==========================================================
#if __name__ == "__main__":
 #   logger.info("Starting Daily Planner – stable + Eisenhower")
    #app.run(debug=True)

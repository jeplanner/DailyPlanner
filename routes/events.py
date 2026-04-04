
import logging
from datetime import datetime
import os

from flask import Blueprint, jsonify, redirect, request, session, url_for
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")

from routes.planner import build_google_datetime, get_conflicts
from services.login_service import login_required
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from utils.dates import safe_date_from_string
from utils.planner_parser import parse_planner_input
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
events_bp = Blueprint("events", __name__)
@events_bp.route("/api/v2/events")
@login_required
def list_events():
    user_id = session["user_id"]
    plan_date = request.args.get("date")

    events = get(
        "daily_events",
        params={
            "user_id": f"eq.{user_id}",
            "plan_date": f"eq.{plan_date}",
            "is_deleted": "eq.false",
            "order": "start_time.asc"
        }
    ) or []

    return jsonify(events)

@events_bp.route("/api/v2/events", methods=["POST"])
@login_required
def create_event():
    user_id = session["user_id"]
    data = request.json
    force = data.get("force", False)

    if data["end_time"] <= data["start_time"]:
        return jsonify({"error": "Invalid time range"}), 400

    conflicts = get_conflicts(
        user_id,
        data["plan_date"],
        data["start_time"],
        data["end_time"]
    )

    if conflicts and not force:
        return jsonify({
            "conflict": True,
            "conflicting_events": conflicts
        }), 409

    response1 = post("daily_events", {
    "user_id": user_id,
    "plan_date": data["plan_date"],
    "start_time": data["start_time"],
    "end_time": data["end_time"],
    "title": data["title"],
    "description": data.get("description", ""),
    "priority": data.get("priority", "medium")
    })
    created_row = response1[0] if response1 else None
    if created_row:
        try:
            google_id = insert_google_event(created_row)
            if google_id:
                update(
                    "daily_events",
                    params={"id": f"eq.{created_row['id']}", "user_id": f"eq.{session['user_id']}"},
                    json={"google_event_id": google_id}
                )
        except Exception as e:
            logger.warning("Google sync failed on create: %s", e)

    return jsonify({"success": True})


@events_bp.route("/api/v2/events/<event_id>", methods=["PUT"])
@login_required
def update_event(event_id):

    user_id = session["user_id"]
    data = request.json
    force = data.get("force", False)

    conflicts = get_conflicts(
        user_id,
        data["plan_date"],
        data["start_time"],
        data["end_time"],
        exclude_id=event_id
    )

    if conflicts and not force:
        return jsonify({
            "conflict": True,
            "conflicting_events": conflicts
        }), 409

    update(
        "daily_events",
        params={"id": f"eq.{event_id}"},
        json={
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "title": data["title"],
            "description": data.get("description", "")
        }
    )
    # 🔥 SYNC GOOGLE UPDATE
    row = get(
        "daily_events",
        params={"id": f"eq.{event_id}"}
    )

    if row and row[0].get("google_event_id"):
        try:
            google_id = row[0]["google_event_id"]

            # 🔥 Load user Google credentials from DB
            user_id = session["user_id"]

            rows = get(
                "user_google_tokens",
                {"user_id": f"eq.{user_id}"}
            )

            if rows:
                token_row = rows[0]

                credentials = Credentials(
                    token=token_row["access_token"],
                    refresh_token=token_row["refresh_token"],
                    token_uri=token_row["token_uri"],
                    client_id=token_row["client_id"],
                    client_secret=token_row["client_secret"],
                    scopes=token_row["scopes"].split(",")
                )

                if credentials.expired and credentials.refresh_token:
                    print("Google Credentials Expired")
                    credentials.refresh(Request())

                    update(
                        "user_google_tokens",
                        params={"user_id": f"eq.{user_id}"},
                        json={"access_token": credentials.token}
                    )

                service = build("calendar", "v3", credentials=credentials)

                service.events().update(
                    calendarId="primary",
                    eventId=google_id,
                    body={
                        "summary": data["title"],
                        "description": data.get("description", ""),
                        "start": {
                            "dateTime": f"{data['plan_date']}T{data['start_time']}:00",
                            "timeZone": "Asia/Kolkata"
                        },
                        "end": {
                            "dateTime": f"{data['plan_date']}T{data['end_time']}:00",
                            "timeZone": "Asia/Kolkata"
                        }
                    }
                ).execute()
        except Exception as e:
            logger.warning("Google update failed: %s", e)
    return jsonify({"success": True})

@events_bp.route("/api/v2/events/<event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id):
    update(
        "daily_events",
        params={"id": f"eq.{event_id}"},
        json={"is_deleted": True}
    )
    row = get(
    "daily_events",
    params={"id": f"eq.{event_id}"}
)

    if row and row[0].get("google_event_id"):
        try:
            google_id = row[0]["google_event_id"]

            user_id = session["user_id"]

            rows = get(
                "user_google_tokens",
                {"user_id": f"eq.{user_id}"}
            )

            if rows:
                token_row = rows[0]

                credentials = Credentials(
                    token=token_row["access_token"],
                    refresh_token=token_row["refresh_token"],
                    token_uri=token_row["token_uri"],
                    client_id=token_row["client_id"],
                    client_secret=token_row["client_secret"],
                    scopes=token_row["scopes"].split(",")
                )

                service = build("calendar", "v3", credentials=credentials)

                service.events().delete(
                    calendarId="primary",
                    eventId=google_id
                ).execute()

        except Exception as e:
            logger.warning("Google delete failed: %s", e)
    return {"ok": True}

@events_bp.post("/api/v2/smart-create")
@login_required
def smart_create():
    data = request.json or {}

    text = data.get("text", "").strip()
    date = safe_date_from_string(data.get("date"))

    created = []
    failed = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            parsed = parse_planner_input(line, date)

            payload = {
                "plan_date": str(parsed["date"]),
                "start_time": parsed["start"].strftime("%H:%M"),
                "end_time": parsed["end"].strftime("%H:%M"),
                "title": parsed["title"],
            }
            user_id = session["user_id"]
            result, status = insert_event(user_id, payload)

            if status == 200:
                created.append(payload)
            else:
                failed.append({
                    "line": raw_line,
                    "error": result
                })

        except Exception as e:
            failed.append({
                "line": raw_line,
                "error": str(e)
            })

    return jsonify({
        "status": "ok",
        "created_count": len(created),
        "failed_count": len(failed),
        "failed": failed
    })
@events_bp.route('/google-login')
@login_required
def google_login():
    flow = Flow.from_client_config(
    {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    scopes=SCOPES,
    redirect_uri=url_for('events.oauth2callback', _external=True)
    )

    authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true',
    prompt='consent'
    )

    session['state'] = state
    return redirect(authorization_url)

def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
@events_bp.route('/oauth2callback')
@login_required
def oauth2callback():

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=url_for("events.oauth2callback", _external=True)
    )

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    creds_dict = credentials_to_dict(credentials)
    user_id = session["user_id"]

    # 🔥 MANUAL UPSERT (since you don't use supabase upsert)
    existing = get(
        "user_google_tokens",
        {"user_id": f"eq.{user_id}"}
    )

    if existing:
        update(
            "user_google_tokens",
            params={"user_id": f"eq.{user_id}"},
            json={
                "access_token": creds_dict["token"],
                "refresh_token": creds_dict["refresh_token"],
                "token_uri": creds_dict["token_uri"],
                "client_id": creds_dict["client_id"],
                "client_secret": creds_dict["client_secret"],
                "scopes": ",".join(creds_dict["scopes"])
            }
        )
    else:
        post(
            "user_google_tokens",
            {
                "user_id": user_id,
                "access_token": creds_dict["token"],
                "refresh_token": creds_dict["refresh_token"],
                "token_uri": creds_dict["token_uri"],
                "client_id": creds_dict["client_id"],
                "client_secret": creds_dict["client_secret"],
                "scopes": ",".join(creds_dict["scopes"])
            }
        )

    return redirect("/planner-v2")

def insert_google_event(event_row):
    user_id = session.get("user_id")
    if not user_id:
        return None
    rows = get(
        "user_google_tokens",
        {"user_id": f"eq.{user_id}"}
    )

    if not rows:
        return None

    row = rows[0]

    credentials = Credentials(
        token=row["access_token"],
        refresh_token=row["refresh_token"],
        token_uri=row["token_uri"],
        client_id=row["client_id"],
        client_secret=row["client_secret"],
        scopes=row["scopes"].split(",")
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        update(
            "user_google_tokens",
            params={"user_id": f"eq.{user_id}"},
            json={
                "access_token": credentials.token,
                "updated_at": datetime.utcnow().isoformat()
            }
        )

    service = build("calendar", "v3", credentials=credentials)

    start_iso = build_google_datetime(event_row["plan_date"], event_row["start_time"])
    end_iso = build_google_datetime(event_row["plan_date"], event_row["end_time"])

    event_body = {
        "summary": event_row["title"],
        "description": event_row.get("description", ""),
        "start": {
            "dateTime": start_iso,
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": "Asia/Kolkata"
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 10}
            ]
        }
    }

    created = service.events().insert(
        calendarId="primary",
        body=event_body
    ).execute()

    return created.get("id")

def insert_event(user_id, data, force=False):
    if data["end_time"] <= data["start_time"]:
        return {"error": "Invalid time range"}, 400

    conflicts = get_conflicts(
        user_id,
        data["plan_date"],
        data["start_time"],
        data["end_time"]
    )

    if conflicts and not force:
        return {
            "conflict": True,
            "conflicting_events": conflicts
        }, 409

    response1 = post("daily_events", {
        "user_id": user_id,
        "plan_date": data["plan_date"],
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "title": data["title"],
        "description": data.get("description", "")
    })

    created_row = response1[0] if response1 else None

    # 🔥 GOOGLE AUTO SYNC HERE
    if created_row:
        try:
            google_id = insert_google_event(created_row)

            if google_id:
                update(
                    "daily_events",
                    params={"id": f"eq.{created_row['id']}"},
                    json={"google_event_id": google_id}
                )
        except Exception as e:
            logger.warning("Google sync failed on insert: %s", e)

    return {"success": True}, 200
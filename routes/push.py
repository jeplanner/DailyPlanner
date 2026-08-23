"""
Web Push endpoints.

Flow:
  1. Client requests /api/push/vapid-public-key and uses it to subscribe
     via the browser's PushManager.
  2. Client POSTs the subscription JSON to /api/push/subscribe.
  3. Server stores { endpoint, p256dh, auth, user_agent } in
     `push_subscriptions`.
  4. The scheduler (services/push_scheduler.py) later calls
     services.push_service.send_to_user() to fan a notification out to
     every active subscription for a user.
"""
import os

from flask import Blueprint, jsonify, request, session

from auth import login_required
from services import push_service
from supabase_client import get, post, update

push_bp = Blueprint("push", __name__)


@push_bp.route("/api/push/vapid-public-key", methods=["GET"])
@login_required
def vapid_public_key():
    key = os.environ.get("VAPID_PUBLIC_KEY", "")
    if not key:
        return jsonify({"error": "VAPID_PUBLIC_KEY not configured"}), 503
    return jsonify({"key": key})


@push_bp.route("/api/push/subscribe", methods=["POST"])
@login_required
def subscribe():
    user_id = session["user_id"]
    data = request.get_json() or {}

    sub = data.get("subscription") or {}
    endpoint = sub.get("endpoint")
    keys = sub.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({"error": "Invalid subscription payload"}), 400

    existing = get(
        "push_subscriptions",
        {"endpoint": f"eq.{endpoint}"},
    )

    if existing:
        update(
            "push_subscriptions",
            params={"endpoint": f"eq.{endpoint}"},
            json={
                "user_id": user_id,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": (data.get("user_agent") or request.headers.get("User-Agent") or "")[:500],
                "is_active": True,
            },
        )
    else:
        post(
            "push_subscriptions",
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": (data.get("user_agent") or request.headers.get("User-Agent") or "")[:500],
                "is_active": True,
            },
            prefer="return=minimal",
        )

    return jsonify({"success": True})


@push_bp.route("/api/push/status", methods=["POST"])
@login_required
def status():
    """Does the SERVER think it can reach this exact browser?

    The panel used to report `Notification.permission`, which is the
    browser's opinion and not the one that decides whether anything gets
    delivered. A device can sit at "granted" for months while its row here
    is `is_active = false` — the send got a 404/410 from the push service
    once and the row was retired — and every screen still says
    notifications are on.

    That gap is the whole diagnosis for a phone that receives nothing with
    the app closed, and it was visible nowhere. Now the panel can ask.
    """
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"known": False, "active": False})

    rows = get("push_subscriptions", {
        "endpoint": f"eq.{endpoint}",
        "user_id": f"eq.{session['user_id']}",
        "select": "endpoint,is_active",
        "limit": "1",
    }) or []
    if not rows:
        return jsonify({"known": False, "active": False})
    return jsonify({"known": True, "active": bool(rows[0].get("is_active"))})


@push_bp.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def unsubscribe():
    data = request.get_json() or {}
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"error": "endpoint required"}), 400

    update(
        "push_subscriptions",
        params={
            "endpoint": f"eq.{endpoint}",
            "user_id": f"eq.{session['user_id']}",
        },
        json={"is_active": False},
    )
    return jsonify({"success": True})


@push_bp.route("/api/push/test", methods=["POST"])
@login_required
def send_test():
    user_id = session["user_id"]
    sent, failed = push_service.send_to_user(
        user_id,
        title="✓ DailyPlanner",
        body="Reminders are working on this device.",
        url="/checklist",
        tag="cl-test",
    )
    return jsonify({"success": True, "sent": sent, "failed": failed})

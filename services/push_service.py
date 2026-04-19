"""
Web Push delivery helpers.

`send_to_user(user_id, ...)` fetches every active push_subscription row
for the user and sends the payload to each via pywebpush. Expired or
gone subscriptions (HTTP 404/410 from the push service) are marked
inactive so we stop retrying them.

VAPID keys are read from the environment:
    VAPID_PRIVATE_KEY  – PEM-encoded EC private key (one line with \\n)
    VAPID_PUBLIC_KEY   – base64url-encoded uncompressed public key
    VAPID_SUBJECT      – mailto:you@example.com  (required by the spec)

Generate a keypair once with `python scripts/generate_vapid_keys.py`.
"""
import json
import logging
import os

from supabase_client import get, update

logger = logging.getLogger(__name__)


def _vapid_claims():
    # env var present-but-empty should still fall back, not crash py_vapid
    # with "Missing 'sub' from claims".
    subject = (os.environ.get("VAPID_SUBJECT") or "").strip()
    if not subject:
        subject = "mailto:admin@example.com"
    elif not subject.startswith(("mailto:", "http:", "https:")):
        # Accept a bare email by upgrading it to a mailto: URI.
        subject = f"mailto:{subject}"
    return {"sub": subject}


def _private_key():
    return os.environ.get("VAPID_PRIVATE_KEY", "")


def _active_subscriptions(user_id):
    return get(
        "push_subscriptions",
        {"user_id": f"eq.{user_id}", "is_active": "eq.true"},
    ) or []


def _deactivate(endpoint):
    try:
        update(
            "push_subscriptions",
            params={"endpoint": f"eq.{endpoint}"},
            json={"is_active": False},
        )
    except Exception:
        logger.exception("Failed to deactivate push subscription")


def send_to_user(user_id, title, body, url="/checklist", tag=None, icon=None):
    """Return (sent_count, failed_count)."""
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.error("pywebpush is not installed — skipping push send")
        return 0, 0

    private_key = _private_key()
    if not private_key:
        logger.warning("VAPID_PRIVATE_KEY not set — skipping push send")
        return 0, 0

    subs = _active_subscriptions(user_id)
    if not subs:
        return 0, 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or "dailyplanner",
        "icon": icon or "/static/icons/icon.svg",
    })

    claims = _vapid_claims()
    sent = 0
    failed = 0

    for sub in subs:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(claims),
                ttl=3600,
                headers={"Urgency": "high"},
            )
            sent += 1
        except WebPushException as e:
            failed += 1
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                # Subscription is gone (user uninstalled, cleared data, …).
                _deactivate(sub["endpoint"])
                logger.info("Push subscription %s deactivated (HTTP %s)", sub["endpoint"][:40], status)
            else:
                logger.warning("Push send failed (HTTP %s) for %s", status, sub["endpoint"][:40])
        except Exception:
            failed += 1
            logger.exception("Push send raised unexpectedly")

    return sent, failed

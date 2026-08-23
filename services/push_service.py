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

from services import loud

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
    """Live subscriptions for this user.

    NONE is worth a warning rather than a shrug. A user with no active
    subscription receives nothing, silently, forever — and the browser goes
    on reporting "notifications are on", because the two sides drift apart
    the moment a send returns 410. That is very likely why this household's
    checklist reminders stopped arriving in April and nobody found out until
    August.
    """
    rows = get(
        "push_subscriptions",
        {"user_id": f"eq.{user_id}", "is_active": "eq.true"},
    ) or []
    if not rows:
        # Distinguished from "never subscribed": if there ARE rows for this
        # user and all of them are inactive, something expired them and the
        # user still thinks push is on.
        try:
            any_rows = get("push_subscriptions",
                           {"user_id": f"eq.{user_id}", "select": "endpoint",
                            "limit": "1"}) or []
        except Exception:
            any_rows = []
        if any_rows:
            loud.bailed("web push", "every subscription for this user is "
                                    "INACTIVE — they believe push is on and "
                                    "will receive nothing",
                        user_id=user_id)
        else:
            loud.bailed("web push", "no subscription at all", user_id=user_id)
    return rows


def _deactivate(endpoint):
    try:
        update(
            "push_subscriptions",
            params={"endpoint": f"eq.{endpoint}"},
            json={"is_active": False},
        )
    except Exception:
        logger.exception("Failed to deactivate push subscription")


def send_to_user(user_id, title, body, url="/checklist", tag=None, icon=None,
                 extra=None, urgency="high"):
    """Return (sent_count, failed_count).

    `extra` is merged into the payload and reaches the service worker as-is.
    It exists for AMBIENT notifications — a pinned day summary that refreshes
    itself must not buzz the phone every time it updates, so it needs to send
    {"silent": True, "renotify": False, "vibrate": []}. Without a channel like
    this the service worker's alert defaults apply to everything, and a status
    display becomes an interruption.

    `urgency` is the Web Push header, not a notification property. "low" tells
    the push service it may batch and delay delivery to save the device's
    battery, which is the correct trade for a status update and the wrong one
    for a reminder.
    """
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

    body_payload = {
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or "dailyplanner",
        "icon": icon or "/static/icons/icon.svg",
    }
    if extra:
        body_payload.update(extra)
    payload = json.dumps(body_payload)

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
                headers={"Urgency": urgency},
            )
            sent += 1
        except WebPushException as e:
            failed += 1
            status = getattr(e.response, "status_code", None)
            ua = (sub.get("user_agent") or "")
            device = ("Android" if "Android" in ua else
                      "iPhone" if "iPhone" in ua else
                      "iPad" if "iPad" in ua else
                      "Windows" if "Windows" in ua else "device")
            if status in (404, 410):
                # Subscription is gone (user uninstalled, cleared data, …).
                _deactivate(sub["endpoint"])
                logger.info("Push subscription %s deactivated (HTTP %s)",
                            sub["endpoint"][:40], status)
                # LOUD, because this is the failure that has cost this
                # household months of missed reminders and was visible
                # nowhere. A subscription dying is normal; a subscription
                # dying REPEATEDLY on one device is a diagnosis, and it can
                # only be spotted if each one is recorded where the user
                # looks rather than in a log only the author reads.
                loud.bailed("push delivery",
                            f"{device} subscription rejected and deactivated",
                            status=status, device=device)
            else:
                logger.warning("Push send failed (HTTP %s) for %s",
                               status, sub["endpoint"][:40])
                # A non-410 failure does NOT deactivate, so without this it
                # is invisible forever — the row stays active and simply
                # never delivers.
                body = ""
                try:
                    body = (e.response.text or "")[:120]
                except Exception:
                    pass
                loud.bailed("push delivery",
                            f"{device} send failed (HTTP {status})",
                            status=status, device=device, detail=body)
        except Exception as exc:
            failed += 1
            logger.exception("Push send raised unexpectedly")
            loud.bailed("push delivery", "send raised unexpectedly",
                        error=type(exc).__name__)

    return sent, failed

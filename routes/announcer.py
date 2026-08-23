"""Spoken announcements, stored server-side so they follow you between
devices.

WHY THIS EXISTS. The announcer used to keep everything in localStorage,
which meant a schedule built on the laptop did not exist on the phone —
and the phone is the device that actually matters here, because it is the
one in your pocket with the screen off. Clearing site data wiped it.

WHAT THIS OWNS, and what it deliberately does not:

  * IT OWNS the announcements, the repeating interval and the shared
    label. Those are CONTENT — what gets announced. They belong to the
    person, not to a browser.
  * IT DOES NOT OWN mode (start/pause/stop), the keep-alive checkbox, or
    the "already said this slot" marks. Those are per-device RUNTIME
    state and stay in localStorage. Pausing on the phone must not silence
    the laptop you are sitting at; holding audio open is a battery
    decision belonging to the device making it; and a synced `said` would
    mean the first device to speak silences all the others.

EVERY WRITE IS AN UPSERT on (user_id, client_id), where client_id is the
id the browser already generates. A retry after a flaky connection
therefore cannot create a duplicate, which matters because this is a
phone talking over a mobile connection.
"""
import logging

from flask import Blueprint, current_app, jsonify, request, session

from auth import login_required
from services import loud
from services import announcer_calendar_service as announcer_calendar
from supabase_client import get, post, update

logger = logging.getLogger("daily_plan")
announcer_bp = Blueprint("announcer", __name__)

#: Mirrors REPEATS in static/js/time-announcer.js. A value outside this set
#: would be stored and then silently never match a day, so it is rejected
#: here rather than becoming an announcement that cannot speak.
REPEATS = ("once", "daily", "weekly", "monthly", "yearly", "custom")


def _clean(raw):
    """Validate one announcement from the client into storable columns.

    Returns None when the row could not possibly work, rather than storing
    something that will never fire.
    """
    at = str(raw.get("at") or "")[:5]
    if len(at) != 5 or at[2] != ":":
        return None
    until = str(raw.get("until") or "")[:5] or None
    if until and (len(until) != 5 or until[2] != ":"):
        until = None
    try:
        mins = int(raw.get("mins") or 0)
    except (TypeError, ValueError):
        mins = 0
    mins = max(0, min(720, mins))

    rule = raw.get("repeat")
    if rule not in REPEATS:
        rule = "daily"

    days = []
    for d in (raw.get("days") or []):
        try:
            d = int(d)
        except (TypeError, ValueError):
            continue
        if 0 <= d <= 6 and d not in days:
            days.append(d)

    return {
        "client_id": str(raw.get("id") or "")[:80],
        "at_time": at,
        "until_time": until,
        "every_mins": mins,
        "repeat_rule": rule,
        "days": sorted(days),
        "start_date": str(raw.get("start") or "")[:10] or None,
        "end_date": str(raw.get("end") or "")[:10] or None,
        "say_text": str(raw.get("text") or "")[:120],
        "is_on": raw.get("on") is not False,
    }


def _to_client(row):
    """One stored row in the shape the browser already uses."""
    return {
        "id": row.get("client_id"),
        "at": row.get("at_time"),
        "until": row.get("until_time"),
        "mins": row.get("every_mins") or 0,
        "repeat": row.get("repeat_rule") or "daily",
        "days": row.get("days") or [],
        "start": row.get("start_date"),
        "end": row.get("end_date"),
        "text": row.get("say_text") or "",
        "on": row.get("is_on") is not False,
    }


@announcer_bp.route("/api/announcer/state", methods=["GET"])
@login_required
def announcer_state():
    """Everything that syncs, in one request."""
    user_id = session["user_id"]
    try:
        items = get("announcer_items", {
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "order": "at_time.asc",
        }) or []
        rows = get("announcer_settings", {
            "user_id": f"eq.{user_id}", "limit": "1",
        }) or []
    except Exception:
        # The panel keeps working from its local cache, so this is a
        # degraded read rather than an outage — but it must not be silent.
        loud.bailed("announcer sync", "could not read the stored schedule")
        logger.warning("announcer state read failed", exc_info=True)
        return jsonify({"ok": False}), 503

    s = rows[0] if rows else {}
    return jsonify({
        "ok": True,
        "every": s.get("every_mins", 15),
        "label": s.get("label") or "",
        "items": [_to_client(r) for r in items],
    })


@announcer_bp.route("/api/announcer/items", methods=["POST"])
@login_required
def save_items():
    """Upsert one or more announcements.

    Takes a LIST so the first sync — pushing up whatever the browser
    already had — is one request rather than one per announcement.
    """
    user_id = session["user_id"]
    body = request.get_json(silent=True) or {}
    raw = body.get("items")
    if not isinstance(raw, list):
        raw = [body]

    rows = []
    for r in raw:
        c = _clean(r)
        if c and c["client_id"]:
            c["user_id"] = user_id
            c["is_deleted"] = False
            rows.append(c)
    if not rows:
        return jsonify({"ok": True, "saved": 0})

    # What the calendar mirror already knows about, so an update replaces
    # its event instead of leaving a second one behind.
    known = {}
    try:
        for r in get("announcer_items", params={
                "user_id": f"eq.{user_id}",
                "select": "client_id,google_event_id",
                "limit": "200"}) or []:
            known[r.get("client_id")] = r.get("google_event_id")
    except Exception:
        known = {}       # column arrives with MIGRATION_ANNOUNCER_DELIVERY.sql

    try:
        post("announcer_items?on_conflict=user_id,client_id", rows,
             prefer="resolution=merge-duplicates,return=minimal")
    except Exception:
        logger.warning("announcer item save failed", exc_info=True)
        return jsonify({
            "ok": False,
            "error": "Could not save. If this is new, "
                     "MIGRATION_ANNOUNCER_SYNC.sql may not have been run yet.",
        }), 500
    # ── AND MIRROR EACH ONE INTO GOOGLE CALENDAR ──────────────────────
    # A calendar popup is the only alert on Android that is not deferred
    # by Doze — see services/announcer_calendar_service. Off the request
    # thread: saving must never wait on Google, and a household that never
    # linked Calendar must not notice this exists.
    for c in rows:
        cid = c.get("client_id")
        try:
            announcer_calendar.sync_async(
                user_id, cid, {**c, "google_event_id": known.get(cid)},
                old_event_id=known.get(cid),
                remove=(c.get("is_on") is False))
        except Exception:
            logger.debug("announcer: calendar mirror not started for %s", cid,
                         exc_info=True)

    return jsonify({"ok": True, "saved": len(rows)})


@announcer_bp.route("/api/announcer/items/<client_id>", methods=["DELETE"])
@login_required
def delete_item(client_id):
    """SOFT delete, like everything else here — it stops speaking and stays
    recoverable."""
    user_id = session["user_id"]

    # Read the mirror's id BEFORE the soft delete, or the calendar keeps
    # ringing for an announcement the user has removed — which is the
    # worst possible way for a mirror to fail.
    old_event = None
    try:
        rows = get("announcer_items", params={
            "user_id": f"eq.{user_id}",
            "client_id": f"eq.{client_id}",
            "select": "google_event_id",
            "limit": "1",
        }) or []
        old_event = (rows[0] or {}).get("google_event_id") if rows else None
    except Exception:
        old_event = None

    try:
        # update(table, FILTERS, PAYLOAD) — filters first. Getting this
        # round the wrong way raises a ValueError that the except below
        # would have turned into a plausible-sounding 500.
        update("announcer_items", {
            "user_id": f"eq.{user_id}",
            "client_id": f"eq.{client_id}",
        }, {"is_deleted": True})
    except Exception:
        logger.warning("announcer delete failed for %s", client_id,
                       exc_info=True)

    if old_event:
        try:
            announcer_calendar.sync_async(user_id, client_id, {},
                                          old_event_id=old_event, remove=True)
        except Exception:
            logger.debug("announcer: calendar removal not started for %s",
                         client_id, exc_info=True)
        return jsonify({"ok": False}), 500
    return jsonify({"ok": True})


#: Rendered speech, keyed by the exact text. Announcements repeat — the
#: same words at the same minute every day — so a small cache turns most
#: requests into a memory read. Bounded, because this is a personal app and
#: an unbounded cache in a long-lived worker is a slow leak.
_SAY_CACHE = {}
_SAY_CACHE_MAX = 200


@announcer_bp.route("/api/announcer/say", methods=["GET"])
def say():
    """AUTH CHECKED BY HAND, so a signed-out request gets 401 and not HTML.

    @login_required answers with a 302 to the login PAGE. This URL is the
    `src` of an <audio> element, and fetch() follows redirects — so a
    lapsed session arrived at the browser as a cheerful 200 of text/html,
    which a media element cannot decode (NotSupportedError) and which a
    cache will happily store under the announcement's URL forever.

    Still requires a session: this renders arbitrary text to speech and
    must never be an open proxy.
    """
    if not session.get("user_id"):
        return jsonify({"error": "not signed in"}), 401
    return _say_audio()


def _say_audio():
    """Return the announcement text as AUDIO.

    WHY THIS EXISTS. Android Chrome refuses speechSynthesis while the page
    is hidden. Measured on 2026-08-23: a locked Android played the chime —
    so the page was awake and media playback was permitted — and spoke
    nothing at all. iPhone spoke fine in the same state.

    Media playback IS allowed in the background on every platform here.
    So the words have to arrive as audio rather than as a speech call, and
    the browser plays them through the same element the chime uses.

    The client PREFETCHES this before a slot arrives, so the sound at fire
    time needs no network and works offline once cached.
    """
    text = (request.args.get("text") or "").strip()[:300]
    if not text:
        return jsonify({"error": "no text"}), 400

    key = text
    if key in _SAY_CACHE:
        audio = _SAY_CACHE[key]
    else:
        try:
            from gtts import gTTS
        except Exception:
            # Not installed: the client falls back to speechSynthesis,
            # which still works whenever the page is visible.
            return jsonify({"error": "tts unavailable"}), 503
        try:
            import io
            buf = io.BytesIO()
            # tld='co.in' gives an Indian English voice, which is what this
            # household actually speaks.
            gTTS(text, lang="en", tld="co.in").write_to_fp(buf)
            audio = buf.getvalue()
        except Exception:
            # An unofficial endpoint, so a failure is expected occasionally
            # and must not look like an application error.
            loud.bailed("announcer speech", "could not render audio")
            logger.warning("gTTS failed", exc_info=True)
            return jsonify({"error": "tts failed"}), 503
        if len(_SAY_CACHE) >= _SAY_CACHE_MAX:
            _SAY_CACHE.clear()
        _SAY_CACHE[key] = audio

    resp = current_app.response_class(audio, mimetype="audio/mpeg")
    # Cacheable by the browser and the service worker: the same words
    # always sound the same, so a re-fetch is pure waste.
    resp.headers["Cache-Control"] = "private, max-age=604800"
    return resp


@announcer_bp.route("/api/announcer/settings", methods=["POST"])
@login_required
def save_settings():
    """The repeating interval and the shared label."""
    user_id = session["user_id"]
    body = request.get_json(silent=True) or {}
    try:
        every = int(body.get("every", 15))
    except (TypeError, ValueError):
        every = 15
    row = {
        "user_id": user_id,
        "every_mins": max(0, min(720, every)),
        "label": str(body.get("label") or "")[:60],
    }
    try:
        post("announcer_settings?on_conflict=user_id", row,
             prefer="resolution=merge-duplicates,return=minimal")
    except Exception:
        logger.warning("announcer settings save failed", exc_info=True)
        return jsonify({"ok": False}), 500
    return jsonify({"ok": True})

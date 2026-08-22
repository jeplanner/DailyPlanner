"""Record every sign-in, and work out where it came from.

WHY THIS EXISTS
---------------
`users.last_login_at` was the only trace of a sign-in, and each login
overwrote it. That answers "when was the last time" and nothing else. The
question a login history is actually for is "was that me?", and answering it
needs the ones before the last one, and where they came from.

THREE THINGS THAT KEEP IT FROM HURTING
--------------------------------------
1. IT NEVER BLOCKS THE LOGIN. The write and the geolocation lookup happen on
   a background thread. A slow or dead geo provider must not add a second to
   signing in, and a Supabase hiccup must not stop someone getting into their
   own planner.
2. IT NEVER RAISES INTO THE CALLER. Every failure is logged and swallowed.
   The worst outcome is a missing history row, which is strictly better than
   a failed login.
3. THE LOOKUP IS CACHED PER IP, in-process. A household signs in from the
   same few addresses; without the cache every login would spend a network
   round trip rediscovering the same city.

ON THE ADDRESS ITSELF
---------------------
Behind Render (and any proxy) `request.remote_addr` is the PROXY, not the
client — the real address is the first entry of X-Forwarded-For. That header
is client-settable and therefore spoofable, so it is trusted only for
"roughly where was this", never for anything security-critical.
"""

import ipaddress
import json
import logging
import threading
import urllib.request

logger = logging.getLogger("daily_plan")

#: ip -> resolved location dict. Bounded so a stream of distinct addresses
#: cannot grow it without limit.
_GEO_CACHE = {}
_GEO_CACHE_MAX = 512
_GEO_LOCK = threading.Lock()

#: Free, no-key, and explicitly fine for low volume. Chosen over a paid
#: provider because the alternative to a best-effort city is no city at all.
_GEO_URL = "http://ip-api.com/json/{ip}?fields=status,message,city,regionName,country,countryCode,timezone"
_GEO_TIMEOUT = 4.0


def client_ip(request):
    """The client's address, preferring the proxy's forwarded-for header.

    Returns None rather than a useless value when nothing is available, so
    callers can record 'unknown' honestly instead of storing a placeholder
    that later looks like real data.
    """
    fwd = (request.headers.get("X-Forwarded-For") or "").strip()
    if fwd:
        # The left-most entry is the original client; everything after it is
        # the chain of proxies that handled the request.
        first = fwd.split(",")[0].strip()
        if first:
            return first
    return (request.remote_addr or "").strip() or None


def _is_private(ip):
    """True for loopback, LAN and link-local addresses.

    These are worth detecting rather than sending to a geo provider: the
    lookup would fail anyway, and 'on this network' is a better thing to show
    than 'could not determine'.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_unspecified)


def _blank(status):
    return {"city": None, "region": None, "country": None,
            "country_code": None, "timezone": None, "location_status": status}


def locate(ip):
    """Best-effort geolocation for an IP. Never raises.

    `location_status` carries WHY a row has no city, so the page can say
    'on this network' or 'could not determine' rather than showing an empty
    cell that reads as a bug.
    """
    if not ip:
        return _blank("unknown")
    if _is_private(ip):
        return _blank("private")

    with _GEO_LOCK:
        hit = _GEO_CACHE.get(ip)
    if hit is not None:
        return dict(hit)

    result = _blank("failed")
    try:
        req = urllib.request.Request(
            _GEO_URL.format(ip=ip),
            headers={"User-Agent": "DailyPlanner/1.0 (login history)"})
        with urllib.request.urlopen(req, timeout=_GEO_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        if (data.get("status") or "").lower() == "success":
            result = {
                "city": data.get("city") or None,
                "region": data.get("regionName") or None,
                "country": data.get("country") or None,
                "country_code": data.get("countryCode") or None,
                "timezone": data.get("timezone") or None,
                "location_status": "ok",
            }
        else:
            logger.info("geo lookup declined for %s: %s", ip, data.get("message"))
    except Exception as exc:
        logger.info("geo lookup failed for %s: %s", ip, exc)

    with _GEO_LOCK:
        if len(_GEO_CACHE) >= _GEO_CACHE_MAX:
            _GEO_CACHE.clear()          # crude, and fine: it is only a cache
        _GEO_CACHE[ip] = dict(result)
    return result


def _write(user_id, ip, user_agent, outcome):
    from supabase_client import post
    row = {"user_id": user_id, "ip": ip,
           "user_agent": (user_agent or "")[:500], "outcome": outcome}
    row.update(locate(ip))
    try:
        post("login_events", row, prefer="return=minimal")
    except Exception as exc:
        # A missing table means the migration has not been run. That is worth
        # one clear line naming the file, not a stack trace on every login.
        text = str(exc)
        if "login_events" in text or "does not exist" in text or "schema cache" in text:
            logger.warning("login history not recorded — run "
                           "MIGRATION_LOGIN_HISTORY.sql (%s)", text[:120])
        else:
            logger.warning("login history write failed: %s", text[:200])


def record(user_id, request, outcome="success"):
    """Record a sign-in attempt. Returns immediately; the work is threaded.

    Failed attempts are recorded too — a history that shows only successes
    cannot show someone trying to get in, which is half of what the page is
    for.
    """
    try:
        ip = client_ip(request)
        ua = request.headers.get("User-Agent") or ""
    except Exception:
        return
    threading.Thread(target=_write, args=(user_id, ip, ua, outcome),
                     name="login-history", daemon=True).start()


import os
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}
logger = logging.getLogger("daily_plan")

# ─────────────────────────────────────────────────────────────────
# Connection-pooled session — reuses TCP connections across requests.
#
# We mount an HTTPAdapter with a urllib3 Retry policy that handles the
# common "Connection reset by peer" (errno 104) that happens when
# Supabase (or an intermediate LB) closes a pooled keep-alive socket
# while the Flask worker was idle. `connect` retries only kick in when
# the request never left the box, so they are safe for every HTTP
# method including POST/PATCH/DELETE — no duplicate writes possible.
#
# `status_forcelist` covers transient 5xx from Supabase itself. Those
# are retried only for idempotent methods (GET/HEAD/OPTIONS/PUT/DELETE)
# to avoid accidentally double-inserting on a POST timeout.
# ─────────────────────────────────────────────────────────────────
_session = requests.Session()
_session.headers.update(HEADERS)

_retry = Retry(
    total=3,
    connect=3,          # retry on connection establishment errors
    read=1,             # read errors only retried once (not safe for POST)
    status=2,           # retry on status_forcelist responses
    backoff_factor=0.4, # 0.4s, 0.8s, 1.6s between retries
    status_forcelist=(502, 503, 504),
    allowed_methods=frozenset(["GET", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH"]),
    raise_on_status=False,
)
_adapter = HTTPAdapter(
    max_retries=_retry,
    pool_connections=10,
    pool_maxsize=20,
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# (connect, read) timeout — tighter connect so a bad DNS / SYN hang fails
# fast, generous read so large list queries finish.
_DEFAULT_TIMEOUT = (5, 15)


def _request(method, url, **kwargs):
    """Invoke _session.<method> with one application-level retry on
    ConnectionError. The urllib3 Retry adapter already handles the
    common case; this wrapper is a safety net for edge cases where the
    exception surfaces above urllib3 (e.g. a pooled socket that gets
    reset between the adapter's retry attempts).
    """
    kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
    try:
        return _session.request(method, url, **kwargs)
    except requests.exceptions.ConnectionError as e:
        logger.warning(
            "SUPABASE %s connection reset, retrying once: %s", method, e
        )
        # Drop the (possibly poisoned) pool so the retry uses a fresh socket
        try:
            _session.close()
        except Exception:
            pass
        return _session.request(method, url, **kwargs)


def _strip_eq(value):
    if isinstance(value, str) and value.startswith("eq."):
        return value[3:]
    return value


def get(path, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"

    # 🔍 Log intent
    logger.debug("SUPABASE GET → %s | params=%s", url, params)

    r = _request("GET", url, params=params)

    # 🔑 Log final URL (THIS IS WHAT SUPABASE SEES)
    logger.debug("SUPABASE FINAL URL → %s", r.url)

    if not r.ok:
        # 🔥 Log full error context
        logger.error("SUPABASE ERROR %s", r.status_code)
        logger.error("SUPABASE URL → %s", r.url)
        logger.error("SUPABASE RESPONSE → %s", r.text)

        r.raise_for_status()

    return r.json()
def post(path, data, prefer="return=representation"):
    headers = HEADERS.copy()

    # ✅ Always return inserted rows by default
    if prefer:
        if "return=" not in prefer:
            prefer = f"{prefer},return=representation"
        headers["Prefer"] = prefer

    # 🔒 SAFETY: strip eq. from POST payload
    if isinstance(data, dict):
        data = {k: _strip_eq(v) for k, v in data.items()}
    elif isinstance(data, list):
        data = [
            {k: _strip_eq(v) for k, v in row.items()}
            for row in data
        ]

    logger.debug("SUPABASE Post → %s | params=%s", path, data)

    def _do_post(payload):
        return _request(
            "POST",
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=headers,
            json=payload,
        )

    r = _do_post(data)

    # Resilience: if Supabase complains that a column doesn't exist in the
    # schema cache (PGRST204), strip that column from the payload and retry
    # once. This keeps inserts working when a migration is pending — the
    # row just misses the new field — instead of 500-ing the whole request.
    if not r.ok and r.status_code == 400 and isinstance(data, dict):
        try:
            err = r.json()
        except Exception:
            err = {}
        if err.get("code") == "PGRST204":
            msg = err.get("message") or ""
            import re
            m = re.search(r"'([^']+)'\s+column", msg)
            missing = m.group(1) if m else None
            if missing and missing in data:
                logger.warning(
                    "SUPABASE POST: '%s.%s' missing in schema cache — retrying without it. "
                    "Run: ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s ...;",
                    path, missing, path, missing
                )
                retry_payload = {k: v for k, v in data.items() if k != missing}
                r = _do_post(retry_payload)

    if not r.ok:
        logger.error("SUPABASE POST ERROR %s on %s", r.status_code, path)
        logger.error("SUPABASE POST URL → %s", r.url)
        logger.error("SUPABASE POST PAYLOAD → %s", data)
        logger.error("SUPABASE POST RESPONSE → %s", r.text)
        r.raise_for_status()

    if r.text:
        return r.json()

    return []
def delete(path, params):
    r = _request(
        "DELETE",
        f"{SUPABASE_URL}/rest/v1/{path}",
        params=params,
    )
    if not r.ok:
        logger.error("SUPABASE DELETE ERROR %s on %s", r.status_code, path)
        logger.error("SUPABASE DELETE RESPONSE → %s", r.text)
        r.raise_for_status()
def update(table, params, json):
    """
    Update rows in a Supabase table.
    params example: {"id": "eq.123"}
    json example: {"is_done": True}
    """
    # 🛑 Guard: params must already be operator-based
    for k, v in params.items():
        if not isinstance(v, str) or "." not in v:
            raise ValueError(
                f"Invalid filter for Supabase: {k}={v}. "
                "Filters must include operators like eq., gt., lt."
            )
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    # 🔍 Log intent
    logger.debug("SUPABASE UPDATE → %s | params=%s", url, params)
    response = _request(
        "PATCH",
        url,
        params=params,
        json=json,
    )
    # 🔑 Log final URL (THIS IS WHAT SUPABASE SEES)
    logger.debug("SUPABASE FINAL URL → %s", response.url)
    if not response.ok:
        logger.error("SUPABASE RESPONSE → %s", response.text)
        raise Exception(
            f"UPDATE failed {response.status_code}: {response.text}",
        )

    return response.json() if response.text else None


def get_for_user(path, user_id, params=None):
    params = params or {}
    params["user_id"] = f"eq.{user_id}"
    return get(path, params)
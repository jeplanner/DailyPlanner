"""Random thoughts: a ~5 minute spoken summary of each answer, stored as MP3.

One file per question, built for recall rather than just listening:

    "Question. <the question>. Pause and recall the answer before it plays."
    [ five seconds of silence ]
    "Here is the answer." <the spoken summary, ~600 words>

* The SCRIPT is written by the same AI providers as the answers, with
  instructions for the ear: no code, tables or diagrams read out, short
  sentences, one worked example. Without a provider the answer itself is
  cleaned for speech and trimmed, so a question still gets audio.
* The VOICE is gTTS (the announcer's engine, Indian English).
* The SILENCE is real MP3 frames, copied from gTTS's own frame header with
  an empty body, so the pause survives a locked phone - a client-side
  timer between two files would be throttled exactly then.
* Files go in the private `thought-audio` bucket (created by
  MIGRATION_PREP_THOUGHTS.sql) and are served to their owner only.
* prep_thoughts.audio holds {status, key, hash, seconds, words, error, at}.
  `hash` is of the question + answer, so an edited or rewritten answer
  makes the audio stale and it is rebuilt; an unchanged one never is.

WHICH QUESTIONS GET AUDIO. Only ones you ask for (the button) or mark as
studied - the ones that come back for revision. Making it for every
question opened would put ~350 MB per shelf of shipped answers into a free
Supabase project's 1 GB of storage. A rewrite or edit re-records only a
question that already had audio (start_if_wanted).

Builds run in a background thread, one at a time per process: gTTS is an
unofficial endpoint and a burst of requests would get throttled.
"""
import hashlib
import io
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone

import requests

from services import thoughts_service as ts
from supabase_client import SUPABASE_URL, get, update

logger = logging.getLogger(__name__)

BUCKET = os.getenv("THOUGHTS_AUDIO_BUCKET", "thought-audio")
RECALL_PAUSE = 5            # seconds of silence between the question and the answer
# gTTS speaks ~120 words a minute (measured: 889 words ran 7m25s), so five
# minutes is ~600 words. Models overshoot, hence the hard cap.
TARGET_WORDS = (520, 600)
MAX_WORDS = 640
RETRY_WAIT = 20
_lock = threading.Semaphore(1)
_busy = set()

SCRIPT_SYSTEM = f"""You turn a written study answer into a SPOKEN summary that \
will be converted to speech and listened to on a walk, as revision. Write \
{TARGET_WORDS[0]} to {TARGET_WORDS[1]} words (about five minutes aloud).
- Plain spoken English: short sentences, no markdown, no bullet symbols, no \
headings, no emoji, no URLs.
- Never read out code, tables, diagrams or formulas symbol by symbol. Say what \
they show in words instead ("the loop keeps the k largest so far").
- Open with the one-sentence answer. Then the key ideas in the order they \
build, each explained simply. Then one concrete worked example walked through \
in words. Then the common mistake or interview trap. End with a three-point \
recap that starts "To recap:".
- Define any technical term the first time you use it.
- Do not mention that this is a summary or a script."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def answer_hash(question, answer):
    return hashlib.sha1(f"{question}\n{answer}".encode("utf-8")).hexdigest()[:16]


def speakable(text):
    """Markdown answer -> plain text a voice can read."""
    t = re.sub(r"```.*?```", " ", text or "", flags=re.S)          # code and diagrams
    t = re.sub(r"^\s*\|.*\|\s*$", " ", t, flags=re.M)               # table rows
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                      # images
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)                   # links -> their text
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", t, flags=re.M)
    t = re.sub(r"[*_~>#|]+", " ", t)
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _trim_words(text, n):
    words = text.split()
    if len(words) <= n:
        return text
    cut = " ".join(words[:n])
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[:end + 1] if end > len(cut) // 2 else cut + "."


def make_script(question, answer):
    """(script, source): source is the model name, or "answer" when no
    provider answered and the answer itself is read."""
    # The answer goes in already stripped of code and diagrams, and capped:
    # Groq's free tier refuses any request over 8,000 tokens a minute, and
    # that counts the reply budget too.
    prompt = ("THE QUESTION:\n" + question + "\n\nTHE WRITTEN ANSWER:\n"
              + _trim_words(speakable(answer), 2600))
    for attempt in range(2):
        if attempt:
            # Usually a per-minute limit that clears in seconds: one wait, then
            # the plain answer rather than no audio at all.
            time.sleep(RETRY_WAIT)
        for fn in ts.PROVIDERS:
            try:
                text, model = fn(prompt, (), system=SCRIPT_SYSTEM, max_tokens=2500)
            except Exception:
                logger.warning("thought audio: %s failed", fn.__name__, exc_info=True)
                continue
            if text and len(text.split()) > 80:
                return _trim_words(speakable(text), MAX_WORDS), model
    return _trim_words(speakable(answer), TARGET_WORDS[1]), "answer"


# MPEG audio, layer III: kbps by bitrate index, sample rates by version.
_BITRATES = {1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
             2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]}
_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def _first_frame(mp3):
    """(offset, version, bitrate index, rate index) of the first layer III frame."""
    for i in range(len(mp3) - 3):
        if mp3[i] == 0xFF and (mp3[i + 1] & 0xE0) == 0xE0:
            ver, layer = (mp3[i + 1] >> 3) & 3, (mp3[i + 1] >> 1) & 3
            br, sr = (mp3[i + 2] >> 4) & 15, (mp3[i + 2] >> 2) & 3
            if ver != 1 and layer == 1 and 0 < br < 15 and sr < 3:
                return i, ver, br, sr
    return None


def kbps_of(mp3):
    f = _first_frame(mp3)
    return _BITRATES[1 if f[1] == 3 else 2][f[2]] if f else 0


def silence_like(mp3, seconds):
    """`seconds` of silent frames in the same format as `mp3`: its header,
    padding bit cleared, and an all-zero body (no side info = no sound)."""
    f = _first_frame(mp3)
    if not f:
        return b""
    i, ver, br, sr = f
    hdr = bytearray(mp3[i:i + 4])
    hdr[2] &= ~0x02
    rate, kbps = _RATES[ver][sr], _BITRATES[1 if ver == 3 else 2][br]
    samples = 1152 if ver == 3 else 576
    flen = (144 if ver == 3 else 72) * kbps * 1000 // rate
    return (bytes(hdr) + bytes(flen - 4)) * int(seconds * rate / samples + 0.5)


def _tts(text):
    from gtts import gTTS
    buf = io.BytesIO()
    # The announcer's voice: Indian English.
    gTTS(text, lang="en", tld="co.in").write_to_fp(buf)
    return buf.getvalue()


def render(question, script):
    """The whole file: question, recall pause, answer."""
    q = _tts(f"Question. {question.rstrip('?. ')}? Pause, and recall the answer before it plays.")
    a = _tts("Here is the answer. " + script)
    return q + silence_like(q, RECALL_PAUSE) + a


def _headers(extra=None):
    key = os.environ.get("SUPABASE_KEY", "")
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    h.update(extra or {})
    return h


def owner_prefix(user_id):
    return f"{user_id}/"


def store(user_id, row_id, h, data):
    key = f"{owner_prefix(user_id)}{row_id}-{h}.mp3"
    r = requests.post(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}",
                      headers=_headers({"Content-Type": "audio/mpeg", "x-upsert": "true",
                                        "Cache-Control": "private, max-age=31536000, immutable"}),
                      data=data, timeout=120)
    if not r.ok:
        raise RuntimeError(f"storage {r.status_code}: {r.text[:200]}")
    return key


_CACHE, _CACHE_MAX = {}, 12


def fetch(key):
    """MP3 bytes, or None. A small cache: iOS asks for a file in many Range
    requests, and each must not be a fresh download from storage."""
    if key in _CACHE:
        return _CACHE[key]
    r = requests.get(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}", headers=_headers(), timeout=60)
    if not r.ok:
        return None
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = r.content
    return r.content


def is_current(row):
    a = row.get("audio") or {}
    return a.get("status") in ("ready", "pending") and a.get("hash") == answer_hash(
        row.get("question") or "", row.get("answer") or "")


def _save(where, audio):
    update(ts.TABLE, params=where, json={"audio": audio})


def build(row_id, user_id, force=False):
    """Make (or remake) one question's audio. Runs in the caller's thread."""
    where = {"id": f"eq.{row_id}", "user_id": f"eq.{user_id}"}
    rows = get(ts.TABLE, params=dict(where, deleted_at="is.null", limit="1",
                                     select="id,parent_id,question,answer,status,audio")) or []
    if not rows:
        return None
    row = rows[0]
    if row.get("parent_id") or row.get("status") != "ready" or not (row.get("answer") or "").strip():
        return None
    a = row.get("audio") or {}
    h = answer_hash(row.get("question") or "", row.get("answer") or "")
    if not force and a.get("status") == "ready" and a.get("hash") == h:
        return a
    try:
        script, source = make_script(row["question"], row["answer"])
        data = render(row["question"], script)
        key = store(user_id, row_id, h, data)
        kb = kbps_of(data) or 64
        out = {"status": "ready", "key": key, "hash": h, "words": len(script.split()),
               "seconds": round(len(data) * 8 / (kb * 1000)), "source": source,
               "error": None, "at": _now()}
    except Exception as exc:
        logger.warning("thought audio: build failed for %s", row_id, exc_info=True)
        msg = str(exc)
        if "gtts" in msg.lower() or "429" in msg:
            msg = "The speech service didn't answer (it limits bursts). Try again in a minute."
        elif "storage" in msg and ("bucket" in msg.lower() or "404" in msg):
            msg = ("The thought-audio storage bucket is missing - run the latest "
                   "MIGRATION_PREP_THOUGHTS.sql in Supabase.")
        out = {"status": "failed", "hash": h, "error": msg[:300], "at": _now()}
    _save(where, out)
    return out


def start(row_id, user_id, force=False):
    """Queue a build in the background. Returns the audio state to show now:
    "pending" when a build was queued, else None (nothing to do)."""
    if row_id in _busy:
        return {"status": "pending"}
    _busy.add(row_id)
    pending = {"status": "pending", "at": _now()}
    try:
        _save({"id": f"eq.{row_id}", "user_id": f"eq.{user_id}"}, pending)
    except Exception:
        _busy.discard(row_id)
        raise

    def run():
        try:
            with _lock:
                build(row_id, user_id, force=force)
        except Exception:
            logger.exception("thought audio: crashed for %s", row_id)
            try:
                _save({"id": f"eq.{row_id}", "user_id": f"eq.{user_id}"},
                      {"status": "failed", "error": "Audio could not be made.", "at": _now()})
            except Exception:
                pass
        finally:
            _busy.discard(row_id)

    threading.Thread(target=run, name=f"thought-audio-{row_id}", daemon=True).start()
    return pending


def start_if_wanted(row_id, user_id):
    """Re-record after an answer changes, or record on being marked studied -
    only for a question that is studied or already had audio."""
    rows = get(ts.TABLE, params={"id": f"eq.{row_id}", "user_id": f"eq.{user_id}",
                                 "select": "id,parent_id,question,answer,status,understood,audio",
                                 "limit": "1"}) or []
    if not rows:
        return None
    r = rows[0]
    if r.get("parent_id") or r.get("status") != "ready" or is_current(r):
        return r.get("audio")
    if not (r.get("understood") or r.get("audio")):
        return None
    return start(row_id, user_id)

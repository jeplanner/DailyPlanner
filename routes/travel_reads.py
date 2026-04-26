"""TravelReads — a curated queue of articles, videos, and podcasts to
consume while travelling.

Endpoints:
    GET  /travel-reads                                  page render
    GET  /api/travel-reads                              list (active)
    POST /api/travel-reads                              add (auto-fetch metadata)
    POST /api/travel-reads/<id>/update                  edit fields
    POST /api/travel-reads/<id>/status                  change status
    POST /api/travel-reads/<id>/archive                 soft delete
    POST /api/travel-reads/<id>/transcript-paste        save user-pasted transcript

Soft-delete only — items the user "removes" set status='archived'
(matching the project's no-hard-delete convention).

Transcription is paste-only: the user captures the transcript on
their own machine (bookmarklet that scrapes YouTube's caption track
and copies it to the clipboard, or YouTube's own "Show transcript"
panel) and pastes it in. Server-side auto-transcription via yt-dlp
was removed because YouTube blocks both caption fetches AND audio
downloads from cloud-host IPs.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import get, post, update
from services.inbox_service import fetch_meta, detect_type

logger = logging.getLogger("daily_plan")
travel_reads_bp = Blueprint("travel_reads", __name__)


VALID_KINDS = {"article", "video", "podcast", "audio", "other"}
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"queued", "in_progress", "done", "archived"}

_MAX_TITLE = 240
_MAX_DESC = 600
_MAX_NOTES = 10000   # ~2000 words — generous room for video summaries


# ─── Helpers ─────────────────────────────────────────────────────


_YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([A-Za-z0-9_-]{6,})"
)


def _youtube_video_id(url: str):
    """Return the YouTube video ID encoded in a URL, or None."""
    m = _YOUTUBE_ID_RE.search(url or "")
    return m.group(1) if m else None


def _normalize_kind(raw: str, url: str) -> str:
    raw = (raw or "").strip().lower()
    if raw in VALID_KINDS:
        return raw
    # Auto-detect if not provided.
    t = detect_type(url or "")
    if t == "video":
        return "video"
    if t == "article":
        return "article"
    if t == "pdf":
        return "article"
    return "article"   # default — most "TravelReads" links are articles


def _source_from_url(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def _thumbnail_for(url: str, kind: str) -> str | None:
    """Best-effort thumbnail. YouTube has predictable URLs; everything
    else falls back to None for now (we could parse og:image later)."""
    yt_id = _youtube_video_id(url)
    if yt_id:
        # hqdefault is 480x360, available for nearly every video.
        return f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
    return None


# ─── Page ────────────────────────────────────────────────────────


@travel_reads_bp.route("/travel-reads", methods=["GET"])
@login_required
def travel_reads_page():
    return render_template(
        "travel_reads.html",
        kinds=sorted(VALID_KINDS),
        priorities=["high", "medium", "low"],
    )


# ─── API: list ───────────────────────────────────────────────────


@travel_reads_bp.route("/api/travel-reads", methods=["GET"])
@login_required
def list_travel_reads():
    user_id = session["user_id"]
    rows = get(
        "travel_reads",
        params={
            "user_id": f"eq.{user_id}",
            "status": "neq.archived",
            "select": (
                "id,url,title,description,thumbnail_url,source,kind,"
                "duration_minutes,priority,status,notes,transcript_note_id,"
                "added_at,started_at,finished_at,updated_at"
            ),
            "order": "status.asc,added_at.desc",
            "limit": "500",
        },
    ) or []

    prio_rank = {"high": 0, "medium": 1, "low": 2}
    status_rank = {"in_progress": 0, "queued": 1, "done": 2}
    rows.sort(key=lambda r: (
        status_rank.get(r.get("status") or "queued", 1),
        prio_rank.get(r.get("priority") or "medium", 1),
        -(r.get("added_at") or "").__hash__(),  # newer first within bucket
    ))

    # Aggregate stats for the header strip.
    queued = [r for r in rows if (r.get("status") or "queued") == "queued"]
    in_progress = [r for r in rows if (r.get("status") or "") == "in_progress"]
    done = [r for r in rows if (r.get("status") or "") == "done"]

    def _sum_minutes(items):
        return sum(int(r.get("duration_minutes") or 0) for r in items)

    return jsonify({
        "items": rows,
        "stats": {
            "queued": len(queued),
            "in_progress": len(in_progress),
            "done": len(done),
            "queued_minutes": _sum_minutes(queued + in_progress),
        },
    })


# ─── API: add ────────────────────────────────────────────────────


@travel_reads_bp.route("/api/travel-reads", methods=["POST"])
@login_required
def add_travel_read():
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    url = (data.get("url") or "").strip()
    if not url or not re.match(r"^https?://", url):
        return jsonify({"error": "Valid URL required (http/https)"}), 400

    # User-supplied overrides; otherwise auto-fetch.
    title = (data.get("title") or "").strip()[:_MAX_TITLE]
    description = (data.get("description") or "").strip()[:_MAX_DESC]
    if not title or not description:
        meta = fetch_meta(url)
        if not title:
            title = (meta.get("title") or url)[:_MAX_TITLE]
        if not description:
            description = (meta.get("description") or "")[:_MAX_DESC]

    kind = _normalize_kind(data.get("kind"), url)
    priority = (data.get("priority") or "medium").strip().lower()
    if priority not in VALID_PRIORITIES:
        priority = "medium"

    duration_raw = data.get("duration_minutes")
    duration = None
    if duration_raw not in (None, ""):
        try:
            duration = max(0, int(duration_raw))
        except (TypeError, ValueError):
            duration = None

    payload = {
        "user_id": user_id,
        "url": url,
        "title": title,
        "description": description,
        "thumbnail_url": _thumbnail_for(url, kind),
        "source": _source_from_url(url),
        "kind": kind,
        "duration_minutes": duration,
        "priority": priority,
        "status": "queued",
        "notes": (data.get("notes") or "").strip()[:_MAX_NOTES] or None,
    }

    try:
        rows = post("travel_reads", payload)
    except Exception as e:
        logger.error("travel_reads insert failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502

    return jsonify({"ok": True, "item": rows[0] if rows else None})


# ─── API: update fields ──────────────────────────────────────────


@travel_reads_bp.route("/api/travel-reads/<read_id>/update", methods=["POST"])
@login_required
def update_travel_read(read_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}

    patch = {}
    if "title" in data:
        v = (data.get("title") or "").strip()
        if not v:
            return jsonify({"error": "Title required"}), 400
        patch["title"] = v[:_MAX_TITLE]
    if "description" in data:
        patch["description"] = (data.get("description") or "").strip()[:_MAX_DESC] or None
    if "kind" in data:
        v = (data.get("kind") or "").strip().lower()
        patch["kind"] = v if v in VALID_KINDS else "article"
    if "priority" in data:
        v = (data.get("priority") or "").strip().lower()
        patch["priority"] = v if v in VALID_PRIORITIES else "medium"
    if "duration_minutes" in data:
        v = data.get("duration_minutes")
        if v in (None, ""):
            patch["duration_minutes"] = None
        else:
            try:
                patch["duration_minutes"] = max(0, int(v))
            except (TypeError, ValueError):
                patch["duration_minutes"] = None
    if "notes" in data:
        patch["notes"] = (data.get("notes") or "").strip()[:_MAX_NOTES] or None

    if not patch:
        return jsonify({"ok": True, "noop": True})

    try:
        update(
            "travel_reads",
            params={"id": f"eq.{read_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("travel_reads update failed: %s", e)
        return jsonify({"error": "Couldn't save — please try again."}), 502

    return jsonify({"ok": True, "patch": patch})


# ─── API: status ─────────────────────────────────────────────────


@travel_reads_bp.route("/api/travel-reads/<read_id>/status", methods=["POST"])
@login_required
def set_status(read_id):
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    new_status = (data.get("status") or "").strip().lower()
    if new_status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400

    patch = {"status": new_status}
    now_iso = datetime.utcnow().isoformat()
    if new_status == "in_progress":
        patch["started_at"] = now_iso
    if new_status == "done":
        patch["finished_at"] = now_iso
    if new_status == "archived":
        patch["archived_at"] = now_iso

    try:
        update(
            "travel_reads",
            params={"id": f"eq.{read_id}", "user_id": f"eq.{user_id}"},
            json=patch,
        )
    except Exception as e:
        logger.error("travel_reads status update failed: %s", e)
        return jsonify({"error": "Couldn't update — please try again."}), 502

    return jsonify({"ok": True, "status": new_status})


@travel_reads_bp.route("/api/travel-reads/<read_id>/archive", methods=["POST"])
@login_required
def archive_travel_read(read_id):
    """Soft-delete shorthand — sets status='archived'."""
    user_id = session["user_id"]
    try:
        update(
            "travel_reads",
            params={"id": f"eq.{read_id}", "user_id": f"eq.{user_id}"},
            json={"status": "archived", "archived_at": datetime.utcnow().isoformat()},
        )
    except Exception as e:
        logger.error("travel_reads archive failed: %s", e)
        return jsonify({"error": "Couldn't remove — please try again."}), 502

    return jsonify({"ok": True})


# ─── API: transcript-paste ──────────────────────────────────────


_MAX_PASTE_CHARS = 500_000   # ~250 pages — generous, but bounded


def _save_transcript_note(user_id, item, text: str, source_label: str) -> str:
    """Persist `text` as a scribble note in the 'Transcripts' notebook
    and link it back to the travel_reads row. Returns the note id."""
    title = (item.get("title") or "Transcript").strip()[:200]
    note_payload = {
        "user_id": user_id,
        "title": f"📝 {title}",
        "content": (
            f"_{source_label} from [{item.get('url')}]({item.get('url')})_\n\n"
            + text
        ),
        "notebook": "Transcripts",
        "is_pinned": False,
    }
    note_rows = post("scribble_notes", note_payload)
    note_id = note_rows[0]["id"] if note_rows else None
    if not note_id:
        raise RuntimeError("Save returned no id.")
    try:
        update(
            "travel_reads",
            params={"id": f"eq.{item['id']}", "user_id": f"eq.{user_id}"},
            json={"transcript_note_id": note_id},
        )
    except Exception as e:
        logger.warning("link transcript_note_id failed: %s", e)
        # Note is saved either way; don't fail the request.
    return note_id


def _load_item(user_id: str, read_id: str):
    rows = get(
        "travel_reads",
        params={
            "id": f"eq.{read_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,url,title,kind,transcript_note_id",
            "limit": "1",
        },
    ) or []
    return rows[0] if rows else None


@travel_reads_bp.route("/api/travel-reads/<read_id>/transcript-paste", methods=["POST"])
@login_required
def transcript_paste(read_id):
    """Save a transcript the user pasted in (option C — bypasses cloud-IP
    blocks on YouTube's caption endpoint by using the user's residential
    IP via a browser bookmarklet, or by copy-pasting from YouTube's
    'Show transcript' panel).

    Body: {"text": "..."}
    """
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Paste some transcript text first."}), 400
    if len(text) > _MAX_PASTE_CHARS:
        return jsonify({
            "error": f"Transcript too long — keep it under {_MAX_PASTE_CHARS:,} chars.",
        }), 413

    item = _load_item(user_id, read_id)
    if not item:
        return jsonify({"error": "Not found"}), 404
    if item.get("transcript_note_id"):
        return jsonify({
            "ok": True,
            "already_transcribed": True,
            "note_id": item["transcript_note_id"],
        })

    try:
        note_id = _save_transcript_note(user_id, item, text, "Pasted transcript")
    except Exception as e:
        logger.error("paste transcript save failed: %s", e)
        return jsonify({"error": "Couldn't save transcript note."}), 502

    snippet = text[:280] + ("…" if len(text) > 280 else "")
    return jsonify({
        "ok": True,
        "note_id": note_id,
        "note_url": f"/notes/scribble/{note_id}",
        "char_count": len(text),
        "snippet": snippet,
    })

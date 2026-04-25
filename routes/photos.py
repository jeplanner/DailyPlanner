"""
Photos page — general-purpose photo album.

Mirrors the prayer-photos pattern but on its own bucket and metadata
table so the two surfaces stay logically distinct. Files in Supabase
Storage bucket `user-photos`; metadata in `user_photos` table (see
MIGRATION_USER_PHOTOS.sql for setup).

Render's filesystem is ephemeral so user uploads MUST go to Supabase —
we can't write into static/. Public bucket = direct CDN URLs, no
signed-URL bookkeeping.
"""
import logging
import mimetypes
import uuid

import requests
from flask import Blueprint, jsonify, render_template, request, session

from auth import login_required
from supabase_client import SUPABASE_URL, SUPABASE_KEY, get, post, update

logger = logging.getLogger("daily_plan")

photos_bp = Blueprint("photos", __name__)

_BUCKET = "user-photos"
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_ALLOWED_MIMES = {
    "image/jpeg": "jpg",
    "image/jpg":  "jpg",
    "image/png":  "png",
    "image/webp": "webp",
    "image/gif":  "gif",
}


def _public_storage_url(storage_key: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{_BUCKET}/{storage_key}"


def _list_photos(user_id: str) -> list[dict]:
    try:
        rows = get(
            "user_photos",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "select": "id,storage_key,display_name,created_at",
                "order": "created_at.desc",
                "limit": "500",
            },
        ) or []
    except Exception as e:
        logger.warning("user_photos fetch failed (migration missing?): %s", e)
        return []
    return [
        {
            "id": r["id"],
            "name": r.get("display_name") or "Photo",
            "img":  _public_storage_url(r["storage_key"]),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]


@photos_bp.route("/photos")
@login_required
def photos_page():
    user_id = session["user_id"]
    return render_template("photos.html", photos=_list_photos(user_id))


@photos_bp.route("/photos/upload", methods=["POST"])
@login_required
def upload_photo():
    user_id = session["user_id"]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    mime = (f.mimetype or "").lower()
    if mime not in _ALLOWED_MIMES:
        guessed, _ = mimetypes.guess_type(f.filename)
        if guessed and guessed.lower() in _ALLOWED_MIMES:
            mime = guessed.lower()
        else:
            return jsonify({"error": "Only JPG, PNG, WebP, or GIF are allowed."}), 400
    ext = _ALLOWED_MIMES[mime]

    f.stream.seek(0, 2)
    size = f.stream.tell()
    f.stream.seek(0)
    if size <= 0:
        return jsonify({"error": "Empty file"}), 400
    if size > _MAX_UPLOAD_BYTES:
        return jsonify({"error": "File too large (max 5 MB)."}), 400

    storage_key = f"{user_id}/{uuid.uuid4().hex}.{ext}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{_BUCKET}/{storage_key}"
    try:
        r = requests.post(
            upload_url,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": mime,
                "x-upsert": "false",
                # 1-year immutable cache — the URL embeds a UUID so the
                # asset is content-stable for its whole lifetime.
                "Cache-Control": "public, max-age=31536000, immutable",
            },
            data=f.stream.read(),
            timeout=30,
        )
    except requests.RequestException as e:
        logger.error("Photo upload failed: %s", e)
        return jsonify({"error": "Upload failed — please try again."}), 502

    if not r.ok:
        msg = "Upload failed."
        try:
            body = r.json()
            if body.get("message"):
                msg = body["message"]
        except Exception:
            pass
        logger.error("Photo upload %s on %s: %s", r.status_code, upload_url, r.text[:300])
        return jsonify({"error": msg, "status": r.status_code}), 502

    display_name = (request.form.get("display_name") or "").strip()[:80] or None
    rows = post(
        "user_photos",
        {
            "user_id": user_id,
            "storage_key": storage_key,
            "display_name": display_name,
            "mime_type": mime,
            "size_bytes": size,
        },
    )
    new_id = rows[0]["id"] if rows else None
    return jsonify({
        "ok": True,
        "id": new_id,
        "url": _public_storage_url(storage_key),
        "display_name": display_name,
    })


@photos_bp.route("/photos/<photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    user_id = session["user_id"]
    rows = get(
        "user_photos",
        params={
            "id": f"eq.{photo_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,storage_key",
            "limit": "1",
        },
    ) or []
    if not rows:
        return jsonify({"error": "Not found"}), 404
    storage_key = rows[0].get("storage_key")

    update(
        "user_photos",
        params={"id": f"eq.{photo_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )
    if storage_key:
        try:
            requests.delete(
                f"{SUPABASE_URL}/storage/v1/object/{_BUCKET}/{storage_key}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10,
            )
        except Exception as e:
            logger.warning("Storage delete failed (orphan blob): %s", e)
    return jsonify({"ok": True})


@photos_bp.route("/photos/<photo_id>/rename", methods=["POST"])
@login_required
def rename_photo(photo_id):
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    name = (data.get("display_name") or "").strip()[:80] or None
    update(
        "user_photos",
        params={"id": f"eq.{photo_id}", "user_id": f"eq.{user_id}"},
        json={"display_name": name},
    )
    return jsonify({"ok": True, "display_name": name})

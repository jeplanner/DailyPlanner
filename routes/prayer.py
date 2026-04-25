"""
Prayer page — renders devotional images for the user's chosen deities.

Two image sources surface together on /prayer:
  1. Curated assets bundled in static/icons/gods/ (deity portraits we
     ship). Auto-discovered; drop a file in, it shows up.
  2. User uploads stored in Supabase Storage bucket `prayer-photos`,
     metadata in the prayer_photos table (MIGRATION_PRAYER_PHOTOS.sql).

Render's filesystem is ephemeral so user uploads MUST go to Supabase —
we can't write into static/. The /prayer/upload endpoint streams the
file to Storage and inserts a row recording the storage key.

Performance-conscious:
  * Bundled assets are served by Flask's static handler with far-future
    caching headers.
  * User uploads are served directly from Supabase's CDN URL.
  * Templates set loading="lazy" + decoding="async" on every image,
    so only tiles visible in the viewport fetch bytes.
"""
import logging
import mimetypes
import os
import uuid

import requests
from flask import Blueprint, jsonify, render_template, request, session

from services.kavasam_text import get_verses as get_kavasam_verses
from services.login_service import login_required
from services.rangapura_text import get_sections as get_rangapura_sections
from supabase_client import SUPABASE_URL, SUPABASE_KEY, get, post, update

logger = logging.getLogger("daily_plan")

prayer_bp = Blueprint("prayer", __name__)

# Supabase Storage bucket name. Must match what's been created in the
# dashboard (see MIGRATION_PRAYER_PHOTOS.sql for setup steps).
_BUCKET = "prayer-photos"
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB — match the bucket policy
_ALLOWED_MIMES = {
    "image/jpeg": "jpg",
    "image/jpg":  "jpg",
    "image/png":  "png",
    "image/webp": "webp",
    "image/gif":  "gif",
}


_GODS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "icons", "gods",
)
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# Filename → display name. The order of entries is also the display
# order for those deities. Any image in _GODS_DIR that isn't listed
# here is auto-appended (alphabetical) with a prettified display name
# derived from the filename. Entries that no longer exist on disk are
# skipped silently.
_DEITY_NAMES: list[tuple[str, str]] = [
    ("ganesa.webp",                        "Lord Ganesha"),
    ("kandhan.webp",                       "Murugan"),
    ("murugan1.webp",                      "Murugan II"),
    ("meenakshi.webp",                     "Meenakshi Amman"),
    ("kolavizhiamman.jpg",                 "Kolavizhi Amman"),
    ("kolavizhiammanji.jpg",               "Kolavizhi Amman II"),
    ("renganathar.jpg",                    "Renganathar"),
    ("rengu.jpg",                          "Renganathar II"),
    ("renganathaswamy temple-Tiruchy.jpg", "Srirangam Temple"),
    ("srirangapatinam renga temple.jpg",   "Srirangapatnam Temple"),
    ("parthasarathy.jpg",                  "Parthasarathy"),
    ("parthasarathy1.jpg",                 "Parthasarathy II"),
    ("tirupathi.webp",                     "Venkateswara"),
    ("upilliappan.jpg",                    "Oppiliappan"),
    ("mantralayam-1.jpg",                  "Raghavendra Swamy I"),
    ("mantralayam-2.jpg",                  "Raghavendra Swamy II"),
]


def _prettify(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    return stem.replace("-", " ").replace("_", " ").strip().title()


def _list_deities() -> list[dict]:
    try:
        files_on_disk = set(os.listdir(_GODS_DIR))
    except (FileNotFoundError, OSError):
        # Can't list the folder — fall back to the static list so the
        # page still renders (missing <img>s degrade gracefully).
        return [{"name": name, "img": fn} for fn, name in _DEITY_NAMES]

    listed = {fn for fn, _ in _DEITY_NAMES}

    deities = [
        {"name": name, "img": fn}
        for fn, name in _DEITY_NAMES
        if fn in files_on_disk
    ]
    for fn in sorted(files_on_disk):
        if fn in listed or not fn.lower().endswith(_IMAGE_EXTS):
            continue
        deities.append({"name": _prettify(fn), "img": fn})
    return deities


def _public_storage_url(storage_key: str) -> str:
    """Public CDN URL for a Storage object. Bucket must be marked public
    in the Supabase dashboard for these URLs to work without signing."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{_BUCKET}/{storage_key}"


def _list_user_photos(user_id: str) -> list[dict]:
    """User-uploaded photos for the prayer page. Best-effort — if the
    table doesn't exist (migration not run) we silently fall back to
    an empty list rather than 500-ing the page."""
    try:
        rows = get(
            "prayer_photos",
            params={
                "user_id": f"eq.{user_id}",
                "is_deleted": "eq.false",
                "select": "id,storage_key,display_name,created_at",
                "order": "created_at.desc",
                "limit": "200",
            },
        ) or []
    except Exception as e:
        logger.warning("prayer_photos fetch failed (migration missing?): %s", e)
        return []
    out = []
    for r in rows:
        out.append({
            "id":   r["id"],
            "name": r.get("display_name") or "Photo",
            "img":  _public_storage_url(r["storage_key"]),
            "user_uploaded": True,
        })
    return out


@prayer_bp.route("/prayer")
@login_required
def prayer_page():
    user_id = session.get("user_id")
    deities = _list_deities()
    user_photos = _list_user_photos(user_id) if user_id else []
    return render_template(
        "prayer.html",
        deities=deities,
        user_photos=user_photos,
    )


@prayer_bp.route("/prayer/upload", methods=["POST"])
@login_required
def upload_prayer_photo():
    """Accept a multipart upload and stream it to Supabase Storage.

    Form fields:
      file          — the image (required)
      display_name  — optional caption shown under the tile

    Returns: { ok, id, url, display_name } on success.
    """
    user_id = session["user_id"]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    # MIME guard. We trust the file's reported content_type loosely but
    # also normalise from the extension as a backup.
    mime = (f.mimetype or "").lower()
    if mime not in _ALLOWED_MIMES:
        guessed, _ = mimetypes.guess_type(f.filename)
        if guessed and guessed.lower() in _ALLOWED_MIMES:
            mime = guessed.lower()
        else:
            return jsonify({"error": "Only JPG, PNG, WebP, or GIF are allowed."}), 400
    ext = _ALLOWED_MIMES[mime]

    # Size guard. .seek/.tell costs nothing for in-memory uploads.
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
                # Long-immutable cache. The object key includes a UUID
                # so the URL never changes once uploaded — safe to mark
                # immutable so browsers skip the conditional GET on
                # repeat visits.
                "Cache-Control": "public, max-age=31536000, immutable",
            },
            data=f.stream.read(),
            timeout=30,
        )
    except requests.RequestException as e:
        logger.error("Storage upload failed: %s", e)
        return jsonify({"error": "Upload failed — please try again."}), 502

    if not r.ok:
        # Likely the bucket doesn't exist or isn't public yet. Surface
        # the Supabase error message so the user knows what to fix.
        msg = "Upload failed."
        try:
            body = r.json()
            if body.get("message"):
                msg = body["message"]
        except Exception:
            pass
        logger.error("Storage upload %s on %s: %s", r.status_code, upload_url, r.text[:300])
        return jsonify({"error": msg, "status": r.status_code}), 502

    display_name = (request.form.get("display_name") or "").strip()[:80] or None
    rows = post(
        "prayer_photos",
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


@prayer_bp.route("/prayer/photos/<photo_id>/delete", methods=["POST"])
@login_required
def delete_prayer_photo(photo_id):
    """Soft-delete a user-uploaded photo (audit trail preserved).
    Removing the underlying Storage object is best-effort; if it fails
    the row stays soft-deleted so it never re-surfaces in the UI."""
    user_id = session["user_id"]
    rows = get(
        "prayer_photos",
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
        "prayer_photos",
        params={"id": f"eq.{photo_id}", "user_id": f"eq.{user_id}"},
        json={"is_deleted": True},
    )

    # Best-effort Storage delete. The row's already soft-deleted, so a
    # failure here just leaves an orphan blob — fine to ignore.
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


@prayer_bp.route("/prayer/kavasam")
@login_required
def kavasam_page():
    """Kanda Sashti Kavasam — full Tamil text, mobile-friendly with
    text-size toggle and saved preference."""
    return render_template("kavasam.html", verses=get_kavasam_verses())


@prayer_bp.route("/prayer/rangapura")
@login_required
def rangapura_page():
    """Rangapura Vihara (Muthuswami Dikshitar) — as rendered by MSS."""
    return render_template("rangapura.html", sections=get_rangapura_sections())

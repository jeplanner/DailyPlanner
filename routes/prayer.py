"""
Prayer page — renders devotional images for the user's chosen deities.

Performance-conscious:
  * Assets live in static/icons/gods/ and are served by Flask's static
    handler with far-future caching headers (default behaviour).
  * The template sets loading="lazy" + decoding="async" on every image,
    so only tiles visible in the viewport fetch bytes.
  * Cards use fixed aspect-ratio frames so layout doesn't shift as
    images arrive out of order.

Images are auto-discovered from static/icons/gods/ on each request.
Drop a new .jpg/.jpeg/.png/.webp/.gif into the folder and it appears on
the page — no code change needed. To pin a custom display name or force
display order, add/edit an entry in _DEITY_NAMES below.
"""
import os

from flask import Blueprint, render_template

from services.kavasam_text import get_verses as get_kavasam_verses
from services.login_service import login_required
from services.rangapura_text import get_sections as get_rangapura_sections

prayer_bp = Blueprint("prayer", __name__)


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


@prayer_bp.route("/prayer")
@login_required
def prayer_page():
    return render_template("prayer.html", deities=_list_deities())


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

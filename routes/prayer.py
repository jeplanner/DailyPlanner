"""
Prayer page — renders devotional images for the user's chosen deities.

Performance-conscious:
  * Assets live in static/icons/gods/ and are served by Flask's static
    handler with far-future caching headers (default behaviour).
  * The template sets loading="lazy" + decoding="async" on every image,
    so only tiles visible in the viewport fetch bytes.
  * Cards use fixed aspect-ratio frames so layout doesn't shift as
    images arrive out of order.

Add or remove a deity by editing DEITIES below. Missing files degrade
gracefully (the <img> simply won't render).
"""
from flask import Blueprint, render_template

from services.kavasam_text import get_verses as get_kavasam_verses
from services.login_service import login_required
from services.rangapura_text import get_sections as get_rangapura_sections

prayer_bp = Blueprint("prayer", __name__)


# Order here = display order on the page.
# Filenames must match exactly what's on disk in static/icons/gods/.
DEITIES = [
    {"name": "Lord Ganesha",        "img": "ganesa.webp"},
    {"name": "Murugan",             "img": "kandhan.webp"},
    {"name": "Renganathar",         "img": "renganathar.jpg"},
    {"name": "Meenakshi Amman",     "img": "meenakshi.webp"},
    {"name": "Venkateswara",        "img": "tirupathi.webp"},
    {"name": "Oppiliappan",         "img": "upilliappan.jpg"},
]


@prayer_bp.route("/prayer")
@login_required
def prayer_page():
    return render_template("prayer.html", deities=DEITIES)


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

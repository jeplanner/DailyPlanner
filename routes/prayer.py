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

from services.login_service import login_required

prayer_bp = Blueprint("prayer", __name__)


# Order here = display order on the page.
DEITIES = [
    {"name": "Lord Ganesha",        "img": "ganesa.webp"},
    {"name": "Murugan",             "img": "murugan.webp"},
    {"name": "Renganathar",         "img": "renganathar.jpg"},
    {"name": "Meenakshi Amman",     "img": "meenakshi.webp"},
    {"name": "Venkateswara",        "img": "tirupathi.webp"},
    {"name": "Oppiliappan",         "img": "upilliappan.gif"},
]


@prayer_bp.route("/prayer")
@login_required
def prayer_page():
    return render_template("prayer.html", deities=DEITIES)

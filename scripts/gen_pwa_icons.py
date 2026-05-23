"""Generate PNG icons + iOS splash screens for the PWA.

Renders the same artwork as static/icons/icon.svg:
  - indigo rounded-square background (#6366f1)
  - centered white checkmark
The SVG is simple enough that PIL can reproduce it pixel-accurately
without an SVG parser. Re-run after editing icon.svg by hand."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BG = (99, 102, 241, 255)
FG = (255, 255, 255, 255)
SPLASH_BG = (247, 248, 250, 255)

ICONS_DIR = Path(__file__).resolve().parent.parent / "static" / "icons"
SPLASH_DIR = ICONS_DIR / "splash"


def _round_rect(size: int, radius_ratio: float, padding: int = 0) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int((size - 2 * padding) * radius_ratio)
    d.rounded_rectangle(
        [padding, padding, size - 1 - padding, size - 1 - padding],
        radius=radius,
        fill=BG,
    )
    return img


def _checkmark(img: Image.Image, scale: float = 1.0) -> None:
    """Draw the white check inside img. scale<1 shrinks the mark
    (used for maskable icons that need a safe zone)."""
    size = img.width
    d = ImageDraw.Draw(img)
    # Source viewBox is 512: M148 260 L214 326 L364 176, stroke 44.
    sx = size / 512.0 * scale
    cx = size / 2.0
    cy = size / 2.0
    pts_src = [(148, 260), (214, 326), (364, 176)]
    pts = [(cx + (x - 256) * sx, cy + (y - 256) * sx) for x, y in pts_src]
    width = max(2, int(44 * sx))
    d.line(pts, fill=FG, width=width, joint="curve")
    # Round caps — line() with joint="curve" rounds joins but not ends.
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=FG)


def make_icon(size: int, *, maskable: bool = False) -> Image.Image:
    if maskable:
        # Maskable spec: art must fit in the inner 80% safe zone; the
        # outer 10% on each side can be cropped by the OS into a circle,
        # squircle, etc. So we fill the full canvas with the BG and
        # shrink the check to 80%.
        img = _round_rect(size, radius_ratio=0.0)  # full square bg
        # Re-fill as solid (rounded_rectangle with r=0 is still a square).
        img = Image.new("RGBA", (size, size), BG)
        _checkmark(img, scale=0.8)
    else:
        img = _round_rect(size, radius_ratio=96 / 512)
        _checkmark(img, scale=1.0)
    return img


def make_apple_touch(size: int = 180) -> Image.Image:
    # iOS masks the icon itself to a squircle, so render fully opaque
    # square background (no transparent corners) and let iOS clip.
    img = Image.new("RGBA", (size, size), BG)
    _checkmark(img, scale=1.0)
    return img


def make_splash(width: int, height: int) -> Image.Image:
    img = Image.new("RGBA", (width, height), SPLASH_BG)
    # Icon sized to ~30% of the shorter edge, centered.
    icon_size = int(min(width, height) * 0.30)
    icon = make_icon(icon_size, maskable=False)
    img.paste(icon, ((width - icon_size) // 2, (height - icon_size) // 2), icon)
    return img


# (width, height, filename) — covers the common iPhone/iPad device pixel
# sizes Apple expects via <link rel="apple-touch-startup-image">.
SPLASH_SIZES = [
    (1290, 2796, "splash-1290x2796.png"),  # iPhone 15 Pro Max
    (1179, 2556, "splash-1179x2556.png"),  # iPhone 15 / 14 Pro
    (1170, 2532, "splash-1170x2532.png"),  # iPhone 13 / 14
    (1125, 2436, "splash-1125x2436.png"),  # iPhone X / 11 Pro
    (828,  1792, "splash-828x1792.png"),   # iPhone XR / 11
    (1242, 2688, "splash-1242x2688.png"),  # iPhone XS Max / 11 Pro Max
    (750,  1334, "splash-750x1334.png"),   # iPhone 8 / SE2
    (1536, 2048, "splash-1536x2048.png"),  # iPad mini / 9.7"
    (1668, 2388, "splash-1668x2388.png"),  # iPad Pro 11"
    (2048, 2732, "splash-2048x2732.png"),  # iPad Pro 12.9"
]


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    SPLASH_DIR.mkdir(parents=True, exist_ok=True)

    make_icon(192).save(ICONS_DIR / "icon-192.png", optimize=True)
    make_icon(512).save(ICONS_DIR / "icon-512.png", optimize=True)
    make_icon(512, maskable=True).save(ICONS_DIR / "icon-512-maskable.png", optimize=True)
    make_icon(192, maskable=True).save(ICONS_DIR / "icon-192-maskable.png", optimize=True)
    make_apple_touch(180).save(ICONS_DIR / "apple-touch-icon.png", optimize=True)
    make_icon(32).save(ICONS_DIR / "favicon-32.png", optimize=True)

    for w, h, name in SPLASH_SIZES:
        make_splash(w, h).save(SPLASH_DIR / name, optimize=True)

    print(f"wrote {len(SPLASH_SIZES) + 6} files to {ICONS_DIR}")


if __name__ == "__main__":
    main()

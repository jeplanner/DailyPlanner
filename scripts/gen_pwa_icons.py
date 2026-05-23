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
SHORTCUT_DIR = ICONS_DIR / "shortcuts"
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "static" / "screenshots"


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

# Shortcut icons: tinted rounded square + a single glyph drawn with PIL.
# These appear in the long-press launcher menu on Android.
SHORTCUTS = [
    # (filename, tint hex, glyph kind)
    ("quick.png",     "#6366f1", "lightning"),
    ("checklist.png", "#22c55e", "check"),
    ("inbox.png",     "#0ea5e9", "tray"),
]


def make_shortcut(tint_hex: str, glyph: str, size: int = 192) -> Image.Image:
    tint = tuple(int(tint_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    img = Image.new("RGBA", (size, size), tint)
    # Round the corners.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 96 / 512), fill=255)
    rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(rounded)
    # Glyph drawn at ~50% of the canvas, white, single-stroke shapes.
    c = size / 2
    s = size * 0.22
    w = max(4, int(size * 0.08))
    if glyph == "check":
        d.line([(c - s, c), (c - s * 0.2, c + s * 0.7), (c + s, c - s * 0.6)],
               fill=FG, width=w, joint="curve")
    elif glyph == "lightning":
        d.polygon([
            (c - s * 0.3, c - s),
            (c + s * 0.6, c - s),
            (c + s * 0.05, c - s * 0.1),
            (c + s * 0.65, c - s * 0.1),
            (c - s * 0.5, c + s),
            (c, c + s * 0.15),
            (c - s * 0.55, c + s * 0.15),
        ], fill=FG)
    elif glyph == "tray":
        d.rounded_rectangle([c - s, c - s * 0.7, c + s, c + s * 0.85],
                            radius=int(size * 0.04), outline=FG, width=w)
        d.line([(c - s * 0.55, c + s * 0.2), (c + s * 0.55, c + s * 0.2)],
               fill=FG, width=w, joint="curve")
    return rounded


def make_screenshot(width: int, height: int, title: str, subtitle: str) -> Image.Image:
    """Synthetic placeholder screenshot for the manifest. Real screenshots
    captured from the running PWA would land here too — they just need
    to match the declared sizes in manifest.json."""
    img = Image.new("RGBA", (width, height), SPLASH_BG)
    d = ImageDraw.Draw(img)
    # Tinted header bar (~12% of height).
    bar_h = int(height * 0.12)
    d.rectangle([0, 0, width, bar_h], fill=BG)
    # Drop the icon top-left.
    icon = make_icon(int(bar_h * 0.7), maskable=False)
    img.paste(icon, (24, (bar_h - icon.width) // 2), icon)
    # Title + subtitle text (basic — Pillow's default font is fine for a
    # placeholder; replace with real screenshots when you have them).
    try:
        from PIL import ImageFont
        font_t = ImageFont.load_default()
        font_s = ImageFont.load_default()
    except Exception:
        font_t = None; font_s = None
    d.text((24 + bar_h, bar_h // 2 - 14), title, fill=FG, font=font_t)
    d.text((24, bar_h + 40), subtitle, fill=(60, 70, 90, 255), font=font_s)
    # A few faux list items to give the install dialog something to look at.
    y = bar_h + 110
    for i in range(8):
        d.rounded_rectangle([24, y, width - 24, y + 70], radius=12, outline=(220, 224, 235, 255), width=2)
        d.ellipse([40, y + 22, 70, y + 52], outline=(160, 170, 195, 255), width=2)
        d.rectangle([90, y + 28, width - 60, y + 38], fill=(200, 208, 222, 255))
        y += 86
        if y > height - 80:
            break
    return img


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    SPLASH_DIR.mkdir(parents=True, exist_ok=True)
    SHORTCUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    make_icon(192).save(ICONS_DIR / "icon-192.png", optimize=True)
    make_icon(512).save(ICONS_DIR / "icon-512.png", optimize=True)
    make_icon(512, maskable=True).save(ICONS_DIR / "icon-512-maskable.png", optimize=True)
    make_icon(192, maskable=True).save(ICONS_DIR / "icon-192-maskable.png", optimize=True)
    make_apple_touch(180).save(ICONS_DIR / "apple-touch-icon.png", optimize=True)
    make_icon(32).save(ICONS_DIR / "favicon-32.png", optimize=True)

    for w, h, name in SPLASH_SIZES:
        make_splash(w, h).save(SPLASH_DIR / name, optimize=True)
    # Landscape splash (rotated 90°) for each portrait size.
    for w, h, name in SPLASH_SIZES:
        rot = make_splash(w, h).rotate(-90, expand=True)
        rot.save(SPLASH_DIR / name.replace("splash-", "splash-land-"), optimize=True)

    for name, tint, glyph in SHORTCUTS:
        make_shortcut(tint, glyph).save(SHORTCUT_DIR / name, optimize=True)

    # Two placeholder screenshots for Chrome's rich install dialog —
    # one phone (wide=narrow) and one desktop (wide=wide). Real
    # screenshots captured from the live PWA can replace these and
    # keep the same filenames; the manifest will pick them up.
    make_screenshot(1080, 1920, "DailyPlanner", "Quick capture, gentle nudges, no clutter") \
        .save(SCREENSHOT_DIR / "phone-1080x1920.png", optimize=True)
    make_screenshot(1920, 1080, "DailyPlanner", "Today's checklist, inbox, and goals on one screen") \
        .save(SCREENSHOT_DIR / "desktop-1920x1080.png", optimize=True)

    total = 6 + len(SPLASH_SIZES) * 2 + len(SHORTCUTS) + 2
    print(f"wrote {total} files (icons={6}, splash={len(SPLASH_SIZES)*2}, "
          f"shortcuts={len(SHORTCUTS)}, screenshots=2)")


if __name__ == "__main__":
    main()

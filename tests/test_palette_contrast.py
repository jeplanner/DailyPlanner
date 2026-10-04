"""The palette is only as good as its worst pair.

Every colour in design-system.css is declared as `light-dark(<light>,
<dark>)`, so each token carries BOTH themes and this file can check them
together. What it asserts is the thing that kept breaking by hand:

  - all four badge variants measured between 2.1:1 and 2.6:1 in dark
    mode, because they set the saturated hue as text on the dark tint;
  - tooltips were white-on-near-white in dark mode, because
    --color-text-inverse never flipped when --color-text did;
  - the sidebar's group headings -- which became buttons -- and the muted
    text used across ~94 sites sat at 2.5:1.

None of those are visible in a diff and all three shipped. A ratio is,
so the pairs are listed here and measured instead.

WCAG 2.1 AA: 4.5:1 for body text, 3:1 for large text and for the
boundary of a UI component. Ratios below are the AA floor for the role
each pair actually plays.
"""
import re
import os
import pytest

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "static", "design-system.css")


def _luminance(hex_colour):
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    chan = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        chan.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2]


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _tokens():
    """Resolve every colour token to its (light, dark) hex pair.

    Handles the three forms the file uses: a bare hex (same in both
    themes), a light-dark() pair, and a var() alias onto another token.
    """
    src = open(CSS, encoding="utf-8").read()
    root = src[src.index(":root {"):src.index("--z-toast")]
    raw = {}
    for name, value in re.findall(r"(--color-[\w-]+)\s*:\s*([^;]+);", root):
        raw[name] = value.strip()

    def resolve(name, seen=()):
        if name in seen:
            return None
        value = raw.get(name)
        if value is None:
            return None
        ld = re.match(r"light-dark\(\s*(#[0-9a-fA-F]{3,6})\s*,\s*(#[0-9a-fA-F]{3,6})\s*\)$", value)
        if ld:
            return ld.group(1), ld.group(2)
        alias = re.match(r"var\(\s*(--[\w-]+)\s*\)$", value)
        if alias:
            return resolve(alias.group(1), seen + (name,))
        bare = re.match(r"(#[0-9a-fA-F]{3,6})$", value)
        if bare:
            return bare.group(1), bare.group(1)
        return None

    out = {}
    for name in raw:
        pair = resolve(name)
        if pair:
            out[name] = pair
    return out


TOKENS = _tokens()

# (foreground token, background token, AA floor, what it is)
PAIRS = [
    ("--color-text",              "--color-bg",                7.0, "body text on the page"),
    ("--color-text",              "--color-surface",           7.0, "body text on a card"),
    ("--color-text-secondary",    "--color-surface",           4.5, "secondary text on a card"),
    ("--color-text-secondary",    "--color-bg",                4.5, "secondary text on the page"),
    ("--color-text-secondary",    "--color-surface-secondary", 4.5, "secondary text on a sub-surface"),
    ("--color-text-muted",        "--color-surface",           4.5, "muted text on a card"),
    ("--color-text-muted",        "--color-bg",                4.5, "muted text on the page"),
    ("--color-text-muted",        "--color-surface-secondary", 4.5, "muted text on a sub-surface"),
    ("--color-text-muted",        "--color-surface-sunken",    4.5, "muted text on a sunken surface"),
    # The tooltip is --color-text-inverse ON --color-text. Both themes.
    ("--color-text-inverse",      "--color-text",              7.0, "tooltip text on the inverted surface"),
    # Links and active nav. The ink, never the fill.
    ("--color-link",              "--color-surface",           4.5, "link on a card"),
    ("--color-link",              "--color-bg",                4.5, "link on the page"),
    ("--color-primary-ink",       "--color-primary-light",     4.5, "active nav link on its own tint"),
    # Solid buttons: the label on the fill.
    ("--color-on-primary",        "--color-primary",           4.5, "label on a primary button"),
    ("--color-on-success",        "--color-success",           4.5, "label on a success button"),
    ("--color-on-danger",         "--color-danger",            4.5, "label on a danger button"),
    ("--color-on-warning",        "--color-warning",           4.5, "label on a warning button"),
    # Badges / chips: the -on-tint text on its own tint. This is the set
    # that was unreadable in dark mode.
    ("--color-primary-on-tint",   "--color-primary-light",     4.5, "primary badge"),
    ("--color-success-on-tint",   "--color-success-light",     4.5, "success badge"),
    ("--color-warning-on-tint",   "--color-warning-light",     4.5, "warning badge"),
    ("--color-danger-on-tint",    "--color-danger-light",      4.5, "danger badge"),
    ("--color-info-on-tint",      "--color-info-light",        4.5, "info badge"),
    # State text straight on a page surface, which is how most pages use it.
    ("--color-success-on-tint",   "--color-surface",           4.5, "success text on a card"),
    ("--color-warning-on-tint",   "--color-surface",           4.5, "warning text on a card"),
    ("--color-danger-on-tint",    "--color-surface",           4.5, "danger text on a card"),
    # The focus ring has to be findable against both the surface it rings
    # and the page behind it. 3:1 is the AA floor for a UI boundary.
    ("--color-primary-ink",       "--color-surface",           3.0, "focus ring against a card"),
    ("--color-primary-ink",       "--color-bg",                3.0, "focus ring against the page"),
]


@pytest.mark.parametrize("fg,bg,floor,what", PAIRS, ids=[p[3] for p in PAIRS])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_palette_pair_meets_wcag_aa(theme, fg, bg, floor, what):
    assert fg in TOKENS, f"{fg} is not a resolvable colour token"
    assert bg in TOKENS, f"{bg} is not a resolvable colour token"
    i = 0 if theme == "light" else 1
    f, b = TOKENS[fg][i], TOKENS[bg][i]
    ratio = contrast(f, b)
    assert ratio >= floor, (
        f"{what} fails in {theme} mode: {fg} ({f}) on {bg} ({b}) "
        f"is {ratio:.2f}:1, needs {floor}:1"
    )


def test_every_surface_and_text_token_carries_both_themes():
    """A token that only has a light value is how dark mode breaks.

    Each of these must be a light-dark() pair, i.e. resolve to two
    DIFFERENT hexes. A bare hex here means the token keeps its light
    value on a dark page.
    """
    must_flip = [
        "--color-bg", "--color-surface", "--color-surface-secondary",
        "--color-surface-elevated", "--color-surface-sunken",
        "--color-text", "--color-text-secondary", "--color-text-muted",
        "--color-text-inverse", "--color-border", "--color-border-strong",
        "--color-border-light", "--color-primary-light", "--color-primary-ink",
        "--color-success-light", "--color-warning-light", "--color-danger-light",
        "--color-success-on-tint", "--color-warning-on-tint", "--color-danger-on-tint",
    ]
    flat = [t for t in must_flip
            if t in TOKENS and TOKENS[t][0].lower() == TOKENS[t][1].lower()]
    assert not flat, f"these tokens do not change between themes: {flat}"


def test_borders_stay_visible_against_their_surface():
    """A border you cannot see is a card that has no edge."""
    for theme, i in (("light", 0), ("dark", 1)):
        border = TOKENS["--color-border"][i]
        for surface in ("--color-surface", "--color-bg"):
            ratio = contrast(border, TOKENS[surface][i])
            assert ratio >= 1.18, (
                f"--color-border ({border}) is invisible on {surface} "
                f"in {theme} mode: {ratio:.2f}:1"
            )

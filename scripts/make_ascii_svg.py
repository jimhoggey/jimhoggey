#!/usr/bin/env python3
"""Render an avatar (or any image) as an animated ASCII-art SVG.

Reads the GitHub avatar by default, so the portrait re-renders itself whenever
the avatar changes. Alpha is used as the subject mask, and contrast is
auto-levelled across the subject only -- that keeps the background empty while
still pulling detail out of a mostly-black silhouette.

Each row is revealed by a left-to-right clip wipe, staggered top to bottom, so
the portrait appears to type itself in.

Usage:
    python scripts/make_ascii_svg.py [source-image]
"""

import io
import os
import sys

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import (BORDER, CYAN, DIM, MONO, PURPLE, PURPLE_HI, USER,
                   blink_cursor, esc, reveal, window_chrome)

OUT = "ascii.svg"
AVATAR = f"https://github.com/{USER}.png?size=460"

# Density ramp: index 0 is empty, last index is solid.
RAMP = " .`:-=+*csS#%@"

COLS = 78
FONT = 8.0
CHAR_W = 4.7          # advance width of the monospace grid
LINE_H = 8.0
BAR_H = 26
PAD_X = 17.0
PAD_TOP = 12.0
PAD_BOTTOM = 16.0

# Square source -> square character grid, corrected for cell aspect ratio.
ROWS = int(round(COLS * CHAR_W / LINE_H))

TEXT_W = COLS * CHAR_W
TEXT_H = ROWS * LINE_H
WIDTH = int(round(TEXT_W + 2 * PAD_X))
HEIGHT = int(round(BAR_H + PAD_TOP + TEXT_H + PAD_BOTTOM))

ROW_DELAY = 0.055     # stagger between rows
WIPE = 0.30           # duration of a single row's wipe


def load_image(source):
    """Return an RGBA PIL image from a local path or the GitHub avatar."""
    if source:
        return Image.open(source).convert("RGBA")
    resp = requests.get(AVATAR, timeout=30,
                        headers={"User-Agent": f"{USER}-profile-art"})
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def square_crop(img, margin=0.05):
    """Crop to the subject's alpha bounds, then centre it on a square canvas.

    The GitHub avatar carries a lot of transparent padding. Without this the
    portrait uses barely half the character grid. Squaring the canvas keeps the
    aspect ratio honest, since the grid geometry assumes a square source.
    """
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img

    subject = img.crop(bbox)
    side = int(round(max(subject.size) * (1 + 2 * margin)))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(subject,
                 ((side - subject.width) // 2, (side - subject.height) // 2))
    return canvas


def to_ascii(img):
    """Convert an RGBA image to a list of ROWS strings, each COLS chars."""
    img = square_crop(img)

    # Composite on white at full resolution so downsampling cannot create
    # dark halos around the transparent edges.
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, img)

    lum = np.asarray(
        flat.convert("L").resize((COLS, ROWS), Image.LANCZOS), dtype=float)
    alpha = np.asarray(
        img.getchannel("A").resize((COLS, ROWS), Image.LANCZOS), dtype=float)

    subject = alpha > 40
    if not subject.any():
        subject = np.ones_like(alpha, dtype=bool)

    # Auto-level across subject pixels only, so a near-black silhouette still
    # shows its internal detail (screen glow, sunglasses, edges).
    lo, hi = np.percentile(lum[subject], [2, 98])
    if hi - lo < 1e-6:
        hi = lo + 1.0

    # Dark pixels map towards the dense end of the ramp.
    t = np.clip((hi - lum) / (hi - lo), 0.0, 1.0)
    idx = np.rint(t * (len(RAMP) - 1)).astype(int)
    idx = np.clip(idx, 1, len(RAMP) - 1)   # never blank out the silhouette
    idx[~subject] = 0

    return ["".join(RAMP[i] for i in row) for row in idx]


def build_svg(rows):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'role="img" aria-label="ASCII-art portrait of the {USER} avatar">',
        "  <defs>",
        '    <linearGradient id="ink" x1="0" y1="0" x2="0.35" y2="1">',
        f'      <stop offset="0%" stop-color="{PURPLE_HI}"/>',
        f'      <stop offset="45%" stop-color="{PURPLE}"/>',
        f'      <stop offset="100%" stop-color="{CYAN}"/>',
        "    </linearGradient>",
        '    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">',
        '      <feGaussianBlur stdDeviation="1.4" result="b"/>',
        "      <feMerge>",
        '        <feMergeNode in="b"/>',
        '        <feMergeNode in="SourceGraphic"/>',
        "      </feMerge>",
        "    </filter>",
    ]

    # One clip rect per row. The rect's own width is already full, so the row
    # is visible without SMIL; the animation wipes it in when SMIL is live.
    for r in range(len(rows)):
        y = BAR_H + PAD_TOP + r * LINE_H
        parts.append(f'    <clipPath id="w{r}">')
        parts.append(
            f'      <rect x="{PAD_X:.1f}" y="{y:.1f}" '
            f'width="{TEXT_W:.1f}" height="{LINE_H:.1f}">')
        parts.append("        " + reveal(
            "width", 0, f"{TEXT_W:.1f}", r * ROW_DELAY, WIPE))
        parts.append("      </rect>")
        parts.append("    </clipPath>")

    parts.append("  </defs>")
    parts.append(window_chrome(WIDTH, HEIGHT, f"{USER}.png -- ascii", BAR_H))

    parts.append(f'  <g filter="url(#glow)" fill="url(#ink)" '
                 f'font-family="{MONO}" font-size="{FONT}">')
    for r, line in enumerate(rows):
        # Baseline sits near the bottom of the cell.
        baseline = BAR_H + PAD_TOP + r * LINE_H + LINE_H - 1.6

        # Drop the spaces and give every remaining glyph an explicit x. SVG
        # collapses runs of whitespace, and textLength then redistributes the
        # survivors across the row -- which destroys the grid. Per-glyph
        # positioning sidesteps both problems and pins the art to an exact
        # grid regardless of which monospace font the renderer picks.
        glyphs = [(c, ch) for c, ch in enumerate(line) if ch != " "]
        if not glyphs:
            continue
        xs = " ".join(f"{PAD_X + c * CHAR_W:.1f}" for c, _ in glyphs)
        content = esc("".join(ch for _, ch in glyphs))
        parts.append(
            f'    <text clip-path="url(#w{r})" x="{xs}" '
            f'y="{baseline:.1f}">{content}</text>')
    parts.append("  </g>")

    # Prompt line under the portrait, arriving after the wipe finishes.
    done = len(rows) * ROW_DELAY + WIPE
    prompt_y = BAR_H + PAD_TOP + TEXT_H + 9.5
    parts.append(
        f'  <text x="{PAD_X:.1f}" y="{prompt_y:.1f}" font-family="{MONO}" '
        f'font-size="9" fill="{DIM}">'
        f'<tspan fill="{PURPLE}">&gt;</tspan> render complete'
        f'{reveal("opacity", 0, 1, done, 0.4)}</text>')
    parts.append(blink_cursor(PAD_X + 17 * 5.4, prompt_y - 7.5,
                              begin=done + 0.3))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    img = load_image(source)
    rows = to_ascii(img)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(rows))
    print(f"wrote {OUT}  ({COLS}x{ROWS} chars, {WIDTH}x{HEIGHT}px)")


if __name__ == "__main__":
    main()

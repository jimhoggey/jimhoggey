#!/usr/bin/env python3
"""The avatar as an animated ASCII-art portrait, as a positionable fragment.

Unlike the other sections this one loops: the whole portrait clears and retypes
itself every CYCLE seconds, so the page has something alive on it rather than a
one-off entrance you only see if you happen to arrive at the right moment.
"""

import io
import os
import sys

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import CYAN, MONO, PURPLE, PURPLE_HI, USER, esc

AVATAR = f"https://github.com/{USER}.png?size=460"

# Density ramp: index 0 is empty, the last index is solid.
RAMP = " .`:-=+*csS#%@"

COLS = 74
FONT = 8.0
CHAR_W = 4.7          # advance width of the monospace grid
LINE_H = 8.0

# Square source -> square grid, corrected for the cell's aspect ratio.
ROWS = int(round(COLS * CHAR_W / LINE_H))
WIDTH = COLS * CHAR_W
HEIGHT = ROWS * LINE_H

CYCLE = 15.0          # seconds between re-renders
ROW_DELAY = 0.055     # stagger between rows
WIPE = 0.30           # duration of one row's wipe


def load_image(source=None):
    """An RGBA image from a local path, or the GitHub avatar."""
    if source:
        return Image.open(source).convert("RGBA")
    resp = requests.get(AVATAR, timeout=30,
                        headers={"User-Agent": f"{USER}-profile-art"})
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def square_crop(img, margin=0.04):
    """Crop to the subject's alpha bounds, then centre it on a square canvas.

    The avatar carries a lot of transparent padding; without this the portrait
    uses barely half the grid. Squaring keeps the aspect ratio honest, since the
    grid geometry assumes a square source.
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


def to_rows(img):
    """Convert an RGBA image to ROWS strings of COLS characters."""
    img = square_crop(img)

    # Composite on white at full resolution, so downsampling cannot pull dark
    # halos in from the transparent edges.
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

    t = np.clip((hi - lum) / (hi - lo), 0.0, 1.0)   # dark -> dense
    idx = np.rint(t * (len(RAMP) - 1)).astype(int)
    idx = np.clip(idx, 1, len(RAMP) - 1)            # never blank the silhouette
    idx[~subject] = 0

    return ["".join(RAMP[i] for i in row) for row in idx]


def build(x, y, rows, prefix="a"):
    """Render the portrait at (x, y). Returns (fragment, width, height)."""
    parts = ["  <defs>",
             f'    <linearGradient id="{prefix}ink" x1="0" y1="0" '
             f'x2="0.35" y2="1">',
             f'      <stop offset="0%" stop-color="{PURPLE_HI}"/>',
             f'      <stop offset="45%" stop-color="{PURPLE}"/>',
             f'      <stop offset="100%" stop-color="{CYAN}"/>',
             "    </linearGradient>"]

    # One clip rect per row. The rect's own width is already full, so the row
    # shows without SMIL; with SMIL it wipes in, holds, then clears and repeats.
    for r in range(len(rows)):
        begin = r * ROW_DELAY
        row_y = y + r * LINE_H
        k1 = begin / CYCLE
        k2 = (begin + WIPE) / CYCLE
        parts.append(f'    <clipPath id="{prefix}w{r}">')
        parts.append(
            f'      <rect x="{x:.1f}" y="{row_y:.1f}" '
            f'width="{WIDTH:.1f}" height="{LINE_H:.1f}">')
        parts.append(
            f'        <animate attributeName="width" begin="0s" '
            f'dur="{CYCLE:.0f}s" repeatCount="indefinite" '
            f'values="0;0;{WIDTH:.1f};{WIDTH:.1f}" '
            f'keyTimes="0;{k1:.4f};{k2:.4f};1"/>')
        parts.append("      </rect>")
        parts.append("    </clipPath>")
    parts.append("  </defs>")

    parts.append(f'  <g fill="url(#{prefix}ink)" font-family="{MONO}" '
                 f'font-size="{FONT}">')
    for r, line in enumerate(rows):
        baseline = y + r * LINE_H + LINE_H - 1.6

        # Drop the spaces and give every remaining glyph an explicit x. SVG
        # collapses runs of whitespace, which shears a space-padded grid;
        # per-glyph positioning also pins the art to an exact grid regardless
        # of which monospace font the renderer picks.
        glyphs = [(c, ch) for c, ch in enumerate(line) if ch != " "]
        if not glyphs:
            continue
        xs = " ".join(f"{x + c * CHAR_W:.1f}" for c, _ in glyphs)
        parts.append(
            f'    <text clip-path="url(#{prefix}w{r})" x="{xs}" '
            f'y="{baseline:.1f}">'
            f'{esc("".join(ch for _, ch in glyphs))}</text>')
    parts.append("  </g>")

    return "\n".join(parts) + "\n", WIDTH, HEIGHT

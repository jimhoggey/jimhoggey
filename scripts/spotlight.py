#!/usr/bin/env python3
"""A "recently worked on" card, filling the space beside the half-width heatmap.

Deliberately says almost nothing about the project. The logo mark plus a name is
enough to make someone wonder what it is and go look, which a paragraph of
explanation would not.

The mark is the service-visuals logo -- a gold ring with a gap and a centre dot
-- drawn as characters on the same grid the portrait uses. A highlight chases
around the ring, which is both eye-catching and on the nose: the project renders
countdown timers and spinner wheels.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import AMBER, AMBER_DIM, BORDER, CYAN, DIM, MONO, PANEL, esc

# Hardcoded for now -- one project, chosen by hand.
PROJECT = "service-visuals"
META = "python · 1★"
NUDGE = "↗ take a look"

# A tighter grid than the portrait uses: at 8px line height a circle this size
# only gets five rows of vertical resolution and reads as a blob.
COLS, ROWS = 24, 15
CHAR_W, LINE_H, FONT = 4.2, 6.0, 7.0
RING_W, RING_H = COLS * CHAR_W, ROWS * LINE_H

R_OUT, R_IN = 42.0, 31.0     # ring band, in pixels
R_SOFT = 2.0                 # soft edge either side of the band
R_DOT = 9.0                  # centre dot
GAP = (-74.0, -8.0)          # arc opening, degrees (0 = right, negative = up)

CHASE = 2.6                  # seconds for one lap of the highlight
LIT_WINDOW = 0.16            # fraction of a lap a segment stays lit

PAD = 16.0


def mark():
    """The logo as a grid of (col, row, char, phase) ring cells plus the dot.

    `phase` is the cell's angle normalised to 0..1, which the chase animation
    uses to stagger each segment around the ring.
    """
    cx, cy = (COLS - 1) / 2.0, (ROWS - 1) / 2.0
    cells = []
    for r in range(ROWS):
        for c in range(COLS):
            dx = (c - cx) * CHAR_W
            dy = (r - cy) * LINE_H
            dist = math.hypot(dx, dy)

            if dist <= R_DOT:
                cells.append((c, r, "@", None))
                continue

            angle = math.degrees(math.atan2(dy, dx))
            if GAP[0] <= angle <= GAP[1]:
                continue

            if R_IN <= dist <= R_OUT:
                char = "#"
            elif R_IN - R_SOFT <= dist < R_IN or R_OUT < dist <= R_OUT + R_SOFT:
                char = "."
            else:
                continue

            # Clockwise from 12 o'clock, so the chase reads as a spinner.
            phase = ((angle + 90.0) % 360.0) / 360.0
            cells.append((c, r, char, phase))
    return cells


def _chase(phase):
    """An indefinite opacity pulse, lit as the chase passes this segment."""
    half = LIT_WINDOW / 2.0
    p = min(max(phase, half + 0.001), 1.0 - half - 0.001)
    return (f'<animate attributeName="opacity" begin="0s" dur="{CHASE}s" '
            f'repeatCount="indefinite" values="0.32;0.32;1;0.32;0.32" '
            f'keyTimes="0;{p - half:.4f};{p:.4f};{p + half:.4f};1"/>')


def build(x, y, width, height):
    """Render the card at (x, y) filling width x height. Returns a fragment."""
    parts = [
        f'  <rect x="{x + 0.5:.1f}" y="{y + 0.5:.1f}" '
        f'width="{width - 1:.1f}" height="{height - 1:.1f}" rx="7" '
        f'fill="{PANEL}" stroke="{BORDER}" stroke-width="1"/>\n',
        f'  <text x="{x + PAD:.1f}" y="{y + 19:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">recently worked on</text>\n',
    ]

    ring_x = x + PAD
    ring_y = y + (height - RING_H) / 2.0 + 8

    # Ring and dot. Base opacity is 1, and the chase never freezes, so a
    # renderer without SMIL shows the whole mark lit.
    parts.append(f'  <g font-family="{MONO}" font-size="{FONT}">')
    for col, row, char, phase in mark():
        cx_ = ring_x + col * CHAR_W
        cy_ = ring_y + row * LINE_H + LINE_H - 1.6
        if phase is None:
            parts.append(f'    <text x="{cx_:.1f}" y="{cy_:.1f}" '
                         f'fill="{AMBER}">{char}</text>')
        else:
            parts.append(f'    <text x="{cx_:.1f}" y="{cy_:.1f}" '
                         f'fill="{AMBER}">{char}{_chase(phase)}</text>')
    parts.append("  </g>\n")

    tx = ring_x + RING_W + 22
    mid = y + height / 2.0
    parts.append(
        f'  <text x="{tx:.1f}" y="{mid - 10:.1f}" font-family="{MONO}" '
        f'font-size="14" font-weight="bold" fill="{AMBER}">'
        f'{esc(PROJECT)}</text>\n'
        f'  <text x="{tx:.1f}" y="{mid + 8:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">{esc(META)}</text>\n'
        f'  <text x="{tx:.1f}" y="{mid + 28:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{CYAN}">{esc(NUDGE)}</text>\n')

    return "".join(parts)

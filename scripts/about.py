#!/usr/bin/env python3
"""The about blurb, typed out line by line, as a positionable fragment."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import MONO, TEXT, esc

# Wrapped by hand so the breaks fall in sensible places.
LINES = [
    "I build AI-powered software that solves real problems for real people.",
    "Into LLMs, AI agents, automation and workflow integration - tools that",
    "augment how people work, remove the repetitive, and unlock things that",
    "weren't possible before.",
]

FONT = 15.5
CHAR_W = 9.3          # monospace advance at this size
LINE_H = 24.0
CPS = 55.0            # typing speed, characters per second
LINE_GAP = 0.18       # pause between lines


def build(x, y, delay=0.0, prefix="ab"):
    """Render the blurb at (x, y). Returns (fragment, width, height, end)."""
    parts = []
    cursor_y = y

    for i, text in enumerate(LINES):
        cursor_y += LINE_H
        n = len(text)
        dur = n / CPS
        total = delay + dur
        hold = delay / total
        ident = f"{prefix}{i}"

        # One step per character with calcMode="discrete", which reads as real
        # typing rather than a smooth wipe. The rect's own width is already
        # full and the animation does not freeze, so without SMIL the finished
        # line just shows.
        values = ["0", "0"] + [f"{c * CHAR_W:.1f}" for c in range(1, n + 1)]
        keytimes = ["0", f"{hold:.4f}"] + [
            f"{hold + (1 - hold) * c / n:.4f}" for c in range(1, n + 1)]

        parts.append(
            f'  <clipPath id="{ident}">\n'
            f'    <rect x="{x:.1f}" y="{cursor_y - LINE_H + 4:.1f}" '
            f'width="{n * CHAR_W:.1f}" height="{LINE_H}">\n'
            f'      <animate attributeName="width" begin="0s" '
            f'dur="{total:.2f}s" calcMode="discrete" '
            f'values="{";".join(values)}" keyTimes="{";".join(keytimes)}"/>\n'
            f'    </rect>\n'
            f'  </clipPath>\n'
            f'  <text clip-path="url(#{ident})" x="{x:.1f}" '
            f'y="{cursor_y:.1f}" font-family="{MONO}" font-size="{FONT}" '
            f'fill="{TEXT}">{esc(text)}</text>\n')

        delay = total + LINE_GAP

    width = max(len(line) for line in LINES) * CHAR_W
    return "".join(parts), width, cursor_y - y, delay

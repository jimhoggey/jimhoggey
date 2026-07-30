#!/usr/bin/env python3
"""Render the about blurb as a full-width `cat about.txt` panel.

A neofetch field is one short line, which is the wrong shape for a paragraph.
This gets its own full-width card instead, with each line typed out character
by character.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import (CYAN, DIM, MONO, PURPLE, PURPLE_HI, TEXT, USER,
                   blink_cursor, esc, reveal, window_chrome)

OUT = "about.svg"

# Wrapped by hand so the line breaks fall in sensible places.
LINES = [
    "I build AI-powered software that solves real problems for real people.",
    "Into LLMs, AI agents, automation and workflow integration - tools that",
    "augment how people work, remove the repetitive, and unlock things that",
    "weren't possible before.",
]

WIDTH, HEIGHT = 862, 208
BAR_H = 26
PAD_X = 32.0
FONT = 15.5
CHAR_W = 9.3          # monospace advance at this size
LINE_H = 24.0

CPS = 55.0            # typing speed, characters per second
LINE_GAP = 0.18       # pause between lines


def type_line(text, y, delay, fill=TEXT):
    """A line of text revealed one character at a time.

    Steps a clip rect through one width per character with calcMode="discrete",
    which reads as real typing rather than a smooth wipe. The rect's own width
    is already full, and the animation does not freeze, so a renderer without
    SMIL just shows the finished line.
    """
    n = len(text)
    dur = n / CPS
    total = delay + dur
    hold = delay / total
    ident = f"t{int(y)}"

    # Hold at zero width for the stagger, then one step per character.
    values = ["0", "0"] + [f"{i * CHAR_W:.1f}" for i in range(1, n + 1)]
    keytimes = ["0", f"{hold:.4f}"] + [
        f"{hold + (1 - hold) * i / n:.4f}" for i in range(1, n + 1)]

    return (
        f'  <clipPath id="{ident}">\n'
        f'    <rect x="{PAD_X}" y="{y - LINE_H + 4:.1f}" '
        f'width="{n * CHAR_W:.1f}" height="{LINE_H}">\n'
        f'      <animate attributeName="width" begin="0s" '
        f'dur="{total:.2f}s" calcMode="discrete" '
        f'values="{";".join(values)}" keyTimes="{";".join(keytimes)}"/>\n'
        f'    </rect>\n'
        f'  </clipPath>\n'
        f'  <text clip-path="url(#{ident})" x="{PAD_X}" y="{y:.1f}" '
        f'font-family="{MONO}" font-size="{FONT}" fill="{fill}">'
        f'{esc(text)}</text>\n'), total


def build_svg():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{" ".join(LINES)}">',
        window_chrome(WIDTH, HEIGHT, f"{USER}@github -- cat about.txt", BAR_H),
    ]

    y = BAR_H + 30
    parts.append(
        f'  <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}">'
        f'<tspan fill="{CYAN}">$</tspan>'
        f'<tspan fill="{DIM}"> cat about.txt</tspan>'
        f'{reveal("opacity", 0, 1, 0.15, 0.35)}</text>\n')

    delay = 0.7
    y += 12
    for line in LINES:
        y += LINE_H
        fragment, delay = type_line(line, y, delay)
        parts.append(fragment)
        delay += LINE_GAP

    y += LINE_H + 4
    parts.append(
        f'  <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}">'
        f'<tspan fill="{CYAN}">$</tspan>'
        f'{reveal("opacity", 0, 1, delay, 0.3)}</text>\n')
    parts.append(blink_cursor(PAD_X + CHAR_W * 2, y - LINE_H + 6,
                              w=7, h=14, begin=delay + 0.3, color=PURPLE_HI))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg())
    print(f"wrote {OUT}  ({WIDTH}x{HEIGHT}px, {len(LINES)} lines)")


if __name__ == "__main__":
    main()

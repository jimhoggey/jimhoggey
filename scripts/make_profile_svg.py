#!/usr/bin/env python3
"""Compose every section into one terminal window: profile.svg

Four separate images cannot sit flush in a README -- GitHub puts each in its own
block with margins, and each would carry its own window chrome, so the page
reads as four floating cards rather than one session. One SVG with a single
frame removes the gaps by construction.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import about
import ascii_art
import heatmap
import infocard
import spotlight
from theme import BG, BORDER, CYAN, DIM, MONO, PURPLE_HI, USER, blink_cursor
from theme import prompt as prompt_line
from theme import window_chrome

OUT = "profile.svg"
DATA = os.path.join("data", "contributions.json")

WIDTH = 900
PAD = 26              # left/right content margin
BAR_H = 30            # window title bar
GUTTER = 36           # space between the portrait and the card
SPOTLIGHT_GAP = 40    # space between the heatmap and the spotlight
SECTION_GAP = 30      # blank line between sections
PROMPT_DROP = 22      # from a prompt's baseline to its output


def build(data, card, rows):
    body = []
    y = BAR_H + 26
    delay = 0.15

    # $ ./contributions.sh -- heatmap on the left, spotlight filling the space
    # its other half used to waste.
    body.append(prompt_line(PAD, y, "./contributions.sh", delay))
    y += PROMPT_DROP
    frag, grid_w, height = heatmap.build(PAD, y, data)
    body.append(frag)
    card_x = PAD + grid_w + SPOTLIGHT_GAP
    body.append(spotlight.build(card_x, y, WIDTH - PAD - card_x, height))
    y += height + SECTION_GAP

    # $ cat about.txt
    delay += 0.2
    body.append(prompt_line(PAD, y, "cat about.txt", delay))
    y += PROMPT_DROP - 6
    frag, _, height, delay = about.build(PAD, y, delay + 0.35)
    body.append(frag)
    y += height + SECTION_GAP

    # $ whoami -- portrait on the left, card on the right
    body.append(prompt_line(PAD, y, "whoami", delay))
    y += PROMPT_DROP
    art, art_w, art_h = ascii_art.build(PAD, y + 4, rows)
    body.append(art)
    frag, _, card_h = infocard.build(PAD + art_w + GUTTER, y, card, delay + 0.2)
    body.append(frag)
    y += max(art_h, card_h) + SECTION_GAP - 8

    # Trailing prompt, so the window ends on a live line.
    body.append(
        f'  <text x="{PAD}" y="{y:.1f}" font-family="{MONO}" font-size="13.5">'
        f'<tspan fill="{CYAN}">{USER}@github</tspan>'
        f'<tspan fill="{DIM}"> ~ $</tspan></text>\n')
    body.append(blink_cursor(PAD + 20 * 8.1, y - 11, w=7, h=14,
                             begin=0.0, color=PURPLE_HI))
    height = int(y + 22)

    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" '
            f'aria-label="{USER} on GitHub: {data["total"]} contributions, '
            f'{card["public_repos"]} public repos, {card["stars"]} stars. '
            f'{" ".join(about.LINES)}">\n')

    return (head
            + window_chrome(WIDTH, height, f"{USER}@github -- zsh", BAR_H)
            + "".join(body)
            + "</svg>\n")


def main():
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)

    rows = ascii_art.to_rows(ascii_art.load_image(
        sys.argv[1] if len(sys.argv) > 1 else None))
    card = infocard.gather()

    svg = build(data, card, rows)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(svg)

    height = svg.split('height="', 1)[1].split('"', 1)[0]
    print(f"wrote {OUT}  ({WIDTH}x{height}px, "
          f"{svg.count('<animate')} animations, {len(svg) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render data/contributions.json as an animated contribution heatmap SVG.

53 weeks across, 7 days down. Cells fade and scale in along the diagonal, so
the graph sweeps in from the top-left corner.
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import (BORDER, CYAN, DIM, HEAT, MONO, PURPLE, PURPLE_HI, TEXT,
                   USER, esc, reveal, window_chrome)

SRC = os.path.join("data", "contributions.json")
OUT = "contrib-heatmap.svg"

BAR_H = 26
CELL = 12
GAP = 3
STEP = CELL + GAP
GRID_X = 46           # leaves room for the day-of-week labels
GRID_Y = BAR_H + 20   # leaves room for the month labels
WEEKS = 53
ROWS = 7

WIDTH = GRID_X + WEEKS * STEP + 21
HEIGHT = GRID_Y + ROWS * STEP + 40

DIAG = 0.022          # per-diagonal-step delay
POP = 0.42            # per-cell animation duration

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}


def month_labels(days):
    """One label per month, at the first week column that month appears in."""
    first_of_col = {}
    for day in days:
        col = day["col"]
        if col not in first_of_col or day["date"] < first_of_col[col]:
            first_of_col[col] = day["date"]

    cols = sorted(first_of_col)
    # Key on year-month, not month: a 53-week window starts and ends in the
    # same calendar month, and merging the two would let the one-column stub
    # at the left edge inherit the full month's width.
    month_of = {c: first_of_col[c][:7] for c in cols}
    width = {}
    for c in cols:
        width[month_of[c]] = width.get(month_of[c], 0) + 1

    labels = []
    previous = None
    for col in cols:
        month = month_of[col]
        # Only label a month that owns at least three columns. This drops the
        # partial months at either end, which would otherwise collide with
        # their neighbour and render as "JulAug".
        if month != previous and width[month] >= 3 and col <= WEEKS - 3:
            labels.append((col, MONTHS[int(month[5:7]) - 1]))
        previous = month
    return labels


def build_svg(data):
    days = data["days"]
    today = date.today().isoformat()

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{data["total"]} contributions from {data["start"]} '
        f'to {data["end"]}">',
        "  <defs>",
        '    <filter id="cellglow" x="-50%" y="-50%" width="200%" height="200%">',
        '      <feGaussianBlur stdDeviation="1.6" result="b"/>',
        "      <feMerge>",
        '        <feMergeNode in="b"/>',
        '        <feMergeNode in="SourceGraphic"/>',
        "      </feMerge>",
        "    </filter>",
        "  </defs>",
        window_chrome(WIDTH, HEIGHT, f"{USER}@github -- ./contributions.sh",
                      BAR_H),
    ]

    # Month labels along the top.
    parts.append(f'  <g font-family="{MONO}" font-size="9" fill="{DIM}">')
    for col, name in month_labels(days):
        x = GRID_X + col * STEP
        parts.append(f'    <text x="{x}" y="{GRID_Y - 7}">{name}</text>')
    for row, name in DAY_LABELS.items():
        y = GRID_Y + row * STEP + CELL - 2.5
        parts.append(
            f'    <text x="{GRID_X - 8}" y="{y}" '
            f'text-anchor="end">{name}</text>')
    parts.append("  </g>")

    # The grid. Level 0 cells are static; anything with activity glows.
    plain, lit = [], []
    for day in days:
        if day["col"] >= WEEKS:
            continue
        x = GRID_X + day["col"] * STEP
        y = GRID_Y + day["row"] * STEP
        level = max(0, min(4, day["level"]))
        begin = (day["col"] + day["row"]) * DIAG
        cx, cy = x + CELL / 2, y + CELL / 2

        total = begin + POP
        hold = min(max(begin / total, 0.0), 0.999) if total else 0.0

        head = (f'    <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{HEAT[level]}">\n'
                f'      {reveal("opacity", 0, 1, begin, POP)}\n')

        if level > 0:
            # Scale about the cell's own centre: a scale plus a compensating
            # translate. Only active cells get this -- doing it for all 371
            # would double the file size for a pop nobody sees on an empty day.
            # Neither animation freezes, so both fall back to identity.
            head += (
                f'      <animateTransform attributeName="transform" '
                f'type="scale" begin="0s" dur="{total:.2f}s" '
                f'values="0.2;0.2;1" keyTimes="0;{hold:.4f};1" '
                f'additive="sum"/>\n'
                f'      <animateTransform attributeName="transform" '
                f'type="translate" begin="0s" dur="{total:.2f}s" '
                f'values="{cx * 0.8:.1f} {cy * 0.8:.1f};'
                f'{cx * 0.8:.1f} {cy * 0.8:.1f};0 0" '
                f'keyTimes="0;{hold:.4f};1" additive="sum"/>\n')

        cell = head + "    </rect>\n"

        # Ring today's cell so the graph has an obvious "you are here".
        if day["date"] == today:
            cell += (
                f'    <rect x="{x - 1.5}" y="{y - 1.5}" width="{CELL + 3}" '
                f'height="{CELL + 3}" rx="3.5" fill="none" '
                f'stroke="{PURPLE_HI}" stroke-width="1.2">\n'
                f'      <animate attributeName="opacity" '
                f'values="1;0.3;1" dur="2.4s" begin="{begin + POP:.2f}s" '
                f'repeatCount="indefinite"/>\n'
                f'    </rect>\n')

        (lit if level > 0 else plain).append(cell)

    parts.append("  <g>")
    parts.extend(plain)
    parts.append("  </g>")
    parts.append('  <g filter="url(#cellglow)">')
    parts.extend(lit)
    parts.append("  </g>")

    # Footer: totals on the left, level legend on the right.
    footer_y = GRID_Y + ROWS * STEP + 21
    streak = data["streaks"]
    # Single spaces only: SVG collapses runs of whitespace, so separators have
    # to be real glyphs.
    summary = (f'{data["total"]} contributions · '
               f'{data["active_days"]} active days · '
               f'best day {data["best_day"]} · '
               f'streak {streak["current"]}d (longest {streak["longest"]}d)')
    last_cell = (WEEKS - 1 + ROWS - 1) * DIAG + POP

    parts.append(
        f'  <g font-family="{MONO}" font-size="9.5">'
        f'{reveal("opacity", 0, 1, last_cell, 0.6)}')
    parts.append(
        f'    <text x="{GRID_X}" y="{footer_y}" fill="{DIM}">'
        f'<tspan fill="{CYAN}">&gt;</tspan> <tspan fill="{TEXT}">'
        f'{esc(summary)}</tspan></text>')

    # Right-align the legend: "More" ends at the grid's right edge.
    grid_right = GRID_X + WEEKS * STEP - GAP
    legend_x = grid_right - 30 - 5 * STEP
    parts.append(
        f'    <text x="{legend_x - 8}" y="{footer_y}" text-anchor="end" '
        f'fill="{DIM}">Less</text>')
    for level in range(5):
        parts.append(
            f'    <rect x="{legend_x + level * STEP}" y="{footer_y - 9}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{HEAT[level]}"/>')
    parts.append(
        f'    <text x="{legend_x + 4 * STEP + CELL + 8}" y="{footer_y}" '
        f'fill="{DIM}">More</text>')
    parts.append("  </g>")

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    with open(SRC, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(data))
    print(f"wrote {OUT}  ({WIDTH}x{HEIGHT}px, {len(data['days'])} cells)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""The contribution heatmap as a positionable fragment.

53 weeks across, 7 days down. Cells fade and scale in along the diagonal, so
the grid sweeps in from its top-left corner.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import CYAN, DIM, HEAT, MONO, PURPLE_HI, TEXT, esc, reveal

CELL = 12
GAP = 3
STEP = CELL + GAP
LABEL_W = 30          # gutter for the Mon/Wed/Fri labels
MONTH_H = 18          # gutter for the month labels
WEEKS = 53
ROWS = 7

GRID_W = WEEKS * STEP - GAP
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
    # Key on year-month, not month: a 53-week window opens and closes in the
    # same calendar month, and merging the two lets the one-column stub at the
    # left edge inherit the full month's width.
    month_of = {c: first_of_col[c][:7] for c in cols}
    width = {}
    for c in cols:
        width[month_of[c]] = width.get(month_of[c], 0) + 1

    labels = []
    previous = None
    for col in cols:
        month = month_of[col]
        # Only label a month owning at least three columns, which drops the
        # partial months at either end -- they would otherwise collide with
        # their neighbour and render as "JulAug".
        if month != previous and width[month] >= 3 and col <= WEEKS - 3:
            labels.append((col, MONTHS[int(month[5:7]) - 1]))
        previous = month
    return labels


def build(x, y, data):
    """Render the heatmap at (x, y). Returns (fragment, width, height)."""
    days = data["days"]
    today = date.today().isoformat()
    gx = x + LABEL_W
    gy = y + MONTH_H

    parts = [
        '  <defs>',
        '    <filter id="cellglow" x="-50%" y="-50%" width="200%" '
        'height="200%">',
        '      <feGaussianBlur stdDeviation="1.6" result="b"/>',
        "      <feMerge>",
        '        <feMergeNode in="b"/>',
        '        <feMergeNode in="SourceGraphic"/>',
        "      </feMerge>",
        "    </filter>",
        "  </defs>",
        f'  <g font-family="{MONO}" font-size="9" fill="{DIM}">',
    ]
    for col, name in month_labels(days):
        parts.append(f'    <text x="{gx + col * STEP}" y="{gy - 6}">'
                     f'{name}</text>')
    for row, name in DAY_LABELS.items():
        parts.append(
            f'    <text x="{gx - 8}" y="{gy + row * STEP + CELL - 2.5}" '
            f'text-anchor="end">{name}</text>')
    parts.append("  </g>")

    plain, lit = [], []
    for day in days:
        if day["col"] >= WEEKS:
            continue
        cx_ = gx + day["col"] * STEP
        cy_ = gy + day["row"] * STEP
        level = max(0, min(4, day["level"]))
        begin = (day["col"] + day["row"]) * DIAG
        total = begin + POP
        hold = min(max(begin / total, 0.0), 0.999)
        mid_x, mid_y = cx_ + CELL / 2, cy_ + CELL / 2

        cell = (f'    <rect x="{cx_}" y="{cy_}" width="{CELL}" '
                f'height="{CELL}" rx="2.5" fill="{HEAT[level]}">\n'
                f'      {reveal("opacity", 0, 1, begin, POP)}\n')

        if level > 0:
            # Scale about the cell's own centre: a scale plus a compensating
            # translate. Only active cells get this -- doing it for all 371
            # would double the file size for a pop nobody sees on an empty day.
            cell += (
                f'      <animateTransform attributeName="transform" '
                f'type="scale" begin="0s" dur="{total:.2f}s" '
                f'values="0.2;0.2;1" keyTimes="0;{hold:.4f};1" '
                f'additive="sum"/>\n'
                f'      <animateTransform attributeName="transform" '
                f'type="translate" begin="0s" dur="{total:.2f}s" '
                f'values="{mid_x * 0.8:.1f} {mid_y * 0.8:.1f};'
                f'{mid_x * 0.8:.1f} {mid_y * 0.8:.1f};0 0" '
                f'keyTimes="0;{hold:.4f};1" additive="sum"/>\n')
        cell += "    </rect>\n"

        # Ring today's cell so the grid has an obvious "you are here".
        if day["date"] == today:
            cell += (
                f'    <rect x="{cx_ - 1.5}" y="{cy_ - 1.5}" '
                f'width="{CELL + 3}" height="{CELL + 3}" rx="3.5" fill="none" '
                f'stroke="{PURPLE_HI}" stroke-width="1.2">\n'
                f'      <animate attributeName="opacity" values="1;0.3;1" '
                f'dur="2.4s" begin="{total:.2f}s" '
                f'repeatCount="indefinite"/>\n'
                f'    </rect>\n')

        (lit if level > 0 else plain).append(cell)

    parts.append("  <g>")
    parts.extend(plain)
    parts.append("  </g>")
    parts.append('  <g filter="url(#cellglow)">')
    parts.extend(lit)
    parts.append("  </g>")

    # Footer: totals on the left, level legend right-aligned to the grid.
    footer_y = gy + ROWS * STEP + 15
    streak = data["streaks"]
    # Single spaces only: SVG collapses runs of whitespace, so separators must
    # be real glyphs.
    summary = (f'{data["total"]} contributions · '
               f'{data["active_days"]} active days · '
               f'best day {data["best_day"]} · '
               f'streak {streak["current"]}d (longest {streak["longest"]}d)')
    last_cell = (WEEKS - 1 + ROWS - 1) * DIAG + POP

    parts.append(f'  <g font-family="{MONO}" font-size="9.5">'
                 f'{reveal("opacity", 0, 1, last_cell, 0.6)}')
    parts.append(f'    <text x="{gx}" y="{footer_y}" fill="{DIM}">'
                 f'<tspan fill="{CYAN}">&gt;</tspan> '
                 f'<tspan fill="{TEXT}">{esc(summary)}</tspan></text>')

    right = gx + GRID_W
    legend_x = right - 30 - 5 * STEP
    parts.append(f'    <text x="{legend_x - 8}" y="{footer_y}" '
                 f'text-anchor="end" fill="{DIM}">Less</text>')
    for level in range(5):
        parts.append(
            f'    <rect x="{legend_x + level * STEP}" y="{footer_y - 9}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{HEAT[level]}"/>')
    parts.append(
        f'    <text x="{legend_x + 4 * STEP + CELL + 8}" y="{footer_y}" '
        f'fill="{DIM}">More</text>')
    parts.append("  </g>")

    return "\n".join(parts) + "\n", LABEL_W + GRID_W, footer_y - y + 5

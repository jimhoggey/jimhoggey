#!/usr/bin/env python3
"""Sanity-check profile.svg and build two preview pages under scratch/.

  scratch/preview.html         -- <object> embed, so SMIL actually runs
  scratch/preview-static.html  -- every <animate*> stripped, which is exactly
                                  what a renderer without SMIL support shows

The static page is the one that matters: if the profile looks right there, it
also looks right in GitHub's mobile app, in feed readers, and anywhere else that
renders SVG without a timeline.
"""

import os
import re
import shutil
import sys
import xml.dom.minidom

TARGET = "profile.svg"
OUT_DIR = "scratch"
ANIM = re.compile(r"<animate(?:Transform|Motion)?\b[^>]*/>|"
                  r"<animate(?:Transform|Motion)?\b.*?</animate"
                  r"(?:Transform|Motion)?>", re.S)

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ background:#0d1117; margin:0; padding:24px;
         font:14px -apple-system,system-ui,sans-serif; }}
  .wrap {{ width:{w}px; margin:0 auto; }}
  object {{ display:block; width:100%; }}
</style>
<div class="wrap">
  <object type="image/svg+xml" data="{src}" width="{w}" height="{h}"></object>
</div>
"""


def dims(path):
    root = xml.dom.minidom.parse(path).documentElement
    return (float(root.getAttribute("width")),
            float(root.getAttribute("height")))


def check_timing(path):
    """Validate every animation's SMIL timing attributes.

    A mismatched values/keyTimes count, or keyTimes that do not run 0..1
    monotonically, makes a renderer drop the animation silently -- the SVG still
    displays, so the only symptom is that nothing moves.
    """
    errors = []
    doc = xml.dom.minidom.parse(path)

    for tag in ("animate", "animateTransform"):
        for el in doc.getElementsByTagName(tag):
            attr = el.getAttribute("attributeName")
            values = [v for v in el.getAttribute("values").split(";") if v]
            keytimes = [k for k in el.getAttribute("keyTimes").split(";") if k]
            splines = [s for s in el.getAttribute("keySplines").split(";") if s]
            where = f"<{tag} {attr}>"

            if not values:
                errors.append(f"{where} has no values")
                continue

            if keytimes:
                if len(keytimes) != len(values):
                    errors.append(f"{where} {len(values)} values vs "
                                  f"{len(keytimes)} keyTimes")
                nums = [float(k) for k in keytimes]
                if nums[0] != 0.0 or abs(nums[-1] - 1.0) > 1e-9:
                    errors.append(f"{where} keyTimes must span 0..1, got "
                                  f"{nums[0]}..{nums[-1]}")
                if any(b < a for a, b in zip(nums, nums[1:])):
                    errors.append(f"{where} keyTimes not monotonic")

            if el.getAttribute("calcMode") == "spline":
                if len(splines) != len(values) - 1:
                    errors.append(f"{where} needs {len(values) - 1} "
                                  f"keySplines, got {len(splines)}")

            if not el.getAttribute("dur"):
                errors.append(f"{where} has no dur")

            # Every animation must land on the element's own attribute value,
            # either by not freezing or by looping forever. Freezing would mean
            # the fallback state is unreachable.
            if el.getAttribute("fill") == "freeze":
                errors.append(f"{where} freezes, so it cannot fall back")
            if (not el.getAttribute("repeatCount")
                    and el.getAttribute("begin") != "0s"):
                errors.append(f"{where} begins at "
                              f"'{el.getAttribute('begin')}', not 0s")

    return errors


def check_bounds(path):
    """Nothing should be positioned outside the canvas."""
    errors = []
    width, height = dims(path)
    doc = xml.dom.minidom.parse(path)

    for el in doc.getElementsByTagName("text"):
        xs = el.getAttribute("x").split()
        if not xs:
            continue
        right = max(float(v) for v in xs)
        if right > width - 4:
            errors.append(f"text at x={right:.0f} exceeds width {width:.0f}: "
                          f"{el.firstChild.nodeValue[:30] if el.firstChild else ''!r}")
        y = el.getAttribute("y")
        if y and float(y) > height:
            errors.append(f"text at y={y} exceeds height {height:.0f}")

    return errors


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    raw = open(TARGET, encoding="utf-8").read()
    shutil.copy(TARGET, os.path.join(OUT_DIR, TARGET))

    static = ANIM.sub("", raw)
    static_name = TARGET.replace(".svg", "-static.svg")
    with open(os.path.join(OUT_DIR, static_name), "w", encoding="utf-8") as fh:
        fh.write(static)

    problems = []
    xml.dom.minidom.parseString(static)
    for bad in ('opacity="0"', 'width="0"', 'fill="freeze"'):
        if bad in static:
            problems.append(f"fallback state contains {bad}")

    problems += check_timing(TARGET) + check_bounds(TARGET)

    w, h = dims(TARGET)
    print(f"  {TARGET}  {int(w)}x{int(h)}px  {len(raw) / 1024:.1f} KB  "
          f"{raw.count('<animate')} animations")

    looping = raw.count('repeatCount="indefinite"')
    print(f"  {looping} looping animations "
          f"(ASCII re-renders every {int(__import__('ascii_art').CYCLE)}s)")

    for kind, src in (("preview", TARGET), ("preview-static", static_name)):
        with open(os.path.join(OUT_DIR, f"{kind}.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(PAGE.format(title=kind, src=src, w=int(w), h=int(h)))

    if problems:
        print("\nFAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK -- parses, degrades visibly, stays in bounds")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())

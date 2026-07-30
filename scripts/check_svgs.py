#!/usr/bin/env python3
"""Build two preview pages under scratch/ and sanity-check the SVGs.

  scratch/preview.html         -- <object> embeds, so SMIL actually runs
  scratch/preview-static.html  -- every <animate*> stripped, which is exactly
                                  what a renderer without SMIL support shows

The static page is the one that matters: if the profile looks right there, it
also looks right in GitHub's mobile app, in feed readers, and anywhere else
that renders SVG without a timeline.
"""

import os
import re
import shutil
import sys
import xml.dom.minidom

SVGS = ["contrib-heatmap.svg", "about.svg", "ascii.svg", "info-card.svg"]
OUT_DIR = "scratch"
ANIM = re.compile(r"<animate(?:Transform|Motion)?\b[^>]*/>|"
                  r"<animate(?:Transform|Motion)?\b.*?</animate"
                  r"(?:Transform|Motion)?>", re.S)

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ background:#0d1117; color:#c9d1d9;
         font:14px -apple-system,system-ui,sans-serif; margin:0; padding:28px; }}
  .wrap {{ width:900px; margin:0 auto; text-align:center; }}
  h3 {{ font-family:ui-monospace,monospace; font-weight:400; color:#8b949e; }}
  table {{ margin:0 auto; border-collapse:collapse; }}
  td {{ padding:0; vertical-align:top; }}
  object {{ display:block; pointer-events:none; }}
</style>
<div class="wrap">
  <h3><code>jimhoggey@github ~ $ ./contributions.sh</code></h3>
  <object type="image/svg+xml" data="{h}" width="860" height="191"></object>
  <h3><code>jimhoggey@github ~ $ cat about.txt</code></h3>
  <object type="image/svg+xml" data="{b}" width="860" height="208"></object>
  <h3><code>jimhoggey@github ~ $ whoami</code></h3>
  <table><tr>
    <td><object type="image/svg+xml" data="{a}" width="370" height="389"></object></td>
    <td><object type="image/svg+xml" data="{i}" width="490" height="390"></object></td>
  </tr></table>
</div>
"""


def dims(path):
    root = xml.dom.minidom.parse(path).documentElement
    return float(root.getAttribute("width")), float(root.getAttribute("height"))


def check_timing(path):
    """Validate every animation's SMIL timing attributes.

    A mismatched values/keyTimes count, or keyTimes that do not run 0..1
    monotonically, makes a renderer drop the animation silently -- the SVG
    still displays, so the only symptom is that nothing moves.
    """
    errors = []
    doc = xml.dom.minidom.parse(path)

    for tag in ("animate", "animateTransform"):
        for el in doc.getElementsByTagName(tag):
            attr = el.getAttribute("attributeName")
            values = [v for v in el.getAttribute("values").split(";") if v]
            keytimes = [k for k in el.getAttribute("keyTimes").split(";") if k]
            splines = [s for s in el.getAttribute("keySplines").split(";") if s]
            where = f"{path}: <{tag} {attr}>"

            if not values:
                errors.append(f"{where} has no values")
                continue

            if keytimes:
                if len(keytimes) != len(values):
                    errors.append(f"{where} {len(values)} values vs "
                                  f"{len(keytimes)} keyTimes")
                nums = [float(k) for k in keytimes]
                if nums[0] != 0.0 or abs(nums[-1] - 1.0) > 1e-9:
                    errors.append(f"{where} keyTimes must span 0..1, "
                                  f"got {nums[0]}..{nums[-1]}")
                if any(b < a for a, b in zip(nums, nums[1:])):
                    errors.append(f"{where} keyTimes not monotonic: {nums}")

            if el.getAttribute("calcMode") == "spline":
                if len(splines) != len(values) - 1:
                    errors.append(f"{where} needs {len(values) - 1} "
                                  f"keySplines, got {len(splines)}")

            if not el.getAttribute("dur"):
                errors.append(f"{where} has no dur")

            # Everything except the endless blink/pulse must reach its base
            # value, which means running from 0 and not freezing.
            if not el.getAttribute("repeatCount"):
                if el.getAttribute("begin") != "0s":
                    errors.append(f"{where} begins at "
                                  f"'{el.getAttribute('begin')}', not 0s")
                if el.getAttribute("fill") == "freeze":
                    errors.append(f"{where} freezes, so it cannot fall back")

    return errors


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    problems = []

    for name in SVGS:
        raw = open(name, encoding="utf-8").read()
        shutil.copy(name, os.path.join(OUT_DIR, name))

        static = ANIM.sub("", raw)
        static_name = name.replace(".svg", "-static.svg")
        with open(os.path.join(OUT_DIR, static_name), "w",
                  encoding="utf-8") as fh:
            fh.write(static)

        # A stripped copy must still parse, and must not leave anything
        # permanently hidden or collapsed.
        xml.dom.minidom.parseString(static)
        for bad in ('opacity="0"', 'width="0"', 'fill="freeze"'):
            if bad in static:
                problems.append(f"{name}: fallback state contains {bad}")

        problems.extend(check_timing(name))

        w, h = dims(name)
        print(f"  {name:22} {int(w)}x{int(h)}  "
              f"{len(raw) / 1024:5.1f} KB  "
              f"{raw.count('<animate'):4d} animations")

    # The two lower cards must render the same height side by side.
    aw, ah = dims("ascii.svg")
    iw, ih = dims("info-card.svg")
    left, right = 370.0, 490.0
    lh, rh = left * ah / aw, right * ih / iw
    print(f"\n  side-by-side heights: ascii {lh:.1f}px, card {rh:.1f}px "
          f"(delta {abs(lh - rh):.1f}px)")
    if abs(lh - rh) > 6:
        problems.append(f"card heights differ by {abs(lh - rh):.1f}px")

    hw, _ = dims("contrib-heatmap.svg")
    print(f"  heatmap {int(hw)}px wide, displayed at 860 "
          f"= {int(left)} + {int(right)}")

    for kind, suffix in (("preview", ".svg"), ("preview-static", "-static.svg")):
        with open(os.path.join(OUT_DIR, f"{kind}.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(PAGE.format(
                title=kind,
                h=SVGS[0].replace(".svg", suffix),
                b=SVGS[1].replace(".svg", suffix),
                a=SVGS[2].replace(".svg", suffix),
                i=SVGS[3].replace(".svg", suffix)))

    if problems:
        print("\nFAIL")
        for p in problems:
            print("  -", p)
        return 1
    print(f"\nOK -- all {len(SVGS)} parse, degrade visibly, and line up")
    return 0


if __name__ == "__main__":
    sys.exit(main())

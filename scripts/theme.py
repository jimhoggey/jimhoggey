"""Shared palette and helpers for the profile SVG generators.

Neon purple / cyan terminal theme, picked to match the avatar's glowing
sunglasses. Every generator imports from here so the three SVGs stay in sync.
"""

USER = "jimhoggey"

# --- palette ---------------------------------------------------------------
BG = "#0b0912"          # window background
PANEL = "#100e1a"       # inner panel
BORDER = "#2b2440"      # 1px frame
TITLEBAR = "#171327"    # window chrome
TEXT = "#ded9ec"        # primary text
DIM = "#6f6790"         # labels, secondary text
PURPLE = "#b57bff"      # primary accent
PURPLE_HI = "#d9b8ff"   # highlight
CYAN = "#5ff0ff"        # secondary accent
MAGENTA = "#ff7bd5"     # tertiary accent

# Contribution levels 0-4, dark -> bright purple.
HEAT = ["#181327", "#3a2370", "#6337bd", "#9a63ff", "#cbaaff"]

# Traffic-light dots in the fake window chrome.
DOTS = ["#ff5f57", "#febc2e", "#28c840"]

MONO = ("ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"
        "'DejaVu Sans Mono','Liberation Mono',monospace")


def esc(text):
    """Escape a string for use as SVG text content."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def window_chrome(width, height, label, bar_h=26):
    """Frame + title bar shared by all three SVGs.

    Returns the SVG fragment for the window shell. Callers draw their own
    content below `bar_h`.
    """
    return f"""  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="9"
        fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  <path d="M0.5 9.5a9 9 0 0 1 9-9h{width - 20}a9 9 0 0 1 9 9v{bar_h - 10}H0.5z"
        fill="{TITLEBAR}"/>
  <line x1="0.5" y1="{bar_h}" x2="{width - 0.5}" y2="{bar_h}"
        stroke="{BORDER}" stroke-width="1"/>
  <circle cx="16" cy="{bar_h / 2}" r="4" fill="{DOTS[0]}"/>
  <circle cx="31" cy="{bar_h / 2}" r="4" fill="{DOTS[1]}"/>
  <circle cx="46" cy="{bar_h / 2}" r="4" fill="{DOTS[2]}"/>
  <text x="{width / 2}" y="{bar_h / 2 + 3.5}" text-anchor="middle"
        font-family="{MONO}" font-size="9.5" fill="{DIM}">{esc(label)}</text>
"""


def reveal(attr, hidden, shown, delay, dur, splines=None):
    """A staggered reveal that degrades to the visible state.

    The obvious way to stagger an entrance is `opacity="0"` plus an animation
    that freezes at 1. But anything that renders SVG without running SMIL --
    GitHub's mobile app, feed readers, some screenshot pipelines -- then shows
    a permanently blank image.

    So instead the element's own attribute holds the *final* value, and this
    animation runs from t=0, sitting on `hidden` for the stagger before easing
    to `shown`. It deliberately does not freeze: when it ends the attribute
    falls back to the element's own value, which is already correct. No SMIL
    means no animation and a fully visible image.
    """
    total = delay + dur
    if total <= 0:
        return ""

    hold = min(max(delay / total, 0.0), 0.999)
    extra = ""
    if splines:
        extra = f' calcMode="spline" keySplines="0 0 1 1;{splines}"'

    return (f'<animate attributeName="{attr}" begin="0s" dur="{total:.2f}s" '
            f'values="{hidden};{hidden};{shown}" '
            f'keyTimes="0;{hold:.4f};1"{extra}/>')


def prompt(x, y, command, delay, font=13.5, dur=0.35):
    """A `user@github ~ $ command` line introducing a section."""
    return (f'  <text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" '
            f'font-size="{font}">'
            f'<tspan fill="{CYAN}">{USER}@github</tspan>'
            f'<tspan fill="{DIM}"> ~ $ </tspan>'
            f'<tspan fill="{TEXT}">{esc(command)}</tspan>'
            f'{reveal("opacity", 0, 1, delay, dur)}</text>\n')


def blink_cursor(x, y, w=5, h=10, begin=0.0, color=PURPLE):
    """A block cursor that blinks forever, and sits solid if SMIL is off."""
    return f"""  <rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" fill="{color}">
    <animate attributeName="opacity" values="1;1;0;0;1" dur="1.1s"
             begin="{begin:.2f}s" repeatCount="indefinite"/>
  </rect>
"""

#!/usr/bin/env python3
"""Render a neofetch-style info card SVG from live GitHub API data.

The article generates this once by hand. Pulling it from the API instead means
repo counts, star totals and the language mix never go stale -- the daily
workflow re-renders it alongside the heatmap.

Set GITHUB_TOKEN to lift the unauthenticated rate limit (the workflow does).
"""

import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import (BORDER, CYAN, DIM, MAGENTA, MONO, PURPLE, PURPLE_HI, TEXT,
                   USER, blink_cursor, esc, reveal, window_chrome)

OUT = "info-card.svg"
API = "https://api.github.com"

# Hand-written lines: the things an API cannot infer.
FOCUS = "church tech - computer vision - small sharp tools"
STACK = "python - astro - typescript - opencv - tensorflow"
STATUS = "vibing"

# Sized so that, laid out at 490px next to ascii.svg at 370px, both cards
# render the same height in the README table.
WIDTH, HEIGHT = 552, 439
BAR_H = 26
PAD_X = 22.0
LABEL_W = 92.0        # gutter before values, keeps the colons aligned

FONT = 11.0
ROW_STEP = 17.5

BAR_X = 118.0
BAR_W = 330.0
BAR_H_PX = 7.0

ROW_DELAY = 0.085
FADE = 0.45


def session():
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": f"{USER}-profile-art",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        sess.headers["Authorization"] = f"Bearer {token}"
    return sess


def get(sess, path):
    resp = sess.get(f"{API}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def gather():
    sess = session()
    user = get(sess, f"/users/{USER}")

    repos, page = [], 1
    while True:
        batch = get(sess, f"/users/{USER}/repos?per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned = [r for r in repos if not r.get("fork")]

    # Sum language bytes across owned repos for a weighted, honest mix.
    langs = {}
    for repo in owned:
        try:
            for name, size in get(
                    sess, f"/repos/{USER}/{repo['name']}/languages").items():
                langs[name] = langs.get(name, 0) + size
        except requests.HTTPError:
            continue   # a repo can vanish or 404 mid-run; skip it

    created = datetime.strptime(
        user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    months = (now.year - created.year) * 12 + (now.month - created.month)
    if now.day < created.day:
        months -= 1

    return {
        "name": user.get("name") or USER,
        "blog": (user.get("blog") or "").replace("https://", "")
                                        .replace("http://", "") or "-",
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "stars": sum(r.get("stargazers_count", 0) for r in owned),
        "created": created,
        "uptime": f"{months // 12} years, {months % 12} months",
        "langs": sorted(langs.items(), key=lambda kv: -kv[1])[:5],
        "lang_total": sum(langs.values()) or 1,
        "top_repos": sorted(
            [r for r in owned if not r.get("private")],
            key=lambda r: (-r.get("stargazers_count", 0),
                           r.get("pushed_at") or ""))[:3],
        "synced": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def row(y, label, value, delay, value_fill=TEXT):
    """One `label : value` line that fades in from the left."""
    total = delay + FADE
    hold = min(max(delay / total, 0.0), 0.999)
    return (
        f'  <g>\n'
        f'    {reveal("opacity", 0, 1, delay, FADE)}\n'
        f'    <animateTransform attributeName="transform" type="translate" '
        f'begin="0s" dur="{total:.2f}s" values="-8 0;-8 0;0 0" '
        f'keyTimes="0;{hold:.4f};1"/>\n'
        f'    <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}" fill="{PURPLE}">{esc(label)}</text>\n'
        f'    <text x="{PAD_X + LABEL_W - 10}" y="{y:.1f}" '
        f'font-family="{MONO}" font-size="{FONT}" fill="{DIM}">:</text>\n'
        f'    <text x="{PAD_X + LABEL_W}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}" fill="{value_fill}">{esc(value)}</text>\n'
        f'  </g>\n')


def lang_bar(y, name, pct, delay, color):
    """A language name, a filled proportion bar, and its percentage."""
    fill_w = max(2.0, BAR_W * pct / 100.0)
    return (
        f'  <g>\n'
        f'    {reveal("opacity", 0, 1, delay, FADE)}\n'
        f'    <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{TEXT}">{esc(name[:12])}</text>\n'
        f'    <rect x="{BAR_X}" y="{y - BAR_H_PX + 1:.1f}" width="{BAR_W}" '
        f'height="{BAR_H_PX}" rx="3.5" fill="{BORDER}" opacity="0.55"/>\n'
        f'    <rect x="{BAR_X}" y="{y - BAR_H_PX + 1:.1f}" '
        f'width="{fill_w:.1f}" height="{BAR_H_PX}" rx="3.5" fill="{color}">\n'
        f'      {reveal("width", 0, f"{fill_w:.1f}", delay, 0.9, "0.22 1 0.36 1")}\n'
        f'    </rect>\n'
        f'    <text x="{BAR_X + BAR_W + 8}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">{pct:.1f}%</text>\n'
        f'  </g>\n')


def build_svg(d):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Profile summary for {USER}">',
        window_chrome(WIDTH, HEIGHT, f"{USER} -- neofetch", BAR_H),
    ]

    # Header: user@github, then a rule.
    hy = BAR_H + 26
    parts.append(
        f'  <g>{reveal("opacity", 0, 1, 0.1, 0.5)}\n'
        f'    <text x="{PAD_X}" y="{hy}" font-family="{MONO}" '
        f'font-size="13.5" font-weight="bold">'
        f'<tspan fill="{PURPLE_HI}">{USER}</tspan>'
        f'<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{CYAN}">github</tspan></text>\n'
        f'    <line x1="{PAD_X}" y1="{hy + 9}" x2="{WIDTH - PAD_X}" '
        f'y2="{hy + 9}" stroke="{BORDER}" stroke-width="1"/>\n'
        f'  </g>\n')

    rows = [
        ("name", d["name"], TEXT),
        ("web", d["blog"], CYAN),
        ("uptime", f'{d["uptime"]}  (since {d["created"]:%b %Y})', TEXT),
        ("repos", f'{d["public_repos"]} public · '
                  f'{d["stars"]} stars · {d["followers"]} followers', TEXT),
        ("focus", FOCUS, TEXT),
        ("stack", STACK, TEXT),
        ("status", STATUS, MAGENTA),
        ("synced", d["synced"], DIM),
    ]

    y = hy + 30
    delay = 0.25
    for label, value, fill in rows:
        parts.append(row(y, label, value, delay, fill))
        y += ROW_STEP
        delay += ROW_DELAY

    # Language mix.
    y += 12
    parts.append(
        f'  <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">languages by bytes'
        f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')

    palette = [PURPLE_HI, PURPLE, CYAN, MAGENTA, "#7c5cff"]
    y += 18
    delay += ROW_DELAY
    for i, (name, size) in enumerate(d["langs"]):
        pct = 100.0 * size / d["lang_total"]
        parts.append(lang_bar(y, name, pct, delay, palette[i % len(palette)]))
        y += 16.5
        delay += ROW_DELAY

    # Most-starred public repos, filling the space above the prompt.
    y += 14
    delay += ROW_DELAY
    parts.append(
        f'  <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">pinned by stars'
        f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')

    y += 16
    for repo in d["top_repos"]:
        delay += ROW_DELAY
        stars = repo.get("stargazers_count", 0)
        lang = (repo.get("language") or "-").lower()
        parts.append(
            f'  <text x="{PAD_X}" y="{y:.1f}" font-family="{MONO}" '
            f'font-size="9.5">'
            f'<tspan fill="{PURPLE_HI}">{esc(repo["name"][:26])}</tspan>'
            f'<tspan fill="{DIM}"> · {esc(lang)} · {stars}★</tspan>'
            f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')
        y += 15

    # Prompt footer. The cursor sits one cell past the prompt, measured from
    # the string length rather than a guessed offset.
    footer_y = HEIGHT - 16
    prompt = f"{USER}@github ~ $ "
    cursor_x = PAD_X + len(prompt) * 6.0
    parts.append(
        f'  <text x="{PAD_X}" y="{footer_y}" font-family="{MONO}" '
        f'font-size="10">'
        f'<tspan fill="{CYAN}">{USER}@github</tspan>'
        f'<tspan fill="{DIM}"> ~ $</tspan>'
        f'{reveal("opacity", 0, 1, delay + 0.2, 0.4)}</text>\n')
    parts.append(blink_cursor(cursor_x, footer_y - 8, w=6, h=11,
                             begin=delay + 0.5, color=CYAN))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    data = gather()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(data))
    print(f"wrote {OUT}  ({WIDTH}x{HEIGHT}px, "
          f"{len(data['langs'])} languages, {data['stars']} stars)")


if __name__ == "__main__":
    main()

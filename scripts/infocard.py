#!/usr/bin/env python3
"""The neofetch-style summary, built from live GitHub API data.

Pulling this from the API rather than hand-writing it means repo counts, star
totals and the language mix never go stale -- the daily workflow re-renders it.

Set GITHUB_TOKEN to lift the unauthenticated rate limit (the workflow does).
Only public endpoints are read, so nothing private can reach the card.
"""

import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import (BORDER, CYAN, DIM, MAGENTA, MONO, PURPLE, PURPLE_HI, TEXT,
                   USER, esc, reveal)

API = "https://api.github.com"

# Hand-written lines: the things an API cannot infer.
FOCUS = "LLMs · AI agents · automation · workflow integration"
STACK = "python · javascript · + whatever the model swears is best"
STATUS = "in the flow state, building AI that actually helps people"

FONT = 11.0
ROW_STEP = 17.5
LABEL_W = 76.0        # gutter before values, keeps the colons aligned
BAR_OFF = 84.0
BAR_W = 260.0
BAR_H = 7.0

ROW_DELAY = 0.085
FADE = 0.45


def _session():
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": f"{USER}-profile-art",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        sess.headers["Authorization"] = f"Bearer {token}"
    return sess


def _get(sess, path):
    resp = sess.get(f"{API}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def gather():
    """Everything the card needs, from the public API."""
    sess = _session()
    user = _get(sess, f"/users/{USER}")

    repos, page = [], 1
    while True:
        batch = _get(sess, f"/users/{USER}/repos?per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned = [r for r in repos if not r.get("fork")]

    # Sum language bytes across owned repos for a weighted, honest mix.
    langs = {}
    for repo in owned:
        try:
            for name, size in _get(
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
            owned, key=lambda r: (-r.get("stargazers_count", 0),
                                  r.get("pushed_at") or ""))[:3],
        "synced": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def _row(x, y, label, value, delay, fill):
    total = delay + FADE
    hold = min(max(delay / total, 0.0), 0.999)
    return (
        f'  <g>\n'
        f'    {reveal("opacity", 0, 1, delay, FADE)}\n'
        f'    <animateTransform attributeName="transform" type="translate" '
        f'begin="0s" dur="{total:.2f}s" values="-8 0;-8 0;0 0" '
        f'keyTimes="0;{hold:.4f};1"/>\n'
        f'    <text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}" fill="{PURPLE}">{esc(label)}</text>\n'
        f'    <text x="{x + LABEL_W - 10:.1f}" y="{y:.1f}" '
        f'font-family="{MONO}" font-size="{FONT}" fill="{DIM}">:</text>\n'
        f'    <text x="{x + LABEL_W:.1f}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="{FONT}" fill="{fill}">{esc(value)}</text>\n'
        f'  </g>\n')


def _lang_bar(x, y, name, pct, delay, color):
    fill_w = max(2.0, BAR_W * pct / 100.0)
    bx = x + BAR_OFF
    return (
        f'  <g>\n'
        f'    {reveal("opacity", 0, 1, delay, FADE)}\n'
        f'    <text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{TEXT}">{esc(name[:12])}</text>\n'
        f'    <rect x="{bx:.1f}" y="{y - BAR_H + 1:.1f}" width="{BAR_W}" '
        f'height="{BAR_H}" rx="3.5" fill="{BORDER}" opacity="0.55"/>\n'
        f'    <rect x="{bx:.1f}" y="{y - BAR_H + 1:.1f}" '
        f'width="{fill_w:.1f}" height="{BAR_H}" rx="3.5" fill="{color}">\n'
        f'      {reveal("width", 0, f"{fill_w:.1f}", delay, 0.9, "0.22 1 0.36 1")}\n'
        f'    </rect>\n'
        f'    <text x="{bx + BAR_W + 8:.1f}" y="{y:.1f}" '
        f'font-family="{MONO}" font-size="9.5" fill="{DIM}">'
        f'{pct:.1f}%</text>\n'
        f'  </g>\n')


def build(x, y, d, delay=0.0):
    """Render the card at (x, y). Returns (fragment, width, height)."""
    parts = []

    hy = y + 14
    parts.append(
        f'  <g>{reveal("opacity", 0, 1, delay, 0.5)}\n'
        f'    <text x="{x:.1f}" y="{hy:.1f}" font-family="{MONO}" '
        f'font-size="13.5" font-weight="bold">'
        f'<tspan fill="{PURPLE_HI}">{USER}</tspan>'
        f'<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{CYAN}">github</tspan></text>\n'
        f'    <line x1="{x:.1f}" y1="{hy + 9:.1f}" '
        f'x2="{x + BAR_OFF + BAR_W + 50:.1f}" y2="{hy + 9:.1f}" '
        f'stroke="{BORDER}" stroke-width="1"/>\n'
        f'  </g>\n')

    rows = [
        ("name", d["name"], TEXT),
        ("web", d["blog"], CYAN),
        ("uptime", f'{d["uptime"]} (since {d["created"]:%b %Y})', TEXT),
        ("repos", f'{d["public_repos"]} public · {d["stars"]} stars · '
                  f'{d["followers"]} followers', TEXT),
        ("focus", FOCUS, TEXT),
        ("stack", STACK, TEXT),
        ("status", STATUS, MAGENTA),
        ("synced", d["synced"], DIM),
    ]

    cy = hy + 26
    delay += ROW_DELAY
    for label, value, fill in rows:
        parts.append(_row(x, cy, label, value, delay, fill))
        cy += ROW_STEP
        delay += ROW_DELAY

    cy += 10
    parts.append(
        f'  <text x="{x:.1f}" y="{cy:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">languages by bytes'
        f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')

    palette = [PURPLE_HI, PURPLE, CYAN, MAGENTA, "#7c5cff"]
    cy += 17
    delay += ROW_DELAY
    for i, (name, size) in enumerate(d["langs"]):
        parts.append(_lang_bar(x, cy, name,
                               100.0 * size / d["lang_total"],
                               delay, palette[i % len(palette)]))
        cy += 16.5
        delay += ROW_DELAY

    cy += 12
    parts.append(
        f'  <text x="{x:.1f}" y="{cy:.1f}" font-family="{MONO}" '
        f'font-size="9.5" fill="{DIM}">pinned by stars'
        f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')

    cy += 16
    for repo in d["top_repos"]:
        delay += ROW_DELAY
        parts.append(
            f'  <text x="{x:.1f}" y="{cy:.1f}" font-family="{MONO}" '
            f'font-size="9.5">'
            f'<tspan fill="{PURPLE_HI}">{esc(repo["name"][:26])}</tspan>'
            f'<tspan fill="{DIM}"> · {esc((repo.get("language") or "-").lower())}'
            f' · {repo.get("stargazers_count", 0)}★</tspan>'
            f'{reveal("opacity", 0, 1, delay, FADE)}</text>\n')
        cy += 15

    return "".join(parts), BAR_OFF + BAR_W + 50, cy - y

#!/usr/bin/env python3
"""Scrape the public contribution calendar into data/contributions.json.

Uses https://github.com/users/<user>/contributions, the same HTML fragment the
profile page requests. It needs no token and no API quota.

Only publicly visible contributions appear here -- that is what the profile
page itself shows.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import USER

URL = f"https://github.com/users/{USER}/contributions"
OUT = os.path.join("data", "contributions.json")

CELL_ID = re.compile(r"contribution-day-component-(\d+)-(\d+)$")
LEADING_INT = re.compile(r"^\s*(\d[\d,]*)")


def fetch_html():
    resp = requests.get(URL, timeout=30, headers={
        "User-Agent": f"{USER}-profile-art",
        "Accept": "text/html",
        "X-Requested-With": "XMLHttpRequest",
    })
    resp.raise_for_status()
    return resp.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # Counts live in sr-only <tool-tip> elements keyed to each cell's id.
    tips = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if target:
            tips[target] = tip.get_text(strip=True)

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        cell_id = td.get("id") or ""
        match = CELL_ID.search(cell_id)
        if not date or not match:
            continue

        # "No contributions on ..." -> 0, "12 contributions on ..." -> 12
        count = 0
        number = LEADING_INT.match(tips.get(cell_id, ""))
        if number:
            count = int(number.group(1).replace(",", ""))

        days.append({
            "date": date,
            "count": count,
            "level": int(td.get("data-level") or 0),
            "row": int(match.group(1)),   # day of week, 0 = Sunday
            "col": int(match.group(2)),   # week index
        })

    if not days:
        raise SystemExit("no contribution cells found -- the page layout "
                         "may have changed")

    days.sort(key=lambda d: d["date"])
    return days


def streaks(days):
    """Current and longest run of consecutive days with contributions."""
    today = datetime.now(timezone.utc).date().isoformat()
    past = [d for d in days if d["date"] <= today]

    longest = run = 0
    for day in past:
        run = run + 1 if day["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    for day in reversed(past):
        if day["count"] > 0:
            current += 1
        else:
            break

    return {"current": current, "longest": longest}


def main():
    days = parse(fetch_html())
    payload = {
        "user": USER,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "start": days[0]["date"],
        "end": days[-1]["date"],
        "total": sum(d["count"] for d in days),
        "best_day": max(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"] > 0),
        "weeks": days[-1]["col"] + 1,
        "streaks": streaks(days),
        "days": days,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")

    print(f"wrote {OUT}  ({payload['total']} contributions, "
          f"{payload['active_days']} active days, "
          f"{payload['start']} -> {payload['end']})")


if __name__ == "__main__":
    main()

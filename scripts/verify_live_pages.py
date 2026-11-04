#!/usr/bin/env python3
"""Verify every published race page and its independent dataset on GitHub Pages."""
from __future__ import annotations

import json
import sys
import time
from urllib.request import Request, urlopen

from update_races import RACES

BASE = "https://mbp8912.github.io/fec-48hour-dashboard/"
PAGES = [("", "NY-17")] + [(slug, cfg["district"]) for slug, cfg in RACES.items()]
HEADERS = {"User-Agent": "FEC-district-pages-deployment-check/1.0"}


def load(url: str):
    with urlopen(Request(url, headers=HEADERS), timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} at {url}")
        if "/fec-48hour-dashboard/" not in response.geturl().lower():
            raise RuntimeError(f"Unexpected redirect from {url}: {response.geturl()}")
        return response.read()


def verify():
    approved=load(BASE+"ca-13/spiros-consulting-logo.png")
    shared=load(BASE+"race-assets/spiros-consulting-logo.png")
    if shared!=approved or not shared.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise RuntimeError("Published shared Spiros logo differs from approved CA-13 PNG")
    for slug, district in PAGES:
        url = BASE + (slug + "/" if slug else "")
        html = load(url).decode("utf-8")
        if f"<title>{district} |" not in html:
            raise RuntimeError(f"{district} page has incorrect title at {url}")
        if district == "CA-13":
            if 'class="ca13-spiros-logo"' not in html or 'src="./spiros-consulting-logo.png"' not in html:
                raise RuntimeError("CA-13 trial logo is missing")
            logo = load(url + "spiros-consulting-logo.png")
            if not logo.startswith(bytes.fromhex("89504e470d0a1a0a")) or len(logo) < 1000:
                raise RuntimeError("Spiros Consulting PNG not deployed at CA-13")
        else:
            expected=("./race-assets/" if not slug else "../race-assets/")+"spiros-consulting-logo.png"
            if ('class="topbar spiros-branded-header"' not in html or
                'class="spiros-header-logo"' not in html or
                f'src="{expected}"' not in html or
                'alt="Spiros Consulting"' not in html):
                raise RuntimeError(f"Spiros logo or header missing from {district}")
        data = json.loads(load(url + "data/data.json"))
        if data.get("status") != "ok":
            raise RuntimeError(f"{district} still lacks a verified dataset at {url}")
        count = len(data.get("contributions", []))
        print(f"{district}: HTTP 200, correct title, verified dataset ({count} entries) — {url}", flush=True)


    # Prediction contest is hosted alongside the FEC pages. Verify that the
    # live site received the score data, not merely that deployment succeeded.
    contest_url = BASE + "predictions/"
    contest_html = load(contest_url).decode("utf-8")
    if "<title>Spiros Election Night Contest 2026</title>" not in contest_html:
        raise RuntimeError("Prediction contest HTML or heading did not deploy")
    if "Spiros Election Night <span>Contest 2026</span>" not in contest_html:
        raise RuntimeError("Prediction contest heading is missing")
    picks = json.loads(load(contest_url + "picks.json"))
    calls = json.loads(load(contest_url + "calls.json"))
    if len(picks.get("people", [])) != 20 or len(picks.get("races", [])) != 18:
        raise RuntimeError("Prediction contest lost participants or races")
    roster = {race["id"]: race for race in picks["races"]}
    verified = 0
    for race_id, call in calls.get("calls", {}).items():
        if (race_id not in roster or call.get("calledBy") != "AP" or
            call.get("winner") not in [c["name"] for c in roster[race_id]["candidates"]]):
            raise RuntimeError(f"Unverified or mismatched AP race winner in {race_id}")
        verified += 1
    if verified < 14:
        raise RuntimeError(f"Only {verified} verified AP calls deployed; expected at least 14")
    print(f"Prediction contest: HTTP 200, 20 participants, 18 races, "
          f"{verified} verified AP calls — {contest_url}", flush=True)


if __name__ == "__main__":
    for attempt in range(1, 7):
        try:
            verify()
            print("All 9 fundraising dashboards verified with the Spiros logo and intact datasets.", flush=True)
            raise SystemExit(0)
        except Exception as exc:
            print(f"Deployment check {attempt}/6: {exc}", file=sys.stderr, flush=True)
            if attempt == 6:
                raise SystemExit(1)
            time.sleep(8)

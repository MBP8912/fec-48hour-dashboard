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
        elif "spiros-consulting-logo.png" in html:
            raise RuntimeError(f"Trial logo incorrectly appears in {district}")
        data = json.loads(load(url + "data/data.json"))
        if data.get("status") != "ok":
            raise RuntimeError(f"{district} still lacks a verified dataset at {url}")
        count = len(data.get("contributions", []))
        print(f"{district}: HTTP 200, correct title, verified dataset ({count} entries) — {url}", flush=True)


if __name__ == "__main__":
    for attempt in range(1, 7):
        try:
            verify()
            print("All 9 dashboards verified at their renamed public URLs.", flush=True)
            raise SystemExit(0)
        except Exception as exc:
            print(f"Deployment check {attempt}/6: {exc}", file=sys.stderr, flush=True)
            if attempt == 6:
                raise SystemExit(1)
            time.sleep(8)

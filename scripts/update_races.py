#!/usr/bin/env python3
"""Eight independent 2026 general-election Form 6 archives, reusing the NY17 parser."""
from __future__ import annotations
import sys
import os
import re
import html
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import update_data as fec

ROOT = Path(__file__).resolve().parents[1]
RACES = {
  "co-4": {
    "district": "CO-4",
    "republican": {
      "name": "Lauren Boebert",
      "short": "Boebert",
      "committee": "Lauren Boebert for Congress",
      "id": "C00728238"
    },
    "democratic": {
      "name": "Eileen Laubacher",
      "short": "Laubacher",
      "committee": "Eileen for Colorado",
      "id": "C00904284"
    }
  },
  "co-5": {
    "district": "CO-5",
    "republican": {
      "name": "Jeff Crank",
      "short": "Crank",
      "committee": "Jeff Crank for Congress",
      "id": "C00865592"
    },
    "democratic": {
      "name": "Jessica Killin",
      "short": "Killin",
      "committee": "Killin for Colorado",
      "id": "C00911941"
    }
  },
  "ia-1": {
    "district": "IA-1",
    "republican": {
      "name": "Mariannette Miller-Meeks",
      "short": "Miller-Meeks",
      "committee": "Miller-Meeks for Congress",
      "id": "C00558825"
    },
    "democratic": {
      "name": "Christina Bohannan",
      "short": "Bohannan",
      "committee": "Christina Bohannan for Congress",
      "id": "C00787820"
    }
  },
  "mn-1": {
    "district": "MN-1",
    "republican": {
      "name": "Brad Finstad",
      "short": "Finstad",
      "committee": "Finstad for Congress",
      "id": "C00807743"
    },
    "democratic": {
      "name": "Jake Johnson",
      "short": "Johnson",
      "committee": "Jake Johnson for Congress",
      "id": "C00902684"
    }
  },
  "ne-2": {
    "district": "NE-2",
    "republican": {
      "name": "Brinker Harding",
      "short": "Harding",
      "committee": "Brinker Harding for Congress",
      "id": "C00909515"
    },
    "democratic": {
      "name": "Denise Powell",
      "short": "Powell",
      "committee": "Denise Powell for Congress",
      "id": "C00903948"
    }
  },
  "wi-1": {
    "district": "WI-1",
    "republican": {
      "name": "Bryan Steil",
      "short": "Steil",
      "committee": "Steil for Wisconsin, Inc.",
      "id": "C00677286"
    },
    "democratic": {
      "name": "Mitchell Berman",
      "short": "Berman",
      "committee": "Mitchell Berman for Congress",
      "id": "C00915637"
    }
  },
  "ny-19": {
    "district": "NY-19",
    "republican": {
      "name": "Peter Oberacker",
      "short": "Oberacker",
      "committee": "Peter for NY Inc",
      "id": "C00921668"
    },
    "democratic": {
      "name": "Josh Riley",
      "short": "Riley",
      "committee": "Josh Riley for Congress",
      "id": "C00793760"
    }
  },
  "ca-13": {
    "district": "CA-13",
    "republican": {
      "name": "Kevin Lincoln",
      "short": "Lincoln",
      "committee": "Kevin Lincoln for Congress",
      "id": "C00845826"
    },
    "democratic": {
      "name": "Adam Gray",
      "short": "Gray",
      "committee": "Adam Gray for Congress",
      "id": "C00801431"
    }
  }
}


# Check all nine dashboards at once rather than spending the FEC shared
# DEMO_KEY allowance on one API query per committee.
NY17 = {
    "district": "NY-17",
    "republican": {"name": "Mike Lawler", "short": "Lawler", "committee": "Lawler for Congress, Inc.", "id": "C00815415"},
    "democratic": {"name": "Cait Conley", "short": "Conley", "committee": "Cait for New York", "id": "C00900431"}
}
ALL_RACES = {"ny-17": NY17, **RACES}
ALL_IDS = {v["id"] for race in ALL_RACES.values() for v in (race["republican"], race["democratic"])}
RSS_URL = "https://efilingapps.fec.gov/rss/generate?preDefinedFilingType=ALL"


def index_from_api():
    """Search up to 24 pages across ALL 18 committees in one filtered query."""
    grouped = {cid: [] for cid in ALL_IDS}
    api_key = os.environ.get("FEC_API_KEY") or "DEMO_KEY"
    for page in range(1, 25):
        query = {
            "api_key": api_key, "committee_id": sorted(ALL_IDS),
            "form_type": "F6", "min_receipt_date": fec.FILED_FROM,
            "max_receipt_date": fec.FILED_THROUGH, "per_page": 100,
            "page": page, "sort": "-receipt_date"
        }
        url = "https://api.open.fec.gov/v1/efile/filings/?" + urlencode(query, doseq=True)
        # Avoid wasting several minutes retrying shared DEMO_KEY 429 responses:
        # fail over immediately to the Commission's public official RSS feed.
        data = fec.fetch_url(url, tries=1)
        batch = data.get("results")
        if not isinstance(batch, list):
            raise ValueError("Unexpected FEC efiling API result; do not publish")
        for item in batch:
            committee = str(item.get("committee_id") or "").upper()
            if committee in grouped and str(item.get("form_type") or "").upper().startswith("F6"):
                grouped[committee].append(item)
        pages = (data.get("pagination") or {}).get("pages")
        if not batch or (pages and page >= pages) or len(batch) < 100:
            return grouped
    raise RuntimeError("FEC efiling pagination exceeded limit, refusing incomplete results")


def parse_rss(rss_bytes, committee_ids=ALL_IDS):
    """Read FEC's official 7-day efiling feed and only retain target F6 notices."""
    root = ET.fromstring(rss_bytes)
    result = {cid: [] for cid in committee_ids}
    found = set()
    for item in root.findall(".//item"):
        description = html.unescape(item.findtext("description", default=""))
        fields = {
            key.lower(): value.strip()
            for key, value in re.findall(r"([A-Za-z]+)\s*:\s*([^|*<>]+)", description)
        }
        cid = fields.get("committeeid", "").upper()
        form = fields.get("formtype", "").upper()
        file_number = fec.positive_int(fields.get("filingid"))
        if cid not in result or not re.fullmatch(r"F6(?:[NAT])?", form) or not file_number:
            continue
        pub_date = item.findtext("pubDate", default="")
        try:
            filed = parsedate_to_datetime(pub_date).astimezone(fec.ZoneInfo("America/New_York")).date()
        except (TypeError, ValueError, IndexError, OverflowError):
            continue
        if not (date(2026, 10, 1) <= filed <= date(2026, 11, 10)):
            continue
        if (cid, file_number) in found:
            continue
        found.add((cid, file_number))
        result[cid].append({
            "committee_id": cid, "file_number": file_number, "form_type": form,
            "filed_date": filed.isoformat()
        })
    return result


def index_from_rss():
    req = Request(RSS_URL, headers={"User-Agent": fec.AGENT, "Accept": "application/rss+xml,application/xml,*/*"})
    with urlopen(req, timeout=45) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("FEC RSS exceeded expected maximum size")
    result = parse_rss(raw)
    if not any(result.values()):
        raise RuntimeError("FEC RSS had no matching recent Form 6 notices; keep archived data")
    return result


def get_filing_index():
    try:
        grouped = index_from_api()
        print("FEC index: one batched API request series for all 18 committees.", flush=True)
        return grouped
    except Exception as exc:
        print(f"FEC API unavailable ({exc}); switching to official seven-day RSS efiling feed.", flush=True)
        grouped = index_from_rss()
        print("FEC RSS fallback: " + str(sum(map(len, grouped.values()))) + " recent Form 6 notice(s).", flush=True)
        return grouped


def update_one(slug, race, grouped):
    if slug == "ny-17":
        destination = ROOT / "data"
    else:
        destination = ROOT / slug / "data"
    destination.mkdir(parents=True, exist_ok=True)
    fec.CACHE_FILE = destination / "cache.json"
    fec.OUTPUT_FILE = destination / "data.json"
    # The dashboard's internal chart keys retain the names of the original
    # reference page; each publication still has independently verified IDs.
    fec.COMMITTEES = {
        "lawler": {
            "name": race["republican"]["committee"],
            "id": race["republican"]["id"],
            "candidate": race["republican"]["name"]
        },
        "conley": {
            "name": race["democratic"]["committee"],
            "id": race["democratic"]["id"],
            "candidate": race["democratic"]["name"]
        }
    }
    fec.KNOWN_F6_FILINGS = {"lawler": [2033856]} if slug == "ny-17" else {}
    fec.main(prefetched_by_committee=grouped)


def main():
    try:
        grouped = get_filing_index()
    except Exception as exc:
        print(f"FEC filing discovery failed; retaining all archived data: {exc}", file=sys.stderr, flush=True)
        return 1
    failures = []
    for slug, race in ALL_RACES.items():
        print("--- " + race["district"] + " ---", flush=True)
        try:
            update_one(slug, race, grouped)
        except Exception as exc:
            print(f"ERROR: {slug} refresh failed; preserving its verified archive: {exc}", file=sys.stderr, flush=True)
            failures.append(slug)
    if failures:
        print("Incomplete refresh: " + ", ".join(failures), file=sys.stderr, flush=True)
        return 1
    print("All nine independent FEC district datasets refreshed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

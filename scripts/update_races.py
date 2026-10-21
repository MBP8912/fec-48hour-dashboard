#!/usr/bin/env python3
"""Eight independent 2026 general-election Form 6 archives, reusing the NY17 parser."""
from __future__ import annotations
import sys
from pathlib import Path
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

def update_one(slug, race):
    destination = ROOT / slug / "data"
    destination.mkdir(parents=True, exist_ok=True)
    fec.CACHE_FILE = destination / "cache.json"
    fec.OUTPUT_FILE = destination / "data.json"
    # The existing NY17 dashboard uses these same two *internal chart keys*.
    # Here 'lawler' is the Republican chart slot and 'conley' the Democrat.
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
    fec.KNOWN_F6_FILINGS = {}
    fec.main()

def main():
    failures = []
    for slug, race in RACES.items():
        print("--- " + race["district"] + " ---", flush=True)
        try:
            update_one(slug, race)
        except Exception as exc:
            # Keep each previously verified dataset on source/network failures.
            print(f"ERROR: {slug} refresh failed; preserving prior data: {exc}", file=sys.stderr, flush=True)
            failures.append(slug)
    if failures:
        print("Incomplete refresh: " + ", ".join(failures), file=sys.stderr, flush=True)
        return 1
    print("All eight independently archived race datasets refreshed.", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

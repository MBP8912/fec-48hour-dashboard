"""Offline verification of eight separately deployed and archived district dashboards."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_races import RACES

class RaceDashboardTests(unittest.TestCase):
    def test_exactly_eight_races_and_sixteen_disjoint_committees(self):
        self.assertEqual(len(RACES), 8)
        ids = []
        for slug, race in RACES.items():
            self.assertEqual(slug, race["district"].lower())
            for party in ("republican", "democratic"):
                cid = race[party]["id"]
                self.assertRegex(cid, r"^C\d{8}$")
                ids.append(cid)
        self.assertEqual(len(set(ids)), 16)

    def test_html_candidates_and_popup_fields(self):
        shared = (ROOT / "race-assets" / "app.js").read_text()
        self.assertIn("contribution.employer", shared)
        self.assertIn("contribution.occupation", shared)
        self.assertIn("const COMMITTEE_IDS = {lawler:CONFIG.republican.id", shared)
        for slug, race in RACES.items():
            html = (ROOT / slug / "index.html").read_text()
            self.assertIn(race["district"] + " 48-Hour Report Fundraising 2026", html)
            self.assertEqual(html.count('<th scope="col"'), 4)
            prefix = '<script id="race-config" type="application/json">'
            payload = html.split(prefix)[1].split("</script>")[0]
            settings = json.loads(payload)
            self.assertEqual(settings["slug"], slug)
            for party in ("republican", "democratic"):
                self.assertEqual(settings[party]["id"], race[party]["id"])
                self.assertIn(race[party]["name"], html)

    def test_independent_cached_data(self):
        for slug, race in RACES.items():
            d = ROOT / slug / "data"
            archive = json.loads((d / "cache.json").read_text())
            public = json.loads((d / "data.json").read_text())
            self.assertEqual(archive["schema_version"], 1)
            self.assertIn(public["status"], ("not_initialized", "ok"))
            valid_ids = {race["republican"]["id"], race["democratic"]["id"]}
            for contribution in public.get("contributions", []):
                self.assertIn(contribution["committee_id"], valid_ids)
            for filing in archive["filings"].values():
                self.assertIn(filing["committee_id"], valid_ids)

if __name__ == "__main__":
    unittest.main()

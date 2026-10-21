"""Offline verification of eight separately deployed and archived district dashboards."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_races import RACES, ALL_RACES, ALL_IDS, parse_rss

class RaceDashboardTests(unittest.TestCase):
    def test_single_index_includes_ny17_and_eight_other_races(self):
        self.assertEqual(len(RACES), 8)
        self.assertEqual(len(ALL_RACES), 9)
        self.assertEqual(len(ALL_IDS), 18)

    def test_official_rss_fallback_extracts_only_relevant_forms(self):
        fixture = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
<title>New Filing By Steil</title>
<description>&lt;p&gt;F6N&lt;/p&gt;*********CommitteeId: C00677286 | FilingId: 2033555 | FormType: F6N | CoverageFrom: | CoverageThrough: *********</description>
<pubDate>Wed, 21 Oct 2026 18:00:00 GMT</pubDate>
</item><item>
<description>*********CommitteeId: C00921668 | FilingId: 2033556 | FormType: F6A | CoverageFrom: | CoverageThrough: *********</description>
<pubDate>Wed, 21 Oct 2026 18:00:00 GMT</pubDate></item><item>
<description>*********CommitteeId: C00677286 | FilingId: 2033557 | FormType: F3N | CoverageFrom: | CoverageThrough: *********</description>
<pubDate>Wed, 21 Oct 2026 18:00:00 GMT</pubDate></item></channel></rss>'''
        result = parse_rss(fixture)
        self.assertEqual(len(result["C00677286"]), 1)
        self.assertEqual(len(result["C00921668"]), 1)
        self.assertEqual(result["C00677286"][0]["file_number"], 2033555)
        self.assertEqual(result["C00677286"][0]["filed_date"], "2026-10-21")
        self.assertEqual(result["C00921668"][0]["form_type"], "F6A")
        self.assertEqual(sum(map(len, result.values())), 2)

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

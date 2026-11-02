import unittest
from datetime import datetime,timezone
from refresh_ny import parse_page,build_snapshot

class NYResultsTests(unittest.TestCase):
    def setUp(self):
        self.page='''<html><body>
           <h1>New York State Unofficial Election Night Results</h1>
           <div>10/29/2026 11:38:17 AM | Election General Election</div>
           <h3>17th Congressional District > All Counties (Active Registered Voters: 528,603) Election Districts Reporting: 60 of 679</h3>
           <table><tr><th>Candidate</th><th>Party</th></tr>
           <tr><td>Cait Conley</td><td>DEM</td><td></td><td>54.5 %</td><td>34,000</td><td></td><td>56.8 %</td><td>36,000</td></tr>
           <tr><td></td><td>WOR</td><td></td><td>3.2 %</td><td>2,000</td></tr>
           <tr><td>Mike Lawler</td><td>REP</td><td></td><td>40.0 %</td><td>25,000</td><td></td><td>43.2 %</td><td>27,000</td></tr>
           <tr><td></td><td>CON</td><td></td><td>3.2 %</td><td>2,000</td></tr></table>
           <h3>19th Congressional District > All Counties (Active Registered Voters: 518,603) Election Districts Reporting: 0 of 654</h3>
           <table><tr><td>Josh Riley</td><td>DEM</td><td>0.00 %</td><td>0</td><td>0.00 %</td><td>0</td></tr>
           <tr><td>Peter K. Oberacker</td><td>REP</td><td>0.00 %</td><td>0</td><td>0.00 %</td><td>0</td></tr></table>
           </body></html>'''
    def test_vote_by_candidate_not_ballot_line(self):
        r=parse_page(self.page)
        self.assertEqual([x['votes'] for x in r['races']['NY-17']['candidates']],[36000,27000])
        self.assertEqual(r['races']['NY-17']['precincts_reporting'],60)
        self.assertEqual(r['races']['NY-17']['precincts_total'],679)
        self.assertEqual(r['races']['NY-19']['candidates'][0]['votes'],0)
    def test_timestamp_must_not_show_preclose_results(self):
        page=parse_page(self.page)
        snapshot=build_snapshot(page,None,datetime(2026,11,4,12,tzinfo=timezone.utc))
        self.assertTrue(snapshot['test_data'])
    def test_missing_congressional_contest_rejected(self):
        with self.assertRaisesRegex(ValueError,'NY-19'):
            parse_page(self.page.replace('19th Congressional District','20th Congressional District'))

if __name__=='__main__':unittest.main()

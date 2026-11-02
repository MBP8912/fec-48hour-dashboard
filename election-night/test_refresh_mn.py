import unittest
from datetime import datetime,timezone
from refresh_mn import parse_mn1,build_snapshot,CLOSE_UTC

class MinnesotaResultsTests(unittest.TestCase):
    def test_district_specific_county_rows_and_no_double_count(self):
        counties={str(i).zfill(2):f'County {i}' for i in range(1,15)}
        records=[]
        for i in range(1,14):
            cid=str(i).zfill(2)
            records.append(f'MN;{cid};;0104;U.S. Representative District 1;1;0401;Jake Johnson;;;DFL;8;9;100;60.00;200')
            records.append(f'MN;{cid};;0104;U.S. Representative District 1;1;0302;Brad Finstad;;;R;8;9;100;40.00;200')
        records.append('MN;01;;0105;U.S. Representative District 2;2;0302;Different Person;;;R;9;9;999;100.00;999')
        parsed=parse_mn1('\n'.join(records),counties)
        self.assertEqual(len(parsed),13)
        self.assertEqual(sum(c['candidates'][0]['votes'] for c in parsed),1300)
        self.assertTrue(all(c['precincts_total']==9 for c in parsed))

    def test_precincts_reporting_are_not_estimated_ballots(self):
        counties={str(i).zfill(2):f'County {i}' for i in range(1,15)}
        rows=[f'MN;{str(i).zfill(2)};;0104;U.S. Representative District 1;1;0302;Brad Finstad;;;R;6;9;100;100.00;100' for i in range(1,14)]
        parsed=parse_mn1('\n'.join(rows),counties)
        self.assertEqual(parsed[0]['precincts_reporting'],6)
        self.assertEqual(parsed[0]['precincts_total'],9)

    def test_never_show_pre_close_test_data(self):
        now=CLOSE_UTC.replace(hour=1)
        snap=build_snapshot(now,[{'name':'A','votes':100}],None)
        self.assertTrue(snap['test_data'])
        after=CLOSE_UTC.replace(hour=3)
        snap2=build_snapshot(after,[{'name':'A','votes':100}],snap)
        self.assertTrue(snap2['test_data'])
        snap3=build_snapshot(after,[{'name':'A','votes':101}],snap2)
        self.assertFalse(snap3['test_data'])

if __name__=='__main__': unittest.main()

import unittest
from datetime import datetime,timezone
from refresh_ca import parse_files,build_snapshot

class CaliforniaResultsTests(unittest.TestCase):
  def setUp(self):
    self.c='\n'.join(['C|CAS|10|3561|Adam|Gray|Democratic','C|CAS|11|3868|Kevin|Lincoln|Republican'])
    self.s='\n'.join([f'S|CAS|99|{k}|{v}' for k,v in [('10','Fresno'),('20','Madera'),('24','Merced'),('39','San Joaquin'),('50','Stanislaus')]])
    rows=['B|CAS|1|20261103|2045000']
    for k,num in [('59',50),('10',10),('20',10),('24',10),('39',10),('50',10)]:
      rows.append(f'V|CAS|25|110000130000|{k}|1|10||3561|{num}|50.0|50.0|3868|{num*2}|50.0|50.0')
    self.v='\n'.join('['+x+']' for x in rows)
  def test_district_vote_counties_and_no_double_count(self):
    a=parse_files(self.v,self.c,self.s)
    self.assertEqual(len(a['counties']),5)
    self.assertEqual(a['counties'][0]['candidates'][0]['name'],'Adam Gray')
    self.assertEqual(sum(x['candidates'][0]['votes'] for x in a['counties']),50)
    self.assertEqual(a['counties'][0]['precincts_reporting'],1)
  def test_reject_non_reconciling_county_votes(self):
    with self.assertRaisesRegex(ValueError,'reconcile'):
      parse_files(self.v.replace('59|1|10','59|1|10').replace('59|1|10','59|1|10').replace('59|1|10','59|1|10').replace('|59|1|10||3561|50','|59|1|10||3561|49'),self.c,self.s)
  def test_preclose_mock_values_hidden(self):
    a=parse_files(self.v,self.c,self.s)
    b=build_snapshot(a,datetime(2026,11,3,23,tzinfo=timezone.utc))
    self.assertTrue(b['test_data'])

if __name__=='__main__':unittest.main()

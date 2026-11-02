import unittest
from datetime import timedelta
from refresh_ne import parse_county,build_snapshot,CLOSE_UTC

class NebraskaResultTests(unittest.TestCase):
 def test_ne2_candidate_values_and_ignores_other_contests(self):
  html='''<html><body><h1>General Election November 3, 2026</h1>
   <h2>Douglas County Results</h2>
   <h3>For Representative in Congress - 2 Year Term - District 01</h3><p>Different Candidate</p>
   <h3>For Representative in Congress - 2 Year Term - District 02</h3>
   <span>Vote Centers Fully: 0 / 334</span>
   <h3>Brinker Harding</h3><p>Republican</p><div>1,200</div>
   <h3>Denise Powell</h3><p>Democratic</p><div>3,400</div>
   <h3>Eric Michael Foreman</h3><p>Libertarian</p><div>101</div>
   <h3>For Governor and Lt. Governor</h3><h4>Brinker Harding</h4><p>10,000</p>
   </body></html>'''
  r=parse_county(html,'Douglas')
  self.assertEqual([x['votes'] for x in r['candidates']],[1200,3400,101])
  self.assertIsNone(r['precincts_reporting'])
 def test_no_preclose_test_data(self):
  c=[{'name':'Douglas','candidates':[{'name':'Brinker Harding','party':'R','votes':3}]}]
  a=build_snapshot(CLOSE_UTC-timedelta(hours=2),c,None)
  self.assertTrue(a['test_data'])
  b=build_snapshot(CLOSE_UTC+timedelta(hours=1),c,a)
  self.assertTrue(b['test_data'])
  c[0]['candidates'][0]['votes']=4
  newer=build_snapshot(CLOSE_UTC+timedelta(hours=1),c,b)
  self.assertFalse(newer['test_data'])

if __name__=='__main__':unittest.main()

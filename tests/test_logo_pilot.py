"""The approved CA-13 Spiros PNG brands all nine 48-hour fundraising pages."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OTHER=("co-4","co-5","ia-1","mn-1","ne-2","wi-1","ny-19")
class TestSpirosBranding(unittest.TestCase):
    def test_approved_ca13_pilot_remains_intact(self):
        logo=ROOT/"ca-13"/"spiros-consulting-logo.png"
        self.assertTrue(logo.is_file())
        self.assertGreater(logo.stat().st_size,1000)
        self.assertTrue(logo.read_bytes().startswith(bytes.fromhex("89504e470d0a1a0a")))
        html=(ROOT/"ca-13"/"index.html").read_text(encoding="utf-8")
        self.assertIn('class="ca13-spiros-logo"',html)
        self.assertIn('src="./spiros-consulting-logo.png"',html)
        self.assertIn('alt="Spiros Consulting"',html)
    def test_shared_png_is_byte_identical_to_approved_pilot(self):
        self.assertEqual((ROOT/"race-assets"/"spiros-consulting-logo.png").read_bytes(),
                         (ROOT/"ca-13"/"spiros-consulting-logo.png").read_bytes())
    def test_other_eight_dashboards_have_identical_header_placement(self):
        for path in (ROOT/"index.html",)+tuple(ROOT/name/"index.html" for name in OTHER):
            with self.subTest(path=str(path)):
                html=path.read_text(encoding="utf-8")
                self.assertEqual(html.count('class="spiros-header-logo"'),1)
                self.assertIn('class="topbar spiros-branded-header"',html)
                self.assertIn('alt="Spiros Consulting"',html)
                self.assertLess(html.index("spiros-header-logo"),html.index("<main>"))
                expected=("./race-assets/" if path==ROOT/"index.html" else "../race-assets/")+"spiros-consulting-logo.png"
                self.assertIn('src="'+expected+'"',html)
                self.assertIn("styles.css?v=20261023-spiros-all-races-v1",html)
    def test_shared_stylesheet_has_mobile_logo_rules(self):
        for name in ("assets/styles.css","race-assets/styles.css"):
            css=(ROOT/name).read_text(encoding="utf-8")
            self.assertIn(".spiros-branded-header",css)
            self.assertIn(".spiros-header-logo",css)
            self.assertIn("@media(max-width:680px)",css)
            self.assertIn("@media(max-width:400px)",css)
    def test_pages_workflow_publishes_shared_and_ca13_pngs(self):
        code=(ROOT/".github/workflows/update-and-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("race-assets/spiros-consulting-logo.png _site/race-assets/",code)
        self.assertIn("cp ca-13/spiros-consulting-logo.png _site/ca-13/",code)
if __name__=="__main__":
    unittest.main()

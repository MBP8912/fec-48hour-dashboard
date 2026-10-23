"""The Spiros logo trial must remain restricted to CA-13 Form 6 pages."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OTHER=("co-4","co-5","ia-1","mn-1","ne-2","wi-1","ny-19")

class TestLogoPilot(unittest.TestCase):
    def test_ca13_asset_and_html(self):
        path=ROOT/"ca-13"/"spiros-consulting-logo.png"
        self.assertTrue(path.is_file())
        self.assertTrue(path.read_bytes().startswith(bytes.fromhex("89504e470d0a1a0a")))
        page=(ROOT/"ca-13"/"index.html").read_text(encoding="utf-8")
        self.assertIn('class="topbar ca13-branded-header"',page)
        self.assertIn('src="./spiros-consulting-logo.png"',page)
        self.assertIn('alt="Spiros Consulting"',page)
        self.assertIn("CA-13 48-Hour Report Fundraising 2026",page)

    def test_other_races_unbranded(self):
        for name in ("index.html",)+(tuple(r+"/index.html" for r in OTHER)):
            with self.subTest(page=name):
                text=(ROOT/name).read_text(encoding="utf-8")
                self.assertNotIn("spiros-consulting-logo.png",text)
                self.assertNotIn("ca13-branded-header",text)

    def test_pages_workflow_publishes_logo(self):
        s=(ROOT/".github"/"workflows"/"update-and-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("cp ca-13/spiros-consulting-logo.png _site/ca-13/",s)

if __name__=="__main__":
    unittest.main()

"""Regression guard for hosted release/downstream reconciliation retirement."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILES=(
 ".github/workflows/downstream-propagation.yml",
 ".github/workflows/reconcile-published-release.yml",
 ".github/workflows/reconcile-release-activation.yml",
)

class ReleaseReconciliationHostedAuthorityRetirementTests(unittest.TestCase):
    def test_workflows_are_read_only(self):
        forbidden=("contents: write","actions: write","issues: write","git push","git commit","gh issue ","gh workflow run","github.token","GH_TOKEN:","${{ secrets.","gh release ")
        for rel in FILES:
            text=(ROOT/rel).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token,text,rel)
            self.assertIn("contents: read",text,rel)
            self.assertIn("VALIDATION_TRANSPORT_ONLY",text,rel)
            self.assertIn("actions/upload-artifact@v4",text,rel)
            self.assertIn("authority_effect",text,rel)
            self.assertIn("NONE",text,rel)
            if "actions/checkout@v4" in text:
                self.assertIn("persist-credentials: false",text,rel)

if __name__=="__main__":
    unittest.main()

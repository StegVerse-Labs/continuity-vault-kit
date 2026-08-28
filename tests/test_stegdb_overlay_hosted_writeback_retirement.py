"""Regression guard for hosted StegDB overlay writeback retirement."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILES=(
 ".github/workflows/sync-knowledgevault-overlay-from-stegdb.yml",
 ".github/workflows/sync-overlay-from-stegdb.yml",
)

class StegDBOverlayHostedWritebackRetirementTests(unittest.TestCase):
    def test_overlay_sync_is_candidate_only(self):
        for rel in FILES:
            text=(ROOT/rel).read_text(encoding="utf-8")
            for token in ("contents: write","git push","git commit","github.token","GH_TOKEN:","${{ secrets."):
                self.assertNotIn(token,text,rel)
            for token in ("contents: read","persist-credentials: false","VALIDATION_TRANSPORT_ONLY","NON_HOSTED_REPOSITORY_SYNC_REQUIRED","repository_mutation_performed","git_push_performed","actions/upload-artifact@v4","authority_effect","NONE"):
                self.assertIn(token,text,rel)

if __name__=="__main__":
    unittest.main()

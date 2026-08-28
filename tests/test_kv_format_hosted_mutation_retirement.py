"""Regression guard for hosted KV format branch mutation retirement."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/kv-format-branch.yml"

class KVFormatHostedMutationRetirementTests(unittest.TestCase):
    def test_format_workflow_is_candidate_only(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for token in ("contents: write","git push","git commit","github.token","GH_TOKEN:","${{ secrets."):
            self.assertNotIn(token,text,token)
        for token in ("contents: read","persist-credentials: false","VALIDATION_TRANSPORT_ONLY","NON_HOSTED_FORMAT_PATCH_APPLICATION","repository_mutation_performed","git_push_performed","actions/upload-artifact@v4","authority_effect","NONE"):
            self.assertIn(token,text,token)

if __name__=="__main__":
    unittest.main()

"""Repository-wide hosted workflow authority invariant."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW_ROOT=ROOT/".github/workflows"

class GlobalHostedWorkflowAuthorityTests(unittest.TestCase):
    def test_all_workflows_declare_permissions_and_no_authority_markers(self):
        forbidden=(
            "contents: write","actions: write","issues: write","pull-requests: write",
            "id-token: write","packages: write","deployments: write",
            "git push","git commit","git tag","gh release ","gh workflow run",
            "github.token","GH_TOKEN:","${{ secrets.",
            "aws-actions/configure-aws-credentials","terraform apply","kubectl apply",
            "helm upgrade","repository_dispatch",
        )
        workflows=sorted(WORKFLOW_ROOT.glob("*.yml"))
        self.assertEqual(len(workflows),44)
        for path in workflows:
            text=path.read_text(encoding="utf-8")
            self.assertIn("permissions:",text,path.name)
            for token in forbidden:
                self.assertNotIn(token,text,path.name)

if __name__=="__main__":
    unittest.main()

"""Repository-wide hosted workflow authority invariant.

G17 (StegVerse-Labs/.github#167/#168): the exact-count pin (EXPECTED_WORKFLOW_COUNT)
is replaced by control/workflow-surface-registry.json - the workflow files must be
exactly the registered surfaces (tests/test_workflow_surface_registry.py fails closed
otherwise). The authority-marker scan covers the live surfaces, the verbatim records
of the folded workflows and every task-catalog step body the dispatcher runs.
"""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW_ROOT=ROOT/".github/workflows"
FOLDED_ROOT=ROOT/"tools/tasks/folded"
STEPS_ROOT=ROOT/"tools/tasks/steps"
REGISTRY=ROOT/"control/workflow-surface-registry.json"

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
        registered=sorted(s["path"] for s in json.loads(REGISTRY.read_text(encoding="utf-8"))["surfaces"])
        self.assertEqual([str(p.relative_to(ROOT)) for p in workflows],registered)
        for path in workflows+sorted(FOLDED_ROOT.glob("*.yml")):
            text=path.read_text(encoding="utf-8")
            self.assertIn("permissions:",text,path.name)
            for token in forbidden:
                self.assertNotIn(token,text,path.name)
        for path in sorted(STEPS_ROOT.rglob("*.sh")):
            text=path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token,text,str(path.relative_to(ROOT)))

if __name__=="__main__":
    unittest.main()

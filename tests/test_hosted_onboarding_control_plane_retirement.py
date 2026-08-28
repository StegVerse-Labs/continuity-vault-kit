"""Regression guards for hosted onboarding/candidate control-plane retirement."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ".github/workflows/onboarding-friction.yml",
    ".github/workflows/onboarding-friction-maintenance.yml",
    ".github/workflows/onboarding-friction-bootstrap.yml",
    ".github/workflows/automation-candidate-lifecycle.yml",
)


class HostedOnboardingControlPlaneRetirementTests(unittest.TestCase):
    def test_workflows_are_validation_transport_only(self):
        forbidden = (
            "contents: write",
            "actions: write",
            "issues: write",
            "pull-requests: write",
            "github.token",
            "GH_TOKEN:",
            "${{ secrets.",
            "gh label ",
            "gh issue ",
            "gh workflow run",
            "git push",
            "git commit",
            "git tag",
        )
        for relative in WORKFLOWS:
            text=(ROOT/relative).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token,text,relative)
            self.assertIn("contents: read",text,relative)
            self.assertIn("VALIDATION_TRANSPORT_ONLY",text,relative)
            self.assertIn("actions/upload-artifact@v4",text,relative)
            self.assertIn("authority_effect",text,relative)
            self.assertIn("NONE",text,relative)
            if "actions/checkout@v4" in text:
                self.assertIn("persist-credentials: false",text,relative)

    def test_threshold_semantics_remain_three(self):
        triage=(ROOT/WORKFLOWS[0]).read_text(encoding="utf-8")
        maintenance=(ROOT/WORKFLOWS[1]).read_text(encoding="utf-8")
        lifecycle=(ROOT/WORKFLOWS[3]).read_text(encoding="utf-8")
        self.assertIn('"threshold":3',triage)
        self.assertIn('"threshold":int(registry.get("threshold",3))',maintenance)
        self.assertIn('threshold=int(registry.get("threshold",3))',lifecycle)


if __name__ == "__main__":
    unittest.main()

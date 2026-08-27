"""Regression guards for hosted automation-candidate mutation retirement."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "automation-candidate-implementation.yml"


class HostedCandidateAuthorityRetirementTests(unittest.TestCase):
    def test_candidate_observer_is_read_only_validation_transport(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "contents: write",
            "actions: write",
            "issues: write",
            "git push",
            "git commit",
            "gh issue ",
            "gh workflow run",
            "github.token",
            "GH_TOKEN:",
            "CHANGELOG.md",
        ):
            self.assertNotIn(token, text, token)
        for token in (
            "contents: read",
            "pull-requests: read",
            "persist-credentials: false",
            "VALIDATION_TRANSPORT_ONLY",
            "NON_HOSTED_CANDIDATE_RECONCILIATION",
            "candidate_lifecycle_mutation_performed",
            "issue_mutation_performed",
            "changelog_mutation_performed",
            "repository_mutation_performed",
            "workflow_dispatch_performed",
            "actions/upload-artifact@v4",
            "authority_effect",
            "NONE",
        ):
            self.assertIn(token, text, token)


if __name__ == "__main__":
    unittest.main()

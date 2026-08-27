"""Regression guards for CMC-022 hosted release authority retirement."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = [
    ".github/workflows/one_button_release.yml",
    ".github/workflows/release-assets.yml",
    ".github/workflows/build-and-attach-release.yml",
    ".github/workflows/release-cycle-outcome.yml",
    ".github/workflows/release-cycle-recovery.yml",
]


class HostedReleaseAuthorityRetirementTests(unittest.TestCase):
    def test_retired_release_workflows_have_no_hosted_publication_authority(self):
        for relative in WORKFLOWS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("${{ secrets.", text, relative)
            self.assertNotIn("GITHUB_TOKEN:", text, relative)
            self.assertNotIn("contents: write", text, relative)
            self.assertNotIn("softprops/action-gh-release", text, relative)
            self.assertNotIn("git push", text, relative)
            self.assertNotIn("actions: write", text, relative)
            self.assertNotIn("github.token", text, relative)
            self.assertNotIn("GH_TOKEN:", text, relative)
            self.assertNotIn("gh workflow run", text, relative)
            marker_present = (
                "HOSTED_RELEASE_PUBLICATION_PROHIBITED_USE_TVC_ADMITTED_RELEASE_CAPABILITY" in text
                or "SOURCE_RECONSTRUCTED_RELEASE_NOT_MUTATED" in text
                or "VALIDATION_TRANSPORT_ONLY" in text
            )
            self.assertTrue(marker_present, relative)

    def test_release_workflows_are_validation_transport_only(self):
        for relative in WORKFLOWS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("contents: read", text, relative)
            self.assertIn("persist-credentials: false", text, relative)
            self.assertIn("actions/upload-artifact@v4", text, relative)


if __name__ == "__main__":
    unittest.main()

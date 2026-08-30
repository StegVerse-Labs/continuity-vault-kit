from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "production-provider-activation.yml"


class ProductionProviderActivationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_manual_only_and_non_authorizing(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotIn("pull_request:", self.text)
        self.assertNotIn("push:", self.text)
        self.assertIn("Production Provider Activation - Validation Only", self.text)
        self.assertNotIn("environment: production-provider-activation", self.text)

    def test_has_read_only_permissions_and_no_cloud_identity(self) -> None:
        self.assertIn("contents: read", self.text)
        self.assertNotIn("id-token: write", self.text)
        self.assertNotIn("aws-actions/configure-aws-credentials", self.text)
        self.assertNotIn("role-to-assume:", self.text)
        self.assertNotIn("AWS_ACCESS_KEY_ID", self.text)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", self.text)

    def test_validates_source_without_plan_or_apply(self) -> None:
        self.assertIn("terraform init -backend=false -input=false", self.text)
        self.assertIn("terraform validate", self.text)
        self.assertNotIn("terraform plan", self.text)
        self.assertNotIn("terraform apply", self.text)

    def test_inputs_are_fail_closed_and_evidence_is_retained(self) -> None:
        self.assertIn('[[ "$SPIFFE_IDENTITY" == spiffe://* ]]', self.text)
        self.assertIn('[[ "$CHAT_ENDPOINT" == https://* ]]', self.text)
        self.assertIn('[[ "$MASTER_RECORDS_ENDPOINT" == https://* ]]', self.text)
        self.assertIn('"state": "TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION_REQUIRED"', self.text)
        self.assertIn('"provider_mutation_performed": False', self.text)
        self.assertIn('"authority_effect": "NONE"', self.text)
        self.assertIn("actions/upload-artifact@v4", self.text)
        self.assertIn("retention-days: 30", self.text)


if __name__ == "__main__":
    unittest.main()

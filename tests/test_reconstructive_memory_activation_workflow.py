from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "production-provider-activation.yml"


class ProductionProviderActivationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_manual_only_and_environment_protected(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotIn("pull_request:", self.text)
        self.assertNotIn("push:", self.text)
        self.assertIn("environment: production-provider-activation", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_uses_oidc_and_minimum_repository_permissions(self) -> None:
        self.assertIn("contents: read", self.text)
        self.assertIn("id-token: write", self.text)
        self.assertIn("aws-actions/configure-aws-credentials@v4", self.text)
        self.assertIn("role-to-assume: ${{ vars.PROVIDER_ACTIVATION_AWS_ROLE_ARN }}", self.text)
        self.assertNotIn("AWS_ACCESS_KEY_ID", self.text)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", self.text)

    def test_apply_requires_explicit_confirmation_and_saved_plan(self) -> None:
        self.assertIn('CONFIRM_APPLY" != "APPLY"', self.text)
        self.assertIn("terraform plan -input=false -out=provider-activation.tfplan", self.text)
        self.assertIn("terraform apply -input=false -auto-approve provider-activation.tfplan", self.text)
        self.assertNotIn("terraform apply -auto-approve\n", self.text)

    def test_inputs_are_fail_closed_and_evidence_is_retained(self) -> None:
        self.assertIn('[[ "$SPIFFE_IDENTITY" == spiffe://* ]]', self.text)
        self.assertIn('[[ "$CHAT_ENDPOINT" == https://* ]]', self.text)
        self.assertIn('[[ "$MASTER_RECORDS_ENDPOINT" == https://* ]]', self.text)
        self.assertIn('"decision": "FAIL_CLOSED"', self.text)
        self.assertIn("actions/upload-artifact@v4", self.text)
        self.assertIn("retention-days: 30", self.text)


if __name__ == "__main__":
    unittest.main()

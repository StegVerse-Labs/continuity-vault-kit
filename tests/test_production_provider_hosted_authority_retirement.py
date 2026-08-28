"""Regression guard for hosted production-provider authority retirement."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/production-provider-activation.yml"

class ProductionProviderHostedAuthorityRetirementTests(unittest.TestCase):
    def test_hosted_workflow_cannot_acquire_or_apply_production_authority(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "id-token: write",
            "aws-actions/configure-aws-credentials",
            "role-to-assume:",
            "terraform plan",
            "terraform apply",
            "confirm_apply",
            "PROVIDER_ACTIVATION_AWS_ROLE_ARN",
            "github.token",
            "GH_TOKEN:",
            "${{ secrets.",
        ):
            self.assertNotIn(token,text,token)
        for token in (
            "contents: read",
            "persist-credentials: false",
            "terraform init -backend=false",
            "terraform validate",
            "VALIDATION_TRANSPORT_ONLY",
            "TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION",
            "cloud_identity_acquired",
            "terraform_apply_performed",
            "provider_mutation_performed",
            "actions/upload-artifact@v4",
            "authority_effect",
            "NONE",
        ):
            self.assertIn(token,text,token)

if __name__=="__main__":
    unittest.main()

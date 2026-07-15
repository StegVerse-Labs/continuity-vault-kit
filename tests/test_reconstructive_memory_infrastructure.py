from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProviderInfrastructureTests(unittest.TestCase):
    def test_terraform_defines_required_resources_and_outputs(self) -> None:
        text = (ROOT / "infra/production-providers/main.tf").read_text(encoding="utf-8")
        for token in (
            'resource "aws_kms_key" "stegid_verification"',
            'key_usage                = "SIGN_VERIFY"',
            'resource "aws_kms_key" "memory_custody"',
            'enable_key_rotation      = true',
            'resource "aws_dynamodb_table" "authoritative_state"',
            'point_in_time_recovery',
            'deletion_protection_enabled',
            'output "activation_profile_fragment"',
        ):
            self.assertIn(token, text)

    def test_infrastructure_files_do_not_contain_secret_values(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "infra/production-providers").iterdir()
            if path.is_file()
        )
        for forbidden in ("AKIA", "BEGIN PRIVATE KEY", "Bearer ", "aws_secret_access_key"):
            self.assertNotIn(forbidden, combined)

    def test_spire_template_remains_fail_closed(self) -> None:
        data = json.loads((ROOT / "infra/production-providers/spire-entry.template.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "FAIL_CLOSED")
        self.assertIn("UNCONFIGURED", data["spiffe_id"])
        self.assertEqual(data["activation_profile_mapping"]["provider_role"], "ai-entity-attestation")


if __name__ == "__main__":
    unittest.main()

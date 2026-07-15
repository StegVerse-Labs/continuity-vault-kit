from __future__ import annotations

import unittest

from reconstructive_memory.readiness import validate_provider_profile


class ProviderReadinessTests(unittest.TestCase):
    def complete_profile(self):
        return {
            "environment": "staging",
            "providers": {
                "stegid_verify": {"technology": "aws-kms-asymmetric-verify", "resource_id": "kms-stegid-test", "region": "test-region-1", "evidence_commitment": "sha256:test-stegid"},
                "ai_entity_attestation": {"technology": "spiffe-spire-x509-svid", "resource_id": "spiffe-test-ai", "trust_domain": "test.invalid", "evidence_commitment": "sha256:test-spiffe"},
                "key_custody": {"technology": "aws-kms-customer-managed-key", "resource_id": "kms-custody-test", "region": "test-region-1", "evidence_commitment": "sha256:test-custody"},
                "authoritative_state": {"technology": "amazon-dynamodb-conditional-writes", "resource_id": "state-table-test", "region": "test-region-1", "evidence_commitment": "sha256:test-state"},
                "ecosystem_chat": {"technology": "stegverse-authenticated-https", "resource_id": "chat-test", "endpoint": "https://chat.test.invalid/continuity", "evidence_commitment": "sha256:test-chat"},
                "master_records": {"technology": "stegverse-receipt-ingestion-https", "resource_id": "records-test", "endpoint": "https://records.test.invalid/receipts", "evidence_commitment": "sha256:test-records"},
            },
            "rollback": {"procedure_ref": "docs/test-rollback", "revocation_receipt_ref": "sha256:test-rollback"},
        }

    def test_complete_profile_is_ready(self):
        report = validate_provider_profile(self.complete_profile())
        self.assertTrue(report.ready)
        self.assertEqual(report.failures, ())
        self.assertTrue(report.profile_commitment.startswith("sha256:"))

    def test_template_profile_fails_closed(self):
        profile = self.complete_profile()
        profile["providers"]["key_custody"]["resource_id"] = "UNCONFIGURED"
        report = validate_provider_profile(profile)
        self.assertFalse(report.ready)
        self.assertIn("key_custody.resource_id is unconfigured", report.failures)

    def test_non_https_endpoint_is_rejected(self):
        profile = self.complete_profile()
        profile["providers"]["master_records"]["endpoint"] = "http://records.test.invalid/receipts"
        report = validate_provider_profile(profile)
        self.assertFalse(report.ready)
        self.assertIn("master_records.endpoint must be an absolute HTTPS URL", report.failures)

    def test_rollback_evidence_is_required(self):
        profile = self.complete_profile()
        profile["rollback"]["revocation_receipt_ref"] = "UNCONFIGURED"
        report = validate_provider_profile(profile)
        self.assertFalse(report.ready)
        self.assertIn("rollback.revocation_receipt_ref is unconfigured", report.failures)


if __name__ == "__main__":
    unittest.main()

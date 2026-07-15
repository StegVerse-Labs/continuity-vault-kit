import unittest

from reconstructive_memory.provider_activation import (
    DeploymentReceipt,
    ProviderSelection,
    ProductionActivationProfile,
    default_aws_profile,
)


class ProviderActivationTests(unittest.TestCase):
    def test_default_profile_is_selected_not_ready(self):
        profile = default_aws_profile(created_at=1)
        profile.verify()
        self.assertFalse(profile.activation_ready())
        self.assertIn("UNCONFIGURED", profile.steg_id.identity_ref)

    def test_verified_profile_is_activation_ready(self):
        selected = default_aws_profile(created_at=2)
        verified = ProductionActivationProfile(
            profile_id=selected.profile_id,
            environment="production",
            steg_id=ProviderSelection("steg-id-signature", "AWS", "KMS asymmetric verify", "arn:kms:steg-id", "us-east-1", "verified"),
            ai_attestation=ProviderSelection("ai-entity-attestation", "SPIFFE", "SPIRE X.509-SVID", "spiffe://stegverse/ai/auri", "global", "verified"),
            key_custody=ProviderSelection("key-custody", "AWS", "KMS customer-managed key", "arn:kms:vault", "us-east-1", "verified"),
            state_store=ProviderSelection("replicated-state", "AWS", "DynamoDB conditional write", "arn:dynamodb:table/state", "us-east-1", "verified"),
            chat_transport=ProviderSelection("ecosystem-chat", "StegVerse", "authenticated chat endpoint", "https://chat.example", "global", "verified"),
            master_records=ProviderSelection("master-records", "StegVerse", "receipt ingestion endpoint", "https://records.example", "global", "verified"),
            rollback_ref=selected.rollback_ref,
            created_at=2,
        ).with_hash()
        self.assertTrue(verified.activation_ready())

    def test_tampered_profile_fails(self):
        profile = default_aws_profile(created_at=3)
        tampered = ProductionActivationProfile(**{**profile.__dict__, "environment": "production"})
        with self.assertRaises(ValueError):
            tampered.verify()

    def test_receipt_requires_all_provider_evidence(self):
        receipt = DeploymentReceipt(
            receipt_id="deploy-1",
            profile_hash="sha256:profile",
            validation_commit="abc123",
            rollback_ref="docs/rollback",
            provider_evidence={"only": "one"},
            issued_at=4,
            decision="ALLOW",
        ).with_hash()
        with self.assertRaises(ValueError):
            receipt.verify()

    def test_complete_receipt_verifies_without_plaintext(self):
        evidence = {name: f"sha256:{name}" for name in (
            "steg_id", "ai_attestation", "key_custody", "state_store", "chat_transport", "master_records"
        )}
        receipt = DeploymentReceipt(
            receipt_id="deploy-2",
            profile_hash="sha256:profile",
            validation_commit="def456",
            rollback_ref="docs/rollback",
            provider_evidence=evidence,
            issued_at=5,
            decision="FAIL_CLOSED",
        ).with_hash()
        receipt.verify()
        self.assertNotIn("plaintext", str(receipt.payload()).lower())


if __name__ == "__main__":
    unittest.main()

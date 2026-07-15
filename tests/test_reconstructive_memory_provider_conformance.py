import unittest
from dataclasses import replace

from reconstructive_memory.provider_activation import ProductionActivationProfile, ProviderSelection
from reconstructive_memory.provider_conformance import (
    REQUIRED_ROLES,
    ProviderProbeResult,
    assemble_deployment_receipt,
    run_provider_conformance,
)


class FakeProbe:
    def __init__(self, role: str, resource_id: str, *, success: bool = True) -> None:
        self.role = role
        self.resource_id = resource_id
        self.success = success

    def run(self, profile, *, checked_at: int):
        return ProviderProbeResult(
            role=self.role,
            resource_id=self.resource_id,
            observed_identity=f"observed:{self.role}",
            capability=f"verified:{self.role}",
            success=self.success,
            evidence_commitment="sha256:" + (self.role.replace("-", "") + "0" * 64)[:64],
            checked_at=checked_at,
            failure_code=None if self.success else "PROBE_FAILED",
        ).with_hash()


def verified_profile() -> ProductionActivationProfile:
    return ProductionActivationProfile(
        profile_id="prod-1",
        environment="production",
        steg_id=ProviderSelection("steg-id-signature", "AWS", "KMS Verify", "arn:aws:kms:region:acct:key/steg", "us-east-1", "verified"),
        ai_attestation=ProviderSelection("ai-entity-attestation", "SPIFFE", "X.509-SVID", "spiffe://stegverse/ai/runtime", "global", "verified"),
        key_custody=ProviderSelection("key-custody", "AWS", "KMS CMK", "arn:aws:kms:region:acct:key/custody", "us-east-1", "verified"),
        state_store=ProviderSelection("replicated-state", "AWS", "DynamoDB conditional write", "arn:aws:dynamodb:region:acct:table/state", "us-east-1", "verified"),
        chat_transport=ProviderSelection("ecosystem-chat", "StegVerse", "authenticated endpoint", "https://chat.example.test/ingest", "global", "verified"),
        master_records=ProviderSelection("master-records", "StegVerse", "receipt endpoint", "https://records.example.test/receipts", "global", "verified"),
        rollback_ref="docs/PRODUCTION_PROVIDER_ACTIVATION.md#rollback-and-revocation",
        created_at=1,
    ).with_hash()


class ProviderConformanceTests(unittest.TestCase):
    def probes(self, *, failed_role: str | None = None):
        resources = {
            "steg-id-signature": "arn:aws:kms:region:acct:key/steg",
            "ai-entity-attestation": "spiffe://stegverse/ai/runtime",
            "key-custody": "arn:aws:kms:region:acct:key/custody",
            "replicated-state": "arn:aws:dynamodb:region:acct:table/state",
            "ecosystem-chat": "https://chat.example.test/ingest",
            "master-records": "https://records.example.test/receipts",
        }
        return [FakeProbe(role, resources[role], success=role != failed_role) for role in REQUIRED_ROLES]

    def test_successful_conformance_assembles_allow_receipt(self):
        profile = verified_profile()
        report = run_provider_conformance(profile, self.probes(), checked_at=2)
        self.assertTrue(report.ready)
        receipt = assemble_deployment_receipt(profile, report, receipt_id="receipt-1", issued_at=3)
        self.assertEqual(receipt.decision, "ALLOW")
        self.assertEqual(receipt.validation_commit, report.report_hash)
        self.assertEqual(set(receipt.provider_evidence), set(REQUIRED_ROLES))

    def test_failed_probe_blocks_receipt(self):
        profile = verified_profile()
        report = run_provider_conformance(profile, self.probes(failed_role="master-records"), checked_at=2)
        self.assertFalse(report.ready)
        with self.assertRaises(PermissionError):
            assemble_deployment_receipt(profile, report, receipt_id="receipt-2", issued_at=3)

    def test_unverified_profile_blocks_receipt(self):
        profile = verified_profile()
        unverified = replace(profile, master_records=replace(profile.master_records, status="configured")).with_hash()
        report = run_provider_conformance(unverified, self.probes(), checked_at=2)
        with self.assertRaises(PermissionError):
            assemble_deployment_receipt(unverified, report, receipt_id="receipt-3", issued_at=3)

    def test_tampered_probe_is_rejected(self):
        result = self.probes()[0].run(verified_profile(), checked_at=2)
        with self.assertRaises(ValueError):
            replace(result, observed_identity="changed").verify()

    def test_duplicate_role_set_fails_closed(self):
        probes = self.probes()
        probes[-1] = FakeProbe("ecosystem-chat", "https://duplicate.example.test")
        with self.assertRaises(ValueError):
            run_provider_conformance(verified_profile(), probes, checked_at=2)


if __name__ == "__main__":
    unittest.main()

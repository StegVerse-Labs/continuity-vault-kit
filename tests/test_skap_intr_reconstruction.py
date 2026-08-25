import json
import tempfile
import unittest
from pathlib import Path

from execution.vault_store import KnowledgeVaultExecutionStore
from scripts.intr_hop_receipt import FORWARD, RETURN, build_receipt, verify_chain
from scripts.validate_skap_endpoint_contracts import (
    sha256_uri,
    validate_endpoint,
    validate_lifecycle_receipt,
)


ROOT = Path(__file__).resolve().parents[1]


class SkapInTrReconstructionTests(unittest.TestCase):
    def test_synthetic_round_trip_reconstructs_without_secret_or_authority_transfer(self):
        packet = json.loads((ROOT / "specs/intr-packet-review-candidate.v1.json").read_text(encoding="utf-8"))
        envelope = packet["envelope"]
        packet_id = envelope["packet_id"]
        operation_hash = envelope["operation_hash"]
        payload_hash = envelope["payload_hash"]
        packet_hash = sha256_uri(packet)
        grant_hash = sha256_uri(envelope["credential_grant"])

        lifecycle = {
            "schema": "stegverse.skap.lifecycle_transition_receipt/v1",
            "receipt_id": "skap-life-e2e-001",
            "secret_ref": envelope["credential_grant"]["credential_ref"],
            "credential_version": envelope["credential_grant"]["credential_version"],
            "from_state": "SEALED",
            "to_state": "ACTIVE",
            "transition_reason": "synthetic non-secret reconstruction fixture",
            "prior_transition_receipt_hash": None,
            "sealed_object_hash_before": "sha256:" + "1" * 64,
            "sealed_object_hash_after": "sha256:" + "2" * 64,
            "supersedes_credential_version": None,
            "replacement_secret_ref": None,
            "revocation_effect": "NONE",
            "outstanding_grants_invalidated": False,
            "authority_ref": "tvc://authority/synthetic-e2e",
            "authority_transfer": False,
            "secret_plaintext_present": False,
            "effective_at": "2026-08-24T20:40:00Z",
        }
        lifecycle["receipt_hash"] = sha256_uri(lifecycle)
        self.assertEqual(validate_lifecycle_receipt(lifecycle), [])

        forward = []
        prior = None
        for index, (from_role, to_role) in enumerate(FORWARD):
            receipt = build_receipt(
                receipt_id=f"intr-e2e-forward-{index}",
                packet_id=packet_id,
                hop_index=index,
                direction="FORWARD",
                from_role=from_role,
                to_role=to_role,
                operation_hash=operation_hash,
                payload_hash=payload_hash,
                prior_receipt_hash=prior,
                boundary_identity_ref=f"identity:{to_role.lower()}-synthetic",
                boundary_verification="VERIFIED",
                transition_state="TERMINAL" if index == len(FORWARD) - 1 else "FORWARDED",
                recorded_at=f"2026-08-24T20:4{index}:00Z",
            )
            forward.append(receipt)
            prior = receipt["receipt_hash"]
        self.assertEqual(verify_chain(forward), [])

        endpoint_ref = "endpoint://provider-example/v1/"
        binding = {
            "packet_id": packet_id,
            "packet_hash": packet_hash,
            "operation_hash": operation_hash,
            "credential_grant_hash": grant_hash,
            "authorized_endpoint_ref": endpoint_ref,
            "tls_session_binding_hash": "sha256:" + "f" * 64,
        }
        endpoint_proof = {
            "schema": "stegverse.intr.endpoint_session_proof/v1",
            "proof_id": "intr-endpoint-e2e-001",
            **binding,
            "resolved_host": envelope["credential_grant"]["authorized_endpoint"]["host"],
            "scheme": "https",
            "port": 443,
            "path_prefix": envelope["credential_grant"]["authorized_endpoint"]["path_prefix"],
            "tls_session_ref": "tls-session://synthetic-e2e",
            "peer_identity_ref": "peer://provider-example-synthetic",
            "certificate_chain_hash": "sha256:" + "c" * 64,
            "verification_state": "VERIFIED",
            "verified_at": "2026-08-24T20:44:00Z",
            "same_session_required_for_resolution_and_submission": True,
            "redirect_permitted": False,
            "credential_resolution_permitted": True,
            "revocation_rechecked_immediately_before_resolution": True,
            "authority_transfer": False,
            "failure_disposition": "NOT_APPLICABLE",
        }
        endpoint_proof["proof_hash"] = sha256_uri(endpoint_proof)
        self.assertEqual(validate_endpoint(endpoint_proof, expected_binding=binding), [])

        return_packet_id = f"{packet_id}-return"
        response_payload_hash = "sha256:" + "e" * 64
        returned = []
        prior = None
        for index, (from_role, to_role) in enumerate(RETURN):
            receipt = build_receipt(
                receipt_id=f"intr-e2e-return-{index}",
                packet_id=return_packet_id,
                hop_index=index,
                direction="RETURN",
                from_role=from_role,
                to_role=to_role,
                operation_hash=operation_hash,
                payload_hash=response_payload_hash,
                prior_receipt_hash=prior,
                boundary_identity_ref=f"identity:{to_role.lower()}-return-synthetic",
                boundary_verification="VERIFIED",
                transition_state="TERMINAL" if index == len(RETURN) - 1 else "FORWARDED",
                recorded_at=f"2026-08-24T20:5{index}:00Z",
            )
            returned.append(receipt)
            prior = receipt["receipt_hash"]
        self.assertEqual(verify_chain(returned), [])

        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            store.append_intr_packet(packet_id, packet)
            for receipt in forward:
                store.append_intr_receipt(packet_id, receipt)
            for receipt in returned:
                store.append_intr_receipt(packet_id, receipt)
            store.append_receipt(packet_id, {"kind": "endpoint_session_proof_ref", "proof_hash": endpoint_proof["proof_hash"]})
            store.append_receipt(packet_id, {"kind": "skap_lifecycle_receipt_ref", "receipt_hash": lifecycle["receipt_hash"]})

            persisted_packet = store.read_stream("Extensions", packet_id)
            persisted_receipts = store.read_stream("Receipts", packet_id)

        self.assertEqual(persisted_packet, [packet])
        self.assertEqual(len(persisted_receipts), 10)
        self.assertEqual([r for r in persisted_receipts if r.get("direction") == "FORWARD"], forward)
        self.assertEqual([r for r in persisted_receipts if r.get("direction") == "RETURN"], returned)
        self.assertEqual(
            [r["proof_hash"] for r in persisted_receipts if r.get("kind") == "endpoint_session_proof_ref"],
            [endpoint_proof["proof_hash"]],
        )
        self.assertEqual(
            [r["receipt_hash"] for r in persisted_receipts if r.get("kind") == "skap_lifecycle_receipt_ref"],
            [lifecycle["receipt_hash"]],
        )
        self.assertTrue(all(r.get("secret_plaintext_present") is False for r in forward + returned))
        self.assertTrue(all(r.get("authority_transfer") is False for r in forward + returned))

    def test_endpoint_proof_cannot_reconstruct_under_substituted_packet(self):
        packet = json.loads((ROOT / "specs/intr-packet-review-candidate.v1.json").read_text(encoding="utf-8"))
        envelope = packet["envelope"]
        binding = {
            "packet_id": envelope["packet_id"],
            "packet_hash": sha256_uri(packet),
            "operation_hash": envelope["operation_hash"],
            "credential_grant_hash": sha256_uri(envelope["credential_grant"]),
            "authorized_endpoint_ref": "endpoint://provider-example/v1/",
            "tls_session_binding_hash": "sha256:" + "f" * 64,
        }
        proof = {
            "schema": "stegverse.intr.endpoint_session_proof/v1",
            "proof_id": "intr-endpoint-e2e-negative",
            **binding,
            "resolved_host": envelope["credential_grant"]["authorized_endpoint"]["host"],
            "scheme": "https",
            "port": 443,
            "path_prefix": "/v1/",
            "tls_session_ref": "tls-session://synthetic-e2e",
            "peer_identity_ref": "peer://provider-example-synthetic",
            "certificate_chain_hash": "sha256:" + "c" * 64,
            "verification_state": "VERIFIED",
            "verified_at": "2026-08-24T20:44:00Z",
            "same_session_required_for_resolution_and_submission": True,
            "redirect_permitted": False,
            "credential_resolution_permitted": True,
            "revocation_rechecked_immediately_before_resolution": True,
            "authority_transfer": False,
            "failure_disposition": "NOT_APPLICABLE",
        }
        proof["proof_hash"] = sha256_uri(proof)
        substituted = dict(binding)
        substituted["packet_hash"] = "sha256:" + "9" * 64
        errors = validate_endpoint(proof, expected_binding=substituted)
        self.assertTrue(any("packet_hash" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()

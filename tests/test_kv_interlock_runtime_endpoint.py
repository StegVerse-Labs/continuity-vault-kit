from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "kv_interlock_endpoint.py"
sys.path.insert(0, str(ROOT / "tests"))

from kv_two_layer_e0 import e0_standin_healthy_node_evaluator, healthy_evidence  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")


def load_module():
    spec = importlib.util.spec_from_file_location("kv_interlock_endpoint", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class KVInterlockRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.receipts = []
        self.candidates = []
        self.now = datetime(2026, 8, 27, 21, 30, 0, tzinfo=timezone.utc)
        self.runtime = self.m.KVInterlockRuntime(
            authority_validator=lambda authority_ref, request, envelope: authority_ref == "owner-assertion-1",
            policy_evaluator=self.policy,
            receipt_store=self.store_receipt,
            candidate_store=self.store_candidate,
            clock=lambda: self.now,
            healthy_node_evaluator=e0_standin_healthy_node_evaluator,
        )

    def assert_layer1_refusal(self, response, text, cause=None):
        """Layer 1 returns a six-field FAIL_CLOSED (never raises) and mints no KV-access receipt."""
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertEqual(response["disposition"], "FAIL_CLOSED")
        self.assertEqual(response["failure_code"], "KV_ACCESS_LAYER1_REFUSED")
        self.assertIn(text, response["required_evidence_or_repair"])
        for field in SIX:
            self.assertTrue(response[field], field)
        self.assertIn("KV-SKAP-VAULT-FUNCTIONAL-001", response["owning_existing_goal"])
        self.assertIsNone(response["kv_access_receipt"])
        self.assertEqual((response["granted_scope"], response["context"]), ([], {}))
        if cause:
            self.assertEqual(response["refusal_cause"], cause)

    def request(self, operation="REQUEST"):
        value = {
            "schema_version": "kv.interlock.request.v1",
            "operation": operation,
            "request_id": "request-1",
            "requester": {"module": "Site", "component": "generic-login-test"},
            "purpose": "Read minimum onboarding state.",
            "record_class": "KV_ONBOARDING_STATE",
            "requested_scope": [
                "lifecycle_state", "kv_ref", "owner_identity_ref",
                "device_ref", "transition_receipt_refs",
            ],
            "minimum_necessary_justification": "Render the next permitted owner action.",
            "authority_ref": "owner-assertion-1",
            "disclosure_mode": "BOUNDED_CONTEXT",
        }
        if operation == "COMMIT_CANDIDATE":
            value["candidate_writeback"] = {
                "candidate_type": "KV_CREATE_REQUEST",
                "payload_ref": "urn:stegverse:test:candidate:1",
                "requested_destination": None,
            }
        return value

    def envelope(self, request):
        return {
            "schema": "stegverse.kv-interlock.intr-envelope/v1",
            "protocol": "InTr",
            "packet_id": "packet-1",
            "direction": "REQUEST",
            "source_role": "DEVICE",
            "next_role": "KV",
            "request_id": request["request_id"],
            "operation": request["operation"],
            "payload_schema_version": "kv.interlock.request.v1",
            "payload_hash": self.m.sha256_uri(request),
            "sealed_material_ref": "urn:stegverse:sealed:test:1",
            "authority": {
                "authority_transfer": False,
                "transport_grants_execution_authority": False,
                "model_output_grants_execution_authority": False,
                "credential_authority_effect": "NONE",
            },
            "boundary_proof": {
                "required": True,
                "source_identity_ref": "device:test:1",
                "next_boundary_identity_ref": "kv:test:1",
                "verification_state": "VERIFIED",
            },
            "receipt_policy": {
                "receipt_required": True,
                "receipt_contains_payload_plaintext": False,
                "receipt_chain_required": True,
                "ambiguous_disposition": "FAIL_CLOSED",
            },
            "issued_at": "2026-08-27T21:29:00Z",
            "expires_at": "2026-08-27T21:35:00Z",
            "nonce": "nonce-1",
        }

    def policy(self, request):
        return {
            "decision": "ALLOW_BOUNDED_CONTEXT",
            "granted_scope": list(request["requested_scope"]),
            "context": {
                "lifecycle_state": "NO_KV",
                "kv_ref": None,
                "owner_identity_ref": None,
                "device_ref": None,
                "transition_receipt_refs": [],
            },
            "source_refs": ["urn:stegverse:kv:readiness:head"],
            "policy_profile": "kv-onboarding-owner-minimum-v1",
            "redaction_profile": "opaque-refs-only",
        }

    def store_receipt(self, receipt):
        self.receipts.append(receipt)
        return "urn:stegverse:kv-interlock-receipt:" + receipt["receipt_id"].split(":")[-1]

    def store_candidate(self, candidate):
        self.candidates.append(candidate)
        return "urn:stegverse:kv-candidate:1"

    def execute(self, request=None, envelope=None):
        request = request or self.request()
        envelope = envelope or self.envelope(request)
        return self.runtime.handle(
            request,
            intr_envelope=envelope,
            intr_receipt_ref="sha256:" + "a" * 64,
            healthy_node_evidence=healthy_evidence(envelope["boundary_proof"]["source_identity_ref"]),
        )

    def test_verified_request_returns_bounded_context_and_hash_verified_receipt(self):
        response = self.execute()
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertEqual(set(response["context"]), set(response["granted_scope"]))
        self.assertEqual(response["receipt"]["authority_ref"], "owner-assertion-1")
        projection = {
            "schema_version": response["schema_version"],
            "request_id": response["request_id"],
            "decision": response["decision"],
            "granted_scope": response["granted_scope"],
            "context": response["context"],
            "source_refs": response["source_refs"],
        }
        self.assertEqual(response["receipt"]["response_hash"], self.m.sha256_hex(projection))
        self.assertEqual(response["receipt"]["response_hash"], self.m.response_hash(response))
        self.assertEqual(len(self.receipts), 1)
        self.assertNotIn("password", self.m.canonical_json(response).lower())
        self.assertNotIn("credential_value", self.m.canonical_json(response).lower())

    def test_unverified_boundary_is_rejected_before_policy(self):
        request = self.request()
        envelope = self.envelope(request)
        envelope["boundary_proof"]["verification_state"] = "PENDING"
        self.assert_layer1_refusal(self.execute(request, envelope), "verified boundary proof")
        self.assertEqual(self.receipts, [])

    def test_payload_hash_drift_is_rejected(self):
        request = self.request()
        envelope = self.envelope(request)
        envelope["payload_hash"] = "sha256:" + "b" * 64
        self.assert_layer1_refusal(self.execute(request, envelope), "payload hash mismatch")

    def test_missing_authority_fails_closed_without_context(self):
        request = self.request()
        request["authority_ref"] = "stale-owner-assertion"
        envelope = self.envelope(request)
        response = self.execute(request, envelope)
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertEqual(response["granted_scope"], [])
        self.assertEqual(response["context"], {})
        self.assertIn("AUTHORITY_NOT_ADMITTED", response["receipt"]["policy_profile"])

    def test_policy_scope_expansion_fails_closed(self):
        def bad_policy(request):
            value = self.policy(request)
            value["granted_scope"] = [*request["requested_scope"], "extra_private_field"]
            return value
        runtime = self.m.KVInterlockRuntime(
            authority_validator=lambda *_: True,
            policy_evaluator=bad_policy,
            receipt_store=self.store_receipt,
            clock=lambda: self.now,
            healthy_node_evaluator=e0_standin_healthy_node_evaluator,
        )
        request = self.request()
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
            healthy_node_evidence=healthy_evidence("device:test:1"),
        )
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertEqual(response["context"], {})

    def test_secret_like_context_fails_closed(self):
        def bad_policy(request):
            value = self.policy(request)
            value["granted_scope"] = ["lifecycle_state"]
            value["context"] = {"credential_value": "should-never-pass"}
            return value
        runtime = self.m.KVInterlockRuntime(
            authority_validator=lambda *_: True,
            policy_evaluator=bad_policy,
            receipt_store=self.store_receipt,
            clock=lambda: self.now,
            healthy_node_evaluator=e0_standin_healthy_node_evaluator,
        )
        request = self.request()
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
            healthy_node_evidence=healthy_evidence("device:test:1"),
        )
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertNotIn("should-never-pass", self.m.canonical_json(response))

    def test_commit_candidate_is_candidate_only_and_returns_opaque_reference(self):
        request = self.request("COMMIT_CANDIDATE")
        envelope = self.envelope(request)
        response = self.execute(request, envelope)
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertEqual(response["context"], {})
        self.assertEqual(response["receipt"]["writeback_candidate_ref"], "urn:stegverse:kv-candidate:1")
        self.assertEqual(len(self.candidates), 1)
        self.assertTrue(self.candidates[0]["candidate_only"])
        self.assertFalse(self.candidates[0]["canonical_state_changed"])
        self.assertEqual(self.candidates[0]["authority_effect"], "NONE")

    def test_commit_candidate_fails_closed_without_candidate_store(self):
        runtime = self.m.KVInterlockRuntime(
            authority_validator=lambda *_: True,
            policy_evaluator=self.policy,
            receipt_store=self.store_receipt,
            candidate_store=None,
            clock=lambda: self.now,
            healthy_node_evaluator=e0_standin_healthy_node_evaluator,
        )
        request = self.request("COMMIT_CANDIDATE")
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
            healthy_node_evidence=healthy_evidence("device:test:1"),
        )
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertIsNone(response["receipt"]["writeback_candidate_ref"])

    def test_expired_intr_envelope_is_rejected(self):
        request = self.request()
        envelope = self.envelope(request)
        envelope["expires_at"] = "2026-08-27T21:29:59Z"
        self.assert_layer1_refusal(self.execute(request, envelope), "expired")

    def test_candidate_writeback_is_rejected_on_plain_request(self):
        request = self.request()
        request["candidate_writeback"] = {
            "candidate_type": "KV_CREATE_REQUEST",
            "payload_ref": "urn:unexpected",
        }
        envelope = self.envelope(request)
        self.assert_layer1_refusal(self.execute(request, envelope), "only allowed")

    def test_request_selector_is_bounded_and_authority_neutral(self):
        request = self.request()
        request["selector"] = {
            "directory_id": "pictures",
            "canonical_path": "04_Media/Pictures",
        }
        response = self.execute(request, self.envelope(request))
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertEqual(request["authority_ref"], "owner-assertion-1")

    def test_selector_rejects_extra_fields(self):
        request = self.request()
        request["selector"] = {
            "directory_id": "pictures",
            "canonical_path": "04_Media/Pictures",
            "extra": True,
        }
        self.assert_layer1_refusal(self.execute(request, self.envelope(request)), "selector invalid")

    def test_selector_is_request_only(self):
        request = self.request("COMMIT_CANDIDATE")
        request["selector"] = {
            "directory_id": "pictures",
            "canonical_path": "04_Media/Pictures",
        }
        self.assert_layer1_refusal(self.execute(request, self.envelope(request)), "selector only allowed for REQUEST")


class Layer1HealthyNodeTests(KVInterlockRuntimeTests):
    """LC-KV-07/10/11 (StegVerse-Labs/.github#3330 rev 1): KV is reachable only via InTr from a healthy node."""

    def handle(self, runtime, evidence="healthy", envelope=None):
        request = self.request()
        return runtime.handle(request, intr_envelope=envelope or self.envelope(request),
                              intr_receipt_ref="sha256:" + "a" * 64,
                              healthy_node_evidence=healthy_evidence("device:test:1") if evidence == "healthy"
                              else evidence)

    def test_admitted_healthy_node_gets_a_kv_access_receipt(self):
        response = self.handle(self.runtime)
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        receipt = response["kv_access_receipt"]
        self.assertEqual((receipt["boundary"], receipt["layer"], receipt["minted_by"]),
                         ("INTR_DEVICE_KV", 1, "KVInterlockRuntime.handle"))
        self.assertEqual(receipt["requester_node_ref"], "device:test:1")
        self.assertEqual(receipt["response_hash"], response["receipt"]["response_hash"])
        self.assertEqual(receipt["healthy_node_evaluator"], self.m.PINNED_HEALTHY_NODE_EVALUATOR_ID)
        self.assertEqual(self.runtime.verify_kv_access_receipt(receipt["receipt_hash"]), receipt)
        self.assertIsNone(self.runtime.verify_kv_access_receipt(self.m.sha256_uri({"forged": True})))

    def test_no_health_evidence_or_an_unhealthy_node_is_refused(self):
        for evidence in (None, {}, healthy_evidence("device:other"), healthy_evidence("device:test:1", healthy=False),
                         healthy_evidence("device:test:1", admitted=False)):
            self.assert_layer1_refusal(self.handle(self.runtime, evidence), "", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY")
        self.assertEqual(self.receipts, [])  # refused before authority, policy or any receipt

    def test_without_the_intr_evaluator_layer1_fails_closed_and_never_self_asserts(self):
        runtime = self.m.KVInterlockRuntime(authority_validator=lambda *_: True, policy_evaluator=self.policy,
                                            receipt_store=self.store_receipt, clock=lambda: self.now)
        self.assertIsNone(self.m.resolve_pinned_healthy_node_evaluator())  # LC-KV-13/14 not installed here
        response = self.handle(runtime)
        self.assert_layer1_refusal(response, "is not installed", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY")
        self.assertEqual(response["failure_class"], "B")
        self.assertIn("LLM-adapter", response["next_attempt"])

    def test_an_evaluator_that_raises_or_returns_a_malformed_receipt_is_refused(self):
        def raising(*_, **__):
            raise RuntimeError("down")

        def flagged(evidence, *, requester_node_ref):  # a bare caller flag is not a healthy-node receipt
            return {"disposition": "ALLOW", "healthy_node_established": True}

        def rehashed(evidence, *, requester_node_ref):
            out = e0_standin_healthy_node_evaluator(evidence, requester_node_ref=requester_node_ref)
            out["healthy_node_receipt"]["node_ref"] = "device:other"
            return out
        for evaluator in (raising, flagged, rehashed):
            runtime = self.m.KVInterlockRuntime(authority_validator=lambda *_: True, policy_evaluator=self.policy,
                                                receipt_store=self.store_receipt, clock=lambda: self.now,
                                                healthy_node_evaluator=evaluator)
            self.assert_layer1_refusal(self.handle(runtime), "", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY")

    def test_malformed_transitions_return_dispositions(self):
        for request in (None, [], {"schema_version": "x"}):
            response = self.runtime.handle(request, intr_envelope={}, intr_receipt_ref="sha256:" + "a" * 64)
            self.assert_layer1_refusal(response, "")


if __name__ == "__main__":
    unittest.main()

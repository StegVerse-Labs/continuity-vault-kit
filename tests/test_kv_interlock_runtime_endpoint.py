from __future__ import annotations

import hashlib
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "kv_interlock_endpoint.py"
sys.path.insert(0, str(ROOT / "tests"))

from kv_two_layer_e0 import e0_empty_ref_checkout, e0_health_ledger, e0_ref_without_namespace, healthy_node_kwargs  # noqa: E402,E501
from kv_two_layer_e0 import enter_e0 as setUpModule, exit_e0 as tearDownModule  # noqa: E402,F401  (E0 trust anchors, labelled)

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")


def load_module():
    # The imported module itself: its TRUST_ANCHORS are the ones the E0 harness puts in force (LC-KV-15).
    from runtime import kv_interlock_endpoint
    assert Path(kv_interlock_endpoint.__file__).resolve() == MODULE_PATH.resolve()
    return kv_interlock_endpoint


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
            **healthy_node_kwargs("SV-NODE-E0TEST0001"),
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
                "source_identity_ref": "SV-NODE-E0TEST0001",
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
            **healthy_node_kwargs("SV-NODE-E0TEST0001"),
        )
        request = self.request()
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
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
            **healthy_node_kwargs("SV-NODE-E0TEST0001"),
        )
        request = self.request()
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
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
            **healthy_node_kwargs("SV-NODE-E0TEST0001"),
        )
        request = self.request("COMMIT_CANDIDATE")
        response = runtime.handle(
            request,
            intr_envelope=self.envelope(request),
            intr_receipt_ref="sha256:" + "a" * 64,
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
    """LC-KV-07/10/11 (StegVerse-Labs/.github#3330 rev 1): KV is reachable only via InTr from a healthy node, as
    decided by the pinned InTr evaluator (StegVerse-org/LLM-adapter#428 @0b37fe3b, LC-KV-13/14)."""

    def handle(self, runtime, evidence=None, envelope=None):
        request = self.request()
        return runtime.handle(request, intr_envelope=envelope or self.envelope(request),
                              intr_receipt_ref="sha256:" + "a" * 64, healthy_node_evidence=evidence)

    def runtime_for(self, ledger_root, evaluator=None):
        return self.m.KVInterlockRuntime(authority_validator=lambda *_: True, policy_evaluator=self.policy,
                                         receipt_store=self.store_receipt, clock=lambda: self.now,
                                         healthy_node_evaluator=evaluator, healthy_node_ledger_checkout=ledger_root)

    def test_admitted_healthy_node_gets_a_kv_access_receipt(self):
        response = self.handle(self.runtime)
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        receipt = response["kv_access_receipt"]
        self.assertEqual((receipt["boundary"], receipt["layer"], receipt["minted_by"]),
                         ("INTR_DEVICE_KV", 1, "KVInterlockRuntime.handle"))
        self.assertEqual(receipt["requester_node_ref"], "SV-NODE-E0TEST0001")
        self.assertEqual(receipt["response_hash"], response["receipt"]["response_hash"])
        self.assertEqual(receipt["healthy_node_evaluator"], self.m.PINNED_HEALTHY_NODE_EVALUATOR_ID)
        self.assertEqual(receipt["healthy_node_evaluator_source_sha256"],
                         self.m.PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"])
        evaluation = receipt["healthy_node_receipt"]
        self.assertEqual((evaluation["schema"], evaluation["disposition"], evaluation["node_id"],
                          evaluation["admission_required"]),
                         ("stegverse.healthy-node-evaluation/v1", "ALLOW", "SV-NODE-E0TEST0001", True))
        self.assertEqual(self.runtime.verify_kv_access_receipt(receipt["receipt_hash"]), receipt)
        self.assertIsNone(self.runtime.verify_kv_access_receipt(self.m.sha256_uri({"forged": True})))

    def test_the_vendored_evaluator_is_byte_identical_to_the_pin(self):
        evaluator, why = self.m.resolve_pinned_healthy_node_evaluator()
        self.assertEqual(why, "")
        self.assertEqual(self.m.evaluator_identity(evaluator), self.m.PINNED_ANCHORED_EVALUATOR_ID)
        pinned_dir = ROOT / "runtime" / "intr_pinned" / "llm_adapter"
        for name, pin in (("healthy_node_evaluator.py", self.m.PINNED_HEALTHY_NODE_EVALUATOR),
                          ("endpoint_ledger_anchor.py", self.m.PINNED_ANCHORED_EVALUATOR)):
            self.assertEqual("sha256:" + hashlib.sha256((pinned_dir / name).read_bytes()).hexdigest(),
                             pin["source_sha256"], name)
        self.assertEqual(self.m.PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"],
                         "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58")

    def test_the_ledger_is_bound_by_the_org_ledger_contract_location(self):
        loc = self.m.HEALTHY_NODE_LEDGER_LOCATION
        self.assertEqual((loc["repository"], loc["ref"], loc["namespace"], loc["new_ref"], loc["new_ledger_root"]),
                         ("StegVerse-org/.github", "refs/stegverse/organization-ledger",
                          "repository-ledger/StegVerse-org/LLM-adapter", False, False))
        self.assertEqual(self.m.healthy_node_ledger_root("/x"), "/x/repository-ledger/StegVerse-org/LLM-adapter")
        anchor = self.m.load_pinned_intr()[0]["endpoint_ledger_anchor"]
        seen, evaluated = [], []
        real_verify, real_evaluate = anchor.verify_anchor, anchor.hne.evaluate

        def spy_anchor(*a, **kw):
            seen.append(kw)
            return real_verify(*a, **kw)

        def spy_evaluate(node_id, **kw):
            evaluated.append(kw)
            return real_evaluate(node_id, **kw)
        source = e0_health_ledger("SV-NODE-E0TEST0001")[0]  # (the harness's own proof uses verify_anchor too)
        anchor.verify_anchor, anchor.hne.evaluate = spy_anchor, spy_evaluate
        try:
            response = self.handle(self.runtime_for(source))
        finally:
            anchor.verify_anchor, anchor.hne.evaluate = real_verify, real_evaluate
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT", response)
        # the org namespace is materialized from the observed org-ledger head and handed to evaluate_anchored, with
        # its HEAD pin; the node root is the deployment's PERMANENT endpoint; the observed transport state is passed
        self.assertTrue(str(seen[-1]["org_ledger_root"]).endswith("/repository-ledger/StegVerse-org/LLM-adapter"))
        self.assertRegex(seen[-1]["org_ledger_head_receipt_sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(seen[-1]["endpoint"]["endpoint_kind"], "PERMANENT")
        self.assertEqual((evaluated[-1]["ledger_root"], evaluated[-1]["require_admission"],
                          evaluated[-1]["transport_state"]), (seen[-1]["endpoint"]["ledger_root"], True, "INSTALLED"))
        self.assertEqual((len(seen), len(evaluated)), (1, 1))
        self.assertFalse(Path(seen[-1]["org_ledger_root"]).exists())  # the materialized tree is removed after the call

    def test_the_real_path_today_fails_closed_ledger_not_onboarded(self):
        """The LLM-adapter chain at the contract location is not onboarded and has no genesis: class B."""
        for checkout in (None, e0_empty_ref_checkout(), e0_ref_without_namespace()):
            response = self.handle(self.runtime_for(checkout))
            self.assert_layer1_refusal(response, "repository-ledger/StegVerse-org/LLM-adapter")
            self.assertEqual((response["failure_class"], response["refusal_cause"], response["failed_predicate"]),
                             ("B", "HEALTHY_NODE_LEDGER_NOT_ONBOARDED", "HEALTHY_NODE_LEDGER_CHAIN_ONBOARDED_WITH_GENESIS"))
            self.assertIn("StegVerse-org/LLM-adapter#431", response["retry_entrypoint"])
            self.assertIn("LC-KV-13", response["owning_existing_goal"])
            self.assertIsNone(response["kv_access_receipt"])
        self.assertEqual(self.receipts, [])

    def test_an_onboarded_chain_without_a_report_fails_closed(self):
        """No report: #432 @a2ee67e6 runs health/admission before the transport stages (precedence location, anchor,
        identity, health/admission, transport, carrier), so HEALTH_REPORT_MISSING is no longer masked by transport:
        class B, six fields."""
        response = self.handle(self.runtime_for(e0_health_ledger("SV-NODE-E0TEST0001", report=False)[0]))
        self.assertEqual((response["decision"], response["failure_code"], response["failure_class"],
                          response["refusal_cause"]),
                         ("FAIL_CLOSED", "KV_ACCESS_LAYER1_REFUSED", "B", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY"))
        self.assertEqual((response["health_evaluation"]["reason"], response["health_evaluation"]["failed_stage"]),
                         ("HEALTH_REPORT_MISSING", "HEALTH_AND_ADMISSION"))
        for field in SIX:
            self.assertTrue(response[field], field)
        self.assertIsNone(response["kv_access_receipt"])

    def test_the_pin_records_428_429_and_430_provenance(self):
        pin = self.m.PINNED_HEALTHY_NODE_EVALUATOR
        self.assertEqual([p["commit"][:8] for p in pin["provenance"]],
                         ["0b37fe3b", "5f5f7bbe", "4e1499ab", "3c106de4", "c2c57505", "1cbad77e", "a2ee67e6", "73316297", "74509fec"])
        self.assertEqual({p["source_sha256"] for p in pin["provenance"]}, {pin["source_sha256"]})

    def test_an_unhealthy_superseded_unadmitted_or_foreign_node_is_refused(self):
        # each ledger is built right before it is used: the node's identity proof is over its current chain head
        cases = (
            ({"status": "DEGRADED"}, None, "DENY", "HEALTH_REPORTED_NOT_HEALTHY"),
            ({"superseded_by": "HEALTHY"}, "first", "FAIL_CLOSED", "HEALTH_REPORT_SUPERSEDED"),
            ({}, {"health_report_receipt_sha256": "sha256:" + "0" * 64}, "FAIL_CLOSED", "HEALTH_REPORT_NOT_RECEIPTED"),
        )
        for ledger, evidence, disposition, reason in cases:
            root, first = e0_health_ledger("SV-NODE-E0TEST0001", **ledger)
            if evidence == "first":
                evidence = {"health_report_receipt_sha256": first}
            response = self.handle(self.runtime_for(root), evidence)
            self.assert_layer1_refusal(response, reason)
            self.assertEqual((response["health_evaluation"]["disposition"], response["health_evaluation"]["reason"]),
                             (disposition, reason))
        # a node the boundary refused: #432 @a2ee67e6 decides admission before transport, so NODE_NOT_ADMITTED
        response = self.handle(self.runtime_for(e0_health_ledger("SV-NODE-E0TEST0001", admitted=False)[0]))
        self.assert_layer1_refusal(response, "NODE_NOT_ADMITTED")
        self.assertEqual((response["refusal_cause"], response["health_evaluation"]["reason"],
                          response["health_evaluation"]["failed_stage"]),
                         ("NODE_NOT_CURRENTLY_ADMITTED_HEALTHY", "NODE_NOT_ADMITTED", "HEALTH_AND_ADMISSION"))
        # another node's endpoint or a foreign producer's receipts are refused by evaluate_anchored's anchored-root check
        for root, reason in ((e0_health_ledger("SV-NODE-E0OTHER001")[0], None),
                             (e0_health_ledger("SV-NODE-E0TEST0001", foreign=True)[0], "FOREIGN_PRODUCER_RECEIPT")):
            response = self.handle(self.runtime_for(root))
            self.assertEqual((response["decision"], response["failure_code"]),
                             ("FAIL_CLOSED", self.m.ANCHOR_REFUSAL_CODE), response)
            self.assertIsNone(response["kv_access_receipt"])
            if reason:
                self.assertEqual(response["health_evaluation"]["reason"], reason)
        self.assertEqual(self.receipts, [])  # refused before authority, policy or any receipt

    def test_health_is_never_caller_asserted(self):
        for evidence in ({"healthy": True}, {"healthy_node_established": True}, "yes",
                         {"health_report_receipt_sha256": "not-a-sha"}):
            response = self.handle(self.runtime, evidence)
            self.assert_layer1_refusal(response, "never caller-asserted")
            self.assertEqual(response["failure_class"], "C")

    def test_a_tampered_vendored_evaluator_is_not_resolved(self):
        source = e0_health_ledger("SV-NODE-E0TEST0001")[0]
        files = self.m.PINNED_ANCHORED_EVALUATOR["vendored_files"]
        key = next(k for k in files if k.endswith("healthy_node_evaluator.py"))
        original = files[key]
        files[key] = "sha256:" + "f" * 64  # the bytes on disk no longer match the pin
        try:
            evaluator, why = self.m.resolve_pinned_healthy_node_evaluator()
            self.assertIsNone(evaluator)
            self.assertIn("not the pinned", why)
            runtime = self.runtime_for(source)
            response = self.handle(runtime)
        finally:
            files[key] = original
        self.assert_layer1_refusal(response, "never asserts a node's health itself")
        self.assertEqual(response["failure_class"], "B")
        self.assertIn("LLM-adapter", response["required_evidence_or_repair"])

    def test_an_evaluator_that_raises_or_returns_a_malformed_allow_is_refused(self):
        anchor = self.m.load_pinned_intr()[0]["endpoint_ledger_anchor"]
        evaluator = anchor.hne.evaluate
        root = e0_health_ledger("SV-NODE-E0TEST0001")[0]

        def raising(*_, **__):
            raise RuntimeError("down")

        def flagged(*_, **__):  # a bare caller flag is not the evaluator's ALLOW
            return {"disposition": "ALLOW", "healthy_node_established": True}

        def other_node(node_id, **kw):
            return {**evaluator(node_id, **kw), "node_id": "SV-NODE-E0OTHER001"}

        def no_admission(node_id, **kw):
            return evaluator(node_id, **{**kw, "require_admission": False})
        for bad in (raising, flagged, other_node, no_admission):
            # injected as the decider: refused by identity (LC-KV-10) before it is ever called
            self.assert_layer1_refusal(self.handle(self.runtime_for(root, bad)), "",
                                       "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED")
            # behind the genuine evaluate_anchored (the inner evaluate misbehaving): refused by the ALLOW-shape checks
            anchor.hne.evaluate = bad
            try:
                response = self.handle(self.runtime_for(root))
            finally:
                anchor.hne.evaluate = evaluator
            self.assert_layer1_refusal(response, "", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY")

    def test_malformed_transitions_return_dispositions(self):
        for request in (None, [], {"schema_version": "x"}):
            response = self.runtime.handle(request, intr_envelope={}, intr_receipt_ref="sha256:" + "a" * 64)
            self.assert_layer1_refusal(response, "")


if __name__ == "__main__":
    unittest.main()

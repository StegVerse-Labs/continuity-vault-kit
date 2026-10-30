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

from kv_two_layer_e0 import E0_TRANSPORT, e0_health_ledger, e0_node_identity_key, healthy_node_kwargs  # noqa: E402
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
    decided by the pinned InTr evaluator (StegVerse-org/LLM-adapter#430 @919851cb, which carried #429 and #428; merged as
    649f0775 on LLM-adapter main), over the requesting node's OWN transition ledger. There is no organization ledger in this model."""

    NODE = "SV-NODE-E0TEST0001"

    def handle(self, runtime, evidence=None, envelope=None):
        request = self.request()
        return runtime.handle(request, intr_envelope=envelope or self.envelope(request),
                              intr_receipt_ref="sha256:" + "a" * 64, healthy_node_evidence=evidence)

    def runtime_for(self, chain, evaluator=None):
        return self.m.KVInterlockRuntime(authority_validator=lambda *_: True, policy_evaluator=self.policy,
                                         receipt_store=self.store_receipt, clock=lambda: self.now,
                                         healthy_node_evaluator=evaluator, healthy_node_chain=chain)

    def test_admitted_healthy_node_gets_a_kv_access_receipt(self):
        response = self.handle(self.runtime)
        self.assertEqual(response["decision"], "ALLOW_BOUNDED_CONTEXT")
        receipt = response["kv_access_receipt"]
        self.assertEqual((receipt["boundary"], receipt["layer"], receipt["minted_by"]),
                         ("INTR_DEVICE_KV", 1, "KVInterlockRuntime.handle"))
        self.assertEqual(receipt["requester_node_ref"], self.NODE)
        self.assertEqual(receipt["response_hash"], response["receipt"]["response_hash"])
        self.assertEqual(receipt["healthy_node_evaluator"], self.m.PINNED_HEALTHY_NODE_EVALUATOR_ID)
        self.assertEqual(receipt["healthy_node_evaluator_source_sha256"],
                         self.m.PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"])
        evaluation = receipt["healthy_node_receipt"]
        self.assertEqual((evaluation["schema"], evaluation["disposition"], evaluation["node_id"],
                          evaluation["admission_required"]),
                         ("stegverse.healthy-node-evaluation/v1", "ALLOW", self.NODE, True))
        binding = receipt["healthy_node_ledger_binding"]
        self.assertEqual((binding["kind"], binding["genesis_pinned_by"]), ("NODE_OWN_LEDGER_CHAIN", "DEPLOYMENT_BINDING"))
        self.assertEqual(binding["chain_head_receipt_sha256"], evaluation["chain_head_receipt_sha256"])
        self.assertNotIn("ledger_root", binding)  # a deployment path is never recorded
        self.assertNotIn("endpoint_kind_schema", receipt)
        self.assertEqual(self.runtime.verify_kv_access_receipt(receipt["receipt_hash"]), receipt)
        self.assertIsNone(self.runtime.verify_kv_access_receipt(self.m.sha256_uri({"forged": True})))

    def test_the_vendored_evaluator_is_byte_identical_to_the_pin(self):
        evaluator, why = self.m.resolve_pinned_healthy_node_evaluator()
        self.assertEqual(why, "")
        self.assertEqual(self.m.evaluator_identity(evaluator), self.m.PINNED_HEALTHY_NODE_EVALUATOR_ID)
        pin = self.m.PINNED_HEALTHY_NODE_EVALUATOR
        pinned_dir = ROOT / "runtime" / "intr_pinned" / "llm_adapter"
        self.assertEqual("sha256:" + hashlib.sha256((pinned_dir / "healthy_node_evaluator.py").read_bytes()).hexdigest(),
                         pin["source_sha256"])
        self.assertEqual(pin["source_sha256"],
                         "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58")

    def test_the_exec_targets_of_the_pinned_code_are_a_literal_tuple(self):
        # The adjacency ruling's finish-point closure analysis resolves an exec target only from literals and static
        # constants; a computed tuple (a generator over the load order) fails closed ADJACENCY_RULING_FINISH_POINT_CLOSURE_UNRESOLVED.
        import ast
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        values = [n.value for n in tree.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "_PINNED_EXEC_SOURCES" for t in n.targets)]
        self.assertEqual(len(values), 1)
        self.assertIsInstance(values[0], ast.Tuple)
        self.assertEqual([e.args[2].value[:-len(".py")] for e in values[0].elts], list(self.m._PINNED_LOAD_ORDER))

    def test_layer_1_calls_the_bare_pinned_evaluate_over_the_bound_node_chain(self):
        real = self.m.resolve_pinned_healthy_node_evaluator()[0]
        source = e0_health_ledger(self.NODE)[0]
        calls = []

        def spy(node_id, **kw):
            calls.append((node_id, kw))
            return real(node_id, **kw)
        runtime = self.runtime_for(source, evaluator=spy)
        runtime._EXERCISE_ONLY_UNPINNED_DECIDER = True  # lets the spy observe the call; its receipts record NOT_THE_PINNED_OBJECT
        self.assertEqual(self.handle(runtime)["decision"], "ALLOW_BOUNDED_CONTEXT")
        node_id, kw = calls[-1]
        self.assertEqual(node_id, self.NODE)
        self.assertEqual(sorted(kw), ["ledger_root", "report_receipt_sha256", "repository", "require_admission",
                                      "transport_state"])
        self.assertEqual((kw["require_admission"], kw["transport_state"], kw["repository"]),
                         (True, "INSTALLED", "StegVerse-org/LLM-adapter"))
        self.assertEqual(kw["ledger_root"], source["ledger_root"])
        self.assertIsNone(kw["report_receipt_sha256"])

    def test_the_chain_is_the_nodes_own_ledger_bound_by_the_deployment(self):
        # no organization ledger, git ref or contract location is involved anywhere in the binding
        self.assertFalse(hasattr(self.m, "HEALTHY_NODE_LEDGER_LOCATION"))
        self.assertFalse(hasattr(self.m, "healthy_node_ledger_root"))
        source = e0_health_ledger(self.NODE)[0]
        self.assertEqual(set(source), {"kind", "ledger_root", "genesis_receipt_sha256"})
        self.assertEqual(source["kind"], self.m.NODE_CHAIN_SOURCE)
        self.assertEqual(self.handle(self.runtime_for(source))["decision"], "ALLOW_BOUNDED_CONTEXT")
        # a caller-shaped source (extra keys, another kind, a bare path) is refused
        for bad in ({**source, "org_ledger_git_dir": "/tmp/x"}, {**source, "kind": "ORG_LEDGER"},
                    {"ledger_root": source["ledger_root"]}, source["ledger_root"]):
            response = self.handle(self.runtime_for(bad))
            self.assert_layer1_refusal(response, "by the deployment", "LEDGER_SOURCE_NOT_BOUND_BY_DEPLOYMENT")
            self.assertEqual(response["failure_class"], "C")

    def test_the_real_path_today_fails_closed_no_chain_bound(self):
        """Production binds no node chain and no InTr transport is installed: class B (the evaluator stack is on main)."""
        for chain in (None, {"kind": self.m.NODE_CHAIN_SOURCE, "ledger_root": "/nonexistent-e0",
                             "genesis_receipt_sha256": "sha256:" + "0" * 64}):
            response = self.handle(self.runtime_for(chain))
            self.assert_layer1_refusal(response, "own transition ledger", self.m.HEALTHY_NODE_LEDGER_REFUSAL_CAUSE)
            self.assertEqual((response["failure_class"], response["failed_predicate"]),
                             ("B", self.m.HEALTHY_NODE_LEDGER_PREDICATE))
            self.assertIn("LC-KV-13", response["owning_existing_goal"])
            self.assertIsNone(response["kv_access_receipt"])
        rows = {r.get("failure_code"): r for r in self.m.layer1_prerequisites() if r["disposition"] != "ALLOW"}
        self.assertEqual(set(rows), {"INTR_TRANSPORT_NOT_INSTALLED"} - ({"INTR_TRANSPORT_NOT_INSTALLED"}
                                                                        if self.m.observe_intr_transport()[0] else set()))
        for row in rows.values():
            self.assertEqual(row["failure_class"], "B")
            for field in SIX:
                self.assertTrue(row[field], field)
        self.assertEqual(self.receipts, [])

    def test_a_wrong_genesis_pin_or_an_unreadable_chain_is_refused(self):
        source = e0_health_ledger(self.NODE, pin_genesis="sha256:" + "1" * 64)[0]
        response = self.handle(self.runtime_for(source))
        self.assert_layer1_refusal(response, "genesis", "NODE_LEDGER_GENESIS_MISMATCH")
        self.assertEqual(response["failure_class"], "C")
        good = e0_health_ledger(self.NODE)[0]
        head = Path(good["ledger_root"]) / "HEAD.json"
        head.write_text("{not json", encoding="utf-8")
        self.assert_layer1_refusal(self.handle(self.runtime_for(good)), "HEAD.json",
                                   self.m.HEALTHY_NODE_LEDGER_REFUSAL_CAUSE)

    def test_an_onboarded_chain_without_a_report_fails_closed(self):
        response = self.handle(self.runtime_for(e0_health_ledger(self.NODE, report=False)[0]))
        self.assertEqual((response["decision"], response["failure_code"], response["failure_class"],
                          response["refusal_cause"]),
                         ("FAIL_CLOSED", "KV_ACCESS_LAYER1_REFUSED", "B", "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY"))
        self.assertEqual(response["health_evaluation"]["reason"], "HEALTH_REPORT_MISSING")
        for field in SIX:
            self.assertTrue(response[field], field)
        self.assertIsNone(response["kv_access_receipt"])

    def test_the_pin_records_428_429_and_430_provenance_and_the_admission_order(self):
        pin = self.m.PINNED_HEALTHY_NODE_EVALUATOR
        self.assertEqual(pin["commit"][:8], "919851cb")
        self.assertEqual([p["commit"][:8] for p in pin["provenance"]][-3:], ["f2ccfc28", "6a51553a", "919851cb"])
        self.assertTrue(pin["on_upstream_main"])
        self.assertEqual(pin["merge_commit"], "649f0775a1c4a6203bbbca835234453c9b6aee1f")
        self.assertTrue(pin["admission_order"].startswith(
            "StegVerse-Labs/StegOS#430 (supersedes #426; merged d7b23eb5), then StegVerse-org/LLM-adapter#430"))
        self.assertNotIn("open draft", str(pin))
        self.assertEqual({p["source_sha256"] for p in pin["provenance"] if "source_sha256" in p} - {pin["source_sha256"]},
                         set())

    def test_an_unhealthy_superseded_unadmitted_or_foreign_node_is_refused(self):
        cases = (
            ({"status": "DEGRADED"}, None, "DENY", "HEALTH_REPORTED_NOT_HEALTHY"),
            ({"superseded_by": "HEALTHY"}, "first", "FAIL_CLOSED", "HEALTH_REPORT_SUPERSEDED"),
            ({}, {"health_report_receipt_sha256": "sha256:" + "0" * 64}, "FAIL_CLOSED", "HEALTH_REPORT_NOT_RECEIPTED"),
        )
        for ledger, evidence, disposition, reason in cases:
            root, first = e0_health_ledger(self.NODE, **ledger)
            if evidence == "first":
                evidence = {"health_report_receipt_sha256": first}
            response = self.handle(self.runtime_for(root), evidence)
            self.assert_layer1_refusal(response, reason)
            self.assertEqual((response["health_evaluation"]["disposition"], response["health_evaluation"]["reason"]),
                             (disposition, reason))
        response = self.handle(self.runtime_for(e0_health_ledger(self.NODE, admitted=False)[0]))
        self.assert_layer1_refusal(response, "NODE_NOT_ADMITTED")
        self.assertEqual((response["refusal_cause"], response["health_evaluation"]["reason"]),
                         ("NODE_NOT_CURRENTLY_ADMITTED_HEALTHY", "NODE_NOT_ADMITTED"))
        self.assertEqual(self.receipts, [])  # refused before authority, policy or any receipt

    def test_a_foreign_producer_chain_that_bare_evaluate_allows_is_refused_by_kv(self):
        """Bare evaluate() ALLOWs a report no pinned producer wrote; KV's provenance check refuses it."""
        source = e0_health_ledger(self.NODE, foreign=True)[0]
        hne = self.m.load_pinned_intr()[0]["healthy_node_evaluator"]
        self.assertEqual(hne.evaluate(self.NODE, ledger_root=source["ledger_root"], transport_state="INSTALLED",
                                      require_admission=True)["disposition"], "ALLOW")
        response = self.handle(self.runtime_for(source))
        self.assert_layer1_refusal(response, "", self.m.PROVENANCE_REFUSAL_CODE)
        self.assertEqual(response["failure_class"], "C")
        self.assertEqual(self.receipts, [])

    def test_the_authenticated_key_must_be_the_key_the_chain_binds(self):
        other = e0_node_identity_key(self.NODE, "another-key:")
        # the transport authenticates a key the chain's NODE_IDENTITY_BINDING does not bind
        response = self.handle(self.runtime_for(e0_health_ledger(self.NODE, transport_key=other)[0]))
        self.assert_layer1_refusal(response, "", self.m.NODE_KEY_REFUSAL_CODE)
        self.assertEqual(response["failure_class"], "C")
        # the chain binds another key than the node's authenticated one
        response = self.handle(self.runtime_for(e0_health_ledger(self.NODE, bound_key=other)[0]))
        self.assert_layer1_refusal(response, "", self.m.NODE_KEY_REFUSAL_CODE)
        # a restored enrolment (matching key) admits again
        self.assertEqual(self.handle(self.runtime_for(e0_health_ledger(self.NODE)[0]))["decision"],
                         "ALLOW_BOUNDED_CONTEXT")
        E0_TRANSPORT.enroll(self.NODE)

    def test_another_nodes_chain_is_refused(self):
        response = self.handle(self.runtime_for(e0_health_ledger("SV-NODE-E0OTHER001", enroll=False)[0]))
        self.assertEqual(response["decision"], "FAIL_CLOSED")
        self.assertIsNone(response["kv_access_receipt"])
        self.assertEqual(self.receipts, [])

    def test_health_is_never_caller_asserted(self):
        for evidence in ({"healthy": True}, {"healthy_node_established": True}, "yes",
                         {"health_report_receipt_sha256": "not-a-sha"}):
            response = self.handle(self.runtime, evidence)
            self.assert_layer1_refusal(response, "never caller-asserted")
            self.assertEqual(response["failure_class"], "C")

    def test_a_tampered_vendored_evaluator_is_not_resolved(self):
        source = e0_health_ledger(self.NODE)[0]
        files = self.m.PINNED_INTR_FILES["vendored_files"]
        key = next(k for k in files if k.endswith("healthy_node_evaluator.py"))
        original = files[key]
        files[key] = "sha256:" + "f" * 64  # the bytes on disk no longer match the pin
        try:
            evaluator, why = self.m.resolve_pinned_healthy_node_evaluator()
            self.assertIsNone(evaluator)
            self.assertIn("not the pinned", why)
            response = self.handle(self.runtime_for(source))
        finally:
            files[key] = original
        self.assert_layer1_refusal(response, "never asserts a node's health itself")
        self.assertEqual(response["failure_class"], "B")
        self.assertIn("LLM-adapter", response["required_evidence_or_repair"])

    def test_an_evaluator_that_raises_or_returns_a_malformed_allow_is_refused(self):
        hne = self.m.load_pinned_intr()[0]["healthy_node_evaluator"]
        evaluator = hne.evaluate
        root = e0_health_ledger(self.NODE)[0]

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
                                       "LAYER1_NOT_EVALUATED_THROUGH_THE_PINNED_EVALUATE")
        # the pinned function object itself misbehaving (patched at the module attribute): the runtime resolved the
        # object at construction, so a fresh runtime resolves the replacement and the load-time code hash refuses it
        for bad in (raising, flagged, other_node, no_admission):
            hne.evaluate = bad
            try:
                response = self.handle(self.runtime_for(root))
            finally:
                hne.evaluate = evaluator
            self.assertEqual(response["decision"], "FAIL_CLOSED", bad.__name__)
            self.assertIsNone(response["kv_access_receipt"], bad.__name__)

    def test_malformed_transitions_return_dispositions(self):
        for request in (None, [], {"schema_version": "x"}):
            response = self.runtime.handle(request, intr_envelope={}, intr_receipt_ref="sha256:" + "a" * 64)
            self.assert_layer1_refusal(response, "")


if __name__ == "__main__":
    unittest.main()

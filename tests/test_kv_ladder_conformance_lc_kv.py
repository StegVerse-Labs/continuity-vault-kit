"""Negative tests for P1's ladder-conformance DENYs on cvk#258 (StegVerse-Labs/.github#3330 @578583be and rev 4
@c8b8d156).

Each test closes one bypass P1 named: LC-KV-10 (layer 1 and layer 2 pin the decider by identity and load-time code
digest, never by its self-reported name), LC-KV-15 (org ledger bound by contract location at an observed head with its
genesis derived from its own receipt; node roots admitted only by #432's evaluate_anchored; identity from the installed
InTr transport; real transport state), LC-KV-07 (gated read_stream / append_extension with provenance) and LC-KV-03
(only the real layer-2 gate may attest the access layers). E0 stand-ins are labelled E0_STANDIN_TEST_ONLY_NOT_EVIDENCE.
Stdlib only: no cryptography import (Coordination class D ruling).
"""
from __future__ import annotations

import copy
import contextlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from execution.adapter import canonical_sha256  # noqa: E402
from execution.vault_store import KnowledgeVaultExecutionStore, SkapAccessRefused  # noqa: E402
from kv_two_layer_e0 import (  # noqa: E402
    E0_CONTRACT_431, E0_CONTRACT_PINNED, E0_GENESIS, E0_LABEL, E0_ROUTE_KEY_ID, E0_TRANSPORT, NEVER_ENROLLED_NODE, NODE,
    TwoLayers, e0_attest, e0_contract, e0_health_ledger, e0_node_identity_key, e0_without_append_route,
    PRODUCTION_TRUST_ANCHORS, e0_scratch_ledger_root, e0_trust_anchors, pinned, production_trust_anchors,
)
from kv_two_layer_e0 import enter_e0 as setUpModule, exit_e0 as tearDownModule  # noqa: E402,F401
from runtime import kv_interlock_endpoint as ep  # noqa: E402
from runtime import task_registry_event_sovereign_kv_binding as binding_module  # noqa: E402
from runtime.kv_skap_layer2 import SkapLayer2Gate, kv_skap_transition  # noqa: E402
from test_skap_kv_persistence import SkapKvPersistenceTests  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")
VENDORED_ANCHOR = str(ROOT / "runtime" / "intr_pinned" / "llm_adapter" / "endpoint_ledger_anchor.py")


def spoofed_evaluate_anchored():
    """A callable that claims to be the pinned evaluate_anchored by every self-reported attribute (__module__,
    __qualname__, __name__ and its code object's source filename) and delegates to the real one."""
    real = pinned()["endpoint_ledger_anchor"].evaluate_anchored

    def evaluate_anchored(node_id, **kw):
        return real(node_id, **kw)
    evaluate_anchored.__module__ = "llm_adapter.endpoint_ledger_anchor"
    evaluate_anchored.__qualname__ = "evaluate_anchored"
    evaluate_anchored.__code__ = evaluate_anchored.__code__.replace(co_filename=VENDORED_ANCHOR)
    return evaluate_anchored


def refused(case, out, cause, klass=None, code="KV_ACCESS_LAYER1_REFUSED"):
    case.assertEqual(out["decision"], "FAIL_CLOSED", out)
    if code is None:  # evaluate_anchored's own failure_code is carried (anchor refusals)
        case.assertEqual(out["refusal_cause"], cause, out)
        case.assertEqual(out["failure_code"], out["health_evaluation"]["failure_code"], out)
    else:
        case.assertEqual((out["failure_code"], out["refusal_cause"]), (code, cause), out)
    if klass:
        case.assertEqual(out["failure_class"], klass, out)
    for field in SIX:
        case.assertTrue(out[field], field)
    case.assertIsNone(out["kv_access_receipt"])


class LcKv10PinnedByIdentity(unittest.TestCase):
    def admit(self, layers, kv_hash):
        return layers.gate.admit(kv_skap_transition(principal_ref=layers.principal, operation="SKAP_READ",
                                                    subject_ref="s", prior_receipt_hash=kv_hash))

    def test_a_spoofed_module_qualname_and_filename_is_refused_at_both_layers(self):
        spoof = spoofed_evaluate_anchored()
        self.assertEqual((spoof.__module__, spoof.__qualname__, spoof.__code__.co_filename),
                         ("llm_adapter.endpoint_ledger_anchor", "evaluate_anchored", VENDORED_ANCHOR))
        self.assertIsNone(ep.pinned_decider_identity(spoof))
        self.assertEqual(ep.evaluator_identity(spoof), ep.NOT_PINNED_DECIDER)
        record = ep._layer1_decider_record(spoof)
        self.assertEqual((record["healthy_node_anchor_check"], record["healthy_node_anchor_check_source_sha256"]),
                         (ep.NOT_PINNED_DECIDER, None))
        layers = TwoLayers(evaluator=spoof)
        refused(self, layers.kv_access(), "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED", "C")
        # even a receipt minted by the genuine runtime is refused at layer 2 once its decider is swapped for the spoof
        genuine = TwoLayers()
        kv_hash = genuine.kv_hash()
        genuine.layer1.healthy_node_evaluator = spoof
        answer = self.admit(genuine, kv_hash)
        self.assertEqual((answer["disposition"], answer["refusal_cause"]),
                         ("FAIL_CLOSED", "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED"))
        for field in SIX:
            self.assertTrue(answer[field], field)

    def test_bare_evaluate_and_a_rewrapped_pin_are_not_the_decider(self):
        m = pinned()
        anchor = m["endpoint_ledger_anchor"]
        self.assertIs(ep.pinned_decider_identity(anchor.evaluate_anchored), ep.PINNED_ANCHORED_EVALUATOR_ID)
        rewrapped = types.FunctionType(anchor.evaluate_anchored.__code__, anchor.evaluate_anchored.__globals__,
                                       "evaluate_anchored", anchor.evaluate_anchored.__defaults__,
                                       anchor.evaluate_anchored.__closure__)
        rewrapped.__kwdefaults__ = anchor.evaluate_anchored.__kwdefaults__
        for decider in (m["healthy_node_evaluator"].evaluate, rewrapped, lambda *a, **k: {}, "llm_adapter.x", None):
            self.assertIsNone(ep.pinned_decider_identity(decider), decider)
        refused(self, TwoLayers(evaluator=m["healthy_node_evaluator"].evaluate).kv_access(),
                "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED", "C")

    def test_edited_pin_fields_are_refused(self):
        layers = TwoLayers()
        receipt = layers.kv_access()["kv_access_receipt"]
        for field, value, cause in (
                ("healthy_node_evaluator", "x.y", "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"),
                ("healthy_node_evaluator_source_sha256", "sha256:" + "0" * 64, "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"),
                ("healthy_node_anchor_check", "x.y", "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED"),
                ("healthy_node_anchor_check_code_sha256", "sha256:" + "0" * 64,
                 "LAYER1_DECIDER_CODE_NOT_THE_PINNED_CODE"),
                ("healthy_node_evaluator_code_sha256", None, "LAYER1_DECIDER_CODE_NOT_THE_PINNED_CODE")):
            self.assertEqual(ep.layer1_receipt_conformance({**receipt, field: value}), cause, field)
        self.assertIsNone(ep.layer1_receipt_conformance(receipt))

    def test_a_subclassed_layer_1_runtime_is_refused(self):
        layers = TwoLayers()
        kv_hash = layers.kv_hash()

        class Lenient(ep.KVInterlockRuntime):
            pass
        layers.layer1.__class__ = Lenient
        answer = self.admit(layers, kv_hash)
        self.assertEqual(answer["disposition"], "FAIL_CLOSED")

    def test_a_receipt_minted_under_e0_anchors_is_refused_under_production(self):
        layers = TwoLayers()
        kv_hash = layers.kv_hash()
        with production_trust_anchors():
            answer = self.admit(layers, kv_hash)
        self.assertEqual(answer["refusal_cause"], "LAYER1_RECEIPT_MINTED_UNDER_OTHER_TRUST_ANCHORS")


class LcKv15LedgerIdentityTransport(unittest.TestCase):
    def test_receipt_binds_contract_location_head_identity_and_transport(self):
        out = TwoLayers().kv_access()
        receipt = out["kv_access_receipt"]
        binding = receipt["healthy_node_ledger_binding"]
        self.assertEqual((binding["kind"], binding["endpoint_kind"], binding["repository"], binding["ref"],
                          binding["namespace"], binding["genesis_derived_from"], binding["genesis_receipt_sha256"]),
                         (ep.LEDGER_SOURCE_ANCHORED, "PERMANENT", "StegVerse-org/.github",
                          "refs/stegverse/organization-ledger", "repository-ledger/StegVerse-org/LLM-adapter",
                          ep.GENESIS_DERIVATION, E0_GENESIS))
        self.assertRegex(binding["observed_head"], r"^[0-9a-f]{40}$")
        self.assertEqual(binding["anchored_by"], ep.PINNED_ANCHORED_EVALUATOR_ID)
        self.assertEqual(binding["node_identity_key"], e0_node_identity_key(NODE))
        self.assertEqual((receipt["intr_transport_state"], receipt["requester_node_ref"], receipt["endpoint_kind"],
                          receipt["trust_anchors_label"]), ("INSTALLED", NODE, "KV", E0_LABEL))
        self.assertEqual(receipt["requester_identity"]["authenticated_by"], "e0-standin-intr-transport")

    def test_scratch_ledger_root_is_refused_on_every_path(self):
        root = e0_scratch_ledger_root(NODE)
        for source in (root, root + "/repository-ledger/StegVerse-org/LLM-adapter",
                       {"ledger_root": root}, {"kind": "SCRATCH", "ledger_root": root}):
            out = TwoLayers(ledger_checkout=source).kv_access()
            self.assertEqual(out["decision"], "FAIL_CLOSED", source)
            self.assertIsNone(out["kv_access_receipt"])
        with production_trust_anchors():
            out = TwoLayers(ledger_checkout=root).kv_access()
        self.assertEqual(out["decision"], "FAIL_CLOSED")

    def test_genesis_is_pinned_by_the_431_contract_not_by_kv(self):
        # #432 @a2ee67e6: evaluate_anchored checks the store's genesis against the contract's
        # expected_genesis_receipt_sha256; KV's own derivation from the receipt was dropped as a duplicate.
        self.assertNotIn("healthy_node_ledger_genesis_receipt_sha256", ep.TRUST_ANCHORS)
        self.assertFalse(hasattr(ep, "_org_genesis_failure"))
        refused(self, TwoLayers(ledger_checkout=e0_health_ledger(NODE, own_genesis=True)[0]).kv_access(),
                "NODE_ROOT_NOT_ANCHORED_ORG_LEDGER_GENESIS_MISMATCH", "C", None)
        with e0_contract(E0_CONTRACT_431):  # #431's location without the pinned genesis
            out = TwoLayers().kv_access()
            refused(self, out, "NODE_ROOT_NOT_ANCHORED_ORG_LEDGER_GENESIS_NOT_PINNED", "B", None)
            # #432 @74509fec: the next attempt is the REPOSITORY_LEDGER_GENESIS_PIN transition, not a person
            self.assertIn("REPOSITORY_LEDGER_GENESIS_PIN", out["health_evaluation"]["next_attempt"])
            pin_row = [r for r in ep.org_ledger_prerequisites() if r.get("failure_code") ==
                       "ORG_LEDGER_GENESIS_NOT_PINNED"]
            self.assertEqual(len(pin_row), 1)
            self.assertIn("REPOSITORY_LEDGER_GENESIS_PIN", pin_row[0]["next_attempt"])
        source = e0_health_ledger(NODE)[0]
        with production_trust_anchors():
            ep.TRUST_ANCHORS["intr_transport"] = E0_TRANSPORT
            out = TwoLayers(ledger_checkout=source).kv_access()
        refused(self, out, "NODE_ROOT_NOT_ANCHORED_ORG_LEDGER_LOCATION_NOT_DESIGNATED", "B", None)

    def test_transport_not_observed_or_not_installed_is_refused(self):
        class NotInstalled:
            transport_id, state = "e0-not-installed", "NOT_YET_ENABLED"

            def authenticate(self, envelope):
                return {"node_id": NODE, "node_identity_key": e0_node_identity_key(NODE)}
        saved = ep.TRUST_ANCHORS["intr_transport"]
        for transport in (None, NotInstalled()):
            ep.TRUST_ANCHORS["intr_transport"] = transport
            try:
                out = TwoLayers().kv_access()
            finally:
                ep.TRUST_ANCHORS["intr_transport"] = saved
            refused(self, out, "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", "B")

    def test_production_transport_is_observed_state_and_refuses_with_six_fields(self):
        """LC-KV-15 (rev 5): production has no installed InTr transport (intr_transport None). It is read as observed
        state, UNKNOWN_NOT_AUTHENTICALLY_OBSERVED, never assumed, and layer 1 refuses with six fields."""
        self.assertIsNone(PRODUCTION_TRUST_ANCHORS["intr_transport"])
        with production_trust_anchors():
            self.assertEqual(ep.observe_intr_transport(), (None, "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED", None))
            production = TwoLayers().kv_access()
        self.assertEqual((production["decision"], production["kv_access_receipt"]), ("FAIL_CLOSED", None))
        for field in SIX:
            self.assertTrue(production[field], field)
        # with the ledger bound, the unobserved production transport itself is the six-field refusal (class B)
        saved = ep.TRUST_ANCHORS["intr_transport"]
        ep.TRUST_ANCHORS["intr_transport"] = PRODUCTION_TRUST_ANCHORS["intr_transport"]
        try:
            out = TwoLayers().kv_access()
        finally:
            ep.TRUST_ANCHORS["intr_transport"] = saved
        refused(self, out, "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", "B")
        self.assertIn("UNKNOWN_NOT_AUTHENTICALLY_OBSERVED", out["required_evidence_or_repair"])

    def test_caller_asserted_identity_is_refused(self):
        stranger = TwoLayers(node=NEVER_ENROLLED_NODE, ledger_checkout=e0_health_ledger(NODE)[0])
        E0_TRANSPORT.enrolled.pop(NEVER_ENROLLED_NODE, None)  # the envelope claims it; the transport never saw it
        refused(self, stranger.kv_access(), "REQUESTER_IDENTITY_NOT_TRANSPORT_AUTHENTICATED", "C")
        claimed = TwoLayers().kv_access(verification_state="CLAIMED")
        self.assertEqual((claimed["decision"], claimed["kv_access_receipt"]), ("FAIL_CLOSED", None))
        with production_trust_anchors():
            out = TwoLayers().kv_access()
        self.assertEqual(out["decision"], "FAIL_CLOSED")


class AnchoredEndpointThroughEvaluateAnchored(unittest.TestCase):
    """Layer 1 binds to #432's evaluate_anchored; Lane B's anchored-root check is authoritative (no duplicate here)."""

    def kv(self, **ledger):
        return TwoLayers(ledger_checkout=e0_health_ledger(NODE, **ledger)[0]).kv_access()

    def anchor_refused(self, out, reason):
        refused(self, out, "NODE_ROOT_NOT_ANCHORED_" + reason, code=ep.ANCHOR_REFUSAL_CODE)
        self.assertEqual(out["failure_code"], "EPHEMERAL_NODE_LEDGER_NOT_ANCHORED")
        self.assertEqual(out["health_evaluation"]["schema"], ep.PINNED_ANCHORED_EVALUATOR["result_schema"])
        self.assertEqual(out["health_evaluation"]["reason"], reason)

    def test_layer_1_goes_through_evaluate_anchored(self):
        anchor = pinned()["endpoint_ledger_anchor"]
        layers = TwoLayers()
        self.assertIs(layers.layer1.healthy_node_evaluator, anchor.evaluate_anchored)
        calls = []
        real_verify = anchor.verify_anchor

        def spy(*a, **k):
            calls.append(k.get("endpoint"))
            return real_verify(*a, **k)
        anchor.verify_anchor = spy
        try:
            out = layers.kv_access()
        finally:
            anchor.verify_anchor = real_verify
        self.assertEqual(out["decision"], "ALLOW_BOUNDED_CONTEXT", out)
        self.assertEqual([c["endpoint_kind"] for c in calls], ["PERMANENT"])
        receipt = out["kv_access_receipt"]
        self.assertEqual((receipt["healthy_node_anchor_check"], receipt["healthy_node_anchor_check_source_sha256"]),
                         (ep.PINNED_ANCHORED_EVALUATOR_ID, ep.PINNED_ANCHORED_EVALUATOR["source_sha256"]))
        self.assertEqual(receipt["healthy_node_receipt"]["anchor"]["anchor"], "INTR_PATH_RECEIPT_PAIR")

    def test_a_foreign_producer_bare_evaluate_allows_is_refused(self):
        source, _ = e0_health_ledger(NODE, foreign=True)
        bare = pinned()["healthy_node_evaluator"].evaluate(NODE, ledger_root=source["endpoint"]["ledger_root"],
                                                          require_admission=True)
        self.assertEqual(bare["disposition"], "ALLOW")  # why layer 1 must not call bare evaluate()
        self.anchor_refused(TwoLayers(ledger_checkout=source).kv_access(), "FOREIGN_PRODUCER_RECEIPT")

    def test_an_unanchored_node_root_is_refused(self):
        out = self.kv(anchored=False)
        self.assertEqual(out["failure_code"], ep.ANCHOR_REFUSAL_CODE)
        self.assertTrue(out["refusal_cause"].startswith("NODE_ROOT_NOT_ANCHORED_"), out)

    def test_the_transport_key_must_be_the_anchored_genesis_key(self):
        refused(self, self.kv(transport_key=e0_node_identity_key(NODE, salt="other")),
                "REQUESTER_KEY_NOT_THE_ANCHORED_NODE_IDENTITY_KEY", "C")

    def test_an_ephemeral_node_fails_closed_until_tv_tvc_publishes_a_signer(self):
        """EPHEMERAL anchors are signed envelopes (#432 @1cbad77e). The vendored signers file is empty, so the E0
        envelope's key is not published: six-field FAIL_CLOSED, class B, owner TV/TVC. The file is never patched."""
        self.assertEqual(json.loads((Path(ep._INTR_PINNED_ROOT) / ".stegverse/node-ledger/node-ledger-opened-signers.v1.json")
                                    .read_text(encoding="utf-8"))["signers"], [])
        out = self.kv(kind="EPHEMERAL")
        self.anchor_refused(out, "NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED")
        self.assertEqual(out["failure_class"], "B")
        self.assertTrue(out["owning_existing_goal"].startswith("TV/TVC"), out["owning_existing_goal"])
        self.assertEqual(out["failed_predicate"], "NODE_LEDGER_OPENED_SIGNED_BY_PUBLISHED_KEY")
        self.assertEqual(ep.FINISH_POINT_NODE_ENDPOINT_KIND, "PERMANENT")

    def test_the_pins_are_checked_on_evaluate_anchoreds_allow(self):
        """No per-receipt pinned_digests (#432 @1cbad77e): the pins are bound in the genesis and returned on the ALLOW's
        anchor under KV's key names; KV checks them there."""
        receipt = TwoLayers().kv_access()["kv_access_receipt"]
        self.assertEqual(receipt["healthy_node_receipt"]["anchor"]["pinned_digests"], ep.PINNED_DIGESTS_FROM_GENESIS)
        self.assertEqual(pinned()["endpoint_ledger_anchor"].pinned_digests(), ep.PINNED_DIGESTS_FROM_GENESIS)

    def test_transport_is_read_from_the_nodes_ingress_receipt(self):
        out = self.kv(transport_installed=False)
        self.assertEqual((out["decision"], out["failure_code"], out["failure_class"]),
                         ("FAIL_CLOSED", "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", "B"))
        for field in SIX:
            self.assertTrue(out[field], field)
        self.assertIsNone(out["kv_access_receipt"])

    def test_identity_must_be_proven_by_the_anchored_key(self):
        for proof, reason, failure_class in ((None, "NODE_IDENTITY_PROOF_ABSENT", "B"),
                                             ("other_key", "NODE_IDENTITY_PROOF_INVALID", "C"),
                                             ("stale", "NODE_IDENTITY_PROOF_INVALID", "C")):
            out = self.kv(proof=proof)
            self.assertEqual((out["decision"], out["failure_code"], out["refusal_cause"], out["failure_class"]),
                             ("FAIL_CLOSED", "NODE_IDENTITY_NOT_PROVEN", reason, failure_class), proof)
            for field in SIX:
                self.assertTrue(out[field], field)
        identity = TwoLayers().kv_access()["kv_access_receipt"]["healthy_node_receipt"]["identity"]
        self.assertEqual((identity["node_id"], identity["established_by"]), (NODE, "NODE_IDENTITY_KEY_ED25519_PROOF"))

    def test_no_temp_code_alias_remains(self):
        self.assertFalse([name for name in vars(ep) if "TEMP_" in name])
        self.assertNotIn("TEMP_NODE_LEDGER_NOT_ANCHORED", Path(ep.__file__).read_text(encoding="utf-8"))


class LcKv16CallerStoreAndIngressNeverAllow(unittest.TestCase):
    """LC-KV-16 class and P1 rev 6 (LC-KV-15), through KV's wrapper inside the E0 test anchors: a caller-named object
    store or a caller-appended ingress record never reaches ALLOW. #432 @74509fec refuses each case; KV maps it."""

    def assert_no_allow(self, source, cause, klass, evidence=None):
        out = TwoLayers(ledger_checkout=source).kv_access(evidence=evidence)
        self.assertEqual(out["decision"], "FAIL_CLOSED", out)
        self.assertIsNone(out["kv_access_receipt"])
        refused(self, out, cause, klass, None if cause.startswith("NODE_ROOT_NOT_ANCHORED_") else
                ("INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED" if cause.startswith("INTR_") else "KV_ACCESS_LAYER1_REFUSED"))
        return out

    def test_unlabelled_caller_created_store_is_refused_inside_e0(self):
        # P1 rev 6: at b93b06a4 KV ALLOWed a PERMANENT node on an unlabelled org store the caller created (its genesis
        # derived and carried no label to refuse). Now its genesis is not the contract-pinned one, even if attested.
        for own in (True, "labelled"):
            source = e0_health_ledger(NODE, own_genesis=own)[0]
            out = self.assert_no_allow(source, "NODE_ROOT_NOT_ANCHORED_ORG_LEDGER_GENESIS_MISMATCH", "C")
            self.assertEqual(out["health_evaluation"]["reason"], "ORG_LEDGER_GENESIS_MISMATCH")

    def test_caller_store_with_the_pinned_genesis_but_no_route_attestation_is_refused(self):
        # the pinned genesis is public: a caller can copy it, but cannot get its own head attested by the append route
        deployment = e0_health_ledger(NODE)[0]
        cases = {
            "unattested": e0_health_ledger(NODE, attest=None)[0],
            "callers-own-key": e0_health_ledger(NODE, attest="own_key")[0],
            # the deployment store's genuine attestation replayed onto a caller's store with another head (the
            # caller appended its own ingress record)
            "replayed-route-attestation": {**e0_health_ledger(NODE, carried=False)[0],
                                           "org_ledger_head_attestation": deployment["org_ledger_head_attestation"]},
            "attestation-names-another-location": {**deployment, "org_ledger_head_attestation": e0_attest(
                deployment["org_ledger_git_dir"], org_ledger_location="git+x#refs/heads/main:elsewhere")},
        }
        for name, source in cases.items():
            with self.subTest(name):
                out = self.assert_no_allow(source, "NODE_ROOT_NOT_ANCHORED_ORG_LEDGER_HEAD_NOT_AUTHENTICATED", "C")
                self.assertEqual(out["health_evaluation"]["failed_predicate"],
                                 "ORG_LEDGER_HEAD_AUTHENTICATED_BY_APPEND_ROUTE")

    def test_no_admitted_append_route_refuses_every_store(self):
        with e0_without_append_route():  # the vendored org-ledger-head-signers.v1.json is empty
            self.assert_no_allow(e0_health_ledger(NODE)[0], "NODE_ROOT_NOT_ANCHORED_MERGE_APPEND_PATH_NOT_ADMITTED", "B")

    def test_caller_appended_ingress_record_without_its_intr_carrier_is_refused(self):
        out = self.assert_no_allow(e0_health_ledger(NODE, carried=False)[0],
                                   "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", "B")
        evaluation = out["health_evaluation"]
        self.assertEqual((evaluation["failed_stage"], evaluation["intr_carrier_refusal"]),
                         ("TRANSPORT_INTR_CARRIER", "INTR_CARRIER_NOT_ON_AUTHENTICATED_ORG_LEDGER"))

    def test_a_requester_can_supply_neither_the_store_nor_the_attestation(self):
        source = e0_health_ledger(NODE)[0]
        out = TwoLayers(ledger_checkout=source).kv_access(
            evidence={"org_ledger_head_attestation": source["org_ledger_head_attestation"]})
        refused(self, out, "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY", "C")
        out = TwoLayers(ledger_checkout={**source, "org_ledger_git_dir_override": "/tmp/x"}).kv_access()
        self.assertEqual(out["decision"], "FAIL_CLOSED")
        self.assertIsNone(out["kv_access_receipt"])


class LcKv15OnlyAllowPath(unittest.TestCase):
    """P1 rev 6: the only ALLOW goes through the #431-contract-located, genesis-pinned, receipt-authenticated org ledger
    (proved in the harness, not only by production refusing)."""

    def test_the_allow_reads_the_contract_located_genesis_pinned_route_attested_store(self):
        modules = pinned()
        anchor, location = modules["endpoint_ledger_anchor"], modules["org_ledger_location"]
        real, seen = anchor.designated_org_ledger, []

        @contextlib.contextmanager
        def spy(git_dir, attestation=None):
            with real(git_dir, attestation) as (root, failed):
                seen.append({"git_dir": git_dir, "attestation": attestation, "failed": failed,
                             "contract": location.CONTRACT_PATH, "location": location.org_ledger_location()})
                yield root, failed
        source = e0_health_ledger(NODE)[0]
        anchor.designated_org_ledger = spy
        try:
            out = TwoLayers(ledger_checkout=source).kv_access()
        finally:
            anchor.designated_org_ledger = real
        self.assertEqual(out["decision"], "ALLOW_BOUNDED_CONTEXT", out)
        self.assertGreaterEqual(len(seen), 1)  # verify_anchor and evaluate_anchored both read the designated store
        for call in seen:
            self.assertIsNone(call["failed"])
            self.assertEqual(call["contract"], E0_CONTRACT_PINNED)
            self.assertEqual((call["location"]["ref"], call["location"]["namespace"],
                              call["location"]["expected_genesis_receipt_sha256"]),
                             ("refs/stegverse/organization-ledger", "repository-ledger/StegVerse-org/LLM-adapter",
                              E0_GENESIS))
            self.assertEqual(call["attestation"], source["org_ledger_head_attestation"])
            self.assertEqual(call["attestation"]["key_id"], E0_ROUTE_KEY_ID)
            self.assertTrue(str(call["git_dir"]).startswith(str(source["org_ledger_git_dir"])) or
                            os.path.samefile(call["git_dir"], source["org_ledger_git_dir"]), call["git_dir"])
        receipt = out["kv_access_receipt"]
        binding, evaluation = receipt["healthy_node_ledger_binding"], receipt["healthy_node_receipt"]
        self.assertEqual(binding["genesis_receipt_sha256"], E0_GENESIS)
        attested = source["org_ledger_head_attestation"]
        self.assertEqual((attested["genesis_receipt_sha256"], attested["head_receipt_sha256"]),
                         (E0_GENESIS, evaluation["anchor"]["org_ledger_head_receipt_sha256"]))
        self.assertEqual(evaluation["observed_transport"]["intr_carrier"]["org_ledger_head_receipt_sha256"],
                         attested["head_receipt_sha256"])
        self.assertEqual(binding["chain_head_receipt_sha256"], attested["head_receipt_sha256"])
        self.assertEqual(evaluation["observed_transport"]["signal_sha256"],
                         modules["intr_transport_carrier"].sha({"mode": "ESTABLISH_GENESIS", "node_ref": NODE,
                                                                "predecessor": None, "node_class": "LLM_ADAPTER"}))

    def test_removing_any_one_leg_leaves_no_allow(self):
        legs = {
            "no #431 location (vendored contract)": (lambda: e0_contract(ep_contract_path()), {}),
            "no pinned genesis": (lambda: e0_contract(E0_CONTRACT_431), {}),
            "no admitted append route": (e0_without_append_route, {}),
            "unattested head": (contextlib.nullcontext, {"attest": None}),
            "caller genesis": (contextlib.nullcontext, {"own_genesis": True}),
            "no InTr carrier": (contextlib.nullcontext, {"carried": False}),
        }
        for name, (context, ledger) in legs.items():
            with self.subTest(name):
                source = e0_health_ledger(NODE, **ledger)[0]
                with context():
                    out = TwoLayers(ledger_checkout=source).kv_access()
                self.assertEqual(out["decision"], "FAIL_CLOSED", out)
                self.assertIsNone(out["kv_access_receipt"])


class LcKv18OrgLedgerPrerequisites(unittest.TestCase):
    """LC-KV-18: org-ledger-head-signers.v1.json is empty and gates every PERMANENT anchor, so the finish point records
    it (with #431's location and genesis legs) as six-field FAIL_CLOSED class B rows; owner TV/TVC + Lane C."""

    def test_production_records_each_unmet_leg_with_six_fields(self):
        from runtime import kv_skap_vault as kv
        with production_trust_anchors():
            rows = {r["failure_code"]: r for r in kv.finish_point()["org_ledger_prerequisites"]}
            self.assertEqual(pinned()["org_ledger_location"].load_head_signers.__module__,
                             "llm_adapter.org_ledger_location")  # the vendored, empty signers file
        self.assertEqual(set(rows), {"ORG_LEDGER_LOCATION_NOT_DESIGNATED", "ORG_LEDGER_GENESIS_NOT_PINNED",
                                     "MERGE_APPEND_PATH_NOT_ADMITTED"})
        for row in rows.values():
            self.assertEqual((row["disposition"], row["failure_class"]), ("FAIL_CLOSED", "B"))
            for field in SIX:
                self.assertTrue(isinstance(row[field], str) and row[field].strip(), field)
        lc18 = rows["MERGE_APPEND_PATH_NOT_ADMITTED"]
        self.assertEqual(lc18["tracked_by"], "LC-KV-18")
        self.assertIn("TV/TVC", lc18["dependency_owner"])
        self.assertIn("Lane C", lc18["dependency_owner"])

    def test_inside_the_e0_anchors_every_leg_is_met(self):
        self.assertEqual({r["disposition"] for r in ep.org_ledger_prerequisites()}, {"ALLOW"})
        with e0_without_append_route():
            rows = [r for r in ep.org_ledger_prerequisites() if r["disposition"] != "ALLOW"]
        self.assertEqual([r["failure_code"] for r in rows], ["MERGE_APPEND_PATH_NOT_ADMITTED"])


def ep_contract_path():
    return Path(ep.__file__).resolve().parent / "intr_pinned" / ".stegverse" / "transition-ledger" / "contract.json"


class LcKv07GatedStreams(unittest.TestCase):
    def setUp(self):
        self.layers = TwoLayers(principal="principal:alice")
        self.bundle = SkapKvPersistenceTests.make_bundle(self)

    def access(self, operation, stream_id):
        return {"skap_gate": self.layers.gate, "principal_ref": "principal:alice",
                "skap_access_receipt_hash": self.layers.skap_hash(operation, stream_id)}

    def test_append_extension_refuses_skap_records(self):
        sealed, receipt = self.bundle
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            for record in ({"schema": "stegverse.kv.skap_sealed_credential_record/v1", "sealed_material": sealed},
                           {"sealed_material": sealed}, receipt):
                with self.assertRaises(SkapAccessRefused):
                    store.append_extension("s1", record)
                with self.assertRaises(SkapAccessRefused):
                    store.append_receipt("s1", record)
            self.assertFalse((Path(tmp) / "Extensions" / "s1.jsonl").exists() and
                             (Path(tmp) / "Extensions" / "s1.jsonl").read_text().strip())

    def forge(self, store, record):
        path = store.execution_root / "Extensions" / "s1.jsonl"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"record": record, "record_sha256": canonical_sha256(record)}) + "\n")

    def legit(self, store):
        sealed, receipt = self.bundle
        store.append_skap_sealed_credential("s1", sealed, receipt, **self.access("SKAP_SEALED_CREDENTIAL_APPEND", "s1"))
        path = store.execution_root / "Extensions" / "s1.jsonl"
        return json.loads(path.read_text(encoding="utf-8").splitlines()[0])["record"]

    def test_forged_records_are_refused_by_the_gated_read(self):
        sealed, _ = self.bundle
        other = copy.deepcopy(sealed)
        other["ciphertext_b64"] = ("B" if sealed["ciphertext_b64"][0] == "A" else "A") + sealed["ciphertext_b64"][1:]
        forgeries = {
            "payload swapped under a real receipt": lambda r: {**r, "sealed_material": other,
                                                               "sealed_material_hash": canonical_sha256(other)},
            "replayed record": lambda r: r,
            "fabricated receipt hashes": lambda r: {**r, "access": {"kv_access_receipt_hash": "sha256:" + "1" * 64,
                                                                    "skap_access_receipt_hash": "sha256:" + "2" * 64}},
            "no access block": lambda r: {k: v for k, v in r.items() if k != "access"},
        }
        for name, forge in forgeries.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                store = KnowledgeVaultExecutionStore(tmp)
                self.forge(store, forge(self.legit(store)))
                with self.assertRaisesRegex(SkapAccessRefused, "SKAP_RECORD_PROVENANCE_NOT_VERIFIED"):
                    store.read_skap_sealed_credential("s1", **self.access("SKAP_SEALED_CREDENTIAL_READ", "s1"))

    def test_read_stream_refuses_skap_streams_and_the_legit_read_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            self.legit(store)
            for category in ("Extensions", "Receipts"):
                with self.assertRaises(SkapAccessRefused):
                    store.read_stream(category, "s1")
            self.assertEqual(store.read_skap_sealed_credential(
                "s1", **self.access("SKAP_SEALED_CREDENTIAL_READ", "s1")), self.bundle[0])


class LcKv03OnlyTheRealGateAttests(unittest.TestCase):
    def test_arbitrary_callables_and_gate_subclasses_are_not_the_gate(self):
        layers = TwoLayers()

        class Lenient(SkapLayer2Gate):
            pass
        for verifier in (lambda *_: {"disposition": "ALLOW"}, Lenient(layers.layer1),
                         Lenient(layers.layer1).verify_access_chain, object(), None):
            self.assertIsNone(binding_module.pinned_layer2_gate(verifier))
        self.assertIs(binding_module.pinned_layer2_gate(layers.gate), layers.gate)
        self.assertIs(binding_module.pinned_layer2_gate(layers.gate.verify_access_chain), layers.gate)


class EndpointKindDeclaration(unittest.TestCase):
    def test_kinds_and_schemas_are_432s_v1(self):
        anchor = pinned()["endpoint_ledger_anchor"]
        schema = json.loads((Path(ep._INTR_PINNED_ROOT) / ep.ENDPOINT_KIND_SCHEMA_PATH).read_text(encoding="utf-8"))
        self.assertEqual(ep.ENDPOINT_KINDS, tuple(schema["$defs"]["endpoint_kind"]["enum"]))  # taken from the schema
        self.assertEqual(ep.ENDPOINT_KINDS, tuple(anchor.ENDPOINT_KINDS))
        self.assertTrue({"PERMANENT", "GATEWAY"} <= set(ep.ENDPOINT_KINDS))
        self.assertEqual((ep.ENDPOINT_KIND_SCHEMA, ep.ENDPOINT_GENESIS_SCHEMA, ep.ENDPOINT_ANCHOR_SCHEMA,
                          ep.EPHEMERAL_NODE_LEDGER_OPENED_SCHEMA, ep.EPHEMERAL_NODE_LEDGER_OPENED_SIGNED_SCHEMA,
                          ep.EPHEMERAL_NODE_LEDGER_OPENED_GENERATION_SCHEMA),
                         (anchor.ENDPOINT_KIND_SCHEMA, anchor.GENESIS_SCHEMA, anchor.ANCHOR_BODY_SCHEMA,
                          anchor.OPENED_ANCHOR_SCHEMA, anchor.SIGNED_OPENED_SCHEMA, anchor.GENERATION_SCHEMA))
        self.assertEqual(ep.ENDPOINT_KIND_SCHEMA, "stegverse.endpoint-kind/v1")
        self.assertFalse([n for n in vars(ep) if "SCHEMA_PENDING" in n])
        self.assertNotIn("ENDPOINT_KIND_SCHEMA_PENDING", Path(ep.__file__).read_text(encoding="utf-8"))
        layers = TwoLayers()
        skap = layers.gate.verify_skap_access_receipt(layers.skap_hash("SKAP_READ", "s"))
        self.assertEqual((skap["endpoint_kind"], skap["layer1_endpoint_kind"], skap["endpoint_kind_schema"]),
                         ("SKAP_VAULT", "KV", "stegverse.endpoint-kind/v1"))


class AdmissionOrder(unittest.TestCase):
    def test_258_and_259_are_admitted_together_on_every_verdict(self):
        from runtime import kv_skap_vault as kv
        self.assertEqual(kv.ADMISSION_ORDER["rule"], "ADMITTED_TOGETHER")
        self.assertEqual(kv.ADMISSION_ORDER["admitted_together"],
                         ["StegVerse-Labs/continuity-vault-kit#258", "StegVerse-Labs/continuity-vault-kit#259"])
        self.assertEqual(kv.evaluate()["admission_order"], kv.ADMISSION_ORDER)


class E0IsScoped(unittest.TestCase):
    def test_production_anchors_hold_no_constants_and_e0_is_labelled(self):
        with production_trust_anchors():
            self.assertEqual(set(ep.TRUST_ANCHORS), {"label", "intr_transport"})
            self.assertEqual(ep.TRUST_ANCHORS["label"], ep.PRODUCTION_TRUST_ANCHORS_LABEL)
            self.assertIsNone(ep.TRUST_ANCHORS["intr_transport"])
            with e0_trust_anchors():
                self.assertEqual(ep.TRUST_ANCHORS["label"], E0_LABEL)
            self.assertEqual(ep.TRUST_ANCHORS["label"], ep.PRODUCTION_TRUST_ANCHORS_LABEL)


def _checkout(git_repo):
    """A plain read of the E0 org repository's committed tree (the runtime itself reads the ref via git archive)."""
    return git_repo


if __name__ == "__main__":
    unittest.main()


# --- KV-SKAP-LEDGER-LOCATION-001: KV's own recorded receipt chains ('kv', 'skap_vault') behind KV's own InTr ---------
# Governing correction: StegVerse-org/.github#167 comment 6372442705 (STEGVERSE_KV, storage endpoint v2 names only,
# no ledger-wide encryption, ENVELOPE v2 governs SKAP's root; genesis is the two-event crossing model, ENVELOPE v2 line 55).

import hashlib  # noqa: E402

from runtime import kv_receipt_ledgers as rl  # noqa: E402
from runtime import kv_storage_provider_adapter as spa  # noqa: E402

#: StegVerse-Labs/TVC#542 @2b364921 config/org_ledger_head_signer.json org_ledger.custody_ledgers.<key>.carries (read-only)
TVC542_CARRIES = {
    "kv": ["stegverse.kv-access-receipt/v1 (L1)"],
    "skap_vault": ["stegverse.skap-access-receipt/v1 (L2)",
                   "stegverse.tvc.skap-custody-reference-issuance/v1 (TVC#537)",
                   "stegverse.tvc.skap-custody-operation-result/v1"],
}
#: #431 contract fixture d97cd4dc (vendored E0_CONTRACT_431): the key shape every designation copies
CONTRACT_431 = json.loads(Path(E0_CONTRACT_431).read_text(encoding="utf-8"))
#: the superseded cvk#263 @f5f971a5 location (org-hosted), kept only as a refusal fixture
SUPERSEDED_ORG_LOCATION = {"repository": "StegVerse-org/.github", "ref": "refs/stegverse/organization-ledger",
                           "namespace": "repository-ledger/StegVerse-org/01_KV_Ledger"}
E0_REQUEST = "E0-TEST-ONLY-NOT-A-KV-REQUEST"  # TEST-ONLY label; never a real KV request id
KV2 = "SITE-CLOUD-KV-4347408852127319cbda574f02e03edb"


def tvc542_ledger_location(location):
    """TVC#542 @2b364921 ledger_location's acceptance rule, restated (a consumer check, not an import). It accepts only
    the org-ledger shape, so it refuses KV's receipt chains until Lane C rebinds it."""
    import re
    if not (isinstance(location, dict) and location.get("repository") == "StegVerse-org/.github"
            and location.get("ref") == "refs/stegverse/organization-ledger"
            and isinstance(location.get("namespace"), str)
            and re.match(r"^repository-ledger/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$", location["namespace"])):
        return None, "NOT_DESIGNATED"
    return {}, "OK"


def _sha_file(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def device_local():
    return spa.default_registry().get("device-local")


@contextlib.contextmanager
def kv_chain_e0(which, genesis, edit=None):
    """TEST-ONLY: one designation pinned at `genesis` whose single store is the documented device-local storage
    endpoint (LOCAL_ROOT, resident-device-local) outside the KV #2 lineage, and a published E0 KV head signer.
    Production files are untouched (scratch copy, digest re-pinned in memory)."""
    spec = rl.RECEIPT_LEDGERS[which]
    contract = json.loads((ROOT / spec["contract_path"]).read_text(encoding="utf-8"))
    contract["repository_ledger_location"]["expected_genesis_receipt_sha256"] = genesis
    ld = contract["ledger_designation"]
    ld["expected_genesis_receipt_sha256"] = genesis
    ld["stores"][0].update(provider_id="device-local", access_adapter="resident-device-local", kv_request_id=E0_REQUEST)
    if edit:
        edit(contract)
    raw = (json.dumps(contract, indent=2) + "\n").encode()
    scratch = Path(tempfile.mkdtemp(prefix="e0-kv-chain-"))
    (scratch / "contract.json").write_bytes(raw)
    saved, saved_signers = dict(spec), rl.load_head_signers
    spec.update(contract_path=str(scratch / "contract.json"), contract_sha256=_sha_file(raw))
    from kv_two_layer_e0 import e0_route_ref
    rl.load_head_signers = lambda: [{**e0_route_ref(), "signs": "KV_RECORDED_RECEIPT_CHAIN_HEAD"}]
    try:
        yield spec
    finally:
        spec.clear()
        spec.update(saved)
        rl.load_head_signers = saved_signers


def _receipt(repository, klass, transition_id, evidence, previous):
    hne = pinned()["healthy_node_evaluator"]
    body = {"schema": "stegverse.repo-transition-receipt/v1", "repository": repository, "transition_id": transition_id,
            "transition_class": klass, "predecessor_state_sha256": hne.sha({"previous": previous}),
            "successor_state_sha256": hne.sha({"transition": transition_id}), "evidence": evidence,
            "authority_effect": "NONE", "observed_at": "2026-10-23T12:00:00Z", "previous_receipt_sha256": previous}
    return {**body, "receipt_sha256": hne.sha(body)}


def e0_kv_root(which, carried=("sha256:" + "ab" * 32,), repository=None):
    """A TEST-ONLY scratch KV root holding this chain as plain recorded receipts at the chain's documented location
    (HEAD.json + receipts/<hex>.json). Returns (root, chain newest first)."""
    spec = rl.RECEIPT_LEDGERS[which]
    repo = repository or spec["repository"]
    chain = [_receipt(repo, rl.GENESIS_CLASS, "REPOSITORY_LEDGER_INITIALIZATION:e0",
                      {"label": E0_LABEL, "repository": repo}, None)]
    for i, h in enumerate(carried):
        chain.append(_receipt(repo, "RECEIPT_APPENDED", f"e0-{i}", {"receipt_sha256": h, "label": E0_LABEL},
                              chain[-1]["receipt_sha256"]))
    root = Path(tempfile.mkdtemp(prefix="e0-kv-root-"))
    where = root / spec["storage_location"]
    (where / "receipts").mkdir(parents=True)
    for r in chain:
        (where / "receipts" / (r["receipt_sha256"][7:] + ".json")).write_text(json.dumps(r), encoding="utf-8")
    (where / "HEAD.json").write_text(json.dumps({"receipt_sha256": chain[-1]["receipt_sha256"]}), encoding="utf-8")
    return root, list(reversed(chain))


def e0_kv_attestation(which, chain, **override):
    from kv_two_layer_e0 import E0_ROUTE_SEED, signer
    d = rl.designation(which)[0]
    body = {**rl.head_attestation_body(d["repository"], d["store_location"], chain[-1]["receipt_sha256"],
                                       chain[0]["receipt_sha256"]), **override}
    message = rl.HEAD_ATTESTATION_SCHEMA.encode() + b"\n" + pinned()["healthy_node_evaluator"].canon(body)
    return {**body, "key_id": E0_ROUTE_KEY_ID, "signature_b64": signer().sign_b64(message, E0_ROUTE_SEED)}


class KvSkapLedgerLocation(unittest.TestCase):
    """KV-SKAP-LEDGER-LOCATION-001: STEGVERSE_KV's two recorded receipt chains (_StegVerse/Receipts,
    _Vault/SKAP/Receipts) on the documented storage endpoint v2 of the KV #2 lineage, never on an Org ledger ref; the
    SKAP chain only via KV's InTr; genesis null until pinned (two-event crossing model)."""

    CHAINS = {"kv": ("_StegVerse/Receipts", "KV"), "skap_vault": ("_Vault/SKAP/Receipts", "SKAP_VAULT")}

    def assertSix(self, out, code, klass=None, disposition="FAIL_CLOSED"):
        self.assertEqual((out["disposition"], out["failure_code"]), (disposition, code), out)
        if klass:
            self.assertEqual(out["failure_class"], klass)
        for field in SIX:
            self.assertTrue(isinstance(out[field], str) and out[field].strip(), field)

    def test_contracts_designate_stegverse_kv_on_the_documented_storage_endpoint(self):
        self.assertEqual(set(rl.RECEIPT_LEDGERS), set(self.CHAINS))
        layouts = json.loads((ROOT / "specs/kv-ai-persistence-layouts.v1.json").read_text())
        skap = json.loads((ROOT / "specs/skap-kv-storage-layout.v2.json").read_text())
        self.assertIn("_StegVerse/Receipts", json.dumps(layouts))
        self.assertIn("_Vault/SKAP/Receipts", json.dumps(skap))
        google = spa.default_registry().get("google-drive").descriptor()
        for which, (location, kind) in self.CHAINS.items():
            spec = rl.RECEIPT_LEDGERS[which]
            raw = (ROOT / spec["contract_path"]).read_bytes()
            self.assertEqual(_sha_file(raw), spec["contract_sha256"])
            contract = json.loads(raw)
            keys = list(CONTRACT_431)
            at = keys.index("repository_ledger_location") + 1
            keys[at:at] = ["ledger_designation", "designation_notes"]
            self.assertEqual(list(contract), keys)
            loc = contract["repository_ledger_location"]
            self.assertEqual(list(loc), list(CONTRACT_431["repository_ledger_location"]))  # #431 key shape
            self.assertEqual((contract["repository"], loc["repository"], loc["ref"], loc["namespace"]),
                             (f"STEGVERSE_KV:{location}", "STEGVERSE_KV", "KV_INTR_ENDPOINT", location))
            self.assertIs(loc["new_ledger_root"], True)
            self.assertIsNone(loc["expected_genesis_receipt_sha256"])
            self.assertIn("SUPPLIED_HB_EPOCH", loc["expected_genesis_note"])
            self.assertIn(KV2, loc["designation_source"])
            self.assertIn("6372442705", loc["designation_source"])
            ld = contract["ledger_designation"]
            self.assertEqual(tuple(ld), rl.DESIGNATION_KEYS)  # LLM-adapter#431 @a2237bc3 field names
            self.assertEqual(len(ld["stores"]), 1)
            store = ld["stores"][0]
            self.assertEqual(tuple(store), rl.STORE_KEYS)
            self.assertEqual(store, {"store_type": "KV_STORAGE_ENDPOINT", "storage_endpoint_schema":
                                     spa.STORAGE_ENDPOINT_SCHEMA, "provider_id": google["provider_id"],
                                     "access_adapter": google["access_adapter"], "kv_class": "STEGVERSE_KV",
                                     "kv_request_id": KV2, "location": location})
            self.assertEqual((ld["endpoint_id"], ld["endpoint_kind"], ld["provider_selection"], ld["head_signer_source"]),
                             (f"STEGVERSE_KV:{location}", kind, "SINGLE_PROVIDER_V1", "KV_LEDGER_HEAD_SIGNER"))
            self.assertEqual(ld["rollback_watermark_source"]["source"], "ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD")
            self.assertTrue(ld["rollback_watermark_source"]["path_ids"][0].endswith(":intr-destination"))
            self.assertIsNone(ld["expected_genesis_receipt_sha256"])
            notes = contract["designation_notes"]
            self.assertEqual(json.loads((ROOT / notes["head_signers_path"]).read_text())["signers"], [])
            self.assertIsNone(rl._org_designation(contract))
            text = json.dumps({k: v for k, v in contract.items() if k != "designation_notes"})
            for withdrawn in ("SVKV", "ECOSYSTEM-OWN-KV-001", "GATE" + "WAY", "gate" + "way", "encrypted blob", "G8",
                              "federal", "self-organizing", "TV/TVC root", "session key"):
                self.assertNotIn(withdrawn, text, (which, withdrawn))
        signers = json.loads((ROOT / rl.HEAD_SIGNERS_REL).read_text())
        self.assertEqual((rl.HEAD_SIGNERS_REL, signers["schema"]), (".stegverse/node-ledger/kv-ledger-head-signers.v1.json",
                         "stegverse.published-public-key-references/v1"))

    def test_no_chain_on_any_org_ledger_ref_and_the_head_digest_name(self):
        """LC-KV-21 (.github#163 comment 6372658597); TVC#542 @4c2504da kv_ledger_head_signer.signs."""
        for which in self.CHAINS:
            contract = json.loads((ROOT / rl.RECEIPT_LEDGERS[which]["contract_path"]).read_text())
            loc, ld = contract["repository_ledger_location"], contract["ledger_designation"]
            placed = json.dumps([loc["repository"], loc["ref"], loc["namespace"], ld["endpoint_id"], ld["stores"]])
            for org in ("organization-ledger", "StegVerse-org/", "repository-ledger/", "refs/"):
                self.assertNotIn(org, placed, (which, org))
            self.assertEqual(contract["designation_notes"]["head_digest_name"], "KV_RECORDED_RECEIPT_CHAIN_HEAD")
            self.assertIn("digest-only", contract["designation_notes"]["org_crossing_receipts"])
        self.assertEqual(rl.HEAD_DIGEST_NAME, "KV_RECORDED_RECEIPT_CHAIN_HEAD")
        from kv_two_layer_e0 import e0_route_ref
        rl.load_head_signers, saved = rl.load_head_signers, rl.load_head_signers
        try:
            rl.HEAD_SIGNERS_PATH, path = Path(tempfile.mkdtemp()) / "s.json", rl.HEAD_SIGNERS_PATH
            for signs, n in (("KV_RECORDED_RECEIPT_CHAIN_HEAD", 1), ("KV_LEDGER_HEAD", 0)):
                rl.HEAD_SIGNERS_PATH.write_text(json.dumps({"schema": rl.HEAD_SIGNERS_SCHEMA,
                                                            "signers": [{**e0_route_ref(), "signs": signs}]}))
                self.assertEqual(len(rl.load_head_signers()), n, signs)
        finally:
            rl.HEAD_SIGNERS_PATH = path

    def test_the_documented_storage_endpoint_is_reused_not_duplicated(self):
        self.assertFalse((ROOT / "runtime/kv_gateway_storage.py").exists())
        self.assertFalse((ROOT / ".stegverse/kv-gateway").exists())
        source = (ROOT / "runtime/kv_receipt_ledgers.py").read_text(encoding="utf-8")
        self.assertIn("from runtime import kv_storage_provider_adapter as spa", source)
        import ast
        classes = [n.name for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ClassDef)]
        self.assertEqual(classes, [])  # no new adapter / storage interface
        for withdrawn in ("SVKV", "GatewayStore", "BlobOpener", "G8", "self-organizing"):
            self.assertFalse(withdrawn in source, withdrawn)

    def test_no_endpoint_is_a_github_organization_member(self):
        """Rigel's rule (Coordination on .github#160): KV reaches the Orgs only through InTr, never as an org member."""
        for which in ("kv", "skap_vault"):
            contract = json.loads((ROOT / rl.RECEIPT_LEDGERS[which]["contract_path"]).read_text())
            self.assertIsNone(rl._org_membership(contract), which)
            loc = contract["repository_ledger_location"]
            self.assertEqual((loc["repository"], loc["ref"]), ("STEGVERSE_KV", "KV_INTR_ENDPOINT"))
            self.assertTrue(all(p.endswith(":intr-destination")
                                for p in contract["ledger_designation"]["rollback_watermark_source"]["path_ids"]), which)
            self.assertIn("ENDPOINT_ORG_MEMBERSHIP_REFUSED", contract["designation_notes"]["org_membership"])

        def org_repository(c):
            c["repository_ledger_location"]["repository"] = "StegVerse-Labs/continuity-vault-kit"

        def org_ref(c):
            c["repository_ledger_location"]["ref"] = "refs/heads/main"

        def team(c):
            c["ledger_designation"]["team_slug"] = "kv-endpoints"

        def app_installation(c):
            c["ledger_designation"]["stores"][0]["installation_id"] = 1

        def membership(c):
            c["org_membership"] = {"org": "StegVerse-org", "role": "member"}

        def top_level(key, value):
            def edit(c):
                c[key] = value
            edit.__name__ = f"top_level_{key}"
            return edit

        # LC-KV-24: a closed key schema, not a deny list
        extra = [top_level("organization", "StegVerse-org"), top_level("github_app_installation_id", 12345),
                 top_level("permissions", {"contents": "write"}), top_level("owner", "StegVerse-org")]

        def note_owner(c):
            c["designation_notes"]["owner"] = "StegVerse-org"

        def store_permissions(c):
            c["ledger_designation"]["stores"][0]["permissions"] = ["read"]

        def watermark_org(c):
            c["ledger_designation"]["rollback_watermark_source"]["organization"] = "StegVerse-org"

        for which in ("kv", "skap_vault"):
            for edit in (org_repository, org_ref, team, app_installation, membership, *extra, note_owner,
                         store_permissions, watermark_org):
                with self.subTest(which=which, edit=edit.__name__), kv_chain_e0(which, None, edit):
                    out = rl.read_receipt_ledger(which)
                    self.assertSix(out, "ENDPOINT_ORG_MEMBERSHIP_REFUSED", "C")
                    self.assertIn("InTr", out["required_evidence_or_repair"])
                    self.assertEqual(out["failed_predicate"], "ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER")

    def test_an_unknown_designation_key_is_refused_by_the_closed_schema(self):
        def unknown_top(c):
            c["retention_days"] = 30

        def unknown_store(c):
            c["ledger_designation"]["stores"][0]["cache_ttl"] = 60

        def unknown_location(c):
            c["repository_ledger_location"]["mirror"] = "_Backup"

        for which in ("kv", "skap_vault"):
            for edit in (unknown_top, unknown_store, unknown_location):
                with self.subTest(which=which, edit=edit.__name__), kv_chain_e0(which, None, edit):
                    out = rl.read_receipt_ledger(which)
                    self.assertSix(out, "KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY", "C")
                    self.assertEqual(out["failed_predicate"], "KV_RECEIPT_CHAIN_DESIGNATION_KEYS_CLOSED")
        for key in ("organization", "github_app_installation_id", "permissions", "owner", "teamSlug"):
            self.assertTrue(rl._membership_like(key), key)
        for key in ("retention_days", "cache_ttl", "mirror"):
            self.assertFalse(rl._membership_like(key), key)

    def test_an_org_git_ref_other_store_or_multi_store_designation_is_refused(self):
        def org_location(c):
            c["repository_ledger_location"].update(SUPERSEDED_ORG_LOCATION)

        def git_ref_store(c):
            c["ledger_designation"]["stores"][0]["store_type"] = "GIT_REF"


        def git_fields(c):
            c["ledger_designation"]["stores"][0]["ref"] = "refs/heads/kv"

        for edit in (org_location, git_ref_store, git_fields):
            with self.subTest(edit=edit.__name__), kv_chain_e0("kv", None, edit):
                self.assertSix(rl.read_receipt_ledger("kv"), "KV_RECEIPT_CHAIN_DESIGNATED_ON_ORG_LEDGER", "C")

        def two(c):
            c["ledger_designation"]["stores"].append(dict(c["ledger_designation"]["stores"][0]))

        def other_store_type(c):
            c["ledger_designation"]["stores"][0]["store_type"] = "ENCRYPTED_" + "BLOB"

        def undocumented_provider(c):
            c["ledger_designation"]["stores"][0]["provider_id"] = "made-up-provider"

        def wrong_adapter(c):
            c["ledger_designation"]["stores"][0]["access_adapter"] = "provider-or-file-provider"

        def wrong_location(c):
            c["ledger_designation"]["stores"][0]["location"] = "_StegVerse/Other"

        with kv_chain_e0("kv", None, two):
            self.assertSix(rl.read_receipt_ledger("kv"), "ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED", "C")
        for edit in (other_store_type, undocumented_provider, wrong_adapter, wrong_location):
            with self.subTest(edit=edit.__name__), kv_chain_e0("kv", None, edit):
                self.assertSix(rl.read_receipt_ledger("kv"), "KV_RECEIPT_CHAIN_STORE_NOT_STORAGE_ENDPOINT_V2", "C")

    def test_production_fails_closed_kv2_pending_then_genesis_and_signer(self):
        out = rl.read_receipt_ledger("kv", spa.default_registry().get("google-drive"), "/nonexistent")
        self.assertSix(out, "KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR", "B")
        self.assertIn(KV2, out["owning_existing_goal"])
        self.assertIn("KV-CONNECTION-REVALIDATION-WORKER-001", out["owning_existing_goal"])
        self.assertEqual(ep.KVInterlockRuntime.receipt_ledger()["failure_code"],
                         "KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR")
        rows = {r["receipt_ledger"]: r for r in rl.receipt_ledger_prerequisites()}
        self.assertEqual([b["failure_code"] for b in rows["kv"]["fail_closed"]],
                         ["KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR", "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED",
                          rl.PIN_MECHANISM_CODE, "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED"])
        self.assertEqual([b["failure_code"] for b in rows["skap_vault"]["fail_closed"]],
                         ["KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR",
                          "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED", rl.PIN_MECHANISM_CODE,
                          "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED"])
        for row in rows.values():
            self.assertEqual(row["disposition"], "FAIL_CLOSED")
            for b in row["fail_closed"]:
                for field in rl.SIX_FIELDS:
                    self.assertTrue(b[field].strip(), field)
        with kv_chain_e0("kv", None):
            root, _ = e0_kv_root("kv")
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), root), "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED", "B")

    def test_skap_genesis_is_the_two_event_crossing_model_and_reads_back_via_kv_intr(self):
        """C-1 withdrawn: ENVELOPE v2 line 55 (d749bb2) is CAPTURE's two-event crossing model; no fence FAIL_CLOSED."""
        self.assertFalse(hasattr(rl, "genesis_fence_unreconciled"))
        self.assertNotIn("SKAP_GENESIS_FENCE_UNRECONCILED", (ROOT / "runtime/kv_receipt_ledgers.py").read_text())
        envelope = (ROOT / "SKAP_PORTABLE_ENVELOPE_V2_MIRROR_HANDOFF.md").read_text(encoding="utf-8").splitlines()
        self.assertIn("exactly-once fence", envelope[54])  # line 55
        for text in (rl.GENESIS_CROSSING, json.loads((ROOT / rl.RECEIPT_LEDGERS["skap_vault"]["contract_path"])
                                                      .read_text())["designation_notes"]["genesis_crossing"]):
            self.assertIn("line 55", text)
            self.assertIn("digest-only", text)
            self.assertIn("SUPPLIED_HB_EPOCH", text)
            self.assertIn("never held on the Org ledger", text)
        layers = TwoLayers()
        prior = layers.kv_hash()
        carried = "sha256:" + "ab" * 32
        root, chain = e0_kv_root("skap_vault", (carried,))
        with kv_chain_e0("skap_vault", chain[-1]["receipt_sha256"]):
            out = layers.gate.receipt_ledger(prior, device_local(), root, e0_kv_attestation("skap_vault", chain),
                                             chain[0]["receipt_sha256"])
            self.assertEqual(out["disposition"], "ALLOW", out)
            self.assertEqual(out["store_location"], "storage-endpoint:device-local/_Vault/SKAP/Receipts")
            self.assertEqual(rl.receipt_on_ledger("skap_vault", carried, _read_result=out)["disposition"], "ALLOW")

    def test_the_skap_chain_is_reached_only_via_kv_intr(self):
        root, chain = e0_kv_root("skap_vault")
        with kv_chain_e0("skap_vault", chain[-1]["receipt_sha256"]):
            good = e0_kv_attestation("skap_vault", chain)
            self.assertSix(rl.read_receipt_ledger("skap_vault", device_local(), root, good),
                           "SKAP_RECEIPT_CHAIN_NOT_VIA_KV_INTR", "A")
            self.assertSix(TwoLayers().gate.receipt_ledger(None, device_local(), root, good),
                           "SKAP_RECEIPT_CHAIN_NOT_VIA_KV_INTR", "A")

    def test_e0_read_back_through_the_device_local_storage_endpoint(self):
        carried = "sha256:" + "ab" * 32
        root, chain = e0_kv_root("kv", (carried,))
        with kv_chain_e0("kv", chain[-1]["receipt_sha256"]):
            good = e0_kv_attestation("kv", chain)
            head = chain[0]["receipt_sha256"]
            out = rl.read_receipt_ledger("kv", device_local(), root, good, head)
            self.assertEqual(out["disposition"], "ALLOW", out)
            self.assertEqual(out["store_location"], "storage-endpoint:device-local/_StegVerse/Receipts")
            self.assertEqual(out["location"], "STEGVERSE_KV#KV_INTR_ENDPOINT:_StegVerse/Receipts")
            self.assertEqual(rl.receipt_on_ledger("kv", carried, device_local(), root, good, head)["disposition"], "ALLOW")
            self.assertEqual(rl.receipt_on_ledger("kv", "sha256:" + "ee" * 32, device_local(), root, good, head)
                             ["failure_code"], "RECEIPT_NOT_ON_DESIGNATED_RECEIPT_CHAIN")
            self.assertEqual(ep.KVInterlockRuntime.receipt_ledger(device_local(), root, good, head)["disposition"],
                             "ALLOW")
            # LC-KV-23: the watermark is required (absent or malformed -> FAIL_CLOSED, class B)
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), root, good),
                           "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING", "B")
            self.assertSix(ep.KVInterlockRuntime.receipt_ledger(device_local(), root, good),
                           "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING", "B")
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), root, good, "77"),
                           "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING", "B")
            # the Org-recorded head watermark: on chain ALLOW; not on chain DENY
            self.assertEqual(rl.read_receipt_ledger("kv", device_local(), root, good, chain[0]["receipt_sha256"])
                             ["disposition"], "ALLOW")
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), root, good, "sha256:" + "77" * 32),
                           "KV_LEDGER_HEAD_ROLLBACK_DETECTED", "C", disposition="DENY")
            # a rolled-back read-back (HEAD moved to genesis) cannot carry the newer recorded head
            old_root, _ = e0_kv_root("kv", (carried,))
            where = old_root / "_StegVerse/Receipts"
            (where / "receipts" / (chain[0]["receipt_sha256"][7:] + ".json")).unlink()
            (where / "HEAD.json").write_text(json.dumps({"receipt_sha256": chain[-1]["receipt_sha256"]}))
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), old_root, e0_kv_attestation("kv", chain[1:]),
                                                  chain[0]["receipt_sha256"]),
                           "KV_LEDGER_HEAD_ROLLBACK_DETECTED", disposition="DENY")
            # signed head
            self.assertEqual(rl.read_receipt_ledger("kv", device_local(), root, None)["failure_code"],
                             "KV_LEDGER_HEAD_NOT_AUTHENTICATED")
            self.assertEqual(rl.read_receipt_ledger("kv", device_local(), root, {**good, "head_receipt_sha256":
                             chain[1]["receipt_sha256"]})["failure_code"], "KV_LEDGER_HEAD_NOT_AUTHENTICATED")
            rl.load_head_signers, saved = (lambda: []), rl.load_head_signers
            try:
                self.assertSix(rl.read_receipt_ledger("kv", device_local(), root, good),
                               "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED", "B")
            finally:
                rl.load_head_signers = saved
            # another storage endpoint than the designated one; an absent read-back
            self.assertSix(rl.read_receipt_ledger("kv", spa.default_registry().get("nas"), root, good),
                           "KV_STORAGE_ENDPOINT_NOT_THE_DESIGNATED_ONE", "C")
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), None, good), "KV_RECEIPT_CHAIN_UNREADABLE", "D")
            empty = Path(tempfile.mkdtemp(prefix="e0-empty-"))
            (empty / "_StegVerse/Receipts").mkdir(parents=True)
            self.assertSix(rl.read_receipt_ledger("kv", device_local(), empty, good), "KV_RECEIPT_CHAIN_UNREADABLE")
        with kv_chain_e0("kv", "sha256:" + "9" * 64):
            self.assertEqual(rl.read_receipt_ledger("kv", device_local(), root, good)["failure_code"],
                             "KV_RECEIPT_CHAIN_GENESIS_MISMATCH")

    def test_an_older_signed_head_is_refused_without_or_with_a_regressing_watermark(self):
        """LC-KV-23: an older head that is properly signed is never accepted on the signature alone."""
        carried = "sha256:" + "ab" * 32
        for which in self.CHAINS:
            root, chain = e0_kv_root(which, (carried,))
            newest = chain[0]["receipt_sha256"]
            loc = rl.RECEIPT_LEDGERS[which]["storage_location"]
            old_root, _ = e0_kv_root(which, (carried,))
            (old_root / loc / "receipts" / (newest[7:] + ".json")).unlink()
            (old_root / loc / "HEAD.json").write_text(json.dumps({"receipt_sha256": chain[-1]["receipt_sha256"]}))
            with self.subTest(which=which), kv_chain_e0(which, chain[-1]["receipt_sha256"]):
                older_signed = e0_kv_attestation(which, chain[1:])  # a valid kv_ledger_head_signer signature
                if which == "skap_vault":
                    layers = TwoLayers()
                    read = lambda r, att, wm: layers.gate.receipt_ledger(layers.kv_hash(), device_local(), r, att, wm)
                else:
                    read = lambda r, att, wm: rl.read_receipt_ledger(which, device_local(), r, att, wm)
                self.assertEqual(read(root, e0_kv_attestation(which, chain), newest)["disposition"], "ALLOW")
                # no watermark: FAIL_CLOSED, never ALLOW on the older signed head
                self.assertSix(read(old_root, older_signed, None), "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING", "B")
                # a watermark the read-back regresses from (the Org recorded the newer head): DENY
                self.assertSix(read(old_root, older_signed, newest), "KV_LEDGER_HEAD_ROLLBACK_DETECTED", "C",
                               disposition="DENY")

    def test_external_storage_records_are_refused(self):
        """The provider's own records (Drive metadata files, revisions) never cross into KV."""
        root, chain = e0_kv_root("kv")
        (root / "_StegVerse/Receipts/desktop.ini").write_text("[.ShellClassInfo]")
        (root / "_StegVerse/Receipts/receipts/1DriveFileId.json").write_text(json.dumps({"kind": "drive#file"}))
        with kv_chain_e0("kv", chain[-1]["receipt_sha256"]):
            out = rl.read_receipt_ledger("kv", device_local(), root, e0_kv_attestation("kv", chain))
        self.assertSix(out, "EXTERNAL_STORAGE_RECORD_REFUSED", "C")

    def test_correspondence_not_storage_an_org_receipt_is_not_kv_input(self):
        root, chain = e0_kv_root("kv", repository="StegVerse-org/LLM-adapter")
        with kv_chain_e0("kv", chain[-1]["receipt_sha256"]):
            out = rl.read_receipt_ledger("kv", device_local(), root, e0_kv_attestation("kv", chain))
        self.assertSix(out, "KV_RECEIPT_CHAIN_FOREIGN_RECORD_REFUSED", "C")
        self.assertIn("CORRESPONDENCE_NOT_STORAGE", out["required_evidence_or_repair"])
        for which in self.CHAINS:
            rule = json.loads((ROOT / rl.RECEIPT_LEDGERS[which]["contract_path"]).read_text())[
                "repository_ledger_location"]["rule"]
            self.assertIn("neither ledger is copied across the boundary", rule)
            self.assertIn("KV_LEDGER_HEAD_ROLLBACK_DETECTED", rule)
            self.assertIn("proposes; it never transitions", rule)

    def test_receipts_carry_kv_own_receipt_chain(self):
        layers = TwoLayers()
        vault = layers.vault()
        bound = layers.bind(vault, custody_key_ref="tvc://skap-custody/e0-ledger", issued_by="TV/TVC",
                            tvc_issuance_receipt_ref="sha256:" + "cd" * 32)
        l1, l2 = layers.layer1_receipts[-1], layers.gate.export_receipts()[-1]
        self.assertEqual(l1["receipt_ledger"], rl.receipt_ledger_binding("kv"))
        self.assertEqual((l1["receipt_ledger"]["storage_location"], l1["receipt_ledger"]["location"]),
                         ("_StegVerse/Receipts", "STEGVERSE_KV#KV_INTR_ENDPOINT:_StegVerse/Receipts"))
        self.assertEqual(l2["receipt_ledger"]["location"], "STEGVERSE_KV#KV_INTR_ENDPOINT:_Vault/SKAP/Receipts")
        self.assertEqual(l2["layer1_receipt_ledger"], l1["receipt_ledger"])
        self.assertEqual(bound["body"]["receipt_ledger"], rl.receipt_ledger_binding("skap_vault"))
        self.assertEqual(l1["receipt_ledger"]["failure_code"], "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED")

    def test_layer2_refuses_a_layer1_receipt_naming_another_chain(self):
        layers = TwoLayers()
        prior = layers.kv_hash()
        import runtime.kv_skap_layer2 as l2
        real = l2.receipt_ledger_binding
        l2.receipt_ledger_binding = lambda which: {**real(which), "location": "elsewhere"} if which == "kv" else real(which)
        try:
            out = layers.gate.admit(kv_skap_transition(principal_ref=layers.principal, operation="SKAP_READ",
                                                       subject_ref="p1", prior_receipt_hash=prior))
        finally:
            l2.receipt_ledger_binding = real
        self.assertEqual(out["disposition"], "FAIL_CLOSED")
        self.assertIn("LAYER1_RECEIPT_LEDGER_NOT_THE_DESIGNATED_KV_LEDGER", json.dumps(out))

    def test_consumer_config_and_the_superseded_org_rule(self):
        config = rl.custody_ledgers_config()
        self.assertEqual(set(config), {"kv", "skap_vault"})
        for which, entry in config.items():
            self.assertEqual(entry["carries"], TVC542_CARRIES[which])
            self.assertEqual(entry["repository_ledger_location"]["repository"], "STEGVERSE_KV")
            self.assertEqual(entry["ledger_designation"]["stores"][0]["store_type"], "KV_STORAGE_ENDPOINT")
            self.assertIs(entry["via_kv_intr_only"], which == "skap_vault")
            # TVC#542 @2b364921's org-shape rule no longer accepts KV's chains: Lane C rebinds
            self.assertEqual(tvc542_ledger_location(entry["repository_ledger_location"])[1], "NOT_DESIGNATED")
        self.assertEqual(tvc542_ledger_location(SUPERSEDED_ORG_LOCATION)[1], "OK")

    def test_a_changed_contract_is_not_designated(self):
        spec = rl.RECEIPT_LEDGERS["skap_vault"]
        saved = spec["contract_sha256"]
        spec["contract_sha256"] = "sha256:" + "0" * 64
        try:
            out = rl.read_receipt_ledger("skap_vault")
            self.assertIsNone(rl.custody_ledgers_config()["skap_vault"]["repository_ledger_location"])
        finally:
            spec["contract_sha256"] = saved
        self.assertEqual(out["failure_code"], "CUSTODY_RECEIPT_CHAIN_NOT_DESIGNATED")
        self.assertEqual(rl.read_receipt_ledger("other")["failure_code"], "RECEIPT_LEDGER_UNKNOWN")

    def test_no_cryptography_import_and_vendored_intr_untouched(self):
        source = (ROOT / "runtime" / "kv_receipt_ledgers.py").read_text(encoding="utf-8")
        self.assertNotIn("import cryptography", source)
        self.assertNotIn("from cryptography", source)
        modules, why = ep.load_pinned_intr()
        self.assertIsNotNone(modules, why)  # the vendored #432 bytes still match their pins

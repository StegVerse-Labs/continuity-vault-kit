"""Negative tests for P1's ladder-conformance DENY on cvk#258 @61104a57 (StegVerse-Labs/.github#3330 @578583be).

Each test closes one bypass P1 named: LC-KV-10 (layer 2 re-checks the evaluator pin), LC-KV-15 (ledger bound by contract
location at an observed head, identity from the installed InTr transport, real transport state; an anchored temporary
node ledger only with NODE_LEDGER_OPENED), LC-KV-07 (gated read_stream / append_extension with provenance) and LC-KV-03
(only the real layer-2 gate may attest the access layers). E0 stand-ins are labelled E0_STANDIN_TEST_ONLY_NOT_EVIDENCE.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from execution.adapter import canonical_sha256  # noqa: E402
from execution.vault_store import KnowledgeVaultExecutionStore, SkapAccessRefused  # noqa: E402
from kv_two_layer_e0 import (  # noqa: E402
    E0_LABEL, E0_TRANSPORT, PINNED_DIGESTS, TwoLayers, e0_health_ledger, e0_node_ledger_opened, e0_scratch_ledger_root,
    e0_temporary_node_ledger, e0_temporary_source, e0_trust_anchors, production_trust_anchors,
)
from kv_two_layer_e0 import enter_e0 as setUpModule, exit_e0 as tearDownModule  # noqa: E402,F401
from runtime import kv_interlock_endpoint as ep  # noqa: E402
from runtime import task_registry_event_sovereign_kv_binding as binding_module  # noqa: E402
from runtime.intr_pinned.healthy_node_evaluator import evaluate as pinned_evaluate  # noqa: E402
from runtime.kv_skap_layer2 import SkapLayer2Gate, kv_skap_transition  # noqa: E402
from test_skap_kv_persistence import SkapKvPersistenceTests  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")
NODE = "device:test:1"


def refused(case, out, cause, klass=None, code="KV_ACCESS_LAYER1_REFUSED"):
    case.assertEqual(out["decision"], "FAIL_CLOSED", out)
    case.assertEqual((out["failure_code"], out["refusal_cause"]), (code, cause), out)
    if klass:
        case.assertEqual(out["failure_class"], klass, out)
    for field in SIX:
        case.assertTrue(out[field], field)
    case.assertIsNone(out["kv_access_receipt"])


class LcKv10Layer2RechecksTheEvaluatorPin(unittest.TestCase):
    def admit(self, layers, kv_hash):
        return layers.gate.admit(kv_skap_transition(principal_ref=layers.principal, operation="SKAP_READ",
                                                    subject_ref="s", prior_receipt_hash=kv_hash))

    def test_injected_evaluator_receipt_is_refused_at_layer_2(self):
        def injected(node_id, **kw):  # same answers as the pin, but not the pinned evaluator
            return pinned_evaluate(node_id, **kw)
        layers = TwoLayers(evaluator=injected)
        out = layers.kv_access()
        self.assertEqual(out["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertNotEqual(out["kv_access_receipt"]["healthy_node_evaluator"], ep.PINNED_HEALTHY_NODE_EVALUATOR_ID)
        self.assertIsNone(layers.gate.verify_kv_access_receipt(out["kv_access_receipt"]["receipt_hash"]))
        answer = self.admit(layers, out["kv_access_receipt"]["receipt_hash"])
        self.assertEqual((answer["disposition"], answer["refusal_cause"]),
                         ("FAIL_CLOSED", "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"))
        for field in SIX:
            self.assertTrue(answer[field], field)

    def test_edited_pin_fields_are_refused(self):
        layers = TwoLayers()
        receipt = layers.kv_access()["kv_access_receipt"]
        for field, value in (("healthy_node_evaluator", "x.y"),
                             ("healthy_node_evaluator_source_sha256", "sha256:" + "0" * 64)):
            self.assertEqual(ep.layer1_receipt_conformance({**receipt, field: value}),
                             "LAYER1_HEALTH_EVALUATOR_NOT_PINNED")
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
                          binding["namespace"]),
                         (ep.LEDGER_SOURCE_ORGANIZATION, "ORG", "StegVerse-org/.github",
                          "refs/stegverse/organization-ledger", "repository-ledger/StegVerse-org/LLM-adapter"))
        self.assertRegex(binding["observed_head"], r"^[0-9a-f]{40}$")
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

    def test_unpinned_or_foreign_genesis_is_refused(self):
        repo = e0_health_ledger(NODE)[0]
        with production_trust_anchors():
            refused(self, TwoLayers(ledger_checkout=repo).kv_access(), "HEALTHY_NODE_LEDGER_GENESIS_NOT_PINNED", "B")
        saved = ep.TRUST_ANCHORS["healthy_node_ledger_genesis_receipt_sha256"]
        ep.TRUST_ANCHORS["healthy_node_ledger_genesis_receipt_sha256"] = "sha256:" + "9" * 64
        try:
            out = TwoLayers(ledger_checkout=repo).kv_access()
        finally:
            ep.TRUST_ANCHORS["healthy_node_ledger_genesis_receipt_sha256"] = saved
        self.assertEqual((out["decision"], out["failure_class"]), ("FAIL_CLOSED", "C"))
        self.assertIn("GENESIS_MISMATCH", out["refusal_cause"])

    def test_transport_not_observed_or_not_installed_is_refused(self):
        class NotInstalled:
            transport_id, state = "e0-not-installed", "NOT_YET_ENABLED"

            def authenticate(self, envelope):
                return {"node_id": NODE, "node_identity_key": "k"}
        saved = ep.TRUST_ANCHORS["intr_transport"]
        for transport in (None, NotInstalled()):
            ep.TRUST_ANCHORS["intr_transport"] = transport
            try:
                out = TwoLayers().kv_access()
            finally:
                ep.TRUST_ANCHORS["intr_transport"] = saved
            refused(self, out, "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", "B")

    def test_caller_asserted_identity_is_refused(self):
        stranger = TwoLayers(node="device:never-enrolled", ledger_checkout=e0_health_ledger(NODE)[0])
        E0_TRANSPORT.enrolled.pop("device:never-enrolled", None)  # the envelope claims it; the transport never saw it
        refused(self, stranger.kv_access(), "REQUESTER_IDENTITY_NOT_TRANSPORT_AUTHENTICATED", "C")
        claimed = TwoLayers().kv_access(verification_state="CLAIMED")
        self.assertEqual((claimed["decision"], claimed["kv_access_receipt"]), ("FAIL_CLOSED", None))
        with production_trust_anchors():
            out = TwoLayers().kv_access()
        self.assertEqual(out["decision"], "FAIL_CLOSED")


class SteeringTwoAnchoredTemporaryLedger(unittest.TestCase):
    def kv(self, source):
        return TwoLayers(ledger_checkout=source).kv_access()

    def temp_refused(self, out, cause):
        refused(self, out, cause, code=ep.TEMP_LEDGER_REFUSAL_CODE)
        self.assertEqual(out["failed_predicate"], ep.TEMP_LEDGER_PREDICATE)
        self.assertIn("KV-SKAP-VAULT-FUNCTIONAL-001", out["owning_existing_goal"])
        self.assertIn("Lane B", out["retry_entrypoint"])
        self.assertIn("dissolution", out["retry_entrypoint"])

    def test_an_anchored_temporary_ledger_binds_as_ephemeral(self):
        out = self.kv(e0_temporary_source(NODE))
        self.assertEqual(out["decision"], "ALLOW_BOUNDED_CONTEXT", out)
        binding = out["kv_access_receipt"]["healthy_node_ledger_binding"]
        self.assertEqual((binding["kind"], binding["endpoint_kind"]), (ep.LEDGER_SOURCE_TEMPORARY, "EPHEMERAL"))
        self.assertEqual(binding["node_ledger_opened"]["transition_class"], "NODE_LEDGER_OPENED")

    def test_no_anchor(self):
        root, _ = e0_temporary_node_ledger(NODE)
        for anchor in (None, {}, "anchor"):
            self.temp_refused(self.kv({"kind": ep.LEDGER_SOURCE_TEMPORARY, "ledger_root": root,
                                       "node_ledger_opened": anchor}),
                              "NODE_LEDGER_OPENED_ANCHOR_MALFORMED" if isinstance(anchor, dict) else "NODE_LEDGER_OPENED_ANCHOR_ABSENT")

    def test_mismatched_node_identity_key(self):
        self.temp_refused(self.kv(e0_temporary_source(NODE, node_identity_key="e0-node-identity-key:other")),
                          "NODE_LEDGER_OPENED_NODE_IDENTITY_KEY_MISMATCH")

    def test_mismatched_genesis(self):
        self.temp_refused(self.kv(e0_temporary_source(NODE, genesis="sha256:" + "7" * 64)),
                          "NODE_LEDGER_OPENED_GENESIS_MISMATCH")

    def test_health_receipts_without_the_pinned_digests(self):
        for digests in (None, {"evaluator_source_sha256": PINNED_DIGESTS["evaluator_source_sha256"]},
                        {**PINNED_DIGESTS, "producer_source_sha256": "sha256:" + "0" * 64}):
            root, _ = e0_temporary_node_ledger(NODE, pinned_digests=digests)
            self.temp_refused(self.kv({"kind": ep.LEDGER_SOURCE_TEMPORARY, "ledger_root": root,
                                       "node_ledger_opened": e0_node_ledger_opened(NODE)}),
                              "TEMPORARY_LEDGER_HEALTH_RECEIPT_NOT_PINNED")

    def test_unissued_edited_or_other_node_anchor(self):
        self.temp_refused(self.kv(e0_temporary_source(NODE, issued=False)), "NODE_LEDGER_OPENED_ISSUER_NOT_VERIFIED")
        self.temp_refused(self.kv(e0_temporary_source(NODE, issuer="CALLER")), "NODE_LEDGER_OPENED_ANCHOR_MALFORMED")
        source = e0_temporary_source(NODE)
        source["node_ledger_opened"]["node_id"] = "device:other"  # digest no longer matches
        self.temp_refused(self.kv(source), "NODE_LEDGER_OPENED_ANCHOR_HASH_MISMATCH")
        with production_trust_anchors():  # no issuer verifier is pinned in production
            out = self.kv(e0_temporary_source(NODE))
        self.assertEqual(out["decision"], "FAIL_CLOSED")


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
    def test_kinds_are_declared_pending_lane_b(self):
        self.assertEqual(set(ep.ENDPOINT_KINDS), {"ORG", "KV", "SKAP_VAULT", "PERMANENT", "EPHEMERAL", "GATEWAY"})
        self.assertIn("PENDING_LANE_B", ep.ENDPOINT_KIND_SCHEMA)
        layers = TwoLayers()
        skap = layers.gate.verify_skap_access_receipt(layers.skap_hash("SKAP_READ", "s"))
        self.assertEqual((skap["endpoint_kind"], skap["layer1_endpoint_kind"]), ("SKAP_VAULT", "KV"))


class E0IsScoped(unittest.TestCase):
    def test_production_anchors_are_empty_and_e0_is_labelled(self):
        with production_trust_anchors():
            self.assertEqual(ep.TRUST_ANCHORS["label"], ep.PRODUCTION_TRUST_ANCHORS_LABEL)
            self.assertIsNone(ep.TRUST_ANCHORS["healthy_node_ledger_genesis_receipt_sha256"])
            self.assertIsNone(ep.TRUST_ANCHORS["intr_transport"])
            self.assertFalse(ep.TRUST_ANCHORS["node_ledger_anchor_issuers"])
            with e0_trust_anchors():
                self.assertEqual(ep.TRUST_ANCHORS["label"], E0_LABEL)
            self.assertEqual(ep.TRUST_ANCHORS["label"], ep.PRODUCTION_TRUST_ANCHORS_LABEL)


if __name__ == "__main__":
    unittest.main()

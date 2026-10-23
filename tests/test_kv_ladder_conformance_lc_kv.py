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
import json
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
    E0_GENESIS, E0_LABEL, E0_TRANSPORT, NEVER_ENROLLED_NODE, NODE, TwoLayers, e0_health_ledger, e0_node_identity_key,
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

    def test_genesis_is_derived_from_the_org_receipt_not_a_constant(self):
        self.assertNotIn("healthy_node_ledger_genesis_receipt_sha256", ep.TRUST_ANCHORS)
        source = e0_health_ledger(NODE)[0]
        # an E0-labelled genesis is refused under the production anchors (it derives, but for other trust anchors)
        with production_trust_anchors():
            ep.TRUST_ANCHORS["intr_transport"] = E0_TRANSPORT
            out = TwoLayers(ledger_checkout=source).kv_access()
        refused(self, out, "HEALTHY_NODE_LEDGER_GENESIS_NOT_DERIVABLE", "C")
        self.assertIn("labelled", out["required_evidence_or_repair"])
        modules = pinned()
        a = modules["endpoint_ledger_anchor"]
        good = modules["healthy_node_evaluator"].read_chain(
            ep.healthy_node_ledger_root(_checkout(source["org_ledger_git_dir"])))[0][-1]
        self.assertIsNone(ep._org_genesis_failure(good))
        for edit in ({"repository": "x/y"}, {"transition_class": "NODE_HEALTH_REPORTED"},
                     {"predecessor_state_sha256": "sha256:" + "9" * 64},
                     {"previous_receipt_sha256": "sha256:" + "9" * 64},
                     {"evidence": {**good["evidence"], "repository": "x/y"}},
                     {"successor_state_sha256": a.sha({"other": True})}):
            self.assertIsNotNone(ep._org_genesis_failure({**good, **edit}), edit)

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

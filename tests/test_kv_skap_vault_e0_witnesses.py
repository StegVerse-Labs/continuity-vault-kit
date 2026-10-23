"""LC-KV-04 (StegVerse-Labs/.github#3330), revised by rev 1: the E0 witnesses of KV-SKAP-VAULT-FUNCTIONAL-001.

One ecosystem-only run, end to end. It uses no model, network, clock or credential. The steps:
  1. Every vault operation enters through both credential layers:
     * layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV), for a node that the E0 stand-in of the pinned
       InTr healthy-node evaluator (LC-KV-13/14) admits;
     * layer 2 is SkapLayer2Gate (INTR_KV_SKAP), fed by that layer-1 receipt.
     The lineage binds a TV/TVC-shaped issuance receipt, then records a write, an exact read and a revoke.
  2. The sealed lineage goes to durable custody below the gates. That is a #259 vault-lineage custody binding on a
     non-device provider. The git-ref adapter is withdrawn, and no provider is an access path.
     validate_vault_lineage_custody_result returns ALLOW only with the layer-1 and layer-2 receipts verified by
     the gate's verify_access_chain.
  3. That receipt, the InTr, TVC and access receipts form the evidence bundle. The finish point reaches ALLOW
     without a code edit and appends its receipt to a scratch organization ledger.

Every producer receipt is a structural stand-in with the producer's exact shape: InTr, TVC, the provider write, and
the healthy-node receipt. Real producer receipts on admitted heads are UNKNOWN_NOT_AUTHENTICALLY_OBSERVED. No test
is skipped.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from runtime import kv_skap_vault as kv  # noqa: E402
from runtime.task_registry_event_sovereign_kv_binding import (  # noqa: E402
    build_vault_lineage_custody_binding,
    build_vault_lineage_record,
    validate_vault_lineage_custody_result,
)
from tests.kv_two_layer_e0 import E0_FINISH_POINT_CLI, TwoLayers  # noqa: E402
from tests.kv_two_layer_e0 import enter_e0 as setUpModule, exit_e0 as tearDownModule  # noqa: E402,F401  (E0 trust anchors, labelled)
from test_kv_skap_vault_finish_point import scratch_ledger, tvc_issuance  # noqa: E402
from test_task_registry_event_sovereign_kv_binding import provider_receipt  # noqa: E402

PRINCIPAL = "principal:test"


def witness_lineage(layers):
    issuance = tvc_issuance(PRINCIPAL)
    vault = layers.vault()
    layers.bind(vault, custody_key_ref=issuance["custody_key_ref"], issued_by="TV/TVC",
                tvc_issuance_receipt_ref=issuance["receipt_sha256"])
    consent = layers.grant(vault, purposes=["WRITE", "READ"], projection_ids=["notes/profile"],
                           observed_at="witness-t0")["receipt_hash"]
    layers.write(vault, projection_id="notes/profile", content={"title": "profile", "languages": ["en"]},
                 consent_receipt_hash=consent, custody_key_ref=issuance["custody_key_ref"])
    layers.read(vault, projection_id="notes/profile", consent_receipt_hash=consent)
    layers.revoke(vault, consent_receipt_hash=consent, observed_at="witness-t1")
    return vault.export_lineage(), issuance


class KvSkapVaultE0Witnesses(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger_git = scratch_ledger(self._tmp.name)
        self.layers = TwoLayers(principal=PRINCIPAL)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def binding(self, exported):
        return build_vault_lineage_custody_binding(
            lineage_record=build_vault_lineage_record(exported_lineage=exported), provider_id="nas",
            instance_id="kvi_vault_witness", kv_set_id="kv-skap-vault", storage_locator="private://kv/vault-lineage")

    def custody_receipt(self, exported):
        binding = self.binding(exported)
        access = exported["receipts"][2]["body"]["access"]  # the write's two layer receipts
        provider = {**provider_receipt(binding["provider_write_request"]),
                    "kv_access_receipt_hash": access["kv_access_receipt_hash"],
                    "skap_access_receipt_hash": access["skap_access_receipt_hash"]}
        return validate_vault_lineage_custody_result(binding=binding, provider_receipt=provider,
                                                     read_back_lineage=json.loads(json.dumps(exported)),
                                                     access_receipt_verifier=self.layers.gate.verify_access_chain)

    def evidence(self):
        exported, issuance = witness_lineage(self.layers)
        custody = self.custody_receipt(exported)
        return {"schema": kv.EVIDENCE_SCHEMA, "lineage": exported,
                "intr_transition_receipts": list(self.layers.intr_receipts),
                "durable_custody_readback_receipt": custody, "tvc_issuance_receipts": [issuance],
                **self.layers.access_evidence()}

    def test_e0_witness_run_reaches_allow_and_a_scratch_ledger_receipt(self) -> None:
        evidence = self.evidence()
        self.assertEqual(evidence["durable_custody_readback_receipt"]["disposition"], "ALLOW")
        verdict = kv.finish_point(evidence, self.ledger_git)
        self.assertEqual(verdict["disposition"], "ALLOW",
                         [(r["predicate"], r.get("failure_code")) for r in verdict["predicates"]])
        self.assertEqual(verdict["runtime_disposition"], "ALLOW", verdict["ledger_append"])
        self.assertEqual(verdict["ledger_append"]["locus"], "SCRATCH_LEDGER")
        self.assertFalse(verdict["ledger_append"]["real_ledger_written"])
        self.assertFalse(verdict["llm_used"] or verdict["network_used"] or verdict["clock_read"])

    def test_the_same_run_through_the_cli(self) -> None:
        path = Path(self._tmp.name) / "evidence.json"
        path.write_text(json.dumps(self.evidence()), encoding="utf-8")
        proc = subprocess.run([*E0_FINISH_POINT_CLI, "finish-point", "--evidence", str(path),
                               "--scratch-ledger-git-dir", self.ledger_git], cwd=ROOT, capture_output=True,
                              text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout[-2000:])

    def test_an_unsigned_ephemeral_opened_record_is_refused_then_the_finish_point_runs(self) -> None:
        """LC-KV-17 (P1 rev 5, class A, E0_TERMINAL_DECIDES_AS_REQUIRED): the vendored evaluate_anchored is #432
        @73316297 (this check unchanged since 1cbad77e), which refuses an EPHEMERAL node whose NODE_LEDGER_OPENED record is unsigned (c2c57505 admitted it)
        with EPHEMERAL_NODE_LEDGER_NOT_ANCHORED; a signed envelope whose key is not published is refused the same way
        (owner TV/TVC). Neither mints a receipt, and the finish point still runs to ALLOW with the PERMANENT node."""
        from runtime import kv_interlock_endpoint as ep
        from tests.kv_two_layer_e0 import NODE, e0_health_ledger
        self.assertEqual(ep.PINNED_ANCHORED_EVALUATOR["commit"], "733162978292fbc7be3a562a4fa9f5bed4ada91e")
        anchor_source = (ROOT / "runtime/intr_pinned/llm_adapter/endpoint_ledger_anchor.py").read_text(encoding="utf-8")
        self.assertNotIn("TEMP_NODE_LEDGER_NOT_ANCHORED", anchor_source)
        six = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
               "owning_existing_goal", "next_attempt")
        for signed, reason, failure_class in ((False, "NODE_LEDGER_OPENED_UNSIGNED", "C"),
                                              (True, "NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED", "B")):
            source = e0_health_ledger(NODE, kind="EPHEMERAL", opened_signed=signed)[0]
            out = TwoLayers(principal=PRINCIPAL, ledger_checkout=source).kv_access()
            self.assertEqual((out["decision"], out["failure_code"], out["failure_class"],
                              out["health_evaluation"]["reason"], out["kv_access_receipt"]),
                             ("FAIL_CLOSED", "EPHEMERAL_NODE_LEDGER_NOT_ANCHORED", failure_class, reason, None), signed)
            for field in six:
                self.assertTrue(isinstance(out[field], str) and out[field].strip(), (signed, field))
        # the PERMANENT node's own ledger and identity proof (the E0 transport holds the latest proof per node)
        self.layers = TwoLayers(principal=PRINCIPAL)
        verdict = kv.finish_point(self.evidence(), self.ledger_git)
        self.assertEqual((verdict["disposition"], verdict["runtime_disposition"]), ("ALLOW", "ALLOW"),
                         [(r["predicate"], r.get("failure_code")) for r in verdict["predicates"]])

    def test_unbound_custody_receipt_is_a_disposition_and_keeps_the_verdict_closed(self) -> None:
        evidence = self.evidence()
        binding = self.binding(evidence["lineage"])
        refused = validate_vault_lineage_custody_result(binding=binding, provider_receipt={}, read_back_lineage={})
        self.assertEqual(refused["disposition"], "FAIL_CLOSED")
        evidence["durable_custody_readback_receipt"] = refused
        verdict = kv.finish_point(evidence, self.ledger_git)
        self.assertEqual(verdict["unmet_predicates"], ["ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED"])
        self.assertEqual(verdict["ledger_append"]["failure_code"], "FINISH_POINT_VERDICT_NOT_ALLOW")

    def test_custody_without_verified_access_layers_is_refused(self) -> None:
        exported, _ = witness_lineage(self.layers)
        binding = self.binding(exported)
        access = exported["receipts"][2]["body"]["access"]
        base = provider_receipt(binding["provider_write_request"])
        other = TwoLayers(principal=PRINCIPAL)
        for receipt, verifier, code in (
                (base, self.layers.gate.verify_access_chain, "KV_ACCESS_LAYER1_REFUSED"),
                ({**base, "kv_access_receipt_hash": access["kv_access_receipt_hash"]},
                 self.layers.gate.verify_access_chain, "SKAP_ACCESS_LAYER2_REFUSED"),
                ({**base, **{k: access[k] for k in ("kv_access_receipt_hash", "skap_access_receipt_hash")}},
                 other.gate.verify_access_chain, "KV_ACCESS_LAYER1_REFUSED"),
                ({**base, "kv_access_receipt_hash": access["kv_access_receipt_hash"],
                  "skap_access_receipt_hash": exported["receipts"][3]["body"]["access"]["skap_access_receipt_hash"]},
                 self.layers.gate.verify_access_chain, "SKAP_ACCESS_LAYER2_REFUSED")):
            out = validate_vault_lineage_custody_result(binding=binding, provider_receipt=receipt,
                                                        read_back_lineage=exported, access_receipt_verifier=verifier)
            self.assertEqual((out["disposition"], out["failure_code"]), ("FAIL_CLOSED", code))


if __name__ == "__main__":
    unittest.main()

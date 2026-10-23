"""LC-KV-04 (StegVerse-Labs/.github#3330): the E0 witnesses of KV-SKAP-VAULT-FUNCTIONAL-001, exercised end to end.

This is one ecosystem-only run. It uses no model, network, clock or credential, and writes only scratch git
directories in a temporary directory. The steps:
  1. a KV/SKAP Vault lineage binds a TV/TVC-shaped custody-key issuance receipt and records a write, an exact
     read and a revoke under InTr-shaped transition refs;
  2. the lineage is appended to ecosystem-only durable custody (refs/stegverse/kv-custody/<principal>,
     continuity-vault-kit#259) and read back by exact hash;
  3. validate_vault_lineage_custody_result returns its ALLOW disposition;
  4. that receipt, the InTr receipts and the TVC receipt form the finish-point evidence bundle;
  5. finish-point reaches ALLOW without a code edit and appends its receipt to a scratch organization ledger.

The InTr and TVC receipts are structural stand-ins with the producers' exact shapes
(stegverse.canonical-state-transition-receipt/v1; stegverse.tvc.skap-custody-reference-issuance/v1, see the
StegVerse-Labs/TVC draft TVC_SKAP_CUSTODY_REFERENCE_ISSUE). Real producer receipts on admitted heads are
UNKNOWN_NOT_AUTHENTICALLY_OBSERVED. Exercising SV_CHANGE_ADMIT on exact heads stays a class B FAIL_CLOSED
until StegVerse-Labs/.github#3313 is admitted. No test is skipped.
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

from runtime import kv_ecosystem_git_ref_custody as custody  # noqa: E402
from runtime import kv_skap_vault as kv  # noqa: E402
from runtime.task_registry_event_sovereign_kv_binding import (  # noqa: E402
    build_vault_lineage_custody_binding,
    build_vault_lineage_record,
    validate_vault_lineage_custody_result,
)
from test_kv_skap_vault_finish_point import intr_receipt, scratch_ledger, tvc_issuance  # noqa: E402

PRINCIPAL = "principal:test"


def witness_lineage():
    issuance = tvc_issuance(PRINCIPAL)
    vault = kv.KVSkapVault(PRINCIPAL)
    vault.bind_custody_key_reference(custody_key_ref=issuance["custody_key_ref"], issued_by="TV/TVC",
                                     tvc_issuance_receipt_ref=issuance["receipt_sha256"])
    consent = vault.grant_consent(purposes=["WRITE", "READ"], projection_ids=["notes/profile"],
                                  observed_at="witness-t0")["receipt_hash"]
    vault.write_projection(projection_id="notes/profile", content={"title": "profile", "languages": ["en"]},
                           consent_receipt_hash=consent, custody_key_ref=issuance["custody_key_ref"],
                           intr_transition_ref="intr:witness-write")
    vault.read_projection(projection_id="notes/profile", consent_receipt_hash=consent)
    vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:witness-revoke",
                         observed_at="witness-t1")
    return vault.export_lineage(), issuance


class KvSkapVaultE0Witnesses(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.custody_git = str(Path(self._tmp.name) / "custody.git")
        subprocess.run(["git", "init", "-q", "--bare", self.custody_git], check=True)
        self.ledger_git = scratch_ledger(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def custody_receipt(self, exported):
        binding = build_vault_lineage_custody_binding(
            lineage_record=build_vault_lineage_record(exported_lineage=exported), provider_id="ecosystem-git-ref",
            instance_id="kvi_vault_witness", kv_set_id="kv-skap-vault",
            storage_locator=custody.custody_ref(PRINCIPAL))
        written = custody.write_lineage(self.custody_git, custody.build_write_manifest(
            binding=binding, exact_lineage=exported, expected_predecessor_commit=None))
        self.assertEqual(written["disposition"], "ALLOW", written)
        back = custody.read_back(self.custody_git, principal_ref=PRINCIPAL, lineage_sha256=binding["lineage_sha256"])
        self.assertEqual(back["disposition"], "ALLOW", back)
        provider = custody.build_provider_receipt(binding=binding, write_result=written,
                                                  interlock_receipt_ref="interlock:witness",
                                                  intr_receipt_ref="intr:witness-write",
                                                  skap_credential_ref=exported["receipts"][0]["body"]["custody_key_ref"])
        return validate_vault_lineage_custody_result(binding=binding, provider_receipt=provider,
                                                     read_back_lineage=back["exact_lineage"])

    def evidence(self):
        exported, issuance = witness_lineage()
        return {"schema": kv.EVIDENCE_SCHEMA, "lineage": exported,
                "intr_transition_receipts": [intr_receipt("witness-write", PRINCIPAL),
                                             intr_receipt("witness-revoke", PRINCIPAL, outcome="APPLIED")],
                "durable_custody_readback_receipt": self.custody_receipt(exported),
                "tvc_issuance_receipts": [issuance]}

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
        proc = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point", "--evidence", str(path),
                               "--scratch-ledger-git-dir", self.ledger_git], cwd=ROOT, capture_output=True,
                              text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout[-2000:])

    def test_unbound_custody_receipt_is_a_disposition_and_keeps_the_verdict_closed(self) -> None:
        evidence = self.evidence()
        exported = evidence["lineage"]
        binding = build_vault_lineage_custody_binding(
            lineage_record=build_vault_lineage_record(exported_lineage=exported), provider_id="ecosystem-git-ref",
            instance_id="kvi_vault_witness", kv_set_id="kv-skap-vault", storage_locator=custody.custody_ref(PRINCIPAL))
        refused = validate_vault_lineage_custody_result(binding=binding, provider_receipt={}, read_back_lineage={})
        self.assertEqual(refused["disposition"], "FAIL_CLOSED")
        evidence["durable_custody_readback_receipt"] = refused
        verdict = kv.finish_point(evidence, self.ledger_git)
        self.assertEqual(verdict["unmet_predicates"], ["ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED"])
        self.assertEqual(verdict["ledger_append"]["failure_code"], "FINISH_POINT_VERDICT_NOT_ALLOW")


if __name__ == "__main__":
    unittest.main()

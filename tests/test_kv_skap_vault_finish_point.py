"""KV-SKAP-VAULT-FUNCTIONAL-001 finish point (StegVerse-Labs/.github#3324). Stdlib unittest; runs at E0.

The acceptance test is ``KvSkapVaultFinishPoint::test_finish_point_verdict``. It passes when the verdict is
ALLOW, or when it is an honest six-field FAIL_CLOSED that names exactly the pieces not yet built. No test
here is skipped.
"""
from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime import kv_skap_vault as kv  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")
REF = kv.CUSTODY_REF_PREFIX + "test-0001"


def vault_with_consent(purposes=("WRITE", "READ"), projection="p"):
    vault = kv.KVSkapVault("principal:test")
    vault.bind_custody_key_reference(custody_key_ref=REF, issued_by="TV/TVC", tvc_issuance_receipt_ref="test:issuance")
    consent = vault.grant_consent(purposes=list(purposes), projection_ids=[projection], observed_at="t0")["receipt_hash"]
    return vault, consent


class KvSkapVaultFinishPoint(unittest.TestCase):
    def test_finish_point_verdict(self) -> None:
        verdict = kv.finish_point()
        self.assertEqual(verdict["task_id"], "KV-SKAP-VAULT-FUNCTIONAL-001")
        self.assertEqual(verdict["scope_digest"],
                         "sha256:d68e239bd1eeabe6558b52928632e9e1df35656e55b3f899755924e66b862ada")
        self.assertEqual([r["predicate"] for r in verdict["predicates"]], list(kv.PREDICATES))
        self.assertEqual(len(kv.PREDICATES), 9)
        unmet = [r for r in verdict["predicates"] if r["disposition"] != "ALLOW"]
        self.assertEqual(verdict["disposition"], "FAIL_CLOSED" if unmet else "ALLOW")
        for row in unmet:
            self.assertEqual(row["disposition"], "FAIL_CLOSED")
            for field in SIX:
                self.assertTrue(row.get(field), (row["predicate"], field))
            self.assertIn(row["failure_class"], ("A", "B", "C", "D"))
            # only declared not-yet-built pieces may be unmet; a class-A local regression fails here
            self.assertIn(row["predicate"], kv.NOT_YET_BUILT, row)
        self.assertEqual(set(verdict["unmet_predicates"]), set(kv.NOT_YET_BUILT))
        self.assertFalse(verdict["llm_used"] or verdict["network_used"] or verdict["clock_read"])
        self.assertEqual(verdict["lowest_supported_mode"], "E0")

    def test_cli_exit_code_matches_disposition(self) -> None:
        proc = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
        verdict = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0 if verdict["disposition"] == "ALLOW" else 2)


class RoundTrip(unittest.TestCase):
    def test_write_read_revoke_round_trip_is_exact(self) -> None:
        vault, consent = vault_with_consent()
        content = {"a": [1, 2, {"b": "ü"}], "n": None}
        vault.write_projection(projection_id="p", content=content, consent_receipt_hash=consent,
                               custody_key_ref=REF, intr_transition_ref="intr:w")
        read, receipt = vault.read_projection(projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(read, content)
        self.assertEqual(receipt["body"]["content_sha256"], kv.sha256_uri(content))
        read["a"].append(3)  # the caller's copy never aliases the vault
        self.assertEqual(vault.read_projection(projection_id="p", consent_receipt_hash=consent)[0], content)
        vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:r", observed_at="t1")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.read_projection(projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_REVOKED")
        for field in SIX:
            self.assertTrue(ctx.exception.fields[field])

    def test_mutations_require_an_intr_transition_reference(self) -> None:
        vault, consent = vault_with_consent()
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.write_projection(projection_id="p", content={}, consent_receipt_hash=consent,
                                   custody_key_ref=REF, intr_transition_ref="")
        self.assertEqual(ctx.exception.fields["failure_code"], "INTR_TRANSITION_REF_MISSING")
        with self.assertRaises(kv.VaultRefusal):
            vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="none", observed_at="t")


class Consent(unittest.TestCase):
    def test_write_and_read_require_a_covering_consent(self) -> None:
        vault, consent = vault_with_consent(purposes=("WRITE",))
        vault.write_projection(projection_id="p", content={"x": 1}, consent_receipt_hash=consent,
                               custody_key_ref=REF, intr_transition_ref="intr:w")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.read_projection(projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_SCOPE_DOES_NOT_COVER_OPERATION")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.write_projection(projection_id="other", content={}, consent_receipt_hash=consent,
                                   custody_key_ref=REF, intr_transition_ref="intr:w")
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_SCOPE_DOES_NOT_COVER_OPERATION")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.read_projection(projection_id="p", consent_receipt_hash="sha256:unknown")
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_RECEIPT_NOT_FOUND")

    def test_revocation_is_receipted_and_not_repeatable(self) -> None:
        vault, consent = vault_with_consent()
        receipt = vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:r", observed_at="t")
        self.assertEqual(receipt["kind"], "CONSENT_REVOKED")
        self.assertEqual(receipt["body"]["consent_receipt_hash"], consent)
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:r2", observed_at="t")
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_ALREADY_REVOKED")


class Custody(unittest.TestCase):
    def test_only_tv_tvc_custody_key_references_are_held(self) -> None:
        vault = kv.KVSkapVault("principal:test")
        for issued_by in ("KV", "SKAP Vault", "user", ""):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                vault.bind_custody_key_reference(custody_key_ref=REF, issued_by=issued_by, tvc_issuance_receipt_ref="r")
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_WRITER_NOT_TV_TVC")
        for ref in ("raw-bytes", kv.CUSTODY_REF_PREFIX, "-----BEGIN PRIVATE KEY-----"):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                vault.bind_custody_key_reference(custody_key_ref=ref, issued_by="TV/TVC", tvc_issuance_receipt_ref="r")
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_KEY_REFERENCE_INVALID")
        self.assertEqual(vault.lineage, [])

    def test_key_or_credential_material_never_enters_kv(self) -> None:
        vault, consent = vault_with_consent()
        for content in ({"private_key": "x"}, {"nested": {"password": "x"}}, {"skap_ciphertext": "x"}):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                vault.write_projection(projection_id="p", content=content, consent_receipt_hash=consent,
                                       custody_key_ref=REF, intr_transition_ref="intr:w")
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED")

    def test_write_requires_a_bound_custody_reference(self) -> None:
        vault, consent = vault_with_consent()
        with self.assertRaises(kv.VaultRefusal) as ctx:
            vault.write_projection(projection_id="p", content={}, consent_receipt_hash=consent,
                                   custody_key_ref=kv.CUSTODY_REF_PREFIX + "unbound", intr_transition_ref="intr:w")
        self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_KEY_REFERENCE_NOT_BOUND")


class LineageAndContinuity(unittest.TestCase):
    def _vault(self):
        vault, consent = vault_with_consent()
        vault.write_projection(projection_id="p", content={"v": 1}, consent_receipt_hash=consent,
                               custody_key_ref=REF, intr_transition_ref="intr:w")
        vault.read_projection(projection_id="p", consent_receipt_hash=consent)
        vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:r", observed_at="t")
        return vault, consent

    def test_lineage_is_one_continuous_hash_chain(self) -> None:
        vault, _ = self._vault()
        self.assertEqual([r["kind"] for r in vault.lineage],
                         ["CUSTODY_KEY_REFERENCE_BOUND", "CONSENT_GRANTED", "KV_PROJECTION_WRITTEN",
                          "KV_PROJECTION_READ", "CONSENT_REVOKED"])
        self.assertIsNone(vault.lineage[0]["previous_receipt_hash"])
        for prev, cur in zip(vault.lineage, vault.lineage[1:]):
            self.assertEqual(cur["previous_receipt_hash"], prev["receipt_hash"])
        kv.verify_lineage(vault.export_lineage())

    def test_tampering_anywhere_breaks_the_lineage(self) -> None:
        vault, _ = self._vault()
        exported = vault.export_lineage()
        for mutate in (lambda e: e["receipts"][2]["body"]["content"].update(v=2),
                       lambda e: e["receipts"].pop(1),
                       lambda e: e.update(head="sha256:other"),
                       lambda e: e["receipts"][3].update(principal_ref="principal:other")):
            copy_ = copy.deepcopy(exported)
            mutate(copy_)
            with self.assertRaises(kv.VaultRefusal) as ctx:
                kv.KVSkapVault.reconstruct(copy_)
            self.assertEqual(ctx.exception.fields["failure_code"], "KV_RECEIPT_LINEAGE_BROKEN")

    def test_any_device_reconstructs_exactly_from_the_lineage_alone(self) -> None:
        vault, consent = self._vault()
        wire = json.dumps(vault.export_lineage())  # the only thing another device receives
        fresh = kv.KVSkapVault.reconstruct(json.loads(wire))
        self.assertEqual(fresh.head, vault.head)
        self.assertEqual(fresh.export_lineage(), vault.export_lineage())
        with self.assertRaises(kv.VaultRefusal) as ctx:  # revocation survives the move
            fresh.read_projection(projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_REVOKED")


class AuthorityAndLadder(unittest.TestCase):
    def test_no_authority_is_duplicated(self) -> None:
        model = kv.AUTHORITY_MODEL
        self.assertEqual(model["credential_authority"], "TV/TVC")
        self.assertEqual(model["skap_ciphertext_custody_writer"], "TV/TVC")
        self.assertEqual(model["transition_authority"], "Interlock/InTr")
        self.assertEqual(model["claim_and_fence_authority"], "WorkerCoordinator")
        for key, value in model.items():
            if key.startswith(("mints_", "holds_")):
                self.assertIs(value, False, key)

    def test_e0_stdlib_only_no_model_network_or_clock(self) -> None:
        tree = ast.parse((ROOT / "runtime" / "kv_skap_vault.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertLessEqual(imported, {"__future__", "argparse", "copy", "hashlib", "json", "sys", "typing", "runtime"})
        source = (ROOT / "runtime" / "kv_skap_vault.py").read_text(encoding="utf-8")
        for forbidden in ("datetime.now", "time.time", "urllib", "socket", "requests", "openai", "anthropic"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

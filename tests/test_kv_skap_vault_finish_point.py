"""KV-SKAP-VAULT-FUNCTIONAL-001 finish point (StegVerse-Labs/.github#3324). Stdlib unittest; runs at E0.

The acceptance test is ``KvSkapVaultFinishPoint::test_finish_point_verdict``. It passes when the verdict is
ALLOW, or when it is an honest six-field FAIL_CLOSED that names exactly the predicates whose evidence is
absent. ``EvidenceDrivenVerdict`` reaches ALLOW from an evidence bundle without any code edit (LC-KV-01).
``OrganizationLedgerReceipt`` covers the ledger append (LC-KV-06), in scratch only. No test here is skipped.
"""
from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import tempfile
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
            # only evidence-bound predicates may be unmet without evidence; a class-A local regression fails here
            self.assertIn(row["predicate"], kv.EVIDENCE_BOUND, row)
            self.assertEqual(row["failure_code"], kv.EVIDENCE_BOUND[row["predicate"]][0])
        self.assertEqual(set(verdict["unmet_predicates"]), set(kv.EVIDENCE_BOUND))
        self.assertFalse(hasattr(kv, "NOT_YET_BUILT"))  # no constant decides a verdict
        self.assertEqual(verdict["ledger_append"]["failure_code"], "FINISH_POINT_VERDICT_NOT_ALLOW")
        for field in SIX:
            self.assertTrue(verdict["ledger_append"][field], field)
        self.assertFalse(verdict["llm_used"] or verdict["network_used"] or verdict["clock_read"])
        self.assertEqual(verdict["lowest_supported_mode"], "E0")

    def test_cli_exit_code_matches_disposition(self) -> None:
        proc = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
        verdict = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0 if verdict["runtime_disposition"] == "ALLOW" else 2)

    def test_cli_unreadable_evidence_fails_closed(self) -> None:
        proc = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point", "--evidence",
                               "/nonexistent/evidence.json"], cwd=ROOT, capture_output=True, text=True, check=False)
        verdict = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({r.get("failure_code") for r in verdict["predicates"] if r["disposition"] != "ALLOW"},
                         {"KV_FINISH_POINT_EVIDENCE_INVALID"})


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

    def test_durable_custody_is_consumed_from_the_sovereign_kv_goal_not_reimplemented(self) -> None:
        verdict = kv.finish_point()
        row = next(r for r in verdict["predicates"]
                   if r["predicate"] == "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED")
        self.assertEqual(row["failure_code"], "KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND")
        self.assertEqual(row["owning_existing_goal"], "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001")
        self.assertEqual(row["failure_class"], "B")
        self.assertEqual(row["dependency_relation"], "CONSUMES")
        self.assertNotIn("#163", row["required_evidence_or_repair"])
        source = (ROOT / "runtime" / "kv_skap_vault.py").read_text(encoding="utf-8")
        for owned in ("task_registry_event_sovereign_kv_binding", "kv_storage_provider_adapter"):
            self.assertNotIn(owned, source)  # consumed, never imported or re-implemented here

    def test_e0_stdlib_only_no_model_network_or_clock(self) -> None:
        tree = ast.parse((ROOT / "runtime" / "kv_skap_vault.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertLessEqual(imported, {"__future__", "argparse", "copy", "hashlib", "json", "os", "subprocess", "sys",
                                        "typing", "runtime"})
        source = (ROOT / "runtime" / "kv_skap_vault.py").read_text(encoding="utf-8")
        for forbidden in ("datetime.now", "time.time", "urllib", "socket", "requests", "openai", "anthropic"):
            self.assertNotIn(forbidden, source)


# --- evidence bundle builders (structural stand-ins for InTr, TVC and sovereign-KV custody receipts; the
#     cross-module E0 witness run is tests/test_kv_skap_vault_e0_witnesses.py)
def tvc_issuance(principal="principal:test", sequence=0):
    manifest = {"schema": "stegverse.tvc.skap-custody-reference-issuance-manifest/v1",
                "transition": "TVC_SKAP_CUSTODY_REFERENCE_ISSUE", "principal_ref": principal,
                "kv_task_id": kv.TASK_ID, "custody_purpose": "SKAP_VAULT_CIPHERTEXT_CUSTODY",
                "issuance_sequence": sequence, "requested_by": "kv-skap-vault", "authority_effect": "NONE"}
    digest = kv.sha256_uri(manifest)
    body = {"schema": kv.TVC_ISSUANCE_SCHEMA, "transition": "TVC_SKAP_CUSTODY_REFERENCE_ISSUE",
            "disposition": "ALLOW", "issuer": "TV/TVC", "manifest_sha256": digest, "principal_ref": principal,
            "kv_task_id": kv.TASK_ID, "custody_purpose": "SKAP_VAULT_CIPHERTEXT_CUSTODY",
            "issuance_sequence": sequence, "custody_key_ref": kv.CUSTODY_REF_PREFIX + digest[7:39],
            "key_material_location": "TVC_ONLY", "key_material_present": False,
            "credential_material_present": False, "live_key_slot_binding": "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED",
            "authority_effect": "NONE"}
    return {**body, "receipt_sha256": kv.sha256_uri(body)}


def intr_receipt(transition_id, principal="principal:test", outcome="ADMITTED"):
    content = {"transition_id": transition_id, "admitted_by": "Interlock/InTr"}
    return {"schema": kv.INTR_RECEIPT_SCHEMA, "transition_id": transition_id, "transition_sequence": 1,
            "subject_or_correlation_id": principal, "transition_outcome": outcome, "prior_state_ref_or_hash": None,
            "required_evidence_manifest": [{
                "evidence_id": "intr_admission", "evidence_type": "INTR_TRANSITION_ADMISSION",
                "origin_transition_id": transition_id, "encoding": "canonical-json", "content": content,
                "sha256": __import__("hashlib").sha256(kv.canonical_json(content).encode()).hexdigest()}]}


def custody_readback(lineage, provider="ecosystem-git-ref"):
    digest = kv.sha256_uri(lineage)
    return {"schema": kv.CUSTODY_READBACK_SCHEMA, "record_type": "KV_SKAP_VAULT_LINEAGE", "disposition": "ALLOW",
            "task_id": kv.TASK_ID, "principal_ref": lineage["principal_ref"], "lineage_sha256": digest,
            "read_back_lineage_sha256": digest, "head_receipt_hash": lineage["head"],
            "receipt_count": len(lineage["receipts"]),
            "provider_adapter_ref": f"continuity-vault-kit:runtime/kv_storage_provider_adapter.py#{provider}",
            "exact_hash_readback_verified": True, "authority_effect": "NONE"}


def evidence_bundle():
    issuance = tvc_issuance()
    vault = kv.KVSkapVault("principal:test")
    vault.bind_custody_key_reference(custody_key_ref=issuance["custody_key_ref"], issued_by="TV/TVC",
                                     tvc_issuance_receipt_ref=issuance["receipt_sha256"])
    consent = vault.grant_consent(purposes=["WRITE", "READ"], projection_ids=["p"], observed_at="t0")["receipt_hash"]
    vault.write_projection(projection_id="p", content={"v": 1}, consent_receipt_hash=consent,
                           custody_key_ref=issuance["custody_key_ref"], intr_transition_ref="intr:w1")
    vault.read_projection(projection_id="p", consent_receipt_hash=consent)
    vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:r1", observed_at="t1")
    lineage = vault.export_lineage()
    return {"schema": kv.EVIDENCE_SCHEMA, "lineage": lineage,
            "intr_transition_receipts": [intr_receipt("w1"), intr_receipt("r1", outcome="APPLIED")],
            "durable_custody_readback_receipt": custody_readback(lineage), "tvc_issuance_receipts": [issuance]}


def failure_codes(verdict):
    return {r["predicate"]: r["failure_code"] for r in verdict["predicates"] if r["disposition"] != "ALLOW"}


class EvidenceDrivenVerdict(unittest.TestCase):
    def test_evidence_reaches_allow_without_a_code_edit(self) -> None:
        verdict = kv.evaluate(evidence_bundle())
        self.assertEqual(verdict["disposition"], "ALLOW", failure_codes(verdict))
        self.assertEqual(verdict["unmet_predicates"], [])
        for row in verdict["predicates"]:
            if row["predicate"] in kv.EVIDENCE_BOUND:
                self.assertEqual(row["locus"], "LOCAL_EXERCISE+EVIDENCE")

    def test_each_evidence_gap_is_a_six_field_fail_closed(self) -> None:
        RT, AD, TV = ("KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                      "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED",
                      "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER")

        def drop(key):
            return lambda e: e.pop(key)

        def intr_outcome(e):
            e["intr_transition_receipts"][0]["transition_outcome"] = "DENIED"

        def intr_missing(e):
            e["intr_transition_receipts"].pop(0)

        def intr_manifest(e):
            e["intr_transition_receipts"][0]["required_evidence_manifest"][0]["content"]["x"] = 1

        def device_local(e):
            e["durable_custody_readback_receipt"] = custody_readback(e["lineage"], "device-local")

        def other_lineage(e):
            e["durable_custody_readback_receipt"]["lineage_sha256"] = "sha256:" + "0" * 64

        def not_verified(e):
            e["durable_custody_readback_receipt"]["exact_hash_readback_verified"] = False

        def tvc_edited(e):
            e["tvc_issuance_receipts"][0]["issuer"] = "KV"

        def tvc_other(e):
            e["tvc_issuance_receipts"] = [tvc_issuance(sequence=7)]

        cases = [(drop("intr_transition_receipts"), RT, "INTR_TRANSITION_RECEIPTS_NOT_OBSERVED"),
                 (intr_missing, RT, "INTR_TRANSITION_RECEIPT_NOT_BOUND"),
                 (intr_outcome, RT, "INTR_TRANSITION_RECEIPT_INVALID"),
                 (intr_manifest, RT, "INTR_TRANSITION_RECEIPT_INVALID"),
                 (drop("durable_custody_readback_receipt"), AD, "KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND"),
                 (device_local, AD, "KV_DURABLE_CUSTODY_IS_DEVICE_LOCAL"),
                 (other_lineage, AD, "KV_DURABLE_CUSTODY_READBACK_NOT_THIS_LINEAGE"),
                 (not_verified, AD, "KV_DURABLE_CUSTODY_READBACK_NOT_ALLOW"),
                 (drop("tvc_issuance_receipts"), TV, "TVC_CUSTODY_KEY_ISSUANCE_NOT_OBSERVED"),
                 (tvc_edited, TV, "TVC_CUSTODY_KEY_ISSUANCE_RECEIPT_INVALID"),
                 (tvc_other, TV, "TVC_CUSTODY_KEY_ISSUANCE_NOT_BOUND")]
        for mutate, predicate, code in cases:
            evidence = evidence_bundle()
            mutate(evidence)
            verdict = kv.evaluate(evidence)
            self.assertEqual(failure_codes(verdict), {predicate: code}, code)
            row = next(r for r in verdict["predicates"] if r["predicate"] == predicate)
            for field in SIX:
                self.assertTrue(row[field], (code, field))

    def test_a_tampered_or_malformed_bundle_never_raises(self) -> None:
        evidence = evidence_bundle()
        evidence["lineage"]["receipts"][2]["body"]["content"]["v"] = 2
        self.assertEqual(set(failure_codes(kv.evaluate(evidence)).values()), {"KV_RECEIPT_LINEAGE_BROKEN"})
        for bad in ({"schema": kv.EVIDENCE_SCHEMA, "lineage": "x", "intr_transition_receipts": [1],
                     "durable_custody_readback_receipt": {"a": 1}, "tvc_issuance_receipts": [None]},
                    {"schema": kv.EVIDENCE_SCHEMA, "lineage": {**evidence_bundle()["lineage"], "receipts": [{}]},
                     "intr_transition_receipts": [1], "durable_custody_readback_receipt": {"a": 1},
                     "tvc_issuance_receipts": [None]},
                    "not a dict", ["list"], {"schema": "other"}):
            verdict = kv.finish_point(bad)
            self.assertEqual(verdict["disposition"], "FAIL_CLOSED")
            self.assertEqual(set(verdict["unmet_predicates"]), set(kv.EVIDENCE_BOUND))

    def test_an_evidence_lineage_without_revocation_is_not_a_round_trip(self) -> None:
        evidence = evidence_bundle()
        vault = kv.KVSkapVault.reconstruct(evidence["lineage"])
        vault.lineage.pop()  # drop the revocation: no longer a write-read-revoke round trip
        lineage = vault.export_lineage()
        evidence["lineage"] = lineage
        evidence["durable_custody_readback_receipt"] = custody_readback(lineage)
        self.assertEqual(set(failure_codes(kv.evaluate(evidence)).values()),
                         {"KV_EVIDENCE_LINEAGE_NOT_A_WRITE_READ_REVOKE_ROUNDTRIP"})


def scratch_ledger(tmp, genesis=True, remote=False):
    git_dir = str(Path(tmp) / "ledger.git")
    env = {**kv._GIT_ENV}
    subprocess.run(["git", "init", "-q", "--bare", git_dir], check=True, env=env)
    if genesis:
        tree = subprocess.run(["git", "--git-dir", git_dir, "mktree"], input="", capture_output=True, text=True,
                              check=True, env=env).stdout.strip()
        commit = subprocess.run(["git", "--git-dir", git_dir, "commit-tree", tree, "-m", "scratch genesis"],
                                capture_output=True, text=True, check=True, env=env).stdout.strip()
        subprocess.run(["git", "--git-dir", git_dir, "update-ref", kv.ORGANIZATION_LEDGER_REF, commit],
                       check=True, env=env)
    if remote:
        subprocess.run(["git", "--git-dir", git_dir, "remote", "add", "origin", "https://example.invalid/x.git"],
                       check=True, env=env)
    return git_dir


class OrganizationLedgerReceipt(unittest.TestCase):
    def test_receipt_is_a_canonical_state_transition_receipt(self) -> None:
        verdict = kv.evaluate(evidence_bundle())
        receipt = kv.organization_ledger_receipt(verdict)
        self.assertEqual(receipt["schema"], "stegverse.canonical-state-transition-receipt/v1")
        self.assertEqual(receipt["transition_outcome"], "ALLOW")
        self.assertEqual(receipt["prior_state_ref_or_hash"], verdict["evidence_lineage_head"])
        entry = receipt["required_evidence_manifest"][0]
        self.assertEqual(entry["origin_transition_id"], receipt["transition_id"])
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(receipt, kv.organization_ledger_receipt(kv.evaluate(evidence_bundle())))  # deterministic

    def test_without_a_ledger_the_append_fails_closed_pending_genesis(self) -> None:
        verdict = kv.finish_point(evidence_bundle())
        self.assertEqual(verdict["disposition"], "ALLOW")
        self.assertEqual(verdict["runtime_disposition"], "FAIL_CLOSED")
        append = verdict["ledger_append"]
        self.assertEqual(append["failure_code"], "ORGANIZATION_LEDGER_GENESIS_NOT_OBSERVED")
        self.assertEqual(append["failure_class"], "B")
        for field in SIX:
            self.assertTrue(append[field], field)
        self.assertFalse(append["real_ledger_written"])

    def test_scratch_ledger_genesis_absent_is_never_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = scratch_ledger(tmp, genesis=False)
            append = kv.finish_point(evidence_bundle(), git_dir)["ledger_append"]
            self.assertEqual(append["failure_code"], "ORGANIZATION_LEDGER_GENESIS_ABSENT")
            probe = subprocess.run(["git", "--git-dir", git_dir, "rev-parse", "--verify", "--quiet",
                                    kv.ORGANIZATION_LEDGER_REF], capture_output=True, check=False)
            self.assertNotEqual(probe.returncode, 0)

    def test_scratch_ledger_append_and_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = scratch_ledger(tmp)
            verdict = kv.finish_point(evidence_bundle(), git_dir)
            self.assertEqual(verdict["runtime_disposition"], "ALLOW", verdict["ledger_append"])
            append = verdict["ledger_append"]
            self.assertEqual(append["locus"], "SCRATCH_LEDGER")
            tip = subprocess.run(["git", "--git-dir", git_dir, "rev-parse", kv.ORGANIZATION_LEDGER_REF],
                                 capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(tip, append["appended_commit"])
            parent = subprocess.run(["git", "--git-dir", git_dir, "rev-parse", tip + "^"], capture_output=True,
                                    text=True, check=True).stdout.strip()
            self.assertEqual(parent, append["predecessor_commit"])
            name = append["receipt_transition_id"].replace(":", "_") + ".json"
            stored = subprocess.run(["git", "--git-dir", git_dir, "show", f"{tip}:{name}"], capture_output=True,
                                    text=True, check=True).stdout
            self.assertEqual(kv.sha256_uri(json.loads(stored)), append["receipt_sha256"])
            cli = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point", "--evidence",
                                  str(Path(tmp) / "e.json"), "--scratch-ledger-git-dir", git_dir], cwd=ROOT,
                                 capture_output=True, text=True, check=False)
            self.assertEqual(cli.returncode, 2)  # missing evidence file fails closed, never raises
        with tempfile.TemporaryDirectory() as tmp:
            append = kv.finish_point(evidence_bundle(), scratch_ledger(tmp, remote=True))["ledger_append"]
            self.assertEqual(append["failure_code"], "LEDGER_TARGET_NOT_SCRATCH")
            append = kv.finish_point(evidence_bundle(), str(Path(tmp) / "absent"))["ledger_append"]
            self.assertEqual(append["failure_code"], "SCRATCH_LEDGER_NOT_A_GIT_DIR")

    def test_cli_round_trip_reaches_runtime_allow_on_a_scratch_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            path.write_text(json.dumps(evidence_bundle()), encoding="utf-8")
            cli = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point", "--evidence",
                                  str(path), "--scratch-ledger-git-dir", scratch_ledger(tmp)], cwd=ROOT,
                                 capture_output=True, text=True, check=False)
            self.assertEqual(cli.returncode, 0, cli.stdout[-2000:])
            self.assertEqual(json.loads(cli.stdout)["ledger_append"]["disposition"], "ALLOW")


if __name__ == "__main__":
    unittest.main()

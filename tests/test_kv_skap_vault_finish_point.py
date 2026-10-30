"""KV-SKAP-VAULT-FUNCTIONAL-001 finish point (StegVerse-Labs/.github#3324). Stdlib unittest; runs at E0.

The acceptance test is ``KvSkapVaultFinishPoint::test_finish_point_verdict``. It passes when the verdict is
ALLOW, or when it is an honest six-field FAIL_CLOSED that names exactly the predicates whose evidence is
absent. ``EvidenceDrivenVerdict`` refuses reference-only issuance (LC-KV-01); authenticated issuance and
consumer verifier integration are required before evidence can reach ALLOW.
``OrganizationLedgerReceipt`` covers the ledger append (LC-KV-06), in scratch only. No test here is skipped.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Consumed-source pin (CONSUMES_DEPENDENCY ruling, StegVerse-Labs/.github#3327 c6392179411): the finish point consumes
#: runtime/kv_storage_provider_adapter.py, owned by TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001, through
#: runtime/kv_receipt_ledgers.py. It is pinned to the continuity-vault-kit commit below and its sha256, and verified
#: here before anything imports it. Any edit to the pinned file is routed to its owner task; it is never silently used.
CONSUMED_SOURCE_PIN = {
    "repository": "StegVerse-Labs/continuity-vault-kit",
    "commit": "859f1cf7f65f87b35e65fd8a9aa58e2933a12c01",
    "owner_task_id": "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001",
    "files": {
        "runtime/kv_storage_provider_adapter.py": "d6ab2d2395e045d703787917388cf9656261424e1f1ae78cfc36c4b41b08e1ee",
    },
}


def _consumed_pin_divergence() -> list[str]:
    out = []
    for rel, digest in CONSUMED_SOURCE_PIN["files"].items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != digest:
            out.append(f"{rel}: sha256 {actual} != pin {digest} @{CONSUMED_SOURCE_PIN['commit']}")
    return out


_PIN_DIVERGENCE = _consumed_pin_divergence()
if _PIN_DIVERGENCE:  # verified before use: refuse to import the consumed source at all
    raise RuntimeError("FAIL_CLOSED CONSUMED_SOURCE_PIN_DIVERGES (route the edit to "
                       f"{CONSUMED_SOURCE_PIN['owner_task_id']}): " + "; ".join(_PIN_DIVERGENCE))

from runtime import kv_skap_vault as kv  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
from tests.kv_two_layer_e0 import TwoLayers, intr_receipt  # noqa: E402,F401  (package path: in the pinned closure)
from tests.kv_two_layer_e0 import E0_FINISH_POINT_CLI  # noqa: E402
from tests.kv_two_layer_e0 import enter_e0 as setUpModule, exit_e0 as tearDownModule  # noqa: E402,F401  (E0 trust anchors, labelled)

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")
REF = kv.CUSTODY_REF_PREFIX + "test-0001"


TVC_REF = kv.sha256_uri({"test": "issuance"})


def vault_with_consent(purposes=("WRITE", "READ"), projection="p"):
    """(vault, consent, layers): every vault call below goes through both credential layers."""
    layers = TwoLayers()
    vault = layers.vault()
    layers.bind(vault, custody_key_ref=REF, issued_by="TV/TVC", tvc_issuance_receipt_ref=TVC_REF)
    consent = layers.grant(vault, purposes=list(purposes), projection_ids=[projection], observed_at="t0")["receipt_hash"]
    return vault, consent, layers


class KvSkapVaultFinishPoint(unittest.TestCase):
    def test_finish_point_verdict(self) -> None:
        self.assertEqual(_consumed_pin_divergence(), [])  # the consumed source is the pinned bytes
        verdict = kv.finish_point()
        self.assertEqual(verdict["task_id"], "KV-SKAP-VAULT-FUNCTIONAL-001")
        self.assertEqual(verdict["scope_digest"],
                         "sha256:95f060fcc2b2455908c838fbcada36eb80b05cad2bf15b8a0b9607cd4672d9dc")  # no-intra-org-InTr reseal (after LC-KV-09)
        self.assertEqual([r["predicate"] for r in verdict["predicates"]], list(kv.PREDICATES))
        self.assertEqual(len(kv.PREDICATES), 13)
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
        self.assertEqual({r["predicate"]: r.get("failure_code") for r in verdict["predicates"]
                          if r["disposition"] != "ALLOW"},
                         {**{p: "KV_FINISH_POINT_EVIDENCE_INVALID" for p in kv._EVIDENCE_CHECKS},
                          "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY": "SKAP_ACCESS_LAYER2_REFUSED",
                          "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE": "KV_ACCESS_LAYER1_REFUSED",
                          "SKAP_VAULT_REACHABLE_ONLY_FROM_INSIDE_KV": "SKAP_ACCESS_LAYER2_REFUSED",
                          "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT": "SKAP_ACCESS_LAYER2_REFUSED"})


class RoundTrip(unittest.TestCase):
    def test_write_read_revoke_round_trip_is_exact(self) -> None:
        vault, consent, L = vault_with_consent()
        content = {"a": [1, 2, {"b": "ü"}], "n": None}
        L.write(vault, projection_id="p", content=content, consent_receipt_hash=consent, custody_key_ref=REF)
        read, receipt = L.read(vault, projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(read, content)
        self.assertEqual(receipt["body"]["content_sha256"], kv.sha256_uri(content))
        read["a"].append(3)  # the caller's copy never aliases the vault
        self.assertEqual(L.read(vault, projection_id="p", consent_receipt_hash=consent)[0], content)
        L.revoke(vault, consent_receipt_hash=consent, observed_at="t1")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.read(vault, projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_REVOKED")
        for field in SIX:
            self.assertTrue(ctx.exception.fields[field])

    def test_no_vault_operation_is_reachable_without_the_layer2_gate(self) -> None:
        """LC-KV-07/10/12: direct calls, caller strings, forged or replayed receipts all refuse with six fields."""
        vault, consent, L = vault_with_consent()
        gateless = kv.KVSkapVault("principal:test")
        forged = kv.sha256_uri({"caller": "minted"})
        spent = L.skap_hash("SKAP_WRITE", "p")
        L.write(vault, projection_id="p", content={"n": 0}, consent_receipt_hash=consent, custody_key_ref=REF)
        vault.write_projection(projection_id="p", content={"n": 1}, consent_receipt_hash=consent, custody_key_ref=REF,
                               skap_access_receipt_hash=spent)
        attempts = [
            lambda: gateless.bind_custody_key_reference(custody_key_ref=REF, issued_by="TV/TVC",
                                                        tvc_issuance_receipt_ref=TVC_REF),
            lambda: gateless.grant_consent(purposes=["READ"], projection_ids=["p"], observed_at="t"),
            lambda: vault.read_projection(projection_id="p", consent_receipt_hash=consent),
            lambda: vault.write_projection(projection_id="p", content={}, consent_receipt_hash=consent,
                                           custody_key_ref=REF, intr_transition_ref="intr:caller-asserted"),
            lambda: vault.read_projection(projection_id="p", consent_receipt_hash=consent,
                                          skap_access_receipt_hash=forged),
            lambda: vault.write_projection(projection_id="p", content={}, consent_receipt_hash=consent,
                                           custody_key_ref=REF, skap_access_receipt_hash=spent),
            lambda: vault.read_projection(projection_id="p", consent_receipt_hash=consent,
                                          skap_access_receipt_hash=L.skap_hash("SKAP_WRITE", "p")),
            lambda: vault.read_projection(projection_id="p", consent_receipt_hash=consent,
                                          skap_access_receipt_hash=L.skap_hash("SKAP_READ", "other")),
            lambda: vault.revoke_consent(consent_receipt_hash=consent, observed_at="t"),
            lambda: kv.KVSkapVault.reconstruct(vault.export_lineage()),
        ]
        for attempt in attempts:
            with self.assertRaises(kv.VaultRefusal) as ctx:
                attempt()
            self.assertEqual(ctx.exception.fields["failure_code"], kv.LAYER2_REFUSAL_CODE)
            for field in SIX:
                self.assertTrue(ctx.exception.fields[field], field)
        self.assertEqual(ctx.exception.fields["owning_existing_goal"], kv.GOAL_REF)
        self.assertEqual(vault.lineage[-1]["body"]["content"], {"n": 1})

    def test_layer2_admits_only_a_layer1_receipt_from_a_healthy_node(self) -> None:
        from runtime.kv_skap_layer2 import kv_skap_transition
        L = TwoLayers()

        def admit(prior):
            return L.gate.admit(kv_skap_transition(principal_ref=L.principal, operation="SKAP_READ", subject_ref="p",
                                                   prior_receipt_hash=prior))
        sick = L.kv_access(evidence={"schema": "x"})
        self.assertEqual((sick["decision"], sick["failure_code"]), ("FAIL_CLOSED", "KV_ACCESS_LAYER1_REFUSED"))
        self.assertIsNone(sick["kv_access_receipt"])
        good = L.kv_hash()
        recomputed = kv.sha256_uri({"schema": "stegverse.kv-access-receipt/v1", "boundary": "INTR_DEVICE_KV"})
        for prior, cause in ((None, "LAYER1_KV_ACCESS_RECEIPT_ABSENT"), ("intr:x", "LAYER1_KV_ACCESS_RECEIPT_ABSENT"),
                             (recomputed, "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1")):
            out = admit(prior)
            self.assertEqual((out["disposition"], out["failure_code"], out["refusal_cause"]),
                             ("FAIL_CLOSED", "SKAP_ACCESS_LAYER2_REFUSED", cause))
            self.assertEqual(out["failed_predicate"], "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT")
            for field in SIX:
                self.assertTrue(out[field], field)
        first = admit(good)
        self.assertEqual(first["disposition"], "ALLOW")
        self.assertEqual(first["skap_access_receipt"]["prior_receipt_hash"], good)
        self.assertEqual(admit(good)["refusal_cause"], "LAYER1_KV_ACCESS_RECEIPT_ALREADY_USED")
        # a layer-1 runtime that is not the gate's own cannot vouch for a receipt
        other = TwoLayers()
        self.assertEqual(other.gate.admit(kv_skap_transition(principal_ref=L.principal, operation="SKAP_READ",
                                                             subject_ref="p", prior_receipt_hash=L.kv_hash()))
                         ["refusal_cause"], "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1")
        chain = L.gate.verify_access_chain(good, first["skap_access_receipt"]["receipt_hash"])
        self.assertEqual(chain["disposition"], "ALLOW")
        self.assertEqual(L.gate.verify_access_chain(L.kv_hash(), first["skap_access_receipt"]["receipt_hash"])
                         ["failure_code"], "SKAP_ACCESS_LAYER2_REFUSED")
        self.assertEqual(L.gate.verify_access_chain(recomputed, first["skap_access_receipt"]["receipt_hash"])
                         ["failure_code"], "KV_ACCESS_LAYER1_REFUSED")

    def test_skap_entry_is_deterministic_and_returns_dispositions(self) -> None:
        L = TwoLayers()
        vault = L.vault()
        out = kv.skap_entry(L.gate, vault, operation="BIND_CUSTODY_KEY_REFERENCE", kv_access_receipt_hash=L.kv_hash(),
                            arguments={"custody_key_ref": REF, "issued_by": "TV/TVC", "tvc_issuance_receipt_ref": TVC_REF})
        self.assertEqual(out["disposition"], "ALLOW")
        self.assertEqual(out["result"]["body"]["access"]["skap_access_receipt_hash"], out["skap_access_receipt_hash"])
        refused = kv.skap_entry(L.gate, vault, operation="SKAP_READ", kv_access_receipt_hash="sha256:" + "0" * 64,
                                arguments={"projection_id": "p", "consent_receipt_hash": "x"})
        self.assertEqual(refused["failure_code"], "SKAP_ACCESS_LAYER2_REFUSED")
        inner = kv.skap_entry(L.gate, vault, operation="BIND_CUSTODY_KEY_REFERENCE", kv_access_receipt_hash=L.kv_hash(),
                              arguments={"custody_key_ref": REF, "issued_by": "KV", "tvc_issuance_receipt_ref": TVC_REF})
        self.assertEqual(inner["failure_code"], "SKAP_CUSTODY_WRITER_NOT_TV_TVC")
        self.assertEqual(kv.skap_entry(TwoLayers().gate, vault, operation="SKAP_READ", kv_access_receipt_hash=None,
                                       arguments={})["failure_code"], "SKAP_ACCESS_LAYER2_REFUSED")


class Consent(unittest.TestCase):
    def test_write_and_read_require_a_covering_consent(self) -> None:
        vault, consent, L = vault_with_consent(purposes=("WRITE",))
        L.write(vault, projection_id="p", content={"x": 1}, consent_receipt_hash=consent,
                               custody_key_ref=REF)
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.read(vault, projection_id="p", consent_receipt_hash=consent)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_SCOPE_DOES_NOT_COVER_OPERATION")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.write(vault, projection_id="other", content={}, consent_receipt_hash=consent,
                                   custody_key_ref=REF)
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_SCOPE_DOES_NOT_COVER_OPERATION")
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.read(vault, projection_id="p", consent_receipt_hash="sha256:unknown")
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_RECEIPT_NOT_FOUND")

    def test_revocation_is_receipted_and_not_repeatable(self) -> None:
        vault, consent, L = vault_with_consent()
        receipt = L.revoke(vault, consent_receipt_hash=consent, observed_at="t")
        self.assertEqual(receipt["kind"], "CONSENT_REVOKED")
        self.assertEqual(receipt["body"]["consent_receipt_hash"], consent)
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.revoke(vault, consent_receipt_hash=consent, observed_at="t")
        self.assertEqual(ctx.exception.fields["failure_code"], "KV_CONSENT_ALREADY_REVOKED")


class Custody(unittest.TestCase):
    def test_only_tv_tvc_custody_key_references_are_held(self) -> None:
        L = TwoLayers()
        vault = L.vault()
        for issued_by in ("KV", "SKAP Vault", "user", ""):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                L.bind(vault, custody_key_ref=REF, issued_by=issued_by, tvc_issuance_receipt_ref=TVC_REF)
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_WRITER_NOT_TV_TVC")
        for ref in ("raw-bytes", kv.CUSTODY_REF_PREFIX, "-----BEGIN PRIVATE KEY-----"):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                L.bind(vault, custody_key_ref=ref, issued_by="TV/TVC", tvc_issuance_receipt_ref=TVC_REF)
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_KEY_REFERENCE_INVALID")
        for receipt_ref in ("r", "probe:tvc", "", None):  # bind verifies the issuance receipt hash, never a string
            with self.assertRaises(kv.VaultRefusal) as ctx:
                L.bind(vault, custody_key_ref=REF, issued_by="TV/TVC", tvc_issuance_receipt_ref=receipt_ref)
            self.assertEqual(ctx.exception.fields["failure_code"], "TVC_CUSTODY_ISSUANCE_RECEIPT_MISSING")
        self.assertEqual(vault.lineage, [])

    def test_key_or_credential_material_never_enters_kv(self) -> None:
        vault, consent, L = vault_with_consent()
        for content in ({"private_key": "x"}, {"nested": {"password": "x"}}, {"skap_ciphertext": "x"}):
            with self.assertRaises(kv.VaultRefusal) as ctx:
                L.write(vault, projection_id="p", content=content, consent_receipt_hash=consent,
                                       custody_key_ref=REF)
            self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED")

    def test_write_requires_a_bound_custody_reference(self) -> None:
        vault, consent, L = vault_with_consent()
        with self.assertRaises(kv.VaultRefusal) as ctx:
            L.write(vault, projection_id="p", content={}, consent_receipt_hash=consent,
                                   custody_key_ref=kv.CUSTODY_REF_PREFIX + "unbound")
        self.assertEqual(ctx.exception.fields["failure_code"], "SKAP_CUSTODY_KEY_REFERENCE_NOT_BOUND")


class LineageAndContinuity(unittest.TestCase):
    def _vault(self):
        vault, consent, L = vault_with_consent()
        L.write(vault, projection_id="p", content={"v": 1}, consent_receipt_hash=consent,
                               custody_key_ref=REF)
        L.read(vault, projection_id="p", consent_receipt_hash=consent)
        L.revoke(vault, consent_receipt_hash=consent, observed_at="t")
        self.L = L
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
                self.L.reconstruct(copy_)
            self.assertEqual(ctx.exception.fields["failure_code"], "KV_RECEIPT_LINEAGE_BROKEN")

    def test_any_device_reconstructs_exactly_from_the_lineage_alone(self) -> None:
        vault, consent = self._vault()
        wire = json.dumps(vault.export_lineage())  # the only thing another device receives
        fresh = self.L.reconstruct(json.loads(wire))
        self.assertEqual(fresh.head, vault.head)
        self.assertEqual(fresh.export_lineage(), vault.export_lineage())
        with self.assertRaises(kv.VaultRefusal) as ctx:  # revocation survives the move
            self.L.read(fresh, projection_id="p", consent_receipt_hash=consent)
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
        self.assertLessEqual(imported, {"__future__", "argparse", "copy", "datetime", "hashlib", "json", "os",
                                        "subprocess", "sys", "typing", "runtime"})
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


def custody_readback(lineage, provider="ecosystem-git-ref"):
    digest = kv.sha256_uri(lineage)
    return {"schema": kv.CUSTODY_READBACK_SCHEMA, "record_type": "KV_SKAP_VAULT_LINEAGE", "disposition": "ALLOW",
            "task_id": kv.TASK_ID, "principal_ref": lineage["principal_ref"], "lineage_sha256": digest,
            "read_back_lineage_sha256": digest, "head_receipt_hash": lineage["head"],
            "receipt_count": len(lineage["receipts"]),
            "provider_adapter_ref": f"continuity-vault-kit:runtime/kv_storage_provider_adapter.py#{provider}",
            "exact_hash_readback_verified": True, "authority_effect": "NONE"}


def evidence_bundle(layers=None):
    """A full bundle. Every lineage receipt went through both layers (E0 stand-in healthy-node evaluator)."""
    issuance = tvc_issuance()
    L = layers or TwoLayers()
    vault = L.vault()
    L.bind(vault, custody_key_ref=issuance["custody_key_ref"], issued_by="TV/TVC",
           tvc_issuance_receipt_ref=issuance["receipt_sha256"])
    consent = L.grant(vault, purposes=["WRITE", "READ"], projection_ids=["p"], observed_at="t0")["receipt_hash"]
    L.write(vault, projection_id="p", content={"v": 1}, consent_receipt_hash=consent,
            custody_key_ref=issuance["custody_key_ref"])
    L.read(vault, projection_id="p", consent_receipt_hash=consent)
    L.revoke(vault, consent_receipt_hash=consent, observed_at="t1")
    lineage = vault.export_lineage()
    return {"schema": kv.EVIDENCE_SCHEMA, "lineage": lineage, "intr_transition_receipts": list(L.intr_receipts),
            "durable_custody_readback_receipt": custody_readback(lineage), "tvc_issuance_receipts": [issuance],
            **L.access_evidence()}


def failure_codes(verdict):
    return {r["predicate"]: r["failure_code"] for r in verdict["predicates"] if r["disposition"] != "ALLOW"}


TVC_AUTHORITY_PREDICATE = "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER"
TVC_AUTHORITY_GAP = {TVC_AUTHORITY_PREDICATE: "TVC_CUSTODY_ISSUANCE_AUTHENTICITY_NOT_PROVEN"}


class EvidenceDrivenVerdict(unittest.TestCase):
    def test_reference_only_evidence_cannot_reach_allow(self) -> None:
        verdict = kv.evaluate(evidence_bundle())
        self.assertEqual(verdict["disposition"], "FAIL_CLOSED")
        self.assertEqual(failure_codes(verdict), TVC_AUTHORITY_GAP)
        self.assertEqual(verdict["unmet_predicates"], [TVC_AUTHORITY_PREDICATE])
        row = next(r for r in verdict["predicates"] if r["predicate"] == TVC_AUTHORITY_PREDICATE)
        self.assertTrue(row["owning_existing_goal"].startswith("TV/TVC"))
        self.assertEqual(row["dependency_relation"], "CONSUMES")
        self.assertIn("integrates its verifier", row["next_attempt"])
        self.assertIn("evidence-only retry cannot", row["next_attempt"])
        for field in SIX:
            self.assertTrue(row[field], field)

    def test_each_evidence_gap_is_a_six_field_fail_closed(self) -> None:
        RT, AD, TV = ("KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                      "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED",
                      "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER")

        def drop(key):
            return lambda e: e.pop(key)

        def write_intr(e):  # the InTr receipt bound by the write's layer-1 receipt
            ref = e["lineage"]["receipts"][2]["body"]["access"]["intr_receipt_ref"]
            return next(r for r in e["intr_transition_receipts"] if kv.sha256_uri(r) == ref)

        def intr_missing(e):
            e["intr_transition_receipts"].remove(write_intr(e))

        def intr_edited(e):  # an edited InTr receipt no longer hashes to the ref its layer-1 receipt binds
            write_intr(e)["transition_outcome"] = "APPLIED_LATER"

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
                 (intr_edited, RT, "INTR_TRANSITION_RECEIPT_NOT_BOUND"),
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
            self.assertEqual(failure_codes(verdict), {**TVC_AUTHORITY_GAP, predicate: code}, code)
            row = next(r for r in verdict["predicates"] if r["predicate"] == predicate)
            for field in SIX:
                self.assertTrue(row[field], (code, field))

    def test_an_invalid_bound_intr_receipt_is_refused(self) -> None:
        def denied(r):
            r["transition_outcome"] = "DENIED"

        def bad_manifest(r):
            r["required_evidence_manifest"][0]["content"]["x"] = 1
        for edit in (denied, bad_manifest):
            verdict = kv.evaluate(evidence_bundle(TwoLayers(intr_edit=edit)))
            self.assertEqual(failure_codes(verdict),
                             {**TVC_AUTHORITY_GAP,
                              "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT": "INTR_TRANSITION_RECEIPT_INVALID"})

    def test_every_access_row_failure_fails_its_mapped_sealed_predicate(self) -> None:
        """LC-KV-09 E1 condition (Coordination, Oct 23): for each access row, if the row fails, the sealed predicate
        it maps to (ACCESS_CONSTRAINT_PREDICATE) fails. Since the LC-KV-09 reseal (d68e239b -> d4a98dc0) each row is
        also its own sealed predicate, and a failing row fails that predicate too.

        Part 1 isolates each row: only that row is made to fail. Part 2 uses real evidence mutations, including
        multi-row ones.
        """
        mapping = kv.ACCESS_CONSTRAINT_PREDICATE
        self.assertEqual(set(mapping), {kv.LAYER_PREDICATE_L1, kv.LAYER_PREDICATE_L2, kv.LAYER_PREDICATE_PRIOR})
        self.assertTrue(set(mapping.values()) <= set(kv.PREDICATES), mapping)
        self.assertTrue(set(mapping) <= set(kv.PREDICATES), mapping)  # LC-KV-09: each row is a sealed predicate
        self.assertTrue(kv.SCOPE_DIGEST.startswith("sha256:95f060fc"))
        baseline = kv.evaluate(evidence_bundle())
        self.assertEqual(baseline["access_constraints_conformant"], 3)
        allowed = {r["predicate"] for r in baseline["predicates"] if r["disposition"] == "ALLOW"}
        self.assertTrue(set(mapping.values()) <= allowed)  # every mapped predicate passes when its rows pass

        def state(verdict):
            rows = {a["constraint"]: a["disposition"] for a in verdict["access_constraints"]}
            preds = {r["predicate"]: r for r in verdict["predicates"]}
            return rows, preds
        # Part 1: make exactly one row fail, and leave the evidence and every other row untouched.
        original = kv._access_failures
        for row in mapping:
            def only_this_row(evidence, lineage_failure, _row=row):
                out = original(evidence, lineage_failure)
                return {c: (("ISOLATED_ROW_FAILURE", "B", "test") if c == _row else v) for c, v in out.items()}
            kv._access_failures = only_this_row
            try:
                verdict = kv.evaluate(evidence_bundle())
            finally:
                kv._access_failures = original
            rows, preds = state(verdict)
            self.assertEqual({c for c, d in rows.items() if d != "ALLOW"}, {row})
            mapped = preds[mapping[row]]
            self.assertNotEqual(mapped["disposition"], "ALLOW", row)
            self.assertIn(row, mapped["access_constraints_unmet"])
            for field in SIX:
                self.assertTrue(mapped[field], (row, field))
            own = preds[row]
            self.assertEqual(own["disposition"], "FAIL_CLOSED", row)
            self.assertEqual(own["failure_code"], next(a["failure_code"] for a in verdict["access_constraints"]
                                                       if a["constraint"] == row), row)
            self.assertEqual(own["access_constraints_unmet"], [row])
            for field in SIX:
                self.assertTrue(own[field], (row, field))
            for sibling in set(mapping) - {row}:
                self.assertEqual(preds[sibling]["disposition"], "ALLOW", (row, sibling))
            for other in set(mapping.values()) - {mapping[row]}:
                if all(mapping[r] != other for r in rows if rows[r] != "ALLOW"):
                    self.assertEqual(preds[other]["disposition"], "ALLOW", (row, other))
        # Part 2: with real mutated evidence, every failing row fails its mapped predicate.
        mutations = {
            "drop layer-1 receipts": lambda e: e.pop("layer1_kv_access_receipts"),
            "drop layer-2 receipts": lambda e: e.pop("layer2_skap_access_receipts"),
            "layer-1 health edited": lambda e: e["layer1_kv_access_receipts"][0]["healthy_node_receipt"].update(
                healthy_node_established=False),
            "layer-1 evaluator not pinned": lambda e: e["layer1_kv_access_receipts"][0].update(
                healthy_node_evaluator="someone.else"),
            "layer-2 operation edited": lambda e: e["layer2_skap_access_receipts"][0].update(operation="SKAP_READ"),
            "layer-2 prior edited": lambda e: e["layer2_skap_access_receipts"][0].update(
                prior_receipt_hash="sha256:" + "0" * 64),
        }
        for name, mutate in mutations.items():
            evidence = evidence_bundle()
            mutate(evidence)
            rows, preds = state(kv.evaluate(evidence))
            failing = {c for c, d in rows.items() if d != "ALLOW"}
            self.assertTrue(failing, name)
            for row in failing:
                self.assertNotEqual(preds[mapping[row]]["disposition"], "ALLOW", (name, row))
                self.assertNotEqual(preds[row]["disposition"], "ALLOW", (name, row))

    def test_each_access_layer_gap_is_a_six_field_fail_closed(self) -> None:
        """LC-KV-09/10/11: the three access constraints, each evidence-bound and named by its own layer."""
        RT, SK = "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT", "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY"
        L1, L2, PRIOR = (kv.LAYER_PREDICATE_L1, kv.LAYER_PREDICATE_L2, kv.LAYER_PREDICATE_PRIOR)

        def edit_l1(e):
            e["layer1_kv_access_receipts"][0]["healthy_node_receipt"]["healthy_node_established"] = False

        def edit_l1_rehash(e):  # a caller recomputing the receipt hash after editing still cannot pass
            r = e["layer1_kv_access_receipts"][0]
            r["healthy_node_receipt"]["node_id"] = "SV-NODE-E0OTHER001"
            r["receipt_hash"] = kv.sha256_uri({k: v for k, v in r.items() if k != "receipt_hash"})

        def edit_l2(e):
            e["layer2_skap_access_receipts"][0]["operation"] = "SKAP_READ"

        cases = [
            (lambda e: e.pop("layer1_kv_access_receipts"),
             {RT: "KV_ACCESS_LAYER1_REFUSED", SK: "SKAP_ACCESS_LAYER2_REFUSED"}, {L1, PRIOR}),
            (lambda e: e.pop("layer2_skap_access_receipts"), {SK: "SKAP_ACCESS_LAYER2_REFUSED"}, {L2, PRIOR}),
            (edit_l1, {RT: "KV_ACCESS_LAYER1_REFUSED"}, {L1}),
            (edit_l1_rehash, {RT: "KV_ACCESS_LAYER1_REFUSED", SK: "SKAP_ACCESS_LAYER2_REFUSED"}, {L1, PRIOR}),
            (edit_l2, {SK: "SKAP_ACCESS_LAYER2_REFUSED"}, {L2}),
        ]
        for mutate, codes, unmet in cases:
            evidence = evidence_bundle()
            mutate(evidence)
            verdict = kv.evaluate(evidence)
            self.assertEqual({a["constraint"] for a in verdict["access_constraints"] if a["disposition"] != "ALLOW"},
                             unmet, codes)
            self.assertEqual({k: v for k, v in failure_codes(verdict).items() if k in (RT, SK)}, codes)
            own = {k: v for k, v in failure_codes(verdict).items() if k in (L1, L2, PRIOR)}
            self.assertEqual(set(own), unmet, codes)  # LC-KV-09: each failing row fails its own sealed predicate
            rows = {r["constraint"]: r.get("failure_code") for r in verdict["access_constraints"]}
            self.assertEqual(own, {c: rows[c] for c in unmet})
            for row in verdict["access_constraints"]:
                if row["disposition"] != "ALLOW":
                    for field in SIX:
                        self.assertTrue(row[field], field)
                    self.assertEqual(row["owning_existing_goal"], kv.GOAL_REF)
        # health decided by anything but the pinned InTr evaluator never reaches layer 2 (LC-KV-10), so it can never
        # become evidence; the finish point applies the same conformance function to every layer-1 receipt.
        from kv_two_layer_e0 import pinned

        def injected(node_id, **kw):
            return pinned()["healthy_node_evaluator"].evaluate(node_id, **kw)
        out = TwoLayers(evaluator=injected).kv_access()  # refused at layer 1 by identity: no receipt to carry
        self.assertEqual((out["decision"], out["refusal_cause"], out["kv_access_receipt"]),
                         ("FAIL_CLOSED", "LAYER1_NOT_EVALUATED_THROUGH_THE_PINNED_EVALUATE", None))
        exercise = TwoLayers()
        out = exercise.kv_access()
        self.assertEqual(out["decision"], "ALLOW_BOUNDED_CONTEXT")
        edited = {**out["kv_access_receipt"], "healthy_node_evaluator_code_sha256": "sha256:" + "0" * 64}
        self.assertEqual(kv.layer1_receipt_conformance(edited), "LAYER1_DECIDER_CODE_NOT_THE_PINNED_CODE")
        exercise.layer1.healthy_node_evaluator = injected  # swapped after minting
        refused = exercise.gate.admit(kv.kv_skap_transition(
            principal_ref=exercise.principal, operation="SKAP_READ", subject_ref="p",
            prior_receipt_hash=out["kv_access_receipt"]["receipt_hash"]))
        self.assertEqual((refused["disposition"], refused["failure_code"], refused["refusal_cause"]),
                         ("FAIL_CLOSED", "SKAP_ACCESS_LAYER2_REFUSED", "LAYER1_NOT_EVALUATED_THROUGH_THE_PINNED_EVALUATE"))
        for field in SIX:
            self.assertTrue(refused[field], field)

    def test_endpoint_not_an_org_member_reuses_the_closed_membership_schema(self) -> None:
        """LC-KV-09 P4 (ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER): decided by runtime.kv_receipt_ledgers' closed
        membership schema and by both digest-pinned contracts loading through designation(); nothing re-implemented."""
        P4 = kv.MEMBERSHIP_PREDICATE
        self.assertIn(P4, kv.PREDICATES)
        self.assertNotIn(P4, kv.EVIDENCE_BOUND)  # decided without evidence, at E0
        from runtime import kv_receipt_ledgers as ledgers
        self.assertIs(kv._closed_schema, ledgers._closed_schema)
        self.assertIs(kv.designation, ledgers.designation)
        for verdict in (kv.evaluate(), kv.evaluate(evidence_bundle())):
            row = next(r for r in verdict["predicates"] if r["predicate"] == P4)
            self.assertEqual((row["disposition"], row["locus"]), ("ALLOW", "LOCAL_EXERCISE+CONTRACTS"))
        for probe in kv._MEMBERSHIP_PROBES:  # every probe is refused by the shared checks
            closed = ledgers._closed_schema(probe)
            self.assertTrue((closed and closed[0] == ledgers.MEMBERSHIP_CODE) or ledgers._org_membership(probe)
                            or ledgers._org_designation(probe), probe)

    def test_endpoint_org_membership_fails_closed(self) -> None:
        P4 = kv.MEMBERSHIP_PREDICATE
        # a contract that binds an org membership: designation() refuses it, and P4 fails closed with six fields
        original = kv.designation
        refusal = {"failure_code": kv.MEMBERSHIP_CODE, "failure_class": "C",
                   "required_evidence_or_repair": "remove the organization binding"}
        kv.designation = lambda which: (None, refusal) if which == kv.SKAP_VAULT_LEDGER else original(which)
        try:
            self.assertEqual(kv._contracts_membership()[0], kv.MEMBERSHIP_CODE)
            verdict = kv.evaluate(evidence_bundle())
        finally:
            kv.designation = original
        row = next(r for r in verdict["predicates"] if r["predicate"] == P4)
        self.assertEqual(row["disposition"], "FAIL_CLOSED")
        self.assertNotEqual(verdict["disposition"], "ALLOW")
        for field in SIX:
            self.assertTrue(row[field], field)
        # a shared schema that stopped refusing membership keys is a local regression: P4 fails closed
        original_closed = kv._closed_schema
        kv._closed_schema = lambda contract: None
        try:
            self.assertFalse(kv._membership_exercise())
            verdict = kv.evaluate(evidence_bundle())
        finally:
            kv._closed_schema = original_closed
        self.assertEqual(failure_codes(verdict).keys(), {P4, TVC_AUTHORITY_PREDICATE})
        row = next(r for r in verdict["predicates"] if r["predicate"] == P4)
        for field in SIX:
            self.assertTrue(row[field], field)

    def test_the_finish_point_expects_the_nodes_own_ledger_chain(self) -> None:
        """LC-KV-13 completes with a node admitted through its OWN ledger chain, bound by the deployment with its
        pinned genesis. There is no org ledger and no endpoint-kind model: any other binding kind is refused."""
        from tests.kv_two_layer_e0 import NODE, e0_health_ledger
        self.assertEqual(failure_codes(kv.evaluate(evidence_bundle())), TVC_AUTHORITY_GAP)
        self.assertEqual(kv.FINISH_POINT_NODE_KIND, "NODE_OWN_LEDGER_CHAIN")
        # a binding that is not the node's own chain is refused at layer 1 itself, so no receipt can carry it
        source = {**e0_health_ledger(NODE)[0], "kind": "SKAP_VAULT"}
        out = TwoLayers(chain=source).kv_access()
        self.assertEqual((out["decision"], out["refusal_cause"], out["kv_access_receipt"]),
                         ("FAIL_CLOSED", "LEDGER_SOURCE_NOT_BOUND_BY_DEPLOYMENT", None))
        # and a receipt that did carry another kind would be refused by the finish point's own check
        evidence = evidence_bundle()
        evidence["layer1_kv_access_receipts"][0]["healthy_node_ledger_binding"]["kind"] = "SKAP_VAULT"
        verdict = kv.evaluate(evidence)
        row = next(r for r in verdict["access_constraints"] if r["constraint"] == kv.LAYER_PREDICATE_L1)
        self.assertEqual(row["disposition"], "FAIL_CLOSED")

    def test_an_unknown_node_chain_is_refused_and_does_not_block_the_finish_point(self) -> None:
        """A chain whose transport-authenticated key is not the key it binds is a six-field FAIL_CLOSED (class C). It
        does not block the finish point, which completes with the honest node."""
        from tests.kv_two_layer_e0 import NODE, e0_health_ledger, e0_node_identity_key
        out = TwoLayers(chain=e0_health_ledger(NODE, transport_key=e0_node_identity_key(NODE, "another-key:"))[0]
                        ).kv_access()
        self.assertEqual((out["decision"], out["failure_code"], out["failure_class"], out["refusal_cause"]),
                         ("FAIL_CLOSED", "KV_ACCESS_LAYER1_REFUSED", "C", "REQUESTER_KEY_NOT_THE_BOUND_NODE_IDENTITY_KEY"))
        for field in SIX:
            self.assertTrue(isinstance(out[field], str) and out[field].strip(), field)
        self.assertEqual(failure_codes(kv.evaluate(evidence_bundle())), TVC_AUTHORITY_GAP)

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
        vault = TwoLayers().reconstruct(evidence["lineage"])
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
        self.assertEqual(receipt["transition_outcome"], "FAIL_CLOSED")
        self.assertEqual(receipt["prior_state_ref_or_hash"], verdict["evidence_lineage_head"])
        entry = receipt["required_evidence_manifest"][0]
        self.assertEqual(entry["origin_transition_id"], receipt["transition_id"])
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(receipt, kv.organization_ledger_receipt(kv.evaluate(evidence_bundle())))  # deterministic

    def test_unproven_issuance_never_attempts_a_finish_point_append(self) -> None:
        verdict = kv.finish_point(evidence_bundle())
        self.assertEqual(verdict["disposition"], "FAIL_CLOSED")
        self.assertEqual(verdict["runtime_disposition"], "FAIL_CLOSED")
        append = verdict["ledger_append"]
        self.assertEqual(append["failure_code"], "FINISH_POINT_VERDICT_NOT_ALLOW")
        self.assertFalse(append["ledger_append_attempted"])
        self.assertEqual(append["failure_class"], "B")
        for field in SIX:
            self.assertTrue(append[field], field)
        self.assertFalse(append["real_ledger_written"])
        # Independently retain the low-level writer's missing-genesis check.
        direct = kv.append_organization_ledger_receipt(kv.organization_ledger_receipt(verdict), None)
        self.assertEqual(direct["failure_code"], "ORGANIZATION_LEDGER_GENESIS_NOT_OBSERVED")

    def test_scratch_ledger_genesis_absent_is_never_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = scratch_ledger(tmp, genesis=False)
            receipt = kv.organization_ledger_receipt(kv.evaluate(evidence_bundle()))
            append = kv.append_organization_ledger_receipt(receipt, git_dir)
            self.assertEqual(append["failure_code"], "ORGANIZATION_LEDGER_GENESIS_ABSENT")
            probe = subprocess.run(["git", "--git-dir", git_dir, "rev-parse", "--verify", "--quiet",
                                    kv.ORGANIZATION_LEDGER_REF], capture_output=True, check=False)
            self.assertNotEqual(probe.returncode, 0)

    def test_scratch_ledger_append_and_refusals(self) -> None:
        # Test the low-level scratch CAS writer with a FAIL_CLOSED diagnostic
        # receipt. This does not manufacture an ALLOW finish-point verdict.
        receipt = kv.organization_ledger_receipt(kv.evaluate(evidence_bundle()))
        self.assertEqual(receipt["transition_outcome"], "FAIL_CLOSED")
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = scratch_ledger(tmp)
            append = kv.append_organization_ledger_receipt(receipt, git_dir)
            self.assertEqual(append["disposition"], "ALLOW", append)
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
            append = kv.append_organization_ledger_receipt(receipt, scratch_ledger(tmp, remote=True))
            self.assertEqual(append["failure_code"], "LEDGER_TARGET_NOT_SCRATCH")
            append = kv.append_organization_ledger_receipt(receipt, str(Path(tmp) / "absent"))
            self.assertEqual(append["failure_code"], "SCRATCH_LEDGER_NOT_A_GIT_DIR")

    def test_cli_refuses_unproven_issuance_without_moving_scratch_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            path.write_text(json.dumps(evidence_bundle()), encoding="utf-8")
            git_dir = scratch_ledger(tmp)
            tip_before = kv._git(git_dir, "rev-parse", kv.ORGANIZATION_LEDGER_REF).stdout.strip()
            cli = subprocess.run([*E0_FINISH_POINT_CLI, "finish-point", "--evidence",
                                  str(path), "--scratch-ledger-git-dir", git_dir], cwd=ROOT,
                                 capture_output=True, text=True, check=False)
            self.assertEqual(cli.returncode, 2, cli.stdout[-2000:])
            verdict = json.loads(cli.stdout)
            self.assertEqual(failure_codes(verdict), TVC_AUTHORITY_GAP)
            self.assertFalse(verdict["ledger_append"]["ledger_append_attempted"])
            self.assertEqual(verdict["runtime_disposition"], "FAIL_CLOSED")
            self.assertEqual(kv._git(git_dir, "rev-parse", kv.ORGANIZATION_LEDGER_REF).stdout.strip(), tip_before)
            self.assertEqual(verdict["trust_anchors_label"], "E0_STANDIN_TEST_ONLY_NOT_EVIDENCE")
            # LC-KV-15: the production CLI (no E0 anchors) refuses the same E0 evidence, six fields per access row
            plain = subprocess.run([sys.executable, "-m", "runtime.kv_skap_vault", "finish-point", "--evidence",
                                    str(path), "--scratch-ledger-git-dir", scratch_ledger(tmp + "/p")], cwd=ROOT,
                                   capture_output=True, text=True, check=False)
            self.assertEqual(plain.returncode, 2, plain.stdout[-2000:])
            verdict = json.loads(plain.stdout)
            self.assertEqual((verdict["disposition"], verdict["trust_anchors_label"]), ("FAIL_CLOSED", "PRODUCTION"))
            row = next(a for a in verdict["access_constraints"] if a["constraint"] == kv.LAYER_PREDICATE_L1)
            self.assertEqual(row["refusal_cause"], "LAYER1_RECEIPT_MINTED_UNDER_OTHER_TRUST_ANCHORS")
            for field in SIX:
                self.assertTrue(row[field], field)


class TvcIssuanceAuthenticityBoundary(unittest.TestCase):
    def evidence(self):
        manifest_hash = 'sha256:' + 'a' * 64
        body = {
            'schema': kv.TVC_ISSUANCE_SCHEMA,
            'transition': 'TVC_SKAP_CUSTODY_REFERENCE_ISSUE',
            'disposition': 'ALLOW', 'issuer': 'TV/TVC',
            'manifest_sha256': manifest_hash,
            'principal_ref': 'principal:synthetic-only',
            'kv_task_id': kv.TASK_ID,
            'custody_purpose': 'SKAP_VAULT_CIPHERTEXT_CUSTODY',
            'issuance_sequence': 0,
            'custody_key_ref': kv.CUSTODY_REF_PREFIX + manifest_hash[7:39],
            'key_material_location': 'TVC_ONLY',
            'key_material_present': False, 'credential_material_present': False,
            'live_key_slot_binding': 'UNKNOWN_NOT_AUTHENTICALLY_OBSERVED',
            'authority_effect': 'NONE',
        }
        receipt = {**body, 'receipt_sha256': kv.sha256_uri(body)}
        return {
            'lineage': {
                'principal_ref': body['principal_ref'],
                'receipts': [{'kind': 'CUSTODY_KEY_REFERENCE_BOUND', 'body': {
                    'custody_key_ref': body['custody_key_ref'],
                    'tvc_issuance_receipt_ref': receipt['receipt_sha256'],
                }}],
            },
            'tvc_issuance_receipts': [receipt],
        }

    def assertAuthorityUnproven(self, evidence):
        result = kv._evidence_tvc(evidence)
        self.assertIsNotNone(result, 'a public digest is not an authenticated TVC issuance witness')
        self.assertEqual(result[0], 'TVC_CUSTODY_ISSUANCE_AUTHENTICITY_NOT_PROVEN')

    def test_self_constructed_receipt_does_not_prove_tvc_authority(self):
        self.assertAuthorityUnproven(self.evidence())

    def test_rehashed_changed_principal_does_not_prove_tvc_authority(self):
        evidence = self.evidence()
        receipt = evidence['tvc_issuance_receipts'][0]
        receipt['principal_ref'] = 'principal:synthetic-altered'
        receipt['receipt_sha256'] = kv.sha256_uri({k: v for k, v in receipt.items() if k != 'receipt_sha256'})
        evidence['lineage']['principal_ref'] = receipt['principal_ref']
        evidence['lineage']['receipts'][0]['body']['tvc_issuance_receipt_ref'] = receipt['receipt_sha256']
        self.assertAuthorityUnproven(evidence)

    def test_self_asserted_live_binding_is_not_an_authenticated_witness(self):
        evidence = self.evidence()
        receipt = evidence['tvc_issuance_receipts'][0]
        receipt['live_key_slot_binding'] = 'BOUND'
        receipt['receipt_sha256'] = kv.sha256_uri({k: v for k, v in receipt.items() if k != 'receipt_sha256'})
        evidence['lineage']['receipts'][0]['body']['tvc_issuance_receipt_ref'] = receipt['receipt_sha256']
        self.assertAuthorityUnproven(evidence)

    def test_tamper_without_rehash_remains_invalid(self):
        evidence = self.evidence()
        evidence['tvc_issuance_receipts'][0]['principal_ref'] = 'principal:synthetic-altered'
        self.assertEqual(kv._evidence_tvc(evidence)[0], 'TVC_CUSTODY_KEY_ISSUANCE_RECEIPT_INVALID')

    def test_missing_issuance_receipt_remains_unobserved(self):
        evidence = self.evidence()
        evidence['tvc_issuance_receipts'] = []
        self.assertEqual(kv._evidence_tvc(evidence)[0], 'TVC_CUSTODY_KEY_ISSUANCE_NOT_OBSERVED')

    def test_receipt_not_bound_to_lineage_remains_refused(self):
        evidence = self.evidence()
        evidence['lineage']['receipts'][0]['body']['tvc_issuance_receipt_ref'] = 'sha256:' + 'b' * 64
        self.assertEqual(kv._evidence_tvc(evidence)[0], 'TVC_CUSTODY_KEY_ISSUANCE_NOT_BOUND')



if __name__ == "__main__":
    unittest.main()

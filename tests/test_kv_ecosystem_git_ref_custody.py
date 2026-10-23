"""LC-KV-03(a) (StegVerse-Labs/.github#3330): ecosystem-only durable custody, exercised end to end at E0.

Each test runs a real manifest-directed append and exact-hash read-back against a scratch bare git repository
created in a temporary directory; nothing outside it is touched and nothing is pushed. No test is skipped.
"""
from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from runtime import kv_ecosystem_git_ref_custody as custody  # noqa: E402
from runtime.kv_storage_provider_adapter import default_registry, vault_lineage_registry  # noqa: E402
from runtime.task_registry_event_sovereign_kv_binding import (  # noqa: E402
    build_vault_lineage_custody_binding,
    build_vault_lineage_record,
    validate_vault_lineage_custody_result,
)
from test_sovereign_kv_vault_lineage_record import SIX, lineage  # noqa: E402


def bind(exported):
    return build_vault_lineage_custody_binding(
        lineage_record=build_vault_lineage_record(exported_lineage=exported), provider_id="ecosystem-git-ref",
        instance_id="kvi_vault_001", kv_set_id="kv-skap-vault",
        storage_locator=custody.custody_ref(exported["principal_ref"]))


class EcosystemGitRefCustody(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.git_dir = str(Path(self._tmp.name) / "custody.git")
        subprocess.run(["git", "init", "-q", "--bare", self.git_dir], check=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assertFailClosed(self, out, code):
        self.assertEqual(out["disposition"], "FAIL_CLOSED", out)
        self.assertEqual(out["failure_code"], code, out)
        for field in SIX:
            self.assertTrue(out[field], field)

    def test_registry_adds_the_ecosystem_adapter_without_changing_default(self) -> None:
        ids = [a.provider_id for a in default_registry().adapters]
        self.assertNotIn("ecosystem-git-ref", ids)
        descriptor = vault_lineage_registry().get("ecosystem-git-ref").descriptor()
        self.assertEqual((descriptor["storage_class"], descriptor["locator_kind"]), ("ECOSYSTEM", "GIT_REF"))
        self.assertEqual(descriptor["session_requirement"], "NONE")
        self.assertEqual(descriptor["authority_effect"], "NONE")

    def test_append_readback_and_validate_round_trip(self) -> None:
        exported = lineage()
        bound = bind(exported)
        manifest = custody.build_write_manifest(binding=bound, exact_lineage=exported,
                                                expected_predecessor_commit=None)
        written = custody.write_lineage(self.git_dir, manifest)
        self.assertEqual(written["disposition"], "ALLOW", written)
        self.assertTrue(written["custody_ref"].startswith("refs/stegverse/kv-custody/"))
        back = custody.read_back(self.git_dir, principal_ref=exported["principal_ref"],
                                 lineage_sha256=bound["lineage_sha256"])
        self.assertEqual(back["disposition"], "ALLOW", back)
        self.assertEqual(back["exact_lineage"], exported)
        receipt = custody.build_provider_receipt(binding=bound, write_result=written,
                                                 interlock_receipt_ref="interlock:receipt:1",
                                                 intr_receipt_ref="intr:receipt:1",
                                                 skap_credential_ref="tvc://skap-custody/k1")
        result = validate_vault_lineage_custody_result(binding=bound, provider_receipt=receipt,
                                                       read_back_lineage=back["exact_lineage"])
        self.assertEqual(result["disposition"], "ALLOW", result)
        self.assertTrue(result["provider_adapter_ref"].endswith("#ecosystem-git-ref"))
        self.assertEqual(result["provider_result_ref"], written["provider_result_ref"])

    def test_without_intr_references_the_receipt_is_not_admitted(self) -> None:
        exported = lineage()
        bound = bind(exported)
        written = custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bound, exact_lineage=exported, expected_predecessor_commit=None))
        receipt = custody.build_provider_receipt(binding=bound, write_result=written, interlock_receipt_ref="",
                                                 intr_receipt_ref="", skap_credential_ref="tvc://skap-custody/k1")
        self.assertEqual(receipt["governance_state"], "PENDING_INTERLOCK_INTR")
        out = validate_vault_lineage_custody_result(binding=bound, provider_receipt=receipt,
                                                    read_back_lineage=exported)
        self.assertFailClosed(out, "VAULT_LINEAGE_CUSTODY_RESULT_NOT_VERIFIED")

    def test_compare_and_swap_refuses_a_stale_predecessor(self) -> None:
        first, second = lineage(2), lineage(3)
        ok = custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bind(first), exact_lineage=first, expected_predecessor_commit=None))
        self.assertEqual(ok["disposition"], "ALLOW")
        stale = custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bind(second), exact_lineage=second, expected_predecessor_commit=None))
        self.assertFailClosed(stale, "KV_CUSTODY_REF_PREDECESSOR_MISMATCH")
        moved = custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bind(second), exact_lineage=second, expected_predecessor_commit=ok["commit"]))
        self.assertEqual(moved["disposition"], "ALLOW", moved)
        self.assertEqual(moved["predecessor_commit"], ok["commit"])
        back = custody.read_back(self.git_dir, principal_ref=second["principal_ref"],
                                 lineage_sha256=bind(second)["lineage_sha256"])
        self.assertEqual(back["exact_lineage"], second)

    def test_readback_is_by_exact_hash(self) -> None:
        exported = lineage()
        custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bind(exported), exact_lineage=exported, expected_predecessor_commit=None))
        self.assertFailClosed(custody.read_back(self.git_dir, principal_ref=exported["principal_ref"],
                                                lineage_sha256="sha256:" + "0" * 64),
                              "KV_CUSTODY_READBACK_HASH_MISMATCH")
        self.assertFailClosed(custody.read_back(self.git_dir, principal_ref="principal:nobody",
                                                lineage_sha256="sha256:" + "0" * 64), "KV_CUSTODY_REF_ABSENT")

    def test_manifest_refusals_are_six_field(self) -> None:
        exported = lineage()
        bound = bind(exported)
        good = custody.build_write_manifest(binding=bound, exact_lineage=exported, expected_predecessor_commit=None)
        edited = copy.deepcopy(good)
        edited["expected_predecessor_commit"] = "f" * 40
        self.assertFailClosed(custody.write_lineage(self.git_dir, edited), "KV_CUSTODY_WRITE_MANIFEST_DIGEST_MISMATCH")
        cloud = build_vault_lineage_custody_binding(
            lineage_record=build_vault_lineage_record(exported_lineage=exported), provider_id="google-drive",
            instance_id="kvi_vault_001", kv_set_id="kv-skap-vault")
        self.assertFailClosed(custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=cloud, exact_lineage=exported, expected_predecessor_commit=None)),
            "KV_CUSTODY_BINDING_NOT_ECOSYSTEM_GIT_REF")
        self.assertFailClosed(custody.write_lineage(self.git_dir, custody.build_write_manifest(
            binding=bound, exact_lineage=lineage(2), expected_predecessor_commit=None)),
            "KV_CUSTODY_LINEAGE_NOT_THE_BOUND_LINEAGE")
        self.assertFailClosed(custody.write_lineage(self.git_dir, {"schema": "other"}),
                              "KV_CUSTODY_WRITE_MANIFEST_INVALID")
        self.assertFailClosed(custody.write_lineage(str(Path(self._tmp.name) / "missing.git"), good),
                              "KV_CUSTODY_GIT_DIR_UNAVAILABLE")
        # nothing was written by any refusal
        code = subprocess.run(["git", "--git-dir", self.git_dir, "for-each-ref", "refs/stegverse/"],
                              capture_output=True, text=True, check=True).stdout
        self.assertEqual(code, "")

    def test_e0_no_network_model_or_clock(self) -> None:
        source = (ROOT / "runtime" / "kv_ecosystem_git_ref_custody.py").read_text(encoding="utf-8")
        for forbidden in ("datetime.now", "time.time", "urllib", "socket", "requests", "openai", "anthropic",
                          "\"push\"", "\"fetch\"", "remote"):
            if forbidden == "remote":
                self.assertNotIn("\"remote\"", source)
            else:
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXEC_SPEC = importlib.util.spec_from_file_location("kv_auto_upgrade", ROOT / "tools" / "apply_legacy_kv_upgrade.py")
EXEC = importlib.util.module_from_spec(EXEC_SPEC)
assert EXEC_SPEC.loader is not None
EXEC_SPEC.loader.exec_module(EXEC)

VERIFY_SPEC = importlib.util.spec_from_file_location("kv_auto_upgrade_verify", ROOT / "tools" / "verify_legacy_kv_upgrade_package.py")
VERIFY = importlib.util.module_from_spec(VERIFY_SPEC)
assert VERIFY_SPEC.loader is not None
VERIFY_SPEC.loader.exec_module(VERIFY)


class AutomatedLegacyKVUpgradeTests(unittest.TestCase):
    def _make_legacy(self, parent: Path) -> tuple[Path, str, str]:
        source = parent / "KnowledgeVault"
        shutil.copytree(EXEC.CURRENT_TEMPLATE, source)
        rows = EXEC.inventory(EXEC.CURRENT_TEMPLATE)
        framework_rel = next(str(row["path"]) for row in rows if str(row["path"]).startswith("_Policy/"))
        personal_rel = next(
            str(row["path"])
            for row in rows
            if str(row["path"]).startswith(("00_Inbox/", "01_Notes/", "02_Research/", "03_Records/", "04_Media/", "05_Projects/", "06_Archive/"))
        )
        (source / framework_rel).write_bytes(b"legacy framework customization\n")
        (source / personal_rel).write_bytes(b"owner-modified seed content\n")
        (source / "01_Notes" / "private-owner-note.md").write_bytes(b"private owner bytes\n")
        runtime = source / "_System" / "Identity" / "owner-runtime.json"
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text(json.dumps({"identity": "preserve-exact"}) + "\n", encoding="utf-8")
        return source, framework_rel, personal_rel

    def test_directory_upgrade_is_non_destructive_and_verified(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source, framework_rel, personal_rel = self._make_legacy(base / "input")
            output = base / "output"
            source_private = (source / "01_Notes" / "private-owner-note.md").read_bytes()
            source_runtime = (source / "_System" / "Identity" / "owner-runtime.json").read_bytes()
            source_personal = (source / personal_rel).read_bytes()
            source_framework = (source / framework_rel).read_bytes()
            source_tree_before = EXEC.inventory_hash(EXEC.inventory(source))

            result = EXEC.execute(source, output, timestamp="20260915T120000Z")

            self.assertEqual(result["result"], "PASS")
            self.assertFalse(result["live_source_overwritten"])
            self.assertFalse(result["manual_file_by_file_work_required"])
            self.assertEqual(EXEC.inventory_hash(EXEC.inventory(source)), source_tree_before)
            updated = Path(result["updated_directory"])
            self.assertEqual((updated / "01_Notes" / "private-owner-note.md").read_bytes(), source_private)
            self.assertEqual((updated / "_System" / "Identity" / "owner-runtime.json").read_bytes(), source_runtime)
            self.assertEqual((updated / personal_rel).read_bytes(), source_personal)
            self.assertEqual((updated / framework_rel).read_bytes(), (EXEC.CURRENT_TEMPLATE / framework_rel).read_bytes())
            preserved_framework = updated / "_System" / "Upgrade" / "Preserved" / framework_rel
            self.assertEqual(preserved_framework.read_bytes(), source_framework)
            candidate_personal = updated / "_System" / "Upgrade" / "Candidates" / personal_rel
            self.assertEqual(candidate_personal.read_bytes(), (EXEC.CURRENT_TEMPLATE / personal_rel).read_bytes())
            self.assertTrue(Path(result["rollback_zip"]).is_file())
            self.assertTrue(Path(result["updated_zip"]).is_file())
            independent = VERIFY.verify(Path(result["updated_zip"]), Path(result["verification_report"]))
            self.assertEqual(independent["result"], "PASS")

    def test_output_collision_refuses_repeat_at_same_identity(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source, _, _ = self._make_legacy(base / "input")
            output = base / "output"
            EXEC.execute(source, output, timestamp="20260915T120001Z")
            with self.assertRaises(FileExistsError):
                EXEC.execute(source, output, timestamp="20260915T120001Z")

    def test_unsafe_zip_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            malicious = base / "malicious.zip"
            with zipfile.ZipFile(malicious, "w") as archive:
                archive.writestr("../escape.txt", "nope")
                archive.writestr("KnowledgeVault/_Meta/vault.manifest.json", "{}")
            with self.assertRaises(ValueError):
                EXEC.execute(malicious, base / "output", timestamp="20260915T120002Z")
            self.assertFalse((base / "escape.txt").exists())

    def test_tampered_updated_zip_fails_independent_verification(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source, _, _ = self._make_legacy(base / "input")
            result = EXEC.execute(source, base / "output", timestamp="20260915T120003Z")
            package = Path(result["updated_zip"])
            with package.open("ab") as handle:
                handle.write(b"tamper")
            with self.assertRaises(ValueError):
                VERIFY.verify(package, Path(result["verification_report"]))


if __name__ == "__main__":
    unittest.main()

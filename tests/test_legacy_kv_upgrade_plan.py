import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legacy_upgrade", ROOT / "tools" / "plan_legacy_kv_upgrade.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class LegacyUpgradePlanTests(unittest.TestCase):
    def test_non_destructive_plan_classifies_changes(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "KnowledgeVault"
            (vault / "_Meta").mkdir(parents=True)
            (vault / "_System").mkdir(parents=True)
            (vault / "00_Inbox").mkdir(parents=True)
            (vault / "_Meta" / "vault.manifest.json").write_text(json.dumps({"version": "0.0.legacy"}), encoding="utf-8")
            (vault / "_System" / "installation.receipt.json").write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
            (vault / "00_Inbox" / "README.md").write_text("legacy different", encoding="utf-8")
            (vault / "owner-note.txt").write_text("preserve me", encoding="utf-8")

            plan = MOD.build_plan(vault)

            self.assertEqual(plan["schema"], "stegverse.kv.legacy-upgrade-plan/v1")
            self.assertEqual(plan["state"], "MIGRATION_PLAN_READY")
            self.assertEqual(plan["source_version"], "0.0.legacy")
            self.assertFalse(plan["mutation_performed"])
            self.assertFalse(plan["overwrite_existing_vault"])
            self.assertTrue(plan["owner_acceptance_required"])
            self.assertTrue(plan["rollback_copy_required"])
            self.assertFalse(plan["credential_material_required"])
            self.assertEqual(plan["authority_effect"], "NONE_PLAN_ONLY")
            self.assertIn("00_Inbox/README.md", plan["template_updates_required"])
            self.assertIn("owner-note.txt", plan["legacy_only_preserve"])
            self.assertTrue(plan["legacy_receipt_present"])

    def test_missing_vault_fails(self):
        with self.assertRaises(ValueError):
            MOD.build_plan(Path("/definitely/not/a/real/knowledgevault"))


if __name__ == "__main__":
    unittest.main()

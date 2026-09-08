#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.adopt_existing_kv_instance import (
    ADOPTION_RECEIPT,
    INSTANCE_RECORD,
    SET_PROJECTION_RECORD,
    AdoptionError,
    apply_adoption,
    plan,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def receipt(root: Path) -> tuple[Path, str]:
    path = root / "_System" / "installation.receipt.json"
    write_json(path, {
        "schema_version": "1.1",
        "source": "continuity-vault-kit:vault_template/KnowledgeVault",
        "destination": str(root),
        "verification": {"full_template_parity": "VALIDATED"},
    })
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


class AdoptionTests(unittest.TestCase):
    def test_plan_is_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            root.mkdir()
            _, digest = receipt(root)
            private = root / "private.txt"
            private.write_text("owner data", encoding="utf-8")
            before = private.read_bytes()
            value = plan(root, instance_number=1, set_id="personal", storage_medium="google-drive", storage_locator="drive-folder:test")
            self.assertEqual(value["installation_receipt_sha256"], "sha256:" + digest)
            self.assertFalse(value["instance_record_exists"])
            self.assertEqual(private.read_bytes(), before)
            self.assertFalse((root / INSTANCE_RECORD).exists())

    def test_apply_requires_exact_receipt_hash_and_preserves_private_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            root.mkdir()
            _, digest = receipt(root)
            private = root / "owner-private.json"
            private.write_text('{"secret_to_owner":"unchanged"}\n', encoding="utf-8")
            before = private.read_bytes()
            with self.assertRaises(AdoptionError):
                apply_adoption(root, instance_number=1, set_id="personal", storage_medium="google-drive", storage_locator=None, expected_receipt_sha256="00" * 32)
            self.assertFalse((root / INSTANCE_RECORD).exists())
            result = apply_adoption(root, instance_number=1, set_id="personal", storage_medium="google-drive", storage_locator="drive-folder:test", expected_receipt_sha256=digest)
            self.assertEqual(result["state"], "EXISTING_KV_ADOPTED_AS_INSTANCE")
            self.assertEqual(result["instance_number"], 1)
            self.assertEqual(result["relationship_tier"], "NOT_CONNECTED")
            self.assertFalse(result["provider_operation_executed"])
            self.assertEqual(private.read_bytes(), before)
            projection = json.loads((root / SET_PROJECTION_RECORD).read_text(encoding="utf-8"))
            self.assertEqual(projection["schema"], "stegverse.kv.my-kv-set-projection/v1")
            self.assertEqual(projection["instance_count"], 1)
            self.assertFalse(projection["private_content_included"])
            self.assertFalse(projection["credential_material_included"])
            self.assertEqual(projection["authority_effect"], "NONE_STATUS_ONLY")
            self.assertFalse(projection["activation_effect"])

    def test_apply_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            root.mkdir()
            _, digest = receipt(root)
            (root / INSTANCE_RECORD).parent.mkdir(parents=True)
            (root / INSTANCE_RECORD).write_text('{"existing":true}\n', encoding="utf-8")
            with self.assertRaisesRegex(AdoptionError, "would be overwritten"):
                apply_adoption(root, instance_number=1, set_id="personal", storage_medium="google-drive", storage_locator=None, expected_receipt_sha256=digest)
            self.assertFalse((root / SET_PROJECTION_RECORD).exists())
            self.assertFalse((root / ADOPTION_RECEIPT).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

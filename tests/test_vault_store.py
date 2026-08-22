import tempfile
import unittest
from pathlib import Path

from execution.vault_store import KnowledgeVaultExecutionStore, VaultStoreError


class VaultStoreTests(unittest.TestCase):
    def test_initializes_expected_execution_layout_and_persists_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            root = store.initialize()
            self.assertTrue((root / "Attempts").is_dir())
            self.assertTrue((root / "Extensions").is_dir())
            self.assertTrue((root / "Receipts").is_dir())
            self.assertTrue((root / "Recovery").is_dir())

            record = {"attempt_id": "attempt:1", "state": "STARTED", "authority_ref": "vault:authority:1"}
            path = store.append_attempt("attempt-1", record)
            self.assertEqual(path, Path(tmp) / "_System" / "Execution" / "Attempts" / "attempt-1.jsonl")
            self.assertEqual(store.read_stream("Attempts", "attempt-1"), [record])

    def test_multiple_execution_categories_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            store.append_extension("message-1", {"extension_id": "stegtalk:communication", "operation": "SEND_MESSAGE"})
            store.append_receipt("message-1", {"receipt_id": "receipt:1", "result": "submitted"})
            store.append_recovery("attempt-1", {"decision": "VERIFY_EXTERNALLY"})
            self.assertEqual(len(store.read_stream("Extensions", "message-1")), 1)
            self.assertEqual(len(store.read_stream("Receipts", "message-1")), 1)
            self.assertEqual(len(store.read_stream("Recovery", "attempt-1")), 1)

    def test_detects_tampered_record_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            path = store.append_receipt("receipt-1", {"receipt_id": "receipt:1", "result": "submitted"})
            text = path.read_text(encoding="utf-8").replace("submitted", "delivered")
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(VaultStoreError):
                store.read_stream("Receipts", "receipt-1")


if __name__ == "__main__":
    unittest.main()

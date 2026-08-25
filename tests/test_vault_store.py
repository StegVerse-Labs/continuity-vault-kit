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

    @staticmethod
    def _intr_packet():
        return {
            "schema": "stegverse.intr.packet.review_candidate/v1",
            "status": "REVIEW_CANDIDATE",
            "protocol": "InTr",
            "topology_ref": "stegverse.skap_intr.review_candidate/v1",
            "envelope": {
                "packet_id": "intrpkt-test-001",
                "authority": {
                    "authority_transfer": False,
                    "model_output_grants_execution_authority": False,
                    "transport_grants_execution_authority": False,
                },
                "protected_payload": {
                    "sealed": True,
                    "plaintext_present": False,
                    "content_class": "SKAP_CREDENTIAL_GRANT",
                    "sealed_material_ref": "sealed://test/object",
                    "resolution_policy": "ENDPOINT_SESSION_VERIFIED_AND_GRANT_VALID",
                },
            },
            "hop_state_machine": [],
            "endpoint_resolution_state_machine": [],
            "failure_invariants": {},
            "kv_decryption_authority": False,
            "kv_secret_resolution_authority": False,
        }

    @staticmethod
    def _intr_receipt():
        return {
            "schema": "stegverse.intr.hop_receipt/v1",
            "receipt_id": "intrrcpt-test-001",
            "packet_id": "intrpkt-test-001",
            "hop_index": 0,
            "direction": "FORWARD",
            "from_role": "SKAP",
            "to_role": "KV",
            "operation_hash": "sha256:" + "a" * 64,
            "payload_hash": "sha256:" + "b" * 64,
            "prior_receipt_hash": None,
            "boundary_identity_ref": "identity:kv-test",
            "boundary_verification": "VERIFIED",
            "transition_state": "FORWARDED",
            "secret_plaintext_present": False,
            "authority_transfer": False,
            "recorded_at": "2026-08-24T20:40:00-05:00",
            "receipt_hash": "sha256:" + "c" * 64,
        }

    def test_persists_sealed_intr_packet_and_nonsecret_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            packet = self._intr_packet()
            receipt = self._intr_receipt()
            packet_path = store.append_intr_packet("intrpkt-test-001", packet)
            receipt_path = store.append_intr_receipt("intrpkt-test-001", receipt)
            self.assertEqual(packet_path, Path(tmp) / "_System" / "Execution" / "Extensions" / "intrpkt-test-001.jsonl")
            self.assertEqual(receipt_path, Path(tmp) / "_System" / "Execution" / "Receipts" / "intrpkt-test-001.jsonl")
            self.assertEqual(store.read_stream("Extensions", "intrpkt-test-001"), [packet])
            self.assertEqual(store.read_stream("Receipts", "intrpkt-test-001"), [receipt])

    def test_rejects_intr_plaintext_and_authority_escalation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)

            packet = self._intr_packet()
            packet["envelope"]["protected_payload"]["plaintext_present"] = True
            with self.assertRaises(VaultStoreError):
                store.append_intr_packet("bad-plaintext", packet)

            packet = self._intr_packet()
            packet["kv_decryption_authority"] = True
            with self.assertRaises(VaultStoreError):
                store.append_intr_packet("bad-kv-authority", packet)

            packet = self._intr_packet()
            packet["envelope"]["authority"]["authority_transfer"] = True
            with self.assertRaises(VaultStoreError):
                store.append_intr_packet("bad-transfer", packet)

            receipt = self._intr_receipt()
            receipt["secret_plaintext_present"] = True
            with self.assertRaises(VaultStoreError):
                store.append_intr_receipt("bad-receipt-plaintext", receipt)

            receipt = self._intr_receipt()
            receipt["authority_transfer"] = True
            with self.assertRaises(VaultStoreError):
                store.append_intr_receipt("bad-receipt-transfer", receipt)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest

from execution.adapter import canonical_sha256
from execution.vault_store import KnowledgeVaultExecutionStore, VaultStoreError
from skap.crypto_boundary import seal


class SkapKvPersistenceTests(unittest.TestCase):
    def make_bundle(self):
        sealed = seal(
            b"synthetic-coinbase-credential",
            root_key=b"k" * 32,
            object_id="skap://APIs/coinbase/test/v1",
            credential_version=1,
            wrapping_policy_ref="policy://skap/coinbase/advanced-trade",
            purpose="coinbase.permission_observation",
            endpoint_ref="https://api.coinbase.com",
            key_authority_ref="tvc://credential-root/test-only",
        ).envelope
        receipt = {
            "schema": "stegverse.skap.owner_credential_ingress_receipt/v1",
            "object_id": sealed["object_id"],
            "credential_version": sealed["credential_version"],
            "purpose": sealed["purpose"],
            "endpoint_ref": sealed["endpoint_ref"],
            "wrapping_policy_ref": sealed["wrapping_policy_ref"],
            "authorization_ref": "webauthn://stegverse.org/assertion/test",
            "source_class": "TRUSTED_INTERACTIVE_EDGE",
            "key_authority_ref": sealed["key_authority_ref"],
            "sealed_material_hash": canonical_sha256(sealed),
            "plaintext_length": len(b"synthetic-coinbase-credential"),
            "owner_authorized": True,
            "plaintext_persisted": False,
            "device_durable_secret_custody": False,
            "kv_decryption_authority": False,
            "model_secret_access": False,
            "authority_transfer": False,
            "ingressed_at": "2026-08-24T21:40:00-05:00",
        }
        return sealed, receipt

    def test_ciphertext_and_secret_free_receipt_round_trip_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            sealed, receipt = self.make_bundle()
            store.append_skap_sealed_credential("coinbase-test-v1", sealed, receipt)

            readback = store.read_skap_sealed_credential("coinbase-test-v1")
            self.assertEqual(readback, sealed)
            self.assertEqual(canonical_sha256(readback), canonical_sha256(sealed))

            serialized = json.dumps({
                "extensions": store.read_stream("Extensions", "coinbase-test-v1"),
                "receipts": store.read_stream("Receipts", "coinbase-test-v1"),
            }, sort_keys=True)
            self.assertNotIn("synthetic-coinbase-credential", serialized)
            self.assertNotIn("kkkkkkkk", serialized)
            self.assertIn(sealed["ciphertext_b64"], serialized)
            self.assertFalse(store.read_stream("Extensions", "coinbase-test-v1")[0]["kv_decryption_authority"])
            self.assertFalse(store.read_stream("Extensions", "coinbase-test-v1")[0]["kv_secret_resolution_authority"])

    def test_receipt_must_bind_exact_ciphertext(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            sealed, receipt = self.make_bundle()
            receipt["sealed_material_hash"] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(VaultStoreError, "sealed-material hash mismatch"):
                store.append_skap_sealed_credential("bad-hash", sealed, receipt)

    def test_kv_rejects_plaintext_key_or_authority_claims(self):
        mutations = [
            (lambda sealed, receipt: sealed.update(plaintext_persisted=True), "plaintext_persisted"),
            (lambda sealed, receipt: sealed.update(key_material_persisted=True), "key_material_persisted"),
            (lambda sealed, receipt: sealed.update(authority_transfer=True), "authority_transfer"),
            (lambda sealed, receipt: receipt.update(kv_decryption_authority=True), "kv_decryption_authority"),
            (lambda sealed, receipt: receipt.update(device_durable_secret_custody=True), "device_durable_secret_custody"),
        ]
        for mutate, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                store = KnowledgeVaultExecutionStore(tmp)
                sealed, receipt = self.make_bundle()
                mutate(sealed, receipt)
                if receipt.get("sealed_material_hash") != canonical_sha256(sealed):
                    receipt["sealed_material_hash"] = canonical_sha256(sealed)
                with self.assertRaisesRegex(VaultStoreError, expected):
                    store.append_skap_sealed_credential("bad-boundary", sealed, receipt)

    def test_stored_record_tamper_is_detected_before_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeVaultExecutionStore(tmp)
            sealed, receipt = self.make_bundle()
            extension_path, _ = store.append_skap_sealed_credential("tamper-test", sealed, receipt)
            text = extension_path.read_text(encoding="utf-8")
            text = text.replace(sealed["ciphertext_b64"], "A" + sealed["ciphertext_b64"][1:])
            extension_path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(VaultStoreError, "hash verification"):
                store.read_skap_sealed_credential("tamper-test")


if __name__ == "__main__":
    unittest.main()

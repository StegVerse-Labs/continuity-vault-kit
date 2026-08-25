import json
import unittest

from skap.ingress import SKAPIngressError, ingest_owner_credential


class MemoryProvider:
    def __init__(self):
        self._key = bytearray(b"R" * 32)
        self.calls = 0

    @property
    def authority_ref(self):
        return "tvc-resident://SKAP_ROOT_KEY_TEST"

    def with_key(self, consumer):
        self.calls += 1
        scratch = bytearray(self._key)
        try:
            return consumer(memoryview(scratch))
        finally:
            for i in range(len(scratch)):
                scratch[i] = 0


class OwnerIngressTests(unittest.TestCase):
    def setUp(self):
        self.provider = MemoryProvider()
        self.common = dict(
            owner_authorized=True,
            authorization_ref="owner-auth://synthetic-test",
            key_provider=self.provider,
            object_id="skap://APIs/coinbase/test-only",
            credential_version=1,
            wrapping_policy_ref="policy://skap/coinbase/read-only",
            purpose="coinbase.permission_observation",
            endpoint_ref="endpoint://coinbase/api",
            observed_at="2026-08-24T21:30:00Z",
        )

    def test_ingress_wipes_input_and_returns_only_sealed_material_and_receipt(self):
        plaintext = bytearray(b"synthetic-owner-credential")
        original = bytes(plaintext)
        sealed, receipt = ingest_owner_credential(plaintext, **self.common)
        self.assertEqual(bytes(plaintext), b"\x00" * len(original))
        combined = json.dumps({"sealed": sealed.envelope, "receipt": receipt}, sort_keys=True)
        self.assertNotIn(original.decode("ascii"), combined)
        self.assertFalse(receipt["plaintext_persisted"])
        self.assertFalse(receipt["device_durable_secret_custody"])
        self.assertFalse(receipt["kv_decryption_authority"])
        self.assertFalse(receipt["model_secret_access"])
        self.assertFalse(receipt["authority_transfer"])
        self.assertTrue(receipt["owner_authorized"])
        self.assertEqual(receipt["key_authority_ref"], self.provider.authority_ref)
        self.assertEqual(receipt["sealed_material_hash"], sealed.sealed_material_hash)
        self.assertEqual(self.provider.calls, 1)

    def test_missing_owner_authorization_fails_before_provider_use(self):
        plaintext = bytearray(b"synthetic")
        args = dict(self.common); args["owner_authorized"] = False
        with self.assertRaisesRegex(SKAPIngressError, "owner authorization"):
            ingest_owner_credential(plaintext, **args)
        self.assertEqual(self.provider.calls, 0)

    def test_missing_authorization_reference_fails(self):
        args = dict(self.common); args["authorization_ref"] = ""
        with self.assertRaisesRegex(SKAPIngressError, "authorization reference"):
            ingest_owner_credential(bytearray(b"synthetic"), **args)

    def test_noninteractive_source_fails_closed(self):
        for source in ("ARGV", "ENVIRONMENT", "FILE", "NETWORK", "MODEL_OUTPUT"):
            args = dict(self.common); args["source_class"] = source
            with self.subTest(source=source), self.assertRaisesRegex(SKAPIngressError, "TRUSTED_INTERACTIVE_EDGE"):
                ingest_owner_credential(bytearray(b"synthetic"), **args)

    def test_immutable_inputs_rejected(self):
        for value in (b"synthetic", "synthetic"):
            with self.subTest(kind=type(value).__name__), self.assertRaisesRegex(SKAPIngressError, "mutable bytearray"):
                ingest_owner_credential(value, **self.common)  # type: ignore[arg-type]

    def test_empty_input_rejected(self):
        with self.assertRaisesRegex(SKAPIngressError, "must not be empty"):
            ingest_owner_credential(bytearray(), **self.common)


if __name__ == "__main__":
    unittest.main()

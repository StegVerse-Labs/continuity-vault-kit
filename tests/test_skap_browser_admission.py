import unittest

from cryptography.hazmat.primitives.asymmetric import ec

from skap.browser_admission import BrowserAdmissionError, admit_browser_envelope
from skap.browser_ingress import public_jwk_from_private, seal_for_recipient
from skap.crypto_boundary import resolve_transiently


class RecipientProvider:
    def __init__(self, key_id, private_key):
        self._key_id = key_id
        self._private_key = private_key
        self.calls = 0

    @property
    def key_id(self):
        return self._key_id

    def with_private_key(self, consumer):
        self.calls += 1
        return consumer(self._private_key)


class RootKeyProvider:
    authority_ref = "tvc://skap/root/coinbase/v1"

    def __init__(self):
        self.key = bytearray(b"R" * 32)
        self.calls = 0

    def with_key(self, consumer):
        self.calls += 1
        temporary = bytearray(self.key)
        try:
            return consumer(memoryview(temporary))
        finally:
            temporary[:] = b"\x00" * len(temporary)


class BrowserAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.private = ec.generate_private_key(ec.SECP256R1())
        self.recipient = RecipientProvider("tvc://skap/browser-ingress/coinbase/v1", self.private)
        self.root = RootKeyProvider()
        self.object_id = "skap://APIs/coinbase/owner/1"
        self.browser_policy = "policy://skap/coinbase/browser-ingress"
        self.canonical_policy = "policy://skap/coinbase/advanced-trade"
        self.purpose = "coinbase.permission_observation"
        self.endpoint = "https://api.coinbase.com"

    def browser_envelope(self, plaintext=b"synthetic-coinbase-browser-secret"):
        mutable = bytearray(plaintext)
        envelope = seal_for_recipient(
            mutable,
            recipient_public_jwk=public_jwk_from_private(self.private),
            recipient_key_id=self.recipient.key_id,
            object_id=self.object_id,
            credential_version=1,
            wrapping_policy_ref=self.browser_policy,
            purpose=self.purpose,
            endpoint_ref=self.endpoint,
        ).envelope
        self.assertEqual(mutable, bytearray(len(mutable)))
        return envelope

    def test_browser_ciphertext_is_resealed_into_canonical_skap(self):
        canonical = admit_browser_envelope(
            self.browser_envelope(),
            recipient_key_provider=self.recipient,
            canonical_key_provider=self.root,
            object_id=self.object_id,
            credential_version=1,
            browser_wrapping_policy_ref=self.browser_policy,
            canonical_wrapping_policy_ref=self.canonical_policy,
            purpose=self.purpose,
            endpoint_ref=self.endpoint,
        )
        self.assertEqual(canonical["format"], "stegverse.skap.sealed_material/aes256gcm-hkdf-sha256/v1")
        self.assertEqual(canonical["key_authority_ref"], self.root.authority_ref)
        self.assertFalse(canonical["plaintext_persisted"])
        self.assertFalse(canonical["key_material_persisted"])
        self.assertFalse(canonical["authority_transfer"])
        self.assertEqual(self.recipient.calls, 1)
        self.assertEqual(self.root.calls, 1)

        observed = {}
        resolve_transiently(
            canonical,
            root_key=self.root.key,
            expected_object_id=self.object_id,
            expected_credential_version=1,
            expected_wrapping_policy_ref=self.canonical_policy,
            expected_purpose=self.purpose,
            expected_endpoint_ref=self.endpoint,
            expected_key_authority_ref=self.root.authority_ref,
            consumer=lambda view: observed.setdefault("plaintext", bytes(view)),
        )
        self.assertEqual(observed["plaintext"], b"synthetic-coinbase-browser-secret")

    def test_wrong_browser_recipient_key_fails_before_canonical_seal(self):
        wrong = RecipientProvider(self.recipient.key_id, ec.generate_private_key(ec.SECP256R1()))
        with self.assertRaises(Exception):
            admit_browser_envelope(
                self.browser_envelope(),
                recipient_key_provider=wrong,
                canonical_key_provider=self.root,
                object_id=self.object_id,
                credential_version=1,
                browser_wrapping_policy_ref=self.browser_policy,
                canonical_wrapping_policy_ref=self.canonical_policy,
                purpose=self.purpose,
                endpoint_ref=self.endpoint,
            )
        self.assertEqual(self.root.calls, 0)

    def test_recipient_key_authority_substitution_fails_closed(self):
        bad = RecipientProvider("tvc://skap/browser-ingress/other/v1", self.private)
        with self.assertRaisesRegex(BrowserAdmissionError, "recipient key authority invalid"):
            admit_browser_envelope(
                self.browser_envelope(),
                recipient_key_provider=bad,
                canonical_key_provider=self.root,
                object_id=self.object_id,
                credential_version=1,
                browser_wrapping_policy_ref=self.browser_policy,
                canonical_wrapping_policy_ref=self.canonical_policy,
                purpose=self.purpose,
                endpoint_ref=self.endpoint,
            )

    def test_endpoint_substitution_fails_before_key_provider_use(self):
        with self.assertRaisesRegex(BrowserAdmissionError, "exact Coinbase origin"):
            admit_browser_envelope(
                self.browser_envelope(),
                recipient_key_provider=self.recipient,
                canonical_key_provider=self.root,
                object_id=self.object_id,
                credential_version=1,
                browser_wrapping_policy_ref=self.browser_policy,
                canonical_wrapping_policy_ref=self.canonical_policy,
                purpose=self.purpose,
                endpoint_ref="https://attacker.example",
            )
        self.assertEqual(self.recipient.calls, 0)
        self.assertEqual(self.root.calls, 0)

    def test_browser_context_substitution_fails_without_canonical_output(self):
        envelope = self.browser_envelope()
        envelope["purpose"] = "coinbase.advanced_trade"
        with self.assertRaises(Exception):
            admit_browser_envelope(
                envelope,
                recipient_key_provider=self.recipient,
                canonical_key_provider=self.root,
                object_id=self.object_id,
                credential_version=1,
                browser_wrapping_policy_ref=self.browser_policy,
                canonical_wrapping_policy_ref=self.canonical_policy,
                purpose=self.purpose,
                endpoint_ref=self.endpoint,
            )
        self.assertEqual(self.root.calls, 0)


if __name__ == "__main__":
    unittest.main()

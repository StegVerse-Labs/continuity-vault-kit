import copy
import json
import unittest

from cryptography.hazmat.primitives.asymmetric import ec

from skap.browser_ingress import (
    BrowserIngressError,
    public_jwk_from_private,
    resolve_at_skap,
    seal_for_recipient,
)


class BrowserIngressTests(unittest.TestCase):
    def setUp(self):
        self.private = ec.generate_private_key(ec.SECP256R1())
        self.public_jwk = public_jwk_from_private(self.private)
        self.kw = {
            "recipient_key_id": "tvc://skap/browser-ingress/coinbase/v1",
            "object_id": "skap://APIs/coinbase/owner/v1",
            "credential_version": 1,
            "wrapping_policy_ref": "policy://skap/coinbase/browser-ingress",
            "purpose": "coinbase.permission_observation",
            "endpoint_ref": "https://api.coinbase.com",
        }

    def seal(self):
        plaintext = bytearray(b"synthetic-browser-coinbase-secret")
        envelope = seal_for_recipient(
            plaintext,
            recipient_public_jwk=self.public_jwk,
            **self.kw,
        ).envelope
        self.assertEqual(plaintext, bytearray(len(plaintext)))
        return envelope

    def resolve(self, envelope, private=None, overrides=None):
        observed = {}
        args = {
            "recipient_private_key": private or self.private,
            "expected_recipient_key_id": self.kw["recipient_key_id"],
            "expected_object_id": self.kw["object_id"],
            "expected_credential_version": self.kw["credential_version"],
            "expected_wrapping_policy_ref": self.kw["wrapping_policy_ref"],
            "expected_purpose": self.kw["purpose"],
            "expected_endpoint_ref": self.kw["endpoint_ref"],
        }
        args.update(overrides or {})
        result = resolve_at_skap(
            envelope,
            consumer=lambda view: observed.setdefault("plaintext", bytes(view)) or "USED",
            **args,
        )
        return result, observed

    def test_browser_receives_public_key_only_and_ciphertext_round_trips(self):
        envelope = self.seal()
        serialized = json.dumps(envelope, sort_keys=True)
        self.assertNotIn("synthetic-browser-coinbase-secret", serialized)
        self.assertNotIn("private", serialized.lower())
        self.assertFalse(envelope["plaintext_persisted"])
        self.assertFalse(envelope["device_private_key_persisted"])
        self.assertFalse(envelope["skap_private_key_exported"])
        self.assertFalse(envelope["authority_transfer"])
        _, observed = self.resolve(envelope)
        self.assertEqual(observed["plaintext"], b"synthetic-browser-coinbase-secret")

    def test_wrong_skap_private_key_fails_closed(self):
        envelope = self.seal()
        wrong = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(BrowserIngressError):
            self.resolve(envelope, private=wrong)

    def test_endpoint_substitution_fails_before_decrypt(self):
        envelope = self.seal()
        with self.assertRaisesRegex(BrowserIngressError, "endpoint_ref binding mismatch"):
            self.resolve(envelope, overrides={"expected_endpoint_ref": "https://attacker.example"})

    def test_recipient_key_substitution_fails_before_decrypt(self):
        envelope = self.seal()
        with self.assertRaisesRegex(BrowserIngressError, "recipient_key_id binding mismatch"):
            self.resolve(envelope, overrides={"expected_recipient_key_id": "tvc://skap/browser-ingress/other"})

    def test_ciphertext_tamper_fails_closed(self):
        envelope = copy.deepcopy(self.seal())
        ciphertext = envelope["ciphertext_b64"]
        envelope["ciphertext_b64"] = ("A" if ciphertext[0] != "A" else "B") + ciphertext[1:]
        with self.assertRaises(BrowserIngressError):
            self.resolve(envelope)

    def test_authority_or_persistence_claim_fails_closed(self):
        for field in ("plaintext_persisted", "device_private_key_persisted", "skap_private_key_exported", "authority_transfer"):
            envelope = copy.deepcopy(self.seal())
            envelope[field] = True
            with self.subTest(field=field), self.assertRaises(BrowserIngressError):
                self.resolve(envelope)

    def test_non_coinbase_destination_rejected_at_seal(self):
        plaintext = bytearray(b"synthetic")
        with self.assertRaisesRegex(BrowserIngressError, "exact Coinbase origin"):
            seal_for_recipient(
                plaintext,
                recipient_public_jwk=self.public_jwk,
                **{**self.kw, "endpoint_ref": "https://attacker.example"},
            )


if __name__ == "__main__":
    unittest.main()

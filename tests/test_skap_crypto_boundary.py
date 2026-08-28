import copy
import json
import os
import unittest

from skap.crypto_boundary import (
    SKAPCryptoError,
    resolve_granted_transiently,
    resolve_transiently,
    seal,
)


class SKAPCryptoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.root_key = bytes(range(32))
        self.kw = {
            "object_id": "skap://APIs/provider/example",
            "credential_version": 1,
            "wrapping_policy_ref": "policy://skap/provider/example",
            "purpose": "provider.readiness",
            "endpoint_ref": "endpoint://provider/example",
            "key_authority_ref": "tvc://credential-root/test-only",
        }

    def _seal(self, value=b"synthetic-non-production-secret"):
        return seal(value, root_key=self.root_key, **self.kw).envelope

    def _resolve(self, envelope, *, root_key=None, overrides=None):
        args = dict(
            root_key=self.root_key if root_key is None else root_key,
            expected_object_id=self.kw["object_id"],
            expected_credential_version=self.kw["credential_version"],
            expected_wrapping_policy_ref=self.kw["wrapping_policy_ref"],
            expected_purpose=self.kw["purpose"],
            expected_endpoint_ref=self.kw["endpoint_ref"],
            expected_key_authority_ref=self.kw["key_authority_ref"],
        )
        args.update(overrides or {})
        observed = {}

        def consumer(view):
            observed["value"] = bytes(view)
            return "USED_TRANSIENTLY"

        result = resolve_transiently(envelope, consumer=consumer, **args)
        return result, observed

    def _grant(self, *, version=1, state="ACTIVE", revoked=False, consumed=False):
        return {
            "object_id": self.kw["object_id"],
            "credential_version": version,
            "purpose": self.kw["purpose"],
            "endpoint_ref": self.kw["endpoint_ref"],
            "state": state,
            "revoked": revoked,
            "consumed": consumed,
        }

    def _resolve_grant(self, envelope, grant, *, lifecycle_state="ACTIVE", current_version=1, revocation_check=True):
        observed = {}

        def consumer(view):
            observed["value"] = bytes(view)
            return "USED_GRANTED_TRANSIENTLY"

        result = resolve_granted_transiently(
            envelope,
            root_key=self.root_key,
            lifecycle_state=lifecycle_state,
            current_credential_version=current_version,
            grant=grant,
            revocation_check_passed=revocation_check,
            expected_object_id=self.kw["object_id"],
            expected_wrapping_policy_ref=self.kw["wrapping_policy_ref"],
            expected_key_authority_ref=self.kw["key_authority_ref"],
            consumer=consumer,
        )
        return result, observed

    def test_round_trip_is_ciphertext_only_and_callback_only(self):
        envelope = self._seal()
        encoded = json.dumps(envelope, sort_keys=True)
        self.assertNotIn("synthetic-non-production-secret", encoded)
        self.assertFalse(envelope["plaintext_persisted"])
        self.assertFalse(envelope["key_material_persisted"])
        self.assertFalse(envelope["authority_transfer"])
        result, observed = self._resolve(envelope)
        self.assertEqual(result, "USED_TRANSIENTLY")
        self.assertEqual(observed["value"], b"synthetic-non-production-secret")

    def test_wrong_root_key_fails_closed(self):
        envelope = self._seal()
        with self.assertRaises(SKAPCryptoError):
            self._resolve(envelope, root_key=os.urandom(32))

    def test_ciphertext_tamper_fails_closed(self):
        envelope = copy.deepcopy(self._seal())
        envelope["ciphertext_b64"] = ("A" if envelope["ciphertext_b64"][0] != "A" else "B") + envelope["ciphertext_b64"][1:]
        with self.assertRaises(SKAPCryptoError):
            self._resolve(envelope)

    def test_endpoint_substitution_fails_before_decrypt(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "endpoint_ref binding mismatch"):
            self._resolve(envelope, overrides={"expected_endpoint_ref": "endpoint://attacker/substitute"})

    def test_purpose_substitution_fails_before_decrypt(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "purpose binding mismatch"):
            self._resolve(envelope, overrides={"expected_purpose": "provider.write"})

    def test_version_substitution_fails_before_decrypt(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "credential_version binding mismatch"):
            self._resolve(envelope, overrides={"expected_credential_version": 2})

    def test_key_authority_substitution_fails_closed(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "key authority mismatch"):
            self._resolve(envelope, overrides={"expected_key_authority_ref": "caller://unauthorized"})

    def test_persistence_or_authority_claim_fails_closed(self):
        for field in ("plaintext_persisted", "key_material_persisted", "authority_transfer"):
            envelope = copy.deepcopy(self._seal())
            envelope[field] = True
            with self.subTest(field=field), self.assertRaises(SKAPCryptoError):
                self._resolve(envelope)

    def test_root_key_shorter_than_256_bits_rejected(self):
        with self.assertRaisesRegex(SKAPCryptoError, "256 bits"):
            seal(b"x", root_key=b"short", **self.kw)

    def test_active_current_grant_resolves_only_after_immediate_revocation_check(self):
        envelope = self._seal()
        result, observed = self._resolve_grant(envelope, self._grant())
        self.assertEqual(result, "USED_GRANTED_TRANSIENTLY")
        self.assertEqual(observed["value"], b"synthetic-non-production-secret")
        with self.assertRaisesRegex(SKAPCryptoError, "revocation check"):
            self._resolve_grant(envelope, self._grant(), revocation_check=False)

    def test_rotation_invalidates_outstanding_old_version_grant(self):
        envelope = self._seal()
        old_grant = self._grant(version=1)
        with self.assertRaisesRegex(SKAPCryptoError, "lifecycle ROTATED blocks resolution"):
            self._resolve_grant(envelope, old_grant, lifecycle_state="ROTATED", current_version=2)
        with self.assertRaisesRegex(SKAPCryptoError, "stale or mismatched"):
            self._resolve_grant(envelope, old_grant, lifecycle_state="ACTIVE", current_version=2)

    def test_revocation_blocks_outstanding_grant(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "lifecycle REVOKED blocks resolution"):
            self._resolve_grant(envelope, self._grant(), lifecycle_state="REVOKED", current_version=1)
        with self.assertRaisesRegex(SKAPCryptoError, "grant is revoked"):
            self._resolve_grant(envelope, self._grant(revoked=True))

    def test_consumed_grant_cannot_be_replayed(self):
        envelope = self._seal()
        with self.assertRaisesRegex(SKAPCryptoError, "already been consumed"):
            self._resolve_grant(envelope, self._grant(consumed=True))


if __name__ == "__main__":
    unittest.main()

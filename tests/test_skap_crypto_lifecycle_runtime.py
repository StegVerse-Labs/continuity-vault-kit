import unittest

from skap.crypto_boundary import SKAPCryptoError, resolve_granted_transiently, seal


class SKAPCryptoLifecycleRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root_key = bytes(range(32))
        self.object_id = "skap://APIs/coinbase/test-only"
        self.policy = "policy://skap/coinbase/read-only"
        self.endpoint = "endpoint://coinbase/api"
        self.authority = "tvc://credential-root/test-only"
        self.purpose = "coinbase.permission_observation"

    def _seal(self, version, value):
        return seal(
            value,
            root_key=self.root_key,
            object_id=self.object_id,
            credential_version=version,
            wrapping_policy_ref=self.policy,
            purpose=self.purpose,
            endpoint_ref=self.endpoint,
            key_authority_ref=self.authority,
        ).envelope

    def _grant(self, version):
        return {
            "grant_id": f"grant-v{version}",
            "object_id": self.object_id,
            "credential_version": version,
            "purpose": self.purpose,
            "endpoint_ref": self.endpoint,
            "state": "ACTIVE",
            "revoked": False,
            "consumed": False,
        }

    def _resolve(self, sealed, *, lifecycle_state, current_version, grant, revocation_check=True):
        observed = []
        result = resolve_granted_transiently(
            sealed,
            root_key=self.root_key,
            lifecycle_state=lifecycle_state,
            current_credential_version=current_version,
            grant=grant,
            revocation_check_passed=revocation_check,
            expected_object_id=self.object_id,
            expected_wrapping_policy_ref=self.policy,
            expected_key_authority_ref=self.authority,
            consumer=lambda view: observed.append(bytes(view)) or "USED",
        )
        return result, observed

    def test_rotation_invalidates_old_ciphertext_and_grant(self):
        v1 = self._seal(1, b"synthetic-v1")
        grant_v1 = self._grant(1)
        result, observed = self._resolve(v1, lifecycle_state="ACTIVE", current_version=1, grant=grant_v1)
        self.assertEqual(result, "USED")
        self.assertEqual(observed, [b"synthetic-v1"])

        # Rotation advances canonical state to version 2. Old ciphertext + old grant
        # remain physically possessable but must no longer reach decryption.
        with self.assertRaisesRegex(SKAPCryptoError, "credential lifecycle ROTATED blocks resolution"):
            self._resolve(v1, lifecycle_state="ROTATED", current_version=2, grant=grant_v1)

        v2 = self._seal(2, b"synthetic-v2")
        grant_v2 = self._grant(2)
        result, observed = self._resolve(v2, lifecycle_state="ACTIVE", current_version=2, grant=grant_v2)
        self.assertEqual(result, "USED")
        self.assertEqual(observed, [b"synthetic-v2"])

        # Even if an attacker falsely labels the old object ACTIVE, version binding
        # still rejects the stale grant/ciphertext pair.
        with self.assertRaises(SKAPCryptoError):
            self._resolve(v1, lifecycle_state="ACTIVE", current_version=2, grant=grant_v1)

    def test_revocation_blocks_current_ciphertext_and_grant(self):
        v2 = self._seal(2, b"synthetic-v2")
        grant_v2 = self._grant(2)
        self._resolve(v2, lifecycle_state="ACTIVE", current_version=2, grant=grant_v2)

        with self.assertRaisesRegex(SKAPCryptoError, "credential lifecycle REVOKED blocks resolution"):
            self._resolve(v2, lifecycle_state="REVOKED", current_version=2, grant=grant_v2)

        revoked_grant = self._grant(2)
        revoked_grant["revoked"] = True
        with self.assertRaisesRegex(SKAPCryptoError, "grant is revoked"):
            self._resolve(v2, lifecycle_state="ACTIVE", current_version=2, grant=revoked_grant)

    def test_failed_immediate_revocation_check_fails_closed(self):
        v1 = self._seal(1, b"synthetic-v1")
        with self.assertRaisesRegex(SKAPCryptoError, "immediate revocation check did not pass"):
            self._resolve(v1, lifecycle_state="ACTIVE", current_version=1, grant=self._grant(1), revocation_check=False)

    def test_consumed_grant_cannot_be_reused(self):
        v1 = self._seal(1, b"synthetic-v1")
        grant = self._grant(1)
        grant["consumed"] = True
        with self.assertRaisesRegex(SKAPCryptoError, "already been consumed"):
            self._resolve(v1, lifecycle_state="ACTIVE", current_version=1, grant=grant)


if __name__ == "__main__":
    unittest.main()

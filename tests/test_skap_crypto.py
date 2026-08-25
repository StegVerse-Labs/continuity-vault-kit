import unittest

from execution.skap_crypto import SkapCryptoVault, SkapResolutionError


ENDPOINT = "https://api.coinbase.com"
PURPOSE = "coinbase_advanced_trade"


class SkapCryptoVaultTests(unittest.TestCase):
    def make_active(self):
        vault = SkapCryptoVault(wrapping_key=b"k" * 32)
        metadata = vault.seal(
            b"synthetic-coinbase-secret-v1",
            object_id="skap://coinbase/test/v1",
            provider="coinbase",
            allowed_purposes=[PURPOSE],
            allowed_endpoint_refs=[ENDPOINT],
        )
        self.assertEqual(metadata["lifecycle_state"], "SEALED")
        active = vault.activate(metadata["object_id"])
        self.assertEqual(active["lifecycle_state"], "ACTIVE")
        return vault, active

    def test_seal_metadata_contains_no_plaintext_or_wrapping_key(self):
        vault, active = self.make_active()
        state = vault.export_non_secret_state()
        encoded = repr(state)
        self.assertNotIn("synthetic-coinbase-secret-v1", encoded)
        self.assertNotIn("kkkkkkkk", encoded)
        self.assertFalse(state["plaintext_persisted"])
        self.assertFalse(state["wrapping_key_exported"])
        self.assertFalse(state["sealed_blob_exported"])
        self.assertFalse(active["kv_decryption_authority"])
        self.assertFalse(active["device_secret_custody_authority"])
        self.assertFalse(active["model_secret_access"])

    def test_resolution_requires_verified_exact_endpoint_and_fresh_revocation_check(self):
        vault, active = self.make_active()
        grant = vault.issue_grant(active["object_id"], purpose=PURPOSE, endpoint_ref=ENDPOINT)
        plaintext = vault.resolve_transient(
            grant,
            endpoint_ref=ENDPOINT,
            endpoint_session_verified=True,
            revocation_rechecked_immediately_before_resolution=True,
        )
        self.assertEqual(plaintext, b"synthetic-coinbase-secret-v1")

        with self.assertRaisesRegex(SkapResolutionError, "endpoint_mismatch"):
            vault.resolve_transient(
                grant,
                endpoint_ref="https://evil.example",
                endpoint_session_verified=True,
                revocation_rechecked_immediately_before_resolution=True,
            )
        with self.assertRaisesRegex(SkapResolutionError, "endpoint_session_not_verified"):
            vault.resolve_transient(
                grant,
                endpoint_ref=ENDPOINT,
                endpoint_session_verified=False,
                revocation_rechecked_immediately_before_resolution=True,
            )
        with self.assertRaisesRegex(SkapResolutionError, "revocation_not_rechecked"):
            vault.resolve_transient(
                grant,
                endpoint_ref=ENDPOINT,
                endpoint_session_verified=True,
                revocation_rechecked_immediately_before_resolution=False,
            )

    def test_rotation_invalidates_old_grant_and_new_version_can_activate(self):
        vault, active = self.make_active()
        old_grant = vault.issue_grant(active["object_id"], purpose=PURPOSE, endpoint_ref=ENDPOINT)
        rotated_old, replacement = vault.rotate(
            active["object_id"],
            replacement_object_id="skap://coinbase/test/v2",
            new_plaintext=b"synthetic-coinbase-secret-v2",
        )
        self.assertEqual(rotated_old["lifecycle_state"], "ROTATED")
        self.assertEqual(replacement["credential_version"], 2)
        with self.assertRaises(SkapResolutionError):
            vault.resolve_transient(
                old_grant,
                endpoint_ref=ENDPOINT,
                endpoint_session_verified=True,
                revocation_rechecked_immediately_before_resolution=True,
            )

        replacement = vault.activate(replacement["object_id"])
        new_grant = vault.issue_grant(replacement["object_id"], purpose=PURPOSE, endpoint_ref=ENDPOINT)
        self.assertEqual(
            vault.resolve_transient(
                new_grant,
                endpoint_ref=ENDPOINT,
                endpoint_session_verified=True,
                revocation_rechecked_immediately_before_resolution=True,
            ),
            b"synthetic-coinbase-secret-v2",
        )

    def test_revocation_blocks_existing_and_new_grants(self):
        vault, active = self.make_active()
        grant = vault.issue_grant(active["object_id"], purpose=PURPOSE, endpoint_ref=ENDPOINT)
        revoked = vault.revoke(active["object_id"])
        self.assertEqual(revoked["lifecycle_state"], "REVOKED")
        with self.assertRaises(SkapResolutionError):
            vault.resolve_transient(
                grant,
                endpoint_ref=ENDPOINT,
                endpoint_session_verified=True,
                revocation_rechecked_immediately_before_resolution=True,
            )
        with self.assertRaisesRegex(SkapResolutionError, "NO_NEW_GRANTS"):
            vault.issue_grant(active["object_id"], purpose=PURPOSE, endpoint_ref=ENDPOINT)


if __name__ == "__main__":
    unittest.main()

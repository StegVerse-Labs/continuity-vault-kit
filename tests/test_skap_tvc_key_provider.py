import os
import stat
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from skap.crypto_boundary import SKAPCryptoError, resolve_granted_with_provider, seal_with_provider
from skap.key_provider import SKAPKeyProviderError, TVCResidentFileKeyProvider, validate_tvc_ephemeral_key_path


class MemoryProvider:
    def __init__(self, key=b"K" * 32, authority_ref="tvc-resident://SKAP_ROOT_KEY_TEST"):
        self._key = bytearray(key)
        self._authority_ref = authority_ref
        self.calls = 0

    @property
    def authority_ref(self):
        return self._authority_ref

    def with_key(self, consumer):
        self.calls += 1
        scratch = bytearray(self._key)
        try:
            return consumer(memoryview(scratch))
        finally:
            for i in range(len(scratch)):
                scratch[i] = 0


class TVCKeyProviderTests(unittest.TestCase):
    def test_path_must_remain_under_tvc_ephemeral_root(self):
        accepted = validate_tvc_ephemeral_key_path("/run/stegverse/tv-tvc-credentials/SKAP_ROOT_KEY")
        self.assertEqual(str(accepted), "/run/stegverse/tv-tvc-credentials/SKAP_ROOT_KEY")
        for invalid in ("relative/key", "/tmp/SKAP_ROOT_KEY", "/run/stegverse/not-authoritative/key"):
            with self.subTest(invalid=invalid), self.assertRaises(SKAPKeyProviderError):
                validate_tvc_ephemeral_key_path(invalid)

    def test_resident_provider_rejects_non_root_owned_or_loose_permissions(self):
        provider = TVCResidentFileKeyProvider("/run/stegverse/tv-tvc-credentials/SKAP_ROOT_KEY")
        base = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=0)
        with patch("os.open", return_value=9), patch("os.close"), patch("os.read", return_value=b"K" * 32):
            with patch("os.fstat", return_value=SimpleNamespace(st_mode=base.st_mode, st_uid=1000)):
                with self.assertRaisesRegex(SKAPKeyProviderError, "root-owned"):
                    provider.with_key(lambda _: True)
            with patch("os.fstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG | 0o640, st_uid=0)):
                with self.assertRaisesRegex(SKAPKeyProviderError, "group/world"):
                    provider.with_key(lambda _: True)

    def test_resident_provider_requires_exact_256_bit_key(self):
        provider = TVCResidentFileKeyProvider("/run/stegverse/tv-tvc-credentials/SKAP_ROOT_KEY")
        meta = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=0)
        with patch("os.open", return_value=9), patch("os.close"), patch("os.fstat", return_value=meta), patch("os.read", return_value=b"K" * 31):
            with self.assertRaisesRegex(SKAPKeyProviderError, "exactly 256 bits"):
                provider.with_key(lambda _: True)

    def test_provider_api_seals_and_resolves_without_raw_key_argument(self):
        provider = MemoryProvider()
        sealed = seal_with_provider(
            b"synthetic-owner-ingress",
            key_provider=provider,
            object_id="skap://APIs/coinbase/test-only",
            credential_version=1,
            wrapping_policy_ref="policy://skap/coinbase/read-only",
            purpose="coinbase.permission_observation",
            endpoint_ref="endpoint://coinbase/api",
        ).envelope
        self.assertEqual(sealed["key_authority_ref"], provider.authority_ref)
        grant = {
            "object_id": "skap://APIs/coinbase/test-only",
            "credential_version": 1,
            "purpose": "coinbase.permission_observation",
            "endpoint_ref": "endpoint://coinbase/api",
            "state": "ACTIVE",
            "revoked": False,
            "consumed": False,
        }
        seen = []
        result = resolve_granted_with_provider(
            sealed,
            key_provider=provider,
            lifecycle_state="ACTIVE",
            current_credential_version=1,
            grant=grant,
            revocation_check_passed=True,
            expected_object_id=grant["object_id"],
            expected_wrapping_policy_ref="policy://skap/coinbase/read-only",
            consumer=lambda view: seen.append(bytes(view)) or "SUBMITTED_TRANSIENTLY",
        )
        self.assertEqual(result, "SUBMITTED_TRANSIENTLY")
        self.assertEqual(seen, [b"synthetic-owner-ingress"])
        self.assertEqual(provider.calls, 2)

    def test_provider_authority_substitution_fails_closed(self):
        original = MemoryProvider(authority_ref="tvc-resident://SKAP_ROOT_KEY_A")
        sealed = seal_with_provider(
            b"synthetic",
            key_provider=original,
            object_id="skap://APIs/coinbase/test-only",
            credential_version=1,
            wrapping_policy_ref="policy://skap/coinbase/read-only",
            purpose="coinbase.permission_observation",
            endpoint_ref="endpoint://coinbase/api",
        ).envelope
        substituted = MemoryProvider(key=b"K" * 32, authority_ref="tvc-resident://SKAP_ROOT_KEY_B")
        grant = {
            "object_id": "skap://APIs/coinbase/test-only",
            "credential_version": 1,
            "purpose": "coinbase.permission_observation",
            "endpoint_ref": "endpoint://coinbase/api",
            "state": "ACTIVE",
            "revoked": False,
            "consumed": False,
        }
        with self.assertRaisesRegex(SKAPCryptoError, "key authority mismatch"):
            resolve_granted_with_provider(
                sealed,
                key_provider=substituted,
                lifecycle_state="ACTIVE",
                current_credential_version=1,
                grant=grant,
                revocation_check_passed=True,
                expected_object_id=grant["object_id"],
                expected_wrapping_policy_ref="policy://skap/coinbase/read-only",
                consumer=lambda _: None,
            )


if __name__ == "__main__":
    unittest.main()

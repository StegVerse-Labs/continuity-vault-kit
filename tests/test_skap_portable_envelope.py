"""Portable wrapped-root envelope (SKAP layout v2) reference tests.

All keys, secrets, salts, nonces and credential strings used here are either fixed,
publicly known TEST VECTORS from fixtures/skap/portable-envelope-v2.vectors.json or
fresh random bytes generated for the test run. None is real recovery material.
"""

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

from skap import portable_envelope as pe
from skap.crypto_boundary import SKAPCryptoError, resolve_transiently, seal, seal_with_provider
from skap.key_provider import TVCResidentFileKeyProvider

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "fixtures/skap/portable-envelope-v2.vectors.json").read_text(encoding="utf-8"))
LAYOUT_V1 = json.loads((ROOT / "specs/skap-kv-storage-layout.v1.json").read_text(encoding="utf-8"))
LAYOUT_V2 = json.loads((ROOT / "specs/skap-kv-storage-layout.v2.json").read_text(encoding="utf-8"))


def _h(value):
    return bytes.fromhex(value)


def _open(sealed, root_key, bindings):
    return resolve_transiently(
        sealed,
        root_key=root_key,
        expected_object_id=bindings["object_id"],
        expected_credential_version=bindings["credential_version"],
        expected_wrapping_policy_ref=bindings["wrapping_policy_ref"],
        expected_purpose=bindings["purpose"],
        expected_endpoint_ref=bindings["endpoint_ref"],
        expected_key_authority_ref=bindings["key_authority_ref"],
        consumer=lambda view: bytes(view),
    )


class LayoutV2Tests(unittest.TestCase):
    def test_v2_supersedes_v1_and_preserves_boundaries(self):
        self.assertEqual(LAYOUT_V1["schema"], "stegverse.skap.kv-storage-layout/v1")
        sup = LAYOUT_V2["supersession"]
        self.assertEqual(sup["supersedes"], "specs/skap-kv-storage-layout.v1.json")
        self.assertEqual(sup["owning_goal"], "TVC-CREDENTIAL-MODEL-CONSISTENCY-20260826")
        self.assertEqual(sup["approval_ref"], "FINAL-REVIEW-009 D2/D6")
        self.assertTrue(sup["reason"])
        rules = LAYOUT_V2["storage_rules"]
        self.assertTrue(rules["wrapped_root_key_envelope_allowed"])
        self.assertFalse(rules["plaintext_root_key_at_rest_allowed"])
        self.assertFalse(rules["recovery_secret_at_rest_allowed"])
        self.assertFalse(rules["plaintext_allowed"])
        self.assertFalse(rules["kv_decryption_authority"])
        self.assertEqual(LAYOUT_V2["paths"]["wrapped_root_envelope"], "_Vault/SKAP/Root/wrapped-root-envelope.json")
        self.assertEqual(LAYOUT_V2["paths"]["wrapped_root_envelope"], pe.KV_ENVELOPE_PATH)
        boundary = LAYOUT_V2["runtime_boundary"]
        self.assertEqual(boundary["kv_role"], "sealed-ciphertext-and-non-secret-evidence-custody-only")
        self.assertEqual(boundary["credential_authority"], "TV/TVC")
        self.assertTrue(boundary["ephemeral_skap_boundary_decryption"]["permitted"])
        self.assertFalse(boundary["ephemeral_skap_boundary_decryption"]["persistence_of_plaintext_or_root_key"])
        contract = LAYOUT_V2["wrapped_root_envelope_contract"]
        self.assertEqual(contract["kdf"]["min_iterations"], pe.MIN_PBKDF2_ITERATIONS)
        self.assertEqual(contract["schema"], pe.ENVELOPE_SCHEMA)


class CanonicalJSONTests(unittest.TestCase):
    def test_canonical_vectors(self):
        for case in VECTORS["canonical_json"]:
            with self.subTest(case=case["name"]):
                if "expected_error" in case:
                    with self.assertRaises(pe.PortableEnvelopeError) as ctx:
                        pe.canonical_json(case["input"])
                    self.assertEqual(ctx.exception.code, case["expected_error"])
                else:
                    self.assertEqual(pe.canonical_json(case["input"]).decode("ascii"), case["expected"])
                    self.assertEqual(pe.digest(case["input"]), case["expected_sha256_digest"])

    def test_nan_and_infinity_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(pe.PortableEnvelopeError):
                pe.canonical_json({"v": value})

    def test_policy_hash_vector_matches_policy_object(self):
        self.assertEqual(pe.digest(VECTORS["policy_object"]), VECTORS["policy_hash"])


class RecoverySecretTests(unittest.TestCase):
    def test_parse_vectors(self):
        for case in VECTORS["recovery_secret_parse"]:
            with self.subTest(case=case["name"]):
                if "expected_error" in case:
                    with self.assertRaises(pe.PortableEnvelopeError) as ctx:
                        pe.parse_recovery_secret(case["text"])
                    self.assertEqual(ctx.exception.code, case["expected_error"])
                else:
                    self.assertEqual(bytes(pe.parse_recovery_secret(case["text"])).hex(), case["expected_hex"])

    def test_generated_secret_round_trips_and_is_grouped(self):
        secret = pe.generate_recovery_secret()
        self.assertEqual(len(secret), 20)
        text = pe.format_recovery_secret(secret)
        groups = text.split("-")
        self.assertEqual(len(groups), 8)
        self.assertTrue(all(len(g) == 4 for g in groups))
        self.assertNotIn("=", text)
        self.assertEqual(pe.parse_recovery_secret(text), secret)

    def test_format_rejects_wrong_length(self):
        with self.assertRaises(pe.PortableEnvelopeError):
            pe.format_recovery_secret(bytes(19))


class EnvelopeVectorTests(unittest.TestCase):
    def test_root_key_id_vectors(self):
        for case in VECTORS["root_key_id"]:
            self.assertEqual(pe.root_key_id(_h(case["root_key_hex"])), case["expected_root_key_id"])

    def test_wrap_reproduces_vector_and_unwraps(self):
        for case in VECTORS["envelope_wrap"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(case["iterations"], 600000)
                envelope = pe.wrap_root_key(
                    _h(case["root_key_hex"]), _h(case["recovery_secret_hex"]),
                    kv_identity=case["kv_identity"], policy_hash=case["policy_hash"], iterations=case["iterations"],
                    _test_vector_salt=_h(case["salt_hex"]), _test_vector_nonce=_h(case["nonce_hex"]),
                )
                self.assertEqual(envelope, case["expected_envelope"])
                self.assertEqual(pe.digest(envelope), case["expected_envelope_digest"])
                aad = pe.envelope_aad(kv_identity=envelope["kv_identity"], root_key_id_value=envelope["root_key_id"], kdf=envelope["kdf"], policy_hash=envelope["policy_hash"])
                self.assertEqual(aad.decode("ascii"), case["expected_aad_ascii"])
                secret = pe.parse_recovery_secret(case["recovery_secret_text"])
                got = pe.unwrap_root_key_transiently(case["expected_envelope"], secret, lambda view: bytes(view),
                                                     expected_kv_identity=case["kv_identity"], expected_policy_hash=case["policy_hash"])
                self.assertEqual(got.hex(), case["root_key_hex"])

    def test_wrap_negative_vectors(self):
        for case in VECTORS["envelope_wrap_negative"]:
            with self.subTest(case=case["name"]), self.assertRaises(pe.PortableEnvelopeError) as ctx:
                pe.wrap_root_key(_h(case["root_key_hex"]), _h(case["recovery_secret_hex"]), kv_identity=case["kv_identity"],
                                 policy_hash=case["policy_hash"], iterations=case["iterations"],
                                 _test_vector_salt=_h(case["salt_hex"]), _test_vector_nonce=_h(case["nonce_hex"]))
            self.assertEqual(ctx.exception.code, case["expected_error"])

    def test_unwrap_negative_vectors(self):
        for case in VECTORS["envelope_unwrap_negative"]:
            with self.subTest(case=case["name"]):
                consumer = mock.Mock()
                with self.assertRaises(pe.PortableEnvelopeError) as ctx:
                    pe.unwrap_root_key_transiently(case["envelope"], pe.parse_recovery_secret(case["recovery_secret_text"]), consumer)
                self.assertEqual(ctx.exception.code, case["expected_error"])
                consumer.assert_not_called()

    def test_downgrade_refused_before_key_derivation(self):
        case = next(c for c in VECTORS["envelope_unwrap_negative"] if c["name"] == "iterations_599999_downgrade")
        with mock.patch.object(pe, "PBKDF2HMAC") as kdf:
            with self.assertRaises(pe.PortableEnvelopeError):
                pe.unwrap_root_key_transiently(case["envelope"], pe.parse_recovery_secret(case["recovery_secret_text"]), lambda v: None)
            kdf.assert_not_called()

    def test_binding_expectations_fail_closed(self):
        case = VECTORS["envelope_wrap"][0]
        secret = _h(case["recovery_secret_hex"])
        with self.assertRaises(pe.PortableEnvelopeError) as ctx:
            pe.unwrap_root_key_transiently(case["expected_envelope"], secret, lambda v: None, expected_kv_identity="kv://other")
        self.assertEqual(ctx.exception.code, "BINDING_MISMATCH")

    def test_random_wrap_is_fresh_and_ciphertext_only(self):
        root_key = pe.generate_root_key()
        secret = pe.generate_recovery_secret()
        a = pe.wrap_root_key(root_key, secret, kv_identity="kv://test/random", policy_hash=VECTORS["policy_hash"])
        b = pe.wrap_root_key(root_key, secret, kv_identity="kv://test/random", policy_hash=VECTORS["policy_hash"])
        self.assertNotEqual(a["aead"]["nonce_b64url"], b["aead"]["nonce_b64url"])
        self.assertNotEqual(a["kdf"]["salt_b64url"], b["kdf"]["salt_b64url"])
        encoded = pe.canonical_json(a)
        for needle in (bytes(root_key).hex().encode(), pe.b64url(bytes(root_key)).encode(), pe.format_recovery_secret(secret).encode(), bytes(secret).hex().encode()):
            self.assertNotIn(needle, encoded)
        self.assertEqual(pe.unwrap_root_key_transiently(a, secret, lambda v: bytes(v)), bytes(root_key))

    def test_test_vector_injection_requires_both_values(self):
        case = VECTORS["envelope_wrap"][0]
        with self.assertRaises(pe.PortableEnvelopeError) as ctx:
            pe.wrap_root_key(_h(case["root_key_hex"]), _h(case["recovery_secret_hex"]), kv_identity=case["kv_identity"],
                             policy_hash=case["policy_hash"], _test_vector_salt=_h(case["salt_hex"]))
        self.assertEqual(ctx.exception.code, "TEST_VECTOR_INJECTION_INVALID")
        with self.assertRaises(SKAPCryptoError):
            seal(b"x", root_key=bytes(32), object_id="skap://t", credential_version=1, wrapping_policy_ref="p", purpose="p",
                 endpoint_ref="e", key_authority_ref="k", _test_vector_nonce=bytes(12))


class SealedObjectVectorTests(unittest.TestCase):
    def test_sealed_vectors_reproduce_with_existing_crypto_boundary(self):
        for case in VECTORS["sealed_objects"]:
            with self.subTest(case=case["name"]):
                sealed = seal(case["plaintext_ascii"].encode("ascii"), root_key=_h(case["root_key_hex"]), **case["bindings"],
                              _test_vector_salt=_h(case["kdf_salt_hex"]), _test_vector_nonce=_h(case["nonce_hex"]))
                self.assertEqual(sealed.envelope, case["expected_sealed"])
                self.assertEqual(sealed.sealed_material_hash, case["expected_sealed_material_hash"])
                self.assertEqual(_open(case["expected_sealed"], _h(case["root_key_hex"]), case["bindings"]), case["plaintext_ascii"].encode("ascii"))

    def test_sealed_open_negative_vectors(self):
        messages = {
            "SEALED_AUTH_FAILED": "authentication/decryption failed",
            "SEALED_BINDING_MISMATCH": "binding mismatch",
            "SEALED_BOUNDARY_VIOLATION": "non-persistence/non-authority",
        }
        for case in VECTORS["sealed_open_negative"]:
            with self.subTest(case=case["name"]), self.assertRaisesRegex(SKAPCryptoError, messages[case["expected_error"]]):
                _open(case["sealed"], _h(case["root_key_hex"]), case["bindings"])

    def test_vector_bindings_match_module_bindings(self):
        cred, anchor = VECTORS["sealed_objects"]
        rkid = VECTORS["root_key_id"][0]["expected_root_key_id"]
        self.assertEqual(cred["bindings"], pe.provider_credential_bindings("anthropic", policy_hash=VECTORS["policy_hash"], root_key_id_value=rkid))
        self.assertEqual(anchor["bindings"], pe.bootstrap_anchor_bindings(policy_hash=VECTORS["policy_hash"], root_key_id_value=rkid))
        self.assertEqual(cred["bindings"]["purpose"], "provider-credential")
        self.assertEqual(anchor["bindings"]["purpose"], "kv-skap-bootstrap-anchor")
        self.assertEqual(pe.parse_bootstrap_anchor(anchor["plaintext_ascii"].encode("ascii"))["policy_hash"], VECTORS["policy_hash"])


class KVWrappedEnvelopeKeyProviderTests(unittest.TestCase):
    def setUp(self):
        self.case = VECTORS["envelope_wrap"][0]
        self.provider = pe.KVWrappedEnvelopeKeyProvider(self.case["expected_envelope"], _h(self.case["recovery_secret_hex"]),
                                                        expected_kv_identity=self.case["kv_identity"], expected_policy_hash=self.case["policy_hash"])

    def test_authority_ref_and_callback_only_key_with_wipe(self):
        self.assertEqual(self.provider.authority_ref, "kv-wrapped://" + self.case["expected_envelope"]["root_key_id"])
        captured = {}

        def consumer(view):
            captured["view"] = view
            captured["bytes"] = bytes(view)
            return "USED"

        self.assertEqual(self.provider.with_key(consumer), "USED")
        self.assertEqual(captured["bytes"].hex(), self.case["root_key_hex"])
        self.assertEqual(bytes(captured["view"]), bytes(32))  # wiped after callback

    def test_seal_and_bootstrap_anchor_through_provider(self):
        rkid = self.case["expected_envelope"]["root_key_id"]
        bindings = pe.provider_credential_bindings("openai", policy_hash=self.case["policy_hash"], root_key_id_value=rkid)
        kw = {k: v for k, v in bindings.items() if k != "key_authority_ref"}
        sealed = seal_with_provider(b"TEST-VECTOR-ONLY-NOT-A-PROVIDER-CREDENTIAL", key_provider=self.provider, **kw)
        self.assertEqual(sealed.envelope["key_authority_ref"], self.provider.authority_ref)
        self.assertEqual(self.provider.with_key(lambda key: _open(sealed.envelope, key, bindings)), b"TEST-VECTOR-ONLY-NOT-A-PROVIDER-CREDENTIAL")
        anchor = pe.build_bootstrap_anchor(loader_sha256="a" * 64, loader_repository="StegVerse-Labs/continuity-vault-kit", loader_commit="b" * 40,
                                           loader_path="skap/loader/kv-skap-loader.html", policy_hash=self.case["policy_hash"],
                                           kv_identity=self.case["kv_identity"], genesis_manifest_digest="sha256:" + "c" * 64,
                                           predecessor_state="KV_SKAP_UNINITIALIZED")
        sealed_anchor = pe.seal_bootstrap_anchor(anchor, key_provider=self.provider, policy_hash=self.case["policy_hash"])
        self.assertEqual(sealed_anchor.envelope["purpose"], "kv-skap-bootstrap-anchor")
        opened = pe.open_bootstrap_anchor(sealed_anchor.envelope, key_provider=self.provider, policy_hash=self.case["policy_hash"])
        self.assertEqual(pe.canonical_json(opened), anchor)

    def test_close_wipes_recovery_secret(self):
        self.provider.close()
        with self.assertRaises(pe.PortableEnvelopeError) as ctx:
            self.provider.with_key(lambda v: None)
        self.assertEqual(ctx.exception.code, "RECOVERY_SECRET_WIPED")

    def test_wrong_recovery_secret_fails_closed(self):
        provider = pe.KVWrappedEnvelopeKeyProvider(self.case["expected_envelope"], bytes(20))
        consumer = mock.Mock()
        with self.assertRaises(pe.PortableEnvelopeError):
            provider.with_key(consumer)
        consumer.assert_not_called()

    def test_legacy_tvc_resident_provider_scope_unchanged(self):
        legacy = TVCResidentFileKeyProvider("/run/stegverse/tv-tvc-credentials/SKAP_ROOT_KEY")
        self.assertEqual(legacy.authority_ref, "tvc-resident://SKAP_ROOT_KEY")


class VectorHygieneTests(unittest.TestCase):
    def test_vectors_file_is_ascii_and_labelled(self):
        raw = (ROOT / "fixtures/skap/portable-envelope-v2.vectors.json").read_bytes()
        raw.decode("ascii")
        self.assertIn("TEST VECTORS ONLY", VECTORS["notice"])
        for case in VECTORS["sealed_objects"]:
            if case["name"].startswith("provider_credential"):
                self.assertTrue(case["plaintext_ascii"].startswith("TEST-VECTOR-ONLY-NOT-A-PROVIDER-CREDENTIAL"))


if __name__ == "__main__":
    unittest.main()

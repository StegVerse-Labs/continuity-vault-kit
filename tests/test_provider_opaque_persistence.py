import copy

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from continuity.provider_opaque_persistence import (
    ProviderOpaquePersistenceError,
    _public_jwk,
    import_public_jwk,
    resolve_with_protected_key,
    seal_for_provider,
)


def _bindings():
    return {
        "kv_instance_id": "kvi_11111111111111111111111111111111",
        "kv_set_id": "personal",
        "object_id": "notes/example",
        "object_version": 1,
        "object_class": "USER_PRIVATE",
        "state_commitment": "sha256:" + "a" * 64,
        "recipient_key_id": "kv-key:test",
    }


def _fixture():
    recipient = ec.generate_private_key(ec.SECP256R1())
    plain = bytearray(b'{"value":"private user state"}')
    env = seal_for_provider(plain, recipient_public_jwk=_public_jwk(recipient.public_key()), **_bindings())

    def derive(ephemeral_jwk):
        return recipient.exchange(ec.ECDH(), import_public_jwk(ephemeral_jwk))

    return env, derive


def test_provider_object_contains_ciphertext_only_and_zeroizes_input():
    recipient = ec.generate_private_key(ec.SECP256R1())
    plain = bytearray(b"sensitive payload")
    env = seal_for_provider(plain, recipient_public_jwk=_public_jwk(recipient.public_key()), **_bindings())
    assert plain == bytearray(len(plain))
    assert env["plaintext_persisted"] is False
    assert env["private_key_persisted"] is False
    assert env["storage_provider_plaintext_authority"] is False
    assert env["storage_provider_decryption_authority"] is False
    assert env["storage_provider_use_authority"] is False
    assert env["storage_provider_transition_authority"] is False
    assert "sensitive payload" not in str(env)
    assert "d" not in env["ephemeral_public_jwk"]


def test_exact_readback_requires_governed_admission_and_protected_key_operation():
    env, derive = _fixture()
    with pytest.raises(ProviderOpaquePersistenceError, match="admission required"):
        resolve_with_protected_key(env, expected_bindings=_bindings(), derive_shared_secret=derive, admission_granted=False, consumer=lambda v: bytes(v))
    assert resolve_with_protected_key(env, expected_bindings=_bindings(), derive_shared_secret=derive, admission_granted=True, consumer=lambda v: bytes(v)) == b'{"value":"private user state"}'


def test_provider_possession_without_protected_key_cannot_decrypt():
    env, _ = _fixture()
    unrelated = ec.generate_private_key(ec.SECP256R1())

    def wrong_key(ephemeral_jwk):
        return unrelated.exchange(ec.ECDH(), import_public_jwk(ephemeral_jwk))

    with pytest.raises(ProviderOpaquePersistenceError, match="authentication/decryption failed"):
        resolve_with_protected_key(env, expected_bindings=_bindings(), derive_shared_secret=wrong_key, admission_granted=True, consumer=lambda v: bytes(v))


def test_tampered_binding_and_ciphertext_fail_closed():
    env, derive = _fixture()
    changed = copy.deepcopy(_bindings())
    changed["object_id"] = "notes/other"
    with pytest.raises(ProviderOpaquePersistenceError, match="object_id binding mismatch"):
        resolve_with_protected_key(env, expected_bindings=changed, derive_shared_secret=derive, admission_granted=True, consumer=lambda v: bytes(v))

    tampered = copy.deepcopy(env)
    tampered["ciphertext_b64"] = tampered["ciphertext_b64"][:-1] + ("A" if tampered["ciphertext_b64"][-1] != "A" else "B")
    with pytest.raises(ProviderOpaquePersistenceError, match="authentication/decryption failed"):
        resolve_with_protected_key(tampered, expected_bindings=_bindings(), derive_shared_secret=derive, admission_granted=True, consumer=lambda v: bytes(v))


def test_persisted_authority_claims_are_rejected():
    env, derive = _fixture()
    for field in (
        "plaintext_persisted",
        "private_key_persisted",
        "storage_provider_plaintext_authority",
        "storage_provider_decryption_authority",
        "storage_provider_use_authority",
        "storage_provider_transition_authority",
        "authority_transfer",
    ):
        invalid = copy.deepcopy(env)
        invalid[field] = True
        with pytest.raises(ProviderOpaquePersistenceError, match="boundary violated"):
            resolve_with_protected_key(invalid, expected_bindings=_bindings(), derive_shared_secret=derive, admission_granted=True, consumer=lambda v: bytes(v))

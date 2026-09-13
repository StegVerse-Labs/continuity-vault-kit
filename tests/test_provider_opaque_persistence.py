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


def _transition(operation, commitment_char):
    return {
        "schema": "stegverse.kv.interlock-intr-transition/v1",
        "boundary": "KV",
        "initiator": "INTERLOCK_INTR_ONLY",
        "operation": operation,
        "kv_instance_id": "kvi_11111111111111111111111111111111",
        "object_id": "notes/example",
        "interlock_observed": True,
        "intr_admitted": True,
        "interlock_receipt_ref": "receipt://interlock/test",
        "intr_receipt_ref": "receipt://intr/test",
        "state_commitment": "sha256:" + "a" * 64,
        "transition_commitment": "sha256:" + commitment_char * 64,
    }


def _bindings(write_transition):
    return {
        "kv_instance_id": "kvi_11111111111111111111111111111111",
        "kv_set_id": "personal",
        "object_id": "notes/example",
        "object_version": 1,
        "object_class": "USER_PRIVATE",
        "state_commitment": write_transition["state_commitment"],
        "transition_commitment": write_transition["transition_commitment"],
        "recipient_key_id": "kv-key:test",
    }


def _fixture():
    recipient = ec.generate_private_key(ec.SECP256R1())
    write_transition = _transition("WRITE", "b")
    plain = bytearray(b'{"value":"private user state"}')
    env = seal_for_provider(
        plain,
        transition=write_transition,
        recipient_public_jwk=_public_jwk(recipient.public_key()),
        recipient_key_id="kv-key:test",
        kv_instance_id="kvi_11111111111111111111111111111111",
        kv_set_id="personal",
        object_id="notes/example",
        object_version=1,
        object_class="USER_PRIVATE",
    )

    def derive(ephemeral_jwk):
        return recipient.exchange(ec.ECDH(), import_public_jwk(ephemeral_jwk))

    return env, derive, write_transition


def test_write_cannot_start_without_kv_boundary_interlock_intr_transition():
    recipient = ec.generate_private_key(ec.SECP256R1())
    plain = bytearray(b"sensitive payload")
    with pytest.raises(ProviderOpaquePersistenceError, match="requires canonical Interlock/InTr transition"):
        seal_for_provider(
            plain,
            transition={},
            recipient_public_jwk=_public_jwk(recipient.public_key()),
            recipient_key_id="kv-key:test",
            kv_instance_id="kvi_11111111111111111111111111111111",
            kv_set_id="personal",
            object_id="notes/example",
            object_version=1,
            object_class="USER_PRIVATE",
        )


def test_provider_object_contains_ciphertext_only_and_transition_binding():
    env, _, write_transition = _fixture()
    assert env["plaintext_persisted"] is False
    assert env["private_key_persisted"] is False
    assert env["storage_provider_plaintext_authority"] is False
    assert env["storage_provider_decryption_authority"] is False
    assert env["storage_provider_use_authority"] is False
    assert env["storage_provider_transition_authority"] is False
    assert env["transition_commitment"] == write_transition["transition_commitment"]
    assert env["interlock_receipt_ref"] == write_transition["interlock_receipt_ref"]
    assert env["intr_receipt_ref"] == write_transition["intr_receipt_ref"]
    assert "private user state" not in str(env)
    assert "d" not in env["ephemeral_public_jwk"]


def test_read_cannot_start_without_distinct_kv_boundary_interlock_intr_transition():
    env, derive, write_transition = _fixture()
    with pytest.raises(ProviderOpaquePersistenceError, match="requires canonical Interlock/InTr transition"):
        resolve_with_protected_key(
            env,
            transition={},
            expected_bindings=_bindings(write_transition),
            derive_shared_secret=derive,
            consumer=lambda v: bytes(v),
        )

    with pytest.raises(ProviderOpaquePersistenceError, match="read transition must be distinct"):
        resolve_with_protected_key(
            env,
            transition=write_transition | {"operation": "READ"},
            expected_bindings=_bindings(write_transition),
            derive_shared_secret=derive,
            consumer=lambda v: bytes(v),
        )


def test_exact_readback_requires_interlock_intr_observed_read_transition_and_protected_key():
    env, derive, write_transition = _fixture()
    read_transition = _transition("READ", "c")
    assert resolve_with_protected_key(
        env,
        transition=read_transition,
        expected_bindings=_bindings(write_transition),
        derive_shared_secret=derive,
        consumer=lambda v: bytes(v),
    ) == b'{"value":"private user state"}'


def test_provider_possession_without_protected_key_cannot_decrypt():
    env, _, write_transition = _fixture()
    unrelated = ec.generate_private_key(ec.SECP256R1())

    def wrong_key(ephemeral_jwk):
        return unrelated.exchange(ec.ECDH(), import_public_jwk(ephemeral_jwk))

    with pytest.raises(ProviderOpaquePersistenceError, match="authentication/decryption failed"):
        resolve_with_protected_key(
            env,
            transition=_transition("READ", "c"),
            expected_bindings=_bindings(write_transition),
            derive_shared_secret=wrong_key,
            consumer=lambda v: bytes(v),
        )


def test_tampered_binding_and_ciphertext_fail_closed():
    env, derive, write_transition = _fixture()
    changed = copy.deepcopy(_bindings(write_transition))
    changed["object_id"] = "notes/other"
    changed_transition = _transition("READ", "c")
    changed_transition["object_id"] = "notes/other"
    with pytest.raises(ProviderOpaquePersistenceError, match="object_id binding mismatch"):
        resolve_with_protected_key(
            env,
            transition=changed_transition,
            expected_bindings=changed,
            derive_shared_secret=derive,
            consumer=lambda v: bytes(v),
        )

    tampered = copy.deepcopy(env)
    tampered["ciphertext_b64"] = tampered["ciphertext_b64"][:-1] + ("A" if tampered["ciphertext_b64"][-1] != "A" else "B")
    with pytest.raises(ProviderOpaquePersistenceError, match="authentication/decryption failed"):
        resolve_with_protected_key(
            tampered,
            transition=_transition("READ", "c"),
            expected_bindings=_bindings(write_transition),
            derive_shared_secret=derive,
            consumer=lambda v: bytes(v),
        )


def test_persisted_authority_claims_are_rejected():
    env, derive, write_transition = _fixture()
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
            resolve_with_protected_key(
                invalid,
                transition=_transition("READ", "c"),
                expected_bindings=_bindings(write_transition),
                derive_shared_secret=derive,
                consumer=lambda v: bytes(v),
            )

"""Provider-independent cryptographic persistence envelope for KnowledgeVault objects.

KnowledgeVault is a state-dependent AI boundary. ALL KV activity is initiated only
through the KV-boundary Interlock/InTr bridge observing a proposed state transition.
No persistence, readback, provider event, local function call, or possession event may
initiate KV activity independently.

Storage providers hold ciphertext materialization only. Possession of persisted bytes
grants no plaintext, decryption, use, transition, credential, or execution authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Callable, TypeVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FORMAT = "stegverse.kv.provider-opaque-object/p256-ecdh-hkdf-sha256-aes256gcm/v1"
TRANSITION_SCHEMA = "stegverse.kv.interlock-intr-transition/v1"
T = TypeVar("T")


class ProviderOpaquePersistenceError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode((value + "=" * ((4 - len(value) % 4) % 4)).encode("ascii"))
    except Exception as exc:
        raise ProviderOpaquePersistenceError("invalid base64url value") from exc


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _public_jwk(key: ec.EllipticCurvePublicKey) -> dict[str, str]:
    numbers = key.public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64(numbers.x.to_bytes(32, "big")),
        "y": _b64(numbers.y.to_bytes(32, "big")),
    }


def import_public_jwk(jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256" or "d" in jwk:
        raise ProviderOpaquePersistenceError("recipient/ephemeral key must be public EC P-256")
    x, y = _unb64(str(jwk.get("x", ""))), _unb64(str(jwk.get("y", "")))
    if len(x) != 32 or len(y) != 32:
        raise ProviderOpaquePersistenceError("P-256 coordinate length invalid")
    try:
        return ec.EllipticCurvePublicNumbers(int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()).public_key()
    except Exception as exc:
        raise ProviderOpaquePersistenceError("invalid P-256 public key") from exc


def _transition(transition: dict[str, Any], *, operation: str, kv_instance_id: str, object_id: str,
                expected_state_commitment: str | None = None) -> dict[str, Any]:
    if not isinstance(transition, dict) or transition.get("schema") != TRANSITION_SCHEMA:
        raise ProviderOpaquePersistenceError("KV activity requires canonical Interlock/InTr transition")
    if transition.get("boundary") != "KV":
        raise ProviderOpaquePersistenceError("transition not observed at KV boundary")
    if transition.get("initiator") != "INTERLOCK_INTR_ONLY":
        raise ProviderOpaquePersistenceError("KV transition must be initiated through Interlock/InTr only")
    if transition.get("operation") != operation:
        raise ProviderOpaquePersistenceError("KV transition operation mismatch")
    if transition.get("kv_instance_id") != kv_instance_id or transition.get("object_id") != object_id:
        raise ProviderOpaquePersistenceError("KV transition object binding mismatch")
    if transition.get("interlock_observed") is not True:
        raise ProviderOpaquePersistenceError("Interlock observation required")
    if transition.get("intr_admitted") is not True:
        raise ProviderOpaquePersistenceError("InTr admission required")
    if not str(transition.get("interlock_receipt_ref") or ""):
        raise ProviderOpaquePersistenceError("Interlock receipt required")
    if not str(transition.get("intr_receipt_ref") or ""):
        raise ProviderOpaquePersistenceError("InTr receipt required")
    state_commitment = str(transition.get("state_commitment") or "")
    if not state_commitment.startswith("sha256:"):
        raise ProviderOpaquePersistenceError("transition state commitment required")
    if expected_state_commitment is not None and state_commitment != expected_state_commitment:
        raise ProviderOpaquePersistenceError("transition state commitment mismatch")
    transition_commitment = str(transition.get("transition_commitment") or "")
    if not transition_commitment.startswith("sha256:"):
        raise ProviderOpaquePersistenceError("transition commitment required")
    return transition


def _context(*, kv_instance_id: str, kv_set_id: str, object_id: str, object_version: int,
             object_class: str, state_commitment: str, transition_commitment: str,
             recipient_key_id: str) -> dict[str, Any]:
    if not kv_instance_id.startswith("kvi_"):
        raise ProviderOpaquePersistenceError("kv_instance_id invalid")
    if not kv_set_id or not object_id or object_version < 1 or not object_class:
        raise ProviderOpaquePersistenceError("object binding invalid")
    if not state_commitment.startswith("sha256:") or not transition_commitment.startswith("sha256:"):
        raise ProviderOpaquePersistenceError("state/transition commitment invalid")
    if not recipient_key_id:
        raise ProviderOpaquePersistenceError("recipient_key_id required")
    return {
        "kv_instance_id": kv_instance_id,
        "kv_set_id": kv_set_id,
        "object_id": object_id,
        "object_version": object_version,
        "object_class": object_class,
        "state_commitment": state_commitment,
        "transition_commitment": transition_commitment,
        "recipient_key_id": recipient_key_id,
    }


def _derive(shared_secret: bytes, *, salt: bytes, aad: bytes) -> bytes:
    info = b"stegverse-kv-provider-opaque-object-v1\x00" + hashlib.sha256(aad).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared_secret)


def seal_for_provider(plaintext: bytearray, *, transition: dict[str, Any], recipient_public_jwk: dict[str, Any],
                      recipient_key_id: str, kv_instance_id: str, kv_set_id: str, object_id: str,
                      object_version: int, object_class: str) -> dict[str, Any]:
    if not isinstance(plaintext, bytearray) or not plaintext:
        raise ProviderOpaquePersistenceError("plaintext must be a non-empty mutable bytearray")
    observed = _transition(transition, operation="WRITE", kv_instance_id=kv_instance_id, object_id=object_id)
    state_commitment = observed["state_commitment"]
    transition_commitment = observed["transition_commitment"]
    recipient = import_public_jwk(recipient_public_jwk)
    context = _context(
        kv_instance_id=kv_instance_id, kv_set_id=kv_set_id, object_id=object_id,
        object_version=object_version, object_class=object_class,
        state_commitment=state_commitment, transition_commitment=transition_commitment,
        recipient_key_id=recipient_key_id,
    )
    aad = _canonical(context)
    ephemeral_private = ec.generate_private_key(ec.SECP256R1())
    shared = bytearray(ephemeral_private.exchange(ec.ECDH(), recipient))
    salt, nonce = os.urandom(32), os.urandom(12)
    key = bytearray(_derive(bytes(shared), salt=salt, aad=aad))
    try:
        ciphertext = AESGCM(bytes(key)).encrypt(nonce, bytes(plaintext), aad)
        return {
            "format": FORMAT,
            **context,
            "interlock_receipt_ref": observed["interlock_receipt_ref"],
            "intr_receipt_ref": observed["intr_receipt_ref"],
            "ephemeral_public_jwk": _public_jwk(ephemeral_private.public_key()),
            "kdf_salt_b64": _b64(salt),
            "nonce_b64": _b64(nonce),
            "aad_hash": _sha(aad),
            "ciphertext_b64": _b64(ciphertext),
            "provider_independent": True,
            "plaintext_persisted": False,
            "private_key_persisted": False,
            "storage_provider_plaintext_authority": False,
            "storage_provider_decryption_authority": False,
            "storage_provider_use_authority": False,
            "storage_provider_transition_authority": False,
            "authority_transfer": False,
        }
    finally:
        for index in range(len(plaintext)):
            plaintext[index] = 0
        for buffer in (shared, key):
            for index in range(len(buffer)):
                buffer[index] = 0


def resolve_with_protected_key(envelope: dict[str, Any], *, transition: dict[str, Any],
                               expected_bindings: dict[str, Any],
                               derive_shared_secret: Callable[[dict[str, str]], bytes],
                               consumer: Callable[[memoryview], T]) -> T:
    observed = _transition(
        transition,
        operation="READ",
        kv_instance_id=expected_bindings["kv_instance_id"],
        object_id=expected_bindings["object_id"],
        expected_state_commitment=expected_bindings["state_commitment"],
    )
    if envelope.get("format") != FORMAT or envelope.get("provider_independent") is not True:
        raise ProviderOpaquePersistenceError("persisted object format invalid")
    for field in (
        "plaintext_persisted", "private_key_persisted", "storage_provider_plaintext_authority",
        "storage_provider_decryption_authority", "storage_provider_use_authority",
        "storage_provider_transition_authority", "authority_transfer",
    ):
        if envelope.get(field) is not False:
            raise ProviderOpaquePersistenceError(f"{field} boundary violated")
    context = _context(**expected_bindings)
    for key, value in context.items():
        if envelope.get(key) != value:
            raise ProviderOpaquePersistenceError(f"{key} binding mismatch")
    if observed["transition_commitment"] == envelope.get("transition_commitment"):
        raise ProviderOpaquePersistenceError("read transition must be distinct from write transition")
    aad = _canonical(context)
    if envelope.get("aad_hash") != _sha(aad):
        raise ProviderOpaquePersistenceError("AAD hash mismatch")
    ephemeral_jwk = envelope.get("ephemeral_public_jwk") or {}
    import_public_jwk(ephemeral_jwk)
    shared_raw = derive_shared_secret(ephemeral_jwk)
    if not isinstance(shared_raw, (bytes, bytearray)) or len(shared_raw) == 0:
        raise ProviderOpaquePersistenceError("protected key operation failed")
    shared = bytearray(shared_raw)
    salt, nonce, ciphertext = (_unb64(str(envelope.get(name, ""))) for name in ("kdf_salt_b64", "nonce_b64", "ciphertext_b64"))
    if len(salt) != 32 or len(nonce) != 12 or len(ciphertext) < 16:
        raise ProviderOpaquePersistenceError("cryptographic dimensions invalid")
    key = bytearray(_derive(bytes(shared), salt=salt, aad=aad))
    try:
        try:
            decrypted = AESGCM(bytes(key)).decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise ProviderOpaquePersistenceError("authentication/decryption failed") from exc
        mutable = bytearray(decrypted)
        del decrypted
        try:
            return consumer(memoryview(mutable))
        finally:
            for index in range(len(mutable)):
                mutable[index] = 0
    finally:
        for buffer in (shared, key):
            for index in range(len(buffer)):
                buffer[index] = 0

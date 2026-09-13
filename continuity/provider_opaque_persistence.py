"""Provider-independent cryptographic persistence envelope for KnowledgeVault objects.

Storage providers hold ciphertext materialization only. Possession of the persisted
object grants no plaintext, decryption, use, transition, or credential authority.
Decryption is possible only through a separately supplied protected-key operation.
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


def _context(*, kv_instance_id: str, kv_set_id: str, object_id: str, object_version: int,
             object_class: str, state_commitment: str, recipient_key_id: str) -> dict[str, Any]:
    if not kv_instance_id.startswith("kvi_"):
        raise ProviderOpaquePersistenceError("kv_instance_id invalid")
    if not kv_set_id or not object_id or object_version < 1 or not object_class:
        raise ProviderOpaquePersistenceError("object binding invalid")
    if not state_commitment.startswith("sha256:"):
        raise ProviderOpaquePersistenceError("state_commitment must be sha256")
    if not recipient_key_id:
        raise ProviderOpaquePersistenceError("recipient_key_id required")
    return {
        "kv_instance_id": kv_instance_id,
        "kv_set_id": kv_set_id,
        "object_id": object_id,
        "object_version": object_version,
        "object_class": object_class,
        "state_commitment": state_commitment,
        "recipient_key_id": recipient_key_id,
    }


def _derive(shared_secret: bytes, *, salt: bytes, aad: bytes) -> bytes:
    info = b"stegverse-kv-provider-opaque-object-v1\x00" + hashlib.sha256(aad).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared_secret)


def seal_for_provider(plaintext: bytearray, *, recipient_public_jwk: dict[str, Any], recipient_key_id: str,
                      kv_instance_id: str, kv_set_id: str, object_id: str, object_version: int,
                      object_class: str, state_commitment: str) -> dict[str, Any]:
    if not isinstance(plaintext, bytearray) or not plaintext:
        raise ProviderOpaquePersistenceError("plaintext must be a non-empty mutable bytearray")
    recipient = import_public_jwk(recipient_public_jwk)
    context = _context(
        kv_instance_id=kv_instance_id, kv_set_id=kv_set_id, object_id=object_id,
        object_version=object_version, object_class=object_class,
        state_commitment=state_commitment, recipient_key_id=recipient_key_id,
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


def resolve_with_protected_key(envelope: dict[str, Any], *, expected_bindings: dict[str, Any],
                               derive_shared_secret: Callable[[dict[str, str]], bytes],
                               admission_granted: bool, consumer: Callable[[memoryview], T]) -> T:
    if not admission_granted:
        raise ProviderOpaquePersistenceError("governed readback admission required")
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

"""SKAP authenticated cryptographic sealing and transient resolution boundary.

This module deliberately owns no durable key authority. A caller supplies root key
material for one operation; SKAP derives an object/version-specific AES-256-GCM key
with HKDF-SHA256, authenticates immutable context as AAD, and returns only a sealed
ciphertext envelope. Resolution is callback-only: plaintext is not returned and a
mutable copy is overwritten immediately after the callback completes.

Python cannot guarantee compiler/runtime-level zeroization of every temporary byte
allocation. The boundary therefore guarantees no deliberate plaintext persistence,
logging, serialization, return value, or KV storage, and performs best-effort wiping
of the mutable resolution buffer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SEALED_FORMAT = "stegverse.skap.sealed_material/aes256gcm-hkdf-sha256/v1"
T = TypeVar("T")


class SKAPCryptoError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except Exception as exc:  # pragma: no cover - backend-specific decoder detail
        raise SKAPCryptoError("invalid sealed-material base64") from exc


def _aad_context(*, object_id: str, credential_version: int, wrapping_policy_ref: str, purpose: str, endpoint_ref: str) -> dict[str, Any]:
    if not object_id.startswith("skap://"):
        raise SKAPCryptoError("object_id must use skap://")
    if credential_version < 1:
        raise SKAPCryptoError("credential_version must be >= 1")
    if not wrapping_policy_ref or not purpose or not endpoint_ref:
        raise SKAPCryptoError("wrapping policy, purpose and endpoint are required")
    return {
        "object_id": object_id,
        "credential_version": credential_version,
        "wrapping_policy_ref": wrapping_policy_ref,
        "purpose": purpose,
        "endpoint_ref": endpoint_ref,
    }


def _derive_key(root_key: bytes, salt: bytes, aad: bytes) -> bytes:
    if not isinstance(root_key, (bytes, bytearray)) or len(root_key) < 32:
        raise SKAPCryptoError("root key material must contain at least 256 bits")
    info = b"stegverse-skap-aes256gcm-v1\x00" + hashlib.sha256(aad).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(bytes(root_key))


@dataclass(frozen=True)
class SealedMaterial:
    envelope: dict[str, Any]

    @property
    def sealed_material_hash(self) -> str:
        return _sha256_uri(_canonical_bytes(self.envelope))


def seal(
    plaintext: bytes | bytearray,
    *,
    root_key: bytes | bytearray,
    object_id: str,
    credential_version: int,
    wrapping_policy_ref: str,
    purpose: str,
    endpoint_ref: str,
    key_authority_ref: str,
) -> SealedMaterial:
    """Seal plaintext under caller-supplied key authority and return ciphertext only."""
    if not isinstance(plaintext, (bytes, bytearray)) or not plaintext:
        raise SKAPCryptoError("non-empty plaintext bytes are required")
    if not key_authority_ref:
        raise SKAPCryptoError("key_authority_ref is required")

    context = _aad_context(
        object_id=object_id,
        credential_version=credential_version,
        wrapping_policy_ref=wrapping_policy_ref,
        purpose=purpose,
        endpoint_ref=endpoint_ref,
    )
    aad = _canonical_bytes(context)
    salt = os.urandom(32)
    nonce = os.urandom(12)
    key = _derive_key(root_key, salt, aad)
    ciphertext = AESGCM(key).encrypt(nonce, bytes(plaintext), aad)

    envelope = {
        "format": SEALED_FORMAT,
        "object_id": object_id,
        "credential_version": credential_version,
        "wrapping_policy_ref": wrapping_policy_ref,
        "purpose": purpose,
        "endpoint_ref": endpoint_ref,
        "key_authority_ref": key_authority_ref,
        "kdf_salt_b64": _b64(salt),
        "nonce_b64": _b64(nonce),
        "aad_hash": _sha256_uri(aad),
        "ciphertext_b64": _b64(ciphertext),
        "plaintext_persisted": False,
        "key_material_persisted": False,
        "authority_transfer": False,
    }
    return SealedMaterial(envelope=envelope)


def resolve_transiently(
    sealed: dict[str, Any],
    *,
    root_key: bytes | bytearray,
    expected_object_id: str,
    expected_credential_version: int,
    expected_wrapping_policy_ref: str,
    expected_purpose: str,
    expected_endpoint_ref: str,
    expected_key_authority_ref: str,
    consumer: Callable[[memoryview], T],
) -> T:
    """Authenticate/decrypt and expose plaintext only for the duration of ``consumer``."""
    required_false = ("plaintext_persisted", "key_material_persisted", "authority_transfer")
    if sealed.get("format") != SEALED_FORMAT:
        raise SKAPCryptoError("unsupported sealed material format")
    if any(sealed.get(name) is not False for name in required_false):
        raise SKAPCryptoError("sealed material violates non-persistence/non-authority boundary")

    expected = _aad_context(
        object_id=expected_object_id,
        credential_version=expected_credential_version,
        wrapping_policy_ref=expected_wrapping_policy_ref,
        purpose=expected_purpose,
        endpoint_ref=expected_endpoint_ref,
    )
    for field, value in expected.items():
        if sealed.get(field) != value:
            raise SKAPCryptoError(f"sealed material {field} binding mismatch")
    if sealed.get("key_authority_ref") != expected_key_authority_ref:
        raise SKAPCryptoError("sealed material key authority mismatch")

    aad = _canonical_bytes(expected)
    if sealed.get("aad_hash") != _sha256_uri(aad):
        raise SKAPCryptoError("sealed material AAD hash mismatch")

    salt = _unb64(str(sealed.get("kdf_salt_b64", "")))
    nonce = _unb64(str(sealed.get("nonce_b64", "")))
    ciphertext = _unb64(str(sealed.get("ciphertext_b64", "")))
    if len(salt) != 32 or len(nonce) != 12 or len(ciphertext) < 16:
        raise SKAPCryptoError("sealed material cryptographic dimensions invalid")

    key = _derive_key(root_key, salt, aad)
    try:
        decrypted = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise SKAPCryptoError("sealed material authentication/decryption failed") from exc

    mutable = bytearray(decrypted)
    del decrypted
    try:
        return consumer(memoryview(mutable))
    finally:
        for index in range(len(mutable)):
            mutable[index] = 0

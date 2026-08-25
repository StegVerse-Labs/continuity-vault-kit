"""Browser-to-SKAP public-key sealed ingress primitive.

The browser/device receives only a SKAP recipient *public* key. It generates an
one-operation ephemeral P-256 key, derives an AES-256-GCM content key with
ECDH + HKDF-SHA256, encrypts the credential locally, and may then send only the
ciphertext envelope over InTr. The SKAP recipient private key never leaves SKAP.

This module is the Python reference/recipient implementation for the WebCrypto
P-256 ECDH envelope used by the current-user iPhone browser surface.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FORMAT = "stegverse.skap.browser_ingress/p256-ecdh-hkdf-sha256-aes256gcm/v1"
T = TypeVar("T")


class BrowserIngressError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode((value + "=" * ((4 - len(value) % 4) % 4)).encode("ascii"))
    except Exception as exc:
        raise BrowserIngressError("invalid base64url value") from exc


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


def public_jwk_from_private(key: ec.EllipticCurvePrivateKey) -> dict[str, str]:
    return _public_jwk(key.public_key())


def import_public_jwk(jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise BrowserIngressError("recipient/ephemeral key must be EC P-256")
    x, y = _unb64(str(jwk.get("x", ""))), _unb64(str(jwk.get("y", "")))
    if len(x) != 32 or len(y) != 32:
        raise BrowserIngressError("P-256 coordinate length invalid")
    try:
        return ec.EllipticCurvePublicNumbers(int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()).public_key()
    except Exception as exc:
        raise BrowserIngressError("invalid P-256 public key") from exc


def _context(*, object_id: str, credential_version: int, wrapping_policy_ref: str, purpose: str, endpoint_ref: str, recipient_key_id: str) -> dict[str, Any]:
    if not object_id.startswith("skap://"):
        raise BrowserIngressError("object_id must use skap://")
    if credential_version < 1:
        raise BrowserIngressError("credential_version must be >= 1")
    if endpoint_ref != "https://api.coinbase.com":
        raise BrowserIngressError("browser ingress endpoint must be exact Coinbase origin")
    if not wrapping_policy_ref or not purpose or not recipient_key_id:
        raise BrowserIngressError("wrapping policy, purpose and recipient key id are required")
    return {
        "object_id": object_id,
        "credential_version": credential_version,
        "wrapping_policy_ref": wrapping_policy_ref,
        "purpose": purpose,
        "endpoint_ref": endpoint_ref,
        "recipient_key_id": recipient_key_id,
    }


def _derive(shared_secret: bytes, *, salt: bytes, aad: bytes) -> bytes:
    info = b"stegverse-skap-browser-ingress-v1\x00" + hashlib.sha256(aad).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared_secret)


@dataclass(frozen=True)
class BrowserIngressEnvelope:
    envelope: dict[str, Any]

    @property
    def envelope_hash(self) -> str:
        return _sha(_canonical(self.envelope))


def seal_for_recipient(
    plaintext: bytearray,
    *,
    recipient_public_jwk: dict[str, Any],
    recipient_key_id: str,
    object_id: str,
    credential_version: int,
    wrapping_policy_ref: str,
    purpose: str,
    endpoint_ref: str,
) -> BrowserIngressEnvelope:
    if not isinstance(plaintext, bytearray) or not plaintext:
        raise BrowserIngressError("browser ingress plaintext must be a non-empty mutable bytearray")
    recipient = import_public_jwk(recipient_public_jwk)
    context = _context(
        object_id=object_id,
        credential_version=credential_version,
        wrapping_policy_ref=wrapping_policy_ref,
        purpose=purpose,
        endpoint_ref=endpoint_ref,
        recipient_key_id=recipient_key_id,
    )
    aad = _canonical(context)
    ephemeral_private = ec.generate_private_key(ec.SECP256R1())
    shared = bytearray(ephemeral_private.exchange(ec.ECDH(), recipient))
    salt, nonce = os.urandom(32), os.urandom(12)
    key = bytearray(_derive(bytes(shared), salt=salt, aad=aad))
    try:
        ciphertext = AESGCM(bytes(key)).encrypt(nonce, bytes(plaintext), aad)
        envelope = {
            "format": FORMAT,
            **context,
            "ephemeral_public_jwk": _public_jwk(ephemeral_private.public_key()),
            "kdf_salt_b64": _b64(salt),
            "nonce_b64": _b64(nonce),
            "aad_hash": _sha(aad),
            "ciphertext_b64": _b64(ciphertext),
            "plaintext_persisted": False,
            "device_private_key_persisted": False,
            "skap_private_key_exported": False,
            "authority_transfer": False,
        }
        return BrowserIngressEnvelope(envelope)
    finally:
        for index in range(len(plaintext)):
            plaintext[index] = 0
        for buffer in (shared, key):
            for index in range(len(buffer)):
                buffer[index] = 0


def resolve_at_skap(
    envelope: dict[str, Any],
    *,
    recipient_private_key: ec.EllipticCurvePrivateKey,
    expected_recipient_key_id: str,
    expected_object_id: str,
    expected_credential_version: int,
    expected_wrapping_policy_ref: str,
    expected_purpose: str,
    expected_endpoint_ref: str,
    consumer: Callable[[memoryview], T],
) -> T:
    if envelope.get("format") != FORMAT:
        raise BrowserIngressError("unsupported browser ingress format")
    for field in ("plaintext_persisted", "device_private_key_persisted", "skap_private_key_exported", "authority_transfer"):
        if envelope.get(field) is not False:
            raise BrowserIngressError(f"browser ingress {field} must be false")
    context = _context(
        object_id=expected_object_id,
        credential_version=expected_credential_version,
        wrapping_policy_ref=expected_wrapping_policy_ref,
        purpose=expected_purpose,
        endpoint_ref=expected_endpoint_ref,
        recipient_key_id=expected_recipient_key_id,
    )
    for key, value in context.items():
        if envelope.get(key) != value:
            raise BrowserIngressError(f"browser ingress {key} binding mismatch")
    aad = _canonical(context)
    if envelope.get("aad_hash") != _sha(aad):
        raise BrowserIngressError("browser ingress AAD hash mismatch")
    ephemeral = import_public_jwk(envelope.get("ephemeral_public_jwk") or {})
    salt, nonce, ciphertext = (_unb64(str(envelope.get(name, ""))) for name in ("kdf_salt_b64", "nonce_b64", "ciphertext_b64"))
    if len(salt) != 32 or len(nonce) != 12 or len(ciphertext) < 16:
        raise BrowserIngressError("browser ingress cryptographic dimensions invalid")
    shared = bytearray(recipient_private_key.exchange(ec.ECDH(), ephemeral))
    key = bytearray(_derive(bytes(shared), salt=salt, aad=aad))
    try:
        try:
            decrypted = AESGCM(bytes(key)).decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise BrowserIngressError("browser ingress authentication/decryption failed") from exc
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

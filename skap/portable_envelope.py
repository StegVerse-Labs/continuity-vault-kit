"""Portable wrapped SKAP root-key envelope (layout v2) reference implementation.

Approved design FINAL-REVIEW-009 (D2/D6) permits one wrapped root-key envelope at
``_Vault/SKAP/Root/wrapped-root-envelope.json``. The root key is never at rest in
plaintext: it is wrapped with AES-256-GCM under a PBKDF2-HMAC-SHA256 key derived
from an owner-held 160-bit recovery secret. Unwrapping happens only on an
authenticated per-attempt execution surface (the SKAP boundary) and only into an
in-process callback; the mutable key copy is wiped afterwards on a best-effort
basis, matching ``TVCResidentFileKeyProvider``.

KV keeps ciphertext and non-secret evidence custody only. Credential authority
remains TV/TVC. This module creates no runtime, performs no genesis, persists
nothing, and logs nothing.

The JavaScript loader (skap/loader/kv-skap-loader.html) must reproduce this
module byte-for-byte on fixtures/skap/portable-envelope-v2.vectors.json.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from typing import Any, Callable, TypeVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from skap.crypto_boundary import SealedMaterial, resolve_transiently, seal

T = TypeVar("T")

ENVELOPE_SCHEMA = "stegverse.skap.wrapped-root-envelope/v2"
GENESIS_TRANSITION = "KV_SKAP_TRUST_GENESIS"
KDF_NAME = "PBKDF2-HMAC-SHA256"
AEAD_NAME = "AES-256-GCM"
MIN_PBKDF2_ITERATIONS = 600000
RECOVERY_SECRET_BYTES = 20
ROOT_KEY_BYTES = 32
KDF_SALT_BYTES = 16
AEAD_NONCE_BYTES = 12
ROOT_KEY_ID_DOMAIN = b"stegverse.skap.root-key-id/v1\x00"
KV_ENVELOPE_PATH = "_Vault/SKAP/Root/wrapped-root-envelope.json"
MAX_SAFE_INTEGER = 2**53 - 1  # JS Number.MAX_SAFE_INTEGER; larger integers fail closed

# Sealed-object bindings shared with the loader (crypto_boundary seal format).
PROVIDER_CREDENTIAL_PURPOSE = "provider-credential"
BOOTSTRAP_ANCHOR_PURPOSE = "kv-skap-bootstrap-anchor"
BOOTSTRAP_ANCHOR_OBJECT_ID = "skap://kv-skap/bootstrap-anchor"
BOOTSTRAP_ANCHOR_ENDPOINT_REF = "kv://_Vault/SKAP/Root/bootstrap-anchor.sealed.json"
PROVIDER_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/responses",
}
ANCHOR_FIELDS = ("genesis_manifest_digest", "kv_identity", "loader_sha256", "loader_source", "policy_hash", "predecessor_state")
LOADER_SOURCE_FIELDS = ("commit", "path", "repository")


class PortableEnvelopeError(ValueError):
    """Fail-closed error carrying a stable ``code`` shared with the JS loader vectors."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------
# Canonical JSON (shared with JS): sorted keys, no whitespace, ASCII only,
# integers only. Non-ASCII input is rejected, never escaped.
# ---------------------------------------------------------------------------

def _check_canonical(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise PortableEnvelopeError("CANONICAL_UNSAFE_INTEGER", "canonical JSON integers must be within +/-(2**53 - 1)")
        return
    if isinstance(value, float):
        raise PortableEnvelopeError("CANONICAL_NON_INTEGER", "canonical JSON forbids non-integer numbers")
    if isinstance(value, str):
        if not value.isascii():
            raise PortableEnvelopeError("CANONICAL_NON_ASCII", "canonical JSON forbids non-ASCII strings")
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _check_canonical(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PortableEnvelopeError("CANONICAL_TYPE", "canonical JSON object keys must be strings")
            if not key.isascii():
                raise PortableEnvelopeError("CANONICAL_NON_ASCII", "canonical JSON forbids non-ASCII keys")
            _check_canonical(item)
        return
    raise PortableEnvelopeError("CANONICAL_TYPE", f"canonical JSON forbids {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    _check_canonical(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(bytes(data)).decode("ascii").rstrip("=")


def unb64url(value: Any) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "invalid base64url field")
    try:
        return base64.urlsafe_b64decode((value + "=" * ((4 - len(value) % 4) % 4)).encode("ascii"))
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "invalid base64url field") from exc


def _wipe(buffer: bytearray) -> None:
    for index in range(len(buffer)):
        buffer[index] = 0


# ---------------------------------------------------------------------------
# Recovery secret: 20 random bytes, RFC 4648 base32 without padding (32 chars),
# shown in groups of 4 separated by "-".
# ---------------------------------------------------------------------------

def generate_recovery_secret() -> bytearray:
    return bytearray(os.urandom(RECOVERY_SECRET_BYTES))


def format_recovery_secret(secret: bytes | bytearray | memoryview) -> str:
    if len(secret) != RECOVERY_SECRET_BYTES:
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must be exactly 20 bytes")
    text = base64.b32encode(bytes(secret)).decode("ascii")
    return "-".join(text[i:i + 4] for i in range(0, len(text), 4))


def parse_recovery_secret(text: str) -> bytearray:
    if not isinstance(text, str):
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must be text")
    compact = "".join(ch for ch in text if ch != "-" and not ch.isspace()).upper()
    if len(compact) != 32 or not compact.isascii():
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must decode to exactly 20 bytes")
    try:
        raw = base64.b32decode(compact.encode("ascii"), casefold=False)
    except (binascii.Error, ValueError) as exc:
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret is not valid base32") from exc
    if len(raw) != RECOVERY_SECRET_BYTES:
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must decode to exactly 20 bytes")
    return bytearray(raw)


# ---------------------------------------------------------------------------
# Root key and wrapped envelope
# ---------------------------------------------------------------------------

def generate_root_key() -> bytearray:
    return bytearray(os.urandom(ROOT_KEY_BYTES))


def root_key_id(root_key: bytes | bytearray | memoryview) -> str:
    if len(root_key) != ROOT_KEY_BYTES:
        raise PortableEnvelopeError("ROOT_KEY_INVALID", "root key must be exactly 256 bits")
    return "sha256:" + hashlib.sha256(ROOT_KEY_ID_DOMAIN + bytes(root_key)).hexdigest()


def _require_digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71 or any(c not in "0123456789abcdef" for c in value[7:]):
        raise PortableEnvelopeError("FIELD_INVALID", f"{name} must be a sha256:<64 lowercase hex> digest")
    return value


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise PortableEnvelopeError("FIELD_INVALID", f"{name} must be non-empty ASCII text")
    return value


def envelope_aad(*, kv_identity: str, root_key_id_value: str, kdf: dict[str, Any], policy_hash: str) -> bytes:
    return canonical_json({
        "schema": ENVELOPE_SCHEMA,
        "kv_identity": kv_identity,
        "root_key_id": root_key_id_value,
        "kdf": kdf,
        "policy_hash": policy_hash,
    })


def _derive_wrapping_key(recovery_secret: bytes | bytearray | memoryview, salt: bytes, iterations: int) -> bytearray:
    if len(recovery_secret) != RECOVERY_SECRET_BYTES:
        raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must be exactly 20 bytes")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < MIN_PBKDF2_ITERATIONS:
        raise PortableEnvelopeError("KDF_DOWNGRADE", "PBKDF2 iterations below 600000 refused (downgrade)")
    if len(salt) != KDF_SALT_BYTES:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "KDF salt must be exactly 16 bytes")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=bytes(salt), iterations=iterations)
    return bytearray(kdf.derive(bytes(recovery_secret)))


def wrap_root_key(
    root_key: bytes | bytearray | memoryview,
    recovery_secret: bytes | bytearray | memoryview,
    *,
    kv_identity: str,
    policy_hash: str,
    iterations: int = MIN_PBKDF2_ITERATIONS,
    _test_vector_salt: bytes | None = None,
    _test_vector_nonce: bytes | None = None,
) -> dict[str, Any]:
    """Wrap a 256-bit root key; returns a ciphertext-only envelope.

    ``_test_vector_salt`` / ``_test_vector_nonce`` are TEST-VECTOR-ONLY and default
    to None (fresh ``os.urandom``). Both must be supplied together.
    """
    _require_text(kv_identity, "kv_identity")
    _require_digest(policy_hash, "policy_hash")
    key_id = root_key_id(root_key)
    if _test_vector_salt is None and _test_vector_nonce is None:
        salt = os.urandom(KDF_SALT_BYTES)
        nonce = os.urandom(AEAD_NONCE_BYTES)
    else:
        if not isinstance(_test_vector_salt, bytes) or not isinstance(_test_vector_nonce, bytes) or len(_test_vector_salt) != KDF_SALT_BYTES or len(_test_vector_nonce) != AEAD_NONCE_BYTES:
            raise PortableEnvelopeError("TEST_VECTOR_INJECTION_INVALID", "test-vector salt and nonce must be supplied together with exact lengths")
        salt, nonce = _test_vector_salt, _test_vector_nonce
    kdf = {"name": KDF_NAME, "iterations": iterations, "salt_b64url": b64url(salt)}
    aad = envelope_aad(kv_identity=kv_identity, root_key_id_value=key_id, kdf=kdf, policy_hash=policy_hash)
    wrapping_key = _derive_wrapping_key(recovery_secret, salt, iterations)
    try:
        ciphertext = AESGCM(bytes(wrapping_key)).encrypt(nonce, bytes(root_key), aad)
    finally:
        _wipe(wrapping_key)
    return {
        "schema": ENVELOPE_SCHEMA,
        "kv_identity": kv_identity,
        "root_key_id": key_id,
        "policy_hash": policy_hash,
        "created_by_transition": GENESIS_TRANSITION,
        "kdf": kdf,
        "aead": {"name": AEAD_NAME, "nonce_b64url": b64url(nonce), "ciphertext_b64url": b64url(ciphertext)},
    }


def validate_envelope_shape(envelope: Any) -> None:
    if not isinstance(envelope, dict):
        raise PortableEnvelopeError("ENVELOPE_INVALID", "envelope must be an object")
    expected_keys = {"schema", "kv_identity", "root_key_id", "policy_hash", "created_by_transition", "kdf", "aead"}
    if set(envelope) != expected_keys:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "envelope fields do not match schema")
    if envelope["schema"] != ENVELOPE_SCHEMA:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "unsupported envelope schema")
    if envelope["created_by_transition"] != GENESIS_TRANSITION:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "envelope not created by KV_SKAP_TRUST_GENESIS")
    _require_text(envelope["kv_identity"], "kv_identity")
    _require_digest(envelope["root_key_id"], "root_key_id")
    _require_digest(envelope["policy_hash"], "policy_hash")
    kdf, aead = envelope["kdf"], envelope["aead"]
    if not isinstance(kdf, dict) or set(kdf) != {"name", "iterations", "salt_b64url"} or kdf["name"] != KDF_NAME:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "unsupported KDF")
    if isinstance(kdf["iterations"], bool) or not isinstance(kdf["iterations"], int) or kdf["iterations"] < MIN_PBKDF2_ITERATIONS:
        raise PortableEnvelopeError("KDF_DOWNGRADE", "PBKDF2 iterations below 600000 refused (downgrade)")
    if not isinstance(aead, dict) or set(aead) != {"name", "nonce_b64url", "ciphertext_b64url"} or aead["name"] != AEAD_NAME:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "unsupported AEAD")


def unwrap_root_key_transiently(
    envelope: dict[str, Any],
    recovery_secret: bytes | bytearray | memoryview,
    consumer: Callable[[memoryview], T],
    *,
    expected_kv_identity: str | None = None,
    expected_policy_hash: str | None = None,
    expected_root_key_id: str | None = None,
) -> T:
    """Unwrap into an in-process callback only; the key copy is wiped afterwards."""
    validate_envelope_shape(envelope)
    if expected_kv_identity is not None and envelope["kv_identity"] != expected_kv_identity:
        raise PortableEnvelopeError("BINDING_MISMATCH", "envelope kv_identity binding mismatch")
    if expected_policy_hash is not None and envelope["policy_hash"] != expected_policy_hash:
        raise PortableEnvelopeError("BINDING_MISMATCH", "envelope policy_hash binding mismatch")
    if expected_root_key_id is not None and envelope["root_key_id"] != expected_root_key_id:
        raise PortableEnvelopeError("BINDING_MISMATCH", "envelope root_key_id binding mismatch")
    kdf, aead = envelope["kdf"], envelope["aead"]
    salt = unb64url(kdf["salt_b64url"])
    nonce = unb64url(aead["nonce_b64url"])
    ciphertext = unb64url(aead["ciphertext_b64url"])
    if len(nonce) != AEAD_NONCE_BYTES or len(ciphertext) != ROOT_KEY_BYTES + 16:
        raise PortableEnvelopeError("ENVELOPE_INVALID", "envelope cryptographic dimensions invalid")
    aad = envelope_aad(kv_identity=envelope["kv_identity"], root_key_id_value=envelope["root_key_id"], kdf=kdf, policy_hash=envelope["policy_hash"])
    wrapping_key = _derive_wrapping_key(recovery_secret, salt, kdf["iterations"])
    try:
        decrypted = AESGCM(bytes(wrapping_key)).decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise PortableEnvelopeError("ENVELOPE_AUTH_FAILED", "envelope authentication/decryption failed") from exc
    finally:
        _wipe(wrapping_key)
    key = bytearray(decrypted)
    del decrypted
    try:
        if root_key_id(key) != envelope["root_key_id"]:
            raise PortableEnvelopeError("ENVELOPE_AUTH_FAILED", "unwrapped root key does not match root_key_id")
        return consumer(memoryview(key))
    finally:
        _wipe(key)


class KVWrappedEnvelopeKeyProvider:
    """KeyProvider over a KV-held wrapped root envelope (layout v2).

    The recovery secret is held only as a mutable buffer for this provider's
    lifetime; call ``close()`` (or use as a context manager) to wipe it. Root key
    bytes exist only inside ``with_key``'s callback and are wiped afterwards.
    """

    def __init__(self, envelope: dict[str, Any], recovery_secret: bytes | bytearray | memoryview, *, expected_kv_identity: str | None = None, expected_policy_hash: str | None = None):
        validate_envelope_shape(envelope)
        if len(recovery_secret) != RECOVERY_SECRET_BYTES:
            raise PortableEnvelopeError("RECOVERY_SECRET_INVALID", "recovery secret must be exactly 20 bytes")
        self._envelope = json.loads(canonical_json(envelope))
        self._secret = bytearray(recovery_secret)
        self._expected_kv_identity = expected_kv_identity
        self._expected_policy_hash = expected_policy_hash

    @property
    def authority_ref(self) -> str:
        return f"kv-wrapped://{self._envelope['root_key_id']}"

    def with_key(self, consumer: Callable[[memoryview], T]) -> T:
        if not any(self._secret):
            raise PortableEnvelopeError("RECOVERY_SECRET_WIPED", "recovery secret has been wiped")
        return unwrap_root_key_transiently(
            self._envelope,
            self._secret,
            consumer,
            expected_kv_identity=self._expected_kv_identity,
            expected_policy_hash=self._expected_policy_hash,
        )

    def close(self) -> None:
        _wipe(self._secret)

    def __enter__(self) -> "KVWrappedEnvelopeKeyProvider":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Sealed objects under the root (existing crypto_boundary seal format)
# ---------------------------------------------------------------------------

def provider_credential_bindings(provider: str, *, policy_hash: str, root_key_id_value: str, credential_version: int = 1) -> dict[str, Any]:
    if provider not in PROVIDER_ENDPOINTS:
        raise PortableEnvelopeError("FIELD_INVALID", "provider must be openai or anthropic")
    _require_digest(policy_hash, "policy_hash")
    _require_digest(root_key_id_value, "root_key_id")
    return {
        "object_id": f"skap://provider/{provider}/api-key",
        "credential_version": credential_version,
        "wrapping_policy_ref": policy_hash,
        "purpose": PROVIDER_CREDENTIAL_PURPOSE,
        "endpoint_ref": PROVIDER_ENDPOINTS[provider],
        "key_authority_ref": f"kv-wrapped://{root_key_id_value}",
    }


def bootstrap_anchor_bindings(*, policy_hash: str, root_key_id_value: str) -> dict[str, Any]:
    _require_digest(policy_hash, "policy_hash")
    _require_digest(root_key_id_value, "root_key_id")
    return {
        "object_id": BOOTSTRAP_ANCHOR_OBJECT_ID,
        "credential_version": 1,
        "wrapping_policy_ref": policy_hash,
        "purpose": BOOTSTRAP_ANCHOR_PURPOSE,
        "endpoint_ref": BOOTSTRAP_ANCHOR_ENDPOINT_REF,
        "key_authority_ref": f"kv-wrapped://{root_key_id_value}",
    }


def build_bootstrap_anchor(
    *,
    loader_sha256: str,
    loader_repository: str,
    loader_commit: str,
    loader_path: str,
    policy_hash: str,
    kv_identity: str,
    genesis_manifest_digest: str,
    predecessor_state: str,
) -> bytes:
    """Return the canonical JSON plaintext of the bootstrap anchor (non-secret content)."""
    if not isinstance(loader_sha256, str) or len(loader_sha256) != 64 or any(c not in "0123456789abcdef" for c in loader_sha256):
        raise PortableEnvelopeError("FIELD_INVALID", "loader_sha256 must be 64 lowercase hex characters")
    anchor = {
        "loader_sha256": loader_sha256,
        "loader_source": {
            "repository": _require_text(loader_repository, "loader_repository"),
            "commit": _require_text(loader_commit, "loader_commit"),
            "path": _require_text(loader_path, "loader_path"),
        },
        "policy_hash": _require_digest(policy_hash, "policy_hash"),
        "kv_identity": _require_text(kv_identity, "kv_identity"),
        "genesis_manifest_digest": _require_digest(genesis_manifest_digest, "genesis_manifest_digest"),
        "predecessor_state": _require_text(predecessor_state, "predecessor_state"),
    }
    return canonical_json(anchor)


def parse_bootstrap_anchor(plaintext: bytes | bytearray | memoryview) -> dict[str, Any]:
    try:
        anchor = json.loads(bytes(plaintext).decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortableEnvelopeError("ANCHOR_INVALID", "bootstrap anchor is not canonical ASCII JSON") from exc
    if not isinstance(anchor, dict) or tuple(sorted(anchor)) != ANCHOR_FIELDS:
        raise PortableEnvelopeError("ANCHOR_INVALID", "bootstrap anchor fields do not match")
    if not isinstance(anchor["loader_source"], dict) or tuple(sorted(anchor["loader_source"])) != LOADER_SOURCE_FIELDS:
        raise PortableEnvelopeError("ANCHOR_INVALID", "bootstrap anchor loader_source fields do not match")
    if canonical_json(anchor) != bytes(plaintext):
        raise PortableEnvelopeError("ANCHOR_INVALID", "bootstrap anchor is not in canonical form")
    return anchor


def seal_bootstrap_anchor(anchor_plaintext: bytes, *, key_provider: Any, policy_hash: str) -> SealedMaterial:
    bindings = bootstrap_anchor_bindings(policy_hash=policy_hash, root_key_id_value=_root_key_id_from_provider(key_provider))
    parse_bootstrap_anchor(anchor_plaintext)
    return key_provider.with_key(lambda key: seal(anchor_plaintext, root_key=key, **bindings))


def open_bootstrap_anchor(sealed: dict[str, Any], *, key_provider: Any, policy_hash: str) -> dict[str, Any]:
    bindings = bootstrap_anchor_bindings(policy_hash=policy_hash, root_key_id_value=_root_key_id_from_provider(key_provider))
    # The anchor is non-secret by design, so returning its parsed content is permitted.
    return key_provider.with_key(lambda key: resolve_transiently(
        sealed,
        root_key=key,
        expected_object_id=bindings["object_id"],
        expected_credential_version=bindings["credential_version"],
        expected_wrapping_policy_ref=bindings["wrapping_policy_ref"],
        expected_purpose=bindings["purpose"],
        expected_endpoint_ref=bindings["endpoint_ref"],
        expected_key_authority_ref=bindings["key_authority_ref"],
        consumer=lambda view: parse_bootstrap_anchor(bytes(view)),
    ))


def _root_key_id_from_provider(key_provider: Any) -> str:
    ref = getattr(key_provider, "authority_ref", "")
    if not isinstance(ref, str) or not ref.startswith("kv-wrapped://"):
        raise PortableEnvelopeError("ANCHOR_INVALID", "bootstrap anchor requires a kv-wrapped:// key provider")
    return ref[len("kv-wrapped://"):]

"""TEST-ONLY Ed25519 signer (RFC 8032 section 5.1.6) for the node-receipt producer tests.

It exists only so the tests can make signatures for llm_adapter.ed25519_verify
to check. The production code has no signing function and never sees a private
key. The only seed here is TEST_SEED, a public constant derived from a label, so
it is not a secret, a credential or anyone's key. Never use it outside tests.
"""
from __future__ import annotations

import base64
import hashlib

from llm_adapter import ed25519_verify as ev

TEST_SEED = hashlib.sha256(b"llm-adapter node-receipt tests: public fixture seed, not a secret").digest()


def _compress(point) -> bytes:
    x, y, z, _ = point
    zi = pow(z, ev._P - 2, ev._P)
    x, y = x * zi % ev._P, y * zi % ev._P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _expand(seed: bytes):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(seed: bytes = TEST_SEED) -> bytes:
    a, _ = _expand(seed)
    return _compress(ev._mul(a, ev._G))


def sign(message: bytes, seed: bytes = TEST_SEED) -> bytes:
    a, prefix = _expand(seed)
    pk = _compress(ev._mul(a, ev._G))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % ev._L
    big_r = _compress(ev._mul(r, ev._G))
    h = int.from_bytes(hashlib.sha512(big_r + pk + message).digest(), "little") % ev._L
    return big_r + int.to_bytes((r + h * a) % ev._L, 32, "little")


def public_key_b64(seed: bytes = TEST_SEED) -> str:
    return base64.b64encode(public_key(seed)).decode()


def sign_b64(message: bytes, seed: bytes = TEST_SEED) -> str:
    return base64.b64encode(sign(message, seed)).decode()

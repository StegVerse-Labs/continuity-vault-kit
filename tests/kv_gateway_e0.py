"""TEST-ONLY gateway storage stand-ins for the KV gateway storage adapter interface (E0, stdlib only).

``E0MemoryGateway`` is an in-memory GatewayStorageAdapter. ``E0Opener`` is a TEST-ONLY XOR keystream over a public
fixed seed: it is NOT encryption and exists only so the sealed-blob framing can be exercised without a cipher. No real
Google Drive (or other provider) client is built anywhere.
"""
from __future__ import annotations

import hashlib
from typing import Any

from runtime import kv_gateway_storage as gw

E0_GATEWAY_REF = "e0-test-only-gateway-storage"
_E0_KEY = hashlib.sha256(b"kv gateway E0: TEST-ONLY public keystream seed (not encryption)").digest()


def _keystream(n: int) -> bytes:
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(_E0_KEY + i.to_bytes(8, "big")).digest()
        i += 1
    return out[:n]


def e0_seal(plain: bytes) -> bytes:
    body = bytes(a ^ b for a, b in zip(b"\x00" + plain, _keystream(len(plain) + 1)))
    return gw.SEALED_MAGIC + body


class E0Opener(gw.BlobOpener):
    def open(self, blob: bytes) -> bytes:
        body = blob[len(gw.SEALED_MAGIC):]
        return bytes(a ^ b for a, b in zip(body, _keystream(len(body))))[1:]


class E0MemoryGateway(gw.GatewayStorageAdapter):
    adapter_ref = E0_GATEWAY_REF

    def __init__(self) -> None:
        self.blobs: dict[str, dict[str, bytes]] = {}
        self.heads: dict[str, str | None] = {}

    def put(self, location: str, blob: bytes) -> str:
        address = gw.blob_sha256(blob)
        self.blobs.setdefault(location, {})[address] = bytes(blob)
        return address

    def get(self, location: str, blob_sha256: str) -> Any:
        return self.blobs.get(location, {})[blob_sha256]

    def list(self, location: str) -> Any:
        return list(self.blobs.get(location, {}))

    def get_head(self, location: str) -> Any:
        return self.heads.get(location)

    def advance_head(self, location: str, expected_previous: str | None, new: str) -> bool:
        if self.heads.get(location) != expected_previous:
            return False
        self.heads[location] = new
        return True

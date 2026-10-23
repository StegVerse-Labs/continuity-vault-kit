"""KV gateway storage adapter interface (E0, stdlib only, no new dependency).

Rigel's KV rule (Coordination, StegVerse-org/.github#160 comment 6372045430): KV exists only as a governed layer over
storage the user already owns (for example their Google Drive), connected through a GATEWAY node. KV keeps its own
ledger and its own InTr endpoint (comment 6371986288). The storage holds only encrypted contents, and the external
storage's own records never cross into KV.

Final (Rigel, #160 comment 6372216673): KV's ledger and contents live as encrypted, content-addressed objects in the
user's storage, verified on KV's side; cloud storage behind a GATEWAY is an accepted existing dependency. The
interface depends on no single provider (Google Drive is one backing, not the contract); multi-provider redundancy is
a later, separately registered task. Order lives in KV's ledger (the head pointer KV verifies), never in a provider's
file history. Design: docs/kv-gateway-storage-adapter.md.

This module is the interface only. It does not build a Google Drive (or any other) client.

* ``GatewayStorageAdapter``: the three operations a gateway storage node offers, over opaque sealed blobs keyed by a
  ``##_<name>`` storage location and content-addressed by sha256: ``put(location, blob) -> blob_sha256``,
  ``get(location, blob_sha256) -> blob``, ``list(location) -> [blob_sha256, ...]``, plus the append-only head pointer
  at ``<location>/HEAD``: ``get_head(location) -> blob_sha256 | None`` and
  ``advance_head(location, expected_previous, new) -> bool`` (compare-and-swap; ``new`` must already be stored).
  Nothing else crosses. This is the seam a non-git reader (Lane B, store_type GATEWAY_ENCRYPTED_BLOB) consumes.
* ``NullGatewayStorageAdapter``: the production binding while no gateway storage is provisioned. Every operation is a
  six-field FAIL_CLOSED SVKV_GATEWAY_STORAGE_NOT_PROVISIONED (owning goal ECOSYSTEM-OWN-KV-001).
* ``GatewayStore``: KV's side of the boundary. It checks every value an adapter hands back: the location name, the
  content address (sha256 of the bytes), the sealed-blob framing (no plaintext), and that a listing is only blob
  addresses. External storage metadata or records (file ids, owners, revisions, modified times, sharing, ...) are
  refused as KV input with EXTERNAL_STORAGE_RECORD_REFUSED. KV computes every ledger receipt from its own side only.
* ``BlobOpener``: KV-side opening of a sealed blob with a key held under TV/TVC custody. ``NullBlobOpener`` is the
  production binding while no key is custodied (KV_LEDGER_BLOB_KEY_NOT_CUSTODIED). KV itself never imports
  ``cryptography``; the cipher is whatever SKAP-UNDECLARED-CRYPTOGRAPHY-001 settles, behind this interface.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

FAIL_CLOSED = "FAIL_CLOSED"
GOAL = "ECOSYSTEM-OWN-KV-001 (SVKV; StegVerse-org/.github#160 comment 6372045430)"
DESIGN = "docs/kv-gateway-storage-adapter.md"
#: ``##_<name>``: two digits keep data-location names distinct for human review; the name is the storage location
LOCATION_RE = re.compile(r"^[0-9]{2}_[A-Za-z0-9][A-Za-z0-9_]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
#: every blob KV writes starts with this framing; what follows is ciphertext KV's opener alone can open
SEALED_MAGIC = b"stegverse.kv-sealed-blob/v1\n"
NOT_PROVISIONED = "SVKV_GATEWAY_STORAGE_NOT_PROVISIONED"
EXTERNAL_RECORD = "EXTERNAL_STORAGE_RECORD_REFUSED"
KEY_NOT_CUSTODIED = "KV_LEDGER_BLOB_KEY_NOT_CUSTODIED"
RETRY = "runtime.kv_gateway_storage.GatewayStore(<registered gateway storage adapter>).list_blobs(<##_name>)"


class GatewayStorageRefused(Exception):
    """Raised by an adapter or by GatewayStore; ``refusal`` is the six-field FAIL_CLOSED."""

    def __init__(self, refusal: Mapping[str, Any]):
        super().__init__(refusal.get("failure_code"))
        self.refusal = dict(refusal)


def refusal(code: str, klass: str, predicate: str, repair: str, next_attempt: str, detail: str,
            owner: str = GOAL, retry: str = RETRY) -> dict[str, Any]:
    return {"disposition": FAIL_CLOSED, "failure_code": code, "failure_class": klass, "failed_predicate": predicate,
            "required_evidence_or_repair": repair, "retry_entrypoint": retry, "owning_existing_goal": owner,
            "next_attempt": next_attempt, "detail": detail, "ledger_written": False, "authority_effect": "NONE"}


def not_provisioned(detail: str = "no gateway storage adapter is registered for this KV") -> dict[str, Any]:
    return refusal(NOT_PROVISIONED, "B", "KV_GATEWAY_STORAGE_PROVISIONED",
                   "the SVKV backing storage (the Google Drive of the ecosystem account StegVerse@gmail.com, being set "
                   "up by Rigel) provisioned and connected through a registered GATEWAY node, recorded as a "
                   "gateway_storage_adapter_ref in .stegverse/kv-gateway/storage-binding.v1.json",
                   "on the gateway registration once the Drive is provisioned; event-driven, no polling", detail)


def blob_sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def check_location(location: Any) -> str | None:
    if not isinstance(location, str) or not LOCATION_RE.match(location):
        return f"storage location {location!r} is not a ##_<name> location"
    return None


def plaintext_failure(blob: Any) -> str | None:
    """None for a sealed blob; else why it is not one. KV never stores or reads plaintext through a gateway."""
    if not isinstance(blob, (bytes, bytearray)):
        return f"blob is {type(blob).__name__}, not bytes"
    if not bytes(blob).startswith(SEALED_MAGIC) or len(blob) == len(SEALED_MAGIC):
        return "blob is not a stegverse.kv-sealed-blob/v1 (plaintext or foreign bytes)"
    body = bytes(blob)[len(SEALED_MAGIC):]
    try:
        json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return "the sealed framing wraps plaintext JSON"


class GatewayStorageAdapter:
    """What a gateway storage node offers KV. Implementations hold no KV key and see only sealed blobs."""

    adapter_ref: str | None = None

    def put(self, location: str, blob: bytes) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def get(self, location: str, blob_sha256: str) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def list(self, location: str) -> list[str]:  # pragma: no cover - interface
        raise NotImplementedError

    def get_head(self, location: str) -> str | None:  # pragma: no cover - interface
        raise NotImplementedError

    def advance_head(self, location: str, expected_previous: str | None, new: str) -> bool:  # pragma: no cover
        raise NotImplementedError


class NullGatewayStorageAdapter(GatewayStorageAdapter):
    """Production binding until the gateway storage is provisioned: every operation fails closed."""

    adapter_ref = None

    def put(self, location: str, blob: bytes) -> str:
        raise GatewayStorageRefused(not_provisioned())

    def get(self, location: str, blob_sha256: str) -> bytes:
        raise GatewayStorageRefused(not_provisioned())

    def list(self, location: str) -> list[str]:
        raise GatewayStorageRefused(not_provisioned())

    def get_head(self, location: str) -> str | None:
        raise GatewayStorageRefused(not_provisioned())

    def advance_head(self, location: str, expected_previous: str | None, new: str) -> bool:
        raise GatewayStorageRefused(not_provisioned())


def _external(detail: str) -> dict[str, Any]:
    return refusal(EXTERNAL_RECORD, "C", "EXTERNAL_STORAGE_RECORDS_NEVER_CROSS_INTO_KV",
                   "the gateway hands KV only content-addressed sealed blobs and their sha256 addresses; KV computes "
                   "every ledger receipt from its own side", "never: an external record is not KV ledger input",
                   detail)


class GatewayStore:
    """KV's side of the gateway boundary. Every method returns (value, None) or (None, six-field refusal)."""

    def __init__(self, adapter: Any):
        self.adapter = adapter

    def _call(self, op: str, *args: Any) -> tuple[Any, dict[str, Any] | None]:
        if not isinstance(self.adapter, GatewayStorageAdapter):
            return None, _external(f"{type(self.adapter).__name__} is not a GatewayStorageAdapter")
        try:
            return getattr(self.adapter, op)(*args), None
        except GatewayStorageRefused as exc:
            return None, exc.refusal
        except Exception as exc:  # an adapter failure is never an ALLOW
            return None, refusal("KV_GATEWAY_STORAGE_UNREADABLE", "D", "KV_GATEWAY_STORAGE_READABLE",
                                 "a reachable gateway storage node", "when the gateway is reachable",
                                 f"{op}: {type(exc).__name__}")

    def put_blob(self, location: str, blob: bytes) -> tuple[str | None, dict[str, Any] | None]:
        bad = check_location(location)
        if bad:
            return None, refusal("KV_STORAGE_LOCATION_INVALID", "A", "KV_STORAGE_LOCATION_IS_##_NAME",
                                 "a ##_<name> location", "on the corrected call", bad)
        bad = plaintext_failure(blob)
        if bad:
            return None, refusal("KV_GATEWAY_BLOB_NOT_SEALED", "A", "KV_GATEWAY_HOLDS_ONLY_ENCRYPTED_CONTENTS",
                                 "a stegverse.kv-sealed-blob/v1 sealed by KV's opener key", "on a sealed blob", bad)
        address, failed = self._call("put", location, bytes(blob))
        if failed:
            return None, failed
        if address != blob_sha256(bytes(blob)):
            return None, _external(f"put returned {address!r}, not the blob's sha256")
        return address, None

    def get_blob(self, location: str, address: str) -> tuple[bytes | None, dict[str, Any] | None]:
        if check_location(location) or not isinstance(address, str) or not SHA_RE.match(address):
            return None, refusal("KV_STORAGE_LOCATION_INVALID", "A", "KV_STORAGE_LOCATION_IS_##_NAME",
                                 "a ##_<name> location and a sha256 hex address", "on the corrected call",
                                 f"{location!r} {address!r}")
        blob, failed = self._call("get", location, address)
        if failed:
            return None, failed
        if not isinstance(blob, (bytes, bytearray)):
            return None, _external(f"get returned {type(blob).__name__} (an external record), not sealed bytes")
        if blob_sha256(bytes(blob)) != address:
            return None, _external(f"the blob at {address} does not hash to its address")
        bad = plaintext_failure(blob)
        if bad:
            return None, _external(bad)
        return bytes(blob), None

    def list_blobs(self, location: str) -> tuple[list[str] | None, dict[str, Any] | None]:
        bad = check_location(location)
        if bad:
            return None, refusal("KV_STORAGE_LOCATION_INVALID", "A", "KV_STORAGE_LOCATION_IS_##_NAME",
                                 "a ##_<name> location", "on the corrected call", bad)
        listed, failed = self._call("list", location)
        if failed:
            return None, failed
        if not isinstance(listed, list) or not all(isinstance(a, str) and SHA_RE.match(a) for a in listed):
            return None, _external("the listing carries something other than sha256 blob addresses (external "
                                   "storage metadata or records)")
        return sorted(set(listed)), None


    def head(self, location: str) -> tuple[str | None, dict[str, Any] | None]:
        """The head pointer's blob address (None for an empty location), or a refusal."""
        bad = check_location(location)
        if bad:
            return None, refusal("KV_STORAGE_LOCATION_INVALID", "A", "KV_STORAGE_LOCATION_IS_##_NAME",
                                 "a ##_<name> location", "on the corrected call", bad)
        head, failed = self._call("get_head", location)
        if failed:
            return None, failed
        if head is not None and not (isinstance(head, str) and SHA_RE.match(head)):
            return None, _external("the head pointer is not a sha256 blob address (an external record)")
        return head, None

    def advance(self, location: str, expected_previous: str | None, new: str) -> tuple[bool, dict[str, Any] | None]:
        """Append-only: move the head pointer from expected_previous to new, a blob already stored here."""
        listed, failed = self.list_blobs(location)
        if failed:
            return False, failed
        if new not in listed or (expected_previous is not None and expected_previous not in listed):
            return False, refusal("KV_HEAD_POINTER_NOT_APPEND_ONLY", "A", "KV_HEAD_POINTER_APPEND_ONLY",
                                  "advance to a stored blob from the current head", "on the corrected call",
                                  f"{expected_previous!r} -> {new!r}")
        moved, failed = self._call("advance_head", location, expected_previous, new)
        if failed:
            return False, failed
        if moved is not True:
            return False, refusal("KV_HEAD_POINTER_NOT_APPEND_ONLY", "A", "KV_HEAD_POINTER_APPEND_ONLY",
                                  "advance from the current head (compare-and-swap)", "after re-reading the head",
                                  "the head moved or the adapter refused")
        return True, None


class BlobOpener:
    """KV-side opening of a sealed blob under a TV/TVC-custodied key. Returns the plaintext bytes."""

    def open(self, blob: bytes) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


class NullBlobOpener(BlobOpener):
    def open(self, blob: bytes) -> bytes:
        raise GatewayStorageRefused(refusal(
            KEY_NOT_CUSTODIED, "B", "KV_LEDGER_BLOB_KEY_CUSTODIED_BY_TV_TVC",
            "a wrapped KV ledger data key whose root key stays in TV/TVC custody (G8, #167 comment 6372136062; bots "
            "never hold keys), unwrapped only by a custody transition, with the cipher SKAP-UNDECLARED-"
            "CRYPTOGRAPHY-001 settles", "when TV/TVC custodies the KV ledger blob key; event-driven",
            "no KV ledger blob key is custodied", owner=f"{GOAL}; dependency owner TV/TVC + Lane C"))


__all__ = ["BlobOpener", "GatewayStorageAdapter", "GatewayStorageRefused", "GatewayStore", "NullBlobOpener",
           "NullGatewayStorageAdapter", "SEALED_MAGIC", "blob_sha256", "check_location", "not_provisioned",
           "plaintext_failure", "refusal"]

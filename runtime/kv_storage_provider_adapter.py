"""Provider-neutral storage adapter contract for KnowledgeVault.

Adapters in this module construct normalized provider-operation intents only. They do
not authenticate, open provider sessions, read/write remote storage, synchronize data,
or grant Interlock/InTr authority. Provider credentials remain outside ordinary KV state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Protocol


SUPPORTED_OPERATIONS = (
    "CONNECT",
    "VERIFY",
    "READ",
    "WRITE",
    "SYNC",
    "DISCONNECT",
)
REQUEST_SCHEMA = "stegverse.kv.storage-provider-operation-request/v1"


class KVStorageProviderError(ValueError):
    pass


class KVStorageProviderAdapter(Protocol):
    provider_id: str
    display_name: str
    provider_family: str

    def supports(self, operation: str) -> bool: ...
    def descriptor(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DeclarativeStorageProviderAdapter:
    provider_id: str
    display_name: str
    provider_family: str
    operations: tuple[str, ...] = SUPPORTED_OPERATIONS

    def supports(self, operation: str) -> bool:
        return operation.upper() in self.operations

    def descriptor(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_family": self.provider_family,
            "operations": list(self.operations),
            "credential_material_location": "SKAP_ONLY",
            "provider_session_required": True,
            "provider_execution_implemented": False,
            "authority_effect": "NONE",
        }


@dataclass
class StorageProviderRegistry:
    adapters: list[KVStorageProviderAdapter]

    def __post_init__(self) -> None:
        ids = [adapter.provider_id for adapter in self.adapters]
        if len(ids) != len(set(ids)):
            raise KVStorageProviderError("provider_id values must be unique")

    def get(self, provider_id: str) -> KVStorageProviderAdapter:
        matches = [adapter for adapter in self.adapters if adapter.provider_id == provider_id]
        if len(matches) != 1:
            raise KVStorageProviderError("provider adapter unavailable or ambiguous")
        return matches[0]

    def descriptors(self) -> list[dict[str, Any]]:
        return [self.get(provider_id).descriptor() for provider_id in sorted(a.provider_id for a in self.adapters)]


def build_operation_request(
    *,
    adapter: KVStorageProviderAdapter,
    instance_id: str,
    kv_set_id: str,
    operation: str,
    storage_locator: str | None = None,
    requested_by: str = "owner",
    object_ref: str | None = None,
) -> dict[str, Any]:
    op = operation.upper().strip()
    if op not in SUPPORTED_OPERATIONS:
        raise KVStorageProviderError("unsupported provider operation")
    if not adapter.supports(op):
        raise KVStorageProviderError("provider adapter does not support requested operation")
    if not instance_id.startswith("kvi_"):
        raise KVStorageProviderError("instance_id must use kvi_ identifier")
    if not kv_set_id.strip():
        raise KVStorageProviderError("kv_set_id is required")
    if not requested_by.strip():
        raise KVStorageProviderError("requested_by is required")

    canonical = {
        "provider_id": adapter.provider_id,
        "instance_id": instance_id,
        "kv_set_id": kv_set_id.strip(),
        "operation": op,
        "storage_locator": storage_locator,
        "object_ref": object_ref,
        "requested_by": requested_by.strip(),
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema": REQUEST_SCHEMA,
        "request_id": f"kvprov_{digest[:24]}",
        **canonical,
        "governance_state": "PENDING_INTERLOCK_INTR",
        "skap_credential_ref_required": True,
        "credential_material_present": False,
        "provider_session_established": False,
        "provider_operation_executed": False,
        "data_moved": False,
        "replication_started": False,
        "authority_effect": "NONE",
        "activation_effect": False,
    }


def default_registry() -> StorageProviderRegistry:
    return StorageProviderRegistry([
        DeclarativeStorageProviderAdapter("icloud-drive", "iCloud Drive", "apple-cloud-storage"),
        DeclarativeStorageProviderAdapter("google-drive", "Google Drive", "google-cloud-storage"),
        DeclarativeStorageProviderAdapter("onedrive", "Microsoft OneDrive", "microsoft-cloud-storage"),
        DeclarativeStorageProviderAdapter("dropbox", "Dropbox", "dropbox-cloud-storage"),
    ])

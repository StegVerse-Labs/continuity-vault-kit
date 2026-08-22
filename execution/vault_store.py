"""Portable filesystem backing for KnowledgeVault execution state.

A KnowledgeVault root may itself be synchronized by the owner's cloud account.
This module stores only governed execution metadata/refs and never embeds credential
material. The edge device can disappear; durable execution state remains in KV.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .adapter import ExecutionEnvelopeError, canonical_sha256


EXECUTION_SUBDIRS = ("Attempts", "Extensions", "Receipts", "Recovery")
FORBIDDEN_KEYS = {
    "credential_material", "password", "private_key", "seed_phrase",
    "recovery_code", "access_token", "refresh_token", "secret",
}


class VaultStoreError(ExecutionEnvelopeError):
    pass


def _scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_KEYS and item not in (None, ""):
                raise VaultStoreError(f"credential/secret material rejected at {path}.{key}")
            _scan_forbidden(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_forbidden(item, f"{path}[{index}]")


class KnowledgeVaultExecutionStore:
    def __init__(self, vault_root: str | os.PathLike[str]):
        self.vault_root = Path(vault_root)
        self.execution_root = self.vault_root / "_System" / "Execution"

    def initialize(self) -> Path:
        self.execution_root.mkdir(parents=True, exist_ok=True)
        for name in EXECUTION_SUBDIRS:
            (self.execution_root / name).mkdir(parents=True, exist_ok=True)
        return self.execution_root

    def _append(self, category: str, stream_id: str, record: dict[str, Any]) -> Path:
        if category not in EXECUTION_SUBDIRS:
            raise VaultStoreError("unsupported KnowledgeVault execution category")
        if not stream_id or any(part in stream_id for part in ("/", "\\", "..")):
            raise VaultStoreError("stream_id must be a safe single path component")
        _scan_forbidden(record)
        self.initialize()
        destination = self.execution_root / category / f"{stream_id}.jsonl"
        stored = {
            "record": record,
            "record_sha256": canonical_sha256(record),
        }
        encoded = json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with destination.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return destination

    def append_attempt(self, attempt_id: str, record: dict[str, Any]) -> Path:
        return self._append("Attempts", attempt_id, record)

    def append_extension(self, extension_stream_id: str, record: dict[str, Any]) -> Path:
        return self._append("Extensions", extension_stream_id, record)

    def append_receipt(self, receipt_stream_id: str, record: dict[str, Any]) -> Path:
        return self._append("Receipts", receipt_stream_id, record)

    def append_recovery(self, attempt_id: str, record: dict[str, Any]) -> Path:
        return self._append("Recovery", attempt_id, record)

    def read_stream(self, category: str, stream_id: str) -> list[dict[str, Any]]:
        path = self.execution_root / category / f"{stream_id}.jsonl"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stored = json.loads(line)
            record = stored.get("record")
            if not isinstance(record, dict) or stored.get("record_sha256") != canonical_sha256(record):
                raise VaultStoreError(f"stored execution record failed hash verification at line {line_number}")
            records.append(record)
        return records

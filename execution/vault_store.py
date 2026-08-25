"""Portable filesystem backing for KnowledgeVault execution state.

A KnowledgeVault root may itself be synchronized by the owner's cloud account.
This module stores only governed execution metadata/refs and never embeds credential
material. The edge device can disappear; durable execution state remains in KV.

InTr packet/receipt persistence is metadata custody only. Persisting an InTr record in
KV never grants KV secret-resolution, decryption, execution, identity, continuity, or
governance authority.
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
INTR_PACKET_SCHEMA = "stegverse.intr.packet.review_candidate/v1"
INTR_RECEIPT_SCHEMA = "stegverse.intr.hop_receipt/v1"


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


def _require_false(value: Any, label: str) -> None:
    if value is not False:
        raise VaultStoreError(f"{label} must be false for KnowledgeVault persistence")


def _validate_intr_packet_for_kv(record: dict[str, Any]) -> None:
    if record.get("schema") != INTR_PACKET_SCHEMA:
        raise VaultStoreError("unsupported InTr packet schema for KnowledgeVault persistence")
    envelope = record.get("envelope")
    if not isinstance(envelope, dict):
        raise VaultStoreError("InTr packet envelope is required")

    authority = envelope.get("authority")
    if not isinstance(authority, dict):
        raise VaultStoreError("InTr packet authority boundary is required")
    for key in ("authority_transfer", "model_output_grants_execution_authority", "transport_grants_execution_authority"):
        _require_false(authority.get(key), f"InTr packet {key}")

    protected = envelope.get("protected_payload")
    if not isinstance(protected, dict):
        raise VaultStoreError("InTr protected payload metadata is required")
    if protected.get("sealed") is not True:
        raise VaultStoreError("InTr protected payload must remain sealed in KnowledgeVault")
    _require_false(protected.get("plaintext_present"), "InTr protected payload plaintext_present")

    # KV may preserve a sealed-material reference but never claim ability to resolve it.
    if record.get("kv_decryption_authority") not in (None, False):
        raise VaultStoreError("KnowledgeVault must not claim SKAP decryption authority")
    if record.get("kv_secret_resolution_authority") not in (None, False):
        raise VaultStoreError("KnowledgeVault must not claim SKAP secret-resolution authority")


def _validate_intr_receipt_for_kv(record: dict[str, Any]) -> None:
    if record.get("schema") != INTR_RECEIPT_SCHEMA:
        raise VaultStoreError("unsupported InTr receipt schema for KnowledgeVault persistence")
    _require_false(record.get("secret_plaintext_present"), "InTr receipt secret_plaintext_present")
    _require_false(record.get("authority_transfer"), "InTr receipt authority_transfer")


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

    def append_intr_packet(self, packet_stream_id: str, record: dict[str, Any]) -> Path:
        """Persist a sealed InTr packet as governed execution-extension metadata."""
        _validate_intr_packet_for_kv(record)
        return self._append("Extensions", packet_stream_id, record)

    def append_intr_receipt(self, packet_stream_id: str, record: dict[str, Any]) -> Path:
        """Persist a non-secret InTr hop receipt in the packet receipt stream."""
        _validate_intr_receipt_for_kv(record)
        return self._append("Receipts", packet_stream_id, record)

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

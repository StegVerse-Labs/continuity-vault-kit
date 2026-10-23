"""Portable filesystem backing for KnowledgeVault execution state.

A KnowledgeVault root may itself be synchronized by the owner's cloud account.
This module stores only governed execution metadata/refs and never embeds plaintext
credential material or decryption keys. The edge device can disappear; durable
execution state remains in KV.

InTr packet/receipt and SKAP ciphertext persistence are metadata/ciphertext custody
only. Persisting them in KV never grants KV secret-resolution, decryption, execution,
identity, continuity, or governance authority.

LC-KV-07 (StegVerse-Labs/.github#3330 rev 1): the SKAP sealed-credential append/read are SKAP Vault operations, so
they are reachable only through both credential layers. Each call consumes one single-use SKAP-access receipt from
the layer-2 gate (runtime.kv_skap_layer2.SkapLayer2Gate, INTR_KV_SKAP). The gate mints that receipt only on a
layer-1 KV-access receipt (KVInterlockRuntime.handle, INTR_DEVICE_KV, healthy node). Without the gate and receipt,
the call raises SkapAccessRefused, which carries a six-field FAIL_CLOSED, before any state is touched.
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
    "root_key", "wrapping_key", "plaintext",
}
INTR_PACKET_SCHEMA = "stegverse.intr.packet.review_candidate/v1"
INTR_RECEIPT_SCHEMA = "stegverse.intr.hop_receipt/v1"
SKAP_SEALED_FORMAT = "stegverse.skap.sealed_material/aes256gcm-hkdf-sha256/v1"
SKAP_INGRESS_RECEIPT_SCHEMA = "stegverse.skap.owner_credential_ingress_receipt/v1"
SKAP_KV_RECORD_SCHEMA = "stegverse.kv.skap_sealed_credential_record/v1"


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

    if record.get("kv_decryption_authority") not in (None, False):
        raise VaultStoreError("KnowledgeVault must not claim SKAP decryption authority")
    if record.get("kv_secret_resolution_authority") not in (None, False):
        raise VaultStoreError("KnowledgeVault must not claim SKAP secret-resolution authority")


def _validate_intr_receipt_for_kv(record: dict[str, Any]) -> None:
    if record.get("schema") != INTR_RECEIPT_SCHEMA:
        raise VaultStoreError("unsupported InTr receipt schema for KnowledgeVault persistence")
    _require_false(record.get("secret_plaintext_present"), "InTr receipt secret_plaintext_present")
    _require_false(record.get("authority_transfer"), "InTr receipt authority_transfer")


def _validate_skap_sealed_material_for_kv(sealed: dict[str, Any]) -> None:
    if sealed.get("format") != SKAP_SEALED_FORMAT:
        raise VaultStoreError("unsupported SKAP sealed-material format")
    if not str(sealed.get("object_id") or "").startswith("skap://"):
        raise VaultStoreError("SKAP object_id must use skap://")
    if not isinstance(sealed.get("credential_version"), int) or sealed.get("credential_version", 0) < 1:
        raise VaultStoreError("SKAP credential version invalid")
    for field in ("wrapping_policy_ref", "purpose", "endpoint_ref", "key_authority_ref", "kdf_salt_b64", "nonce_b64", "aad_hash", "ciphertext_b64"):
        if not sealed.get(field):
            raise VaultStoreError(f"SKAP sealed material missing {field}")
    _require_false(sealed.get("plaintext_persisted"), "SKAP plaintext_persisted")
    _require_false(sealed.get("key_material_persisted"), "SKAP key_material_persisted")
    _require_false(sealed.get("authority_transfer"), "SKAP authority_transfer")


def _validate_skap_ingress_receipt_for_kv(receipt: dict[str, Any], sealed: dict[str, Any]) -> None:
    if receipt.get("schema") != SKAP_INGRESS_RECEIPT_SCHEMA:
        raise VaultStoreError("unsupported SKAP owner-ingress receipt schema")
    if receipt.get("object_id") != sealed.get("object_id"):
        raise VaultStoreError("SKAP ingress receipt object binding mismatch")
    if receipt.get("credential_version") != sealed.get("credential_version"):
        raise VaultStoreError("SKAP ingress receipt version binding mismatch")
    if receipt.get("purpose") != sealed.get("purpose"):
        raise VaultStoreError("SKAP ingress receipt purpose binding mismatch")
    if receipt.get("endpoint_ref") != sealed.get("endpoint_ref"):
        raise VaultStoreError("SKAP ingress receipt endpoint binding mismatch")
    if receipt.get("sealed_material_hash") != canonical_sha256(sealed):
        raise VaultStoreError("SKAP ingress receipt sealed-material hash mismatch")
    if receipt.get("owner_authorized") is not True:
        raise VaultStoreError("SKAP ingress receipt must prove owner authorization")
    for field in ("plaintext_persisted", "device_durable_secret_custody", "kv_decryption_authority", "model_secret_access", "authority_transfer"):
        _require_false(receipt.get(field), f"SKAP ingress receipt {field}")


SKAP_LAYER2_REFUSAL_CODE = "SKAP_ACCESS_LAYER2_REFUSED"
SKAP_LAYER2_PREDICATE = "SKAP_VAULT_REACHABLE_ONLY_VIA_INTR_FROM_KV"
SKAP_OWNING_GOAL = "KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"


class SkapAccessRefused(VaultStoreError):
    """A six-field FAIL_CLOSED at the SKAP layer-2 gate; ``fields`` carries it."""

    def __init__(self, detail: str, *, failure_code: str = SKAP_LAYER2_REFUSAL_CODE,
                 failed_predicate: str = SKAP_LAYER2_PREDICATE, failure_class: str = "C",
                 next_attempt: str = "on the next SKAP operation admitted by the layer-2 gate"):
        self.fields = {
            "disposition": "FAIL_CLOSED",
            "failure_code": failure_code,
            "failed_predicate": failed_predicate,
            "required_evidence_or_repair": detail,
            "retry_entrypoint": "runtime.kv_skap_layer2.SkapLayer2Gate.admit, then KnowledgeVaultExecutionStore "
                                "with skap_gate and skap_access_receipt_hash",
            "owning_existing_goal": SKAP_OWNING_GOAL,
            "next_attempt": next_attempt,
            "failure_class": failure_class,
            "layer": 2,
        }
        super().__init__(f"{failure_code}: {detail}")


def _consume_skap_access(gate: Any, receipt_hash: Any, *, principal_ref: Any, operation: str,
                         subject_ref: str) -> dict[str, Any]:
    if gate is None or not callable(getattr(gate, "consume", None)):
        raise SkapAccessRefused(
            "SKAP sealed credentials are reachable only through InTr from inside KV: pass skap_gate "
            "(runtime.kv_skap_layer2.SkapLayer2Gate over KVInterlockRuntime) and a SKAP-access receipt",
            failure_class="B")
    if not (isinstance(principal_ref, str) and principal_ref.strip()):
        raise SkapAccessRefused("principal_ref is required to scope the SKAP-access receipt")
    if not (isinstance(receipt_hash, str) and receipt_hash.startswith("sha256:") and len(receipt_hash) == 71):
        raise SkapAccessRefused("skap_access_receipt_hash must be a SKAP-access receipt minted by "
                                "SkapLayer2Gate.admit on a verified layer-1 KV-access receipt")
    receipt, refusal = gate.consume(receipt_hash, principal_ref=principal_ref, operation=operation,
                                    subject_ref=subject_ref)
    if refusal is not None:
        raise SkapAccessRefused(refusal["required_evidence_or_repair"], failure_code=refusal["failure_code"],
                                failed_predicate=refusal["failed_predicate"],
                                failure_class=refusal.get("failure_class", "C"), next_attempt=refusal["next_attempt"])
    return {"kv_access_receipt_hash": receipt["prior_receipt_hash"], "skap_access_receipt_hash": receipt_hash}


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
        _validate_intr_packet_for_kv(record)
        return self._append("Extensions", packet_stream_id, record)

    def append_intr_receipt(self, packet_stream_id: str, record: dict[str, Any]) -> Path:
        _validate_intr_receipt_for_kv(record)
        return self._append("Receipts", packet_stream_id, record)

    def append_skap_sealed_credential(self, stream_id: str, sealed: dict[str, Any], ingress_receipt: dict[str, Any],
                                      *, skap_gate: Any = None, skap_access_receipt_hash: Any = None,
                                      principal_ref: Any = None) -> tuple[Path, Path]:
        """Persist ciphertext/reference state plus a secret-free owner-ingress receipt.

        KnowledgeVault receives no root key and gains no resolution authority. The
        sealed envelope is retained byte-for-byte in canonical JSON form for later
        integrity-checked reconstruction. Reachable only through both credential layers (LC-KV-07).
        """
        access = _consume_skap_access(skap_gate, skap_access_receipt_hash, principal_ref=principal_ref,
                                      operation="SKAP_SEALED_CREDENTIAL_APPEND", subject_ref=str(stream_id))
        _validate_skap_sealed_material_for_kv(sealed)
        _validate_skap_ingress_receipt_for_kv(ingress_receipt, sealed)
        extension_record = {
            "schema": SKAP_KV_RECORD_SCHEMA,
            "object_id": sealed["object_id"],
            "credential_version": sealed["credential_version"],
            "sealed_material": sealed,
            "sealed_material_hash": canonical_sha256(sealed),
            "kv_decryption_authority": False,
            "kv_secret_resolution_authority": False,
            "plaintext_present": False,
            "key_material_present": False,
            "authority_transfer": False,
            "access": access,
        }
        extension_path = self._append("Extensions", stream_id, extension_record)
        receipt_path = self._append("Receipts", stream_id, ingress_receipt)
        return extension_path, receipt_path

    def read_skap_sealed_credential(self, stream_id: str, *, skap_gate: Any = None,
                                    skap_access_receipt_hash: Any = None,
                                    principal_ref: Any = None) -> dict[str, Any] | None:
        _consume_skap_access(skap_gate, skap_access_receipt_hash, principal_ref=principal_ref,
                             operation="SKAP_SEALED_CREDENTIAL_READ", subject_ref=str(stream_id))
        extensions = self.read_stream("Extensions", stream_id)
        candidates = [record for record in extensions if record.get("schema") == SKAP_KV_RECORD_SCHEMA]
        if not candidates:
            return None
        record = candidates[-1]
        sealed = record.get("sealed_material")
        if not isinstance(sealed, dict):
            raise VaultStoreError("stored SKAP sealed-material record is malformed")
        _validate_skap_sealed_material_for_kv(sealed)
        if record.get("sealed_material_hash") != canonical_sha256(sealed):
            raise VaultStoreError("stored SKAP sealed-material hash mismatch")
        _require_false(record.get("kv_decryption_authority"), "stored SKAP kv_decryption_authority")
        _require_false(record.get("kv_secret_resolution_authority"), "stored SKAP kv_secret_resolution_authority")
        _require_false(record.get("plaintext_present"), "stored SKAP plaintext_present")
        _require_false(record.get("key_material_present"), "stored SKAP key_material_present")
        _require_false(record.get("authority_transfer"), "stored SKAP authority_transfer")
        return sealed

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

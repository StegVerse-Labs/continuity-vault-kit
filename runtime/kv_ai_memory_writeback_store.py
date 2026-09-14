"""Evidence-gated persistence for admitted KV AI memory write proposals.

This module never decides Interlock/InTr admission and never treats model output as
authority. It accepts only an already-admitted exact write proposal, verifies the
target KV instance and content binding, performs a write-once/idempotent local KV
materialization, reads the bytes back, and emits a receipt bound to the admission.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PROPOSAL_SCHEMA = "stegverse.kv.ai-memory-write-proposal/v1"
RECEIPT_SCHEMA = "stegverse.kv.ai-memory-writeback-receipt/v1"
INSTANCE_SCHEMA = "stegverse.kv.instance/v1"
INSTANCE_RECORD = Path("_System/Instances/instance.json")
RECEIPT_ROOT = Path("_System/AI/Memory/Receipts")


class MemoryWritebackError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MemoryWritebackError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_relative(path: str) -> bool:
    if not isinstance(path, str) or not path or path.startswith(("/", "\\")):
        return False
    parts = PurePosixPath(path.replace("\\", "/")).parts
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def load_instance(kv_root: Path) -> dict[str, Any]:
    path = kv_root.expanduser().resolve() / INSTANCE_RECORD
    _require(path.is_file(), "target KV instance record missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict) and value.get("schema") == INSTANCE_SCHEMA, "target KV instance record invalid")
    _require(isinstance(value.get("instance_id"), str) and value["instance_id"].startswith("kvi_"), "target KV instance_id invalid")
    return value


def validate_proposal(proposal: dict[str, Any]) -> None:
    _require(proposal.get("schema") == PROPOSAL_SCHEMA, "write proposal schema mismatch")
    _require(isinstance(proposal.get("proposal_id"), str) and proposal["proposal_id"].startswith("KVMEM-WRITE-"), "proposal_id invalid")
    _require(isinstance(proposal.get("target_kv_instance_id"), str) and proposal["target_kv_instance_id"].startswith("kvi_"), "target_kv_instance_id invalid")
    _require(_safe_relative(str(proposal.get("relative_path") or "")), "write proposal relative_path unsafe")
    _require(isinstance(proposal.get("content"), str), "write proposal content must be text")
    expected = sha256_bytes(proposal["content"].encode("utf-8"))
    _require(proposal.get("content_sha256") == expected, "write proposal content hash mismatch")
    _require(proposal.get("intr_admission_required") is True, "write proposal must require InTr admission")
    _require(proposal.get("execution_authorized") is False, "proposal may not self-authorize execution")
    _require(proposal.get("model_is_authority") is False, "model may not be KV authority")
    _require(proposal.get("authority_effect") == "NONE_PROPOSAL_ONLY", "write proposal authority effect invalid")


def validate_admission(proposal: dict[str, Any], admission: dict[str, Any]) -> None:
    _require(isinstance(admission, dict), "writeback admission must be object")
    _require(admission.get("governance_state") == "ADMITTED", "writeback requires ADMITTED governance evidence")
    _require(admission.get("disposition") == "ALLOW", "writeback InTr disposition must be ALLOW")
    _require(admission.get("proposal_id") == proposal.get("proposal_id"), "writeback admission proposal binding mismatch")
    _require(admission.get("target_kv_instance_id") == proposal.get("target_kv_instance_id"), "writeback admission target instance mismatch")
    _require(admission.get("content_sha256") == proposal.get("content_sha256"), "writeback admission content hash mismatch")
    _require(admission.get("persistence_authorized") is True, "writeback admission must authorize persistence consequence")
    _require(isinstance(admission.get("interlock_receipt_ref"), str) and admission["interlock_receipt_ref"].strip(), "Interlock receipt reference required")
    _require(isinstance(admission.get("intr_receipt_ref"), str) and admission["intr_receipt_ref"].strip(), "InTr receipt reference required")
    _require(admission.get("credential_material_present") is False, "writeback admission may not contain credential material")
    _require(admission.get("authority_effect") in (None, "NONE"), "writeback admission may not grant source authority")


def _atomic_write_once_or_same(path: Path, raw: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _require(path.is_file() and not path.is_symlink(), "writeback target must be regular file")
        existing = path.read_bytes()
        _require(existing == raw, "writeback target collision with different bytes")
        return "IDEMPOTENT_EXISTING_EXACT_BYTES"
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(raw)
        temp_name = stream.name
    os.replace(temp_name, path)
    return "MATERIALIZED_NEW_EXACT_BYTES"


def apply_admitted_writeback(kv_root: Path, *, proposal: dict[str, Any], admission: dict[str, Any]) -> dict[str, Any]:
    """Apply an already-admitted exact write proposal and prove exact-byte readback."""
    validate_proposal(proposal)
    validate_admission(proposal, admission)
    root = kv_root.expanduser().resolve()
    instance = load_instance(root)
    _require(instance["instance_id"] == proposal["target_kv_instance_id"], "target KV instance binding mismatch")

    relative = proposal["relative_path"].replace("\\", "/")
    target = (root / relative).resolve()
    _require(target != root and root in target.parents, "writeback target escaped KV root")
    raw = proposal["content"].encode("utf-8")
    disposition = _atomic_write_once_or_same(target, raw)
    readback = target.read_bytes()
    readback_hash = sha256_bytes(readback)
    _require(readback == raw and readback_hash == proposal["content_sha256"], "writeback exact-byte readback verification failed")

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "proposal_id": proposal["proposal_id"],
        "source_packet_id": proposal.get("source_packet_id"),
        "target_kv_instance_id": proposal["target_kv_instance_id"],
        "relative_path": relative,
        "content_sha256": proposal["content_sha256"],
        "readback_sha256": readback_hash,
        "readback_bytes": len(readback),
        "materialization_disposition": disposition,
        "governance_state": "ADMITTED",
        "interlock_receipt_ref": admission["interlock_receipt_ref"],
        "intr_receipt_ref": admission["intr_receipt_ref"],
        "persistence_performed": True,
        "exact_byte_readback_verified": True,
        "model_is_authority": False,
        "credential_material_present": False,
        "authority_effect": "NONE_RECEIPT_ONLY",
    }
    receipt_path = root / RECEIPT_ROOT / f"{proposal['proposal_id']}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt

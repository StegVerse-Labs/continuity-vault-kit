"""Provider-neutral reconstruction proof for MACHINE_KV continuity.

This verifier does not access storage providers, resolve credentials, or authorize
transitions. It evaluates externally observed source/target provider evidence and
proves only whether one Machine-KV identity and exact state manifest were
reconstructed across distinct providers under admitted InTr transitions.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "stegverse.kv.machine-reconstruction-evidence/v1"
RESULT_SCHEMA = "stegverse.kv.machine-reconstruction-result/v1"


class MachineKVReconstructionError(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MachineKVReconstructionError(message)


def validate_state_manifest(manifest: dict[str, Any]) -> str:
    _require(manifest.get("kv_class") == "MACHINE_KV", "state manifest must be MACHINE_KV")
    _require(manifest.get("authority_domain") == "MACHINE_EXECUTION_ENTITY", "state manifest authority domain mismatch")
    _require(isinstance(manifest.get("machine_kv_id"), str) and manifest["machine_kv_id"], "machine_kv_id required")
    entries = manifest.get("entries")
    _require(isinstance(entries, list) and entries, "state manifest entries required")
    paths: set[str] = set()
    for entry in entries:
        _require(isinstance(entry, dict), "state manifest entry malformed")
        path = entry.get("relative_path")
        digest = entry.get("sha256")
        size = entry.get("bytes")
        _require(isinstance(path, str) and path.startswith("_Machine/") and ".." not in path.split("/"), "Machine-KV state path invalid")
        _require(path not in paths, "duplicate Machine-KV state path")
        paths.add(path)
        _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "state entry sha256 invalid")
        _require(isinstance(size, int) and size >= 0, "state entry byte size invalid")
    basis = {
        "kv_class": manifest["kv_class"],
        "authority_domain": manifest["authority_domain"],
        "machine_kv_id": manifest["machine_kv_id"],
        "entries": sorted(entries, key=lambda row: row["relative_path"]),
    }
    return canonical_hash(basis)


def verify_reconstruction(evidence: dict[str, Any]) -> dict[str, Any]:
    _require(evidence.get("schema") == SCHEMA, "reconstruction evidence schema mismatch")
    source = evidence.get("source")
    target = evidence.get("target")
    manifest = evidence.get("state_manifest")
    _require(isinstance(source, dict) and isinstance(target, dict) and isinstance(manifest, dict), "source/target/manifest evidence required")
    manifest_hash = validate_state_manifest(manifest)

    checks = {
        "distinct_providers": source.get("provider_id") != target.get("provider_id") and bool(source.get("provider_id")) and bool(target.get("provider_id")),
        "source_provider_not_authority": source.get("provider_is_authority") is False,
        "target_provider_not_authority": target.get("provider_is_authority") is False,
        "source_observed": source.get("state_observed") is True,
        "target_observed": target.get("state_observed") is True,
        "source_manifest_hash_bound": source.get("state_manifest_sha256") == manifest_hash,
        "target_manifest_hash_bound": target.get("state_manifest_sha256") == manifest_hash,
        "machine_identity_preserved": source.get("machine_kv_id") == manifest.get("machine_kv_id") == target.get("machine_kv_id"),
        "source_intr_admitted": source.get("intr_disposition") == "ALLOW" and bool(source.get("intr_receipt_ref")),
        "target_intr_admitted": target.get("intr_disposition") == "ALLOW" and bool(target.get("intr_receipt_ref")),
        "credential_material_absent": source.get("credential_material_present") is False and target.get("credential_material_present") is False,
        "provider_session_not_identity": evidence.get("provider_session_transfers_machine_identity") is False,
        "authority_effect_none": evidence.get("authority_effect") == "NONE_EVIDENCE_ONLY",
    }
    complete = all(checks.values())
    result = {
        "schema": RESULT_SCHEMA,
        "reconstruction_id": evidence.get("reconstruction_id"),
        "machine_kv_id": manifest.get("machine_kv_id"),
        "source_provider_id": source.get("provider_id"),
        "target_provider_id": target.get("provider_id"),
        "state_manifest_sha256": manifest_hash,
        "machine_identity_preserved": checks["machine_identity_preserved"] if complete else False,
        "exact_state_continuity_proven": complete,
        "provider_is_authority": False,
        "provider_session_transfers_machine_identity": False,
        "credential_material_present": False,
        "decision": "PASS" if complete else "FAIL_CLOSED",
        "checks": checks,
        "authority_effect": "NONE_RECONSTRUCTION_PROOF_ONLY",
    }
    result["reconstruction_sha256"] = canonical_hash(result)
    return result

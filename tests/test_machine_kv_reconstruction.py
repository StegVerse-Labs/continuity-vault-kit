from __future__ import annotations

import copy

from runtime.machine_kv_reconstruction import canonical_hash, verify_reconstruction


def manifest():
    return {
        "kv_class": "MACHINE_KV",
        "authority_domain": "MACHINE_EXECUTION_ENTITY",
        "machine_kv_id": "mkv-node-alpha",
        "entries": [
            {"relative_path": "_Machine/Identity/node.json", "sha256": "1" * 64, "bytes": 128},
            {"relative_path": "_Machine/ExecutionState/current.json", "sha256": "2" * 64, "bytes": 256},
            {"relative_path": "_Machine/Checkpoints/checkpoint-7.json", "sha256": "3" * 64, "bytes": 512},
        ],
    }


def manifest_hash(value):
    basis = {
        "kv_class": value["kv_class"],
        "authority_domain": value["authority_domain"],
        "machine_kv_id": value["machine_kv_id"],
        "entries": sorted(value["entries"], key=lambda row: row["relative_path"]),
    }
    return canonical_hash(basis)


def evidence():
    m = manifest()
    digest = manifest_hash(m)
    return {
        "schema": "stegverse.kv.machine-reconstruction-evidence/v1",
        "reconstruction_id": "MKR-001",
        "state_manifest": m,
        "source": {
            "provider_id": "icloud-drive",
            "provider_is_authority": False,
            "state_observed": True,
            "state_manifest_sha256": digest,
            "machine_kv_id": "mkv-node-alpha",
            "intr_disposition": "ALLOW",
            "intr_receipt_ref": "receipt://intr/source",
            "credential_material_present": False,
        },
        "target": {
            "provider_id": "google-drive",
            "provider_is_authority": False,
            "state_observed": True,
            "state_manifest_sha256": digest,
            "machine_kv_id": "mkv-node-alpha",
            "intr_disposition": "ALLOW",
            "intr_receipt_ref": "receipt://intr/target",
            "credential_material_present": False,
        },
        "provider_session_transfers_machine_identity": False,
        "authority_effect": "NONE_EVIDENCE_ONLY",
    }


def test_exact_cross_provider_reconstruction_passes():
    result = verify_reconstruction(evidence())
    assert result["decision"] == "PASS"
    assert result["exact_state_continuity_proven"] is True
    assert result["machine_identity_preserved"] is True
    assert result["provider_is_authority"] is False


def test_same_provider_fails_closed():
    value = evidence()
    value["target"]["provider_id"] = value["source"]["provider_id"]
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["distinct_providers"] is False


def test_target_state_drift_fails_closed():
    value = evidence()
    value["target"]["state_manifest_sha256"] = "0" * 64
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["target_manifest_hash_bound"] is False


def test_machine_identity_drift_fails_closed():
    value = evidence()
    value["target"]["machine_kv_id"] = "mkv-other"
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["machine_identity_preserved"] is False


def test_provider_authority_claim_fails_closed():
    value = evidence()
    value["target"]["provider_is_authority"] = True
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["target_provider_not_authority"] is False


def test_missing_target_intr_receipt_fails_closed():
    value = evidence()
    value["target"]["intr_receipt_ref"] = ""
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["target_intr_admitted"] is False


def test_credential_material_fails_closed():
    value = evidence()
    value["source"]["credential_material_present"] = True
    result = verify_reconstruction(value)
    assert result["decision"] == "FAIL_CLOSED"
    assert result["checks"]["credential_material_absent"] is False

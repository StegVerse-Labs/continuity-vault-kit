from __future__ import annotations

import hashlib
import json
from typing import Any

OUTCOMES = {"ALLOW","ALLOW_WITH_SIGNOFF","DENY","FAIL_CLOSED","REDIRECT","ESCALATE"}

def _hash(obj: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def reconstruct(evidence: dict[str, Any]) -> dict[str, Any]:
    old = evidence["old_device"]
    new = evidence["new_device"]
    auth = evidence["recovery_authority"]
    provider = evidence["provider_access"]
    continuity = evidence["continuity"]
    transport = evidence["transport"]
    keys = evidence["key_provisioning"]

    checks = {
        "browser_only_provider_access": provider["mode"] == "BROWSER_ONLY",
        "encrypted_package_acquired": provider["encrypted_package_acquired"] is True,
        "provider_auth_not_kv_authority": provider["provider_auth_exposes_usable_kv"] is False,
        "old_device_unavailable": old["unavailable_observed"] is True,
        "old_device_revoked_or_lost": old["status_after"] in {"LOST","LOST_REVOKED","REVOKED"},
        "new_device_identity_distinct": new["distinct_identity"] is True and new["device_id"] != old["device_id"],
        "new_device_registration_observed": new["registration_observed"] is True and bool(new["attestation_ref"]),
        "recovery_authority_verified": auth["verified"] is True and auth["independent_of_provider_auth"] is True,
        "continuity_identity_preserved": continuity["kv_identity_preserved"] is True,
        "continuity_root_present": len(continuity["root_before"]) == 64 and len(continuity["root_after"]) == 64,
        "interlock_intr_observed": transport["protocol"] == "InTr" and transport["interlock_observed"] is True and bool(transport["intr_packet_ref"]) and bool(transport["intr_receipt_ref"]),
        "bounded_key_provisioning_observed": keys["observed"] is True and keys["old_device_key_reused"] is False,
        "durable_final_receipt_present": bool(evidence["final_receipt"]["receipt_ref"]) and len(evidence["final_receipt"]["receipt_sha256"]) == 64,
    }
    complete = all(checks.values())
    result = {
        "schema":"stegverse.kv.physical-recovery-reconstruction/v1",
        "experiment_id":evidence["experiment_id"],
        "kv_id":evidence["kv_id"],
        "decision":"ALLOW_WITH_SIGNOFF" if complete else "FAIL_CLOSED",
        "physical_recovery_proven":complete,
        "kv_identity_preserved":continuity["kv_identity_preserved"] is True if complete else False,
        "old_device_identity_preserved":False,
        "new_device_identity_created":checks["new_device_identity_distinct"],
        "cloud_account_is_kv_authority":False,
        "browser_is_execution_surface":False,
        "authority_effect":"NONE",
        "checks":checks,
    }
    result["reconstruction_sha256"] = _hash(result)
    return result

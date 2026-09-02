from __future__ import annotations

import hashlib
import json
from typing import Any

OUTCOMES = {"ALLOW","ALLOW_WITH_SIGNOFF","DENY","FAIL_CLOSED","REDIRECT","ESCALATE"}

def _hash(obj: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def evaluate(case_id: str, package: dict[str, Any]) -> dict[str, Any]:
    old_id = package["old_device"]["device_id"]
    new_id = package["new_device"]["device_id"]
    recovery = package["recovery"]
    transport = package["transport"]

    decision = "ALLOW_WITH_SIGNOFF"
    reason = "cross-platform recovery admissible with explicit recovery signoff"
    kv_preserved = True
    new_device_created = True

    if package["package_sha256"] != package["expected_package_sha256"]:
        decision, reason = "FAIL_CLOSED", "recovery package hash mismatch"
        kv_preserved = False
        new_device_created = False
    elif package["continuity_root"] != package["current_continuity_root"]:
        decision, reason = "ESCALATE", "stale continuity root requires recovery review"
        kv_preserved = False
        new_device_created = False
    elif package["new_device"]["claims_old_device_identity"] or new_id == old_id:
        decision, reason = "FAIL_CLOSED", "replacement device may not inherit old device identity"
        new_device_created = False
    elif recovery["browser_execution_requested"]:
        decision, reason = "DENY", "browser-only provider access is recovery transport, not execution authority"
        new_device_created = False
    elif recovery["cloud_account_authenticated"] and not recovery["recovery_authority_verified"]:
        decision, reason = "DENY", "cloud account authentication alone is insufficient"
        new_device_created = False
    elif not recovery["recovery_authority_verified"]:
        decision, reason = "DENY", "recovery authority not verified"
        new_device_created = False
    elif not recovery["old_device_unavailable"]:
        decision, reason = "REDIRECT", "normal device enrollment path should be used while old device remains available"
        new_device_created = False
    elif package["old_device"]["status"] not in {"LOST","LOST_REVOKED","REVOKED"}:
        decision, reason = "FAIL_CLOSED", "old device is not in a recoverable loss/revocation state"
        new_device_created = False
    elif not transport["interlock_verified"] or not transport["intr_bound"]:
        decision, reason = "FAIL_CLOSED", "verified Interlock/InTr binding is required"
        new_device_created = False

    core = {
        "schema":"stegverse.kv.cross-platform-recovery-receipt/v1",
        "case_id":case_id,
        "decision":decision,
        "kv_id":package["kv_id"],
        "kv_identity_preserved":kv_preserved,
        "old_device_identity_preserved":False,
        "new_device_identity_created":new_device_created,
        "cloud_account_is_kv_authority":False,
        "browser_is_execution_surface":False,
        "transport_protocol":"InTr",
        "authority_effect":"NONE",
        "reason":reason,
    }
    core["receipt_sha256"] = _hash(core)
    return core

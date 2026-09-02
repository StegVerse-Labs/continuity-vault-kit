from __future__ import annotations

import hashlib
import json
from typing import Any

OUTCOMES={"ALLOW","ALLOW_WITH_SIGNOFF","DENY","FAIL_CLOSED","REDIRECT","ESCALATE"}

def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def evaluate(request: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    src=request["source_provider"]
    dst=request["destination_provider"]
    decision="ALLOW_WITH_SIGNOFF"
    reason="provider relocation admissible with governed continuity signoff"
    exact_readback_match=False

    if src == dst:
        decision,reason="REDIRECT","source and destination providers are identical"
    elif request["authority"]["source_provider_is_kv_authority"] or request["authority"]["destination_provider_is_kv_authority"]:
        decision,reason="FAIL_CLOSED","storage provider may not become KV authority"
    elif request["authority"]["credential_authority"] != "TV/TVC":
        decision,reason="FAIL_CLOSED","credential authority must remain TV/TVC"
    elif not request["kv_identity_preserved"]:
        decision,reason="FAIL_CLOSED","KV identity continuity must be preserved"
    elif request["continuity_transition"]=="PRESERVED" and request["source_continuity_root"] != request["destination_continuity_root"]:
        decision,reason="ESCALATE","preserved continuity transition requires identical roots"
    elif request["continuity_transition"]=="GOVERNED_ADVANCE" and request["source_continuity_root"] == request["destination_continuity_root"]:
        decision,reason="ESCALATE","governed advance requires a changed continuity root"
    elif not request["transport"]["interlock_verified"] or not request["transport"]["intr_bound"]:
        decision,reason="FAIL_CLOSED","verified Interlock/InTr binding is required"
    elif evidence is None:
        decision,reason="ALLOW_WITH_SIGNOFF","deterministic relocation admissible; live provider evidence still required"
    else:
        required_refs=("intr_packet_ref","intr_receipt_ref","continuity_receipt_ref")
        if evidence.get("relocation_id") != request["relocation_id"]:
            decision,reason="FAIL_CLOSED","evidence relocation id mismatch"
        elif evidence.get("provider_credentials_exported") is not False or evidence.get("provider_authority_transferred") is not False:
            decision,reason="FAIL_CLOSED","provider credentials/authority may not transfer"
        elif any(not evidence.get(k) for k in required_refs):
            decision,reason="FAIL_CLOSED","required relocation evidence reference missing"
        else:
            exact_readback_match=evidence.get("source_readback_sha256")==evidence.get("destination_readback_sha256")
            if not exact_readback_match:
                decision,reason="FAIL_CLOSED","destination exact-byte readback differs from source"
            else:
                decision,reason="ALLOW","observed relocation evidence reconstructs exactly"

    core={
        "schema":"stegverse.kv.provider-relocation-receipt/v1",
        "relocation_id":request["relocation_id"],
        "decision":decision,
        "kv_id":request["kv_id"],
        "source_provider":src,
        "destination_provider":dst,
        "kv_identity_preserved":request["kv_identity_preserved"] if decision in {"ALLOW","ALLOW_WITH_SIGNOFF"} else False,
        "continuity_transition":request["continuity_transition"],
        "exact_readback_match":exact_readback_match,
        "transport_protocol":"InTr",
        "source_provider_is_kv_authority":False,
        "destination_provider_is_kv_authority":False,
        "credential_authority":"TV/TVC",
        "authority_effect":"NONE",
        "reason":reason,
    }
    core["receipt_sha256"]=_hash(core)
    return core

from __future__ import annotations

def evaluate(request: dict) -> dict:
    src=request["source_provider"]
    dst=request["destination_provider"]
    decision="ALLOW_WITH_SIGNOFF"
    reason="provider relocation admissible with governed continuity signoff"
    if src == dst:
        decision,reason="REDIRECT","source and destination providers are identical"
    elif request["source_provider_is_kv_authority"] or request["destination_provider_is_kv_authority"]:
        decision,reason="FAIL_CLOSED","storage provider may not become KV authority"
    elif not request["kv_identity_preserved"]:
        decision,reason="FAIL_CLOSED","KV identity continuity must be preserved"
    elif not request["continuity_transition_valid"]:
        decision,reason="ESCALATE","continuity transition is not valid"
    elif not request["interlock_verified"] or not request["intr_bound"]:
        decision,reason="FAIL_CLOSED","verified Interlock/InTr binding is required"
    return {
        "schema":"stegverse.kv.provider-relocation-receipt/v1",
        "decision":decision,
        "source_provider":src,
        "destination_provider":dst,
        "kv_identity_preserved":request["kv_identity_preserved"] if decision=="ALLOW_WITH_SIGNOFF" else False,
        "source_provider_is_kv_authority":False,
        "destination_provider_is_kv_authority":False,
        "transport_protocol":"InTr",
        "authority_effect":"NONE",
        "reason":reason,
    }

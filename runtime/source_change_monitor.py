"""Pure compatibility-state transition logic for provider/source change observations.

This module does not perform network monitoring. Production observation belongs on an
admitted resident machine surface; this code evaluates already-observed non-secret facts.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Dict

from runtime.connection_assembly import (
    ConnectionAssemblyError, assemble_connection, health_receipt, reject_secret_fields,
)

CHANGE_SCHEMA = "stegverse.kv.source-change-observation/v1"
BLOCKING_CLASSES = {"authentication","mfa_session","endpoint","deprecation","permission_scope","data_schema","product_model"}

def deterministic_observation_id(provider: str, source_ref: str, observed_at: str, change_class: str) -> str:
    material = "|".join((provider,source_ref,observed_at,change_class)).lower()
    return "kvchg_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

def normalize_change_observation(value: Dict[str,Any]) -> Dict[str,Any]:
    if not isinstance(value,dict):
        raise ConnectionAssemblyError("change observation must be an object")
    reject_secret_fields(value)
    for field in ("provider","observed_at","source_ref","source_type","change_class","severity","summary"):
        if not value.get(field):
            raise ConnectionAssemblyError(f"missing source change field: {field}")
    result=copy.deepcopy(value)
    result["schema"]=CHANGE_SCHEMA
    result["observation_id"]=deterministic_observation_id(
        result["provider"],result["source_ref"],result["observed_at"],result["change_class"]
    )
    result.setdefault("breaking",False)
    result.setdefault("affected_assumptions",[])
    result.setdefault("effective_at",None)
    result["authority_effect"]="NONE"
    return result

def evaluate_source_change(assembly: Dict[str,Any], observation: Dict[str,Any]) -> tuple[Dict[str,Any],Dict[str,Any]]:
    current=assemble_connection(assembly)
    change=normalize_change_observation(observation)
    if current["provider"].lower() != change["provider"].lower():
        raise ConnectionAssemblyError("source change provider does not match assembly")
    prior=current["compatibility_state"]
    if prior == "RETIRED":
        receipt=health_receipt(current,observed_at=change["observed_at"],prior_state=prior,current_state=prior,
                               reason="RETIRED_CONNECTION_UNCHANGED",revalidation_required=False,
                               change_observation_ref=change["observation_id"])
        return current,receipt

    monitored=set(current["monitoring"].get("change_classes") or [])
    if change["change_class"] not in monitored:
        receipt=health_receipt(current,observed_at=change["observed_at"],prior_state=prior,current_state=prior,
                               reason="CHANGE_CLASS_NOT_MONITORED_FOR_ASSEMBLY",revalidation_required=False,
                               change_observation_ref=change["observation_id"])
        return current,receipt

    blocking=bool(change.get("breaking")) and change["change_class"] in BLOCKING_CLASSES
    new_state="BLOCKED_SOURCE_CHANGE" if blocking else "REVALIDATION_REQUIRED"
    current["compatibility_state"]=new_state
    current["monitoring"]["last_checked_at"]=change["observed_at"]
    current["monitoring"]["last_change_ref"]=change["observation_id"]
    receipt=health_receipt(
        current,observed_at=change["observed_at"],prior_state=prior,current_state=new_state,
        reason="BREAKING_SOURCE_CHANGE" if blocking else "SOURCE_CHANGE_REVALIDATION_REQUIRED",
        revalidation_required=True,change_observation_ref=change["observation_id"],
        connection_proof_ref=current.get("last_connection_proof_ref"),
        readback_proof_ref=current.get("last_readback_proof_ref"),
    )
    return current,receipt

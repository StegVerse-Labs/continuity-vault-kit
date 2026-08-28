"""Deterministic, non-secret KnowledgeVault connection assembly helpers."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict

ASSEMBLY_SCHEMA = "stegverse.kv.connection-assembly/v1"
HEALTH_SCHEMA = "stegverse.kv.connection-health-receipt/v1"

ALLOWED_STATES = {
    "UNASSEMBLED","ASSEMBLED_UNVERIFIED","VERIFIED","DEGRADED",
    "REVALIDATION_REQUIRED","BLOCKED_SOURCE_CHANGE","BLOCKED_SESSION",
    "BLOCKED_RUNTIME","RETIRED",
}
FORBIDDEN_KEYS = {
    "password","passcode","pin","cvv","cvc","card_number","account_number",
    "routing_number","private_key","recovery_code","refresh_token","access_token",
    "oauth_token","api_key","secret","client_secret","authorization",
}

class ConnectionAssemblyError(ValueError):
    pass

def _norm(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")

def reject_secret_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _norm(str(key))
            padded = f"_{normalized}_"
            if any(fragment == normalized or f"_{fragment}_" in padded for fragment in FORBIDDEN_KEYS):
                raise ConnectionAssemblyError(f"forbidden credential-bearing field at {path}.{key}")
            reject_secret_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_fields(child, f"{path}[{index}]")

def deterministic_assembly_id(provider: str, target_domain: str, canonical_kv_path: str, adapter_name: str) -> str:
    material = "|".join(part.strip().lower() for part in (provider,target_domain,canonical_kv_path,adapter_name))
    return "kvcxn_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

def canonical_hash(value: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def assemble_connection(spec: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(spec, dict):
        raise ConnectionAssemblyError("connection specification must be an object")
    reject_secret_fields(spec)
    result = copy.deepcopy(spec)
    if result.get("access") not in (None,"READ_ONLY"):
        raise ConnectionAssemblyError("connection assembly access must be READ_ONLY")
    if result.get("direct_source_required") not in (None,True):
        raise ConnectionAssemblyError("direct_source_required must remain true")
    if result.get("minimum_necessary") not in (None,True):
        raise ConnectionAssemblyError("minimum_necessary must remain true")
    if result.get("credential_authority") not in (None,"TV/TVC"):
        raise ConnectionAssemblyError("credential authority must remain TV/TVC")
    if result.get("authority_effect") not in (None,"NONE"):
        raise ConnectionAssemblyError("authority effect must remain NONE")
    for required in ("provider","source_kind","target_domain","canonical_kv_path","adapter","provider_capability_binding","intr_hops","monitoring"):
        if not result.get(required):
            raise ConnectionAssemblyError(f"missing connection assembly field: {required}")
    if not isinstance(result["adapter"],dict) or not result["adapter"].get("name") or not result["adapter"].get("version"):
        raise ConnectionAssemblyError("adapter name/version required")
    if not isinstance(result["intr_hops"],list) or not result["intr_hops"]:
        raise ConnectionAssemblyError("at least one InTr hop required")
    result["schema"] = ASSEMBLY_SCHEMA
    result["assembly_id"] = deterministic_assembly_id(
        result["provider"], result["target_domain"], result["canonical_kv_path"], result["adapter"]["name"]
    )
    result["access"] = "READ_ONLY"
    result["direct_source_required"] = True
    result["minimum_necessary"] = True
    result["credential_authority"] = "TV/TVC"
    result.setdefault("credential_reference_class","SKAP_REFERENCE")
    result.setdefault("authentication_mechanism_class",None)
    result.setdefault("ingress_surface",None)
    result.setdefault("egress_surface",None)
    result.setdefault("last_connection_proof_ref",None)
    result.setdefault("last_readback_proof_ref",None)
    result.setdefault("compatibility_state","ASSEMBLED_UNVERIFIED")
    if result["compatibility_state"] not in ALLOWED_STATES:
        raise ConnectionAssemblyError("invalid compatibility state")
    result["authority_effect"] = "NONE"
    return result

def verify_connection(assembly: Dict[str, Any], *, observed_at: str, connection_proof_ref: str, readback_proof_ref: str) -> tuple[Dict[str,Any],Dict[str,Any]]:
    current = assemble_connection(assembly)
    if current["compatibility_state"] == "RETIRED":
        raise ConnectionAssemblyError("retired connection cannot be verified")
    if not connection_proof_ref or not readback_proof_ref:
        raise ConnectionAssemblyError("connection and KV readback proof are both required")
    prior = current["compatibility_state"]
    current["compatibility_state"] = "VERIFIED"
    current["last_connection_proof_ref"] = connection_proof_ref
    current["last_readback_proof_ref"] = readback_proof_ref
    receipt = health_receipt(
        current, observed_at=observed_at, prior_state=prior, current_state="VERIFIED",
        reason="CONNECTION_AND_KV_READBACK_VERIFIED", revalidation_required=False,
        connection_proof_ref=connection_proof_ref, readback_proof_ref=readback_proof_ref,
    )
    return current, receipt

def health_receipt(assembly: Dict[str,Any], *, observed_at: str, prior_state: str, current_state: str, reason: str,
                   revalidation_required: bool, change_observation_ref: str|None=None,
                   connection_proof_ref: str|None=None, readback_proof_ref: str|None=None) -> Dict[str,Any]:
    if prior_state not in ALLOWED_STATES or current_state not in ALLOWED_STATES:
        raise ConnectionAssemblyError("invalid health state")
    return {
        "schema": HEALTH_SCHEMA,
        "assembly_id": assembly["assembly_id"],
        "provider": assembly["provider"],
        "observed_at": observed_at,
        "prior_state": prior_state,
        "current_state": current_state,
        "reason": reason,
        "change_observation_ref": change_observation_ref,
        "revalidation_required": revalidation_required,
        "connection_proof_ref": connection_proof_ref,
        "readback_proof_ref": readback_proof_ref,
        "provider_operation_authorized": False,
        "credential_material_present": False,
        "authority_effect": "NONE",
    }

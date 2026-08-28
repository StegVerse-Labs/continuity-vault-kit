"""Non-secret proof admission for Personal KV connection revalidation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from runtime.connection_assembly import (
    ConnectionAssemblyError,
    assemble_connection,
    reject_secret_fields,
    verify_connection,
)

CONFORMANCE_SCHEMA="stegverse.kv.connection-conformance-proof/v1"
READBACK_SCHEMA="stegverse.kv.connection-readback-proof/v1"

class ConnectionRevalidationError(ConnectionAssemblyError):
    pass

def _parse_time(value: Any, label: str) -> datetime:
    text=str(value or "").strip()
    if not text:
        raise ConnectionRevalidationError(f"{label} timestamp required")
    try:
        if text.endswith("Z"):
            parsed=datetime.fromisoformat(text[:-1]+"+00:00")
        else:
            parsed=datetime.fromisoformat(text)
    except ValueError as exc:
        raise ConnectionRevalidationError(f"{label} timestamp invalid") from exc
    if parsed.tzinfo is None:
        raise ConnectionRevalidationError(f"{label} timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)

def _assert_common_proof_boundary(proof: Dict[str,Any], label: str) -> None:
    if not isinstance(proof,dict):
        raise ConnectionRevalidationError(f"{label} proof must be an object")
    try:
        reject_secret_fields(proof,f"$.{label}")
    except ConnectionAssemblyError as exc:
        raise ConnectionRevalidationError(str(exc)) from exc
    if proof.get("provider_operation_authorized") is not False:
        raise ConnectionRevalidationError(f"{label} provider operation authority prohibited")
    if proof.get("credential_material_present") is not False:
        raise ConnectionRevalidationError(f"{label} credential material prohibited")
    if proof.get("authority_effect")!="NONE":
        raise ConnectionRevalidationError(f"{label} authority effect must remain NONE")
    _parse_time(proof.get("observed_at"),label)

def validate_conformance_proof(assembly: Dict[str,Any], proof: Dict[str,Any]) -> None:
    current=assemble_connection(assembly)
    _assert_common_proof_boundary(proof,"conformance")
    if proof.get("schema")!=CONFORMANCE_SCHEMA:
        raise ConnectionRevalidationError("unexpected conformance proof schema")
    if proof.get("assembly_id")!=current["assembly_id"]:
        raise ConnectionRevalidationError("conformance proof assembly mismatch")
    if str(proof.get("provider") or "").lower()!=str(current["provider"]).lower():
        raise ConnectionRevalidationError("conformance proof provider mismatch")
    if proof.get("direct_source_verified") is not True:
        raise ConnectionRevalidationError("direct source verification required")
    if proof.get("session_verified") is not True:
        raise ConnectionRevalidationError("provider session verification required")
    adapter=proof.get("adapter")
    if not isinstance(adapter,dict) or adapter.get("name")!=current["adapter"]["name"] or adapter.get("version")!=current["adapter"]["version"]:
        raise ConnectionRevalidationError("conformance proof adapter mismatch")
    if not proof.get("compatibility_assumptions_ref"):
        raise ConnectionRevalidationError("compatibility assumptions reference required")
    if not proof.get("connection_proof_ref"):
        raise ConnectionRevalidationError("connection proof reference required")

def validate_readback_proof(assembly: Dict[str,Any], proof: Dict[str,Any]) -> None:
    current=assemble_connection(assembly)
    _assert_common_proof_boundary(proof,"readback")
    if proof.get("schema")!=READBACK_SCHEMA:
        raise ConnectionRevalidationError("unexpected readback proof schema")
    if proof.get("assembly_id")!=current["assembly_id"]:
        raise ConnectionRevalidationError("readback proof assembly mismatch")
    if proof.get("canonical_kv_path")!=current["canonical_kv_path"]:
        raise ConnectionRevalidationError("readback proof canonical path mismatch")
    if proof.get("readback_verified") is not True:
        raise ConnectionRevalidationError("private KV readback verification required")
    if not proof.get("persistence_receipt_ref") or not proof.get("readback_proof_ref"):
        raise ConnectionRevalidationError("persistence and readback proof references required")

def admit_revalidation(
    assembly: Dict[str,Any],
    conformance_proof: Dict[str,Any],
    readback_proof: Dict[str,Any],
    *,
    required_after: str|None=None,
) -> tuple[Dict[str,Any],Dict[str,Any]]:
    current=assemble_connection(assembly)
    if current["compatibility_state"]=="RETIRED":
        raise ConnectionRevalidationError("retired connection cannot be revalidated")
    validate_conformance_proof(current,conformance_proof)
    validate_readback_proof(current,readback_proof)
    conformance_time=_parse_time(conformance_proof["observed_at"],"conformance")
    readback_time=_parse_time(readback_proof["observed_at"],"readback")
    if required_after is not None:
        floor=_parse_time(required_after,"required_after")
        if conformance_time < floor or readback_time < floor:
            raise ConnectionRevalidationError("revalidation proof predates required invalidation/recovery event")
    observed_at=max(conformance_time,readback_time).isoformat().replace("+00:00","Z")
    return verify_connection(
        current,
        observed_at=observed_at,
        connection_proof_ref=str(conformance_proof["connection_proof_ref"]),
        readback_proof_ref=str(readback_proof["readback_proof_ref"]),
    )

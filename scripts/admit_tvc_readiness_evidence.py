#!/usr/bin/env python3
"""Admit canonical TVC runtime-readiness evidence into KV readiness facts.

This adapter is evidence-only. It never activates a module/service and never
grants provider, execution, identity, governance, or credential authority.
"""
from __future__ import annotations

import json
from typing import Any

RESIDENT_SCHEMA = "stegverse.tvc.coinbase_intr_resident_readiness/v3"
BOUNDARY_SCHEMA = "stegverse.tvc.skap_vault_runtime_boundary_observation/v1"
ADMISSION_SCHEMA = "stegverse.kv.tvc-readiness-evidence-admission/v1"

FORBIDDEN_KEYS = {
    "private_key",
    "recipient_private_key",
    "credential_plaintext",
    "credential_value",
    "api_secret",
    "secret",
    "access_token",
    "authorization",
    "bearer_token",
    "jwt",
}
FORBIDDEN_STRING_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "Authorization: Bearer ",
)


class AdmissionError(ValueError):
    pass


def _walk_for_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise AdmissionError(f"forbidden secret-bearing key at {path}.{key}")
            _walk_for_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_for_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if any(marker in value for marker in FORBIDDEN_STRING_MARKERS):
            raise AdmissionError(f"forbidden secret-bearing string at {path}")


def _require_resident_authority_boundary(resident: dict[str, Any]) -> None:
    if resident.get("schema") != RESIDENT_SCHEMA:
        raise AdmissionError("unexpected resident readiness schema")
    if resident.get("credential_authority") != "TV/TVC":
        raise AdmissionError("credential authority mismatch")
    if resident.get("credential_custody_target") != "SKAP_VAULT":
        raise AdmissionError("credential custody target mismatch")
    if resident.get("transport_protocol") != "InTr":
        raise AdmissionError("transport protocol mismatch")
    if resident.get("authority_transfer") is not False:
        raise AdmissionError("authority transfer must be false")
    if resident.get("provider_operation_authorized") is not False:
        raise AdmissionError("provider operation authority must be false")
    if resident.get("provider_operation_started") is not False:
        raise AdmissionError("provider operation must not be started")
    if resident.get("credential_plaintext_observed") is not False:
        raise AdmissionError("credential plaintext must not be observed")


def _require_boundary_authority_boundary(boundary: dict[str, Any]) -> None:
    if boundary.get("schema") != BOUNDARY_SCHEMA:
        raise AdmissionError("unexpected SKAP Vault boundary schema")
    if boundary.get("credential_authority") != "TV/TVC":
        raise AdmissionError("SKAP boundary credential authority mismatch")
    if boundary.get("credential_custody_target") != "KV_HOSTED_SKAP_VAULT":
        raise AdmissionError("SKAP boundary custody target mismatch")
    if boundary.get("storage_connector") != "KV_SKAP_INTR_ONLY":
        raise AdmissionError("SKAP boundary storage connector mismatch")
    if boundary.get("device_durable_secret_custody") is not False:
        raise AdmissionError("device durable secret custody must be false")
    if boundary.get("kv_decryption_authority") is not False:
        raise AdmissionError("KV decryption authority must be false")
    if boundary.get("provider_operation_authorized") is not False:
        raise AdmissionError("SKAP boundary provider authority must be false")
    if boundary.get("execution_authority") != "NONE":
        raise AdmissionError("SKAP boundary execution authority must be NONE")
    if boundary.get("authority_transfer") is not False:
        raise AdmissionError("SKAP boundary authority transfer must be false")


def admit(
    resident: dict[str, Any],
    boundary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(resident, dict):
        raise AdmissionError("resident readiness object required")
    if boundary is not None and not isinstance(boundary, dict):
        raise AdmissionError("boundary observation must be an object")

    _walk_for_secrets(resident)
    if boundary is not None:
        _walk_for_secrets(boundary)

    _require_resident_authority_boundary(resident)
    if boundary is not None:
        _require_boundary_authority_boundary(boundary)

    ready = resident.get("ready_for_owner_ingress") is True
    liveness = (
        ready
        and resident.get("private_key_liveness_verified") is True
        and resident.get("public_projection_verified") is True
        and resident.get("successor_service_installed") is True
        and resident.get("browser_ingress_service_installed") is True
        and resident.get("browser_ingress_health_verified") is True
    )
    double_interlock = (
        resident.get("double_interlock_receipt_chain_observed") is True
        and resident.get("device_kv_receipt_observed") is True
        and resident.get("kv_skap_receipt_observed") is True
        and bool(resident.get("device_kv_receipt_hash"))
        and bool(resident.get("kv_skap_receipt_hash"))
        and bool(resident.get("double_interlock_chain_digest"))
    )
    skap_boundary_ready = bool(
        boundary is not None
        and boundary.get("ready_for_skap_vault_ingress") is True
        and boundary.get("state") == "READY_FOR_SKAP_VAULT_INGRESS"
    )
    gateway_route = resident.get("public_intr_route_verified") is True

    facts_delta = {
        "tvc_resident_key_liveness_observed": liveness,
        "ready_for_owner_ingress_observed": ready,
        "production_gateway_route_observed": gateway_route,
        "production_double_interlock_receipts_observed": double_interlock,
        "skap_vault_runtime_boundary_observed": skap_boundary_ready,
    }

    return {
        "schema": ADMISSION_SCHEMA,
        "decision": "ADMIT_FACTS_DELTA",
        "resident_state": resident.get("state"),
        "boundary_state": None if boundary is None else boundary.get("state"),
        "facts_delta": facts_delta,
        "production_interlock_runtime_activated_set_by_adapter": False,
        "provider_session_evidence_set_by_adapter": False,
        "activation_performed": False,
        "provider_operation_authorized": False,
        "execution_authority": "NONE",
        "authority_effect": "NONE",
    }


def main() -> int:
    raise SystemExit(
        "library adapter only; call admit() from a governed evidence-ingestion path"
    )


if __name__ == "__main__":
    main()

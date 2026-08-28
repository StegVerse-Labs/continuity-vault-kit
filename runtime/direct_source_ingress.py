"""Direct-source SKAP-backed ingress contract helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict

REQUEST_SCHEMA = "stegverse.kv.direct-source-ingress-request/v1"
RECEIPT_SCHEMA = "stegverse.kv.direct-source-ingress-receipt/v1"

FORBIDDEN_SECRET_FRAGMENTS = (
    "password",
    "access_token",
    "refresh_token",
    "private_key",
    "secret",
    "api_key",
    "cvv",
    "card_number",
    "account_number",
    "routing_number",
)


class DirectSourceIngressError(ValueError):
    pass


def _reject_secret_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN_SECRET_FRAGMENTS):
                raise DirectSourceIngressError(f"secret-bearing field prohibited at {path}.{key}")
            _reject_secret_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_fields(child, f"{path}[{index}]")


def build_request(
    *,
    source_id: str,
    source_kind: str,
    target_domain: str,
    skap_credential_ref: str,
    provider_route: str | None = None,
    masked_owner_reference: str | None = None,
) -> Dict[str, Any]:
    if not isinstance(skap_credential_ref, str) or not skap_credential_ref.startswith("skap://"):
        raise DirectSourceIngressError("SKAP credential reference required")
    request = {
        "schema_version": REQUEST_SCHEMA,
        "source_id": str(source_id).strip(),
        "source_kind": str(source_kind).strip(),
        "target_domain": str(target_domain).strip(),
        "provider_route": provider_route,
        "masked_owner_reference": masked_owner_reference,
        "skap_credential_ref": skap_credential_ref,
        "requested_access": "READ_ONLY",
        "direct_source_required": True,
        "minimum_necessary": True,
        "owner_authorized": True,
        "intermediary_transport": None,
        "authority_effect": "NONE",
    }
    assert_request(request)
    return request


def assert_request(request: Dict[str, Any]) -> None:
    if not isinstance(request, dict):
        raise DirectSourceIngressError("request must be an object")
    _reject_secret_fields(request)
    if request.get("schema_version") != REQUEST_SCHEMA:
        raise DirectSourceIngressError("request schema mismatch")
    if request.get("requested_access") != "READ_ONLY":
        raise DirectSourceIngressError("direct-source ingress is read-only")
    if request.get("direct_source_required") is not True:
        raise DirectSourceIngressError("direct source must be required")
    if request.get("minimum_necessary") is not True:
        raise DirectSourceIngressError("minimum-necessary access required")
    if request.get("owner_authorized") is not True:
        raise DirectSourceIngressError("owner authorization required")
    if request.get("authority_effect") != "NONE":
        raise DirectSourceIngressError("ingress may not grant authority")
    ref = request.get("skap_credential_ref")
    if not isinstance(ref, str) or not ref.startswith("skap://"):
        raise DirectSourceIngressError("valid SKAP reference required")


def admit_receipt(
    request: Dict[str, Any],
    provider_result: Dict[str, Any],
    *,
    normalization_receipt_ref: str,
    persistence_receipt_ref: str,
) -> Dict[str, Any]:
    assert_request(request)
    _reject_secret_fields(provider_result, "provider_result")

    if provider_result.get("direct_source_verified") is not True:
        raise DirectSourceIngressError("FAIL_CLOSED: direct source verification required")
    if provider_result.get("session_verified") is not True:
        raise DirectSourceIngressError("FAIL_CLOSED: provider session verification required")
    if not provider_result.get("retrieved_at"):
        raise DirectSourceIngressError("FAIL_CLOSED: retrieval timestamp required")
    if not normalization_receipt_ref or not persistence_receipt_ref:
        raise DirectSourceIngressError("FAIL_CLOSED: normalization and persistence receipts required")

    intermediary = provider_result.get("intermediary") or {}
    return {
        "schema_version": RECEIPT_SCHEMA,
        "source_id": request["source_id"],
        "target_domain": request["target_domain"],
        "state": "ADMITTED_PERSISTED",
        "direct_source_verified": True,
        "masked_owner_reference": request.get("masked_owner_reference"),
        "retrieved_at": provider_result["retrieved_at"],
        "coverage_start": provider_result.get("coverage_start"),
        "coverage_end": provider_result.get("coverage_end"),
        "adapter_version": provider_result.get("adapter_version"),
        "intermediary_used": bool(intermediary.get("used", False)),
        "intermediary_name": intermediary.get("name"),
        "freshness_state": provider_result.get("freshness_state", "UNKNOWN"),
        "normalization_receipt_ref": normalization_receipt_ref,
        "persistence_receipt_ref": persistence_receipt_ref,
        "failure_reason": None,
        "authority_effect": "NONE",
    }


def fail_closed_receipt(request: Dict[str, Any], reason: str) -> Dict[str, Any]:
    assert_request(request)
    return {
        "schema_version": RECEIPT_SCHEMA,
        "source_id": request["source_id"],
        "target_domain": request["target_domain"],
        "state": "FAIL_CLOSED",
        "direct_source_verified": False,
        "masked_owner_reference": request.get("masked_owner_reference"),
        "retrieved_at": None,
        "coverage_start": None,
        "coverage_end": None,
        "adapter_version": None,
        "intermediary_used": False,
        "intermediary_name": None,
        "freshness_state": "UNAVAILABLE",
        "normalization_receipt_ref": None,
        "persistence_receipt_ref": None,
        "failure_reason": str(reason)[:512],
        "authority_effect": "NONE",
    }

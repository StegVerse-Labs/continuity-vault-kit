"""Bind an authenticated resident cloud-peer adoption request to provider operations.

This module does not authenticate providers, resolve credentials, decide Interlock/InTr
admission, or mutate a KnowledgeVault.  It converts an already-observed Site adoption
request into the canonical storage-provider CONNECT/VERIFY lane and exposes a strict
materialization-readiness gate.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.kv_storage_provider_adapter import build_operation_request, default_registry

SITE_ADOPTION_SCHEMA = "stegverse.site.cloud-kv-peer-adoption-request/v1"
BINDING_SCHEMA = "stegverse.kv.cloud-peer-adoption-provider-binding/v1"
READINESS_SCHEMA = "stegverse.kv.cloud-peer-adoption-materialization-readiness/v1"
PROVIDER_RECEIPT_SCHEMA = "stegverse.kv.storage-provider-operation-receipt/v1"


class CloudPeerAdoptionProviderBindingError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CloudPeerAdoptionProviderBindingError(message)


def _validate_site_request(request: Dict[str, Any]) -> None:
    _require(request.get("schema") == SITE_ADOPTION_SCHEMA, "unexpected Site adoption schema")
    _require(request.get("operation") == "ADOPT_EXISTING_CLOUD_KV_PEER", "unexpected adoption operation")
    _require(str(request.get("request_id") or "").startswith("SITE-CLOUD-KV-"), "Site request_id invalid")
    _require(request.get("governance_state") == "PENDING_INTERLOCK_INTR", "adoption request must remain pending")
    _require(request.get("storage_medium") == "google-drive", "only recovered Google Drive peer is bound in this slice")
    _require(request.get("requested_instance_number") == 2, "requested peer ordinal must be KV #2")
    _require(str(request.get("existing_instance_id") or "").startswith("kvi_"), "existing cloud instance_id invalid")
    _require(request.get("kv_set_id") == "personal", "kv_set_id mismatch")
    _require(request.get("credential_material_present") is False, "credential material prohibited")
    _require(request.get("provider_operation_authorized") is False, "request cannot pre-authorize provider execution")
    _require(request.get("instance_materialized") is False, "request cannot pre-materialize KV #2")
    _require(request.get("relationship_mutation_authorized") is False, "request cannot mutate relationship state")
    _require(request.get("data_moved") is False, "request cannot claim data movement")
    _require(request.get("replication_started") is False, "request cannot claim replication")
    _require(request.get("ai_corpus_exposed") is False, "request cannot expose AI corpus")
    _require(request.get("existing_identity_rewrite_authorized") is False, "existing cloud identity rewrite prohibited")
    _require(request.get("private_content_rewrite_authorized") is False, "private content rewrite prohibited")


def build_provider_binding(
    *,
    site_request: Dict[str, Any],
    resident_ingress_evidence: Dict[str, Any],
    private_storage_locator: str,
) -> Dict[str, Any]:
    """Build deterministic Google Drive CONNECT + VERIFY requests from resident ingress.

    ``private_storage_locator`` is runtime-private input.  Callers must not publish the
    resulting provider request or copy the locator into public Site/COSV projections.
    """
    _validate_site_request(site_request)
    _require(bool(private_storage_locator.strip()), "private storage locator required")
    _require(resident_ingress_evidence.get("request_id") == site_request["request_id"], "resident ingress request binding mismatch")
    _require(resident_ingress_evidence.get("resident_ingress_observed") is True, "resident ingress evidence required")
    _require(resident_ingress_evidence.get("governance_state") == "PENDING_INTERLOCK_INTR", "resident evidence must preserve pending governance")
    _require(resident_ingress_evidence.get("instance_materialized") is False, "resident evidence cannot claim materialization")
    _require(resident_ingress_evidence.get("provider_operation_authorized") is False, "resident evidence cannot authorize provider operation")

    adapter = default_registry().get("google-drive")
    common = dict(
        adapter=adapter,
        instance_id=site_request["existing_instance_id"],
        kv_set_id=site_request["kv_set_id"],
        storage_locator=private_storage_locator.strip(),
        requested_by="owner",
        object_ref=site_request["request_id"],
    )
    connect = build_operation_request(operation="CONNECT", **common)
    verify = build_operation_request(operation="VERIFY", **common)

    return {
        "schema": BINDING_SCHEMA,
        "source_site_request_id": site_request["request_id"],
        "resident_instance_id": site_request["resident_instance_id"],
        "existing_cloud_instance_id": site_request["existing_instance_id"],
        "kv_set_id": site_request["kv_set_id"],
        "provider_id": "google-drive",
        "requested_instance_number": 2,
        "requested_logical_name": "KV #2",
        "initial_relationship_tier": "NOT_CONNECTED",
        "connect_request": connect,
        "verify_request": verify,
        "interlock_intr_admission_required": True,
        "skap_credential_reference_required": True,
        "provider_result_evidence_required": True,
        "cloud_identity_rewrite_required": False,
        "private_content_rewrite_authorized": False,
        "instance_materialization_authorized": False,
        "relationship_mutation_authorized": False,
        "credential_material_present": False,
        "authority_effect": "NONE_REQUEST_BINDING_ONLY",
        "activation_effect": False,
    }


def _validate_provider_receipt(receipt: Dict[str, Any], *, request: Dict[str, Any], operation: str) -> None:
    _require(receipt.get("schema") == PROVIDER_RECEIPT_SCHEMA, f"{operation} receipt schema mismatch")
    _require(receipt.get("request_id") == request.get("request_id"), f"{operation} receipt request mismatch")
    _require(receipt.get("instance_id") == request.get("instance_id"), f"{operation} receipt instance mismatch")
    _require(receipt.get("kv_set_id") == request.get("kv_set_id"), f"{operation} receipt set mismatch")
    _require(receipt.get("provider_id") == "google-drive", f"{operation} receipt provider mismatch")
    _require(receipt.get("operation") == operation, f"{operation} receipt operation mismatch")
    _require(receipt.get("governance_state") == "ADMITTED", f"{operation} requires ADMITTED governance")
    _require(receipt.get("provider_operation_executed") is True, f"{operation} execution evidence required")
    _require(bool(str(receipt.get("interlock_receipt_ref") or "").strip()), f"{operation} Interlock receipt required")
    _require(bool(str(receipt.get("intr_receipt_ref") or "").strip()), f"{operation} InTr receipt required")
    _require(bool(str(receipt.get("skap_credential_ref") or "").strip()), f"{operation} SKAP reference required")
    _require(bool(str(receipt.get("provider_result_ref") or "").strip()), f"{operation} provider result required")
    _require(receipt.get("credential_material_present") is False, f"{operation} receipt cannot contain credential material")
    _require(receipt.get("authority_effect") == "NONE", f"{operation} receipt cannot grant source authority")
    _require(receipt.get("data_moved") is False, f"{operation} cannot claim data movement")
    _require(receipt.get("replication_started") is False, f"{operation} cannot claim replication")


def evaluate_materialization_readiness(
    *,
    binding: Dict[str, Any],
    connect_receipt: Dict[str, Any] | None = None,
    verify_receipt: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return fail-closed readiness; it never performs materialization itself."""
    _require(binding.get("schema") == BINDING_SCHEMA, "unexpected provider binding schema")
    _require(binding.get("instance_materialization_authorized") is False, "binding cannot pre-authorize materialization")

    missing: list[str] = []
    if connect_receipt is None:
        missing.append("ADMITTED_GOOGLE_DRIVE_CONNECT_RESULT")
    else:
        _validate_provider_receipt(connect_receipt, request=binding["connect_request"], operation="CONNECT")
    if verify_receipt is None:
        missing.append("ADMITTED_GOOGLE_DRIVE_VERIFY_RESULT")
    else:
        _validate_provider_receipt(verify_receipt, request=binding["verify_request"], operation="VERIFY")

    ready = not missing
    return {
        "schema": READINESS_SCHEMA,
        "source_site_request_id": binding["source_site_request_id"],
        "existing_cloud_instance_id": binding["existing_cloud_instance_id"],
        "requested_instance_number": 2,
        "requested_logical_name": "KV #2",
        "provider_id": "google-drive",
        "provider_connect_verified": ready,
        "materialization_ready": ready,
        "materialization_mode": "SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY" if ready else None,
        "cloud_identity_rewrite_required": False,
        "private_content_rewrite_authorized": False,
        "relationship_tier_after_materialization": "NOT_CONNECTED",
        "missing_evidence": missing,
        "credential_material_present": False,
        "authority_effect": "NONE_READINESS_ONLY",
        "activation_effect": False,
    }

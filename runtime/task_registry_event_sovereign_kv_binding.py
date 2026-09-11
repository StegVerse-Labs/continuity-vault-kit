"""Bind canonical Task Registry event custody to the existing governed KV provider path.

This module does not authenticate providers, resolve credentials, decide Interlock/InTr
admission, execute provider I/O, or grant authority. It converts an already-validated
Task Registry sovereign-KV projection request into the canonical provider-neutral
WRITE request used by continuity-vault-kit and validates the resulting admitted
provider receipt against the exact event hash.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.kv_storage_provider_adapter import build_operation_request, default_registry

PROJECTION_REQUEST_SCHEMA = "stegverse.task-registry-sovereign-kv-projection-request/v1"
PROJECTION_RECEIPT_SCHEMA = "stegverse.task-registry-sovereign-kv-projection-receipt/v1"
PROVIDER_RECEIPT_SCHEMA = "stegverse.kv.storage-provider-operation-receipt/v1"
BINDING_SCHEMA = "stegverse.kv.task-registry-event-custody-binding/v1"
CUSTODY_CLASS = "STEGVERSE_SOVEREIGN_KV"


class TaskRegistryEventCustodyBindingError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskRegistryEventCustodyBindingError(message)


def build_task_registry_event_custody_binding(
    *,
    projection_request: Dict[str, Any],
    provider_id: str,
    instance_id: str,
    kv_set_id: str,
    storage_locator: str | None = None,
) -> Dict[str, Any]:
    _require(projection_request.get("schema") == PROJECTION_REQUEST_SCHEMA, "unexpected projection request schema")
    _require(projection_request.get("custody_class") == CUSTODY_CLASS, "unexpected custody class")
    _require(projection_request.get("authority_effect") == "NONE", "projection request cannot grant authority")
    event = projection_request.get("exact_event")
    _require(isinstance(event, dict), "exact_event required")
    event_sha256 = projection_request.get("event_sha256")
    _require(isinstance(event_sha256, str) and event_sha256.startswith("sha256:"), "event_sha256 required")
    _require(event.get("event_sha256") == event_sha256, "exact_event hash binding mismatch")
    _require(event.get("authority_effect") == "NONE", "exact event cannot grant authority")

    adapter = default_registry().get(provider_id)
    provider_write_request = build_operation_request(
        adapter=adapter,
        instance_id=instance_id,
        kv_set_id=kv_set_id,
        operation="WRITE",
        storage_locator=storage_locator,
        requested_by="task-registry-coordination",
        object_ref=event_sha256,
    )

    return {
        "schema": BINDING_SCHEMA,
        "task_id": projection_request.get("task_id"),
        "session_id": projection_request.get("session_id"),
        "event_sha256": event_sha256,
        "predecessor_event_sha256": projection_request.get("predecessor_event_sha256"),
        "custody_class": CUSTODY_CLASS,
        "provider_id": provider_id,
        "kv_instance_ref": instance_id,
        "kv_set_id": kv_set_id,
        "provider_write_request": provider_write_request,
        "interlock_intr_admission_required": True,
        "skap_credential_reference_required": True,
        "provider_result_evidence_required": True,
        "exact_hash_readback_required": True,
        "credential_material_present": False,
        "authority_effect": "NONE",
    }


def validate_task_registry_event_custody_result(
    *,
    binding: Dict[str, Any],
    provider_receipt: Dict[str, Any],
    stored_event_sha256: str,
) -> Dict[str, Any]:
    _require(binding.get("schema") == BINDING_SCHEMA, "unexpected custody binding schema")
    request = binding.get("provider_write_request")
    _require(isinstance(request, dict), "provider write request required")
    _require(provider_receipt.get("schema") == PROVIDER_RECEIPT_SCHEMA, "provider receipt schema mismatch")
    _require(provider_receipt.get("request_id") == request.get("request_id"), "provider receipt request mismatch")
    _require(provider_receipt.get("instance_id") == request.get("instance_id"), "provider receipt instance mismatch")
    _require(provider_receipt.get("kv_set_id") == request.get("kv_set_id"), "provider receipt set mismatch")
    _require(provider_receipt.get("provider_id") == request.get("provider_id"), "provider receipt provider mismatch")
    _require(provider_receipt.get("operation") == "WRITE", "provider receipt must prove WRITE")
    _require(provider_receipt.get("governance_state") == "ADMITTED", "provider WRITE requires ADMITTED governance")
    _require(provider_receipt.get("provider_operation_executed") is True, "provider WRITE execution evidence required")
    _require(bool(str(provider_receipt.get("interlock_receipt_ref") or "").strip()), "Interlock receipt required")
    _require(bool(str(provider_receipt.get("intr_receipt_ref") or "").strip()), "InTr receipt required")
    _require(bool(str(provider_receipt.get("skap_credential_ref") or "").strip()), "SKAP credential reference required")
    _require(bool(str(provider_receipt.get("provider_result_ref") or "").strip()), "provider result evidence required")
    _require(provider_receipt.get("credential_material_present") is False, "credential material prohibited")
    _require(provider_receipt.get("authority_effect") == "NONE", "provider receipt cannot grant authority")
    _require(request.get("object_ref") == binding.get("event_sha256"), "provider request object_ref must bind exact event hash")
    _require(stored_event_sha256 == binding.get("event_sha256"), "stored event hash readback mismatch")

    return {
        "schema": PROJECTION_RECEIPT_SCHEMA,
        "task_id": binding.get("task_id"),
        "session_id": binding.get("session_id"),
        "event_sha256": binding["event_sha256"],
        "stored_event_sha256": stored_event_sha256,
        "custody_class": CUSTODY_CLASS,
        "provider_adapter_ref": f"continuity-vault-kit:runtime/kv_storage_provider_adapter.py#{request['provider_id']}",
        "interlock_intr_receipt_ref": f"{provider_receipt['interlock_receipt_ref']}|{provider_receipt['intr_receipt_ref']}",
        "kv_instance_ref": request["instance_id"],
        "provider_operation_request_id": request["request_id"],
        "provider_result_ref": provider_receipt["provider_result_ref"],
        "skap_credential_ref": provider_receipt["skap_credential_ref"],
        "exact_hash_readback_verified": True,
        "authority_effect": "NONE",
    }

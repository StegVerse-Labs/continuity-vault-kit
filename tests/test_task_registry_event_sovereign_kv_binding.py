from runtime.task_registry_event_sovereign_kv_binding import (
    build_task_registry_event_custody_binding,
    validate_task_registry_event_custody_result,
)


def projection_request():
    event_hash = "sha256:" + "a" * 64
    return {
        "schema": "stegverse.task-registry-sovereign-kv-projection-request/v1",
        "task_id": "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001",
        "session_id": "session-1",
        "event_sha256": event_hash,
        "predecessor_event_sha256": None,
        "custody_class": "STEGVERSE_SOVEREIGN_KV",
        "exact_event": {
            "schema": "stegverse.task-registry-checkin-event/v1",
            "task_id": "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001",
            "session_id": "session-1",
            "event_sha256": event_hash,
            "authority_effect": "NONE",
        },
        "authority_effect": "NONE",
    }


def provider_receipt(request):
    return {
        "schema": "stegverse.kv.storage-provider-operation-receipt/v1",
        "request_id": request["request_id"],
        "instance_id": request["instance_id"],
        "kv_set_id": request["kv_set_id"],
        "provider_id": request["provider_id"],
        "operation": "WRITE",
        "governance_state": "ADMITTED",
        "provider_operation_executed": True,
        "data_moved": True,
        "replication_started": False,
        "interlock_receipt_ref": "interlock:receipt:1",
        "intr_receipt_ref": "intr:receipt:1",
        "skap_credential_ref": "skap:credential:1",
        "provider_result_ref": "provider:result:1",
        "authority_effect": "NONE",
        "credential_material_present": False,
    }


def test_binding_reuses_existing_provider_write_contract():
    binding = build_task_registry_event_custody_binding(
        projection_request=projection_request(),
        provider_id="google-drive",
        instance_id="kvi_task_registry_001",
        kv_set_id="stegverse-task-registry",
        storage_locator="private://task-registry/events",
    )
    request = binding["provider_write_request"]
    assert request["schema"] == "stegverse.kv.storage-provider-operation-request/v1"
    assert request["operation"] == "WRITE"
    assert request["governance_state"] == "PENDING_INTERLOCK_INTR"
    assert request["object_ref"] == binding["event_sha256"]
    assert request["credential_material_present"] is False
    assert binding["authority_effect"] == "NONE"


def test_admitted_write_plus_exact_readback_yields_projection_receipt():
    binding = build_task_registry_event_custody_binding(
        projection_request=projection_request(),
        provider_id="google-drive",
        instance_id="kvi_task_registry_001",
        kv_set_id="stegverse-task-registry",
    )
    receipt = validate_task_registry_event_custody_result(
        binding=binding,
        provider_receipt=provider_receipt(binding["provider_write_request"]),
        stored_event_sha256=binding["event_sha256"],
    )
    assert receipt["schema"] == "stegverse.task-registry-sovereign-kv-projection-receipt/v1"
    assert receipt["stored_event_sha256"] == binding["event_sha256"]
    assert receipt["exact_hash_readback_verified"] is True
    assert receipt["authority_effect"] == "NONE"


def test_hash_readback_mismatch_fails_closed():
    binding = build_task_registry_event_custody_binding(
        projection_request=projection_request(),
        provider_id="google-drive",
        instance_id="kvi_task_registry_001",
        kv_set_id="stegverse-task-registry",
    )
    try:
        validate_task_registry_event_custody_result(
            binding=binding,
            provider_receipt=provider_receipt(binding["provider_write_request"]),
            stored_event_sha256="sha256:" + "b" * 64,
        )
    except ValueError as exc:
        assert "readback mismatch" in str(exc)
    else:
        raise AssertionError("expected exact hash readback mismatch")

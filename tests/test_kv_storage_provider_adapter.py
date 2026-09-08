from __future__ import annotations

import pytest

from runtime.kv_storage_provider_adapter import (
    KVStorageProviderError,
    StorageProviderRegistry,
    build_operation_request,
    default_registry,
)


def test_default_registry_contains_expected_provider_adapters() -> None:
    registry = default_registry()
    ids = [item["provider_id"] for item in registry.descriptors()]
    assert ids == ["dropbox", "google-drive", "icloud-drive", "onedrive"]
    for descriptor in registry.descriptors():
        assert descriptor["credential_material_location"] == "SKAP_ONLY"
        assert descriptor["provider_session_required"] is True
        assert descriptor["provider_execution_implemented"] is False
        assert descriptor["authority_effect"] == "NONE"


def test_operation_request_is_non_authorizing_and_deterministic() -> None:
    adapter = default_registry().get("icloud-drive")
    one = build_operation_request(
        adapter=adapter,
        instance_id="kvi_two",
        kv_set_id="personal",
        operation="CONNECT",
        storage_locator="icloud-slot-2",
    )
    two = build_operation_request(
        adapter=adapter,
        instance_id="kvi_two",
        kv_set_id="personal",
        operation="CONNECT",
        storage_locator="icloud-slot-2",
    )
    assert one == two
    assert one["request_id"].startswith("kvprov_")
    assert one["governance_state"] == "PENDING_INTERLOCK_INTR"
    assert one["skap_credential_ref_required"] is True
    assert one["credential_material_present"] is False
    assert one["provider_session_established"] is False
    assert one["provider_operation_executed"] is False
    assert one["data_moved"] is False
    assert one["authority_effect"] == "NONE"
    assert one["activation_effect"] is False


def test_all_declared_operations_are_representable() -> None:
    registry = default_registry()
    for provider_id in ["icloud-drive", "google-drive", "onedrive", "dropbox"]:
        adapter = registry.get(provider_id)
        for operation in ["CONNECT", "VERIFY", "READ", "WRITE", "SYNC", "DISCONNECT"]:
            request = build_operation_request(
                adapter=adapter,
                instance_id="kvi_one",
                kv_set_id="personal",
                operation=operation,
            )
            assert request["provider_id"] == provider_id
            assert request["operation"] == operation
            assert request["provider_operation_executed"] is False


def test_unknown_provider_and_bad_instance_fail_closed() -> None:
    registry = default_registry()
    with pytest.raises(KVStorageProviderError):
        registry.get("unknown")
    with pytest.raises(KVStorageProviderError):
        build_operation_request(
            adapter=registry.get("icloud-drive"),
            instance_id="bad",
            kv_set_id="personal",
            operation="CONNECT",
        )


def test_duplicate_provider_ids_are_rejected() -> None:
    adapter = default_registry().get("icloud-drive")
    with pytest.raises(KVStorageProviderError):
        StorageProviderRegistry([adapter, adapter])

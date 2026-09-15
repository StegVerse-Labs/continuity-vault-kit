from runtime.kv_storage_provider_adapter import build_operation_request, default_registry


def test_endpoint_registry_includes_device_cloud_network_and_removable():
    registry = default_registry()
    descriptors = {item["provider_id"]: item for item in registry.descriptors()}
    assert descriptors["device-local"]["storage_class"] == "DEVICE"
    assert descriptors["google-drive"]["storage_class"] == "CLOUD"
    assert descriptors["nas"]["storage_class"] == "NETWORK"
    assert descriptors["removable-storage"]["storage_class"] == "REMOVABLE"
    assert descriptors["device-local"]["credential_requirement"] == "NONE"
    assert descriptors["device-local"]["provider_session_required"] is False
    assert descriptors["nas"]["session_requirement"] == "ADAPTER_DEFINED"


def test_legacy_cloud_request_hash_shape_is_preserved():
    registry = default_registry()
    request = build_operation_request(
        adapter=registry.get("google-drive"),
        instance_id="kvi_a31335d2cc3745fa987b635432cfed2c",
        kv_set_id="personal",
        operation="VERIFY",
        storage_locator="/KnowledgeVault",
    )
    assert request["schema"] == "stegverse.kv.storage-provider-operation-request/v1"
    assert request["provider_id"] == "google-drive"
    assert request["governance_state"] == "PENDING_INTERLOCK_INTR"
    assert request["skap_credential_ref_required"] is True
    assert request["provider_operation_executed"] is False
    assert request["authority_effect"] == "NONE"


def test_device_local_endpoint_does_not_invent_provider_credentials():
    registry = default_registry()
    request = build_operation_request(
        adapter=registry.get("device-local"),
        instance_id="kvi_11111111111111111111111111111111",
        kv_set_id="personal",
        operation="VERIFY",
        storage_locator="KnowledgeVault",
    )
    assert request["schema"] == "stegverse.kv.storage-provider-operation-request/v1"
    assert request["skap_credential_ref_required"] is False
    assert request["credential_material_present"] is False
    assert request["provider_session_established"] is False
    assert request["activation_effect"] is False

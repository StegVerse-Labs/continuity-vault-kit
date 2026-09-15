import unittest

from runtime.kv_storage_provider_adapter import build_operation_request, default_registry


class StorageEndpointV2Tests(unittest.TestCase):
    def test_endpoint_registry_includes_device_cloud_network_and_removable(self):
        registry = default_registry()
        descriptors = {item["provider_id"]: item for item in registry.descriptors()}
        self.assertEqual(descriptors["device-local"]["storage_class"], "DEVICE")
        self.assertEqual(descriptors["google-drive"]["storage_class"], "CLOUD")
        self.assertEqual(descriptors["nas"]["storage_class"], "NETWORK")
        self.assertEqual(descriptors["removable-storage"]["storage_class"], "REMOVABLE")
        self.assertEqual(descriptors["device-local"]["credential_requirement"], "NONE")
        self.assertFalse(descriptors["device-local"]["provider_session_required"])
        self.assertEqual(descriptors["nas"]["session_requirement"], "ADAPTER_DEFINED")

    def test_legacy_cloud_request_hash_shape_is_preserved(self):
        registry = default_registry()
        request = build_operation_request(
            adapter=registry.get("google-drive"),
            instance_id="kvi_a31335d2cc3745fa987b635432cfed2c",
            kv_set_id="personal",
            operation="VERIFY",
            storage_locator="/KnowledgeVault",
        )
        self.assertEqual(request["schema"], "stegverse.kv.storage-provider-operation-request/v1")
        self.assertEqual(request["provider_id"], "google-drive")
        self.assertEqual(request["governance_state"], "PENDING_INTERLOCK_INTR")
        self.assertTrue(request["skap_credential_ref_required"])
        self.assertFalse(request["provider_operation_executed"])
        self.assertEqual(request["authority_effect"], "NONE")

    def test_device_local_endpoint_does_not_invent_provider_credentials(self):
        registry = default_registry()
        request = build_operation_request(
            adapter=registry.get("device-local"),
            instance_id="kvi_11111111111111111111111111111111",
            kv_set_id="personal",
            operation="VERIFY",
            storage_locator="KnowledgeVault",
        )
        self.assertEqual(request["schema"], "stegverse.kv.storage-provider-operation-request/v1")
        self.assertFalse(request["skap_credential_ref_required"])
        self.assertFalse(request["credential_material_present"])
        self.assertFalse(request["provider_session_established"])
        self.assertFalse(request["activation_effect"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from runtime.kv_provider_operation_store import (
    KVProviderOperationStateError,
    apply_admitted_result,
    canonical_paths,
    initialize_store,
    load_state,
    persist_operation_request,
)
from runtime.kv_storage_provider_adapter import build_operation_request, default_registry


class KVProviderOperationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "KnowledgeVault-2"
        self.root.mkdir()
        self.instance_id = "kvi_test000000000000000000000001"
        self.kv_set_id = "kvset_test"
        initialize_store(self.root, instance_id=self.instance_id, kv_set_id=self.kv_set_id)
        self.adapter = default_registry().get("icloud-drive")

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, operation):
        return build_operation_request(
            adapter=self.adapter,
            instance_id=self.instance_id,
            kv_set_id=self.kv_set_id,
            operation=operation,
            storage_locator="iCloud Drive/KnowledgeVault-2",
        )

    def admitted(self, request, **overrides):
        value = {
            "governance_state": "ADMITTED",
            "request_id": request["request_id"],
            "interlock_receipt_ref": "interlock:receipt:test",
            "intr_receipt_ref": "intr:receipt:test",
            "skap_credential_ref": "skap:credential-ref:test",
            "provider_result_ref": "provider:result:test",
            "provider_operation_executed": True,
            "credential_material_present": False,
            "authority_effect": "NONE",
            "data_moved": False,
            "replication_started": False,
        }
        value.update(overrides)
        return value

    def test_initializes_empty_fail_closed_state(self):
        state = load_state(self.root)
        self.assertEqual(state["providers"], {})
        self.assertEqual(state["authority_effect"], "NONE")
        self.assertFalse(state["credential_material_present"])

    def test_pending_request_is_persisted_without_state_change(self):
        request = self.request("CONNECT")
        path = persist_operation_request(self.root, request)
        self.assertTrue(path.is_file())
        self.assertEqual(load_state(self.root)["providers"], {})
        stored = json.loads(path.read_text())
        self.assertEqual(stored["governance_state"], "PENDING_INTERLOCK_INTR")
        self.assertFalse(stored["provider_operation_executed"])

    def test_connect_then_verify_materializes_only_from_admitted_evidence(self):
        connect = self.request("CONNECT")
        persist_operation_request(self.root, connect)
        state = apply_admitted_result(self.root, request=connect, admission=self.admitted(connect))
        row = state["providers"]["icloud-drive"]
        self.assertEqual(row["connection_state"], "CONNECTED")
        self.assertFalse(row["verified"])

        verify = self.request("VERIFY")
        persist_operation_request(self.root, verify)
        state = apply_admitted_result(self.root, request=verify, admission=self.admitted(verify))
        self.assertTrue(state["providers"]["icloud-drive"]["verified"])
        receipt = canonical_paths(self.root)["receipts"] / f"{verify['request_id']}.json"
        self.assertTrue(receipt.is_file())

    def test_read_write_sync_require_connected_provider(self):
        for operation in ("READ", "WRITE", "SYNC"):
            with self.subTest(operation=operation):
                request = self.request(operation)
                kwargs = {"replication_started": operation == "SYNC"}
                with self.assertRaises(KVProviderOperationStateError):
                    apply_admitted_result(self.root, request=request, admission=self.admitted(request, **kwargs))

    def test_sync_requires_replication_evidence(self):
        connect = self.request("CONNECT")
        apply_admitted_result(self.root, request=connect, admission=self.admitted(connect))
        sync = self.request("SYNC")
        with self.assertRaises(KVProviderOperationStateError):
            apply_admitted_result(self.root, request=sync, admission=self.admitted(sync, replication_started=False))
        state = apply_admitted_result(self.root, request=sync, admission=self.admitted(sync, replication_started=True, data_moved=True))
        self.assertEqual(state["providers"]["icloud-drive"]["last_operation"], "SYNC")

    def test_disconnect_resets_verified_state(self):
        connect = self.request("CONNECT")
        apply_admitted_result(self.root, request=connect, admission=self.admitted(connect))
        verify = self.request("VERIFY")
        apply_admitted_result(self.root, request=verify, admission=self.admitted(verify))
        disconnect = self.request("DISCONNECT")
        state = apply_admitted_result(self.root, request=disconnect, admission=self.admitted(disconnect))
        row = state["providers"]["icloud-drive"]
        self.assertEqual(row["connection_state"], "DISCONNECTED")
        self.assertFalse(row["verified"])

    def test_missing_runtime_evidence_fails_closed(self):
        request = self.request("CONNECT")
        for field in ("interlock_receipt_ref", "intr_receipt_ref", "skap_credential_ref", "provider_result_ref"):
            with self.subTest(field=field):
                admission = self.admitted(request)
                admission[field] = ""
                with self.assertRaises(KVProviderOperationStateError):
                    apply_admitted_result(self.root, request=request, admission=admission)

    def test_credential_material_is_rejected(self):
        request = self.request("CONNECT")
        admission = self.admitted(request, credential_material_present=True)
        with self.assertRaises(KVProviderOperationStateError):
            apply_admitted_result(self.root, request=request, admission=admission)


if __name__ == "__main__":
    unittest.main()

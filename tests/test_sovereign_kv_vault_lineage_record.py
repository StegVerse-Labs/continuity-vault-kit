"""Vault-lineage record type on the TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001 binding (additive only).

The first group pins the bytes of everything that existed before the extension, as observed at
continuity-vault-kit main bcc2d75: the projection-request schema and the other schema constants, the source of
the existing binding functions and of the adapter's v1 request builder, and the exact binding and receipt the
existing fixture produces. Any change to them fails here.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import runtime.task_registry_event_sovereign_kv_binding as binding_module  # noqa: E402
from runtime.kv_storage_provider_adapter import (  # noqa: E402
    KVStorageProviderError,
    build_vault_lineage_readback_request,
    default_registry,
)
from runtime.task_registry_event_sovereign_kv_binding import (  # noqa: E402
    TaskRegistryEventCustodyBindingError,
    build_task_registry_event_custody_binding,
    build_vault_lineage_custody_binding,
    build_vault_lineage_record,
    validate_task_registry_event_custody_result,
    validate_vault_lineage_custody_result,
)
from test_task_registry_event_sovereign_kv_binding import projection_request, provider_receipt  # noqa: E402


def h(value) -> str:
    raw = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def segment(rel: str, name: str) -> str:
    source = (ROOT / rel).read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return ast.get_source_segment(source, node)
    raise AssertionError(f"{name} missing from {rel}")


# observed at main bcc2d75, before this change
PINNED = {
    "constants": "sha256:c712d7b888fa78c9634359971c323ea11e1226421ab519ebfa294bcc6280f86b",
    "fixture_projection_request": "sha256:2316ab464f69b08d9d3a5da73415e815b6d154a5aadf20d2da5f47e8dac16201",
    "event_binding": "sha256:50e92fde1585bc0d9114a871736e1c78ccf79a40efa51c08002e60ddb0e9f648",
    "event_receipt": "sha256:1d23b2ccca4904238dd9b8d5a1ccf14815978891d427a039a3c4c74ba4f50d7c",
    ("runtime/task_registry_event_sovereign_kv_binding.py", "_require"):
        "sha256:21e64d2cd080871ecb1433975f2570c82c9c0cc263efe1c77719484613278377",
    ("runtime/task_registry_event_sovereign_kv_binding.py", "build_task_registry_event_custody_binding"):
        "sha256:b5628eca1d4d497255f8b431c997ba14a60146466de566c90884488dfff15cf1",
    ("runtime/task_registry_event_sovereign_kv_binding.py", "validate_task_registry_event_custody_result"):
        "sha256:17bb23bf324ad291abe1821fed1642a4f14db329f254ed65e4cf775182be2107",
    ("runtime/kv_storage_provider_adapter.py", "build_operation_request"):
        "sha256:eceb4da1ddf412d9fd30ab62451bbd5d5ec43eb79c133f31efd2b1842c457943",
    ("runtime/kv_storage_provider_adapter.py", "default_registry"):
        "sha256:faba88cc62f5aadf2610ba47f5a7e6d7dec5d9b57ed2269823f19fe40f5a6e2c",
}


def event_binding():
    return build_task_registry_event_custody_binding(
        projection_request=projection_request(), provider_id="google-drive",
        instance_id="kvi_task_registry_001", kv_set_id="stegverse-task-registry",
        storage_locator="private://task-registry/events")


def receipt_hash(receipt):
    return h({k: v for k, v in receipt.items() if k != "receipt_hash"})


def lineage(count: int = 3, principal: str = "principal:alice"):
    receipts, previous = [], None
    for index in range(count):
        receipt = {"schema": "stegverse.kv-skap-vault-receipt/v1", "task_id": "KV-SKAP-VAULT-FUNCTIONAL-001",
                   "principal_ref": principal, "sequence": index, "kind": ["custody", "write", "revoke"][index % 3],
                   "previous_receipt_hash": previous,
                   "body": {"custody_key_ref": "tvc://skap-custody/k1", "intr_transition_ref": f"intr:{index}"},
                   "authority_effect": "NONE_RECEIPT_ONLY"}
        receipt["receipt_hash"] = receipt_hash(receipt)
        receipts.append(receipt)
        previous = receipt["receipt_hash"]
    return {"schema": "stegverse.kv-skap-vault-lineage/v1", "task_id": "KV-SKAP-VAULT-FUNCTIONAL-001",
            "principal_ref": principal, "head": previous, "receipts": receipts}


class ExistingContractBytesUnchanged(unittest.TestCase):
    def test_projection_request_schema_and_constants(self) -> None:
        self.assertEqual(binding_module.PROJECTION_REQUEST_SCHEMA,
                         "stegverse.task-registry-sovereign-kv-projection-request/v1")
        constants = {k: getattr(binding_module, k) for k in ("PROJECTION_REQUEST_SCHEMA", "PROJECTION_RECEIPT_SCHEMA",
                                                             "PROVIDER_RECEIPT_SCHEMA", "BINDING_SCHEMA", "CUSTODY_CLASS")}
        self.assertEqual(h(constants), PINNED["constants"])
        self.assertEqual(h(projection_request()), PINNED["fixture_projection_request"])

    def test_existing_function_sources_unchanged(self) -> None:
        for key, digest in PINNED.items():
            if isinstance(key, tuple):
                self.assertEqual(h(segment(*key)), digest, key)

    def test_existing_event_binding_and_receipt_bytes_unchanged(self) -> None:
        bound = event_binding()
        self.assertEqual(h(bound), PINNED["event_binding"])
        result = validate_task_registry_event_custody_result(
            binding=bound, provider_receipt=provider_receipt(bound["provider_write_request"]),
            stored_event_sha256=bound["event_sha256"])
        self.assertEqual(h(result), PINNED["event_receipt"])

    def test_lineage_record_cannot_pass_as_projection_request(self) -> None:
        record = build_vault_lineage_record(exported_lineage=lineage())
        with self.assertRaises(TaskRegistryEventCustodyBindingError):
            build_task_registry_event_custody_binding(projection_request=record, provider_id="google-drive",
                                                      instance_id="kvi_x", kv_set_id="s")


class VaultLineageRecord(unittest.TestCase):
    def bind(self, record=None):
        return build_vault_lineage_custody_binding(
            lineage_record=record or build_vault_lineage_record(exported_lineage=lineage(), session_id="s-1"),
            provider_id="google-drive", instance_id="kvi_vault_001", kv_set_id="kv-skap-vault",
            storage_locator="private://kv/vault-lineage")

    def receipt(self, bound, **over):
        base = provider_receipt(bound["provider_write_request"])
        base.update(over)
        return base

    def test_round_trip_write_and_exact_readback(self) -> None:
        exported = lineage()
        bound = self.bind()
        write, read = bound["provider_write_request"], bound["provider_readback_request"]
        self.assertEqual((write["operation"], read["operation"]), ("WRITE", "READ"))
        self.assertEqual(write["object_ref"], h(exported))
        self.assertEqual(read["object_ref"], h(exported))
        self.assertEqual(write["schema"], "stegverse.kv.storage-provider-operation-request/v1")
        self.assertEqual(bound["head_receipt_hash"], exported["head"])
        result = validate_vault_lineage_custody_result(binding=bound, provider_receipt=self.receipt(bound),
                                                       read_back_lineage=copy.deepcopy(exported))
        self.assertTrue(result["exact_hash_readback_verified"])
        self.assertEqual(result["read_back_lineage_sha256"], result["lineage_sha256"])
        self.assertEqual(result["authority_effect"], "NONE")

    def test_readback_request_is_the_v1_read(self) -> None:
        adapter = default_registry().get("device-local")
        request = build_vault_lineage_readback_request(adapter=adapter, instance_id="kvi_1", kv_set_id="v",
                                                       lineage_sha256="sha256:" + "b" * 64)
        self.assertEqual(request["operation"], "READ")
        self.assertFalse(request["skap_credential_ref_required"])
        with self.assertRaises(KVStorageProviderError):
            build_vault_lineage_readback_request(adapter=adapter, instance_id="kvi_1", kv_set_id="v",
                                                 lineage_sha256="b" * 64)

    def test_broken_lineages_refused(self) -> None:
        for mutate in (
            lambda e: e["receipts"][1].__setitem__("previous_receipt_hash", "sha256:" + "0" * 64),
            lambda e: e["receipts"][2]["body"].__setitem__("intr_transition_ref", "intr:other"),
            lambda e: e.__setitem__("head", e["receipts"][0]["receipt_hash"]),
            lambda e: e["receipts"][1].__setitem__("principal_ref", "principal:bob"),
            lambda e: e.__setitem__("receipts", []),
            lambda e: e.__setitem__("schema", "other"),
        ):
            exported = lineage()
            mutate(exported)
            with self.assertRaises(TaskRegistryEventCustodyBindingError):
                build_vault_lineage_record(exported_lineage=exported)

    def test_credential_material_refused(self) -> None:
        exported = lineage(1)
        exported["receipts"][0]["body"]["private_key"] = "x"
        exported["receipts"][0]["receipt_hash"] = receipt_hash(exported["receipts"][0])
        exported["head"] = exported["receipts"][0]["receipt_hash"]
        with self.assertRaises(TaskRegistryEventCustodyBindingError):
            build_vault_lineage_record(exported_lineage=exported)

    def test_edited_record_does_not_rederive(self) -> None:
        record = build_vault_lineage_record(exported_lineage=lineage())
        record["receipt_count"] = 99
        with self.assertRaises(TaskRegistryEventCustodyBindingError):
            self.bind(record)

    def test_readback_and_receipt_must_match(self) -> None:
        bound = self.bind()
        with self.assertRaises(TaskRegistryEventCustodyBindingError):
            validate_vault_lineage_custody_result(binding=bound, provider_receipt=self.receipt(bound),
                                                  read_back_lineage=lineage(2))
        for over in ({"governance_state": "PENDING_INTERLOCK_INTR"}, {"operation": "READ"},
                     {"intr_receipt_ref": ""}, {"credential_material_present": True}, {"request_id": "kvprov_x"}):
            with self.assertRaises(TaskRegistryEventCustodyBindingError):
                validate_vault_lineage_custody_result(binding=bound, provider_receipt=self.receipt(bound, **over),
                                                      read_back_lineage=lineage())


if __name__ == "__main__":
    unittest.main()

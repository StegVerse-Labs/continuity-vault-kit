from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from runtime.portable_direct_source_ingress import (
    PortableDirectSourceIngressError,
    admit_and_persist_portable_direct_source,
    admit_portable_direct_source,
    persist_canonical_raw,
    sha256_uri,
    sha256_uri_bytes,
)


def build_request(files: list[tuple[str, bytes]], *, canonical_path: str = "04_Media/Pictures") -> dict:
    payload = {
        "schema": "stegverse.kv.portable-direct-source-inline-payload/v1",
        "directory_id": "pictures",
        "canonical_path": canonical_path,
        "source_class": "OWNER_CONTROLLED_FILE",
        "credential_requirement": "NONE",
        "total_bytes": sum(len(raw) for _, raw in files),
        "files": [
            {
                "name": name,
                "media_type": "application/octet-stream",
                "size_bytes": len(raw),
                "sha256": sha256_uri_bytes(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
            for name, raw in files
        ],
        "authority_effect": "NONE",
    }
    carrier = {
        "schema": "stegverse.intr.hb-derived-carrier-binding/v1",
        "carrier_profile": "stegverse.intr.hb-derived-carrier-profile/v1",
        "fundamental_mode": "HB",
        "packet_id": "INTR-0123456789abcdef01234567",
        "payload_hash": sha256_uri(payload),
        "heartbeat_reference": {"heartbeat_epoch": 32, "heartbeat_id": "HB32-TEST"},
        "channel": {"channel_id": "HB:H1:P0"},
        "carrier_grants_admission_authority": False,
        "carrier_grants_execution_authority": False,
        "carrier_grants_credential_authority": False,
        "carrier_grants_routing_authority": False,
        "carrier_grants_transition_authority": False,
        "carrier_grants_receiving_authority": False,
        "credential_authority": "TV/TVC",
        "authority_effect": "NONE_CARRIER_ONLY",
    }
    carrier["binding_sha256"] = sha256_uri(carrier)
    body = {
        "schema": "stegverse.universal-intr-materialization-request/v1",
        "materialization_id": "INTR-MAT-0123456789abcdef01234567",
        "state": "QUEUED_FOR_EVENT_EPHEMERAL_MATERIALIZATION",
        "transport_schema": "stegverse.universal-intr-transport/v1",
        "transport_protocol": "InTr",
        "transport_intent_hash": "sha256:" + "1" * 64,
        "operation_id": "KV-PORTABLE-SOURCE-001",
        "packet_id": "INTR-0123456789abcdef01234567",
        "payload_hash": sha256_uri(payload),
        "payload_ref": "inline://materialization_request.portable_payload",
        "portable_payload": payload,
        "carrier_binding": carrier,
        "destination": {"boundary": "KV", "subsystem": "KnowledgeVault:Interlock"},
        "boundary_path": ["DEVICE_SYSTEM", "KV"],
        "downstream_owner_ref": "StegVerse-Labs/continuity-vault-kit#79",
        "event_triggered": True,
        "always_on_receiver_required": False,
        "second_user_device_required": False,
        "receiver_unavailable_disposition": "DURABLE_QUEUE_OR_EVENT_EPHEMERAL_MATERIALIZATION",
        "exact_packet_transport_retry_allowed": True,
        "blind_consequence_retry_allowed": False,
        "interlock_required": True,
        "request_grants_execution_authority": False,
        "claim_or_fence_minted": False,
        "transport_grants_execution_authority": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_transfer": False,
        "authority_effect": "NONE_REQUEST_ONLY",
    }
    body["request_hash"] = sha256_uri(body)
    return body


def ingress_for(request: dict) -> dict:
    return {
        "schema": "stegverse.device-kv-intr-materialization-ingress/v1",
        "state": "INGRESS_ADMITTED",
        "materialization_id": request["materialization_id"],
        "request_hash": request["request_hash"],
        "transport_intent_hash": request["transport_intent_hash"],
        "payload_hash": request["payload_hash"],
        "operation_id": request["operation_id"],
        "packet_id": request["packet_id"],
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_INGRESS_ONLY",
        "carrier_binding_present": True,
        "carrier_binding_validated": True,
        "carrier_profile": request["carrier_binding"]["carrier_profile"],
        "heartbeat_reference_epoch": request["carrier_binding"]["heartbeat_reference"]["heartbeat_epoch"],
        "heartbeat_reference_id": request["carrier_binding"]["heartbeat_reference"]["heartbeat_id"],
        "carrier_channel_id": request["carrier_binding"]["channel"]["channel_id"],
        "carrier_binding_sha256": request["carrier_binding"]["binding_sha256"],
        "carrier_binding_grants_authority": False,
    }


class PortableDirectSourceIngressTests(unittest.TestCase):
    def test_exact_bytes_stage_and_read_back(self) -> None:
        request = build_request([("one.bin", b"abc"), ("two.bin", b"xyz")])
        ingress = ingress_for(request)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            receipt = admit_portable_direct_source(request, ingress, kv_data_root=root)
            self.assertEqual(receipt["state"], "STAGED_UNTRUSTED")
            self.assertTrue(receipt["canonical_kv_staging_persistence_observed"])
            self.assertTrue(receipt["exact_readback_verified"])
            self.assertFalse(receipt["trusted_semantic_admission"])
            stage = root / receipt["staging_path"]
            self.assertEqual((stage / "files" / "one.bin").read_bytes(), b"abc")
            self.assertEqual((stage / "files" / "two.bin").read_bytes(), b"xyz")
            self.assertEqual(json.loads((stage / "receipt.json").read_text()), receipt)

    def test_canonical_raw_persistence_and_readback(self) -> None:
        request = build_request([("one.bin", b"abc"), ("two.bin", b"xyz")])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"; (root / "00_Inbox").mkdir(parents=True)
            staged = admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)
            receipt = persist_canonical_raw(request, staged, kv_data_root=root)
            self.assertEqual(receipt["state"], "PERSISTED_CANONICAL_RAW")
            self.assertTrue(receipt["canonical_kv_raw_persistence_observed"])
            self.assertTrue(receipt["exact_readback_verified"])
            self.assertFalse(receipt["trusted_semantic_admission"])
            self.assertEqual((root / "04_Media/Pictures/one.bin").read_bytes(), b"abc")
            self.assertEqual((root / "04_Media/Pictures/two.bin").read_bytes(), b"xyz")

    def test_admit_and_persist_completes_raw_path(self) -> None:
        request = build_request([("one.bin", b"abc")])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"; (root / "00_Inbox").mkdir(parents=True)
            result = admit_and_persist_portable_direct_source(request, ingress_for(request), kv_data_root=root)
            self.assertEqual(result["state"], "PERSISTED_CANONICAL_RAW")
            self.assertFalse(result["trusted_semantic_admission"])
            self.assertEqual((root / "04_Media/Pictures/one.bin").read_bytes(), b"abc")

    def test_carrier_authority_tamper_fails_closed(self) -> None:
        request = build_request([("one.bin", b"abc")])
        request["carrier_binding"]["carrier_grants_routing_authority"] = True
        body = dict(request["carrier_binding"]); body.pop("binding_sha256")
        request["carrier_binding"]["binding_sha256"] = sha256_uri(body)
        request["request_hash"] = sha256_uri({k:v for k,v in request.items() if k != "request_hash"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"; (root / "00_Inbox").mkdir(parents=True)
            with self.assertRaisesRegex(PortableDirectSourceIngressError, "carrier_grants_routing_authority_must_be_false"):
                admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)

    def test_idempotent_identical_retry(self) -> None:
        request = build_request([("one.bin", b"abc")])
        ingress = ingress_for(request)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            first = admit_portable_direct_source(request, ingress, kv_data_root=root)
            second = admit_portable_direct_source(request, ingress, kv_data_root=root)
            self.assertEqual(first, second)

    def test_tamper_fails_closed(self) -> None:
        request = build_request([("one.bin", b"abc")])
        request["portable_payload"]["files"][0]["content_base64"] = base64.b64encode(b"abd").decode("ascii")
        request["request_hash"] = sha256_uri({k: v for k, v in request.items() if k != "request_hash"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            with self.assertRaisesRegex(PortableDirectSourceIngressError, "file_sha256_mismatch"):
                admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)

    def test_path_traversal_fails_closed(self) -> None:
        request = build_request([("../escape.bin", b"abc")])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            with self.assertRaises(PortableDirectSourceIngressError):
                admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)

    def test_credential_like_field_fails_closed(self) -> None:
        request = build_request([("one.bin", b"abc")])
        request["portable_payload"]["access_token"] = "forbidden"
        request["payload_hash"] = sha256_uri(request["portable_payload"])
        request["request_hash"] = sha256_uri({k: v for k, v in request.items() if k != "request_hash"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            with self.assertRaisesRegex(PortableDirectSourceIngressError, "secret_like"):
                admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)

    def test_noncanonical_destination_fails_closed(self) -> None:
        request = build_request([("one.bin", b"abc")])
        request["destination"] = {"boundary": "KV", "subsystem": "KnowledgeVault:DirectSourceIngress"}
        request["request_hash"] = sha256_uri({k: v for k, v in request.items() if k != "request_hash"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            (root / "00_Inbox").mkdir(parents=True)
            with self.assertRaisesRegex(PortableDirectSourceIngressError, "request_destination_mismatch"):
                admit_portable_direct_source(request, ingress_for(request), kv_data_root=root)


if __name__ == "__main__":
    unittest.main()

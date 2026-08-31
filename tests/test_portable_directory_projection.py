from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from runtime.portable_directory_projection import (
    PortableDirectoryProjectionError,
    get_directory_health,
    list_admitted_directory,
)

def write_json(path:Path,value:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding="utf-8")

def install_batch(root:Path,mid:str="INTR-MAT-"+"a"*24)->Path:
    batch=root/"04_Media/Pictures"/mid
    file_path=batch/"files/one.bin"
    file_path.parent.mkdir(parents=True,exist_ok=True)
    file_path.write_bytes(b"abc")
    admission={
      "schema":"stegverse.kv.portable-direct-source-canonical-admission/v1",
      "state":"CANONICAL_ADMITTED","materialization_id":mid,
      "request_hash":"sha256:"+"1"*64,"transport_intent_hash":"sha256:"+"2"*64,
      "payload_hash":"sha256:"+"3"*64,"staging_receipt_sha256":"sha256:"+"4"*64,
      "ingress_receipt_sha256":"sha256:"+"5"*64,"directory_id":"pictures",
      "requested_canonical_path":"04_Media/Pictures",
      "canonical_batch_path":str(batch.relative_to(root)),
      "canonical_kv_persistence_observed":True,"exact_canonical_readback_verified":True,
      "trusted_semantic_admission":True,"provider_session_required":False,
      "provider_session_observed":False,"credential_material_present":False,
      "provider_operation_authorized":False,"credential_authority":"TV/TVC",
      "github_token_runtime_authority":"NONE","authority_effect":"NONE",
      "observed_at":"2026-08-31T16:00:00Z","receipt_sha256":"sha256:"+"6"*64,
    }
    provenance={
      "schema":"stegverse.kv.portable-direct-source-provenance/v1",
      "materialization_id":mid,"request_hash":admission["request_hash"],
      "transport_intent_hash":admission["transport_intent_hash"],
      "payload_hash":admission["payload_hash"],"staging_receipt_sha256":admission["staging_receipt_sha256"],
      "ingress_receipt_sha256":admission["ingress_receipt_sha256"],
      "canonical_batch_path":admission["canonical_batch_path"],
      "credential_material_present":False,"provider_operation_authorized":False,
      "authority_effect":"NONE",
      "files":[{"name":"one.bin","media_type":"application/octet-stream","size_bytes":3,
                "sha256":"sha256:"+"7"*64,"canonical_ref":str(file_path.relative_to(root))}],
    }
    health={
      "schema":"stegverse.kv.portable-direct-source-connection-health/v1",
      "directory_id":"pictures","canonical_path":"04_Media/Pictures",
      "compatibility_state":"VERIFIED","last_observed_at":"2026-08-31T16:00:00Z",
      "reason":"OWNER_CONTROLLED_FILE_CANONICAL_READBACK_VERIFIED",
      "revalidation_required":False,
      "connection_proof_ref":str((batch/"admission-receipt.json").relative_to(root)),
      "readback_proof_ref":str((batch/"provenance.json").relative_to(root)),
      "credential_material_present":False,"provider_operation_authorized":False,"authority_effect":"NONE",
    }
    write_json(batch/"admission-receipt.json",admission)
    write_json(batch/"provenance.json",provenance)
    write_json(batch/"connection-health.json",health)
    return batch

class PortableDirectoryProjectionTests(unittest.TestCase):
    def test_lists_only_canonical_admitted_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"KnowledgeVault"; (root/"00_Inbox").mkdir(parents=True)
            install_batch(root)
            result=list_admitted_directory(kv_data_root=root,directory_id="pictures",canonical_path="04_Media/Pictures")
            self.assertEqual(result["state"],"KV_LISTED")
            self.assertEqual(len(result["entries"]),1)
            self.assertEqual(result["entries"][0]["name"],"one.bin")
            self.assertNotIn("content_base64",result["entries"][0])
            self.assertEqual(result["connection_health"]["compatibility_state"],"VERIFIED")

    def test_staged_only_batch_is_not_listed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"KnowledgeVault"; (root/"00_Inbox").mkdir(parents=True)
            staged=root/"04_Media/Pictures"/("INTR-MAT-"+"b"*24)
            staged.mkdir(parents=True)
            result=list_admitted_directory(kv_data_root=root,directory_id="pictures",canonical_path="04_Media/Pictures")
            self.assertEqual(result["entries"],[])
            self.assertIsNone(result["connection_health"])

    def test_unassembled_health_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"KnowledgeVault"; (root/"00_Inbox").mkdir(parents=True)
            health=get_directory_health(kv_data_root=root,directory_id="pictures",canonical_path="04_Media/Pictures")
            self.assertEqual(health["compatibility_state"],"UNASSEMBLED")
            self.assertFalse(health["provider_operation_authorized"])

    def test_receipt_authority_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"KnowledgeVault"; (root/"00_Inbox").mkdir(parents=True)
            batch=install_batch(root)
            value=json.loads((batch/"admission-receipt.json").read_text())
            value["provider_operation_authorized"]=True
            write_json(batch/"admission-receipt.json",value)
            with self.assertRaisesRegex(PortableDirectoryProjectionError,"provider_operation_authorized"):
                list_admitted_directory(kv_data_root=root,directory_id="pictures",canonical_path="04_Media/Pictures")

    def test_path_traversal_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"KnowledgeVault"; (root/"00_Inbox").mkdir(parents=True)
            with self.assertRaises(PortableDirectoryProjectionError):
                list_admitted_directory(kv_data_root=root,directory_id="pictures",canonical_path="../Pictures")

if __name__=="__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from runtime.connection_assembly import assemble_connection, verify_connection
from runtime.connection_registry_store import (
    ConnectionRegistryStoreError, canonical_paths, initialize_store, load_registry,
    persist_health_receipt, persist_source_change, upsert_assembly,
)

class ConnectionRegistryStoreTests(unittest.TestCase):
    def spec(self):
        return {
            "provider":"coinbase","source_kind":"crypto_exchange","target_domain":"finance",
            "canonical_kv_path":"03_Records/Finance","access":"READ_ONLY",
            "direct_source_required":True,"minimum_necessary":True,"credential_authority":"TV/TVC",
            "credential_reference_class":"SKAP_REFERENCE","intr_hops":["SKAP","TVC","Provider","KV"],
            "adapter":{"name":"coinbase-finance-ingress","version":"v1"},
            "provider_capability_binding":{"registry_schema":"stegverse.kv.provider-surface-capability-registry/v1","provider":"coinbase","observation_selector":{},"evidence_version":None},
            "monitoring":{"enabled":True,"authoritative_sources":["provider:coinbase:changelog"],"change_classes":["api_version"],"last_checked_at":None,"last_change_ref":None},
            "authority_effect":"NONE"
        }

    def test_initialize_empty_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); initialize_store(root); value=load_registry(root)
            self.assertEqual(value["state"],"EMPTY")
            self.assertTrue(canonical_paths(root)["source_changes"].is_dir())

    def test_upsert_assembly(self):
        with tempfile.TemporaryDirectory() as td:
            value=upsert_assembly(Path(td),self.spec())
            self.assertEqual(value["state"],"ASSEMBLED_UNVERIFIED")
            self.assertEqual(len(value["assemblies"]),1)

    def test_verified_assembly_sets_verified_registry(self):
        with tempfile.TemporaryDirectory() as td:
            a=assemble_connection(self.spec())
            a,_=verify_connection(a,observed_at="2026-08-28T16:00:00Z",connection_proof_ref="proof:c",readback_proof_ref="proof:r")
            value=upsert_assembly(Path(td),a)
            self.assertEqual(value["state"],"VERIFIED")

    def test_secret_registry_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); initialize_store(root)
            p=canonical_paths(root)["registry"]
            value=json.loads(p.read_text()); value["access_token"]="synthetic"; p.write_text(json.dumps(value))
            with self.assertRaises(ConnectionRegistryStoreError): load_registry(root)

    def test_persist_source_change_and_health(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            obs={"schema":"stegverse.kv.source-change-observation/v1","observation_id":"kvchg_1234567890abcdef12345678","provider":"coinbase","observed_at":"2026-08-28T16:00:00Z","source_ref":"provider:coinbase:changelog","source_type":"provider_changelog","change_class":"api_version","severity":"MEDIUM","breaking":False,"affected_assumptions":["api_version"],"summary":"Synthetic","effective_at":None,"authority_effect":"NONE"}
            sp=persist_source_change(root,obs); self.assertTrue(sp.is_file())
            a=assemble_connection(self.spec())
            _,r=verify_connection(a,observed_at="2026-08-28T16:00:00Z",connection_proof_ref="proof:c",readback_proof_ref="proof:r")
            hp=persist_health_receipt(root,r); self.assertTrue(hp.is_file())

if __name__=="__main__": unittest.main()

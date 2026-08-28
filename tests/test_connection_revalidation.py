import unittest

from runtime.connection_assembly import assemble_connection
from runtime.connection_revalidation import ConnectionRevalidationError, admit_revalidation

class ConnectionRevalidationTests(unittest.TestCase):
    def assembly(self):
        return assemble_connection({
            "provider":"coinbase","source_kind":"crypto_exchange","target_domain":"finance",
            "canonical_kv_path":"03_Records/Finance","access":"READ_ONLY",
            "direct_source_required":True,"minimum_necessary":True,"credential_authority":"TV/TVC",
            "credential_reference_class":"SKAP_REFERENCE","intr_hops":["SKAP","TVC","Provider","KV"],
            "adapter":{"name":"coinbase-finance-ingress","version":"v1"},
            "provider_capability_binding":{"registry_schema":"stegverse.kv.provider-surface-capability-registry/v1","provider":"coinbase","observation_selector":{},"evidence_version":None},
            "monitoring":{"enabled":True,"authoritative_sources":["provider:coinbase:changelog"],"change_classes":["api_version"],"last_checked_at":"2026-08-28T16:00:00Z","last_change_ref":"kvchg_synthetic"},
            "compatibility_state":"REVALIDATION_REQUIRED","authority_effect":"NONE"
        })
    def conformance(self,a):
        return {
            "schema":"stegverse.kv.connection-conformance-proof/v1","assembly_id":a["assembly_id"],
            "provider":"coinbase","observed_at":"2026-08-28T17:00:00Z",
            "direct_source_verified":True,"session_verified":True,
            "adapter":{"name":"coinbase-finance-ingress","version":"v1"},
            "compatibility_assumptions_ref":"sha256:synthetic-current-assumptions",
            "connection_proof_ref":"proof:provider-conformance",
            "provider_operation_authorized":False,"credential_material_present":False,"authority_effect":"NONE"
        }
    def readback(self,a):
        return {
            "schema":"stegverse.kv.connection-readback-proof/v1","assembly_id":a["assembly_id"],
            "canonical_kv_path":"03_Records/Finance","observed_at":"2026-08-28T17:01:00Z",
            "readback_verified":True,"persistence_receipt_ref":"receipt:private-kv-persist",
            "readback_proof_ref":"proof:private-kv-readback",
            "provider_operation_authorized":False,"credential_material_present":False,"authority_effect":"NONE"
        }
    def test_both_proofs_restore_verified(self):
        a=self.assembly()
        updated,receipt=admit_revalidation(a,self.conformance(a),self.readback(a),required_after="2026-08-28T16:00:00Z")
        self.assertEqual(updated["compatibility_state"],"VERIFIED")
        self.assertEqual(receipt["current_state"],"VERIFIED")
        self.assertFalse(receipt["provider_operation_authorized"])
        self.assertFalse(receipt["credential_material_present"])
    def test_stale_proof_rejected(self):
        a=self.assembly(); c=self.conformance(a); c["observed_at"]="2026-08-28T15:59:59Z"
        with self.assertRaises(ConnectionRevalidationError):
            admit_revalidation(a,c,self.readback(a),required_after="2026-08-28T16:00:00Z")
    def test_adapter_mismatch_rejected(self):
        a=self.assembly(); c=self.conformance(a); c["adapter"]["version"]="v2"
        with self.assertRaises(ConnectionRevalidationError):
            admit_revalidation(a,c,self.readback(a))
    def test_path_mismatch_rejected(self):
        a=self.assembly(); r=self.readback(a); r["canonical_kv_path"]="03_Records/Assets"
        with self.assertRaises(ConnectionRevalidationError):
            admit_revalidation(a,self.conformance(a),r)
    def test_secret_field_rejected(self):
        a=self.assembly(); c=self.conformance(a); c["access_token"]="synthetic"
        with self.assertRaises(ConnectionRevalidationError):
            admit_revalidation(a,c,self.readback(a))
    def test_provider_authority_rejected(self):
        a=self.assembly(); c=self.conformance(a); c["provider_operation_authorized"]=True
        with self.assertRaises(ConnectionRevalidationError):
            admit_revalidation(a,c,self.readback(a))
if __name__=="__main__": unittest.main()

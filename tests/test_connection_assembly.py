import unittest
from runtime.connection_assembly import ConnectionAssemblyError, assemble_connection, verify_connection

class ConnectionAssemblyTests(unittest.TestCase):
    def spec(self):
        return {
            "provider":"coinbase",
            "source_kind":"crypto_exchange",
            "target_domain":"finance",
            "canonical_kv_path":"03_Records/Finance",
            "access":"READ_ONLY",
            "direct_source_required":True,
            "minimum_necessary":True,
            "credential_authority":"TV/TVC",
            "credential_reference_class":"SKAP_REFERENCE",
            "authentication_mechanism_class":"provider_native_session",
            "ingress_surface":"provider_api",
            "egress_surface":None,
            "intr_hops":["SKAP","TVC","Provider","KV"],
            "adapter":{"name":"coinbase-finance-ingress","version":"v1"},
            "provider_capability_binding":{
                "registry_schema":"stegverse.kv.provider-surface-capability-registry/v1",
                "provider":"coinbase",
                "observation_selector":{"access_surface":"direct_api"},
                "evidence_version":None
            },
            "monitoring":{
                "enabled":True,
                "authoritative_sources":["provider:coinbase:docs","provider:coinbase:changelog"],
                "change_classes":["api_version","authentication","mfa_session","endpoint","deprecation","changelog","rate_limit","permission_scope","product_model","data_schema","service_health"],
                "last_checked_at":None,
                "last_change_ref":None
            },
            "authority_effect":"NONE"
        }

    def test_deterministic_assembly(self):
        a=assemble_connection(self.spec()); b=assemble_connection(self.spec())
        self.assertEqual(a["assembly_id"],b["assembly_id"])
        self.assertEqual(a["compatibility_state"],"ASSEMBLED_UNVERIFIED")
        self.assertEqual(a["credential_authority"],"TV/TVC")

    def test_secret_rejected(self):
        s=self.spec(); s["access_token"]="synthetic"
        with self.assertRaises(ConnectionAssemblyError): assemble_connection(s)

    def test_write_access_rejected(self):
        s=self.spec(); s["access"]="READ_WRITE"
        with self.assertRaises(ConnectionAssemblyError): assemble_connection(s)

    def test_verified_requires_connection_and_readback(self):
        a=assemble_connection(self.spec())
        with self.assertRaises(ConnectionAssemblyError):
            verify_connection(a,observed_at="2026-08-28T16:00:00Z",connection_proof_ref="proof:connection",readback_proof_ref="")
        updated,receipt=verify_connection(a,observed_at="2026-08-28T16:00:00Z",connection_proof_ref="proof:connection",readback_proof_ref="proof:kv-readback")
        self.assertEqual(updated["compatibility_state"],"VERIFIED")
        self.assertFalse(receipt["provider_operation_authorized"])
        self.assertFalse(receipt["credential_material_present"])

if __name__=="__main__": unittest.main()

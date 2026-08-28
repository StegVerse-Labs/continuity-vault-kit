import unittest
from runtime.connection_assembly import assemble_connection, verify_connection
from runtime.source_change_monitor import evaluate_source_change

class SourceChangeMonitorTests(unittest.TestCase):
    def assembly(self):
        spec={
            "provider":"coinbase","source_kind":"crypto_exchange","target_domain":"finance",
            "canonical_kv_path":"03_Records/Finance","access":"READ_ONLY",
            "direct_source_required":True,"minimum_necessary":True,"credential_authority":"TV/TVC",
            "credential_reference_class":"SKAP_REFERENCE","intr_hops":["SKAP","TVC","Provider","KV"],
            "adapter":{"name":"coinbase-finance-ingress","version":"v1"},
            "provider_capability_binding":{"registry_schema":"stegverse.kv.provider-surface-capability-registry/v1","provider":"coinbase","observation_selector":{},"evidence_version":None},
            "monitoring":{"enabled":True,"authoritative_sources":["provider:coinbase:changelog"],"change_classes":["authentication","api_version","service_health"],"last_checked_at":None,"last_change_ref":None},
            "authority_effect":"NONE"
        }
        a=assemble_connection(spec)
        a,_=verify_connection(a,observed_at="2026-08-28T15:00:00Z",connection_proof_ref="proof:c",readback_proof_ref="proof:r")
        return a

    def change(self, change_class="api_version", breaking=False):
        return {
            "provider":"coinbase","observed_at":"2026-08-28T16:00:00Z","source_ref":"provider:coinbase:changelog:1",
            "source_type":"provider_changelog","change_class":change_class,"severity":"MEDIUM","breaking":breaking,
            "affected_assumptions":["adapter_api_version"],"summary":"Synthetic provider change"
        }

    def test_nonbreaking_monitored_change_requires_revalidation(self):
        a,r=evaluate_source_change(self.assembly(),self.change())
        self.assertEqual(a["compatibility_state"],"REVALIDATION_REQUIRED")
        self.assertTrue(r["revalidation_required"])

    def test_breaking_auth_change_blocks(self):
        a,r=evaluate_source_change(self.assembly(),self.change("authentication",True))
        self.assertEqual(a["compatibility_state"],"BLOCKED_SOURCE_CHANGE")
        self.assertEqual(r["reason"],"BREAKING_SOURCE_CHANGE")

    def test_unmonitored_change_does_not_invalidate(self):
        a,r=evaluate_source_change(self.assembly(),self.change("export_format",True))
        self.assertEqual(a["compatibility_state"],"VERIFIED")
        self.assertFalse(r["revalidation_required"])

if __name__=="__main__": unittest.main()

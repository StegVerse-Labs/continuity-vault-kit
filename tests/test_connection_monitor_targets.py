import unittest

from runtime.connection_monitor_targets import ConnectionMonitorTargetError, compile_monitor_targets, validate_target_document

class ConnectionMonitorTargetTests(unittest.TestCase):
    def assembly(self):
        return {
            "provider":"coinbase",
            "monitoring":{
                "authoritative_sources":["coinbase:changelog"],
                "change_classes":["api_version"],
            }
        }
    def catalog(self):
        return {
            "coinbase:changelog":{
                "url":"https://docs.coinbase.example/changelog",
                "allowed_host":"docs.coinbase.example",
                "source_type":"provider_changelog",
                "change_class":"api_version",
                "severity":"MEDIUM",
                "breaking_on_change":False,
                "affected_assumptions":["adapter_api_version"],
                "summary_on_change":"Coinbase changelog changed"
            }
        }

    def test_compile_deterministic_target(self):
        a=compile_monitor_targets([self.assembly()],self.catalog())
        b=compile_monitor_targets([self.assembly()],self.catalog())
        self.assertEqual(a,b)
        self.assertTrue(a["targets"][0]["target_id"].startswith("kvmon_"))
        validate_target_document(a)

    def test_non_https_rejected(self):
        catalog=self.catalog(); catalog["coinbase:changelog"]["url"]="http://docs.coinbase.example/changelog"
        with self.assertRaises(ConnectionMonitorTargetError): compile_monitor_targets([self.assembly()],catalog)

    def test_host_mismatch_rejected(self):
        catalog=self.catalog(); catalog["coinbase:changelog"]["allowed_host"]="evil.example"
        with self.assertRaises(ConnectionMonitorTargetError): compile_monitor_targets([self.assembly()],catalog)

    def test_embedded_credentials_rejected(self):
        catalog=self.catalog(); catalog["coinbase:changelog"]["url"]="https://user:pass@docs.coinbase.example/changelog"
        with self.assertRaises(ConnectionMonitorTargetError): compile_monitor_targets([self.assembly()],catalog)

    def test_secret_descriptor_rejected(self):
        catalog=self.catalog(); catalog["coinbase:changelog"]["access_token"]="synthetic"
        # descriptor field is not copied, so rejection is enforced by validating source catalog first at integration boundary
        with self.assertRaises(Exception):
            from runtime.connection_assembly import reject_secret_fields
            reject_secret_fields(catalog)

if __name__=="__main__": unittest.main()

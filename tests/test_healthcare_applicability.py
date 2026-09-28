import json, unittest
from scripts.resolve_healthcare_applicability import resolve

class TestHealthcareApplicability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.load(open("data/healthcare-authority-schema-registry.v1.json"))

    def test_hospital_provider_price_uses_hpt(self):
        x=resolve("HOSPITAL","US_TX","PROVIDER_CASH_PRICE",self.r)
        self.assertEqual(x["disposition"],"ALLOW")
        self.assertEqual(x["matches"][0]["authority_id"],"CMS-HPT-2026")

    def test_plan_public_rate_uses_tic_2(self):
        x=resolve("GROUP_HEALTH_PLAN","US_TX","PAYER_IN_NETWORK_RATE",self.r)
        self.assertEqual(x["disposition"],"ALLOW")
        self.assertEqual(x["matches"][0]["schema_version"],"2.0")

    def test_member_estimate_not_collapsed_into_public_mrf(self):
        x=resolve("GROUP_HEALTH_PLAN","US_TX","MEMBER_SPECIFIC_COST_SHARING_ESTIMATE",self.r)
        self.assertEqual(x["disposition"],"ALLOW")
        self.assertEqual(x["matches"][0]["required_surface"],"MEMBER_AUTHORIZED_PRICE_COMPARISON_SURFACE")

    def test_unknown_entity_fails_closed(self):
        x=resolve("UNREGISTERED_PROVIDER_CLASS","US_TX","PROVIDER_CASH_PRICE",self.r)
        self.assertEqual(x["disposition"],"FAIL_CLOSED")
        self.assertEqual(x["predicate"],"APPLICABLE_AUTHORITY_RESOLVED")

if __name__=="__main__": unittest.main()

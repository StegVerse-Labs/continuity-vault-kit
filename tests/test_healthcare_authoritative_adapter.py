import hashlib,json,unittest
from scripts.resolve_healthcare_applicability import REGISTRY
from scripts.select_healthcare_authoritative_adapter import select_and_preserve

class TestHealthcareAuthoritativeAdapter(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=json.loads(REGISTRY.read_text())
 def test_hpt_preserves_exact_source_without_field_renaming(self):
  raw=b'{"standard_charge_information":[{"discounted_cash":"125.00"}]}'
  x=select_and_preserve("HOSPITAL","US_TX","PROVIDER_CASH_PRICE",raw,"application/json","fixture:hpt",self.r)
  self.assertEqual(x["disposition"],"ALLOW"); self.assertEqual(x["adapter_id"],"CMS_HPT_MACHINE_READABLE_FILE")
  self.assertEqual(x["evidence"]["source_sha256"],hashlib.sha256(raw).hexdigest())
  self.assertFalse(x["evidence"]["governing_fields_renamed"])
 def test_tic_selects_v2_adapter(self):
  x=select_and_preserve("GROUP_HEALTH_PLAN","US_TX","PAYER_IN_NETWORK_RATE",b'{}',"application/json","fixture:tic",self.r)
  self.assertEqual(x["adapter_id"],"CMS_TIC_V2_MACHINE_READABLE_FILE")
 def test_member_surface_is_separate_adapter(self):
  x=select_and_preserve("GROUP_HEALTH_PLAN","US_TX","MEMBER_SPECIFIC_COST_SHARING_ESTIMATE",b'{}',"application/json","fixture:member",self.r)
  self.assertEqual(x["adapter_id"],"MEMBER_AUTHORIZED_COST_COMPARISON")
 def test_unregistered_class_fails_closed_before_adapter(self):
  x=select_and_preserve("PHYSICIAN_OFFICE","US_TX","PROVIDER_CASH_PRICE",b'{}',"application/json","fixture:unknown",self.r)
  self.assertEqual(x["disposition"],"FAIL_CLOSED"); self.assertEqual(x["predicate"],"APPLICABLE_AUTHORITY_RESOLVED")
if __name__=="__main__":unittest.main()

import unittest
from scripts.validate_healthcare_assertion import open_validation,resolve_validation,escalation_package

class TestHealthcareAssertionValidation(unittest.TestCase):
 def request(self):
  return open_validation("a"*64,{"type":"CLAIM","amount":"2200.00"},["SERVICE_RECORD","CODE_BASIS","PRICE_BASIS"])
 def test_complete_rebuttal_rebuts_presumption(self):
  r=self.request(); ev=[{"kind":k,"evidence_ref":k+"#1","sha256":"b"*64} for k in ["SERVICE_RECORD","CODE_BASIS","PRICE_BASIS"]]
  x=resolve_validation(r,ev); self.assertEqual(x["state"],"PRESUMPTION_REBUTTED"); self.assertFalse(x["original_state_mutated"])
 def test_missing_evidence_escalates(self):
  x=resolve_validation(self.request(),[{"kind":"SERVICE_RECORD","evidence_ref":"service#1","sha256":"b"*64}])
  self.assertEqual(x["disposition"],"DENY"); self.assertEqual(x["state"],"UNRESOLVED_SUSPECTED_FRAUD / ESCALATION_REQUIRED")
  self.assertIn("CODE_BASIS",x["missing_evidence"])
 def test_escalation_package_preserves_pre_state_hash(self):
  x=resolve_validation(self.request(),[])
  p=escalation_package(x,{"authority_id":"APPLICABILITY_RESOLVER_SELECTED_AUTHORITY"})
  self.assertEqual(p["disposition"],"ALLOW"); self.assertEqual(p["package"]["pre_service_state_sha256"],"a"*64); self.assertEqual(p["submission_effect"],"NONE_NOT_SUBMITTED")
 def test_rebutted_assertion_is_not_escalated(self):
  r=self.request(); ev=[{"kind":k,"evidence_ref":k,"sha256":"b"*64} for k in ["SERVICE_RECORD","CODE_BASIS","PRICE_BASIS"]]
  p=escalation_package(resolve_validation(r,ev),{})
  self.assertEqual(p["disposition"],"DENY")
if __name__=="__main__":unittest.main()

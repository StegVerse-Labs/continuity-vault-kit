import json,unittest
from scripts.resolve_healthcare_applicability import REGISTRY
from scripts.bind_healthcare_governed_escalation import bind_oversight,build_egress_candidate,record_egress_result

class TestHealthcareGovernedEscalation(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=json.loads(REGISTRY.read_text())
 def candidate(self):
  o=bind_oversight("HOSPITAL","US_TX","PROVIDER_CASH_PRICE",self.r)
  e={"disposition":"ALLOW","predicate":"ESCALATION_PACKAGE_ASSEMBLED","package":{"request_id":"r1"},"package_sha256":"a"*64}
  return build_egress_candidate(e,o,"MYKV-HEALTHCARE-TRANSACTION-EVIDENCE-001","20010000100000")
 def test_registry_binds_actual_regulator(self):
  o=bind_oversight("HOSPITAL","US_TX","PROVIDER_CASH_PRICE",self.r)
  self.assertEqual(o["disposition"],"ALLOW"); self.assertEqual(o["oversight"]["regulator"],"Centers for Medicare & Medicaid Services")
 def test_candidate_uses_existing_governed_components(self):
  c=self.candidate(); self.assertIn("RTC-STEGVERSE-EGRESS-007",c["packet"]["required_components"]); self.assertEqual(c["submission_effect"],"NONE_NOT_SUBMITTED")
 def test_absent_runtime_receipt_is_actionable_fail_closed(self):
  x=record_egress_result(self.candidate())
  self.assertEqual(x["disposition"],"FAIL_CLOSED"); self.assertEqual(x["failed_predicate"],"AUTHENTIC_INTR_EGRESS_DISPOSITION_OBSERVED")
 def test_intr_deny_is_preserved(self):
  x=record_egress_result(self.candidate(),{"disposition":"DENY","receipt_ref":"intr#1","failed_predicate":"DESTINATION_NOT_ADMITTED"})
  self.assertEqual(x["disposition"],"DENY"); self.assertEqual(x["failed_predicate"],"DESTINATION_NOT_ADMITTED")
 def test_allow_requires_org_and_master_records_custody(self):
  x=record_egress_result(self.candidate(),{"disposition":"ALLOW","receipt_ref":"intr#1"})
  self.assertEqual(x["disposition"],"FAIL_CLOSED"); self.assertEqual(x["predicate"],"EGRESS_CUSTODY_RECONSTRUCTED")
 def test_complete_chain_proves_submission(self):
  x=record_egress_result(self.candidate(),{"disposition":"ALLOW","receipt_ref":"intr#1"},{"receipt_ref":"org#1"},{"reconstruction_ref":"mr#1"})
  self.assertEqual(x["disposition"],"ALLOW"); self.assertEqual(x["submission_effect"],"AUTHENTIC_SUBMISSION_EVIDENCED")
if __name__=="__main__":unittest.main()

import unittest
from scripts.evaluate_healthcare_transaction_evidence import extract_hpt,extract_tic_v2,extract_member_cost,patient_evaluation

class TestHealthcareSemanticEvaluation(unittest.TestCase):
 def test_hpt_keeps_governing_field(self):
  raw=b'{"standard_charge_information":[{"description":"MRI","discounted_cash":"500.00"}]}'
  x=extract_hpt(raw,"fixture:hpt")
  self.assertEqual(x["disposition"],"ALLOW")
  self.assertIn("standard_charge_information",x["governing_facts"])
  self.assertFalse(x["governing_fields_renamed"])
 def test_tic_missing_required_field_fails_closed(self):
  x=extract_tic_v2(b'{"reporting_entity_name":"Plan"}',"fixture:tic")
  self.assertEqual(x["disposition"],"FAIL_CLOSED")
 def test_member_cost_is_distinct(self):
  x=extract_member_cost(b'{"patient_responsibility":"75.00"}',"fixture:member")
  self.assertEqual(x["authority_id"],"CMS-TIC-COST-COMPARISON")
 def test_patient_evaluation_never_selects_path(self):
  p=extract_hpt(b'{"standard_charge_information":[]}',"fixture:hpt")
  m=extract_member_cost(b'{"patient_responsibility":"75.00"}',"fixture:member")
  x=patient_evaluation(p,None,m)
  self.assertEqual(x["disposition"],"ALLOW")
  self.assertIsNone(x["patient_decision"])
  self.assertTrue(x["patient_decision_required"])
 def test_bad_evidence_is_not_zero(self):
  p=extract_hpt(b'{}',"fixture:hpt")
  x=patient_evaluation(p)
  self.assertEqual(x["evidence_status"],"NOT_VERIFIED")
  self.assertNotIn("patient_responsibility",x)
if __name__=="__main__":unittest.main()

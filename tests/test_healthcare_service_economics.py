import unittest
from scripts.evaluate_healthcare_service_economics import evaluate_service

class TestHealthcareServiceEconomics(unittest.TestCase):
 def test_service_specific_cash_and_member_cost_derivation(self):
  s={"code":"73221"}
  p=[{"billing_code":"73221","discounted_cash":"500.00","_evidence_refs":["hpt#abc"]}]
  q=[{"code":"73221","negotiated_rate":"900.00","_evidence_refs":["tic#def"]}]
  m={"patient_responsibility":"75.00","_evidence_refs":["member#ghi"]}
  x=evaluate_service(s,p,q,m)
  self.assertEqual(x["evidence_status"],"VERIFIED")
  self.assertEqual(x["comparison"]["difference"]["amount"],"-425.00")
  self.assertIsNone(x["comparison"]["recommendation"])
  self.assertIsNone(x["patient_decision"])
 def test_other_service_cannot_supply_price(self):
  x=evaluate_service({"code":"72141"},[{"billing_code":"73221","discounted_cash":"500.00"}])
  self.assertEqual(x["disposition"],"FAIL_CLOSED")
  self.assertEqual(x["predicate"],"SCHEDULED_SERVICE_PROVIDER_FACT_BOUND")
 def test_ambiguous_provider_rows_fail_closed(self):
  rows=[{"billing_code":"73221","discounted_cash":"500"},{"billing_code":"73221","discounted_cash":"550"}]
  x=evaluate_service({"code":"73221"},rows)
  self.assertEqual(x["disposition"],"FAIL_CLOSED")
 def test_missing_member_cost_does_not_become_zero(self):
  x=evaluate_service({"code":"73221"},[{"billing_code":"73221","discounted_cash":"500"}])
  self.assertEqual(x["evidence_status"],"PARTIALLY_VERIFIED")
  self.assertIsNone(x["comparison"]["insurance_patient_outlay"])
if __name__=="__main__": unittest.main()

import copy,unittest
from scripts.bind_healthcare_transaction_state import seal_pre_service,reconcile

class TestHealthcareTransactionState(unittest.TestCase):
 def base(self):
  ev={"disposition":"ALLOW","patient_decision":None,"derived_values":[]}
  return seal_pre_service({"code":"73221"},ev,{"policy_id":"P1"},["provider#1","payer#1"])
 def test_seals_immutable_pre_service_state(self):
  x=self.base(); self.assertEqual(x["disposition"],"ALLOW"); self.assertTrue(x["immutable"]); self.assertEqual(len(x["state_sha256"]),64)
 def test_mutation_fails_closed(self):
  x=self.base(); x["state"]["service"]["code"]="72141"; y=reconcile(x,[])
  self.assertEqual(y["disposition"],"FAIL_CLOSED"); self.assertEqual(y["predicate"],"PRE_SERVICE_STATE_HASH_VALID")
 def test_actual_service_variance_requires_validation(self):
  x=self.base(); y=reconcile(x,[{"code":"72141","evidence_refs":["service#2"]}])
  self.assertEqual(y["evidence_status"],"CONFLICTING_EVIDENCE"); self.assertEqual(y["variances"][0]["status"],"VALIDATION_REQUIRED")
 def test_unsupported_claim_enters_presumptive_fraud_validation(self):
  x=self.base(); y=reconcile(x,[{"code":"73221"}],claim={"type":"CLAIM","amount":"2200.00","evidence_refs":[]})
  self.assertEqual(y["unsupported_assertions"][0]["state"],"PRESUMPTIVE_FRAUD / VALIDATION_REQUIRED")
  self.assertFalse(y["patient_responsibility_inferred"])
 def test_supported_objects_do_not_create_patient_liability_by_themselves(self):
  x=self.base(); y=reconcile(x,[{"code":"73221"}],claim={"type":"CLAIM","evidence_refs":["claim#1"]},eob={"type":"EOB","evidence_refs":["eob#1"]},payment={"type":"PAYMENT","evidence_refs":["payment#1"]})
  self.assertEqual(y["evidence_status"],"VERIFIED"); self.assertFalse(y["patient_responsibility_inferred"])
if __name__=="__main__":unittest.main()

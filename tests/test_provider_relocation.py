from __future__ import annotations
import copy, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from provider_relocation import evaluate  # noqa: E402

BASE={
 "source_provider":"iCloud",
 "destination_provider":"Google Drive",
 "source_provider_is_kv_authority":False,
 "destination_provider_is_kv_authority":False,
 "kv_identity_preserved":True,
 "continuity_transition_valid":True,
 "interlock_verified":True,
 "intr_bound":True,
}

class ProviderRelocationTests(unittest.TestCase):
 def test_valid_relocation(self):
  r=evaluate(copy.deepcopy(BASE))
  self.assertEqual(r["decision"],"ALLOW_WITH_SIGNOFF")
  self.assertTrue(r["kv_identity_preserved"])
  self.assertEqual(r["authority_effect"],"NONE")
 def test_destination_provider_authority_fails_closed(self):
  x=copy.deepcopy(BASE); x["destination_provider_is_kv_authority"]=True
  self.assertEqual(evaluate(x)["decision"],"FAIL_CLOSED")
 def test_missing_intr_fails_closed(self):
  x=copy.deepcopy(BASE); x["intr_bound"]=False
  self.assertEqual(evaluate(x)["decision"],"FAIL_CLOSED")
 def test_bad_continuity_escalates(self):
  x=copy.deepcopy(BASE); x["continuity_transition_valid"]=False
  self.assertEqual(evaluate(x)["decision"],"ESCALATE")

if __name__=="__main__": unittest.main()

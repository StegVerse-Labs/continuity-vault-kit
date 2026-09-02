from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from provider_relocation import evaluate  # noqa: E402

REQUEST={
 "schema":"stegverse.kv.provider-relocation-request/v1",
 "relocation_id":"relocate-001",
 "kv_id":"kv-test",
 "source_provider":"iCloud",
 "destination_provider":"Google Drive",
 "source_continuity_root":"a"*64,
 "destination_continuity_root":"a"*64,
 "kv_identity_preserved":True,
 "continuity_transition":"PRESERVED",
 "transport":{"protocol":"InTr","interlock_verified":True,"intr_bound":True},
 "authority":{"source_provider_is_kv_authority":False,"destination_provider_is_kv_authority":False,"credential_authority":"TV/TVC"}
}
EVIDENCE={
 "schema":"stegverse.kv.provider-relocation-evidence/v1",
 "relocation_id":"relocate-001",
 "request_sha256":"1"*64,
 "source_readback_sha256":"2"*64,
 "destination_readback_sha256":"2"*64,
 "intr_packet_ref":"intr:packet:1",
 "intr_receipt_ref":"intr:receipt:1",
 "continuity_receipt_ref":"continuity:receipt:1",
 "provider_credentials_exported":False,
 "provider_authority_transferred":False
}

class ProviderRelocationTests(unittest.TestCase):
 def test_deterministic_path_requires_signoff(self):
  r=evaluate(copy.deepcopy(REQUEST))
  self.assertEqual(r["decision"],"ALLOW_WITH_SIGNOFF")
  self.assertFalse(r["exact_readback_match"])

 def test_observed_exact_relocation_allows(self):
  r=evaluate(copy.deepcopy(REQUEST),copy.deepcopy(EVIDENCE))
  self.assertEqual(r["decision"],"ALLOW")
  self.assertTrue(r["exact_readback_match"])
  self.assertEqual(r["authority_effect"],"NONE")

 def test_provider_authority_fails_closed(self):
  x=copy.deepcopy(REQUEST);x["authority"]["destination_provider_is_kv_authority"]=True
  self.assertEqual(evaluate(x)["decision"],"FAIL_CLOSED")

 def test_missing_intr_fails_closed(self):
  x=copy.deepcopy(REQUEST);x["transport"]["intr_bound"]=False
  self.assertEqual(evaluate(x)["decision"],"FAIL_CLOSED")

 def test_preserved_root_drift_escalates(self):
  x=copy.deepcopy(REQUEST);x["destination_continuity_root"]="b"*64
  self.assertEqual(evaluate(x)["decision"],"ESCALATE")

 def test_readback_mismatch_fails_closed(self):
  e=copy.deepcopy(EVIDENCE);e["destination_readback_sha256"]="3"*64
  self.assertEqual(evaluate(copy.deepcopy(REQUEST),e)["decision"],"FAIL_CLOSED")

if __name__=="__main__": unittest.main()

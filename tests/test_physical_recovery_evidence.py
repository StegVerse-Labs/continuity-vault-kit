from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from physical_recovery_evidence import reconstruct  # noqa: E402

BASE={
 "schema":"stegverse.kv.physical-recovery-evidence/v1","experiment_id":"physical-001","kv_id":"kv-test","provider":"iCloud",
 "provider_access":{"mode":"BROWSER_ONLY","encrypted_package_acquired":True,"provider_auth_exposes_usable_kv":False},
 "old_device":{"device_id":"iphone-A","status_before":"CONFIRMED","status_after":"LOST_REVOKED","unavailable_observed":True},
 "new_device":{"device_id":"samsung-B","platform":"Android","distinct_identity":True,"registration_observed":True,"attestation_ref":"attestation:test"},
 "recovery_authority":{"verified":True,"independent_of_provider_auth":True,"evidence_ref":"authority:test"},
 "continuity":{"root_before":"a"*64,"root_after":"b"*64,"kv_identity_preserved":True},
 "transport":{"protocol":"InTr","interlock_observed":True,"intr_packet_ref":"intr:packet:test","intr_receipt_ref":"intr:receipt:test"},
 "key_provisioning":{"mode":"REWRAP","observed":True,"old_device_key_reused":False},
 "final_receipt":{"receipt_ref":"receipt:test","receipt_sha256":"c"*64}
}

class PhysicalRecoveryEvidenceTests(unittest.TestCase):
 def test_complete_observation_reconstructs(self):
  r=reconstruct(copy.deepcopy(BASE))
  self.assertEqual(r["decision"],"ALLOW_WITH_SIGNOFF")
  self.assertTrue(r["physical_recovery_proven"])
  self.assertFalse(r["old_device_identity_preserved"])
  self.assertEqual(r["authority_effect"],"NONE")

 def test_provider_login_cannot_substitute_for_recovery_authority(self):
  e=copy.deepcopy(BASE); e["recovery_authority"]["verified"]=False
  r=reconstruct(e); self.assertEqual(r["decision"],"FAIL_CLOSED"); self.assertFalse(r["physical_recovery_proven"])

 def test_old_identity_reuse_fails_closed(self):
  e=copy.deepcopy(BASE); e["new_device"]["device_id"]="iphone-A"
  self.assertEqual(reconstruct(e)["decision"],"FAIL_CLOSED")

 def test_missing_intr_observation_fails_closed(self):
  e=copy.deepcopy(BASE); e["transport"]["interlock_observed"]=False
  self.assertEqual(reconstruct(e)["decision"],"FAIL_CLOSED")

 def test_key_reuse_fails_closed(self):
  e=copy.deepcopy(BASE); e["key_provisioning"]["old_device_key_reused"]=True
  self.assertEqual(reconstruct(e)["decision"],"FAIL_CLOSED")

if __name__=="__main__": unittest.main()

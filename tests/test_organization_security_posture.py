import unittest
from runtime.organization_security_posture import materialize_posture, authorize_operation, posture_change_receipt

class OrgPostureTests(unittest.TestCase):
    def mk(self,preset="GOVERNMENT_HIGH_CONTROL",tier="P2_RECONSTRUCTION",version=1):
        return materialize_posture(organization_id="org:test",posture_id="posture:test",version=version,preset=preset,effective_at="2026-08-28T23:00:00Z",employee_kv_count=100,capability_tier=tier,official_use_default=True)

    def test_p1_replay_but_not_reconstruction(self):
        p=self.mk(tier="P1_REPLAY")
        self.assertTrue(p["surfaces"]["org_replay"])
        self.assertFalse(p["surfaces"]["org_reconstruction"])

    def test_p2_reconstruction_requires_authorized_role(self):
        p=self.mk()
        self.assertTrue(authorize_operation(p,operation="RECONSTRUCT",actor_role="AUDITOR",purpose_declared=True)["allowed"])
        self.assertFalse(authorize_operation(p,operation="RECONSTRUCT",actor_role="IT_ADMIN",purpose_declared=True)["allowed"])

    def test_government_posture_no_employee_consent_requirement(self):
        p=self.mk()
        d=authorize_operation(p,operation="INSPECT",actor_role="IT_ADMIN",purpose_declared=True,employee_consent=False)
        self.assertTrue(d["allowed"])

    def test_compartment_denies_even_broad_org_authority(self):
        p=self.mk()
        d=authorize_operation(p,operation="INSPECT",actor_role="IT_ADMIN",purpose_declared=True,clearance_ok=False)
        self.assertFalse(d["allowed"]); self.assertEqual(d["reason"],"CLEARANCE_OR_COMPARTMENT_DENIED")

    def test_employee_private_requires_consent(self):
        p=self.mk(preset="EMPLOYEE_PRIVATE",tier="P1_REPLAY")
        d=authorize_operation(p,operation="INSPECT",actor_role="ORG_ADMIN",purpose_declared=True,employee_consent=False)
        self.assertFalse(d["allowed"]); self.assertEqual(d["reason"],"EMPLOYEE_CONSENT_REQUIRED")

    def test_posture_change_is_hash_bound_and_history_not_silent(self):
        a=self.mk(version=1)
        b=self.mk(preset="COMPARTMENTED_REGULATED",version=2)
        r=posture_change_receipt(a,b,actor_ref="actor:1",role="SECURITY_ADMIN",decision_ref="decision:2")
        self.assertEqual(r["prior_version"],1); self.assertEqual(r["new_version"],2)
        self.assertEqual(r["historical_scope_effect"],"NONE")
        self.assertEqual(len(r["new_posture_hash"]),64)

if __name__=="__main__": unittest.main()

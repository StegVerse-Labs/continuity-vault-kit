import unittest

from delegation.onboarding import propose_standing_delegation, render_governance_profile


class DelegationOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.pattern = {
            "purpose": "Post selected family photos to the private family group",
            "actions": ["publish_post"],
            "resources": ["photo:user_selected", "caption:user_supplied"],
            "destinations": ["facebook:private-family-group"],
            "constraints": {"visibility": "private_group"},
            "exclusions": ["public_timeline", "location_tagging"],
            "starts_at": "2026-07-15T21:10:00Z",
            "expires_at": "2027-07-15T21:10:00Z",
        }

    def test_repeated_instruction_becomes_proposal_not_authority(self):
        proposal = propose_standing_delegation(
            self.pattern,
            delegation_id="proposal-001",
            principal={"entity_id": "user:owner", "entity_type": "user"},
            delegate={"entity_id": "auri:primary", "entity_type": "governed_ai"},
        )
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["authority_source"], "standing_delegation")
        self.assertTrue(proposal["validity"]["revocable"])

    def test_profile_separates_active_and_proposed(self):
        proposal = propose_standing_delegation(
            self.pattern,
            delegation_id="proposal-001",
            principal={"entity_id": "user:owner", "entity_type": "user"},
            delegate={"entity_id": "auri:primary", "entity_type": "governed_ai"},
        )
        active = dict(proposal)
        active["delegation_id"] = "active-001"
        active["status"] = "active"
        profile = render_governance_profile([active, proposal])
        self.assertEqual(len(profile["active_delegations"]), 1)
        self.assertEqual(len(profile["proposed_changes"]), 1)
        self.assertIn("revoke", profile["user_controls"])

    def test_missing_pattern_fields_fail(self):
        incomplete = dict(self.pattern)
        del incomplete["destinations"]
        with self.assertRaises(ValueError):
            propose_standing_delegation(
                incomplete,
                delegation_id="proposal-002",
                principal={"entity_id": "user:owner", "entity_type": "user"},
                delegate={"entity_id": "auri:primary", "entity_type": "governed_ai"},
            )


if __name__ == "__main__":
    unittest.main()

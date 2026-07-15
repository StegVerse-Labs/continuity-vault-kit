import json
import unittest
from pathlib import Path

from delegation.lifecycle import DelegationTransitionError, transition_delegation

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads((ROOT / "fixtures" / "delegation" / name).read_text(encoding="utf-8"))


class DelegationLifecycleTests(unittest.TestCase):
    def test_narrowing_creates_proposal_and_lineage(self):
        policy = load("standing-social-posts.json")
        successor, receipt = transition_delegation(
            policy,
            transition="narrow",
            actor="user:owner",
            reason="Keep automatic posting private",
            occurred_at="2026-07-15T22:00:00Z",
            requested_change={"scope.destinations": ["facebook:private-family-group"]},
            user_accepted=True,
        )
        self.assertEqual(successor["status"], "proposed")
        self.assertEqual(receipt["event"], "delegation_revised")
        self.assertNotEqual(receipt["source_policy_sha256"], receipt["result_policy_sha256"])

    def test_expansion_requires_user_acceptance(self):
        policy = load("standing-social-posts.json")
        with self.assertRaises(DelegationTransitionError):
            transition_delegation(
                policy,
                transition="expand",
                actor="auri:primary",
                reason="Observed repeated public posts",
                occurred_at="2026-07-15T22:00:00Z",
                requested_change={"scope.destinations": ["facebook:private-family-group", "facebook:public-timeline"]},
            )

    def test_revocation_terminates_authority_and_receipts(self):
        policy = load("standing-social-posts.json")
        successor, receipt = transition_delegation(
            policy,
            transition="revoke",
            actor="user:owner",
            reason="Stop automatic social posting",
            occurred_at="2026-07-15T22:00:00Z",
            user_accepted=True,
        )
        self.assertEqual(successor["status"], "revoked")
        self.assertEqual(successor["validity"]["revocation_reason"], "Stop automatic social posting")
        self.assertEqual(receipt["event"], "delegation_revoked")

    def test_expiry_may_be_clock_recorded(self):
        policy = load("standing-social-posts.json")
        successor, receipt = transition_delegation(
            policy,
            transition="expire",
            actor="system:clock",
            reason="Delegation validity window ended",
            occurred_at="2027-07-15T21:10:00Z",
        )
        self.assertEqual(successor["status"], "expired")
        self.assertFalse(receipt["user_accepted"])

    def test_source_policy_is_not_mutated(self):
        policy = load("standing-social-posts.json")
        original = json.dumps(policy, sort_keys=True)
        transition_delegation(
            policy,
            transition="revoke",
            actor="user:owner",
            reason="Stop automatic social posting",
            occurred_at="2026-07-15T22:00:00Z",
            user_accepted=True,
        )
        self.assertEqual(json.dumps(policy, sort_keys=True), original)


if __name__ == "__main__":
    unittest.main()

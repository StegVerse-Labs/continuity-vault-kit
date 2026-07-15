import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from delegation.decision import DelegationError, decide, validate_delegation


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 15, 21, 30, tzinfo=timezone.utc)


def load(name: str):
    return json.loads((ROOT / "fixtures" / "delegation" / name).read_text(encoding="utf-8"))


class DelegationDecisionTests(unittest.TestCase):
    def test_direct_instruction_acts_without_redundant_confirmation(self):
        policy = load("direct-facebook-post.json")
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:current_capture",
            "destination": "facebook:owner-account",
        }, now=NOW)
        self.assertEqual(result.outcome, "ACT")
        self.assertEqual(result.authority_source, "direct_instruction")

    def test_standing_delegation_acts(self):
        policy = load("standing-social-posts.json")
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:user_selected",
            "destination": "facebook:private-family-group",
        }, now=NOW)
        self.assertEqual(result.outcome, "ACT")

    def test_destination_change_asks(self):
        policy = load("standing-social-posts.json")
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:user_selected",
            "destination": "facebook:public-timeline",
        }, now=NOW)
        self.assertEqual(result.outcome, "ASK")

    def test_explicit_exclusion_asks(self):
        policy = load("standing-social-posts.json")
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:user_selected",
            "destination": "facebook:private-family-group",
            "features": ["location_tagging"],
        }, now=NOW)
        self.assertEqual(result.outcome, "ASK")

    def test_no_authority_denies(self):
        result = decide(None, {"action": "publish_post"}, now=NOW)
        self.assertEqual(result.outcome, "DENY")

    def test_revoked_delegation_denies(self):
        policy = load("standing-social-posts.json")
        policy["status"] = "revoked"
        policy["validity"]["revoked_at"] = "2026-07-15T21:20:00Z"
        policy["validity"]["revocation_reason"] = "User revoked social posting"
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:user_selected",
            "destination": "facebook:private-family-group",
        }, now=NOW)
        self.assertEqual(result.outcome, "DENY")

    def test_expired_delegation_denies(self):
        policy = load("standing-social-posts.json")
        policy["validity"]["expires_at"] = "2026-07-15T21:00:00Z"
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:user_selected",
            "destination": "facebook:private-family-group",
        }, now=NOW)
        self.assertEqual(result.outcome, "DENY")

    def test_silent_authority_expansion_is_rejected(self):
        policy = load("standing-social-posts.json")
        policy["scope"]["actions"] = []
        with self.assertRaises(DelegationError):
            validate_delegation(policy)

    def test_material_context_change_asks(self):
        policy = load("direct-facebook-post.json")
        result = decide(policy, {
            "action": "publish_post",
            "resource": "photo:current_capture",
            "destination": "facebook:owner-account",
            "material_context_change": True,
        }, now=NOW)
        self.assertEqual(result.outcome, "ASK")


if __name__ == "__main__":
    unittest.main()

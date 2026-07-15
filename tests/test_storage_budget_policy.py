from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validate_storage_budget_policy import PolicyError, validate_policy


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "storage-budget" / "semantic-recall.json"


class StorageBudgetPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def assertInvalid(self, policy: dict) -> None:  # noqa: N802
        with self.assertRaises(PolicyError):
            validate_policy(policy)

    def test_reference_fixture_is_valid(self) -> None:
        validate_policy(self.policy)

    def test_required_property_cannot_lose_coverage(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["capture_plan"]["streams"][1]["enabled"] = False
        self.assertInvalid(policy)

    def test_durable_allocations_cannot_exceed_episode_budget(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["capacity_budget"]["local_bytes"] = policy["capacity_budget"]["max_bytes_per_episode"]
        self.assertInvalid(policy)

    def test_ephemeral_compute_cannot_be_counted_as_durable_storage(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["capacity_budget"]["ephemeral_compute_excluded"] = False
        self.assertInvalid(policy)

    def test_substitution_cannot_silently_drop_required_property(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["sensor_substitutions"] = [{
            "substitution_id": "bad-substitution",
            "replaced_stream_refs": ["transcript"],
            "substitute_stream_refs": ["continuity"],
            "preserved_properties": ["precise_event_ordering"],
            "lost_properties": ["spoken_semantic_content"],
            "expected_uncertainty": 0.7,
            "validation_basis": "negative test",
            "restore_triggers": ["speech_active"]
        }]
        self.assertInvalid(policy)

    def test_budget_exhaustion_requires_capability_loss_declaration(self) -> None:
        policy = copy.deepcopy(self.policy)
        del policy["capability_loss_policy"]
        self.assertInvalid(policy)

    def test_receipts_must_cover_initial_plan_and_exhaustion(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["receipt_policy"]["events"].remove("budget_exhaustion")
        self.assertInvalid(policy)


if __name__ == "__main__":
    unittest.main()

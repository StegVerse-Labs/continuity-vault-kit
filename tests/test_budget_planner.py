from __future__ import annotations

import json
import unittest
from pathlib import Path

from multimodal_storage.budget_planner import build_budget_plan


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "storage-budget" / "semantic-recall.json"


class BudgetPlannerTests(unittest.TestCase):
    def test_builds_deterministic_non_controlling_plan(self) -> None:
        policy = json.loads(FIXTURE.read_text(encoding="utf-8"))
        plan = build_budget_plan(policy)
        self.assertEqual(plan.policy_id, "policy-semantic-recall-default")
        self.assertEqual(plan.reconstruction_goal, "semantic_recall")
        self.assertEqual(plan.enabled_streams, ("continuity", "transcript", "voice-buffer"))
        self.assertEqual(plan.required_properties, ("precise_event_ordering", "spoken_semantic_content"))
        self.assertTrue(plan.within_hourly_budget)
        self.assertTrue(plan.advisory_only)


if __name__ == "__main__":
    unittest.main()

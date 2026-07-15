import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from delegation.decision import decide


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 15, 21, 30, tzinfo=timezone.utc)


def apply_override(policy, override):
    for dotted_key, value in override.items():
        target = policy
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value


class CanonicalDelegationCaseTests(unittest.TestCase):
    def test_canonical_cases(self):
        packet = json.loads(
            (ROOT / "fixtures" / "delegation-decisions" / "act-ask-deny.json").read_text(encoding="utf-8")
        )
        for case in packet["cases"]:
            with self.subTest(case_id=case["case_id"]):
                policy = None
                if case["policy_ref"]:
                    policy = json.loads((ROOT / case["policy_ref"]).read_text(encoding="utf-8"))
                    policy = deepcopy(policy)
                    apply_override(policy, case.get("policy_override", {}))
                result = decide(policy, case["request"], now=NOW)
                self.assertEqual(result.outcome, case["expected"])
                self.assertTrue(result.receipt_required)


if __name__ == "__main__":
    unittest.main()

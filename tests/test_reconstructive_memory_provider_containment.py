from __future__ import annotations

import unittest

from reconstructive_memory.provider_containment import ActionStatus, ContainmentReceipt, build_default_plan


class ProviderContainmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resources = {
            "stegid-signature": "arn:kms:sign",
            "key-custody": "arn:kms:custody",
            "replicated-state": "table:state",
            "ai-entity-attestation": "spiffe://example/agent",
            "ecosystem-chat": "https://chat.example/probe",
            "master-records": "https://records.example/probe",
        }
        self.plan = build_default_plan("incident-1", self.resources, "reason-1")

    def receipt(self, command, status=ActionStatus.APPLIED):
        return ContainmentReceipt(command.commitment, status, "operator-1", f"evidence-{command.role}", "2026-07-15T21:00:00Z")

    def test_all_actions_applied_is_contained(self) -> None:
        self.assertEqual(self.plan.evaluate(self.receipt(c) for c in self.plan.commands), "CONTAINED")

    def test_missing_failed_duplicate_and_unknown_fail_closed(self) -> None:
        self.assertEqual(self.plan.evaluate(self.receipt(c) for c in self.plan.commands[:-1]), "FAIL_CLOSED")
        receipts = [self.receipt(c) for c in self.plan.commands]
        receipts[0] = self.receipt(self.plan.commands[0], ActionStatus.FAILED)
        self.assertEqual(self.plan.evaluate(receipts), "FAIL_CLOSED")
        receipts = [self.receipt(c) for c in self.plan.commands]
        self.assertEqual(self.plan.evaluate(receipts + [receipts[0]]), "FAIL_CLOSED")
        receipts.append(ContainmentReceipt("unknown", ActionStatus.APPLIED, "operator", "evidence", "2026-07-15T21:00:00Z"))
        self.assertEqual(self.plan.evaluate(receipts), "FAIL_CLOSED")

    def test_missing_role_resource_rejected(self) -> None:
        resources = dict(self.resources)
        del resources["key-custody"]
        with self.assertRaises(ValueError):
            build_default_plan("incident", resources, "reason")


if __name__ == "__main__":
    unittest.main()

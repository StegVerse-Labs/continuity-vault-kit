from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from cross_platform_recovery import evaluate  # noqa: E402

FIXTURE = ROOT / "fixtures" / "kv_cross_platform_recovery_cases.json"

def set_path(obj, dotted, value):
    parts = dotted.split(".")
    cur = obj
    for key in parts[:-1]:
        cur = cur[key]
    cur[parts[-1]] = value

class CrossPlatformRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text())
        cls.base = cls.data["cases"][0]["package"]

    def test_all_declared_cases(self):
        for case in self.data["cases"]:
            package = copy.deepcopy(self.base if "package" not in case else case["package"])
            for key, value in case.get("mutate", {}).items():
                set_path(package, key, value)
            receipt = evaluate(case["case_id"], package)
            self.assertEqual(receipt["decision"], case["expected"], case["case_id"])
            self.assertEqual(receipt["authority_effect"], "NONE")
            self.assertFalse(receipt["cloud_account_is_kv_authority"])
            self.assertFalse(receipt["browser_is_execution_surface"])
            self.assertFalse(receipt["old_device_identity_preserved"])
            self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_success_preserves_kv_but_creates_new_device_identity(self):
        receipt = evaluate("success", copy.deepcopy(self.base))
        self.assertTrue(receipt["kv_identity_preserved"])
        self.assertTrue(receipt["new_device_identity_created"])
        self.assertEqual(receipt["decision"], "ALLOW_WITH_SIGNOFF")

    def test_receipt_is_deterministic(self):
        a = evaluate("same", copy.deepcopy(self.base))
        b = evaluate("same", copy.deepcopy(self.base))
        self.assertEqual(a, b)

    def test_cloud_login_never_equals_recovery_authority(self):
        package = copy.deepcopy(self.base)
        package["recovery"]["recovery_authority_verified"] = False
        self.assertEqual(evaluate("cloud-only", package)["decision"], "DENY")

if __name__ == "__main__":
    unittest.main()

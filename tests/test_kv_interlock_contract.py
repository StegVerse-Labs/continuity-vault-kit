from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import validate_kv_interlock_contract as contract  # noqa: E402


class KVInterlockContractTests(unittest.TestCase):
    def test_canonical_contract_validates(self) -> None:
        result = contract.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["protocol"], "KV-INTERLOCK-v1")

    def test_request_contract_is_model_neutral(self) -> None:
        req = contract.load(contract.REQUEST)
        module = req["properties"]["requester"]["properties"]["module"]
        self.assertEqual(module["type"], "string")
        self.assertNotIn("const", module)

    def test_decision_vocabulary_is_fail_closed(self) -> None:
        res = contract.load(contract.RESPONSE)
        decisions = res["properties"]["decision"]["enum"]
        self.assertEqual(decisions[-1], "FAIL_CLOSED")
        self.assertIn("DENY", decisions)
        self.assertNotIn("ALLOW", decisions)

    def test_receipt_hash_is_required_sha256_hex(self) -> None:
        res = contract.load(contract.RESPONSE)
        receipt = res["properties"]["receipt"]
        self.assertIn("response_hash", receipt["required"])
        self.assertEqual(receipt["properties"]["response_hash"]["pattern"], "^[a-f0-9]{64}$")

    def test_direct_commit_operation_is_not_exposed(self) -> None:
        req = contract.load(contract.REQUEST)
        operations = req["properties"]["operation"]["enum"]
        self.assertNotIn("COMMIT", operations)
        self.assertIn("COMMIT_CANDIDATE", operations)


if __name__ == "__main__":
    unittest.main()

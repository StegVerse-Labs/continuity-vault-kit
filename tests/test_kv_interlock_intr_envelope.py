from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import validate_kv_interlock_intr_envelope as intr  # noqa: E402


class KVInterlockInTrEnvelopeTests(unittest.TestCase):
    def test_contract_validates(self) -> None:
        result = intr.validate_contract()
        self.assertTrue(result["valid"])
        self.assertFalse(result["credential_specific"])
        self.assertEqual(result["authority_effect"], "NONE")

    def test_generic_contract_has_no_credential_grant(self) -> None:
        schema = intr.load(intr.SCHEMA)
        self.assertNotIn("credential_grant", schema["properties"])

    def test_request_path_is_device_to_kv(self) -> None:
        spec = intr.load(intr.SPEC)
        self.assertEqual(spec["direction"], "REQUEST")
        self.assertEqual(spec["source_role"], "DEVICE")
        self.assertEqual(spec["next_role"], "KV")
        self.assertEqual(spec["payload_schema_version"], "kv.interlock.request.v1")

    def test_transport_cannot_grant_authority(self) -> None:
        spec = intr.load(intr.SPEC)
        authority = spec["authority"]
        self.assertFalse(authority["authority_transfer"])
        self.assertFalse(authority["transport_grants_execution_authority"])
        self.assertFalse(authority["model_output_grants_execution_authority"])
        self.assertEqual(authority["credential_authority_effect"], "NONE")

    def test_receipt_policy_is_plaintext_free_and_fail_closed(self) -> None:
        spec = intr.load(intr.SPEC)
        policy = spec["receipt_policy"]
        self.assertTrue(policy["receipt_required"])
        self.assertTrue(policy["receipt_chain_required"])
        self.assertFalse(policy["receipt_contains_payload_plaintext"])
        self.assertEqual(policy["ambiguous_disposition"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()

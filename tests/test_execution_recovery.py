import unittest

from execution.adapter import canonical_sha256
from execution.extensions import assert_extension_execution_matches, host_extension_request
from execution.recovery import advance_attempt, recovery_decision, start_attempt, verify_journal


def envelope():
    return {
        "schema_version": "0.1",
        "envelope_id": "env:sms:1",
        "instruction_ref": "instruction:1",
        "authority_decision": {
            "outcome": "ACT",
            "decision_sha256": "a" * 64,
            "delegation_id": "delegation:1",
            "authority_source": "direct_instruction",
        },
        "action": "send",
        "resource": "communication",
        "destination": "sms:+15551234567",
        "payload": {"content_sha256": "b" * 64, "media_refs": [], "text": "hello"},
        "connector": {"connector_id": "StegTalk", "operation": "SEND_MESSAGE", "credential_ref": "TV/TVC"},
        "idempotency": {"key": "sms:1", "duplicate_policy": "verify_before_retry"},
        "receipt_required": True,
        "state": "PREPARED",
    }


class RecoveryTests(unittest.TestCase):
    def test_indeterminate_dispatch_requires_external_verification(self):
        started = start_attempt(envelope(), attempt_id="attempt:1", lease_owner="worker:1")
        dispatched = advance_attempt(started, state="DISPATCHED", receipt_refs=["receipt:dispatch"])
        terminal = advance_attempt(dispatched, state="TERMINAL", result="INDETERMINATE", receipt_refs=["receipt:timeout"])
        verify_journal([started, dispatched, terminal])
        decision = recovery_decision([started, dispatched, terminal])
        self.assertEqual(decision["decision"], "VERIFY_EXTERNALLY")
        self.assertFalse(decision["new_authority_granted"])

    def test_confirmed_failed_attempt_may_retry_exact_only(self):
        started = start_attempt(envelope(), attempt_id="attempt:2")
        dispatched = advance_attempt(started, state="DISPATCHED")
        terminal = advance_attempt(dispatched, state="TERMINAL", result="FAILED", side_effect_absence_confirmed=True)
        decision = recovery_decision([started, dispatched, terminal])
        self.assertEqual(decision["decision"], "RETRY_EXACT")
        self.assertTrue(decision["exact_envelope_required"])

    def test_kv_hosts_stegtalk_without_device_authority(self):
        request = {
            "schema_version": "0.1",
            "extension_id": "stegtalk:sms",
            "extension_type": "StegTalk",
            "vault_subject_ref": "vault:self",
            "operation": "SEND_MESSAGE",
            "destination": "sms:+15551234567",
            "payload_ref": "vault:payload:1",
            "payload_sha256": canonical_sha256("hello"),
            "authority_ref": "vault:authority:1",
            "idempotency_key": "sms:1",
            "device_role": "EPHEMERAL_TRANSPORT_EDGE",
            "device_authority": False,
            "device_continuity_authority": False,
            "vault_continuity_authority": True,
            "receipt_required": True,
            "credential_material": None,
        }
        hosted = host_extension_request(request)
        execution = dict(hosted)
        assert_extension_execution_matches(hosted, execution)
        self.assertEqual(hosted["continuity_authority"], "KnowledgeVault")
        self.assertFalse(hosted["device_authority"])
        self.assertFalse(hosted["device_continuity_authority"])


if __name__ == "__main__":
    unittest.main()

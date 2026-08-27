import tempfile
import unittest
from pathlib import Path

from execution.communication_runtime import (
    CommunicationRuntimeJournal,
    CommunicationRuntimeJournalError,
    stegtalk_communication_sha256,
    stegtalk_selection_sha256,
)
from execution.vault_store import KnowledgeVaultExecutionStore


def selection():
    value = {
        "schema_version": "0.1",
        "receipt_type": "CROSS_EDGE_SELECTION",
        "attempt_id": "attempt:runtime:1",
        "policy_version": "stegtalk.cross-edge.v0.1",
        "posture": "AUTO",
        "recipient_state": "KNOWN",
        "candidate_set_sha256": "1" * 64,
        "selected_edge_id": "edge:gateway",
        "selected_bearer": "stegtalk-ip",
        "primary_score": 10.0,
        "primary_score_components": {},
        "fallback_order": [{"edge_id": "edge:phone", "bearer": "sms", "score": 5.0}],
        "excluded_paths": [],
        "selected_advertisement_sha256": "2" * 64,
        "decided_at": "2026-08-22T22:35:00Z",
        "multipath_authorized": False,
        "remote_edge_execution_authorized": True,
    }
    value["selection_sha256"] = stegtalk_selection_sha256(value)
    return value


def lease():
    return {
        "attempt_id": "attempt:runtime:1",
        "edge_id": "edge:gateway",
        "lease_epoch": 1,
        "expires_at": "2026-08-22T22:45:00Z",
    }


def execution_receipt(*, key="idem:runtime:1", outcome="DELIVERED", side_effect_absence_confirmed=False):
    value = {
        "receipt_type": "EDGE_EXECUTION",
        "attempt_id": "attempt:runtime:1",
        "selection_sha256": selection()["selection_sha256"],
        "edge_id": "edge:gateway",
        "bearer": "stegtalk-ip",
        "idempotency_key": key,
        "lease_epoch": 1,
        "dispatch_state": "OBSERVED" if outcome == "DELIVERED" else "DISPATCHED",
        "outcome": outcome,
        "side_effect_absence_confirmed": side_effect_absence_confirmed,
        "observed_at": "2026-08-22T22:36:00Z",
    }
    value["receipt_sha256"] = stegtalk_communication_sha256(value)
    return value


def receive_evidence(*, key="idem:runtime:receive:1", request_sha256="sha256:" + "e" * 64, accepted=True):
    return {
        "attempt_id": "attempt:runtime:1",
        "selection_sha256": selection()["selection_sha256"],
        "edge_id": "edge:gateway",
        "bearer": "stegtalk-ip",
        "idempotency_key": key,
        "request_sha256": request_sha256,
        "ack_protocol": "stegtalk.edge-tls-ack.v0.1",
        "accepted": accepted,
        "received_at": "2026-08-22T22:36:30Z",
        "authority_created": False,
    }


class CommunicationRuntimeJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "KnowledgeVault"

    def tearDown(self):
        self.tmp.cleanup()

    def journal(self):
        return CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(self.root))

    def test_distinct_hash_profiles_preserve_same_canonical_utf8(self):
        selection_hash = stegtalk_selection_sha256({"text": "mañana"})
        execution_hash = stegtalk_communication_sha256({"text": "mañana"})
        self.assertEqual(len(selection_hash), 64)
        self.assertFalse(selection_hash.startswith("sha256:"))
        self.assertEqual(execution_hash, "sha256:" + selection_hash)

    def test_begin_persists_selection_and_lease_and_reconstructs(self):
        j = self.journal()
        stream_id = j.begin(selection=selection(), lease=lease())
        recovered = j.recover("attempt:runtime:1")
        self.assertEqual(stream_id, j.stream_id("attempt:runtime:1"))
        self.assertEqual(recovered.selection, selection())
        self.assertEqual(recovered.lease, lease())
        self.assertIsNone(recovered.execution_receipt)

    def test_execution_receipt_reconstructs_after_new_store_instance(self):
        first = self.journal()
        first.record_execution(selection=selection(), lease=lease(), receipt=execution_receipt())
        restarted = CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(self.root))
        recovered = restarted.recover("attempt:runtime:1")
        self.assertEqual(recovered.execution_receipt, execution_receipt())
        self.assertEqual(recovered.execution_receipt["outcome"], "DELIVERED")

    def test_same_execution_receipt_is_idempotent_in_durable_store(self):
        j = self.journal()
        receipt = execution_receipt()
        stream_id = j.record_execution(selection=selection(), lease=lease(), receipt=receipt)
        j.record_execution(selection=selection(), lease=lease(), receipt=receipt)
        attempts = j.store.read_stream("Attempts", stream_id)
        receipts = j.store.read_stream("Receipts", stream_id)
        observed = [row for row in attempts if row.get("record_type") == "EDGE_EXECUTION_OBSERVED"]
        self.assertEqual(len(observed), 1)
        self.assertEqual(len(receipts), 2)

    def test_idempotency_key_cannot_rebind_to_different_receipt(self):
        j = self.journal()
        j.record_execution(selection=selection(), lease=lease(), receipt=execution_receipt())
        different = execution_receipt(key="idem:runtime:1", outcome="FAILED", side_effect_absence_confirmed=True)
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "idempotency key already bound"):
            j.record_execution(selection=selection(), lease=lease(), receipt=different)

    def test_prefixed_selection_hash_is_rejected(self):
        bad = selection()
        bad["selection_sha256"] = "sha256:" + bad["selection_sha256"]
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "selection receipt hash mismatch"):
            self.journal().begin(selection=bad, lease=lease())

    def test_wrong_execution_edge_is_rejected(self):
        receipt = execution_receipt()
        receipt["edge_id"] = "edge:other"
        body = dict(receipt)
        body.pop("receipt_sha256")
        receipt["receipt_sha256"] = stegtalk_communication_sha256(body)
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "execution edge does not match"):
            self.journal().record_execution(selection=selection(), lease=lease(), receipt=receipt)

    def test_ambiguous_execution_cannot_claim_no_side_effect(self):
        receipt = execution_receipt(outcome="TIMEOUT_AFTER_DISPATCH", side_effect_absence_confirmed=True)
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "ambiguous dispatch"):
            self.journal().record_execution(selection=selection(), lease=lease(), receipt=receipt)


    def test_receive_evidence_reconstructs_after_new_store_instance(self):
        first = self.journal()
        first.record_receive(selection=selection(), lease=lease(), evidence=receive_evidence())
        restarted = CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(self.root))
        recovered = restarted.recover("attempt:runtime:1")
        self.assertEqual(len(recovered.receive_records), 1)
        self.assertEqual(recovered.receive_records[0]["request_sha256"], receive_evidence()["request_sha256"])
        self.assertTrue(recovered.receive_records[0]["accepted"])
        self.assertFalse(recovered.receive_records[0]["final_delivery_claimed"])
        self.assertFalse(recovered.receive_records[0]["authority_created"])

    def test_same_receive_evidence_is_durably_idempotent(self):
        j = self.journal()
        stream_id = j.record_receive(selection=selection(), lease=lease(), evidence=receive_evidence())
        j.record_receive(selection=selection(), lease=lease(), evidence=receive_evidence())
        attempts = j.store.read_stream("Attempts", stream_id)
        received = [row for row in attempts if row.get("record_type") == "EDGE_RECEIVE_ACCEPTED"]
        self.assertEqual(len(received), 1)

    def test_receive_idempotency_key_cannot_rebind_to_different_request(self):
        j = self.journal()
        j.record_receive(selection=selection(), lease=lease(), evidence=receive_evidence())
        conflict = receive_evidence(request_sha256="sha256:" + "f" * 64)
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "receive idempotency key already bound"):
            j.record_receive(selection=selection(), lease=lease(), evidence=conflict)

    def test_negative_receiver_ack_is_not_persisted_as_acceptance(self):
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "positively accepted"):
            self.journal().record_receive(
                selection=selection(),
                lease=lease(),
                evidence=receive_evidence(accepted=False),
            )

    def test_receive_evidence_cannot_create_authority(self):
        evidence = receive_evidence()
        evidence["authority_created"] = True
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "cannot create authority"):
            self.journal().record_receive(selection=selection(), lease=lease(), evidence=evidence)

    def test_recovery_record_cannot_grant_authority(self):
        j = self.journal()
        j.begin(selection=selection(), lease=lease())
        with self.assertRaisesRegex(CommunicationRuntimeJournalError, "recovery cannot grant new authority"):
            j.record_recovery(
                attempt_id="attempt:runtime:1",
                decision={"action": "TRY_FALLBACK", "reason": "TEST", "new_authority_granted": True},
            )

    def test_recovery_record_round_trips_without_new_authority(self):
        j = self.journal()
        j.begin(selection=selection(), lease=lease())
        j.record_recovery(
            attempt_id="attempt:runtime:1",
            decision={
                "action": "VERIFY_EXTERNALLY",
                "reason": "AMBIGUOUS_AFTER_DISPATCH",
                "new_authority_granted": False,
            },
        )
        recovered = j.recover("attempt:runtime:1")
        self.assertEqual(recovered.recovery_records[0]["action"], "VERIFY_EXTERNALLY")
        self.assertFalse(recovered.recovery_records[0]["new_authority_granted"])


if __name__ == "__main__":
    unittest.main()

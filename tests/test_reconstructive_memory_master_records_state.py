from __future__ import annotations

import unittest

from reconstructive_memory.master_records import MasterRecordAcknowledgement, MasterRecordEnvelope
from reconstructive_memory.master_records_state import DurableMasterRecordsOutbox, InMemoryMasterRecordsStateStore


class Verifier:
    def verify_acknowledgement(self, acknowledgement):
        return acknowledgement.destination_receipt_ref == "mr:receipt:1"


def envelope(export_id: str, source: str, prior: str | None = None) -> MasterRecordEnvelope:
    return MasterRecordEnvelope(
        export_id=export_id,
        source_type="access-receipt",
        source_commitment=source,
        pair_id="pair:1",
        policy_ref="policy:1",
        relationship_epoch=1,
        destination="master-records",
        created_at=10,
        prior_export_hash=prior,
        payload_commitment="sha256:payload",
    ).with_hash()


class DurableMasterRecordsTests(unittest.TestCase):
    def test_enqueue_and_acknowledge(self):
        store = InMemoryMasterRecordsStateStore(); outbox = DurableMasterRecordsOutbox(store)
        item = envelope("exp:1", "src:1")
        outbox.enqueue(item)
        ack = MasterRecordAcknowledgement("exp:1", item.export_hash, "mr:receipt:1", "sha256:receipt", 20).with_hash()
        entry = outbox.acknowledge(ack, Verifier())
        self.assertEqual(entry.state, "acknowledged")
        self.assertEqual(store.read().version, 2)

    def test_retry_retention_and_due_selection(self):
        store = InMemoryMasterRecordsStateStore(); outbox = DurableMasterRecordsOutbox(store)
        item = envelope("exp:1", "src:1"); outbox.enqueue(item)
        entry = outbox.record_attempt("exp:1", now=20, retry_after=30)
        self.assertEqual(entry.attempts, 1)
        self.assertEqual(outbox.due(29), ())
        self.assertEqual(outbox.due(30)[0].envelope.export_id, "exp:1")

    def test_replay_denied_across_instances(self):
        store = InMemoryMasterRecordsStateStore(); first = DurableMasterRecordsOutbox(store); second = DurableMasterRecordsOutbox(store)
        item = envelope("exp:1", "src:1"); first.enqueue(item)
        with self.assertRaises(PermissionError): second.enqueue(item)

    def test_deprecate_pending_export(self):
        store = InMemoryMasterRecordsStateStore(); outbox = DurableMasterRecordsOutbox(store)
        outbox.enqueue(envelope("exp:1", "src:1"))
        entry = outbox.deprecate("exp:1", reason="destination retired")
        self.assertEqual(entry.state, "deprecated")
        self.assertEqual(outbox.due(999), ())

    def test_supersede_pending_export(self):
        store = InMemoryMasterRecordsStateStore(); outbox = DurableMasterRecordsOutbox(store)
        first = envelope("exp:1", "src:1"); outbox.enqueue(first)
        second = envelope("exp:2", "src:2", first.export_hash); outbox.enqueue(second)
        entry = outbox.supersede("exp:1", successor_export_id="exp:2", reason="corrected receipt")
        self.assertEqual(entry.state, "superseded")
        self.assertEqual(entry.superseded_by, "exp:2")

    def test_state_does_not_store_plaintext_descriptor(self):
        store = InMemoryMasterRecordsStateStore(); outbox = DurableMasterRecordsOutbox(store)
        outbox.enqueue(envelope("exp:1", "src:1"))
        self.assertNotIn("private query", str(store.read().payload()))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from reconstructive_memory.deployment import (
    BlobMasterRecordsStateStore,
    MasterRecordsStateCodec,
    deliver_due_exports,
)
from reconstructive_memory.master_records import (
    MasterRecordAcknowledgement,
    MasterRecordEnvelope,
)
from reconstructive_memory.master_records_state import DurableMasterRecordsOutbox


class MemoryBlobStore:
    def __init__(self) -> None:
        self.blob: bytes | None = None

    def read_blob(self) -> bytes | None:
        return self.blob

    def compare_and_swap_blob(self, expected: bytes | None, updated: bytes) -> bool:
        if self.blob != expected:
            return False
        self.blob = updated
        return True


class Verifier:
    def verify_acknowledgement(self, acknowledgement: MasterRecordAcknowledgement) -> bool:
        return acknowledgement.destination_receipt_ref.startswith("mr:")


class Client:
    def __init__(self, acknowledge: bool) -> None:
        self.acknowledge = acknowledge

    def deliver(self, envelope: MasterRecordEnvelope) -> MasterRecordAcknowledgement | None:
        if not self.acknowledge:
            return None
        return MasterRecordAcknowledgement(
            export_id=envelope.export_id,
            export_hash=envelope.export_hash,
            destination_receipt_ref="mr:receipt-1",
            destination_receipt_hash="sha256:destination",
            accepted_at=10,
        ).with_hash()


def envelope() -> MasterRecordEnvelope:
    return MasterRecordEnvelope(
        export_id="export-1",
        source_type="access-receipt",
        source_commitment="sha256:source",
        pair_id="sha256:pair",
        policy_ref="policy:v1",
        relationship_epoch=1,
        destination="master-records",
        created_at=1,
        payload_commitment="sha256:payload",
    ).with_hash()


class DeploymentTests(unittest.TestCase):
    def test_state_round_trip_preserves_integrity(self) -> None:
        backend = MemoryBlobStore()
        store = BlobMasterRecordsStateStore(backend)
        outbox = DurableMasterRecordsOutbox(store)
        outbox.enqueue(envelope())
        state = store.read()
        encoded = MasterRecordsStateCodec.encode(state)
        decoded = MasterRecordsStateCodec.decode(encoded)
        self.assertEqual(decoded.state_hash, state.state_hash)
        self.assertIn("export-1", decoded.entries)

    def test_tampered_blob_is_rejected(self) -> None:
        backend = MemoryBlobStore()
        store = BlobMasterRecordsStateStore(backend)
        DurableMasterRecordsOutbox(store).enqueue(envelope())
        assert backend.blob is not None
        backend.blob = backend.blob.replace(b'"attempts":0', b'"attempts":7')
        with self.assertRaises(ValueError):
            store.read()

    def test_unresolved_delivery_schedules_retry(self) -> None:
        store = BlobMasterRecordsStateStore(MemoryBlobStore())
        outbox = DurableMasterRecordsOutbox(store)
        outbox.enqueue(envelope())
        completed = deliver_due_exports(outbox, Client(False), Verifier(), now=5, retry_after=20)
        self.assertEqual(completed, ())
        entry = store.read().entries["export-1"]
        self.assertEqual(entry.attempts, 1)
        self.assertEqual(entry.next_attempt_at, 20)

    def test_verified_delivery_finalizes_acknowledgement(self) -> None:
        store = BlobMasterRecordsStateStore(MemoryBlobStore())
        outbox = DurableMasterRecordsOutbox(store)
        outbox.enqueue(envelope())
        completed = deliver_due_exports(outbox, Client(True), Verifier(), now=5, retry_after=20)
        self.assertEqual(completed, ("export-1",))
        self.assertEqual(store.read().entries["export-1"].state, "acknowledged")


if __name__ == "__main__":
    unittest.main()

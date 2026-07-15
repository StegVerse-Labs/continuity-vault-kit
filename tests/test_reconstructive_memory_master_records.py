from __future__ import annotations

import unittest

from reconstructive_memory.master_records import (
    MasterRecordAcknowledgement,
    MasterRecordsOutbox,
)


class _Verifier:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted

    def verify_acknowledgement(self, acknowledgement: MasterRecordAcknowledgement) -> bool:
        return self.accepted


class MasterRecordsPropagationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.outbox = MasterRecordsOutbox()
        self.common = {
            "export_id": "export-1",
            "source_type": "access-receipt",
            "source_commitment": "sha256:" + "a" * 64,
            "pair_id": "sha256:" + "b" * 64,
            "policy_ref": "policy://memory/v1",
            "relationship_epoch": 2,
            "created_at": 500,
            "payload_descriptor": {
                "event_count": 3,
                "result_class": "ephemeral_reconstruction",
                "plaintext_retained": False,
            },
        }

    def test_enqueue_and_acknowledge_receipt(self) -> None:
        envelope = self.outbox.enqueue(**self.common)
        envelope.verify()
        acknowledgement = MasterRecordAcknowledgement(
            export_id=envelope.export_id,
            export_hash=envelope.export_hash,
            destination_receipt_ref="master-records://receipts/1",
            destination_receipt_hash="sha256:" + "c" * 64,
            accepted_at=501,
        ).with_hash()
        stored = self.outbox.acknowledge(acknowledgement, _Verifier())
        self.assertEqual(stored, acknowledgement)
        self.assertEqual(self.outbox.acknowledged("export-1"), acknowledgement)
        with self.assertRaises(KeyError):
            self.outbox.pending("export-1")

    def test_export_identifier_replay_is_denied(self) -> None:
        self.outbox.enqueue(**self.common)
        changed = dict(self.common)
        changed["source_commitment"] = "sha256:" + "d" * 64
        with self.assertRaises(PermissionError):
            self.outbox.enqueue(**changed)

    def test_source_receipt_cannot_be_exported_twice(self) -> None:
        self.outbox.enqueue(**self.common)
        changed = dict(self.common)
        changed["export_id"] = "export-2"
        with self.assertRaises(PermissionError):
            self.outbox.enqueue(**changed)

    def test_acknowledgement_must_match_export(self) -> None:
        envelope = self.outbox.enqueue(**self.common)
        acknowledgement = MasterRecordAcknowledgement(
            export_id=envelope.export_id,
            export_hash="sha256:" + "e" * 64,
            destination_receipt_ref="master-records://receipts/1",
            destination_receipt_hash="sha256:" + "f" * 64,
            accepted_at=501,
        ).with_hash()
        with self.assertRaises(PermissionError):
            self.outbox.acknowledge(acknowledgement, _Verifier())

    def test_unverified_acknowledgement_fails_closed(self) -> None:
        envelope = self.outbox.enqueue(**self.common)
        acknowledgement = MasterRecordAcknowledgement(
            export_id=envelope.export_id,
            export_hash=envelope.export_hash,
            destination_receipt_ref="master-records://receipts/1",
            destination_receipt_hash="sha256:" + "f" * 64,
            accepted_at=501,
        ).with_hash()
        with self.assertRaises(PermissionError):
            self.outbox.acknowledge(acknowledgement, _Verifier(False))

    def test_export_payload_retains_no_plaintext(self) -> None:
        descriptor = dict(self.common["payload_descriptor"])
        descriptor["private_query"] = "where was I treated?"
        common = dict(self.common)
        common["payload_descriptor"] = descriptor
        envelope = self.outbox.enqueue(**common)
        serialized = repr(envelope.payload())
        self.assertNotIn("where was I treated?", serialized)
        self.assertIn("payload_commitment", serialized)


if __name__ == "__main__":
    unittest.main()

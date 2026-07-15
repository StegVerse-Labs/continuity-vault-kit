from __future__ import annotations

import unittest

from reconstructive_memory.ingestion import ChatObservation
from reconstructive_memory.replay import DurableTransportReplayRegistry, InMemoryReplayStateStore
from reconstructive_memory.transport import ChatTransportEnvelope


class DurableReplayTests(unittest.TestCase):
    def envelope(self, *, envelope_id="env-1", nonce="nonce-1", sequence=1):
        return ChatTransportEnvelope(
            envelope_id=envelope_id,
            source_session_id="chat-session-1",
            sequence=sequence,
            issued_at=100,
            expires_at=200,
            nonce=nonce,
            pair_id="sha256:pair",
            policy_ref="policy://memory/v1",
            relationship_epoch=1,
            observation=ChatObservation(
                observation_id=f"obs-{sequence}",
                event_type="accepted_context",
                plaintext="private content",
                approved=True,
                retention_class="reconstructable",
            ),
            user_approval_proof="approval-proof",
            transport_proof="transport-proof",
        )

    def test_state_advances_atomically(self):
        store = InMemoryReplayStateStore()
        state = DurableTransportReplayRegistry(store).validate_and_record(self.envelope())
        self.assertEqual(state.version, 1)
        self.assertEqual(dict(state.last_sequences)["chat-session-1"], 1)
        self.assertNotIn("env-1", repr(state.payload()))
        self.assertNotIn("nonce-1", repr(state.payload()))

    def test_envelope_replay_is_rejected_across_registry_instances(self):
        store = InMemoryReplayStateStore()
        DurableTransportReplayRegistry(store).validate_and_record(self.envelope())
        with self.assertRaisesRegex(PermissionError, "envelope replay"):
            DurableTransportReplayRegistry(store).validate_and_record(self.envelope())

    def test_nonce_replay_is_rejected(self):
        store = InMemoryReplayStateStore()
        registry = DurableTransportReplayRegistry(store)
        registry.validate_and_record(self.envelope())
        with self.assertRaisesRegex(PermissionError, "nonce replay"):
            registry.validate_and_record(self.envelope(envelope_id="env-2", sequence=2))

    def test_sequence_regression_is_rejected(self):
        store = InMemoryReplayStateStore()
        registry = DurableTransportReplayRegistry(store)
        registry.validate_and_record(self.envelope(sequence=2))
        with self.assertRaisesRegex(PermissionError, "not monotonic"):
            registry.validate_and_record(self.envelope(envelope_id="env-2", nonce="nonce-2", sequence=1))


if __name__ == "__main__":
    unittest.main()

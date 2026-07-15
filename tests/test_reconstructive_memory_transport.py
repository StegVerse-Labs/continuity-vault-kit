from __future__ import annotations

import unittest

from reconstructive_memory.core import ProtectedObject, _digest
from reconstructive_memory.ingestion import ChatObservation, EcosystemChatIngestor
from reconstructive_memory.transport import (
    AuthenticatedChatTransportAdapter,
    ChatTransportEnvelope,
    TransportReplayRegistry,
)


class FakeProtector:
    def protect(self, *, content_ref, plaintext, pair_id, policy_ref):
        return ProtectedObject(
            content_ref=content_ref,
            pair_id=pair_id,
            policy_ref=policy_ref,
            ciphertext=("cipher:" + plaintext).encode(),
            plaintext_commitment=_digest(plaintext),
        )


class FakeVerifier:
    def __init__(self, *, user=True, transport=True):
        self.user = user
        self.transport = transport

    def verify_user_approval(self, envelope):
        return self.user

    def verify_transport(self, envelope):
        return self.transport


class AuthenticatedTransportTests(unittest.TestCase):
    def setUp(self):
        self.pair_id = "sha256:" + "a" * 64
        self.policy_ref = "policy://memory/v1"
        self.ingestor = EcosystemChatIngestor(
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
            authority_ref="authority://pair/1",
            minimizer=lambda observation: observation.plaintext.strip()[:24],
            protector=FakeProtector(),
        )
        self.registry = TransportReplayRegistry()

    def envelope(self, **changes):
        observation = ChatObservation(
            observation_id="evt-transport-1",
            event_type="accepted_context",
            plaintext="private approved durable context",
            approved=True,
            retention_class="reconstructable",
        )
        values = {
            "envelope_id": "env-1",
            "source_session_id": "chat-session-1",
            "sequence": 1,
            "issued_at": 100,
            "expires_at": 200,
            "nonce": "nonce-1",
            "pair_id": self.pair_id,
            "policy_ref": self.policy_ref,
            "relationship_epoch": 1,
            "observation": observation,
            "user_approval_proof": "approval-proof",
            "transport_proof": "transport-proof",
        }
        values.update(changes)
        return ChatTransportEnvelope(**values)

    def adapter(self, verifier=None):
        return AuthenticatedChatTransportAdapter(
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            verifier=verifier or FakeVerifier(),
            replay_registry=self.registry,
            ingestor=self.ingestor,
        )

    def test_valid_envelope_reaches_minimized_ingestion(self):
        envelope = self.envelope()
        result = self.adapter().accept(envelope, now=150, previous_event_hash=None)
        self.assertEqual(result.event.event_id, "evt-transport-1")
        self.assertNotIn("private approved durable context", str(result.event.payload()))
        self.assertIsNotNone(result.protected_object)
        self.assertNotIn(envelope.observation.plaintext, repr(envelope.signed_payload()))

    def test_envelope_replay_is_rejected(self):
        adapter = self.adapter()
        envelope = self.envelope()
        adapter.accept(envelope, now=150, previous_event_hash=None)
        with self.assertRaisesRegex(PermissionError, "replay"):
            adapter.accept(envelope, now=151, previous_event_hash=None)

    def test_nonce_reuse_is_rejected_across_envelope_ids(self):
        adapter = self.adapter()
        adapter.accept(self.envelope(), now=150, previous_event_hash=None)
        with self.assertRaisesRegex(PermissionError, "nonce replay"):
            adapter.accept(
                self.envelope(envelope_id="env-2", sequence=2),
                now=151,
                previous_event_hash=None,
            )

    def test_nonmonotonic_sequence_is_rejected(self):
        adapter = self.adapter()
        adapter.accept(self.envelope(), now=150, previous_event_hash=None)
        with self.assertRaisesRegex(PermissionError, "monotonic"):
            adapter.accept(
                self.envelope(envelope_id="env-2", nonce="nonce-2", sequence=1),
                now=151,
                previous_event_hash=None,
            )

    def test_expired_envelope_is_rejected(self):
        with self.assertRaisesRegex(PermissionError, "validity"):
            self.adapter().accept(self.envelope(), now=200, previous_event_hash=None)

    def test_pair_policy_and_epoch_are_bound(self):
        with self.assertRaisesRegex(PermissionError, "pair"):
            self.adapter().accept(
                self.envelope(pair_id="sha256:" + "b" * 64),
                now=150,
                previous_event_hash=None,
            )
        with self.assertRaisesRegex(PermissionError, "policy"):
            self.adapter().accept(
                self.envelope(policy_ref="policy://other"),
                now=150,
                previous_event_hash=None,
            )
        with self.assertRaisesRegex(PermissionError, "epoch"):
            self.adapter().accept(
                self.envelope(relationship_epoch=2),
                now=150,
                previous_event_hash=None,
            )

    def test_both_proofs_must_verify(self):
        with self.assertRaisesRegex(PermissionError, "approval"):
            self.adapter(FakeVerifier(user=False)).accept(
                self.envelope(), now=150, previous_event_hash=None
            )
        with self.assertRaisesRegex(PermissionError, "transport"):
            self.adapter(FakeVerifier(transport=False)).accept(
                self.envelope(), now=150, previous_event_hash=None
            )


if __name__ == "__main__":
    unittest.main()

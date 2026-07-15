import unittest

from reconstructive_memory.core import ProtectedObject, _digest
from reconstructive_memory.ingestion import ChatObservation, EcosystemChatIngestor


class FakeProtector:
    def protect(self, *, content_ref, plaintext, pair_id, policy_ref):
        return ProtectedObject(
            content_ref=content_ref,
            pair_id=pair_id,
            policy_ref=policy_ref,
            ciphertext=("cipher:" + plaintext).encode(),
            plaintext_commitment=_digest(plaintext),
        )


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.ingestor = EcosystemChatIngestor(
            pair_id="sha256:pair",
            policy_ref="policy://memory/v1",
            authority_ref="authority://pair/1",
            minimizer=lambda observation: observation.plaintext.strip()[:32],
            protector=FakeProtector(),
        )

    def test_unapproved_observation_is_rejected(self):
        observation = ChatObservation(
            observation_id="evt-1",
            event_type="decision",
            plaintext="private raw chat",
            approved=False,
            retention_class="reconstructable",
        )
        with self.assertRaises(PermissionError):
            self.ingestor.ingest(observation, sequence=1, previous_event_hash=None)

    def test_chain_contains_no_plaintext(self):
        observation = ChatObservation(
            observation_id="evt-1",
            event_type="decision",
            plaintext="approved durable fact and extra words",
            approved=True,
            retention_class="reconstructable",
        )
        result = self.ingestor.ingest(observation, sequence=1, previous_event_hash=None)
        self.assertNotIn("approved", str(result.event.payload()))
        self.assertIsNotNone(result.protected_object)
        self.assertEqual(result.event.content_commitment, result.protected_object.plaintext_commitment)

    def test_integrity_only_stores_no_object(self):
        observation = ChatObservation(
            observation_id="evt-1",
            event_type="disclosure_occurred",
            plaintext="sensitive content",
            approved=True,
            retention_class="integrity-only",
        )
        result = self.ingestor.ingest(observation, sequence=1, previous_event_hash=None)
        self.assertIsNone(result.event.content_ref)
        self.assertIsNone(result.event.content_commitment)
        self.assertIsNone(result.protected_object)

    def test_reconstructable_requires_minimized_content(self):
        ingestor = EcosystemChatIngestor(
            pair_id="sha256:pair",
            policy_ref="policy://memory/v1",
            authority_ref="authority://pair/1",
            minimizer=lambda observation: None,
            protector=FakeProtector(),
        )
        observation = ChatObservation(
            observation_id="evt-1",
            event_type="decision",
            plaintext="content",
            approved=True,
            retention_class="reconstructable",
        )
        with self.assertRaises(ValueError):
            ingestor.ingest(observation, sequence=1, previous_event_hash=None)


if __name__ == "__main__":
    unittest.main()

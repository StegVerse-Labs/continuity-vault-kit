import unittest

from reconstructive_memory import (
    AuthorizationContext,
    ChainEvent,
    EphemeralReconstructor,
    ProtectedObject,
    compute_pair_id,
)
from reconstructive_memory.core import _digest


class ReconstructiveMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair_id = compute_pair_id("stegid:user-1", "entity:auri-1", "vault:1", 1)
        self.policy_ref = "policy://memory/v1"

        first = ChainEvent(
            event_id="evt-1",
            sequence=1,
            event_type="proposal",
            pair_id=self.pair_id,
            content_ref="vault://obj/1",
            content_commitment=_digest("Initial proposal"),
            policy_ref=self.policy_ref,
            authority_ref="authority://pair/1",
            retention_class="reconstructable",
            previous_event_hash=None,
        ).with_hash()
        second = ChainEvent(
            event_id="evt-2",
            sequence=2,
            event_type="decision_accepted",
            pair_id=self.pair_id,
            content_ref="vault://obj/2",
            content_commitment=_digest("Accepted decision"),
            policy_ref=self.policy_ref,
            authority_ref="authority://pair/1",
            retention_class="reconstructable",
            previous_event_hash=first.event_hash,
            dependencies=("evt-1",),
        ).with_hash()
        third = ChainEvent(
            event_id="evt-3",
            sequence=3,
            event_type="access_marker",
            pair_id=self.pair_id,
            content_ref=None,
            content_commitment=None,
            policy_ref=self.policy_ref,
            authority_ref="authority://pair/1",
            retention_class="integrity-only",
            previous_event_hash=second.event_hash,
            dependencies=("evt-2",),
        ).with_hash()

        self.events = [first, second, third]
        self.objects = {
            "vault://obj/1": ProtectedObject(
                content_ref="vault://obj/1",
                pair_id=self.pair_id,
                policy_ref=self.policy_ref,
                ciphertext=b"Initial proposal",
                plaintext_commitment=_digest("Initial proposal"),
            ),
            "vault://obj/2": ProtectedObject(
                content_ref="vault://obj/2",
                pair_id=self.pair_id,
                policy_ref=self.policy_ref,
                ciphertext=b"Accepted decision",
                plaintext_commitment=_digest("Accepted decision"),
            ),
        }
        self.auth = AuthorizationContext(
            pair_id=self.pair_id,
            user_proof="signed-user-proof",
            entity_proof="signed-entity-proof",
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            capability_id="capability:ephemeral-1",
        )

    @staticmethod
    def decrypt(obj: ProtectedObject, auth: AuthorizationContext) -> str:
        del auth
        return obj.ciphertext.decode("utf-8")

    def test_reconstructs_dependency_complete_minimal_subgraph(self) -> None:
        engine = EphemeralReconstructor(self.events, self.objects, self.decrypt)
        result = engine.reconstruct(["evt-2"], self.auth)
        self.assertEqual(result.event_ids, ("evt-1", "evt-2"))
        self.assertEqual(result.plaintext_sections, ("Initial proposal", "Accepted decision"))
        self.assertFalse(result.plaintext_retained)
        self.assertTrue(result.workspace_destroyed)

    def test_integrity_only_event_does_not_add_plaintext(self) -> None:
        engine = EphemeralReconstructor(self.events, self.objects, self.decrypt)
        result = engine.reconstruct(["evt-3"], self.auth)
        self.assertEqual(result.event_ids, ("evt-1", "evt-2", "evt-3"))
        self.assertEqual(len(result.plaintext_sections), 2)

    def test_wrong_pair_fails_closed(self) -> None:
        engine = EphemeralReconstructor(self.events, self.objects, self.decrypt)
        wrong = AuthorizationContext(
            pair_id="sha256:wrong",
            user_proof="user",
            entity_proof="entity",
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            capability_id="capability:wrong",
        )
        with self.assertRaises(PermissionError):
            engine.reconstruct(["evt-2"], wrong)

    def test_bounded_window_fails_closed(self) -> None:
        engine = EphemeralReconstructor(self.events, self.objects, self.decrypt)
        with self.assertRaises(ValueError):
            engine.reconstruct(["evt-3"], self.auth, max_events=2)


if __name__ == "__main__":
    unittest.main()

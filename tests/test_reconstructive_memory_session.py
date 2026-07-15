from __future__ import annotations

import unittest

from reconstructive_memory import (
    AuthorizationContext,
    CallableProofVerifier,
    CapabilityGrant,
    ChainEvent,
    ObjectLifecycleRegistry,
    ObjectLifecycleState,
    OpaqueRouteEntry,
    OpaqueRouteIndex,
    ProtectedObject,
    RelationshipRegistry,
    RelationshipState,
    compute_pair_id,
)
from reconstructive_memory.core import _digest
from reconstructive_memory.session import ReconstructionSessionCoordinator


class ReconstructionSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair_id = compute_pair_id("steg:user", "entity:auri", "vault:1", 1)
        self.policy_ref = "policy://memory/v1"
        self.auth = AuthorizationContext(
            pair_id=self.pair_id,
            user_proof="user-proof",
            entity_proof="entity-proof",
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            capability_id="cap:session:1",
        )
        event = ChainEvent(
            event_id="evt-1",
            sequence=1,
            event_type="accepted_context",
            pair_id=self.pair_id,
            content_ref="vault://object/1",
            content_commitment=_digest("accepted context"),
            policy_ref=self.policy_ref,
            authority_ref="authority://pair/1",
            retention_class="reconstructable",
            previous_event_hash=None,
        ).with_hash()
        self.events = (event,)
        self.protected = ProtectedObject(
            content_ref="vault://object/1",
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
            ciphertext=b"accepted context",
            plaintext_commitment=_digest("accepted context"),
        )
        self.relationships = RelationshipRegistry((RelationshipState(
            pair_id=self.pair_id,
            relationship_epoch=1,
            policy_ref=self.policy_ref,
        ),))
        self.lifecycles = ObjectLifecycleRegistry((ObjectLifecycleState(
            content_ref=self.protected.content_ref,
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
        ),))
        self.route_index = OpaqueRouteIndex((OpaqueRouteEntry.build(
            route_token="route-token",
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            event_ids=("evt-1",),
        ),))
        self.capability = CapabilityGrant(
            capability_id=self.auth.capability_id,
            pair_id=self.pair_id,
            policy_ref=self.policy_ref,
            relationship_epoch=1,
            issued_at=100,
            expires_at=200,
            nonce="nonce-1",
        )

    def coordinator(self, *, verifier=None, lifecycles=None):
        return ReconstructionSessionCoordinator(
            events=self.events,
            objects={self.protected.content_ref: self.protected},
            relationships=self.relationships,
            lifecycles=lifecycles or self.lifecycles,
            route_index=self.route_index,
            proof_verifier=verifier or CallableProofVerifier(lambda auth: True, lambda auth: True),
            decrypt=lambda protected, auth: protected.ciphertext.decode("utf-8"),
            resolve_token=lambda query, auth: "route-token",
        )

    def test_success_consumes_capability_and_emits_receipt(self) -> None:
        result = self.coordinator().execute(
            query="recover accepted context",
            auth=self.auth,
            capability=self.capability,
            now=150,
            receipt_id="receipt-1",
        )
        self.assertEqual(result.reconstruction.plaintext_sections, ("accepted context",))
        self.assertEqual(result.consumed_capability.use_count, 1)
        result.receipt.verify()
        self.assertNotIn("recover accepted context", str(result.receipt.payload()))

    def test_failed_proof_does_not_return_consumed_capability(self) -> None:
        verifier = CallableProofVerifier(lambda auth: False, lambda auth: True)
        with self.assertRaises(PermissionError):
            self.coordinator(verifier=verifier).execute(
                query="query",
                auth=self.auth,
                capability=self.capability,
                now=150,
                receipt_id="receipt-1",
            )
        self.assertEqual(self.capability.use_count, 0)

    def test_tombstoned_object_blocks_session(self) -> None:
        lifecycles = self.lifecycles.tombstone(
            self.protected.content_ref,
            reason_code="user-deletion",
            deletion_receipt_ref="receipt://delete/1",
        )
        with self.assertRaises(FileNotFoundError):
            self.coordinator(lifecycles=lifecycles).execute(
                query="query",
                auth=self.auth,
                capability=self.capability,
                now=150,
                receipt_id="receipt-1",
            )

    def test_empty_route_fails_closed(self) -> None:
        coordinator = ReconstructionSessionCoordinator(
            events=self.events,
            objects={self.protected.content_ref: self.protected},
            relationships=self.relationships,
            lifecycles=self.lifecycles,
            route_index=OpaqueRouteIndex(()),
            proof_verifier=CallableProofVerifier(lambda auth: True, lambda auth: True),
            decrypt=lambda protected, auth: protected.ciphertext.decode("utf-8"),
            resolve_token=lambda query, auth: "missing-token",
        )
        with self.assertRaises(LookupError):
            coordinator.execute(
                query="query",
                auth=self.auth,
                capability=self.capability,
                now=150,
                receipt_id="receipt-1",
            )


if __name__ == "__main__":
    unittest.main()

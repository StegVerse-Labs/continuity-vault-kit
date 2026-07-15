from __future__ import annotations

import unittest

from reconstructive_memory import AuthorizationContext, ReconstructionResult
from reconstructive_memory.access import (
    CallableKeyUnwrapper,
    RelationshipRegistry,
    RelationshipState,
    make_access_receipt,
)


class ReconstructiveMemoryAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = AuthorizationContext(
            pair_id="sha256:" + "a" * 64,
            user_proof="user-proof",
            entity_proof="entity-proof",
            policy_ref="policy://kv/reconstruct/v1",
            relationship_epoch=3,
            capability_id="capability-123",
        )
        self.state = RelationshipState(
            pair_id=self.auth.pair_id,
            relationship_epoch=3,
            policy_ref=self.auth.policy_ref,
        )

    def test_active_relationship_resolves_and_unwraps(self) -> None:
        registry = RelationshipRegistry((self.state,))
        resolved = registry.resolve(self.auth)
        unwrapper = CallableKeyUnwrapper(lambda wrapped, auth, relationship: b"data-key")
        self.assertEqual(unwrapper.unwrap(b"wrapped", self.auth, resolved), b"data-key")

    def test_revoked_relationship_fails_closed(self) -> None:
        registry = RelationshipRegistry((self.state,)).revoke(
            self.state.pair_id,
            self.state.relationship_epoch,
            successor_pair_id="sha256:" + "b" * 64,
        )
        with self.assertRaises(PermissionError):
            registry.resolve(self.auth)

    def test_wrong_epoch_fails_closed(self) -> None:
        registry = RelationshipRegistry((self.state,))
        wrong = AuthorizationContext(
            pair_id=self.auth.pair_id,
            user_proof=self.auth.user_proof,
            entity_proof=self.auth.entity_proof,
            policy_ref=self.auth.policy_ref,
            relationship_epoch=4,
            capability_id=self.auth.capability_id,
        )
        with self.assertRaises(PermissionError):
            registry.resolve(wrong)

    def test_access_receipt_contains_commitments_not_plaintext(self) -> None:
        result = ReconstructionResult(
            event_ids=("evt-1", "evt-2"),
            plaintext_sections=("private section",),
            event_range_commitment="sha256:" + "c" * 64,
        )
        receipt = make_access_receipt(
            receipt_id="receipt-1",
            auth=self.auth,
            request_descriptor={"target_event_ids": ["evt-2"], "purpose": "continuity"},
            result=result,
        )
        receipt.verify()
        serialized = str(receipt.payload())
        self.assertNotIn("private section", serialized)
        self.assertNotIn(self.auth.capability_id, serialized)
        self.assertFalse(receipt.plaintext_retained)
        self.assertTrue(receipt.workspace_destroyed)
        self.assertEqual(receipt.event_count, 2)

    def test_empty_unwrap_result_is_rejected(self) -> None:
        unwrapper = CallableKeyUnwrapper(lambda wrapped, auth, relationship: b"")
        with self.assertRaises(PermissionError):
            unwrapper.unwrap(b"wrapped", self.auth, self.state)


if __name__ == "__main__":
    unittest.main()

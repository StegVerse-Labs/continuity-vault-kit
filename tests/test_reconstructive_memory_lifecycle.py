from __future__ import annotations

import unittest

from reconstructive_memory import AuthorizationContext, ProtectedObject, compute_pair_id
from reconstructive_memory.lifecycle import (
    CapabilityGrant,
    ObjectLifecycleRegistry,
    ObjectLifecycleState,
    make_tombstone_event,
)


class CapabilityLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair_id = compute_pair_id("steg:user", "entity:auri", "vault:1", 1)
        self.auth = AuthorizationContext(
            pair_id=self.pair_id,
            user_proof="user-proof",
            entity_proof="entity-proof",
            policy_ref="policy:memory:v1",
            relationship_epoch=1,
            capability_id="cap:one",
        )

    def grant(self) -> CapabilityGrant:
        return CapabilityGrant(
            capability_id="cap:one",
            pair_id=self.pair_id,
            policy_ref="policy:memory:v1",
            relationship_epoch=1,
            issued_at=100,
            expires_at=200,
            nonce="nonce-1",
            max_uses=1,
        )

    def test_single_use_capability_is_consumed(self) -> None:
        consumed = self.grant().consume(self.auth, now=150)
        self.assertEqual(consumed.use_count, 1)
        with self.assertRaises(PermissionError):
            consumed.consume(self.auth, now=151)

    def test_expired_capability_fails_closed(self) -> None:
        with self.assertRaises(PermissionError):
            self.grant().consume(self.auth, now=200)

    def test_revoked_capability_fails_closed(self) -> None:
        with self.assertRaises(PermissionError):
            self.grant().revoke().consume(self.auth, now=150)

    def test_capability_commitment_does_not_expose_secret_fields_directly(self) -> None:
        commitment = self.grant().commitment
        self.assertTrue(commitment.startswith("sha256:"))
        self.assertNotIn("nonce-1", commitment)
        self.assertNotIn("cap:one", commitment)


class ObjectLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair_id = compute_pair_id("steg:user", "entity:auri", "vault:1", 1)
        self.protected = ProtectedObject(
            content_ref="vault://object/1",
            pair_id=self.pair_id,
            policy_ref="policy:memory:v1",
            ciphertext=b"ciphertext",
            plaintext_commitment="sha256:commitment",
        )
        self.registry = ObjectLifecycleRegistry(
            (
                ObjectLifecycleState(
                    content_ref=self.protected.content_ref,
                    pair_id=self.pair_id,
                    policy_ref=self.protected.policy_ref,
                ),
            )
        )

    def test_active_object_is_resolvable(self) -> None:
        state = self.registry.resolve(self.protected)
        self.assertEqual(state.status, "active")

    def test_tombstoned_object_cannot_be_reconstructed(self) -> None:
        registry = self.registry.tombstone(
            self.protected.content_ref,
            reason_code="user-deletion",
            deletion_receipt_ref="receipt://delete/1",
        )
        with self.assertRaises(FileNotFoundError):
            registry.resolve(self.protected)
        state = registry.state(self.protected.content_ref)
        self.assertEqual(state.status, "tombstoned")
        self.assertTrue(state.tombstone_commitment.startswith("sha256:"))

    def test_tombstone_event_retains_no_content_reference(self) -> None:
        state = self.registry.tombstone(
            self.protected.content_ref,
            reason_code="user-deletion",
            deletion_receipt_ref="receipt://delete/1",
        ).state(self.protected.content_ref)
        event = make_tombstone_event(
            event_id="evt:delete:1",
            sequence=2,
            pair_id=self.pair_id,
            policy_ref=self.protected.policy_ref,
            authority_ref="authority:user",
            previous_event_hash="sha256:prior",
            content_ref=self.protected.content_ref,
            tombstone_commitment=state.tombstone_commitment or "",
            dependencies=("evt:original",),
        )
        self.assertIsNone(event.content_ref)
        self.assertEqual(event.retention_class, "integrity-only")
        self.assertEqual(event.event_type, "protected_object_tombstoned")


if __name__ == "__main__":
    unittest.main()

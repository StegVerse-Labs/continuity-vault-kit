from __future__ import annotations

import unittest

from reconstructive_memory import AuthorizationContext, ChainEvent
from reconstructive_memory.access import RelationshipState
from reconstructive_memory.routing import OpaqueRouteEntry, OpaqueRouteIndex, validate_candidate_events


class OpaqueRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = AuthorizationContext(
            pair_id="sha256:" + "d" * 64,
            user_proof="user",
            entity_proof="entity",
            policy_ref="policy://route/v1",
            relationship_epoch=2,
            capability_id="cap-route",
        )
        self.relationship = RelationshipState(
            pair_id=self.auth.pair_id,
            relationship_epoch=2,
            policy_ref=self.auth.policy_ref,
        )
        self.entry = OpaqueRouteEntry.build(
            route_token="opaque-health-token",
            pair_id=self.auth.pair_id,
            policy_ref=self.auth.policy_ref,
            relationship_epoch=2,
            event_ids=("evt-1", "evt-2"),
        )

    def test_authorized_query_returns_only_candidate_ids(self) -> None:
        index = OpaqueRouteIndex((self.entry,))
        result = index.candidates(
            query="private natural language query",
            auth=self.auth,
            relationship=self.relationship,
            resolve_token=lambda query, auth: "opaque-health-token",
        )
        self.assertEqual(result, ("evt-1", "evt-2"))
        self.assertNotIn("private natural language query", repr(self.entry))

    def test_wrong_epoch_fails_closed(self) -> None:
        bad = RelationshipState(
            pair_id=self.auth.pair_id,
            relationship_epoch=3,
            policy_ref=self.auth.policy_ref,
        )
        index = OpaqueRouteIndex((self.entry,))
        with self.assertRaises(PermissionError):
            index.candidates(
                query="query",
                auth=self.auth,
                relationship=bad,
                resolve_token=lambda query, auth: "opaque-health-token",
            )

    def test_candidate_limit_is_enforced(self) -> None:
        entry = OpaqueRouteEntry.build(
            route_token="token",
            pair_id=self.auth.pair_id,
            policy_ref=self.auth.policy_ref,
            relationship_epoch=2,
            event_ids=tuple(f"evt-{i}" for i in range(5)),
        )
        with self.assertRaises(ValueError):
            OpaqueRouteIndex((entry,)).candidates(
                query="query",
                auth=self.auth,
                relationship=self.relationship,
                resolve_token=lambda query, auth: "token",
                max_candidates=3,
            )

    def test_routed_event_binding_is_rechecked(self) -> None:
        event = ChainEvent(
            event_id="evt-1",
            sequence=1,
            event_type="accepted_context",
            pair_id=self.auth.pair_id,
            content_ref=None,
            content_commitment=None,
            policy_ref=self.auth.policy_ref,
            authority_ref="authority://pair/2",
            retention_class="integrity-only",
            previous_event_hash=None,
        ).with_hash()
        self.assertEqual(validate_candidate_events(("evt-1",), (event,), self.auth), ("evt-1",))


if __name__ == "__main__":
    unittest.main()

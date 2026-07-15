from __future__ import annotations

import unittest

from reconstructive_memory import (
    AuthoritativeSessionStore,
    AuthorizationContext,
    CapabilityGrant,
    ReconstructionResult,
    ReconstructionSessionResult,
    make_access_receipt,
)


class AuthoritativeSessionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = AuthorizationContext(
            pair_id="sha256:" + "a" * 64,
            user_proof="user-proof",
            entity_proof="entity-proof",
            policy_ref="policy://memory/v1",
            relationship_epoch=1,
            capability_id="capability-1",
        )
        self.capability = CapabilityGrant(
            capability_id=self.auth.capability_id,
            pair_id=self.auth.pair_id,
            policy_ref=self.auth.policy_ref,
            relationship_epoch=1,
            issued_at=100,
            expires_at=200,
            nonce="nonce-1",
        )
        self.store = AuthoritativeSessionStore(self.capability)

    def result(self) -> ReconstructionSessionResult:
        reconstruction = ReconstructionResult(
            event_ids=("evt-1",),
            plaintext_sections=("private result",),
            event_range_commitment="sha256:" + "b" * 64,
        )
        receipt = make_access_receipt(
            receipt_id="receipt-1",
            auth=self.auth,
            request_descriptor={"candidate_count": 1},
            result=reconstruction,
        )
        return ReconstructionSessionResult(
            reconstruction=reconstruction,
            receipt=receipt,
            consumed_capability=self.capability.consume(self.auth, now=150),
        )

    def prepare(self):
        return self.store.prepare(
            session_id="session-1",
            pair_id=self.auth.pair_id,
            policy_ref=self.auth.policy_ref,
            relationship_epoch=1,
            request_commitment="sha256:" + "c" * 64,
        )

    def test_commit_persists_receipt_capability_and_journal_together(self) -> None:
        prepared = self.prepare()
        snapshot = self.store.commit(prepared=prepared, result=self.result())
        self.assertEqual(snapshot.capability.use_count, 1)
        self.assertEqual(snapshot.receipt.receipt_id, "receipt-1")
        self.assertEqual(snapshot.journal.entries[-1].status, "committed")
        self.assertEqual(self.store.receipt("receipt-1").receipt_hash, snapshot.receipt.receipt_hash)

    def test_stale_capability_state_blocks_commit(self) -> None:
        prepared = self.prepare()
        self.store._capability = self.capability.consume(self.auth, now=150)
        with self.assertRaisesRegex(PermissionError, "changed after preparation"):
            self.store.commit(prepared=prepared, result=self.result())

    def test_duplicate_session_is_rejected_before_new_prepare(self) -> None:
        self.prepare()
        with self.assertRaisesRegex(PermissionError, "replay"):
            self.prepare()

    def test_abort_does_not_consume_capability_or_store_receipt(self) -> None:
        prepared = self.prepare()
        self.store.abort(prepared=prepared, failure_code="ROUTE_EMPTY")
        self.assertEqual(self.store.capability.use_count, 0)
        self.assertEqual(self.store.journal.entries[-1].status, "aborted")
        with self.assertRaises(KeyError):
            self.store.receipt("receipt-1")

    def test_journal_and_store_do_not_retain_plaintext(self) -> None:
        prepared = self.prepare()
        self.store.commit(prepared=prepared, result=self.result())
        serialized = repr([entry.payload() for entry in self.store.journal.entries])
        self.assertNotIn("private result", serialized)


if __name__ == "__main__":
    unittest.main()
